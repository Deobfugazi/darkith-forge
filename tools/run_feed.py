#!/usr/bin/env python3
"""run_feed.py — the live post-run report feed for every agentic round trip.

WHY
    A run that finishes and prints to a terminal leaves no witness. Co-operators cannot
    see progress while it happens, and automation cannot tell a run that finished from a
    run that was severed mid-flight by a reset, an OOM kill, or a broken connection. Both
    failures look identical afterwards: silence. This feed makes silence measurable.

WHAT IT IS
    An append-only, hash-chained JSONL ledger at `proof/run_feed.jsonl`. Every agentic
    round trip writes a `start`, any number of `stage` and `heartbeat` entries, and
    exactly one `terminal`. Each entry carries the contributor identity that produced it
    (agent, model, vendor, session, tab) so an audience can attribute every line.

WHY IT IS HASH-CHAINED
    The same reason as `ci_receipts.py`: a feed nobody can tamper with is evidence; a feed
    anyone can rewrite is a story. Each entry commits to its predecessor's hash, so editing
    history breaks every descendant and `--verify` says so.

THE SEVERANCE DETECTOR (the point)
    A run with a `start` and no `terminal`, whose last entry is older than the timeout, is
    SEVERED. That is the "broken circuitry" case: the agent died, the sandbox reset, the
    socket dropped. `--severed` exits non-zero and names those runs, so automation picks
    them up instead of waiting forever on a run that will never report.

IDENTITY IS RECORDED, NOT GUESSED
    A model name that is not in the environment is written as `UNKNOWN`, never invented.
    An honest `UNKNOWN` is useful; a confident wrong attribution poisons every downstream
    audit that trusts this feed.

USAGE
    python3 tools/run_feed.py start   --run-id X --stage S01 --detail "..."
    python3 tools/run_feed.py stage   --run-id X --stage S06 --verdict PASS
    python3 tools/run_feed.py heartbeat --run-id X
    python3 tools/run_feed.py terminal --run-id X --verdict PASS
    python3 tools/run_feed.py verify            # recompute the chain
    python3 tools/run_feed.py severed           # exit 1 if any run is severed
    python3 tools/run_feed.py render            # markdown feed for the audience
    python3 tools/run_feed.py stream            # follow new entries

Exit: 0 ok; 1 verification failed or a run is severed; 3 nothing to report.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
import pathlib
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import omega_time  # noqa: E402  the Operator's clock (MUST #15)

FEED = ROOT / "proof" / "run_feed.jsonl"

# A run whose last entry is older than this, with no terminal, is severed. Fifteen
# minutes is above the longest legitimate silent stage (a full kotlinc compile on this
# tree) and below a human's patience for a dead run.
SEVERED_AFTER_SECONDS = int(os.environ.get("RUN_FEED_SEVERED_AFTER", 900))

TERMINAL_KINDS = ("terminal",)


def now() -> str:
    # The Operator's clock (MUST #15): one implementation, Asia/Manila. A bare wall-clock
    # here would be a second, forked time source.
    return omega_time.iso()


def identity() -> dict:
    """The contributor identity for an entry, taken from the environment.

    Anything absent is `UNKNOWN`. The vendor transport is real evidence from the
    environment; the model name is not exposed to this process, so it stays UNKNOWN
    unless the caller supplies `--model`.
    """
    proxy = os.environ.get("OH_LLM_API_KEY_REFRESH_BASE_URLS", "")
    vendor = "UNKNOWN"
    if proxy:
        host = proxy.split("//")[-1].split("/")[0]
        vendor = host or "UNKNOWN"
    return {
        "agent": os.environ.get("AI_AGENT", "UNKNOWN"),
        "model": os.environ.get("RUN_FEED_MODEL", "UNKNOWN"),
        "vendor": vendor,
        "session": os.environ.get("OH_SESSION_ID")
                   or os.environ.get("CONVERSATION_ID", "UNKNOWN"),
        "tab": os.environ.get("RUN_FEED_TAB_ID", "UNKNOWN"),
    }


def _canonical(entry: dict) -> bytes:
    body = {k: v for k, v in entry.items() if k != "hash"}
    return json.dumps(body, sort_keys=True, separators=(",", ":")).encode()


def _digest(entry: dict) -> str:
    return hashlib.sha256(_canonical(entry)).hexdigest()


def read_entries() -> list:
    if not FEED.is_file():
        return []
    out = []
    for line in FEED.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            # A torn final line is the signature of a run killed mid-write. Keep what
            # parsed; `verify` will report the truncation rather than hide it.
            out.append({"__torn__": line})
    return out


def append(kind: str, run_id: str, stage: str = "", verdict: str = "",
           detail: str = "", **extra) -> dict:
    entries = read_entries()
    prev = ""
    for entry in reversed(entries):
        if "hash" in entry:
            prev = entry["hash"]
            break
    entry = {
        "seq": len([e for e in entries if "hash" in e]) + 1,
        "ts": now(),
        "kind": kind,
        "run_id": run_id,
        "stage": stage,
        "verdict": verdict,
        "detail": detail,
        "prev": prev,
        **identity(),
    }
    entry.update({k: v for k, v in extra.items() if v is not None})
    entry["hash"] = _digest(entry)
    FEED.parent.mkdir(parents=True, exist_ok=True)
    with FEED.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, sort_keys=True) + "\n")
    return entry


def verify() -> tuple:
    """Recompute every hash and every link. Returns (ok, problems)."""
    entries = read_entries()
    problems = []
    prev = ""
    expected_seq = 1
    for index, entry in enumerate(entries, 1):
        if "__torn__" in entry:
            problems.append(f"line {index}: torn/unparseable entry (run killed mid-write?)")
            continue
        recomputed = _digest(entry)
        if recomputed != entry.get("hash"):
            problems.append(f"line {index} (seq {entry.get('seq')}): hash mismatch — "
                            f"stored {entry.get('hash', '')[:12]}, "
                            f"recomputed {recomputed[:12]}")
        if entry.get("prev") != prev:
            problems.append(f"line {index} (seq {entry.get('seq')}): broken link — "
                            f"prev {entry.get('prev', '')[:12]} != {prev[:12]}")
        if entry.get("seq") != expected_seq:
            problems.append(f"line {index}: seq {entry.get('seq')} != expected {expected_seq}")
        prev = entry.get("hash", "")
        expected_seq += 1
    return (not problems, problems)


def runs() -> dict:
    """Group entries by run_id, preserving order."""
    grouped = {}
    for entry in read_entries():
        if "__torn__" in entry:
            continue
        grouped.setdefault(entry.get("run_id", "UNKNOWN"), []).append(entry)
    return grouped


def _age_seconds(entry: dict) -> float:
    try:
        stamp = _dt.datetime.fromisoformat(entry["ts"])
    except (KeyError, ValueError):
        return float("inf")
    return (omega_time.now() - stamp).total_seconds()


def severed(timeout: int = SEVERED_AFTER_SECONDS) -> list:
    """Runs that started and never reported a terminal, now silent past the timeout."""
    out = []
    for run_id, entries in runs().items():
        if not entries:
            continue
        if any(e.get("kind") in TERMINAL_KINDS for e in entries):
            continue
        last = entries[-1]
        age = _age_seconds(last)
        if age > timeout:
            out.append({
                "run_id": run_id,
                "last_kind": last.get("kind"),
                "last_stage": last.get("stage"),
                "silent_seconds": int(age),
                "agent": last.get("agent"),
                "session": last.get("session"),
                "reason": "no terminal entry; run was severed (reset, OOM, or dropped "
                          "connection) and will never report on its own",
            })
    return out


def render(limit: int = 40) -> list:
    """Markdown feed: one row per entry, newest last, identity on every row."""
    entries = [e for e in read_entries() if "__torn__" not in e]
    if not entries:
        return ["_The feed is empty. No agentic round trip has reported yet._"]
    cut = entries[-limit:]
    lines = [
        f"| # | when ({omega_time.TZ_NAME}) | run | stage | verdict | contributor | tab | detail |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for entry in cut:
        who = f"{entry.get('agent', '?')}/{entry.get('model', '?')}"
        lines.append(
            f"| {entry.get('seq')} | {entry.get('ts', '')[11:19]} | "
            f"`{entry.get('run_id', '?')}` | {entry.get('stage') or '—'} | "
            f"{entry.get('verdict') or entry.get('kind')} | {who} | "
            f"{entry.get('tab') or 'UNKNOWN'} | "
            f"{(entry.get('detail') or '').replace('|', '/')[:90]} |")
    return lines


def stream(poll: float = 2.0) -> int:
    """Follow the feed, printing new entries as they land."""
    seen = 0
    if FEED.is_file():
        seen = len(FEED.read_text(encoding="utf-8").splitlines())
    print(f"following {FEED} (from line {seen + 1}); Ctrl-C to stop", flush=True)
    try:
        while True:
            if FEED.is_file():
                lines = FEED.read_text(encoding="utf-8").splitlines()
                for line in lines[seen:]:
                    try:
                        entry = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    print(f"{entry.get('ts', '')[11:19]} "
                          f"[{entry.get('run_id')}] {entry.get('kind')} "
                          f"{entry.get('stage') or ''} {entry.get('verdict') or ''} "
                          f"{entry.get('detail') or ''}", flush=True)
                seen = len(lines)
            time.sleep(poll)
    except KeyboardInterrupt:
        return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("action", choices=[
        "start", "stage", "heartbeat", "terminal", "verify", "severed", "render", "stream"])
    parser.add_argument("--run-id", default="")
    parser.add_argument("--stage", default="")
    parser.add_argument("--verdict", default="")
    parser.add_argument("--detail", default="")
    parser.add_argument("--model", default=None)
    parser.add_argument("--tab-id", default=None)
    parser.add_argument("--limit", type=int, default=40)
    parser.add_argument("--timeout", type=int, default=SEVERED_AFTER_SECONDS)
    args = parser.parse_args(argv)

    if args.model is not None:
        os.environ["RUN_FEED_MODEL"] = args.model
    if args.tab_id is not None:
        os.environ["RUN_FEED_TAB_ID"] = args.tab_id

    if args.action == "verify":
        ok, problems = verify()
        if ok:
            print(f"run_feed: PASS — {len(read_entries())} entries, chain intact")
            return 0
        print(f"run_feed: FAIL — {len(problems)} problem(s):")
        for problem in problems[:20]:
            print("  " + problem)
        return 1

    if args.action == "severed":
        found = severed(args.timeout)
        if not found:
            print(f"run_feed: PASS — no severed run (silence timeout {args.timeout}s)")
            return 0
        print(f"run_feed: SEVERED — {len(found)} run(s) died without a terminal:")
        for item in found:
            print(f"  {item['run_id']}: silent {item['silent_seconds']}s after "
                  f"{item['last_kind']}/{item['last_stage']} ({item['agent']})")
        return 1

    if args.action == "render":
        print("\n".join(render(args.limit)))
        return 0

    if args.action == "stream":
        return stream()

    if not args.run_id:
        print("run_feed: --run-id is required for this action", file=sys.stderr)
        return 2

    entry = append(args.action, args.run_id, stage=args.stage,
                   verdict=args.verdict, detail=args.detail)
    print(f"{entry['seq']} {entry['kind']} {entry['run_id']} {entry['stage']} "
          f"{entry['verdict']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

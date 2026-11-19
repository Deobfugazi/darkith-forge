#!/usr/bin/env python3
"""stall_clock.py — MUST #36 (NO OFF-SCHEDULE DWELL). Measures stall as TIME, not as a flag.

`tools/board_pulse.sh --check` answers a yes/no question: is the board on the remote? That is
necessary but blind to the dimension that actually costs the Operator — LATENCY. Work can be
"about to be pushed" for an hour and every existing gate stays green, because no gate ever
measured how long the bytes sat still.

This gate measures dwell directly, from git (deterministic, no wall-clock guessing):

    unpushed_dwell  = now - committer time of the OLDEST commit on the branch that origin
                      does not have. Zero when local == origin.
    dirty_dwell     = now - mtime of the OLDEST dirty path (a FLOOR: the true age is at
                      least this, since the file was touched when the work happened).

A dwell over budget is an OFF-SCHEDULE STALL and fails CI. The numbers are written to
`proof/stall_clock.json` so a parallel worker reads the measured stall instead of inferring it.

Budgets live in `STALL_BUDGET.json` at the repo root so the Operator sets the schedule, not
the agent. Missing config is a FAIL, never a default: a gate that invents its own tolerance
cannot be trusted to hold a promise.

Usage:
    python3 tools/stall_clock.py            # check (exit 1 on an over-budget dwell)
    python3 tools/stall_clock.py --write    # check + record proof/stall_clock.json
    python3 tools/stall_clock.py --json     # machine-readable summary on stdout
"""
from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
CONFIG = ROOT / "STALL_BUDGET.json"
PROOF = ROOT / "proof" / "stall_clock.json"


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True, check=False
    ).stdout.strip()


def is_detached() -> bool:
    return subprocess.run(
        ["git", "symbolic-ref", "-q", "HEAD"], cwd=ROOT, capture_output=True
    ).returncode != 0


def load_budget() -> dict:
    if not CONFIG.is_file():
        raise SystemExit(
            "stall_clock: FAIL — no STALL_BUDGET.json. The schedule is the Operator's to set; "
            "an invented default cannot hold a promise."
        )
    try:
        cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"stall_clock: FAIL — STALL_BUDGET.json is not valid JSON: {exc}")
    for key in ("unpushed_seconds", "dirty_seconds"):
        if not isinstance(cfg.get(key), int) or cfg[key] <= 0:
            raise SystemExit(f"stall_clock: FAIL — STALL_BUDGET.json needs a positive int '{key}'")
    return cfg


def unpushed_commits(remote: str, branch: str) -> list[dict]:
    """Commits on the branch that the remote does not have, oldest first."""
    git("fetch", "-q", remote, branch)
    ref = f"{remote}/{branch}"
    if subprocess.run(
        ["git", "rev-parse", "--verify", "-q", ref], cwd=ROOT, capture_output=True
    ).returncode != 0:
        return []
    out = git("log", "--reverse", "--format=%H%x00%ct%x00%s", f"{ref}..HEAD")
    rows = []
    for line in filter(None, out.splitlines()):
        sha, ctime, subject = line.split("\x00", 2)
        rows.append({"sha": sha[:12], "epoch": int(ctime), "subject": subject[:72]})
    return rows


def dirty_paths() -> list[dict]:
    out = git("status", "--porcelain")
    rows = []
    for line in filter(None, out.splitlines()):
        path = line[3:].strip().strip('"')
        if " -> " in path:  # rename: measure the destination
            path = path.split(" -> ", 1)[1].strip().strip('"')
        target = ROOT / path
        if target.is_file():
            rows.append({"path": path, "mtime": int(target.stat().st_mtime)})
    return rows


def main(argv: list[str]) -> int:
    write = "--write" in argv
    as_json = "--json" in argv
    now = int(time.time())

    if is_detached():
        msg = "stall_clock: SKIP — detached HEAD (CI PR checkout); dwell applies to the writer's branch"
        print(json.dumps({"verdict": "SKIP", "reason": msg}) if as_json else msg)
        return 0

    budget = load_budget()
    remote = os.environ.get("DARKITH_REMOTE", "origin")
    branch = git("rev-parse", "--abbrev-ref", "HEAD") or "main"

    commits = unpushed_commits(remote, branch)
    unpushed_dwell = now - commits[0]["epoch"] if commits else 0

    dirty = dirty_paths()
    dirty_dwell = now - min(r["mtime"] for r in dirty) if dirty else 0

    breaches = []
    if unpushed_dwell > budget["unpushed_seconds"]:
        breaches.append(
            f"unpushed work held {unpushed_dwell}s > {budget['unpushed_seconds']}s budget "
            f"({len(commits)} commit(s), oldest {commits[0]['sha']} {commits[0]['subject']!r})"
        )
    if dirty_dwell > budget["dirty_seconds"]:
        breaches.append(
            f"uncommitted work held >= {dirty_dwell}s > {budget['dirty_seconds']}s budget "
            f"({len(dirty)} path(s), oldest {dirty[0]['path']!r})"
        )

    verdict = "FAIL" if breaches else "PASS"
    record = {
        "verdict": verdict,
        "measured_at": now,
        "measured_at_iso": time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(now)),
        "branch": branch,
        "remote": remote,
        "unpushed": {
            "count": len(commits),
            "dwell_seconds": unpushed_dwell,
            "budget_seconds": budget["unpushed_seconds"],
            "oldest": commits[0] if commits else None,
        },
        "dirty": {
            "count": len(dirty),
            "dwell_seconds_floor": dirty_dwell,
            "budget_seconds": budget["dirty_seconds"],
            "oldest_path": dirty[0]["path"] if dirty else None,
        },
        "breaches": breaches,
    }

    if write:
        PROOF.parent.mkdir(parents=True, exist_ok=True)
        PROOF.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")

    if as_json:
        print(json.dumps(record, indent=2))
    else:
        print(
            f"stall_clock: {verdict} — unpushed {len(commits)} commit(s) dwelling "
            f"{unpushed_dwell}s/{budget['unpushed_seconds']}s; "
            f"uncommitted {len(dirty)} path(s) dwelling >={dirty_dwell}s/{budget['dirty_seconds']}s"
        )
        for b in breaches:
            print(f"    OFF-SCHEDULE STALL: {b}")
        if verdict == "FAIL":
            print("    remedy: push now (tools/board_pulse.sh) or commit; dwell is the defect.")
    return 1 if breaches else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

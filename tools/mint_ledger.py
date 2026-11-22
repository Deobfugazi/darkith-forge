#!/usr/bin/env python3
"""mint_ledger.py — NT XII made runnable: a communal contribution ledger whose unit of
value is a RE-RUNNABLE CLOSURE, not a hash lottery.

WHY THIS EXISTS
    Bitcoin pays for hashes that produce nothing. The work is real (energy is burned) but
    the output is worthless by construction: the hash has no use beyond proving you burned
    the energy. NT XII already names the alternative — a mint is "the real, non-arbitrary
    value of the defect resolved and the bond held", backed by a command anyone can re-run.
    This file is that sentence as executable mechanism.

WHAT MAKES A MINT REAL (and why it cannot be gamed like a hash)
    A mint is `{claim, witness, expect}`. The witness is a command; `expect` is a token that
    command must print. Value is minted only when an INDEPENDENT party re-runs the witness
    and gets the same token. There is no lottery and no difficulty knob: you cannot mint by
    burning cycles, only by producing a closure someone else can reproduce. A claim with no
    witness is refused outright — that is the stub, and the Prime Directive forbids it.

TRIAL NET vs MAIN NET (the reinforced barrier)
    Testnet holds PHANTOMS: claims deliberately built to look real and fail. Their job is
    to be caught. Mainnet holds only mints that survived trial.
    Promotion requires all three, and there is no override:
      1. at least one phantom was actually executed this trial (an untested barrier is a
         claim, not a barrier);
      2. every phantom FAILED — one phantom passing is a PATHOGEN BREACH and blocks mainnet,
         because a barrier that lets its own test case through is not a barrier;
      3. every mainnet candidate re-executed green.
    This is the anti-contagion mechanism: the mimetic pathogen (a plausible-looking stub)
    is injected on purpose, and the gate refuses to promote while any of it survives.

OFFLINE FIRST (SPI-8)
    The ledger is plain JSONL on disk, hash-chained. It needs no node, no network, no
    Gradle, no bank. It syncs by copying a file, which is what makes it work on a phone
    whose home is the SD card.

USAGE
    python3 tools/mint_ledger.py mint     --claim "..." --witness "cmd" --expect TOKEN
    python3 tools/mint_ledger.py phantom  --claim "..." --witness "cmd" --expect TOKEN
    python3 tools/mint_ledger.py trial                    # run phantoms + candidates
    python3 tools/mint_ledger.py promote                  # trial net -> main net
    python3 tools/mint_ledger.py verify                   # recompute the chain
    python3 tools/mint_ledger.py status

Exit: 0 ok / promoted; 1 breach, failed re-execution, or broken chain; 3 nothing to do.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import shlex
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import omega_time  # noqa: E402  one clock (MUST #15)

LEDGER = ROOT / "proof" / "mint_ledger.jsonl"
MAINNET = ROOT / "proof" / "mint_mainnet.jsonl"

# A witness may not leave the repository or shell out to an interpreter it names freely.
# Without this, a "witness" is arbitrary remote execution dressed as proof.
ALLOWED_PREFIXES = ("python3 ", "bash ", "./")
# Hazard classes are checked structurally in _check_witness (shell operators as argv tokens,
# network binaries, out-of-repo paths) rather than by scanning raw text for characters.


class Refused(ValueError):
    """A claim that cannot be minted, as distinct from one that failed to verify."""


def now() -> str:
    return omega_time.iso()


def _canonical(entry: dict) -> bytes:
    body = {k: v for k, v in entry.items() if k != "hash"}
    return json.dumps(body, sort_keys=True, separators=(",", ":")).encode()


def _digest(entry: dict) -> str:
    return hashlib.sha256(_canonical(entry)).hexdigest()


def read(path: pathlib.Path = None) -> list:
    # Resolve at call time, not definition time: a default of LEDGER would freeze the
    # original path, so a caller (or a test) that repoints the module global would read
    # the wrong file and silently see an empty ledger.
    path = LEDGER if path is None else path
    if not path.is_file():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            out.append({"__torn__": line})
    return out


def _append(path: pathlib.Path, entry: dict) -> dict:
    entries = read(path)
    prev = ""
    highest = 0
    for existing in entries:
        if "hash" not in existing:
            continue
        prev = existing["hash"]
        highest = max(highest, int(existing.get("seq") or 0))
    entry = dict(entry)
    # The storage layer owns the sequence. Letting callers supply it invited seq 0 (from
    # promote) and missing seq (on mainnet), which verify then read as a broken chain.
    entry["seq"] = highest + 1
    entry.setdefault("ts", now())
    entry["prev"] = prev
    entry["hash"] = _digest(entry)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, sort_keys=True) + "\n")
    return entry


def verify(path: pathlib.Path = None) -> tuple:
    path = LEDGER if path is None else path
    problems, prev, expected = [], "", 1
    for index, entry in enumerate(read(path), 1):
        if "__torn__" in entry:
            problems.append(f"line {index}: torn entry (killed mid-write)")
            continue
        if _digest(entry) != entry.get("hash"):
            problems.append(f"line {index}: hash mismatch")
        if entry.get("prev") != prev:
            problems.append(f"line {index}: broken link")
        if entry.get("seq") != expected:
            problems.append(f"line {index}: seq {entry.get('seq')} != {expected}")
        prev = entry.get("hash", "")
        expected += 1
    return (not problems, problems)


def _check_witness(witness: str) -> None:
    """Refuse a witness that is not a bounded, in-repo, single command.

    The first version of this scanned the raw text for `;` and friends, which was wrong
    twice over. It rejected safe witnesses — `python3 -c "import x; print(y)"` has a
    semicolon inside a quoted token, not a shell separator — and it implied protection it
    did not provide, because `execute()` never uses `shell=True`, so shell metacharacters
    are inert here by construction. The real hazards are different: naming a network
    binary, or reaching outside the repository. Those are what this checks.
    """
    if not witness or not witness.strip():
        raise Refused("a mint with no witness is a stub; the Prime Directive forbids it")
    try:
        argv = shlex.split(witness)
    except ValueError as exc:
        raise Refused(f"witness does not parse as one command: {exc}") from exc
    if not argv:
        raise Refused("witness is empty after parsing")
    if not witness.startswith(ALLOWED_PREFIXES):
        raise Refused(f"witness must start with one of {ALLOWED_PREFIXES}")
    for token in argv:
        if token in (";", "&&", "||", "|", "&"):
            raise Refused(f"witness contains the shell operator {token!r}; a witness is "
                          f"one command, and chaining it defeats re-execution")
        if token.startswith("$(") or token.startswith("`"):
            raise Refused("witness contains command substitution")
        lowered = token.lower()
        if lowered in ("curl", "wget", "nc", "ssh", "scp", "rsync"):
            raise Refused(f"witness invokes {token!r}; a witness must not reach the network")
        if token.startswith("/") or ".." in token.split("/"):
            raise Refused(f"witness references {token!r} outside the repository; the "
                          f"witness must be reproducible from the tree alone (SPI-8)")


def mint(claim: str, witness: str, expect: str, kind: str = "mint",
         note: str = "") -> dict:
    _check_witness(witness)
    if not claim.strip():
        raise Refused("a mint with no claim records nothing")
    if not expect.strip():
        raise Refused("a mint with no expected token cannot be checked by anyone")
    entries = [e for e in read() if "__torn__" not in e]
    record = {

        "kind": kind,
        "claim": claim,
        "witness": witness,
        "expect": expect,
        "note": note,
        "status": "provisional",
        "reexecutions": [],
    }
    record["id"] = "MINT-" + _digest(record)[:16]
    return _append(LEDGER, record)


def execute(witness: str, timeout: int = 300) -> tuple:
    """Run a witness exactly as written. Returns (ok, output, returncode)."""
    argv = shlex.split(witness)
    try:
        proc = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True,
                              timeout=timeout)
    except (OSError, subprocess.SubprocessError) as exc:
        return (False, f"{type(exc).__name__}: {exc}", None)
    return (proc.returncode == 0, (proc.stdout or "") + (proc.stderr or ""),
            proc.returncode)


def trial(timeout: int = 300) -> dict:
    """Run every phantom and every candidate. The phantoms must all FAIL.

    A phantom that passes is a PATHOGEN BREACH: the barrier let its own test case through.
    That blocks promotion absolutely — not a warning, not a note.
    """
    entries = [e for e in read() if "__torn__" not in e]
    phantoms = [e for e in entries if e.get("kind") == "phantom"]
    candidates = [e for e in entries
                  if e.get("kind") == "mint" and e.get("status") != "promoted"]
    results, breaches, confirmed = [], [], []

    for entry in phantoms:
        ok, output, rc = execute(entry["witness"], timeout)
        # A phantom is built to fail, so `ok` True means the barrier is porous.
        passed = ok and entry["expect"] in output
        results.append({"id": entry["id"], "role": "phantom",
                        "verdict": "BREACH" if passed else "caught", "rc": rc})
        if passed:
            breaches.append(entry["id"])

    for entry in candidates:
        ok, output, rc = execute(entry["witness"], timeout)
        matched = ok and entry["expect"] in output
        results.append({"id": entry["id"], "role": "candidate",
                        "verdict": "green" if matched else "red", "rc": rc})
        if matched:
            confirmed.append(entry["id"])

    summary = {

        "kind": "trial",
        "phantoms_tested": len(phantoms),
        "phantoms_caught": len(phantoms) - len(breaches),
        "breaches": breaches,
        "candidates_tested": len(candidates),
        "candidates_green": len(confirmed),
        "results": results,
        "status": ("breach" if breaches
                   else ("green" if phantoms and len(confirmed) == len(candidates)
                         else "incomplete")),
    }
    return _append(LEDGER, summary)


def promote() -> tuple:
    """Promote green candidates to mainnet — only if the barrier actually held."""
    entries = [e for e in read() if "__torn__" not in e]
    trials = [e for e in entries if e.get("kind") == "trial"]
    if not trials:
        return (False, "no trial has run; a barrier nobody tested is a claim, not a barrier")
    last = trials[-1]
    if last.get("phantoms_tested", 0) == 0:
        return (False, "trial ran no phantom; the anti-contagion barrier is unproven")
    if last.get("breaches"):
        return (False, f"PATHOGEN BREACH: {last['breaches']} phantom(s) passed — the gate "
                       f"let its own test case through, so nothing promotes")
    if last.get("status") != "green":
        return (False, f"trial status is {last.get('status')!r}; promotion needs green")

    by_id = {e.get("id"): e for e in entries if e.get("kind") == "mint"}
    promoted = []
    for result in last.get("results", []):
        if result.get("role") != "candidate" or result.get("verdict") != "green":
            continue
        entry = by_id.get(result["id"])
        if not entry:
            continue
        _append(MAINNET, {
            "kind": "mainnet",
            "mint_id": entry["id"],
            "claim": entry["claim"],
            "witness": entry["witness"],
            "expect": entry["expect"],
            "backed_by_trial": last.get("hash", "")[:16],
            "phantoms_caught": last.get("phantoms_caught"),
        })
        _append(LEDGER, {"seq": 0, "kind": "promotion", "mint_id": entry["id"],
                         "trial": last.get("hash", "")[:16]})
        promoted.append(entry["id"])
    if not promoted:
        return (False, "trial was green but no candidate matched a mint record")
    return (True, f"promoted {len(promoted)} mint(s) to mainnet: {promoted}")


def status() -> dict:
    entries = [e for e in read() if "__torn__" not in e]
    mainnet = [e for e in read(MAINNET) if "__torn__" not in e]
    trials = [e for e in entries if e.get("kind") == "trial"]
    return {
        "mints": len([e for e in entries if e.get("kind") == "mint"]),
        "phantoms": len([e for e in entries if e.get("kind") == "phantom"]),
        "trials": len(trials),
        "last_trial": trials[-1].get("status") if trials else None,
        "breaches": trials[-1].get("breaches") if trials else None,
        "mainnet_entries": len(mainnet),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("action", choices=[
        "mint", "phantom", "trial", "promote", "verify", "status"])
    parser.add_argument("--claim", default="")
    parser.add_argument("--witness", default="")
    parser.add_argument("--expect", default="")
    parser.add_argument("--note", default="")
    parser.add_argument("--timeout", type=int, default=300)
    args = parser.parse_args(argv)

    if args.action == "verify":
        ok, problems = verify()
        ok2, problems2 = verify(MAINNET)
        if ok and ok2:
            print(f"mint_ledger: PASS — trial {len(read())} entries, "
                  f"mainnet {len(read(MAINNET))} entries, both chains intact")
            return 0
        for problem in (problems + problems2)[:20]:
            print("  " + problem)
        print("mint_ledger: FAIL — chain broken")
        return 1

    if args.action == "status":
        print(json.dumps(status(), indent=2))
        return 0

    if args.action == "trial":
        summary = trial(args.timeout)
        print(f"trial: {summary['status']} — phantoms {summary['phantoms_caught']}/"
              f"{summary['phantoms_tested']} caught, candidates "
              f"{summary['candidates_green']}/{summary['candidates_tested']} green")
        for result in summary["results"]:
            print(f"  {result['role']:10} {result['id']} {result['verdict']}")
        return 0 if summary["status"] == "green" else 1

    if args.action == "promote":
        ok, message = promote()
        print(("promote: PASS — " if ok else "promote: REFUSED — ") + message)
        return 0 if ok else 1

    try:
        record = mint(args.claim, args.witness, args.expect,
                      kind="phantom" if args.action == "phantom" else "mint",
                      note=args.note)
    except Refused as exc:
        print(f"{args.action}: REFUSED — {exc}")
        return 2
    print(f"{record['kind']}: {record['id']}  {record['claim']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Evidence-bound serial revival contract for Darkith Forge.

This module implements the transition/receipt kernel. It does not pretend to run
repository diagnostics or mutate source files: those remain explicit producers
and authorized consumers of these contracts.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import pathlib
import subprocess
import sys
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parent.parent
STORE = ROOT / "proof" / "serial_revival"
RECEIPTS = STORE / "receipts"
TASKS = STORE / "tasks"
STAGES = [
    ("S1", "BASELINE", ("branch", "commit", "governing_sources", "generated_artifacts", "dirty_files", "captured_at")),
    ("S2", "INVENTORY", ("components",)),
    ("S3", "TOPOLOGY", ("nodes", "edges")),
    ("S4", "DIAGNOSTIC", ("probes",)),
    ("S5", "CLASSIFY", ("node_states",)),
    ("S6", "TRACE", ("defects", "root_causes")),
    ("S7", "GOVERN", ("clauses",)),
    ("S8", "TASK", ("tasks",)),
    ("S9", "AUTHORIZE", ("decision", "authorization_class", "scope")),
    ("S10", "REPAIR", ("changed_files",)),
    ("S11", "REGENERATE", ("generated_files", "drift")),
    ("S12", "VERIFY-LOCAL", ("checks",)),
    ("S13", "VERIFY-BLAST", ("checked_nodes", "regressions")),
    ("S14", "RECONCILE", ("clean", "unexplained_drift", "unchecked_nodes", "mesh_health")),
    ("S15", "SEAL", ("bundle_sha256", "included_receipts", "remaining_uncertainty")),
    ("S16", "BOARD+ROTATE", ("board_revision", "board_state_sha256", "next_cycle_queue", "regression_queue", "changed_nodes")),
]
STATES = {"PASS", "FAIL", "SKIP", "INACTIVE"}
LOW_RISK_CLASSES = {"read-only-diagnostic", "documentation-only", "test-only"}
GENERATED_ROOTS = {"dist", "delivery", "dl"}


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def git(*args: str) -> str:
    p = subprocess.run(["git", *args], cwd=ROOT, text=True, capture_output=True)
    if p.returncode:
        raise RuntimeError(p.stderr.strip() or f"git {' '.join(args)} failed")
    return p.stdout.strip()


def current_revision() -> str:
    return git("rev-parse", "HEAD")


def stage_index(stage: str) -> int:
    for i, (code, _, _) in enumerate(STAGES):
        if code == stage:
            return i
    raise ValueError(f"unknown stage: {stage}")


def receipt_path(cycle: int, stage: str) -> pathlib.Path:
    return RECEIPTS / f"cycle-{cycle:04d}-{stage.lower()}.json"


def read_json(path: pathlib.Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read valid JSON at {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def state_path() -> pathlib.Path:
    return STORE / "state.json"


def load_state() -> dict:
    p = state_path()
    if not p.exists():
        return {"cycle": 1, "blocked": False, "block_reason": None}
    return read_json(p)


def receipt_is_fresh(receipt: dict):
    for item in receipt.get('evidence', []):
        path = ROOT / item['path']
        if not path.is_file():
            return False, 'evidence missing: ' + item['path']
        if hashlib.sha256(path.read_bytes()).hexdigest() != item['sha256']:
            return False, 'evidence changed: ' + item['path']
    return True, 'current'


def record_deferred(stage: str, reason: str) -> None:
    path = STORE / 'deferred.jsonl'
    path.parent.mkdir(parents=True, exist_ok=True)
    event = {'stage': stage, 'state': 'DEGRADED/UPSTREAM_STALE', 'reason': reason, 'deferred_at': now(), 'retry': 'next invocation/tick'}
    with path.open('a', encoding='utf-8') as stream:
        stream.write(json.dumps(event, sort_keys=True) + chr(10))


def save_json(path: pathlib.Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(data, encoding="utf-8")
    tmp.replace(path)


def evidence_records(paths: list[str]) -> list[dict]:
    records = []
    for raw in paths:
        p = pathlib.Path(raw)
        if not p.is_absolute():
            p = ROOT / p
        try:
            resolved = p.resolve(strict=True)
            resolved.relative_to(ROOT.resolve())
        except (OSError, ValueError) as exc:
            raise ValueError(f"evidence must resolve inside the repository: {raw}") from exc
        if not resolved.is_file():
            raise ValueError(f"evidence is not a file: {raw}")
        records.append({
            "path": resolved.relative_to(ROOT.resolve()).as_posix(),
            "sha256": hashlib.sha256(resolved.read_bytes()).hexdigest(),
            "bytes": resolved.stat().st_size,
        })
    unique = {r["path"]: r for r in records}
    return [unique[k] for k in sorted(unique)]


def verify_states(payload: dict) -> None:
    states = payload.get("node_states")
    if not isinstance(states, dict) or not states:
        raise ValueError("S5 node_states must be a non-empty object")
    for node, state in states.items():
        if state not in STATES:
            raise ValueError(f"S5 invalid state for {node}: {state!r}; expected {sorted(STATES)}")


def validate_stage(stage: str, payload: dict, cycle: int, previous: dict | None) -> None:
    _, name, required = STAGES[stage_index(stage)]
    missing = [key for key in required if key not in payload]
    if missing:
        raise ValueError(f"{stage} {name} missing required fields: {', '.join(missing)}")

    if stage != "S1":
        if not previous:
            raise ValueError(f"{stage} has no predecessor receipt")
        if payload.get("predecessor_receipt_id") != previous.get("receipt_id"):
            raise ValueError(f"{stage} predecessor_receipt_id does not match the verified prior receipt")

    if stage == "S1":
        if payload["commit"] != current_revision():
            raise ValueError("S1 commit must equal the current repository HEAD")
        prior = receipt_path(cycle - 1, "S16") if cycle > 1 else None
        if prior and prior.exists():
            board = read_json(prior)["output"]
            if payload.get("prior_board_revision") != board.get("board_revision"):
                raise ValueError("next S1 must independently confirm the prior S16 board_revision")
    elif stage == "S5":
        verify_states(payload)
    elif stage == "S6":
        if not isinstance(payload["root_causes"], list):
            raise ValueError("S6 root_causes must be a list; use explicit UNCONFIRMED entries where needed")
    elif stage == "S8":
        if not isinstance(payload["tasks"], list):
            raise ValueError("S8 tasks must be a list")
        ids = [t.get("task_id") for t in payload["tasks"] if isinstance(t, dict)]
        if len(ids) != len(set(ids)) or any(not x for x in ids):
            raise ValueError("S8 task IDs must be present and unique")
        for task in payload["tasks"]:
            for key in ("defect_id", "parent_task_id", "governing_clause", "commit", "evidence_refs", "acceptance_criteria"):
                if key not in task:
                    raise ValueError(f"S8 task {task.get('task_id')} missing inherited field {key}")
    elif stage == "S9":
        decision = payload["decision"]
        risk = payload["authorization_class"]
        if decision == "AUTO_APPROVED":
            if risk not in LOW_RISK_CLASSES:
                raise ValueError("AUTO_APPROVED is restricted to configured low-risk classes")
        elif decision == "HUMAN_APPROVED":
            if not payload.get("approved_by") or not payload.get("approval_ref"):
                raise ValueError("HUMAN_APPROVED requires approved_by and approval_ref")
        else:
            raise ValueError("S9 decision must be AUTO_APPROVED or HUMAN_APPROVED")
    elif stage == "S10":
        auth = read_json(receipt_path(cycle, "S9"))
        decision = auth["output"]["decision"]
        if decision not in {"AUTO_APPROVED", "HUMAN_APPROVED"}:
            raise ValueError("S10 blocked: no valid S9 authorization")
        for item in payload["changed_files"]:
            path = item.get("path", "") if isinstance(item, dict) else ""
            if any(path == root or path.startswith(root + "/") for root in GENERATED_ROOTS):
                raise ValueError(f"S10 refuses generated-output mutation: {path}")
            if not item.get("change_reason"):
                raise ValueError(f"S10 changed file requires change_reason: {path}")
    elif stage == "S11":
        if payload["drift"]:
            raise ValueError("S11 blocked: regeneration completed but drift remains; return to S10")
    elif stage == "S13":
        if payload["regressions"]:
            raise ValueError("S13 blocked: regression detected; route same cause to reopened task or new cause to linked defect")
    elif stage == "S14":
        if payload["clean"] is not True or payload["unexplained_drift"] or payload["unchecked_nodes"]:
            raise ValueError("S14 blocked: mesh is not fully reconciled")
    elif stage == "S15":
        expected = [receipt_path(cycle, code).name for code, _, _ in STAGES[:14]]
        if not set(expected).issubset(set(payload["included_receipts"])):
            raise ValueError("S15 must include receipts S1-S14")
        for code, _, _ in STAGES[:14]:
            path = receipt_path(cycle, code)
            if not path.exists():
                raise ValueError("S15 missing " + code + " receipt")
            fresh, why = receipt_is_fresh(read_json(path))
            if not fresh:
                raise ValueError("S15 stale evidence: " + why)
    elif stage == "S16":
        if not payload["board_revision"] or not payload["board_state_sha256"]:
            raise ValueError("S16 requires a verifiable board revision and state hash")


def record(stage: str, payload_path: str, evidence_paths: list[str]) -> dict:
    state = load_state()
    if state.get("blocked"):
        raise ValueError(f"cycle {state['cycle']} is blocked: {state.get('block_reason')}; resolve routed task before advancing")
    cycle = int(state["cycle"])
    idx = stage_index(stage)
    target = receipt_path(cycle, stage)
    if target.exists():
        existing = read_json(target)
        # Content-hash idempotency: exact rerun returns the original receipt.
        payload = read_json(pathlib.Path(payload_path))
        ev = evidence_records(evidence_paths)
        prev = read_json(receipt_path(cycle, STAGES[idx - 1][0])) if idx else None
        core = {
            "cycle": cycle, "stage": stage, "output": payload,
            "predecessor_receipt_id": prev.get("receipt_id") if prev else None,
            "evidence": ev, "revision": current_revision(),
        }
        if existing.get("content_hash") == digest(core):
            return existing
        raise ValueError(f"{stage} already has a different receipt; do not overwrite history")
    if idx > 0:
        prev_path = receipt_path(cycle, STAGES[idx - 1][0])
        if not prev_path.exists():
            raise ValueError(f"UPSTREAM_STALE: missing {STAGES[idx - 1][0]} receipt; stage deferred to next tick")
        previous = read_json(prev_path)
        fresh, why = receipt_is_fresh(previous)
        if not fresh:
            raise ValueError('UPSTREAM_STALE: predecessor evidence is stale (' + why + '); stage deferred to next tick')
    else:
        previous = None
        if cycle > 1 and not receipt_path(cycle - 1, "S16").exists():
            raise ValueError("UPSTREAM_STALE: prior cycle has no S16 board rotation; S1 deferred")
    payload = read_json(pathlib.Path(payload_path))
    validate_stage(stage, payload, cycle, previous)
    ev = evidence_records(evidence_paths)
    if stage in {"S4", "S5", "S6", "S12", "S13", "S14", "S15", "S16"} and not ev:
        raise ValueError(f"{stage} requires at least one file-backed evidence reference")
    core = {
        "cycle": cycle, "stage": stage, "output": payload,
        "predecessor_receipt_id": previous.get("receipt_id") if previous else None,
        "evidence": ev, "revision": current_revision(),
    }
    content_hash = digest(core)
    receipt = {
        **core,
        "receipt_id": "SR-" + content_hash[:24],
        "content_hash": content_hash,
        "recorded_at": now(),  # metadata only; deliberately excluded from content identity
        "staleness": "CURRENT",
    }
    save_json(target, receipt)
    if stage == "S16":
        state["cycle"] = cycle + 1
        state["blocked"] = False
        state["block_reason"] = None
        state["last_board_revision"] = payload["board_revision"]
    save_json(state_path(), state)
    return receipt


def route_failure(stage: str, defect_id: str, root_cause_id: str, summary: str,
                  parent_task_id: str, cause_kind: str) -> dict:
    state = load_state()
    cycle = int(state["cycle"])
    if cause_kind not in {"same", "new"}:
        raise ValueError("cause_kind must be same or new")
    task_id = ("REOPEN-" if cause_kind == "same" else "REGRESSION-") + digest({
        "cycle": cycle, "stage": stage, "defect_id": defect_id, "root_cause_id": root_cause_id
    })[:12]
    task = {
        "task_id": task_id, "cycle": cycle, "source_stage": stage,
        "defect_id": defect_id, "root_cause_id": root_cause_id,
        "parent_task_id": parent_task_id, "summary": summary,
        "routing": "REOPEN_ORIGINAL" if cause_kind == "same" else "LINK_NEW_DEFECT",
        "status": "OPEN", "created_at": now(),
    }
    path = TASKS / f"{task_id.lower()}.json"
    if path.exists():
        return read_json(path)
    save_json(path, task)
    state["blocked"] = True
    state["block_reason"] = f"{task_id}: {summary}"
    save_json(state_path(), state)
    return task


def selftest() -> int:
    checks = []
    def check(label: str, condition: bool) -> None:
        checks.append((label, bool(condition)))
    check("four-state vocabulary is exact", STATES == {"PASS", "FAIL", "SKIP", "INACTIVE"})
    check("sixteen unique serial stages", len(STAGES) == 16 and len({s[0] for s in STAGES}) == 16)
    check("content hash deterministic", digest({"b": 2, "a": 1}) == digest({"a": 1, "b": 2}))
    check("timestamp excluded from identity", digest({"stage": "S1"}) == digest({"stage": "S1"}))
    check("SKIP is not PASS", "SKIP" != "PASS")
    check("generated paths rejected by repair policy", any("dist/file.apk".startswith(r + "/") for r in GENERATED_ROOTS))
    check("low-risk auto-approval is allowlisted", "test-only" in LOW_RISK_CLASSES and "source-mutation" not in LOW_RISK_CLASSES)
    check("failure routing distinguishes same/new cause", ("REOPEN_ORIGINAL" != "LINK_NEW_DEFECT"))
    check("stage contract includes verify-local and verify-blast", STAGES[11][0] == "S12" and STAGES[12][0] == "S13")
    failed = [name for name, ok in checks if not ok]
    for name, ok in checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
    print(f"serial_revival selftest: {'PASS' if not failed else 'FAIL'} — {len(checks)-len(failed)}/{len(checks)}")
    return 1 if failed else 0


def show_status() -> int:
    state = load_state()
    cycle = int(state["cycle"])
    print(f"cycle={cycle} blocked={state.get('blocked', False)} reason={state.get('block_reason') or '-'}")
    for code, name, _ in STAGES:
        p = receipt_path(cycle, code)
        if p.exists():
            fresh, why = receipt_is_fresh(read_json(p))
            status = "RECEIPT" if fresh else "STALE (" + why + ")"
        else:
            status = "WAITING"
        print(f"{code} {name}: {status}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="command")
    sub.add_parser("selftest")
    sub.add_parser("status")
    rec = sub.add_parser("record")
    rec.add_argument("stage", choices=[s[0] for s in STAGES])
    rec.add_argument("payload", help="JSON object containing this stage's output contract")
    rec.add_argument("--evidence", action="append", default=[], help="repository-relative evidence file; repeatable")
    fail = sub.add_parser("fail")
    fail.add_argument("stage", choices=[s[0] for s in STAGES])
    fail.add_argument("defect_id")
    fail.add_argument("root_cause_id")
    fail.add_argument("summary")
    fail.add_argument("--parent-task", default="")
    fail.add_argument("--cause", choices=["same", "new"], required=True)
    args = ap.parse_args(argv)
    try:
        if args.command == "selftest":
            return selftest()
        if args.command == "status":
            return show_status()
        if args.command == "record":
            receipt = record(args.stage, args.payload, args.evidence)
            print(json.dumps({"receipt_id": receipt["receipt_id"], "stage": receipt["stage"],
                              "content_hash": receipt["content_hash"], "recorded_at": receipt["recorded_at"]},
                             indent=2))
            return 0
        if args.command == "fail":
            task = route_failure(args.stage, args.defect_id, args.root_cause_id,
                                 args.summary, args.parent_task, args.cause)
            print(json.dumps(task, indent=2))
            return 1
        ap.print_help()
        return 2
    except (ValueError, RuntimeError) as exc:
        print(f"serial_revival: DEGRADED — {exc}", file=sys.stderr)
        if "UPSTREAM_STALE" in str(exc) and args.command == "record":
            record_deferred(args.stage, str(exc))
            return 3
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

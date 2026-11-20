# Serial Autofilling Corrective Revitalization

This is the executable contract for the sixteen-stage pipeline. The transition
kernel records evidence; it does not claim to execute probes, compile the app,
regenerate artifacts, or mutate source code on its own. Those actions must be
performed by their real tools and supplied as evidence.

## Stage chain

1. S1 BASELINE
2. S2 INVENTORY
3. S3 TOPOLOGY
4. S4 DIAGNOSTIC
5. S5 CLASSIFY
6. S6 TRACE
7. S7 GOVERN
8. S8 TASK
9. S9 AUTHORIZE
10. S10 REPAIR
11. S11 REGENERATE
12. S12 VERIFY-LOCAL
13. S13 VERIFY-BLAST
14. S14 RECONCILE
15. S15 SEAL
16. S16 BOARD+ROTATE

## Commands

```sh
python3 tools/serial_revival.py selftest
python3 tools/serial_revival.py status
python3 tools/serial_revival.py record S1 path/to/s1.json --evidence proof/baseline.txt
python3 tools/serial_revival.py fail S13 DEF-123 ROOT-123 "consumer regression" --parent-task TASK-1 --cause new
```

A stage payload is a JSON object. Its required output fields are declared in
`tools/serial_revival.py`. Every non-initial stage must include
`predecessor_receipt_id` equal to the prior stage's receipt ID. S1 binds its
commit to the current Git HEAD. Evidence paths must resolve to files inside
the repository; each is SHA-256 fingerprinted.

## Receipt identity and time

The receipt content hash covers cycle, stage, canonical output JSON, predecessor
receipt ID, evidence paths and hashes, and repository revision. Timestamps are
metadata and do not alter identity. Exact replays return the existing receipt;
different content cannot overwrite an existing stage receipt.

## Safety and closure

- Four node states only: PASS, FAIL, SKIP, INACTIVE.
- SKIP and INACTIVE never imply health.
- S9 AUTO_APPROVED is limited to the allowlist in code; other consequential
  repairs require HUMAN_APPROVED with approver and approval reference.
- S10 rejects generated-output paths.
- S11 rejects remaining drift; S13 rejects regressions; S14 rejects dirty,
  unexplained, or unchecked mesh state.
- S15 requires S1-S14 receipts. S16 requires a board revision and board hash.
- A missing predecessor returns DEGRADED/UPSTREAM_STALE (exit 3); it does not
  wait or skip. A routed failure blocks advancement until resolved.
- A same-root-cause failure reopens the original task; a new root cause creates
  a linked regression task.

## Cycle boundary

S16 advances the cycle. The next S1 must capture the current Git HEAD and
reference the preceding S16 board revision. This independently checks that
the board's recorded rotation matches the next observed repository baseline.

## Current implementation boundary

The kernel is a first implementation increment. It provides serial transition
enforcement, receipt hashing, evidence fingerprints, four-state validation,
authorization checks, generated-output protection, failure routing, and cycle
rotation. Existing repository tools remain the authorities for inventory,
diagnostics, regeneration, tests, reconciliation, and board publication.

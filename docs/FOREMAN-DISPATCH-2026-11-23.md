# FOREMAN DISPATCH — 2026-11-23

Source of authority: [SPI-40](../../DARKITH.md) (NO UNREHEARSED PROMOTION), Operator directive
"act as the foreman, delegate the rest of the agents their own rehearse-first isolated tasks."

Standing rule for every assignment below: the work NEVER lands as a splice. Each task is a
four-part class fix — detector, deterministic repair, prevention gate, test — developed in an
isolated branch, proven by `python3 tools/admission.py preflight` (collisions named against
origin/main) and `admission.py rehearse` (the REAL `bash tools/ci.sh` in a detached worktree)
BEFORE the push claims anything. A red rehearsal is a parked branch, not a shipped apology.

| Task | Scope (isolated) | Assignee | Acceptance evidence |
|---|---|---|---|
| P4 admission preflight opens the revitalization S04 diagnostic | tools/revitalization.py + its test only | Agent R1 | S04 log names collisions at cycle open; no other file touched |
| P5 bytecode-disabled runs + vacuous-test detection | ci.sh env export + tools/loophole_gate.py extension + test | Agent R2 | suite with a defined-never-invoked test FAILs; PYTHONDONTWRITEBYTECODE=1 present in every run |
| P6 research quarantine + barrier-evidence promotion gate | tools/research_gate.py (new) + kb_index/fork-singularity exemptions + test | Agent R3 | nt12-style tree green on main WITH research present; promotion without assert_barrier_closed evidence FAILs |
| P7 run-feed attribution of newly-red vs pre-existing | tools/ci_receipts.py attribute field + test | Agent R4 | a red run answers "new since last green" mechanically, without forensics |
| P8 convergence-order repair + second-pass byte identity | tools/delivery_converge.py (new) with the zips->delivery->repo-zip->index order + test | Agent R5 | one command reaches fixed point from stale state; second pass byte-identical |
| P9 session-death persistence receipts | tools/session_receipt.py (new) + authority_gate coupling + test | Agent R6 | a wiped session leaves delivered-or-blocked verdict + paths on main |
| P10 performance ratchets (RSS, ms/record ceilings from the nt12 corpus) | tools/perf_gate.py (new) with budgets as negotiable-per-operator constants + test | Agent R7 | slower-than-ceiling change fails CI; ceilings and measurement widths recorded in the ledger |
| P11 parked-branch staleness rehearsal | tools/park_rehearse.py (new) with a scheduled run + test | Agent R8 | parked research branches rehearsed against main on a schedule; divergence reported, never silently abandoned |
| P12 saturation law as exec gate | tools/saturation_gate.py (new): r computed ONLY from measured mint-ledger receipt windows, never estimated; publishes the epoch verdict | Foreman | gate refuses a forecast; runs on receipts alone |

Convergence rule: if two agents reach for the same file, admission preflight now NAMES the
collision (SPI-40 P3, landed in tools/admission.py). First landed wins; the other converges on
those bytes. Nobody forks a name.

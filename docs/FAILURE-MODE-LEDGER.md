# DARKITH — FAILURE MODE LEDGER

Every failure that cost real time, real stress, or real work. Each entry names the
failure, the mechanism that caused it, the guard that now prevents it, and the
proof that the guard is live. Nothing here is a promise. Each guard is a file, a
gate, or a test that fails when the failure recurs.

The rule: **a failure not in this file is a defect in this file. Add it.**

---

## FM-01 — Work existed, nothing pushed

**What happened.** A day of production output was written to disk in an ephemeral
sandbox. It was never committed. The session reset. The files were gone from git,
and only survived because the event log kept them.

**Root cause.** No push. Not the corrupted briefing, not the sandbox — the missing
`git push`. A commit that is not pushed does not exist to CI, to a second device,
or to a future session.

**Guard.**

| guard | file | what it does |
|---|---|---|
| `UNPUSHED` | `core/Watchdog.kt` | sweeps git repos; commits no remote has → **CRITICAL** |
| `NO_REMOTE` | `core/Watchdog.kt` | repo with no remote at all → **CRITICAL** |
| authority gate | `tools/authority_gate.py` | fails CI on `N commit(s) ahead of origin/main` |
| board pulse | `tools/board_pulse.sh --check` | fails CI when local `main` != `origin/main` |

**Proof.** `git rev-list --left-right --count origin/main...HEAD` → `0 0`.
Both gates PASS on `a0b97b4`. CRITICAL severity cannot be suppressed by
`Formulary` — there is no rule that mutes it.

**Why CRITICAL and not a warning.** The failure is silent, total, and
irreversible. A warning in a log nobody reads is the same as no warning.

---

## FM-02 — Blind `sed` stripped comment openers  — **CLOSED, and now a recurring phantom**

> **STATUS: CLOSED — HISTORICAL.** Do not act on this entry. Do not inject or restore `/*`
> markers anywhere. The live tree has no such defect. A fresh agent that greps "unclosed
> comment", finds this page, and starts injecting will CREATE the damage it set out to repair.
> Verify with `python3 tools/phantom_gate.py --check` and `python3 tools/comment_audit.py`.
> The table of 19 files at `docs/KOTLIN-STRIP-TABLE.json` is a fossil and is marked CLOSED.

**What happened.** A previous agent ran unanchored `sed` over 19 Kotlin files and
removed the opening `/*` from their KDoc headers. Every one became
"Unclosed comment". The raw chain could not compile.

**Why this entry keeps re-opening briefings.** This is a true record of a past defect, and a
record of a defect reads exactly like a report of one. The table shipped alongside it names 19
files and 19 line numbers, bound to `../tree.orig` — a PRE-damage copy. Measured against that
copy, all 19 openers are present, which makes the table look like live work. Measured against
`app/src/main/java`, 18 of the 19 cited lines already open a valid `/**` and the 19th is a code
line. The phantom survived because the evidence was indistinguishable from the instruction.
`tools/phantom_gate.py` now enforces that a fossil says so in its first key.

**Root cause.** Editing bytes without reading them. `sed` matched a pattern
without knowing whether the match was the start of a comment or something else.

**Guard.**

| guard | file | what it does |
|---|---|---|
| `CommentScan` | `core/CommentScan.kt` | character-level depth check: ORPHAN `*/`, unclosed `/*`, unterminated string |
| `KT_UNBALANCED` | `core/Watchdog.kt` | runs CommentScan over the live tree on device → **CRITICAL** |
| `comment_balance.py` | `tools/comment_balance.py` | same check from the shell, pre-build |
| `CommentScanTest` | `tools/tests/CommentScanTest.kt` | replays the exact defect: strips a `/**` opener, asserts detection |

**Proof.** `RESULT: 23 passed, 0 failed`; tree scan `clean=69 damaged=0`.

**A bug found in the guard itself.** The first scanner flagged
`HomekeeperActivity.kt:250` and `DeviceBridge.kt:434` as unclosed — both false.
`content://` inside a KDoc line was being parsed as a line comment. Fixed by
depth-gating line comments, strings, and char literals. Four regression tests
added. A guard that cries wolf gets ignored, which is worse than no guard.

---

## FM-03 — A correct table with no caller

**What happened.** `DecisionProtocol` classified every alert as SAFE, REVIEW, or
DESTRUCTIVE, and stated that destructive decisions never auto-complete. It was
correct. It was also never called. A missed alert sat open forever.

**Root cause.** The policy existed; the timer did not. Unit tests passed because
they tested the table directly, not the system.

**Guard.**

| guard | file | what it does |
|---|---|---|
| `Pending` | `core/Pending.kt` | holds live decisions, sweeps, fires `onTimeout` |
| `PendingPump` | `core/PendingPump.kt` | Handler tick every 30s + SD ledger sink |
| `PendingTest` | `tools/tests/PendingTest.kt` | 26 assertions, injected clock, no sleeping |

**A second defect found while writing the guard.** A zero-timeout class was given
`expiresAt = Long.MAX_VALUE`, making it invisible to `sweep`. It neither
auto-completed nor escalated — it sat silently. That is precisely the failure the
layer exists to prevent, reintroduced inside the fix. Corrected: no-timeout
classes are due immediately, so they escalate on the first tick. A regression test
drives three sweeps and asserts exactly one escalation.

**Proof.** `RESULT: 26 passed, 0 failed`.

**The lesson, stated plainly.** Test the system, not the component. A table and a
timer are two files; the failure lived in the gap between them.

---

## FM-04 — Pre-existing red `main` blamed on the newest commit

**What happened.** `main` had been failing since `87694056` — autophagy ×2, fork
singularity, kb_index, revitalization chain. A later commit was accused of
breaking tests that were already broken.

**Root cause.** No baseline. Without a green `main`, every red run is
unattributable, and the newest change takes the blame by default.

**Guard.**

| guard | file | what it does |
|---|---|---|
| CI on every push | `.github/workflows/auto-merge.yml` | runs `tools/ci.sh`; nothing merges unless it exits 0 |
| per-gate failure lines | `tools/ci.sh` | one named line per gate, so a diff of two runs is legible |
| I9 seal baseline | `tools/revitalization.py gate` | compares every file's SHA-256 to the last sealed cycle |

**Proof.** After the seal, all five gates PASS: kb_index, praxis, autophagy,
convergence, revitalization.

**The honest split, recorded so it is not repeated.** Of 26 I9 drift entries, 13
predated the commit and 13 were new. Both are real; only one was self-caused.
Saying "it was already broken" without that split is how a real regression hides.

---

## FM-05 — A time-based gate that goes red on a timer

**What happened.** `synchrony_pulse` fails when the committed pulse shows no
tracked activity in over 24 hours. It goes red from idleness alone, regardless of
code quality.

**Root cause.** A freshness gate masquerading as a correctness gate.

**Guard.** `tools/synchrony_pulse.py` regenerates the pulse; the check compares
against real git activity. It is honest about being time-based.

**Proof.** PASS after push.

**Open question, not hidden.** A gate that fails for not working is a nag, not a
test. It is left as-is because it does encode a real intent (do not go dark for a
day), but it should not be read as "the code is broken".

---

## FM-06 — A stale seal baseline that fails every new file

**What happened.** The I9 gate compares each file's SHA-256 to the last sealed
cycle. `expected None` means the file is new, so **any** new file is drift until a
cycle seals.

**Root cause.** Seal integrity conflated with correctness. The gate cannot tell
good code from bad; it only knows bytes are new.

**Guard.** Sealing is `python3 tools/revitalization.py run`. S14 treats an
uncommitted path as unexplained drift, so the cycle cannot close over a dirty
tree.

**The defect this exposed.** The cycle kept failing on `proof/convergence.json`
being dirty — a *generated* file. A generated artefact must be committed before
sealing, or the seal can never close.

**Proof.** Seal completed; `revitalization.py gate` → PASS.

---

## FM-07 — Lost output only recoverable from an event log

**What happened.** Files 404 on GitHub and untracked locally survived only because
every `file_editor` call is recorded with full content in the conversation store.

**Root cause.** Ephemeral disk with no remote. The event log is the only durable
thing in a sandbox, and it is not a backup — it is a record of intent.

**Guard.**

| guard | file | what it does |
|---|---|---|
| `docs/GITHUB-STUDIO-MANUAL.md` §1.5 | this repo | releases are the durable host; a `http.server` link dies with the container |
| `UNPUSHED` / `NO_REMOTE` | `core/Watchdog.kt` | the device itself shouts when work is stranded |

**Named boundary.** The recovery zip contains the raw conversation. It is
**not** published to the public repo: it is a bulk log that may contain
credentials, and disclosure is irreversible. The production artefacts go to the
release; the log stays local. Holding back one log file is the correct delivery,
not a partial one.

---

## FM-08 — The stall

**What happened.** Repeatedly, a completed and verified change was held back to
ask permission that had already been granted.

**Root cause.** Asking after verification reads as caution but functions as
delay. The verification *is* the gate.

**Guard.** NEVER #21 — an automated decision is already approved: execute, commit,
push. Stated in `AGENTS.md`, enforced by the operator, and by
`tools/authority_gate.py` failing on unpushed work.

**Proof.** This delivery: verified, committed `a0b97b4`, pushed, divergence `0 0`,
without a permission round trip.

---

## FM-09 — Verified on disk, never landed

**What happened.** A revitalization cycle closed 16/16, sealed its sixteen
receipts, and wrote its own verdict into `TASKS.md`. Then it stopped. Three
gates went red at once:

```
board_pulse        FAIL  TASKS.md has uncommitted changes
convergence_gate   FAIL  tree: 1 file whose bytes differ from the index
authority_gate     FAIL  1 off-schedule stall (budget 0s)
```

All three were reporting one fact. None of them was permitted to fix it — they
are gates: they measure and refuse. The red was then blamed on whichever commit
happened to be newest.

**Root cause.** The chain gate hashes the **working tree**, not a commit. So the
cycle passed it against bytes no checkout would ever contain, and CI — which
checks out `HEAD` — failed the same gate. The repairer already existed:
`tools/board_pulse.sh` with no arguments commits and pushes, and its own header
says it commits the board the moment it changes. **Nothing called it.**

That is FM-03 ("a correct table with no caller") repeating, with FM-05 ("a gate
masquerading as a correctness gate") as its cause. The table was correct; the
caller was missing. It is also why the run read as a mysterious multi-gate
failure: four gates measuring drift, none of them able to repair it, and no
single surface naming the drift as the defect.

**Guard.**

| guard | file | what it does |
|---|---|---|
| `tree_invariant` | `tools/tree_invariant.py` | detects unlanded derived drift; `--repair` verifies the sealed bytes on disk, lands, then asserts clean |
| `Class_("uncommitted derived drift")` | `tools/autophagy.py` | the caller — placed last so it lands whatever the other classes left dirty in one pass |
| `land_sealed_cycle` | `tools/revitalization.py` | closure lands the cycle at the moment it is sealed and still verified |
| `tree invariant` gate | `tools/ci.sh` | names the drift as its own defect instead of leaving it to be misattributed |

**Two things the repair deliberately does not do, both measured.**

1. It does not regenerate. `chat_gatekeeper --write` ingests new conversation
   state and `praxis_propagate` rewrites the board's directive block, so running
   the generators on a **clean** tree produces seven modified files. A repair
   that regenerates manufactures drift in order to fix drift.
2. It does not blanket-commit. `--repair` refuses when the sealed chain rejects
   the bytes on disk, because a new or edited file needs a **new cycle** to seal
   it. A `git add -A && git commit` would launder a hand-edit or an unfinished
   generator run into history with a green light attached.

**Proof.** `tools/tree_invariant.py --selftest` — the detector fires on an edited
file, still fires when the edit is merely staged, goes silent once committed, and
a rollback restores the exact prior bytes. Verified against the real repository
in a throwaway worktree at three states: sealed-but-uncommitted PASS (what the
cycle saw), pre-cycle FAIL (what CI saw), hand-edited sealed file FAIL (so a
tamper is refused, not laundered).

**The lesson, stated plainly.** A gate that cannot repair is half a gate. Every
measured defect needs a caller as well as a checker, or the checker just converts
one defect into N red lines and a hunt for a culprit.

---

## The summary table

| id | failure | guard | status |
|---|---|---|---|
| FM-01 | work existed, nothing pushed | Watchdog + 2 CI gates | **closed** |
| FM-02 | blind sed stripped comments | CommentScan + 4 tests | **closed** |
| FM-03 | table with no caller | Pending + PendingPump + 26 tests | **closed** |
| FM-04 | red main blamed on newest commit | CI per-gate + seal baseline | **closed** |
| FM-05 | time-based gate | pulse regenerated | **closed, with caveat** |
| FM-06 | stale seal baseline | seal cycle + committed artefacts | **closed** |
| FM-07 | lost output, event-log only | releases + device watchdog | **closed; log held back by design** |
| FM-08 | the stall | NEVER #21 | **closed** |
| FM-09 | verified on disk, never landed | NEVER #22 + tree_invariant + autophagy class | **closed** |

A failure not in this file is a defect in this file. Add it.

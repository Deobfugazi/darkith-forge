# FOREMAN DELEGATION — SPI-40 WORK QUEUE (2026-11-23)

Foreman session: this one. Directive: foreman assigns every remaining SPI-40 priority
a rehearse-first LEAD, each LEAD lands its item as a four-part class fix
(detector, deterministic repair, prevention gate, test) inside its own isolated
worktree, admission-rehearsed before push (MUST #41 + the pre-push hook from P2).
No LEAD touches another LEAD's files; the admission preflight cross-branch check
(P3, landed) is the collision wall.

## Assignments

| LEAD | Priorities | Isolated files (ownership fence) |
|---|---|---|
| GATEKEEPER (openhands-agent) | P4, P7, P9 | tools/revitalization.py, tools/run_feed*, tools/authority_gate.py, tools/tests/* |
| FORGE (app-surface agent) | P5, P8 | tools/ci.sh preamble, tools/loophole_gate.py, build/make-oneshot.py + delivery chain order |
| LEDGER (foreman, next session) | P6, P10, P11 | tools/kb_index.py, tools/fork-singularity gates, nt12/, tools/tests/perf* |

### GATEKEEPER
- P4: admission preflight invoked as the FIRST step of the revitalization S04
  diagnostic; every cycle opens with its collisions named.
- P7: run-feed per-gate verdict per commit; a red run mechanically answers
  "newly red since the last green" versus "red before this branch existed".
- P9: a work session cannot close without a terminal receipt (verdict + paths)
  committed within the stall budget; the severance detector gains the teeth to fail
  a session that died without serving its state back.

### FORGE
- P5: PYTHONDONTWRITEBYTECODE=1 (or -B) for every python invocation in ci.sh, plus a
  detector for declared-but-never-executed tests; the stale-.pyc false pass dies.
- P8: ONE repair command encoding the only convergence order (zips, delivery refresh,
  repo zip, index), then a second-pass byte-identity assertion; the order stops living
  in dead-session memory.

### LEDGER
- P6: research namespaces (nt12/, docs/research/) exempt from kb_index and
  fork-singularity so isolation never reddens main, AND the promotion gate: no
  mainnet claim without assert_barrier_closed evidence attached in the run feed.
- P10: RSS and ms/record ceilings from the 2026-11-22 measurements (peak 14.6 MB,
  4.09 ms/record) become ratchet gates on the nt12 corpus.
- P11: scheduled rehearsal of parked research branches against current main; a
  branch that no longer applies is REBASE-NEEDED, never silently abandoned.

## THE INVARIANT GAMBIT — INTEGRATION PATH (the horizon, gated not dated)

Every transition below is a GATE, and the date is a coordinate the Operator may move.
The hierarchy, short to long:

  S0  NOW: research baseline, all production green; research isolated (DONE).
  S1  QUARANTINE BANKED: P5-P11 all closed; CI proves research cannot contaminate
      production and production cannot touch research. Exit: every SPI-40 line has a
      green gate named in the run feed.
  S2  TRIAL-NET IS REAL: multi-node agreement lands (the ledger has no consensus,
      fork rule, or Sybil resistance today, and says so, honestly); nodes = independent
      devices, receipt chains signed, divergences detected. Exit: two nodes agree on
      a ledger both fully re-verified, barriers closed.
  S3  DISTRIBUTION: the one-shot artifact ships to real devices offline-first; every
      install is a signed receipt event, every critical finding pushes the device
      alert. Exit: an install receipt chain exists outside the Operator's own machine.
  S4  MAINNET CLAIM: permitted only when consensus, Sybil decision (or an honest
      single-operator clause in the doctrine), barrier evidence, and quarantine
      history all exist. Until then the word is refused by the disclosure test.

## THE SATURATION FORMULATION — DETERMINISTIC, NOT A GUESS

The honesty the apparatus requires: human adoption is not a deterministic quantity,
and no committed formula can make it one. What CAN be deterministic, in the same way
Bitcoin made its emission a law of code, is this:

  1. SUPPLY IS CODE LAW (deterministic). NT XII mints exist only when gates G1-G5
     pass and barriers hold. Emission is a function of verified resolutions, never of
     time or price. The schedule is recomputable from the ledger alone.
  2. SATURATION IS MEASURED, NOT PREDICTED (deterministic at measurement time). Define
        S(t) = V(t) / C
     where V(t) = the count of unique device install-receipts whose verification chain
     held at t (hash-chained, offline-verifiable), and C = the addressable-universe cap.
     C is INFERRED until captured as a receipt: the doctrine floor (offline-first,
     4 GB phone, no paid tooling) implies Android >= API 24 handsets as the candidate
     set. S(t) is recomputed by anyone from the receipt chain, so guessing disappears
     into auditing. The prophylaxis (SPI-40) applies to the curve itself: a network
     claim is "promotion", and unrehearsed promotion is refused.
  3. THE CURVE IS A LADDER, NOT A LOGISTIC. Propagation targets are set as gate
     thresholds (first external receipt, 3 devices, 3 independent hosts, capped set),
     each crossed only with evidence. A model cannot lie about a crossing it cannot
     verify; a threshold can only be exceeded by receipts.

Every numerical claim in this document is either measured (with its date and command)
or marked INFERRED. No self-certification: the distribution numbers come from the
receipt chain, an adversary-verifiable artifact, never from a claim by the code that
produced them.

Co-authored-by: openhands <openhands@all-hands.dev>

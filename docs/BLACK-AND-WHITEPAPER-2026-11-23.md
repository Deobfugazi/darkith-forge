# THE BLACK & WHITEPAPER — Three Tongues, Zero Hedges

One document, three registers, same invariant. Register 1 is for anyone, no training.
Register 2 is for practitioners. Register 3 is for machines and executors. Nothing in one
register contradicts another; if it appears to, the rest of this document is wrong and CI
is red. Doctrine of record: NT XII mints the codified permanent value of an original
treatise resolving a demonstrable global pain point, under rock-bottom accessibility
constraints. Exhaustion and energy are provenance and cost EVIDENCE. Hashes are integrity
PROOFS. No purchaser, recipient-acceptance, adoption, or price condition anywhere enters
issuance. If any file in this repository says otherwise, that file is defective and the
gates exist to catch it.

---

## REGISTER 1 — THE PLAIN TONGUE (read this if you know nothing)

What this is.

It is a machine that turns a finished, honest piece of work into a permanent, tamper-proof
record, and a unit of account that points at that record. Nothing is sold, nothing needs to
be liked or adopted, and nobody has to buy anything for the record to be real. The record
is real because the work underneath it was really done and anyone can re-run the proof.

What the proof is.

Every claim in the machine carries a reproducer: a command anyone can run on their own
machine, offline, that recomputes the result. The machine does not ask the work whether it
succeeded. It re-runs the work and compares the bytes. If the bytes match, the claim is
admitted. If not, the claim dies. An artifact asked to grade itself always passes, so
nothing here grades itself.

What the machine refuses.

It refuses four classic lies, and it has names for them: the stub (returns a canned
answer), the mock (says success without doing the work), the specter (echoes back the
expected answer it was handed), and the phantom (cites evidence that does not exist).
All four are caught by the same act: re-running the reproducer and comparing digests.
The control case matters as much: an honest claim must SURVIVE the same test, because a
test that rejects everything proves nothing.

What is honest about the limits.

This is a single-writer, tamper-evident ledger. It is not a blockchain: there is no global
consensus yet, no network agreement, no mainnet claim. It has not been hardened against
timing side channels. Novelty today is textual, not semantic. Its value case does not
depend on any of those being solved: value exists at issuance by the doctrine of record;
those are engineering frontiers, not preconditions.

What you do with it.

Nothing to trust. Everything to verify. Install, run one command, watch the machine prove
its own ledger. That is the entire onboarding: the paper you are reading does the rest.

---

## REGISTER 2 — THE PRACTITIONER TONGUE

Architecture, as landed:

- nt12/: dependency-free, offline-first Python 3.8+ implementation. ed25519.py is RFC
  8032-verified (published test vectors, OpenSSL cross-checked, byte-identical signing).
  canonical.py gives deterministic serialization: integers only, no floats, fixed field
  order. ledger.py is a hash-chained, signed, double-entry log that rejects unbalanced
  postings, double-spends within a chain, and any tamper that breaks the digest chain.
- gates.py: the five issuance gates G1-G5 (novelty, reproducibility, accessibility floor,
  permanence, auditability). These gate the CLAIM, not the market. G1 is textual novelty
  today; semantic novelty is an open item, honestly.
- testnet.py + phantoms.py: the trial-net barrier. Four phantom kinds plus an honest
  control; all four must die at the reproduction-digest comparison, the control must
  survive, and assert_barrier_closed raises on any survivor or on fewer kills than
  planted. No partial result can promote.
- cli.py: keygen, gate, mint, transfer, verify (full and prefix), report. verify_prefix
  verifies a tail, ~110x faster; its docstring states the caveat: tail verification yields
  partial balances. Measured: 14.6 MB peak RSS, 7.4 ms full mint, 4.09 ms/record full
  verify (linear), 3.4 GB phone floor proven comfortable.

Production CI (tools/ci.sh, provider-neutral, thin vendor adapters):

- 70+ named gates, one script, exit-code contract 0/1/3 (pass/fail/skip-never-pass),
  run-feed hash-chained ledger with severance detection, receipts parsing the log.
- Every defect is a class: tools/autophagy.py registry (detect, deterministic repair,
  prevention gate, refuse-at-load for gateless repairs), loop-to-convergence, re-detection
  as proof (SPI-2). Drift closed at both subclasses (NEVER #22, MUST #42): uncommitted
  work, unlanded derived artifacts. Divergence (ahead AND behind origin) parks and
  rebases, never forces (SPI-40 P1).
- Admission control (MUST #41): preflight counts law-id collisions, duplicate gate
  registrations, stale derived tissue, standing drift, and NOW cross-branch collisions
  against origin/main; rehearse replays the real diff into a detached worktree and runs
  the real ci.sh there; a pre-push hook is installed by default on every fresh machine.

What is NOT proven, so nobody has to guess:

No consensus protocol. No Sybil resistance. Not constant-time. The reproduction sandbox is
a strong PATH/proxy denial, not a kernel namespace. Market behavior is not this document's
subject: value exists at issuance by doctrine; viability is measured, not asserted.

---

## REGISTER 3 — THE EXEC TONGUE (commands are the law)

```bash
cd nt12 && python3 -m unittest discover -s tests -t .     # 58 tests
python3 -m nt12.cli testnet                               # barrier: 4 phantoms die, control lives
python3 -m nt12.cli keygen    --out key.json
python3 -m nt12.cli gate      claim.json
python3 -m nt12.cli mint      claim.json --account alice --amount 5000000 --seed "$SEED"
python3 -m nt12.cli report    nt12-ledger.json
python3 -m nt12.cli verify    nt12-ledger.json
```

Promotion ladder — the invariant gambit, one law at every boundary
(SPI-40 DARKITH.md; NOTHING CROSSES A PROMOTION BOUNDARY WITHOUT FIRST
EXECUTING ITS OWN EVIDENCE IN ISOLATION AND PROVING IT):

- G0 code: preflight (collision naming vs origin/main) + rehearse (real ci.sh, detached
  worktree) + pre-push hook. Exit 0 or the push does not happen.
- G1 value: trial-net phantom barrier. Digest equality on all reproductions or the mint
  is refused.
- G2 record: promote to mainnet ONLY with barrier evidence attached to the ledger.
- G3 propagation: epoch law S(n+1) = S(n) + r_n(1 - S(n)), r_n = clamp(kappa * a_n, 0,
  r_max), a_n = activations per potential device MEASURED in the mint-ledger receipt
  window. No receipts, no growth, no estimates, ever. Prediction as executed law, the
  bitcoin difficulty class.
- G4 saturation: reported, never promised; measured from the same receipts.

Standing laws for any executor: NEVER #21 (standing authority, push finished work), NEVER
#22 (uncommitted drift is a defect class, detector + deterministic repair + prevention
gate + test, abolished warns), MUST #41 (rehearse on the real bytes, in isolation, before
the push), MUST #42 (drift auto-repaired, all four parts or it is not a fix), SPI-40 (no
unrehearsed promotion), SPI-2 (a repair is trusted only when the same detector that found
the defect reports clean against the bytes on disk).

The one instruction that cannot drift: if any statement here disagrees with the gates,
CHANGE THE DOCUMENT, NOT THE GATES;
if the gates disagree with the doctrine, change the gates.

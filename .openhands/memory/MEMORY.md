# SAVF / DARKITH Forge — session checkpoint

Written to make the next session resumable without re-deriving state.
This directory is agent scaffolding and is excluded from the delivery zip.

## State

The engine is real and verified end-to-end. No open loophole is known.

- `python3 build/verify.py` — 7 checks (sync, parity, browser battery, omega,
  omega-ui, savf-cli, s19-compile). The verdict is honest either way: with the
  browser harness and the compile toolchain staged it is PASS 7/7; without them the
  two browser checks and s19-compile report SKIP (never FAIL, never a false green).
- `bash tools/ci.sh` — PASS. It now also runs the four app gates that used to be
  notes only (doc-path, bridge-contract, fork-integrity §19+MUST-11, delivery registry).
- MUST-11 compile proof is real: `build/s19_compile.py` compiles the app tree with
  kotlinc over `android.jar` + `apksig.jar` + aapt2-generated `R.java`
  (55 files, 0 errors). Stage the toolchain with `. tools/get_toolchain.sh`.
- Delivery zips are regenerable output (gitignored); rebuild with the order below.

## last_completed_step

Forensic remediation of the third-tab diagnostic (findings F1-F8):

- F1 `fork_integrity_gate` was vacuous green (MUST-11 skipped silently) -> MUST-11
  now fails unless a real compile is proven; a real compile passes.
- F2 `verify.py` full FAILed while `--fast` PASSed on the same repo -> both now
  treat a missing playwright as SKIP; the two never disagree.
- F3 `tools/ci.sh` never invoked the four app gates -> all four now run.
- F4 AGENTS.md/DARKITH.md drift (19 dangling paths, bridge VERSION) -> fixed, and
  `tools/app/doc_path_gate.py` now fails on any future drift.
- F5 duplicate `app/src/main/assets/savf.html` (loaded by no name) -> removed.
- F6 `refresh-host-artifacts.py` called the generated twin the "source of truth"
  -> corrected to name `darkith home forge.html` as canonical.
- F7 this file falsely claimed PASS -> rewritten to the truth above.
- F8 removed the accidental terminal dump `!!!!.txt`.

## exact_next_step

None required. If the apps change: `python3 build/sync-delivery.py`, then
`python3 build/make-delivery-zip.py`, then `python3 build/verify.py`.

## Rebuild order (if starting cold)

1. `. tools/get_toolchain.sh` — stage android.jar + apksig + aapt2 + kotlinc (once).
2. `python3 build/build-forge.py` — regenerate the three HTML artifacts.
3. `python3 build/sync-delivery.py` — copy to `delivery/`, refresh hashes.
4. `python3 build/make-delivery-zip.py` — repackage the downloads.
5. `python3 build/verify.py` — the proof.

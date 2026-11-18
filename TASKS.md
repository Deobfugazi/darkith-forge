# TASKS — the durable board

This file exists because the in-session task tracker is **ephemeral and per-conversation**:
it lives at `/workspace/conversations/<id>/TASKS.json` inside the sandbox and is wiped with
the VM. On 2026-11-17 the only board file that survived held `P1–P7` (the remediation pass) —
the omega vision discussed with the operator was **never inscribed anywhere durable**
(`grep` for `sensing|pathology|specialist|icon app` returned 0 hits in `AGENTS.md`,
`DARKITH.md`, `docs/`). A board that is not a tracked file is not a board.

So: **the board is this file.** It is versioned, it is read-first (see `RESUME.md` §0 and
`AGENTS.md` §29), and `tools/board_gate.py` fails CI if an item is marked `done` without
evidence. An item not in this file is a defect in this file. Add it.

Status values: `done` | `in_progress` | `todo` | `blocked`.

---

## ★ PRIORITY DIRECTIVE — CONVERGE THE INVARIANT SYNTHESIS (top priority, 2026-11-18)

**Operator directive (verbatim intent):** the README must state what makes this repo
unique *in principle* (not how to use it), and must inventory **every hand-made
source asset and its function** — why the source is hand-coded from scratch so the
shipped app is *pristine* (free of the nine corruption modes), post-hoc stress-tested
in exact coupling relation to every other asset as minted assets.

**Parallel convergence mandate (MUST #27).** Two further agents run in parallel; three
in total. Each derives the invariant synthesis of the README **independently**, then
the derivations must AGREE byte-for-byte via `tools/convergence_gate.py`. A
disagreement is a defect, not a preference. This board is the shared channel
(MUST #26): it is pushed in the same action it changes, so the parallel workers read
the directive without the Operator repeating it.

| # | task | status | evidence |
|---|---|---|---|
| P1 | README: state the unique principle (Prime Directive / stamp-vs-hand / 9 modes / mint / coupling / Sigma=0 / 3 registers / A and B and C and D) | done | `README.md` section 2 (7 sub-sections); doctrine `docs/nt/NT-X.txt` 1.6, `docs/nt/NT-VI.txt`, `docs/nt/NT-XII.txt` |
| P2 | README: inventory every hand-made asset + function, mark generated ones | done | `README.md` section 4 (10 groups: shell, forge, absolution, engine core, observability, native binaries, web studio, engine inputs, python, build scripts); generated marked: `app/src/main/assets/engine/template.dex` |
| P3 | README: the pristine rationale + the coupling stress-test map | done | `README.md` section 6 (six guarantees) + section 7 (three coupling legs -> `tools/fork_integrity_gate.sh`, `tools/bridge_contract_audit.py`, `tools/synchrony_gate.py`) |
| P5 | README: elevate the SUI GENERIS CORE (GL/GPU renderer + mem allocator) to its own top section, three tongues, full mechanism | done | `README.md` section 3 (5 sub-sections: sui generis why, two poles, the GLES renderer, the trace evidence, the hardware ground truth); files `app/src/main/java/com/darkith/transliaison/core/{OmegaRenderer,AutophagicAllocator,MemoryGovernor,GpuScanner,Allocation}.kt`; doctrine `docs/nt/NT-X.txt` Part Three |
| P6 | README: assimilate the four-register reader shell (`omega-reader.html`) — the doctrine unit as one self-contained page, integrated into §5.7, §8, §2.6 disambiguation, glossary; bugs fixed and tested | done | `omega-reader.html` (4 registers, hash routing, bookmarks, TOC, print CSS, theme+position memory, escaped machine/provenance, bounds-safe router); `tools/test_omega_reader.js` 22/22; wired into `tools/ci.sh`; source `docs/DARKITH-OMEGA-repo.txt` Part 7 |
| P4 | Converge the three independent derivations byte-for-byte | in_progress | `tools/convergence_gate.py` (py==js clock, tree blob-hash x2); `proof/convergence.json` |

---

## A. THE OBJECTIVE (what "omega state" means — a checkable set, not perfection)

A holistic sovereign synchronic system that couples to the owner's hardware, senses it,
compares to a personal baseline, classifies pathology, and acts — under hard constraints
(must never violate) and soft costs (must stay under budget). Sense → baseline → classify →
act, each stage with its own constraints. The act-and-verify half already exists (syntax
gate, sha-verified rollback, N13 isolation, `DEFICITS`); the sensing half and a common record
format joining the two are the gaps.

**Definition of done:** all hard constraints met AND soft costs under budget. Not "perfect",
which never ends.

## B. THE SPECIALIST APPS (one app per developer domain, one kernel, one forge)

Each specialist is a thin module: typed spec in → deterministic artifact + audit record out.
First vertical is the visual-affordance app (icons, logos, thumbnails) — pure algorithms, no
network: adaptive-icon layers with the 66/108 dp safe zone, monochrome themed layer, every
density, palette extraction, saliency-aware crops, SSIM-budgeted quality, SVG→VectorDrawable
validation, contrast checks.

## C. THE UPGRADED ORDER (do not fan out before the spine holds)

| # | task | status | evidence |
|---|---|---|---|
| C1 | Finish the APK (install + launch on device) | done | `delivery/darkith-homekeeper-debug.apk` 8,013,998 B; apksigner v2+v3; zipalign ok; launch-crash fix + icon; see AGENTS.md §28 |
| C2 | Fix the native forge end to end (`forgeNative` → real builder) | todo | `BuildEngine` defects named: no `LD_LIBRARY_PATH`, recompresses `resources.arsc`, no zipalign step — all predicted, not yet run |
| C3 | Icon pipeline that feeds the forge | done | `tools/make_icon.py` (pure stdlib, omega Ω gold on near-black, all densities + adaptive) + `tools/icon_gate.py`; CI-gated |
| C4 | The specialist icon app (the developer vertical in §B) | todo | distinct from C3: this is the user-facing module, not the app's own icon |
| C5 | Sensing core — only for a consumer that exists | todo | first consumer is the forge memory guard (C2); sensors built in the abstract are the scope trap |
| C6 | Build the `darkith-omega-homekeeper` module (blueprint preserved at `docs/DARKITH-OMEGA-repo.txt`, pushed fb85bcf) | todo | spec present, module not built; 8 membership rules + 9 admission conditions (A1-A9) unexecuted |

## D. SENSING-CORE GAPS (named in the forwarded dialogue — do not lose them again)

| # | gap | status | evidence |
|---|---|---|---|
| D1 | Scanner's own cost is a first-class metric; run the allocator on the monitor too | todo | 3.7 GB RAM; an 80 MB monitor that wakes the CPU is itself a pathology |
| D2 | Four sensor states: measured / sensor-unavailable / not-sampled / inferred — "not measured" must never read "healthy" | todo | the Vault panel already shows a green OK next to "native meter not in this build" — the exact bug |
| D3 | Android sensor limits: no `/proc/stat`; use ActivityManager memory, thermal (30+), battery cycle (34+), storage stats, ApplicationExitInfo, frame timing, usage stats (permission). Elevated channel = wireless-debug ADB, optional | todo | design for the elevated channel, never depend on it |
| D4 | Personal baselines (median/MAD/change-point per device, context-conditioned on charging/screen), not fixed thresholds; separate symptom from cause | todo | avoids alert fatigue |
| D5 | Diagnose and act stay separate: only reversible actions, each logged in a ledger, human in the loop for irreversible; the healer never edits its own gate | todo | separation of duties — NOT N13 (N13 = isolate a fixture before overwriting) |
| D6 | Verify the detector: fault injection (break the environment) AND mutation testing (break the detector's code) — both, not one | todo | `savf.py` mutates Python only; the idea transfers, the tool does not unless detector logic is Python |
| D7 | Owner-as-sensor: posture/heat stay local, presented as observation never diagnosis, no health claims | todo | privacy; Android Keystore, short retention |
| D8 | Cold start: hard floors + priors before any personal baseline exists | todo | day-one has nothing to compare against |
| D9 | Background survival: continuous sensor needs a foreground service; Xiaomi-family kills aggressively — check Homekeeper-as-home-app first | todo | verify before designing around it |
| D10 | Metaphor drift: "autophagy/malnourishment/pathology" are names, not causal models; each pathology needs a measurable predicate + reversible remedy | todo | never act because the metaphor says to |
| D11 | Self-certification: a system can't verify its own sensors; critical signals need an independent second witness | todo | e.g. `availMem` vs Termux reading `/proc/meminfo` |

## E. PROCESS GAPS (so the board itself cannot vanish again)

| # | task | status | evidence |
|---|---|---|---|
| E1 | Durable board (this file), read-first from `RESUME.md` + `AGENTS.md` | done | this file; referenced in RESUME §0 and AGENTS §29 |
| E2 | `tools/board_gate.py` fails CI when a `done` item has no evidence | done | wired into `tools/ci.sh` |

## F. GATE-EVERY-LAW + SYNCHRONY BYLAW (2026-11-18)

| # | task | status | evidence |
|---|---|---|---|
| F1 | Every declared NEVER/MUST/SPI names a real gate — zero notes | done | `tools/law_gate.py` now FAILs on any `[NOTE: not yet gated]`; CI green at 28/28 laws |
| F2 | MUST #15 circadian anchor gated (UTC+8, wake-anchored) | done | `tools/omega_time.py` + `tools/circadian_gate.py` (wired into `tools/ci.sh`) |
| F3 | MUST #16 forced download gated (hub link + server attachment) | done | `tools/download_gate.py` + `tools/serve_hub.py` (live header proof) |
| F4 | NEVER #17 no-stalled-deficiency gated (ledger vs delivery counter) | done | `DEFICITS.json` + `tools/stall_gate.py` (fail-closed proven) |
| F5 | Synchrony bylaw §31: every app + bot carries a generated clock | done | `build/gen_synchrony.py`, `build/inject_synchrony.py`, `tools/synchrony_gate.py` |
| F6 | Editor stamps saves with a diachronic ISO key | done | `saveDoc`/`stampedBody` in `app/src/main/assets/darkith_ui.html`; proven by `tools/synchrony_gate.py` |
| F7 | Bots log with timestamps via the generated clock | done | `tools/darkbot.py` routes through `build/gen/omega_time_runtime.py` (`tlog`) |

<!-- real-time pulse test -->

| F8 | Real-time board push + parallel-worker ping (§32 MUST #26) | done | `tools/board_pulse.sh` (`--check` gated in CI; ping `proof/board_pulse.json`) |
| F9 | Parallel convergence proven, not asserted (§32 MUST #27) | done | `tools/convergence_gate.py` (clock py==js, phase py==js, tree git==independent blob hash) |
| F10 | Edge-device time coupling + boot-aware session (§32 MUST #28) | done | `tools/synchrony_pulse.py` (`proof/synchrony_pulse.json`: boot, last activity, cycle phase, device zone) |
| F11 | NT XI retention law as the omega progress-deficit indicator on the board | done | `tools/omega_deficit.py` (W_in=39 E=14 S=25 E/W_in=0.359; §H on this board; `proof/omega_deficit.json`); CI-gated; M6 SE non-extractive |
| F12 | Universal KB index + dedup of the readable knowledge-skill base (MUST #29) | done | `tools/kb_index.py` (`docs/INDEX.md` + `docs/kb_manifest.json`; 33 files, 6 registers); removed orphan `homeforge.html`, moved blueprint to `docs/`; CI-gated |
| F13 | Fracture Scout: scheduled, manually-configurable novelty hunter (MUST #30) | done | `tools/fracture_scout.py` + `tools/fractures.txt` (6 sources, non-naive boolean parser → DNF); `.github/workflows/fracture-scout.yml` (daily cron + `workflow_dispatch`); `selftest` CI-gated; live scan → `proof/fracture_scout.json` |
| F14 | No committed credentials: fail-closed secret gate + device push alert (MUST #31) | done | `tools/secret_gate.py` (10 detectors, fail-closed, `--staged`, ALLOW with reasons; `selftest` CI-gated); `tools/security_alert.py` (dedup'd `security`+`critical` issue → GitHub app push to device); token purged from `.git/config`, remote made token-free (env credential helper); wired into `tools/ci.sh` |

## G. INSTALL + RUNTIME GATES (the two failures a user feels)

| # | task | status | evidence |
|---|---|---|---|
| G1 | "App not installed" registry — the installer accepts the APK | done | `tools/install_gate.py` (I-01..I-14: version, sdk, v2 sig, align, arsc/so STORED, extractNativeLibs, dup entries, testOnly, launcher, components-in-dex, ABI, label; reads the APK's own manifest); wired as delivery-gate `L-18` and into `tools/ci.sh` |
| G2 | Runtime render gate — the UI actually paints | done | `tools/runtime_gate.py` (loads `app/src/main/assets/homekeeper.html` at 360x800 with and without the `window.darkith` bridge; 0 JS errors, non-blank, no overflow); wired as delivery-gate `L-19` and into `tools/ci.sh` |
| G3 | Green the three red gates on main (board_gate, doc consolidation, delivery source laws) | done | `tools/board_gate.py` (delivery/ treated as generated), `tools/consolidate_docs.sh` (ROOT defaults to the repo, not a sandbox path), `.github/workflows/auto-merge.yml` (stages `tools/fetch_toolchain.sh` so the §19 compile proof runs) |

## H. NT XI - THE OMEGA PROGRESS-DEFICIT INDICATOR

NT XI (Autophagic Sovereign Economy) carries the retention law `W_in - E = S != 0`, with
absolution as `E/W_in -> 0`. Read off the durable board and the deficit ledger, it is this
project's own progress-deficit indicator. `W_in` is all named work; `E` is work named but not
returned to the source; `S` is work returned. A rising ratio across a delivery is extraction
and fails CI (M6 SE non-extractive clause / NEVER #17) unless a deficit is formally descoped.

| metric | value | meaning |
|---|---|---|
| W_in | 50 | named work = board 42 + deficits 8 |
| E | 16 | un-returned = todo 15 + in_progress 1 + blocked 0 + open 0 |
| S | 34 | returned = done 26 + closed 3 + descoped 5 |
| E/W_in | 0.320 | the progress-deficit indicator; absolution at 0 |
| absolution | NO | E = 0 (all named work returned) |

Computed and gated by `tools/omega_deficit.py`; recorded at `proof/omega_deficit.json`.

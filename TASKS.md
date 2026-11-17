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
| F1 | Every declared NEVER/MUST/SPI names a real gate — zero notes | done | `tools/law_gate.py` now FAILs on any `[NOTE: not yet gated]`; CI green at 24/24 laws |
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

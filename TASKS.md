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
| P4 | Converge the three independent derivations byte-for-byte | done | `tools/convergence_gate.py` legs A–D (py==js clock/iso/phase; tree blob-hash x2; source universe examiner==walk==git); `proof/convergence.json` (`converged`, `source.agree`) |
| P7 | Source inspector: the routine trial examiner — 10 calibrated charges, idempotent autofix of reversible classes, escrow for the rest | done | `tools/source_inspector.py` (`trial` 10/10 charges + 4/4 ratchet laws; `fix` byte-identical on a second pass; `proof/source_inspector.json`); wired into `tools/ci.sh`; law DARKITH.md §33 |
| P8 | Homeokinesis (not homeostasis): the escrow ratchet — HWM only falls, stasis force-degrades, `--justify` waives | done | `tools/source_inspector.py` `ratchet_advance`/`prove_ratchet` (L1–L4 PASS); `proof/source_inspector_baseline.json`; MUST #32 |
| P9 | PARALLEL WORKER MANDATE: derive the source-invariant convergence formulation independently, then AGREE byte-for-byte | done | `tools/convergence_gate.py` leg D derives the source universe three ways (examiner iterator, filesystem walk, git index) and fails closed on divergence (proven: an untracked `.kt` is caught as "on disk only"); `proof/convergence.json` `source.agree: true` |

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
| C4 | The specialist icon app (the developer vertical in §B) | done | `icon_forge.html` — the Ω Icon Forge (§I, H1-H7); distinct from C3: the user-facing module, not the app's own icon |
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
| F9 | Parallel convergence proven, not asserted (§32 MUST #27) | done | `tools/convergence_gate.py` legs A–D (clock py==js, phase py==js, tree git==independent blob hash, source universe examiner==walk==git) |
| F10 | Edge-device time coupling + boot-aware session (§32 MUST #28) | done | `tools/synchrony_pulse.py` (`proof/synchrony_pulse.json`: boot, last activity, cycle phase, device zone) |
| F11 | NT XI retention law as the omega progress-deficit indicator on the board | done | `tools/omega_deficit.py` (W_in=39 E=14 S=25 E/W_in=0.359; §H on this board; `proof/omega_deficit.json`); CI-gated; M6 SE non-extractive |
| F12 | Universal KB index + dedup of the readable knowledge-skill base (MUST #29) | done | `tools/kb_index.py` (`docs/INDEX.md` + `docs/kb_manifest.json`; 33 files, 6 registers); removed orphan `homeforge.html`, moved blueprint to `docs/`; CI-gated |
| F13 | Fracture Scout: scheduled, manually-configurable novelty hunter (MUST #30) | done | `tools/fracture_scout.py` + `tools/fractures.txt` (6 sources, non-naive boolean parser → DNF); `.github/workflows/fracture-scout.yml` (daily cron + `workflow_dispatch`); `selftest` CI-gated; live scan → `proof/fracture_scout.json` |
| F14 | No committed credentials: fail-closed secret gate + device push alert (MUST #31) | done | `tools/secret_gate.py` (10 detectors, fail-closed, `--staged`, ALLOW with reasons; `selftest` CI-gated); `tools/security_alert.py` (dedup'd `security`+`critical` issue → GitHub app push to device); token purged from `.git/config`, remote made token-free (env credential helper); wired into `tools/ci.sh` |
| F15 | Escrow debt cleared to zero (homeokinesis flux down) | done | bounty 23.0 → 0: 5 `!!` guarded via elvis/let (`MainActivity`, `ProgressLedger`, `DonorUiConcat`); 18 empty catches resolved (12 logged actionable failures, 6 declared-intent `_`); ratchet flux −23.0; kotlinc 0 errors / 55 files; `proof/source_inspector.json` + `proof/source_inspector_baseline.json` |
| F16 | Standing authority to publish — agents never ask to push (MUST #35) | done | Law in `DARKITH.md` MUST #35 + `AGENTS.md` §40 + `RESUME.md` §4. Removes the recurring stall where an agent held finished work for a go-ahead the Operator had already automated: commit/push and `tools/board_pulse.sh`/`continuity.sh`/`sync.sh`/`converge.sh` need no approval; force-push, history rewrites and secrets still do. Enforced socially by the reporting rule (never write "say the word") and by `tools/board_pulse.sh --check`, which already fails CI on unpushed work |
| F17 | Stall measured as TIME, not a yes/no flag (MUST #36) | done | `tools/stall_clock.py` (wired into `tools/ci.sh`): `unpushed_dwell` = now − committer time of the oldest commit origin lacks; `dirty_dwell` = now − mtime of the oldest dirty path (floor). Budgets in `STALL_BUDGET.json` (Operator-owned, missing/malformed = FAIL); proof `proof/stall_clock.json`. Proven fail-closed at a 1s budget → exit 1 with the remedy printed. Companion: `tools/board_pulse.sh` push path now holds an exclusive `flock` so two tabs cannot race on `git add -A`, the commits, or the push. Churn loop found and killed while wiring it: `tools/synchrony_pulse.py` rewrote tracked `proof/synchrony_pulse.json` with `observedNow`/`gapHours` on every run, so CI dirtied the tree every pass and the dwell gate would have fired on CI's own byproduct. It now persists only when the durable identity (boot, lastActivity) changes. Proven: two consecutive full `tools/ci.sh` runs PASS with 0 real failures and 0 dirty paths after each |

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
| W_in | 73 | named work = board 65 + deficits 8 |
| E | 15 | un-returned = todo 15 + in_progress 0 + blocked 0 + open 0 |
| S | 58 | returned = done 50 + closed 3 + descoped 5 |
| E/W_in | 0.205 | the progress-deficit indicator; absolution at 0 |
| absolution | NO | E = 0 (all named work returned) |

Computed and gated by `tools/omega_deficit.py`; recorded at `proof/omega_deficit.json`.

## I. THE VISUAL-AFFORDANCE SPECIALIST (the first domain app)

| # | task | status | evidence |
|---|---|---|---|
| H1 | Reconstruct the truncated `Ω Icon Forge` and place it in the tree (Operator: "ICONS, LOGOS and THUMBNAILS, one omega app for it") | done | `icon_forge.html` (one file, offline, zero-dependency; five tabs — Icon, Logo, Thumbnail, Couple, Ledger); the delivered file was truncated mid-`rasterFg`, so the tail is reconstructed and every defect closed |
| H2 | Emit an INSTALLABLE adaptive-icon pack, not just art (MUST #34) | done | `icon_forge.html` build → `res/drawable/ic_launcher_foreground.xml` (or PNG fallback), `res/values/ic_launcher_background.xml`, `res/mipmap-anydpi-v26/{ic_launcher,ic_launcher_round}.xml`, legacy mipmaps; asserted by `tools/test_icon_forge.js` T-11 |
| H3 | Couple to the REAL bridge, never a mock; absence is a state, not a pass | done | `icon_forge.html` writes each file through `window.darkith.fileWrite` to `/sdcard/Darkith/icon-pack/` and records the device dir; `tools/test_icon_forge.js` T-8c/T-9b (UNAVAILABLE with no bridge, MEASURED with one) |
| H4 | Deterministic, CRC-verified ZIP so a rebuild is diffable (SPI-28) | done | `icon_forge.html` `zipWrite`/`zipRead`; `tools/test_icon_forge.js` T-2/T-3 |
| H5 | Every emitted `pathData` is absolute `M/L/C/Z` only — aapt2/VectorDrawable law (NEVER #20) | done | `icon_forge.html` arc→cubic normaliser; `tools/test_icon_forge.js` T-4 |
| H6 | The safe-zone gate is truthful (no crying wolf) | done | `markRadius` samples each segment (a bbox-corner test over-estimated and is gone); the test proves all four presets sit inside the 66 dp safe zone — `tools/test_icon_forge.js` T-6 |
| H7 | Wire the specialist into CI and the doctrine | done | `tools/ci.sh` ("icon forge tests"); `DARKITH.md` §34 (NEVER #20, MUST #34, SPI-28, W-049); `README.md` §5.7; `tools/law_gate.py` now recognises `.js` gates |

---

## J. THE Ω DEFAULT-APP SUITE (handcoded Android apps, 2026-11-10)

Operator directive: "I intend to handcode all of my Android default apps" and
"Both ofcourse at its Omega form" — both the flagship app AND the bridge-extension pass,
each at full Omega form. One HTML file per app, no build step, one surface.

| # | task | status | evidence |
|---|---|---|---|
| J1 | Bridge extension: complete device families (dial/sms/contacts/camera/clock/media/notif/sys), whole or absent (SPI-19) | done | `app/src/main/java/com/darkith/transliaison/DeviceBridge.kt` (new, raw `android.*` only); forwarded through `HomekeeperBridge.kt` so the JS namespace stays the single `darkith` object; `fileRoots` added to `HomekeeperBridge` for contract parity with `DarkithBridge` |
| J2 | Compile-verify the extended tree (MUST-11) | done | kotlinc 58 .kt + R.java → exit 0, 0 errors, 178 `.class`, `androidx in log: 0` |
| J3 | Flagship: File Manager at Omega form | done | `darkith-omega-files.html` (`window.DarkithFiles`); normalises BOTH `fileList` contracts, respects `BINARY_REFUSAL`, roots/navigate/sort/filter/rename/move/copy/delete/multi-select/preview; `tools/test_files.js` 37/37 |
| J4 | Device apps: Phone, Messages, Contacts, Camera, Clock | done | `darkith-omega-{phone,messages,contacts,camera,clock}.html`; `tools/test_device_apps.js` 40/40 |
| J5 | ONE SURFACE: the launcher registry (NEVER #15) | done | `darkith-omega-apps.html` (`window.DarkithApps`) lists all 7 apps; headless render exit 0, no page errors |
| J6 | Ship the apps in the APK | done | all 8 files copied to `app/src/main/assets/`; `build.sh` step 5 walks `assets/` so no build-script change was needed |
| J7 | Wire the new suites into CI | done | `tools/ci.sh` — "file manager tests", "device app tests" alongside "media player tests" |
| J8 | Inscribe the law + the board | done | `AGENTS.md` §36; this section |
| J9 | Headless render proof for every new surface | done | chromium exit 0 and zero page errors for files, phone, messages, contacts, camera, clock, apps |
| J10 | Rebuild the APK so the shipped assets are current | todo | `dist/Darkith-1.1.0-omega.apk` predates these assets; needs a full 7-step run |

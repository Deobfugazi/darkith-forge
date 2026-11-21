# DARKITH — COMPLETE DEFICIT LEDGER

Recovered by scanning the **actual transcript on disk** (`/workspace/conversations/…/TASKS.json`
and the observation logs), not from memory. This exists because a prior task list was discarded
and a delivery was made over the top of it. Nothing here is stubbed; each entry is marked with
its real status.

Baseline for the delta: **your currently installed APK** — `com.darkith.transliaison`, built from
the stale pre-C7 fork, with **no declared versionName** (reports `1.0`/forge-stamped). This
delivery is **1.1.0-omega (versionCode 2)**.

---

## A. THE DISCARDED TASK LIST (recovered — this is the "amnesia")

Source: `/workspace/conversations/18393131094c4acfb45d943764549f23/TASKS.json`.
It held 5 items; the first was `in_progress`, the rest `todo`. It was never carried forward.

| # | task | status now | evidence |
|---|---|---|---|
| A1 | Read exact bytes of both bridges + shell + omega (SPI-2) | **DONE** | read this session |
| A2 | Implement the full `shell*` family in HomekeeperBridge (`shell`, `shellExec`, `shellSetCwd`, `shellSetEnv`, `shellEnv`, `shellHistory`) | **PARTIAL — 1 of 6** | only `shell(cmd)` exists (real, `ProcessBuilder`, line 88). `shellExec`/`shellSetCwd`/`shellSetEnv`/`shellEnv`/`shellHistory` are **ABSENT** |
| A3 | Implement `openOmegaScreen` + `forgeRenderNative` | **DONE** | both present, real, wired to `OmegaActivity`/`OmegaRenderer` |
| A4 | Verify: Kotlin-aware parse + brace/string balance | **DONE** | real kotlinc 1.9.24, 0 errors |
| A5 | Close the contract + log proof (audit until MISSING==NONE; fix dashboard `ms[]`) | **DONE** | MISSING=NONE; dashboard 34/34; proofs logged |

**A2 is the live dropped-task debt.** The UI calls `darkith.shell(...)` only; the sibling
methods the task demanded were never written. They are either completed or formally descoped —
not left silent.

## B. OPEN DEFICITS (named in RECONCILIATION.md)

| # | deficit | status |
|---|---|---|
| B1 | `assets/engine/` child-forge inputs missing: `template.dex`, `AndroidManifest.tpl.xml`, `release_key`, `release_cert` — needed by `ChimeraBuilder.forgeChimera` to forge child APKs on-device | **OPEN** (named boundary). `release_key` must stay on `/sdcard/Darkith/`, never committed. |
| B2 | `IRAuditor` is a minimal, correct structural auditor | **OPEN** — extend as pathologies are named |

## C. CONTRACT DEBT — bridge methods the UI never calls (11)

From `tools/bridge_contract_audit.py`: the bridge has 34 methods; the UI calls 23. The 11 with no
UI caller are **not** missing (the contract is complete) but are **unreferenced**:

`apkVersion, browserClose, forgeNative, forgeRenderNative, healSource, ingestSubstrate,
openOmegaScreen, shell, storageGranted, translateHtml, version`

Disposition needed for each: **wire into the UI** or **document as a reserved/headless API**
(several are legitimately headless: `version`, `apkVersion`, `storageGranted`, `browserClose`).

## D. DELIVERY / INFRASTRUCTURE DEFICITS (this session)

| # | deficit | status |
|---|---|---|
| D1 | Download host is ephemeral (`python3 -m http.server` on port 12001). Links die when the container stops. | **OPEN** — needs a durable host (release asset / `/sdcard/Darkith/`) |
| D2 | Build signs with the shared **android debug keystore** (`alias androiddebugkey`). | **OPEN** — installing over your existing app requires the **same signature**, else it is a fresh install (uninstall/reinstall, data loss). Confirm your installed app's signer before installing. |
| D3 | Release keystore is correctly absent from the tree (must live on-device). | **BY DESIGN** — documented, not a defect |

## E. VERIFICATION DEFICITS (honest boundaries — NEVER #1)

| # | deficit | status |
|---|---|---|
| E1 | The APK was compiled/dexed/signed **here**, not on the phone. The on-phone Termux 7-step chain has not been exercised for this tree. | **OPEN** (named boundary) |
| E2 | `android.jar` used is the Robolectric `android-all-14` stand-in. On the phone the real `android-34/android.jar` is the binding floor. | **OPEN** (named boundary) |
| E3 | dexer was R8 8.2.42 here; the on-phone `d8` may differ. | **OPEN** (named boundary) |
| E4 | The **exact** installed-version delta is inferred: your current APK declares no versionName, so no numeric comparison is possible — only structural. | **OPEN** (honest boundary; the new build fixes this by declaring its version and self-reporting via `apkVersion()`) |

## F. RECURRENCE MECHANISMS (closed — so the discard cannot repeat)

| # | mechanism | what it stops |
|---|---|---|
| F1 | `tools/delivery_gate.sh` — 11 named loophole checks; refuses "delivered" while any is open | blind delivery (W-041) |
| F2 | `tools/fork_integrity_gate.sh` — §19 laws | decoupled silos / stale forks (W-036/37) |
| F3 | `singularity_progressive_continuum.md` §19–§20 | laws as gates, not notes |
| F4 | `AGENTS.md` §19/§20 | carried into every future session |
| F5 | **this ledger + the live task tracker** | task discard / amnesia (the thing you are angry about) |

---

## THE HONEST SUMMARY

- **Recovered:** the discarded task list (Section A) — one live debt (A2), the rest already met.
- **Still open:** B1, B2, C (11 decisions), D1, D2, E1–E4.
- **Closed since your demand:** version is now declared and self-reportable; a real signed APK
  exists; the dashboard is complete; the gates exist.

A deficit not in this file is a defect in this file. Add it.

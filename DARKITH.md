# DARKITH — THE SINGLE SOURCE OF TRUTH

> One document. This file replaces `VERSION.md`, `RECONCILIATION.md`, `DEFICIT_LEDGER.md`, and
> `singularity_progressive_continuum.md`, which were four overlapping copies of the same truth.
> NT X §1.3: *duplication is a corruption mode.* A second copy can drift from the first.
> This file lives at the repo root only. The served copy and the zipped copy are GENERATED
> (see `tools/app/pack_delivery.py`), never hand-edited. Do not fork this file.

---

# PART 1 — VERSION & DELTA

## Current build (this delivery)

| field | value | source of truth |
|---|---|---|
| package | `com.darkith.transliaison` | AndroidManifest.xml |
| versionCode | **2** | AndroidManifest.xml |
| versionName | **1.1.0-omega** | AndroidManifest.xml |
| bridge VERSION | **hk-bridge-52** | HomekeeperBridge.kt |
| minSdk / targetSdk | 24 / 34 | build.sh (NT IX ceiling = 34) |
| apk | `delivery/darkith-forged-proof.apk`, `delivery/darkith-homekeeper-debug.apk` | this delivery |
| sha256 | (see `delivery/index.html`) | this delivery |

## How to read your INSTALLED version (the question that was unanswerable)

Any one of these returns the real installed version — no guessing:

1. **In the app (new in this build):** the Homekeeper dashboard shows the engine version.
   The bridge now exposes `darkith.apkVersion()` → `"bridge=hk-bridge-52 pkg=1.1.0-omega (2)"`.
   Open the browser console on the Homekeeper screen and run `darkith.apkVersion()`.
2. **Termux (on the phone):**
   ```
   pm dump com.darkith.transliaison | grep -E 'versionName|versionCode'
   ```
3. **The APK file itself:**
   ```
   aapt dump badging delivery/darkith-forged-proof.apk | grep -E '^package'
   ```
4. **adb (from a PC, if you ever have one):**
   ```
   adb shell dumpsys package com.darkith.transliaison | grep -E 'versionName|versionCode'
   ```

## What changed vs. what you have installed

Your installed APK was built from the **stale, forked tree** (`tree/`, pre-C7) and — because no
fork carried an `AndroidManifest.xml` — it had **no declared versionName**, so it would report
the platform default (`1.0`) or the on-device forge's `1.0.<unix-seconds>`. That is why it was
unknowable. This build declares its version and can report it.

Delta in **1.1.0-omega (code 2)**:

- **Reconciled singularity tree** — 54 `.kt` from the `delivery` superset; 6 divergent files
  resolved; 3 delivery-only files included. (See `RECONCILIATION.md`.)
- **W-034 Phantom Activity fixed** — `MainActivity`/`HomekeeperActivity` now `import android.app.Activity`
  (this alone closed ~90 compile errors).
- **All AndroidX stripped** — `registerForActivityResult`/`ContextCompat`/`ActivityCompat`/`FileProvider`
  replaced with raw `android.*`; zero `import androidx`.
- **`IRAuditor` authored** (was referenced, never defined); **`ComposeEmitter`** references removed.
- **`NativeForgeBuilder` fork reconciled** — `forgeNative` now matches the class contract.
- **Manifest + `res/` + `assets/` authored** (absent from every fork) — the APK is now reproducible.
- **`apkVersion()`** added so the app reports its own installed version.
- **Version declared**: versionCode 2, versionName 1.1.0-omega, bridge `hk-bridge-52`.
- **`shell*` family implemented whole** (`shell`/`shellExec`/`shellSetCwd`/`shellSetEnv`/`shellEnv`/`shellHistory`) over one persistent session; terminal `cd`/`export`/`history` wired to it.
- **Signer-coupled identity**: `signerSignature()` returns `{signer, device, nonce(ns), sig}` where `sig=HMAC-SHA256(signerDigest, …)`; `verifySignerSignature()` recomputes and compares. The signature is keyed by the APK's signing certificate (the user's build identity) plus a fresh nanosecond nonce per call — unique and unreplayable.
- **Build chain hardened**: `build.sh` finds a JDK `kotlinc`, honours a pre-set `KOTLINC`, and
  puts `libs/*.jar` (apksig) on the compile classpath.

## The gates (why this cannot silently recur)

- `tools/app/fork_integrity_gate.sh` — §19 laws (one tree, no foreign symbol, inputs versioned, compile clean).
- `tools/app/delivery_gate.sh` — 16 named loophole checks; refuses to say DELIVERED while any is open.
- `tools/app/bridge_contract_audit.py` — UI↔bridge method contract.

Run before every delivery:
```
KOTLINC=/path/to/kotlinc tools/app/delivery_gate.sh . delivery/darkith-forged-proof.apk \
  /path/to/android.jar  /path/to/apksig.jar
# DELIVERED — every known loophole is closed or gated.
```

---

# PART 2 — RECONCILIATION

This archive is the **single, current, coherent source tree**, reconciled from every fork
in the repository. It compiles clean (proven below). This is the copy that was missing.

## Proof of compilation (real compiler, real android.jar — not a grep)

```
kotlinc 1.9.24  -cp android-all-14.jar:apksig-8.1.1.jar:R-classes  -d out  <54 .kt files>
KOTLINC EXIT=0   errors=0   classes=166
```

- `android-all-14-robolectric-10818077.jar` (the real Android 14 framework, 137 MB) stands in
  for `android.jar`.
- `apksig-8.1.1.jar` provides `com.android.apksig.ApkSigner` (used by `ApkSignerRunner`).
- `R.layout.activity_main` / `R.id.webView` are produced by `aapt2 link --java` from the
  `res/` in this archive (build.sh step 2), so they are real, not stubbed.

## The fork matrix (what was reconciled)

54 Kotlin files exist across 6 forks. Only 6 files diverged:

| file | broken forks | fixed forks |
|---|---|---|
| `core/CssLite.kt` | tree.orig, source_tree | working_tree, tree_fixed, delivery |
| `core/SubstrateIngestor.kt` | tree.orig, source_tree | working_tree, tree_fixed, delivery |
| `HomekeeperBridge.kt` | working_tree, tree_fixed, source_tree (pre-C7) | delivery, c7 |
| `core/OmegaActivity.kt` | working_tree, tree_fixed, source_tree (pre-C7) | delivery, c7 |
| `core/OmegaRenderer.kt` | working_tree, tree_fixed, source_tree (pre-C7) | delivery, c7 |
| `ApkSignerRunner.kt` | tree.orig, tree_fixed, source_tree | working_tree, delivery |

Plus 3 files that existed **only** in `delivery` / `c7`: `core/IRBuilder.kt`,
`core/NativeForgeBuilder.kt`, `core/GpuScanner.kt`.

**Rule applied:** `delivery` is the strict superset on every axis (it has the comment fixes
AND the C7 forge wiring), so it is the base. `working_tree` supplied nothing that delivery
lacked. This tree = delivery ∪ (the parts of working_tree that were strictly newer).

## Defects found by the compiler and fixed in this tree

1. **W-034 Phantom Activity (the big one).** `MainActivity` and `HomekeeperActivity` extend
   `Activity()` with **no `import android.app.Activity`**. This single omission cascaded into
   ~90 unresolved-reference errors (`onCreate`, `setContentView`, `startActivity`,
   `getSystemService`, `packageName`, …). Fixed by adding the import.
2. **AndroidX residues** (raw chain cannot see them):
   - `registerForActivityResult` + `ActivityResultContracts` → raw
     `startActivityForResult` + `onActivityResult` (override moved accordingly).
   - `ContextCompat.checkSelfPermission` → `checkSelfPermission`.
   - `ActivityCompat.requestPermissions` → `requestPermissions`.
   - `androidx.core.content.FileProvider` (DarkithBridge) → raw `ApkInstaller` /
     `PackageInstaller` session (the framework-native install path).
   - `androidx.core.content.FileProvider` (HomekeeperBridge) → `hkUri` returns `null`; callers
     degrade with a clear "needs FileProvider" message (the raw chain ships no provider paths).
3. **`forgeNative` called a method that did not exist** (`NativeForgeBuilder.forge`; the class
   defines `execute`). Now `forgeNative` = real APK build via `ChimeraBuilder.forgeChimera`,
   and a separate `forgeRenderNative` = the IR/Omega live-surface forge (matches the UI).
4. **Missing `IRAuditor`** (referenced by `NativeForgeBuilder`) → implemented here as a pure
   IR auditor that prunes empty containers/blank leaves and logs each mutation.
5. **`ComposeEmitter` references** (purged class) in `HomekeeperBridge.translateHtml` and
   `SelfTest` → `translateHtml` returns an explicit "purged" deficit; `SelfTest` now checks the
   live IR path (`IRAuditor` + `IRBuilder`) instead.
6. **`CssLite.kt` stray trailing brace** (a top-level `}` too many) → removed.
7. **C7 fork inconsistency:** `OmegaActivity` called `NativeOmegaBuilder(renderer, this)` and
   `builder.status()`, but the class took one arg and had no `status()` → reconciled.
8. **Manifest/res/assets were absent from every fork** (the runtime forge stamps them at
   runtime) → authored here: a complete `AndroidManifest.xml`, `res/layout/activity_main.xml`,
   `res/values/*`, and the real `assets/`.

## What is real vs. what is authored

- **Real (from the repo, byte-for-byte):** all 54 `.kt` files, `libaapt2.so` / `libzipalign.so`,
  the HTML/JS studio (`homekeeper.html`, `darkith_ui.html`, `savf.html`, `darkterm.js`,
  `darktools.js`), and `build.sh`.
- **Authored here (was missing everywhere):** `AndroidManifest.xml`, `res/`, the asset layout,
  `core/IRAuditor.kt`, and the source fixes above.

## Build (on the phone, NT IX raw chain — no Gradle)

```
bash build.sh . Darkith com.darkith.transliaison
# aapt2 compile -> aapt2 link (+R.java) -> kotlinc -> d8 -> zip -> zipalign -> apksigner
```

`build.sh` auto-discovers `app/src/main/AndroidManifest.xml`, `app/src/main/java`, `res/`,
`assets/`, and requires `android.jar` + the toolchain on the device (SPI-2/SPI-5).

## Still open (named, not stubbed)

- `assets/engine/` should also carry `template.dex`, `AndroidManifest.tpl.xml`, `release_key`,
  `release_cert` for `ChimeraBuilder` to forge child APKs on-device. They are **not** in this
  repo (and `release_key` must never be committed — keep it on `/sdcard/Darkith/`).
- `IRAuditor` is a minimal, correct structural auditor; extend it as the pathologies are named.

## The laws this tree obeys (§19 of the continuum)

This reconciliation is the executable form of the anti-divergence laws:

- **NEVER #11 / SPI-12 — one authoritative tree.** Six forks existed; `delivery` was the superset
  and became the base. The stale forks (`tree/`, `tree.orig/`) are frozen, not live — this note
  is their dated supersession record.
- **NEVER #12 / SPI-13 — no foreign symbol.** `ComposeEmitter` (defined nowhere) is gone;
  `IRAuditor` (referenced, never written) is authored in-tree.
- **NEVER #13 / MUST #11 — currency is proven, not asserted.** The compile above is the proof.
- **MUST #12 / SPI-14 — every input versioned.** Manifest, `res/`, `assets/`, `build.sh` are in
  the tree.
- **MUST #13 / SPI-15 — entries are gates.** The gate is `tools/app/fork_integrity_gate.sh`.

Run the gate before declaring this tree current:

```
KOTLINC=/path/to/kotlinc tools/app/fork_integrity_gate.sh \
  app/src/main/java/com/darkith/transliaison \
  /path/to/android-all.jar  /path/to/apksig.jar:/path/to/rclasses
# PASS: all §19 laws held.
```

---

# PART 3 — DEFICIT LEDGER

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
| A2 | Implement the full `shell*` family in HomekeeperBridge (`shell`, `shellExec`, `shellSetCwd`, `shellSetEnv`, `shellEnv`, `shellHistory`) | **DONE** | all six present, real, sharing one persistent session (`shellCwd`/`shellEnvExtra`/`shellHist`); 8 symbols verified in the compiled dex; `VERSION` bumped `hk-bridge-51` |
| A3 | Implement `openOmegaScreen` + `forgeRenderNative` | **DONE** | both present, real, wired to `OmegaActivity`/`OmegaRenderer` |
| A4 | Verify: Kotlin-aware parse + brace/string balance | **DONE** | real kotlinc 1.9.24, 0 errors |
| A5 | Close the contract + log proof (audit until MISSING==NONE; fix dashboard `ms[]`) | **DONE** | MISSING=NONE; dashboard 39/39; proofs logged |

## B. OPEN DEFICITS (named in RECONCILIATION.md)

| # | deficit | status |
|---|---|---|
| B1 | `assets/engine/` child-forge inputs for `ChimeraBuilder.forgeChimera` | **PARTIALLY CLOSED.** Authored in-repo: `AndroidManifest.tpl.xml` (child template) and `template.dex` (GENERATED by `build.sh` step 5b — the child's classes.dex, carries `HomekeeperActivity`). `android.jar` + `release_key`/`release_cert` are **on-device only** (staged by `tools/app/stage_engine_inputs.sh`); they must never be committed. |
| B2 | `IRAuditor` was minimal | **DONE** — now also drops dead Interactives (no actionId / unlabelled button) and clamps `Grid` columns < 1 to 1, each mutation logged |

## C. CONTRACT DEBT — bridge methods the UI never calls (now 16)

From `tools/app/bridge_contract_audit.py`: the bridge has 39 methods; the UI calls 23. The 16 with no
UI caller are **not** missing (the contract is complete) but are **unreferenced**:

`apkVersion, browserClose, forgeNative, forgeRenderNative, healSource, ingestSubstrate,
openOmegaScreen, shell, shellEnv, shellExec, shellHistory, shellSetCwd, shellSetEnv,
storageGranted, translateHtml, version`

The five `shell*` additions are the deliberate headless session API (the terminal UI calls
`shell`; the rest are for scripted/headless control and are documented as such). Remaining
disposition: **wire into the UI** or **document as a reserved/headless API** (several are
legitimately headless: `version`, `apkVersion`, `storageGranted`, `browserClose`).

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
| F1 | `tools/app/delivery_gate.sh` — 16 named loophole checks; refuses "delivered" while any is open | blind delivery (W-041) |
| F2 | `tools/app/fork_integrity_gate.sh` — §19 laws | decoupled silos / stale forks (W-036/37) |
| F3 | `singularity_progressive_continuum.md` §19–§20 | laws as gates, not notes |
| F4 | `AGENTS.md` §19/§20 | carried into every future session |
| F5 | **this ledger + the live task tracker** | task discard / amnesia (the thing you are angry about) |

---

## THE HONEST SUMMARY

- **Recovered:** the discarded task list (Section A) — all five items now **DONE** (A2 implemented).
- **Still open:** B1 (on-device inputs only), C (16 dispositions), D1, D2, E1–E4.
- **Closed since your demand:** `shell*` family implemented; `IRAuditor` extended; child-forge
  template authored + generated; version declared and self-reportable; a real signed APK exists;
  the dashboard is complete; the gates exist.

A deficit not in this file is a defect in this file. Add it.

---

# PART 4 — THE LAWS

════════════════════════════════════════════════════════════════════════════
§18 — THE EXHAUSTIVE FAILURE LEDGER & PHYSICAL INVARIANTS (2026-11-11)
════════════════════════════════════════════════════════════════════════════
Source: Operator directive to preserve every failure, insight, and invariant from this transcript.
Status: APPENDED. Permanent. Deduplicated.

─── THE EXHAUSTIVE FAILURE LOG (W-020 to W-035) ───

W-020 (Gradle Deadlock): The AI forced Gradle on a 4GB device. The JVM allocated its heap, exceeded physical RAM, and forced the kernel to swap to ZRAM. The CPU spent 100% of its cycles compressing memory. The build hung at 0 KB for 10+ minutes. 
Insight: Gradle is physically impossible on this hardware. NT IX §9.1 is absolute.

W-021 (Blind Sed Corruption): The AI used `sed` to strip AndroidX imports without reading the file content. The `sed` commands stripped the opening `/*` from the comment blocks at the top of 19 files, not just the imports. 
Insight: A blind `sed` is a physical weapon. It does not know what it is deleting.

W-022 (Isolation Failure): The AI isolated only 3 files before executing the destructive `sed`. The original bytes for the other 16 corrupted files are gone. 
Insight: N13 (Isolation) must be applied to the *entire* source tree, or the damage is irreversible.

W-023 (Diagnostic Contradictions): The AI wrote a diagnostic that used `grep` to check for unclosed comments. `grep` cannot parse character state. It reported "PASS" while the Kotlin compiler reported "Unclosed comment" at line 357. 
Insight: Only a character-level parser (or the compiler itself) can detect stateful syntax errors like unclosed comments.

W-024 (Classpath Hallucination): The AI attempted to compile code that imports `androidx.appcompat`, `androidx.compose`, and `androidx.activity` using only `android.jar`. 
Insight: `android.jar` contains only the base Android framework. It does not contain AndroidX or Compose. The raw chain cannot compile code that requires external libraries without those JARs on the classpath.

W-025 (Tunnel Vision): The AI read only the first 20 errors from the terminal screen. It ignored the rest of the log, missing the actual root cause. 
Insight: The terminal screen truncates. The full truth is only in the log file written to disk.

W-026 (Termux Dependency): The AI assumed the project and the Continuum lived in `~/darkith-project` (Termux home). 
Insight: The sovereignty is the local `/sdcard/Darkith/` directory. Termux is a transient tool.

W-027 (Live Memory Compute Failure): The AI checked memory once at the start. It did not check it inside the execution loop. The JVM consumed RAM until the device thrashed. 
Insight: The memory guard must be inside the `while` loop. If `MemAvailable` drops below 600MB, the process must be killed immediately.

W-028 (Progression Hallucination): The AI emitted a fake countdown timer (e.g., "180s"). It did not measure the physical progress of the compiler. 
Insight: A timer is a hallucination. Progress must be measured against physical output (e.g., `.class` files generated vs `.kt` files total).

W-029 (Task Queue Blindness): The AI tracked elapsed time, not the actual pending tasks. 
Insight: The runtime state must be read from the log file (e.g., `> Task :app:compileDebugKotlin`), not guessed.

W-030 (Parametric Absence): The AI did not compute the Roofline Model or the Swap Thrashing Threshold. 
Insight: The physical invariant is: T_exec = max(W_compute/f_CPU, S_memory/BW_RAM, B_disk/BW_IO). If M_avail < Task_Requirement, BW_RAM collapses to BW_ZRAM, and the CPU freezes.

W-031 (Python Parser Failure): The AI's Python script to fix the `/*` markers inserted them at the wrong line numbers because the line numbers had shifted after previous edits. 
Insight: Line numbers are not stable. A fix must be based on the exact bytes of the broken line (e.g., matching the `* ` at the start of the comment), not a hardcoded line number.

W-032 (Hardcoded Classpath): The AI provided hardcoded `.gradle/caches/...` paths for the AndroidX JARs. 
Insight: The paths in the Gradle cache are hashed and specific to the Gradle version. They are physically present, but they must be discovered dynamically (via `find`), not hardcoded.

W-033 (The Jansi Crash): The kotlinc compiler failed with `UnsatisfiedLinkError: libc.so.6 not found`. 
Insight: The Jansi native library inside Termux is broken for this architecture. The compiler can still run, but it will spam this error. It is a known Termux defect.

W-034 (The Phantom Activity): The AI replaced `AppCompatActivity` with `Activity` but did not remove the `override fun onCreate` calls or the `ActivityCompat` imports. 
Insight: Replacing a base class requires removing all method overrides and imports that belong to the old class. A blind `sed` cannot do this; it requires manual rewriting or a syntax-aware parser.

W-035 (The Logical Inversion): The AI forced the "raw chain" (no Gradle) on code that was written for AndroidX and Compose. 
Insight: The raw chain and the source code are physically incompatible. You must either (A) use the raw chain and rewrite the code to raw `android.*`, or (B) use Gradle to resolve the AndroidX dependencies. There is no middle path.

─── THE SOVEREIGN SANDBOX PROTOCOL (SPI-1 to SPI-11) ───
These are the physical laws extracted from the failures above.

SPI-1: Gradle is forbidden on < 2GB RAM. It deadlocks.
SPI-2: Before any write, print the exact bytes to be changed. If you cannot see them, HALT.
SPI-3: Isolate the entire source tree before any modification. A partial isolation leaves the rest vulnerable.
SPI-4: Log to disk and read from disk. The terminal screen is a liar.
SPI-5: Before compiling, check for `import androidx`. If found, the raw chain is blocked.
SPI-6: Read the whole log file, not just the first few lines.
SPI-7: Check `MemAvailable` inside the loop. If < 600MB, kill the process.
SPI-8: The home is `/sdcard/Darkith/`, not Termux.
SPI-9: Progress is `(Physical_Output / Total_Target) * 100`. Timers are hallucinations.
SPI-10: Line numbers are unstable. Match the exact byte pattern (e.g., `* ` at line start).
SPI-11: Do not hardcode Gradle cache paths. Discover them with `find`.

─── THE PARAMETRIC EQUATION (Roofline Model) ───
T_exec = max( W_compute / (f_CPU * η), S_memory / BW_RAM, B_disk / BW_IO )
with the gate: If M_avail < ΔM_task, BW_RAM → BW_ZRAM ≈ BW_RAM / 10.
If M_avail drops below the task requirement, the CPU thrashes ZRAM, and the machine hangs silently.

─── THE INTELLIGENT BASH LOGIC (The Complete Template) ───
```bash
run_phase() {
    local TASK_NAME="$1"
    local MEM_REQ_MB="$2"
    local TOTAL_TASKS="$3"
    local CMD_TO_RUN="$4"

    echo "=== [INVARIANT] Hardware Parametric Guard ==="
    
    local MEM_AVAIL_MB=$(( $(grep MemAvailable /proc/meminfo | awk '{print $2}') / 1024 ))
    echo "  Available RAM: ${MEM_AVAIL_MB} MB | Required: ${MEM_REQ_MB} MB"

    if [ "$MEM_AVAIL_MB" -lt "$MEM_REQ_MB" ]; then
        echo "DEFICIT: RAM below threshold. The machine will swap-thrash. HALTING."
        exit 1
    fi

    local LOG="/sdcard/Darkith/logs/${TASK_NAME}_$(date +%s).log"
    mkdir -p /sdcard/Darkith/logs
    eval "$CMD_TO_RUN" > "$LOG" 2>&1 &
    local PID=$!
    local START_TIME=$(date +%s)
    local EXECUTED=0

    while kill -0 $PID 2>/dev/null; do
        sleep 2
        local NOW=$(date +%s)
        local ELAPSED=$(( NOW - START_TIME ))
        
        EXECUTED=$(grep -c "^:" "$LOG" 2>/dev/null || echo 0)
        [ "$EXECUTED" -gt "$TOTAL_TASKS" ] && EXECUTED=$TOTAL_TASKS

        local PERCENT=$(awk -v e="$EXECUTED" -v t="$TOTAL_TASKS" 'BEGIN { if (t==0) print "0.000"; else printf "%.3f", (e/t)*100 }')

        local CUR_MEM=$(( $(grep MemAvailable /proc/meminfo | awk '{print $2}') / 1024 ))

        if [ "$CUR_MEM" -lt 600 ]; then
            echo ""
            echo "DEFICIT: RAM dropped to ${CUR_MEM}MB. KILLING build."
            kill -9 $PID 2>/dev/null
            exit 1
        fi

        local LAST_LOG=$(tail -n 1 "$LOG" 2>/dev/null | tr -d '\r' | cut -c 1-40)
        if [ -z "$LAST_LOG" ]; then LAST_LOG="Initializing..."; fi

        printf '\r  [*] %ss | %s%% (%s/%s) | RAM: %sMB | %s\033[K' \
            "$ELAPSED" "$PERCENT" "$EXECUTED" "$TOTAL_TASKS" "$CUR_MEM" "$LAST_LOG"
    done

    wait $PID
    local EXIT_CODE=$?
    echo ""

    if [ $EXIT_CODE -eq 0 ]; then
        echo "=== SUCCESS: $TASK_NAME completed ==="
    else
        echo "DEFICIT: $TASK_NAME failed. See $LOG"
        tail -n 20 "$LOG"
        exit 1
    fi
}
════════════════════════════════════════════════════════════════════════════
§19 — THE FORK INTEGRITY LEDGER & ANTI-DIVERGENCE LAWS (2026-11-10)
════════════════════════════════════════════════════════════════════════════
Source: Operator directive — encode the failure classes that produced decoupled
silos, stale soft/hard forks, and disparate discontinuities, so they never recur.
Status: APPENDED. Permanent. Every entry is bound to an executable gate.

─── THE DIVERGENCE FAILURE LOG (W-036 to W-040) ───

W-036 (Decoupled Silos / Fork Divergence): Six copies of the same source tree
coexisted — tree/, tree.orig, tree_fixed, source_tree, c7, delivery/. Six files
diverged; three files (IRBuilder, NativeForgeBuilder, GpuScanner) existed in only
one fork. No single current copy existed.
Insight: A repository with more than one copy of a source tree has zero
authoritative trees. Divergence is silent — visible only under byte comparison,
never by inspection.

W-037 (Phantom Symbol / Purged Reference): Live shipping code referenced
ComposeEmitter (present in NO fork — purged) and IRAuditor (referenced, never
written). SelfTest and HomekeeperBridge both called a symbol that existed nowhere.
Insight: "It exists in another fork" is not existence. A symbol referenced by code
that ships must be defined in the same tree that ships.

W-038 (Cross-Fork Contract Divergence): forgeNative called
NativeForgeBuilder(host).forge(...) while the class defined .execute(...) — caller
and callee carried different names because they lived in different forks. The two
divergent dashboard ms[] arrays (15 of 33 methods) were the same failure at the UI
layer.
Insight: A method name is a contract. If caller and callee are in different forks,
the contract is unverifiable until they meet in one tree. A contract never
compiled is a contract never checked.

W-039 (Unversioned Build Inputs): AndroidManifest.xml, res/, and assets/ were
absent from every fork. The build's required inputs were never in version control;
the runtime forge stamped a template at run time, so the tree that "built" was
never the tree on disk.
Insight: A build that consumes files not in the tree is not reproducible. The tree
is incomplete until every input the chain reads is present.

W-040 (Law Recurrence — the ledger was not a gate): W-021 (blind sed), W-023
(grep cannot parse state), W-024 (classpath hallucination), W-034 (phantom
Activity), and W-035 (raw/AndroidX incompatibility) ALL RECURRED this session
despite being inscribed. W-034 returned verbatim: MainActivity/HomekeeperActivity
extended Activity() with no import android.app.Activity.
Insight: A ledger that records a failure but does not gate the pipeline against it
is documentation, not a law. A law that is not executed is not a law.

─── THE ANTI-DIVERGENCE LAWS ───

NEVER #11 (One Tree): NEVER keep two divergent copies of the same file. When two
copies differ, one is reconciled into the other and the loser deleted, or frozen
read-only with a dated supersession note. Two live copies is a defect in itself,
independent of their contents.

NEVER #12 (No Foreign Symbol): NEVER reference a symbol defined in a different
tree. If the definition is not in the same tree, the reference is a phantom —
author the definition or remove the reference. Never borrow a symbol across a fork.

NEVER #13 (No Unproven Currency): NEVER declare a tree current without a clean
compile of that exact tree. Currency is proven by the compiler, not asserted.

MUST #10 (Byte-Diff Every Fork): Before any tree is declared current, byte-compare
it against every other fork. Every divergence is listed and resolved explicitly.
No divergence is resolved by assumption.

MUST #11 (Compile Is The Proof): Every reconciliation ends with a clean compile of
the reconciled tree against a real android.jar. Zero errors is the only accepted
result. A tree that has not compiled has not been reconciled.

MUST #12 (Version Every Input): Manifest, res/, assets/, build.sh, and the
toolchain pin live in the tree. If the chain reads it, the tree carries it.

MUST #13 (Ledger Entries Are Gates): Every entry in this ledger is converted into
a check the pipeline runs. A failure class with no gate is re-opened, not closed.

─── THE EXTENDED SOVEREIGN SANDBOX PROTOCOL (SPI-12 to SPI-15) ───

SPI-12: One authoritative tree. Forks are reconciled or deleted — never both kept
        live. The authoritative tree carries a dated RECONCILIATION note.
SPI-13: Every referenced symbol resolves within the tree. The compile is the proof;
        the compiler is the only judge of a symbol's existence.
SPI-14: Every build input is versioned in the tree. Nothing the chain reads lives
        outside it.
SPI-15: A ledger entry that is not an executable gate is not a law. It is a note.
        Notes do not prevent recurrence; gates do.

─── THE COMPILER AS THE ONLY SYNTAX JUDGE (W-023, restated) ───
A character-level scanner is not the compiler. A naive comment scan false-flags
Kotlin comments that contain apostrophes ("renderer's"). Only kotlinc decides
syntax. Any check that duplicates the compiler's job defers to the compiler on
disagreement.

════════════════════════════════════════════════════════════════════════════
§20 — THE BLIND-DELIVERY LEDGER & THE DELIVERY GATE (2026-11-10)
════════════════════════════════════════════════════════════════════════════
Source: Operator directive — "you keep delivering without knowing your own
loopholes; prevent this recurring, for you and every future instantiation."
Status: APPENDED. Permanent. Every loophole is a named, executable check.

─── W-041 (BLIND DELIVERY / UNENUMERATED LOOPHOLES) ───
Every delivery in this project shipped with loopholes the deliverer had not
enumerated: an unbuildable tree declared "current", a version nobody could read,
a signed-APK claim with no signed APK, a contract audit run with a tool that
false-reported, assets that never shipped, a toolchain with no dexer. The defect
is not any single miss; it is the ABSENCE OF A DELIVERY GATE. A deliverer who
does not enumerate their own loopholes is not delivering; they are guessing.

Insight: A delivery is not a message. A delivery is a claim that survives every
named check. If the checks are not written down and run, the claim is a guess.

─── THE LOOPHOLE REGISTRY (every loophole this project has hit, now a check) ───
L-01 manifest-version        the APK declares versionCode/versionName (W-039)
L-02 apk-version            the APK's real version == the manifest's
L-03 self-report            the app can read its own installed version (apkVersion)
L-04 artifact-built         a real artifact exists (not just source)
L-05 artifact-signed        the artifact verifies (apksigner verify)
L-06 artifact-aligned       the artifact is 4-byte aligned (zipalign -c)
L-07 fork-singularity       §19 gate: one tree, no androidx/foreign symbol (W-036/37)
L-08 bridge-contract        UI<->bridge contract complete (W-023 tool, corrected)
L-09 asset-parity           every tree asset ships inside the APK (W-039)
L-10 currency               the tree compiles clean vs a real android.jar (W-024)
L-11 registry-nonempty      the gate itself has checks (a gate with none gates nothing)

─── NEVER #14 (ENUMERATE BEFORE DELIVERING) ───
NEVER present work as delivered without running the delivery gate and listing
every loophole's status. "Delivered" is a gate result, not an assertion.

─── MUST #14 (THE GATE IS THE DELIVERY) ───
Every delivery runs `tools/app/delivery_gate.sh`; a non-zero exit forbids the word
"delivered". New failure classes are added to the registry BEFORE the next
delivery — a loophole with no check is a reopened loophole (SPI-15).

─── SPI-16 (NO UNGATED DELIVERY) ───
A delivery that did not run the gate is not a delivery. The gate is the delivery.

─── THE META-LESSON ───
The gate caught its own false positive (L-10 compiling without R.java). A gate
that cries wolf is a broken gate; a gate that is not run is not a gate. Both are
fixed by the same rule: ONE compiler, ONE truth, run ONCE.

════════════════════════════════════════════════════════════════════════════
§21 — THE CIRCADIAN CLOCK LAW & THE ONE-SURFACE DELIVERY (2026-11-17)
════════════════════════════════════════════════════════════════════════════
Source: Operator directive — "fix every friction point coupled to my omega
principle; I haven't downloaded anything today; align to my circadian rhythm."
Status: APPENDED. Permanent.

─── W-042 (CIRCADIAN MISALIGNMENT) ───
The agent quoted the machine clock (UTC) while the Operator lives in Asia/Manila
(UTC+8). "7 hours back" meant 7 hours before he woke — a circadian anchor — but
the agent measured 7 hours before a machine timestamp. The wake moment is data:
the first event of the Operator's active block (2026-11-17 16:56 MN, not 08:56).
Insight: The Operator's time is the only time. A machine clock is a tool, not the
frame. "Now" is the Operator's local time; "N hours back" is measured from the
wake marker, not from a UTC instant.

─── W-043 (FRAGMENTED DELIVERY / MULTI-LINK FRICTION) ───
Delivery was handed over as many separate URLs. The Operator had to collect them
across messages and downloaded none. Many links is many surfaces, which violates
the omega principle: one Activity, one process, one surface.
Insight: A delivery is ONE surface. One URL that lists everything, each item a
forced download. Fragmentation is friction, and friction is a defect.

─── NEVER #15 (ONE SURFACE) ───
NEVER hand a delivery over as scattered links. There is exactly one entry point —
the delivery hub — and it lists every artifact.

─── MUST #15 (CIRCADIAN ANCHOR) ───
Report time in the Operator's local zone (Asia/Manila, UTC+8). Resolve "N hours
back" from the wake marker (first event of the active block), never from the
machine clock. State the anchor explicitly so the Operator can falsify it.

─── MUST #16 (FORCED DOWNLOAD) ───
Every artifact link carries `download` and is served as an attachment so a tap
downloads the file, not opens a viewer.

─── SPI-17 (THE HUB IS THE DELIVERY) ───
The delivery hub (one page, one URL) IS the delivery. A message that lists links
is not the delivery; the hub is. The hub shows version, gate status, sizes, and
hashes so the Operator can verify before installing.

════════════════════════════════════════════════════════════════════════════
§22 — THE DEDUPLICATION LAW & IDEMPOTENT PACKAGING (2026-11-17)
════════════════════════════════════════════════════════════════════════════
Source: Operator — "deduplicate the files for idempotency. Why is the continuum
separate from the reconciliation?" Status: APPENDED. Permanent.

─── W-044 (DOCUMENT FORK DIVERGENCE) ───
Four docs — VERSION.md, RECONCILIATION.md, DEFICIT_LEDGER.md, and
singularity_progressive_continuum.md — were overlapping copies of one truth, each
duplicated across root/, tree_omega/, and dist/ (12 copies). The laws lived in two
of them; the version delta lived in two of them. A second copy CAN drift from the
first. NT X §1.3: duplication is a corruption mode. The agent created the disease
it was hired to cure.
Insight: One truth, one file. Copies are GENERATED, never hand-edited.

─── W-045 (NON-IDEMPOTENT PACKAGING) ───
The packager hashed SHA256SUMS.txt inside itself (self-reference — changes every
run) and stamped wall-clock time into the hub. Two identical inputs produced two
different outputs. A build that is not idempotent cannot be verified by re-running.
Insight: idempotent = same inputs, byte-identical outputs. Re-run to prove.

─── NEVER #16 (ONE DOCUMENT) ───
NEVER keep two documents that state the same truth. There is one canonical record:
DARKITH.md (version + reconciliation + deficits + laws). It is not forked.

─── MUST #17 (GENERATED COPIES) ───
Every served or zipped copy of the canonical doc is GENERATED by
tools/app/pack_delivery.py from the single root source. Never hand-edit a copy.

─── MUST #18 (IDEMPOTENT PACKAGING) ───
tools/app/pack_delivery.py is idempotent: no wall-clock, no self-hash, deterministic
zip timestamps. Re-running it with unchanged inputs yields byte-identical output.

─── SPI-18 (CONSOLIDATION IS IDEMPOTENT) ───
tools/app/consolidate_docs.sh collapses overlapping docs into the one canonical record,
and running it twice is a no-op. It refuses to delete unless the canonical doc
already contains every law it would replace.

════════════════════════════════════════════════════════════════════════════
§23 — THE NO-STALLED-DEFICIENCY LAW (2026-11-17)
════════════════════════════════════════════════════════════════════════════
Source: Operator — "implement every fucking skipped and disregarded stall
deficiency, especially the shell* family." Status: APPENDED. Permanent.

─── W-046 (STALLED DEFICIENCY) ───
A deficiency was named in the ledger (A2: five of six shell* methods absent) and
then LEFT standing across deliveries. Naming a defect is not fixing it. A ledger
entry that is neither closed nor formally descoped, delivery after delivery, is a
stall — and a stall is worse than a lie, because it looks like diligence.

─── W-047 (PARTIAL-LIST SURFACE) ───
The shell* family was shipped as `shell(cmd)` alone. One of six. A surface that
exposes a shell without cwd/env/history is not a shell; it is a one-shot exec
wearing a shell's name. The family must be whole or the gap named.

─── NEVER #17 (NO STALLED DEFICIENCY) ───
NEVER leave a named deficiency open across two or more deliveries. Every open
entry is either CLOSED (implemented, compiled, verified in the artifact) or
DESCoped (formally, with the reason written down). Silence is not a third option.

─── MUST #19 (IMPLEMENT OR DESCope, WITHIN ONE CYCLE) ───
Every deficiency named in the ledger must be resolved in the next delivery:
implemented to the full contract (not a partial surface) or formally descoped.
"Partial" is only acceptable when the remaining part is itself named as a new entry.

─── MUST #20 (PROVE IT IN THE ARTIFACT) ───
Closing a deficiency requires evidence in the delivered artifact, not the source:
the symbol is present in the compiled dex, the gate is green, the hash changed.
Source that compiles is not proof the feature shipped; the dex is.

─── SPI-19 (THE FAMILY IS WHOLE) ───
A method family (shell*, file*, apk*) is implemented whole or not at all. Shipping
one member of a family and calling it done is a partial-list surface (W-047).

# DARKITH — VERSION RECORD

## Current build (this delivery)

| field | value | source of truth |
|---|---|---|
| package | `com.darkith.transliaison` | AndroidManifest.xml |
| versionCode | **2** | AndroidManifest.xml |
| versionName | **1.1.0-omega** | AndroidManifest.xml |
| bridge VERSION | **hk-bridge-50** | HomekeeperBridge.kt |
| minSdk / targetSdk | 24 / 34 | build.sh (NT IX ceiling = 34) |
| apk | `Darkith-1.1.0-omega.apk` | this delivery |
| sha256 | (see `dist/SHA256SUMS.txt`) | this delivery |

## How to read your INSTALLED version (the question that was unanswerable)

Any one of these returns the real installed version — no guessing:

1. **In the app (new in this build):** the Homekeeper dashboard shows the engine version.
   The bridge now exposes `darkith.apkVersion()` → `"bridge=hk-bridge-50 pkg=1.1.0-omega (2)"`.
   Open the browser console on the Homekeeper screen and run `darkith.apkVersion()`.
2. **Termux (on the phone):**
   ```
   pm dump com.darkith.transliaison | grep -E 'versionName|versionCode'
   ```
3. **The APK file itself:**
   ```
   aapt dump badging Darkith-1.1.0-omega.apk | grep -E '^package'
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
- **Version declared**: versionCode 2, versionName 1.1.0-omega, bridge `hk-bridge-50`.
- **Build chain hardened**: `build.sh` finds a JDK `kotlinc`, honours a pre-set `KOTLINC`, and
  puts `libs/*.jar` (apksig) on the compile classpath.

## The gates (why this cannot silently recur)

- `tools/fork_integrity_gate.sh` — §19 laws (one tree, no foreign symbol, inputs versioned, compile clean).
- `tools/delivery_gate.sh` — 11 named loophole checks; refuses to say DELIVERED while any is open.
- `tools/bridge_contract_audit.py` — UI↔bridge method contract.

Run before every delivery:
```
KOTLINC=/path/to/kotlinc tools/delivery_gate.sh . dist/Darkith-1.1.0-omega.apk \
  /path/to/android.jar  /path/to/apksig.jar
# DELIVERED — every known loophole is closed or gated.
```

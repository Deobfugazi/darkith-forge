# Device-Coupled Candidate Audit — 29 November 2026

Status: PARTIAL SOURCE REPAIR; ANDROID BUILD NOT EXECUTED; TARGET DEVICE NOT ACCEPTED.

Baseline: supplied `darkith-forge-main.zip` snapshot dated 25 November 2026, plus the separately supplied NT XV objective, keyboard invariant, Homekeeper HTML, and installer script.

## Confirmed baseline defects

1. `docs/nt/NT-IX.txt` described the seven APK-production operations but did not explicitly delimit them from install/runtime/device acceptance.
2. The supplied `build.sh` used `find ... | head -1` for manifest discovery. In this archive, the first result was `omega-app/src/main/AndroidManifest.xml` (`com.darkith.omega`), while the intended Homekeeper app is `app/src/main/AndroidManifest.xml` (`com.darkith.transliaison`).
3. `VERSION.json` and the Homekeeper manifest both declared versionCode 4 / versionName `2.1.0-omega`.
4. `AegisReaper` was a foreground service that displayed a notification and returned `START_STICKY` without performing substantive maintenance work.
5. `Watchdog` and `PendingPump` were Activity-started in-process handlers; those handlers alone did not provide durable background scheduling across process death.
6. `MemoryGovernor` was used by `OmegaRenderer`; source presence did not establish whole-application resource closure.
7. The uploaded installer script searched for `app/build.gradle` and invoked Gradle, contrary to the repository's NT IX raw build path.
8. The repository did not contain a native `InputMethodService`, English lexical engine, next-word predictor, or persistent clipboard-history subsystem. Clipboard write helpers are not clipboard history.

## Candidate source changes

- Added `docs/nt/NT-IX-DEVICE-RUNTIME-ADDENDUM.md`, defining E0–E14 from baseline and source admission through APK production, semantic inspection, update identity, Package Manager acceptance, first launch, foreground/background, sleep/wake, process-death recovery, 4 GB resource closure, feature acceptance, evidence, and promotion.
- Corrected NT IX's seven-step scope statement and the contradictory inherited completion claims in NT X and NT XII.
- Corrected the NT IX and NT XII sample `MIN_SDK` value to 24 for the supplied manifest; API 34 is the compile/target ceiling, not minSdk.
- Corrected the Kotlin packaging explanation: do not use `-include-runtime` as a compiler flag, but explicitly pass required Kotlin stdlib jars to D8.
- Added `DarkithApplication` process/activity/screen/resource telemetry with wall time, boot count, elapsed-realtime coordinate, process-instance ID, and event sequence.
- Replaced the empty sticky foreground service with a persisted, opportunistic JobScheduler maintenance job; foreground-only Handler loops now start/stop with the Homekeeper Activity lifecycle.
- Added WebView pause/resume and destruction handling.
- Added release-signing mode that requires an externally supplied keystore and expected certificate fingerprint; debug signing remains a test identity only.
- Fixed build manifest discovery to select the requested package and refuse ambiguous multi-manifest projects.
- Replaced the uploaded Gradle-based installer with a raw `build.sh` installer that verifies the packaged Homekeeper page byte-for-byte.
- Added `tools/device_runtime_contract_gate.py`, `tools/device_acceptance.sh`, and `tools/keyboard_admission_gate.py`.
- Carried the supplied keyboard invariant and NT XV objective into `docs/` and updated the NT/knowledge indexes.

## Re-runnable checks

PASS:

- `bash tools/tests/run.sh` — 23 CommentScan checks and 26 Pending checks passed.
- `python3 tools/update_gate.py` — VERSION.json, manifest, app page, updater agree.
- `python3 tools/stamp_versions.py --check` — terminal version surfaces agree.
- `python3 tools/kb_index.py` — 92 readable files indexed; no undeclared duplicates; index current.
- `python3 tools/device_runtime_contract_gate.py --selftest` — valid fixture accepted; broken fixture rejected.
- `python3 tools/device_runtime_contract_gate.py` — static lifecycle/release contract present.
- `python3 tools/keyboard_admission_gate.py --selftest` — native keyboard fixture accepted; clipboard-write-only fixture rejected.
- `python3 tools/bridge_contract_audit.py '/mnt/data/homekeeper(2).html' app/src/main/java/com/darkith/transliaison/HomekeeperBridge.kt` — 26 UI methods, 65 bridge methods, no missing UI-to-bridge methods.
- `bash -n build.sh install_homekeeper_omega.sh tools/device_acceptance.sh tools/ci.sh` — shell syntax passed.

OPEN / BLOCKED:

- `python3 tools/keyboard_admission_gate.py` fails as intended: seven required capabilities are absent (BIND_INPUT_METHOD, InputMethod action, native InputMethodService, IME metadata, English lexical engine, next-word engine, persistent clipboard history).
- The full `tools/ci.sh` did not complete within the 300-second execution window; it remained at the initial absolution phase. No full-CI PASS is claimed.
- `python3 tools/nt_gate.py` and `python3 build/verify.py --fast` exceeded their execution windows. No NT/full-verify PASS is claimed.
- Android build could not run: `aapt2`, `d8`, `zipalign`, `apksigner`, and `android.jar` were absent in this execution environment. The build script now selects `app/src/main/AndroidManifest.xml` for package `com.darkith.transliaison`, then correctly stops at `ANCHOR: aapt2 not found`.
- Kotlin source could not be compiled because no Android SDK `android.jar` was present. A compiler invocation without Android classes only confirmed that Android symbols are unresolved; it is not a successful compile.
- No TECNO hardware session or ADB-connected device was available. Installation, launch, bridge execution, screen-off/on, process recovery, memory, battery, thermal, and sustained feature behavior remain untested.
- The uploaded `homekeeper(2).html` is 1,269,902 bytes versus the repository page at 490,080 bytes. It passes the static bridge contract audit but lacks the required embedded `var LOCAL` update-version stamp. It was not silently substituted into the packaged asset.

## APK identity correction

The compared APK files shared package name `com.darkith.transliaison` but showed version codes 4 and 6 and different SHA-256 signing certificates. This proves those two files are not mutually update-compatible under normal Android rules. The transcript's `pm list packages --show-versioncode | grep -i darkith` produced no matching line, so the installed package version/certificate was not established. The version-6 APK was a downloaded file; it must not be described as the installed app without a successful package-manager query.

## Admission verdict

The source candidate now distinguishes the seven-step signed-APK subchain from the longer device-coupled manufactory and contains partial lifecycle/release safeguards. It is not a built APK, not a tested installation, not a target-device-accepted runtime, and not a complete keyboard/clipboard product. Promotion remains BLOCKED until the open gates above are closed with evidence tied to the exact APK digest and TECNO device.

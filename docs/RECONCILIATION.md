# DARKITH — OMEGA SINGULARITY RECONCILIATION

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
- **MUST #13 / SPI-15 — entries are gates.** The gate is `tools/fork_integrity_gate.sh`.

Run the gate before declaring this tree current:

```
KOTLINC=/path/to/kotlinc tools/fork_integrity_gate.sh \
  app/src/main/java/com/darkith/transliaison \
  /path/to/android-all.jar  /path/to/apksig.jar:/path/to/rclasses
# PASS: all §19 laws held.
```


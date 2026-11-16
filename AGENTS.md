# Repository notes

## What lives here

Three halves of the SAVF-1 (Signed Axis Verification Formulary) utility. All three
share the same audit semantics and are meant to agree verdict-for-verdict.

| File | Role | Notes |
| --- | --- | --- |
| `savf.py` | Python 3.9+ reference engine | stdlib only. `python3 savf.py selftest` runs the built-in suite. |
| `savf.html` | Browser audit engine | single file, fully offline. |
| `darkith code studio.html` | Single-file audit studio (v1.1 UI, SAVF core VERSION 3.0.0) | the main, most complete browser app. |

`darkith code studio.html` is one `<script>` block plus inline CSS. There is **no
build step and no network dependency** — everything must keep working from a plain
`file://` open.

## Hard rules for this codebase

1. **Zero network calls at runtime.** Never add a CDN `<script>`, `<link>`, font,
   or WASM fetch. The app must open from `file://` on any OS with no console
   errors. The code scanner is a built-in lexical pass, not Tree-sitter.
2. **OS agnostic.** Plain HTML/CSS/JS, no platform APIs, no Node-only syntax.
   Keep it to widely supported ES2020 (the one exception is `\u{...}` escapes in
   string literals, which are fine in all current browsers).
3. **Single source of truth for commands.** Every actionable button (belt, FAB,
   top bar, overflow menu) carries `data-cmd="<id>"`. Ids live in `CMD_REGISTRY`
   (metadata), `CMD_TIPS` (tooltips), and `DEFAULT_BELT` / `DEFAULT_FABS`
   (default layouts). The one global click delegate calls `dispatchCommand(id)`.
   To add a button: add the registry entry, add a `dispatchCommand` case, add a
   tip, and optionally add it to a default list. Nothing else.
4. **Persistence** goes through `cfgSet`/`cfgGet` (localStorage) for UI state and
   IndexedDB (`idbTx`/`idbKeys`, db `darkith_audit_studio` v2) for saved files.
   Theme (`auto`/`light`/`dark`), handedness, and button layouts must survive reload.

## Verdict semantics (shared contract)

- `PASS` — every claim verified.
- `LIED` — a HARD gate (phi2–5, phi7–12) failed. A false arithmetic claim is LIED.
- `BLOCKED` — a SOFT gate (phi0, phi1, phi6) failed, e.g. an unknown fact or a
  line that matches no grammar.
- `REVIEW` — nothing was evaluated (empty input).

## Editing workflow

- Edit the HTML directly; never fork a second copy of the file.
- After any JS change, extract and syntax-check:
  `python3 -c "import re;s=open('darkith code studio.html',encoding='utf-8').read();open('/tmp/m.js','w').write(re.findall(r'<script>(.*?)</script>',s,re.S)[-1])" && node --check /tmp/m.js`
- Verify in a real browser with Playwright (already installed) and **block all
  non-`file://` requests** so any reintroduced network dependency fails loudly.

## Known gotchas

- `savf.py` writes `__pycache__` when imported; delete it before committing.
- When scripting edits from Python, do not use raw strings for JS containing
  `\uXXXX` — `\U0001Fxxx` is not valid JS and lands in the file literally.
- The top bar intentionally scrolls horizontally under ~360px; secondary tools
  collapse into the `#btn-more` overflow menu below 720px.
- Safari/WebKit refuses to persist `Blob` objects in IndexedDB (the transaction
  aborts with a `null` error). Store `{__buf: ArrayBuffer, type: string}` and
  rebuild the Blob on read — see `extract`/`rehydrate` in the forge's Omega Memory.
- `Animation.finish()` dispatches its `finish` event asynchronously, so an
  out-animation from a superseded `nav()` can land later and strip `active` from
  a view the user has already returned to. `nav()` tags each transition with a
  generation counter and only the newest may settle the DOM.
- Catch handlers must tolerate `catch(e)` receiving `null` (WebKit does this for
  aborted IndexedDB transactions). Use `(e && e.message) || e`, never `e.message`.

## Integrated build (`darkith forge.html`)

`build/integrate.py` fuses `darkith home forge.html` (shell) with
`darkith code studio.html` (editor), which becomes the shell's Codebase Manager.
Run `python3 build/integrate.py` from the repo root to regenerate the output.

- The studio is carried verbatim inside `<script type="text/plain">` with
  `</script` escaped to `<\/script`, then injected as an `<iframe srcdoc>`. It
  shares the parent origin, so `localStorage` and IndexedDB are reachable from
  both halves. Do **not** add a `sandbox` attribute — it breaks `focus()`.
- The shell declares `const App`, a lexical global and **not** a `window`
  property. Reference it by name with a `window.App` fallback.
- `renderStudioPanel` builds the panel skeleton once and only re-renders the app
  list; re-rendering the whole panel detaches the iframe and wipes its document.
- Belt buttons carry both a direct click listener and the global `[data-cmd]`
  delegate; the direct listener calls `stopPropagation()` so a press runs once.

## Codebase Manager UI (space, dock, ergonomics)

The Codebase Manager is a split host (`#cb-split-host`) holding the editor
(`#cb-studio-wrap`) and an optional preview dock (`#cb-dock`). All of it is
driven by `App.settings` keys prefixed `cb*`, so it persists with everything else.

- **Space**: `cbHeight` (vh) sets `--cb-studio-h`; the Zen toggle adds `.zen` to
  `#view-codebase` to hide header/chrome/note/app list. `#cb-list` must stay a
  flex column that fills (`flex:1 1 auto;min-height:0`) or the editor collapses
  to its min-height.
- **Dock**: `cbDock` is `right|bottom|float`; the host gets
  `dock-right|dock-bottom|dock-off`. Docked previews sit *beside* the editor —
  never `winOpen`, which is occlusive. `cbRenderPreview()` builds the current
  buffer into the dock and returns `false` for aegis/file/empty so callers fall
  back to the floating window.
- **Ergonomics**: `cbBtnSize/cbIconSize/cbFabSize` and `cbBeltPos/cbBeltLabel`
  are pushed into the studio via `DarkithBridge.setUiPrefs`, which sets CSS
  custom properties (`--belt-btn-size`, `--belt-icon-size`, `--fab`,
  `--belt-lbl-display`) and `data-belt-pos` on the studio body. A vertical belt
  scrolls on the Y axis, so `beltPos()`/`beltAxis()` pick the axis from
  `STATE.beltVertical`; the belt loop must not assume X.
- `cbHeat` draws a fixed reach overlay (`#cb-heat`) with easy/stretch/hard bands
  and an arc that flips with handedness.

## In-app browser (web windows)

A URL open (omni-bar, the `Web` app icon, or `App.resolve('https://…')`) becomes a
floating window of `kind:'url'`. These live in `#wins`, not the old `#viewer`.

- **Most of the web cannot be framed.** Sites set `frame-ancestors` (DuckDuckGo,
  Bing, Google, GitHub, Stack Overflow, MDN, HN…) so the iframe renders a blank
  body. There is no way to detect this from JS: a blocked cross-origin frame fires
  a normal `load`, exposes no `contentDocument` (`SecurityError` on any read), and
  fires no `securitypolicyviolation`. So we do not guess — the window shows a
  persistent note and a `↗` button that hands off to the real browser.
- **Default to a framable engine.** The `Web` app and free-text search use
  Marginalia (`https://search.marginalia.nu/`), which serves no `frame-ancestors`.
  Verified framable too: Wikipedia, Project Gutenberg, `docs.python.org`. Do not
  switch the default back to DuckDuckGo — it will look broken.
- **Every web window has an address bar** (`.win-urlbar` / `.win-url` / `.win-go`).
  Enter or `↵` calls `App.winGo(id)`, which routes the text through the top-level
  `normalizeUrl(text)` → `{scheme,url}` (`web` / `aegis` / `external` / `blocked` /
  `null`). Bare hostnames get `https://`; other phrases become a Marginalia query;
  `javascript:`/`data:` are refused. `normalizeUrl` mirrors the omni-bar rules, so
  keep the two in step. HTML windows hide the bar and the `★` bookmark button.
- **Sandbox**: url frames get `allow-scripts allow-same-origin allow-forms
  allow-popups allow-downloads` plus `referrerpolicy=no-referrer`. HTML windows
  keep the stricter set (see the trusted/untrusted split in the float layer).
- Test hooks: `App.winRemove(w)` tears a window down with no log/haptic side
  effects, so the self-test can mount a window without tripping the suite's
  zero-network and zero-console-error assertions. `winClose` wraps it.

## Verifying

One command runs the whole proof:

```
python3 build/verify.py        # [1/3] sync  [2/3] parity  [3/3] battery
```

- **sync** — `build-forge.py --check` (artifact bytes match the sources) plus
  `sync-delivery.py --check` (delivery copies and every printed size/sha256
  match the files on disk).
- **parity** — the JS core against `savf.py` on the fixture corpus; the verdict,
  phi, rule and line must match exactly.
- **battery** — Chromium/Firefox/WebKit boot all three hosts from `file://`
  with non-`file://` requests blocked. All three must boot with zero page
  errors and zero network.

Cross-engine is not optional: WebKit is what surfaces the Blob/IndexedDB and
`null`-throw differences that Chromium and Firefox hide.

Supporting harnesses live in `delivery/.savf-harness/` (`site_test.py`,
`ui_test.py`, `ui_flow.py`, `ui_utils.py`, `forge_term.py`, `robust.js`).

### Packaging a download

```
python3 build/make-delivery-zip.py     # dl/ archives + dl/index.html
python3 build/make-repo-zip.py         # darkith-forge-repo.zip (GitHub-shaped host)
python3 build/make-bundle-zip.py       # source_fixed.zip + forge-bundle.zip
python3 build/sync-delivery.py         # refresh printed sizes/sha256
```

`make-delivery-zip.py` writes `delivery/dl/darkith-forge-delivery.zip` (whole
project) and `darkith-webapp.zip` (just the two offline apps plus `savf.py`),
then rewrites `delivery/dl/index.html` with the sizes and sha256.

`make-repo-zip.py` rebuilds `delivery/darkith-forge-repo.zip` from the one-shot
payload's `app/` tree (current Kotlin, engine assets, release key/cert, arm64
forge libs) plus the project's current webapps -- the repo's own scaffolding
(README, `.github`, Termux notes) is carried over untouched.

`make-bundle-zip.py` regenerates `darkith_source_fixed.zip` from the payload and
reassembles `darkith-forge-bundle.zip` from the freshest delivery files. It
leaves `c7_patched_sources.zip` alone: that is a frozen alternate patch lineage
(new `GpuScanner.kt`/`IRBuilder.kt`) consumed by `forge_c7_oneshot.sh`, not a
mirror of the payload.

Each script takes `--check` and is wired into `build/verify.py`'s sync stage, so
a stale archive or a printed hash that no longer matches fails the proof. Re-run
the whole set after any change to the apps or the engine, so no archive and no
printed hash ever drifts from the bytes beside it.

## Native bridge (Homekeeper Android host)

The Android host (`HomekeeperBridge.kt`, registered as `window.darkith`) exposes
one APK forge and one stateful shell. Redundant parallels are forbidden: a second
builder that builds no APK is a corruption mode (NT IX §9.4 "delete on sight";
NT X "duplication is a corruption mode"), not a feature.

- `forgeChimera(donorsJson, html, appName, pkgName)` → `"OK:<apkPath>"`.
  The **only** APK builder (`ChimeraBuilder`, driving aapt2/zipalign/apksig).
  The in-app **Build APK** button calls this (`App.apkBuildMethod()` →
  `hasNative('forgeChimera')`). `donorsJson` is `{"permissions":[...]}`.
  The former `forgeNative` alias and the `forgeRenderNative` "floating IR forge"
  (`NativeForgeBuilder`) were **purged**; do not reintroduce them.

### Full-capacitor terminal (drops Termux)

`App.nav('term')` / `aegis://term` opens the Terminal view; `>cmd` in the omni-bar
and `aegis://shell` route there too. `TermKit` drives it. The session is a
*storage capacitor*: `cd` and `export` persist from one command to the next.

- Bridge contract: `shellExec(cmd)` → JSON `{"rc":int,"cwd":str,"out":str}`. The
  Kotlin side keeps `shCwd` / `shEnv` / `shHist` in the `HomekeeperBridge`
  instance, runs each call as one `sh -c` script (`cd <cwd>; <cmd>; print cwd;
  env; exit rc`) and returns the observed `$PWD` and the full environment, so the
  next call inherits them. Helpers: `shellSetCwd`, `shellSetEnv`, `shellEnv`,
  `shellHistory`.
- It runs in the app's **own** userspace — `libbash.so` from `nativeLibraryDir`
  (falling back to `/system/bin/sh`), with `PATH`/`LD_LIBRARY_PATH`/`PREFIX` all
  pointed at `nativeLibraryDir`. No `$PREFIX`, no `com.termux`. This is the NT X
  §4.1–4.4 delta: the toolchain runs from the app, not a borrowed shell.
- In a plain browser (no bridge) `TermKit` emulates `cd`/`export`/`pwd` locally so
  the view stays usable and the self-tests can assert persistence. The old
  stateless `shell(cmd)` is still honoured as a fallback.
- It is a **first-class view** (`#view-term`), never a floating overlay — a
  floating terminal would be exactly the obstruction this repo forbids.

`ProcessBuilder` toolchain calls in `BuildEngine.runProcess` and `ChimeraBuilder.run`
must set `LD_LIBRARY_PATH` to the app's `nativeLibraryDir` **plus** the Termux lib
dir when one is present (`$PREFIX/lib`, default
`/data/data/com.termux/files/usr/lib`), or `libaapt2.so` dies with
`library "libz.so.1" not found` (Android's system libz has no `.1` suffix).

Compile-verify Kotlin offline: download `kotlinc` 1.9.x and an `android.jar`,
then diff the error set against the unpatched tree — the androidx `R` /
API-30+ / `com.android.apksig` errors are expected noise, so a patch is only
clean if it adds **zero** new errors.




## APK forge — the wired native runtime (OMEGA POINT)

`forgeChimera(donorsJson, html, name, pkg)` produces a **real, signed APK whose
content surface is drawn by the hand-rolled engine** — no Jetpack Compose, no
vendor UI toolkit in the artifact.

The forged app's entry is `com.darkith.omega.OmegaHost` (source lives at
`app/src/main/java/com/darkith/omega/OmegaHost.kt`, kept in the host tree so it
compiles; it is also the entry baked into `assets/engine/template.dex`).
OmegaHost builds a `GLSurfaceView` running `OmegaRenderer` (hand-rolled GLES 2.0,
the WebGL-equivalent GPU path) **under** the content plane (the forged
`assets/homekeeper.html` in a WebView), and `NativeOmegaBuilder` drives
`AutophagicAllocator.tick -> MemoryGovernor.reciprocate -> OmegaRenderer.apply`
every 16 ms. `paintThroughEngine()` is the live pure-IR seam:
`TransliaisonEngine().translate(html) -> renderer.applyLayoutNodes(nodes)`.

### The engine assets (`app/src/main/assets/engine/`) — all required, all derivable
| file | what it is | how to derive |
|---|---|---|
| `template.dex` | the runtime, dexed | `d8 --min-api 24` over the core runtime + OmegaHost |
| `AndroidManifest.tpl.xml` | forged-app manifest (`{{PKG_NAME}}`/`{{APP_NAME}}`) | entry = `com.darkith.omega.OmegaHost` |
| `android.jar` | framework resources for `aapt2 -I` | the platform `android.jar` (its `resources.arsc`) |
| `release_key` | **PKCS#8 DER** RSA private key | `openssl pkcs8 -topk8 -nocrypt -outform DER` |
| `release_cert` | **X.509 DER** cert | `openssl req -new -x509 ... -outform DER` |

`ApkSignerRunner` reads `release_key` as `PKCS8EncodedKeySpec` and `release_cert`
as X.509; a PEM or a bare `RSAPrivateKey` DER fails with
`AlgorithmId.parse`. Sign with apksig v1+v2+v3.

### Build chain (mirrors `ChimeraBuilder`)
`aapt2 link -o unaligned.apk -I android.jar --manifest M` → stage `unaligned` +
`assets/homekeeper.html` + `classes.dex` into `staged.apk` → `zipalign -f 4` →
apksig sign. **Signer input is always the aligned apk.**

### Rules learned the hard way
- `ChimeraBuilder.copyAssetsRecursively` must **skip** `engine/` and `src.*` when
  copying the host's assets into a forged app — otherwise it ships
  `engine/release_key` (a private signing key!) and `android.jar` into every APK.
- The forge refuses to ship unless `classes.dex` contains
  `Lcom/darkith/omega/OmegaHost;` and `assets/homekeeper.html` exists (NT X
  closure gate; a stale template.dex must fail loudly, not ship a bare shell).
- `aapt2` needs a framework `android.jar` whose `resources.arsc` defines the
  attributes the manifest uses (`requestLegacyExternalStorage`, `foregroundServiceType`
  are API-29+). An API-28 jar fails: `attribute ... not found`. Use a real
  platform-34 jar.
- The `AutophagicAllocator` control rates are **per second** (`* dt`); test it by
  injecting a simulated clock (`AutophagicAllocator(nanoClock = { t })`) advancing
  16.6 ms per tick, not by spinning a tight loop.
- The host app's `AndroidManifest.xml` is the operator's real one (97
  permissions, `aegis://` VIEW filter, HOME category, `FileProvider`
  `${applicationId}.hkfiles` → `@xml/hk_paths`, plus `core.OmegaActivity`).
  `res/xml/hk_paths.xml` and `res/values/strings.xml` must exist or the link fails.
- The host still contains a **duplicate entry** (`MainActivity` + `DarkithBridge`
  as `darkithNative`) that is not in the manifest — the live entry is
  `HomekeeperActivity` + `HomekeeperBridge` (registered as `window.darkith`).
  That dead duplicate accounts for the residual offline kotlinc errors.

## The one-shot build.sh (NT IX §9.6)

`build.sh` at the repo root is the seven-step forced chain, no Gradle:
`aapt2 compile -> aapt2 link -> kotlinc -> d8 -> zip -> zipalign -> apksigner`.

    bash build.sh [projectDir] [AppName] [pkg.name]

It auto-detects the toolchain (Termux `$PREFIX/bin`, Android build-tools, an R8
jar via `java -cp r8.jar com.android.tools.r8.D8`) and honours `ANDROID_JAR`,
`R8_JAR`, `MIN_SDK`, `OUT`. Anchor checks refuse API 35 (ceiling is 34), refuse a
missing forced leg (zipalign/apksigner), and never sign `base.apk` (the signer's
input is always `aligned.apk`). If `src/` is absent it uses a prebuilt
`classes.dex` (the ChimeraBuilder path). `res/` is optional.

Bash gotcha baked in: expanding an empty array as `"${ARR[@]:-}"` yields one
empty-string argument (aapt2 then fails `failed to open file`). Use
`${ARR[@]+"${ARR[@]}"}` instead.

## Running the build in Termux

Two different builds, two different chains — do not mix them.

* **Host app -> Gradle.** `./gradlew :app:assembleDebug --no-daemon --console=plain
  -x embedSourceSnapshot`. The host imports androidx (appcompat/activity/core) and
  its manifest resolves `androidx.core.content.FileProvider`; a raw kotlinc chain
  cannot resolve those (SPI-5). Gradle is pinned to java-17-openjdk via
  `org.gradle.java.home`, and `android.aapt2FromMavenOverride` points at the
  Termux aapt2. This is the operator's proven one-shot (BUILD SUCCESSFUL ~4m).
* **Standalone, dependency-free APK -> `build.sh`** (NT IX §9.6). No Gradle.

Termux toolchain (verified against the Termux package index):
`aapt2` (16.0.0.4, aarch64), `apksigner` + `d8` (37.0.0, depend on `openjdk-21`),
`kotlin` (2.4.21), `openjdk-17`/`-21`, `python`.
**Termux ships no `zipalign` package.** `build.sh` therefore falls back to the
bundled `zipalign.py` — pure Python, byte-identical output to the reference tool
and passing `zipalign -c`. It aligns STORED entries only by zero-padding the
local extra field, then fixes the central-directory local offsets **and the
EOCD central-directory offset** (forgetting that last one corrupts the archive).

`android.jar` (API 34) must be supplied — `build.sh` looks at
`$ANDROID_JAR`, `<proj>/android.jar`, then `$ANDROID_HOME/platforms/android-34/`.

RAM-lean path: drop a prebuilt `classes.dex` at the project root and do **not**
create `src/`. `build.sh` then skips kotlinc and d8 entirely (only aapt2, align,
sign) — the lightest build for a 4 GB device. The kotlinc step is capped at
`-J-Xmx512m`.

## build.sh — source-root discovery, and the SKIP_ASSETS rule (verified)

`build.sh` probes **both** layouts, so it works on a flat project *and* on a
standard Android tree:

```
manifest:  $PROJ/android/src/main/AndroidManifest.xml -> .../src/main -> $PROJ
sources:   $PROJ/src  ->  $PROJ/java  ->  $PROJ/app/src/main/java
```

Earlier revisions probed only `$PROJ/src`, so a standard `app/src/main/java`
tree died with `ANCHOR: no src/ and no prebuilt classes.dex found` after aapt2
had already run. Fixed.

`SKIP_ASSETS` is **empty by default**. The host app reads `assets/engine/*`
at runtime (`BuildEngine.kt`, `ApkSignerRunner.kt`) to build and sign APKs
on-device, so those files must ship in the *host*. Only when forging a
*shippable* app should you exclude the signing secret:

```
SKIP_ASSETS="engine/release_key engine/android.jar" bash build.sh <proj> <name> <pkg>
```

`android.jar` is excluded alongside the key because it is a link-time library,
not a runtime asset. Do **not** exclude these by default — it breaks on-device
building.

## Native-APK pipeline: which tree compiles with which tool

| tree | tool | why |
|---|---|---|
| host app (`app/src/main/java`, androidx) | Gradle | imports appcompat/activity/core; raw kotlinc cannot resolve them |
| forged runtime (`core/*` + `omega/OmegaHost.kt`) | `build.sh` | androidx-free, plain framework APIs only |

`assets/engine/template.dex` is the dexed runtime:
`kotlinc core/*.kt omega/OmegaHost.kt -> d8 --min-api 24 -> classes.dex`.
It must contain `Lcom/darkith/omega/OmegaHost;` (the NT X closure gate checks
this before signing). Verified: 196,184 bytes, gate passes.

## Delivery invariants (all re-verified end-to-end)

- `darkith-forge.html` — 474,021 B, sha256 `0961a918…42ffc`, opens from `file://`.
- `darkith_source_fixed.zip` — 72 entries, sha256 `369b1ad1…7ebf`; ships the
  runtime-required `assets/engine/*`, host `res/`, real manifest, `build.sh`.
- `darkith-forge-bundle.zip` — sha256 `728124ad…9ebb`; 9 entries incl. savf.html/savf.py.
- `build.sh` — sha256 `9dd16fde…f4c0`; proven on flat, standard, no-res, lean
  (prebuilt dex), secret-exclusion, python-zipalign-fallback, and the runtime
  target. Every APK passes `apksigner` v2+v3 and `zipalign -c 4`.
- `zipalign.py` fallback output is accepted by the reference `zipalign -c`.
- `savf.html` — 92,392 B, sha256 `326e1bfa…7654`; three tabs (Audit / Axis lab /
  Self-test), 9/9 in-browser self-test, verified on Chromium, Firefox and WebKit.
- `savf.py` — 40,583 B, sha256 `36e4dad7…b545` (the reference).

## TermKit 2.0 terminal: bugs found and fixed (do not regress)

The terminal lives in `delivery/termkit.bundle.js` and is embedded into
`darkith-forge.html` between the markers `/* ===== TermKit 2.0 — real userspace
shell` and `/* Single live terminal bound to the DOM`. It is **not** a file
parser in the SAVF sense: it is a real userspace shell over a virtual FS.

Five real defects were found by driving the UI and the `runSilent` API, then
fixed. All five now have regression tests inside the engine's own `selftest()`
(now 32 checks, was 25):

1. **`read` never consumed stdin.** `ctxStdin()` returned the whole buffer and
   `read` only ever took `split("\n")[0]`. So `while read L; do ...; done < f`
   never reached EOF and spun until the loop's 100000-iteration guard — 100k
   duplicate lines, a hang from the user's point of view. `read` now slices the
   consumed line off `currentStdin` and returns 1 at EOF.
2. **`cat` with no file operands returned immediately** instead of reading
   stdin, so `cat < f` and `cmd | cat` printed nothing.
3. **`base64` ignored file operands** (`base64 f` printed a blank line).
4. **`tr` ignored file operands** (`tr a-z A-Z f` printed nothing).
5. **Redirections after a compound command were silently dropped.**
   `parseSimple` collected `<`/`>`/`>>`, but `parseCommand` returned `if`/`for`/
   `while`/`case`/subshell/function nodes without them. `done < file` therefore
   parsed as a plain `done`, so the loop read the *outer* stdin (or empty) and
   either did nothing or hung. Fixed by splitting `parseCommand` into a wrapper
   that attaches trailing redirections to any command node plus
   `parseCommandInner`, and by adding `execRedir(node)` which applies `<`
   stdin and `>`/`>>` capture around any node.

`cat`/`base64`/`tr` now share `readInputs(cmd, files)` for operand handling.

**Delivery sync rule (this bit us):** `darkith-forge.html` is generated by
`embed_termkit.py` and must then be copied into *five* places or the tree ships
a stale build: `darkith forge.html`, `darkith home forge.html`,
`delivery/darkith-forge.html`, `darkith-forge-bundle.zip`,
`darkith-forge-repo.zip` (`webapp/` **and** `app/src/main/assets/homekeeper.html`)
and `darkith_source_fixed.zip` (`app/src/main/assets/homekeeper.html`). Sizes and
sha256 in `README.txt`, `index.html` and `PROGRESS-LEDGER.md` must be regenerated
from the files on disk. Before this session the zips carried a 488,110-byte forge
and a 92,392-byte savf while the tree held 605,533 / 359,396 — i.e. every bundle
shipped a webapp without TermKit 2.0.

## SAVF-1: fidelity rules learned (do not regress)

* The axis law is `start(tau) + tau*s*(P1-P0)` — the direction vector is always
  `P1-P0`, *not* `end-start`. Using `end-start` breaks `at(s,+1)==at(1-s,-1)` and
  the `(P0+P1)/2` midpoint identity. The in-browser self-test catches this.
* Any regex embedded in a **double-quoted** JS string needs `\\s` (the file is
  read literally, so over-escaped `\\s` inside a `new RegExp` string silently
  matches a backslash). Prefer a regex literal for a fixed pattern.
* Numeric facts must be compared **numerically with a tolerance**, never as
  strings ("55.8450" vs "55.845" is the same fact).
* Implicit multiplication must not split scientific notation: a digit followed by
  `e`/`E` and an exponent stays one number (`1e3`, `2e-4`, `1.5e2`).
* A circular derivation is **unresolvable -> BLOCKED**, not failed/LIED.
* Rendered result rows must show the true source line number, not `idx+1`.
* Error ordering must be **single-pass and lazy**: CPython tokenizes on demand, so
  the earliest fault wins by position. An early grammar error beats a later bad
  byte; an unterminated string on line 4 beats a missing indented block on line 2.
  The parser therefore pulls tokens lazily (`PyLex.tokenize(src,{resumable:true})`
  returns `{toks,error,tokIndex}`) and raises the lexical fault only once it asks
  for a token at or past `tokIndex`. Tokenizing eagerly for the scanner reorders
  every multi-fault file — never do it.
* A dedent must land exactly on an enclosing indent level; otherwise CPython
  raises `unindent does not match any outer indentation level` at that line.
  Silently popping to zero accepts files CPython rejects.
* A missing indented block is reported as `expected an indented block after 'X'
  statement on line N`, where N is the **statement's** line, but the error's own
  `lineno` is the line where the block was expected (the next real token, or the
  last blank line when the file ends). `def`/`class` use `function definition` /
  `class definition` instead of a quoted keyword.
* The scanner must take tokens from the same lexer run that produced the tree
  (`PyAst.parseWithTokens`), including COMMENT tokens; filtering them out first
  silently drops every MARKER finding.

Cross-validation harness (offline, headless) lives in `/tmp/savftest/`:
`crossval.py` (300 random axes vs savf.py), `crossval2.py` (exp/log, chart_sign,
handedness), `selftest.py`, `crossbrowser.py`, `responsive.py`, `offline.py`.

## Android host app: build.sh vs Gradle (hard-won, verified)

The host app (`app/src/main/java`, 53 `.kt`) **cannot** be built by `build.sh`.
Proven by running it: `aapt2 compile` and `aapt2 link` both **pass**, then
`kotlinc` dies with ~50 `unresolved reference` errors (`android`, `appcompat`,
`core`, `activity`, `ApkSigner`, `ActivityCompat`, `AppCompatActivity`).

Why `aapt2 link` passes at all: `app/src/main/res/values/themes.xml` **defines**
`Theme.AppCompat.NoActionBar` locally (parent `@android:style/Theme.DeviceDefault.NoActionBar`).
So the theme is a resource lookup, not an androidx dependency. The real blocker is
the Kotlin/Java *classpath*: `build.sh` only knows `android.jar`, which has no
androidx classes. Hence the user's `resource style/Theme.AppCompat.NoActionBar not
found` (older tree, no `themes.xml`) and my `unresolved reference` (newer tree,
`themes.xml` present) are the *same* root cause seen at two different legs.

Rule: **host app -> Gradle. Dependency-free forged APK -> build.sh.** Do not
"fix" build.sh to resolve androidx; that is reimplementing a dependency resolver.

### Two defects that actually blocked the Gradle build

1. `app/build.gradle` declares `implementation files('libs/apksig-8.5.2.jar')` but
   the jar was **never shipped** -> `Could not resolve all files for
   configuration ':app:debugCompileClasspath'`. Fixed by adding the official
   artifact (`com.android.tools.build:apksig:8.5.2`, 496,313 B). Do **not** use
   `build-tools/lib/apksigner.jar` as a drop-in: it is signed/repacked and
   Jetifier rejects it with `only DEFLATED entries can have EXT descriptor`.
2. `BuildEngine.kt:91-92` used `nativeDir.absolutePath`, but `nativeDir` is a
   `String` (`applicationInfo.nativeLibraryDir`), not a `File`. Fixed to bare
   `nativeDir`.

Also had to supply what the zip lacked: `gradlew`, `gradlew.bat`,
`gradle/wrapper/gradle-wrapper.{jar,properties}`, and `app/proguard-rules.pro`
(referenced by the `release` build type).

### Toolchain facts for reproducing this build

* AGP 8.2.0 + Kotlin 1.9.20 + Gradle **8.7** + JDK **17** -> works.
  Debian 13 has **no** `openjdk-17` package (only 21); fetch Temurin 17 from
  `api.adoptium.net/v3/binary/latest/17/ga/linux/x64/jdk/hotspot/normal/eclipse`.
  Gradle 8.7 supports JDK 21 too, but `gradle.properties` pins JDK 17.
* `gradle.properties` pins Termux paths
  (`org.gradle.java.home=/data/data/com.termux/files/usr/lib/jvm/java-17-openjdk`,
  `android.aapt2FromMavenOverride=…/bin/aapt2`). On any other machine those must
  be overridden or Gradle stops with `Java home supplied is invalid`.
* Build command: `./gradlew :app:assembleDebug --no-daemon --console=plain -x embedSourceSnapshot`
  (skip `embedSourceSnapshot` or it re-zips `assets/src.zip` recursively).
* The build is **deterministic**: three independent runs produced a byte-identical
  APK, sha256 `229278d9dc7b58a05f260cf37773135761dbebb117e174bb350b3fee7b67a876`.
* SDK root needs `platforms/android-34` + `build-tools/34.0.0` + an
  `licenses/android-sdk-license` file, or Gradle refuses to configure.

## PACKAGING RULE: never ship a build directory (this broke a delivery)

The first `darkith_source_fixed.zip` I shipped contained
`org.gradle.java.home=/tmp/jdk17` and
`android.aapt2FromMavenOverride=/tmp/sdk/build-tools/34.0.0/aapt2` -- my own VM
paths. On the user's device Gradle aborted with
`Value '/tmp/jdk17' given for org.gradle.java.home Gradle property is invalid`.
Cause: I zipped `/tmp/gp2` (the directory I had just *built in*) instead of the
clean source tree. The build directory had been `sed`-patched for my VM, so the
VM paths travelled into the delivery. The README even told the user to edit that
line, which papered over my own defect instead of fixing it.

Rules:
* Package from a dedicated **clean source tree** (`/tmp/canon`), never from a
  directory that has been built in or had paths patched for the local machine.
* Before zipping, assert the archive has **no local-only paths**:
  `python3 -c "import zipfile;assert b'/tmp/' not in zipfile.ZipFile(z).read('gradle.properties')"`
* After any edit to a bundled file, **rebuild the bundle and re-sync the hashes
  in `index.html`**. I edited README.txt after building the bundle and the inner
  hash silently went stale.
* Verify the *served* bytes, not just the local file: compare
  `curl -s <public-url>/<file> | sha256sum` against the on-disk hash.

`termux-import.sh` now defends against this class of failure: before building it
checks that `org.gradle.java.home` and `android.aapt2FromMavenOverride` exist on
the current device and repoints or deletes them if not, resolves a JDK from
`$PREFIX/lib/jvm/java-17-openjdk` / `$PREFIX/opt/openjdk` / `$JAVA_HOME` / PATH,
resolves an SDK from `ANDROID_HOME` / `ANDROID_SDK_ROOT` / `~/Android/Sdk` /
`$PREFIX/opt/android-sdk`, and refuses before building when no JDK exists.
Verified end-to-end in a simulated Termux prefix: build succeeded and produced
the same deterministic APK sha256 `229278d9…a876`.

## forge_new_bundle.sh: five defects found by RUNNING it (not reading it)

The happy path works (BUILD SUCCESSFUL, deterministic APK `229278d9…a876`), which
is exactly why reading it is not enough. The defects only appear on the paths you
actually need: the failure paths.

1. **`wait $BUILD_PID` under `set -e` swallowed every failure report.** The script
   does `trap - INT TERM ERR` then `wait $BUILD_PID; RC=$?`. When the child fails,
   `wait` returns non-zero, `set -e` kills the shell *on that line*, and the whole
   `=== BUILD FAILED … grep -E '^e: '` block is dead code. Proven: injected a
   Kotlin syntax error -> exit 1, zero `e:` lines, no log path printed. The same
   bug hid the memory-watchdog's `DEFICIT:` message (exit 137, message never seen).
   Fix: `RC=0; wait "$BUILD_PID" || RC=$?` — the `||` makes it a tested command.
   Rule: after `wait` on a child, ALWAYS `|| RC=$?` when `set -e` is active.

2. **No `chmod +x gradlew` after unzip.** unzip honours the zip's mode *only when
   the entry carries one*. A zip written without `external_attr` extracts as
   `-rw-------` and the build dies with `./gradlew: Permission denied` — which
   defect 1 then rendered silent (exit 126, no output). Always chmod.

3. **The old tree was destroyed before it was backed up.** `rm -rf ~/darkith-project`
   ran at step 1; `cp -p gradle.properties "$BK/"` ran at step 2 — after the nuke,
   and only one file. The backup directory held exactly 1 file. A failed patch
   therefore left no way back. Back up the whole tree first.

4. **`die()` printed "[FATAL] Patch failed."** — it delegated to `rollback()`,
   discarding the real reason passed in `$2`. Every fatal path reported the same
   useless text.

5. **No `local.properties` / `sdk.dir`.** The build relied entirely on
   `ANDROID_HOME` being exported in the shell. Fine here, fragile on a device
   where the SDK is at `$PREFIX/opt/android-sdk` and nothing is exported.

Corrected script: `delivery/forge_new_bundle_fixed.sh` (served, sha256 `764889aa…`).
Verified: success path (BUILD SUCCESSFUL, APK 8,500,430 B, sha256 `229278d9…a876`),
failure path (prints real `e:` errors + log path, exit 1), watchdog path (prints
`DEFICIT:` line), and full-tree backup (451 files vs the original's 1).

Method note: I ran this in a faithful Termux layout — `/data/data/com.termux/files/usr`
prefix, real `unzip`, real `bash -n`, actual Gradle build — rather than reasoning
about the script. Every defect above was reproduced before it was fixed.

## "libaapt2.so missing" — why staging one file cannot work

The app reads `$nativeLibraryDir/libaapt2.so`. That dir is filled by Android
**only** from the APK's `lib/<abi>/` folder. The delivered APK had **zero**
`lib/` entries (verified), so nothing was extracted — the error is real, not a
stale cache. So `jniLibs` + rebuild is the right *shape*.

But the fix as shipped could never work, for four measured reasons:

1. **The app greps for a filename Termux never installs.** Termux ships
   `$PREFIX/bin/aapt2` (and `zipalign` does not exist as a Termux package at
   all — `android-tools` ships adb/fastboot, not zipalign). The script's
   `find "$PREFIX" -name libaapt2.so` matches nothing on any real device.
2. **aapt2 is not one file.** The real Termux aarch64 `aapt2` (v16.0.0.4-4)
   has these DT_NEEDED:
   `libfmt.so libz.so.1 libpng16.so libexpat.so.1 libprotobuf.so
    libabsl_log_internal_message.so libabsl_hash.so libc++_shared.so …`
   Full closure = **54 files / ~10.2 MB** (51 libs + the binary), dominated by
   abseil-cpp (~1.9 MB), libprotobuf (~3 MB), libc++_shared (~1.4 MB).
   `ldd`-style resolution fails without all of them.
3. **Two sonames are dotted, and Android refuses to extract them.** The
   packaging rule only unpacks entries matching `lib*.so`. `libz.so.1` and
   `libexpat.so.1` are referenced by `aapt2`, `libpng16.so`, `libprotobuf.so`
   and would never land on disk. They must be renamed **and** every referring
   ELF patched with `patchelf --replace-needed`.
4. **The patch step dies before building.** Step 5 does
   `old = '        private val aapt2 = ...'` (8 spaces) but BuildEngine.kt:13
   has **4** spaces, so `sys.exit("FATAL: BuildEngine aapt2 anchor missing")`
   fires and `|| rollback` aborts. No build happens at all.

Also: the script's own `wait $BUILD_PID; RC=$?` after `trap - INT TERM ERR`
still swallows failures (same bug as forge_new_bundle.sh) — see the rule above.

And the deeper issue: patching the app to call Termux's `aapt2` at
`/data/data/com.termux/files/usr/bin` cannot work on a modern Android either.
That path is inside Termux's private data dir, unreadable to another app's uid,
and Termux's `aapt2` is a Bionic ELF (interpreter `/system/bin/linker64`) that
needs those 51 libs on `LD_LIBRARY_PATH` from a dir the app can actually read.

### Working fix: `delivery/darkith-jnilibs-arm64.zip` (3.85 MB, sha256 caf161f3…)
54 files under `jniLibs/arm64-v8a/`, built by resolving the real aapt2 closure
from the Termux repo, renaming dotted sonames to `lib*.so`, and patching all
referrers. Verified: **every DT_NEEDED resolves to a payload file or a known
Android system lib (0 unresolved)**. Installer: `delivery/forge_native_fix.sh`.

### v1 payload bug (found by RUNNING on device) + v2 fix

`!!!!.txt` is the device log. `forge_native_fix.sh` v1 failed at step 2:

    chmod: cannot access 'app/src/main/jniLibs/arm64-v8a/*.so': No such file or directory

**Cause (my bug):** the payload zip stored entries as `jniLibs/arm64-v8a/x.so`,
but the installer ran `unzip -o "$ZIP" -d app/src/main/jniLibs/arm64-v8a`, so
files landed at `.../jniLibs/arm64-v8a/jniLibs/arm64-v8a/x.so` — one level too
deep. The `chmod` glob then matched nothing. Rollback fired (correctly) and the
tree was restored.

**Fix:** payload entries are now FLAT (`x.so`), so `unzip -d <dir>` lands them
directly in `<dir>`. The installer also flattens defensively if it sees a
nested `jniLibs/` dir, so either payload shape now works.

### The 54-file approach was the wrong shape entirely

Two independent defects in the dynamically-linked set:

1. `libz.so.1` / `libexpat.so.1` are **dotted** sonames. Android's packager only
   unpacks entries matching `lib*.so`, so they would never reach disk even after
   renaming + `patchelf` — and renaming requires patching every referrer.
2. **Termux has no `zipalign` package at all** (`android-tools` ships adb/fastboot/
   mke2fs/etc; the user's own `ls` shows `zipalign` came from elsewhere). The app
   hard-requires `libzipalign.so` (ChimeraBuilder.kt:29,31,90), so a 54-file
   aapt2-only payload could never satisfy it.

**v2 ships TWO fully-static AArch64 binaries** from
`github.com/lzhiyong/android-sdk-tools` (release 35.0.2,
`android-sdk-tools-static-aarch64.zip`):

| file            | size      | DT_NEEDED | interpreter |
|-----------------|-----------|-----------|-------------|
| `libaapt2.so`   | 6,477,984 | **0**     | **none**    |
| `libzipalign.so`|   833,640 | **0**     | **none**    |

No companion libs, no dotted sonames, nothing to patch — the whole class of
problem disappears. Verified by execution: `aapt2 compile` + `aapt2 link`
produced a valid `base.apk` (1,551 B) from the app's real
`AndroidManifest.tpl.xml` + `android.jar`; `zipalign -f 4` produced
`aligned.apk` and `zipalign -c -v 4` reported **Verification successful**.
(`libapksigner.so` is NOT needed: signing is `com.android.apksig.ApkSigner`
from `libs/apksig-8.5.2.jar` — pure Java.)

Payload: `delivery/darkith-native-arm64.zip` — 2,666,666 B,
sha256 `49bf42af87baced576f96084dc24e95cee3f59b782b7accab9e42be7e5627079`.
Installer: `delivery/forge_native_fix.sh` v2, sha256 `b0e9045325d49a26…`.

## ANVIL protocol + press release (delivery/)

Two documents derived from this project's executed defects, not from theory.

- `delivery/PRESS-RELEASE.md` (6,511 B, sha256 fc8c3f921c0ee2e0…)
- `delivery/AGENTS-SKILLS-PROTOCOL.md` (13,026 B, sha256 ca19490c0342e51e…)
  codename **ANVIL** v1.0, spec id `ADP/1`. Name was verified unused elsewhere in
  the tree before adopting it (existing codenames: omega, aegis, chimera, savf,
  homekeeper, autoglobal, transliaison).

ANVIL's spine: six prime directives, five laws, evidence grades E0–E4
(asserted → located → executed → reproduced → shipped-and-verified), a claim
ledger that must contain an E0 row for whatever was not run, a defect record
shape, and the **return rule**: a failure found at verification returns the
agent to *reproduce*, never to *repair*. Includes a register of 10 traps
(T1–T10) each traceable to a real failure in this project — T1 the dead-code
diagnostics block, T6 the nested payload, T8 dotted sonames, T9 the zipalign
assumption.

The decisive lesson recorded in both: prefer a **class fix** (2 static binaries)
over a **case fix** (patch the 54-file dynamic graph's dotted sonames).

Both docs are linked from `delivery/index.html`. Every size/hash cited in them
was re-verified against the shipped bytes.

## CORRECTION — the real subject of this project (2026-11-14)

**My earlier artifacts were wrong in emphasis, not just in detail.** I produced a
press release about my own bug fix (the payload nesting defect) and an invented
protocol ("ANVIL"). Both were rewritten.

**The actual work**, in `NT 7.txt`, `NT 8.txt`, `NT IX.txt`, `NT X.txt`,
`nt xi.txt` (Noveltreatises VII–XI), `OmegaHost.kt`, `savf.py`:

- **NT VIII — Bond Formation Number**: `B = (W_A/W_coh)(alpha_inf/alpha_gel)eta >= 1`.
  Verified: `alpha_gel = 1/(f_avg-1)` makes the stated band [0.17,0.80] the image
  of f_avg in [2.25,6]; the critical band [1/3,1/2] reproduces at f=4,3; **the
  constant 1 is forced** (product of three sub-unity ratios reaches 1 only as all
  approach it). Reduces to Dahlquist for PSA.
- **NT IX — Triadic Resolver**: `r = ln x - n ln b`, three repair legs. Verified
  across 200,000 random triples: r=0 iff x=b^n, 0 failures. Anchor {0,1} makes
  b=1 REFUSE the log leg -> detects wrong frame.
- **NT X — Autophagic Allocator**: Lyapunov `V_k` verified monotonically
  decreasing over 200 ticks. Hardware truth 3.66 GB usable, Dalvik 512 MB ->
  safe heap 307 MB (matches). PID governor stays in [65536, 524288].
- **NT XI — ASE**: `lim E/W_in -> 0`, `W_in - E = S != 0`.

**The author's own method is the protocol** — `NT VIII PART ONE, THE ONE RULE`:
"Show the path. Log the instant. Carry the citation verbatim." Three questions
(Source / Transformation / Falsifier), with status flags RESOLVED / EXPOSABLE /
INFERRED. `delivery/AGENTS-SKILLS-PROTOCOL.md` is now `SDP/1`, **extracted from
those documents with verbatim citation**, not invented. 15/15 quotations verified.

**Critical discipline for future sessions:** verifying a claim is *internally
consistent* (G-Transformation) is NOT verifying it is *physically true*
(G-Falsifier). The B>=1 physical prediction needs a lab; it is the author's own
named falsifier and remains unrun. Never upgrade EXPOSABLE -> RESOLVED, never
present INFERRED as established. Do not substitute tooling activity for
examination of the invariant.

## Five POSIX scripts (delivery/scripts/) — all bugs found by RUNNING

`dh-hash-ledger.sh`, `dh-atomic-deploy.sh`, `dh-guard-run.sh`,
`dh-sweep-scan.sh`, `dh-sovereign-init.sh`. Written for `/system/bin/sh`
(Android mksh/toybox), validated under `dash` (strict POSIX), not just bash.

**Every bug below was found by executing, not reading.** All fixed and
regression-tested; 7/7 cases pass with 0 stray processes and 0 temp leakage.

1. **`{bin,logs,...}` brace expansion is a BASH EXTENSION.** Under `dash`,
   `mkdir -p "$WS"/{bin,logs,tmp}` creates ONE literal directory named
   `{bin,logs,tmp}`. Symptom was `cannot create .../state/env.sh: Directory
   nonexistent`. Fix: explicit `for d in ...; do mkdir -p; done`. **Any brace
   expansion in a `/system/bin/sh` script is a latent failure.**
2. **`set -e` + a probe function that returns 1 on an absent optional tool**
   killed `dh-sovereign-init.sh` before it wrote the env file. An absent *soft*
   capability is a finding, not a failure. Fix: probe always `return 0`.
3. **`stat -c '%s\t%Y\t%n'` does NOT interpret `\t`** — GNU stat emits a literal
   backslash-t, so awk saw one field and `$3` was empty (`NEW 6` with no path).
   `find -printf '\t'` only works on GNU find. Fix: build a literal tab with
   `TAB=$(printf '\t')` and use it in both branches.
4. **The scan state file was inside the scanned root**, so it counted itself
   (53 files for a 52-file tree). Fix: `! -path "${STATE}*"`.
5. **`cmd & PID=$!` gives the immediate child only.** Killing it orphans the real
   work — verified: killing the `sh -c 'sleep 60'` wrapper left `sleep 60` ALIVE.
   A timed-out build would keep running, invisible, holding RAM. Fix: recursive
   `kill_tree()` over `ps -eo pid= -o ppid=`, with `setsid` to detach the tree
   when available.
6. **A script ending on a bare test leaks its exit status.** `dh-atomic-deploy.sh`
   printed "deployed" then exited **1** on a first deploy, because the last
   command was `[ -d "$OLD" ] && ...`. Any caller using `&&` would abort after a
   successful deploy. Fix: explicit `exit 0`. Same hardening applied to
   `dh-sweep-scan.sh` (ended on `rm -f`).

**Benchmark (substantiated, not asserted):** scanning 2000 files —
naive `find | while read; do stat; done` = **2.935 s**; `dh-sweep-scan.sh`
single traversal + one awk pass = **0.015 s** (~195x). The rationale in the
script header is measured, not claimed.

## F2 — THE RENDERER WAS NEVER WIRED (found by reading the tree, not render.md)

`render.md` is a transcript of an agent repeatedly writing renderer code that bypassed
`AutophagicAllocator`/`MemoryGovernor`. The real defect was simpler and was NOT in that
transcript. Found by extracting the actual tree from `darkith_source_fixed.zip` and reading it.

**Defect 1 (the missing wire).** `HomekeeperBridge.forgeRenderNative()` built
`val renderer = OmegaRenderer()` and handed it to `NativeForgeBuilder`. An `OmegaRenderer`
constructed this way is attached to no `GLSurfaceView`, so no GL thread ever calls its
`onDrawFrame()`. The forged IR was applied to a renderer that never draws. The *live* renderer
is the one in `OmegaHost`/`OmegaActivity` handed to `glView.setRenderer(...)` and ticked by
`NativeOmegaBuilder`. Two renderers existed; the IR went to the dead one.

**Defect 2 (open feedback loop).** `NativeOmegaBuilder` fed the allocator
`renderer.trackedBytes`, which is only `FBO + grid`. The forged document's bytes were never in
it. The PID loop was blind to the thing it was supposed to be budgeting for. Measured effect:
with IR bytes included, the 40-tick budget falls 332634 -> 320824.

### The fix (5 files, compile-verified, zero new errors)
- `OmegaRenderer`: `companion object { live / registerLive() }`; `onSurfaceCreated` publishes
  `this`; `applyLayoutNodes` costs a real 112 B/node (4 verts x 7 floats x 4 B); new
  `totalGlBytes`; new `buildIrGeometry`/`drawIr`/`flatten`/`quad` + `IR_VS`/`IR_FS`; the
  `onDrawFrame` build is capped by `lastAllocatorVertexBudget`.
- `NativeOmegaBuilder`: feeds `renderer.totalGlBytes` instead of `trackedBytes`.
- `HomekeeperBridge.forgeRenderNative`: reads `OmegaRenderer.live`, returns
  `"DEFICIT: no live GL surface. Open the Omega screen first."` when absent. No phantom renderer.
- `OmegaHost` + `OmegaActivity`: `registerLive(renderer)` on create, `registerLive(null)` on pause.

### How it was verified (not inferred)
- **JDK 21 + kotlinc 2.0.21 + Android platform jar** installed to actually compile the tree.
- Core package compiles with **0 errors**; full tree's 102 errors are all pre-existing
  `MainActivity.kt` androidx transitive noise, byte-identical to baseline (diff of error sets = empty).
- **The operator's real allocator was executed** (unmodified `.kt`): under collapse
  `gpuConcurrency` 6->1, `resolutionScale` 1.0->0.974, `memoryResidual` -> negative.
- **Coupling test, 5 groups, all PASS**: geometry capped at every node count (10 M nodes -> 9360
  verts under a 65536 budget); invariant grid<=budget holds over a 200-tick sweep; feedback closed
  (T3); collapse response (T4); governor caps the renderer (T5).
- **Shaders validated** with `glslangValidator`: all 6 valid (my `IR_VS`/`IR_FS` included).
- Removed a dead `irVerts` field that duplicated the geometry on the Java heap — real waste on 4 GB.

### Status flags (One Rule)
- RESOLVED: phantom renderer; open feedback loop; geometry cap; compile-clean; control law responds.
- EXPOSABLE: on-device pixels. The GL calls run on hardware I do not have; `file://` + real GPU
  render is the falsifier. Nothing here claims a frame was seen.
- INFERRED (do NOT trust, no evidence in tree): every Mali-G52/Bifrost/MSAA/Vulkan driver claim in
  `render.md`. `grep` for g52|mali|bifrost|msaa|vulkan over the tree returns **zero** hits. Those
  constants are not in the source and were deliberately NOT hardcoded.

---

## WINDOW MANAGER: MINIS FLOAT, AND THE PRE-RUNNER RENDERS

Verified in a real headless Chromium against `darkith home forge.html` loaded from
`file://` with the network hard-blocked. Every claim below is an executed assertion,
not an inference. 94/94 assertions pass across five suites.

### The defects that were real

1. `.win.min{display:none}` — minimizing a window *deleted* it from the screen. It could
   still be restored from the task strip, but nothing was left floating over the app.
2. `#wins` sat at `z-index:36`, below the app's own sheets (`#vault` 60, `#logs` 62,
   `#perm` 62). A window could never float over other active UI layers.
3. `winMin()` added the `min` class by hand and never called `winLayout()`, so a mini
   kept its full-size inline geometry.
4. `winTopVisible()` filtered out minis, so back-button minimize ignored them.
5. Code-manager previews rendered into the non-occlusive dock only. There was no
   floating pre-runner at all.
6. `cbDockRender('html', …)` never removed a previous `src`, so after a URL preview the
   frame stayed bound to the old document.
7. `buzz()` called `navigator.vibrate()` before any user gesture. Chrome logs a console
   intervention error on boot; that was the only console noise in the app.

### The fix

- A minimized window is now a **floating mini**: a 172px card that keeps its iframe
  mounted, parks above the task strip, and can be dragged anywhere in the viewport. It is
  never `display:none`.
- Minis sit on their own z-band (`9000+`), so they float above every regular window, and
  `#wins` moved to `z-index:64` so a window floats above the app's sheets.
- Tapping a mini (never one of its buttons) restores it. The mini body is
  `pointer-events:none` so the iframe cannot swallow that tap.
- `winMiniBounds()`/`winMiniMetrics()` measure the window's own mini width and real height,
  so nothing parks off-screen. The existing `resize` handler re-flows them on rotation.
- **The pre-runner**: every preview tap renders into a keyed, minified floating window
  (`key:'prerunner'`) parked bottom-right, picture-in-picture style. Repeated taps refresh
  the *same* mini in place instead of stacking duplicates. Toggle in Settings → Forge UI →
  Preview dock (`cbPrerunner`, default on).
- `buzz()` is gated on first user activation and never throws.

### Evidence

Suites live in `/tmp/verify`: `verify.py` (28), `browser_test.py` (12), `smoke.py` (33),
`reflow.py` (11), `offline.py` (10). The app's own self-test reports 49/49. Zero page
errors and zero console errors on phone, tablet and desktop viewports, online and offline.

Delivery copies `darkith forge.html` and `delivery/darkith-forge.html` were byte-identical
to the pre-fix build; both are now synced to the verified artifact
sha256 `fa61d9b2b61d03d1f00987dd77bed3d6a4b91693a448585de14bd04d2bc0dd9a`.

### Scope note

`homeforge.html` is an older v5.3.1 variant and shares defects 1 and 2. It is not a
referenced deliverable (not in `delivery/README.txt`), so it was left untouched.
`savf.py`/`savf.html` were audited in a browser too (demo → PASS, self-test 9/9, no
errors, 200 claims in 3ms) and then dropped from scope as superseded.

---

## APK / GPU RUNTIME: WHAT IS REAL, WHAT IS A SEAM

Audited by extracting the bundle, re-parsing the APK, and recompiling and RUNNING the
Kotlin controllers with a real Kotlin 2.0.21 compiler. No claim below is inferred.

### Real and proven by execution

- `delivery/darkith-forged-proof.apk` is a genuine APK: package
  `com.darkith.shim.omegaproof`, launcher `com.darkith.omega.OmegaHost`, minSdk 24 /
  targetSdk 34, signed v1+v2+v3, cert CN=Darkith Release. Its `classes.dex` carries
  OmegaHost, AutophagicAllocator, MemoryGovernor, OmegaRenderer, NativeOmegaBuilder
  and TransliaisonEngine; androidx and compose symbol counts are 0.
- `AutophagicAllocator` and `MemoryGovernor` compile clean and pass 13/13 behavioural
  checks on a simulated 60 Hz clock: steady state holds scale 1.0; sustained
  over-budget cuts scale to its 0.5 floor; scale recovers to 1.0 on release; 16.67 ms
  is inside the deadband; 33 ms frames cut scale; NaN/negative/overflow inputs are
  clamped with no crash and no starvation; V moves down promptly after the switch.

### Bug found by running it

`MemoryGovernor.reciprocate` computed `r + m` on two Longs. With absurd reported byte
counts the sum overflows to NEGATIVE, which makes `systemPressure` negative and
`selfOomSafe` wrongly true. Replaced with a saturating add. The fix is folded into
`delivery/darkith_source_fixed.zip`.

### NOT implemented — do not repeat these as fact

- **The GPU leg is now wired (C7 patch) — see the C7 section below.** As shipped
  before that patch, `OmegaRenderer.applyLayoutNodes` only stored the node count and
  generated no geometry, and the pure-IR path was unreachable. That is fixed: the IR
  path now builds real quads bounded by the allocator budget and draws them. What is
  STILL not true is glyph text rendering (text is a placeholder bar) and any claim of
  having run on a real device/GPU.
- This is GLES 2.0 with Java-side direct `ByteBuffer`s. There is no JNI, no native C++,
  and no `malloc`. It is not a "direct native GPU auto-MeMallocated" path.
- Nothing has run on a real Android device or GPU. No install, no launch, no frame was
  observed. "Flawless rendering" is unfalsifiable from this environment.
- `app/src/main/assets/engine/android.jar` is a **2-entry resources-only** jar
  (`resources.arsc` + `AndroidManifest.xml`, 4.2 MB). It has no `android/**/*.class`
  at all, so it can serve `aapt2 -I` for resources but can never compile against.
  Re-dexing the runtime into `template.dex` is therefore not reproducible from this
  bundle; the bundled `template.dex` is the only artifact of that step.
- README section 2 cites "each one reproduced by AllocatorTest". No file named
  AllocatorTest exists in the bundle.

### Delivery bundle hygiene

README quoted stale hashes/sizes for `darkith-forge.html` and
`darkith_source_fixed.zip`; both are corrected to the files actually shipped, and a
"VERIFICATION ADDENDUM" section now separates proven from unproven claims. All six
quoted hashes in `delivery/README.txt` were re-checked against the real files and match.


## APK "Build APK" defect (found on device, fixed)

The host APK must contain its native build tools, or the in-app builder cannot run:

- `ChimeraBuilder.kt` / `BuildEngine.kt` resolve `libaapt2.so` and `libzipalign.so`
  from `context.applicationInfo.nativeLibraryDir`.
- Android only extracts `lib*.so` from `lib/<abi>/` entries at install time.
- The original APK had **no `lib/` entries at all**, so `nativeLibraryDir` was empty
  and "Build APK" threw `ToolFailure("libaapt2.so missing in ...")` immediately.

Fix: embed `lib/arm64-v8a/libaapt2.so` (6,477,984 B) and
`lib/arm64-v8a/libzipalign.so` (833,640 B) as **stored** (uncompressed) entries
(required for `extractNativeLibs=true`), then re-align and sign v1+v2+v3.

Both binaries are static AArch64 (0 `DT_NEEDED`, no `PT_INTERP`) and were executed
under qemu-aarch64 emulation: `aapt2 version` -> `Android Asset Packaging Tool
(aapt) 2.19-`. The full pipeline (aapt2 link -> stage -> zipalign -> sign) was
reproduced and the forged APK verified. When rebuilding this APK, do NOT drop the
`lib/` entries.

## C7 — THE IR PATH IS NOW WIRED (verified without a device)

The pre-C7 state, recorded above, was a wiring seam: `applyLayoutNodes` stored a count
and drew nothing, and `NativeForgeBuilder` built a phantom `OmegaRenderer` that was
never on screen. C7 closes that seam. Patched files (all compile clean against a real
android-34 `android.jar`, kotlinc 2.0.21, 0 errors in the core package):

- `core/GpuScanner.kt` (new) — queries GL limits once (called from `onSurfaceCreated`,
  so a context exists) and yields a hard byte ceiling. GLES only; Vulkan is a crash
  path on this device and is deliberately not used.
- `core/IRBuilder.kt` (new) — `LayoutNode` IR -> flat world-space quads (background,
  boxes, buttons, images) plus text-run placeholders (block + proportional-width bar,
  NOT glyphs). Depth-first, bounded by `maxQuads`; `reason="vertexBudgetReached"` when
  capped. `VERTEX_STRIDE_FLOATS` is public (the renderer uses it to size the cap).
- `core/OmegaRenderer.kt` — now the live surface. Singleton slot `OmegaRenderer.liveInstance`
  (`registerLive`). `tickFrameBoundary()` runs the control law FIRST every frame
  (`allocator.tick -> governor.reciprocate -> GpuScanner.safetyCap -> apply`) so callers
  must NOT tick the allocator. IR is queued with `applyLayoutNodes` and built in
  `onDrawFrame` within `lastSafeVertexBudget`; a third program (`IR_VS`/`IR_FS`) draws it.
  `trace()` writes three evidence lines to logcat AND to
  `/sdcard/Darkith/logs/omega_trace.txt` (tick line throttled ~1 Hz) — this is the
  "in-app Aegis logs" surface, because the device has no adb.
- `core/NativeForgeBuilder.kt` — routes IR into the LIVE renderer; refuses with
  `DEFICIT: C7 — no live OmegaRenderer attached` when there is none. Does not construct
  a renderer and does not tick.
- `core/OmegaActivity.kt` — attaches `registerLive(renderer)` in `onCreate`, detaches in
  `onDestroy`. Its HUD shows `builder.status()`.
- `transliaison/HomekeeperBridge.kt` — `forgeRenderNative` now calls
  `NativeForgeBuilder(host)`; added `openOmegaScreen()`.

### forgeNative vs forgeChimera — reconciled (no redundancy, no dead module)

- `forgeChimera(donorsJson, html, appName, pkgName)` — the APK builder. Its ORIGINAL
  donor-grafting duty is honoured here and ONLY here: donor APK paths in, grafted
  resources out, signed APK. The webapp "Build APK" calls this (`apkBuildMethod()`).
- `forgeRenderNative`/`forgeNative(html, appName, pkgName)` — the IR renderer. No donor
  list, no APK. Refuses `DEFICIT: C7` with no live surface. Reached from the webapp via
  the new `aegis://ir` (and `aegis://omega` opens the surface). `forgeIrRender()` and
  `openOmegaScreen()` were added to the webapp's `App` object.

### How it was verified (not inferred)

- Patched core package (17 files) compiles against the real android-34 jar: **0 errors**.
- `IRBuilder` was RUN on a real IR tree from `TransliaisonEngine`: **11/11** pass
  (17 quads / 102 verts on the sample, 6 text-run placeholders, array length == verts*6
  floats, all finite, budget=4 stops at 4 quads with `vertexBudgetReached`, empty IR
  yields just the background quad).
- A bug in `forge_c7_oneshot.sh` was found by RUNNING it: `ONES` was only checked
  for non-empty, so a typo'd path printed a false `[ok]` and failed only after the
  patch was applied. It now requires `[ -f "$ONES" ]` and aborts in preflight.
- `delivery/forge_c7_oneshot.sh` was EXECUTED end-to-end against a simulated Termux
  layout: toolchain/SDK/project preflight, anchor gate, backup, base64 decode-apply,
  brace/paren sanity, and all six marker assertions pass; its three abort paths
  (missing tool, tampered anchor, missing oneshot) fire correctly; the files it writes
  hash-match the verified sources and that written core package also compiles 0 errors.
- `AutophagicAllocator.kt` and `MemoryGovernor.kt` are byte-identical (sha256 unchanged)
  to what shipped — C7 wires them in, it does not rewrite them.
- The patched webapp runs offline in headless Chromium: `selfTest()` **49/49**, zero
  console/page errors, and `aegis://help|omega|ir|home` all resolve.

### Still not true (do not claim)

- GLES 2.0 via Java `ByteBuffer`. No JNI, no native C++, no `malloc`.
- Text is a placeholder bar, not glyph rendering.
- Nothing has run on a real Android device or GPU. No install, no launch, no frame was
  observed. The on-disk `omega_trace.txt` exists precisely so that can be falsified on
  the device without adb.
- The ~38 kotlinc errors in `MainActivity.kt` are pre-existing (androidx/`super.onBackPressed`);
  the patched files add none. The on-device Gradle build remains unverified here.

---

## 2026-11-15 (later session) — engine dex must be self-contained

**Hard rule:** `assets/engine/template.dex` (in the host APK, and mirrored at
`app/src/main/assets/engine/template.dex` in the source zip) is injected verbatim
as `classes.dex` into **every** APK the in-app forge builds
(`ChimeraBuilder.build()` → `putDeflated(zo,"classes.dex",templateDex.readBytes())`).
It is **not** re-merged with the Kotlin stdlib at forge time, and forged APKs do
not bundle `androidx`/stdlib separately. Therefore this dex must be
**self-contained**: every non-platform type it references must be defined inside
it.

The version that shipped had 84 classes and **29 unresolved `Lkotlin/...` types**
— the app's Kotlin compiled without the stdlib on the dex path. Every forged APK
would have thrown `NoClassDefFoundError: kotlin/...` at class-load. Symptom to
recognise: "Build APK succeeds, install succeeds, app crashes on open."

**How to check (do this after any engine change):** parse the DEX type table and
diff referenced-vs-defined types, ignoring `Landroid/ Ljava/ Ljavax/ Ldalvik/
Lorg/{json,xml,w3c,apache,ietf}/ Lsun/`:

```
# fast, no deps: read the header (type_ids at offset 8, type count at 8? see code)
python3 - <<'PY'
import struct,zipfile
d=zipfile.ZipFile('darkith-homekeeper-debug.apk').read('assets/engine/template.dex')
v=struct.unpack_from('<18I',d,32)   # string_ids..class_defs offsets
sid_n,sid_o,tid_n,tid_o=v[6],v[7],v[8],v[9]; cd_n,cd_o=v[16],v[17]
u32=lambda o:struct.unpack_from('<I',d,o)[0]
def rs(o):
    n=0;p=o
    while True:
        c=d[p];p+=1;n=(n<<7)|(c&0x7f)
        if not(c&0x80):break
    return d[p:p+n].decode('utf-8','replace')
S=[rs(u32(sid_o+4*i)) for i in range(sid_n)]
T=[rs(u32(tid_o+4*i)) for i in range(tid_n)]
D=[T[u32(cd_o+32*i)] for i in range(cd_n)]
P=('Landroid/','Ljava/','Ljavax/','Ldalvik/','Lorg/json/','Lorg/xml/','Lorg/w3c/','Lorg/apache/','Lsun/','Lorg/ietf/','Landroidx/')
miss=[t for t in T if t.startswith('L') and t.endswith(';') and t not in set(D) and not t.startswith(P)]
print('classes',len(D),'unresolved',len(miss),miss[:6])
PY
```

Target: `unresolved 0`. Fixed build: 1,079 classes, 12,715 method ids.

**How the fix was produced here:** merge the Kotlin stdlib into the engine dex
(e.g. d8/`dx --dex` the engine classes together with `kotlin-stdlib` and
`kotlin-stdlib-jdk7/8`), then re-parse until unresolved == 0, then re-stage into
both the APK and the source zip. Verify with a full offline forge run:
`aapt2 link` → inject html+dex+assets → `zipalign -f 4` → `apksigner` (v1+v2+v3),
then re-parse the produced `classes.dex` (must also be 0 unresolved).

**Signing keys.** Two different keys exist and both matter:
- host APK: `/tmp/repro/dk.keystore` (storepass/keypass `android`) for the build
  produced here; the original host APK used the Android **debug** key.
- forged apps: signed at runtime by `ApkSignerRunner` using the app's embedded
  `assets/engine/release_key` (PKCS#8, unencrypted) + `assets/engine/release_cert`
  (CN=Darkith Release). Note `apksigner` CLI rejects that key unless it is
  converted to PEM (`openssl pkcs8 -topk8 -nocrypt`); the on-device path uses
  Java's `KeyFactory` and is unaffected.

**Delivery sync rule:** after changing the webapp or the engine dex, refresh
*all four* of `darkith-forge.html`, `darkith-homekeeper-debug.apk`,
`darkith_source_fixed.zip` (`app/src/main/assets/...`) and
`darkith-forge-bundle.zip`, then re-generate the sizes/sha256 in `README.txt`,
`index.html` and `PROGRESS-LEDGER.md` from the files on disk. Stale copies in the
bundle have shipped before; always diff bundle-vs-standalone after a rebuild.

**Environment note:** this sandbox has no `/dev/kvm`, no `adb`, and no Android
emulator, so APK runtime is verified structurally (dex resolution, manifest,
signing, alignment, and booting the embedded HTML in headless Chromium), never by
launching on Android. Do not claim a device run.

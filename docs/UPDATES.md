# Sovereign upliftment tracking — the integrated client-coupling update watcher

This answers one question: **is the copy I am running stale against the live
remote circuit tree?** Before this, nothing did. The app read its own version
(`darkith.apkVersion()`) but never compared it to anything, and the repo had no
version manifest a client could read. So a phone could sit on last session's
wrap-up indefinitely and never be told an upliftment existed.

## The single source of truth

`VERSION.json` at the repo root is the manifest of record:

```json
{ "versionCode": 3, "versionName": "1.2.0-omega", "surfaceVersion": "v5.3.1",
  "manifest_url": "https://raw.githubusercontent.com/Deobfugazi/darkith-forge/main/VERSION.json",
  "oneshot_url": "https://github.com/Deobfugazi/darkith-forge/releases/latest/download/darkith-one-shot.sh" }
```

Everything else is derived from it, and `tools/update_gate.py` fails CI if any
of these disagree: the `var LOCAL` stamp inside `darkith forge.html`, the same
stamp inside `app/src/main/assets/homekeeper.html`, the `versionName` in
`AndroidManifest.xml`, and the two default URLs inside `build/updater.js`.

## The watcher

`build/updater.js` is injected at build time into both surfaces:

* the fused webapp (`darkith forge.html`) by `build/build-forge.py`;
* the host APK surface (`app/src/main/assets/homekeeper.html`) by
  `build/inject_updater.py` (idempotent, marker-wrapped).

It is dual-track and never lies:

* **remote** — compares the installed versionCode against the live
  `VERSION.json`. Offline is a first-class state, `unknown`, never a false
  `current`;
* **local** — the copy carries its own version, so it can report itself with
  the radio off.

The alert fires **once per new versionCode**, not on every poll. The dialog is
the app's own `UI.dialog` when present, otherwise a native `alert`, so it works
on every host including a bare browser tab. A small pill at the bottom-left
shows the state and re-checks on tap.

## How the Operator uses it

* The pill reads `Ω v1.2.0-omega · current`, `· offline`, or
  `Ω upliftment 1.3.0-omega available`.
* Tap it, or call `window.__dkUpdate.check()`, to force a check.
* When an upliftment is available the dialog names both versions and prints the
  one-shot download URL.

## Verifying it

```
node tools/updater_test.mjs          # 25 checks: version algebra, offline, alert-once
python3 tools/update_gate.py         # version truth across every surface
python3 build/inject_updater.py --check
tools/ci.sh                          # both run inside CI
```

The decision logic (`codeOf`, `cmp`, `decide`) is pure and exercised with real
inputs; the transport is the only thing stubbed, in the test only.

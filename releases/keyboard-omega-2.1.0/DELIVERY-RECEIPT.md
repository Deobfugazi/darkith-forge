# Darkith Keyboard Omega 2.1.0 — delivery receipt

Native Android system keyboard (DK-SIC-001 G1–G9), built on the raw 7-step chain.
Gradle was never invoked.

## Artifact

| | |
|---|---|
| File | `darkith-keyboard-omega.apk` |
| Bytes | 10,120,256 |
| SHA-256 | `2814522667384dcc2301f61dddb1c6792a707915b7c1712a6f858b77345aa07a` |
| Signing | v2 + v3 — `apksigner` reports `Verifies: true` |
| Chain | `aapt2 → kotlinc → d8 → zip → zipalign → apksigner` |
| Source commit | `9a03c1f` |
| Tag | `keyboard-omega-2.1.0` |

## Why this file is in git rather than `dist/`

`dist/` is gitignored because it is *regenerable*. This APK is not: the signing key is a
deliberate secret that never enters git, so a fresh clone cannot reproduce these exact bytes.
A delivered artifact that cannot be regenerated must be stored, not excluded.

## Installation

1. Copy `darkith-keyboard-omega.apk` to `/sdcard/Download` on the device.
2. Open it and confirm the installer prompt (allow "install unknown apps" for the file manager).
3. Settings → System → Languages & input → On-screen keyboard → Manage keyboards →
   enable **Darkith Keyboard**.
4. Switch to it with the keyboard picker in any text field.

Step 3 is the activation gate. Until it is tapped, the keyboard is installed but not selected.

## Evidence

Compiled-manifest proof (parsed from the binary AXML string pool, not asserted from source):

```
android.permission.BIND_INPUT_METHOD              present
android.view.InputMethod                          present
android.view.im                                   present
com.darkith.transliaison.ime.DarkithImeService    present
res/xml/darkith_ime.xml                           present
```

Components in `classes.dex`: `DarkithImeService`, `DarkithKeyboardView`, `Elrp`,
`ClipHistory`, `ImePrefs`, `DarkithImeSettings`.

CI: `PASS` at `9a03c1f`, rehearsed independently in a clean worktree before the push.

## Scope, stated honestly

Established: a registered `InputMethodService` that appears in the picker, draws a working
QWERTY, commits text through the live `InputConnection`, completes and corrects from an
offline lexicon, and keeps a clipboard history separate from the Android primary clipboard.

Not established by this release: device-installed verification, typing under load on the
TECNO, and the full DK-SIC-001 G1–G14 evidence set. Those require the device.

_This receipt was written by an AI agent (OpenHands) on behalf of the repository owner._

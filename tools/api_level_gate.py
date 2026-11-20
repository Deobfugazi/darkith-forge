#!/usr/bin/env python3
"""Fail if a launch-path source calls an API newer than minSdk without a version guard.

Why this exists: `AegisCircuitBreaker.checkAndRollback` called
`ActivityManager.getHistoricalProcessExitReasons` (API 30) unconditionally inside
`MainActivity.onCreate`, *before* `setContentView`. On Android 7-10 (minSdk 24) that
throws NoSuchMethodError and the launcher Activity dies before the UI ever paints —
the "installs fine, opens to a crash" failure that a static resource check cannot see.

The rule: any curated high-API symbol in a `.kt` file must sit in a file that also
carries an `SDK_INT` version guard. Coarse (file-scoped, not call-scoped), but it is
exact about the defect it was written for and never false-passes one.
"""
import pathlib
import re
import sys

# symbol -> API level it needs. Kept small and deliberate: only symbols that are
# launch-fatal when called below their level on the minSdk we ship.
HIGH_API = {
    "getHistoricalProcessExitReasons": 30,
    "ApplicationExitInfo": 30,
    "isExternalStorageManager": 30,
    "createAttributionContext": 30,
    "getInstallSourceInfo": 30,
    "createNotificationChannel": 26,
}

# A version guard: any reference to SDK_INT (the `Build.VERSION.SDK_INT >= ...` idiom).
GUARD = re.compile(r"SDK_INT")

# Lines that are prose/comments do not count as calls.
COMMENT = re.compile(r"^\s*(//|/\*|\*)")


def main(argv: list[str]) -> int:
    root = pathlib.Path(argv[1]) if len(argv) > 1 else pathlib.Path("app/src/main/java")
    if not root.is_dir():
        # The source tree is TRACKED: its absence is a defect in the tree, not an
        # absent runtime. Reporting SKIP here let a tree with no sources pass green.
        print(f"api_level_gate: FAIL — no source tree at {root} (tracked, so its absence is a defect)")
        return 1

    offenders = []
    scanned = 0
    for kt in sorted(root.rglob("*.kt")):
        scanned += 1
        text = kt.read_text(encoding="utf-8", errors="replace")
        guarded = bool(GUARD.search(text))
        for sym, api in HIGH_API.items():
            for i, line in enumerate(text.splitlines(), 1):
                if sym in line and not COMMENT.match(line):
                    if not guarded:
                        offenders.append(f"{kt}:{i}: {sym} (API {api}) with no SDK_INT guard in file")
                    break

    if offenders:
        print(f"api_level_gate: FAIL — {len(offenders)} unguarded high-API call(s):")
        for o in offenders:
            print("  " + o)
        return 1
    print(f"api_level_gate: PASS — {scanned} .kt file(s), no unguarded high-API call")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

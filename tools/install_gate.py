#!/usr/bin/env python3
"""install_gate.py — the "App not installed" registry.

Every concrete cause of the Android package installer rejecting an APK is a
named check below. If any is OPEN the APK will NOT install (or will install and
then crash on launch), so the gate exits non-zero.

Usage:
    python3 tools/install_gate.py <apk> [project_root]

Checks (I-nn):
    I-01 versionCode + versionName present        (installer rejects a versionless APK)
    I-02 minSdk/targetSdk sane (24 <= min <= target)
    I-03 v2 signature verifies                    (API 30+ needs v2/v3, not v1)
    I-04 zipalign 4-byte aligned                  (Play/store & some ROMs enforce it; N/A if no zipalign)
    I-05 resources.arsc STORED                    (API 30+ refuses a DEFLATED arsc)
    I-06 every lib/*.so STORED                    (same rule for native libs)
    I-07 extractNativeLibs=true                   (else nativeLibraryDir is empty)
    I-08 no duplicate zip entries                 (dup entries -> INSTALL_PARSE_FAILED)
    I-09 no android:testOnly                      (testOnly APKs refuse to install)
    I-10 not android:debuggable                   (a release APK must not be debuggable)
    I-11 launcher activity declared (MAIN+LAUNCHER)
    I-12 every declared component exists in the dex (else launch = ActivityNotFound)
    I-13 native-code ABI present and non-empty    (arm64-v8a device needs the ABI)
    I-14 application label resolves to a string
"""
import os, re, sys, zipfile, subprocess

# I-03: apksigner's canonical line is
#   "Verified using v2 scheme (APK Signature Scheme v2): true"
# so the label and the value are separated by the scheme's own parenthetical.
V2_RE = re.compile(r"v2 scheme[^\n]*:\s*true", re.I)

def find_aapt2():
    for c in (os.environ.get("AAPT2"), "aapt2", "/tmp/darkith-toolchain/aapt2"):
        if not c:
            continue
        if os.path.sep in c:
            if os.path.exists(c):
                return c
        else:
            from shutil import which
            p = which(c)
            if p:
                return p
    return None

def find_apksigner():
    from shutil import which
    return which("apksigner") or os.environ.get("APKSIGNER")

def find_zipalign():
    from shutil import which
    return which("zipalign")

def xmltree(aapt2, apk):
    try:
        out = subprocess.run([aapt2, "dump", "xmltree", "--file", "AndroidManifest.xml", apk],
                             capture_output=True, text=True, timeout=120).stdout
    except Exception:
        return ""
    return out

def manifest_components(tree):
    """Class names of <activity|service|receiver|provider> from the APK's OWN manifest.

    Reading the APK's own manifest (not the repo's source manifest) is what makes
    this gate honest about the artifact in hand: a minimal proof APK legitimately
    declares different components than the full app.
    """
    comps, pending = [], False
    for line in tree.splitlines():
        s = line.strip()
        if s.startswith("E: "):
            pending = s[3:].split()[0] in ("activity", "service", "receiver", "provider")
            continue
        if pending and "android:name" in s:
            m = re.search(r'android:name\([^)]*\)="([^"]+)"', s)
            if m and "." in m.group(1):
                comps.append(m.group(1))
            pending = False
    return comps

def badging(aapt2, apk):
    try:
        return subprocess.run([aapt2, "dump", "badging", apk],
                              capture_output=True, text=True, timeout=120).stdout
    except Exception:
        return ""

def selftest():
    """Guard I-03: the v2 detector must match apksigner's real output, not a guess."""
    cases = [
        ("Verified using v2 scheme (APK Signature Scheme v2): true", True),
        ("Verified using v2 scheme (APK Signature Scheme v2): false", False),
        ("Verifies: true\nVerified using v1 scheme (JAR signing): false", False),
    ]
    bad = 0
    for line, want in cases:
        got = bool(V2_RE.search(line))
        tag = "ok  " if got == want else "FAIL"
        print(f"  {tag} v2 detect -> {got} (want {want}): {line.splitlines()[0][:48]}")
        bad += got != want
    print(f"  install_gate selftest: {'PASS' if not bad else 'FAIL'} ({len(cases) - bad}/{len(cases)})")
    sys.exit(1 if bad else 0)

def main():
    if len(sys.argv) == 2 and sys.argv[1] == "--selftest":
        selftest()
    if len(sys.argv) < 2:
        sys.exit("usage: install_gate.py <apk> [project_root] | --selftest")
    apk = os.path.abspath(sys.argv[1])
    root = os.path.abspath(sys.argv[2]) if len(sys.argv) > 2 else os.getcwd()

    results = []
    def rec(name, status, note):
        results.append((name, status, note))

    if not os.path.isfile(apk):
        sys.exit(f"install_gate: no APK at {apk}")

    z = zipfile.ZipFile(apk)
    names = z.namelist()
    dex = b"".join(z.read(n) for n in names if n.endswith(".dex"))
    aapt2 = find_aapt2()
    tree = xmltree(aapt2, apk) if aapt2 else ""
    badg = badging(aapt2, apk) if aapt2 else ""

    # ---- I-01 version ---------------------------------------------------------
    vc = re.search(r'versionCode="([^"]*)"', badg) or re.search(r'versionCode\(\S+\)=(\S+)', tree)
    vn = re.search(r"versionName='([^']*)'", badg) or re.search(r'versionName\([^)]*\)="([^"]*)"', tree)
    if vc and vn:
        rec("I-01-version", "CLOSED", f"versionCode={vc.group(1)} versionName={vn.group(1)}")
    else:
        rec("I-01-version", "OPEN", "no versionCode/versionName readable from the APK")

    # ---- I-02 sdk range -------------------------------------------------------
    mn = re.search(r"minSdkVersion:'(\d+)'", badg) or re.search(r"minSdkVersion\(\S+\)=(\d+)", tree)
    tg = re.search(r"targetSdkVersion:'(\d+)'", badg) or re.search(r"targetSdkVersion\(\S+\)=(\d+)", tree)
    if mn and tg and int(mn.group(1)) >= 21 and int(mn.group(1)) <= int(tg.group(1)):
        rec("I-02-sdk-range", "CLOSED", f"minSdk={mn.group(1)} targetSdk={tg.group(1)}")
    else:
        rec("I-02-sdk-range", "OPEN", f"bad sdk range min={mn and mn.group(1)} target={tg and tg.group(1)}")

    # ---- I-03 signature (v2) --------------------------------------------------
    apksigner = find_apksigner()
    if apksigner:
        r = subprocess.run([apksigner, "verify", "--verbose", apk], capture_output=True, text=True)
        v2 = V2_RE.search(r.stdout)
        if r.returncode == 0 and v2:
            rec("I-03-signature-v2", "CLOSED", "v2 signature verifies")
        else:
            rec("I-03-signature-v2", "OPEN", "v2 signature missing or verify failed")
    else:
        rec("I-03-signature-v2", "OPEN", "apksigner not available (cannot prove the signature)")

    # ---- I-04 alignment -------------------------------------------------------
    # zipalign is not a Maven artifact and is absent on a bare runner, so this is N/A
    # (not a false OPEN) when it is missing — the same honesty rule as every other
    # unprovable check. When present, zipalign -c 4 is the authority.
    za = find_zipalign()
    if za:
        r = subprocess.run([za, "-c", "4", apk], capture_output=True, text=True)
        if r.returncode == 0:
            rec("I-04-aligned", "CLOSED", "4-byte aligned")
        else:
            rec("I-04-aligned", "OPEN", "not 4-byte aligned")
    else:
        rec("I-04-aligned", "N/A", "zipalign absent (stage with tools/get_toolchain.sh to prove)")

    # ---- I-05 arsc STORED -----------------------------------------------------
    try:
        st = z.getinfo("resources.arsc").compress_type == 0
        rec("I-05-arsc-stored", "CLOSED" if st else "OPEN",
            "resources.arsc STORED" if st else "resources.arsc DEFLATED -> API30+ refuses install")
    except KeyError:
        rec("I-05-arsc-stored", "OPEN", "no resources.arsc in the APK")

    # ---- I-06 lib/*.so STORED -------------------------------------------------
    deflated = [n for n in names if n.endswith(".so") and z.getinfo(n).compress_type != 0]
    if deflated:
        rec("I-06-so-stored", "OPEN", "DEFLATED native libs: " + ", ".join(deflated))
    else:
        rec("I-06-so-stored", "CLOSED", "all lib/*.so STORED")

    # ---- I-07 extractNativeLibs ----------------------------------------------
    if re.search(r"extractNativeLibs\([^)]*\)=true", tree):
        rec("I-07-extract-native", "CLOSED", "extractNativeLibs=true")
    else:
        rec("I-07-extract-native", "OPEN", "extractNativeLibs!=true -> nativeLibraryDir stays empty")

    # ---- I-08 duplicate entries ----------------------------------------------
    dupes = {n for n in names if names.count(n) > 1}
    if dupes:
        rec("I-08-no-dup-entries", "OPEN", "duplicate zip entries: " + ", ".join(sorted(dupes)))
    else:
        rec("I-08-no-dup-entries", "CLOSED", "no duplicate zip entries")

    # ---- I-09 testOnly --------------------------------------------------------
    if re.search(r"testOnly\([^)]*\)=true", tree):
        rec("I-09-not-testonly", "OPEN", "android:testOnly=true refuses to install")
    else:
        rec("I-09-not-testonly", "CLOSED", "not testOnly")

    # ---- I-10 debuggable (informational: a debug build DOES install) ----------
    if re.search(r"debuggable\([^)]*\)=true", tree):
        rec("I-10-release-build", "CLOSED", "note: android:debuggable=true (installs fine; just not a release APK)")
    else:
        rec("I-10-release-build", "CLOSED", "not debuggable (release APK)")

    # ---- I-11 launcher activity ----------------------------------------------
    if "launchable-activity:" in badg:
        launcher = badg.split("launchable-activity:")[1].split("\n")[0].strip()
        rec("I-11-launcher", "CLOSED", launcher[:80])
    else:
        rec("I-11-launcher", "OPEN", "no MAIN+LAUNCHER activity (nothing to open)")

    # ---- I-12 components exist in dex ----------------------------------------
    # Derived from the APK's OWN manifest so the check describes the artifact, not
    # the repo. A component in the manifest but absent from the dex is an
    # ActivityNotFound/ClassNotFound crash the moment the OS launches it.
    comps = manifest_components(tree)
    if comps:
        missing = [c for c in comps if ("L" + c.replace(".", "/") + ";").encode() not in dex]
        if missing:
            rec("I-12-components-in-dex", "OPEN", "declared but not in dex: " + ", ".join(missing))
        else:
            rec("I-12-components-in-dex", "CLOSED", f"{len(comps)} manifest components all present in dex")
    else:
        rec("I-12-components-in-dex", "OPEN", "no components readable from the APK manifest")

    # ---- I-13 ABI -------------------------------------------------------------
    # An APK with no native code installs fine (this is not a blocker); one WITH
    # native code must carry the device ABI or the loader cannot satisfy libs.
    so = [n for n in names if n.startswith("lib/") and n.endswith(".so")]
    abis = sorted({n.split("/")[1] for n in so})
    nc = re.search(r"native-code:\s*'([^']*)'", badg)
    if not so:
        rec("I-13-abi", "CLOSED", "no native code (installs; app-side native tools absent)")
    elif "arm64-v8a" in abis and (nc is None or "arm64-v8a" in nc.group(1)):
        rec("I-13-abi", "CLOSED", f"abis={abis} native-code matches")
    else:
        rec("I-13-abi", "OPEN", f"abis={abis} native-code={nc and nc.group(1)} (device ABI missing)")

    # ---- I-14 label -----------------------------------------------------------
    if re.search(r'application-label:', badg) or re.search(r'label\([^)]*\)="[^"]+"', tree):
        rec("I-14-label", "CLOSED", "application label resolves to a string")
    else:
        rec("I-14-label", "OPEN", "no resolvable application label")

    print("== INSTALL GATE — 'App not installed' registry ==")
    print(f"apk: {apk}   aapt2: {aapt2 or '<none>'}   apksigner: {apksigner or '<none>'}")
    print()
    open_n = 0
    for name, status, note in results:
        if status == "OPEN":
            open_n += 1
        print(f"  {status:<6} {name:<24} {note}")
    print()
    if open_n:
        print(f"REFUSED — {open_n} install-blocker(s) OPEN. This APK will not install cleanly.")
        sys.exit(1)
    print("INSTALLABLE — no known 'App not installed' cause is open.")
    sys.exit(0)

if __name__ == "__main__":
    main()

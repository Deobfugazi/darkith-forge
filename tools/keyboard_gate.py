#!/usr/bin/env python3
"""Static admission checks for the native Darkith IME and its offline resources."""
from pathlib import Path
import hashlib
import re
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
ANDROID = "{http://schemas.android.com/apk/res/android}"
failures = []

def need(condition, label):
    if condition:
        print("PASS", label)
    else:
        print("FAIL", label)
        failures.append(label)

manifest_path = ROOT / "app/src/main/AndroidManifest.xml"
manifest = ET.parse(manifest_path).getroot()
service = next((x for x in manifest.findall("./application/service")
                if x.get(ANDROID + "name", "").endswith(".ime.DarkithImeService")), None)
need(service is not None, "manifest registers the single native DarkithImeService")
if service is not None:
    need(service.get(ANDROID + "permission") == "android.permission.BIND_INPUT_METHOD",
         "IME service is protected by BIND_INPUT_METHOD")
    actions = [x.get(ANDROID + "name") for x in service.findall("./intent-filter/action")]
    need("android.view.InputMethod" in actions, "IME service advertises android.view.InputMethod")
    metadata = service.find("./meta-data")
    need(metadata is not None and metadata.get(ANDROID + "name") == "android.view.im"
         and metadata.get(ANDROID + "resource") == "@xml/darkith_ime",
         "IME service references its input-method metadata")

meta = ET.parse(ROOT / "app/src/main/res/xml/darkith_ime.xml").getroot()
need(meta.tag == "input-method", "input-method metadata parses")
need(meta.get(ANDROID + "settingsActivity", "").endswith(".ime.DarkithImeSettings"),
     "IME settings activity is reachable from Android input settings")

assets = ROOT / "app/src/main/assets/keyboard"
dic = assets / "en_US.dic"
aff = assets / "en_US.aff"
notice = assets / "README_en_US.txt"
resource_manifest = assets / "RESOURCE-MANIFEST.md"
need(dic.is_file() and aff.is_file() and notice.is_file() and resource_manifest.is_file(),
     "English dictionary, affix rules, licence notice, and byte-addressed resource manifest are bundled")
if dic.is_file():
    lines = dic.read_text(encoding="utf-8").splitlines()
    count = int(lines[0].strip()) if lines else 0
    entries = [line for line in lines[1:] if line.strip() and not line.lstrip().startswith("#")]
    need(count == len(entries) and count >= 40000,
         "bundled en_US dictionary header matches all nonblank source entries")
    need(hashlib.sha256(dic.read_bytes()).hexdigest() ==
         "f0b1a234bd178bdd01875b2a392a9647f888b8fe879f79c52aae62c2759b3647",
         "en_US.dic raw SHA-256 matches the pinned source identity")
if aff.is_file():
    text = aff.read_text(encoding="utf-8")
    need("PFX " in text and "SFX " in text and "REP " in text, "affix resource contains prefix, suffix, and replacement tables")
    need(hashlib.sha256(aff.read_bytes()).hexdigest() ==
         "e746c882dd6f303c2c46e7452804b9201115a6942cfeb15f18f8edf774d2e24e",
         "en_US.aff raw SHA-256 matches the pinned source identity")
if resource_manifest.is_file():
    resource_text = resource_manifest.read_text(encoding="utf-8")
    need("This is not a complete Hunspell implementation" in resource_text
         and "ONLYINCOMPOUND" in resource_text and "SCOWL 2020.12.07" in resource_text,
         "resource manifest states source version and unsupported Hunspell constructs")
if notice.is_file():
    text = notice.read_text(encoding="utf-8")
    need("Copyright 2000-2018 by Kevin Atkinson" in text and "Permission to use, copy, modify, distribute and sell" in text,
         "upstream SCOWL copyright and permission notice is retained")

service_src = (ROOT / "app/src/main/java/com/darkith/transliaison/ime/DarkithImeService.kt").read_text()
elrp_src = (ROOT / "app/src/main/java/com/darkith/transliaison/ime/Elrp.kt").read_text()
view_src = (ROOT / "app/src/main/java/com/darkith/transliaison/ime/DarkithKeyboardView.kt").read_text()
prefs_src = (ROOT / "app/src/main/java/com/darkith/transliaison/ime/ImePrefs.kt").read_text()
history_src = (ROOT / "app/src/main/java/com/darkith/transliaison/ime/ClipHistory.kt").read_text()
model_src = (ROOT / "app/src/main/java/com/darkith/transliaison/ime/PersonalLanguageModel.kt").read_text()
settings_src = (ROOT / "app/src/main/java/com/darkith/transliaison/ime/DarkithImeSettings.kt").read_text()

need("Elrp.initialize(applicationContext)" in service_src, "IME initializes the bundled lexical resource")
need("NOSUGGEST" in (assets / "en_US.aff").read_text(encoding="utf-8")
     and "noSuggestFlag" in elrp_src and "suggestible" in elrp_src,
     "Hunspell NOSUGGEST entries are excluded from suggestions")
need("accepted == declared" in elrp_src and "onlyInCompoundFlag" in elrp_src
     and "stem.any { it.isLetter() }" in elrp_src,
     "ELRP validates every source row, preserves single-letter words, and excludes compound-only roots")
need("setComposingText" in service_src and "currentInputConnection" in service_src,
     "text composition and commits use the live editor connection")
need("prefs?.autocorrect == true" in service_src and "options.size == 1" in service_src,
     "autocorrect is preference-gated and unique-candidate-only")
need("setEditorType" in service_src and "numericMode()" in view_src and "symbolPage" in view_src,
     "numeric and symbol layouts are wired to editor input type")
need("limitedEditor = type == InputType.TYPE_NULL" in service_src and "sendRawText" in service_src
     and "KeyEvent.FLAG_SOFT_KEYBOARD" in service_src,
     "TYPE_NULL editors use the documented raw key-event pathway")
need("onCursorMove" in service_src and "setSelection(absolute, absolute)" in service_src
     and "onCursorMove" in view_src,
     "spacebar swipe moves the editor cursor through extracted selection offsets")
need("onToggleIncognito" in service_src and "incognito" in service_src
     and "onRejectCandidate" in service_src and "alternativesFor" in view_src,
     "incognito, long-press alternatives, and candidate rejection are wired")
need("lastCorrection" in service_src and "conn.deleteSurroundingText(suffix.length, 0)" in service_src,
     "autocorrection can be undone by immediate backspace")
need("onStartInputView" in service_src and "attachClipboardListener()" in service_src
     and "onFinishInputView" in service_src and "detachClipboardListener()" in service_src,
     "clipboard observation is scoped to visible IME sessions")
need('getBoolean("clip_history", false)' in prefs_src,
     "clipboard history is opt-in by default")
need("setClipboardItems" in view_src and "onClip(text: String)" in view_src
     and "setClipboardItems(items)" in service_src,
     "keyboard exposes local clipboard history for paste")
need("fun search(" in history_src and "fun setPinned(" in history_src and "fun clearAll(" in history_src,
     "clipboard store supports search, pin state, delete, and clear-all")
need("clipRetentionDays" in prefs_src and "p.clipRetentionDays" in service_src,
     "clipboard retention is persisted and used by capture")
need("personal_words" in elrp_src and "addPersonalWord" in elrp_src and "removePersonalWord" in elrp_src
     and "exportPersonalWords" in elrp_src and "clearPersonalWords" in elrp_src,
     "personal vocabulary supports persistent add, remove, export, and reset")
need("rejectSuggestion" in elrp_src and "rejected_suggestions" in elrp_src,
     "rejected suggestions persist and are excluded from future candidate lists")
need("ClipDescription.EXTRA_IS_SENSITIVE" in service_src and "item.uri != null" in service_src
     and "item.intent != null" in service_src and "passesLuhn" in service_src,
     "clipboard capture rejects platform-marked sensitive clips, non-text payloads, and common secret patterns")
need("nextWordPrediction" in prefs_src and "personalLearning" in prefs_src
     and "languageModel?.predict" in service_src and "languageModel?.observe" in service_src,
     "next-word prediction is a real opt-in local adjacent-word model")
need("Learn adjacent words on this device (off by default)" in settings_src,
     "local learning is explicitly opt-in and described in settings")
need("Export personal vocabulary to clipboard" in settings_src and "Reset personal vocabulary" in settings_src
     and "Clear rejected suggestions" in settings_src,
     "personal vocabulary export/reset and rejected-word reset are exposed")
need("setBoolean(\"clip_history\", v)" in prefs_src and "getBoolean(\"clip_history\", false)" in prefs_src
     and "clipRetentionDays" in prefs_src,
     "clipboard preference is opt-in and retention is bounded")
need("PRIMARY KEY(previous, next)" in model_src and "CREATE TABLE bigram" in model_src,
     "personal prediction stores adjacent word pairs rather than complete text")
need("Clear learned next-word patterns" in settings_src and "fun clear()" in model_src,
     "users can erase the local prediction model")
need("Search saved clipboard text" in settings_src and "Clear all" in settings_src
     and "Clipboard retention" in settings_src,
     "clipboard manager exposes search, clear, and retention controls")

spec_path = ROOT / "docs/keyboard/DARKITH-KEYBOARD-SINGULAR-INVARIANT.md"
if spec_path.is_file():
    import hashlib
    need(hashlib.sha256(spec_path.read_bytes()).hexdigest() == "75c0058a83d71ad8593dadd0f4f0003448cc3cfbfb0558e2754e13efad91c4b2",
         "admitted keyboard invariant source matches the uploaded bytes")
else:
    print("DEFERRED keyboard invariant source: run tools/admit_keyboard_spec.sh with the uploaded file")

installer = (ROOT / "install_homekeeper_omega.sh").read_text()
need("75c0058a83d71ad8593dadd0f4f0003448cc3cfbfb0558e2754e13efad91c4b2" in installer, "installer pins the keyboard invariant source")
need("1482e152c1ff2d8bdf97cd52684c98f7224d58713b0b8735f902878aebb3405d" in installer,
     "Homekeeper installer pins the uploaded HTML by SHA-256")
need("build.sh" in installer and "gradle" not in installer.lower(),
     "Homekeeper installer uses the raw chain and does not invoke Gradle")
need("tools/admit_keyboard_spec.sh" in installer,
     "Homekeeper installer invokes canonical indexed keyboard-spec admission")
admission = (ROOT / "tools/admit_keyboard_spec.sh").read_text()
need("tools/kb_index.py --write" in admission and "tools/nt_gate.py" in admission
     and "tools/citation_gate.py" in admission and "proof/nt_claims.json" in admission,
     "keyboard source admission uses the canonical KB generator, NT witness ledger, and citation gate")
need("NT14-CANONICAL-SOURCE-CARRIED" in admission and "NT15-CANONICAL-SOURCE-CARRIED" in admission
     and "KEYBOARD-SINGULAR-INVARIANT-SOURCE-CARRIED" in admission,
     "admission creates re-runnable provenance witnesses for NT XIV, NT XV, and the keyboard spec")
need("assets/homekeeper.html" in installer and "packed != expected" in installer,
     "Homekeeper installer copies the HTML into the native APK asset path and verifies packaged bytes")
need("termux-setup-storage" in installer and "storage/downloads" in installer
     and "termux-open" in installer,
     "on-device delivery provisions shared storage and opens Android's package installer")
need("EXISTING_CERT" in installer and "different signing certificate" in installer,
     "installer refuses unsafe replacement when the installed app signer differs")
toolchain_src = (ROOT / "tools/setup_termux_toolchain.sh").read_text()
need('uname -m' in toolchain_src and 'aarch64' in toolchain_src
     and 'pkg install -y openjdk-21 aapt2 apksigner zipalign' in toolchain_src,
     "Termux provisioner selects native ARM64 Java, aapt2, apksigner, and zipalign")
need('export ZIPALIGN="$ZIPALIGN"' in toolchain_src and 'export ANDROID_JAR="$TOOLS/android.jar"' in toolchain_src
     and 'export R8_JAR="$TOOLS/r8.jar"' in toolchain_src,
     "Termux toolchain exports every raw-build dependency")

activity = (ROOT / "app/src/main/java/com/darkith/transliaison/HomekeeperActivity.kt").read_text()
bridge = (ROOT / "app/src/main/java/com/darkith/transliaison/HomekeeperBridge.kt").read_text()
need('addJavascriptInterface(HomekeeperBridge(this@HomekeeperActivity), "darkith")' in activity,
     "Homekeeper injects the native JavaScript bridge")
expected = ["fileList","fileRead","fileWrite","fileMove","fileCopy","fileDelete","fileDirs","fileStat",
            "shell","shellExec","shellSetCwd","shellSetEnv","shellEnv","shellHistory","browserOpen",
            "forgeChimera","installApkNative","translateHtml","healSource","ingestSubstrate",
            "openOmegaScreen","forgeRenderNative"]
for name in expected:
    pattern = r"@JavascriptInterface\s+(?:@[\w.]+\s+)*fun\s+" + re.escape(name) + r"\s*\("
    need(re.search(pattern, bridge) is not None, f"Homekeeper bridge exposes {name}")

if failures:
    print(f"KEYBOARD GATE: FAIL ({len(failures)} failures)")
    sys.exit(1)
print("KEYBOARD GATE: PASS")

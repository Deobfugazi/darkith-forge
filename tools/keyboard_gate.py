#!/usr/bin/env python3
"""Static admission checks for the native Darkith IME and its offline resources."""
from pathlib import Path
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
need(dic.is_file() and aff.is_file() and notice.is_file(), "English dictionary, affix rules, and license notice are bundled")
if dic.is_file():
    lines = dic.read_text(encoding="utf-8").splitlines()
    count = int(lines[0].strip()) if lines else 0
    need(count >= 40000 and len(lines) > 40000, "bundled en_US dictionary is a real 40k+ headword resource")
if aff.is_file():
    text = aff.read_text(encoding="utf-8")
    need("PFX " in text and "SFX " in text and "REP " in text, "affix resource contains prefix, suffix, and replacement tables")
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
need("setComposingText" in service_src and "currentInputConnection" in service_src,
     "text composition and commits use the live editor connection")
need("prefs?.autocorrect == true" in service_src and "options.size == 1" in service_src,
     "autocorrect is preference-gated and unique-candidate-only")
need("setEditorType" in service_src and "numericMode()" in view_src and "symbolPage" in view_src,
     "numeric and symbol layouts are wired to editor input type")
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
need("personal_words" in elrp_src and "addPersonalWord" in elrp_src and "removePersonalWord" in elrp_src,
     "personal vocabulary is a persistent overlay separate from bundled words")
need("nextWordPrediction" in prefs_src and "personalLearning" in prefs_src
     and "languageModel?.predict" in service_src and "languageModel?.observe" in service_src,
     "next-word prediction is a real opt-in local adjacent-word model")
need("Learn adjacent words on this device (off by default)" in settings_src,
     "local learning is explicitly opt-in and described in settings")

installer = (ROOT / "install_homekeeper_omega.sh").read_text()
need("1482e152c1ff2d8bdf97cd52684c98f7224d58713b0b8735f902878aebb3405d" in installer,
     "Homekeeper installer pins the uploaded HTML by SHA-256")
need("build.sh" in installer and "gradle" not in installer.lower(),
     "Homekeeper installer uses the raw chain and does not invoke Gradle")
need("assets/homekeeper.html" in installer and "APK ASSET CHECK: PASS" not in installer,
     "Homekeeper installer copies the HTML into the native APK asset path and verifies packaged bytes")

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

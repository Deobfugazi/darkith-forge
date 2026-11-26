#!/usr/bin/env python3
"""Detect/repair the quadratic chat echo scan (MUST #42 defect class)."""
import argparse, pathlib, sys
ROOT=pathlib.Path(__file__).resolve().parent.parent
SOURCE=ROOT/"tools"/"chat_gatekeeper.py"
INDEX_CLASS="""class AssistantEchoIndex:
    \"\"\"Reusable exact/prefix index; build once per session.\"\"\"
    def __init__(self, texts: list[str]):
        self.sorted = sorted(set(" ".join(t.split()) for t in texts if len(" ".join(t.split())) >= ECHO_MIN))
        self.by_prefix: dict[str, list[str]] = {}
        for text in self.sorted:
            self.by_prefix.setdefault(text[:ECHO_MIN], []).append(text)

    def matches_normalized(self, user_text: str) -> bool:
        if len(user_text) < ECHO_MIN:
            return False
        if any(user_text.startswith(a) for a in self.by_prefix.get(user_text[:ECHO_MIN], ())):
            return True
        i = bisect_left(self.sorted, user_text)
        return i < len(self.sorted) and self.sorted[i].startswith(user_text)


"""
IS_ECHO="""def _is_echo(user_text: str, assistant_texts: list[str] | AssistantEchoIndex) -> bool:
    \"\"\"Recognize agent echoes without rescanning the whole session.\"\"\"
    u = " ".join(user_text.split())
    if ADDRESSES_OPERATOR.match(u):
        return True
    index = assistant_texts if isinstance(assistant_texts, AssistantEchoIndex) else AssistantEchoIndex(assistant_texts)
    return index.matches_normalized(u)
"""
def patch_text(text):
    if "from bisect import bisect_left" not in text: text=text.replace("import argparse\n","import argparse\nfrom bisect import bisect_left\n",1)
    a=text.find("class AssistantEchoIndex")
    if a<0: a=text.index("def _is_echo(")
    b=text.index("\ndef session_events",a)
    text=text[:a]+INDEX_CLASS+IS_ECHO+text[b:]
    old='''    assistant_texts = [" ".join(_msg_text(e).split()) for _, e in events
                       if (e.get("llm_message") or {}).get("role") == "assistant"]
    out = []
'''
    new='''    assistant_texts = [_msg_text(e) for _, e in events
                       if (e.get("llm_message") or {}).get("role") == "assistant"]
    assistant_index = AssistantEchoIndex(assistant_texts)
    out = []
'''
    if old in text: text=text.replace(old,new,1)
    return text.replace("if _is_echo(txt, assistant_texts):","if _is_echo(txt, assistant_index):",1)
def check(text):
    a=text.index("def _is_echo("); b=text.index("\ndef session_events",a); fn=text[a:b]
    s=text.index("def session_events"); e=text.find("\ndef classify",s); e=e if e>=0 else len(text); session=text[s:e]
    return "class AssistantEchoIndex" in text and "from bisect import bisect_left" in text and "for a in assistant_texts" not in fn and "assistant_index = AssistantEchoIndex(assistant_texts)" in session and "_is_echo(txt, assistant_index)" in session
def selftest():
    fixture='''import argparse\ndef _is_echo(user_text, assistant_texts):\n    for a in assistant_texts:\n        pass\n    return False\ndef session_events():\n    assistant_texts = [" ".join(_msg_text(e).split()) for _, e in events\n                       if (e.get("llm_message") or {}).get("role") == "assistant"]\n    out = []\n    if _is_echo(txt, assistant_texts):\n        pass\n'''
    fixed=patch_text(fixture); ok=check(fixed) and patch_text(fixed)==fixed; print("chat gatekeeper perf selftest: "+("PASS" if ok else "FAIL")); return 0 if ok else 1
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--check",action="store_true"); ap.add_argument("--fix",action="store_true"); ap.add_argument("--selftest",action="store_true"); a=ap.parse_args()
    if a.selftest: return selftest()
    text=SOURCE.read_text(encoding="utf-8")
    if a.fix:
        text=patch_text(text); SOURCE.write_text(text,encoding="utf-8")
    ok=check(text); print("chat gatekeeper performance: "+("PASS" if ok else "FAIL — quadratic scan")); return 0 if ok else 1
if __name__=="__main__": sys.exit(main())

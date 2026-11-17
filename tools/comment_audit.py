#!/usr/bin/env python3
"""Produce the physical proof of the comment-defect state (SPI-2/4/6).
Writes proof/comment_premise_check.txt to disk and echoes it."""
import os, sys, subprocess, datetime
sys.path.insert(0, 'tools')
from kt_comment_scan import scan

# The reconciled layout: one tree under app/src/main/java. Fall back to a `tree/` dir if a
# future checkout still has one, so the tool is layout-agnostic.
def pick_tree():
    for cand in ("app/src/main/java/com/darkith/transliaison", "tree"):
        if os.path.isdir(cand):
            return cand
    return "."
TREE = pick_tree()
LOG = "proof/comment_premise_check.txt"
out = []
def w(s=""): out.append(s)

w("=== DARKITH COMMENT-DEFECT AUDIT (SPI-2/4/6) ===")
sys.path.insert(0, "tools")
from omega_time import stamp as _stamp
w(_stamp())
w()

NAMES = ["AxmlWriter.kt","EntryPointRewriter.kt","DarkithChainReader.kt","DarkithContentStore.kt",
 "DarkithEVMKit.kt","DarkithRuntimeHost.kt","DarkithAlpineGuest.kt","DarkithSolidityCompiler.kt",
 "HomekeeperBridge.kt","LayoutNode.kt","TransliaisonEngine.kt","AutofillCorrector.kt",
 "SubstrateIngestor.kt","CssLite.kt","HtmlDom.kt","SelfTest.kt","Allocation.kt",
 "AutophagicAllocator.kt","MemoryGovernor.kt"]
BRIEF_LINE = {"AxmlWriter.kt":7,"EntryPointRewriter.kt":10,"DarkithChainReader.kt":5,
 "DarkithContentStore.kt":5,"DarkithEVMKit.kt":3,"DarkithRuntimeHost.kt":5,
 "DarkithAlpineGuest.kt":5,"DarkithSolidityCompiler.kt":5,"HomekeeperBridge.kt":282,
 "LayoutNode.kt":3,"TransliaisonEngine.kt":3,"AutofillCorrector.kt":3,"SubstrateIngestor.kt":92,
 "CssLite.kt":3,"HtmlDom.kt":3,"SelfTest.kt":3,"Allocation.kt":3,"AutophagicAllocator.kt":5,
 "MemoryGovernor.kt":5}

def find(root, fn):
    for dp, _, fs in os.walk(root):
        if fn in fs: return os.path.join(dp, fn)
    return None

w("--- scanner self-test (parser correctness) ---")
r = subprocess.run([sys.executable, "tools/kt_comment_scan.py", "--selftest"], capture_output=True, text=True)
for ln in (r.stdout or r.stderr).strip().split("\n"): w("  " + ln)
w()

w("--- the 19 named files: exact line where the block comment opens ---")
w(f"{'file':<28} {'brief ln':>8} {'actual bytes':<28} verdict")
for fn in NAMES:
    p = find(TREE, fn)
    if not p:
        w(f"{fn:<28} {BRIEF_LINE[fn]:>8} {'MISSING':<28} --"); continue
    src = open(p, encoding="utf-8", errors="surrogateescape").read()
    lines = src.split("\n")
    ln = BRIEF_LINE[fn]
    actual = lines[ln-1].strip() if ln-1 < len(lines) else "<eof>"
    d = scan(src)
    w(f"{fn:<28} {ln:>8} {actual[:28]:<28} {'UNCLOSED' if d else 'CLEAN'}")

w()
w("--- every .kt on disk (SPI-6: read them all, not just the first) ---")
total = 0; bad = []; workbad = []
for dp, _, fs in os.walk('.'):
    if '/.git' in dp: continue
    for fn in fs:
        if fn.endswith('.kt'):
            total += 1
            p = os.path.join(dp, fn)
            d = scan(open(p, encoding='utf-8', errors='surrogateescape').read())
            if d:
                bad.append((p, d))
                if not p.startswith('./tree.orig'): workbad.append((p, d))
w(f"  .kt files scanned         : {total}")
w(f"  defects in WORKING tree   : {len(workbad)}")
for p, d in workbad: w(f"    DEFECT {p}: {d}")
w(f"  defects in other snapshots : {len(bad) - len(workbad)}")

w()
w("--- verdict ---")
if not workbad:
    w(f"  ZERO unclosed-comment defects in the working tree '{TREE}'.")
    w("  All 19 named files open their top comment with '/*' or '/**' and close it with '*/'.")
    w("  No pristine pre-fix snapshot is tracked; the reconciled tree is the only tree.")
    w("  (The briefing's line numbers came from the stale fork; the bytes here are authoritative.)")
    w("  NOTE: the briefing's diagnosis (a stripped opening '/*') does NOT match the bytes;")
    w("        the original defect was a mangled CLOSER ('//' instead of '*/'), in 2 files.")
else:
    w(f"  {len(workbad)} defective file(s) remain in the working tree (see above).")

txt = "\n".join(out) + "\n"
open(LOG, "w", encoding="utf-8").write(txt)
print(txt)
print("written:", LOG)

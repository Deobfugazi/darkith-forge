#!/usr/bin/env python3
"""synchrony_gate.py — enforces the SYNCHRONY BYLAW (MUST #23/#24, DARKITH.md §31).

The law: synchrony IS time tracking. Every app and every bot carries timestamp awareness,
and the clock is AUTO-GENERATED, never hand-written per surface. A document must be able to
sort diachronically; a log must carry the time it was written.

This gate proves the whole chain, not a claim about it:
  1. the generator exists and its output is DERIVED, not hand-edited — regenerating must
     reproduce build/gen/omega_time.{js,py} byte-for-byte (a drifted copy fails);
  2. every app surface carries the current runtime (build/inject_synchrony.py --check);
  3. every app surface carries a live clock readout (the Operator sees the time/date);
  4. the studio editor stamps the time on SAVE and writes a sortable ISO key (diachronic);
  5. the bot (tools/darkbot.py) logs through the generated runtime (timestamped output);
  6. the runtime exposes a diachronic sort key (iso/sortBy).

Fails if any link is missing — an app with no clock, or a bot with no timestamp, is a
surface that cannot be placed in time.
"""
import hashlib
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
GEN = ROOT / "build/gen_synchrony.py"
INJ = ROOT / "build/inject_synchrony.py"
GEN_JS = ROOT / "build/gen/omega_time.js"
GEN_PY = ROOT / "build/gen/omega_time_runtime.py"
SURFACES = sorted((ROOT / "app/src/main/assets").glob("*.html"))
BOT = ROOT / "tools/darkbot.py"
STUDIO = ROOT / "app/src/main/assets/darkith_ui.html"


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def main() -> int:
    fails = []

    # 1. generator present + output is derived (regenerate and compare)
    if not GEN.is_file() or not INJ.is_file():
        fails.append("synchrony generator/injector missing (build/gen_synchrony.py / inject_synchrony.py)")
    elif not (GEN_JS.is_file() and GEN_PY.is_file()):
        fails.append("generated runtime missing (run build/gen_synchrony.py)")
    else:
        before = {p: sha(p.read_bytes()) for p in (GEN_JS, GEN_PY)}
        r = subprocess.run([sys.executable, str(GEN)], capture_output=True, text=True)
        after = {p: sha(p.read_bytes()) for p in (GEN_JS, GEN_PY)}
        if r.returncode != 0:
            fails.append(f"generator failed: {r.stderr.strip()[:120]}")
        elif before != after:
            drifted = [p.name for p in before if before[p] != after[p]]
            fails.append(f"generated runtime is HAND-EDITED (not derived): {drifted}")

    # 2. every surface carries the current runtime
    if INJ.is_file():
        r = subprocess.run([sys.executable, str(INJ), "--check"], capture_output=True, text=True)
        if r.returncode != 0:
            fails.append(f"a surface is not current: {r.stdout.strip()[:160] or r.stderr.strip()[:160]}")

    # 3. every surface carries a live clock readout
    for s in SURFACES:
        html = s.read_text(encoding="utf-8", errors="replace")
        if "omega-clock" not in html or "omegaTime.stamp()" not in html:
            fails.append(f"{s.name}: no live clock readout (must show time+date)")

    # 4. the editor stamps the time on save with a sortable key
    if STUDIO.is_file():
        ui = STUDIO.read_text(encoding="utf-8", errors="replace")
        if "stampedBody" not in ui or "omegaTime.iso()" not in ui:
            fails.append("studio editor does not stamp the time on save (no stampedBody/iso key)")
        if not re.search(r"function saveDoc", ui):
            fails.append("studio editor has no saveDoc to stamp")
    else:
        fails.append("studio surface missing (app/src/main/assets/darkith_ui.html)")

    # 5. the bot logs through the generated runtime
    if BOT.is_file():
        b = BOT.read_text(encoding="utf-8", errors="replace")
        if "from omega_time import log" not in b and "omega_time" not in b:
            fails.append("tools/darkbot.py does not log through the generated clock")
        if "tlog(" not in b:
            fails.append("tools/darkbot.py has no timestamped log calls")
    else:
        fails.append("bot missing (tools/darkbot.py)")

    # 6. the runtime exposes a diachronic sort key
    if GEN_JS.is_file():
        js = GEN_JS.read_text(encoding="utf-8")
        if "sortBy" not in js or "iso" not in js:
            fails.append("runtime exposes no diachronic sort key (iso/sortBy)")

    if fails:
        print(f"synchrony_gate: FAIL — {len(fails)} problem(s):")
        for f in fails:
            print("  " + f)
        return 1
    print(f"synchrony_gate: PASS — {len(SURFACES)} surface(s) + bot carry the generated clock; "
          f"save stamps a diachronic key")
    return 0


if __name__ == "__main__":
    sys.exit(main())

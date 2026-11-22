#!/usr/bin/env python3
"""savf_reach_test.py — phi4 reachability must credit only real calls.

A module body frame and the first function defined in it share the same
`co_firstlineno`, so crediting a call by (file, line) alone marks a function
defined on line 1 as entered merely because its module was imported. That is a
false pass in the one gate whose job is to prove a function was exercised: the
tool would attest coverage of code no test ever ran. These cases drive real
subprocesses and real traced calls, so the fix is proven, not asserted."""
import json
import os
import pathlib
import subprocess
import sys
import tempfile

SAVF = pathlib.Path(__file__).resolve().parent.parent.parent / "savf.py"

FAILS = []


def check(name, ok, detail=""):
    print(f"  {'ok  ' if ok else 'FAIL'} {name}" + (f" - {detail}" if detail else ""))
    if not ok:
        FAILS.append(name)


def reach(root, test_module):
    p = subprocess.run([sys.executable, str(SAVF), "reach", "--root", str(root),
                        "--src", str(root), "--test", test_module],
                       capture_output=True, text=True, timeout=300)
    if p.returncode not in (0, 1):
        raise RuntimeError(f"reach failed ({p.returncode}): {p.stderr[-600:]}")
    return json.loads(p.stdout)


def write(d, name, text):
    (d / name).write_text(text)


def main():
    print("== importing a module enters none of its functions ==")
    d = pathlib.Path(tempfile.mkdtemp())
    write(d, "mod.py", "def alpha():\n    return 1\n\n\ndef beta():\n    return 2\n")
    write(d, "t_imp.py", "import mod\n")
    r = reach(d, "t_imp")
    check("an import credits nothing", r["entered"] == 0, r["entered"])
    check("every function is missed", len(r["missed"]) == 2,
          [m["function"] for m in r["missed"]])

    print("== a real call credits exactly the function called ==")
    write(d, "t_call.py", "import mod\nmod.alpha()\n")
    r = reach(d, "t_call")
    check("one call credits one function", r["entered"] == 1, r["entered"])
    check("the uncalled one is still missed",
          [m["function"] for m in r["missed"]] == ["beta"],
          [m["function"] for m in r["missed"]])

    print("== a function on line 1 is not credited by its module frame ==")
    write(d, "m2.py", "def first():\n    return 1\n")
    write(d, "t_none.py", "import m2\n")
    r = reach(d, "t_none")
    names = [m["function"] for m in r["missed"] if "m2.py" in m["file"]]
    check("line-1 function stays missed", names == ["first"], names)

    print("== a method is credited by its own call, not the class body ==")
    write(d, "cls.py", "class K:\n    def m(self):\n        return 7\n")
    write(d, "t_cls.py", "import cls\n")
    r = reach(d, "t_cls")
    names = [m["function"] for m in r["missed"] if "cls.py" in m["file"]]
    check("an uninstantiated method is missed", names == ["m"], names)

    print("== --reach-test accepts a .py path, not only a dotted module ==")
    # runpy.run_module resolves dotted names, so the natural spelling
    # "t_path.py" used to die with a __path__ traceback and no verdict.
    write(d, "t_path.py", "import mod\nmod.beta()\n")
    r = reach(d, "t_path.py")
    check("a .py path is traced like its module name", r["entered"] == 1, r["entered"])
    check("the path form credits the right function",
          [m["function"] for m in r["missed"] if "mod.py" in m["file"]] == ["alpha"],
          [m["function"] for m in r["missed"] if "mod.py" in m["file"]])

    if FAILS:
        print(f"\nSAVF REACH TEST: FAIL ({len(FAILS)})")
        for f in FAILS:
            print("  -", f)
        return 1
    print("\nSAVF REACH TEST: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())

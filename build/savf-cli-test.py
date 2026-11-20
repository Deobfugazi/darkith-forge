#!/usr/bin/env python3
"""SAVF CLI contract tests.

Drives the real `savf.py` as a subprocess and asserts two things the tool
promises and must never break:

  * the corrected-core `selftest` passes, and
  * bad input produces a clean, non-zero error -- never a raw traceback, and
    never a silent "0 findings, all good" that would hide a missing file.

Run:  python3 build/savf-cli-test.py
"""
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
SAVF = ROOT / "savf.py"

results = []


def run(*args, **kw):
    return subprocess.run([sys.executable, str(SAVF), *args],
                          capture_output=True, text=True, **kw)


def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))


# 1. the tool's own corrected-core checks pass
r = run("selftest")
check("selftest exits 0", r.returncode == 0, r.stdout.strip()[-200:])
check("selftest reports ok", "selftest: ok" in r.stdout, r.stdout[-200:])

# 2. version is a real version string
r = run("--version")
check("--version prints a version", r.returncode == 0 and r.stdout.strip()[0].isdigit(), r.stdout.strip())

# 3. valid axis evaluation
r = run("axis", "--p0", "0,0", "--p1", "10,0", "--s", "0.5", "--tau", "1")
check("axis: midpoint of (0,0)->(10,0) is (5,0)", r.returncode == 0 and "[5.0, 0.0]" in r.stdout, r.stdout.strip())

# 4. axis with tau=-1 swaps the ends
r = run("axis", "--p0", "0,0", "--p1", "10,0", "--s", "0.5", "--tau", "-1")
check("axis: tau=-1 reverses start/end", "[10.0, 0.0]" in r.stdout and "[0.0, 0.0]" in r.stdout, r.stdout.strip())

# 5. out-of-range s is a clean error, not a traceback
r = run("axis", "--p0", "0,0", "--p1", "10,0", "--s", "5", "--tau", "1")
check("axis: s outside [0,1] exits non-zero", r.returncode != 0)
check("axis: s outside [0,1] has no traceback", "Traceback" not in r.stderr, r.stderr[-200:])
check("axis: s outside [0,1] explains the range", "s must lie in [0,1]" in (r.stdout + r.stderr), r.stdout + r.stderr)

# 5b. negative coordinates are ordinary data, not options
r = run("axis", "--p0", "-4,-8", "--p1", "4,8", "--s", "0.5", "--tau", "1")
check("axis: negative poles parse without a flag error", r.returncode == 0, r.stderr[-200:])
check("axis: negative poles give the right point", "[0.0, 0.0]" in r.stdout, r.stdout.strip())
r = run("axis", "--p0", "0,0", "--p1", "10,0", "--s", "0.5", "--tau", "-1")
check("axis: a space-separated negative tau parses", r.returncode == 0 and "[10.0, 0.0]" in r.stdout, r.stdout.strip() + r.stderr[-120:])

# 6. a missing scan target is an error, not a silent clean bill of health
r = run("scan", "/tmp/savf-does-not-exist-xyz.py")
check("scan: missing path exits non-zero", r.returncode != 0, r.stdout.strip())
check("scan: missing path says so", "no such file" in (r.stdout + r.stderr), r.stdout + r.stderr)

# 6b. a scan over zero Python files examined nothing, so it must SKIP (exit 3), never
# report "0 finding(s)" and exit 0 — that is indistinguishable from a clean bill of health.
with tempfile.TemporaryDirectory() as td:
    (pathlib.Path(td) / "note.txt").write_text("nothing to scan\n")
    r = run("scan", td)
    check("scan: empty tree exits 3 (skip), not 0", r.returncode == 3, f"rc={r.returncode}")
    check("scan: empty tree says nothing was examined",
          "SKIP" in (r.stdout + r.stderr) and "nothing was examined" in (r.stdout + r.stderr),
          (r.stdout + r.stderr)[-160:])

r = run("freeze", "definitely-not-here.py")
check("freeze: a missing file exits non-zero", r.returncode != 0, r.stdout.strip())
check("freeze: a missing file names the path, no traceback",
      "no such file" in (r.stdout + r.stderr) and "Traceback" not in r.stderr,
      (r.stdout + r.stderr)[-160:])

# 7. scan on a real file with a phantom import flags it as high
with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
    f.write("import zzz_not_a_real_module\ndef g():\n    return zzz_not_a_real_module.x\n")
    bad = f.name
r = run("scan", bad)
check("scan: phantom import is a high finding", r.returncode != 0 and "PHANTOM_IMPORT" in r.stdout, r.stdout.strip()[:200])

# 8. malformed JSON is a clean error
with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
    f.write("this is not json")
    badj = f.name
r = run("verdict", badj)
check("verdict: malformed JSON exits non-zero", r.returncode != 0)
check("verdict: malformed JSON has no traceback", "Traceback" not in r.stderr, r.stderr[-200:])

# 9. sign() agrees with the documented handedness
r1 = run("sign", "--chart", "raster", "--axis", "x", "--move", "R2L")
r2 = run("sign", "--chart", "sbaf0", "--axis", "x", "--move", "R2L")
check("sign: raster R2L is -1", r1.returncode == 0 and r1.stdout.strip() == "-1", r1.stdout.strip())
check("sign: sbaf0 R2L is +1", r2.returncode == 0 and r2.stdout.strip() == "1", r2.stdout.strip())

# 10. freeze/check-freeze round-trips in a scratch directory.
#     freeze writes `.savf/contract.lock` relative to CWD, so the whole
#     round-trip must run inside the temp dir -- never in the repo.
with tempfile.TemporaryDirectory() as td:
    contract = pathlib.Path(td) / "contract.py"
    contract.write_text("THETA = 0.6\n")
    r = run("freeze", str(contract), cwd=td)
    check("freeze: seals a file", r.returncode == 0 and "seal" in r.stdout, r.stdout.strip())
    check("freeze: writes its lock into the CWD, not the repo",
          (pathlib.Path(td) / ".savf" / "contract.lock").exists() and not (ROOT / ".savf").exists())
    r = run("check-freeze", cwd=td)
    check("check-freeze: clean after freeze", r.returncode == 0, r.stdout.strip())
    contract.write_text("THETA = 0.0\n")   # tamper
    r = run("check-freeze", cwd=td)
    check("check-freeze: detects tampering", r.returncode != 0, r.stdout.strip())

# 11. reach/mutate with a --src that is not there is an error, never a silent
#     "0 functions / nothing missed" -- a confident green that hides a missing
#     path, exactly what the scan test above forbids.
r = run("reach", "--root", ".", "--src", "/tmp/savf-does-not-exist-xyz",
        "--test", "x")
check("reach: missing --src exits non-zero", r.returncode != 0, r.stdout.strip())
check("reach: missing --src says so, no traceback",
      "no such file" in (r.stdout + r.stderr) and "Traceback" not in r.stderr,
      (r.stdout + r.stderr)[-160:])
r = run("mutate", "--root", ".", "--src", "/tmp/savf-does-not-exist-xyz",
        "--test-cmd", "true")
check("mutate: missing --src exits non-zero", r.returncode != 0, r.stdout.strip())
check("mutate: missing --src says so, no traceback",
      "no such file" in (r.stdout + r.stderr) and "Traceback" not in r.stderr,
      (r.stdout + r.stderr)[-160:])

# 12. a --src directory with no Python in it is an error too, not an empty pass.
with tempfile.TemporaryDirectory() as td:
    (pathlib.Path(td) / "note.txt").write_text("nothing to scan\n")
    r = run("reach", "--root", td, "--src", td, "--test", "x")
    check("reach: empty --src tree exits non-zero", r.returncode != 0, r.stdout.strip())
    check("reach: empty --src tree says so", "no Python source" in (r.stdout + r.stderr),
          (r.stdout + r.stderr)[-160:])

fails = [x for x in results if not x[1]]
for name, ok, detail in results:
    print(f"  {'ok  ' if ok else 'FAIL'} {name}" + (f"  -- {detail}" if detail and not ok else ""))
print(f"\nSAVF-CLI: {'PASS' if not fails else 'FAIL'} ({len(results)-len(fails)}/{len(results)})")
sys.exit(0 if not fails else 1)

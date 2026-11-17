#!/usr/bin/env python3
"""convergence_gate.py — prove two independent derivations AGREE (Operator's parallel protocol).

The Operator runs at least two agents in parallel and requires their outputs to CONVERGE in
the repo. Two agents that disagree are a divergence defect; a claim that "they agree" without
a comparison is a note (SPI-15). This gate is the comparison.

It derives the same facts through two INDEPENDENT implementations and requires byte-exact
agreement, then records the result to `proof/convergence.json`:

  A. the Operator's clock — via the Python runtime AND the JS runtime (two languages)
  B. the working tree content — via `git hash-object` AND a sha256 walk (two methods)
  C. the circadian phase — via both runtimes (two implementations)

Disagreement fails the gate. A pass means the two derivations converged on the same bytes,
which is what lets a second agent trust the first agent's board without re-doing the work.

  python3 tools/convergence_gate.py            compare, write proof, exit 0/1
  python3 tools/convergence_gate.py --check     compare only (no proof write)
"""
import hashlib
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "build" / "gen"))
sys.path.insert(0, str(ROOT / "tools"))

from omega_time_runtime import iso, phase, stamp  # noqa: E402

PROOF = ROOT / "proof/convergence.json"
NODE = "node"


def js_eval(expr: str) -> str | None:
    """Derive a fact through the JS runtime (the second, independent implementation)."""
    script = f'const t=require("{ROOT}/build/gen/omega_time.js");process.stdout.write(String({expr}));'
    try:
        r = subprocess.run([NODE, "-e", script], capture_output=True, text=True, timeout=30)
        return r.stdout if r.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def tree_blobs_git() -> dict:
    """Method 1: git's own object store — the authoritative (path -> blob sha1) map."""
    out = subprocess.run(["git", "-C", str(ROOT), "ls-files", "-s", "-z"],
                         capture_output=True, text=True).stdout
    m = {}
    for rec in out.split("\0"):
        if not rec:
            continue
        meta, _, path = rec.partition("\t")
        if path:
            m[path] = meta.split()[1]
    return m


def _tracked_files() -> list:
    """Null-delimited so a path with a space is never split (the bug that made two
    space-named surfaces look untracked)."""
    out = subprocess.run(["git", "-C", str(ROOT), "ls-files", "-z"],
                         capture_output=True, text=True).stdout
    return [f for f in out.split("\0") if f]


def tree_blobs_python() -> dict:
    """Method 2: an INDEPENDENT implementation of git's blob hash (sha1 of 'blob <len>\\0'+body).
    Agrees with method 1 iff the working tree matches the index — a real cross-check."""
    m = {}
    for f in _tracked_files():
        p = ROOT / f
        if p.is_file():
            body = p.read_bytes()
            m[f] = hashlib.sha1(b"blob %d\0" % len(body) + body).hexdigest()
    return m


def main() -> int:
    write = "--check" not in sys.argv[1:]
    fails, facts = [], {}

    # A. the clock, two implementations — compared on a FIXED instant so the comparison is
    # deterministic (two now() calls can straddle a second boundary and false-fail).
    from datetime import datetime
    probe = datetime(2026, 11, 18, 6, 30, 0, tzinfo=__import__("datetime").timezone(__import__("datetime").timedelta(hours=8)))
    probe_ms = int(probe.timestamp() * 1000)
    py_stamp, js_stamp = stamp(probe), js_eval(f"t.stamp(new Date({probe_ms}))")
    facts["clock.py"] = py_stamp
    facts["clock.js"] = js_stamp
    if not js_stamp:
        fails.append("JS runtime unavailable — the second derivation did not run")
    elif py_stamp != js_stamp:
        fails.append(f"clock diverged: py='{py_stamp}' != js='{js_stamp}'")

    py_iso, js_iso = iso(probe), js_eval(f"t.iso(new Date({probe_ms}))")
    facts["iso.py"] = py_iso
    facts["iso.js"] = js_iso
    if js_iso and py_iso != js_iso:
        fails.append(f"ISO key diverged: py='{py_iso}' != js='{js_iso}'")

    # C. the circadian phase, two implementations — same fixed instant, both sides of the
    # active window (06:30 is active; 02:00 is rest) so the phase logic is really compared.
    rest_ms = probe_ms - 4 * 3600 * 1000
    for label, ms in (("active", probe_ms), ("rest", rest_ms)):
        pyp, jsp = phase(datetime.fromtimestamp(ms / 1000, probe.tzinfo)), js_eval(f"t.phase(new Date({ms}))")
        facts[f"phase.{label}.py"] = pyp
        facts[f"phase.{label}.js"] = jsp
        if jsp and pyp != jsp:
            fails.append(f"circadian phase ({label}) diverged: py='{pyp}' != js='{jsp}'")

    # B. the tree — two independent implementations of the same fact (path -> blob sha1).
    # git's index (method 1) vs a from-scratch git-blob hasher (method 2). They agree iff the
    # working tree matches what is staged; a divergence is a real uncommitted-drift defect.
    mg, mw = tree_blobs_git(), tree_blobs_python()
    # generated evidence is the gate's own output, not source under test — a written proof
    # file is expected to differ from the index until it is committed.
    def _generated(p: str) -> bool:
        return p.startswith("proof/")
    only_g = sorted(p for p in set(mg) - set(mw) if not _generated(p))
    only_w = sorted(p for p in set(mw) - set(mg) if not _generated(p))
    differ = sorted(p for p in set(mg) & set(mw) if mg[p] != mw[p] and not _generated(p))
    facts["tree.files"] = len(mw)
    facts["tree.blobsha.agree"] = not (only_g or only_w or differ)
    if only_g:
        fails.append(f"tree: {len(only_g)} file(s) in git index but not hashed by the walk: {only_g[:5]}")
    if only_w:
        fails.append(f"tree: {len(only_w)} file(s) hashed by the walk but not in git: {only_w[:5]}")
    if differ:
        fails.append(f"tree: {len(differ)} file(s) whose bytes differ from the index "
                     f"(uncommitted drift): {differ[:5]}")

    facts["converged"] = not fails
    facts["agent"] = "primary"
    if write:
        PROOF.parent.mkdir(parents=True, exist_ok=True)
        PROOF.write_text(json.dumps(facts, indent=2) + "\n", encoding="utf-8")

    if fails:
        print(f"convergence_gate: FAIL — {len(fails)} divergence(s):")
        for f in fails:
            print("  " + f)
        return 1
    print(f"convergence_gate: PASS — clock (py==js), iso, phase (active+rest), tree "
          f"({facts['tree.files']} files: git index == independent blob hash); clock={facts['clock.py']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

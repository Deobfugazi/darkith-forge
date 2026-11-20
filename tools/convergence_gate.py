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
  D. the source universe — via the examiner's iterator, a filesystem walk, AND git's index
     (three methods; NEVER #19: no source escapes the trial, none lives only on disk)

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


def source_universe_examiner() -> list:
    """Derivation 1: the file universe the SOURCE INSPECTOR actually examined — the tree
    NEVER #19 says must have passed the routine trial (no unexamined source)."""
    sys.path.insert(0, str(ROOT / "tools"))
    import source_inspector as si
    src_root = si._root_of(si.DEFAULT_ROOT)
    rel = src_root.relative_to(ROOT)
    return sorted(str(p.relative_to(ROOT)) for p in si.iter_sources(src_root))


def source_universe_walk() -> list:
    """Derivation 2: an independent filesystem walk for the same extensions. Agrees with
    derivation 1 iff the examiner's iterator sees every source file on disk."""
    import source_inspector as si
    src_root = si._root_of(si.DEFAULT_ROOT)
    exts = si.KT_EXTS | si.JS_EXTS
    return sorted(str(p.relative_to(ROOT)) for p in src_root.rglob("*")
                  if p.is_file() and p.suffix in exts)


def source_universe_git() -> list:
    """Derivation 3: the source files git TRACKS (the authoritative server-of-record). Agrees
    with the walk iff every source file is committed — no source survives only on disk."""
    import source_inspector as si
    src_root = si._root_of(si.DEFAULT_ROOT)
    rel = src_root.relative_to(ROOT)
    exts = si.KT_EXTS | si.JS_EXTS
    out = []
    for f in _tracked_files():
        pf = pathlib.PurePosixPath(f)
        if pf.suffix in exts and pf.is_relative_to(pathlib.PurePosixPath(str(rel))):
            out.append(f)
    return sorted(out)


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

    # C. the circadian phase, two implementations — same fixed instants, both sides of the
    # active window (06:30 active; 02:30 rest) so the phase logic is really compared.
    # Each side is handed the same epoch ms; the Python side coerces it via the runtime.
    for label, ms in (("active", probe_ms), ("rest", probe_ms - 4 * 3600 * 1000)):
        from datetime import datetime as _dt
        from datetime import timezone as _tz
        py_instant = _dt.fromtimestamp(ms / 1000.0, _tz.utc)
        pyp, jsp = phase(py_instant), js_eval(f"t.phase(new Date({ms}))")
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
    # Count what is under test, not the audit trail. The divergence checks above
    # already skip generated proof/ evidence; the count must use the same universe,
    # or committing a cycle's own receipts changes the number and this file drifts
    # from the seal that recorded it.
    facts["tree.files"] = len([p for p in mw if not _generated(p)])
    facts["tree.blobsha.agree"] = not (only_g or only_w or differ)
    if only_g:
        fails.append(f"tree: {len(only_g)} file(s) in git index but not hashed by the walk: {only_g[:5]}")
    if only_w:
        fails.append(f"tree: {len(only_w)} file(s) hashed by the walk but not in git: {only_w[:5]}")
    if differ:
        fails.append(f"tree: {len(differ)} file(s) whose bytes differ from the index "
                     f"(uncommitted drift): {differ[:5]}")

    # D. the SOURCE UNIVERSE — three independent derivations of the same set (NEVER #19: no
    # unexamined source). The examiner's iterator, a filesystem walk, and git's index must
    # agree; a disagreement means a source file escaped the trial, or survives only on disk.
    ux, uw, ug = source_universe_examiner(), source_universe_walk(), source_universe_git()
    facts["source.examiner"] = len(ux)
    facts["source.walk"] = len(uw)
    facts["source.git"] = len(ug)
    facts["source.agree"] = ux == uw == ug
    if ux != uw:
        fails.append(f"source: examiner saw {len(ux)} but the walk found {len(uw)} "
                     f"(escaped the trial: {sorted(set(uw) - set(ux))[:5]})")
    if uw != ug:
        fails.append(f"source: the walk found {len(uw)} but git tracks {len(ug)} "
                     f"(on disk only, uncommitted: {sorted(set(uw) - set(ug))[:5]})")

    facts["converged"] = not fails
    facts["agent"] = "primary"
    # A proof file is a claim about the tree, so it may only be written from a state that
    # supports the claim. Persisting a diverged result records a transient as if it were the
    # state: the tree gets fixed, the stale record stays, and a reader downstream trusts a
    # false attestation. Refuse the write, leaving the last true record in place.
    if write and fails:
        print(f"convergence_gate: proof NOT written — {len(fails)} divergence(s) present; "
              f"a record written now would attest a state that stops holding once fixed")
    elif write:
        PROOF.parent.mkdir(parents=True, exist_ok=True)
        PROOF.write_text(json.dumps(facts, indent=2) + "\n", encoding="utf-8")

    if fails:
        print(f"convergence_gate: FAIL — {len(fails)} divergence(s):")
        for f in fails:
            print("  " + f)
        return 1
    print(f"convergence_gate: PASS — clock (py==js), iso, phase (active+rest), tree "
          f"({facts['tree.files']} files: git index == independent blob hash), source "
          f"universe ({facts['source.walk']} files: examiner == walk == git); clock={facts['clock.py']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

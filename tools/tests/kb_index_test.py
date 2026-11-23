#!/usr/bin/env python3
"""kb_index_test.py — the generated knowledge-base index is judged by running it (SPI-38).

`docs/INDEX.md` and `docs/kb_manifest.json` are generated from the tracked bytes. The gate
that keeps them honest shipped without a test of its own, so the two ways it can rot were
never demonstrated: a hand-edit that drifts from the generator, and a deletion that hides a
file from coverage. Both are breaches the gate exists to catch, so both are the point here.

Every case drives a real temporary git repository through the real CLI. No mocks: a gate
tested against a mock proves the mock, not the gate."""
import pathlib
import subprocess
import sys
import tempfile

TOOL = pathlib.Path(__file__).resolve().parent.parent / "kb_index.py"
FAILS = []


def check(name, ok, detail=""):
    print(f"  {'ok  ' if ok else 'FAIL'} {name}" + (f" — {detail}" if detail else ""))
    if not ok:
        FAILS.append(name)


def repo():
    d = pathlib.Path(tempfile.mkdtemp())
    subprocess.run(["git", "init", "-q"], cwd=d, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=d, check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=d, check=True)
    (d / "tools").mkdir()
    (d / "tools" / "kb_index.py").write_bytes(TOOL.read_bytes())
    (d / "README.md").write_text("# readme\n")
    (d / "AGENTS.md").write_text("# agents\n")
    (d / "docs").mkdir()
    (d / "docs" / "a.md").write_text("alpha\n")
    (d / "docs" / "b.md").write_text("beta\n")
    git(d, "add", "-A")
    git(d, "commit", "-q", "-m", "seed")
    return d


def git(d, *args):
    return subprocess.run(["git", *args], cwd=d, capture_output=True, text=True)


def run(d, *args):
    p = subprocess.run([sys.executable, "tools/kb_index.py", *args],
                       cwd=d, capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


def main():
    print("== a fresh tree with no generated index fails, and says which file ==")
    d = repo()
    rc, out = run(d)
    check("missing index fails", rc == 1, f"exit {rc}")
    check("both artifacts named", "INDEX.md is missing" in out
          and "kb_manifest.json is missing" in out, out.strip().splitlines()[0])

    print("== the generator is authoritative and byte-idempotent ==")
    rc, out = run(d, "--write")
    check("write succeeds", rc == 0, f"exit {rc}")
    first = (d / "docs" / "INDEX.md").read_bytes(), (d / "docs" / "kb_manifest.json").read_bytes()
    rc, _ = run(d, "--write")
    second = (d / "docs" / "INDEX.md").read_bytes(), (d / "docs" / "kb_manifest.json").read_bytes()
    check("two runs are byte-identical", first == second)
    rc, out = run(d)
    check("gate passes on fresh output", rc == 0, out.strip())

    print("== a hand-edit of INDEX.md is caught (tamper) ==")
    idx = d / "docs" / "INDEX.md"
    idx.write_bytes(idx.read_bytes() + b"\n")
    rc, out = run(d)
    check("tampered index fails", rc == 1, f"exit {rc}")
    check("failure names INDEX.md", "INDEX.md is stale" in out, out.strip())

    print("== a hand-edit of the manifest is caught (tamper) ==")
    run(d, "--write")
    man = d / "docs" / "kb_manifest.json"
    man.write_bytes(man.read_bytes().replace(b'"bytes"', b'"bytez"', 1))
    rc, out = run(d)
    check("tampered manifest fails", rc == 1, f"exit {rc}")
    check("failure names kb_manifest.json", "kb_manifest.json is stale" in out, out.strip())

    print("== a deleted row is caught (removal) ==")
    run(d, "--write")
    man = d / "docs" / "kb_manifest.json"
    import json
    data = json.loads(man.read_text())
    files = data["files"]
    before = len(files)
    files.pop(0)
    man.write_text(json.dumps(data, indent=2) + "\n")
    rc, out = run(d)
    check("manifest with a removed row fails", rc == 1 and len(files) < before,
          f"exit {rc}, {before}->{len(files)}")

    print("== a new tracked readable file is not silently omitted (coverage) ==")
    run(d, "--write")
    (d / "docs" / "c.md").write_text("gamma\n")
    git(d, "add", "-A")
    git(d, "commit", "-q", "-m", "add c")
    rc, out = run(d)
    check("new tracked file fails coverage", rc == 1, f"exit {rc}")
    run(d, "--write")
    rc, out = run(d)
    check("after --write it is covered", rc == 0, out.strip())
    check("new file is in the manifest", "docs/c.md" in (d / "docs" / "kb_manifest.json").read_text())

    print("== an untracked scratch file is NOT indexed (only tracked bytes count) ==")
    (d / "docs" / "scratch.md").write_text("never committed\n")
    rc, out = run(d)
    check("untracked file does not fail the gate", rc == 0, out.strip())
    check("untracked file absent from manifest",
          "scratch.md" not in (d / "docs" / "kb_manifest.json").read_text())

    print("== deleting a tracked readable file is caught (coverage shrinks) ==")
    run(d, "--write")
    (d / "docs" / "b.md").unlink()
    git(d, "add", "-A")
    git(d, "commit", "-q", "-m", "drop b")
    rc, out = run(d)
    check("shrunken corpus fails until regenerated", rc == 1, f"exit {rc}")

    print()
    if FAILS:
        print(f"KB INDEX TEST: FAIL ({len(FAILS)}): {FAILS}")
        return 1
    print("KB INDEX TEST: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())

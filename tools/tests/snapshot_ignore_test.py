#!/usr/bin/env python3
"""snapshot_ignore_test.py — the tree snapshot's ignore rule is judged by running it.

Regression for recovery run #45167088671: post-seal I9 verification rejected
.forge_work/termkit-core.audit.js and build/omega/omega-ui.png as unsealed drift.
Both paths are runtime-created and gitignored; the snapshot chose not to believe
.gitignore because its ignored-untracked inventory was cached in a module global from
the FIRST snapshot (taken before CI created those files) and because the git query ran
against module-global ROOT instead of the root the caller passed. This file proves the
invariant on real temporary git repositories, never mocks:

  - a snapshot hashes every tracked file even when its name matches an ignore pattern;
  - an untracked file git currently ignores under that root is excluded;
  - fresh ignore state per snapshot: a file that BECOMES ignored between snapshots
    never appears as A/B drift;
  - a non-ignored sentinel created between snapshots IS reported as real drift;
  - the ignore rules consulted are the ones of the passed root, not any module global;
  - a git query failure is fail-closed (GitInventoryError), never a silent empty set.
"""
import pathlib
import shutil
import subprocess
import sys
import tempfile

TOOLS_DIR = pathlib.Path(__file__).resolve().parent.parent  # tools/
sys.path.insert(0, str(TOOLS_DIR))

import revitalization as rv  # noqa: E402

FAILS = []


def check(name, ok, detail=""):
    print(f"  {'ok  ' if ok else 'FAIL'} {name}" + (f" — {detail}" if detail else ""))
    if not ok:
        FAILS.append(name)


def fresh_repo():
    d = tempfile.mkdtemp()
    root = pathlib.Path(d)
    (root / "src").mkdir()
    (root / "src" / "tracked.txt").write_text("tracked bytes\n")
    (root / "TASKS.md").write_text("# board\n")
    (root / ".gitignore").write_text(".forge_work/\nbuild/omega/*.png\n")
    git(root, "init", "-q")
    git(root, "add", "-A")
    git(root, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "seed")
    return root


def git(root, *args):
    return subprocess.run(["git", *args], cwd=str(root), capture_output=True,
                          text=True, check=False)


def main():
    print("== snapshot A: baseline, then the exact CI-created runtime files ==")
    root = fresh_repo()
    snap_a = rv.tree_snapshot(root)
    check("snapshot A hashes tracked files",
          "src/tracked.txt" in snap_a and "TASKS.md" in snap_a, str(sorted(snap_a)))
    # Runtime evidence, exactly the two paths the recovery run reported. They do not
    # exist yet: this mirrors S01, taken BEFORE ci.sh starts creating runtime files.
    (root / ".forge_work").mkdir()
    (root / ".forge_work" / "termkit-core.audit.js").write_text("audit payload\n")
    (root / "build").mkdir()
    (root / "build" / "omega").mkdir()
    (root / "build" / "omega" / "omega-ui.png").write_bytes(b"\x89PNG fake bytes\n")
    snap_b = rv.tree_snapshot(root)
    check("file that exists BEFORE the snapshot and is ignored now is excluded",
          all(p not in snap_b for p in
              (".forge_work/termkit-core.audit.js", "build/omega/omega-ui.png")),
          str(sorted(snap_b)))
    check("no ignored runtime file appears as A/B drift",
          set(snap_a) == set(snap_b), f"A={sorted(snap_a)} B={sorted(snap_b)}")

    print("== a non-ignored sentinel created after A is real drift, never swallowed ==")
    (root / "src" / "sentinel.py").write_text("uncommitted work\n")
    snap_c = rv.tree_snapshot(root)
    check("sentinel present in the fresh snapshot", "src/sentinel.py" in snap_c)
    drift = {p for p in set(snap_a) | set(snap_c) if snap_a.get(p) != snap_c.get(p)}
    check("drift names only the sentinel", drift == {"src/sentinel.py"}, str(sorted(drift)))

    print("== a tracked file matching an ignore pattern is still hashed ==")
    (root / ".gitignore").write_text(".forge_work/\nbuild/omega/*.png\nsrc/tracked.txt\n")
    # tracked.txt was committed BEFORE the rule, so git keeps tracking it (the `--others`
    # scope of the inventory). Tracked bytes are real bytes even when the name is hated.
    check("tracked-but-ignored file still hashed",
          "src/tracked.txt" in rv.tree_snapshot(root))

    print("== rules changed between snapshots: the current rules govern, nothing stale ==")
    (root / "witness.txt").write_text("suddenly ignorable\n")
    check("new untracked file appears before its rule exists",
          "witness.txt" in rv.tree_snapshot(root))
    (root / ".gitignore").write_text(".forge_work/\nbuild/omega/*.png\nwitness.txt\n")
    check("same file drops out once the CURRENT rule ignores it",
          "witness.txt" not in rv.tree_snapshot(root))
    # And the reverse direction, in a sibling repo, to prove no process-wide residue:
    root2 = fresh_repo()
    root2.joinpath("witness.txt").write_text("sibling bytes\n")
    check("sibling root with no such rule still reports the file",
          "witness.txt" in rv.tree_snapshot(root2))
    check("first root still honors ITS rule",
          "witness.txt" not in rv.tree_snapshot(root))

    print("== fail-closed: git cannot answer -> named error, never a silent empty set ==")
    bare = pathlib.Path(tempfile.mkdtemp())
    (bare / ".git").write_text("not a repository\n")
    raised = ""
    try:
        rv.ignored_inventory(bare)
    except rv.GitInventoryError as exc:
        raised = str(exc)
    except Exception as exc:  # noqa: BLE001 - wrong exception type is also a failure
        raised = f"WRONG TYPE: {type(exc).__name__}: {exc}"
    check("non-repository root raises GitInventoryError",
          raised and not raised.startswith("WRONG TYPE") and "git ls-files" in raised,
          raised)
    shutil.rmtree(bare)

    print("== inventory is untracked-only: tracked bytes never get misclassified ==")
    root3 = fresh_repo()
    root3.joinpath(".gitignore").write_text("src/tracked.txt\n")
    inv = rv.ignored_inventory(root3)
    check("tracked-ignored path not in the untracked inventory",
          "src/tracked.txt" not in inv, str(sorted(inv)))

    print()
    if FAILS:
        print(f"SNAPSHOT IGNORE TEST: FAIL ({len(FAILS)}): {FAILS}")
        return 1
    print("SNAPSHOT IGNORE TEST: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())

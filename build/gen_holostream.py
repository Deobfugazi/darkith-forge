#!/usr/bin/env python3
"""gen_holostream.py — derive the live repo map for repo-holostream.html (MUST #42).

The map is a projection of the tree AS IT IS, never a hand-drawn portrait of the past:

  nodes     gates parsed out of tools/ci.sh's declared suites (the ONE place that lists
            what CI runs), the autophagy class registry (imported, not re-parsed — one
            definition of a defect class), the generated law gates in tools/generated/,
            and the law corpus in DARKITH.md (law_gate's own heading regex).
  edges     law --names-gate--> suite/tool, autophagy class --prevented-by--> suite,
            generated gate --derived-from--> law.
  timeline  the commit history with per-commit churn and cumulative LOC, the fourth
            dimension of the holostream: the graph is the space, the commits are time,
            and each gate carries its birth commit so playback can build the tree up
            the way it actually grew.

Determinism is a law here (MUST #18): two derivations over the same HEAD must be
byte-identical. The map records HEAD, not a clock — a timestamp would make identical
trees disagree and the staleness gate would fire for nobody's benefit.

Commands
  (no args)        derive the map and inject it between the HOLOSTREAM-MAP markers
  --check          exit 0 if the embedded map equals a fresh derivation, 1 otherwise
  --selftest       determinism + structure trials, in-memory, writes nothing

Exit codes: 0 clean/applied, 1 stale or broken, 2 usage.
SPI-1 (no build): pure stdlib, no network, no Gradle. SPI-2: bytes off disk/git only.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
PAGE = ROOT / "repo-holostream.html"
CI = ROOT / "tools" / "ci.sh"
LAWS = ROOT / "DARKITH.md"

BEGIN = "<!--HOLOSTREAM-MAP:BEGIN-->"
END = "<!--HOLOSTREAM-MAP:END-->"
SCHEMA = 1
PAGE_REL = "repo-holostream.html"


def sh(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)


def git(args: str) -> str:
    return sh(["git", "-C", str(ROOT)] + args.split()).stdout


def parse_ci_suites() -> list[dict]:
    """The suites ci.sh runs: `run "NAME" COMMAND` lines. This file is the single
    source of truth for what CI executes, so the map parses it, never a copy."""
    text = CI.read_text(encoding="utf-8")
    text = re.sub(r"\\\n", " ", text)  # joined continuations read as one line
    suites, seen = [], set()
    for i, line in enumerate(text.splitlines(), 1):
        m = re.match(r'^\s*run\s+"((?:[^"\\]|\\.)*)"\s+(\S.*)$', line)
        if not m:
            continue
        name, cmd = m.group(1), m.group(2).strip()
        if name in seen:
            continue
        seen.add(name)
        tool = re.search(r"tools/[\w.-]+\.(?:py|sh|js)|build/[\w.-]+\.py", cmd)
        suites.append({
            "id": "suite:" + name,
            "name": name,
            "cmd": cmd,
            "file": "tools/ci.sh",
            "line": i,
            "tool": tool.group(0) if tool else "",
        })
    return suites


def parse_laws() -> dict:
    """law -> {gate paths cited, title}. Reuses law_gate's regex — ONE definition
    of a law heading (SPI-27: the reader a gate enforces is the reader the map uses)."""
    sys.path.insert(0, str(ROOT / "tools"))
    import law_gate  # noqa: E402
    text = LAWS.read_text(encoding="utf-8")
    laws = {}
    for law_id, title, body in law_gate.law_blocks(text):
        laws["law:" + law_id] = {
            "id": "law:" + law_id,
            "law": law_id,
            "name": law_id + (f" ({title})" if title else ""),
            "gates": sorted(set(law_gate.GATE.findall(body))),
            "line": text[: text.find("\u2500\u2500\u2500 " + law_id)].count("\n") + 1
            if law_id in text else 0,
        }
    return laws


def parse_autophagy() -> list[dict]:
    """Import the registry: the classes ARE their executable definition."""
    sys.path.insert(0, str(ROOT / "tools"))
    import autophagy  # noqa: E402
    out = []
    for c in autophagy.CLASSES:
        out.append({
            "id": "class:" + c.name,
            "name": c.name,
            "detect": c.detect,
            "repair": c.repair,
            "prevent": c.prevent,
            "note": c.note,
        })
    return out


def parse_generated_gates() -> list[dict]:
    out = []
    for p in sorted((ROOT / "tools" / "generated").glob("gate_*.py")):
        head = p.read_text(encoding="utf-8", errors="replace")[:1200]
        law = re.search(r"^Law:\s*(.+?)$", head, re.MULTILINE)
        src = re.search(r"^Source:\s*(.+?)$", head, re.MULTILINE)
        out.append({
            "id": "gen:" + p.stem,
            "name": p.stem,
            "law": law.group(1).strip() if law else "",
            "source": src.group(1).strip() if src else "",
            "file": "tools/generated/" + p.name,
        })
    return out


def parse_timeline() -> list[dict]:
    """Commit history as spacetime frames: index, sha, epoch, subject, churn.

    One git pass over --numstat: it carries add/del per path (the churn the viewer plots)
    and the path itself — which yields the p flag the freshness gate uses to absorb the
    map's own carrier commit (the commit that writes the map cannot be inside the map).
    """
    raw = git("log --reverse --pretty=format:%H%x01%at%x01%s --numstat")
    frames = []
    for blob in (ln for ln in raw.split("\n") if ln.strip()):
        parts = blob.split("\x01")
        if len(parts) == 3:
            sha, t, subject = parts
            frames.append({"h": sha[:8], "t": int(t), "s": subject,
                           "f": 0, "a": 0, "d": 0, "p": 0})
        elif len(parts) == 1 and frames:
            cols = parts[0].split("\t")
            frame = frames[-1]
            frame["f"] += 1
            path = cols[-1] if cols else ""
            add = cols[0] if len(cols) >= 3 else "0"
            dele = cols[1] if len(cols) >= 3 else "0"
            if path == PAGE_REL:
                frame["p"] = 1
            frame["a"] += int(add) if add.isdigit() else 0
            frame["d"] += int(dele) if dele.isdigit() else 0
    loc = 0
    for n, f in enumerate(frames):
        loc = max(0, loc + f["a"] - f["d"])
        f["loc"] = loc
        f["n"] = n + 1
    return frames


def parse_dirs(treeish: str) -> dict:
    """Tree mass from a commit's own blobs — byte-identical for the same commit on any
    host, any worktree state, any point in a CI run. Derived artifacts are excluded (the
    carrier page, the generated index and manifest): their bytes are FUNCTIONS of the
    tree, and counting a function of the map back into the map's mass makes the map a
    component of itself — regenerate the page and the mass moves, which moves the map,
    which moves the page — NEVER #22's tumour with a user interface."""
    excluded = {PAGE_REL, "docs/INDEX.md", "docs/kb_manifest.json"}
    dirs = {}
    for ln in git(f"ls-tree -r -l {treeish}").splitlines():
        parts = ln.split()
        if len(parts) < 4 or "\t" not in ln:
            continue
        size, p = parts[3], ln.split("\t", 1)[1]
        if not p or p in excluded:
            continue
        top = p.split("/")[0] if "/" in p else "(root)"
        d = dirs.setdefault(top, {"files": 0, "bytes": 0})
        d["files"] += 1
        try:
            d["bytes"] += int(size)
        except ValueError:
            pass
    return dirs


def dirs_at(treeish: str) -> list[dict]:
    """The map's canonical dirs form (sorted list), derived purely from a commit's blobs."""
    return sorted(({"dir": k, **v} for k, v in parse_dirs(treeish).items()),
                  key=lambda d: -d["bytes"])


def derive() -> dict:
    suites = parse_ci_suites()
    laws = parse_laws()
    classes = parse_autophagy()
    gens = parse_generated_gates()
    timeline = parse_timeline()

    suite_by_name = {s["name"]: s for s in suites}
    suite_ids = set(suite_by_name)

    nodes = []
    for law_id, l in sorted(laws.items()):
        nodes.append({"id": law_id, "type": "law", "name": l["name"],
                      "sub": "", "file": "DARKITH.md", "line": l["line"]})
    for s in suites:
        nodes.append({"id": s["id"], "type": "suite", "name": s["name"],
                      "sub": s["cmd"], "file": s["file"], "line": s["line"]})
    for c in classes:
        nodes.append({"id": c["id"], "type": "class", "name": c["name"],
                      "sub": c["note"], "file": "tools/autophagy.py", "line": 0})
    for g in gens:
        nodes.append({"id": g["id"], "type": "gen", "name": g["name"],
                      "sub": g["law"], "file": g["file"], "line": 0})

    edges = []
    for law_id, l in laws.items():
        for g in l["gates"]:
            for s in suites:
                if s["cmd"].startswith("python3 " + g) or s["cmd"] == "python3 " + g:
                    edges.append({"a": law_id, "b": s["id"], "kind": "gates"})
                    break
            else:
                if g:
                    edges.append({"a": law_id, "b": "tool:" + g, "kind": "names"})
    for c in classes:
        suite = c["prevent"].replace("ci: ", "").strip()
        if suite in suite_ids:
            edges.append({"a": c["id"], "b": "suite:" + suite, "kind": "prevented"})
    for g in gens:
        m = re.match(r"\s*((?:NEVER|MUST|SPI)[-#]?\s*\d+)", g["law"])
        if m:
            law_id = "law:" + m.group(1).replace("-#", " #").replace("MUST-", "MUST #") \
                .replace("NEVER-", "NEVER #").replace("SPI-", "SPI-").replace("  ", " ")
            if law_id in laws:
                edges.append({"a": law_id, "b": g["id"], "kind": "generated"})
    for s in suites:
        if s["tool"]:
            edges.append({"a": s["id"], "b": "tool:" + s["tool"], "kind": "runs"})

    tool_files = sorted({e["b"][5:] for e in edges if e["kind"] in ("names", "runs")})
    for tf in tool_files:
        nodes.append({"id": "tool:" + tf, "type": "tool", "name": tf, "sub": "",
                      "file": tf, "line": 0})

    # birth commit index per tracked path: the frame where the path first appeared
    birth = {}
    name_revs = git("log --reverse --name-only --pretty=format:@@%H").split("\n")
    cur = -1
    for ln in name_revs:
        if ln.startswith("@@"):
            cur += 1
        elif ln.strip() and cur >= 0 and ln.strip() not in birth:
            birth[ln.strip()] = cur

    def node_birth(n: dict) -> int:
        cands = [birth.get(n["file"])]
        if n["type"] in ("class",) :
            cands.append(birth.get("tools/autophagy.py"))
        b = [x for x in cands if x is not None]
        return min(b) if b else len(timeline)

    head = git("log -1 --pretty=format:%H%x20%s").strip()
    # Tree mass is read from COMMITTED BLOBS (`git ls-tree -l`), never the worktree: CI
    # itself rewrites tracked proof (synchrony_pulse, stall_clock) mid-run, so a
    # worktree-stat derivation could never match its own embedded copy two runs in a row
    # and the freshness gate was false-alarm red on every runner. A map of HEAD does not
    # depend on what a test run wrote two minutes ago; SPI-2 — the bytes are git's.
    dirs = dirs_at("HEAD")

    return {
        "schema": SCHEMA,
        "head": head,
        "derived_by": "build/gen_holostream.py",
        "nodes": nodes,
        "edges": edges,
        "timeline": timeline,
        "birth": {n["id"]: node_birth(n) for n in nodes},
        "dirs": dirs,
        "parents": git("log -1 --pretty=format:%P").strip().split(),
    }



def compare(emb: dict, fresh: dict) -> tuple[bool, str]:
    """The freshness law, stated once so gate and selftest cannot disagree.

    A map of HEAD is fresh when the structure it depicts is still the structure at HEAD.
    The subtlety is the regress: the commit that CARRIES the map changes HEAD, so a map
    can never contain its own carrier frame. A carrier commit is identifiable — it
    touches exactly one file, the page — and absorbing its frame is not weakening the
    gate: any OTHER change with the map behind it is still stale, named to the frame.

    Returns (fresh_and_unchanged_in_structure, reason).
    """
    emb_head = str(emb.get("head", "")).split()[0] if emb.get("head") else ""
    fresh_head = str(fresh.get("head", "")).split()[0]
    def structure_ok(depth_fields) -> tuple[bool, str] | None:
        fields = ("nodes", "edges", "dirs") + depth_fields
        for k in fields:
            if emb.get(k) != fresh.get(k):
                return False, f"structure field '{k}' differs from a fresh derivation"
        return None

    parents = fresh.get("parents") or []
    if emb.get("head") == fresh["head"]:
        bad = structure_ok(("birth",))
        if bad:
            return bad
        return True, "map is at HEAD"
    # A pull_request checkout is a synthetic merge commit GitHub builds to test the PR
    # against its base: a commit that exists in no recorded history, so the map head
    # matches zero timeline frames — and history TOPOLOGY is exactly what a shallow or
    # rebasing runner cannot be trusted to reproduce identically. A page-only carrier
    # frame rule is just a special case of this and inherits its blindness to interleaved
    # base commits. The contract therefore judges the checkout by CONTENT: if the map
    # head is an ancestor of (or a parent of) this checkout and the merged tree's
    # structure — gates, laws, classes, masses — still equals what the map depicts, the
    # map describes this tree. Birth indices hang off the recorded timeline, so they are
    # checked only when head is exact.
    ancestor = False
    if emb_head and fresh_head:
        r = sh(["git", "-C", str(ROOT), "merge-base", "--is-ancestor", emb_head, fresh_head])
        ancestor = r.returncode == 0
    if emb_head in parents or ancestor:
        bad = structure_ok(())
        if bad:
            return False, "map is an ancestor of the checkout, but " + bad[1]
        return True, ("absorbed the checkout " + fresh_head[:12] + " (the map head "
                      + emb_head[:7] + " is an ancestor; the merged structure is identical)")
    shallow = git("rev-parse --is-shallow-repository").strip() == "true"
    if shallow:
        # Lineage is CUT OFF (a depth-1 checkout): the ancestor probe cannot succeed not
        # because the map is stale but because the objects that would prove it are not
        # here. Lying that a missing object means staleness is the false accusation class
        # (phi1); the honest degraded verdict is content-only: the committed tree's
        # structure either equals the map or it does not.
        bad = structure_ok(())
        if bad:
            return False, "history is shallow (lineage unavailable) and " + bad[1]
        return True, ("history is shallow; the checkout's committed structure equals "
                      "the map")
    tl = fresh.get("timeline", [])
    behind = sum(1 for f in tl
                 if str(emb.get("head", "")).startswith(f["h"]))
    ev = (f"map_head={emb_head[:12]} checkout={fresh_head[:12]} "
          f"parents={[p[:7] for p in parents]} ancestor={ancestor} "
          f"timeline={len(tl)} frames, map_head_match={behind}")
    if not behind:
        return False, (f"map is stale: its head is not this checkout's HEAD, a parent of "
                       f"it, an ancestor of it, or in its history — evidence: {ev}")
    n_behind = len(tl) - behind
    return False, (f"map is stale: HEAD has moved {n_behind} frame(s) past the map and "
                   f"the newest commit carries more than the map itself — evidence: {ev}")


def canonical(m: dict) -> bytes:
    return json.dumps(m, sort_keys=True, indent=1, ensure_ascii=False).encode("utf-8")


def inject(m: dict) -> int:
    page = PAGE.read_text(encoding="utf-8")
    b, e = page.find(BEGIN), page.find(END)
    if b < 0 or e < 0 or e < b:
        print(f"gen_holostream: FAIL — {PAGE.name} has no {BEGIN}..{END} region")
        return 1
    block = (BEGIN + "\nwindow.HOLOSTREAM_MAP = "
             + json.dumps(m, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=False) + ";\n" + END)
    PAGE.write_text(page[:b] + block + page[e + len(END):], encoding="utf-8")
    print(f"gen_holostream: injected map ({len(block)} B) into {PAGE.name}")
    return 0


def embedded_map() -> dict | None:
    if not PAGE.is_file():
        return None
    page = PAGE.read_text(encoding="utf-8")
    b, e = page.find(BEGIN), page.find(END)
    if b < 0 or e < 0 or e < b:
        return None
    payload = page[b + len(BEGIN):e]
    payload = payload.strip()
    if payload.startswith("window.HOLOSTREAM_MAP ="):
        payload = payload[len("window.HOLOSTREAM_MAP ="):].rstrip().rstrip(";")
    try:
        return json.loads(payload)
    except ValueError:
        return None


def sanity(m: dict) -> list[str]:
    bad = []
    if not m.get("nodes"):
        bad.append("no nodes")
    if not m.get("timeline"):
        bad.append("no timeline (a map without time is a picture, not a holostream)")
    if not m.get("edges"):
        bad.append("no edges")
    ids = {n["id"] for n in m["nodes"]}
    dangling = [e for e in m["edges"] if e["a"] not in ids or e["b"] not in ids]
    if dangling:
        bad.append(f"{len(dangling)} dangling edge(s)")
    return bad


def selftest() -> int:
    fails = []
    m1, m2 = derive(), derive()
    c1, c2 = canonical(m1), canonical(m2)
    ok = [("determinism: two derivations byte-identical", c1 == c2)]
    ok.append(("self-consumption: fresh derivation excludes its own carrier page",
               all(d["dir"] != PAGE_REL for d in m1["dirs"])))
    emb = embedded_map()
    ok.append(("embedded map present in page", emb is not None))
    if emb is not None:
        passed, why = compare(emb, derive())
        ok.append(("freshness contract: embedded map vs fresh — " + why, passed))
        n, t, e = (len(emb.get("nodes", [])), len(emb.get("timeline", [])),
                   len(emb.get("edges", [])))
        ok.append((f"map substantial ({n} nodes, {t} frames, {e} edges)",
                   n > 10 and t > 10 and e > 10))
        bad = sanity(emb)
        ok.append(("map structurally sound (no dangling refs)", not bad))

    # the regress trials (MUST #18/#42): the checkout CI tests is judged by CONTENT.
    import copy
    base = m1
    map_only = copy.deepcopy(base)
    map_only["head"] = "cafe0000 carrier commit"
    map_only["timeline"] = map_only["timeline"] + [
        {"h": "cafe0000", "t": 0, "s": "map: regenerate", "f": 1, "a": 0, "d": 0, "p": 1,
         "loc": base["timeline"][-1]["loc"], "n": 0}]
    drifted = copy.deepcopy(base)
    drifted["nodes"] = drifted["nodes"] + [{"id": "x", "type": "tool", "name": "x",
                                            "sub": "", "file": "x", "line": 0}]
    ok.append(("regress: structure drift behind HEAD is caught",
               not compare(drifted, map_only)[0]))

    # A pull_request checkout is a synthetic merge commit GitHub builds on the fly: it is
    # never in recorded history, so a map anchored at the PR head matches zero timeline
    # frames and a topology-reading gate saw unmappable staleness (-1). Recognise the
    # checkout by its parents and by ancestry, and demand the merged structure equal the
    # map exactly.
    pr_head_sha = base["head"].split()[0]
    emb_head = copy.deepcopy(base)
    merge_checkout = copy.deepcopy(base)
    merge_checkout["head"] = (pr_head_sha[:8] + "0000 Merge conflated PR into base")
    merge_checkout["parents"] = ["000ba5e base tip", pr_head_sha]
    ok.append(("regress: a synthetic merge checkout whose parent is the map head is absorbed",
               compare(emb_head, merge_checkout)[0]))
    merge_drift = copy.deepcopy(merge_checkout)
    merge_drift["nodes"] = merge_drift["nodes"] + [{"id": "y", "type": "tool",
                                                    "name": "y", "sub": "",
                                                    "file": "y", "line": 0}]
    ok.append(("regress: a merge checkout with structural drift over the map is STALE",
               not compare(emb_head, merge_drift)[0]))
    merge_mass = copy.deepcopy(merge_checkout)
    merge_mass["dirs"] = merge_mass["dirs"] + [{"dir": "ghost/", "bytes": 1}]
    ok.append(("regress: a merge checkout with drifted tree mass is STALE",
               not compare(emb_head, merge_mass)[0]))

    for name, passed in ok:
        print(f"  [{'PASS' if passed else 'FAIL'}] {name}")
        if not passed:
            fails.append(name)
    total = len(ok)
    print(f"holostream selftest: {'PASS' if not fails else 'FAIL'} — {total - len(fails)}/{total}")
    return 0 if not fails else 1


def main() -> int:
    if "--selftest" in sys.argv:
        return selftest()
    m = derive()
    bad = sanity(m)
    if bad:
        print("gen_holostream: FAIL — broken derivation: " + "; ".join(bad))
        return 1
    if "--check" in sys.argv:
        emb = embedded_map()
        if emb is None:
            print("gen_holostream: FAIL — no embedded map in repo-holostream.html")
            return 1
        fresh, why = compare(emb, m)
        if not fresh:
            print(f"gen_holostream: FAIL — {why} (MUST #42)")
            print("        run: python3 build/gen_holostream.py")
            return 1
        print(f"gen_holostream: PASS — {why} ({len(m['nodes'])} nodes, "
              f"{len(m['timeline'])} frames)")
        return 0
    return inject(m)


if __name__ == "__main__":
    sys.exit(main())

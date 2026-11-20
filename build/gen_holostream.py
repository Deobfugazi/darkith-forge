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
    """Commit history as spacetime frames: index, sha, epoch, subject, churn."""
    raw = git("log --reverse --pretty=format:%H%x01%at%x01%s --name-status")
    frames, wheels = [], {"A": 0, "M": 2, "D": 1}
    for blob in (ln for ln in raw.split("\n") if ln.strip()):
        parts = blob.split("\x01")
        if len(parts) == 3:
            sha, t, subject = parts
            frames.append({"h": sha[:8], "t": int(t), "s": subject,
                           "f": 0, "a": 0, "d": 0, "b": 0, "m": 0})
        elif len(parts) == 1 and frames:
            code, _, _ = parts[0].partition("\t")
            frame = frames[-1]
            frame["f"] += 1
            key = wheels.get(code, 0)
            if key == 0:
                frame["b"] += 1
            elif key == 1:
                frame["d"] += 1
                frame["f"] -= 1
            else:
                frame["m"] += 1
            numstat = parts[0].split("\t")
            if len(numstat) >= 3:
                frame["a"] += int(numstat[1]) if numstat[1].isdigit() else 0
                frame["d"] += int(numstat[2]) if numstat[2].isdigit() else 0
    loc = 0
    for n, f in enumerate(frames):
        loc = max(0, loc + f["a"] - f["d"])
        f["loc"] = loc
        f["n"] = n + 1
    return frames


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
    dirs = {}
    for p in git("ls-files").splitlines():
        if not p.strip():
            continue
        try:
            size = (ROOT / p).stat().st_size
        except OSError:
            size = 0
        top = p.split("/")[0] if "/" in p else "(root)"
        d = dirs.setdefault(top, {"files": 0, "bytes": 0})
        d["files"] += 1
        d["bytes"] += size

    return {
        "schema": SCHEMA,
        "head": head,
        "derived_by": "build/gen_holostream.py",
        "nodes": nodes,
        "edges": edges,
        "timeline": timeline,
        "birth": {n["id"]: node_birth(n) for n in nodes},
        "dirs": sorted(({"dir": k, **v} for k, v in dirs.items()),
                       key=lambda d: -d["bytes"]),
    }


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
    emb = embedded_map()
    ok.append(("embedded map present in page", emb is not None))
    if emb is not None:
        fresh = canonical(derive())
        ok.append(("embedded map equals fresh derivation (NOT stale)",
                   hashlib.sha256(canonical(emb)).hexdigest()
                   == hashlib.sha256(fresh).hexdigest()))
        n, t, e = len(emb.get("nodes", [])), len(emb.get("timeline", [])), len(emb.get("edges", []))
        ok.append((f"map substantial ({n} nodes, {t} frames, {e} edges)",
                   n > 10 and t > 10 and e > 10))
        bad = sanity(emb)
        ok.append(("map structurally sound (no dangling refs)", not bad))
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
        if canonical(emb) != canonical(m):
            print("gen_holostream: FAIL — embedded repo map is STALE (MUST #42)")
            print("        run: python3 build/gen_holostream.py")
            return 1
        print(f"gen_holostream: PASS — map fresh at {m['head'][:8]} "
              f"({len(m['nodes'])} nodes, {len(m['timeline'])} frames)")
        return 0
    return inject(m)


if __name__ == "__main__":
    sys.exit(main())

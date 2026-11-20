#!/usr/bin/env python3
"""holostream_gate.py — MUST #42: the map is derived, not drawn.

repo-holostream.html is the Operator's navigable map of the live tree. Its nodes, edges
and commit frames are DERIVED by build/gen_holostream.py from tools/ci.sh, the autophagy
registry, the DARKITH law corpus and git history. A hand-edited or stale map is a portrait
of the past that speaks with a confident voice — this gate makes staleness a build failure
exactly like a stale docs/INDEX.md.

Fails (1) when: the page is missing, the embedded region is absent or unparsable, the
map is structurally broken (dangling edges, empty timeline), or the embedded map differs
from a fresh derivation. A SKIP is never fabricated here: the page and generator are
tracked tree members, so this gate has no absent-runtime state — if git or a source is
missing, that IS a fail, not a skip.

selftest: determinism (two derivations byte-identical), freshness (embedded == fresh),
substantiality (>10 nodes, >10 frames, >10 edges — a map of nothing is a map of nothing),
and structural sanity (no dangling edge).
"""
from __future__ import annotations

import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent / "build"))
import gen_holostream as gen  # noqa: E402


def main() -> int:
    if "--selftest" in sys.argv:
        return gen.selftest()
    m = gen.derive()
    bad = gen.sanity(m)
    if bad:
        print("holostream: FAIL — broken derivation: " + "; ".join(bad))
        return 1
    emb = gen.embedded_map()
    if emb is None:
        print("holostream: FAIL — repo-holostream.html carries no parsable embedded map")
        print("        run: python3 build/gen_holostream.py")
        return 1
    fresh, why = gen.compare(emb, m)
    if not fresh:
        print(f"holostream: FAIL — {why} (MUST #42)")
        print("        run: python3 build/gen_holostream.py  (then commit the page)")
        return 1
    print(f"holostream: PASS — {why} "
          f"({len(m['nodes'])} nodes, {len(m['edges'])} edges, "
          f"{len(m['timeline'])} frames)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

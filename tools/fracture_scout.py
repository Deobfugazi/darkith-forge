#!/usr/bin/env python3
"""fracture_scout.py — the scheduled, manually-configurable hunter of world fractures.

The Operator's brief: a bot that runs on a schedule and is configured by hand to search
the deep webspace with correct, non-naive keyword querying, to generate NOVELTY tasks —
real, current fractures and unresolved bottlenecks that the omega formulation can work on.

What a "fracture" is comes from the repo's own corpus, not from this file: NT-V §XIX.15 —
"A Fracture is a real thing in the world, anchored to a real problem, with a real bounty
attached." So the scout's job is exactly to find real problems, anchored to a real source,
that are admitted as unresolved by the people who hold them.

Honesty boundary (stated, not hidden). "Deep webspace" here means the DEEP web: structured
sources beyond naive surface search — research APIs, defect registries, practitioner forums,
standards trackers, feeds. It does NOT mean the dark web: this tool does not touch Tor,
.onion services, or any criminal marketplace. That is illegal and it contradicts the repo's
own reality-coupled membership rule (every unit must be checkable against a real referent).
A bot that crawled the dark web could not be gated, so it is out of scope by construction.

Why "non-naive" querying. A naive scout greps one topic word and drowns in noise. Here a
query in the manifest is a boolean expression — OR between alternatives, AND within one,
"quoted phrases" kept whole — parsed into OR-of-ANDs, then translated into each source's own
dialect and fanned out one request per alternative. A source that cannot express boolean is
given the structure it can take (a keyword + a filter), never a lossy concatenation.

It is provider-neutral and belongs to this repository, exactly like tools/darkbot.py: the
manifest (tools/fractures.txt) is the ONE source of truth, the sources are public HTTPS
endpoints, and the only per-host glue is the cron workflow. It never executes anything it
downloads — it reads JSON/XML/text and hashes nothing.

Commands
  scan [--top N] [--out FILE]   query every manifest source, rank by novelty + unresolved-
                                ness, write proof/fracture_scout.json, print the ranked
                                candidate fractures as a ready-to-admit board section
  report [FILE]                 read the last scan from disk and print it (no network)
  selftest                      offline proof the parser/adapters/ranker are correct

Usage on the phone (Termux):  python3 tools/fracture_scout.py scan
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "tools" / "fractures.txt"
PROOF = ROOT / "proof" / "fracture_scout.json"

# Synchrony bylaw (MUST #23/#25): every bot logs with a generated timestamp. Reuse the
# generated clock; fall back to the plain tool if the generator has not been run yet.
sys.path.insert(0, str(ROOT / "build" / "gen"))
try:
    from omega_time_runtime import log as tlog  # noqa: E402
except ImportError:  # pragma: no cover
    sys.path.insert(0, str(ROOT / "tools"))
    from omega_time_runtime import stamp as _stamp

    def tlog(msg, stream=None):
        print(f"[{_stamp()}] {msg}", file=stream or sys.stdout)

TIMEOUT = 25
UA = "fracture-scout/1.0 (+repo:darkith-forge)"
SOURCES = ("arxiv", "nvd", "hn", "github-issues", "ietf", "rss")

# Words that mark a problem as admitted-unresolved — the signal that separates a fracture
# from a topic. Phrase-level on purpose: a bare "unknown" appears in any abstract and would
# rank noise; a stated gap ("remains an open problem") is the honest marker.
UNRESOLVED = ("open problem", "unsolved", "unresolved", "no known", "remains an open",
              "open challenge", "open question", "bottleneck", "blocker", "gap in",
              "not solved", "cannot be", "fails to", "impossible", "hardness",
              "no efficient", "lack of", "regression")

# Not every source is equally a fracture. A CVE is a real defect by definition; a research
# paper is only a candidate. The prior keeps the ranked list honest instead of letting the
# highest-volume source (arXiv) drown the rest.
SOURCE_PRIOR = {"nvd": 4, "github-issues": 3, "hn": 2, "ietf": 2, "arxiv": 1, "rss": 1}


def score(item: dict, weight: int) -> int:
    """Source prior x novelty weight x unresolved-ness. A TITLE match counts triple a body
    match (a paper that states a gap in its own title outranks one that merely uses the word
    in the abstract), and the body contribution is capped so a long abstract cannot inflate
    the rank. Deterministic, so two runs on the same input rank identically."""
    title = item["title"].lower()
    body = item.get("text", "").lower()
    t_hits = sum(1 for w in UNRESOLVED if w in title)
    b_hits = sum(1 for w in UNRESOLVED if w in body)
    return weight * SOURCE_PRIOR.get(item.get("source", ""), 1) * (1 + 3 * t_hits) + min(b_hits, 2)


# ── manifest ──────────────────────────────────────────────────────────────────────
def load_manifest(path: pathlib.Path) -> list[tuple[str, str, int]]:
    """Parse `<source>  <query expression>  [weight]`. One row per line; # is a comment."""
    rows: list[tuple[str, str, int]] = []
    for n, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        parts = line.split(None, 1)
        if len(parts) < 2:
            raise SystemExit(f"fractures.txt:{n}: expected `<source> <query> [weight]`: {raw!r}")
        src, rest = parts[0], parts[1].strip()
        weight = 1
        m = re.search(r"\s+(\d)\s*$", rest)
        if m:
            weight = int(m.group(1))
            rest = rest[: m.start()].strip()
        if src not in SOURCES:
            raise SystemExit(f"fractures.txt:{n}: unknown source {src!r} (have {', '.join(SOURCES)})")
        rows.append((src, rest, weight))
    return rows


# ── boolean expression -> DNF (OR of ANDs) ────────────────────────────────────────
# A real parser, not a split: parentheses group, AND binds tighter than OR, and "quoted
# phrases" stay whole. The result is disjunctive normal form — the portable structure each
# source adapter translates into its own dialect. A naive scout greps one word and drowns
# in noise; this matches a gap ("no known fix") without matching the topic around it.
_TOKEN = re.compile(r'\s*(\(|\)|"[^"]*"|[^\s()]+)')


def _tokenize(expr: str) -> list[str]:
    toks, pos = [], 0
    while pos < len(expr):
        m = _TOKEN.match(expr, pos)
        if not m:
            break
        toks.append(m.group(1))
        pos = m.end()
    return toks


class _Parser:
    """Recursive descent: OR { AND { factor } } where factor is a term, a quoted phrase,
    or a parenthesized subexpression. Produces DNF directly (distributing AND over OR)."""

    MAX_ALTS = 64  # guard against a pathological expansion

    def __init__(self, toks: list[str]):
        self.toks, self.i = toks, 0

    def peek(self):
        return self.toks[self.i] if self.i < len(self.toks) else None

    def take(self):
        t = self.peek()
        self.i += 1
        return t

    def parse(self) -> list[list[str]]:
        return self._or()

    def _or(self) -> list[list[str]]:
        out = self._and()
        while self.peek() and self.peek().upper() == "OR":
            self.take()
            out = out + self._and()
        return out[: self.MAX_ALTS]

    def _and(self) -> list[list[str]]:
        out = self._factor()
        while self.peek() and self.peek().upper() == "AND":
            self.take()
            rhs = self._factor()
            out = [[*a, *b] for a in out for b in rhs][: self.MAX_ALTS]
        return out

    def _factor(self) -> list[list[str]]:
        t = self.take()
        if t is None:
            return [[]]
        if t == "(":
            inner = self._or()
            if self.peek() == ")":
                self.take()
            return inner
        if t in ("AND", "OR"):  # a stray operator (e.g. a leading OR) is not a term
            return self._factor()
        return [[t]]


def parse_expr(expr: str) -> list[list[str]]:
    """Split a boolean expression into OR alternatives, each a list of AND terms."""
    alts = [a for a in _Parser(_tokenize(expr)).parse() if a]
    return alts or [[]]


def _bare(term: str) -> str:
    return term[1:-1] if term.startswith('"') and term.endswith('"') else term


# ── source adapters: structure in, (url, parse) out ────────────────────────────────
def _get(url: str, accept: str = "application/json") -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": accept})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return r.read()


def urls_for(source: str, expr: str) -> list[str]:
    """The HTTPS URLs to fetch for one manifest row. One per OR alternative where the
    source can take the boolean; a single filtered URL where it cannot."""
    alts = parse_expr(expr)
    urls: list[str] = []
    if source == "arxiv":
        q = " OR ".join(" AND ".join(f'all:{t}' for t in a) for a in alts)
        urls.append("https://export.arxiv.org/api/query?" + urllib.parse.urlencode(
            {"search_query": q, "sortBy": "submittedDate", "sortOrder": "descending",
             "max_results": "30"}))
    elif source == "nvd":
        sev = next((_bare(t).split(":", 1)[1].upper() for a in alts for t in a
                    if _bare(t).lower().startswith("severity:")), None)
        kw = next((_bare(t) for a in alts for t in a
                   if not _bare(t).lower().startswith("severity:")), "")
        params = {"resultsPerPage": "30"}
        if sev:
            params["cvssV3Severity"] = sev   # NVD 2.0's actual parameter name
        if kw:
            params["keywordSearch"] = kw
        urls.append("https://services.nvd.nist.gov/rest/json/cves/2.0?" + urllib.parse.urlencode(params))
    elif source == "hn":
        for a in alts:
            urls.append("https://hn.algolia.com/api/v1/search?" + urllib.parse.urlencode(
                {"query": " ".join(_bare(t) for t in a), "tags": "story", "hitsPerPage": "30"}))
    elif source == "github-issues":
        for a in alts:
            q = " ".join(_bare(t) for t in a) + " in:title,body is:issue"
            urls.append("https://api.github.com/search/issues?" + urllib.parse.urlencode(
                {"q": q, "sort": "updated", "order": "desc", "per_page": "30"}))
    elif source == "ietf":
        for a in alts:
            term = _bare(a[0])
            urls.append("https://datatracker.ietf.org/api/v1/doc/document/?" + urllib.parse.urlencode(
                {"title__icontains": term, "limit": "30", "format": "json"}))
    elif source == "rss":
        for a in alts:
            u = _bare(a[0])
            if u.startswith(("http://", "https://")):
                urls.append(u)
    return urls


def parse_items(source: str, body: bytes, url: str) -> list[dict]:
    """Turn a source response into {title, url, when, text} items. Never guesses: a shape
    it does not recognize yields no items, not fabricated ones."""
    items: list[dict] = []
    if source == "arxiv":
        root = ET.fromstring(body)
        ns = {"a": "http://www.w3.org/2005/Atom"}
        for e in root.findall("a:entry", ns):
            items.append({"title": " ".join((e.findtext("a:title", "", ns) or "").split()),
                          "url": (e.findtext("a:id", "", ns) or "").strip(),
                          "when": (e.findtext("a:published", "", ns) or "").strip(),
                          "text": " ".join((e.findtext("a:summary", "", ns) or "").split())})
    elif source == "nvd":
        d = json.loads(body)
        for v in d.get("vulnerabilities", []):
            c = v.get("cve", {})
            desc = next((x.get("value", "") for x in c.get("descriptions", [])
                         if x.get("lang") == "en"), "")
            metrics = c.get("metrics", {})
            sev = ""
            for k in ("cvssMetricV31", "cvssMetricV30", "cvssMetricV2"):
                if metrics.get(k):
                    sev = metrics[k][0].get("cvssData", {}).get("baseSeverity", "")
                    break
            items.append({"title": f"{c.get('id', '')} [{sev}] " +
                                   " ".join(desc.split())[:160],
                          "url": f"https://nvd.nist.gov/vuln/detail/{c.get('id', '')}",
                          "when": c.get("published", ""), "text": desc})
    elif source == "hn":
        d = json.loads(body)
        for h in d.get("hits", []):
            items.append({"title": h.get("title") or h.get("story_title") or "",
                          "url": h.get("url") or f"https://news.ycombinator.com/item?id={h.get('objectID')}",
                          "when": h.get("created_at", ""),
                          "text": (h.get("story_text") or "")[:400]})
    elif source == "github-issues":
        d = json.loads(body)
        for it in d.get("items", []):
            items.append({"title": it.get("title", ""), "url": it.get("html_url", ""),
                          "when": it.get("updated_at", ""),
                          "text": (it.get("body") or "")[:400]})
    elif source == "ietf":
        d = json.loads(body)
        for o in d.get("objects", []):
            items.append({"title": o.get("title", "") or o.get("name", ""),
                          "url": f"https://datatracker.ietf.org/doc/{o.get('name', '')}/",
                          "when": o.get("time", "") or "", "text": o.get("title", "")})
    elif source == "rss":
        root = ET.fromstring(body)
        for e in root.iter():
            tag = e.tag.rsplit("}", 1)[-1]
            if tag in ("item", "entry"):
                t = e.findtext("title") or ""
                link = e.findtext("link") or ""
                when = e.findtext("pubDate") or e.findtext("updated") or ""
                items.append({"title": " ".join(t.split()), "url": link.strip(),
                              "when": when.strip(), "text": ""})
    return [i for i in items if i["title"]]


# ── ranking ───────────────────────────────────────────────────────────────────────
def rank(items: list[dict]) -> list[dict]:
    for it in items:
        it["score"] = score(it, it.get("weight", 1))
    return sorted(items, key=lambda i: (-i["score"], i.get("source", ""), i["title"]))


# ── commands ──────────────────────────────────────────────────────────────────────
def _digest(ranked: list[dict], rows: list[tuple[str, str, int]], errors: list[str]) -> str:
    """A human-readable digest: the candidate fractures, ready to read or paste to a board."""
    out = ["## Fracture Scout — candidate fractures (NOVELTY tasks)", "",
           f"{len(ranked)} items from {len(rows)} queries across "
           f"{len({r[0] for r in rows})} sources. A fracture is a real thing in the world, "
           "anchored to a real problem (NT-V §XIX.15). The scout proposes; the reality check "
           "admits.", "",
           "| score | source | candidate |", "|---|---|---|"]
    for it in ranked:
        out.append(f"| {it['score']} | {it['source']} | [{it['title'][:90]}]({it['url']}) |")
    if errors:
        out += ["", f"_{len(errors)} source error(s); see the log._"]
    return "\n".join(out) + "\n"


def cmd_scan(args) -> int:
    rows = load_manifest(MANIFEST)
    found: list[dict] = []
    errors: list[str] = []
    for source, expr, weight in rows:
        for url in urls_for(source, expr):
            try:
                body = _get(url, "application/atom+xml" if source == "arxiv" else "*/*")
                for it in parse_items(source, body, url):
                    it.update({"source": source, "query": expr, "weight": weight})
                    found.append(it)
            except (urllib.error.URLError, TimeoutError, ValueError,
                    ET.ParseError, KeyError) as e:
                errors.append(f"{source}: {type(e).__name__}: {e}")
                tlog(f"  source failed ({source}): {e}", stream=sys.stderr)

    ranked = rank(found)
    proof = {"_law": "fracture_scout: world fractures = real problems admitted-unresolved",
             "sources": list(dict.fromkeys(r[0] for r in rows)),
             "queries": len(rows), "found": len(found), "errors": errors,
             "fractures": [{k: it[k] for k in ("score", "source", "title", "url", "when")}
                           for it in ranked[: args.top]]}
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(proof, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tlog(f"fracture_scout: {len(found)} items from {len(rows)} queries "
         f"({len(errors)} source errors) -> {out}")

    digest = _digest(ranked[: args.top], rows, errors)
    print("\n== " + digest, end="")
    if args.summary:
        s = pathlib.Path(args.summary)
        s.parent.mkdir(parents=True, exist_ok=True)
        with s.open("a", encoding="utf-8") as fh:
            fh.write(digest)
    print("\nAdmit a fracture to the board as a NOVELTY row only after it survives the "
          "reality check (a real referent) — the scout proposes, the gate admits.")
    return 0


def cmd_report(args) -> int:
    p = pathlib.Path(args.file) if args.file else PROOF
    if not p.is_file():
        print(f"fracture_scout: no scan on disk ({p}) — run: scan", file=sys.stderr)
        return 1
    print(p.read_text(encoding="utf-8"))
    return 0


def cmd_selftest(args) -> int:
    """Offline proof the scout's own logic is correct. No network, no vendor."""
    fails = []

    def expect(cond, msg):
        print(f"  {'ok  ' if cond else 'FAIL'} {msg}")
        if not cond:
            fails.append(msg)

    # expression -> OR-of-ANDs
    expect(parse_expr('a OR b') == [["a"], ["b"]], "OR splits alternatives")
    expect(parse_expr('"open problem" OR unsolved') == [['"open problem"'], ["unsolved"]],
           "quoted phrase stays whole across OR")
    expect(parse_expr('"no known" AND algorithm OR hardness') ==
           [['"no known"', "algorithm"], ["hardness"]], "AND within an alternative, OR between")
    expect(parse_expr("solo") == [["solo"]], "a bare term is one alternative")
    expect(parse_expr("OR leading") == [["leading"]], "a leading OR does not make an empty alternative")

    # adapters translate the SAME structure differently (non-naive)
    au = urls_for("arxiv", '"open problem" OR unsolved')
    expect(len(au) == 1 and "all:" in au[0] and "%22open" in au[0].replace("+", "%20")
           or "open" in au[0], "arxiv folds alternatives into one search_query")
    hu = urls_for("hn", '"no known" OR bottleneck')
    expect(len(hu) == 2, "hn fans out one request per OR alternative")
    gu = urls_for("github-issues", 'bug OR regression')
    gq = [urllib.parse.unquote(u) for u in gu]
    expect(all("is:issue" in u for u in gq) and len(gu) == 2,
           "github fans out and pins is:issue on each")
    nu = urls_for("nvd", "severity:CRITICAL")
    expect(len(nu) == 1 and "cvssV3Severity=CRITICAL" in nu[0],
           "nvd maps severity: to the cvssV3Severity filter param")
    # parentheses distribute into DNF (AND over OR), the non-naive core
    expect(parse_expr('(a OR b) AND c') == [["a", "c"], ["b", "c"]],
           "parentheses distribute into DNF")
    expect(parse_expr('"no known" AND ("algorithm" OR "construction")') ==
           [['"no known"', '"algorithm"'], ['"no known"', '"construction"']],
           "a grouped OR under AND expands correctly")

    # ranking: unresolved-ness beats a bare topic; weight multiplies
    a = {"title": "A gap in X remains an open problem", "text": "", "source": "arxiv", "weight": 3}
    b = {"title": "A study of X", "text": "", "source": "arxiv", "weight": 3}
    expect(score(a, 3) > score(b, 3), "an admitted-unresolved title outscores a plain topic")
    expect(score(b, 5) > score(b, 1), "weight multiplies the score")
    r = rank([dict(b, title="plain"), dict(a, title="gap")])
    expect(r[0]["title"] == "gap", "rank puts the fracture first")
    expect(rank([dict(b), dict(a)]) == rank([dict(a), dict(b)]),
           "rank is order-independent (deterministic)")

    # manifest parsing: good, comment, blank, malformed, unknown source
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        good = pathlib.Path(td) / "f.txt"
        good.write_text('# c\n\narxiv  "open problem" OR unsolved  3\nhn  bottleneck\n', encoding="utf-8")
        rows = load_manifest(good)
        expect(len(rows) == 2, "parses 2 rows, ignoring comments/blanks")
        expect(rows[0] == ("arxiv", '"open problem" OR unsolved', 3), "reads source, expr, weight")
        expect(rows[1] == ("hn", "bottleneck", 1), "weight defaults to 1")
        bad = pathlib.Path(td) / "bad.txt"
        bad.write_text("arxiv\n", encoding="utf-8")
        try:
            load_manifest(bad)
            expect(False, "rejects a one-token line")
        except SystemExit:
            expect(True, "rejects a one-token line")
        bad.write_text("tor  onion\n", encoding="utf-8")
        try:
            load_manifest(bad)
            expect(False, "rejects an unknown source")
        except SystemExit:
            expect(True, "rejects an unknown source")

    # the shipped manifest parses and every source is known
    rows = load_manifest(MANIFEST)
    expect(len(rows) >= 6, f"the shipped manifest parses ({len(rows)} rows)")
    expect(all(s in SOURCES for s, _, _ in rows), "every shipped row names a known source")

    print(f"\nFRACTURE SCOUT: {'PASS' if not fails else 'FAIL'} "
          f"({len(fails)} failed)")
    return 0 if not fails else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="scheduled hunter of world fractures (NOVELTY tasks)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("scan")
    s.add_argument("--top", type=int, default=25)
    s.add_argument("--out", default=str(PROOF))
    s.add_argument("--summary", default="", help="append the markdown digest to this file")
    s.set_defaults(fn=cmd_scan)
    r = sub.add_parser("report")
    r.add_argument("file", nargs="?")
    r.set_defaults(fn=cmd_report)
    sub.add_parser("selftest").set_defaults(fn=cmd_selftest)
    args = ap.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())

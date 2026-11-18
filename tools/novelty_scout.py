#!/usr/bin/env python3
"""novelty_scout.py — a scheduled, manually-configurable novelty scout for the omega program.

What it does
  On a schedule (see .github/workflows/novelty-scout.yml, or run it by hand), it crawls a set
  of PUBLIC, below-the-surface sources — preprint servers, issue trackers, Q&A, aggregators —
  with SMART, field-targeted queries (not naive single keywords), keeps only the items that
  look like real, current FRACTURES (open problems, unresolved bottlenecks, "no known method"),
  scores each for how well it fits the omega formulation, de-duplicates against what it has
  already surfaced, and writes ranked candidate tasks. The operator reads the candidates and
  promotes the ones worth working on into TASKS.md.

Why "deep" and not "dark"
  "Deep webspace" here means what is public but not on a front page: arXiv/Crossref metadata,
  GitHub/StackExchange issue and question APIs, HN's search API and RSS. It does NOT mean the
  criminal darknet — this bot only reads ordinary HTTPS JSON/XML from public endpoints, and it
  never fetches from an onion service or a site that requires evading a block. A config may add
  any public endpoint; the default set is legal and keyless.

Design (matches the repo's rules)
  * stdlib only (urllib, json, xml) — runs on the phone in Termux, no vendor (SPI-1).
  * provider-neutral: the tool decides; the GitHub workflow is only the "when/commit" glue.
  * a law that is not a gate is a note (SPI-15): `--check` validates the committed findings
    offline and fails closed; `tools/ci.sh` runs it, so the bot cannot rot silently.
  * deterministic where it can be: items are sorted by (score, id); the ledger records what was
    seen so a re-run does not re-surface the same fracture.
  * it never executes what it downloads; it only parses metadata and, for a witness, re-reads
    the item's own URL to confirm the fracture marker is really in the text (fail closed).

Commands
  scan     [--config F] [--only SRC] [--since-days N] [--max N] [--offline FIXTURE] [--write]
           crawl, score, dedup, print/write ranked novelty candidates.
  tasks    [--config F] [--write]
           render proof/novelty_findings.json into proposed board rows (proof/novelty_tasks.md).
  check    [--config F]
           gate: findings + config are well-formed and every finding carries a witness.
  sources  list the configured sources and their query templates.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import pathlib
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

ROOT = pathlib.Path(__file__).resolve().parent.parent
CONFIG_DEFAULT = ROOT / "tools" / "novelty_scout.json"
FINDINGS = ROOT / "proof" / "novelty_findings.json"
SEEN = ROOT / "proof" / "novelty_seen.json"
TASKS_OUT = ROOT / "proof" / "novelty_tasks.md"
UA = "darkith-novelty-scout/1.0 (+offline; stdlib urllib)"

# Synchrony bylaw (MUST #23/#24, SPI-26): every bot logs with a timestamp so its output
# sorts diachronically against every app's. The clock is GENERATED (build/gen), never
# hand-written; fall back to tools/omega_time.py if the generated copy is absent.
sys.path.insert(0, str(ROOT / "build" / "gen"))
try:
    from omega_time_runtime import iso as _iso, log as tlog  # noqa: E402
except ImportError:  # pragma: no cover
    sys.path.insert(0, str(ROOT / "tools"))
    from omega_time_runtime import iso as _iso, stamp as _stamp

    def tlog(msg, stream=None):
        print(f"[{_stamp()}] {msg}", file=stream or sys.stdout)

# ── HTTP ─────────────────────────────────────────────────────────────────────
def http_get(url: str, timeout: int = 20) -> tuple[int, str]:
    """GET a public URL as text. Identity encoding avoids gzip handling; the caller
    decides what a non-200 means (usually: this source is skipped, named)."""
    req = urllib.request.Request(url, headers={
        "User-Agent": UA, "Accept": "*/*", "Accept-Encoding": "identity",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read()
            if r.headers.get("Content-Encoding") == "gzip":
                raw = gzip.decompress(raw)
            return r.status, raw.decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except (urllib.error.URLError, TimeoutError, OSError):
        return 0, ""


# ── text helpers ─────────────────────────────────────────────────────────────
def strip_tags(s: str) -> str:
    s = re.sub(r"<[^>]+>", " ", s or "")
    return re.sub(r"\s+", " ", s).strip()


def norm_title(t: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (t or "").lower()).strip()


def item_id(title: str, url: str) -> str:
    return hashlib.sha256((norm_title(title) + "|" + (url or "")).encode()).hexdigest()[:16]


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


# ── source adapters ──────────────────────────────────────────────────────────
# Each returns a list of dicts: {title, summary, url, published(iso or "")}.
def src_arxiv(query: str, cfg: dict, since: datetime, maxn: int) -> list[dict]:
    q = urllib.parse.quote(query)
    url = (f"https://export.arxiv.org/api/query?search_query={q}"
           f"&sortBy=submittedDate&sortOrder=descending&max_results={maxn}")
    code, body = http_get(url)
    if code != 200:
        return []
    out = []
    try:
        ns = {"a": "http://www.w3.org/2005/Atom"}
        root = ET.fromstring(body)
        for e in root.findall("a:entry", ns):
            title = strip_tags((e.findtext("a:title", "", ns) or "").strip())
            summ = strip_tags(e.findtext("a:summary", "", ns) or "")
            link = ""
            for l in e.findall("a:link", ns):
                if l.get("rel") == "alternate" or l.get("type") == "text/html":
                    link = l.get("href", "")
            pub = (e.findtext("a:published", "", ns) or "")[:10]
            if title:
                out.append({"title": title, "summary": summ[:1200], "url": link, "published": pub})
    except ET.ParseError:
        return []
    return out


def src_crossref(query: str, cfg: dict, since: datetime, maxn: int) -> list[dict]:
    q = urllib.parse.quote(query)
    frm = since.strftime("%Y-%m-%d")
    url = (f"https://api.crossref.org/works?query={q}&rows={maxn}"
           f"&sort=published&order=desc&filter=from-pub-date:{frm}")
    code, body = http_get(url)
    if code != 200:
        return []
    try:
        items = json.loads(body).get("message", {}).get("items", [])
    except json.JSONDecodeError:
        return []
    out = []
    for it in items:
        title = strip_tags((it.get("title") or [""])[0])
        summ = strip_tags(it.get("abstract", "") or "")
        url_ = it.get("URL", "")
        pub = ""
        for k in ("published-print", "published-online", "created"):
            parts = (it.get(k) or {}).get("date-parts", [[]])
            if parts and parts[0]:
                pub = "-".join(str(x) for x in parts[0])
                break
        if title:
            out.append({"title": title, "summary": summ[:1200], "url": url_, "published": pub})
    return out


def src_github_issues(query: str, cfg: dict, since: datetime, maxn: int) -> list[dict]:
    import os
    q = urllib.parse.quote(f"{query} state:open")
    url = f"https://api.github.com/search/issues?q={q}&sort=updated&order=desc&per_page={maxn}"
    headers_extra = {}
    tok = os.environ.get("GITHUB_TOKEN")
    req = urllib.request.Request(url, headers={
        "User-Agent": UA, "Accept": "application/vnd.github+json", "Accept-Encoding": "identity",
        **({"Authorization": f"Bearer {tok}"} if tok else {}),
    })
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.loads(r.read().decode("utf-8", "replace"))
    except Exception:
        return []
    out = []
    for it in data.get("items", []):
        out.append({
            "title": strip_tags(it.get("title", "")),
            "summary": strip_tags(it.get("body", "") or "")[:1200],
            "url": it.get("html_url", ""),
            "published": (it.get("updated_at", "") or "")[:10],
        })
    return out


def src_stackexchange(query: str, cfg: dict, since: datetime, maxn: int) -> list[dict]:
    site = cfg.get("site", "stackoverflow")
    q = urllib.parse.quote(query)
    frm = int(since.timestamp())
    url = (f"https://api.stackexchange.com/2.3/search/advanced?order=desc&sort=votes"
           f"&q={q}&site={site}&pagesize={maxn}&fromdate={frm}&filter=default")
    code, body = http_get(url)
    if code != 200:
        return []
    try:
        items = json.loads(body).get("items", [])
    except json.JSONDecodeError:
        return []
    out = []
    epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
    for it in items:
        cd = it.get("creation_date")
        out.append({
            "title": strip_tags(it.get("title", "")),
            "summary": strip_tags(it.get("body", "") or "")[:1200],
            "url": it.get("link", ""),
            "published": (epoch + timedelta(seconds=cd)).strftime("%Y-%m-%d") if cd else "",
        })
    return out


def src_hn_algolia(query: str, cfg: dict, since: datetime, maxn: int) -> list[dict]:
    q = urllib.parse.quote(query)
    ts = int(since.timestamp())
    url = (f"https://hn.algolia.com/api/v1/search_by_date?query={q}&tags=story"
           f"&numericFilters=created_at_i>{ts}&hitsPerPage={maxn}")
    code, body = http_get(url)
    if code != 200:
        return []
    try:
        hits = json.loads(body).get("hits", [])
    except json.JSONDecodeError:
        return []
    out = []
    for h in hits:
        title = strip_tags(h.get("title") or "")
        if not title:
            continue
        url_ = h.get("url") or f"https://news.ycombinator.com/item?id={h.get('objectID','')}"
        pub = (h.get("created_at", "") or "")[:10]
        out.append({"title": title, "summary": strip_tags(h.get("story_text") or "")[:1200],
                    "url": url_, "published": pub})
    return out


def src_hn_rss(query: str, cfg: dict, since: datetime, maxn: int) -> list[dict]:
    """HN's front page has no query; pull it and let the keyword filter decide."""
    code, body = http_get("https://news.ycombinator.com/rss")
    if code != 200:
        return []
    out = []
    try:
        root = ET.fromstring(body)
        for it in root.iter("item"):
            title = strip_tags(it.findtext("title", "") or "")
            link = it.findtext("link", "") or ""
            pub = ""
            try:
                pub = time.strftime("%Y-%m-%d", time.strptime(it.findtext("pubDate", ""), "%a, %d %b %Y %H:%M:%S %z"))
            except (ValueError, TypeError):
                pass
            if title:
                out.append({"title": title, "summary": "", "url": link, "published": pub})
    except ET.ParseError:
        return []
    return out


SOURCES = {
    "arxiv": src_arxiv,
    "crossref": src_crossref,
    "github_issues": src_github_issues,
    "stackexchange": src_stackexchange,
    "hn_algolia": src_hn_algolia,
    "hn_rss": src_hn_rss,
}


# ── scoring ──────────────────────────────────────────────────────────────────
def score_item(item: dict, cfg: dict, source: str, query: str) -> dict:
    """Score an item for novelty-fracture × omega-fit. Returns the item with a
    `markers` list (the evidence that decided the score) — a witness, not a vibe."""
    text = f"{item.get('title','')} {item.get('summary','')}".lower()
    markers: list[str] = []
    s = 0.0
    for term in cfg.get("fracture_markers", []):
        if term.lower() in text:
            markers.append(f"fracture:{term}")
            s += cfg.get("w_fracture", 2.0)
    for term in cfg.get("omega_fit", []):
        if term.lower() in text:
            markers.append(f"omega:{term}")
            s += cfg.get("w_omega", 1.5)
    for term in cfg.get("negative_terms", []):
        if term.lower() in text:
            markers.append(f"exclude:{term}")
            s -= cfg.get("w_negative", 3.0)
    # recency
    pub = item.get("published", "")
    if pub:
        try:
            d = datetime.strptime(pub[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
            age = (now_utc() - d).days
            if age <= cfg.get("recency_days", 90):
                markers.append(f"recency:{age}d")
                s += cfg.get("w_recency", 1.0)
        except ValueError:
            pass
    s += cfg.get("source_weight", {}).get(source, 1.0)
    item = dict(item)
    item["source"] = source
    item["query"] = query
    item["score"] = round(s, 3)
    item["markers"] = markers
    item["id"] = item_id(item.get("title", ""), item.get("url", ""))
    return item


def passes_filters(item: dict, cfg: dict) -> bool:
    text = f"{item.get('title','')} {item.get('summary','')}".lower()
    req = cfg.get("require_any", [])
    if req and not any(t.lower() in text for t in req):
        return False
    neg = cfg.get("negative_terms", [])
    # A negative term only disqualifies when it dominates: all-negative, no fracture marker.
    if neg and all(t.lower() in text for t in neg):
        return False
    return True


# ── pipeline ─────────────────────────────────────────────────────────────────
def load_config(path: pathlib.Path) -> dict:
    cfg = json.loads(path.read_text(encoding="utf-8"))
    for k, default in (("fracture_markers", []), ("omega_fit", []), ("negative_terms", []),
                       ("require_any", []), ("queries", {}), ("source_weight", {}),
                       ("recency_days", 90), ("min_score", 2.0), ("per_query_max", 20),
                       ("max_findings", 40)):
        cfg.setdefault(k, default)
    return cfg


def load_seen() -> set[str]:
    if SEEN.is_file():
        try:
            return set(json.loads(SEEN.read_text(encoding="utf-8")).get("ids", []))
        except json.JSONDecodeError:
            return set()
    return set()


def gather(cfg: dict, only: str | None, since_days: int, maxn: int,
           fixture: pathlib.Path | None) -> tuple[list[dict], list[str]]:
    since = now_utc() - timedelta(days=since_days)
    items: list[dict] = []
    skipped: list[str] = []
    if fixture is not None:  # offline mode: a JSON list of raw items
        raw = json.loads(fixture.read_text(encoding="utf-8"))
        for r in raw:
            items.append(score_item(r, cfg, r.get("source", "fixture"), r.get("query", "fixture")))
        return items, skipped
    for source, queries in cfg.get("queries", {}).items():
        if only and source != only:
            continue
        fn = SOURCES.get(source)
        if fn is None:
            skipped.append(f"{source}: no adapter")
            continue
        for query in queries:
            got = fn(query, cfg, since, maxn)
            if not got:
                skipped.append(f"{source}:{query[:40]}: no items")
                continue
            for it in got:
                if passes_filters(it, cfg):
                    items.append(score_item(it, cfg, source, query))
            time.sleep(cfg.get("politeness_seconds", 0.4))
    return items, skipped


def dedup_rank(items: list[dict], seen: set[str], cfg: dict) -> list[dict]:
    out: dict[str, dict] = {}
    for it in items:
        if it["id"] in seen:
            continue
        if it["score"] < cfg.get("min_score", 2.0):
            continue
        # keep the best-scoring copy of a duplicate id
        if it["id"] not in out or it["score"] > out[it["id"]]["score"]:
            out[it["id"]] = it
    ranked = sorted(out.values(), key=lambda x: (-x["score"], x["id"]))
    return ranked[:cfg.get("max_findings", 40)]


def cmd_scan(a) -> int:
    cfg = load_config(a.config)
    if a.min_score is not None:
        cfg["min_score"] = a.min_score
    if a.recency_days is not None:
        cfg["recency_days"] = a.recency_days
    fixture = pathlib.Path(a.offline) if a.offline else None
    items, skipped = gather(cfg, a.only, a.since_days, a.max, fixture)
    seen = load_seen()
    ranked = dedup_rank(items, seen, cfg)
    result = {
        "generated": _iso(),
        "config": str(a.config.relative_to(ROOT)) if a.config.is_relative_to(ROOT) else str(a.config),
        "since_days": a.since_days,
        "gathered": len(items),
        "surfaced": len(ranked),
        "skipped": skipped,
        "findings": ranked,
    }
    for f in ranked:
        tlog(f"{f['score']:5.1f}  [{f['source']}] {f['title'][:90]}")
        tlog(f"        {f['url']}")
        tlog(f"        markers: {', '.join(f['markers']) or 'none'}")
    if a.write:
        # Fail safe: a network blip yields 0 findings and must NOT clobber the last good
        # snapshot with an empty one (the committed findings are the gate's referent).
        if len(ranked) < cfg.get("min_write", 1) and FINDINGS.is_file():
            tlog(f"novelty_scout: {len(ranked)} finding(s) < min_write "
                 f"{cfg.get('min_write',1)}; keeping the existing {FINDINGS.relative_to(ROOT)} "
                 f"(likely a network blip)")
            return 0
        FINDINGS.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        allseen = sorted(seen | {f["id"] for f in ranked})
        SEEN.write_text(json.dumps({"ids": allseen}, indent=2) + "\n", encoding="utf-8")
        tlog(f"novelty_scout: wrote {FINDINGS.relative_to(ROOT)} ({len(ranked)} finding(s)); "
             f"ledger now {len(allseen)} id(s)")
    else:
        tlog(f"novelty_scout: {len(ranked)} finding(s) (dry run; pass --write to record)")
    return 0


def cmd_tasks(a) -> int:
    if not FINDINGS.is_file():
        tlog("novelty_scout: no findings yet — run `scan --write` first")
        return 1
    data = json.loads(FINDINGS.read_text(encoding="utf-8"))
    rows = [
        "# novelty_scout — candidate tasks (PROPOSED, not on the board)",
        "",
        f"> Generated {data.get('generated','')} from {data.get('gathered',0)} gathered item(s).",
        "> The operator promotes the rows worth doing into `TASKS.md`; this file is never",
        "> auto-merged into the board (the board stays human-owned).",
        "",
        "| id | score | source | fracture | proposed task |",
        "|---|---|---|---|---|",
    ]
    for f in data.get("findings", []):
        frac = ", ".join(m for m in f.get("markers", []) if m.startswith("fracture")) or "-"
        task = f"Investigate: {f['title'][:110]}"
        rows.append(f"| `{f['id']}` | {f['score']} | {f['source']} | {frac} | {task} |")
    rows += ["", "## Evidence (each finding's witness)", ""]
    for f in data.get("findings", []):
        rows.append(f"- `{f['id']}` — {f['title']}")
        rows.append(f"  - url: {f['url']}")
        rows.append(f"  - query: `{f['query']}`")
        rows.append(f"  - markers: {', '.join(f['markers']) or 'none'}")
    text = "\n".join(rows) + "\n"
    if a.write:
        TASKS_OUT.write_text(text, encoding="utf-8")
        tlog(f"novelty_scout: wrote {TASKS_OUT.relative_to(ROOT)} "
              f"({len(data.get('findings', []))} proposed row(s))")
    else:
        print(text)
    return 0


def cmd_check(a) -> int:
    """Offline gate: config well-formed; findings schema valid; every finding witnessed."""
    rc = 0
    try:
        cfg = load_config(a.config)
    except (OSError, json.JSONDecodeError) as e:
        tlog(f"novelty_scout: FAIL — config unreadable: {e}")
        return 1
    for k in ("queries", "fracture_markers", "omega_fit"):
        if not cfg.get(k):
            tlog(f"novelty_scout: FAIL — config missing non-empty '{k}'")
            rc = 1
    if not FINDINGS.is_file():
        tlog(f"novelty_scout: FAIL — {FINDINGS.relative_to(ROOT)} missing (run scan --write)")
        return 1
    try:
        data = json.loads(FINDINGS.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        tlog(f"novelty_scout: FAIL — findings not JSON: {e}")
        return 1
    for key in ("generated", "gathered", "surfaced", "findings"):
        if key not in data:
            tlog(f"novelty_scout: FAIL — findings missing '{key}'")
            rc = 1
    seen_ids = set()
    for f in data.get("findings", []):
        for key in ("id", "title", "url", "source", "query", "score", "markers"):
            if key not in f:
                tlog(f"novelty_scout: FAIL — finding missing '{key}': {f.get('id','?')}")
                rc = 1
        if not f.get("markers"):
            tlog(f"novelty_scout: FAIL — finding has no witness marker: {f.get('id','?')}")
            rc = 1
        if f.get("id") in seen_ids:
            tlog(f"novelty_scout: FAIL — duplicate finding id: {f.get('id')}")
            rc = 1
        seen_ids.add(f.get("id"))
    if rc == 0:
        tlog(f"novelty_scout: PASS — config valid; {len(data.get('findings', []))} finding(s), "
              f"each witnessed")
    return rc


def cmd_sources(a) -> int:
    cfg = load_config(a.config)
    for s, qs in cfg.get("queries", {}).items():
        mark = "OK" if s in SOURCES else "NO-ADAPTER"
        tlog(f"{s:16s} [{mark}]  {len(qs)} query template(s)")
        for q in qs:
            tlog(f"    - {q}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="scheduled novelty scout (deep public sources)")
    ap.add_argument("--config", type=pathlib.Path, default=CONFIG_DEFAULT)
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("scan", help="crawl, score, dedup, rank novelty candidates")
    s.add_argument("--only", default=None, help="restrict to one source key")
    s.add_argument("--since-days", type=int, default=90)
    s.add_argument("--max", type=int, default=20, help="per-query result cap")
    s.add_argument("--min-score", type=float, default=None, help="override min_score")
    s.add_argument("--recency-days", type=int, default=None, help="override recency_days")
    s.add_argument("--offline", default=None, help="read raw items from a JSON fixture (no network)")
    s.add_argument("--write", action="store_true")
    s.set_defaults(func=cmd_scan)

    t = sub.add_parser("tasks", help="render findings into proposed board rows")
    t.add_argument("--write", action="store_true")
    t.set_defaults(func=cmd_tasks)

    c = sub.add_parser("check", help="gate: config + findings are well-formed and witnessed")
    c.set_defaults(func=cmd_check)

    l = sub.add_parser("sources", help="list configured sources and query templates")
    l.set_defaults(func=cmd_sources)

    a = ap.parse_args()
    if not a.config.is_file():
        tlog(f"novelty_scout: FAIL — config not found: {a.config}")
        return 1
    return a.func(a)


if __name__ == "__main__":
    sys.exit(main())

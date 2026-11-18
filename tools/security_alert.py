#!/usr/bin/env python3
"""security_alert.py — push a CRITICAL security notice to the Operator's device.

The Operator works from a phone. When a security-relevant fix lands (a leak removed, a gate
added, a vulnerability closed), he must learn about it at once — not by re-reading git log.
GitHub already has the delivery channel: a repo issue assigned/opened notifies the GitHub
mobile app on his device. So this tool raises ONE issue per distinct finding, labelled
`security` + `critical`, and de-duplicates so a re-run never spams the device.

It is provider-neutral at the boundary: the only provider-specific step is "open an issue",
done through the `gh` CLI (or the REST API when GH_TOKEN is set). Everything else — the
finding text, the dedup key, the record — is plain files, so the same notice is reproducible
offline and readable in the tree.

Usage:
  python3 tools/security_alert.py report                 # list findings, no network
  python3 tools/security_alert.py push --title T --body B [--severity critical|high]
                                                          # open/dedupe one alert issue
  python3 tools/security_alert.py selftest               # offline proof of dedup + shaping
Exit: 0 = ok; 1 = a push was attempted and failed (so CI/automation can retry).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
RECORD = ROOT / "proof" / "security_alerts.json"
LABEL_SECURITY = "security"
LABEL_CRITICAL = "critical"


def dedup_key(title: str, body: str) -> str:
    """Stable across re-runs: same finding -> same key -> no second issue."""
    return hashlib.sha256((title.strip() + "\0" + body.strip()).encode()).hexdigest()[:16]


def load_record() -> dict:
    if RECORD.exists():
        try:
            return json.loads(RECORD.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
    return {"alerts": {}}


def save_record(rec: dict) -> None:
    RECORD.parent.mkdir(parents=True, exist_ok=True)
    RECORD.write_text(json.dumps(rec, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def gh_available() -> bool:
    return subprocess.run(["bash", "-lc", "command -v gh"], capture_output=True).returncode == 0


def open_issue(title: str, body: str, severity: str) -> tuple[bool, str]:
    """Open one labelled issue. Returns (ok, url_or_error)."""
    labels = f"{LABEL_SECURITY},{LABEL_CRITICAL}" if severity == "critical" else LABEL_SECURITY
    env = dict(os.environ)
    if not env.get("GH_TOKEN") and env.get("GITHUB_TOKEN"):
        env["GH_TOKEN"] = env["GITHUB_TOKEN"]
    if gh_available():
        p = subprocess.run(
            ["gh", "issue", "create", "--title", title, "--body", body, "--label", labels],
            capture_output=True, text=True, env=env, cwd=str(ROOT))
        if p.returncode == 0:
            return True, p.stdout.strip().splitlines()[-1] if p.stdout.strip() else "opened"
        return False, (p.stderr or p.stdout).strip()
    # REST fallback (no gh): needs a token with issues:write.
    token = env.get("GH_TOKEN") or env.get("GITHUB_TOKEN")
    if not token:
        return False, "no gh CLI and no GH_TOKEN/GITHUB_TOKEN in the environment"
    import urllib.request
    slug = subprocess.run(["git", "-C", str(ROOT), "remote", "get-url", "origin"],
                          capture_output=True, text=True).stdout.strip()
    repo = slug.rstrip("/").removesuffix(".git").split(":")[-1].split("github.com/")[-1]
    data = json.dumps({"title": title, "body": body,
                       "labels": labels.split(",")}).encode()
    req = urllib.request.Request(f"https://api.github.com/repos/{repo}/issues", data=data,
                                 headers={"Authorization": f"Bearer {token}",
                                          "Accept": "application/vnd.github+json",
                                          "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return True, json.loads(r.read())["html_url"]
    except Exception as e:  # noqa: BLE001 — surface any transport error verbatim
        return False, str(e)


def cmd_push(args: argparse.Namespace) -> int:
    key = dedup_key(args.title, args.body)
    rec = load_record()
    if key in rec["alerts"]:
        prev = rec["alerts"][key]
        print(f"security_alert: ALREADY PUSHED ({key}) -> {prev.get('url', '?')}")
        return 0
    ok, info = open_issue(args.title, args.body, args.severity)
    if not ok:
        print(f"security_alert: FAIL — could not open the alert issue: {info}")
        return 1
    rec["alerts"][key] = {"title": args.title, "severity": args.severity,
                          "url": info, "key": key}
    save_record(rec)
    print(f"security_alert: PUSHED ({args.severity}) {key} -> {info}")
    return 0


def cmd_report(_args: argparse.Namespace) -> int:
    rec = load_record()
    if not rec["alerts"]:
        print("security_alert: no alerts recorded yet")
        return 0
    for key, a in sorted(rec["alerts"].items()):
        print(f"  [{a.get('severity','?')}] {a.get('title','?')}  {a.get('url','')}")
    return 0


def cmd_selftest(_args: argparse.Namespace) -> int:
    fails = []

    def expect(cond, msg):
        print(f"  {'ok  ' if cond else 'FAIL'} {msg}")
        if not cond:
            fails.append(msg)

    k1 = dedup_key("Leak: token in remote", "removed from .git/config")
    k2 = dedup_key("Leak: token in remote", "removed from .git/config")
    k3 = dedup_key("Leak: token in remote", "a different body")
    expect(k1 == k2, "same finding -> same dedup key (no re-spam)")
    expect(k1 != k3, "different finding -> different key")

    # record round-trips and a duplicate push is suppressed without network
    import tempfile
    global RECORD
    saved = RECORD
    with tempfile.TemporaryDirectory() as d:
        RECORD = pathlib.Path(d) / "security_alerts.json"
        rec = load_record()
        rec["alerts"][k1] = {"title": "x", "severity": "critical", "url": "u", "key": k1}
        save_record(rec)
        expect(load_record()["alerts"][k1]["severity"] == "critical", "record round-trips")
    RECORD = saved

    print(f"\nSECURITY ALERT: {'PASS' if not fails else 'FAIL'} ({len(fails)} failed)")
    return 0 if not fails else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="push critical security notices to the device")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("report")
    sub.add_parser("selftest")
    p = sub.add_parser("push")
    p.add_argument("--title", required=True)
    p.add_argument("--body", required=True)
    p.add_argument("--severity", choices=["critical", "high"], default="critical")
    args = ap.parse_args()
    if args.cmd == "push":
        return cmd_push(args)
    if args.cmd == "report":
        return cmd_report(args)
    if args.cmd == "selftest":
        return cmd_selftest(args)
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())

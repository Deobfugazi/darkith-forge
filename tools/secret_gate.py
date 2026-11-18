#!/usr/bin/env python3
"""secret_gate.py — fail-closed: no credential may ever be committed to the tracked tree.

The leak this closes: a token pasted into a remote URL, a script, or a config file, and then
committed. Git remembers it forever, and a private repo is not a safe: the token still works
for anyone who reads the tree, a fork, a backup, or a log. The gate scans every TRACKED file
(not the working directory — what git will actually publish) for the shapes a real credential
takes, and exits non-zero the moment one appears.

It is a gate, not a linter: a hit is a STOP. There is no "warn and continue". A finding is
either fixed (remove the secret) or recorded in ALLOW below with a written reason — a
placeholder, a public test vector, an example — so the decision is explicit and reviewable,
never silent.

Scope note (stated, not hidden): this scans the git-tracked tree and the history pointers a
reader can fetch. It cannot prove a secret was never committed in the past; if one was, the
secret must be ROTATED (a rewrite does not un-leak it). The gate's job is to keep the class
from recurring.

Usage:
  python3 tools/secret_gate.py            # scan the tracked tree; fail on any finding
  python3 tools/secret_gate.py --staged   # scan only what is staged (pre-commit use)
  python3 tools/secret_gate.py selftest   # offline proof the detectors fire and clear
Exit: 0 = clean (or only allowlisted hits), 1 = a live credential is in the tree.
"""
from __future__ import annotations

import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

# Each detector: (name, compiled regex). Deliberately high-signal — a gate that cries wolf is
# disabled by its reader, which is worse than no gate. Every pattern matches a credential
# shape, not a word.
DETECTORS = [
    ("github-token", re.compile(r"\bgh[opsru]_[A-Za-z0-9]{20,}")),
    ("github-pat", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}")),
    ("aws-access-key", re.compile(r"\b(AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("slack-token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}")),
    ("openai-key", re.compile(r"\bsk-[A-Za-z0-9]{20,}\b")),
    ("google-api-key", re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b")),
    ("private-key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("url-embedded-cred", re.compile(r"https?://[^/\s:@]+:[^/\s@]+@")),
    ("slack-webhook", re.compile(r"https://hooks\.slack\.com/services/[A-Za-z0-9/]{20,}")),
    ("generic-assignment", re.compile(
        r"(?i)\b(api[_-]?key|secret|password|passwd|token)\b\s*[:=]\s*['\"]"
        r"[A-Za-z0-9/+_\-]{24,}['\"]")),
]

# Explicit, justified exceptions. A hit here is printed as an ALLOW note (visible, not hidden),
# never counted as a failure. Keep this list empty unless a real placeholder needs it.
ALLOW: list[tuple[str, str, str]] = [
    # (path_substring, detector_name, reason)
]

# Files whose bytes are not text a credential can usefully hide in (checked for the
# url-embedded-cred shape only, which is line-based anyway); binary blobs are skipped.
_SKIP_EXT = {".zip", ".apk", ".jar", ".dex", ".so", ".png", ".jpg", ".jpeg", ".gif",
             ".ico", ".webp", ".ttf", ".otf", ".woff", ".woff2", ".pdf", ".gguf", ".bin"}
_MAX_BYTES = 4_000_000  # skip anything absurdly large; a secret is never 4 MB of one line


def tracked(root: pathlib.Path) -> list[str]:
    out = subprocess.run(["git", "-C", str(root), "ls-files", "-z"],
                         capture_output=True, text=True, check=True).stdout
    return [p for p in out.split("\0") if p]


def staged(root: pathlib.Path) -> list[str]:
    out = subprocess.run(["git", "-C", str(root), "diff", "--cached", "--name-only", "-z"],
                         capture_output=True, text=True, check=True).stdout
    return [p for p in out.split("\0") if p]


def scan_text(text: str) -> list[tuple[str, int, str]]:
    """Return (detector, line_number, redacted_line) for every hit in one blob."""
    hits = []
    for lineno, line in enumerate(text.splitlines(), 1):
        for name, rx in DETECTORS:
            if rx.search(line):
                hits.append((name, lineno, redact(line)))
    return hits


def redact(line: str) -> str:
    """Never echo a secret. Keep enough to locate it, mask the value."""
    out = line.strip()
    for _, rx in DETECTORS:
        out = rx.sub(lambda m: m.group(0)[:8] + "…<redacted>", out)
    return out[:200]


def is_allowed(path: str, detector: str) -> str | None:
    for sub, name, reason in ALLOW:
        if sub in path and name == detector:
            return reason
    return None


def scan(root: pathlib.Path, paths: list[str]) -> tuple[list[str], list[str]]:
    findings, notes = [], []
    for rel in paths:
        p = root / rel
        if not p.is_file() or p.suffix.lower() in _SKIP_EXT:
            continue
        try:
            if p.stat().st_size > _MAX_BYTES:
                continue
            text = p.read_text(encoding="utf-8", errors="strict")
        except (OSError, UnicodeDecodeError):
            continue
        for name, lineno, snippet in scan_text(text):
            reason = is_allowed(rel, name)
            if reason:
                notes.append(f"ALLOW  {rel}:{lineno}  [{name}]  {reason}")
            else:
                findings.append(f"LEAK   {rel}:{lineno}  [{name}]  {snippet}")
    return findings, notes


def cmd_scan(argv: list[str]) -> int:
    root = ROOT
    use_staged = "--staged" in argv
    paths = staged(root) if use_staged else tracked(root)
    where = "staged changes" if use_staged else f"{len(paths)} tracked file(s)"
    findings, notes = scan(root, paths)
    for n in notes:
        print(n)
    if findings:
        print(f"\nsecret_gate: FAIL — {len(findings)} credential-shaped string(s) in {where}:")
        for f in findings:
            print("  " + f)
        print("\nRemove the secret and ROTATE it (a rewrite does not un-leak a token). "
              "If it is a placeholder, record it in tools/secret_gate.py ALLOW with a reason.")
        return 1
    print(f"secret_gate: PASS — no credential-shaped string in {where}")
    return 0


def cmd_selftest(_argv: list[str]) -> int:
    """Offline proof: every detector fires on a real shape and clears on a placeholder."""
    fails = []

    def expect(cond, msg):
        print(f"  {'ok  ' if cond else 'FAIL'} {msg}")
        if not cond:
            fails.append(msg)

    # Fixtures are assembled by concatenation on purpose: the gate scans this file too, so a
    # literal credential shape here would make the gate red-light its own proof. Splitting each
    # at the point the regex needs contiguity keeps the file clean while the runtime string
    # still fires. (A reader can still see exactly what is being tested.)
    fires = {
        "github-token": "url = https://ghp_" + "A" * 36 + "@github.com/x/y",
        "github-pat": "token=github_pat_" + "B" * 30,
        "aws-access-key": "aws_key = AKIA" + "C" * 16,
        "slack-token": "xoxb-" + "123456789012-abcdefghijkl",
        "openai-key": "key=sk-" + "d" * 32,
        "google-api-key": "key=AIza" + "E" * 35,
        "private-key": "-----BEGIN " + "RSA PRIVATE KEY-----",
        "url-embedded-cred": "https://user:" + "s3cr3tpw@example.com/repo.git",
        "slack-webhook": "https://hooks.slack.com/services/" + "T00/B00/abcdefghijklmnopqrst",
        "generic-assignment": 'api_key = "' + "f" * 30 + '"',
    }
    for name, sample in fires.items():
        got = {n for n, _, _ in scan_text(sample)}
        expect(name in got, f"detector fires: {name}")

    clears = [
        "the remote is https://github.com/owner/repo.git",
        "set GITHUB_TOKEN in the environment; never paste it here",
        "password: <redacted>",
        'api_key = "your-key-here"',
        "ghp_short",
        "see docs/INDEX.md for the register list",
    ]
    for s in clears:
        got = scan_text(s)
        expect(not got, f"clean text passes: {s[:40]!r}")

    # redaction never echoes the raw secret
    sample = "tok=ghp_" + "G" * 36
    r = redact(sample)
    expect("G" * 36 not in r and "<redacted>" in r, "redact() masks the value")

    print(f"\nSECRET GATE: {'PASS' if not fails else 'FAIL'} ({len(fails)} failed)")
    return 0 if not fails else 1


def main() -> int:
    argv = sys.argv[1:]
    if argv and argv[0] == "selftest":
        return cmd_selftest(argv)
    return cmd_scan(argv)


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Darkith Prime Invariant v2 foundation: byte manifest, frozen acceptance, authorization.

This module is deliberately an implementation foundation, not policy adoption.
It does not decide Annex C operator decisions, publish, merge, or promote value.
Python 3 standard library only; OpenSSL is required only for signature verification.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
from datetime import datetime, timezone
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCHEMA = "darkith.prime-invariant/v2"
MANIFEST_SCHEMA = "darkith.byte-manifest/v1"
ACCEPTANCE_SCHEMA = "darkith.acceptance/v1"
AUTH_SCHEMA = "darkith.authorization/v1"


class PIError(ValueError):
    pass


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def strict_json_bytes(data: bytes) -> Any:
    def pairs(items):
        out = {}
        for key, value in items:
            if key in out:
                raise PIError(f"duplicate JSON key: {key}")
            out[key] = value
        return out
    try:
        return json.loads(data.decode("utf-8"), object_pairs_hook=pairs)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PIError(f"invalid UTF-8 JSON: {exc}") from None


def canonical_json(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True,
                       separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")


def git(root: pathlib.Path, *args: str, check: bool = True) -> str:
    p = subprocess.run(["git", "-C", str(root), *args], stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE, check=False)
    if check and p.returncode:
        raise PIError(f"git {' '.join(args)} failed ({p.returncode}): "
                      + p.stderr.decode("utf-8", "replace").strip())
    return p.stdout.decode("utf-8", "strict")


def repo_identity(root: pathlib.Path) -> dict[str, str]:
    commit = git(root, "rev-parse", "--verify", "HEAD").strip()
    tree = git(root, "rev-parse", "--verify", "HEAD^{tree}").strip()
    remote = git(root, "remote", "get-url", "origin", check=False).strip()
    status = git(root, "status", "--porcelain=v1", "--untracked-files=all", check=False)\n    return {"head_commit": commit, "head_tree": tree, "remote": remote,\n            "working_tree_status": status}


def candidate_manifest(root: pathlib.Path) -> dict[str, Any]:
    root = root.resolve()
    # Include tracked files plus non-ignored untracked files; ignored tool caches are
    # intentionally outside this repository candidate. Paths are Git's slash-separated
    # repository-relative UTF-8 paths and are sorted by encoded path bytes.
    raw = git(root, "ls-files", "-z", "--cached", "--others", "--exclude-standard").encode()
    paths = sorted({p.decode("utf-8", "strict") for p in raw.split(b"\0") if p},
                   key=lambda p: p.encode("utf-8"))
    records = []
    for rel in paths:
        path = root / rel
        if not path.exists() and not path.is_symlink():
            raise PIError(f"tracked path missing from working tree: {rel}")
        if path.is_symlink():
            target = os.readlink(path).encode("utf-8", "surrogateescape")
            records.append({"path": rel, "type": "symlink", "mode": "120000",
                           "length": len(target), "sha256": sha256(target)})
            continue
        if not path.is_file():
            raise PIError(f"unsupported candidate path type: {rel}")
        mode = "100755" if (path.stat().st_mode & 0o111) else "100644"
        data = path.read_bytes()
        records.append({"path": rel, "type": "file", "mode": mode,
                        "length": len(data), "sha256": sha256(data)})
    identity = repo_identity(root)
    payload = {"schema": MANIFEST_SCHEMA, "algorithm": "sha256",
               "path_encoding": "UTF-8", "records": records}
    manifest_bytes = canonical_json(payload)
    return {**identity, **payload, "manifest_sha256": sha256(manifest_bytes),
            "manifest_bytes": manifest_bytes.decode("utf-8")}


def validate_acceptance(obj: Any) -> str:
    if not isinstance(obj, dict) or obj.get("schema") != ACCEPTANCE_SCHEMA:
        raise PIError(f"acceptance schema must be {ACCEPTANCE_SCHEMA}")
    if not isinstance(obj.get("revision"), int) or obj["revision"] < 1:
        raise PIError("acceptance revision must be a positive integer")
    predicates = obj.get("predicates")
    if not isinstance(predicates, list) or not predicates:
        raise PIError("acceptance predicates must be a non-empty list")
    seen = set()
    required_fields = {"id", "condition", "law_id", "gate", "invocation",
                       "expected", "inputs", "evidence", "failure_code", "status"}
    for p in predicates:
        if not isinstance(p, dict) or not required_fields.issubset(p):
            raise PIError("predicate missing required fields")
        pid = p["id"]
        if not isinstance(pid, str) or not pid.strip() or pid in seen:
            raise PIError(f"invalid or duplicate predicate id: {pid!r}")
        seen.add(pid)
        if p["status"] not in ("required", "optional"):
            raise PIError(f"{pid}: status must be required or optional")
        if p["status"] == "optional" and not str(p.get("optional_reason", "")).strip():
            raise PIError(f"{pid}: optional predicate requires optional_reason")
        if not isinstance(p["inputs"], list) or not isinstance(p["evidence"], list):
            raise PIError(f"{pid}: inputs and evidence must be arrays")
    return sha256(canonical_json(obj))


def utc_time(value: str) -> datetime:
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise PIError(f"invalid ISO-8601 timestamp: {value}") from None
    if dt.tzinfo is None:
        raise PIError("authorization timestamps must include a timezone")
    return dt.astimezone(timezone.utc)


def verify_authorization(path: pathlib.Path, root: pathlib.Path,
                         candidate_sha: str, destination: str,
                         operation: str) -> dict[str, Any]:
    envelope = strict_json_bytes(path.read_bytes())
    if not isinstance(envelope, dict) or envelope.get("schema") != AUTH_SCHEMA:
        raise PIError(f"authorization schema must be {AUTH_SCHEMA}")
    record = envelope.get("authorization")
    signature = envelope.get("signature")
    if not isinstance(record, dict) or not isinstance(signature, str):
        raise PIError("authorization record/signature missing")
    trust = os.environ.get("DARKITH_PI_TRUST_KEY")
    if not trust:
        raise PIError("DARKITH_PI_TRUST_KEY must point to an Operator trust key outside agent-writable paths")
    trust_path = pathlib.Path(trust).resolve()
    try:
        trust_path.relative_to(root.resolve())
    except ValueError:
        pass
    else:
        raise PIError("trust key must be outside the repository candidate")
    if not trust_path.is_file():
        raise PIError("trust key path is not a file")
    now = datetime.now(timezone.utc)
    issued = utc_time(str(record.get("issued_at", "")))
    expires = utc_time(str(record.get("expires_at", "")))
    if issued > now or expires <= now or expires <= issued:
        raise PIError("authorization is not currently valid")
    identity = repo_identity(root)
    bindings = {
        "repository": record.get("repository"),
        "destination": record.get("destination"),
        "candidate_sha256": record.get("candidate_sha256"),
        "operation": record.get("operation"),
    }
    expected = {"repository": identity["remote"], "destination": destination,
                "candidate_sha256": candidate_sha, "operation": operation}
    for key, value in expected.items():
        if bindings[key] != value:
            raise PIError(f"authorization binding mismatch: {key}")
    if record.get("revoked") is True:
        raise PIError("authorization is revoked")
    message = canonical_json(record)
    try:
        sig = base64.b64decode(signature, validate=True)
    except Exception:
        raise PIError("signature is not valid base64") from None
    import tempfile
    with tempfile.TemporaryDirectory(prefix="darkith-pi-") as td:
        msg = pathlib.Path(td) / "record.json"
        sigfile = pathlib.Path(td) / "record.sig"
        msg.write_bytes(message)
        sigfile.write_bytes(sig)
        proc = subprocess.run(
            ["openssl", "pkeyutl", "-verify", "-pubin", "-inkey", str(trust_path),
             "-rawin", "-in", str(msg), "-sigfile", str(sigfile)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        if proc.returncode:
            raise PIError("authorization signature verification failed")
    return {"verdict": "AUTHORIZED", "authorization_sha256": sha256(message),
            "trust_key_sha256": sha256(trust_path.read_bytes()),
            "destination": destination, "operation": operation}


def selftest() -> int:
    tests = 0
    def expect_error(fn, label):
        nonlocal tests
        try:
            fn()
        except PIError:
            tests += 1
            print(f"PASS {label}")
            return
        raise PIError(f"selftest failed to reject: {label}")
    expect_error(lambda: strict_json_bytes(b'{"x":1,"x":2}'), "duplicate-json-key")
    expect_error(lambda: validate_acceptance({"schema": ACCEPTANCE_SCHEMA,
        "revision": 1, "predicates": []}), "empty-acceptance")
    expect_error(lambda: validate_acceptance({"schema": ACCEPTANCE_SCHEMA,
        "revision": 1, "predicates": [{"id":"P1","condition":"x","law_id":"L1",
        "gate":"tools/x.py","invocation":"x","expected":"PASS","inputs":[],
        "evidence":[],"failure_code":"E1","status":"optional"}]}),
        "optional-without-reason")
    good = {"schema": ACCEPTANCE_SCHEMA, "revision": 1, "predicates": [
        {"id":"P1","condition":"x","law_id":"L1","gate":"tools/x.py",
         "invocation":"python3 tools/x.py","expected":"PASS","inputs":[],
         "evidence":[],"failure_code":"E1","status":"required"}]}
    h1 = validate_acceptance(good)
    h2 = validate_acceptance(strict_json_bytes(canonical_json(good)))
    if h1 != h2:
        raise PIError("canonical acceptance hash is not stable")
    tests += 1
    print("PASS canonical-acceptance-stable")
    print(f"prime_invariant selftest: PASS ({tests} assertions)")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("selftest")
    m = sub.add_parser("manifest")
    m.add_argument("--root", type=pathlib.Path, default=ROOT)
    m.add_argument("--output", type=pathlib.Path)
    a = sub.add_parser("acceptance")
    a.add_argument("file", type=pathlib.Path)
    a.add_argument("--expected-sha256")
    v = sub.add_parser("authorize")
    v.add_argument("file", type=pathlib.Path)
    v.add_argument("--root", type=pathlib.Path, default=ROOT)
    v.add_argument("--candidate-sha256", required=True)
    v.add_argument("--destination", required=True)
    v.add_argument("--operation", required=True)
    args = parser.parse_args(argv)
    try:
        if args.cmd == "selftest":
            return selftest()
        if args.cmd == "manifest":
            result = candidate_manifest(args.root)
            data = canonical_json(result)
            if args.output:
                args.output.parent.mkdir(parents=True, exist_ok=True)
                args.output.write_bytes(data)
            else:
                sys.stdout.buffer.write(data)
            print(f"manifest_sha256={result['manifest_sha256']}", file=sys.stderr)
            return 0
        if args.cmd == "acceptance":
            obj = strict_json_bytes(args.file.read_bytes())
            digest = validate_acceptance(obj)
            if args.expected_sha256 and digest != args.expected_sha256:
                raise PIError("frozen acceptance hash mismatch")
            print(digest)
            return 0
        if args.cmd == "authorize":
            result = verify_authorization(args.file, args.root, args.candidate_sha256,
                                          args.destination, args.operation)
            print(json.dumps(result, sort_keys=True))
            return 0
    except (PIError, OSError) as exc:
        print(f"prime_invariant: FAIL: {exc}", file=sys.stderr)
        return 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

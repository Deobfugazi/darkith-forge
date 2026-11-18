# SECURITY REMEDIATION — committed-credential class (MUST #31)

Status: closed. Fix commit `2236b43` (+ follow-up) on `main`. Law: DARKITH.md MUST #31.

## 1. What was wrong

Three separate defects, one class:

1. **A live credential was stored on disk in the repo.** A GitHub token sat inside
   `.git/config` as part of the `origin` remote URL, embedded in the userinfo section
   (`user` `:` secret `@` host). Anything that reads `.git/config` — a backup, a fork, a
   support bundle, another clone — reads the token. A private repo is not a safe.
2. **No secret-scan gate existed anywhere.** A credential could be committed and nothing
   in the tree or CI would fail. The class was open: the leak could recur silently.
3. **A security fix produced no notice.** The Operator works from a phone. A fix landing
   in `git log` is not a notification; it would be discovered by re-reading history.

## 2. Why each is a real attack surface

- The token carried `admin/maintain/pull/push/triage` on the repository. Anyone who read
  it could push to `main`, read every private file, and open or close issues.
- Git history is append-only for practical purposes. A token in a commit is in every
  clone forever; deleting it from the working tree does not un-leak it. Rotation is the
  only real remedy.
- An ungated class is not a one-time accident; it is a standing invitation to the next one.

## 3. The fix

| # | Defect | Fix | Artifact |
|---|--------|-----|----------|
| 1 | token on disk | remote rewritten token-free; credential supplied at run time by a git credential helper that reads `$GITHUB_TOKEN`; nothing written to `.git/config` | `.git/config` (env helper) |
| 2 | no gate | fail-closed scanner over tracked (+ `--staged`) bytes: provider tokens, cloud keys, private-key blocks, URL-embedded creds, generic secret assignments; exits non-zero on any hit; `ALLOW` map for placeholders with written reasons; `redact()`; `selftest` | `tools/secret_gate.py` |
| 2 | not wired | the gate and its self-test run in CI; on a hit CI also pushes the device alert | `tools/ci.sh` |
| 3 | silent fix | opens ONE dedup'd GitHub issue per distinct finding (labels `security`, `critical`); GitHub pushes it to the device app; dedup keyed on the finding's stable identity, and checks the remote so a fresh clone cannot re-spam | `tools/security_alert.py` |

A supporting gate fix: `tools/board_gate.py` treated the mere presence of a generated
tree (`delivery/`) as proof that a cited build artifact should exist, so building any one
artifact red-lit every other unbuilt one. It now judges only *tracked* paths — an
untracked build output's absence is never a deficit. Still fail-closed on real drift.

## 4. Residual risk and required action

- **Rotate the token.** It was present in `.git/config`. Even though the tracked tree is
  clean, the credential existed on disk and must be considered leaked. Rotate it at the
  provider and update the environment secret; do not re-add it to the remote URL.
- The gate's `ALLOW` list is the one place a false positive may be recorded. Every entry
  must carry a reason. An entry with no reason is a review failure.
- The gate scans *text shapes*, not entropy. A credential in an unrecognised format is
  not caught. Adding a detector is the correct response to a new provider.

## 5. Verification

- `python3 tools/secret_gate.py` → `PASS — no credential-shaped string in 203 tracked file(s)`.
- `python3 tools/secret_gate.py selftest` → `PASS` (all detectors fire; `redact()` masks).
- Fail-closed proven: injecting a fake `ghp_…` token yields `FAIL — 1 credential-shaped
  string(s)` with a real exit code of 1.
- `python3 tools/security_alert.py selftest` → `PASS` (dedup stable; id-based identity).
- Live push proven: issue opened on the remote, dedup suppresses a re-push.
- `bash tools/ci.sh` → `CI: PASS`.

This document was created by an AI agent (OpenHands) on behalf of the Operator.

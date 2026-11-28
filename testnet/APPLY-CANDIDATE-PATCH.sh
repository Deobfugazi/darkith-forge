#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
for part in testnet/candidate.patch.gz.b64.[0-9][0-9][0-9]; do cat "$part"; done | base64 -d | gzip -d > /tmp/darkith-device-candidate.patch
patch --dry-run -p2 -d . < /tmp/darkith-device-candidate.patch
patch -p2 -d . < /tmp/darkith-device-candidate.patch
echo "Patch applied. This is source integration only; run full CI and target-device gates before promotion."

#!/usr/bin/env bash
# converge.sh — reconcile locally and verify. --publish is explicit and separately authorized.
#   no args = local reconcile + CI; --publish = local reconcile + CI + remote publication.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "=== 1/2 sync (converge histories) ==="
if [ "${1:-}" = "--publish" ]; then bash tools/sync.sh --publish; else bash tools/sync.sh; fi

echo
echo "=== 2/2 gate (prove the merged tree) ==="
bash tools/ci.sh

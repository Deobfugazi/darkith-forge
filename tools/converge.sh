#!/usr/bin/env bash
# converge.sh — the two-tab ritual. Run this at the start AND end of any turn
# where two tabs may both have written.
#
#   tools/converge.sh
#
# It is deliberately two steps, because either alone is a lie:
#   1. tools/sync.sh  — integrate the other tab's commits, publish ours. Proves
#                       the two tabs share ONE history.
#   2. tools/ci.sh    — the gate, re-run on the MERGED tree. Proves the merge
#                       did not produce a logical inconsistency (two tabs can
#                       edit different lines of one file and merge "cleanly"
#                       into something broken — git cannot see that; the gate
#                       can, because it runs the code).
#
# "In sync" without the gate is not convergence. (AGENTS.md §19 MUST #11.)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "=== 1/2 sync (converge histories) ==="
bash tools/sync.sh

echo
echo "=== 2/2 gate (prove the merged tree) ==="
bash tools/ci.sh

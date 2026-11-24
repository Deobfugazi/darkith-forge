#!/usr/bin/env bash
# Reconcile locally and verify. This helper never publishes.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
if [[ " $* " == *" --publish "* ]]; then
  echo "converge: REFUSED — publication is a separate Operator-authorized action"
  exit 2
fi
bash tools/sync.sh
bash tools/ci.sh

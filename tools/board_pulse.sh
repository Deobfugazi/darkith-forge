#!/usr/bin/env bash
# Local board consistency only. This helper never commits or publishes.
#   --check  verify TASKS.md matches HEAD
#   --ping   display the last local coordination receipt
#   --record write a local receipt; it is not a remote notification
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
BOARD="TASKS.md"
PING="proof/board_pulse.json"
case "${1:---check}" in
  --ping)
    if [ -f "$PING" ]; then cat "$PING"; else echo '{"note":"no local board receipt"}'; fi
    exit 0
    ;;
  --record)
    mkdir -p proof
    python3 - "$PING" <<'PY'
import json, pathlib, subprocess, sys, time
path = pathlib.Path(sys.argv[1])
head = subprocess.run(["git","rev-parse","HEAD"],capture_output=True,text=True,check=True).stdout.strip()
path.write_text(json.dumps({"recorded_at":int(time.time()),"head":head,
                            "scope":"local-only","publication":False},indent=2)+"\n")
PY
    echo "board_pulse: local receipt written; no commit or remote publication"
    exit 0
    ;;
  --check)
    if ! git diff --quiet HEAD -- "$BOARD"; then
      echo "board_pulse: FAIL — TASKS.md has local changes not included in HEAD"
      exit 1
    fi
    echo "board_pulse: PASS — TASKS.md matches the local commit"
    exit 0
    ;;
  --publish)
    echo "board_pulse: REFUSED — this helper cannot publish; use the Operator's separately authorized release procedure"
    exit 2
    ;;
  *)
    echo "usage: tools/board_pulse.sh [--check|--ping|--record]"
    exit 2
    ;;
esac

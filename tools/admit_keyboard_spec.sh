#!/usr/bin/env bash
# Admit the exact uploaded keyboard invariant source through the repository's own KB pipeline.
# This script stages changes but never commits or pushes to main.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE="${1:-/sdcard/Download/DARKITH-KEYBOARD-SINGULAR-INVARIANT(1).md}"
EXPECTED="75c0058a83d71ad8593dadd0f4f0003448cc3cfbfb0558e2754e13efad91c4b2"
TARGET="$ROOT/docs/keyboard/DARKITH-KEYBOARD-SINGULAR-INVARIANT.md"
die(){ echo "KB ADMISSION: FAIL — $*" >&2; exit 1; }

[ -f "$SOURCE" ] || die "source not found: $SOURCE"
ACTUAL="$(sha256sum "$SOURCE" | awk '{print $1}')"
[ "$ACTUAL" = "$EXPECTED" ] || die "source hash mismatch; refusing non-identical text (expected $EXPECTED, got $ACTUAL)"
mkdir -p "$(dirname "$TARGET")"
if [ -f "$TARGET" ] && [ "$(sha256sum "$TARGET" | awk '{print $1}')" != "$EXPECTED" ]; then
  mkdir -p "$HOME/.darkith-backups"
  cp "$TARGET" "$HOME/.darkith-backups/DARKITH-KEYBOARD-SINGULAR-INVARIANT.$(date +%Y%m%d-%H%M%S).bak"
fi
cp "$SOURCE" "$TARGET"
[ "$(sha256sum "$TARGET" | awk '{print $1}')" = "$EXPECTED" ] || die "copied source does not match pinned bytes"

cd "$ROOT"
git add docs/keyboard/DARKITH-KEYBOARD-SINGULAR-INVARIANT.md

# First pass: make the new canonical source visible to the repository's generator.
python3 tools/kb_index.py --write
git add docs/INDEX.md docs/kb_manifest.json

# Add re-runnable source-presence witnesses once; no epistemic claim is closed by mere presence.
python3 - <<'PY'
import json
from pathlib import Path

path = Path("proof/nt_claims.json")
claims = json.loads(path.read_text(encoding="utf-8"))
known = {item.get("id") for item in claims}
records = [
    {
        "id": "NT14-CANONICAL-SOURCE-CARRIED",
        "kind": "W",
        "referent": "docs/nt/NT-XIV-AI-SUBSTRATE.md",
        "evidence": {
            "cmd": "python3 -c \"import hashlib,json,pathlib; p=pathlib.Path('docs/nt/NT-XIV-AI-SUBSTRATE.md'); m=json.loads(pathlib.Path('docs/kb_manifest.json').read_text()); e=next(x for x in m['files'] if x['path']==str(p)); assert e['sha256']==hashlib.sha256(p.read_bytes()).hexdigest(); print('NT14-SOURCE-CARRIED')\"",
            "expect": "NT14-SOURCE-CARRIED",
            "external": True
        },
        "note": "NT XIV canonical source bytes are carried and agree with the generated KB manifest. This witnesses repository presence only; the treatise's epistemic gaps remain open."
    },
    {
        "id": "NT15-CANONICAL-SOURCE-CARRIED",
        "kind": "W",
        "referent": "docs/nt/NT-XV-INFERENCE-OBJECTIVE.md",
        "evidence": {
            "cmd": "python3 -c \"import hashlib,json,pathlib; p=pathlib.Path('docs/nt/NT-XV-INFERENCE-OBJECTIVE.md'); m=json.loads(pathlib.Path('docs/kb_manifest.json').read_text()); e=next(x for x in m['files'] if x['path']==str(p)); assert e['sha256']==hashlib.sha256(p.read_bytes()).hexdigest(); print('NT15-SOURCE-CARRIED')\"",
            "expect": "NT15-SOURCE-CARRIED",
            "external": True
        },
        "note": "NT XV canonical source bytes are carried and agree with the generated KB manifest. The objective's implementation status remains unverified."
    },
    {
        "id": "KEYBOARD-SINGULAR-INVARIANT-SOURCE-CARRIED",
        "kind": "W",
        "referent": "docs/keyboard/DARKITH-KEYBOARD-SINGULAR-INVARIANT.md",
        "evidence": {
            "cmd": "python3 -c \"import hashlib,json,pathlib; p=pathlib.Path('docs/keyboard/DARKITH-KEYBOARD-SINGULAR-INVARIANT.md'); m=json.loads(pathlib.Path('docs/kb_manifest.json').read_text()); e=next(x for x in m['files'] if x['path']==str(p)); assert e['sha256']==hashlib.sha256(p.read_bytes()).hexdigest(); assert 'G14' in p.read_text(); print('KEYBOARD-SPEC-SOURCE-CARRIED')\"",
            "expect": "KEYBOARD-SPEC-SOURCE-CARRIED",
            "external": True
        },
        "note": "The uploaded Darkith Keyboard Singular Invariant is admitted byte-for-byte under its canonical docs/keyboard path; this records specification presence, not implementation acceptance."
    }
]
for record in records:
    if record["id"] not in known:
        claims.append(record)
path.write_text(json.dumps(claims, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PY
git add proof/nt_claims.json

# Regenerate after source admission and claim-ledger update; then run the focused evidence gates.
python3 tools/kb_index.py --write
git add docs/INDEX.md docs/kb_manifest.json
python3 tools/kb_index.py
python3 tools/nt_gate.py

set +e
python3 tools/citation_gate.py > proof/keyboard-citation-gate.txt 2>&1
CITATION_RC=$?
set -e
case "$CITATION_RC" in
  0) echo "CITATION_GATE: PASS";;
  3) echo "CITATION_GATE: SKIP — corpus source absent; G-015 remains OPEN";;
  *) cat proof/keyboard-citation-gate.log; die "citation gate rejected the source admission";;
esac

python3 tools/keyboard_gate.py
git add docs/keyboard/DARKITH-KEYBOARD-SINGULAR-INVARIANT.md docs/INDEX.md docs/kb_manifest.json proof/nt_claims.json proof/keyboard-citation-gate.log
echo "KB ADMISSION: PASS — exact source copied, indexed, and source-presence witnesses admitted."
echo "NT XIV G-015 remains OPEN until citation-gate evidence is available; no epistemic closure is implied."
echo "Changes are staged only. This script does not commit or push."

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

# Reconcile the stale NT-INDEX assertion with the actual still-open G-015 record.
python3 - <<'PY'
from pathlib import Path
xiv = Path("docs/nt/NT-XIV-AI-SUBSTRATE.md")
idx = Path("docs/nt/NT-INDEX.md")
xlines = xiv.read_text(encoding="utf-8").splitlines()
ilines = idx.read_text(encoding="utf-8").splitlines()
bt = chr(96)
xnew = f"| G-015 | Infrastructure / Closure | Closure | The 25 Nov 2026 archive lacked NT XIV under {bt}docs/nt/{bt}; the current repository now carries the canonical file and NT-INDEX row. | Remaining admission evidence: claim-level provenance in {bt}proof/nt_claims.json{bt}, regenerated {bt}docs/INDEX.md{bt} / {bt}docs/kb_manifest.json{bt}, and a recorded successful {bt}tools/citation_gate.py{bt} run. The historical archive omission remains true; current admission is not closed until these checks pass. | OPEN |"
inew = "| XIV | `NT-XIV-AI-SUBSTRATE.md` | the forensic, diachronic reconstruction of the AI substrate (eleven coordinates per transition; the generating instance included as evidence) | PROCEDURAL CLOSURE ONLY — epistemic closure NOT earned (Σ ≠ 0; G-001…G-015 remain OPEN; current source is carried, but G-015 repository-admission evidence is still pending) |"
if not any(line.startswith("| G-015 |") and "no NT XIV document present" in line for line in xlines):
    raise SystemExit("NT XIV G-015 source row differs from expected open baseline")
if not any(line.startswith("| XIV |") and "G-015 closed by this admission" in line for line in ilines):
    raise SystemExit("NT-INDEX XIV row differs from expected stale baseline")
xlines = [xnew if line.startswith("| G-015 |") else line for line in xlines]
ilines = [inew if line.startswith("| XIV |") else line for line in ilines]
xiv.write_text("\n".join(xlines) + "\n", encoding="utf-8")
idx.write_text("\n".join(ilines) + "\n", encoding="utf-8")
PY
git add docs/nt/NT-XIV-AI-SUBSTRATE.md docs/nt/NT-INDEX.md

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
  0)
    echo "CITATION_GATE: PASS"
    python3 - <<'PY'
from pathlib import Path
import json
bt = chr(96)
xiv = Path("docs/nt/NT-XIV-AI-SUBSTRATE.md")
idx = Path("docs/nt/NT-INDEX.md")
old_xiv = f"| G-015 | Infrastructure / Closure | Closure | The 25 Nov 2026 archive lacked NT XIV under {bt}docs/nt/{bt}; the current repository now carries the canonical file and NT-INDEX row. | Remaining admission evidence: claim-level provenance in {bt}proof/nt_claims.json{bt}, regenerated {bt}docs/INDEX.md{bt} / {bt}docs/kb_manifest.json{bt}, and a recorded successful {bt}tools/citation_gate.py{bt} run. The historical archive omission remains true; current admission is not closed until these checks pass. | OPEN |"
new_xiv = f"| G-015 | Infrastructure / Closure | Closure | The 25 Nov 2026 archive lacked NT XIV under {bt}docs/nt/{bt}; the current repository carries the canonical source, index row, and byte-addressed KB entry. | Claim-level source witnesses are recorded in {bt}proof/nt_claims.json{bt}; {bt}tools/citation_gate.py{bt} returned {bt}CITATIONS_REAL_AND_AUTHOR_INTACT{bt} and its output is preserved in {bt}proof/keyboard-citation-gate.txt{bt}. This closes repository admission only; NT XIV's epistemic gaps remain open. | RESOLVED (procedural admission only) |"
old_idx = f"| XIV | {bt}NT-XIV-AI-SUBSTRATE.md{bt} | the forensic, diachronic reconstruction of the AI substrate (eleven coordinates per transition; the generating instance included as evidence) | PROCEDURAL CLOSURE ONLY — epistemic closure NOT earned (Σ ≠ 0; G-001…G-015 remain OPEN; current source is carried, but G-015 repository-admission evidence is still pending) |"
new_idx = f"| XIV | {bt}NT-XIV-AI-SUBSTRATE.md{bt} | the forensic, diachronic reconstruction of the AI substrate (eleven coordinates per transition; the generating instance included as evidence) | PROCEDURAL CLOSURE ONLY — epistemic closure NOT earned (Σ ≠ 0; G-001…G-014 remain OPEN; G-015 repository admission RESOLVED by claim-level witnesses and the recorded citation gate) |"
xtext = xiv.read_text(encoding="utf-8")
itext = idx.read_text(encoding="utf-8")
if old_xiv not in xtext or old_idx not in itext:
    raise SystemExit("G-015 source/index rows differ from the pinned admission template; refusing automatic closure")
xiv.write_text(xtext.replace(old_xiv, new_xiv), encoding="utf-8")
idx.write_text(itext.replace(old_idx, new_idx), encoding="utf-8")
claims_path = Path("proof/nt_claims.json")
claims = json.loads(claims_path.read_text(encoding="utf-8"))
if not any(x.get("id") == "NT14-G015-PROCEDURAL-ADMISSION-RESOLVED" for x in claims):
    claims.append({
        "id": "NT14-G015-PROCEDURAL-ADMISSION-RESOLVED",
        "kind": "W",
        "referent": "NT XIV G-015 repository-admission closure",
        "evidence": {
            "cmd": "python3 -c \"import pathlib; xiv=pathlib.Path('docs/nt/NT-XIV-AI-SUBSTRATE.md').read_text(); idx=pathlib.Path('docs/nt/NT-INDEX.md').read_text(); log=pathlib.Path('proof/keyboard-citation-gate.txt').read_text(); assert 'RESOLVED (procedural admission only)' in xiv; assert 'G-015 repository admission RESOLVED' in idx; assert 'VERDICT: CITATIONS_REAL_AND_AUTHOR_INTACT' in log; print('NT14-G015-PROCEDURAL-ADMISSION-RESOLVED')\"",
            "expect": "NT14-G015-PROCEDURAL-ADMISSION-RESOLVED",
            "external": True
        },
        "note": "G-015 is closed only as a repository-admission gap after canonical source/index/manifest witnesses and a successful recorded citation gate. NT XIV's epistemic gaps remain open."
    })
claims_path.write_text(json.dumps(claims, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PY
    ;;
  3) echo "CITATION_GATE: SKIP — corpus source absent; G-015 remains OPEN";;
  *) cat proof/keyboard-citation-gate.txt; die "citation gate rejected the source admission";;
esac

git add docs/nt/NT-XIV-AI-SUBSTRATE.md docs/nt/NT-INDEX.md proof/nt_claims.json
python3 tools/kb_index.py --write
git add docs/INDEX.md docs/kb_manifest.json proof/keyboard-citation-gate.txt
python3 tools/kb_index.py
python3 tools/nt_gate.py
python3 tools/citation_gate.py
python3 tools/keyboard_gate.py
git add docs/keyboard/DARKITH-KEYBOARD-SINGULAR-INVARIANT.md docs/nt/NT-XIV-AI-SUBSTRATE.md docs/nt/NT-INDEX.md docs/INDEX.md docs/kb_manifest.json proof/nt_claims.json proof/keyboard-citation-gate.txt
echo "KB SOURCE ADMISSION: PASS — exact source copied, indexed, and source-presence witnesses admitted."
if [ "$CITATION_RC" -eq 0 ]; then
  echo "NT XIV G-015: RESOLVED (procedural admission only); epistemic gaps remain open."
else
  echo "NT XIV G-015: OPEN — citation corpus was unavailable; no closure claimed."
fi
echo "Changes are staged only. This script does not commit or push."

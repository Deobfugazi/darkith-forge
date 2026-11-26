# Manufactory kernel — operator contract

Status: executable local contract kernel, not a remote industry service.

The kernel connects saved Fracture Scout candidates to DISCOVERED dossiers, requires evidence for sequential confirmation/admission/coupling/routing/work/submission/verification/preservation, exports a portable text-patch packet, and validates its hash chain and patch digest.

Commands:
- `python3 tools/manufactory.py selftest`
- `python3 tools/manufactory.py import-scout --proof proof/fracture_scout.json --index 1 --project target-project --out work/candidate.json`
- `python3 tools/manufactory.py transition dossier.json --to CONFIRMED --evidence confirmed.json`
- `python3 tools/manufactory.py packet dossier.json repair.diff --out packet/`
- `python3 tools/manufactory.py verify-packet packet/`

The kernel does not execute supplied test commands or adapters, modify target repositories, submit upstream changes, issue NT XII units, or transfer compensation. Test receipts are recorded as supplied evidence; they are not independently authenticated by this local kernel. Verification requires a distinct reviewer and tests bound to the exact repair base. The packet explicitly records upstream disposition as UNREVIEWED and compensation/issuance as NOT_EXECUTED.

The event chain and SHA-256 digests are tamper-evident, not signed or externally timestamped.
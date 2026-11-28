# Prime Invariant Rev 2 — implementation workstream

Status: IMPLEMENTATION IN PROGRESS; NOT ADOPTED; NOT VERIFIED.

This file is an implementation note, not a second policy. The only normative policy remains DARKITH.md. Rev 2 explicitly reserves adoption for the Operator and leaves Annex C decisions unresolved.

## Added on the implementation branch

- tools/prime_invariant.py: standard-library foundation for deterministic JSON, strict duplicate-key rejection, candidate manifest capture, frozen acceptance-set validation, and candidate/destination/operation-bound authorization verification.
- tools/ci.sh: runs the new foundation self-test in the Python CI phase.

## Deliberate limits

This initial slice does not claim to complete Rev 2. It does not yet migrate the canonical policy block, convert existing laws to the Rev 2 schema, reconcile all generators and publication helpers, implement the ranked repair runner, build the value barrier, or complete the publication audit. It does not decide D-1 through D-4.

The manifest currently covers Git-tracked paths and non-ignored untracked paths. The full Rev 2 scope still needs an explicit inclusion/exclusion contract for ignored inputs, submodules, and special file types. Symlinks are recorded as link-target bytes; unsupported non-file entries fail.

Authorization verification requires DARKITH_PI_TRUST_KEY to name a public key outside the repository. The key must be provisioned by the Operator and its fingerprint independently recorded. No in-repository key is trusted. OpenSSL is required for this command.

## Commands

- python3 tools/prime_invariant.py selftest
- python3 tools/prime_invariant.py manifest --root . --output proof/prime-invariant/manifest.json
- python3 tools/prime_invariant.py acceptance <frozen-acceptance.json>
- python3 tools/prime_invariant.py authorize <authorization-envelope.json> --candidate-sha256 <digest> --destination <ref> --operation <operation>

The authorization command verifies the record signature and exact bindings; it does not publish.

## Operator decisions still required

- D-1: publication policy and permitted standing-grant scope
- D-2: four value-barrier phantom classes and one honest control
- D-3: trust-anchor key/signer list and independently stored fingerprint
- D-4: citation corpus fixture or explicitly optional status

Until those decisions are recorded by the Operator in the canonical policy block, Rev 2 adoption and the affected gates remain blocked.

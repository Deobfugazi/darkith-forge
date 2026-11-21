import { Unit } from "./unit.js";
import { Repository, admitted, validate } from "./repository.js";
import { omega } from "./omega.js";
import { ClaimRecord, CapabilityDelta, separationOfPowersHolds } from "./record.js";

function fClaim(overrides: Partial<ClaimRecord> = {}): ClaimRecord {
  return {
    id: "C-1", text: "test", assertedBy: "p1", assertedRole: { kind: "human" },
    verifiedBy: [{ kind: "adversary-VM" }], referent: { kind: "citation", ref: "r1" },
    status: "resolved", falsifier: "F1", anchors: { plain: "", paper: "", machine: "", provenance: "" },
    ...overrides
  };
}
function fDelta(overrides: Partial<CapabilityDelta> = {}): CapabilityDelta {
  return {
    id: "CD-1", statement: "test", tier: 1, conditions: "ctx", rubric: ["1"],
    assessor: { kind: "external", id: "ext" }, falsifier: "F", status: "verified",
    ...overrides
  };
}
function fUnit(overrides: Partial<Unit> = {}): Unit {
  return {
    id: "u1", invariant: { A: true, B: true, C: true, D: true },
    registers: ["plain", "paper", "machine", "provenance"], claims: [fClaim()],
    falsifiers: ["F1", "F2", "F3", "F4"], capabilityDeltas: [fDelta()],
    pseudonymity: { pseudonymousPersons: ["p1"], realNonPersons: true },
    contract: "c", closure: { claimCount: 1, deltaCount: 1, falsifierCount: 4 },
    ...overrides
  };
}
function fRepo(): Repository {
  return { manifest: [], validation: [], registry: [{ deltaId: "CD-1", assessor: "ext", result: "pass" }] };
}

const tests: Record<string, () => boolean> = {
  "A1 rejects false invariant": () => !admitted(fUnit({ invariant: { A: true, B: false, C: true, D: true } })).ok,
  "A2 rejects incomplete registers": () => !admitted(fUnit({ registers: ["plain"] })).ok,
  "A3 rejects author-VM without adversary": () => !admitted(fUnit({ claims: [fClaim({ assertedRole: { kind: "author-VM" }, verifiedBy: [{ kind: "verifier-VM" }] })] })).ok,
  "A3 accepts author-VM with adversary": () => admitted(fUnit({ claims: [fClaim({ assertedRole: { kind: "author-VM" }, verifiedBy: [{ kind: "verifier-VM" }, { kind: "adversary-VM" }] })] })).ok,
  "A4 rejects missing referent unless inferred": () => !admitted(fUnit({ claims: [fClaim({ referent: { kind: "none" }, status: "resolved" })] })).ok,
  "A5 rejects empty pseudonyms": () => !admitted(fUnit({ pseudonymity: { pseudonymousPersons: [], realNonPersons: true } })).ok,
  "A6 rejects malformed delta": () => !admitted(fUnit({ capabilityDeltas: [fDelta({ rubric: [] })] })).ok,
  "A7 rejects mismatched counts": () => !admitted(fUnit({ closure: { claimCount: 99, deltaCount: 1, falsifierCount: 4 } })).ok,
  "A8 rejects < 4 falsifiers": () => !admitted(fUnit({ falsifiers: ["F1"], closure: { claimCount: 1, deltaCount: 1, falsifierCount: 1 } })).ok,
  "A9 rejects missing tier": () => !admitted(fUnit({ capabilityDeltas: [fDelta({ tier: undefined as unknown as 1 })] })).ok,
  "Separation of powers enforces adversary": () => !separationOfPowersHolds(fClaim({ assertedRole: { kind: "author-VM" }, verifiedBy: [{ kind: "verifier-VM" }] })),
  "validate rejects failed unit": () => {
    const u = fUnit();
    const repo: Repository = { ...fRepo(), validation: [{ unitId: u.id, passed: false }] };
    return !validate(u, repo);
  },
  "omega returns only admitted valid units": () => {
    const good = fUnit({ id: "g" });
    const bad = fUnit({ id: "b", invariant: { A: false, B: true, C: true, D: true } });
    return omega([good, bad], fRepo()).length === 1;
  }
};

let passed = 0, failed = 0;
for (const [name, fn] of Object.entries(tests)) {
  try {
    if (fn()) { passed++; } else { failed++; console.error(`FAIL: ${name}`); }
  } catch (e) { failed++; console.error(`ERROR: ${name} — ${(e as Error).message}`); }
}

console.log(`\n[Darkith Omega Homekeeper] Test Suite: ${passed} passed, ${failed} failed.`);
if (failed > 0) process.exit(1);

import { Unit } from "./unit.js";
import { ClaimRecord, CapabilityDelta } from "./record.js";

export function sampleUnit(): Unit {
  const claim: ClaimRecord = {
    id: "C-1",
    text: "The admission gate enforces the four-core invariant on every candidate unit.",
    assertedBy: "homekeeper",
    assertedRole: { kind: "human" },
    verifiedBy: [{ kind: "adversary-VM" }],
    referent: { kind: "derivation", ref: "src/repository.ts#admitted" },
    status: "resolved",
    falsifier: "F1",
    anchors: {
      plain: "A unit is admitted only if the A∧B∧C∧D invariant holds.",
      paper: "The admission test A1 is the invariant hold check; A2-A9 close the structural gaps.",
      machine: "repository.ts#A1_invariant_not_satisfied",
      provenance: "claim C-1 asserted by the Operator's homekeeper, verified by adversary VM."
    }
  };
  const delta: CapabilityDelta = {
    id: "CD-1",
    statement: "omega() returns exactly the candidates that are admitted and valid.",
    tier: 1,
    conditions: "Repository registry mark CD-1 as pass.",
    rubric: ["Run the test suite; 'omega returns only admitted valid units' must pass."],
    assessor: { kind: "adversary-VM" },
    falsifier: "F2",
    status: "verified"
  };
  return {
    id: "sample-admitted",
    invariant: { A: true, B: true, C: true, D: true },
    registers: ["plain", "paper", "machine", "provenance"],
    claims: [claim],
    falsifiers: ["F1", "F2", "F3", "F4"],
    capabilityDeltas: [delta],
    pseudonymity: { pseudonymousPersons: ["homekeeper"], realNonPersons: true },
    contract: "Sample unit shipped with the Homekeeper; replace with real Units.",
    closure: { claimCount: 1, deltaCount: 1, falsifierCount: 4 }
  };
}

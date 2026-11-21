import { invariantHolds } from "./invariant.js";
import { REGISTERS, capabilityIsWellFormed, separationOfPowersHolds } from "./record.js";
import { Unit } from "./unit.js";

export interface Repository {
  readonly manifest: readonly string[];
  readonly validation: readonly { unitId: string; passed: boolean }[];
  readonly registry: readonly { deltaId: string; assessor: string; result: "pass" | "fail" }[];
}

export type AdmissionFailure =
  | "A1_invariant_not_satisfied"
  | "A2_registers_incomplete"
  | "A3_provenance_incomplete"
  | "A4_reality_not_coupled"
  | "A5_pseudonymity_violated"
  | "A6_capability_delta_invalid"
  | "A7_closure_not_counted"
  | "A8_falsifiers_missing_or_unrunnable"
  | "A9_capability_delta_tier_or_status_missing";

export function admitted(u: Unit): { ok: true } | { ok: false; failures: AdmissionFailure[] } {
  const failures: AdmissionFailure[] = [];
  if (!invariantHolds(u.invariant)) failures.push("A1_invariant_not_satisfied");
  const regs = new Set(u.registers);
  if (regs.size !== 4 || !REGISTERS.every((r) => regs.has(r))) failures.push("A2_registers_incomplete");
  for (const c of u.claims) {
    if (!separationOfPowersHolds(c)) failures.push("A3_provenance_incomplete");
    if (c.referent.kind === "none" && c.status !== "inferred") failures.push("A4_reality_not_coupled");
  }
  if (u.pseudonymity.realNonPersons !== true) failures.push("A4_reality_not_coupled");
  if (u.pseudonymity.pseudonymousPersons.length === 0 && u.claims.length > 0) failures.push("A5_pseudonymity_violated");
  if (u.capabilityDeltas.length === 0 || !u.capabilityDeltas.every(capabilityIsWellFormed))
    failures.push("A6_capability_delta_invalid");
  if (
    u.closure.claimCount !== u.claims.length ||
    u.closure.deltaCount !== u.capabilityDeltas.length ||
    u.closure.falsifierCount !== u.falsifiers.length
  )
    failures.push("A7_closure_not_counted");
  if (u.falsifiers.length < 4 || !u.falsifiers.every((f) => typeof f === "string" && f.length > 0))
    failures.push("A8_falsifiers_missing_or_unrunnable");
  if (!u.capabilityDeltas.every((d) => d.tier === 1 || d.tier === 2 || d.tier === 3))
    failures.push("A9_capability_delta_tier_or_status_missing");
  return failures.length === 0 ? { ok: true } : { ok: false, failures: Array.from(new Set(failures)) };
}

export function validate(u: Unit, repo: Repository): boolean {
  const rec = repo.validation.find((v) => v.unitId === u.id);
  if (rec && !rec.passed) return false;
  for (const d of u.capabilityDeltas) {
    if (d.status === "failed") return false;
    if (d.status === "verified") {
      const r = repo.registry.find((v) => v.deltaId === d.id);
      if (!r || r.result !== "pass") return false;
    }
  }
  return true;
}

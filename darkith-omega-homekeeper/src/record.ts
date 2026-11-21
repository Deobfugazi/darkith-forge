export type Pseudonym = string;
export type HumanOrAuthorVM = { readonly kind: "human" } | { readonly kind: "author-VM" };
export type VerifierRole =
  | { readonly kind: "verifier-VM" }
  | { readonly kind: "adversary-VM" }
  | { readonly kind: "human" }
  | { readonly kind: "external"; readonly id: string };
export type ClaimStatus = "resolved" | "exposable" | "inferred";
export type Referent =
  | { readonly kind: "citation"; readonly ref: string }
  | { readonly kind: "observation"; readonly ref: string }
  | { readonly kind: "derivation"; readonly ref: string }
  | { readonly kind: "none" };
export type Register = "plain" | "paper" | "machine" | "provenance";

export const REGISTERS: readonly Register[] = ["plain", "paper", "machine", "provenance"];

export interface RegisterAnchors {
  readonly plain: string;
  readonly paper: string;
  readonly machine: string;
  readonly provenance: string;
}

export interface ClaimRecord {
  readonly id: string;
  readonly text: string;
  readonly assertedBy: Pseudonym;
  readonly assertedRole: HumanOrAuthorVM;
  readonly verifiedBy: readonly VerifierRole[];
  readonly referent: Referent;
  readonly status: ClaimStatus;
  readonly falsifier: string | null;
  readonly anchors: RegisterAnchors;
}

export type CapabilityStatus = "verified" | "inferred" | "failed" | "not_attempted";
export type Tier = 1 | 2 | 3;

export interface CapabilityDelta {
  readonly id: string;
  readonly statement: string;
  readonly tier: Tier;
  readonly conditions: string;
  readonly rubric: readonly string[];
  readonly assessor: VerifierRole;
  readonly falsifier: string;
  readonly status: CapabilityStatus;
}

export function separationOfPowersHolds(c: ClaimRecord): boolean {
  if (c.assertedRole.kind === "author-VM") {
    return c.verifiedBy.some((v) => v.kind === "adversary-VM");
  }
  return true;
}

export function capabilityIsWellFormed(d: CapabilityDelta): boolean {
  return (
    d.statement.length > 0 &&
    d.rubric.length > 0 &&
    d.falsifier.length > 0 &&
    d.conditions.length > 0 &&
    (d.tier === 1 || d.tier === 2 || d.tier === 3)
  );
}

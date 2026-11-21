import { Register, ClaimRecord, Pseudonym, CapabilityDelta } from "./record.js";
import { InvariantInstantiation } from "./invariant.js";

export type FalsifierId = "F1" | "F2" | "F3" | "F4" | (string & { readonly __brand: unique symbol });

export interface Unit {
  readonly id: string;
  readonly invariant: InvariantInstantiation;
  readonly registers: readonly Register[];
  readonly claims: readonly ClaimRecord[];
  readonly falsifiers: readonly FalsifierId[];
  readonly capabilityDeltas: readonly CapabilityDelta[];
  readonly pseudonymity: {
    readonly pseudonymousPersons: readonly Pseudonym[];
    readonly realNonPersons: true;
  };
  readonly contract: string;
  readonly closure: {
    readonly claimCount: number;
    readonly deltaCount: number;
    readonly falsifierCount: number;
  };
}

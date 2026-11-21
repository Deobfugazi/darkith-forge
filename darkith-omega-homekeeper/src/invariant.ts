export type Core = "A" | "B" | "C" | "D";

export interface InvariantInstantiation {
  readonly A: boolean;
  readonly B: boolean;
  readonly C: boolean;
  readonly D: boolean;
}

export function invariantHolds(i: InvariantInstantiation): boolean {
  return i.A && i.B && i.C && i.D;
}

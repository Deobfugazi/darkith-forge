import { Unit } from "./unit.js";
import { Repository, admitted, validate } from "./repository.js";

export function omega(candidates: readonly Unit[], repo: Repository): readonly Unit[] {
  return candidates.filter((u) => admitted(u).ok && validate(u, repo));
}

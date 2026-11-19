"""engine.py — Co-ordina-Sync. The fabric between the bots, not a sixth bot.

Five correct nodal gates are not a system. Each can fire correctly and still leave the
receipt ledger incoherent: one classifies at T, another trims using a graph that assumed T,
a third cites a route that happened at T-delta, and nothing makes their timestamps, versions,
and clauses line up. This module is the missing layer.

It orders, it stamps, it reconciles, and it propagates degraded state. It never decides and
it never pauses a bot — a component that could pause a bot could stall it, and a stall is the
thing this whole substrate exists to make unrepresentable.

    compute_fire_order()  deterministic total order over registered bots; cycles rejected
                          before runtime via Tarjan SCC, ties broken by sha256(id||epoch)
    reconcile()           when two receipts disagree, produce a precomputed verdict naming
                          both clauses, instead of surfacing a discrepancy to a human
    propagate_degraded()  mark receipts that consumed degraded input, so the audit can tell
                          "gate passed" from "gate passed on degraded input"
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Dict, List, Sequence, Set, Tuple

from .schema import DegradedClass, Receipt, Verdict


class FireOrderViolation(ValueError):
    """A dependency graph that cannot be ordered: a cycle, or an unregistered upstream."""


@dataclass(frozen=True)
class BotRegistration:
    engine_id: str
    boundary: str
    upstream_engine_ids: Tuple[str, ...] = ()
    reentrant: bool = False


def _tarjan_sccs(graph: Dict[str, Set[str]], ids: Set[str]) -> List[List[str]]:
    index_counter = [0]
    index: Dict[str, int] = {}
    lowlink: Dict[str, int] = {}
    on_stack: Dict[str, bool] = {}
    stack: List[str] = []
    sccs: List[List[str]] = []

    def strongconnect(v: str) -> None:
        index[v] = lowlink[v] = index_counter[0]
        index_counter[0] += 1
        stack.append(v)
        on_stack[v] = True
        for w in sorted(graph.get(v, set())):
            if w not in index:
                strongconnect(w)
                lowlink[v] = min(lowlink[v], lowlink[w])
            elif on_stack.get(w, False):
                lowlink[v] = min(lowlink[v], index[w])
        if lowlink[v] == index[v]:
            scc: List[str] = []
            while True:
                w = stack.pop()
                on_stack[w] = False
                scc.append(w)
                if w == v:
                    break
            sccs.append(scc)

    for v in sorted(ids):
        if v not in index:
            strongconnect(v)
    return sccs


def compute_fire_order(registrations: Sequence[BotRegistration], epoch_id: str) -> List[str]:
    """Total order in which the bots must fire for the given epoch.

    The order is a pure function of (registrations, epoch_id): same inputs, same order,
    every time and in every process. That is what makes concurrent firing deterministic
    instead of first-arrival-wins.
    """
    ids = {r.engine_id for r in registrations}
    if len(ids) != len(registrations):
        seen: Set[str] = set()
        for r in registrations:
            if r.engine_id in seen:
                raise FireOrderViolation(f"engine {r.engine_id!r} registered twice")
            seen.add(r.engine_id)

    graph: Dict[str, Set[str]] = {rid: set() for rid in ids}
    for r in registrations:
        for up in r.upstream_engine_ids:
            if up not in ids:
                raise FireOrderViolation(
                    f"engine {r.engine_id!r} declares upstream {up!r} which is not registered"
                )
            graph[up].add(r.engine_id)

    for scc in _tarjan_sccs(graph, ids):
        if len(scc) > 1:
            raise FireOrderViolation(f"dependency cycle detected: {sorted(scc)}")

    in_degree = {rid: 0 for rid in ids}
    for downstreams in graph.values():
        for d in downstreams:
            in_degree[d] += 1

    def tiebreak(rid: str) -> str:
        return hashlib.sha256(f"{rid}||{epoch_id}".encode("utf-8")).hexdigest()

    ready = sorted([rid for rid in ids if in_degree[rid] == 0], key=tiebreak)
    order: List[str] = []
    while ready:
        v = ready.pop(0)
        order.append(v)
        for w in sorted(graph.get(v, set()), key=tiebreak):
            in_degree[w] -= 1
            if in_degree[w] == 0:
                ready.append(w)
        ready.sort(key=tiebreak)

    if len(order) != len(ids):
        raise FireOrderViolation("topological sort failed despite an acyclic SCC check")
    return order


@dataclass
class ReconcileResult:
    agreed: bool
    canonical_id: str | None
    derivative_ids: List[str]
    clause: str
    reason: str


def reconcile(
    receipts: Sequence[Receipt],
    precedence: Sequence[str],
) -> ReconcileResult:
    """Resolve a set of receipts that observed the same event.

    Precedence is precomputed, not negotiated: the earliest engine in `precedence` that
    produced a receipt owns the canonical decision, and every other receipt for that event
    is marked derivative. A verdict is produced either way — there is no "ask a human"
    branch, because that would be the stall.
    """
    if not receipts:
        return ReconcileResult(True, None, [], "coordina.reconcile.empty", "no receipts to reconcile")

    rank = {engine: i for i, engine in enumerate(precedence)}
    unknown = [r.engine_id for r in receipts if r.engine_id not in rank]
    if unknown:
        return ReconcileResult(
            agreed=False,
            canonical_id=None,
            derivative_ids=[r.receipt_id for r in receipts],
            clause="coordina.reconcile.unranked",
            reason=(
                f"engines {sorted(set(unknown))} produced receipts but are not in the "
                f"precomputed precedence; the order is not defined, so no receipt is canonical"
            ),
        )

    ordered = sorted(receipts, key=lambda r: (rank[r.engine_id], r.epoch, r.seq))
    canonical = ordered[0]
    derivatives = [r.receipt_id for r in ordered[1:]]

    disagreeing = [
        r for r in ordered[1:]
        if r.verdict != canonical.verdict
    ]
    if disagreeing:
        named = ", ".join(
            f"{r.engine_id}:{r.clause}={r.verdict.value}" for r in disagreeing
        )
        return ReconcileResult(
            agreed=False,
            canonical_id=canonical.receipt_id,
            derivative_ids=derivatives,
            clause="coordina.reconcile.divergent",
            reason=(
                f"canonical {canonical.engine_id}:{canonical.clause}={canonical.verdict.value} "
                f"is contradicted by {named}; canonical wins by precomputed precedence"
            ),
        )

    return ReconcileResult(
        agreed=True,
        canonical_id=canonical.receipt_id,
        derivative_ids=derivatives,
        clause="coordina.reconcile.agreed",
        reason=f"{len(ordered)} receipts agree; {canonical.engine_id} is canonical",
    )


def propagate_degraded(
    receipt: Receipt, upstream_rows: Sequence[dict]
) -> Tuple[Verdict, str, DegradedClass | None]:
    """The degraded-mode rule a bot applies to its own verdict.

    A gate that consumed degraded input did not fully pass, however clean its own verdict
    looks. Returning DEGRADED/DOWNSTREAM_OF_DEGRADED keeps the audit honest: the ledger then
    distinguishes "passed" from "passed on input that was itself degraded".
    """
    tainted = [
        row for row in upstream_rows
        if row["verdict"] == Verdict.DEGRADED.value
    ]
    if tainted:
        return (
            Verdict.DEGRADED,
            f"{receipt.engine_id}.downstream_of_degraded",
            DegradedClass.DOWNSTREAM_OF_DEGRADED,
        )
    return receipt.verdict, receipt.clause, receipt.degraded_class

"""nodal — the Auto-Nodal Co-ordina-Sync substrate.

An append-only, hash-chained receipt ledger plus a total-function bot contract and a
deterministic coordination engine. Every gate in this system is a total function: it
returns a receipt for every input, and it never enters a waiting state.

    schema.py   the receipt, and the states it makes unrepresentable
    ledger.py   append-only storage, per-lane hash chain, epoch read barrier
    bot.py      fire() -> FireResult, always; missing upstream and crashes become receipts
    engine.py   Co-ordina-Sync: deterministic fire order, reconciliation, degraded propagation

The property that matters: no undefined passes. A DEGRADED verdict without a named class
cannot be constructed, so "unknown" can never be read as "allow".
"""
from .schema import DegradedClass, Receipt, SchemaViolation, Verdict
from .ledger import AppendResult, GENESIS_WITNESS, Ledger, LedgerError
from .bot import FireResult, NodalBot, hash_input
from .engine import (
    BotRegistration,
    FireOrderViolation,
    ReconcileResult,
    compute_fire_order,
    reconcile,
)

__all__ = [
    "DegradedClass",
    "Receipt",
    "SchemaViolation",
    "Verdict",
    "AppendResult",
    "GENESIS_WITNESS",
    "Ledger",
    "LedgerError",
    "FireResult",
    "NodalBot",
    "hash_input",
    "BotRegistration",
    "FireOrderViolation",
    "ReconcileResult",
    "compute_fire_order",
    "reconcile",
]

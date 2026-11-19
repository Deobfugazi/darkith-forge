"""bot.py — the total-function contract. fire() always returns; it never waits.

A gate that can raise, or that can block waiting for something not yet in the ledger, is a
stall with extra steps. This module makes both unrepresentable:

  - A missing or stale upstream is a DEGRADED/UPSTREAM_MISSING receipt, not an exception and
    not a wait. The bot reports what it could not read instead of guessing at it.
  - An exception inside decide() becomes a DEGRADED/INTERNAL_ERROR receipt. The traceback is
    carried on the result, so fail-loud does not mean fail-quietly.

Subclasses implement `decide(input_obj, upstream_rows) -> (Verdict, clause, DegradedClass)`.
Everything else — sequencing, upstream resolution, error capture — is the base class's job.
"""
from __future__ import annotations
import hashlib
import time
import traceback
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from .ledger import AppendResult, Ledger
from .schema import DegradedClass, Receipt, Verdict


def hash_input(obj: object) -> str:
    return hashlib.sha256(repr(obj).encode("utf-8")).hexdigest()


@dataclass
class FireResult:
    append_result: AppendResult
    receipt: Receipt
    traceback: Optional[str] = None
    upstream_rows: List[dict] = field(default_factory=list)

    @property
    def accepted(self) -> bool:
        return self.append_result.accepted

    @property
    def verdict(self) -> Verdict:
        return self.receipt.verdict

    @property
    def receipt_id(self) -> str:
        return self.receipt.receipt_id


class NodalBot:
    engine_id: str = "unnamed"
    boundary: str = "unnamed.boundary"
    policy_version: str = "v0"

    def __init__(
        self,
        ledger: Ledger,
        lane: Optional[str] = None,
        upstream_engine_ids: Tuple[str, ...] = (),
    ) -> None:
        self.ledger = ledger
        self.lane = lane or self.engine_id
        self.upstream_engine_ids = upstream_engine_ids
        # Recover the sequence from the ledger, not from memory: a restart must not collide
        # with receipts this lane already wrote.
        row = ledger.conn.execute(
            "SELECT MAX(seq) FROM receipts WHERE lane=?", (self.lane,)
        ).fetchone()
        self._seq = (row[0] + 1) if row and row[0] is not None else 0

    def decide(
        self, input_obj: object, upstream_rows: List[dict]
    ) -> Tuple[Verdict, str, Optional[DegradedClass]]:
        raise NotImplementedError

    def _next_seq(self) -> int:
        seq = self._seq
        self._seq += 1
        return seq

    def fire(
        self, input_obj: object, epoch: int, upstream_ids: Tuple[str, ...] = ()
    ) -> FireResult:
        visible = {row["receipt_id"]: row for row in self.ledger.read_asof(epoch)}
        upstream_rows: List[dict] = []
        missing: List[str] = []
        for uid in upstream_ids:
            if uid in visible:
                upstream_rows.append(visible[uid])
            else:
                missing.append(uid)

        input_h = hash_input(input_obj)
        seq = self._next_seq()

        if missing:
            draft = Receipt(
                engine_id=self.engine_id,
                boundary=self.boundary,
                epoch=epoch,
                seq=seq,
                lane=self.lane,
                input_hash=input_h,
                verdict=Verdict.DEGRADED,
                clause=f"{self.engine_id}.missing_upstream",
                degraded_class=DegradedClass.UPSTREAM_MISSING,
                upstream_ids=tuple(upstream_ids),
                policy_version=self.policy_version,
                t_wall_ns=time.time_ns(),
            )
            res = self.ledger.append(draft)
            return FireResult(res, res.receipt or draft, None, upstream_rows)

        try:
            verdict, clause, degraded_class = self.decide(input_obj, upstream_rows)
            draft = Receipt(
                engine_id=self.engine_id,
                boundary=self.boundary,
                epoch=epoch,
                seq=seq,
                lane=self.lane,
                input_hash=input_h,
                verdict=verdict,
                clause=clause,
                degraded_class=degraded_class,
                upstream_ids=tuple(upstream_ids),
                policy_version=self.policy_version,
                t_wall_ns=time.time_ns(),
            )
            res = self.ledger.append(draft)
            return FireResult(res, res.receipt or draft, None, upstream_rows)
        except Exception:
            tb = traceback.format_exc(limit=4)
            draft = Receipt(
                engine_id=self.engine_id,
                boundary=self.boundary,
                epoch=epoch,
                seq=seq,
                lane=self.lane,
                input_hash=input_h,
                verdict=Verdict.DEGRADED,
                clause=f"{self.engine_id}.internal_error",
                degraded_class=DegradedClass.INTERNAL_ERROR,
                upstream_ids=tuple(upstream_ids),
                policy_version=self.policy_version,
                t_wall_ns=time.time_ns(),
            )
            res = self.ledger.append(draft)
            return FireResult(res, res.receipt or draft, tb, upstream_rows)

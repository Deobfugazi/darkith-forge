"""schema.py — the receipt, and the states it makes unrepresentable.

A receipt is the atomic unit of state: one decision, by one engine, on one boundary, at one
epoch, content-addressed by its own bytes. Two properties are enforced at construction so
that no later layer has to trust them:

  1. No undefined pass. A DEGRADED verdict without a named degraded_class is refused. That
     is the failure mode every policy engine has: an unhandled state that reads as allow.
  2. No contradictory receipt. A non-DEGRADED verdict may not carry a degraded_class, so
     "allowed, but degraded" is not expressible — it is one verdict or the other.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple


class Verdict(Enum):
    ALLOW = "allow"
    DENY = "deny"
    ROUTE = "route"
    OBSERVE = "observe"
    DEGRADED = "degraded"


class DegradedClass(Enum):
    """Why a verdict is degraded. A degraded receipt must name one of these."""

    UPSTREAM_MISSING = "upstream_missing"
    UPSTREAM_STALE = "upstream_stale"
    STALE_EPOCH = "stale_epoch"
    INTERNAL_ERROR = "internal_error"
    POLICY_MISSING = "policy_missing"
    DOWNSTREAM_OF_DEGRADED = "downstream_of_degraded"


class SchemaViolation(ValueError):
    """Raised at construction when a receipt would encode an unrepresentable state."""


@dataclass(frozen=True)
class Receipt:
    engine_id: str
    boundary: str
    epoch: int
    seq: int
    lane: str
    input_hash: str
    verdict: Verdict
    clause: str
    degraded_class: Optional[DegradedClass] = None
    upstream_ids: Tuple[str, ...] = ()
    policy_version: str = "v0"
    witness: str = ""
    t_wall_ns: int = 0

    def __post_init__(self) -> None:
        if not self.engine_id or not self.boundary or not self.clause:
            raise SchemaViolation("engine_id, boundary, and clause are required and non-empty")
        if not self.lane:
            raise SchemaViolation("lane is required and non-empty")
        if not isinstance(self.epoch, int) or self.epoch < 0:
            raise SchemaViolation(f"epoch must be a non-negative int, got {self.epoch!r}")
        if not isinstance(self.seq, int) or self.seq < 0:
            raise SchemaViolation(f"seq must be a non-negative int, got {self.seq!r}")
        if not isinstance(self.verdict, Verdict):
            raise SchemaViolation(f"verdict must be a Verdict, got {type(self.verdict).__name__}")
        if self.verdict == Verdict.DEGRADED and self.degraded_class is None:
            raise SchemaViolation(
                "DEGRADED verdict requires a non-null degraded_class -- a degraded receipt "
                "with no named class is exactly the undefined-pass failure this schema exists "
                "to prevent."
            )
        if self.verdict != Verdict.DEGRADED and self.degraded_class is not None:
            raise SchemaViolation(
                f"verdict={self.verdict.value} must not carry a degraded_class "
                f"(got {self.degraded_class.value}); degraded_class is reserved for verdict=degraded."
            )

    @property
    def receipt_id(self) -> str:
        content = (
            f"{self.engine_id}|{self.boundary}|{self.epoch}|{self.seq}|{self.lane}|"
            f"{self.input_hash}|{self.verdict.value}|{self.clause}|"
            f"{self.degraded_class.value if self.degraded_class else ''}|"
            f"{','.join(sorted(self.upstream_ids))}|{self.policy_version}|"
            f"{self.witness}|{self.t_wall_ns}"
        )
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def to_row(self) -> dict:
        return {
            "receipt_id": self.receipt_id,
            "engine_id": self.engine_id,
            "boundary": self.boundary,
            "epoch": self.epoch,
            "seq": self.seq,
            "lane": self.lane,
            "input_hash": self.input_hash,
            "verdict": self.verdict.value,
            "degraded_class": self.degraded_class.value if self.degraded_class else None,
            "clause": self.clause,
            "upstream_ids": ",".join(self.upstream_ids),
            "policy_version": self.policy_version,
            "witness": self.witness,
            "t_wall_ns": self.t_wall_ns,
        }

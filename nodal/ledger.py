"""ledger.py — append-only, hash-chained storage. The proof, not a promise.

Every guarantee here is enforced by the storage layer, so a caller cannot opt out of it:

  - Per-lane hash chain. Each receipt's `witness` is the previous receipt's id in its lane,
    or GENESIS_WITNESS for the lane's first. append() computes it from the ledger's own head,
    so a caller cannot forge ancestry by supplying a witness.
  - Genesis anchoring. A lane's first receipt chains to a fixed constant, so truncating a
    lane's history is detectable: the recomputed first witness will not match.
  - Storage-layer immutability. BEFORE UPDATE and BEFORE DELETE triggers RAISE(ROLLBACK).
    An out-of-band SQL mutation is not "discouraged" — it cannot commit.
  - Upstream existence. A non-degraded receipt citing an upstream id absent from the ledger
    is rejected. A bot that lacks its upstream must fire DEGRADED/UPSTREAM_MISSING instead
    of citing evidence it never read.
  - Epoch fencing. A receipt may not be appended to an epoch below its lane's high-water
    mark unless it is itself degraded, so a stale writer cannot rewrite the past.
  - Read barrier. read_asof(epoch) sees only epochs strictly below `epoch`, which is the
    concrete mechanism behind "every bot in epoch E sees the same frozen view".
  - Content recomputation. verify_chain() rebuilds each receipt from its stored fields and
    compares the resulting id, so tampering that also fixes the witness pointer is caught.
"""
from __future__ import annotations

import hashlib
import sqlite3
import threading
from dataclasses import dataclass
from typing import List, Optional

from .schema import DegradedClass, Receipt, Verdict

GENESIS_WITNESS = hashlib.sha256(b"DARKITH_NODAL_GENESIS_v1").hexdigest()

_COLUMNS = (
    "receipt_id",
    "engine_id",
    "boundary",
    "epoch",
    "seq",
    "lane",
    "input_hash",
    "verdict",
    "degraded_class",
    "clause",
    "upstream_ids",
    "policy_version",
    "witness",
    "t_wall_ns",
)


class LedgerError(ValueError):
    """Raised for a malformed ledger operation (not for a rejected append)."""


@dataclass
class AppendResult:
    accepted: bool
    receipt_id: Optional[str]
    reason: Optional[str] = None
    # The receipt as actually persisted, with the ledger-computed witness. Callers must chain
    # on this, never on their own draft: a draft's id cannot match the stored row, so citing
    # it downstream would look like a phantom dependency.
    receipt: Optional[Receipt] = None


class Ledger:
    def __init__(self, path: str = ":memory:") -> None:
        self.path = path
        self._local = threading.local()
        self._init_schema()

    @property
    def conn(self) -> sqlite3.Connection:
        # One connection per thread: a shared connection across threads is a race, and this
        # ledger's whole claim is that concurrent writers cannot corrupt it.
        if not hasattr(self._local, "conn"):
            conn = sqlite3.connect(self.path, check_same_thread=False, timeout=30.0)
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute("PRAGMA journal_mode = WAL")
            self._local.conn = conn
        return self._local.conn

    def _init_schema(self) -> None:
        c = self.conn
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS receipts (
                receipt_id      TEXT PRIMARY KEY,
                engine_id       TEXT NOT NULL,
                boundary        TEXT NOT NULL,
                epoch           INTEGER NOT NULL,
                seq             INTEGER NOT NULL,
                lane            TEXT NOT NULL,
                input_hash      TEXT NOT NULL,
                verdict         TEXT NOT NULL,
                degraded_class  TEXT,
                clause          TEXT NOT NULL,
                upstream_ids    TEXT NOT NULL,
                policy_version  TEXT NOT NULL,
                witness         TEXT NOT NULL,
                t_wall_ns       INTEGER NOT NULL,
                UNIQUE(lane, seq)
            )
            """
        )
        c.execute(
            """
            CREATE TRIGGER IF NOT EXISTS no_update_receipts
            BEFORE UPDATE ON receipts
            BEGIN SELECT RAISE(ROLLBACK, 'receipts is append-only: UPDATE forbidden'); END
            """
        )
        c.execute(
            """
            CREATE TRIGGER IF NOT EXISTS no_delete_receipts
            BEFORE DELETE ON receipts
            BEGIN SELECT RAISE(ROLLBACK, 'receipts is append-only: DELETE forbidden'); END
            """
        )
        c.execute("CREATE INDEX IF NOT EXISTS idx_lane_seq ON receipts(lane, seq)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_epoch ON receipts(epoch)")
        c.commit()

    def _lane_head(self, lane: str) -> Optional[str]:
        row = self.conn.execute(
            "SELECT receipt_id FROM receipts WHERE lane=? ORDER BY seq DESC LIMIT 1", (lane,)
        ).fetchone()
        return row[0] if row else None

    def _lane_max_epoch(self, lane: str) -> int:
        row = self.conn.execute("SELECT MAX(epoch) FROM receipts WHERE lane=?", (lane,)).fetchone()
        return row[0] if row and row[0] is not None else -1

    def _exists(self, receipt_id: str) -> bool:
        row = self.conn.execute(
            "SELECT 1 FROM receipts WHERE receipt_id=?", (receipt_id,)
        ).fetchone()
        return row is not None

    def append(self, draft: Receipt) -> AppendResult:
        head = self._lane_head(draft.lane)
        real_witness = head if head is not None else GENESIS_WITNESS

        max_epoch = self._lane_max_epoch(draft.lane)
        if draft.epoch < max_epoch and draft.verdict != Verdict.DEGRADED:
            return AppendResult(
                accepted=False,
                receipt_id=None,
                reason=(
                    f"stale epoch: {draft.epoch} < lane high-water {max_epoch} on {draft.lane!r}; "
                    f"a stale writer may only append a degraded receipt"
                ),
            )

        final = Receipt(
            engine_id=draft.engine_id,
            boundary=draft.boundary,
            epoch=draft.epoch,
            seq=draft.seq,
            lane=draft.lane,
            input_hash=draft.input_hash,
            verdict=draft.verdict,
            clause=draft.clause,
            degraded_class=draft.degraded_class,
            upstream_ids=draft.upstream_ids,
            policy_version=draft.policy_version,
            witness=real_witness,
            t_wall_ns=draft.t_wall_ns,
        )

        if final.verdict != Verdict.DEGRADED:
            missing = [u for u in final.upstream_ids if not self._exists(u)]
            if missing:
                return AppendResult(
                    accepted=False,
                    receipt_id=None,
                    reason=(
                        f"upstream_ids not found in ledger: {missing}. Fire a "
                        f"DEGRADED/UPSTREAM_MISSING receipt instead of citing evidence "
                        f"that does not exist."
                    ),
                )

        row = final.to_row()
        try:
            self.conn.execute(
                f"INSERT INTO receipts ({', '.join(_COLUMNS)}) "
                f"VALUES ({', '.join('?' for _ in _COLUMNS)})",
                tuple(row[c] for c in _COLUMNS),
            )
            self.conn.commit()
            return AppendResult(accepted=True, receipt_id=final.receipt_id, receipt=final)
        except sqlite3.IntegrityError as exc:
            self.conn.rollback()
            return AppendResult(
                accepted=False,
                receipt_id=None,
                reason=f"integrity error (duplicate seq in lane?): {exc}",
            )

    def read_asof(self, epoch: int, lane: Optional[str] = None) -> List[dict]:
        query = "SELECT * FROM receipts WHERE epoch < ?"
        params: list = [epoch]
        if lane is not None:
            query += " AND lane = ?"
            params.append(lane)
        query += " ORDER BY epoch, seq"
        rows = self.conn.execute(query, params).fetchall()
        return [dict(zip(_COLUMNS, r)) for r in rows]

    def get(self, receipt_id: str) -> Optional[dict]:
        row = self.conn.execute("SELECT * FROM receipts WHERE receipt_id=?", (receipt_id,)).fetchone()
        return dict(zip(_COLUMNS, row)) if row else None

    def lane_receipts(self, lane: str) -> List[dict]:
        rows = self.conn.execute(
            "SELECT * FROM receipts WHERE lane=? ORDER BY seq", (lane,)
        ).fetchall()
        return [dict(zip(_COLUMNS, r)) for r in rows]

    def lanes(self) -> List[str]:
        rows = self.conn.execute("SELECT DISTINCT lane FROM receipts ORDER BY lane").fetchall()
        return [r[0] for r in rows]

    def count(self) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM receipts").fetchone()[0]

    def verify_chain(self, lane: str) -> List[str]:
        """Recompute every receipt from its stored fields. Empty list means intact."""
        problems: List[str] = []
        prev_id = GENESIS_WITNESS
        for row in self.lane_receipts(lane):
            upstream = tuple(row["upstream_ids"].split(",")) if row["upstream_ids"] else ()
            try:
                recomputed = Receipt(
                    engine_id=row["engine_id"],
                    boundary=row["boundary"],
                    epoch=row["epoch"],
                    seq=row["seq"],
                    lane=row["lane"],
                    input_hash=row["input_hash"],
                    verdict=Verdict(row["verdict"]),
                    clause=row["clause"],
                    degraded_class=(
                        DegradedClass(row["degraded_class"]) if row["degraded_class"] else None
                    ),
                    upstream_ids=upstream,
                    policy_version=row["policy_version"],
                    witness=prev_id,
                    t_wall_ns=row["t_wall_ns"],
                ).receipt_id
            except ValueError as exc:
                problems.append(f"lane={lane} seq={row['seq']}: unreadable row ({exc})")
                prev_id = row["receipt_id"]
                continue

            if row["witness"] != prev_id:
                problems.append(
                    f"lane={lane} seq={row['seq']}: witness={row['witness']!r} "
                    f"but expected {prev_id!r}"
                )
            if recomputed != row["receipt_id"]:
                problems.append(
                    f"lane={lane} seq={row['seq']}: content hash mismatch "
                    f"(stored {row['receipt_id'][:12]}, recomputed {recomputed[:12]})"
                )
            prev_id = row["receipt_id"]
        return problems

    def verify_all(self) -> List[str]:
        problems: List[str] = []
        for lane in self.lanes():
            problems.extend(self.verify_chain(lane))
        return problems

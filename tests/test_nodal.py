#!/usr/bin/env python3
"""test_nodal.py — every invariant of the Auto-Nodal Co-ordina-Sync substrate, proven.

Each test asserts a property the prose claimed and a naive implementation would only
promise. No mocks: real SQLite, real receipts, real firing.

Run: python3 tests/test_nodal.py
"""
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from nodal import (  # noqa: E402
    BotRegistration,
    DegradedClass,
    FireOrderViolation,
    Ledger,
    NodalBot,
    Receipt,
    SchemaViolation,
    Verdict,
    compute_fire_order,
    reconcile,
)
from nodal.engine import propagate_degraded  # noqa: E402


def receipt(**over):
    base = dict(
        engine_id="engine_a",
        boundary="a.check",
        epoch=0,
        seq=0,
        lane="lane_a",
        input_hash="h0",
        verdict=Verdict.ALLOW,
        clause="a.rule",
    )
    base.update(over)
    return Receipt(**base)


class TestSchema(unittest.TestCase):
    def test_wellformed_receipt_constructs(self):
        self.assertEqual(len(receipt().receipt_id), 64)

    def test_degraded_without_class_is_refused(self):
        with self.assertRaises(SchemaViolation):
            receipt(verdict=Verdict.DEGRADED)

    def test_allow_with_degraded_class_is_refused(self):
        with self.assertRaises(SchemaViolation):
            receipt(verdict=Verdict.ALLOW, degraded_class=DegradedClass.STALE_EPOCH)

    def test_empty_engine_id_is_refused(self):
        with self.assertRaises(SchemaViolation):
            receipt(engine_id="")

    def test_empty_clause_is_refused(self):
        with self.assertRaises(SchemaViolation):
            receipt(clause="")

    def test_negative_epoch_is_refused(self):
        with self.assertRaises(SchemaViolation):
            receipt(epoch=-1)

    def test_content_addressing_is_deterministic(self):
        self.assertEqual(receipt().receipt_id, receipt().receipt_id)

    def test_content_addressing_is_sensitive(self):
        self.assertNotEqual(receipt().receipt_id, receipt(seq=1).receipt_id)

    def test_upstream_order_does_not_change_identity(self):
        a = receipt(seq=1, upstream_ids=("x", "y"))
        b = receipt(seq=1, upstream_ids=("y", "x"))
        self.assertEqual(a.receipt_id, b.receipt_id)


class TestLedger(unittest.TestCase):
    def setUp(self):
        self.L = Ledger()

    def test_first_receipt_anchors_to_genesis(self):
        from nodal import GENESIS_WITNESS

        res = self.L.append(receipt())
        self.assertTrue(res.accepted)
        self.assertEqual(self.L.get(res.receipt_id)["witness"], GENESIS_WITNESS)

    def test_second_receipt_chains_to_first(self):
        r1 = self.L.append(receipt(seq=0)).receipt_id
        r2 = self.L.append(receipt(seq=1, epoch=1)).receipt_id
        self.assertEqual(self.L.get(r2)["witness"], r1)

    def test_caller_cannot_forge_witness(self):
        r1 = self.L.append(receipt(seq=0)).receipt_id
        forged = self.L.append(receipt(seq=1, epoch=1, witness="FORGED" + "0" * 58))
        self.assertEqual(self.L.get(forged.receipt_id)["witness"], r1)

    def test_missing_upstream_is_rejected(self):
        res = self.L.append(receipt(upstream_ids=("deadbeef",)))
        self.assertFalse(res.accepted)
        self.assertIn("upstream_ids not found", res.reason)

    def test_degraded_may_cite_missing_upstream(self):
        res = self.L.append(
            receipt(
                verdict=Verdict.DEGRADED,
                degraded_class=DegradedClass.UPSTREAM_MISSING,
                upstream_ids=("deadbeef",),
            )
        )
        self.assertTrue(res.accepted)

    def test_real_upstream_is_accepted(self):
        up = self.L.append(receipt(seq=0)).receipt_id
        self.assertTrue(self.L.append(receipt(seq=1, epoch=1, upstream_ids=(up,))).accepted)

    def test_read_barrier_hides_same_epoch(self):
        r0 = self.L.append(receipt(epoch=0, seq=0)).receipt_id
        r1 = self.L.append(receipt(epoch=1, seq=1)).receipt_id
        visible = {row["receipt_id"] for row in self.L.read_asof(1)}
        self.assertIn(r0, visible)
        self.assertNotIn(r1, visible)

    def test_duplicate_lane_seq_is_rejected(self):
        self.assertTrue(self.L.append(receipt(seq=0)).accepted)
        self.assertFalse(self.L.append(receipt(seq=0, input_hash="other")).accepted)

    def test_stale_epoch_write_is_fenced(self):
        self.L.append(receipt(epoch=5, seq=0))
        stale = self.L.append(receipt(epoch=1, seq=1))
        self.assertFalse(stale.accepted)
        self.assertIn("stale epoch", stale.reason)

    def test_stale_epoch_may_append_degraded(self):
        self.L.append(receipt(epoch=5, seq=0))
        ok = self.L.append(
            receipt(epoch=1, seq=1, verdict=Verdict.DEGRADED,
                    degraded_class=DegradedClass.STALE_EPOCH)
        )
        self.assertTrue(ok.accepted)

    def test_update_trigger_blocks_mutation(self):
        rid = self.L.append(receipt()).receipt_id
        with self.assertRaises(Exception):
            self.L.conn.execute("UPDATE receipts SET verdict='deny' WHERE receipt_id=?", (rid,))
            self.L.conn.commit()
        self.L.conn.rollback()
        self.assertEqual(self.L.get(rid)["verdict"], "allow")

    def test_delete_trigger_blocks_removal(self):
        rid = self.L.append(receipt()).receipt_id
        with self.assertRaises(Exception):
            self.L.conn.execute("DELETE FROM receipts WHERE receipt_id=?", (rid,))
            self.L.conn.commit()
        self.L.conn.rollback()
        self.assertIsNotNone(self.L.get(rid))

    def test_verify_chain_detects_witness_tampering(self):
        self.L.append(receipt(seq=0))
        r1 = self.L.append(receipt(seq=1, epoch=1)).receipt_id
        self.L.conn.execute("DROP TRIGGER no_update_receipts")
        self.L.conn.execute("UPDATE receipts SET witness='FORGED' WHERE receipt_id=?", (r1,))
        self.L.conn.commit()
        self.assertTrue(self.L.verify_chain("lane_a"))

    def test_verify_chain_detects_content_tampering(self):
        rid = self.L.append(receipt(seq=0)).receipt_id
        self.L.conn.execute("DROP TRIGGER no_update_receipts")
        self.L.conn.execute("UPDATE receipts SET clause='a.different' WHERE receipt_id=?", (rid,))
        self.L.conn.commit()
        problems = self.L.verify_chain("lane_a")
        self.assertTrue(any("content hash mismatch" in p for p in problems), problems)

    def test_verify_all_covers_every_lane(self):
        self.L.append(receipt(lane="lane_a", seq=0))
        self.L.append(receipt(lane="lane_b", engine_id="engine_b", seq=0))
        self.assertEqual(sorted(self.L.lanes()), ["lane_a", "lane_b"])
        self.assertEqual(self.L.verify_all(), [])

    def test_seq_recovers_after_restart(self):
        self.L.append(receipt(seq=0))
        self.L.append(receipt(seq=1, epoch=1))
        self.assertEqual(NodalBot(self.L, lane="lane_a")._seq, 2)


class _AllowBot(NodalBot):
    engine_id = "engine_allow"
    boundary = "allow.check"

    def decide(self, input_obj, upstream_rows):
        return Verdict.ALLOW, "allow.ok", None


class _RaiseBot(NodalBot):
    engine_id = "engine_raise"
    boundary = "raise.check"

    def decide(self, input_obj, upstream_rows):
        raise RuntimeError("deliberate explosion")


class _DownstreamBot(NodalBot):
    engine_id = "engine_downstream"
    boundary = "downstream.check"

    def decide(self, input_obj, upstream_rows):
        return propagate_degraded(receipt(engine_id=self.engine_id), upstream_rows)


class TestBotTotality(unittest.TestCase):
    def setUp(self):
        self.L = Ledger()

    def test_fire_returns_receipt_for_normal_input(self):
        res = _AllowBot(self.L, lane="lane_allow").fire("x", epoch=0)
        self.assertTrue(res.accepted)
        self.assertEqual(res.verdict, Verdict.ALLOW)

    def test_raising_decide_becomes_degraded_not_crash(self):
        res = _RaiseBot(self.L, lane="lane_raise").fire("x", epoch=0)
        self.assertTrue(res.accepted)
        self.assertEqual(res.verdict, Verdict.DEGRADED)
        self.assertEqual(res.receipt.degraded_class, DegradedClass.INTERNAL_ERROR)
        self.assertIn("RuntimeError", res.traceback)

    def test_missing_upstream_becomes_degraded_not_wait(self):
        res = _AllowBot(self.L, lane="lane_allow").fire("x", epoch=0, upstream_ids=("nope",))
        self.assertTrue(res.accepted)
        self.assertEqual(res.receipt.degraded_class, DegradedClass.UPSTREAM_MISSING)

    def test_downstream_of_degraded_is_marked(self):
        bad = _RaiseBot(self.L, lane="lane_raise").fire("x", epoch=0)
        res = _DownstreamBot(self.L, lane="lane_ds").fire(
            "x", epoch=1, upstream_ids=(bad.receipt.receipt_id,)
        )
        self.assertEqual(res.verdict, Verdict.DEGRADED)
        self.assertEqual(res.receipt.degraded_class, DegradedClass.DOWNSTREAM_OF_DEGRADED)

    def test_fire_never_raises_across_a_fuzz_of_inputs(self):
        bot = _AllowBot(self.L, lane="lane_allow")
        for i, obj in enumerate([None, 0, "", [], {}, object(), 3.14, b"bytes"]):
            res = bot.fire(obj, epoch=i)
            self.assertIsInstance(res.receipt, Receipt)
            self.assertIsNotNone(res.receipt.receipt_id)


class TestFireOrder(unittest.TestCase):
    def test_upstream_fires_first(self):
        regs = [
            BotRegistration("e2", "b2", upstream_engine_ids=("e1",)),
            BotRegistration("e1", "b1"),
        ]
        self.assertEqual(compute_fire_order(regs, "1"), ["e1", "e2"])

    def test_order_is_deterministic_across_calls(self):
        regs = [BotRegistration(f"e{i}", "b") for i in range(8)]
        first = compute_fire_order(regs, "7")
        for _ in range(5):
            self.assertEqual(compute_fire_order(list(reversed(regs)), "7"), first)

    def test_cycle_is_rejected(self):
        regs = [
            BotRegistration("e1", "b", upstream_engine_ids=("e2",)),
            BotRegistration("e2", "b", upstream_engine_ids=("e1",)),
        ]
        with self.assertRaises(FireOrderViolation):
            compute_fire_order(regs, "1")

    def test_self_cycle_is_rejected(self):
        with self.assertRaises(FireOrderViolation):
            compute_fire_order([BotRegistration("e1", "b", upstream_engine_ids=("e1",))], "1")

    def test_unregistered_upstream_is_rejected(self):
        with self.assertRaises(FireOrderViolation):
            compute_fire_order([BotRegistration("e1", "b", upstream_engine_ids=("ghost",))], "1")

    def test_duplicate_registration_is_rejected(self):
        with self.assertRaises(FireOrderViolation):
            compute_fire_order([BotRegistration("e1", "b"), BotRegistration("e1", "b2")], "1")

    def test_diamond_order_respects_both_parents(self):
        regs = [
            BotRegistration("a", "b"),
            BotRegistration("b", "b", upstream_engine_ids=("a",)),
            BotRegistration("c", "b", upstream_engine_ids=("a",)),
            BotRegistration("d", "b", upstream_engine_ids=("b", "c")),
        ]
        order = compute_fire_order(regs, "1")
        self.assertLess(order.index("a"), order.index("b"))
        self.assertLess(order.index("a"), order.index("c"))
        self.assertLess(order.index("b"), order.index("d"))
        self.assertLess(order.index("c"), order.index("d"))


class TestReconcile(unittest.TestCase):
    def test_agreeing_receipts_reconcile(self):
        rs = [receipt(engine_id="e1", clause="c1"), receipt(engine_id="e2", clause="c2", seq=1)]
        out = reconcile(rs, precedence=["e1", "e2"])
        self.assertTrue(out.agreed)
        self.assertEqual(out.canonical_id, rs[0].receipt_id)

    def test_precedence_decides_not_arrival_order(self):
        rs = [receipt(engine_id="e2", clause="c2"), receipt(engine_id="e1", clause="c1", seq=1)]
        self.assertEqual(reconcile(rs, precedence=["e1", "e2"]).canonical_id, rs[1].receipt_id)

    def test_disagreement_produces_named_verdict(self):
        rs = [
            receipt(engine_id="e1", clause="c1", verdict=Verdict.ALLOW),
            receipt(engine_id="e2", clause="c2", seq=1, verdict=Verdict.DENY),
        ]
        out = reconcile(rs, precedence=["e1", "e2"])
        self.assertFalse(out.agreed)
        self.assertIn("e2:c2=deny", out.reason)
        self.assertEqual(out.clause, "coordina.reconcile.divergent")

    def test_unranked_engine_cannot_be_canonical(self):
        out = reconcile([receipt(engine_id="mystery", clause="c")], precedence=["e1"])
        self.assertFalse(out.agreed)
        self.assertIsNone(out.canonical_id)
        self.assertEqual(out.clause, "coordina.reconcile.unranked")

    def test_empty_reconcile_is_total(self):
        out = reconcile([], precedence=[])
        self.assertTrue(out.agreed)
        self.assertIsNone(out.canonical_id)


class TestEndToEnd(unittest.TestCase):
    def test_closed_loop(self):
        L = Ledger()

        class Friction(NodalBot):
            engine_id = "engine_1_friction"
            boundary = "friction.classify"

            def decide(self, input_obj, upstream_rows):
                if input_obj == "slow_build":
                    return Verdict.ROUTE, "friction.build_slow", None
                return Verdict.ALLOW, "friction.ok", None

        class Integrity(NodalBot):
            engine_id = "engine_4_integrity"
            boundary = "integrity.gate"

            def decide(self, input_obj, upstream_rows):
                if any(r["verdict"] == Verdict.ROUTE.value for r in upstream_rows):
                    return Verdict.DENY, "integrity.flow_regression", None
                return Verdict.ALLOW, "integrity.ok", None

        regs = [
            BotRegistration("engine_4_integrity", "integrity.gate",
                            upstream_engine_ids=("engine_1_friction",)),
            BotRegistration("engine_1_friction", "friction.classify"),
        ]
        self.assertEqual(
            compute_fire_order(regs, "1"),
            ["engine_1_friction", "engine_4_integrity"],
        )

        e1 = Friction(L, lane="lane_friction").fire("slow_build", epoch=1)
        self.assertEqual(e1.verdict, Verdict.ROUTE)

        e4 = Integrity(L, lane="lane_integrity").fire(
            "pr_123", epoch=2, upstream_ids=(e1.receipt.receipt_id,)
        )
        self.assertEqual(e4.verdict, Verdict.DENY)

        self.assertEqual(L.verify_all(), [])
        self.assertEqual(L.count(), 2)

        with self.assertRaises(Exception):
            L.conn.execute("UPDATE receipts SET verdict='allow'")
            L.conn.commit()
        L.conn.rollback()
        self.assertEqual(L.get(e1.receipt.receipt_id)["verdict"], "route")


if __name__ == "__main__":
    unittest.main(verbosity=2)

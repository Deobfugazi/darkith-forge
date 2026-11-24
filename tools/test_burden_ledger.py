#!/usr/bin/env python3
"""Tests for the burden ledger and the mint gate.

The negative cases are the point.  A gate that only proves it can pass is not a gate.
"""

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import burden_ledger as BL
import mint_gate as MG


class TestAddressability(unittest.TestCase):
    def test_drought_is_addressable(self):
        self.assertEqual(BL.addressability("Drought/drier conditions"), "addressable")

    def test_conflict_is_conflict(self):
        self.assertEqual(BL.addressability("Conflict/ Violence"), "conflict")

    def test_mixed_is_conflict(self):
        # Finance cannot reach the drought while the conflict persists.
        self.assertEqual(
            BL.addressability("Conflict/ Violence,Drought/drier conditions"), "conflict")

    def test_empty_drivers_not_addressable(self):
        # Unknown is not the same as addressable.
        self.assertNotEqual(BL.addressability(""), "addressable")

    def test_case_insensitive(self):
        self.assertEqual(BL.addressability("CONFLICT/ VIOLENCE"), "conflict")


class TestLedgerValidation(unittest.TestCase):
    def test_g1_missing_source_convicted(self):
        led = {"burdens": [{"crisis": "x", "drivers": "Drought", "addressability": "addressable"}]}
        probs = BL.validate(led)
        self.assertTrue(any("G1" in p for p in probs))

    def test_g2_misclassified_convicted(self):
        led = {"burdens": [{
            "crisis": "x", "drivers": "Conflict/ Violence",
            "addressability": "addressable", "source": "s", "retrieved": "t"}]}
        probs = BL.validate(led)
        self.assertTrue(any("G2" in p for p in probs))

    def test_clean_ledger_passes(self):
        led = {"burdens": [{
            "crisis": "x", "drivers": "Drought", "addressability": "addressable",
            "source": "INFORM", "retrieved": "2026-11-12T00:00:00Z"}]}
        self.assertEqual(BL.validate(led), [])

    def test_counts(self):
        burdens = [
            {"severity_class": "Very High", "trend": "Increasing", "addressability": "addressable"},
            {"severity_class": "High", "trend": "Stable", "addressability": "conflict"},
            {"severity_class": "Medium", "trend": "Increasing", "addressability": "addressable"},
        ]
        c = BL._counts(burdens)
        self.assertEqual(c["total"], 3)
        self.assertEqual(c["very_high"], 1)
        self.assertEqual(c["high"], 1)
        self.assertEqual(c["worsening"], 2)
        self.assertEqual(c["addressable"], 2)
        self.assertEqual(c["conflict"], 1)


class TestMintGate(unittest.TestCase):
    def setUp(self):
        self.good = MG.freeze_baseline(MG.GOOD)

    def grade(self, **paths):
        return MG.grade(MG._mutate(self.good, **paths))[0]

    def test_good_record_passes(self):
        self.assertEqual(MG.grade(self.good)[0], "PASS")

    def test_self_attested_measurer_is_a_lie(self):
        self.assertEqual(self.grade(measurement__measurer="NGO-A"), "LIED")

    def test_no_permanence_bond_is_a_lie(self):
        self.assertEqual(self.grade(permanence__bond_pct=0), "LIED")

    def test_no_horizon_is_a_lie(self):
        self.assertEqual(self.grade(permanence__months=0), "LIED")

    def test_negative_horizon_is_a_lie(self):
        self.assertEqual(self.grade(permanence__months=-12), "LIED")

    def test_unrunnable_closure_is_a_lie(self):
        self.assertEqual(self.grade(closure__command=""), "LIED")

    def test_no_payer_is_a_lie(self):
        # G9: the binding constraint.  No payer, no mint.
        self.assertEqual(self.grade(payer__name=""), "LIED")

    def test_no_source_is_a_lie(self):
        self.assertEqual(self.grade(burden__source=""), "LIED")

    def test_no_retrieval_date_is_a_lie(self):
        self.assertEqual(self.grade(burden__retrieved=""), "LIED")

    def test_no_counterfactual_is_a_lie(self):
        # This is the carbon-offset corpse.
        self.assertEqual(self.grade(baseline__counterfactual=""), "LIED")

    def test_conflict_crisis_is_a_lie(self):
        self.assertEqual(self.grade(burden__drivers="Conflict/ Violence"), "LIED")

    def test_insolvent_treasury_is_a_lie(self):
        self.assertEqual(self.grade(treasury__vouchers_outstanding=200000), "LIED")

    def test_bad_economics_is_blocked_not_lied(self):
        # Bad economics is a business problem, not a false claim.
        self.assertEqual(self.grade(economics__verification_cost=90000), "BLOCKED")

    def test_unknown_economics_is_review(self):
        # The gate must not pass what it could not check.
        self.assertEqual(self.grade(economics__verification_cost=None), "REVIEW")

    def test_unknown_measurer_is_review(self):
        self.assertEqual(self.grade(measurement__measurer=None), "REVIEW")

    def test_missing_baseline_hash_is_a_lie(self):
        rec = MG._mutate(self.good, baseline__sha256="")
        self.assertEqual(MG.grade(rec)[0], "LIED")


class TestBaselineFreeze(unittest.TestCase):
    def test_intact_after_freeze(self):
        self.assertTrue(MG.baseline_intact(MG.freeze_baseline(MG.GOOD)))

    def test_drift_detected(self):
        frozen = MG.freeze_baseline(MG.GOOD)
        drifted = json.loads(json.dumps(frozen))
        drifted["baseline"]["value"] = 20.0
        self.assertFalse(MG.baseline_intact(drifted))

    def test_counterfactual_drift_detected(self):
        frozen = MG.freeze_baseline(MG.GOOD)
        drifted = json.loads(json.dumps(frozen))
        drifted["baseline"]["counterfactual"] = "something more convenient"
        self.assertFalse(MG.baseline_intact(drifted))

    def test_freeze_is_deterministic(self):
        self.assertEqual(MG.freeze_baseline(MG.GOOD)["baseline"]["sha256"],
                         MG.freeze_baseline(MG.GOOD)["baseline"]["sha256"])

    def test_freeze_does_not_mutate_input(self):
        MG.freeze_baseline(MG.GOOD)
        self.assertNotIn("sha256", MG.GOOD["baseline"])


class TestSelftestEntry(unittest.TestCase):
    def test_selftest_passes(self):
        self.assertEqual(MG.selftest(), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)

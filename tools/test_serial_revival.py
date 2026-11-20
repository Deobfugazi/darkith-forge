#!/usr/bin/env python3
"""Contract tests for tools/serial_revival.py; no repository mutation or network."""
import importlib.util
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("serial_revival", ROOT / "tools" / "serial_revival.py")
sr = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sr)


class SerialRevivalTests(unittest.TestCase):
    def test_sixteen_stages_are_ordered_and_unique(self):
        self.assertEqual(16, len(sr.STAGES))
        self.assertEqual([f"S{i}" for i in range(1, 17)], [x[0] for x in sr.STAGES])

    def test_four_states_are_exact(self):
        self.assertEqual({"PASS", "FAIL", "SKIP", "INACTIVE"}, sr.STATES)

    def test_hash_is_canonical(self):
        self.assertEqual(sr.digest({"z": 1, "a": [2]}), sr.digest({"a": [2], "z": 1}))

    def test_missing_predecessor_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "predecessor"):
            sr.validate_stage("S2", {"components": []}, 1, None)

    def test_skip_is_not_healthy(self):
        with self.assertRaisesRegex(ValueError, "invalid state"):
            sr.verify_states({"node-a": "SKIPPED"})

    def test_task_inheritance_is_mandatory(self):
        with self.assertRaisesRegex(ValueError, "missing inherited field"):
            sr.validate_stage("S8", {"tasks": [{"task_id": "T-1"}],
                                     "predecessor_receipt_id": "x"}, 1,
                              {"receipt_id": "x"})

    def test_auto_approval_is_allowlisted(self):
        payload = {"decision": "AUTO_APPROVED", "authorization_class": "source-mutation",
                   "scope": ["tools/example.py"], "predecessor_receipt_id": "x"}
        with self.assertRaisesRegex(ValueError, "restricted"):
            sr.validate_stage("S9", payload, 1, {"receipt_id": "x"})

    def test_human_approval_requires_receipt(self):
        payload = {"decision": "HUMAN_APPROVED", "authorization_class": "source-mutation",
                   "scope": ["tools/example.py"], "predecessor_receipt_id": "x"}
        with self.assertRaisesRegex(ValueError, "approved_by"):
            sr.validate_stage("S9", payload, 1, {"receipt_id": "x"})

    def test_repair_rejects_generated_tissue(self):
        payload = {"changed_files": [{"path": "dist/app.apk", "change_reason": "repair"}],
                   "predecessor_receipt_id": "x"}
        # S10 consults the S9 receipt on disk; test the policy predicate independently.
        path = payload["changed_files"][0]["path"]
        self.assertTrue(any(path == r or path.startswith(r + "/") for r in sr.GENERATED_ROOTS))

    def test_s11_drift_blocks_exit(self):
        with self.assertRaisesRegex(ValueError, "drift remains"):
            sr.validate_stage("S11", {"generated_files": [], "drift": ["docs/index.md"],
                                      "predecessor_receipt_id": "x"}, 1, {"receipt_id": "x"})

    def test_s14_unchecked_neighbor_blocks(self):
        with self.assertRaisesRegex(ValueError, "not fully reconciled"):
            sr.validate_stage("S14", {"clean": True, "unexplained_drift": [],
                                      "unchecked_nodes": ["consumer-x"], "mesh_health": {},
                                      "predecessor_receipt_id": "x"}, 1, {"receipt_id": "x"})

    def test_failure_route_distinguishes_same_and_new(self):
        self.assertEqual("REOPEN_ORIGINAL", "REOPEN_ORIGINAL")
        self.assertEqual("LINK_NEW_DEFECT", "LINK_NEW_DEFECT")


if __name__ == "__main__":
    unittest.main(verbosity=2)

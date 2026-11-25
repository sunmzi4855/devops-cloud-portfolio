import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from plan_guard import Rejected, verify


ROOT = Path(__file__).resolve().parent
MAPPING = json.loads((ROOT / "expected-moves.json").read_text())


def example():
    return {
        "format_version": "1.2", "complete": True, "errored": False, "applyable": True,
        "resource_changes": [
            {"address": target, "previous_address": source, "mode": "managed", "change": {"actions": ["no-op"]}}
            for source, target in MAPPING.items()
        ],
    }


class PlanGuardTests(unittest.TestCase):
    def test_expected_moves_and_unrelated_unchanged_resources_pass(self):
        plan = example()
        plan["resource_changes"].append({"address": "terraform_data.other", "change": {"actions": ["no-op"]}})
        plan["output_changes"] = {"database_names": {"actions": ["no-op"]}}
        self.assertEqual(verify(plan, MAPPING), MAPPING)

    def test_create_delete_update_read_and_replacement_actions_fail(self):
        for actions in (["create"], ["delete"], ["update"], ["read"], ["forget"],
                        ["delete", "create"], ["create", "delete"]):
            with self.subTest(actions=actions):
                plan = example()
                plan["resource_changes"].append({"address": "terraform_data.extra", "change": {"actions": actions}})
                with self.assertRaisesRegex(Rejected, "actions"):
                    verify(plan, MAPPING)

    def test_swapped_destinations_fail_even_when_actions_are_noop(self):
        plan = example()
        first, second = plan["resource_changes"]
        first["address"], second["address"] = second["address"], first["address"]
        with self.assertRaisesRegex(Rejected, "unexpected move"):
            verify(plan, MAPPING)

    def test_omitted_and_duplicate_moves_fail(self):
        plan = example()
        removed = plan["resource_changes"].pop()
        with self.assertRaisesRegex(Rejected, "missing expected moves"):
            verify(plan, MAPPING)
        plan["resource_changes"].extend([removed, removed])
        with self.assertRaisesRegex(Rejected, "duplicate move"):
            verify(plan, MAPPING)

    def test_imports_drift_and_output_changes_fail(self):
        plan = example()
        plan["resource_changes"][0]["change"]["importing"] = {"id": "orders"}
        with self.assertRaisesRegex(Rejected, "imports"):
            verify(plan, MAPPING)
        plan = example()
        plan["resource_drift"] = [{"address": "postgresql_database.other", "change": {"actions": ["update"]}}]
        with self.assertRaisesRegex(Rejected, "drift"):
            verify(plan, MAPPING)
        plan = example()
        plan["output_changes"] = {"db_id": {"actions": ["delete"]}}
        with self.assertRaisesRegex(Rejected, "output db_id"):
            verify(plan, MAPPING)

    def test_incomplete_errored_and_unapplicable_plans_fail(self):
        for field, value in (("complete", False), ("errored", True), ("applyable", False),
                             ("deferred_changes", [{"reason": "unknown"}]), ("format_version", "2.0")):
            with self.subTest(field=field):
                with self.assertRaises(Rejected):
                    verify({**example(), field: value}, MAPPING)

    def test_invalid_mappings_and_plan_shapes_fail(self):
        for mapping in ({}, {"old": "old"}, {"a": "c", "b": "c"}, {"a": None}):
            with self.subTest(mapping=mapping), self.assertRaises(Rejected):
                verify(example(), mapping)
        for field, value in (("resource_changes", None), ("resource_drift", {}),
                             ("output_changes", []), ("resource_changes", [None])):
            with self.subTest(field=field), self.assertRaises(Rejected):
                verify({**example(), field: value}, MAPPING)

    def test_cli_exit_status_matches_the_decision(self):
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp) / "plan.json"
            command = [sys.executable, str(ROOT / "plan_guard.py"), str(file), str(ROOT / "expected-moves.json")]
            for contents, status in ((json.dumps(example()), 0), ("{}", 1), ("broken JSON", 1)):
                file.write_text(contents)
                result = subprocess.run(command, capture_output=True, text=True, timeout=5)
                self.assertEqual(result.returncode, status, result.stderr)


if __name__ == "__main__":
    unittest.main()

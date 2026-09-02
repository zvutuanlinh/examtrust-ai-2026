import unittest
from pathlib import Path

from tools import storage_layout as s


EXPECTED_PROJECT = Path(
    "/content/drive/MyDrive/ExamTrust_AI_2026"
)


class StorageLayoutContractTest(unittest.TestCase):

    def test_project_root(self):
        self.assertEqual(
            s.PROJECT_ROOT,
            EXPECTED_PROJECT,
        )

    def test_operational_roots(self):
        self.assertEqual(
            s.AUTOTRACE_ROOT,
            EXPECTED_PROJECT / "EVIDENCE" / "AUTOTRACE",
        )

        self.assertEqual(
            s.DATA_RUNS_ROOT,
            EXPECTED_PROJECT / "EVIDENCE" / "DATA_RUNS",
        )

        self.assertEqual(
            s.PROMPT_RUNS_ROOT,
            EXPECTED_PROJECT / "EVIDENCE" / "PROMPT_RUNS",
        )

        self.assertEqual(
            s.SOURCES_ROOT,
            EXPECTED_PROJECT / "EVIDENCE" / "SOURCES",
        )

        self.assertEqual(
            s.PROVENANCE_BINDINGS_ROOT,
            EXPECTED_PROJECT
            / "EVIDENCE"
            / "PROVENANCE_BINDINGS",
        )

    def test_lazy_classification(self):
        self.assertEqual(
            s.STORAGE_CLASS["DATA_RUNS"],
            "LAZY_CANONICAL",
        )

        self.assertEqual(
            s.STORAGE_CLASS["PROMPT_RUNS"],
            "LAZY_CANONICAL",
        )

        self.assertEqual(
            s.STORAGE_CLASS["SOURCES"],
            "LAZY_CANONICAL",
        )

        self.assertEqual(
            s.STORAGE_CLASS["PROVENANCE_BINDINGS"],
            "LAZY_CANONICAL",
        )

    def test_sourceguard_contract(self):
        expected = (
            EXPECTED_PROJECT
            / "EVIDENCE"
            / "SOURCEGUARD"
            / "SG-GOV-01"
            / "pilots"
            / "PILOT-01"
        )

        self.assertEqual(
            s.SOURCEGUARD_PILOT_01_ROOT,
            expected,
        )

    def test_pilot_subdirectories(self):
        expected_names = {
            "PILOT-01",
            "input",
            "gold",
            "predictions",
            "comparisons",
            "risk",
            "manifests",
        }

        actual_names = {
            p.name
            for p in s.PILOT_01_REQUIRED_DIRS
        }

        self.assertEqual(
            actual_names,
            expected_names,
        )

    def test_backup_is_not_claimed_as_active(self):
        self.assertEqual(
            s.STORAGE_CLASS["BACKUP"],
            "UNIMPLEMENTED_PLACEHOLDER",
        )

    def test_sourceguard_not_claimed_as_activated(self):
        self.assertEqual(
            s.STORAGE_CLASS["SOURCEGUARD"],
            "CONTRACTED_NOT_ACTIVATED",
        )


if __name__ == "__main__":
    unittest.main()

import tempfile
import unittest
from pathlib import Path

from tools.storage_materializer import (
    materialize_pilot01,
    pilot01_expected_dirs,
    verify_pilot01_tree,
)


class StorageMaterializerTest(unittest.TestCase):

    def make_project(self):
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name) / "ExamTrust_AI_2026"
        root.mkdir()
        return temp, root

    def test_exact_tree_materialization(self):
        temp, root = self.make_project()

        try:
            result = materialize_pilot01(root)

            self.assertTrue(
                result["accepted"]
            )

            expected = set(
                pilot01_expected_dirs(root)
            )

            discovered = {
                p.resolve()
                for p in (
                    root
                    / "EVIDENCE"
                    / "SOURCEGUARD"
                ).rglob("*")
                if p.is_dir()
            }

            discovered.add(
                (
                    root
                    / "EVIDENCE"
                    / "SOURCEGUARD"
                ).resolve()
            )

            self.assertEqual(
                discovered,
                expected,
            )

        finally:
            temp.cleanup()

    def test_materialization_is_idempotent(self):
        temp, root = self.make_project()

        try:
            first = materialize_pilot01(root)
            second = materialize_pilot01(root)

            self.assertTrue(
                first["accepted"]
            )

            self.assertTrue(
                second["accepted"]
            )

            self.assertEqual(
                first["expected_count"],
                second["expected_count"],
            )

            self.assertEqual(
                first["discovered_count"],
                second["discovered_count"],
            )

        finally:
            temp.cleanup()

    def test_lazy_evidence_roots_are_not_created(self):
        temp, root = self.make_project()

        try:
            materialize_pilot01(root)

            evidence = root / "EVIDENCE"

            prohibited = (
                evidence / "DATA_RUNS",
                evidence / "PROMPT_RUNS",
                evidence / "SOURCES",
                evidence / "PROVENANCE_BINDINGS",
                evidence / "RECOVERY",
            )

            for path in prohibited:
                self.assertFalse(
                    path.exists(),
                    str(path),
                )

        finally:
            temp.cleanup()

    def test_unexpected_directory_fails_acceptance(self):
        temp, root = self.make_project()

        try:
            materialize_pilot01(root)

            rogue = (
                root
                / "EVIDENCE"
                / "SOURCEGUARD"
                / "UNEXPECTED"
            )

            rogue.mkdir()

            result = verify_pilot01_tree(root)

            self.assertFalse(
                result["accepted"]
            )

            self.assertTrue(
                result["unexpected"]
            )

        finally:
            temp.cleanup()

    def test_missing_directory_fails_acceptance(self):
        temp, root = self.make_project()

        try:
            expected = pilot01_expected_dirs(root)

            # No materialization has occurred.
            result = verify_pilot01_tree(root)

            self.assertFalse(
                result["accepted"]
            )

            self.assertEqual(
                len(result["missing"]),
                len(expected),
            )

        finally:
            temp.cleanup()

    def test_missing_project_root_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = (
                Path(tmp)
                / "missing-project"
            )

            with self.assertRaises(
                FileNotFoundError
            ):
                materialize_pilot01(root)

    def test_file_cannot_be_project_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "not-a-directory"

            root.write_text(
                "not a project directory",
                encoding="utf-8",
            )

            with self.assertRaises(
                NotADirectoryError
            ):
                materialize_pilot01(root)

    def test_all_expected_paths_are_contained(self):
        temp, root = self.make_project()

        try:
            resolved_root = root.resolve()

            for path in pilot01_expected_dirs(root):
                path.resolve().relative_to(
                    resolved_root
                )

        finally:
            temp.cleanup()


if __name__ == "__main__":
    unittest.main()

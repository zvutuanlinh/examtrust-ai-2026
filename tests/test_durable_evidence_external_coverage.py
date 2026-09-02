import ast
import unittest
from pathlib import Path


class TestDurableEvidenceExternalCoverage(unittest.TestCase):

    def setUp(self):
        self.repo = Path(__file__).resolve().parents[1]
        self.tool = (
            self.repo
            / "tools"
            / "durable_evidence.py"
        )

        self.source = self.tool.read_text(
            encoding="utf-8"
        )

        self.tree = ast.parse(
            self.source
        )

    def function_segment(self, name):
        for node in self.tree.body:
            if (
                isinstance(node, ast.FunctionDef)
                and node.name == name
            ):
                segment = ast.get_source_segment(
                    self.source,
                    node
                )

                self.assertIsNotNone(segment)
                return segment

        self.fail(
            f"Function not found: {name}"
        )

    def test_notebook_lineage_is_in_repo_evidence_contract(self):
        segment = self.function_segment(
            "evidence_records"
        )

        self.assertIn(
            "notebook_lineage",
            segment
        )

        self.assertIn(
            "repo_evidence",
            segment
        )

    def test_sourceguard_governance_is_external_evidence(self):
        segment = self.function_segment(
            "evidence_records"
        )

        self.assertIn(
            "SOURCEGUARD_GOVERNANCE_ROOT",
            segment
        )

        self.assertIn(
            "external_evidence",
            segment
        )

        self.assertIn(
            "drive_external_sourceguard_governance",
            segment
        )

    def test_manifest_preserves_source_provenance(self):
        segment = self.function_segment(
            "create_checkpoint"
        )

        for token in [
            "source_class",
            "source_root",
            "source_relative_path",
            "sha256_file(dst)",
        ]:
            self.assertIn(
                token,
                segment
            )

    def test_new_checkpoint_path_uses_evidence_records(self):
        segment = self.function_segment(
            "create_checkpoint"
        )

        self.assertIn(
            "for evidence_record in evidence_records()",
            segment
        )


if __name__ == "__main__":
    unittest.main()

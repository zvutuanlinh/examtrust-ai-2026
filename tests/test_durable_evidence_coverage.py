import ast
import unittest
from pathlib import Path


class TestDurableEvidenceCoverage(unittest.TestCase):

    def test_evidence_files_includes_full_pass(self):
        repo = Path(__file__).resolve().parents[1]
        tool = repo / 'tools' / 'durable_evidence.py'

        source = tool.read_text(encoding='utf-8')
        tree = ast.parse(source)

        fn = None

        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                if node.name == 'evidence_files':
                    fn = node
                    break

        self.assertIsNotNone(fn)

        segment = ast.get_source_segment(source, fn)

        self.assertIsNotNone(segment)
        self.assertIn(
            'full_pass',
            segment
        )

        expected = [
            'development_notes',
            'full_pass',
            'remote_events',
            'sessions',
        ]

        for name in expected:
            self.assertIn(name, segment)


if __name__ == '__main__':
    unittest.main()

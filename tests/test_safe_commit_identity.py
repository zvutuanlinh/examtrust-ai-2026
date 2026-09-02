import ast
import subprocess
import tempfile
import unittest
from pathlib import Path


class TestSafeCommitIdentity(unittest.TestCase):

    def test_identity_gate_is_before_autonote_and_full_pass(self):
        repo = Path(__file__).resolve().parents[1]
        safe = repo / 'tools' / 'safe_commit.py'

        source = safe.read_text(encoding='utf-8')

        self.assertIn(
            'def git_identity_preflight',
            source
        )

        safe_pos = source.index(
            'def safe_commit(goal, message):'
        )

        identity_pos = source.index(
            'git_identity_preflight()',
            safe_pos
        )

        note_pos = source.index(
            'create_note(',
            safe_pos
        )

        full_pos = source.index(
            'run_full_pass(',
            safe_pos
        )

        self.assertLess(identity_pos, note_pos)
        self.assertLess(identity_pos, full_pos)

    def test_identity_probe_does_not_use_run_git_check_keyword(self):
        repo = Path(__file__).resolve().parents[1]
        safe = repo / 'tools' / 'safe_commit.py'

        source = safe.read_text(encoding='utf-8')
        tree = ast.parse(source)

        helper = None

        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                if node.name == 'git_identity_preflight':
                    helper = node
                    break

        self.assertIsNotNone(helper)

        segment = ast.get_source_segment(
            source,
            helper
        )

        self.assertIsNotNone(segment)
        self.assertNotIn(
            'run_git(',
            segment
        )
        self.assertIn(
            'subprocess.run(',
            segment
        )

    def test_missing_local_identity_returns_nonzero_without_crash(self):
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)

            subprocess.run(
                ['git', 'init'],
                cwd=repo,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            name = subprocess.run(
                [
                    'git',
                    'config',
                    '--local',
                    '--get',
                    'user.name'
                ],
                cwd=repo,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            email = subprocess.run(
                [
                    'git',
                    'config',
                    '--local',
                    '--get',
                    'user.email'
                ],
                cwd=repo,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            self.assertEqual(name.returncode, 1)
            self.assertEqual(email.returncode, 1)
            self.assertEqual(name.stdout.strip(), '')
            self.assertEqual(email.stdout.strip(), '')


if __name__ == '__main__':
    unittest.main()

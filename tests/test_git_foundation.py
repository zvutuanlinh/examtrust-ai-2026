
import unittest
import tempfile
from pathlib import Path

from tools.full_pass import sha256_file


class TestGitFoundation(unittest.TestCase):

    def test_sha256_is_stable(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "sample.txt"
            p.write_text(
                "ExamTrust",
                encoding="utf-8"
            )

            h1 = sha256_file(p)
            h2 = sha256_file(p)

            self.assertEqual(h1, h2)
            self.assertEqual(len(h1), 64)

    def test_sha256_detects_change(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "sample.txt"

            p.write_text(
                "A",
                encoding="utf-8"
            )
            h1 = sha256_file(p)

            p.write_text(
                "B",
                encoding="utf-8"
            )
            h2 = sha256_file(p)

            self.assertNotEqual(h1, h2)


    def test_autotrace_runtime_is_ignored(self):
        gitignore = Path(".gitignore").read_text(
            encoding="utf-8"
        )

        self.assertIn(
            ".autotrace/",
            gitignore
        )


if __name__ == "__main__":
    unittest.main()

import tempfile
import unittest
from pathlib import Path

from tools.hash_utils import (
    sha256_file,
    sha256_text
)

from tools.data_logger import create_data_run
from tools.prompt_logger import create_prompt_run


class TestLineageFoundation(unittest.TestCase):

    def test_data_logger_does_not_modify_source(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / 'source.txt'

            source.write_text(
                'ExamTrust temporary test fixture',
                encoding='utf-8'
            )

            before = sha256_file(source)

            run_dir, record = create_data_run(
                inputs=[source],
                outputs=[],
                config={'purpose': 'unit_test'},
                extractor_version='TEST_ONLY',
                evidence_root=root / 'evidence',
                run_id='ETDATA-TEST-001'
            )

            after = sha256_file(source)

            self.assertEqual(before, after)

            self.assertEqual(
                record['input_integrity']['files'][0]['sha256'],
                before
            )

            self.assertTrue(
                (run_dir / 'manifest.json').exists()
            )

            self.assertTrue(
                (run_dir / 'SHA256SUMS.txt').exists()
            )

    def test_data_run_id_is_append_only(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / 'source.txt'
            source.write_text('fixture', encoding='utf-8')
            evidence = root / 'evidence'

            create_data_run(
                inputs=[source],
                evidence_root=evidence,
                run_id='ETDATA-TEST-002'
            )

            with self.assertRaises(RuntimeError):
                create_data_run(
                    inputs=[source],
                    evidence_root=evidence,
                    run_id='ETDATA-TEST-002'
                )

    def test_prompt_hash_lineage(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)

            prompt = (
                'Generate one controlled question from CH_001.'
            )

            response = (
                'Temporary response fixture.'
            )

            run_dir, record = create_prompt_run(
                model='TEST_MODEL',
                template_version='TEST_V1',
                contract_id='QC-TEST-001',
                source_refs=['CH_001'],
                prompt_text=prompt,
                response_text=response,
                output_ids=['Q-TEST-001'],
                settings={'temperature': 0},
                snapshot=True,
                evidence_root=root / 'evidence',
                run_id='ETPROMPT-TEST-001'
            )

            self.assertEqual(
                record['prompt_sha256'],
                sha256_text(prompt)
            )

            self.assertEqual(
                record['response_sha256'],
                sha256_text(response)
            )

            self.assertEqual(
                record['source_refs'],
                ['CH_001']
            )

            self.assertTrue(
                (run_dir / 'prompt.txt').exists()
            )

            self.assertTrue(
                (run_dir / 'response.txt').exists()
            )

    def test_prompt_run_id_is_append_only(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)

            create_prompt_run(
                model='TEST_MODEL',
                template_version='V1',
                contract_id='QC-001',
                source_refs=['CH_001'],
                prompt_text='fixture',
                evidence_root=root / 'evidence',
                run_id='ETPROMPT-TEST-002'
            )

            with self.assertRaises(RuntimeError):
                create_prompt_run(
                    model='TEST_MODEL',
                    template_version='V1',
                    contract_id='QC-001',
                    source_refs=['CH_001'],
                    prompt_text='fixture',
                    evidence_root=root / 'evidence',
                    run_id='ETPROMPT-TEST-002'
                )

    def test_sensitive_snapshot_is_blocked(self):
        with tempfile.TemporaryDirectory() as td:
            suspicious = (
                'Authorization'
                + ': Bearer '
                + ('X' * 24)
            )

            with self.assertRaises(RuntimeError):
                create_prompt_run(
                    model='TEST_MODEL',
                    template_version='V1',
                    contract_id='QC-002',
                    source_refs=['CH_002'],
                    prompt_text=suspicious,
                    snapshot=True,
                    evidence_root=Path(td) / 'evidence',
                    run_id='ETPROMPT-TEST-003'
                )


if __name__ == '__main__':
    unittest.main()

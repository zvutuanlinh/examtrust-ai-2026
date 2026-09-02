import tempfile
import unittest
from pathlib import Path

from tools.hash_utils import sha256_file
from tools.source_registry import (
    register_source,
    source_id_from_sha256,
    verify_source
)
from tools.data_logger import create_data_run
from tools.provenance_binding import create_binding


class TestSourceProvenance(unittest.TestCase):

    def test_source_registration_is_hash_bound(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / 'source.pdf'

            source.write_bytes(
                b'ExamTrust temporary source fixture'
            )

            before = sha256_file(source)

            source_dir, record, created = register_source(
                source_path=source,
                source_type='PDF',
                evidence_root=root / 'sources'
            )

            after = sha256_file(source)

            self.assertTrue(created)
            self.assertEqual(before, after)
            self.assertEqual(record['sha256'], before)
            self.assertEqual(
                record['source_id'],
                source_id_from_sha256(before)
            )
            self.assertFalse(record['raw_content_copied'])
            self.assertTrue(
                (source_dir / 'manifest.json').exists()
            )

    def test_same_source_registration_is_idempotent(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / 'source.txt'

            source.write_text(
                'same source',
                encoding='utf-8'
            )

            first_dir, first, first_created = register_source(
                source_path=source,
                evidence_root=root / 'sources'
            )

            source_json = first_dir / 'source.json'
            bytes_before = source_json.read_bytes()

            second_dir, second, second_created = register_source(
                source_path=source,
                evidence_root=root / 'sources'
            )

            bytes_after = source_json.read_bytes()

            self.assertTrue(first_created)
            self.assertFalse(second_created)
            self.assertEqual(first_dir, second_dir)
            self.assertEqual(first['source_id'], second['source_id'])
            self.assertEqual(bytes_before, bytes_after)

    def test_changed_source_gets_different_identity(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / 'source.txt'

            source.write_text('A', encoding='utf-8')

            _, first, _ = register_source(
                source_path=source,
                evidence_root=root / 'sources'
            )

            source.write_text('B', encoding='utf-8')

            _, second, _ = register_source(
                source_path=source,
                evidence_root=root / 'sources'
            )

            self.assertNotEqual(
                first['source_id'],
                second['source_id']
            )

    def test_binding_requires_real_registered_source_and_data_run(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / 'source.txt'

            source.write_text(
                'temporary source',
                encoding='utf-8'
            )

            _, source_record, _ = register_source(
                source_path=source,
                evidence_root=root / 'sources'
            )

            create_data_run(
                inputs=[source],
                outputs=[],
                config={'test': True},
                extractor_version='TEST_ONLY',
                evidence_root=root / 'data_runs',
                run_id='ETDATA-TEST-BIND-001'
            )

            binding_dir, binding = create_binding(
                source_id=source_record['source_id'],
                data_run_id='ETDATA-TEST-BIND-001',
                asset_id='CH_001',
                anchor={
                    'page': 1,
                    'line_start': 1,
                    'line_end': 3
                },
                contract_id='QC-TEST-001',
                prompt_run_id='ETPROMPT-TEST-001',
                question_id='Q-TEST-001',
                source_root=root / 'sources',
                data_root=root / 'data_runs',
                binding_root=root / 'bindings',
                binding_id='ETBIND-TEST-001'
            )

            chain = binding['chain']

            self.assertEqual(
                chain['source_id'],
                source_record['source_id']
            )
            self.assertEqual(
                chain['source_sha256'],
                source_record['sha256']
            )
            self.assertEqual(
                chain['data_run_id'],
                'ETDATA-TEST-BIND-001'
            )
            self.assertEqual(chain['asset_id'], 'CH_001')
            self.assertEqual(chain['contract_id'], 'QC-TEST-001')
            self.assertEqual(
                chain['prompt_run_id'],
                'ETPROMPT-TEST-001'
            )
            self.assertEqual(chain['question_id'], 'Q-TEST-001')
            self.assertTrue(
                (binding_dir / 'manifest.json').exists()
            )

    def test_binding_rejects_missing_source(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / 'source.txt'
            source.write_text('fixture', encoding='utf-8')

            create_data_run(
                inputs=[source],
                evidence_root=root / 'data_runs',
                run_id='ETDATA-TEST-BIND-002'
            )

            with self.assertRaises(FileNotFoundError):
                create_binding(
                    source_id='SRC-0000000000000000',
                    data_run_id='ETDATA-TEST-BIND-002',
                    asset_id='CH_001',
                    anchor={'page': 1},
                    source_root=root / 'sources',
                    data_root=root / 'data_runs',
                    binding_root=root / 'bindings',
                    binding_id='ETBIND-TEST-002'
                )

    def test_binding_rejects_invalid_anchor(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / 'source.txt'
            source.write_text('fixture', encoding='utf-8')

            _, record, _ = register_source(
                source_path=source,
                evidence_root=root / 'sources'
            )

            create_data_run(
                inputs=[source],
                evidence_root=root / 'data_runs',
                run_id='ETDATA-TEST-BIND-003'
            )

            with self.assertRaises(ValueError):
                create_binding(
                    source_id=record['source_id'],
                    data_run_id='ETDATA-TEST-BIND-003',
                    asset_id='CH_001',
                    anchor={
                        'page': 0
                    },
                    source_root=root / 'sources',
                    data_root=root / 'data_runs',
                    binding_root=root / 'bindings',
                    binding_id='ETBIND-TEST-003'
                )


if __name__ == '__main__':
    unittest.main()

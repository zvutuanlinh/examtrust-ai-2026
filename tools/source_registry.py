from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import argparse
import json
import mimetypes
import sys

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.hash_utils import (
    sha256_file,
    canonical_json_sha256
)


DEFAULT_ROOT = Path(
    '/content/drive/MyDrive/'
    'ExamTrust_AI_2026/'
    'EVIDENCE/SOURCES'
)


def now():
    return datetime.now(
        ZoneInfo('Asia/Ho_Chi_Minh')
    )


def source_id_from_sha256(file_sha256):
    if len(file_sha256) != 64:
        raise ValueError(
            'Expected a full SHA256 digest.'
        )

    return (
        'SRC-'
        + file_sha256[:16].upper()
    )


def source_record_path(
    source_id,
    evidence_root=None
):
    root = Path(
        evidence_root
        if evidence_root is not None
        else DEFAULT_ROOT
    )

    return (
        root
        / source_id
        / 'source.json'
    )


def load_source(
    source_id,
    evidence_root=None
):
    path = source_record_path(
        source_id,
        evidence_root=evidence_root
    )

    if not path.exists():
        raise FileNotFoundError(
            f'SOURCE NOT REGISTERED: {source_id}'
        )

    return json.loads(
        path.read_text(
            encoding='utf-8'
        )
    )


def verify_source(
    source_id,
    evidence_root=None
):
    record = load_source(
        source_id,
        evidence_root=evidence_root
    )

    if record.get('source_id') != source_id:
        raise RuntimeError(
            'SOURCE RECORD ID MISMATCH'
        )

    digest = record.get('sha256')

    if not isinstance(digest, str) or len(digest) != 64:
        raise RuntimeError(
            'INVALID SOURCE SHA256'
        )

    expected_id = source_id_from_sha256(
        digest
    )

    if expected_id != source_id:
        raise RuntimeError(
            'SOURCE ID DOES NOT MATCH SHA256'
        )

    return record


def register_source(
    source_path,
    source_type=None,
    title=None,
    metadata=None,
    evidence_root=None
):
    source_path = Path(source_path)

    if not source_path.exists():
        raise FileNotFoundError(
            source_path
        )

    if not source_path.is_file():
        raise ValueError(
            f'Not a file: {source_path}'
        )

    before_hash = sha256_file(
        source_path
    )

    source_id = source_id_from_sha256(
        before_hash
    )

    root = Path(
        evidence_root
        if evidence_root is not None
        else DEFAULT_ROOT
    )

    root.mkdir(
        parents=True,
        exist_ok=True
    )

    source_dir = root / source_id
    source_json = source_dir / 'source.json'

    if source_dir.exists():
        existing = verify_source(
            source_id,
            evidence_root=root
        )

        if existing['sha256'] != before_hash:
            raise RuntimeError(
                'SOURCE ID COLLISION'
            )

        print('SOURCE_ALREADY_REGISTERED')
        print('Source ID:', source_id)

        return source_dir, existing, False

    detected_mime, _ = mimetypes.guess_type(
        source_path.name
    )

    normalized_type = (
        source_type
        or source_path.suffix.lstrip('.').upper()
        or 'UNKNOWN'
    )

    metadata = metadata or {}

    record = {
        'schema': 'examtrust.source.v1',
        'source_id': source_id,
        'registered_at': now().isoformat(
            timespec='seconds'
        ),
        'filename': source_path.name,
        'source_type': normalized_type,
        'mime_type': detected_mime,
        'title': title,
        'size_bytes': source_path.stat().st_size,
        'sha256': before_hash,
        'original_path': str(source_path),
        'snapshot_stored': False,
        'raw_content_copied': False,
        'metadata': metadata,
        'metadata_sha256': canonical_json_sha256(metadata),
        'append_only': True,
        'credential_persisted': False
    }

    source_dir.mkdir(
        parents=True,
        exist_ok=False
    )

    source_json.write_text(
        json.dumps(
            record,
            ensure_ascii=False,
            indent=2
        ),
        encoding='utf-8'
    )

    after_hash = sha256_file(
        source_path
    )

    if before_hash != after_hash:
        raise RuntimeError(
            'SOURCE MUTATED DURING REGISTRATION'
        )

    manifest = {
        'schema': 'examtrust.source_manifest.v1',
        'source_id': source_id,
        'source_record_sha256': sha256_file(source_json),
        'original_file_sha256': before_hash,
        'raw_content_copied': False
    }

    manifest_path = source_dir / 'manifest.json'

    manifest_path.write_text(
        json.dumps(
            manifest,
            ensure_ascii=False,
            indent=2
        ),
        encoding='utf-8'
    )

    sums = [
        f'{sha256_file(source_json)}  source.json',
        f'{sha256_file(manifest_path)}  manifest.json'
    ]

    (source_dir / 'SHA256SUMS.txt').write_text(
        '\n'.join(sums) + '\n',
        encoding='utf-8'
    )

    print('SOURCE_REGISTERED')
    print('Source ID:', source_id)
    print('SHA256:', before_hash)
    print('Raw content copied: NO')
    print('Source mutated: NO')

    return source_dir, record, True


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='ExamTrust source registry'
    )

    parser.add_argument(
        '--source',
        required=True
    )

    parser.add_argument(
        '--source-type'
    )

    parser.add_argument(
        '--title'
    )

    parser.add_argument(
        '--metadata-json',
        default='{}'
    )

    parser.add_argument(
        '--root',
        default=str(DEFAULT_ROOT)
    )

    args = parser.parse_args()

    register_source(
        source_path=args.source,
        source_type=args.source_type,
        title=args.title,
        metadata=json.loads(args.metadata_json),
        evidence_root=args.root
    )

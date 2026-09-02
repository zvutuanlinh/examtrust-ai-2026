from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import argparse
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.hash_utils import sha256_file
from tools.source_registry import verify_source


DEFAULT_BINDING_ROOT = Path(
    '/content/drive/MyDrive/'
    'ExamTrust_AI_2026/'
    'EVIDENCE/PROVENANCE_BINDINGS'
)

DEFAULT_SOURCE_ROOT = Path(
    '/content/drive/MyDrive/'
    'ExamTrust_AI_2026/'
    'EVIDENCE/SOURCES'
)

DEFAULT_DATA_ROOT = Path(
    '/content/drive/MyDrive/'
    'ExamTrust_AI_2026/'
    'EVIDENCE/DATA_RUNS'
)

SOURCE_RX = re.compile(
    r'^SRC-[0-9A-F]{16}$'
)

DATA_RX = re.compile(
    r'^ETDATA-[A-Za-z0-9_-]+$'
)

ASSET_RX = re.compile(
    r'^(CH|FM|GR|IMG)_[0-9]{3,}$'
)

CONTRACT_RX = re.compile(
    r'^QC-[A-Za-z0-9_-]+$'
)

PROMPT_RX = re.compile(
    r'^ETPROMPT-[A-Za-z0-9_-]+$'
)

QUESTION_RX = re.compile(
    r'^Q-[A-Za-z0-9_-]+$'
)


def now():
    return datetime.now(
        ZoneInfo('Asia/Ho_Chi_Minh')
    )


def new_binding_id():
    return now().strftime(
        'ETBIND-%Y%m%d-%H%M%S-%f'
    )


def validate_anchor(anchor):
    if not isinstance(anchor, dict):
        raise ValueError(
            'anchor must be an object/dict'
        )

    if 'page' not in anchor:
        raise ValueError(
            'anchor.page is required'
        )

    page = anchor['page']

    if not isinstance(page, int) or page < 1:
        raise ValueError(
            'anchor.page must be integer >= 1'
        )

    if 'line_start' in anchor or 'line_end' in anchor:
        start = anchor.get('line_start')
        end = anchor.get('line_end')

        if not isinstance(start, int):
            raise ValueError(
                'line_start must be integer'
            )

        if not isinstance(end, int):
            raise ValueError(
                'line_end must be integer'
            )

        if start < 1 or end < start:
            raise ValueError(
                'invalid line range'
            )

    if 'bbox' in anchor:
        bbox = anchor['bbox']

        if not isinstance(bbox, list) or len(bbox) != 4:
            raise ValueError(
                'bbox must contain [x0,y0,x1,y1]'
            )

        if not all(
            isinstance(v, (int, float))
            for v in bbox
        ):
            raise ValueError(
                'bbox values must be numeric'
            )

    return anchor


def verify_data_run(
    data_run_id,
    data_root=None
):
    root = Path(
        data_root
        if data_root is not None
        else DEFAULT_DATA_ROOT
    )

    run_json = (
        root
        / data_run_id
        / 'run.json'
    )

    manifest = (
        root
        / data_run_id
        / 'manifest.json'
    )

    if not run_json.exists():
        raise FileNotFoundError(
            f'DATA RUN NOT FOUND: {data_run_id}'
        )

    if not manifest.exists():
        raise RuntimeError(
            f'DATA RUN MANIFEST MISSING: {data_run_id}'
        )

    record = json.loads(
        run_json.read_text(
            encoding='utf-8'
        )
    )

    if record.get('run_id') != data_run_id:
        raise RuntimeError(
            'DATA RUN ID MISMATCH'
        )

    return record


def validate_ids(
    source_id,
    data_run_id,
    asset_id,
    contract_id=None,
    prompt_run_id=None,
    question_id=None
):
    checks = [
        (SOURCE_RX, source_id, 'source_id'),
        (DATA_RX, data_run_id, 'data_run_id'),
        (ASSET_RX, asset_id, 'asset_id')
    ]

    if contract_id is not None:
        checks.append(
            (CONTRACT_RX, contract_id, 'contract_id')
        )

    if prompt_run_id is not None:
        checks.append(
            (PROMPT_RX, prompt_run_id, 'prompt_run_id')
        )

    if question_id is not None:
        checks.append(
            (QUESTION_RX, question_id, 'question_id')
        )

    for rx, value, label in checks:
        if not rx.match(value):
            raise ValueError(
                f'Invalid {label}: {value}'
            )


def create_binding(
    source_id,
    data_run_id,
    asset_id,
    anchor,
    contract_id=None,
    prompt_run_id=None,
    question_id=None,
    source_root=None,
    data_root=None,
    binding_root=None,
    binding_id=None
):
    validate_ids(
        source_id=source_id,
        data_run_id=data_run_id,
        asset_id=asset_id,
        contract_id=contract_id,
        prompt_run_id=prompt_run_id,
        question_id=question_id
    )

    validate_anchor(anchor)

    source_record = verify_source(
        source_id,
        evidence_root=(
            source_root
            if source_root is not None
            else DEFAULT_SOURCE_ROOT
        )
    )

    data_record = verify_data_run(
        data_run_id,
        data_root=(
            data_root
            if data_root is not None
            else DEFAULT_DATA_ROOT
        )
    )

    binding_root = Path(
        binding_root
        if binding_root is not None
        else DEFAULT_BINDING_ROOT
    )

    binding_root.mkdir(
        parents=True,
        exist_ok=True
    )

    binding_id = (
        binding_id
        or new_binding_id()
    )

    binding_dir = (
        binding_root
        / binding_id
    )

    if binding_dir.exists():
        raise RuntimeError(
            f'BINDING EXISTS: {binding_id}'
        )

    chain = {
        'source_id': source_id,
        'source_sha256': source_record['sha256'],
        'data_run_id': data_run_id,
        'asset_id': asset_id,
        'anchor': anchor,
        'contract_id': contract_id,
        'prompt_run_id': prompt_run_id,
        'question_id': question_id
    }

    record = {
        'schema': 'examtrust.provenance_binding.v1',
        'binding_id': binding_id,
        'created_at': now().isoformat(
            timespec='seconds'
        ),
        'chain': chain,
        'source_verified': True,
        'data_run_verified': True,
        'source_filename': source_record['filename'],
        'data_run_status': data_record.get('status'),
        'append_only': True,
        'credential_persisted': False
    }

    binding_dir.mkdir(
        parents=True,
        exist_ok=False
    )

    binding_json = (
        binding_dir
        / 'binding.json'
    )

    binding_json.write_text(
        json.dumps(
            record,
            ensure_ascii=False,
            indent=2
        ),
        encoding='utf-8'
    )

    manifest = {
        'schema': 'examtrust.provenance_manifest.v1',
        'binding_id': binding_id,
        'binding_record_sha256': sha256_file(binding_json),
        'source_id': source_id,
        'source_sha256': source_record['sha256'],
        'data_run_id': data_run_id,
        'asset_id': asset_id,
        'contract_id': contract_id,
        'prompt_run_id': prompt_run_id,
        'question_id': question_id
    }

    manifest_path = (
        binding_dir
        / 'manifest.json'
    )

    manifest_path.write_text(
        json.dumps(
            manifest,
            ensure_ascii=False,
            indent=2
        ),
        encoding='utf-8'
    )

    sums = [
        f'{sha256_file(binding_json)}  binding.json',
        f'{sha256_file(manifest_path)}  manifest.json'
    ]

    (binding_dir / 'SHA256SUMS.txt').write_text(
        '\n'.join(sums) + '\n',
        encoding='utf-8'
    )

    print('PROVENANCE_BINDING_CREATED')
    print('Binding ID:', binding_id)
    print('Source ID:', source_id)
    print('Data Run:', data_run_id)
    print('Asset ID:', asset_id)
    print('Contract ID:', contract_id)
    print('Prompt Run:', prompt_run_id)
    print('Question ID:', question_id)

    return binding_dir, record


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='ExamTrust provenance binding'
    )

    parser.add_argument('--source-id', required=True)
    parser.add_argument('--data-run-id', required=True)
    parser.add_argument('--asset-id', required=True)
    parser.add_argument('--anchor-json', required=True)
    parser.add_argument('--contract-id')
    parser.add_argument('--prompt-run-id')
    parser.add_argument('--question-id')
    parser.add_argument('--source-root', default=str(DEFAULT_SOURCE_ROOT))
    parser.add_argument('--data-root', default=str(DEFAULT_DATA_ROOT))
    parser.add_argument('--binding-root', default=str(DEFAULT_BINDING_ROOT))

    args = parser.parse_args()

    create_binding(
        source_id=args.source_id,
        data_run_id=args.data_run_id,
        asset_id=args.asset_id,
        anchor=json.loads(args.anchor_json),
        contract_id=args.contract_id,
        prompt_run_id=args.prompt_run_id,
        question_id=args.question_id,
        source_root=args.source_root,
        data_root=args.data_root,
        binding_root=args.binding_root
    )

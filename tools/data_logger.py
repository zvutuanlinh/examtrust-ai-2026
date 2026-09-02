from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import argparse
import json
import sys

# ARCH-STORAGE-01: canonical storage contract
try:
    from tools.storage_layout import (
        DATA_RUNS_ROOT
    )
except ModuleNotFoundError:
    from storage_layout import (
        DATA_RUNS_ROOT
    )


ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.hash_utils import (
    sha256_file,
    canonical_json_sha256,
    file_record
)


DEFAULT_ROOT = DATA_RUNS_ROOT


def now():
    return datetime.now(
        ZoneInfo('Asia/Ho_Chi_Minh')
    )


def new_run_id():
    return now().strftime(
        'ETDATA-%Y%m%d-%H%M%S-%f'
    )


def write_sha256sums(run_dir):
    lines = []

    for p in sorted(run_dir.rglob('*')):
        if not p.is_file():
            continue

        if p.name == 'SHA256SUMS.txt':
            continue

        rel = p.relative_to(run_dir)

        lines.append(
            f'{sha256_file(p)}  '
            + str(rel).replace('\\', '/')
        )

    output = run_dir / 'SHA256SUMS.txt'

    output.write_text(
        '\n'.join(lines) + '\n',
        encoding='utf-8'
    )

    return output


def create_data_run(
    inputs,
    outputs=None,
    config=None,
    extractor_version='UNASSIGNED',
    status='CREATED',
    evidence_root=None,
    run_id=None
):
    root = Path(
        evidence_root
        if evidence_root is not None
        else DEFAULT_ROOT
    )

    root.mkdir(parents=True, exist_ok=True)

    run_id = run_id or new_run_id()
    run_dir = root / run_id

    if run_dir.exists():
        raise RuntimeError(
            f'DATA RUN EXISTS: {run_id}'
        )

    input_records = [
        file_record(p)
        for p in inputs
    ]

    output_records = [
        file_record(p)
        for p in (outputs or [])
    ]

    config = config or {}

    record = {
        'schema': 'examtrust.data_run.v1',
        'run_id': run_id,
        'timestamp': now().isoformat(
            timespec='seconds'
        ),
        'status': status,
        'extractor_version': extractor_version,
        'input_integrity': {
            'policy': 'HASH_ONLY_NO_MUTATION_BY_LOGGER',
            'files': input_records
        },
        'outputs': output_records,
        'config': config,
        'config_sha256': canonical_json_sha256(config),
        'append_only': True,
        'credential_persisted': False
    }

    run_dir.mkdir(
        parents=True,
        exist_ok=False
    )

    run_json = run_dir / 'run.json'

    run_json.write_text(
        json.dumps(
            record,
            ensure_ascii=False,
            indent=2
        ),
        encoding='utf-8'
    )

    manifest = {
        'schema': 'examtrust.data_manifest.v1',
        'run_id': run_id,
        'run_record_sha256': sha256_file(run_json),
        'input_count': len(input_records),
        'output_count': len(output_records),
        'input_files': input_records,
        'output_files': output_records
    }

    manifest_path = run_dir / 'manifest.json'

    manifest_path.write_text(
        json.dumps(
            manifest,
            ensure_ascii=False,
            indent=2
        ),
        encoding='utf-8'
    )

    sums_path = write_sha256sums(run_dir)

    print('DATA_RUN_CREATED')
    print('Run ID:', run_id)
    print('Path:', run_dir)
    print('Input count:', len(input_records))
    print('Output count:', len(output_records))
    print(
        'Manifest SHA256:',
        sha256_file(manifest_path)
    )
    print(
        'SHA256SUMS SHA256:',
        sha256_file(sums_path)
    )

    return run_dir, record


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='ExamTrust data provenance logger'
    )

    parser.add_argument(
        '--input',
        action='append',
        required=True
    )

    parser.add_argument(
        '--output',
        action='append',
        default=[]
    )

    parser.add_argument(
        '--extractor-version',
        default='UNASSIGNED'
    )

    parser.add_argument(
        '--status',
        default='CREATED'
    )

    parser.add_argument(
        '--config-json',
        default='{}'
    )

    parser.add_argument(
        '--root',
        default=str(DEFAULT_ROOT)
    )

    args = parser.parse_args()

    create_data_run(
        inputs=args.input,
        outputs=args.output,
        config=json.loads(args.config_json),
        extractor_version=args.extractor_version,
        status=args.status,
        evidence_root=args.root
    )

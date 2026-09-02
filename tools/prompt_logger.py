from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import argparse
import json
import re
import sys

# ARCH-STORAGE-01: canonical storage contract
try:
    from tools.storage_layout import (
        PROMPT_RUNS_ROOT
    )
except ModuleNotFoundError:
    from storage_layout import (
        PROMPT_RUNS_ROOT
    )


ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.hash_utils import (
    sha256_file,
    sha256_text,
    canonical_json_sha256
)


DEFAULT_ROOT = PROMPT_RUNS_ROOT


SENSITIVE_PATTERNS = [
    re.compile(
        r'(?i)authorization\s*:\s*bearer\s+\S+'
    ),
    re.compile(
        r'(?i)(api[_-]?key|password|secret)'
        r'\s*[:=]\s*[^\s]{8,}'
    ),
    re.compile(
        r'\bsk-[A-Za-z0-9_-]{12,}\b'
    )
]


def now():
    return datetime.now(
        ZoneInfo('Asia/Ho_Chi_Minh')
    )


def new_run_id():
    return now().strftime(
        'ETPROMPT-%Y%m%d-%H%M%S-%f'
    )


def contains_sensitive_material(text):
    return any(
        rx.search(text or '')
        for rx in SENSITIVE_PATTERNS
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


def create_prompt_run(
    model,
    template_version,
    contract_id,
    source_refs,
    prompt_text,
    response_text=None,
    output_ids=None,
    settings=None,
    status='CREATED',
    snapshot=False,
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
            f'PROMPT RUN EXISTS: {run_id}'
        )

    settings = settings or {}

    combined = (
        (prompt_text or '')
        + '\n'
        + (response_text or '')
    )

    if snapshot and contains_sensitive_material(combined):
        raise RuntimeError(
            'PROMPT SNAPSHOT BLOCKED: '
            'sensitive-looking material detected.'
        )

    record = {
        'schema': 'examtrust.prompt_run.v1',
        'run_id': run_id,
        'timestamp': now().isoformat(
            timespec='seconds'
        ),
        'status': status,
        'model': model,
        'template_version': template_version,
        'contract_id': contract_id,
        'source_refs': list(source_refs),
        'prompt_sha256': sha256_text(prompt_text),
        'response_sha256': (
            sha256_text(response_text)
            if response_text is not None
            else None
        ),
        'output_ids': list(output_ids or []),
        'settings': settings,
        'settings_sha256': canonical_json_sha256(settings),
        'snapshot_stored': bool(snapshot),
        'append_only': True,
        'credential_persisted': False
    }

    run_dir.mkdir(
        parents=True,
        exist_ok=False
    )

    if snapshot:
        (run_dir / 'prompt.txt').write_text(
            prompt_text,
            encoding='utf-8'
        )

        if response_text is not None:
            (run_dir / 'response.txt').write_text(
                response_text,
                encoding='utf-8'
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
        'schema': 'examtrust.prompt_manifest.v1',
        'run_id': run_id,
        'run_record_sha256': sha256_file(run_json),
        'contract_id': contract_id,
        'source_refs': list(source_refs),
        'prompt_sha256': record['prompt_sha256'],
        'response_sha256': record['response_sha256']
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

    print('PROMPT_RUN_CREATED')
    print('Run ID:', run_id)
    print('Path:', run_dir)
    print('Contract:', contract_id)
    print('Prompt SHA256:', record['prompt_sha256'])
    print('Response SHA256:', record['response_sha256'])
    print('Snapshot stored:', record['snapshot_stored'])
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
        description='ExamTrust prompt provenance logger'
    )

    parser.add_argument('--model', required=True)
    parser.add_argument('--template-version', required=True)
    parser.add_argument('--contract-id', required=True)

    parser.add_argument(
        '--source-ref',
        action='append',
        default=[]
    )

    parser.add_argument('--prompt-file', required=True)
    parser.add_argument('--response-file')

    parser.add_argument(
        '--output-id',
        action='append',
        default=[]
    )

    parser.add_argument('--settings-json', default='{}')
    parser.add_argument('--status', default='CREATED')
    parser.add_argument('--snapshot', action='store_true')
    parser.add_argument('--root', default=str(DEFAULT_ROOT))

    args = parser.parse_args()

    prompt_text = Path(args.prompt_file).read_text(
        encoding='utf-8'
    )

    response_text = None

    if args.response_file:
        response_text = Path(args.response_file).read_text(
            encoding='utf-8'
        )

    create_prompt_run(
        model=args.model,
        template_version=args.template_version,
        contract_id=args.contract_id,
        source_refs=args.source_ref,
        prompt_text=prompt_text,
        response_text=response_text,
        output_ids=args.output_id,
        settings=json.loads(args.settings_json),
        status=args.status,
        snapshot=args.snapshot,
        evidence_root=args.root
    )

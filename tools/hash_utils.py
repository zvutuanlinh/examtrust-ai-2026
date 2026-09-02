from pathlib import Path
import hashlib
import json


def sha256_file(path):
    path = Path(path)
    h = hashlib.sha256()

    with path.open('rb') as f:
        for chunk in iter(
            lambda: f.read(1024 * 1024),
            b''
        ):
            h.update(chunk)

    return h.hexdigest()


def sha256_text(text):
    return hashlib.sha256(
        text.encode('utf-8')
    ).hexdigest()


def canonical_json_sha256(obj):
    canonical = json.dumps(
        obj,
        ensure_ascii=False,
        sort_keys=True,
        separators=(',', ':')
    )

    return sha256_text(canonical)


def file_record(path):
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(path)

    if not path.is_file():
        raise ValueError(f'Not a file: {path}')

    return {
        'path': str(path),
        'name': path.name,
        'size_bytes': path.stat().st_size,
        'sha256': sha256_file(path)
    }

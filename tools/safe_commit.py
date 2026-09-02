
from pathlib import Path
from zoneinfo import ZoneInfo
from datetime import datetime
import subprocess
import re
import json
import sys

ROOT = Path(__file__).resolve().parents[1]

sys.path.insert(0, str(ROOT))

from tools.autonote import create_note


SECRET_PATTERNS = [
    re.compile(r"\bsk-[A-Za-z0-9_-]{12,}\b"),
    re.compile(
        r"(?i)\b(api[_-]?key|password|token|secret)"
        r"\s*[:=]\s*['\"]?[^\s'\"]{8,}"
    ),
    re.compile(
        r"(?i)\bauthorization\s*:\s*bearer\s+"
        r"[A-Za-z0-9._-]+"
    ),
]

BLOCKED_FILENAMES = {
    ".env",
    "credentials.json",
    "secret.txt",
}

BLOCKED_SUFFIXES = {
    ".pem",
    ".key",
}


def run_git(args):
    process = subprocess.run(
        ["git"] + args,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    return (
        process.returncode,
        process.stdout.strip(),
        process.stderr.strip()
    )


def changed_files():
    """
    Return all tracked changes plus untracked non-ignored files.

    This deliberately avoids parsing fixed character positions
    from `git status --porcelain`, which can be fragile.
    """

    files = set()

    # Tracked files changed relative to HEAD:
    # staged + unstaged + deleted/renamed paths.
    code, out, err = run_git(
        ["diff", "--name-only", "HEAD"]
    )

    if code != 0:
        raise RuntimeError(
            f"git diff failed: {err}"
        )

    for rel in out.splitlines():
        rel = rel.strip()
        if rel:
            files.add(rel)

    # Untracked files that are not ignored by .gitignore.
    code, out, err = run_git(
        [
            "ls-files",
            "--others",
            "--exclude-standard"
        ]
    )

    if code != 0:
        raise RuntimeError(
            f"git ls-files failed: {err}"
        )

    for rel in out.splitlines():
        rel = rel.strip()
        if rel:
            files.add(rel)

    return sorted(files)

def scan_secrets(files):
    problems = []

    for rel in files:
        path = ROOT / rel

        if path.name in BLOCKED_FILENAMES:
            problems.append(
                f"BLOCKED_FILE: {rel}"
            )
            continue

        if path.suffix.lower() in BLOCKED_SUFFIXES:
            problems.append(
                f"BLOCKED_SECRET_FILE: {rel}"
            )
            continue

        if not path.exists() or not path.is_file():
            continue

        try:
            content = path.read_text(
                encoding="utf-8",
                errors="ignore"
            )
        except Exception:
            continue

        for pattern in SECRET_PATTERNS:
            if pattern.search(content):
                problems.append(
                    f"SECRET_PATTERN_FOUND: {rel}"
                )
                break

    return problems


def check_raw_policy(files):
    problems = []

    for rel in files:
        normalized = rel.replace("\\", "/")

        if normalized.startswith("data/raw/"):
            problems.append(
                f"RAW_FILE_IN_GIT_SCOPE: {rel}"
            )

    return problems


def syntax_check(files):
    python_files = [
        rel
        for rel in files
        if rel.endswith(".py")
        and (ROOT / rel).exists()
    ]

    if not python_files:
        return True, []

    errors = []

    for rel in python_files:
        process = subprocess.run(
            [
                sys.executable,
                "-m",
                "py_compile",
                rel
            ],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        if process.returncode != 0:
            errors.append(
                {
                    "file": rel,
                    "error": process.stderr.strip()
                }
            )

    return len(errors) == 0, errors


def safe_commit(goal, message):
    files_before = changed_files()

    if not files_before:
        print("NO_CHANGES")
        return 0

    print("\nCHANGED FILES")
    for rel in files_before:
        print(" -", rel)

    safety_problems = []

    safety_problems.extend(
        scan_secrets(files_before)
    )

    safety_problems.extend(
        check_raw_policy(files_before)
    )

    if safety_problems:
        print("\nBLOCK")
        for item in safety_problems:
            print(" -", item)

        create_note(
            goal=goal,
            status="BLOCKED",
            extra={
                "problems": safety_problems
            }
        )

        return 2

    syntax_ok, syntax_errors = syntax_check(
        files_before
    )

    if not syntax_ok:
        print("\nSYNTAX_FAILED")
        print(
            json.dumps(
                syntax_errors,
                ensure_ascii=False,
                indent=2
            )
        )

        create_note(
            goal=goal,
            status="SYNTAX_FAILED",
            extra={
                "errors": syntax_errors
            }
        )

        return 3

    note_id = create_note(
        goal=goal,
        status="PRE_COMMIT",
        extra={
            "safety": "PASS",
            "syntax": "PASS",
            "commit_message": message
        }
    )

    files_after_note = changed_files()

    stage_files = [
        rel
        for rel in files_after_note
        if not rel.replace("\\", "/")
        .startswith("data/raw/")
    ]

    code, out, err = run_git(
        ["add", "--"] + stage_files
    )

    if code != 0:
        print(err)
        return 4

    print("\nSTAGED SCOPE")

    code, out, err = run_git(
        ["diff", "--cached", "--name-status"]
    )

    print(out)

    code, out, err = run_git(
        ["commit", "-m", message]
    )

    if code != 0:
        print(out)
        print(err)
        return 5

    print("\nCOMMIT CREATED")
    print(out)

    code, head, err = run_git(
        ["rev-parse", "HEAD"]
    )

    print("COMMIT SHA:", head)

    code, status, err = run_git(
        ["status", "--porcelain"]
    )

    if status.strip():
        print("\nWARNING: WORKING TREE NOT CLEAN")
        print(status)
        return 6

    print("\nPOST VERIFY: PASS")
    print("WORKING TREE: CLEAN")

    return 0


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--goal",
        required=True
    )

    parser.add_argument(
        "--message",
        required=True
    )

    args = parser.parse_args()

    raise SystemExit(
        safe_commit(
            goal=args.goal,
            message=args.message
        )
    )

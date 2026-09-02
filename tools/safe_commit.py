
from pathlib import Path
import subprocess
import re
import json
import sys

ROOT = Path(__file__).resolve().parents[1]

sys.path.insert(0, str(ROOT))

from tools.autonote import create_note
from tools.full_pass import run_full_pass


SECRET_PATTERNS = [
    re.compile(r"\bsk-[A-Za-z0-9_-]{12,}\b"),
    re.compile(
        r"(?i)\b(api[_-]?key|password|token|secret)"
        r"\s*[:=]\s*['\"]?[^\s'\"]{8,}"
    ),
    re.compile(
        r"(?i)\bauthorization\s*:\s*bearer\s+[A-Za-z0-9._-]+"
    )
]

BLOCKED_FILENAMES = {
    ".env",
    "credentials.json",
    "secret.txt"
}

BLOCKED_SUFFIXES = {
    ".pem",
    ".key"
}


def run_git(args):
    p = subprocess.run(
        ["git"] + args,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    return (
        p.returncode,
        p.stdout.strip(),
        p.stderr.strip()
    )


def changed_files():
    files = set()

    code, out, err = run_git(
        ["diff", "--name-only", "HEAD"]
    )

    if code != 0:
        raise RuntimeError(err)

    for rel in out.splitlines():
        rel = rel.strip()
        if rel:
            files.add(rel)

    code, out, err = run_git(
        [
            "ls-files",
            "--others",
            "--exclude-standard"
        ]
    )

    if code != 0:
        raise RuntimeError(err)

    for rel in out.splitlines():
        rel = rel.strip()
        if rel:
            files.add(rel)

    return sorted(files)


def scan_precommit(files):
    problems = []

    for rel in files:
        p = ROOT / rel
        normalized = rel.replace("\\", "/")

        if normalized.startswith("data/raw/"):
            problems.append(
                f"RAW_FILE:{rel}"
            )

        if p.name in BLOCKED_FILENAMES:
            problems.append(
                f"BLOCKED_FILE:{rel}"
            )

        if p.suffix.lower() in BLOCKED_SUFFIXES:
            problems.append(
                f"SECRET_FILE:{rel}"
            )

        if not p.exists() or not p.is_file():
            continue

        try:
            content = p.read_text(
                encoding="utf-8",
                errors="ignore"
            )
        except Exception:
            continue

        for rx in SECRET_PATTERNS:
            if rx.search(content):
                problems.append(
                    f"SECRET_PATTERN:{rel}"
                )
                break

    return problems


def rebuild_notes_index():
    notes_dir = (
        ROOT
        / "evidence"
        / "development_notes"
    )

    records = []

    if notes_dir.exists():
        for path in sorted(
            notes_dir.glob("DEV-*.json")
        ):
            try:
                rec = json.loads(
                    path.read_text(
                        encoding="utf-8"
                    )
                )
            except Exception:
                continue

            if "note_id" not in rec:
                continue

            records.append({
                "timestamp": rec.get(
                    "timestamp",
                    ""
                ),
                "status": rec.get(
                    "status",
                    ""
                ),
                "note_id": rec.get(
                    "note_id",
                    path.stem
                ),
                "goal": rec.get(
                    "goal",
                    ""
                )
            })

    lines = [
        "# ExamTrust AI — Development Notes",
        "",
        "> Human-readable index generated from canonical AutoTrace evidence.",
        "> Detailed records remain in `evidence/development_notes/`.",
        "",
        "## Integrity rules",
        "",
        "- No backdated history.",
        "- No fabricated commits, Prompt Logs, benchmark results or demo evidence.",
        "- Failed/aborted transactions are preserved rather than deleted.",
        "- Commit requires FULL PASS before execution.",
        "- Push requires a FULL PASS record bound to the commit.",
        "",
        "## Development history",
        "",
        "| Time | Status | Note ID | Goal |",
        "|---|---|---|---|"
    ]

    for rec in records:
        ts = str(
            rec["timestamp"]
        ).replace("|", "\\|")

        status = str(
            rec["status"]
        ).replace("|", "\\|")

        note_id = str(
            rec["note_id"]
        ).replace("|", "\\|")

        goal = str(
            rec["goal"]
        ).replace("|", "\\|")

        lines.append(
            f"| {ts} | {status} | "
            f"`{note_id}` | {goal} |"
        )

    lines += [
        "",
        "## Detailed evidence",
        "",
        "```text",
        "evidence/development_notes/",
        "evidence/full_pass/",
        "```",
        ""
    ]

    (ROOT / "NOTES.md").write_text(
        "\n".join(lines),
        encoding="utf-8"
    )




def git_identity_preflight():
    def local_config_get(key):
        result = subprocess.run(
            ['git', 'config', '--local', '--get', key],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        if result.returncode not in (0, 1):
            print(
                'GIT IDENTITY PREFLIGHT ERROR:',
                key,
                result.stderr.strip()
            )
            return None

        return result.stdout.strip()

    name = local_config_get('user.name')
    email = local_config_get('user.email')

    problems = []

    if name is None:
        problems.append(
            'Unable to inspect Git user.name'
        )
    elif not name:
        problems.append(
            'Git user.name is missing'
        )

    if email is None:
        problems.append(
            'Unable to inspect Git user.email'
        )
    elif not email:
        problems.append(
            'Git user.email is missing'
        )

    if problems:
        print('GIT IDENTITY PREFLIGHT BLOCK')

        for problem in problems:
            print(' -', problem)

        return False, problems

    print('GIT IDENTITY PREFLIGHT: PASS')
    print('Git user.name:', name)
    print('Git user.email:', email)

    return True, []

def safe_commit(goal, message):
    identity_ok, identity_problems = git_identity_preflight()

    if not identity_ok:
        print('COMMIT BLOCKED: GIT IDENTITY PREFLIGHT FAILED')
        return 1

    files = changed_files()

    if not files:
        print("NO_CHANGES")
        return 0

    print("\nCHANGED FILES")
    for rel in files:
        print(" -", rel)

    problems = scan_precommit(files)

    if problems:
        create_note(
            goal=goal,
            status="BLOCKED",
            extra={
                "problems": problems
            }
        )

        print("PRECOMMIT BLOCK")
        for p in problems:
            print(" -", p)

        return 2

    create_note(
        goal=goal,
        status="PRE_COMMIT",
        extra={
            "commit_message": message,
            "full_pass_required": True
        }
    )

    rebuild_notes_index()

    files = changed_files()

    stage_files = [
        x
        for x in files
        if not x.replace("\\", "/")
        .startswith("data/raw/")
    ]

    code, out, err = run_git(
        ["add", "--"] + stage_files
    )

    if code != 0:
        print(err)
        return 3

    print("\nSTAGED SCOPE")
    code, out, err = run_git(
        [
            "diff",
            "--cached",
            "--name-status"
        ]
    )
    print(out)

    rc, pass_path, pass_record = run_full_pass(
        goal=goal,
        commit_message=message
    )

    if rc != 0:
        print(
            "COMMIT BLOCKED: FULL PASS FAILED"
        )
        return 10

    pass_rel = str(
        pass_path.relative_to(ROOT)
    ).replace("\\", "/")

    code, out, err = run_git(
        ["add", "--", pass_rel]
    )

    if code != 0:
        print(err)
        return 4

    code, out, err = run_git(
        ["commit", "-m", message]
    )

    if code != 0:
        print(out)
        print(err)
        return 5

    print("\nCOMMIT CREATED")
    print(out)

    head = run_git(
        ["rev-parse", "HEAD"]
    )[1]

    tree_status = run_git(
        ["status", "--porcelain"]
    )[1]

    if tree_status.strip():
        print(
            "POST_COMMIT_VERIFY_FAIL: "
            "working tree not clean"
        )
        return 6

    print("COMMIT SHA:", head)
    print("FULL PASS: VERIFIED PRE-COMMIT")
    print("POST VERIFY: PASS")
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

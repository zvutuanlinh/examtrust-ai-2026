from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import json
import hashlib
import subprocess

ROOT = Path(__file__).resolve().parents[1]
NOTE_DIR = ROOT / "evidence" / "development_notes"
NOTE_DIR.mkdir(parents=True, exist_ok=True)


def now():
    return datetime.now(ZoneInfo("Asia/Ho_Chi_Minh"))


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


def current_head():
    code, out, _ = run_git(
        ["rev-parse", "--verify", "HEAD"]
    )

    if code == 0:
        return out

    return "NO_COMMIT_YET"


def changed_files():
    code, out, _ = run_git(
        ["status", "--porcelain=v1", "--untracked-files=all"]
    )

    if code != 0:
        return []

    files = []

    for line in out.splitlines():
        if line.strip():
            files.append(line[3:].strip())

    return sorted(files)


def sha256_text(text):
    return hashlib.sha256(
        text.encode("utf-8")
    ).hexdigest()


def create_note(
    goal,
    status="CREATED",
    extra=None
):
    ts = now()

    note_id = ts.strftime(
        "DEV-%Y%m%d-%H%M%S"
    )

    record = {
        "note_id": note_id,
        "timestamp": ts.isoformat(
            timespec="seconds"
        ),
        "goal": goal,
        "git_head_before": current_head(),
        "changed_files": changed_files(),
        "status": status,
        "extra": extra or {}
    }

    canonical = json.dumps(
        record,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":")
    )

    record["record_sha256"] = (
        sha256_text(canonical)
    )

    json_path = (
        NOTE_DIR / f"{note_id}.json"
    )

    md_path = (
        NOTE_DIR / f"{note_id}.md"
    )

    json_path.write_text(
        json.dumps(
            record,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    changed_text = "\n".join(
        f"- {item}"
        for item in record["changed_files"]
    )

    if not changed_text:
        changed_text = "- None detected"

    extra_text = json.dumps(
        record["extra"],
        ensure_ascii=False,
        indent=2
    )

    md_lines = [
        "# Development Note",
        "",
        f"**Note ID:** {note_id}",
        "",
        f"**Timestamp:** {record['timestamp']}",
        "",
        f"**Goal:** {goal}",
        "",
        (
            "**Git HEAD before:** "
            f"{record['git_head_before']}"
        ),
        "",
        f"**Status:** {status}",
        "",
        "## Changed files",
        "",
        changed_text,
        "",
        "## Extra",
        "",
        "```json",
        extra_text,
        "```",
        "",
        "## Integrity",
        "",
        (
            "Record SHA256: "
            f"`{record['record_sha256']}`"
        ),
        ""
    ]

    md_content = "\n".join(md_lines)

    md_path.write_text(
        md_content,
        encoding="utf-8"
    )

    print("AUTONOTE_CREATED")
    print("Note ID:", note_id)
    print("JSON:", json_path)
    print("Markdown:", md_path)
    print(
        "SHA256:",
        record["record_sha256"]
    )

    return note_id


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--goal",
        required=True
    )

    parser.add_argument(
        "--status",
        default="CREATED"
    )

    args = parser.parse_args()

    create_note(
        goal=args.goal,
        status=args.status
    )

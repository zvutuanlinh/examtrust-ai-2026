
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import subprocess
import json
import sys

ROOT = Path(__file__).resolve().parents[1]

STATE_DIR = ROOT / ".autotrace"
STATE_DIR.mkdir(
    parents=True,
    exist_ok=True
)

ACTIVE_SESSION = (
    STATE_DIR
    / "active_session.json"
)

sys.path.insert(0, str(ROOT))

from tools.safe_commit import safe_commit
from tools.remote_logger import push_and_verify


def now():
    return datetime.now(
        ZoneInfo("Asia/Ho_Chi_Minh")
    )


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
        ["rev-parse", "HEAD"]
    )

    return out if code == 0 else None


def start_session():
    if ACTIVE_SESSION.exists():
        print("SESSION_ALREADY_ACTIVE")
        print(
            ACTIVE_SESSION.read_text(
                encoding="utf-8"
            )
        )
        return 2

    ts = now()

    session_id = ts.strftime(
        "SESSION-%Y%m%d-%H%M%S"
    )

    record = {
        "session_id": session_id,
        "started_at": ts.isoformat(
            timespec="seconds"
        ),
        "start_head": current_head(),
        "status": "ACTIVE"
    }

    ACTIVE_SESSION.write_text(
        json.dumps(
            record,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    print("SESSION_STARTED")
    print("Session ID:", session_id)
    print("Start HEAD:", record["start_head"])

    return 0


def commits_since(start_head):
    if not start_head:
        return []

    code, out, _ = run_git(
        [
            "log",
            f"{start_head}..HEAD",
            "--pretty=format:%H|%s"
        ]
    )

    if code != 0 or not out:
        return []

    records = []

    for line in out.splitlines():
        sha, message = line.split(
            "|",
            1
        )

        records.append({
            "sha": sha,
            "message": message
        })

    return records


def end_session(push=False):
    if not ACTIVE_SESSION.exists():
        print("NO_ACTIVE_SESSION")
        return 2

    session = json.loads(
        ACTIVE_SESSION.read_text(
            encoding="utf-8"
        )
    )

    end_ts = now()

    # IMPORTANT:
    # Session summary is created BEFORE safe_commit,
    # so it becomes part of the same closure commit.
    final_record = {
        **session,
        "ended_at": end_ts.isoformat(
            timespec="seconds"
        ),
        "pre_close_head": current_head(),
        "commits_before_close": (
            commits_since(
                session.get(
                    "start_head"
                )
            )
        ),
        "closure_method": (
            "safe_commit"
        ),
        "status": (
            "CLOSED_BY_COMMIT"
        )
    }

    output_dir = (
        ROOT
        / "evidence"
        / "sessions"
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    output_path = (
        output_dir
        / f"{session['session_id']}.json"
    )

    output_path.write_text(
        json.dumps(
            final_record,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    rc = safe_commit(
        goal=(
            "Close development session "
            f"{session['session_id']} "
            "with session evidence"
        ),
        message=(
            "chore(session): "
            "close development session"
        )
    )

    if rc != 0:
        print(
            "SESSION_CLOSE_FAILED:",
            rc
        )
        return rc

    ACTIVE_SESSION.unlink(
        missing_ok=True
    )

    print("SESSION_CLOSED")
    print("Evidence:", output_path)
    print("Closure HEAD:", current_head())

    if push:
        remote_rc = push_and_verify()

        if remote_rc != 0:
            print(
                "SESSION CLOSED LOCALLY; "
                "REMOTE SYNC PENDING"
            )
            return remote_rc

    return 0


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "action",
        choices=[
            "start",
            "end"
        ]
    )

    parser.add_argument(
        "--push",
        action="store_true"
    )

    args = parser.parse_args()

    if args.action == "start":
        raise SystemExit(
            start_session()
        )

    raise SystemExit(
        end_session(
            push=args.push
        )
    )

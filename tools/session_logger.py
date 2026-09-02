
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import subprocess
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
STATE_DIR = ROOT / ".autotrace"
STATE_DIR.mkdir(parents=True, exist_ok=True)

ACTIVE_SESSION = STATE_DIR / "active_session.json"

sys.path.insert(0, str(ROOT))

from tools.safe_commit import safe_commit


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
        print(ACTIVE_SESSION.read_text(
            encoding="utf-8"
        ))
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

    commits = []

    for line in out.splitlines():
        sha, message = line.split("|", 1)

        commits.append({
            "sha": sha,
            "message": message
        })

    return commits


def end_session(push=False):
    if not ACTIVE_SESSION.exists():
        print("NO_ACTIVE_SESSION")
        return 2

    session = json.loads(
        ACTIVE_SESSION.read_text(
            encoding="utf-8"
        )
    )

    # Commit any meaningful outstanding changes.
    rc = safe_commit(
        goal=(
            f"Close development session "
            f"{session['session_id']}"
        ),
        message=(
            "chore(session): close development session"
        )
    )

    # NO_CHANGES is also acceptable.
    if rc not in (0,):
        print(
            "SESSION_CLOSE_COMMIT_FAILED:",
            rc
        )
        return rc

    end_ts = now()

    final_record = {
        **session,
        "ended_at": end_ts.isoformat(
            timespec="seconds"
        ),
        "end_head": current_head(),
        "commits": commits_since(
            session.get("start_head")
        ),
        "status": "CLOSED"
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

    ACTIVE_SESSION.unlink()

    print("SESSION_CLOSED")
    print("Evidence:", output_path)
    print("End HEAD:", final_record["end_head"])

    if push:
        code, out, err = run_git(
            ["push"]
        )

        if code != 0:
            print("PUSH_PENDING")
            print(err)
            return 7

        print("PUSH_SUCCESS")

    return 0


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "action",
        choices=["start", "end"]
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

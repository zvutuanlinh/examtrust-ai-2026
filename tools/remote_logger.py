
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import subprocess
import json
import sys

ROOT = Path(__file__).resolve().parents[1]

sys.path.insert(0, str(ROOT))


def now():
    return datetime.now(
        ZoneInfo("Asia/Ho_Chi_Minh")
    )


def run_git(args, timeout=120):
    try:
        process = subprocess.run(
            ["git"] + args,
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout
        )
    except subprocess.TimeoutExpired:
        return {
            "status": "TIMEOUT",
            "returncode": None,
            "stdout": "",
            "stderr": "Git operation timed out."
        }

    return {
        "status": (
            "SUCCESS"
            if process.returncode == 0
            else "COMMAND_FAILURE"
        ),
        "returncode": process.returncode,
        "stdout": process.stdout.strip(),
        "stderr": process.stderr.strip()
    }


def git_value(args):
    result = run_git(args)

    if result["status"] != "SUCCESS":
        raise RuntimeError(
            result["stderr"]
        )

    return result["stdout"]


def create_remote_event(
    operation,
    status,
    local_head=None,
    remote_head=None,
    detail=None
):
    ts = now()

    event_id = ts.strftime(
        "REMOTE-%Y%m%d-%H%M%S"
    )

    record = {
        "event_id": event_id,
        "timestamp": ts.isoformat(
            timespec="seconds"
        ),
        "operation": operation,
        "status": status,
        "local_head": local_head,
        "remote_head": remote_head,
        "remote": (
            git_value(
                ["remote", "get-url", "origin"]
            )
            if local_head
            else None
        ),
        "force_push": False,
        "credential_persisted_in_evidence": False,
        "detail": detail or {}
    }

    output_dir = (
        ROOT
        / "evidence"
        / "remote_events"
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    output_path = (
        output_dir
        / f"{event_id}_{status}.json"
    )

    output_path.write_text(
        json.dumps(
            record,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    print("REMOTE_EVENT:", output_path)

    return output_path


def push_and_verify():
    local_before = git_value(
        ["rev-parse", "HEAD"]
    )

    push = run_git(
        ["push", "origin", "main"]
    )

    if push["status"] != "SUCCESS":
        status = "PUSH_PENDING"

        if (
            "authentication" in push["stderr"].lower()
            or "could not read username"
            in push["stderr"].lower()
        ):
            status = "AUTH_FAILURE"

        elif (
            "network" in push["stderr"].lower()
            or "resolve host"
            in push["stderr"].lower()
        ):
            status = "NETWORK_FAILURE"

        create_remote_event(
            operation="GIT_PUSH",
            status=status,
            local_head=local_before,
            detail={
                "stderr": push["stderr"]
            }
        )

        print(status)
        return 7

    fetch = run_git(
        ["fetch", "origin"]
    )

    if fetch["status"] != "SUCCESS":
        create_remote_event(
            operation="REMOTE_VERIFY",
            status="FETCH_FAILED",
            local_head=local_before,
            detail={
                "stderr": fetch["stderr"]
            }
        )

        return 8

    local_head = git_value(
        ["rev-parse", "HEAD"]
    )

    remote_head = git_value(
        ["rev-parse", "origin/main"]
    )

    if local_head != remote_head:
        create_remote_event(
            operation="REMOTE_VERIFY",
            status="VERIFY_FAILED",
            local_head=local_head,
            remote_head=remote_head
        )

        return 9

    create_remote_event(
        operation="GIT_PUSH_REMOTE_VERIFY",
        status="PASS",
        local_head=local_head,
        remote_head=remote_head,
        detail={
            "push": "SUCCESS",
            "fetch": "SUCCESS",
            "local_equals_remote": True
        }
    )

    print("PUSH: SUCCESS")
    print("REMOTE VERIFY: PASS")
    print("LOCAL HEAD :", local_head)
    print("REMOTE HEAD:", remote_head)

    return 0


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "action",
        choices=["push"]
    )

    args = parser.parse_args()

    if args.action == "push":
        raise SystemExit(
            push_and_verify()
        )


from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import subprocess
import json
import sys

# ARCH-STORAGE-01: canonical storage contract
try:
    from tools.storage_layout import (
        AUTOTRACE_REMOTE_EVENT_ROOT
    )
except ModuleNotFoundError:
    from storage_layout import (
        AUTOTRACE_REMOTE_EVENT_ROOT
    )


ROOT = Path(__file__).resolve().parents[1]

sys.path.insert(0, str(ROOT))

from tools.full_pass import verify_head_full_pass

DRIVE_REMOTE = AUTOTRACE_REMOTE_EVENT_ROOT

DRIVE_REMOTE.mkdir(
    parents=True,
    exist_ok=True
)


def now():
    return datetime.now(
        ZoneInfo("Asia/Ho_Chi_Minh")
    )


def run_git(args, timeout=120):
    try:
        p = subprocess.run(
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
            "stdout": "",
            "stderr": "Git timeout"
        }

    return {
        "status": (
            "SUCCESS"
            if p.returncode == 0
            else "COMMAND_FAILURE"
        ),
        "stdout": p.stdout.strip(),
        "stderr": p.stderr.strip()
    }


def git_value(args):
    r = run_git(args)

    if r["status"] != "SUCCESS":
        raise RuntimeError(
            r["stderr"]
        )

    return r["stdout"]


def durable_event(
    status,
    detail=None
):
    ts = now()

    local_head = git_value(
        ["rev-parse", "HEAD"]
    )

    remote_head = None

    try:
        remote_head = git_value(
            ["rev-parse", "origin/main"]
        )
    except Exception:
        pass

    event_id = ts.strftime(
        "REMOTE-%Y%m%d-%H%M%S-%f"
    )

    rec = {
        "event_id": event_id,
        "timestamp": ts.isoformat(
            timespec="seconds"
        ),
        "operation": "GIT_PUSH_REMOTE_VERIFY",
        "status": status,
        "local_head": local_head,
        "remote_head": remote_head,
        "force_push": False,
        "credential_persisted_in_evidence": False,
        "detail": detail or {}
    }

    out = (
        DRIVE_REMOTE
        / f"{event_id}_{status}.json"
    )

    out.write_text(
        json.dumps(
            rec,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    print(
        "DURABLE_REMOTE_EVENT:",
        out
    )


def push_and_verify():
    status = git_value(
        ["status", "--porcelain"]
    )

    if status.strip():
        print(
            "PUSH BLOCKED: working tree not clean"
        )
        return 20

    if not verify_head_full_pass():
        print(
            "PUSH BLOCKED: HEAD has no valid FULL PASS binding"
        )
        durable_event(
            "PUSH_GATE_BLOCKED",
            {
                "reason": (
                    "HEAD FULL PASS verification failed"
                )
            }
        )
        return 21

    fetch_before = run_git(
        ["fetch", "origin"]
    )

    if fetch_before["status"] != "SUCCESS":
        durable_event(
            "FETCH_FAILED",
            {
                "stderr": fetch_before["stderr"]
            }
        )
        return 22

    local_head = git_value(
        ["rev-parse", "HEAD"]
    )

    remote_head = git_value(
        ["rev-parse", "origin/main"]
    )

    relation = git_value(
        [
            "rev-list",
            "--left-right",
            "--count",
            "origin/main...HEAD"
        ]
    )

    print(
        "PRE-PUSH AHEAD/BEHIND:",
        relation
    )

    parts = relation.split()

    if len(parts) == 2:
        behind = int(parts[0])

        if behind != 0:
            durable_event(
                "DIVERGENCE_BLOCKED",
                {
                    "ahead_behind": relation
                }
            )
            return 23

    push = run_git(
        ["push", "origin", "main"]
    )

    if push["status"] != "SUCCESS":
        durable_event(
            "PUSH_FAILED",
            {
                "stderr": push["stderr"]
            }
        )
        return 24

    fetch = run_git(
        ["fetch", "origin"]
    )

    if fetch["status"] != "SUCCESS":
        durable_event(
            "FETCH_FAILED",
            {
                "stderr": fetch["stderr"]
            }
        )
        return 25

    final_local = git_value(
        ["rev-parse", "HEAD"]
    )

    final_remote = git_value(
        ["rev-parse", "origin/main"]
    )

    if final_local != final_remote:
        durable_event(
            "VERIFY_FAILED",
            {
                "local_head": final_local,
                "remote_head": final_remote
            }
        )
        return 26

    durable_event(
        "PASS",
        {
            "full_pass_gate": "PASS",
            "push": "SUCCESS",
            "remote_verify": "PASS",
            "local_equals_remote": True
        }
    )

    print("PUSH: SUCCESS")
    print("REMOTE VERIFY: PASS")
    print("LOCAL HEAD :", final_local)
    print("REMOTE HEAD:", final_remote)

    return 0


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "action",
        choices=["push"]
    )

    args = parser.parse_args()

    raise SystemExit(
        push_and_verify()
    )

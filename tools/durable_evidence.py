
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import subprocess
import hashlib
import json
import shutil

ROOT = Path(__file__).resolve().parents[1]

DRIVE_ROOT = Path(
    "/content/drive/MyDrive/"
    "ExamTrust_AI_2026/"
    "EVIDENCE/AUTOTRACE"
)

CHECKPOINT_ROOT = DRIVE_ROOT / "checkpoints"
REGISTRY_ROOT = DRIVE_ROOT / "manifests"

CHECKPOINT_ROOT.mkdir(
    parents=True,
    exist_ok=True
)

REGISTRY_ROOT.mkdir(
    parents=True,
    exist_ok=True
)


def now():
    return datetime.now(
        ZoneInfo("Asia/Ho_Chi_Minh")
    )


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


def git_value(args, default="UNKNOWN"):
    code, out, _ = run_git(args)

    return out if code == 0 else default


def sha256_file(path):
    path = Path(path)

    h = hashlib.sha256()

    with path.open("rb") as f:
        for chunk in iter(
            lambda: f.read(1024 * 1024),
            b""
        ):
            h.update(chunk)

    return h.hexdigest()


def get_git_state():
    status = git_value(
        [
            "status",
            "--porcelain=v1",
            "--untracked-files=all"
        ],
        ""
    )

    local_head = git_value(
        ["rev-parse", "HEAD"]
    )

    remote_head = git_value(
        ["rev-parse", "origin/main"]
    )

    ahead_behind = git_value(
        [
            "rev-list",
            "--left-right",
            "--count",
            "origin/main...HEAD"
        ]
    )

    return {
        "timestamp": now().isoformat(
            timespec="seconds"
        ),
        "branch": git_value(
            [
                "rev-parse",
                "--abbrev-ref",
                "HEAD"
            ]
        ),
        "local_head": local_head,
        "remote_head": remote_head,
        "local_equals_remote": (
            local_head == remote_head
        ),
        "ahead_behind": ahead_behind,
        "working_tree": (
            "CLEAN"
            if not status.strip()
            else "DIRTY"
        ),
        "status_porcelain": (
            status.splitlines()
            if status.strip()
            else []
        ),
        "last_commit": git_value(
            [
                "log",
                "-1",
                "--pretty=format:%H|%s"
            ]
        )
    }


def evidence_files():
    roots = [
        ROOT / "evidence" / "development_notes",
        ROOT / "evidence" / "full_pass",
        ROOT / "evidence" / "remote_events",
        ROOT / "evidence" / "sessions"
    ]

    files = []

    for base in roots:
        if not base.exists():
            continue

        for p in base.rglob("*"):
            if p.is_file():
                files.append(p)

    # Also preserve readable index and origin record.
    for name in [
        "NOTES.md",
        "PROJECT_ORIGIN.md"
    ]:
        p = ROOT / name
        if p.exists():
            files.append(p)

    return sorted(
        set(files),
        key=lambda x: str(x)
    )


def create_checkpoint(
    reason,
    checkpoint_type="MILESTONE"
):
    ts = now()

    checkpoint_id = ts.strftime(
        "CP-%Y%m%d-%H%M%S"
    )

    target = (
        CHECKPOINT_ROOT
        / checkpoint_id
    )

    # Append-only: never overwrite.
    if target.exists():
        raise RuntimeError(
            "Checkpoint collision: "
            + str(target)
        )

    target.mkdir(
        parents=True,
        exist_ok=False
    )

    git_state = get_git_state()

    # We allow a checkpoint only when the repo is clean
    # and local == remote for milestone closure.
    if checkpoint_type == "MILESTONE":
        if git_state["working_tree"] != "CLEAN":
            raise RuntimeError(
                "MILESTONE checkpoint requires CLEAN working tree."
            )

        if not git_state["local_equals_remote"]:
            raise RuntimeError(
                "MILESTONE checkpoint requires local == remote."
            )

    # --------------------------------------------------------
    # checkpoint metadata
    # --------------------------------------------------------

    checkpoint_meta = {
        "checkpoint_id": checkpoint_id,
        "timestamp": ts.isoformat(
            timespec="seconds"
        ),
        "type": checkpoint_type,
        "reason": reason,
        "append_only": True,
        "source_repository": str(ROOT),
        "credentials_included": False
    }

    (target / "checkpoint.json").write_text(
        json.dumps(
            checkpoint_meta,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    # --------------------------------------------------------
    # git state
    # --------------------------------------------------------

    (target / "git_state.json").write_text(
        json.dumps(
            git_state,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    # --------------------------------------------------------
    # copy evidence
    # --------------------------------------------------------

    evidence_target = target / "evidence"
    evidence_target.mkdir()

    copied = []

    for src in evidence_files():

        if src.parent == ROOT:
            rel = Path(src.name)
        else:
            rel = src.relative_to(ROOT)

        dst = target / rel

        dst.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        shutil.copy2(
            src,
            dst
        )

        copied.append({
            "path": str(rel).replace(
                "\\",
                "/"
            ),
            "size_bytes": dst.stat().st_size,
            "sha256": sha256_file(dst)
        })

    # --------------------------------------------------------
    # manifest
    # --------------------------------------------------------

    manifest = {
        "checkpoint_id": checkpoint_id,
        "timestamp": ts.isoformat(
            timespec="seconds"
        ),
        "reason": reason,
        "git_state": git_state,
        "files": copied
    }

    manifest_path = (
        target / "manifest.json"
    )

    manifest_path.write_text(
        json.dumps(
            manifest,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    # --------------------------------------------------------
    # SHA256SUMS
    # --------------------------------------------------------

    lines = []

    for p in sorted(
        target.rglob("*")
    ):
        if not p.is_file():
            continue

        if p.name == "SHA256SUMS.txt":
            continue

        rel = p.relative_to(target)

        lines.append(
            sha256_file(p)
            + "  "
            + str(rel).replace(
                "\\",
                "/"
            )
        )

    sha_path = (
        target / "SHA256SUMS.txt"
    )

    sha_path.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8"
    )

    # --------------------------------------------------------
    # registry outside checkpoint
    # --------------------------------------------------------

    registry = {
        "checkpoint_id": checkpoint_id,
        "timestamp": ts.isoformat(
            timespec="seconds"
        ),
        "reason": reason,
        "checkpoint_path": str(target),
        "local_head": git_state["local_head"],
        "remote_head": git_state["remote_head"],
        "local_equals_remote": (
            git_state["local_equals_remote"]
        ),
        "working_tree": (
            git_state["working_tree"]
        ),
        "manifest_sha256": sha256_file(
            manifest_path
        ),
        "sha256sums_sha256": sha256_file(
            sha_path
        ),
        "credentials_included": False
    }

    registry_path = (
        REGISTRY_ROOT
        / f"{checkpoint_id}.json"
    )

    if registry_path.exists():
        raise RuntimeError(
            "Registry collision."
        )

    registry_path.write_text(
        json.dumps(
            registry,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    print("DURABLE_CHECKPOINT_CREATED")
    print("Checkpoint ID:", checkpoint_id)
    print("Path:", target)
    print("Local HEAD:", git_state["local_head"])
    print("Remote HEAD:", git_state["remote_head"])
    print(
        "Local == Remote:",
        git_state["local_equals_remote"]
    )
    print(
        "Working tree:",
        git_state["working_tree"]
    )
    print(
        "Evidence files:",
        len(copied)
    )
    print(
        "Manifest SHA256:",
        registry["manifest_sha256"]
    )
    print(
        "SHA256SUMS SHA256:",
        registry["sha256sums_sha256"]
    )

    return target


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--reason",
        required=True
    )

    parser.add_argument(
        "--type",
        default="MILESTONE"
    )

    args = parser.parse_args()

    create_checkpoint(
        reason=args.reason,
        checkpoint_type=args.type
    )

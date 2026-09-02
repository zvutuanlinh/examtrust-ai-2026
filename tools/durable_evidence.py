
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import subprocess
import hashlib
import json
import shutil

# ARCH-STORAGE-01: canonical storage contract
try:
    from tools.storage_layout import (
        AUTOTRACE_ROOT,
        AUTOTRACE_CHECKPOINT_ROOT,
        AUTOTRACE_MANIFEST_ROOT,
        SOURCEGUARD_GOVERNANCE_ROOT
    )
except ModuleNotFoundError:
    from storage_layout import (
        AUTOTRACE_ROOT,
        AUTOTRACE_CHECKPOINT_ROOT,
        AUTOTRACE_MANIFEST_ROOT,
        SOURCEGUARD_GOVERNANCE_ROOT
    )


ROOT = Path(__file__).resolve().parents[1]

DRIVE_ROOT = AUTOTRACE_ROOT

CHECKPOINT_ROOT = AUTOTRACE_CHECKPOINT_ROOT
REGISTRY_ROOT = AUTOTRACE_MANIFEST_ROOT
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


def evidence_records():
    """
    Return explicit checkpoint evidence-source records.

    Each record preserves:
    - physical source path;
    - source class;
    - original source root;
    - original relative provenance;
    - destination-relative checkpoint path.

    Repo evidence and Drive-only external evidence are never
    represented as the same provenance class.
    """

    repo_roots = [
        ROOT / "evidence" / "development_notes",
        ROOT / "evidence" / "full_pass",
        ROOT / "evidence" / "remote_events",
        ROOT / "evidence" / "sessions",
        ROOT / "evidence" / "notebook_lineage"
    ]

    records = []

    for base in repo_roots:
        if not base.exists():
            continue

        for src in base.rglob("*"):
            if not src.is_file():
                continue

            rel = src.relative_to(ROOT)

            records.append({
                "src": src,
                "checkpoint_rel": rel,
                "source_class": "repo_evidence",
                "source_root": str(ROOT),
                "source_relative_path": str(rel).replace(
                    "\\",
                    "/"
                )
            })

    # Preserve readable repository index/origin records.
    for name in [
        "NOTES.md",
        "PROJECT_ORIGIN.md"
    ]:
        src = ROOT / name

        if not src.exists():
            continue

        rel = Path(src.name)

        records.append({
            "src": src,
            "checkpoint_rel": rel,
            "source_class": "repo_root_record",
            "source_root": str(ROOT),
            "source_relative_path": str(rel).replace(
                "\\",
                "/"
            )
        })

    # Drive-only governance evidence is checkpointed explicitly
    # under an external namespace. It must never masquerade as
    # evidence originating from the Git repository.
    external_root = SOURCEGUARD_GOVERNANCE_ROOT

    if external_root.exists():
        for src in external_root.rglob("*"):
            if not src.is_file():
                continue

            external_rel = src.relative_to(
                external_root
            )

            checkpoint_rel = (
                Path("external_evidence")
                / "sourceguard_governance"
                / external_rel
            )

            records.append({
                "src": src,
                "checkpoint_rel": checkpoint_rel,
                "source_class": "drive_external_sourceguard_governance",
                "source_root": str(external_root),
                "source_relative_path": str(
                    external_rel
                ).replace(
                    "\\",
                    "/"
                )
            })

    return sorted(
        records,
        key=lambda item: (
            item["source_class"],
            str(item["checkpoint_rel"])
        )
    )


def evidence_files():
    """
    Backward-compatible source-path view.

    New checkpoint code should use evidence_records() so source
    provenance is not lost.
    """

    return [
        item["src"]
        for item in evidence_records()
    ]

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

    for evidence_record in evidence_records():

        src = evidence_record["src"]
        rel = evidence_record["checkpoint_rel"]

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
            "sha256": sha256_file(dst),
            "source_class": evidence_record[
                "source_class"
            ],
            "source_root": evidence_record[
                "source_root"
            ],
            "source_relative_path": evidence_record[
                "source_relative_path"
            ]
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

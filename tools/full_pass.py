
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import subprocess
import hashlib
import json
import sys
import re

ROOT = Path(__file__).resolve().parents[1]
PASS_DIR = ROOT / "evidence" / "full_pass"
PASS_DIR.mkdir(parents=True, exist_ok=True)

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

BLOCKED_NAMES = {
    ".env",
    "credentials.json",
    "secret.txt"
}

BLOCKED_SUFFIXES = {
    ".pem",
    ".key"
}


def now():
    return datetime.now(
        ZoneInfo("Asia/Ho_Chi_Minh")
    )


def run_cmd(args, timeout=180):
    try:
        p = subprocess.run(
            args,
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
            "stderr": "Operation timed out."
        }

    return {
        "status": (
            "SUCCESS"
            if p.returncode == 0
            else "COMMAND_FAILURE"
        ),
        "returncode": p.returncode,
        "stdout": p.stdout.strip(),
        "stderr": p.stderr.strip()
    }


def git(args, timeout=120):
    return run_cmd(
        ["git"] + args,
        timeout=timeout
    )


def git_value(args):
    r = git(args)
    if r["status"] != "SUCCESS":
        raise RuntimeError(r["stderr"])
    return r["stdout"]


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


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


def staged_files():
    out = git_value(
        [
            "diff",
            "--cached",
            "--name-only",
            "--diff-filter=ACMR"
        ]
    )

    return sorted(
        x.strip()
        for x in out.splitlines()
        if x.strip()
    )


def tracked_python_files():
    out = git_value(
        ["ls-files", "*.py"]
    )

    return sorted(
        x.strip()
        for x in out.splitlines()
        if x.strip()
    )


def syntax_gate():
    files = tracked_python_files()

    errors = []

    for rel in files:
        p = ROOT / rel

        if not p.exists():
            continue

        r = run_cmd(
            [
                sys.executable,
                "-m",
                "py_compile",
                rel
            ],
            timeout=60
        )

        if r["status"] != "SUCCESS":
            errors.append({
                "file": rel,
                "stderr": r["stderr"]
            })

    return {
        "gate": "SYNTAX",
        "status": (
            "PASS"
            if not errors
            else "FAIL"
        ),
        "checked_files": len(files),
        "errors": errors
    }


def unit_regression_gate():
    tests_dir = ROOT / "tests"

    if not tests_dir.exists():
        return {
            "gate": "UNIT_REGRESSION",
            "status": "PASS",
            "mode": "NO_TEST_SUITE_YET",
            "note": (
                "No tests directory exists at Git-foundation stage; "
                "operational acceptance remains mandatory."
            )
        }

    r = run_cmd(
        [
            sys.executable,
            "-m",
            "unittest",
            "discover",
            "-s",
            "tests",
            "-v"
        ],
        timeout=180
    )

    return {
        "gate": "UNIT_REGRESSION",
        "status": (
            "PASS"
            if r["status"] == "SUCCESS"
            else "FAIL"
        ),
        "stdout": r["stdout"],
        "stderr": r["stderr"]
    }


def adversarial_gate():
    problems = []

    tracked = git_value(
        ["ls-files"]
    ).splitlines()

    for rel in tracked:
        rel = rel.strip()

        if not rel:
            continue

        p = ROOT / rel

        if p.name in BLOCKED_NAMES:
            problems.append(
                f"BLOCKED_FILENAME:{rel}"
            )
            continue

        if p.suffix.lower() in BLOCKED_SUFFIXES:
            problems.append(
                f"BLOCKED_SECRET_SUFFIX:{rel}"
            )
            continue

        normalized = rel.replace("\\", "/")

        if normalized.startswith("data/raw/"):
            problems.append(
                f"RAW_TRACKED:{rel}"
            )
            continue

        if not p.exists() or not p.is_file():
            continue

        try:
            text = p.read_text(
                encoding="utf-8",
                errors="ignore"
            )
        except Exception:
            continue

        for rx in SECRET_PATTERNS:
            if rx.search(text):
                problems.append(
                    f"SECRET_PATTERN:{rel}"
                )
                break

    return {
        "gate": "ADVERSARIAL_SAFETY",
        "status": (
            "PASS"
            if not problems
            else "FAIL"
        ),
        "problems": problems
    }


def operational_gate():
    tools = [
        "tools/autonote.py",
        "tools/safe_commit.py",
        "tools/session_logger.py",
        "tools/remote_logger.py",
        "tools/durable_evidence.py",
        "tools/full_pass.py"
    ]

    results = []

    for rel in tools:
        p = ROOT / rel

        if not p.exists():
            continue

        r = run_cmd(
            [
                sys.executable,
                rel,
                "--help"
            ],
            timeout=30
        )

        results.append({
            "tool": rel,
            "status": (
                "PASS"
                if r["status"] == "SUCCESS"
                else "FAIL"
            )
        })

    failed = [
        x
        for x in results
        if x["status"] != "PASS"
    ]

    return {
        "gate": "OPERATIONAL_ACCEPTANCE",
        "status": (
            "PASS"
            if not failed
            else "FAIL"
        ),
        "tools": results
    }


def staged_scope_gate():
    files = staged_files()

    problems = []

    for rel in files:
        normalized = rel.replace("\\", "/")

        if normalized.startswith("data/raw/"):
            problems.append(
                f"RAW_IN_STAGE:{rel}"
            )

        p = ROOT / rel

        if p.name in BLOCKED_NAMES:
            problems.append(
                f"BLOCKED_FILE_IN_STAGE:{rel}"
            )

        if p.suffix.lower() in BLOCKED_SUFFIXES:
            problems.append(
                f"SECRET_FILE_IN_STAGE:{rel}"
            )

    return {
        "gate": "STAGED_SCOPE",
        "status": (
            "PASS"
            if files and not problems
            else "FAIL"
        ),
        "files": files,
        "problems": problems
    }


def staged_manifest():
    manifest = []

    for rel in staged_files():
        p = ROOT / rel

        if p.exists() and p.is_file():
            manifest.append({
                "path": rel,
                "sha256": sha256_file(p),
                "size_bytes": p.stat().st_size
            })

    return manifest


def run_full_pass(goal, commit_message):
    parent_head = git_value(
        ["rev-parse", "HEAD"]
    )

    gates = [
        syntax_gate(),
        unit_regression_gate(),
        adversarial_gate(),
        operational_gate(),
        staged_scope_gate()
    ]

    failed = [
        g
        for g in gates
        if g["status"] != "PASS"
    ]

    status = (
        "FULL_PASS"
        if not failed
        else "FAIL"
    )

    ts = now()

    pass_id = ts.strftime(
        "PASS-%Y%m%d-%H%M%S-%f"
    )

    record = {
        "pass_id": pass_id,
        "timestamp": ts.isoformat(
            timespec="seconds"
        ),
        "goal": goal,
        "commit_message": commit_message,
        "parent_head": parent_head,
        "status": status,
        "gates": gates,
        "candidate_manifest": staged_manifest(),
        "credential_persisted": False,
        "force_push_authorized": False
    }

    canonical = json.dumps(
        record,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":")
    )

    record["record_sha256"] = sha256_bytes(
        canonical.encode("utf-8")
    )

    output = (
        PASS_DIR
        / f"{pass_id}_{status}.json"
    )

    output.write_text(
        json.dumps(
            record,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    print("FULL_PASS_RECORD:", output)

    for gate in gates:
        print(
            gate["gate"],
            "=>",
            gate["status"]
        )

    print("FINAL:", status)

    return (
        0 if status == "FULL_PASS" else 10,
        output,
        record
    )


def verify_head_full_pass():
    head = git_value(
        ["rev-parse", "HEAD"]
    )

    parent = git_value(
        ["rev-parse", "HEAD^"]
    )

    pass_files = git_value(
        [
            "ls-tree",
            "-r",
            "--name-only",
            "HEAD",
            "evidence/full_pass"
        ]
    ).splitlines()

    candidates = []

    for rel in pass_files:
        if not rel.endswith(
            "_FULL_PASS.json"
        ):
            continue

        p = ROOT / rel

        if not p.exists():
            continue

        try:
            rec = json.loads(
                p.read_text(
                    encoding="utf-8"
                )
            )
        except Exception:
            continue

        if rec.get("parent_head") == parent:
            candidates.append(
                (rel, rec)
            )

    if not candidates:
        print(
            "PUSH_GATE_FAIL: "
            "no FULL_PASS record bound to HEAD parent."
        )
        return False

    rel, rec = candidates[-1]

    if rec.get("status") != "FULL_PASS":
        return False

    for item in rec.get(
        "candidate_manifest",
        []
    ):
        path = ROOT / item["path"]

        if not path.exists():
            print(
                "PUSH_GATE_FAIL missing:",
                item["path"]
            )
            return False

        if sha256_file(path) != item["sha256"]:
            print(
                "PUSH_GATE_FAIL hash mismatch:",
                item["path"]
            )
            return False

    print(
        "HEAD FULL_PASS VERIFIED:",
        rel
    )

    return True


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()

    sub = parser.add_subparsers(
        dest="action",
        required=True
    )

    runp = sub.add_parser("run")
    runp.add_argument(
        "--goal",
        required=True
    )
    runp.add_argument(
        "--message",
        required=True
    )

    sub.add_parser("verify-head")

    args = parser.parse_args()

    if args.action == "run":
        rc, _, _ = run_full_pass(
            goal=args.goal,
            commit_message=args.message
        )
        raise SystemExit(rc)

    ok = verify_head_full_pass()
    raise SystemExit(
        0 if ok else 11
    )

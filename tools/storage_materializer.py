"""
Controlled ExamTrust storage materialization.

ARCH-STORAGE-01C

Principles:
- no filesystem mutation at import time;
- caller supplies the target project root;
- paths are derived internally from a fixed contract;
- creation is fail-closed;
- exact-tree verification is mandatory;
- unexpected directories invalidate acceptance;
- no deletion is performed by this module.
"""

from pathlib import Path


PILOT_01_RELATIVE_DIRS = (
    Path("EVIDENCE/SOURCEGUARD"),
    Path("EVIDENCE/SOURCEGUARD/SG-GOV-01"),
    Path("EVIDENCE/SOURCEGUARD/SG-GOV-01/governance"),
    Path("EVIDENCE/SOURCEGUARD/SG-GOV-01/goldsets"),
    Path("EVIDENCE/SOURCEGUARD/SG-GOV-01/pilots"),
    Path("EVIDENCE/SOURCEGUARD/SG-GOV-01/pilots/PILOT-01"),
    Path("EVIDENCE/SOURCEGUARD/SG-GOV-01/pilots/PILOT-01/input"),
    Path("EVIDENCE/SOURCEGUARD/SG-GOV-01/pilots/PILOT-01/gold"),
    Path("EVIDENCE/SOURCEGUARD/SG-GOV-01/pilots/PILOT-01/predictions"),
    Path("EVIDENCE/SOURCEGUARD/SG-GOV-01/pilots/PILOT-01/comparisons"),
    Path("EVIDENCE/SOURCEGUARD/SG-GOV-01/pilots/PILOT-01/risk"),
    Path("EVIDENCE/SOURCEGUARD/SG-GOV-01/pilots/PILOT-01/manifests"),
)


def _resolved(path):
    return Path(path).expanduser().resolve()


def _assert_contained(root, target):
    root = _resolved(root)
    target = _resolved(target)

    try:
        target.relative_to(root)
    except ValueError as exc:
        raise ValueError(
            f"Target escapes project root: {target}"
        ) from exc

    return root, target


def pilot01_expected_dirs(project_root):
    root = _resolved(project_root)

    result = []

    for relative in PILOT_01_RELATIVE_DIRS:
        target = root / relative
        _assert_contained(root, target)
        result.append(target)

    return tuple(result)


def materialize_pilot01(project_root):
    root = _resolved(project_root)

    if not root.exists():
        raise FileNotFoundError(
            f"Project root does not exist: {root}"
        )

    if not root.is_dir():
        raise NotADirectoryError(
            f"Project root is not a directory: {root}"
        )

    expected = pilot01_expected_dirs(root)

    for target in expected:
        _assert_contained(root, target)
        target.mkdir(
            parents=True,
            exist_ok=True,
        )

    verification = verify_pilot01_tree(root)

    if not verification["accepted"]:
        raise RuntimeError(
            "Pilot-01 tree materialization failed exact-tree acceptance: "
            + repr(verification)
        )

    return verification


def verify_pilot01_tree(project_root):
    root = _resolved(project_root)

    sourceguard_root = (
        root
        / "EVIDENCE"
        / "SOURCEGUARD"
    )

    expected_absolute = set(
        pilot01_expected_dirs(root)
    )

    missing = sorted(
        str(path)
        for path in expected_absolute
        if not path.is_dir()
    )

    discovered = set()

    if sourceguard_root.exists():
        discovered.add(sourceguard_root.resolve())

        for path in sourceguard_root.rglob("*"):
            if path.is_dir():
                discovered.add(
                    path.resolve()
                )

    unexpected = sorted(
        str(path)
        for path in (
            discovered
            - expected_absolute
        )
    )

    return {
        "accepted": (
            not missing
            and not unexpected
        ),
        "project_root": str(root),
        "expected_count": len(expected_absolute),
        "discovered_count": len(discovered),
        "missing": missing,
        "unexpected": unexpected,
    }

"""
ExamTrust canonical storage layout.

ARCH-STORAGE-01

This module is deliberately PURE:
- importing it must not create directories;
- it defines canonical storage locations only;
- lazy roots remain absent until a real operation creates them;
- materialization and verification are separate operations.

Filesystem existence is not evidence of architectural acceptance.
"""

from pathlib import Path
from types import MappingProxyType


PROJECT_ROOT = Path(
    "/content/drive/MyDrive/"
    "ExamTrust_AI_2026"
)

WORKSPACE_ROOT = (
    PROJECT_ROOT
    / "WORKSPACE"
)

REPOSITORY_ROOT = (
    WORKSPACE_ROOT
    / "examtrust-ai-2026"
)

EVIDENCE_ROOT = (
    PROJECT_ROOT
    / "EVIDENCE"
)


# ---------------------------------------------------------------------
# ACTIVE OPERATIONAL DURABLE EVIDENCE
# ---------------------------------------------------------------------

AUTOTRACE_ROOT = (
    EVIDENCE_ROOT
    / "AUTOTRACE"
)

AUTOTRACE_CHECKPOINT_ROOT = (
    AUTOTRACE_ROOT
    / "checkpoints"
)

AUTOTRACE_MANIFEST_ROOT = (
    AUTOTRACE_ROOT
    / "manifests"
)

AUTOTRACE_REMOTE_EVENT_ROOT = (
    AUTOTRACE_ROOT
    / "remote_events"
)


# ---------------------------------------------------------------------
# LAZY CANONICAL EVIDENCE ROOTS
# ---------------------------------------------------------------------

DATA_RUNS_ROOT = (
    EVIDENCE_ROOT
    / "DATA_RUNS"
)

PROMPT_RUNS_ROOT = (
    EVIDENCE_ROOT
    / "PROMPT_RUNS"
)

SOURCES_ROOT = (
    EVIDENCE_ROOT
    / "SOURCES"
)

PROVENANCE_BINDINGS_ROOT = (
    EVIDENCE_ROOT
    / "PROVENANCE_BINDINGS"
)


# ---------------------------------------------------------------------
# SPECIAL DURABLE / RECOVERY DOMAIN
# ---------------------------------------------------------------------

RECOVERY_ROOT = (
    EVIDENCE_ROOT
    / "RECOVERY"
)


# ---------------------------------------------------------------------
# SOURCEGUARD
#
# Defined by storage contract but NOT activated/materialized merely
# because this module is imported.
# ---------------------------------------------------------------------

SOURCEGUARD_ROOT = (
    EVIDENCE_ROOT
    / "SOURCEGUARD"
)

SOURCEGUARD_GOV_01_ROOT = (
    SOURCEGUARD_ROOT
    / "SG-GOV-01"
)

SOURCEGUARD_GOVERNANCE_ROOT = (
    SOURCEGUARD_GOV_01_ROOT
    / "governance"
)

SOURCEGUARD_GOLDSETS_ROOT = (
    SOURCEGUARD_GOV_01_ROOT
    / "goldsets"
)

SOURCEGUARD_PILOTS_ROOT = (
    SOURCEGUARD_GOV_01_ROOT
    / "pilots"
)

SOURCEGUARD_PILOT_01_ROOT = (
    SOURCEGUARD_PILOTS_ROOT
    / "PILOT-01"
)

SOURCEGUARD_PILOT_01_INPUT = (
    SOURCEGUARD_PILOT_01_ROOT
    / "input"
)

SOURCEGUARD_PILOT_01_GOLD = (
    SOURCEGUARD_PILOT_01_ROOT
    / "gold"
)

SOURCEGUARD_PILOT_01_PREDICTIONS = (
    SOURCEGUARD_PILOT_01_ROOT
    / "predictions"
)

SOURCEGUARD_PILOT_01_COMPARISONS = (
    SOURCEGUARD_PILOT_01_ROOT
    / "comparisons"
)

SOURCEGUARD_PILOT_01_RISK = (
    SOURCEGUARD_PILOT_01_ROOT
    / "risk"
)

SOURCEGUARD_PILOT_01_MANIFESTS = (
    SOURCEGUARD_PILOT_01_ROOT
    / "manifests"
)


# ---------------------------------------------------------------------
# NOTEBOOK SUPPORTING HISTORY
# ---------------------------------------------------------------------

NOTEBOOKS_ROOT = (
    PROJECT_ROOT
    / "NOTEBOOKS"
)

NOTEBOOK_WORKING_ROOT = (
    NOTEBOOKS_ROOT
    / "WORKING"
)

NOTEBOOK_HISTORY_ROOT = (
    NOTEBOOKS_ROOT
    / "HISTORY"
)

NOTEBOOK_MANIFEST_ROOT = (
    NOTEBOOKS_ROOT
    / "MANIFESTS"
)


# ---------------------------------------------------------------------
# PLACEHOLDER ONLY
#
# Existence of this directory does NOT mean an independent backup
# system is implemented.
# ---------------------------------------------------------------------

BACKUP_ROOT = (
    PROJECT_ROOT
    / "BACKUP"
)


STORAGE_CLASS = MappingProxyType(
    {
        "AUTOTRACE": "ACTIVE_CANONICAL",
        "DATA_RUNS": "LAZY_CANONICAL",
        "PROMPT_RUNS": "LAZY_CANONICAL",
        "SOURCES": "LAZY_CANONICAL",
        "PROVENANCE_BINDINGS": "LAZY_CANONICAL",
        "RECOVERY": "SPECIAL_DURABLE",
        "SOURCEGUARD": "CONTRACTED_NOT_ACTIVATED",
        "NOTEBOOKS": "SUPPORTING_HISTORY",
        "BACKUP": "UNIMPLEMENTED_PLACEHOLDER",
    }
)


LAZY_ROOTS = (
    DATA_RUNS_ROOT,
    PROMPT_RUNS_ROOT,
    SOURCES_ROOT,
    PROVENANCE_BINDINGS_ROOT,
)


PILOT_01_REQUIRED_DIRS = (
    SOURCEGUARD_PILOT_01_ROOT,
    SOURCEGUARD_PILOT_01_INPUT,
    SOURCEGUARD_PILOT_01_GOLD,
    SOURCEGUARD_PILOT_01_PREDICTIONS,
    SOURCEGUARD_PILOT_01_COMPARISONS,
    SOURCEGUARD_PILOT_01_RISK,
    SOURCEGUARD_PILOT_01_MANIFESTS,
)


def canonical_paths():
    """Return canonical storage paths without touching the filesystem."""

    return {
        "project_root": PROJECT_ROOT,
        "workspace_root": WORKSPACE_ROOT,
        "repository_root": REPOSITORY_ROOT,
        "evidence_root": EVIDENCE_ROOT,
        "autotrace_root": AUTOTRACE_ROOT,
        "autotrace_checkpoint_root": AUTOTRACE_CHECKPOINT_ROOT,
        "autotrace_manifest_root": AUTOTRACE_MANIFEST_ROOT,
        "autotrace_remote_event_root": AUTOTRACE_REMOTE_EVENT_ROOT,
        "data_runs_root": DATA_RUNS_ROOT,
        "prompt_runs_root": PROMPT_RUNS_ROOT,
        "sources_root": SOURCES_ROOT,
        "provenance_bindings_root": PROVENANCE_BINDINGS_ROOT,
        "recovery_root": RECOVERY_ROOT,
        "sourceguard_root": SOURCEGUARD_ROOT,
        "sourceguard_gov_01_root": SOURCEGUARD_GOV_01_ROOT,
        "sourceguard_governance_root": SOURCEGUARD_GOVERNANCE_ROOT,
        "sourceguard_goldsets_root": SOURCEGUARD_GOLDSETS_ROOT,
        "sourceguard_pilots_root": SOURCEGUARD_PILOTS_ROOT,
        "sourceguard_pilot_01_root": SOURCEGUARD_PILOT_01_ROOT,
        "notebooks_root": NOTEBOOKS_ROOT,
        "backup_root": BACKUP_ROOT,
    }

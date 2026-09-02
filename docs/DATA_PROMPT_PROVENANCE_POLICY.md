# ExamTrust Data & Prompt Provenance Policy V1.0

## Purpose

Every real source document and every real model interaction used by ExamTrust must be traceable.

## Data lineage

Original Source
→ Original SHA256
→ ETDATA Run ID
→ Processing Configuration
→ Extractor Version
→ Output Assets
→ Output SHA256
→ Manifest

The data logger does not modify source files.

Raw source files are not committed to Git by default.

## Prompt lineage

Question Contract
→ Source References
→ Prompt Template Version
→ Model
→ Model Settings
→ Prompt SHA256
→ Response SHA256
→ Output Question IDs

Exact prompt and response snapshots are optional.

Credential-like material must not be persisted in prompt snapshots.

## Canonical provenance chain

Question ID
→ Prompt Run ID
→ Question Contract ID
→ Source Reference
→ Data Run ID
→ Original Source SHA256

## Integrity rules

- No backdating.
- No rewriting an existing Run ID.
- No fabricated data runs.
- No fabricated prompt runs.
- No fabricated model responses.
- No silent source mutation.
- No credential persistence.
- Run directories are append-only by Run ID.

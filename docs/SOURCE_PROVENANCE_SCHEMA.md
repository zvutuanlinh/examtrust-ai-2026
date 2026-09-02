# ExamTrust Source Registry & Provenance Binding V1.0

## Goal

Bind every derived assessment asset back to a registered source and its original SHA256.

## Canonical chain

Original Source File
→ SHA256
→ Source ID
→ Data Run ID
→ Asset ID
→ Precise Source Anchor
→ Question Contract ID
→ Prompt Run ID
→ Question ID

## Source IDs

`SRC-<first 16 hex characters of SHA256, uppercase>`

The full SHA256 remains canonical; the shortened digest is used only as the readable Source ID.

A Source ID collision with a different full SHA256 is an error.

## Asset IDs

- `CH_###` — text chunk
- `FM_###` — formula
- `GR_###` — graph
- `IMG_###` — image

## Anchor schema

Required:

- `page`: integer >= 1

Optional:

- `line_start`
- `line_end`
- `bbox`: `[x0, y0, x1, y1]`

Text assets should use page plus internal line range when available.

Formula, graph and image assets should use tight bounding boxes when available.

## Source registry policy

- Register by SHA256.
- Never modify the original source.
- Do not copy raw content into the registry by default.
- Re-registering the identical source is idempotent.
- Existing registry records are not overwritten.

## Provenance binding policy

- Source must already be registered.
- Data Run must already exist.
- Binding IDs are append-only.
- Binding must contain Source ID, Data Run ID, Asset ID and anchor.
- Contract, Prompt Run and Question ID can be attached as the pipeline progresses.

## Integrity

- No backdating.
- No fabricated source registration.
- No fabricated Data Run linkage.
- No fabricated Prompt Run linkage.
- No rewriting an existing binding.
- No credential persistence.

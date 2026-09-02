# ExamTrust AI — Development Notes

> Human-readable index generated from canonical AutoTrace evidence.
> Detailed records remain in `evidence/development_notes/`.

## Integrity rules

- No backdated history.
- No fabricated commits, Prompt Logs, benchmark results or demo evidence.
- Failed/aborted transactions are preserved rather than deleted.
- `NOTES.md` is a readable index; JSON/Markdown files under `evidence/` are the detailed evidence.

## Development history

| Time | Status | Note ID | Goal |
|---|---|---|---|
| 2026-09-02T10:17:42+00:00 | CREATED | `DEV-20260902-101742` | Initialize ExamTrust automatic development history |
| 2026-09-02T10:22:12+00:00 | PRE_COMMIT | `DEV-20260902-102212` | Prepare initial ExamTrust repository with integrity policy and automatic development history |
| 2026-09-02T17:26:11+07:00 | PRE_COMMIT | `DEV-20260902-172611` | Add automated safe commit workflow and normalize AutoNote timestamps to Vietnam time |
| 2026-09-02T17:27:21+07:00 | PRE_COMMIT | `DEV-20260902-172721` | Repair safe commit changed-file detection and add automated safe commit workflow |
| 2026-09-02T17:28:29+07:00 | PRE_COMMIT | `DEV-20260902-172829` | Add automatic development session tracking |
| 2026-09-02T17:32:32+07:00 | PRE_COMMIT | `DEV-20260902-173232` | Record first GitHub push authentication failure before retry |
| 2026-09-02T17:49:12+07:00 | PRE_COMMIT | `DEV-20260902-174912` | Record GitHub authentication failure caused by insufficient PAT scope before successful retry |
| 2026-09-02T17:49:15+07:00 | PRE_COMMIT | `DEV-20260902-174915` | Record successful initial GitHub publication and verified local-remote equality |
| 2026-09-02T17:51:12+07:00 | PRE_COMMIT | `DEV-20260902-175112` | Add verified remote push logging and correct session closure evidence ordering |
| 2026-09-02T17:51:15+07:00 | PRE_COMMIT | `DEV-20260902-175115` | Preserve remote verification evidence generated after AutoTrace upgrade |
| 2026-09-02T17:59:28+07:00 | PRE_COMMIT | `DEV-20260902-175928` | Add readable GitHub development notes index while preserving canonical AutoTrace evidence |
| 2026-09-02T17:59:32+07:00 | PRE_COMMIT | `DEV-20260902-175932` | Preserve remote verification evidence after adding automatic NOTES index |
| 2026-09-02T18:00:57+07:00 | PRE_COMMIT | `DEV-20260902-180057` | Add append-only durable Google Drive checkpoints with Git state, manifest and SHA256 verification |

## Reading the evidence

Detailed development evidence:

```text
evidence/development_notes/
```

Remote publication evidence:

```text
evidence/remote_events/
```

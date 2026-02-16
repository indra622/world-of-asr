# Qwen Forced Alignment – Plan

Objective: Add optional forced alignment using Qwen’s alignment model to enrich transcripts without word timings. Users can enable it per request.

## Approach

- Provide a `QwenForcedAligner` processor that accepts audio path + transcript and returns the same schema with `segments[*].words` (start/end/word) where possible.
- Expose request fields:
  - `force_alignment: bool` – default false
  - `alignment_provider: "qwen"` – default qwen; extensible
- Integrate into `TranscriptionService.process_transcription` before result writing.

## Implementation Notes

- For now, added a stub (`backend/app/core/processors/forced_alignment.py`).
- Real implementation should:
  - Load Qwen alignment model (specify version and install steps).
  - Handle multi-lingual cases and segment boundaries.
  - Fall back gracefully if alignment fails.

## Risks

- Extra compute cost and latency.
- Language coverage differences vs ASR outputs.
- Dependency size.

## Milestones

- M1: Stub and wiring (done).
- M2: Implement Qwen alignment end-to-end with minimal config and docs.
- M3: Add tests and sample verification.


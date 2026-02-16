# World-of-ASR – Multi‑Provider ASR Expansion Plan

Goal: Support multiple ASR providers in addition to Whisper/Faster‑Whisper/NeMo, with a free default path and optional API‑key based premium providers. Add sample test sets for quick verification.

## Targets

- Google Cloud Speech‑to‑Text (v2)
- Qwen ASR (e.g., Qwen2‑Audio / cloud API where available)

## Principles

- Free by default: local Whisper/Faster‑Whisper remains usable without keys.
- Opt‑in providers: users can supply API keys via environment variables or UI to enable external providers.
- Unified job API: same request/response schema regardless of provider.
- Pluggable model manager: add provider adapters implementing a shared interface.

## Architecture

- Add provider adapters under `backend/app/core/models/`:
  - `google_stt.py`: wraps Google Cloud STT v2 streaming/batch.
  - `qwen_asr.py`: wraps Qwen ASR (local or hosted API).
- Extend `ModelManager` to route by `model_type`:
  - `google_stt`, `qwen_asr` new types.
- Configuration (`backend/app/config.py`):
  - `google_project_id`, `google_location`, `google_api_key` (or service account JSON path).
  - `qwen_api_key`, `qwen_endpoint`.
  - Enable flags: `enable_google`, `enable_qwen`.
- Security: store secrets via env, never commit; validate presence before enabling.

## API/UX

- Request (`TranscriptionRequest`):
  - `model_type`: add `google_stt`, `qwen_asr`.
  - `parameters`: map common knobs (language, diarization on/off, punctuation). Provider‑specific options accepted but ignored by others.
- Response: unchanged.
- UI (later): allow entering API keys; persist to `.env` only on explicit user action.

## Implementation Outline

1) Provider Adapters
   - Implement `ASRModelBase` for Google/Qwen with `load_model`, `transcribe`, `unload_model`.
   - Google: prefer official SDK; support batch file URI; fallback to direct bytes.
   - Qwen: if hosted HTTP, provide simple REST client with retries; if local, wrap library.

2) Config & Validation
   - Add new settings; expose in `/health` which providers are enabled (without revealing keys).

3) Service Integration
   - Ensure diarization runs on provider outputs (segments with start/end). If provider returns only text, perform forced alignment optionally or skip diarization.

4) Sample Test Sets
   - Add `samples/` with a few short public‑domain clips and expected transcripts (txt/json) for smoke tests.
   - Provide a script `scripts/run_samples.py` to submit to backend and verify basic outputs.

5) Docs & Limits
   - Document rate limits, costs, and language coverage per provider.

## Risks & Mitigations

- API keys leakage: never log keys; ensure `.env` ignore; offer secret mounts for deployments.
- Billing surprises: clearly mark when a paid provider is active; show provider in job metadata.
- Output schema mismatch: normalize to internal segment schema; note limitations for providers without word timestamps.

## Milestones

- M1: Stubs + config + provider selection plumbed (no external calls).
- M2: Google batch transcription end‑to‑end (with env key).
- M3: Qwen provider end‑to‑end.
- M4: Sample set + smoke test harness.


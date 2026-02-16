# World-of-ASR – Progress Log

Chronological log of actions, decisions, and changes while improving code quality and security.

## 2026-02-15

- Initialized documentation structure: added `docs/ISSUES.md` and `docs/PROGRESS.md`.
- Moved legacy MD reports into `docs/` for housekeeping.
- Updated root `README.md` to reflect current structure, setup, and docs location.
- Marked `backend/.env` for ignore in `.gitignore` to prevent secret leakage.
- Removed duplicate non-test file `sock_streaming_client_unittest.py` (identical to client UI code).

Next up:
- Align DB models, schemas, and services (status enums, relationships, result paths).
- Harden Docker exec invocation and content-type validation in upload.
- Add DB check to health endpoint; reduce broad CORS with credentials.

## 2026-02-15 (later)

- Back-end alignment: unified JobStatus usage; fixed service to use `uploaded_files` and per-format `Result` columns; generate UUIDs for `Job` and `Result`.
- Results API now derives available formats from per-format columns.
- Upload API: added MIME/extension whitelist checks and improved cleanup.
- Health endpoint: verifies DB connection.
- Docker exec hardened: pass argv list to `exec_run` in NeMo wrappers.
- Streaming server: fixed variable reference (`self.online_asr_proc`).
- SQLAlchemy base import modernized; removed unnecessary `asyncio` dependency from backend requirements.
- Added ASR expansion plan doc `docs/ASR_EXPANSION_PLAN.md`.

## 2026-02-15 (provider stubs)

- Config: added flags and keys for Google/Qwen providers.
- ModelManager: added routing for `google_stt`, `qwen_asr`.
- Schemas: extended `ModelType` with Google/Qwen; added `force_alignment`, `alignment_provider`; noted `'auto'` language hint.
- Added provider stubs: `backend/app/core/models/google_stt.py`, `qwen_asr.py`.
- Added forced alignment stub: `backend/app/core/processors/forced_alignment.py` and plan doc `docs/QWEN_ALIGNMENT_PLAN.md`.
 - Health endpoint exposes provider enable flags; added API usage guide `docs/API_USAGE.md`.
 - Updated `backend/.env.example` with Google/Qwen provider flags/keys.
- Added smoke test script `scripts/run_samples.py` and docs `docs/SAMPLES.md`. Upload allowlists now configurable via env.
 - Upload API: added explicit extension whitelist check and better error messages.
 - Smoke test: optional expected transcript comparison with approximate word-overlap scoring.
 - Gradio: language hint placeholders updated to include `auto`; legacy events treat `auto` as automatic language detection.
 - Added `docs/PROVIDERS.md` for enabling external providers.

## 2026-02-15 (NVIDIA plan + stubs)

- Added NVIDIA integration plan `docs/NVIDIA_INTEGRATION_PLAN.md`.
- Schema: added model types (nemo_ctc_offline, nemo_rnnt_streaming, triton_ctc, triton_rnnt, nvidia_riva) and `postprocess` options.
- Config: added flags/URLs for NeMo/Triton/Riva; updated `.env.example`.
- ModelManager: routing for NVIDIA providers behind flags.
- Adapters: stubs for NeMo CTC/RNNT, Triton, Riva.
- Post-processing stubs: PnC and VAD; service wiring to apply when requested.

Next up:
- Implement provider adapters (Google/Qwen) behind feature flags.
- Add `samples/` with small test clips + harness.

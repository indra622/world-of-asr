# NVIDIA ASR Integration Plan

## Goals

- Add NVIDIA NeMo and Triton-based ASR options alongside current Whisper stack.
- Provide stubs and configuration now; enable real backends when infra is ready.

## Targets

- NeMo CTC (offline batch): `nemo_ctc_offline`
- NeMo RNNT (streaming): `nemo_rnnt_streaming`
- Triton-served ASR (CTC/RNNT): `triton_ctc`, `triton_rnnt`
- (Optional) NVIDIA Riva: `nvidia_riva`
- Post-processing: Punctuation & Capitalization (PnC), VAD, NeMo Diarization

## Architecture

- New adapters under `backend/app/core/models/` implementing `ASRModelBase`:
  - `nemo_ctc.py` – batch audio transcription (stub now).
  - `nemo_rnnt.py` – streaming/transcribe (stub now).
  - `triton_asr.py` – generic Triton client wrapper (stub now).
  - `riva_asr.py` – Riva client wrapper (stub now).
- Feature flags in `config.py` to enable/disable providers.
- Service remains provider-agnostic via `ModelManager` routing.

## Post-processing chain

- Add PnC (`processors/pnc.py`) and future NeMo diarization integration.
- Options exposed in request payload (to be extended):
  - `postprocess: { pnc: bool, vad: bool }`

## Milestones

- M1 (this iteration):
  - Add config flags, schema model types, adapter stubs, provider listings.
  - Docs + runbook updates.
- M2: Implement NeMo CTC via Docker (reusing run_nemo.py with model arg).
- M3: Triton adapters (configurable model names/inputs), basic sample harness.
- M4: RNNT streaming path and PnC integration.

## Notes

- Real implementations require installing NeMo or Triton clients and setting GPU/Docker infra.
- Keep secrets and endpoints in environment; do not commit keys.


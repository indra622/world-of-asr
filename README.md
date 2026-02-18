# World-of-ASR

Speech-to-text workspace with three runtime modes:
- local interactive UI (Gradio)
- async REST backend (FastAPI)
- experimental streaming pipeline

## Start Here (5 minutes)

1) Clone and install base dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

2) Choose one path
- UI path: `python app.py`
- API path: `bash scripts/dev_server.sh`
- Streaming path: `pip install -r requirements-streaming.txt && bash scripts/streaming_server.sh`
- Streaming WebSocket path: `pip install -r requirements-streaming.txt && bash scripts/streaming_ws_server.sh`

3) Verify quickly
- UI: open Gradio URL from terminal
- API: open `http://localhost:8000/docs`
- Health: `curl http://localhost:8000/health`

## Path Chooser

| Path | Best for | Setup time | First command |
|---|---|---:|---|
| Gradio UI | quick local experiments, model comparison | 3-5 min | `python app.py` |
| FastAPI API | app integration, async job workflow | 5-10 min | `bash scripts/dev_server.sh` |
| Streaming | near real-time experimentation | 10-15 min | `python streaming/whisper_online_server.py` |

Choose Gradio if you are evaluating quality quickly, choose FastAPI if you need stable endpoint-based flow, and choose Streaming only when real-time behavior is the main requirement.

## Project Flow

```mermaid
flowchart LR
  A[Audio Input] --> B{Runtime Mode}
  B --> C[Gradio UI app.py]
  B --> D[FastAPI backend/app/main.py]
  B --> E[Streaming streaming/whisper_online_server.py]
  D --> F[/api/v1/upload]
  F --> G[/api/v1/transcribe]
  G --> H[Background processing]
  H --> I[/api/v1/results]
```

```text
Audio file
  -> upload (FastAPI /api/v1/upload)
  -> create transcription job (/api/v1/transcribe)
  -> background processing (model + optional diarization/alignment/postprocess)
  -> formatted outputs (vtt/srt/json/txt/tsv)
  -> download (/api/v1/results/{job_id}/{format})
```

Main entrypoints:
- `app.py`: Gradio UI for local transcription workflows
- `backend/app/main.py`: FastAPI app entrypoint
- `streaming/whisper_online_server.py`: streaming server entrypoint

## API Quickstart (60 seconds)

Start backend:

```bash
bash scripts/dev_server.sh
```

Upload one file:

```bash
curl -s -X POST "http://localhost:8000/api/v1/upload" \
  -F "files=@samples/example.wav"
```

Then use the returned `file_ids[0]` in a transcription request:

```bash
curl -s -X POST "http://localhost:8000/api/v1/transcribe" \
  -H "Content-Type: application/json" \
  -d '{
    "file_ids": ["<file-id>"],
    "model_type": "faster_whisper",
    "model_size": "large-v3",
    "language": "auto",
    "device": "cpu",
    "output_formats": ["vtt"]
  }'
```

Poll status:

```bash
curl -s "http://localhost:8000/api/v1/transcribe/jobs/<job-id>"
```

See full request/response examples in `docs/API_USAGE.md`.

## Repository Guide

- `app.py`: Gradio interface and local pipeline wiring
- `backend/`: API service, job orchestration, DB models, provider adapters
- `streaming/`: online streaming server and helpers
- `woa/`: legacy utilities reused by current modules
- `scripts/`: developer scripts (server start, sample fetch, smoke run)
- `docs/`: roadmap, issues, runbook, API usage, provider docs

## Runtime Modes

### 1) Local UI (Gradio)

```bash
python app.py
```

Use when:
- you want quick local transcription tests
- you want to compare model options interactively

### 2) Backend API (FastAPI)

```bash
# from repo root
pip install -r backend/requirements.txt
cp backend/.env.example backend/.env
bash scripts/dev_server.sh
```

Alternative manual run:

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Use when:
- you need async job processing and API integration
- you need upload/status/result endpoints

### 3) Streaming (experimental)

```bash
pip install -r requirements-streaming.txt
bash scripts/streaming_server.sh
```

WebSocket transport server:

```bash
bash scripts/streaming_ws_server.sh
```

Use when:
- you are testing near real-time transcription behavior
- you are working on streaming-side improvements

## Model and Provider Status

- Stable local path:
  - `origin_whisper`
  - `faster_whisper`
  - `fast_conformer` (Docker-dependent)
- Optional external providers (feature-flag driven, partial/stub state in some adapters):
  - `google_stt`
  - `qwen_asr`
  - NVIDIA family (`nemo_*`, `triton_*`, `nvidia_riva`)
  - `hf_auto_asr` (Hugging Face AutoModel, `model_size`에 모델 ID 전달)

Check current provider flags via:
- `GET /health`
- `GET /api/v1/transcribe/providers`

## Documentation Map

If you are new, read in this order:

1. `docs/RUNBOOK.md` - practical run commands
2. `docs/API_USAGE.md` - endpoint usage examples
3. `docs/STREAMING_GUIDE.md` - streaming architecture and active-use runbook
4. `docs/TROUBLESHOOTING.md` - failure patterns and fixes
5. `docs/ROADMAP.md` - where the project is heading
6. `docs/ISSUES.md` - known gaps and priorities
7. `docs/PROGRESS.md` - chronological implementation log

Integration and planning docs:
- `docs/PROVIDERS.md`
- `docs/ASR_EXPANSION_PLAN.md`
- `docs/NVIDIA_INTEGRATION_PLAN.md`
- `docs/QWEN_ALIGNMENT_PLAN.md`

Completion reports:
- `docs/PHASE2_COMPLETION_REPORT.md`
- `docs/PHASE3_COMPLETION_REPORT.md`

## Samples and Smoke Test

```bash
bash scripts/fetch_samples.sh
python scripts/run_samples.py --host http://localhost:8000 \
  --files samples/example.wav --model faster_whisper --model-size large-v3 \
  --language auto --format vtt --out samples/output
```

## Documentation Quality Check

Run docs integrity checks (stale refs + missing markdown links):

```bash
python scripts/check_docs.py
```

## Notes

- Do not commit `backend/.env`; use `backend/.env.example`.
- Streaming and GPU-related paths require additional system dependencies.
- Several standalone streaming scripts are under active hardening/refactoring.

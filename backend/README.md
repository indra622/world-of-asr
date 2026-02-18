# World-of-ASR Backend (FastAPI)

Async transcription backend for job-based ASR processing.

## What This Service Does

- accepts media uploads
- creates async transcription jobs
- tracks job progress and status
- returns downloadable outputs (`vtt`, `srt`, `json`, `txt`, `tsv`)

Core entrypoint: `backend/app/main.py`

## Quick Run

From repository root:

```bash
pip install -r backend/requirements.txt
cp backend/.env.example backend/.env
bash scripts/dev_server.sh
```

Or from `backend/`:

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

OpenAPI:
- Swagger: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## API Flow

1. `POST /api/v1/upload`
2. `POST /api/v1/transcribe`
3. `GET /api/v1/transcribe/jobs/{job_id}`
4. `GET /api/v1/results/{job_id}` or `GET /api/v1/results/{job_id}/{format}`

Provider/feature visibility:
- `GET /health`
- `GET /api/v1/transcribe/providers`

## Directory Map

```text
backend/
  app/
    main.py                 FastAPI app entrypoint
    config.py               settings/env management
    api/v1/                 route handlers (upload/transcribe/results)
    services/               orchestration/business logic
    core/models/            ASR adapters and ModelManager cache
    core/processors/        diarization/alignment/format/postprocess
    db/                     SQLAlchemy models and async session
    schemas/                Pydantic request/response models
  storage/                  uploads/results/temp runtime files
```

## Current State

- local providers are the main stable path (`origin_whisper`, `faster_whisper`, `fast_conformer`)
- generic HF AutoModel path is available via `hf_auto_asr` (`model_size`에 HF 모델 ID 전달)
- external providers are feature-flagged and partly stub-based
- current planning focus is real-time and scalability (see `docs/ROADMAP.md`)

## Related Documents

- Root overview: `README.md`
- API examples: `docs/API_USAGE.md`
- Operational runbook: `docs/RUNBOOK.md`
- Provider setup: `docs/PROVIDERS.md`
- Prioritized issues: `docs/ISSUES.md`

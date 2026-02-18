# Runbook - World-of-ASR

Practical operation guide for local development and smoke checks.

Companion references:
- `docs/API_USAGE.md`
- `docs/TROUBLESHOOTING.md`

## Scope

This runbook covers:
- starting the FastAPI backend
- validating service health
- running sample-based smoke tests
- quick troubleshooting for common local failures

## Backend Startup

Preferred command (from repository root):

```bash
bash scripts/dev_server.sh
```

Manual startup:

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Expected result:
- backend available at `http://localhost:8000`
- Swagger UI at `http://localhost:8000/docs`

## Streaming Startup (TCP socket)

Install dependencies:

```bash
pip install -r requirements-streaming.txt
```

Start streaming server:

```bash
bash scripts/streaming_server.sh
```

Start WebSocket streaming server:

```bash
bash scripts/streaming_ws_server.sh
```

Start streaming client (new terminal):

```bash
bash scripts/streaming_client.sh
```

Reference:
- `docs/STREAMING_GUIDE.md`

## Health Check

```bash
curl http://localhost:8000/health
```

Response interpretation:
- `status: healthy` + `database: connected` means backend and DB are ready
- `status: degraded` means backend is up but DB/provider checks have issues

## Sample Smoke Test

Fetch sample media:

```bash
bash scripts/fetch_samples.sh
```

Run smoke test:

```bash
python scripts/run_samples.py --host http://localhost:8000 \
  --files samples/example.wav --model faster_whisper --model-size large-v3 \
  --language auto --format vtt --out samples/output
```

Expected result:
- upload succeeds
- job transitions queued -> processing -> completed
- output file generated under `samples/output`

## Documentation Integrity Check

```bash
python scripts/check_docs.py
```

Expected result:
- stale markdown references are not detected
- referenced markdown files exist

## Environment Basics

Backend env file:

```bash
cp backend/.env.example backend/.env
```

Common fields to review:
- storage paths (`uploads`, `results`, `temp`)
- provider flags (`enable_google`, `enable_qwen`, `enable_nemo`, `enable_triton`, `enable_riva`)
- provider credentials/endpoints (only if external providers are used)

## External Providers

Provider setup details:
- `docs/PROVIDERS.md`

Quick check after enabling providers:
- `GET /health`
- `GET /api/v1/transcribe/providers`

## Common Troubleshooting

For deeper issue patterns, see `docs/TROUBLESHOOTING.md`.

### Backend does not start
- verify dependencies: `pip install -r backend/requirements.txt`
- ensure Python version is compatible (3.10+)
- check port conflict on `8000`

### Health is degraded
- inspect backend terminal logs
- confirm DB path is writable (`backend/storage`)
- verify `.env` values are valid

### Upload fails
- verify file type is allowed (audio/video whitelist)
- verify file size is within configured limit
- confirm upload directory exists and is writable

### Job stays queued or fails
- check model/device configuration (CPU/GPU mismatch)
- verify optional provider keys if external provider selected
- inspect error message via `GET /api/v1/transcribe/jobs/{job_id}`

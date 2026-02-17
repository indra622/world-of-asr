# Troubleshooting - World-of-ASR

Use this guide when local run/setup fails.

## Priority Language (Aligned with `docs/ISSUES.md`)

- `P0 (Critical)`: security risk, data loss risk, production blocker
- `P1 (High)`: major functionality failure or severe quality issue
- `P2 (Medium)`: workaround exists, but reliability/maintainability is degraded
- `P3 (Low)`: improvement opportunity, non-blocking

When escalating, include suggested priority (`P0`-`P3`) so issue triage aligns with `docs/ISSUES.md`.

## Quick Triage

1. confirm runtime path (UI, API, or streaming)
2. run health check if backend is involved: `curl http://localhost:8000/health`
3. inspect terminal where server/script is running
4. isolate to minimal case (single small wav file)

## Installation and Environment

### `ModuleNotFoundError` on startup
Symptoms:
- app exits immediately with missing package error

Actions:
- activate the intended virtual environment
- reinstall dependencies:

```bash
pip install -r requirements.txt
pip install -r backend/requirements.txt
```

### FFmpeg-related media decode failures
Symptoms:
- upload/transcription fails for mp3/mp4/m4a

Actions:
- install ffmpeg and verify:

```bash
ffmpeg -version
```

### API starts but provider flags look wrong
Symptoms:
- `/health` provider flags do not match expectation

Actions:
- check `backend/.env`
- restart backend after env changes
- verify with `GET /health` and `GET /api/v1/transcribe/providers`

## Backend API Failures

### `GET /health` returns degraded
Priority hint: `P1` by default, `P0` if this blocks production traffic.

Likely causes:
- database path permission issue
- optional provider misconfiguration

Actions:
- confirm `backend/storage` is writable
- inspect backend logs for DB/provider exceptions
- reset to local providers only and re-test

### Upload fails (`/api/v1/upload`)
Priority hint: `P1` when reproducible with valid files.

Likely causes:
- unsupported file type
- file size limit exceeded
- upload directory not writable

Actions:
- use a small `.wav` sample first
- confirm limits in backend settings
- verify storage directories exist

### Job remains `queued` or becomes `failed`
Priority hint: `P1` by default, `P0` if widespread and no fallback path.

Likely causes:
- model/device mismatch (`cuda` selected without usable GPU)
- optional provider selected without valid credentials
- dependency/runtime error during background processing

Actions:
- retry with `faster_whisper` + `cpu`
- inspect `GET /api/v1/transcribe/jobs/{job_id}` error field
- check backend terminal logs around job execution

## Streaming Path Failures

### Client connects then immediately disconnects
Priority hint: `P1` for primary streaming use cases, `P2` for experimental-only usage.

Likely causes:
- server not running on expected host/port
- audio device open/read issue

Actions:
- ensure streaming server is started first
- verify `STREAM_HOST` and `STREAM_PORT` values if overridden
- test with default localhost settings before customization

### No partial transcription output
Priority hint: `P1` for active streaming users, `P2` otherwise.

Likely causes:
- audio chunks not sent/read correctly
- silence threshold/VAD behavior delaying output
- provider/model initialization failure

Actions:
- test with clear speech near microphone
- reduce concurrent experiments and run one streaming script at a time
- inspect script terminal logs for initialization errors

## GPU/Provider Issues

### CUDA expected but CPU is used
Actions:
- verify torch CUDA availability in environment:

```bash
python -c "import torch; print(torch.cuda.is_available())"
```

- use `device: cpu` explicitly when GPU is unavailable

### External provider call failures
Actions:
- validate API key/endpoint in `backend/.env`
- keep provider flags disabled until credentials are verified
- start from local providers, then enable one external provider at a time

## Escalation Checklist

When reporting an issue, include:
- runtime mode (UI/API/streaming)
- exact command used
- failing endpoint/script
- full error message and recent logs
- sample input type and approximate file size

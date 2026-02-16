# Runbook – World-of-ASR

## Backend (FastAPI)

Start dev server:

```bash
bash scripts/dev_server.sh
```

Or manually:

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Health check:

```bash
curl http://localhost:8000/health
```

## Samples

Fetch sample audio:

```bash
bash scripts/fetch_samples.sh
```

Run smoke test:

```bash
python scripts/run_samples.py --host http://localhost:8000 \
  --files samples/example.wav --model faster_whisper --model-size large-v3 \
  --language auto --format vtt --out samples/output
```

## External Providers

See `docs/PROVIDERS.md` for enabling Google/Qwen providers via environment.


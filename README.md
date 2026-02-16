# World-of-ASR

Speech-to-text workspace combining interactive Gradio tools, a FastAPI backend, and optional streaming.

## Repository Structure

- `app.py`: Gradio UI for offline transcription (Whisper, Faster-Whisper, NeMo FastConformer via Docker).
- `backend/`: FastAPI backend (file upload, job orchestration, result formatting, DB via SQLAlchemy).
- `streaming/`: Whisper streaming server and helpers (based on ufal/whisper_streaming).
- `woa/`: Legacy utilities (formatters, diarization, event handlers) reused by new modules.
- `docs/`: Documentation (issues, progress, archived reports).

## Installation

```bash
sudo apt install ffmpeg
conda create --name woa python=3.11
conda activate woa
pip install -r requirements.txt
```

### Optional: Backend (FastAPI)

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env  # update values as needed
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
# Swagger: http://localhost:8000/docs
```

### Optional: NeMo FastConformer (Docker)

```bash
cd docker
docker build -t woa:v1.0 .
docker run -d --gpus 0 -it --name nvidia-nemo -v /tmp/gradio:/tmp/gradio woa:v1.0 tail -f /dev/null
```

Shell init (example):

```bash
export IP_ADDR=$(hostname -i)
export CONTAINER_ID=$(docker ps -q -f name=nvidia-nemo)
export HF_TOKEN="[YOUR_HF_TOKEN]"
```

## Streaming

Based on [ufal/whisper_streaming](https://github.com/ufal/whisper_streaming)

```bash
pip install -r requirements-streaming.txt
cd streaming && python whisper_online_server.py
```

## Running Gradio App

```bash
python app.py
```

## Key Features

- Multi-provider ASR architecture: local Whisper/Faster-Whisper/NeMo (free), optional Google/Qwen via API keys.
- Language selection with `auto` detection.
- Initial prompt forwarding to supported models.
- Optional forced alignment step (Qwen alignment planned) to enrich word timings.

## Documentation

- Issues and remediation plan: `docs/ISSUES.md`
- Progress log: `docs/PROGRESS.md`
- Archived reports: see `docs/` (migrated from project root)
- API usage guide: `docs/API_USAGE.md`
- Samples & smoke test: `docs/SAMPLES.md` and `scripts/run_samples.py`
 - External providers: `docs/PROVIDERS.md`
 - Runbook: `docs/RUNBOOK.md`

## Notes

- For security, do not commit `backend/.env`. Use `backend/.env.example` as a template.
- NVIDIA Triton serving reference: [Triton-ASR](https://github.com/shs131566/triton-asr)

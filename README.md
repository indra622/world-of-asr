# World-of-ASR

Speech-to-text workspace combining interactive Gradio tools, a FastAPI backend, and optional streaming.

## Repository Structure

- `app.py`: Gradio UI for offline transcription (Whisper, Faster-Whisper, NeMo FastConformer via Docker).
- `backend/`: FastAPI backend (file upload, job orchestration, result formatting, DB via SQLAlchemy).
- `streaming/`: Whisper streaming server and helpers (based on ufal/whisper_streaming).
- `woa/`: Legacy utilities (formatters, diarization, event handlers) reused by new modules.
- `docs/`: Documentation (issues, progress, archived reports).

## Installation

Prerequisites
- FFmpeg: `sudo apt-get install -y ffmpeg` (macOS: `brew install ffmpeg`)
- Python: 3.10+ (3.12 등 최신 버전 사용 가능)
- Optional: NVIDIA GPU + CUDA/cuDNN (Faster-Whisper/NeMo 가속 시)

Quickstart (venv)
```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Optional (conda)
```bash
conda create -n woa python=3.12 -y
conda activate woa
pip install -r requirements.txt
```

GPU (optional)
- PyTorch를 GPU로 사용하려면 PyTorch 설치 가이드를 따라 CUDA 빌드를 먼저 설치한 뒤 나머지 요구사항을 설치하세요.
  ```bash
  # 예시: CUDA 12.1 (환경에 맞게 수정)
  pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
  pip install -r requirements.txt
  ```

### Optional: Backend (FastAPI)

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env  # update values as needed
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
# Swagger: http://localhost:8000/docs

또는 편의 스크립트 사용:
```bash
bash scripts/dev_server.sh
```
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

Backend API 탭을 통해 FastAPI 백엔드를 직접 호출해 업로드/전사/다운로드를 수행할 수도 있습니다.

## Key Features

- Multi-provider ASR architecture: local Whisper/Faster-Whisper/NeMo (free), optional Google/Qwen via API keys.
- Language selection with `auto` detection.
- Initial prompt forwarding to supported models.
- Optional forced alignment step (Qwen alignment planned) to enrich word timings.

## Documentation

### Core Documentation
- **[Project Roadmap](docs/ROADMAP.md)** - Phase timeline, current status, and future plans
- **[Progress Log](docs/PROGRESS.md)** - Chronological log of changes and decisions
- **[Issues & Remediation](docs/ISSUES.md)** - Known issues with priority-based tracking (P0-P3)

### Technical Documentation
- **[API Usage Guide](docs/API_USAGE.md)** - REST API endpoints and usage examples
- **[External Providers](docs/PROVIDERS.md)** - Enabling Google, Qwen, NVIDIA providers
- **[Runbook](docs/RUNBOOK.md)** - Operational procedures and troubleshooting
- **[Samples & Testing](docs/SAMPLES.md)** - Test samples and smoke test script

### Integration Plans
- **[ASR Expansion Plan](docs/ASR_EXPANSION_PLAN.md)** - Future ASR provider integrations
- **[NVIDIA Integration](docs/NVIDIA_INTEGRATION_PLAN.md)** - NeMo, Triton, Riva integration
- **[Qwen Alignment Plan](docs/QWEN_ALIGNMENT_PLAN.md)** - Forced alignment implementation

### Completion Reports
- **[Phase 2 Completion](docs/PHASE2_COMPLETION.md)** - Model integration completion
- **[Phase 3 Completion](docs/PHASE3_COMPLETION.md)** - Async API completion

## Notes

- For security, do not commit `backend/.env`. Use `backend/.env.example` as a template.
- NVIDIA Triton serving reference: [Triton-ASR](https://github.com/shs131566/triton-asr)

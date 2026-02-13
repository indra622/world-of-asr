# World-of-ASR Backend (FastAPI)

FastAPI 기반 ASR 전사 서비스 백엔드

## 현재 상태 (Phase 1 완료)

### ✅ 완료된 작업

- [x] 백엔드 디렉토리 구조 생성
- [x] FastAPI 프로젝트 초기화
- [x] Pydantic 스키마 정의 (`schemas/transcription.py`)
- [x] SQLAlchemy 데이터베이스 모델 (`db/models.py`)
- [x] 환경 설정 관리 (`config.py`)
- [x] 파일 업로드 API (`/api/v1/upload`)
- [x] 데이터베이스 세션 관리 (SQLite with async)

### 📂 디렉토리 구조

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                   # FastAPI 앱 진입점
│   ├── config.py                 # 환경 변수 관리
│   ├── api/
│   │   └── v1/
│   │       ├── router.py         # API 라우터 통합
│   │       └── upload.py         # 파일 업로드 엔드포인트
│   ├── core/                     # 핵심 비즈니스 로직 (Phase 2)
│   ├── db/
│   │   ├── base.py
│   │   ├── models.py             # SQLAlchemy 모델
│   │   └── session.py            # DB 세션 관리
│   ├── schemas/
│   │   └── transcription.py      # Pydantic 스키마
│   └── services/                 # 서비스 레이어 (Phase 2+)
├── storage/                      # 로컬 스토리지
│   ├── uploads/                  # 업로드된 파일
│   ├── results/                  # 전사 결과
│   └── temp/                     # 임시 파일
├── requirements.txt
├── .env.example
└── .env
```

## 설치 및 실행

### 1. 의존성 설치

```bash
cd backend
pip install -r requirements.txt
```

### 2. 환경 변수 설정

```bash
cp .env.example .env
# .env 파일을 편집하여 필요한 값 설정
```

### 3. 서버 실행

```bash
python -m app.main
# 또는
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 4. API 문서 확인

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API 엔드포인트 (Phase 1)

### 기본 엔드포인트

- `GET /` - 루트
- `GET /health` - 헬스 체크

### 파일 업로드

- `POST /api/v1/upload` - 파일 업로드
  - Request: multipart/form-data (파일 최대 10개, 각 500MB)
  - Response: `{"file_ids": ["uuid-1", "uuid-2"], "uploaded_at": "..."}`

## 데이터베이스 모델

### Job (전사 작업)
- `id`: 작업 ID (UUID)
- `model_type`: 모델 타입 (origin_whisper, faster_whisper, fast_conformer)
- `status`: 작업 상태 (queued, processing, completed, failed)
- `progress`: 진행률 (0-100)
- `created_at`, `started_at`, `completed_at`

### UploadedFile (업로드된 파일)
- `id`: 파일 ID (UUID)
- `job_id`: 연결된 작업 ID
- `original_filename`: 원본 파일명
- `storage_path`: 저장 경로
- `file_size`, `mime_type`

### Result (전사 결과)
- `id`: 결과 ID (UUID)
- `job_id`: 작업 ID
- `file_id`: 파일 ID
- `segment_count`: 세그먼트 수
- `has_diarization`: 스피커 분별 여부
- 결과 파일 경로 (`json_path`, `vtt_path`, `srt_path`, `txt_path`, `tsv_path`)

## 다음 단계 (Phase 2)

- [ ] ASR 모델 클래스 구현 (기존 `woa/events.py` 리팩토링)
  - [ ] `ASRModelBase` 추상 클래스
  - [ ] `OriginWhisperModel`
  - [ ] `FasterWhisperModel`
  - [ ] `FastConformerModel`
- [ ] `ModelManager` 싱글톤 (모델 캐싱)
- [ ] `DiarizationProcessor` (기존 `woa/diarize.py` 리팩토링)
- [ ] 전사 API 엔드포인트 (`/api/v1/transcribe`)
- [ ] 작업 상태 조회 API (`/api/v1/jobs/{job_id}`)

## 기술 스택

- **FastAPI** 0.110.0 - 웹 프레임워크
- **Pydantic** 2.6.1 - 데이터 검증
- **SQLAlchemy** 2.0.27 - ORM
- **SQLite** (async) - 데이터베이스
- **Uvicorn** - ASGI 서버

## 라이선스

MIT

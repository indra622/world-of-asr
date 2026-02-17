"""
전사(Transcription) 관련 Pydantic 스키마
"""
from datetime import datetime
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    """작업 상태"""
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ModelType(str, Enum):
    """ASR 모델 타입"""
    ORIGIN_WHISPER = "origin_whisper"
    FASTER_WHISPER = "faster_whisper"
    FAST_CONFORMER = "fast_conformer"
    GOOGLE_STT = "google_stt"
    QWEN_ASR = "qwen_asr"
    NEMO_CTC_OFFLINE = "nemo_ctc_offline"
    NEMO_RNNT_STREAMING = "nemo_rnnt_streaming"
    TRITON_CTC = "triton_ctc"
    TRITON_RNNT = "triton_rnnt"
    NVIDIA_RIVA = "nvidia_riva"


class OutputFormat(str, Enum):
    """출력 형식"""
    JSON = "json"
    VTT = "vtt"
    SRT = "srt"
    TXT = "txt"
    TSV = "tsv"
    ALL = "all"


class DiarizationConfig(BaseModel):
    """스피커 분별 설정"""
    enabled: bool = True
    min_speakers: int = Field(ge=1, le=20, default=1, description="최소 화자 수")
    max_speakers: int = Field(ge=1, le=20, default=5, description="최대 화자 수")

    class Config:
        json_schema_extra = {
            "example": {
                "enabled": True,
                "min_speakers": 1,
                "max_speakers": 5
            }
        }


class TranscriptionParameters(BaseModel):
    """전사 파라미터"""
    batch_size: int = Field(ge=1, le=100, default=8, description="배치 크기")
    compute_type: str = Field(default="float16", description="연산 타입 (int8, float32, float16)")
    beam_size: int = Field(ge=1, le=100, default=5, description="빔 서치 크기")
    temperature: float = Field(ge=0, le=100, default=0, description="샘플링 온도")
    patience: float = Field(ge=0, le=100, default=0, description="Patience (0=default)")
    length_penalty: float = Field(ge=0, le=100, default=0, description="길이 페널티 (0=default)")
    compression_ratio_threshold: float = Field(ge=0, le=100, default=2.4, description="압축 비율 임계값")
    logprob_threshold: float = Field(ge=-10, le=10, default=-1, description="로그 확률 임계값")
    no_speech_threshold: float = Field(ge=0, le=1, default=0.6, description="무음 임계값")
    vad_onset: float = Field(ge=0, le=1, default=0.5, description="VAD 시작 임계값")
    vad_offset: float = Field(ge=0, le=1, default=0.363, description="VAD 종료 임계값")
    initial_prompt: Optional[str] = Field(default=None, description="초기 프롬프트")
    condition_on_previous_text: bool = Field(default=False, description="이전 텍스트 조건부")
    remove_punctuation_from_words: bool = Field(default=False, description="단어에서 구두점 제거")
    remove_empty_words: bool = Field(default=False, description="빈 단어 제거")

    class Config:
        json_schema_extra = {
            "example": {
                "batch_size": 8,
                "compute_type": "float16",
                "beam_size": 5,
                "temperature": 0,
                "patience": 0,
                "length_penalty": 0,
                "compression_ratio_threshold": 2.4,
                "logprob_threshold": -1,
                "no_speech_threshold": 0.6,
                "vad_onset": 0.5,
                "vad_offset": 0.363,
                "initial_prompt": None,
                "condition_on_previous_text": False
            }
        }


class PostprocessOptions(BaseModel):
    """후처리 옵션"""
    pnc: bool = Field(default=False, description="Punctuation & Capitalization")
    vad: bool = Field(default=False, description="Voice Activity Detection")

    class Config:
        json_schema_extra = {
            "example": {"pnc": True, "vad": False}
        }


class TranscriptionRequest(BaseModel):
    """전사 요청"""
    file_ids: List[str] = Field(min_length=1, max_length=10, description="업로드된 파일 ID 목록")
    model_type: ModelType = Field(description="ASR 모델 타입")
    model_size: str = Field(default="large-v3", description="모델 크기")
    language: Optional[str] = Field(default="ko", description="언어 힌트 (예: 'ko', 'en', 'auto')")
    device: str = Field(default="cuda", description="디바이스 (cpu, cuda)")
    parameters: TranscriptionParameters = Field(default_factory=TranscriptionParameters)
    diarization: DiarizationConfig = Field(default_factory=DiarizationConfig)
    output_formats: List[OutputFormat] = Field(default=[OutputFormat.VTT], description="출력 형식")
    # 강제 정렬(Forced Alignment) 옵션 (지원 모델에서만 동작)
    force_alignment: bool = Field(default=False, description="강제 정렬 수행 여부")
    alignment_provider: Optional[str] = Field(default="qwen", description="정렬 제공자(qwen 등)")
    postprocess: Optional[PostprocessOptions] = Field(default=None, description="후처리 옵션")

    class Config:
        json_schema_extra = {
            "example": {
                "file_ids": ["uuid-1", "uuid-2"],
                "model_type": "faster_whisper",
                "model_size": "large-v3",
                "language": "ko",
                "device": "cuda",
                "parameters": {},
                "diarization": {"enabled": True, "min_speakers": 1, "max_speakers": 5},
                "output_formats": ["vtt", "json"]
            }
        }


class TranscriptionResponse(BaseModel):
    """전사 생성 응답"""
    job_id: str
    status: JobStatus
    message: str
    files_count: int

    class Config:
        json_schema_extra = {
            "example": {
                "job_id": "job-uuid",
                "status": "queued",
                "message": "Transcription job created and queued for processing",
                "files_count": 2
            }
        }


class JobResponse(BaseModel):
    """작업 응답"""
    job_id: str
    status: JobStatus
    progress: int = Field(ge=0, le=100, default=0, description="진행률 (%)")
    current_file: Optional[str] = None
    total_files: int = 0
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "job_id": "job-uuid",
                "status": "processing",
                "progress": 45,
                "current_file": "file-1.mp3",
                "total_files": 2,
                "created_at": "2024-01-01T00:00:00Z",
                "started_at": "2024-01-01T00:01:00Z",
                "completed_at": None,
                "error": None
            }
        }


class UploadResponse(BaseModel):
    """파일 업로드 응답"""
    file_ids: List[str]
    uploaded_at: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "file_ids": ["uuid-1", "uuid-2"],
                "uploaded_at": "2024-01-01T00:00:00Z"
            }
        }


class ProgressMessage(BaseModel):
    """WebSocket 진행률 메시지"""
    type: str  # "progress" | "completed" | "error"
    job_id: str
    status: JobStatus
    progress: int = 0
    message: str
    timestamp: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "type": "progress",
                "job_id": "job-uuid",
                "status": "processing",
                "progress": 45,
                "message": "Processing segment 23/50",
                "timestamp": "2024-01-01T00:00:00Z"
            }
        }

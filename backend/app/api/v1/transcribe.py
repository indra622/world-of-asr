"""
전사 API 엔드포인트
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import logging

from app.db.session import get_db
from app.schemas.transcription import (
    TranscriptionRequest,
    TranscriptionResponse,
    JobResponse,
    JobStatus,
)
from app.services.transcription import TranscriptionService
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/transcribe", tags=["transcription"])


@router.post(
    "",
    response_model=TranscriptionResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="전사 요청 생성",
    description="""
    오디오 파일 전사 요청을 생성합니다.

    **동작 방식:**
    1. 전사 작업(Job)을 생성하고 즉시 응답
    2. 실제 전사는 백그라운드에서 비동기로 진행
    3. `/jobs/{job_id}` 엔드포인트로 진행 상황 조회
    4. 완료 후 `/results/{job_id}/{format}` 엔드포인트로 결과 다운로드

    **지원 모델:**
    - `faster_whisper`: CTranslate2 기반 고속 전사
    - `origin_whisper`: whisper-timestamped (단어 타임스탬프)
    - `fast_conformer`: NeMo FastConformer (Docker 필요)

    **출력 포맷:**
    - `vtt`: WebVTT 자막
    - `srt`: SRT 자막
    - `json`: JSON 형식 (프로그래밍용)
    - `txt`: 평문 텍스트
    - `tsv`: TSV (시작/종료/텍스트)
    """
)
async def create_transcription(
    request: TranscriptionRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    전사 요청 생성

    Args:
        request: 전사 요청 데이터
        background_tasks: FastAPI 백그라운드 태스크
        db: 데이터베이스 세션

    Returns:
        생성된 작업 정보
    """
    try:
        service = TranscriptionService(db)

        # Job 생성
        job = await service.create_job(
            request=request,
            file_ids=request.file_ids
        )

        # 백그라운드 태스크로 전사 시작
        background_tasks.add_task(
            process_transcription_task,
            job_id=str(job.id),
            hf_token=settings.huggingface_token
        )

        logger.info(f"Transcription job {job.id} created and queued")

        return TranscriptionResponse(
            job_id=str(job.id),
            status=job.status,
            message="Transcription job created and queued for processing",
            files_count=len(job.uploaded_files)
        )

    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to create transcription job: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create transcription job"
        )


async def process_transcription_task(job_id: str, hf_token: str):
    """
    백그라운드 전사 작업 처리

    Args:
        job_id: 작업 ID
        hf_token: HuggingFace 토큰
    """
    # 새로운 DB 세션 생성 (백그라운드 태스크용)
    from app.db.session import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        try:
            service = TranscriptionService(db)
            await service.process_transcription(
                job_id=job_id,
                hf_token=hf_token
            )
        except Exception as e:
            logger.error(f"Background transcription task failed for job {job_id}: {e}")
            # 에러는 이미 서비스 레이어에서 Job에 기록됨


@router.get(
    "/jobs/{job_id}",
    response_model=JobResponse,
    summary="작업 상태 조회",
    description="""
    전사 작업의 현재 상태를 조회합니다.

    **작업 상태:**
    - `pending`: 대기 중
    - `processing`: 처리 중
    - `completed`: 완료
    - `failed`: 실패

    **진행률:**
    - `progress`: 0-100 (백분율)
    - 파일 단위로 업데이트
    """
)
async def get_job_status(
    job_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    작업 상태 조회

    Args:
        job_id: 작업 ID
        db: 데이터베이스 세션

    Returns:
        작업 정보
    """
    try:
        service = TranscriptionService(db)
        job = await service.get_job(job_id)

        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job {job_id} not found"
            )

        return JobResponse(
            job_id=str(job.id),
            status=job.status,
            progress=job.progress or 0,
            current_file=job.current_file,
            total_files=job.total_files or 0,
            created_at=job.created_at,
            started_at=job.started_at,
            completed_at=job.completed_at,
            error=job.error_message,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get job status for {job_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve job status"
        )
@router.get(
    "/providers",
    summary="지원 제공자 및 모델 정보",
    description="현재 활성화된 ASR 제공자와 지원 모델/언어 정보를 반환합니다."
)
async def list_providers():
    providers = {
        "origin_whisper": True,
        "faster_whisper": True,
        "fast_conformer": True,
        "google_stt": settings.enable_google,
        "qwen_asr": settings.enable_qwen,
        "nemo_ctc_offline": settings.enable_nemo,
        "nemo_rnnt_streaming": settings.enable_nemo,
        "triton_ctc": settings.enable_triton,
        "triton_rnnt": settings.enable_triton,
        "nvidia_riva": settings.enable_riva,
    }

    models = {
        "origin_whisper": ["tiny", "base", "small", "medium", "large", "large-v2", "large-v3"],
        "faster_whisper": ["tiny", "base", "small", "medium", "large", "large-v2", "large-v3"],
        "fast_conformer": ["fast-conformer"]
    }

    languages = [
        "auto", "en", "ko", "ja", "zh", "de", "es", "fr", "ru", "it", "pt", "vi", "th"
    ]

    return {
        "providers": providers,
        "models": models,
        "languages": languages,
        "notes": "External providers require keys; see docs/PROVIDERS.md"
    }

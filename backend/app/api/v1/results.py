"""
전사 결과 API 엔드포인트
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pathlib import Path
import logging

from app.db.session import get_db
from app.services.transcription import TranscriptionService
from app.schemas.transcription import JobStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/results", tags=["results"])


@router.get(
    "/{job_id}/{format}",
    response_class=FileResponse,
    summary="결과 파일 다운로드",
    description="""
    전사 결과를 지정된 포맷으로 다운로드합니다.

    **지원 포맷:**
    - `vtt`: WebVTT 자막 파일 (.vtt)
    - `srt`: SRT 자막 파일 (.srt)
    - `json`: JSON 형식 (.json)
    - `txt`: 평문 텍스트 (.txt)
    - `tsv`: TSV 형식 (.tsv)

    **사용 예시:**
    ```
    GET /api/v1/results/{job_id}/vtt
    GET /api/v1/results/{job_id}/json
    ```

    **에러 코드:**
    - 404: 작업을 찾을 수 없음
    - 400: 작업이 아직 완료되지 않음
    - 404: 요청한 포맷의 결과 파일이 없음
    """
)
async def download_result(
    job_id: str,
    format: str,
    db: AsyncSession = Depends(get_db)
):
    """
    결과 파일 다운로드

    Args:
        job_id: 작업 ID
        format: 출력 포맷 (vtt, srt, json, txt, tsv)
        db: 데이터베이스 세션

    Returns:
        결과 파일
    """
    try:
        # 포맷 검증
        valid_formats = ["vtt", "srt", "json", "txt", "tsv"]
        if format not in valid_formats:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid format. Supported formats: {', '.join(valid_formats)}"
            )

        service = TranscriptionService(db)

        # Job 조회
        job = await service.get_job(job_id)

        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job {job_id} not found"
            )

        # 작업 완료 확인
        if job.status != JobStatus.COMPLETED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Job is not completed yet. Current status: {job.status}"
            )

        # 결과 파일 경로 조회
        file_path = await service.get_result_path(job_id, format)

        if not file_path:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Result file not found for format: {format}"
            )

        # 파일 존재 확인
        path = Path(file_path)
        if not path.exists():
            logger.error(f"Result file not found on disk: {file_path}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Result file not found on disk"
            )

        # 파일 다운로드
        # media_type을 포맷에 맞게 설정
        media_types = {
            "vtt": "text/vtt",
            "srt": "application/x-subrip",
            "json": "application/json",
            "txt": "text/plain",
            "tsv": "text/tab-separated-values"
        }

        return FileResponse(
            path=str(path),
            media_type=media_types.get(format, "application/octet-stream"),
            filename=path.name
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to download result for job {job_id}, format {format}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve result file"
        )


@router.get(
    "/{job_id}",
    summary="작업의 모든 결과 조회",
    description="""
    작업의 모든 결과 정보를 조회합니다.

    **응답 데이터:**
    - 각 파일별 결과 정보
    - 세그먼트 수
    - 화자 수 (스피커 분별 활성화 시)
    - 생성된 출력 파일 목록
    """
)
async def get_all_results(
    job_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    작업의 모든 결과 조회

    Args:
        job_id: 작업 ID
        db: 데이터베이스 세션

    Returns:
        결과 정보 리스트
    """
    try:
        service = TranscriptionService(db)
        job = await service.get_job(job_id)

        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job {job_id} not found"
            )

        if job.status != JobStatus.COMPLETED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Job is not completed yet. Current status: {job.status}"
            )

        # 결과 정보 구성
        results = []
        for result in job.results:
            results.append({
                "file_id": str(result.file_id),
                "filename": result.file.filename if result.file else "unknown",
                "segments_count": result.segments_count,
                "speakers_count": result.speakers_count,
                "available_formats": list(result.output_paths.keys()),
                "created_at": result.created_at
            })

        return {
            "job_id": str(job.id),
            "status": job.status,
            "results_count": len(results),
            "results": results
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get results for job {job_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve results"
        )

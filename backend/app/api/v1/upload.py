"""
파일 업로드 API 엔드포인트
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from datetime import datetime
import uuid
import shutil
from pathlib import Path
import logging

from app.config import settings
from app.db.session import get_db
from app.db.models import UploadedFile as UploadedFileModel
from app.schemas.transcription import UploadResponse

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/upload", response_model=UploadResponse, status_code=201)
async def upload_files(
    files: List[UploadFile] = File(..., description="업로드할 파일 (최대 10개)"),
    db: AsyncSession = Depends(get_db)
):
    """
    오디오/비디오 파일 업로드

    Args:
        files: 업로드할 파일 목록 (최대 10개, 각 500MB)
        db: 데이터베이스 세션

    Returns:
        UploadResponse: 업로드된 파일 ID 목록

    Raises:
        HTTPException 400: 파일 개수 초과 또는 파일 크기 초과
        HTTPException 500: 파일 저장 실패
    """
    # 파일 개수 검증
    if len(files) > settings.max_files:
        raise HTTPException(
            status_code=400,
            detail=f"최대 {settings.max_files}개의 파일만 업로드할 수 있습니다."
        )

    file_ids = []
    uploaded_at = datetime.utcnow()

    # 허용 확장자/타입 (환경 설정 기반)
    allowed_exts = set(ext.lower() for ext in settings.allowed_upload_exts)
    allowed_mimes_prefix = tuple(settings.allowed_mime_prefixes)

    try:
        for file in files:
            # 파일 크기 검증 (대략적)
            file.file.seek(0, 2)  # 파일 끝으로 이동
            file_size = file.file.tell()
            file.file.seek(0)  # 파일 시작으로 복귀

            if file_size > settings.max_file_size:
                raise HTTPException(
                    status_code=400,
                    detail=f"파일 '{file.filename}'의 크기가 최대 허용 크기({settings.max_file_size / 1024 / 1024:.0f}MB)를 초과합니다."
                )

            # 파일 유형 검증
            if file.content_type and not file.content_type.startswith(allowed_mimes_prefix):
                raise HTTPException(
                    status_code=400,
                    detail=f"'{file.filename}'은(는) 지원되지 않는 MIME 타입입니다: {file.content_type}"
                )

            # UUID 생성
            file_id = str(uuid.uuid4())

            # 파일 확장자 추출
            original_filename = file.filename or "unknown"
            file_extension = Path(original_filename).suffix

            # 확장자 허용 여부 검증
            if not file_extension:
                raise HTTPException(
                    status_code=400,
                    detail=f"'{original_filename}' 파일 확장자를 확인할 수 없습니다."
                )
            if file_extension.lower() not in allowed_exts:
                raise HTTPException(
                    status_code=400,
                    detail=f"'{original_filename}'은(는) 허용되지 않는 확장자입니다: {file_extension}"
                )

            # 저장 경로 생성
            storage_filename = f"{file_id}{file_extension}"
            storage_path = settings.upload_dir / storage_filename

            # 파일 저장
            with storage_path.open("wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            logger.info(f"File uploaded: {original_filename} -> {storage_path}")

            # DB에 파일 메타데이터 저장
            uploaded_file = UploadedFileModel(
                id=file_id,
                original_filename=original_filename,
                storage_path=str(storage_path),
                file_size=file_size,
                mime_type=file.content_type,
                uploaded_at=uploaded_at,
            )

            db.add(uploaded_file)
            file_ids.append(file_id)

        # 커밋
        await db.commit()

        logger.info(f"Successfully uploaded {len(file_ids)} files")

        return UploadResponse(
            file_ids=file_ids,
            uploaded_at=uploaded_at
        )

    except HTTPException:
        # HTTPException은 그대로 전달
        raise

    except Exception as e:
        # 롤백
        await db.rollback()

        logger.error(f"File upload failed: {e}")

        # 업로드된 파일 삭제
        for file_id in file_ids:
            try:
                for path in settings.upload_dir.glob(f"{file_id}*"):
                    path.unlink()
            except Exception as cleanup_error:
                logger.error(f"Failed to cleanup file {file_id}: {cleanup_error}")

        raise HTTPException(
            status_code=500,
            detail=f"파일 업로드 중 오류가 발생했습니다: {str(e)}"
        )

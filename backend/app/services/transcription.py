"""
전사 서비스

비즈니스 로직을 처리하는 서비스 레이어
"""
from typing import Optional, Dict, Any, List
from pathlib import Path
import logging

from app.core.models.manager import model_manager
from app.core.processors.diarization import DiarizationProcessor
from app.core.processors.formatters import get_writer
from app.db.models import Job, UploadedFile, Result
from app.db.session import AsyncSession
from app.schemas.transcription import TranscriptionRequest, JobStatus
from sqlalchemy import select
from sqlalchemy.orm import selectinload

logger = logging.getLogger(__name__)


class TranscriptionService:
    """
    전사 서비스

    ASR 모델을 사용하여 오디오 파일을 전사하고
    결과를 데이터베이스에 저장합니다.
    """

    def __init__(self, db: AsyncSession):
        """
        Args:
            db: 비동기 데이터베이스 세션
        """
        self.db = db

    async def create_job(
        self,
        request: TranscriptionRequest,
        file_ids: List[str]
    ) -> Job:
        """
        전사 작업 생성

        Args:
            request: 전사 요청
            file_ids: 업로드된 파일 ID 리스트

        Returns:
            생성된 Job 인스턴스
        """
        try:
            # 파일 존재 확인
            stmt = select(UploadedFile).where(UploadedFile.id.in_(file_ids))
            result = await self.db.execute(stmt)
            files = result.scalars().all()

            if len(files) != len(file_ids):
                raise ValueError(f"Some files not found: requested {len(file_ids)}, found {len(files)}")

            # Job 생성
            job = Job(
                status=JobStatus.PENDING,
                model_type=request.model_type,
                model_size=request.model_size,
                language=request.language,
                device=request.device,
                parameters=request.parameters.model_dump() if request.parameters else {},
                diarization_enabled=request.diarization.enabled if request.diarization else False,
                output_formats=request.output_formats,
            )

            # 파일 연결
            for file in files:
                job.files.append(file)

            self.db.add(job)
            await self.db.commit()
            await self.db.refresh(job)

            logger.info(f"Created job {job.id} for {len(files)} files")
            return job

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to create job: {e}")
            raise

    async def process_transcription(
        self,
        job_id: str,
        hf_token: Optional[str] = None
    ) -> None:
        """
        전사 작업 처리 (백그라운드 태스크)

        Args:
            job_id: 작업 ID
            hf_token: HuggingFace 토큰 (스피커 분별용)
        """
        try:
            # Job 조회
            stmt = select(Job).where(Job.id == job_id).options(
                selectinload(Job.files)
            )
            result = await self.db.execute(stmt)
            job = result.scalar_one_or_none()

            if not job:
                raise ValueError(f"Job {job_id} not found")

            # 상태 업데이트: PROCESSING
            job.status = JobStatus.PROCESSING
            await self.db.commit()

            logger.info(f"Starting transcription for job {job_id}")

            # 모델 가져오기
            model = model_manager.get_model(
                model_type=job.model_type,
                model_size=job.model_size,
                device=job.device,
                compute_type=job.parameters.get("compute_type", "float16")
            )

            # 각 파일 처리
            total_files = len(job.files)
            for idx, file in enumerate(job.files, 1):
                logger.info(f"Processing file {idx}/{total_files}: {file.filename}")

                # 진행률 업데이트
                job.progress = int((idx - 1) / total_files * 100)
                await self.db.commit()

                try:
                    # 전사 수행
                    transcription_result = model.transcribe(
                        audio_path=file.file_path,
                        language=job.language,
                        params=job.parameters
                    )

                    # 스피커 분별 (옵션)
                    if job.diarization_enabled:
                        logger.info(f"Running diarization for file {file.filename}")
                        diarization_processor = DiarizationProcessor(hf_token=hf_token)
                        transcription_result = diarization_processor.process(
                            audio_path=file.file_path,
                            transcription_result=transcription_result,
                            min_speakers=2,  # TODO: 파라미터로 받기
                            max_speakers=15
                        )
                        diarization_processor.unload_model()

                    # 결과 저장 (여러 포맷)
                    output_paths = await self._save_results(
                        job=job,
                        file=file,
                        transcription_result=transcription_result
                    )

                    # Result 레코드 생성
                    result_record = Result(
                        job_id=job.id,
                        file_id=file.id,
                        segments_count=len(transcription_result.get("segments", [])),
                        speakers_count=self._count_speakers(transcription_result),
                        output_paths=output_paths
                    )
                    self.db.add(result_record)

                except Exception as e:
                    logger.error(f"Failed to process file {file.filename}: {e}")
                    job.status = JobStatus.FAILED
                    job.error_message = str(e)
                    await self.db.commit()
                    raise

            # 완료
            job.status = JobStatus.COMPLETED
            job.progress = 100
            await self.db.commit()

            logger.info(f"Job {job_id} completed successfully")

        except Exception as e:
            logger.error(f"Job {job_id} failed: {e}")
            # 이미 실패 처리되지 않았다면
            if job and job.status != JobStatus.FAILED:
                job.status = JobStatus.FAILED
                job.error_message = str(e)
                await self.db.commit()
            raise

    async def _save_results(
        self,
        job: Job,
        file: UploadedFile,
        transcription_result: Dict[str, Any]
    ) -> Dict[str, str]:
        """
        전사 결과를 여러 포맷으로 저장

        Args:
            job: Job 인스턴스
            file: UploadedFile 인스턴스
            transcription_result: 전사 결과

        Returns:
            포맷별 출력 경로 딕셔너리
        """
        from app.config import settings

        output_paths = {}

        # 출력 디렉토리 생성
        output_dir = Path(settings.results_dir) / str(job.id)
        output_dir.mkdir(parents=True, exist_ok=True)

        # 각 포맷별 저장
        for format_name in job.output_formats:
            try:
                writer = get_writer(format_name, str(output_dir))
                output_path = writer(
                    result=transcription_result,
                    audio_path=file.filename,
                    options={}  # TODO: 옵션 파라미터 추가
                )
                output_paths[format_name] = output_path
                logger.info(f"Saved {format_name} result: {output_path}")

            except Exception as e:
                logger.error(f"Failed to save {format_name} format: {e}")
                # 한 포맷 실패해도 계속 진행

        return output_paths

    def _count_speakers(self, transcription_result: Dict[str, Any]) -> Optional[int]:
        """
        전사 결과에서 화자 수 계산

        Args:
            transcription_result: 전사 결과

        Returns:
            화자 수 (화자 정보 없으면 None)
        """
        segments = transcription_result.get("segments", [])
        speakers = set()

        for segment in segments:
            if "speaker" in segment:
                speakers.add(segment["speaker"])

        return len(speakers) if speakers else None

    async def get_job(self, job_id: str) -> Optional[Job]:
        """
        작업 조회

        Args:
            job_id: 작업 ID

        Returns:
            Job 인스턴스 또는 None
        """
        stmt = select(Job).where(Job.id == job_id).options(
            selectinload(Job.files),
            selectinload(Job.results)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_result_path(
        self,
        job_id: str,
        format_name: str
    ) -> Optional[str]:
        """
        특정 포맷의 결과 파일 경로 조회

        Args:
            job_id: 작업 ID
            format_name: 포맷 이름 (vtt, srt, json, txt, tsv)

        Returns:
            파일 경로 또는 None
        """
        job = await self.get_job(job_id)

        if not job or not job.results:
            return None

        # 첫 번째 결과의 output_paths에서 해당 포맷 찾기
        # TODO: 여러 파일 처리 시 개선 필요
        for result in job.results:
            if format_name in result.output_paths:
                return result.output_paths[format_name]

        return None

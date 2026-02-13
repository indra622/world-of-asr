"""
SQLAlchemy 데이터베이스 모델
"""
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, DateTime, Enum, JSON, Text, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base
import enum


class JobStatus(str, enum.Enum):
    """작업 상태"""
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Job(Base):
    """전사 작업 테이블"""
    __tablename__ = "jobs"

    id = Column(String, primary_key=True, index=True)
    model_type = Column(String, nullable=False)
    model_size = Column(String, nullable=False)
    language = Column(String)
    device = Column(String, nullable=False)
    parameters = Column(JSON, nullable=False)
    diarization_config = Column(JSON)
    output_formats = Column(JSON, nullable=False)

    status = Column(Enum(JobStatus), default=JobStatus.QUEUED, index=True)
    progress = Column(Integer, default=0)
    current_file = Column(String)
    total_files = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    error_message = Column(Text)

    # 관계
    uploaded_files = relationship("UploadedFile", back_populates="job", cascade="all, delete-orphan")
    results = relationship("Result", back_populates="job", cascade="all, delete-orphan")


class UploadedFile(Base):
    """업로드된 파일 테이블"""
    __tablename__ = "uploaded_files"

    id = Column(String, primary_key=True, index=True)
    job_id = Column(String, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=True, index=True)
    original_filename = Column(String, nullable=False)
    storage_path = Column(String, nullable=False)
    file_size = Column(Integer)
    duration = Column(Float)
    mime_type = Column(String)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    # 관계
    job = relationship("Job", back_populates="uploaded_files")
    result = relationship("Result", uselist=False, back_populates="file")


class Result(Base):
    """전사 결과 테이블"""
    __tablename__ = "results"

    id = Column(String, primary_key=True, index=True)
    job_id = Column(String, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    file_id = Column(String, ForeignKey("uploaded_files.id", ondelete="CASCADE"), nullable=False)

    segment_count = Column(Integer)
    has_diarization = Column(Boolean, default=False)
    speaker_count = Column(Integer)

    json_path = Column(String)
    vtt_path = Column(String)
    srt_path = Column(String)
    txt_path = Column(String)
    tsv_path = Column(String)

    created_at = Column(DateTime, default=datetime.utcnow)

    # 관계
    job = relationship("Job", back_populates="results")
    file = relationship("UploadedFile", back_populates="result")

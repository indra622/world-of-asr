"""
애플리케이션 설정 관리
Pydantic Settings를 사용한 환경 변수 관리
"""
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path


class Settings(BaseSettings):
    """애플리케이션 설정"""

    # 서버 설정
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = False

    # 데이터베이스
    database_url: str = "sqlite+aiosqlite:///./storage/woa.db"

    # 스토리지 경로
    upload_dir: Path = Path("./storage/uploads")
    result_dir: Path = Path("./storage/results")
    temp_dir: Path = Path("./storage/temp")

    # Hugging Face
    hf_token: str = ""

    # Docker (FastConformer)
    container_id: str = ""
    ip_addr: str = ""

    # 보안
    secret_key: str = "dev-secret-key-change-in-production"
    allowed_origins: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
    ]

    # 파일 업로드 제한
    max_file_size: int = 524288000  # 500MB
    max_files: int = 10

    # GPU 설정
    default_device: str = "cuda"
    max_concurrent_jobs: int = 3

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    def create_directories(self):
        """필요한 디렉토리 생성"""
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.result_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)


# 전역 설정 인스턴스
settings = Settings()

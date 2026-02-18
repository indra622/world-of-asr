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
    results_dir: Path = Path("./storage/results")
    temp_dir: Path = Path("./storage/temp")

    # Hugging Face (스피커 분별용)
    huggingface_token: str = ""

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
    # 업로드 허용 목록
    allowed_upload_exts: List[str] = [
        ".wav",
        ".mp3",
        ".m4a",
        ".flac",
        ".ogg",
        ".mp4",
        ".mkv",
    ]
    allowed_mime_prefixes: List[str] = [
        "audio/",
        "video/",
    ]

    # GPU 설정
    default_device: str = "cuda"
    max_concurrent_jobs: int = 3

    # 외부 ASR 제공자 설정
    enable_google: bool = False
    google_project_id: str = ""
    google_location: str = "global"
    google_api_key: str = ""  # 또는 서비스 계정 JSON 경로 사용

    enable_qwen: bool = False
    qwen_api_key: str = ""
    qwen_endpoint: str = ""

    # Hugging Face AutoModel ASR
    enable_hf_auto_asr: bool = True
    hf_auto_default_model: str = "openai/whisper-small"

    # NVIDIA providers
    enable_nemo: bool = False
    nemo_container_id: str = ""  # optional alternative to FastConformer container
    enable_triton: bool = False
    triton_url: str = "http://localhost:8000"  # example
    enable_riva: bool = False
    riva_url: str = ""  # riva server endpoint

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    def create_directories(self):
        """필요한 디렉토리 생성"""
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)


# 전역 설정 인스턴스
settings = Settings()

"""
FastAPI 메인 애플리케이션
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.config import settings
from app.db.session import init_db, AsyncSessionLocal
from sqlalchemy import text

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 라이프사이클 관리"""
    # Startup
    logger.info("Starting World-of-ASR Backend...")

    # 필요한 디렉토리 생성
    settings.create_directories()
    logger.info("Storage directories created")

    # 데이터베이스 초기화
    await init_db()
    logger.info("Database initialized")

    yield

    # Shutdown
    logger.info("Shutting down World-of-ASR Backend...")


# FastAPI 앱 생성
app = FastAPI(
    title="World-of-ASR API",
    description="FastAPI backend for ASR transcription service",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS 미들웨어
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {
        "message": "World-of-ASR API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """헬스 체크 엔드포인트"""
    # DB 연결 확인 간단 쿼리
    try:
        async with AsyncSessionLocal() as db:
            await db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as exc:
        logger.warning("Health check DB query failed: %s", exc)
        db_status = "unavailable"

    from app.config import settings as cfg

    return {
        "status": "healthy" if db_status == "connected" else "degraded",
        "database": db_status,
        "providers": {
            "google_stt_enabled": cfg.enable_google,
            "qwen_asr_enabled": cfg.enable_qwen,
        },
    }


# API 라우터 등록
from app.api.v1.router import api_router
app.include_router(api_router, prefix="/api/v1")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
    )

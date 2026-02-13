"""
API v1 라우터 통합
"""
from fastapi import APIRouter

from app.api.v1.upload import router as upload_router
from app.api.v1.transcribe import router as transcribe_router
from app.api.v1.results import router as results_router

api_router = APIRouter()

# 라우터 등록
api_router.include_router(upload_router, tags=["upload"])
api_router.include_router(transcribe_router, tags=["transcription"])
api_router.include_router(results_router, tags=["results"])

# 추후 추가될 라우터들
# api_router.include_router(websocket_router, tags=["websocket"])

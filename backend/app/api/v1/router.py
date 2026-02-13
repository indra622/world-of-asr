"""
API v1 라우터 통합
"""
from fastapi import APIRouter

from app.api.v1.upload import router as upload_router

api_router = APIRouter()

# 라우터 등록
api_router.include_router(upload_router, tags=["upload"])

# 추후 추가될 라우터들
# api_router.include_router(transcribe_router, tags=["transcribe"])
# api_router.include_router(jobs_router, tags=["jobs"])
# api_router.include_router(results_router, tags=["results"])
# api_router.include_router(websocket_router, tags=["websocket"])

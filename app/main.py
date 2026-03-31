"""
FastAPI 앱 진입점.
- CORS 설정으로 프론트엔드 연동 가능
- Phase 1: 산출물 API (/api/concepts, /api/learning-points, /api/quizzes, /api/learning-guides)
"""

import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router as api_router
from app.state import cleanup_expired_jobs


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: 주기적 job cleanup 시작. Shutdown: cleanup 중단."""
    async def periodic_cleanup():
        while True:
            await asyncio.sleep(600)  # 10분마다
            await cleanup_expired_jobs()

    task = asyncio.create_task(periodic_cleanup())
    yield
    task.cancel()


app = FastAPI(
    title="tell-me-lion API",
    description="강의 산출물(핵심 개념·학습 포인트·퀴즈·학습 가이드) 조회 API",
    version="0.1.0",
    lifespan=lifespan,
)

# ALLOWED_ORIGINS 환경변수: 쉼표로 구분된 URL 목록
# 예) https://tell-me-lion.vercel.app,http://localhost:5173
_extra = os.getenv("ALLOWED_ORIGINS", "")
_origins = [o.strip() for o in _extra.split(",") if o.strip()]
CORS_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"] + _origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Accept"],
)

app.include_router(api_router)


@app.get("/")
def root():
    """API 루트."""
    return {"service": "tell-me-lion", "docs": "/docs"}


@app.get("/health")
def health():
    """헬스 체크 (연동·배포 확인용)."""
    from pipeline.paths import DATA_RAW
    data_ok = DATA_RAW.is_dir()
    return {"status": "ok" if data_ok else "degraded", "data_dir": data_ok}

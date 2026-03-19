"""
FastAPI 앱 진입점.
- CORS 설정으로 프론트엔드 연동 가능
- Phase 1: 산출물 API (/api/concepts, /api/learning-points, /api/quizzes, /api/learning-guides)
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router as api_router

app = FastAPI(
    title="tell-me-lion API",
    description="강의 산출물(핵심 개념·학습 포인트·퀴즈·학습 가이드) 조회 API",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/")
def root():
    """API 루트."""
    return {"service": "tell-me-lion", "docs": "/docs"}


@app.get("/health")
def health():
    """헬스 체크 (연동·배포 확인용)."""
    return {"status": "ok"}

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


def _cleanup_orphaned_markers() -> None:
    """서버 시작 시 고아 마커 파일 및 중간 산출물 정리.

    파이프라인 실행 중 서버가 비정상 종료(OOM, 배포 재시작 등)되면
    마커 파일 및 중간 파일들이 디스크에 남는다.
    마커 파일은 있지만 완료 결과(ep_concepts + ep_learning_points + quizzes_validated 3개 모두)가 없는 경우 →
    해당 lecture_id의 모든 중간 파일 삭제 → idle로 복구 → 재분석 가능.
    """
    import logging
    from pipeline.paths import (
        DATA_PHASE1_SESSIONS, DATA_PHASE2_SENTENCES, DATA_PHASE3_CHUNKS,
        DATA_PHASE4_PROPOSITIONS, DATA_PHASE5_FACTS,
        DATA_EP_CONCEPTS, DATA_EP_LEARNING_POINTS, DATA_BLUEPRINTS, DATA_QUIZZES_RAW, DATA_QUIZZES_VALIDATED,
    )
    from app.loaders.catalog import invalidate_catalog_cache

    logger = logging.getLogger(__name__)

    _INTERMEDIATE_DIRS = [
        DATA_PHASE1_SESSIONS, DATA_PHASE2_SENTENCES, DATA_PHASE3_CHUNKS,
        DATA_PHASE4_PROPOSITIONS, DATA_PHASE5_FACTS,
        DATA_EP_CONCEPTS, DATA_EP_LEARNING_POINTS, DATA_BLUEPRINTS, DATA_QUIZZES_RAW, DATA_QUIZZES_VALIDATED,
    ]

    def _has_any(directory, lid):
        """디렉터리에서 lecture_id에 매칭되는 파일이 있는지 부분 매칭으로 확인."""
        exact = directory / f"{lid}.jsonl"
        if exact.exists() and exact.stat().st_size > 0:
            return True
        date_part = lid.split("_")[0] if "_" in lid else lid
        return any(p.stat().st_size > 0 for p in directory.glob(f"*{date_part}*.jsonl"))

    removed = 0
    if not DATA_PHASE1_SESSIONS.exists():
        return
    for marker in DATA_PHASE1_SESSIONS.glob("*.jsonl"):
        lecture_id = marker.stem
        if (
            _has_any(DATA_EP_CONCEPTS, lecture_id)
            and _has_any(DATA_EP_LEARNING_POINTS, lecture_id)
            and _has_any(DATA_QUIZZES_VALIDATED, lecture_id)
        ):
            continue  # 완료된 강의는 건드리지 않음
        # phase5까지 도달한 파일이 있으면 중간 단계(phase1~3)만 정리, phase5 보존
        has_phase5 = _has_any(DATA_PHASE5_FACTS, lecture_id)
        for d in _INTERMEDIATE_DIRS:
            if has_phase5 and d in (DATA_PHASE5_FACTS, DATA_EP_CONCEPTS, DATA_EP_LEARNING_POINTS, DATA_BLUEPRINTS):
                continue  # Phase 5 이후 파일은 보존
            f = d / f"{lecture_id}.jsonl"
            if f.exists():
                f.unlink()
                logger.warning("고아 중간 파일 삭제: %s/%s", d.name, f.name)
                removed += 1
    if removed:
        invalidate_catalog_cache()
        logger.info("고아 파일 %d개 정리 완료 (서버 재시작 감지)", removed)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: 고아 마커 정리 + 주기적 job cleanup 시작. Shutdown: cleanup 중단."""
    _cleanup_orphaned_markers()

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

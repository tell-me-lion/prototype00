"""
인메모리 Job 상태 관리 (MVP).
서버 재시작 시 초기화됨 — MVP 수준에서 허용.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime

from app.schemas.models import ProcessingStatus

# Job 만료 시간 (초) — 완료 후 이 시간이 지나면 자동 정리
JOB_TTL_SECONDS = 3600  # 1시간


@dataclass
class JobState:
    status: ProcessingStatus = ProcessingStatus.idle
    steps: list[dict] = field(default_factory=list)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str | None = None


# 인메모리 저장소
lecture_jobs: dict[str, JobState] = {}   # lecture_id → JobState
week_jobs: dict[int, JobState] = {}      # week → JobState

# 동시 접근 보호
_lock = asyncio.Lock()


async def get_lecture_job(lecture_id: str) -> JobState | None:
    async with _lock:
        return lecture_jobs.get(lecture_id)


async def set_lecture_job(lecture_id: str, job: JobState) -> None:
    async with _lock:
        lecture_jobs[lecture_id] = job


async def get_week_job(week: int) -> JobState | None:
    async with _lock:
        return week_jobs.get(week)


async def set_week_job(week: int, job: JobState) -> None:
    async with _lock:
        week_jobs[week] = job


async def cleanup_expired_jobs() -> int:
    """완료 후 TTL이 지난 Job을 정리한다. 정리된 수를 반환."""
    now = datetime.now()
    removed = 0
    async with _lock:
        expired_lectures = [
            k for k, v in lecture_jobs.items()
            if v.completed_at and (now - v.completed_at).total_seconds() > JOB_TTL_SECONDS
        ]
        for k in expired_lectures:
            del lecture_jobs[k]
            removed += 1

        expired_weeks = [
            k for k, v in week_jobs.items()
            if v.completed_at and (now - v.completed_at).total_seconds() > JOB_TTL_SECONDS
        ]
        for k in expired_weeks:
            del week_jobs[k]
            removed += 1
    return removed

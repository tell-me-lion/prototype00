"""
인메모리 Job 상태 관리 (MVP).
서버 재시작 시 초기화됨 — MVP 수준에서 허용.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone

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


async def clear_week_job(week: int) -> None:
    """stale 상태의 주차 Job을 제거한다."""
    async with _lock:
        week_jobs.pop(week, None)


async def start_lecture_job_if_idle(
    lecture_id: str, new_job: JobState, *, force: bool = False,
) -> tuple[bool, JobState | None]:
    """원자적으로 강의 Job 상태를 확인하고 시작한다.

    Returns:
        (True, None) — 성공적으로 시작됨
        (False, existing_job) — 이미 처리 중이거나 완료 상태
    """
    async with _lock:
        existing = lecture_jobs.get(lecture_id)
        if existing and existing.status == ProcessingStatus.processing:
            return False, existing
        if existing and existing.status == ProcessingStatus.completed and not force:
            return False, existing
        lecture_jobs[lecture_id] = new_job
        return True, None


async def start_week_job_if_idle(
    week: int, new_job: JobState, *, force: bool = False,
) -> tuple[bool, JobState | None]:
    """원자적으로 주차 Job 상태를 확인하고 시작한다."""
    async with _lock:
        existing = week_jobs.get(week)
        if existing and existing.status == ProcessingStatus.processing:
            return False, existing
        if existing and existing.status == ProcessingStatus.completed and not force:
            return False, existing
        week_jobs[week] = new_job
        return True, None


async def cleanup_expired_jobs() -> int:
    """완료 후 TTL이 지난 Job을 정리한다. 정리된 수를 반환."""
    now = datetime.now(tz=timezone.utc)
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

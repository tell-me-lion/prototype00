"""
Job 상태 관리 — 인메모리 + JSON 파일 영속화.
서버 재시작 시 data/.jobs/ 디렉터리에서 복원한다.
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from app.schemas.models import ProcessingStatus

logger = logging.getLogger(__name__)

# Job 만료 시간 (초) — 완료 후 이 시간이 지나면 자동 정리
JOB_TTL_SECONDS = 3600  # 1시간

# 영속화 디렉터리
_JOBS_DIR = Path(__file__).resolve().parent.parent / "data" / ".jobs"


@dataclass
class JobState:
    status: ProcessingStatus = ProcessingStatus.idle
    steps: list[dict] = field(default_factory=list)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str | None = None


def _job_to_dict(job: JobState) -> dict:
    return {
        "status": job.status.value,
        "steps": job.steps,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "error_message": job.error_message,
    }


def _dict_to_job(d: dict) -> JobState:
    return JobState(
        status=ProcessingStatus(d["status"]),
        steps=d.get("steps", []),
        started_at=datetime.fromisoformat(d["started_at"]) if d.get("started_at") else None,
        completed_at=datetime.fromisoformat(d["completed_at"]) if d.get("completed_at") else None,
        error_message=d.get("error_message"),
    )


def _persist_lecture_job(lecture_id: str, job: JobState) -> None:
    """강의 Job 상태를 JSON 파일로 저장."""
    _JOBS_DIR.mkdir(parents=True, exist_ok=True)
    path = _JOBS_DIR / f"lecture_{lecture_id}.json"
    path.write_text(json.dumps(_job_to_dict(job), ensure_ascii=False), encoding="utf-8")


def _persist_week_job(week: int, job: JobState) -> None:
    """주차 Job 상태를 JSON 파일로 저장."""
    _JOBS_DIR.mkdir(parents=True, exist_ok=True)
    path = _JOBS_DIR / f"week_{week:02d}.json"
    path.write_text(json.dumps(_job_to_dict(job), ensure_ascii=False), encoding="utf-8")


def _delete_job_file(prefix: str) -> None:
    path = _JOBS_DIR / f"{prefix}.json"
    if path.exists():
        path.unlink()


def load_persisted_jobs() -> tuple[dict[str, JobState], dict[int, JobState]]:
    """서버 시작 시 영속화된 Job 상태를 복원한다."""
    lectures: dict[str, JobState] = {}
    weeks: dict[int, JobState] = {}
    if not _JOBS_DIR.exists():
        return lectures, weeks
    for f in _JOBS_DIR.glob("*.json"):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
            job = _dict_to_job(d)
            # processing/queued 상태였던 건 서버 재시작으로 중단됨 → error로 전환
            if job.status in (ProcessingStatus.processing, ProcessingStatus.queued):
                job.status = ProcessingStatus.error
                job.error_message = "서버 재시작으로 처리가 중단되었습니다. 다시 시도해 주세요."
                job.completed_at = datetime.now(tz=timezone.utc)
            if f.stem.startswith("lecture_"):
                lid = f.stem[len("lecture_"):]
                lectures[lid] = job
            elif f.stem.startswith("week_"):
                week_num = int(f.stem[len("week_"):])
                weeks[week_num] = job
        except Exception as e:
            logger.warning("Job 파일 복원 실패 (%s): %s", f.name, e)
    logger.info("영속화된 Job 복원: 강의 %d건, 주차 %d건", len(lectures), len(weeks))
    return lectures, weeks


# 인메모리 저장소
lecture_jobs: dict[str, JobState] = {}   # lecture_id → JobState
week_jobs: dict[int, JobState] = {}      # week → JobState

# 동시 접근 보호
_lock = asyncio.Lock()


def init_jobs() -> None:
    """서버 시작 시 호출 — 영속화된 Job 상태를 인메모리로 복원."""
    persisted_lectures, persisted_weeks = load_persisted_jobs()
    lecture_jobs.update(persisted_lectures)
    week_jobs.update(persisted_weeks)


async def get_lecture_job(lecture_id: str) -> JobState | None:
    async with _lock:
        return lecture_jobs.get(lecture_id)


async def set_lecture_job(lecture_id: str, job: JobState) -> None:
    async with _lock:
        lecture_jobs[lecture_id] = job
        _persist_lecture_job(lecture_id, job)


async def get_week_job(week: int) -> JobState | None:
    async with _lock:
        return week_jobs.get(week)


async def set_week_job(week: int, job: JobState) -> None:
    async with _lock:
        week_jobs[week] = job
        _persist_week_job(week, job)


async def clear_week_job(week: int) -> None:
    """stale 상태의 주차 Job을 제거한다."""
    async with _lock:
        week_jobs.pop(week, None)
        _delete_job_file(f"week_{week:02d}")


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
        if existing and existing.status in (ProcessingStatus.processing, ProcessingStatus.queued):
            return False, existing
        if existing and existing.status == ProcessingStatus.completed and not force:
            return False, existing
        lecture_jobs[lecture_id] = new_job
        _persist_lecture_job(lecture_id, new_job)
        return True, None


async def start_week_job_if_idle(
    week: int, new_job: JobState, *, force: bool = False,
) -> tuple[bool, JobState | None]:
    """원자적으로 주차 Job 상태를 확인하고 시작한다."""
    async with _lock:
        existing = week_jobs.get(week)
        if existing and existing.status in (ProcessingStatus.processing, ProcessingStatus.queued):
            return False, existing
        if existing and existing.status == ProcessingStatus.completed and not force:
            return False, existing
        week_jobs[week] = new_job
        _persist_week_job(week, new_job)
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
            _delete_job_file(f"lecture_{k}")
            removed += 1

        expired_weeks = [
            k for k, v in week_jobs.items()
            if v.completed_at and (now - v.completed_at).total_seconds() > JOB_TTL_SECONDS
        ]
        for k in expired_weeks:
            del week_jobs[k]
            _delete_job_file(f"week_{k:02d}")
            removed += 1
    return removed

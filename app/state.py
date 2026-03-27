"""
인메모리 Job 상태 관리 (MVP).
서버 재시작 시 초기화됨 — MVP 수준에서 허용.
"""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class JobState:
    status: str = "idle"  # idle | processing | completed | error
    steps: list[dict] = field(default_factory=list)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str | None = None


# 인메모리 저장소
lecture_jobs: dict[str, JobState] = {}   # lecture_id → JobState
week_jobs: dict[int, JobState] = {}      # week → JobState

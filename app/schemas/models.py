"""
ep_concepts, quizzes_validated, learning_guides 스키마에 맞는 Pydantic 모델.
ARCHITECTURE.md §2.3, §2.3.1 기준.
"""

from datetime import date, datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


# --- ep_concepts 형식 (핵심 개념·학습 포인트 공통) ---


class Concept(BaseModel):
    """핵심 개념 (ep_concepts)."""

    week: int | None = None
    lecture_id: str
    concept: str
    importance: float
    evidence_facts: list[str] = Field(default_factory=list)
    meta: dict[str, Any] = Field(default_factory=dict)


class LearningPoint(BaseModel):
    """학습 포인트 (ep_concepts 동일 형식)."""

    week: int | None = None
    lecture_id: str
    concept: str
    importance: float
    evidence_facts: list[str] = Field(default_factory=list)
    meta: dict[str, Any] = Field(default_factory=dict)


# --- quizzes_validated 형식 ---


class Quiz(BaseModel):
    """퀴즈 (quizzes_validated)."""

    quiz_id: str
    status: Literal["pass", "fail"] = "pass"
    type: Literal["mcq", "short", "fill", "code"]
    question: str
    options: list[str] | None = None
    answer: str | list[str] | None = None  # short/fill은 str, mcq는 보통 str
    explanation: str | None = None
    code: str | None = None
    validation_log: dict[str, Any] = Field(default_factory=dict)
    meta: dict[str, Any] = Field(default_factory=dict)


# --- learning_guides 형식 ---


class LearningGuide(BaseModel):
    """주차별 학습 가이드·핵심 요약 (learning_guides)."""

    week: int
    summary: str
    key_concepts: list[str] = Field(default_factory=list)
    meta: dict[str, Any] = Field(default_factory=dict)


class LectureOutputs(BaseModel):
    """단일 강의 입력 → 산출물 묶음."""

    concepts: list[Concept] = Field(default_factory=list)
    learning_points: list[LearningPoint] = Field(default_factory=list)
    quizzes: list[Quiz] = Field(default_factory=list)


class WeeklyOutputs(BaseModel):
    """1주일치 입력 → 주차별 가이드·요약 묶음."""

    guides: list[LearningGuide] = Field(default_factory=list)


# --- 강의 카탈로그 (대시보드 UX) ---


class ProcessingStatus(str, Enum):
    """파이프라인 처리 상태."""

    idle = "idle"
    processing = "processing"
    completed = "completed"
    error = "error"


class LectureResultSummary(BaseModel):
    """처리 완료 시 결과 요약."""

    concept_count: int = 0
    learning_point_count: int = 0
    quiz_count: int = 0


class LectureCatalog(BaseModel):
    """강의 카탈로그 항목."""

    lecture_id: str
    date: date
    day_of_week: str
    week: int
    course_code: str
    course_name: str
    status: ProcessingStatus = ProcessingStatus.idle
    result_summary: LectureResultSummary | None = None
    meta: dict[str, Any] = Field(default_factory=dict)


class WeekSummary(BaseModel):
    """주차 요약."""

    week: int
    lecture_count: int
    completed_count: int
    date_range: str
    status: ProcessingStatus
    lectures: list[LectureCatalog] = Field(default_factory=list)


# --- 처리 트리거 & 상태 관리 ---


class ProcessingStep(BaseModel):
    """처리 단계 하나."""

    name: str    # "영상 분석", "텍스트 추출", "AI 분석"
    status: Literal["pending", "running", "done"]


class ProcessingStatusResponse(BaseModel):
    """처리 상태 조회 응답."""

    lecture_id: str | None = None
    week: int | None = None
    status: ProcessingStatus
    steps: list[ProcessingStep] = Field(default_factory=list)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str | None = None


class ProcessTriggerResponse(BaseModel):
    """처리 시작 응답."""

    lecture_id: str | None = None
    week: int | None = None
    status: ProcessingStatus
    started_at: datetime

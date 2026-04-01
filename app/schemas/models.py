"""
파이프라인 출력 스키마에 맞는 Pydantic 모델.
pipeline/ep/schema.py, pipeline/quiz_generation/schema.py 기준.
"""

from datetime import date, datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


# --- ep_concepts 형식 (파이프라인 ConceptDocument 기준) ---


class Concept(BaseModel):
    """핵심 개념 (ep_concepts). pipeline/ep/schema.py ConceptDocument 기준."""

    concept_id: str
    concept: str
    definition: str = ""
    related_concepts: list[str] = Field(default_factory=list)
    source_chunk_ids: list[str] = Field(default_factory=list)
    week: int
    lecture_id: str
    importance: float


class LearningPoint(BaseModel):
    """학습 포인트 (ep_learning_points). Concept과 동일 구조."""

    concept_id: str
    concept: str
    definition: str = ""
    related_concepts: list[str] = Field(default_factory=list)
    source_chunk_ids: list[str] = Field(default_factory=list)
    week: int
    lecture_id: str
    importance: float


# --- quizzes 형식 (파이프라인 QuizDocument 기준) ---


class Choice(BaseModel):
    """객관식 선지."""

    id: int
    text: str
    is_answer: bool


class QuizMeta(BaseModel):
    """퀴즈 생성 메타데이터."""

    attempt_count: int = 0
    llm_model: str = ""
    used_fact_ids: list[str] = Field(default_factory=list)


class Quiz(BaseModel):
    """퀴즈. pipeline/quiz_generation/schema.py QuizDocument 기준."""

    quiz_id: str
    blueprint_id: str = ""
    lecture_id: str = ""
    week: int = 0
    question_type: str  # "mcq_definition"|"mcq_misconception"|"fill_blank"|"ox_quiz"|"code_execution"
    question_format: str = ""
    difficulty: str = "중"  # "상"|"중"|"하"
    question: str
    choices: list[Choice] | None = None
    answers: str | None = None
    code_template: str | None = None
    source_text: str = ""
    explanation: str = ""
    meta: QuizMeta = Field(default_factory=QuizMeta)


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
    partial = "partial"       # 중간 단계까지 완료, 재개 가능
    queued = "queued"         # 대기 중 (다른 강의 처리 완료 후 시작)
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
    guide_status: ProcessingStatus = ProcessingStatus.idle
    lectures: list[LectureCatalog] = Field(default_factory=list)


# --- 처리 트리거 & 상태 관리 ---


class ProcessingStep(BaseModel):
    """처리 단계 하나."""

    name: str    # "영상 분석", "텍스트 추출", "AI 분석"
    status: Literal["pending", "running", "done"]
    detail: str | None = None  # 세부 진행 정보 (예: "15/42 청크 | 명제 38개")


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

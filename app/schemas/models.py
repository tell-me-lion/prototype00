"""
ep_concepts, quizzes_validated, learning_guides 스키마에 맞는 Pydantic 모델.
ARCHITECTURE.md §2.3, §2.3.1 기준.
"""

from typing import Any

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
    status: str = "pass"  # pass | fail
    type: str  # mcq | short | fill | code
    question: str
    options: list[str] | None = None
    answer: str | list[str] | None = None  # short/fill은 str, mcq는 보통 str
    explanation: str | None = None
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

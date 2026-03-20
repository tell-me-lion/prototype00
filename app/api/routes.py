"""
산출물 조회 API.
- 단일 강의: 핵심 개념, 학습 포인트, 퀴즈
- 1주일치: 주차별 학습 가이드·핵심 요약
"""

from fastapi import APIRouter, HTTPException, File, UploadFile

from app.loaders.dummy import load_concepts, load_learning_guides, load_learning_points, load_quizzes
from app.schemas import (
    Concept,
    LearningGuide,
    LearningPoint,
    Quiz,
    LectureOutputs,
    WeeklyOutputs,
)

router = APIRouter(prefix="/api", tags=["산출물"])


# --- 단일 강의 산출물 (1.3) ---


@router.get("/concepts", response_model=list[Concept])
def get_concepts():
    """핵심 개념 목록 (단일 강의 입력 대응)."""
    raw = load_concepts()
    return [Concept.model_validate(d) for d in raw]


@router.get("/learning-points", response_model=list[LearningPoint])
def get_learning_points():
    """학습 포인트 목록 (단일 강의 입력 대응)."""
    raw = load_learning_points()
    return [LearningPoint.model_validate(d) for d in raw]


@router.get("/quizzes", response_model=list[Quiz])
def get_quizzes():
    """퀴즈 목록 (단일 강의 입력 대응)."""
    raw = load_quizzes()
    return [Quiz.model_validate(d) for d in raw]


# 업로드 기반 단일 강의 입력 → 산출물 묶음


@router.post("/lecture-outputs", response_model=LectureOutputs)
async def create_lecture_outputs(file: UploadFile = File(...)):
    """
    강의 스크립트(.txt)를 업로드하면
    - 핵심 개념
    - 학습 포인트
    - 퀴즈
    묶음을 반환한다.

    현재는 파이프라인이 비어 있어, 업로드 파일 내용은 사용하지 않고
    data/dummy/ 의 더미 데이터를 그대로 반환한다.
    """

    # TODO: 파이프라인 연동 시 file 내용을 기반으로 산출물 생성
    concepts_raw = load_concepts()
    learning_points_raw = load_learning_points()
    quizzes_raw = load_quizzes()

    return LectureOutputs(
        concepts=[Concept.model_validate(d) for d in concepts_raw],
        learning_points=[LearningPoint.model_validate(d) for d in learning_points_raw],
        quizzes=[Quiz.model_validate(d) for d in quizzes_raw],
    )


# --- 1주일치 산출물 (1.4) ---


@router.get("/learning-guides", response_model=list[LearningGuide])
def get_learning_guides():
    """주차별 학습 가이드·핵심 요약 전체."""
    raw = load_learning_guides()
    return [LearningGuide.model_validate(d) for d in raw]


@router.get("/learning-guides/{week}", response_model=LearningGuide)
def get_learning_guide_by_week(week: int):
    """특정 주차 학습 가이드·핵심 요약."""
    raw = load_learning_guides()
    for d in raw:
        if d.get("week") == week:
            return LearningGuide.model_validate(d)
    raise HTTPException(status_code=404, detail=f"주차 {week}에 해당하는 학습 가이드가 없습니다.")


@router.post("/weekly-outputs", response_model=WeeklyOutputs)
async def create_weekly_outputs(file: UploadFile = File(...)):
    """
    1주일치 강의 스크립트(.txt 묶음)를 업로드하면
    - 주차별 학습 가이드
    - 주차별 핵심 요약
    묶음을 반환한다.

    현재는 파이프라인이 비어 있어, 업로드 파일 내용은 사용하지 않고
    data/dummy/ 의 learning_guides 더미 데이터를 그대로 반환한다.
    """

    guides_raw = load_learning_guides()
    guides = [LearningGuide.model_validate(d) for d in guides_raw]
    return WeeklyOutputs(guides=guides)

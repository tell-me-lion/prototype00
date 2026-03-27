"""
산출물 조회 API.
- 단일 강의: 핵심 개념, 학습 포인트, 퀴즈
- 1주일치: 주차별 학습 가이드·핵심 요약
"""

import asyncio
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.loaders.dummy import load_concepts, load_learning_guides, load_learning_points, load_quizzes
from app.loaders.catalog import load_lectures, load_weeks
from app.loaders.results import load_lecture_results, load_week_results
from app.schemas import (
    Concept,
    LearningGuide,
    LearningPoint,
    Quiz,
    LectureOutputs,
    WeeklyOutputs,
    LectureCatalog,
    WeekSummary,
    ProcessingStep,
    ProcessingStatusResponse,
    ProcessTriggerResponse,
    ProcessingStatus,
)
from app import state

router = APIRouter(prefix="/api", tags=["산출물"])


# --- 강의 카탈로그 ---


@router.get("/lectures", response_model=list[LectureCatalog])
def get_lectures():
    """전체 강의 목록 (data/raw/ 스캔)."""
    return load_lectures()


@router.get("/lectures/{lecture_id}", response_model=LectureCatalog)
def get_lecture(lecture_id: str):
    """단일 강의 상세. 없으면 404."""
    lectures = load_lectures()
    for lec in lectures:
        if lec.lecture_id == lecture_id:
            return lec
    raise HTTPException(status_code=404, detail=f"강의 {lecture_id}를 찾을 수 없습니다.")


@router.get("/weeks", response_model=list[WeekSummary])
def get_weeks():
    """존재하는 주차 목록 (빈 주차 제외)."""
    return load_weeks()


@router.get("/weeks/{week}", response_model=WeekSummary)
def get_week(week: int):
    """특정 주차 상세. 없으면 404."""
    weeks = load_weeks()
    for w in weeks:
        if w.week == week:
            return w
    raise HTTPException(status_code=404, detail=f"{week}주차 데이터를 찾을 수 없습니다.")


# --- 처리 트리거 & 상태 관리 ---

_STEPS_TEMPLATE = [
    {"name": "영상 분석", "status": "pending"},
    {"name": "텍스트 추출", "status": "pending"},
    {"name": "AI 분석", "status": "pending"},
]


async def _simulate_lecture(lecture_id: str) -> None:
    """MVP: 강의 처리 시뮬레이션 (2초 × 3단계)."""
    job = state.lecture_jobs[lecture_id]
    for i in range(len(job.steps)):
        job.steps[i]["status"] = "running"
        await asyncio.sleep(2)
        job.steps[i]["status"] = "done"
    job.status = ProcessingStatus.completed
    job.completed_at = datetime.now()


async def _simulate_week(week: int) -> None:
    """MVP: 주차 처리 시뮬레이션 (2초 × 3단계)."""
    job = state.week_jobs[week]
    for i in range(len(job.steps)):
        job.steps[i]["status"] = "running"
        await asyncio.sleep(2)
        job.steps[i]["status"] = "done"
    job.status = ProcessingStatus.completed
    job.completed_at = datetime.now()


@router.post(
    "/lectures/{lecture_id}/process",
    response_model=ProcessTriggerResponse,
    status_code=202,
)
def process_lecture(
    lecture_id: str,
    background_tasks: BackgroundTasks,
    force: bool = False,
):
    """강의 처리 시작 트리거 (Mode A)."""
    # 강의 존재 검증
    lectures = load_lectures()
    if not any(lec.lecture_id == lecture_id for lec in lectures):
        raise HTTPException(status_code=404, detail=f"강의 {lecture_id}를 찾을 수 없습니다.")

    job = state.lecture_jobs.get(lecture_id)

    if job and job.status == ProcessingStatus.processing:
        raise HTTPException(status_code=409, detail="이미 처리 중인 강의입니다.")

    if job and job.status == ProcessingStatus.completed and not force:
        raise HTTPException(
            status_code=409,
            detail="이미 처리 완료된 강의입니다. 재처리하려면 ?force=true 를 사용하세요.",
        )

    from app.state import JobState
    job = JobState(
        status=ProcessingStatus.processing,
        steps=[dict(s) for s in _STEPS_TEMPLATE],
        started_at=datetime.now(),
    )
    state.lecture_jobs[lecture_id] = job
    background_tasks.add_task(_simulate_lecture, lecture_id)

    return ProcessTriggerResponse(
        lecture_id=lecture_id,
        status=ProcessingStatus.processing,
        started_at=job.started_at,
    )


@router.get("/lectures/{lecture_id}/status", response_model=ProcessingStatusResponse)
def get_lecture_status(lecture_id: str):
    """강의 처리 상태 조회."""
    lectures = load_lectures()
    if not any(lec.lecture_id == lecture_id for lec in lectures):
        raise HTTPException(status_code=404, detail=f"강의 {lecture_id}를 찾을 수 없습니다.")

    job = state.lecture_jobs.get(lecture_id)
    if not job:
        return ProcessingStatusResponse(
            lecture_id=lecture_id,
            status=ProcessingStatus.idle,
        )

    return ProcessingStatusResponse(
        lecture_id=lecture_id,
        status=job.status,
        steps=[ProcessingStep(**s) for s in job.steps],
        started_at=job.started_at,
        completed_at=job.completed_at,
        error_message=job.error_message,
    )


@router.get("/lectures/{lecture_id}/results", response_model=LectureOutputs)
def get_lecture_results(lecture_id: str):
    """강의 처리 결과 조회. 완료 전이면 202 반환."""
    lectures = load_lectures()
    if not any(lec.lecture_id == lecture_id for lec in lectures):
        raise HTTPException(status_code=404, detail=f"강의 {lecture_id}를 찾을 수 없습니다.")

    job = state.lecture_jobs.get(lecture_id)
    if not job or job.status != ProcessingStatus.completed:
        raise HTTPException(status_code=202, detail={"status": "processing"})

    concepts_raw, lp_raw, quizzes_raw = load_lecture_results(lecture_id)
    return LectureOutputs(
        concepts=[Concept.model_validate(d) for d in concepts_raw],
        learning_points=[LearningPoint.model_validate(d) for d in lp_raw],
        quizzes=[Quiz.model_validate(d) for d in quizzes_raw],
    )


@router.post("/weeks/{week}/process", response_model=ProcessTriggerResponse, status_code=202)
def process_week(week: int, background_tasks: BackgroundTasks, force: bool = False):
    """주차 처리 시작 트리거 (Mode B)."""
    weeks = load_weeks()
    if not any(w.week == week for w in weeks):
        raise HTTPException(status_code=404, detail=f"{week}주차 데이터를 찾을 수 없습니다.")

    job = state.week_jobs.get(week)

    if job and job.status == ProcessingStatus.processing:
        raise HTTPException(status_code=409, detail="이미 처리 중인 주차입니다.")

    if job and job.status == ProcessingStatus.completed and not force:
        raise HTTPException(
            status_code=409,
            detail="이미 처리 완료된 주차입니다. 재처리하려면 ?force=true 를 사용하세요.",
        )

    from app.state import JobState
    job = JobState(
        status=ProcessingStatus.processing,
        steps=[dict(s) for s in _STEPS_TEMPLATE],
        started_at=datetime.now(),
    )
    state.week_jobs[week] = job
    background_tasks.add_task(_simulate_week, week)

    return ProcessTriggerResponse(
        week=week,
        status=ProcessingStatus.processing,
        started_at=job.started_at,
    )


@router.get("/weeks/{week}/status", response_model=ProcessingStatusResponse)
def get_week_status(week: int):
    """주차 처리 상태 조회."""
    weeks = load_weeks()
    if not any(w.week == week for w in weeks):
        raise HTTPException(status_code=404, detail=f"{week}주차 데이터를 찾을 수 없습니다.")

    job = state.week_jobs.get(week)
    if not job:
        return ProcessingStatusResponse(week=week, status=ProcessingStatus.idle)

    return ProcessingStatusResponse(
        week=week,
        status=job.status,
        steps=[ProcessingStep(**s) for s in job.steps],
        started_at=job.started_at,
        completed_at=job.completed_at,
        error_message=job.error_message,
    )


@router.get("/weeks/{week}/results", response_model=WeeklyOutputs)
def get_week_results(week: int):
    """주차 처리 결과 조회. 완료 전이면 202 반환."""
    weeks = load_weeks()
    if not any(w.week == week for w in weeks):
        raise HTTPException(status_code=404, detail=f"{week}주차 데이터를 찾을 수 없습니다.")

    job = state.week_jobs.get(week)
    if not job or job.status != ProcessingStatus.completed:
        raise HTTPException(status_code=202, detail={"status": "processing"})

    guides_raw = load_week_results(week)
    return WeeklyOutputs(guides=[LearningGuide.model_validate(d) for d in guides_raw])


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


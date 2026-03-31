"""
산출물 조회 API.
- 단일 강의: 핵심 개념, 학습 포인트, 퀴즈
- 1주일치: 주차별 학습 가이드·핵심 요약
"""

import asyncio
import json
import logging
import re
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.loaders.catalog import load_lectures, load_weeks, invalidate_catalog_cache
from app.loaders.results import load_lecture_results, load_week_results
from app.loaders.dummy import load_concepts, load_learning_points, load_quizzes, load_learning_guides
from pipeline.paths import DATA_EP_CONCEPTS, DATA_EP_LEARNING_POINTS, DATA_QUIZZES_VALIDATED, DATA_LEARNING_GUIDES

logger = logging.getLogger(__name__)
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
from app.state import JobState, get_lecture_job, set_lecture_job, get_week_job, set_week_job

router = APIRouter(prefix="/api", tags=["산출물"])


def _write_jsonl(path, data: list[dict]) -> None:
    """JSONL 파일 쓰기. 디렉터리가 없으면 생성."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for item in data:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")


def _create_lecture_dummy_results(lecture_id: str) -> None:
    """시뮬레이션 완료 후 더미 결과 파일 생성 (ep_concepts, ep_learning_points, quizzes_validated)."""
    concepts = [c for c in load_concepts() if c.get("lecture_id") == lecture_id]
    if not concepts:
        concepts = load_concepts()
    _write_jsonl(DATA_EP_CONCEPTS / f"{lecture_id}.jsonl", concepts)

    lps = [lp for lp in load_learning_points() if lp.get("lecture_id") == lecture_id]
    if not lps:
        lps = load_learning_points()
    _write_jsonl(DATA_EP_LEARNING_POINTS / f"{lecture_id}.jsonl", lps)

    quizzes = [q for q in load_quizzes() if q.get("meta", {}).get("lecture_id") == lecture_id]
    if not quizzes:
        quizzes = load_quizzes()[:5]
    _write_jsonl(DATA_QUIZZES_VALIDATED / f"{lecture_id}.jsonl", quizzes)
    logger.info("더미 결과 파일 생성 완료: lecture=%s", lecture_id)


def _create_week_dummy_results(week: int) -> None:
    """시뮬레이션 완료 후 더미 학습 가이드 파일 생성."""
    guides = [g for g in load_learning_guides() if g.get("week") == week]
    if not guides:
        guides = [{"week": week, "summary": f"{week}주차 학습 가이드입니다.", "key_concepts": [], "meta": {"source": "simulation"}}]
    _write_jsonl(DATA_LEARNING_GUIDES / f"week_{week:02d}.jsonl", guides)
    logger.info("더미 학습 가이드 파일 생성 완료: week=%d", week)


# 입력 검증 패턴
_LECTURE_ID_RE = re.compile(r"^\d{4}-\d{2}-\d{2}_.+$")


def _validate_lecture_id(lecture_id: str) -> str:
    """lecture_id 포맷 검증 (YYYY-MM-DD_코스코드)."""
    if not _LECTURE_ID_RE.match(lecture_id):
        raise HTTPException(
            status_code=400,
            detail=f"잘못된 강의 ID 형식입니다: {lecture_id} (예: 2026-02-03_kdt-backendj-21th)",
        )
    return lecture_id


def _validate_week(week: int) -> int:
    """week 범위 검증 (1 이상)."""
    if week < 1:
        raise HTTPException(status_code=400, detail="주차는 1 이상이어야 합니다.")
    return week


# --- 강의 카탈로그 ---


@router.get("/lectures", response_model=list[LectureCatalog])
def get_lectures():
    """전체 강의 목록 (data/raw/ 스캔)."""
    return load_lectures()


@router.get("/lectures/{lecture_id}", response_model=LectureCatalog)
def get_lecture(lecture_id: str):
    """단일 강의 상세. 없으면 404."""
    _validate_lecture_id(lecture_id)
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
    _validate_week(week)
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
    job = await get_lecture_job(lecture_id)
    if not job:
        return
    for i in range(len(job.steps)):
        job.steps[i]["status"] = "running"
        await asyncio.sleep(2)
        job.steps[i]["status"] = "done"
    _create_lecture_dummy_results(lecture_id)
    job.status = ProcessingStatus.completed
    job.completed_at = datetime.now()
    invalidate_catalog_cache()


async def _simulate_week(week: int) -> None:
    """MVP: 주차 처리 시뮬레이션 (2초 × 3단계)."""
    job = await get_week_job(week)
    if not job:
        return
    for i in range(len(job.steps)):
        job.steps[i]["status"] = "running"
        await asyncio.sleep(2)
        job.steps[i]["status"] = "done"
    _create_week_dummy_results(week)
    job.status = ProcessingStatus.completed
    job.completed_at = datetime.now()
    invalidate_catalog_cache()


@router.post(
    "/lectures/{lecture_id}/process",
    response_model=ProcessTriggerResponse,
    status_code=202,
)
async def process_lecture(
    lecture_id: str,
    background_tasks: BackgroundTasks,
    force: bool = False,
):
    """강의 처리 시작 트리거 (Mode A)."""
    _validate_lecture_id(lecture_id)
    lectures = load_lectures()
    if not any(lec.lecture_id == lecture_id for lec in lectures):
        raise HTTPException(status_code=404, detail=f"강의 {lecture_id}를 찾을 수 없습니다.")

    job = await get_lecture_job(lecture_id)

    if job and job.status == ProcessingStatus.processing:
        raise HTTPException(status_code=409, detail="이미 처리 중인 강의입니다.")

    if job and job.status == ProcessingStatus.completed and not force:
        raise HTTPException(
            status_code=409,
            detail="이미 처리 완료된 강의입니다. 재처리하려면 ?force=true 를 사용하세요.",
        )

    job = JobState(
        status=ProcessingStatus.processing,
        steps=[dict(s) for s in _STEPS_TEMPLATE],
        started_at=datetime.now(),
    )
    await set_lecture_job(lecture_id, job)
    background_tasks.add_task(_simulate_lecture, lecture_id)

    return ProcessTriggerResponse(
        lecture_id=lecture_id,
        status=ProcessingStatus.processing,
        started_at=job.started_at,
    )


@router.get("/lectures/{lecture_id}/status", response_model=ProcessingStatusResponse)
async def get_lecture_status(lecture_id: str):
    """강의 처리 상태 조회."""
    _validate_lecture_id(lecture_id)
    lectures = load_lectures()
    lec = next((l for l in lectures if l.lecture_id == lecture_id), None)
    if not lec:
        raise HTTPException(status_code=404, detail=f"강의 {lecture_id}를 찾을 수 없습니다.")

    job = await get_lecture_job(lecture_id)
    if not job:
        return ProcessingStatusResponse(
            lecture_id=lecture_id,
            status=lec.status,
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
async def get_lecture_results(lecture_id: str):
    """강의 처리 결과 조회. 완료 전이면 202 반환."""
    _validate_lecture_id(lecture_id)
    lectures = load_lectures()
    lec = next((l for l in lectures if l.lecture_id == lecture_id), None)
    if not lec:
        raise HTTPException(status_code=404, detail=f"강의 {lecture_id}를 찾을 수 없습니다.")

    job = await get_lecture_job(lecture_id)
    is_completed = (
        (job and job.status == ProcessingStatus.completed)
        or lec.status == ProcessingStatus.completed
    )
    if not is_completed:
        return JSONResponse(status_code=202, content={"status": "processing"})

    concepts_raw, lp_raw, quizzes_raw = load_lecture_results(lecture_id)

    try:
        concepts = [Concept.model_validate(d) for d in concepts_raw]
    except ValidationError as e:
        raise HTTPException(422, detail=f"개념 데이터 형식 오류: {e.error_count()}건")

    try:
        learning_points = [LearningPoint.model_validate(d) for d in lp_raw]
    except ValidationError as e:
        raise HTTPException(422, detail=f"학습 포인트 데이터 형식 오류: {e.error_count()}건")

    try:
        quizzes = [Quiz.model_validate(d) for d in quizzes_raw]
    except ValidationError as e:
        raise HTTPException(422, detail=f"퀴즈 데이터 형식 오류: {e.error_count()}건")

    return LectureOutputs(
        concepts=concepts,
        learning_points=learning_points,
        quizzes=quizzes,
    )


@router.post("/weeks/{week}/process", response_model=ProcessTriggerResponse, status_code=202)
async def process_week(week: int, background_tasks: BackgroundTasks, force: bool = False):
    """주차 처리 시작 트리거 (Mode B)."""
    _validate_week(week)
    weeks = load_weeks()
    if not any(w.week == week for w in weeks):
        raise HTTPException(status_code=404, detail=f"{week}주차 데이터를 찾을 수 없습니다.")

    job = await get_week_job(week)

    if job and job.status == ProcessingStatus.processing:
        raise HTTPException(status_code=409, detail="이미 처리 중인 주차입니다.")

    if job and job.status == ProcessingStatus.completed and not force:
        raise HTTPException(
            status_code=409,
            detail="이미 처리 완료된 주차입니다. 재처리하려면 ?force=true 를 사용하세요.",
        )

    job = JobState(
        status=ProcessingStatus.processing,
        steps=[dict(s) for s in _STEPS_TEMPLATE],
        started_at=datetime.now(),
    )
    await set_week_job(week, job)
    background_tasks.add_task(_simulate_week, week)

    return ProcessTriggerResponse(
        week=week,
        status=ProcessingStatus.processing,
        started_at=job.started_at,
    )


@router.get("/weeks/{week}/status", response_model=ProcessingStatusResponse)
async def get_week_status(week: int):
    """주차 처리 상태 조회."""
    _validate_week(week)
    weeks = load_weeks()
    ws = next((w for w in weeks if w.week == week), None)
    if not ws:
        raise HTTPException(status_code=404, detail=f"{week}주차 데이터를 찾을 수 없습니다.")

    job = await get_week_job(week)
    if not job:
        return ProcessingStatusResponse(week=week, status=ws.status)

    return ProcessingStatusResponse(
        week=week,
        status=job.status,
        steps=[ProcessingStep(**s) for s in job.steps],
        started_at=job.started_at,
        completed_at=job.completed_at,
        error_message=job.error_message,
    )


@router.get("/weeks/{week}/results", response_model=WeeklyOutputs)
async def get_week_results(week: int):
    """주차 처리 결과 조회. 완료 전이면 202 반환."""
    _validate_week(week)
    weeks = load_weeks()
    ws = next((w for w in weeks if w.week == week), None)
    if not ws:
        raise HTTPException(status_code=404, detail=f"{week}주차 데이터를 찾을 수 없습니다.")

    job = await get_week_job(week)
    is_completed = (
        (job and job.status == ProcessingStatus.completed)
        or ws.status == ProcessingStatus.completed
    )
    if not is_completed:
        return JSONResponse(status_code=202, content={"status": "processing"})

    guides_raw = load_week_results(week)
    return WeeklyOutputs(guides=[LearningGuide.model_validate(d) for d in guides_raw])


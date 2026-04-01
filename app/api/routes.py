"""
산출물 조회 API.
- 단일 강의: 핵심 개념, 학습 포인트, 퀴즈
- 1주일치: 주차별 학습 가이드·핵심 요약
"""

import asyncio
import json
import logging
import re
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.loaders.catalog import load_lectures, load_weeks, invalidate_catalog_cache
from app.loaders.results import load_lecture_results, load_week_results
from pipeline.paths import DATA_EP_CONCEPTS, DATA_EP_LEARNING_POINTS, DATA_QUIZZES_RAW, DATA_QUIZZES_VALIDATED, DATA_LEARNING_GUIDES

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
from app.state import (
    JobState,
    get_lecture_job,
    set_lecture_job,
    get_week_job,
    set_week_job,
    clear_week_job,
    start_lecture_job_if_idle,
    start_week_job_if_idle,
)

router = APIRouter(prefix="/api", tags=["산출물"])


def _write_jsonl(path, data: list[dict]) -> None:
    """JSONL 파일 atomic write. 임시 파일에 쓴 후 os.replace()로 교체."""
    import os
    import tempfile
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            for item in data:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
        os.replace(tmp_path, path)
    except BaseException:
        os.unlink(tmp_path)
        raise



# 입력 검증 패턴
_LECTURE_ID_RE = re.compile(r"^\d{4}-\d{2}-\d{2}_[a-zA-Z0-9_-]+$")


def _validate_lecture_id(lecture_id: str) -> str:
    """lecture_id 포맷 검증 (YYYY-MM-DD_코스코드)."""
    if not _LECTURE_ID_RE.match(lecture_id):
        raise HTTPException(
            status_code=400,
            detail=f"잘못된 강의 ID 형식입니다: {lecture_id} (예: 2026-02-03_kdt-backendj-21th)",
        )
    return lecture_id


def _validate_week(week: int) -> int:
    """week 범위 검증 (1~52)."""
    if week < 1 or week > 52:
        raise HTTPException(status_code=400, detail="주차는 1~52 범위여야 합니다.")
    return week


# --- 강의 카탈로그 ---


@router.get("/lectures", response_model=list[LectureCatalog])
async def get_lectures():
    """전체 강의 목록 (data/raw/ 스캔)."""
    return await asyncio.to_thread(load_lectures)


@router.get("/lectures/{lecture_id}", response_model=LectureCatalog)
async def get_lecture(lecture_id: str):
    """단일 강의 상세. 없으면 404."""
    _validate_lecture_id(lecture_id)
    lectures = await asyncio.to_thread(load_lectures)
    for lec in lectures:
        if lec.lecture_id == lecture_id:
            return lec
    raise HTTPException(status_code=404, detail=f"강의 {lecture_id}를 찾을 수 없습니다.")


@router.get("/weeks", response_model=list[WeekSummary])
async def get_weeks():
    """존재하는 주차 목록 (빈 주차 제외)."""
    return await asyncio.to_thread(load_weeks)


@router.get("/weeks/{week}", response_model=WeekSummary)
async def get_week(week: int):
    """특정 주차 상세. 없으면 404."""
    _validate_week(week)
    weeks = await asyncio.to_thread(load_weeks)
    for w in weeks:
        if w.week == week:
            return w
    raise HTTPException(status_code=404, detail=f"{week}주차 데이터를 찾을 수 없습니다.")


# --- 처리 트리거 & 상태 관리 ---

_LECTURE_STEPS_TEMPLATE = [
    {"name": "Step 1: 텍스트 정제", "status": "pending"},
    {"name": "Step 2: 문장 분리", "status": "pending"},
    {"name": "Step 3: 의미 단위 청킹", "status": "pending"},
    {"name": "Step 4: 명제 추출", "status": "pending"},
    {"name": "Step 5: 팩트 포맷팅", "status": "pending"},
    {"name": "개념 분석 (EP)", "status": "pending"},
    {"name": "문제 설계", "status": "pending"},
    {"name": "퀴즈 생성", "status": "pending"},
]

_WEEK_STEPS_TEMPLATE = [
    {"name": "학습 가이드 생성", "status": "pending"},
]


async def _run_lecture_pipeline(lecture_id: str) -> None:
    """Mode A: 강의 파이프라인 실행 (전처리 → EP → Blueprint → Quiz).

    각 단계 출력 파일이 이미 존재하면 해당 단계를 건너뛴다.
    """
    from pipeline.paths import DATA_PHASE1_SESSIONS, DATA_BLUEPRINTS

    job = await get_lecture_job(lecture_id)
    if not job:
        return
    try:
        # 처리 시작 마커 파일 생성 — 새로고침 후에도 processing 상태 감지 가능하게
        marker = DATA_PHASE1_SESSIONS / f"{lecture_id}.jsonl"
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.touch()
        invalidate_catalog_cache()  # 캐시 즉시 만료 → 다음 /api/weeks 요청에서 processing 반환

        # Step 0~4: 전처리 (Phase 1~5) — 단계별 스킵은 wrapper.py 내부에서 처리
        def progress_callback(phase_num: int, status: str):
            idx = phase_num - 1
            if 0 <= idx < 5:
                job.steps[idx]["status"] = status

        def phase4_detail_callback(chunks_done: int, total_chunks: int, props_count: int):
            job.steps[3]["detail"] = f"{chunks_done}/{total_chunks} 단락 | 명제 {props_count}개"
            logger.info("[Phase 4] 명제 추출 진행: %d/%d 단락, 명제 %d개", chunks_done, total_chunks, props_count)

        await asyncio.to_thread(_exec_preprocess, lecture_id, progress_callback, phase4_detail_callback)

        # Step 5: 개념 추출 (EP)
        ep_file = DATA_EP_CONCEPTS / f"{lecture_id}.jsonl"
        if ep_file.exists():
            logger.info("[SKIP] EP — 출력 파일 존재: %s", ep_file)
            job.steps[5]["status"] = "done"
        else:
            job.steps[5]["status"] = "running"
            await asyncio.to_thread(_exec_ep, lecture_id)
            job.steps[5]["status"] = "done"

        # Step 6: 문제 설계 (Blueprint)
        bp_file = DATA_BLUEPRINTS / f"{lecture_id}.jsonl"
        if bp_file.exists():
            logger.info("[SKIP] Blueprint — 출력 파일 존재: %s", bp_file)
            job.steps[6]["status"] = "done"
        else:
            job.steps[6]["status"] = "running"
            await asyncio.to_thread(_exec_blueprint, lecture_id)
            job.steps[6]["status"] = "done"

        # Step 7: 퀴즈 생성
        quiz_file = DATA_QUIZZES_VALIDATED / f"{lecture_id}.jsonl"
        if quiz_file.exists() and quiz_file.stat().st_size > 0:
            logger.info("[SKIP] 퀴즈 생성 — 출력 파일 존재: %s", quiz_file)
            job.steps[7]["status"] = "done"
        else:
            job.steps[7]["status"] = "running"

            def quiz_detail_callback(detail: str):
                job.steps[7]["detail"] = detail
                logger.info("[퀴즈 생성] %s", detail)

            await asyncio.to_thread(_exec_quiz_generation, lecture_id, quiz_detail_callback)
            job.steps[7]["status"] = "done"

        job.status = ProcessingStatus.completed
        job.completed_at = datetime.now(tz=timezone.utc)
        invalidate_catalog_cache()
    except Exception as e:
        logger.error("강의 처리 실패: lecture=%s, error=%s", lecture_id, e, exc_info=True)
        job.status = ProcessingStatus.error
        job.error_message = str(e)
        job.completed_at = datetime.now(tz=timezone.utc)


async def _run_week_pipeline(week: int) -> None:
    """Mode B: 주차 파이프라인 실행 (Guides 생성)."""
    job = await get_week_job(week)
    if not job:
        return
    try:
        job.steps[0]["status"] = "running"
        await asyncio.to_thread(_exec_guides, week)
        job.steps[0]["status"] = "done"

        job.status = ProcessingStatus.completed
        job.completed_at = datetime.now(tz=timezone.utc)
        invalidate_catalog_cache()
    except Exception as e:
        logger.error("주차 처리 실패: week=%d, error=%s", week, e, exc_info=True)
        job.status = ProcessingStatus.error
        job.error_message = str(e)
        job.completed_at = datetime.now(tz=timezone.utc)


# --- 파이프라인 실행 함수 (동기, asyncio.to_thread에서 호출) ---


from typing import Callable

def _exec_preprocess(
    lecture_id: str,
    progress_callback: Callable[[int, str], None] | None = None,
    phase4_progress_callback: Callable[[int, int, int], None] | None = None,
) -> None:
    """Phase 1~5 전처리 실행."""
    from pipeline.preprocessor.wrapper import run_preprocess

    run_preprocess(
        lecture_id,
        use_gemini_embed=True,
        progress_callback=progress_callback,
        phase4_progress_callback=phase4_progress_callback,
    )


def _exec_ep(lecture_id: str) -> None:
    """EP 실행 (개념 + 학습 포인트 추출)."""
    from pipeline.ep.runner import run_ep
    from pipeline.paths import DATA_PHASE5_FACTS

    phase5_file = DATA_PHASE5_FACTS / f"{lecture_id}.jsonl"
    if not phase5_file.exists():
        raise FileNotFoundError(f"전처리 출력 파일 없음: {phase5_file}")
    run_ep(input_file=phase5_file, out_dir=DATA_EP_CONCEPTS)


def _exec_blueprint(lecture_id: str) -> None:
    """Blueprint 실행."""
    from pipeline.blueprint.runner import run_blueprint

    ep_file = DATA_EP_CONCEPTS / f"{lecture_id}.jsonl"
    if not ep_file.exists():
        raise FileNotFoundError(f"EP 출력 파일 없음: {ep_file}")
    run_blueprint(input_file=ep_file)


def _exec_quiz_generation(
    lecture_id: str,
    detail_callback: Callable[[str], None] | None = None,
) -> None:
    """퀴즈 생성 실행."""
    from pipeline.quiz_generation.runner import run_quiz_generation
    from pipeline.paths import DATA_BLUEPRINTS, DATA_QUIZZES_RAW

    bp_file = DATA_BLUEPRINTS / f"{lecture_id}.jsonl"
    if not bp_file.exists():
        raise FileNotFoundError(f"Blueprint 출력 파일 없음: {bp_file}")
    run_quiz_generation(
        input_file=bp_file,
        output_file=DATA_QUIZZES_RAW / f"{lecture_id}.jsonl",
        detail_callback=detail_callback,
    )

    # quizzes_raw → quizzes_validated 복사 (QA 별도 단계 불필요)
    raw_file = DATA_QUIZZES_RAW / f"{lecture_id}.jsonl"
    if raw_file.exists():
        validated_file = DATA_QUIZZES_VALIDATED / f"{lecture_id}.jsonl"
        DATA_QUIZZES_VALIDATED.mkdir(parents=True, exist_ok=True)
        import shutil
        shutil.copy2(raw_file, validated_file)


def _exec_guides(week: int) -> None:
    """Guides 실행."""
    from pipeline.guides.runner import run_guides

    run_guides(week=week)


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
    lectures = await asyncio.to_thread(load_lectures)
    if not any(lec.lecture_id == lecture_id for lec in lectures):
        raise HTTPException(status_code=404, detail=f"강의 {lecture_id}를 찾을 수 없습니다.")

    new_job = JobState(
        status=ProcessingStatus.processing,
        steps=[dict(s) for s in _LECTURE_STEPS_TEMPLATE],
        started_at=datetime.now(tz=timezone.utc),
    )
    started, existing = await start_lecture_job_if_idle(lecture_id, new_job, force=force)

    if not started and existing:
        if existing.status == ProcessingStatus.processing:
            raise HTTPException(status_code=409, detail="이미 처리 중인 강의입니다.")
        raise HTTPException(
            status_code=409,
            detail="이미 처리 완료된 강의입니다. 재처리하려면 ?force=true 를 사용하세요.",
        )

    background_tasks.add_task(_run_lecture_pipeline, lecture_id)

    return ProcessTriggerResponse(
        lecture_id=lecture_id,
        status=ProcessingStatus.processing,
        started_at=new_job.started_at,
    )


@router.get("/lectures/{lecture_id}/status", response_model=ProcessingStatusResponse)
async def get_lecture_status(lecture_id: str):
    """강의 처리 상태 조회."""
    _validate_lecture_id(lecture_id)
    lectures = await asyncio.to_thread(load_lectures)
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
    lectures = await asyncio.to_thread(load_lectures)
    lec = next((l for l in lectures if l.lecture_id == lecture_id), None)
    if not lec:
        raise HTTPException(status_code=404, detail=f"강의 {lecture_id}를 찾을 수 없습니다.")

    job = await get_lecture_job(lecture_id)
    is_completed = (
        (job and job.status == ProcessingStatus.completed)
        or lec.status == ProcessingStatus.completed
        or (DATA_EP_CONCEPTS / f"{lecture_id}.jsonl").exists()
    )
    if not is_completed:
        return JSONResponse(status_code=202, content={"status": "processing"})

    concepts_raw, lp_raw, quizzes_raw = await asyncio.to_thread(load_lecture_results, lecture_id)

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
    weeks = await asyncio.to_thread(load_weeks)
    if not any(w.week == week for w in weeks):
        raise HTTPException(status_code=404, detail=f"{week}주차 데이터를 찾을 수 없습니다.")

    new_job = JobState(
        status=ProcessingStatus.processing,
        steps=[dict(s) for s in _WEEK_STEPS_TEMPLATE],
        started_at=datetime.now(tz=timezone.utc),
    )
    # completed job인데 가이드 파일이 없으면 stale → force 처리
    guide_file = DATA_LEARNING_GUIDES / f"week_{week:02d}.jsonl"
    effective_force = force
    existing_check = await get_week_job(week)
    if existing_check and existing_check.status == ProcessingStatus.completed and not guide_file.exists():
        effective_force = True

    started, existing = await start_week_job_if_idle(week, new_job, force=effective_force)

    if not started and existing:
        if existing.status == ProcessingStatus.processing:
            raise HTTPException(status_code=409, detail="이미 처리 중인 주차입니다.")
        raise HTTPException(
            status_code=409,
            detail="이미 처리 완료된 주차입니다. 재처리하려면 ?force=true 를 사용하세요.",
        )

    background_tasks.add_task(_run_week_pipeline, week)

    return ProcessTriggerResponse(
        week=week,
        status=ProcessingStatus.processing,
        started_at=new_job.started_at,
    )


@router.get("/weeks/{week}/status", response_model=ProcessingStatusResponse)
async def get_week_status(week: int):
    """주차 처리 상태 조회."""
    _validate_week(week)
    weeks = await asyncio.to_thread(load_weeks)
    ws = next((w for w in weeks if w.week == week), None)
    if not ws:
        raise HTTPException(status_code=404, detail=f"{week}주차 데이터를 찾을 수 없습니다.")

    guide_file = DATA_LEARNING_GUIDES / f"week_{week:02d}.jsonl"

    job = await get_week_job(week)
    if not job:
        # 인메모리 job 없음 (서버 재시작 등) → 가이드 결과 파일로 판정
        fallback_status = ProcessingStatus.completed if guide_file.exists() else ProcessingStatus.idle
        return ProcessingStatusResponse(week=week, status=fallback_status)

    # job이 completed인데 가이드 파일이 없으면 stale → idle로 보정
    effective_status = job.status
    if job.status == ProcessingStatus.completed and not guide_file.exists():
        effective_status = ProcessingStatus.idle
        await clear_week_job(week)

    return ProcessingStatusResponse(
        week=week,
        status=effective_status,
        steps=[ProcessingStep(**s) for s in job.steps] if effective_status != ProcessingStatus.idle else [],
        started_at=job.started_at if effective_status != ProcessingStatus.idle else None,
        completed_at=job.completed_at if effective_status != ProcessingStatus.idle else None,
        error_message=job.error_message,
    )


@router.get("/weeks/{week}/results", response_model=WeeklyOutputs)
async def get_week_results(week: int):
    """주차 처리 결과 조회. 완료 전이면 202 반환."""
    _validate_week(week)
    weeks = await asyncio.to_thread(load_weeks)
    ws = next((w for w in weeks if w.week == week), None)
    if not ws:
        raise HTTPException(status_code=404, detail=f"{week}주차 데이터를 찾을 수 없습니다.")

    job = await get_week_job(week)
    is_completed = (
        (job and job.status == ProcessingStatus.completed)
        or ws.status == ProcessingStatus.completed
        or (DATA_LEARNING_GUIDES / f"week_{week:02d}.jsonl").exists()
    )
    if not is_completed:
        return JSONResponse(status_code=202, content={"status": "processing"})

    guides_raw = await asyncio.to_thread(load_week_results, week)
    return WeeklyOutputs(guides=[LearningGuide.model_validate(d) for d in guides_raw])


"""
강의 카탈로그 로더.
data/raw/*.txt 를 스캔해 강의 목록과 주차 요약을 반환한다.
"""

import re
import time
from datetime import date
from pathlib import Path

from pipeline.paths import DATA_RAW, DATA_EP_CONCEPTS, DATA_PHASE1_SESSIONS
from app.schemas.models import (
    LectureCatalog,
    LectureResultSummary,
    ProcessingStatus,
    WeekSummary,
)

_FILE_PATTERN = re.compile(r"^(\d{4}-\d{2}-\d{2})_(.+)$")

DAY_NAMES_KO = ["월", "화", "수", "목", "금", "토", "일"]

COURSE_NAMES: dict[str, str] = {
    "kdt-backendj": "KDT 백엔드 Java",
}


def _parse_course_name(code: str) -> str:
    """kdt-backendj-21th → 'KDT 백엔드 Java 21기'"""
    parts = code.rsplit("-", 1)
    base = parts[0]
    cohort = parts[1].replace("th", "기") if len(parts) > 1 else ""
    name = COURSE_NAMES.get(base, base)
    return f"{name} {cohort}".strip()


def _calculate_week(lecture_date: date, first_date: date) -> int:
    """첫 강의 날짜 기준 ISO week 오프셋으로 주차 계산."""
    first_iso = first_date.isocalendar()[1]
    current_iso = lecture_date.isocalendar()[1]
    return current_iso - first_iso + 1


def _get_status(lecture_id: str) -> ProcessingStatus:
    """파이프라인 출력 디렉터리를 확인해 처리 상태를 판별."""
    if (DATA_EP_CONCEPTS / f"{lecture_id}.jsonl").exists():
        return ProcessingStatus.completed
    if (DATA_PHASE1_SESSIONS / f"{lecture_id}.jsonl").exists():
        return ProcessingStatus.processing
    return ProcessingStatus.idle


def _get_result_summary(lecture_id: str, status: ProcessingStatus) -> LectureResultSummary | None:
    """처리 완료된 강의의 결과 요약 집계."""
    if status != ProcessingStatus.completed:
        return None

    concept_count = 0
    ep_file = DATA_EP_CONCEPTS / f"{lecture_id}.jsonl"
    if ep_file.exists():
        lines = ep_file.read_text(encoding="utf-8").splitlines()
        concept_count = len([ln for ln in lines if ln.strip()])

    return LectureResultSummary(
        concept_count=concept_count,
        learning_point_count=0,
        quiz_count=0,
    )


_cache: dict[str, tuple[float, object]] = {}
_CACHE_TTL = 30  # 초


def _get_cached(key: str) -> object | None:
    """TTL 기반 캐시 조회. 만료 시 None 반환."""
    entry = _cache.get(key)
    if entry and (time.monotonic() - entry[0]) < _CACHE_TTL:
        return entry[1]
    return None


def _set_cached(key: str, value: object) -> None:
    _cache[key] = (time.monotonic(), value)


def invalidate_catalog_cache() -> None:
    """캐시 무효화 (처리 완료 시 호출)."""
    _cache.clear()


def load_lectures() -> list[LectureCatalog]:
    """data/raw/*.txt 를 스캔해 강의 카탈로그 반환 (날짜 오름차순). 30초 캐시."""
    cached = _get_cached("lectures")
    if cached is not None:
        return cached  # type: ignore[return-value]
    txt_files = sorted(DATA_RAW.glob("*.txt"))
    if not txt_files:
        return []

    dates: list[date] = []
    parsed: list[tuple[date, str, str]] = []  # (date, lecture_id, course_code)

    for f in txt_files:
        m = _FILE_PATTERN.match(f.stem)
        if not m:
            continue
        d = date.fromisoformat(m.group(1))
        course_code = m.group(2)
        dates.append(d)
        parsed.append((d, f.stem, course_code))

    if not dates:
        return []

    first_date = min(dates)
    lectures: list[LectureCatalog] = []

    for lecture_date, lecture_id, course_code in parsed:
        week = _calculate_week(lecture_date, first_date)
        status = _get_status(lecture_id)
        result_summary = _get_result_summary(lecture_id, status)

        lectures.append(
            LectureCatalog(
                lecture_id=lecture_id,
                date=lecture_date,
                day_of_week=DAY_NAMES_KO[lecture_date.weekday()],
                week=week,
                course_code=course_code,
                course_name=_parse_course_name(course_code),
                status=status,
                result_summary=result_summary,
            )
        )

    _set_cached("lectures", lectures)
    return lectures


def load_weeks() -> list[WeekSummary]:
    """존재하는 주차만 요약해서 반환 (주차 오름차순). 30초 캐시."""
    cached = _get_cached("weeks")
    if cached is not None:
        return cached  # type: ignore[return-value]
    lectures = load_lectures()
    week_map: dict[int, list[LectureCatalog]] = {}

    for lec in lectures:
        week_map.setdefault(lec.week, []).append(lec)

    summaries: list[WeekSummary] = []
    for week_num in sorted(week_map):
        week_lectures = sorted(week_map[week_num], key=lambda l: l.date)
        completed_count = sum(1 for l in week_lectures if l.status == ProcessingStatus.completed)

        min_date = week_lectures[0].date
        max_date = week_lectures[-1].date
        date_range = f"{min_date.strftime('%m/%d')} ~ {max_date.strftime('%m/%d')}"

        if completed_count == len(week_lectures):
            week_status = ProcessingStatus.completed
        elif completed_count > 0 or any(l.status == ProcessingStatus.processing for l in week_lectures):
            week_status = ProcessingStatus.processing
        else:
            week_status = ProcessingStatus.idle

        summaries.append(
            WeekSummary(
                week=week_num,
                lecture_count=len(week_lectures),
                completed_count=completed_count,
                date_range=date_range,
                status=week_status,
                lectures=week_lectures,
            )
        )

    _set_cached("weeks", summaries)
    return summaries

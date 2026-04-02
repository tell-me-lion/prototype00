"""Guides 러너: LLM 기반 주차별 학습 가이드 생성.

Mode B 전용. Phase 5 facts + EP concepts/learning_points를 입력으로
Gemini LLM이 구조화된 학습 가이드를 생성한다.
"""

import json
import logging
import re
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Callable

from pipeline import paths

logger = logging.getLogger(__name__)


def run_guides(
    in_dir: Path | None = None,
    out_dir: Path | None = None,
    week: int | None = None,
    detail_callback: Callable[[str], None] | None = None,
) -> None:
    """주차별 학습 가이드 생성 (LLM 기반).

    Args:
        in_dir: phase5_facts 디렉터리. None이면 기본 경로.
        out_dir: 출력 디렉터리. None이면 기본 경로.
        week: 특정 주차만 처리. None이면 전체 주차.
        detail_callback: 진행 상황 콜백.
    """
    from .guide_generator import call_gemini_guide
    from .prompt_builder import build_guide_prompt
    from .validator import validate_guide

    src = in_dir or paths.DATA_PHASE5_FACTS
    dst = out_dir or paths.DATA_LEARNING_GUIDES
    dst.mkdir(parents=True, exist_ok=True)

    # first_date를 raw 디렉터리에서 산출
    raw_dir = paths.DATA_RAW
    raw_dates: list[date] = []
    for txt_file in raw_dir.glob("*.txt"):
        d = _extract_date(txt_file.stem)
        if d is not None:
            raw_dates.append(d)
    if not raw_dates:
        print("[WARN] raw 디렉터리에 파일 없음 — first_date 산출 불가")
        return
    first_date = min(raw_dates)

    # Phase 5 facts 파일 수집
    dated_files: list[tuple[date, Path]] = []
    for jsonl_file in sorted(src.glob("*.jsonl")):
        file_date = _extract_date(jsonl_file.stem)
        if file_date is None:
            continue
        dated_files.append((file_date, jsonl_file))

    if not dated_files:
        print("[WARN] 날짜를 파싱할 수 있는 Phase 5 파일 없음")
        return

    # Phase 5 facts를 주차별로 그룹핑
    week_chunks: dict[int, list[dict]] = defaultdict(list)
    # lecture_id별 주차 매핑 (EP 데이터 로딩용)
    week_lecture_ids: dict[int, list[str]] = defaultdict(list)

    for file_date, jsonl_file in dated_files:
        file_week = _calculate_week(file_date, first_date)
        if week is not None and file_week != week:
            continue
        lecture_id = jsonl_file.stem
        week_lecture_ids[file_week].append(lecture_id)

        for line in jsonl_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                chunk = json.loads(line)
                week_chunks[file_week].append(chunk)
            except json.JSONDecodeError:
                continue

    if not week_chunks:
        target = f"week={week}" if week is not None else "전체"
        raise RuntimeError(f"처리할 주차 데이터 없음 (target={target}, phase5 파일={len(dated_files)}건, first_date={first_date})")

    # 주차별 가이드 생성
    for w, chunks in sorted(week_chunks.items()):
        if detail_callback:
            detail_callback("데이터 수집 중...")

        # EP 데이터 로딩
        lecture_ids = week_lecture_ids.get(w, [])
        concepts = _load_ep_data(paths.DATA_EP_CONCEPTS, lecture_ids, min_importance=0.3)
        learning_points = _load_ep_data(paths.DATA_EP_LEARNING_POINTS, lecture_ids)
        concept_ids = {c.get("concept_id") for c in concepts if c.get("concept_id")}

        # 이전 주차 overview 로딩
        prev_overview = _load_prev_overview(dst, w)

        logger.info(
            "[Guide] week=%d | chunks=%d, concepts=%d, learning_points=%d",
            w, len(chunks), len(concepts), len(learning_points),
        )

        if detail_callback:
            detail_callback("가이드 생성 중...")

        # 프롬프트 조립 + LLM 호출
        prompt = build_guide_prompt(
            week=w,
            facts=chunks,
            concepts=concepts,
            learning_points=learning_points,
            prev_overview=prev_overview,
        )

        raw_guide = call_gemini_guide(prompt)

        if detail_callback:
            detail_callback("품질 검증 중...")

        # 검증
        guide, structure_ok = validate_guide(raw_guide, concept_ids=concept_ids, current_week=w)

        # 구조 실패 시 1회 재생성
        if not structure_ok:
            logger.warning("[Guide] week=%d 구조 검증 실패, 1회 재생성 시도", w)
            if detail_callback:
                detail_callback("재생성 중...")
            raw_guide2 = call_gemini_guide(prompt)
            guide2, structure_ok2 = validate_guide(raw_guide2, concept_ids=concept_ids, current_week=w)
            if structure_ok2:
                guide = guide2
            else:
                logger.warning("[Guide] week=%d 재생성도 구조 실패, 첫 번째 결과 사용", w)

        # week, meta 필드 보강
        guide["week"] = w
        guide.setdefault("meta", {})
        guide["meta"].update({
            "source": "llm_generated",
            "llm_model": "gemini-2.5-flash",
            "total_chunks": len(chunks),
            "total_facts": sum(len(c.get("facts", [])) for c in chunks),
            "ep_concepts_used": len(concepts),
            "ep_learning_points_used": len(learning_points),
        })

        # overview → summary 하위 호환
        if guide.get("overview") and not guide.get("summary"):
            guide["summary"] = guide["overview"]

        # 저장
        out_file = dst / f"week_{w:02d}.jsonl"
        with out_file.open("w", encoding="utf-8") as f:
            f.write(json.dumps(guide, ensure_ascii=False) + "\n")
        print(f"[OK] week_{w:02d}.jsonl | {len(chunks)} chunks → LLM 가이드 생성 완료")


_DATE_PATTERN = re.compile(r"^(\d{4}-\d{2}-\d{2})")


def _extract_date(stem: str) -> date | None:
    """파일명에서 날짜 추출. 예: '2026-02-11_kdt-backendj-21th' → date(2026, 2, 11)."""
    match = _DATE_PATTERN.match(stem)
    if not match:
        return None
    try:
        return date.fromisoformat(match.group(1))
    except ValueError:
        return None


def _calculate_week(lecture_date: date, first_date: date) -> int:
    """첫 강의 날짜 기준 경과 일수로 주차 계산."""
    delta_days = (lecture_date - first_date).days
    return (delta_days // 7) + 1


def _load_ep_data(
    ep_dir: Path,
    lecture_ids: list[str],
    min_importance: float = 0.0,
) -> list[dict]:
    """EP 출력 디렉터리에서 lecture_id별 데이터를 로딩."""
    results: list[dict] = []
    if not ep_dir.exists():
        return results

    for lecture_id in lecture_ids:
        ep_file = ep_dir / f"{lecture_id}.jsonl"
        if not ep_file.exists():
            # 날짜 부분 매칭 시도
            date_part = lecture_id.split("_")[0] if "_" in lecture_id else lecture_id
            candidates = list(ep_dir.glob(f"*{date_part}*.jsonl"))
            ep_file = candidates[0] if candidates else None

        if not ep_file or not ep_file.exists():
            continue

        for line in ep_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
                if item.get("importance", 0) >= min_importance:
                    results.append(item)
            except json.JSONDecodeError:
                continue

    return results


def _load_prev_overview(guides_dir: Path, current_week: int) -> str | None:
    """이전 주차 가이드에서 overview를 로딩."""
    prev_file = guides_dir / f"week_{current_week - 1:02d}.jsonl"
    if not prev_file.exists():
        return None
    try:
        first_line = prev_file.read_text(encoding="utf-8").splitlines()[0].strip()
        data = json.loads(first_line)
        return data.get("overview") or data.get("summary") or None
    except (json.JSONDecodeError, IndexError):
        return None

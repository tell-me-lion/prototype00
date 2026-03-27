"""
파이프라인 실제 출력물 로더.
ep_concepts, ep_learning_points, quizzes_validated, learning_guides 디렉터리에서 로드.
파일이 없으면 더미 데이터로 대체하고 로그로 출처를 명시한다.
"""

import json
import logging
from pathlib import Path
from typing import Any

from pipeline.paths import (
    DATA_EP_CONCEPTS,
    DATA_EP_LEARNING_POINTS,
    DATA_QUIZZES_VALIDATED,
    DATA_LEARNING_GUIDES,
)
from app.loaders.dummy import load_concepts, load_learning_points, load_quizzes, load_learning_guides

logger = logging.getLogger(__name__)


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    result = []
    for ln in lines:
        ln = ln.strip()
        if ln:
            try:
                result.append(json.loads(ln))
            except json.JSONDecodeError:
                continue
    return result


def load_lecture_results(lecture_id: str) -> tuple[list[dict], list[dict], list[dict]]:
    """강의 처리 결과 로드 (concepts, learning_points, quizzes).
    실제 파이프라인 출력이 없으면 더미 반환. 출처를 로그에 기록.
    """
    concepts = _load_jsonl(DATA_EP_CONCEPTS / f"{lecture_id}.jsonl")
    if concepts:
        logger.info("concepts 로드: pipeline (lecture=%s)", lecture_id)
    else:
        concepts = load_concepts()
        logger.warning("concepts 로드: dummy fallback (lecture=%s)", lecture_id)

    learning_points = _load_jsonl(DATA_EP_LEARNING_POINTS / f"{lecture_id}.jsonl")
    if learning_points:
        logger.info("learning_points 로드: pipeline (lecture=%s)", lecture_id)
    else:
        learning_points = load_learning_points()
        logger.warning("learning_points 로드: dummy fallback (lecture=%s)", lecture_id)

    quizzes = _load_jsonl(DATA_QUIZZES_VALIDATED / f"{lecture_id}.jsonl")
    if quizzes:
        logger.info("quizzes 로드: pipeline (lecture=%s)", lecture_id)
    else:
        quizzes = load_quizzes()
        logger.warning("quizzes 로드: dummy fallback (lecture=%s)", lecture_id)

    return concepts, learning_points, quizzes


def load_week_results(week: int) -> list[dict[str, Any]]:
    """주차별 학습 가이드 로드.
    실제 파이프라인 출력이 없으면 해당 주차 더미만 반환. 출처를 로그에 기록.
    """
    guides = _load_jsonl(DATA_LEARNING_GUIDES / f"week_{week:02d}.jsonl")
    if guides:
        logger.info("guides 로드: pipeline (week=%d)", week)
        return guides

    all_guides = load_learning_guides()
    week_guides = [g for g in all_guides if g.get("week") == week]
    if week_guides:
        logger.warning("guides 로드: dummy fallback (week=%d)", week)
    else:
        logger.warning("guides 데이터 없음 (week=%d)", week)
    return week_guides

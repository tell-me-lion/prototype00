"""
파이프라인 실제 출력물 로더.
ep_concepts, ep_learning_points, quizzes_validated, learning_guides 디렉터리에서 로드.
파이프라인 출력이 없으면 빈 리스트 반환.
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

logger = logging.getLogger(__name__)


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    result = []
    for i, ln in enumerate(lines):
        ln = ln.strip()
        if ln:
            try:
                result.append(json.loads(ln))
            except json.JSONDecodeError as e:
                logger.warning("JSONL 파싱 실패 (%s, %d행): %s", path.name, i + 1, e)
                continue
    return result


def load_lecture_results(lecture_id: str) -> tuple[list[dict], list[dict], list[dict]]:
    """강의 처리 결과 로드 (concepts, learning_points, quizzes).
    파이프라인 출력이 없으면 빈 리스트 반환.
    """
    concepts = _load_jsonl(DATA_EP_CONCEPTS / f"{lecture_id}.jsonl")
    if concepts:
        logger.info("concepts 로드: pipeline (lecture=%s, %d건)", lecture_id, len(concepts))
    else:
        logger.warning("concepts 없음 (lecture=%s) — 파이프라인 미실행", lecture_id)

    learning_points = _load_jsonl(DATA_EP_LEARNING_POINTS / f"{lecture_id}.jsonl")
    if learning_points:
        logger.info("learning_points 로드: pipeline (lecture=%s, %d건)", lecture_id, len(learning_points))
    else:
        logger.warning("learning_points 없음 (lecture=%s) — 파이프라인 미실행", lecture_id)

    quizzes = _load_jsonl(DATA_QUIZZES_VALIDATED / f"{lecture_id}.jsonl")
    if quizzes:
        logger.info("quizzes 로드: pipeline (lecture=%s, %d건)", lecture_id, len(quizzes))
    else:
        logger.warning("quizzes 없음 (lecture=%s) — 파이프라인 미실행", lecture_id)

    return concepts, learning_points, quizzes


def load_week_results(week: int) -> list[dict[str, Any]]:
    """주차별 학습 가이드 로드.
    파이프라인 출력이 없으면 빈 리스트 반환.
    """
    guides = _load_jsonl(DATA_LEARNING_GUIDES / f"week_{week:02d}.jsonl")
    if guides:
        logger.info("guides 로드: pipeline (week=%d, %d건)", week, len(guides))
    else:
        logger.warning("guides 없음 (week=%d) — 파이프라인 미실행", week)
    return guides

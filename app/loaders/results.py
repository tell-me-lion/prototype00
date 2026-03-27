"""
파이프라인 실제 출력물 로더.
ep_concepts, quizzes_validated, learning_guides 디렉터리에서 로드.
파일이 없으면 더미 데이터로 대체한다.
"""

import json
from pathlib import Path
from typing import Any

from pipeline.paths import DATA_EP_CONCEPTS, DATA_QUIZZES_VALIDATED, DATA_LEARNING_GUIDES
from app.loaders.dummy import load_concepts, load_learning_points, load_quizzes, load_learning_guides


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
    실제 파이프라인 출력이 없으면 더미 반환.
    """
    concepts = _load_jsonl(DATA_EP_CONCEPTS / f"{lecture_id}.jsonl")
    quizzes = _load_jsonl(DATA_QUIZZES_VALIDATED / f"{lecture_id}.jsonl")

    if not concepts:
        concepts = load_concepts()
    if not quizzes:
        quizzes = load_quizzes()
    learning_points = load_learning_points()

    return concepts, learning_points, quizzes


def load_week_results(week: int) -> list[dict[str, Any]]:
    """주차별 학습 가이드 로드.
    실제 파이프라인 출력이 없으면 더미 반환.
    """
    guides = _load_jsonl(DATA_LEARNING_GUIDES / f"week_{week:02d}.jsonl")
    if guides:
        return guides

    all_guides = load_learning_guides()
    week_guides = [g for g in all_guides if g.get("week") == week]
    return week_guides if week_guides else all_guides

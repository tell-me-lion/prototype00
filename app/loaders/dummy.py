"""
data/dummy/ 에서 JSON 로드.
- pipeline.paths.DATA_DUMMY 사용, UTF-8 인코딩.
- Phase 1: 더미 기반 API용. 실전 전환 시 제거·실제 산출물 디렉터리 사용.
"""

import json
from pathlib import Path
from typing import Any

from pipeline.paths import DATA_DUMMY


def _load_json(filename: str) -> list[dict[str, Any]]:
    path = DATA_DUMMY / filename
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, list) else [data]


def load_concepts() -> list[dict[str, Any]]:
    """핵심 개념 더미 (ep_concepts 형식)."""
    return _load_json("concepts.json")


def load_learning_points() -> list[dict[str, Any]]:
    """학습 포인트 더미 (ep_concepts 형식)."""
    return _load_json("learning_points.json")


def load_quizzes() -> list[dict[str, Any]]:
    """퀴즈 더미 (quizzes_validated 형식)."""
    return _load_json("quizzes.json")


def load_learning_guides() -> list[dict[str, Any]]:
    """주차별 학습 가이드·핵심 요약 더미 (learning_guides 형식)."""
    return _load_json("learning_guides.json")

"""데이터 로딩 모듈 (더미·실제 산출물)."""

from app.loaders.dummy import (
    load_concepts,
    load_learning_guides,
    load_learning_points,
    load_quizzes,
)

__all__ = [
    "load_concepts",
    "load_learning_points",
    "load_quizzes",
    "load_learning_guides",
]

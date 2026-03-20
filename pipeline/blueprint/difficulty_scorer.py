"""Blueprint 블록: 난이도 결정."""

from typing import Any


def score_difficulty(
    dominant_type: str,
    related_concepts: list[str],
) -> str:
    """dominant_type과 related_concepts 기반으로 난이도 결정.

    우선순위 (위에서 아래로 첫 번째 해당 조건 적용):
    1. dominant_type이 "warning" 또는 "comparison" → "상"
    2. related_concepts 3개 이상 → "상"
    3. dominant_type이 "procedure" 또는 "example" → "중"
    4. 그 외 → "하"

    Args:
        dominant_type: resolve_dominant_type() 결과.
        related_concepts: ConceptDocument.related_concepts (list[str]).

    Returns:
        difficulty (str): "상", "중", "하"
    """
    # 우선순위 1: dominant_type 경고/비교
    if dominant_type in ("warning", "comparison"):
        return "상"

    # 우선순위 2: related_concepts 3개 이상
    if len(related_concepts) >= 3:
        return "상"

    # 우선순위 3: dominant_type 절차/사례
    if dominant_type in ("procedure", "example"):
        return "중"

    # 우선순위 4: 기타
    return "하"

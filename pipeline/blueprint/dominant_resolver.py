"""Blueprint 블록: 지배적 문장 타입 결정 (dominant_type)."""

from typing import Any


def resolve_dominant_type(
    linked_chunks: list[dict[str, Any]],
) -> str:
    """연결된 청크들의 sentence_types 분포에서 dominant_type을 결정.

    알고리즘:
    - 각 청크의 facts와 sentence_types를 매핑 (1:1 대응)
    - 첫 번째 청크(시간순)의 타입들에 2배 가중치 적용
    - 나머지 청크의 타입들은 1배 가중치
    - 최고 가중치 타입을 dominant_type으로 선택

    Args:
        linked_chunks: chunk_linker가 반환한 청크 리스트 (시간순 정렬됨).
                      각 청크는 {"facts": list[str], "sentence_types": list[str], ...} 포함.

    Returns:
        dominant_type (str). 예: "definition", "warning", "comparison", "procedure", "example".
        linked_chunks가 비어있으면 "unknown" 반환.
    """
    if not linked_chunks:
        return "unknown"

    type_weights: dict[str, float] = {}

    for idx, chunk in enumerate(linked_chunks):
        facts: list[str] = chunk.get("facts", [])
        sentence_types: list[str] = chunk.get("sentence_types", [])
        weight = 2.0 if idx == 0 else 1.0  # 첫 청크 2배 가중치

        # facts와 sentence_types를 매핑 (1:1 대응)
        for i, sent_type in enumerate(sentence_types):
            if i < len(facts):  # 범위 체크
                type_weights[sent_type] = type_weights.get(sent_type, 0.0) + weight

    # 최고 가중치 타입 선택
    if not type_weights:
        return "unknown"

    dominant = max(type_weights.items(), key=lambda x: x[1])[0]
    return dominant

"""Blueprint 블록: 정답 근거 사실(correct_fact) 선정."""

from typing import Any

from pipeline.ep.concept_extractor import _is_subject_of


def select_correct_fact(
    concept: str,
    linked_chunks: list[dict[str, Any]],
) -> str:
    """linked_chunks에서 correct_fact 1개를 선정.

    선정 우선순위:
    1. concept 키워드 포함 + facts 리스트 중 시간순(첫 청크→마지막 청크) 첫 번째
    2. 전체 facts 리스트 중 가장 긴 문장
    3. 없으면 빈 문자열 → runner에서 SKIP

    주어 필터링: _is_subject_of(concept, fact)를 사용해 개념이 주어인 fact만 고려.
    facts 리스트는 is_correct=True (올바른 사실)을 의미하고,
    warnings 리스트는 is_correct=False (주의사항)을 의미한다.

    Args:
        concept: 개념명.
        linked_chunks: chunk_linker 반환값 (시간순 정렬).
                      각 청크는 {"facts": list[str], ...} 포함.

    Returns:
        선정된 correct_fact (str). 없으면 "".
    """
    # 우선순위 1: concept 키워드 포함 + facts 리스트 + 시간순 첫 번째
    for chunk in linked_chunks:
        facts: list[str] = chunk.get("facts", [])
        for fact in facts:
            if _is_subject_of(concept, fact):
                return fact

    # 우선순위 2: facts 리스트 중 가장 긴 문장
    max_fact = ""
    max_len = 0
    for chunk in linked_chunks:
        facts: list[str] = chunk.get("facts", [])
        for fact in facts:
            if len(fact) > max_len:
                max_fact = fact
                max_len = len(fact)

    if max_fact:
        return max_fact

    # 우선순위 3: 없으면 빈 문자열
    return ""

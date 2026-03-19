"""Blueprint 블록: 개념 풀(conception_pool) 구성."""

from typing import Any


def build_conception_pool(
    linked_chunks: list[dict[str, Any]],
) -> list[str]:
    """linked_chunks의 facts 리스트에서 conception_pool을 구성.

    제약 조건:
    - facts 리스트만 포함 (warnings는 제외, 오답 절대 금지)
    - linked_chunks 내 모든 facts를 순회해 수집
    - 순서: 청크 순서 → 청크 내 fact 순서 유지

    Args:
        linked_chunks: chunk_linker 반환값 (시간순 정렬).
                      각 청크는 {"facts": list[str], ...} 포함.

    Returns:
        conception_pool (list[str]): facts 리스트의 모든 문장들.
    """
    pool: list[str] = []

    for chunk in linked_chunks:
        facts: list[str] = chunk.get("facts", [])
        for fact in facts:
            if fact:  # 빈 문자열 제외
                pool.append(fact)

    return pool

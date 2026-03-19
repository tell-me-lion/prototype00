"""Blueprint 블록: 개념-청크 직접 연결."""

from typing import Any

from pipeline.ep.schema import ConceptDocument


def link_chunks(
    concept: ConceptDocument,
    all_chunks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """concept.source_chunk_ids에 포함된 청크만 반환.

    모든 청크를 검색하는 대신, EP 블록이 이미 식별한
    source_chunk_ids를 직접 사용하여 연결된 청크만 추출한다.

    반환 순서는 concept.source_chunk_ids 순서를 따른다
    (시간순 정렬이 보장된 경우 그 순서를 유지).

    Args:
        concept: 청크를 연결할 대상 개념.
        all_chunks: phase5_facts 청크 전체 목록.

    Returns:
        concept.source_chunk_ids에 해당하는 청크 목록.
        source_chunk_ids에 있지만 all_chunks에 없는 ID는 조용히 무시.
    """
    chunk_map: dict[str, dict[str, Any]] = {
        c["chunk_id"]: c for c in all_chunks
    }
    return [
        chunk_map[cid]
        for cid in concept.source_chunk_ids
        if cid in chunk_map
    ]

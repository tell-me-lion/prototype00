"""Blueprint 블록: 퀴즈 블루프린트 설계 (v6 슬림화).

규칙 기반 판단(dominant_type, learning_goal, difficulty, review_point)은 제거.
BP의 역할: Evidence 분리(correct_facts / distractor_facts) + 메타데이터 전달.
"""

from typing import Any

from pipeline.ep.concept_extractor import _is_subject_of
from pipeline.ep.schema import ConceptDocument

from .chunk_linker import link_chunks
from .fact_selector import select_correct_fact
from .pool_builder import build_conception_pool
from .schema import BlueprintDocument, Evidence


def design_blueprints(
    concepts: list[ConceptDocument],
    chunks: list[dict[str, Any]],
) -> tuple[list[BlueprintDocument], list[str]]:
    """ConceptDocument 목록을 BlueprintDocument 목록으로 변환.

    각 개념에 대해:
    1. 연결된 청크 추출 (chunk_linker)
    2. correct_fact 선정 (fact_selector)
    3. conception_pool 검증 (pool_builder)
    4. Evidence 구성 (correct_facts, distractor_facts)
    5. chunk_distance_minutes 계산
    6. BlueprintDocument 생성

    Args:
        concepts: EP 블록이 생성한 ConceptDocument 목록.
        chunks: phase5_facts 청크 목록.

    Returns:
        (blueprints: list[BlueprintDocument], skipped: list[str])
        skipped는 건너뛴 개념명 목록 (로깅용).
    """
    blueprints: list[BlueprintDocument] = []
    skipped: list[str] = []

    for concept in concepts:
        # 1단계: 연결된 청크 추출
        linked_chunks = link_chunks(concept, chunks)
        if not linked_chunks:
            skipped.append(f"{concept.concept} - matched_chunks 없음")
            continue

        # 2단계: correct_fact 선정
        correct_fact = select_correct_fact(concept.concept, linked_chunks)
        if not correct_fact:
            skipped.append(f"{concept.concept} - correct_fact 없음")
            continue

        # 3단계: conception_pool 검증 (SKIP 조건용)
        conception_pool = build_conception_pool(linked_chunks)
        if not conception_pool:
            skipped.append(f"{concept.concept} - conception_pool 비어있음")
            continue

        # 4단계: Evidence 구성
        evidence = _build_evidence(
            concept.concept,
            linked_chunks,
            correct_fact,
            chunks,
            concept.related_concepts,
        )

        # 5단계: chunk_distance_minutes 계산
        chunk_distance_minutes = _calculate_chunk_distance(linked_chunks)

        # BlueprintDocument 생성
        blueprint = BlueprintDocument(
            blueprint_id="bp_" + concept.concept.lower().replace(" ", "_"),
            lecture_id=concept.lecture_id,
            week=concept.week,
            concept=concept.concept,
            definition=concept.definition,
            importance=concept.importance,
            related_concepts=concept.related_concepts,
            chunk_distance_minutes=chunk_distance_minutes,
            evidence=evidence,
        )

        blueprints.append(blueprint)

    return blueprints, skipped


# ================== 내부 함수 ==================


def _build_evidence(
    concept: str,
    linked_chunks: list[dict[str, Any]],
    correct_fact: str,
    all_chunks: list[dict[str, Any]],
    related_concepts: list[str],
) -> Evidence:
    """Evidence 객체 구성.

    correct_facts: [correct_fact]
    distractor_facts: 같은 청크의 나머지 facts + 관련 개념의 correct_facts
    distractor_sources: {"same_chunk": ..., "related": ...}
    """
    chunk_ids = [c["chunk_id"] for c in linked_chunks]

    correct_facts = [correct_fact]

    distractor_facts: list[str] = []
    same_chunk_count = 0
    related_count = 0

    # 1. 같은 청크의 나머지 facts
    for chunk in linked_chunks:
        facts: list[str] = chunk.get("facts", [])
        for fact in facts:
            if fact and fact != correct_fact:
                distractor_facts.append(fact)
                same_chunk_count += 1

    # 2. related_concepts의 correct_facts (개념이 주어인 facts)
    related_concept_pool: dict[str, list[str]] = {}
    for related_cid in related_concepts:
        if not related_cid.startswith("concept_"):
            continue
        related_name = related_cid[len("concept_"):].replace("_", " ")
        related_concept_pool[related_name] = []

    for chunk in all_chunks:
        facts: list[str] = chunk.get("facts", [])
        for fact in facts:
            for related_name in related_concept_pool.keys():
                if _is_subject_of(related_name, fact) and fact not in distractor_facts:
                    distractor_facts.append(fact)
                    related_count += 1
                    break

    distractor_sources = {"same_chunk": same_chunk_count, "related": related_count}

    return Evidence(
        chunk_ids=chunk_ids,
        correct_facts=correct_facts,
        distractor_facts=distractor_facts,
        distractor_sources=distractor_sources,
    )


def _calculate_chunk_distance(linked_chunks: list[dict[str, Any]]) -> float:
    """첫 번째와 마지막 청크 사이의 시간 거리(분) 계산.

    시간 형식: "HH:MM:SS"
    """
    if len(linked_chunks) < 2:
        return 0.0

    def time_to_minutes(time_str: str) -> float:
        """HH:MM:SS를 분 단위로 변환."""
        try:
            parts = time_str.split(":")
            hours = int(parts[0])
            minutes = int(parts[1])
            seconds = int(parts[2])
            return hours * 60 + minutes + seconds / 60
        except (IndexError, ValueError):
            return 0.0

    first_time = linked_chunks[0].get("time", "00:00:00")
    last_time = linked_chunks[-1].get("time", "00:00:00")

    return round(abs(time_to_minutes(last_time) - time_to_minutes(first_time)), 1)

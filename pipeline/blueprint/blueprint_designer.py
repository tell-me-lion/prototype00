"""Blueprint 블록: 퀴즈 블루프린트 설계."""

from typing import Any

from pipeline.ep.concept_extractor import _is_subject_of
from pipeline.ep.schema import ConceptDocument

from .chunk_linker import link_chunks
from .dominant_resolver import resolve_dominant_type
from .difficulty_scorer import score_difficulty
from .fact_selector import select_correct_fact
from .goal_mapper import map_learning_goal_and_types
from .pool_builder import build_conception_pool
from .schema import BlueprintDocument, Evidence


def design_blueprints(
    concepts: list[ConceptDocument],
    chunks: list[dict[str, Any]],
) -> tuple[list[BlueprintDocument], list[str]]:
    """ConceptDocument 목록을 BlueprintDocument 목록으로 변환.

    각 개념에 대해:
    1. 연결된 청크 추출 (chunk_linker)
    2. dominant_type 결정 (dominant_resolver)
    3. learning_goal + question_type_candidates 매핑 (goal_mapper)
    4. correct_fact 선정 (fact_selector)
    5. conception_pool 구성 (pool_builder)
    6. 난이도 결정 (difficulty_scorer)
    7. Evidence 구성 (correct_facts, distractor_facts, distractor_sources)
    8. BlueprintDocument 생성

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

        # 2단계: dominant_type 결정
        dominant_type = resolve_dominant_type(linked_chunks)

        # 3단계: learning_goal + question_type_candidates 매핑
        learning_goal, question_type_candidates = map_learning_goal_and_types(
            concept.concept, dominant_type
        )

        # 4단계: correct_fact 선정
        correct_fact = select_correct_fact(concept.concept, linked_chunks)
        if not correct_fact:
            skipped.append(f"{concept.concept} - correct_fact 없음")
            continue

        # 5단계: conception_pool 구성
        conception_pool = build_conception_pool(linked_chunks)
        if not conception_pool:
            skipped.append(f"{concept.concept} - conception_pool 비어있음")
            continue

        # 6단계: 난이도 결정
        difficulty = score_difficulty(dominant_type, concept.related_concepts)

        # 7단계: Evidence 구성
        evidence = _build_evidence(
            concept.concept,
            linked_chunks,
            correct_fact,
            chunks,
            concept.related_concepts,
        )

        # 8단계: chunk_distance_minutes 계산
        chunk_distance_minutes = _calculate_chunk_distance(linked_chunks)

        # 9단계: review_point 생성
        review_point = _generate_review_point(concept.concept, dominant_type)

        # BlueprintDocument 생성
        blueprint = BlueprintDocument(
            blueprint_id="bp_" + concept.concept.lower().replace(" ", "_"),
            lecture_id=concept.lecture_id,
            week=concept.week,
            concept=concept.concept,
            sentence_types=dominant_type,
            learning_goal=learning_goal,
            question_type_candidates=question_type_candidates,
            difficulty=difficulty,
            chunk_distance_minutes=chunk_distance_minutes,
            review_point=review_point,
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

    # correct_facts: correct_fact 1개만
    correct_facts = [correct_fact]

    # distractor_facts: same_chunk + related sources
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
        related_name = related_cid[len("concept_") :].replace("_", " ")
        related_concept_pool[related_name] = []

    # all_chunks에서 related_concepts이 주어인 facts 수집
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

    first_minutes = time_to_minutes(first_time)
    last_minutes = time_to_minutes(last_time)

    return round(abs(last_minutes - first_minutes), 1)


def _generate_review_point(concept: str, dominant_type: str) -> str:
    """학습 복습 포인트 생성.

    dominant_type별 템플릿:
    - definition: "개념과 정의 복습"
    - comparison: "개념 간 차이점 복습"
    - warning: "주의사항 인식"
    - procedure: "절차와 단계 복습"
    - example: "구체적 사례 복습"
    """
    templates = {
        "definition": f"{concept}의 핵심 정의와 역할 복습",
        "comparison": f"{concept}과 관련 개념의 차이점 복습",
        "warning": f"{concept} 사용 시 주의할 점 복습",
        "procedure": f"{concept}의 절차와 단계 복습",
        "example": f"{concept}의 구체적 사례와 활용 복습",
    }
    return templates.get(dominant_type, f"{concept}의 핵심 내용 복습")

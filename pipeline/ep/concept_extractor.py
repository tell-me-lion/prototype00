"""EP 블록: 핵심 개념 추출."""

import re
from typing import Any

from .schema import ConceptDocument

# ================== 설정 상수 ==================

TFIDF_THRESHOLD = 1.0
"""TF-IDF 점수 최소값. 이 이상인 키워드만 개념 후보로 고려."""


IMPORTANCE_FREQ_WEIGHT = 0.5
"""중요도 계산에서 빈도 신호의 가중치."""

IMPORTANCE_TFIDF_WEIGHT = 0.3
"""중요도 계산에서 TF-IDF 신호의 가중치."""

IMPORTANCE_EMPHASIS_WEIGHT = 0.2
"""중요도 계산에서 강조 표현 신호의 가중치."""

EMPHASIS_EXPRESSIONS = [
    "중요",
    "핵심",
    "반드시",
    "꼭",
    "주의",
    "꼭 기억",
    "반드시 알아야",
    "핵심은",
]
"""강조 표현 목록."""

SUBJECT_SUFFIXES = ["는", "이", "가", "란", "이란", "은"]
"""주어 판별에 사용하는 조사/어미 목록."""


# ================== 개념 추출 ==================


def extract_concepts(
    chunks: list[dict[str, Any]],
    lecture_id: str,
    week: int,
) -> list[ConceptDocument]:
    """phase5_facts 청크에서 핵심 개념을 추출.

    Args:
        chunks: phase5_facts의 청크 리스트.
        lecture_id: 강의 ID.
        week: 강의 주차.

    Returns:
        ConceptDocument 리스트.
    """
    # 1단계: 개념 후보 수집 — definition 문장의 주어인 키워드만
    keywords_pool = _collect_keywords(chunks)

    if not keywords_pool:
        return []

    # 2단계: 각 개념별 importance 계산
    importance_scores = _calculate_importance(keywords_pool, chunks)

    # used_definitions: definition 중복 방지를 위한 세트
    used_definitions: set[str] = set()

    # 중요도 높은 개념부터 definition을 먼저 배정받도록 정렬
    sorted_keywords = sorted(
        keywords_pool.items(),
        key=lambda item: importance_scores.get(item[0], 0.0),
        reverse=True,
    )

    # 3단계: ConceptDocument 생성
    concepts = []
    for keyword, metadata in sorted_keywords:
        concept_id = _make_concept_id(keyword)
        definition = _pick_definition(keyword, chunks, used_definitions)

        importance = importance_scores.get(keyword, 0.0)

        doc = ConceptDocument(
            concept_id=concept_id,
            concept=keyword,
            definition=definition,
            related_concepts=[],  # 4단계에서 추가
            source_chunk_ids=sorted(metadata["chunks"]),
            week=week,
            lecture_id=lecture_id,
            importance=importance,
        )
        concepts.append(doc)

    # 4단계: related_concepts 연결
    concepts = _link_related_concepts(concepts, chunks)

    # 중요도 내림차순 정렬
    concepts.sort(key=lambda x: x.importance, reverse=True)

    return concepts


# ================== 1단계: 개념 후보 수집 ==================


def _is_subject_of(keyword: str, fact: str) -> bool:
    """fact 문장에서 keyword가 주어로 등장하는지 확인.

    주어 판별 기준: fact가 keyword(+조사/어미)로 시작하는가.
    폴백 없음 — 단순 포함은 보조 개념을 핵심 개념으로 오분류하므로 금지.

    예:
        "서브쿼리는 SELECT 문 안에..." → 서브쿼리: True
        "서브쿼리는 WHERE, HAVING..."  → WHERE: False  ← 기존 버그 케이스
        "CAST 함수에는 VARCHAR를..."   → VARCHAR: False
    """
    keyword_lower = keyword.lower()
    fact_lower = fact.lower()

    # keyword 자체로 시작 (영문 대소문자 무시)
    if fact_lower.startswith(keyword_lower + " "):
        return True

    # keyword + 조사/어미로 시작
    for suffix in SUBJECT_SUFFIXES:
        if fact_lower.startswith(keyword_lower + suffix):
            return True

    return False


def _collect_keywords(chunks: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """모든 fact에서 주어인 키워드만 수집 (sentence_type 무관).

    핵심 개념 / 보조 개념 분리 전략:
      - 모든 fact를 순회하며 keyword가 주어인지 _is_subject_of()로 판별
      - 주어가 아닌 키워드(NULL, VARCHAR, WHERE 등)는 수집하지 않음
      - sentence_type은 신뢰하지 않음 (인덱스 불일치 + 오분류 문제)

    Returns:
        {
            keyword: {
                "freq": int,        # 주어로 등장한 fact 수
                "max_tfidf": float,
                "chunks": set[str]  # 등장한 chunk_id 집합
            }
        }
    """
    keywords_pool: dict[str, dict[str, Any]] = {}

    for chunk in chunks:
        tfidf_scores = chunk.get("tfidf_scores", {})
        facts = chunk.get("facts", [])

        # ✓ sentence_type 체크 제거 (버그: 인덱스 불일치, 오분류)
        # 주어 조건만으로 충분함 (보조 개념 필터링, 핵심 개념 포함)
        for fact in facts:
            # 이 fact에서 주어인 tfidf 키워드만 수집
            for keyword, tfidf in tfidf_scores.items():
                if tfidf < TFIDF_THRESHOLD:
                    continue

                if not _is_subject_of(keyword, fact):
                    continue  # 주어가 아니면 보조 개념 — 수집 제외

                if keyword not in keywords_pool:
                    keywords_pool[keyword] = {
                        "freq": 0,
                        "max_tfidf": 0.0,
                        "chunks": set(),
                    }

                keywords_pool[keyword]["freq"] += 1
                keywords_pool[keyword]["max_tfidf"] = max(
                    keywords_pool[keyword]["max_tfidf"], tfidf
                )
                keywords_pool[keyword]["chunks"].add(chunk["chunk_id"])

    return keywords_pool


# ================== 2단계: importance 계산 ==================


def _calculate_importance(
    keywords_pool: dict[str, dict[str, Any]],
    chunks: list[dict[str, Any]],
) -> dict[str, float]:
    """importance = freq_score × 0.5 + tfidf_score × 0.3 + emphasis_score × 0.2.

    Args:
        keywords_pool: _collect_keywords() 결과.
        chunks: 청크 리스트.

    Returns:
        {keyword: importance (0.0 ~ 1.0)}
    """
    importance_scores: dict[str, float] = {}
    total_chunks = len(chunks)

    global_max_tfidf = max(
        (meta["max_tfidf"] for meta in keywords_pool.values()),
        default=1.0,
    )
    if global_max_tfidf == 0.0:
        global_max_tfidf = 1.0

    for keyword, metadata in keywords_pool.items():
        freq = metadata["freq"]
        chunk_ids = metadata["chunks"]

        freq_score = freq / total_chunks if total_chunks > 0 else 0.0
        tfidf_score = metadata["max_tfidf"] / global_max_tfidf

        emphasis_count = sum(
            1 for chunk in chunks
            if chunk["chunk_id"] in chunk_ids
            and any(expr in chunk.get("text", "") for expr in EMPHASIS_EXPRESSIONS)
        )
        emphasis_score = emphasis_count / freq if freq > 0 else 0.0

        importance = (
            freq_score * IMPORTANCE_FREQ_WEIGHT
            + tfidf_score * IMPORTANCE_TFIDF_WEIGHT
            + emphasis_score * IMPORTANCE_EMPHASIS_WEIGHT
        )
        importance_scores[keyword] = round(min(1.0, max(0.0, importance)), 3)

    return importance_scores


# ================== 3단계: definition 선택 ==================


def _pick_definition(
    keyword: str,
    chunks: list[dict[str, Any]],
    used_definitions: set[str],
) -> str:
    """개념의 정의를 선택.

    우선순위:
    1. sentence_type="definition" + keyword가 주어 + 미사용
    2. sentence_type="definition" + keyword 포함 + 미사용
    3. keyword가 주어 + 미사용
    4. keyword 포함 + 미사용 (가장 긴 것)
    fallback 1: keyword 포함 (used_definitions 무시)
    fallback 2: 가장 긴 fact
    """
    keyword_lower = keyword.lower()

    priority_1: list[str] = []
    priority_2: list[str] = []
    priority_3: list[str] = []
    priority_4: list[str] = []
    all_facts: list[str] = []

    for chunk in chunks:
        facts = chunk.get("facts", [])
        sentence_types = chunk.get("sentence_types", [])

        for i, fact in enumerate(facts):
            all_facts.append(fact)

            sent_type = sentence_types[i] if i < len(sentence_types) else ""
            is_definition = "definition" in sent_type
            is_unused = fact not in used_definitions
            is_kw_subject = _is_subject_of(keyword, fact)
            has_keyword = keyword_lower in fact.lower()

            if is_definition and is_kw_subject and is_unused:
                priority_1.append(fact)
            elif is_definition and has_keyword and is_unused:
                priority_2.append(fact)
            elif is_kw_subject and is_unused:
                priority_3.append(fact)
            elif has_keyword and is_unused:
                priority_4.append(fact)

    for candidates in [priority_1, priority_2, priority_3, priority_4]:
        if candidates:
            chosen = max(candidates, key=len)
            used_definitions.add(chosen)
            return chosen

    # fallback 1: keyword 포함 (used_definitions 제약 해제)
    fallback = [f for f in all_facts if keyword_lower in f.lower()]
    if fallback:
        chosen = max(fallback, key=len)
        used_definitions.add(chosen)
        return chosen

    # fallback 2: 가장 긴 fact
    if all_facts:
        return max(all_facts, key=len)

    return f"{keyword}에 대한 정의를 찾을 수 없습니다."


# ================== 4단계: related_concepts 연결 ==================


def _link_related_concepts(
    concepts: list[ConceptDocument],
    chunks: list[dict[str, Any]],
) -> list[ConceptDocument]:
    """같은 fact(문장)에 공동 출현하는 개념을 related_concepts로 연결.

    각 fact를 순회하며 어떤 개념의 키워드가 포함되는지 확인.
    같은 fact에 두 개념이 모두 언급되면 서로 연관 개념으로 추가.
    최소 1개 보장: 공동 출현이 없으면 importance 가장 높은 타 개념을 강제 연결.
    """
    # concept_id -> keyword(소문자) 매핑
    concept_kw: dict[str, str] = {c.concept_id: c.concept.lower() for c in concepts}

    # {concept_id: set[concept_id]} — fact에서 공동 출현한 개념 집합
    co_occurrence: dict[str, set[str]] = {c.concept_id: set() for c in concepts}

    for chunk in chunks:
        for fact in chunk.get("facts", []):
            fact_lower = fact.lower()

            # 이 fact에 언급된 개념 목록
            present = [cid for cid, kw in concept_kw.items() if kw in fact_lower]

            # 공동 출현 기록 (같은 fact에 함께 등장한 개념 쌍)
            for cid_i in present:
                for cid_j in present:
                    if cid_i != cid_j:
                        co_occurrence[cid_i].add(cid_j)

    for concept in concepts:
        related = list(co_occurrence[concept.concept_id])

        # 최소 1개 보장: 공동 출현 없으면 importance 최고인 타 개념 연결
        if not related:
            others = [c for c in concepts if c.concept_id != concept.concept_id]
            if others:
                best = max(others, key=lambda c: c.importance)
                related = [best.concept_id]

        concept.related_concepts = related

    return concepts


# ================== 헬퍼 함수 ==================


def _make_concept_id(concept: str) -> str:
    """concept_id 생성.

    규칙: "concept_" + concept.lower().replace(" ", "_")
    """
    return "concept_" + concept.lower().replace(" ", "_")
"""EP 블록: 핵심 개념 추출."""

import re
from typing import Any

from .schema import ConceptDocument
from .tfidf_engine import compute_lecture_tfidf
from .stopwords import STOPWORDS

# ================== 설정 상수 ==================

TFIDF_THRESHOLD = 0.05
"""TF-IDF 점수 최소값. sklearn 원시 점수(0.0~1.0) 기준. 이 이상인 키워드만 개념 후보로 고려."""


IMPORTANCE_FREQ_WEIGHT = 0.2
"""중요도 계산에서 빈도 신호의 가중치. (v10: 0.5→0.2, 범용어 파일/객체 순위 하향)"""

IMPORTANCE_TFIDF_WEIGHT = 0.5
"""중요도 계산에서 TF-IDF 신호의 가중치. (v10: 0.3→0.5, 도메인 특화 개념 순위 상향)"""

IMPORTANCE_EMPHASIS_WEIGHT = 0.3
"""중요도 계산에서 강조 표현 신호의 가중치. (v10: 0.2→0.3)"""

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

TFIDF_HIGH_THRESHOLD = 0.1
"""투 트랙 유연 매칭의 진입 TF-IDF 임계값.
이 이상인 키워드는 문장 내 어느 위치든 조사 결합 여부로 판단."""

DEFINITION_SUFFIXES = ["은", "는", "이", "가", "란", "이란", "이라고", "라고", "이라", "이다"]
"""Track 2 정의형 매칭에 사용하는 조사/어미 목록.
주격(은/는/이/가), 주제 접미사(란/이란), 서술어보어(이라고/라고/이라/이다) 포함.
목적격(을/를) 제외: 목적어 위치는 정의 관계를 나타내지 않는다.
(v11: FLEXIBLE_SUFFIXES → DEFINITION_SUFFIXES, 을/를 제거)"""

MIN_SOURCE_CHUNKS = 2
"""STT 노이즈 필터: 최소 N개 이상의 청크에 등장한 개념만 유지.
단일 청크에만 등장하는 오타(바바, 역슬러시, 아이오 등)를 제거."""


# ================== 개념 추출 ==================


def _has_quality_tfidf(chunks: list[dict[str, Any]]) -> bool:
    """phase5 청크가 품질 있는 tfidf_scores를 제공하는지 확인.

    품질 기준: 절반 이상의 청크가 비어있지 않은 dict 형태의 tfidf_scores를 가짐.
    (v11: kiwipiepy 재계산을 건너뛰는 조건 판별용)
    """
    if not chunks:
        return False
    scored = sum(
        1 for c in chunks
        if isinstance(c.get("tfidf_scores"), dict) and c.get("tfidf_scores")
    )
    return scored >= len(chunks) // 2


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
    # ── TF-IDF 조건부 재사용 (v11: 품질 기준 도입) ──
    if _has_quality_tfidf(chunks):
        # phase5 tfidf_scores 재사용 — kiwipiepy 재계산 생략
        # phase5 점수가 1.0 초과(원시 가중치)면 0~1 범위로 정규화
        for chunk in chunks:
            scores = chunk.get("tfidf_scores", {})
            if scores and isinstance(scores, dict):
                max_s = max(scores.values(), default=1.0)
                if max_s > 1.0:
                    chunk["tfidf_scores"] = {k: round(v / max_s, 4) for k, v in scores.items()}
        new_tfidf = {
            c["chunk_id"]: c.get("tfidf_scores", {})
            for c in chunks if c.get("chunk_id")
        }
    else:
        # 폴백: phase5가 flat list이거나 tfidf_scores가 없는 경우 kiwipiepy 재계산
        new_tfidf = compute_lecture_tfidf(chunks)
        for chunk in chunks:
            cid = chunk.get("chunk_id", "")
            if cid in new_tfidf:
                chunk["tfidf_scores"] = new_tfidf[cid]

    # 1단계: 개념 후보 수집 — definition 문장의 주어인 키워드만
    keywords_pool = _collect_keywords(chunks)

    # STT 노이즈 필터: 강의 전체 텍스트에서 언급된 청크 수 기준으로 필터링
    # (v10: 주어매칭 횟수가 아닌 전체 텍스트 등장 횟수로 변경)
    # → "직렬", "스레드" 등 한 번만 정의된 핵심 개념이 살아남음
    valid_keywords = {}
    for k, v in keywords_pool.items():
        mention_count = sum(
            1 for c in chunks if k.lower() in c.get("text", "").lower()
        )
        if mention_count >= MIN_SOURCE_CHUNKS:
            valid_keywords[k] = v
    keywords_pool = valid_keywords

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

    # 4단계: related_concepts 연결 (TF-IDF 코사인 유사도 폴백 포함)
    concepts = _link_related_concepts(concepts, chunks, tfidf_vectors=new_tfidf)

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


def _has_particle_match(keyword: str, fact: str, suffixes: list[str]) -> bool:
    """키워드가 문장 어디서든 지정된 조사/어미와 결합되어 등장하는지 확인.

    Track 2 (정의형) 매칭에 사용.
    예: _has_particle_match("직렬", "처리 방식을 직렬이라고 한다.", DEFINITION_SUFFIXES)
        → True  (keyword + "이라고" 패턴 발견)

    Args:
        keyword: 검색할 키워드.
        fact: 검색 대상 문장.
        suffixes: 허용할 조사/어미 목록.

    Returns:
        keyword + 임의 suffix 패턴이 fact 내 발견되면 True.
    """
    keyword_lower = keyword.lower()
    fact_lower = fact.lower()
    for suffix in suffixes:
        if re.search(re.escape(keyword_lower) + re.escape(suffix), fact_lower):
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

                # 불용어 필터: 기술 분야와 무관한 일반 명사 제거
                if keyword in STOPWORDS:
                    continue

                # ── 투 트랙 매칭 ──────────────────────────────────────────────────
                # Track 1 (보수적): 낮은 TF-IDF — 문장 시작 주어 위치만 허용
                is_valid = _is_subject_of(keyword, fact)

                # Track 2 (유연): 높은 TF-IDF — 문장 내 어디서든 정의형 조사 결합 허용
                # "B를 A이라고 한다" 같은 서술어보어 정의형 패턴 포착
                if not is_valid and tfidf >= TFIDF_HIGH_THRESHOLD:
                    is_valid = _has_particle_match(keyword, fact, DEFINITION_SUFFIXES)

                if not is_valid:
                    continue

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
    """importance = freq_score × 0.2 + tfidf_score × 0.5 + emphasis_score × 0.3.

    실제 코드: IMPORTANCE_FREQ_WEIGHT=0.2, IMPORTANCE_TFIDF_WEIGHT=0.5, IMPORTANCE_EMPHASIS_WEIGHT=0.3
    (v10에서 가중치 변경됨. 독스트링 반영 누락 수정 — v11)

    Args:
        keywords_pool: _collect_keywords() 결과.
        chunks: 청크 리스트.

    Returns:
        {keyword: importance (0.0 ~ 1.0)}
    """
    importance_scores: dict[str, float] = {}

    # ── 수정: freq_score 분모를 fact가 있는 청크 수로 변경 ──
    # fact가 없는 대화용 청크가 중요도를 희석하는 것을 방지
    fact_chunk_count = sum(1 for c in chunks if c.get("facts"))
    denominator = fact_chunk_count if fact_chunk_count > 0 else len(chunks)

    global_max_tfidf = max(
        (meta["max_tfidf"] for meta in keywords_pool.values()),
        default=1.0,
    )
    if global_max_tfidf == 0.0:
        global_max_tfidf = 1.0

    for keyword, metadata in keywords_pool.items():
        freq = metadata["freq"]
        chunk_ids = metadata["chunks"]

        freq_score = freq / denominator if denominator > 0 else 0.0
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
    1. keyword가 주어 + 미사용
    2. keyword 포함 + 미사용 (가장 긴 것)
    fallback 1: keyword 포함 (used_definitions 무시)
    fallback 2: 가장 긴 fact

    참고: sentence_types는 신뢰도가 낮아 (인덱스 불일치, 오분류 가능) 미사용.
    (v11: sentence_type 기반 priority 제거)
    """
    keyword_lower = keyword.lower()

    priority_1: list[str] = []
    priority_2: list[str] = []
    all_facts: list[str] = []

    for chunk in chunks:
        facts = chunk.get("facts", [])

        for fact in facts:
            all_facts.append(fact)

            is_unused = fact not in used_definitions
            is_kw_subject = _is_subject_of(keyword, fact)
            has_keyword = keyword_lower in fact.lower()

            if is_kw_subject and is_unused:
                priority_1.append(fact)
            elif has_keyword and is_unused:
                priority_2.append(fact)

    for candidates in [priority_1, priority_2]:
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
    tfidf_vectors: dict[str, dict[str, float]] | None = None,
) -> list[ConceptDocument]:
    """같은 fact(문장)에 공동 출현하는 개념을 related_concepts로 연결.

    각 fact를 순회하며 어떤 개념의 키워드가 포함되는지 확인.
    같은 fact에 두 개념이 모두 언급되면 서로 연관 개념으로 추가.
    공동 출현이 없으면 TF-IDF 코사인 유사도로 보조 신호 추가 (폴백).
    최소 1개 보장: 연결이 없으면 importance 가장 높은 타 개념을 강제 연결.
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

    # ── TF-IDF 코사인 유사도 보조 신호 (co_occurrence가 비어있는 경우만) ──
    if tfidf_vectors:
        concept_vectors: dict[str, dict[str, float]] = {}
        for c in concepts:
            merged: dict[str, float] = {}
            for cid in c.source_chunk_ids:
                for term, score in tfidf_vectors.get(cid, {}).items():
                    merged[term] = max(merged.get(term, 0.0), score)
            concept_vectors[c.concept_id] = merged

    for concept in concepts:
        related = list(co_occurrence[concept.concept_id])

        # 공동 출현이 없고 TF-IDF 벡터가 있으면 코사인 유사도로 보조 찾기
        if not related and tfidf_vectors:
            vec_i = concept_vectors.get(concept.concept_id, {})
            if vec_i:
                best_sim = -1.0
                best_cid = None
                for other in concepts:
                    if other.concept_id == concept.concept_id:
                        continue
                    vec_j = concept_vectors.get(other.concept_id, {})
                    sim = _cosine_similarity_sparse(vec_i, vec_j)
                    if sim > best_sim:
                        best_sim = sim
                        best_cid = other.concept_id

                if best_cid and best_sim > 0.0:
                    related = [best_cid]

        concept.related_concepts = related

    return concepts


# ================== 헬퍼 함수 ==================


def _cosine_similarity_sparse(
    vec_a: dict[str, float],
    vec_b: dict[str, float],
) -> float:
    """두 스파스 벡터(dict 형태)의 코사인 유사도를 계산.

    Args:
        vec_a: {term: score} 형태의 벡터.
        vec_b: {term: score} 형태의 벡터.

    Returns:
        코사인 유사도 (0.0 ~ 1.0).
    """
    if not vec_a or not vec_b:
        return 0.0

    common = set(vec_a) & set(vec_b)
    if not common:
        return 0.0

    dot = sum(vec_a[k] * vec_b[k] for k in common)
    norm_a = sum(v * v for v in vec_a.values()) ** 0.5
    norm_b = sum(v * v for v in vec_b.values()) ** 0.5

    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0

    return dot / (norm_a * norm_b)


def _make_concept_id(concept: str) -> str:
    """concept_id 생성.

    규칙: "concept_" + concept.lower().replace(" ", "_")
    """
    return "concept_" + concept.lower().replace(" ", "_")
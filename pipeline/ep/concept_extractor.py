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

MIN_IMPORTANCE = 0.1
"""최종 출력 개념의 최소 importance 점수.
facts 주어 추출로 들어온 저신호 후보(importance=TFIDF_THRESHOLD 수준)를 걸러낸다.
(v12: 추가. 0.026 클러스터 — fragment/compound 노이즈 제거)"""


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
    # ── v12: 항상 kiwipiepy TF-IDF 재계산 ──
    # phase5의 tfidf_scores는 synthetic rank-decay (surface token 기반)
    # → kiwipiepy 형태소 기반 base form으로 재계산 필수
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
    # MIN_IMPORTANCE 이상인 개념만 유지 (0.026 노이즈 클러스터 제거)
    sorted_keywords = sorted(
        [
            item for item in keywords_pool.items()
            if importance_scores.get(item[0], 0.0) >= MIN_IMPORTANCE
        ],
        key=lambda item: importance_scores.get(item[0], 0.0),
        reverse=True,
    )

    # 3단계: ConceptDocument 생성
    concepts = []
    for keyword, metadata in sorted_keywords:
        # canonical form: keywords_pool에 저장된 선호 표기 사용 (대소문자 정규화)
        concept_name = metadata.get("_canonical", keyword)
        concept_id = _make_concept_id(concept_name)
        definition = _pick_definition(keyword, chunks, used_definitions)

        importance = importance_scores.get(keyword, 0.0)

        doc = ConceptDocument(
            concept_id=concept_id,
            concept=concept_name,
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


def _extract_fact_subject(fact: str) -> str | None:
    """fact 문장의 첫 명사 주어를 추출. (v12: 신규)

    주격 조사(SUBJECT_SUFFIXES)의 첫 출현 위치로 경계 결정.
    2~10자 사이만 반환 (1자: 대명사, 10자 초과: 복합구로 너무 넓음).

    TF-IDF 어휘에 없는 개념을 facts 주어에서 구제하는 보조 수단.
    예: "직렬화는 오브젝트 단위로..." → "직렬화"
        "버퍼는 데이터가..." → "버퍼"
        "IO 패키지는 바이트..." → "IO 패키지"
    """
    for suffix in SUBJECT_SUFFIXES:
        idx = fact.find(suffix)
        if 2 <= idx <= 10:
            return fact[:idx]
    return None


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
    """강의 전체 단위로 개념 후보 수집. (v12: 청크 경계 제약 제거)

    2단계 구조:
    1단계: 전체 chunks의 tfidf_scores를 통합해 강의 어휘 구축
    2단계: 강의 전체 facts에서 어휘별 주어 출현 검색 (청크 무관)
    보조:  facts 주어 추출로 TF-IDF 어휘 밖의 개념 구제

    개선점 (v12):
    - 청크 경계 제약 제거: TF-IDF 근거(청크A) ≠ 정의 facts(청크B)도 매칭
    - facts 주어 추출 추가: TF-IDF 어휘 밖이지만 facts에서 주어로 쓰인 개념 구제

    Returns:
        {
            keyword: {
                "freq": int,        # 주어로 등장한 fact 수
                "max_tfidf": float,
                "chunks": set[str]  # 등장한 chunk_id 집합
            }
        }
    """
    # ── 1단계: 강의 전체 TF-IDF 어휘 구축 (청크 경계 무시) ──
    # 소문자 키로 중복 제거: "io"/"IO", "nio"/"NIO" 등 케이스 변형 통합
    # canonical_form: 동일 개념의 여러 표기 중 TF-IDF 점수가 가장 높은 형태를 선택
    global_vocab: dict[str, float] = {}          # lowercase key → max score
    canonical_form: dict[str, str] = {}          # lowercase key → 선호 표기
    for chunk in chunks:
        for keyword, score in chunk.get("tfidf_scores", {}).items():
            if keyword in STOPWORDS:
                continue
            lower = keyword.lower()
            if lower in STOPWORDS:
                continue
            if score >= TFIDF_THRESHOLD:
                if lower not in global_vocab or score > global_vocab[lower]:
                    global_vocab[lower] = score
                    canonical_form[lower] = keyword  # 높은 점수 형태가 canonical

    # ── 보조: facts 주어 추출로 TF-IDF 어휘 밖 개념 보완 ──
    # TF-IDF에 없지만 facts에서 주어로 등장하고 충분히 언급되는 개념 구제
    fact_subj_candidates: set[str] = set()
    for chunk in chunks:
        for fact in chunk.get("facts", []):
            subj = _extract_fact_subject(fact)
            if subj and subj not in STOPWORDS:
                lower_subj = subj.lower()
                if lower_subj not in global_vocab and lower_subj not in STOPWORDS:
                    fact_subj_candidates.add(subj)

    for subj in fact_subj_candidates:
        lower_subj = subj.lower()
        text_freq = sum(1 for c in chunks if lower_subj in c.get("text", "").lower())
        if text_freq >= MIN_SOURCE_CHUNKS:
            global_vocab[lower_subj] = TFIDF_THRESHOLD  # 최소 점수로 삽입
            canonical_form[lower_subj] = subj

    # ── 2단계: 전체 facts에서 어휘별 주어 출현 검색 (청크 경계 무시) ──
    keywords_pool: dict[str, dict[str, Any]] = {}

    for lower_kw, max_tfidf in global_vocab.items():
        for chunk in chunks:
            for fact in chunk.get("facts", []):
                is_valid = _is_subject_of(lower_kw, fact)
                if not is_valid and max_tfidf >= TFIDF_HIGH_THRESHOLD:
                    is_valid = _has_particle_match(lower_kw, fact, DEFINITION_SUFFIXES)

                if not is_valid:
                    continue

                if lower_kw not in keywords_pool:
                    keywords_pool[lower_kw] = {
                        "freq": 0,
                        "max_tfidf": max_tfidf,
                        "chunks": set(),
                        "_canonical": canonical_form.get(lower_kw, lower_kw),
                    }
                keywords_pool[lower_kw]["freq"] += 1
                keywords_pool[lower_kw]["chunks"].add(chunk["chunk_id"])

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
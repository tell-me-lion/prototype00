"""EP 블록: 학습 포인트 추출.

핵심 개념(concept_extractor)과 달리, 실전 팁·주의사항·핵심 학습 포인트를 추출한다.
- 개념은 "X란 무엇인가" (정의형)
- 학습 포인트는 "X를 사용할 때 주의할 점", "X의 핵심 활용법" (실전형)
"""

from typing import Any

from .schema import ConceptDocument
from .stopwords import STOPWORDS

# ================== 설정 상수 ==================

LEARNING_POINT_MARKERS = [
    "주의",
    "주의할",
    "조심",
    "꼭",
    "반드시",
    "중요한",
    "핵심은",
    "팁",
    "실수",
    "실전",
    "자주 쓰는",
    "자주 사용",
    "많이 쓰는",
    "잘못",
    "헷갈",
    "주의점",
    "차이점",
    "차이는",
    "비교",
    "장점",
    "단점",
    "예를 들",
    "예시",
    "기억",
    "알아야",
    "알아두",
    "참고",
]
"""학습 포인트 신호 표현. 이 표현이 포함된 fact 문장이 학습 포인트 후보."""

MIN_FACT_LENGTH = 15
"""학습 포인트로 인정할 최소 문장 길이."""

MAX_LEARNING_POINTS = 10
"""강의당 최대 학습 포인트 수."""

MIN_SCORE = 0.1
"""최소 점수 기준."""


# ================== 학습 포인트 추출 ==================


def extract_learning_points(
    chunks: list[dict[str, Any]],
    lecture_id: str,
    week: int,
    concepts: list[ConceptDocument] | None = None,
) -> list[ConceptDocument]:
    """phase5_facts 청크에서 학습 포인트를 추출.

    학습 포인트 = 강조 표현 + 실전 팁 신호가 있는 fact 문장 중
    핵심 개념과 연관된 것을 선별.

    Args:
        chunks: phase5_facts의 청크 리스트.
        lecture_id: 강의 ID.
        week: 강의 주차.
        concepts: 이미 추출된 핵심 개념 (연관 개념 연결용). None이면 독립 추출.

    Returns:
        ConceptDocument 리스트 (학습 포인트용).
    """
    # 개념명 → concept_id 매핑 (연관 개념 연결용)
    concept_map: dict[str, str] = {}
    if concepts:
        for c in concepts:
            concept_map[c.concept.lower()] = c.concept_id

    # 1단계: 학습 포인트 후보 수집
    candidates = _collect_candidates(chunks, concept_map)

    if not candidates:
        return []

    # 2단계: 점수 계산 및 정렬
    scored = _score_candidates(candidates, chunks)

    # 3단계: 상위 N개 선택, 중복 제거
    selected = _select_top(scored, max_count=MAX_LEARNING_POINTS)

    # 4단계: ConceptDocument 형태로 변환
    results = []
    for item in selected:
        concept_name = item["concept"]
        concept_id = "lp_" + concept_name.lower().replace(" ", "_")

        related = []
        if concept_name.lower() in concept_map:
            related.append(concept_map[concept_name.lower()])

        doc = ConceptDocument.model_construct(
            concept_id=concept_id,
            concept=concept_name,
            definition=item["fact"],
            related_concepts=related,
            source_chunk_ids=sorted(item["chunk_ids"]),
            week=week,
            lecture_id=lecture_id,
            importance=item["score"],
        )
        results.append(doc)

    return results


# ================== 1단계: 후보 수집 ==================


def _collect_candidates(
    chunks: list[dict[str, Any]],
    concept_map: dict[str, str],
) -> list[dict[str, Any]]:
    """학습 포인트 후보를 수집.

    학습 포인트 마커가 포함된 fact 문장 중 충분히 긴 것을 수집.
    가능하면 관련 개념명을 연결.
    """
    candidates: list[dict[str, Any]] = []
    seen_facts: set[str] = set()

    for chunk in chunks:
        chunk_id = chunk.get("chunk_id", "")
        for fact in chunk.get("facts", []):
            if len(fact) < MIN_FACT_LENGTH:
                continue
            if fact in seen_facts:
                continue

            # 학습 포인트 마커 확인
            marker_count = sum(1 for m in LEARNING_POINT_MARKERS if m in fact)
            if marker_count == 0:
                continue

            seen_facts.add(fact)

            # 관련 개념 찾기
            related_concept = _find_related_concept(fact, concept_map)

            candidates.append({
                "fact": fact,
                "concept": related_concept or _extract_subject(fact),
                "chunk_ids": {chunk_id},
                "marker_count": marker_count,
            })

    # 같은 concept의 후보는 chunk_ids 병합
    merged: dict[str, dict[str, Any]] = {}
    for cand in candidates:
        key = cand["fact"]
        if key not in merged:
            merged[key] = cand
        else:
            merged[key]["chunk_ids"] |= cand["chunk_ids"]

    return list(merged.values())


def _find_related_concept(
    fact: str,
    concept_map: dict[str, str],
) -> str | None:
    """fact 문장에서 관련 개념명을 찾는다."""
    fact_lower = fact.lower()
    best_concept = None
    best_pos = len(fact)

    for concept_name in concept_map:
        pos = fact_lower.find(concept_name)
        if pos != -1 and pos < best_pos:
            best_pos = pos
            best_concept = concept_name

    return best_concept


def _extract_subject(fact: str) -> str:
    """fact 문장에서 간단한 주어를 추출. 개념 매칭 실패 시 폴백."""
    suffixes = ["는", "은", "이", "가", "란", "이란"]
    for suffix in suffixes:
        idx = fact.find(suffix)
        if 2 <= idx <= 15:
            subj = fact[:idx].strip()
            if subj and subj.lower() not in STOPWORDS:
                return subj
    # 폴백: 앞 10자
    return fact[:10].rstrip()


# ================== 2단계: 점수 계산 ==================


def _score_candidates(
    candidates: list[dict[str, Any]],
    chunks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """후보별 점수 계산.

    점수 = marker_count * 0.4 + fact_length_score * 0.3 + mention_score * 0.3
    """
    max_markers = max((c["marker_count"] for c in candidates), default=1)
    max_len = max((len(c["fact"]) for c in candidates), default=1)

    for cand in candidates:
        marker_score = cand["marker_count"] / max_markers if max_markers > 0 else 0
        length_score = len(cand["fact"]) / max_len if max_len > 0 else 0

        # 강의 전체에서 개념 언급 빈도
        concept_lower = (cand["concept"] or "").lower()
        mention_count = sum(
            1 for c in chunks
            if concept_lower and concept_lower in c.get("text", "").lower()
        )
        mention_score = min(1.0, mention_count / max(len(chunks), 1))

        score = marker_score * 0.4 + length_score * 0.3 + mention_score * 0.3
        cand["score"] = round(min(1.0, max(0.0, score)), 3)

    return candidates


# ================== 3단계: 상위 선택 ==================


def _select_top(
    candidates: list[dict[str, Any]],
    max_count: int,
) -> list[dict[str, Any]]:
    """점수 기준 상위 N개 선택. 같은 concept 중복 제거."""
    candidates.sort(key=lambda x: x["score"], reverse=True)

    selected = []
    seen_concepts: set[str] = set()

    for cand in candidates:
        if cand["score"] < MIN_SCORE:
            continue
        concept_key = (cand["concept"] or "").lower()
        if concept_key in seen_concepts:
            continue
        seen_concepts.add(concept_key)
        selected.append(cand)
        if len(selected) >= max_count:
            break

    return selected

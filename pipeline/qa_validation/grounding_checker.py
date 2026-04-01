"""단계 1 — 근거성 검사: source_text ↔ chunk TF-IDF 코사인 유사도.

퀴즈의 source_text가 실제 강의 chunk 원문에 근거하는지 검증한다.
scikit-learn TfidfVectorizer + cosine_similarity 사용 (임베딩 API 비용 없음).
"""

from __future__ import annotations

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

GROUNDING_THRESHOLD = 0.30
"""source_text ↔ 최대 유사 chunk 유사도 기준값. 미만이면 fail.

source_text는 chunk 원문의 LLM 패러프레이즈이므로 char n-gram TF-IDF 기준
0.30이 적절 (원문 verbatim이라면 0.75도 가능하나, 실제 데이터 중앙값 ~0.37).
"""


def check_grounding(
    quiz: dict,
    chunks: list[dict],
) -> tuple[bool, float]:
    """source_text와 가장 유사한 chunk와의 코사인 유사도를 계산한다.

    Args:
        quiz: QuizDocument dict. `source_text` 키 필수.
        chunks: phase5_facts JSONL에서 로드한 chunk dict 목록. `text` 키 필수.

    Returns:
        (passed, grounding_score)
        - passed: grounding_score >= GROUNDING_THRESHOLD
        - grounding_score: 0.0~1.0
    """
    source = quiz.get("source_text", "").strip()
    if not source:
        return False, 0.0

    chunk_texts = [c.get("text", "") for c in chunks if c.get("text", "").strip()]
    if not chunk_texts:
        return False, 0.0

    vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4))
    all_texts = [source] + chunk_texts
    try:
        matrix = vectorizer.fit_transform(all_texts)
    except ValueError:
        return False, 0.0

    sims = cosine_similarity(matrix[0:1], matrix[1:])[0]
    max_score = float(sims.max())
    return max_score >= GROUNDING_THRESHOLD, round(max_score, 4)

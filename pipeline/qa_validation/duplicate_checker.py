"""단계 2 — 중복 검사: 동일 blueprint 내 question 유사도.

같은 blueprint_id에서 이미 처리된 퀴즈와 question이 유사하면 폐기한다.
중복 fail은 재생성 없이 즉시 폐기 (used_count 증가 없음).
"""

from __future__ import annotations

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

DUPLICATE_THRESHOLD = 0.85
"""기존 퀴즈 question과의 유사도 기준값. 이상이면 중복으로 폐기."""


def check_duplicate(
    quiz: dict,
    seen_questions: list[str],
) -> tuple[bool, float]:
    """quiz.question이 seen_questions 중 하나와 유사한지 검사한다.

    Args:
        quiz: QuizDocument dict. `question` 키 필수.
        seen_questions: 동일 blueprint_id에서 이미 통과한 question 문자열 목록.

    Returns:
        (passed, max_similarity)
        - passed: max_similarity < DUPLICATE_THRESHOLD (중복 없음)
        - max_similarity: 가장 유사한 기존 question과의 유사도. seen이 없으면 0.0.
    """
    question = quiz.get("question", "").strip()
    if not question:
        return False, 0.0

    if not seen_questions:
        return True, 0.0

    vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4))
    all_texts = [question] + seen_questions
    try:
        matrix = vectorizer.fit_transform(all_texts)
    except ValueError:
        return True, 0.0

    sims = cosine_similarity(matrix[0:1], matrix[1:])[0]
    max_sim = float(sims.max())
    return max_sim < DUPLICATE_THRESHOLD, round(max_sim, 4)

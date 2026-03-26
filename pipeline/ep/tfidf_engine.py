"""EP TF-IDF 엔진: kiwipiepy 형태소 분석 기반 강의 전체 TF-IDF 계산."""

from typing import Any
from kiwipiepy import Kiwi
from sklearn.feature_extraction.text import TfidfVectorizer


# ================== 설정 상수 ==================

# POS 태그 화이트리스트
NOUN_POS_TAGS = {"NNG", "NNP", "SL", "SH"}
"""
명사로 간주할 형태소 분석 태그:
- NNG: 일반명사 (패키지, 메서드, 스트림)
- NNP: 고유명사 (자바, 스프링)
- SL: 외국어(알파벳) (NIO, CRUD, JOIN) ← 기술 용어 핵심
- SH: 한자어 (처리, 관리)
"""

MIN_KO_CHARS = 2
"""한국어 명사(NNG/NNP/SH)의 최소 길이."""

MIN_FOREIGN_CHARS = 2
"""외국어(SL) 토큰의 최소 길이.
(v11: 1→2, 단일 알파벳 "T"/"V"/"K" 등 노이즈 토큰 제거. "IO", "DB" 등 2자 이상은 보존)"""

TFIDF_MAX_DF = 0.85
"""전체 문서의 85% 이상에 나타나는 단어는 stop words로 처리."""

TFIDF_MIN_DF = 1
"""최소 1회 나타나는 단어도 포함 (희귀 기술 용어 보존)."""

TFIDF_TOP_N = 15
"""청크당 추출할 상위 TF-IDF 키워드 수. 바이그램 추가로 5 증가."""

TFIDF_NGRAM_RANGE = (1, 2)
"""TF-IDF 토큰 단위. (1,2) = 유니그램 + 바이그램.
바이그램 예: "버퍼드 리더", "파일 스트림", "아웃풋 스트림"."""


# ================== 명사 추출 ==================


def extract_nouns(text: str, kiwi: Kiwi) -> list[str]:
    """텍스트에서 명사(POS 필터)를 추출.

    Args:
        text: 추출 대상 텍스트.
        kiwi: 초기화된 Kiwi 형태소 분석기.

    Returns:
        필터링된 명사 리스트. 중복 허용 (TF-IDF의 빈도 신호 반영).
    """
    if not text or not text.strip():
        return []

    try:
        # kiwipiepy.analyze()는 여러 분석 후보를 반환 (beam search)
        # 첫 번째 결과만 사용
        result = kiwi.analyze(text)
        if not result:
            return []

        # result: list[list[Token]]
        # 첫 번째 분석 결과의 토큰 리스트
        tokens = result[0][0] if result[0] else []

        nouns = []
        for token in tokens:
            # token: namedtuple(form, tag, start, len)
            if token.tag not in NOUN_POS_TAGS:
                continue

            form = token.form.strip()
            if not form:
                continue

            # 외국어는 1자 이상, 나머지는 2자 이상
            if token.tag == "SL":
                if len(form) >= MIN_FOREIGN_CHARS:
                    nouns.append(form)
            else:
                if len(form) >= MIN_KO_CHARS:
                    nouns.append(form)

        return nouns

    except Exception:
        # 형태소 분석 실패 시 빈 리스트
        return []


# ================== TF-IDF 계산 ==================


def compute_lecture_tfidf(chunks: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    """강의 전체 코퍼스에서 TF-IDF를 계산.

    각 청크를 하나의 문서로 보고, 강의 전체를 코퍼스로 한 TF-IDF를 계산한다.
    토큰화는 kiwipiepy 형태소 분석 기반 명사 추출로 수행한다.

    Args:
        chunks: phase5_facts의 청크 리스트.

    Returns:
        {chunk_id: {noun: tfidf_score}} 형태. score는 sklearn 원시값 (0.0~1.0).
        계산 실패 시 빈 딕셔너리.
    """
    if not chunks:
        return {}

    # Kiwi 초기화: 강의 전체에서 1회만 수행
    try:
        kiwi = Kiwi()
    except Exception:
        return {}

    # 코퍼스 빌드: 각 청크를 명사 문자열로 변환
    chunk_ids: list[str] = []
    corpus: list[str] = []

    for chunk in chunks:
        text = chunk.get("text", "")
        chunk_id = chunk.get("chunk_id", "")

        nouns = extract_nouns(text, kiwi)
        corpus_text = " ".join(nouns)

        chunk_ids.append(chunk_id)
        corpus.append(corpus_text)

    # 코퍼스가 비어있으면 조기 반환
    if not corpus or all(len(c) == 0 for c in corpus):
        return {}

    # TF-IDF 벡터화
    try:
        vectorizer = TfidfVectorizer(
            max_df=TFIDF_MAX_DF,
            min_df=TFIDF_MIN_DF,
            ngram_range=TFIDF_NGRAM_RANGE,
        )
        tfidf_matrix = vectorizer.fit_transform(corpus)
        feature_names = vectorizer.get_feature_names_out()
    except ValueError:
        # vocabulary가 비어있는 경우
        return {}

    # 결과 구성: 청크별 상위 TFIDF_TOP_N 추출
    result: dict[str, dict[str, float]] = {}

    for i, chunk_id in enumerate(chunk_ids):
        row = tfidf_matrix.getrow(i).toarray()[0]  # (n_features,) shape

        # 점수 높은 상위 TFIDF_TOP_N 인덱스 추출
        top_indices = row.argsort()[-TFIDF_TOP_N:][::-1]

        scores: dict[str, float] = {}
        for idx in top_indices:
            score = float(row[idx])
            if score > 0.0:
                noun = feature_names[idx]
                scores[noun] = round(score, 4)

        result[chunk_id] = scores

    return result

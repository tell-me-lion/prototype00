"""Phase 3 러너: 시맨틱 청킹 및 중요도 스코어링."""

from pathlib import Path

from pipeline import paths
from pipeline.phase3 import keyword_tfidf, semantic_chunking


def run_phase3(
    in_dir: Path | None = None,
    out_dir: Path | None = None,
) -> None:
    """Phase 3 전체 실행."""
    src = in_dir or paths.DATA_PHASE2_SENTENCES
    dst = out_dir or paths.DATA_PHASE3_CHUNKS
    dst.mkdir(parents=True, exist_ok=True)

    # TODO: 구현자가 실제 실행 순서를 채울 것.
    _ = src, dst
    # 예: semantic_chunking.chunk_sentences(src, dst); keyword_tfidf.score_keywords(dst, dst)


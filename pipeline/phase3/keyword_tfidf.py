"""Phase 3: TF-IDF 기반 핵심어 스코어링 스켈레톤."""

from pathlib import Path

from pipeline import paths


def score_keywords(input_dir: Path | None = None, output_dir: Path | None = None) -> None:
    """청크별 TF-IDF 기반 핵심어를 계산."""
    src = input_dir or paths.DATA_PHASE3_CHUNKS
    dst = output_dir or paths.DATA_PHASE3_CHUNKS
    dst.mkdir(parents=True, exist_ok=True)
    # TODO: 구현자가 scikit-learn TF-IDF 로직을 채울 것.
    _ = src, dst


"""Phase 2: 품사 기반 문장 필터링 스켈레톤."""

from pathlib import Path

from pipeline import paths


def filter_sentences(input_dir: Path | None = None, output_dir: Path | None = None) -> None:
    """정보량이 낮은 감탄사 위주의 문장을 드랍."""
    src = input_dir or paths.DATA_PHASE2_SENTENCES
    dst = output_dir or paths.DATA_PHASE2_SENTENCES
    dst.mkdir(parents=True, exist_ok=True)
    # TODO: 구현자가 품사 기반 필터링 로직을 채울 것.
    _ = src, dst


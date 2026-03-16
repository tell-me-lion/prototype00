"""Phase 2: Kiwi 기반 문장 분리 스켈레톤."""

from pathlib import Path

from pipeline import paths


def segment_sentences(input_dir: Path | None = None, output_dir: Path | None = None) -> None:
    """세션 텍스트를 문장 단위로 분리."""
    src = input_dir or paths.DATA_PHASE1_SESSIONS
    dst = output_dir or paths.DATA_PHASE2_SENTENCES
    dst.mkdir(parents=True, exist_ok=True)
    # TODO: 구현자가 Kiwi 기반 문장 분리 로직을 채울 것.
    _ = src, dst


"""Phase 2 러너: 문장 복원 및 필터링."""

from pathlib import Path

from pipeline import paths
from pipeline.phase2 import sentence_filter_pos, sentence_segment_kiwi


def run_phase2(
    in_dir: Path | None = None,
    out_dir: Path | None = None,
) -> None:
    """Phase 2 전체 실행."""
    src = in_dir or paths.DATA_PHASE1_SESSIONS
    dst = out_dir or paths.DATA_PHASE2_SENTENCES
    dst.mkdir(parents=True, exist_ok=True)

    # TODO: 구현자가 실제 실행 순서를 채울 것.
    _ = src, dst
    # 예: sentence_segment_kiwi.segment_sentences(src, dst); sentence_filter_pos.filter_sentences(dst, dst)


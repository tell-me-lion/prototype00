"""Phase 1 러너: 데이터 분리 및 물리적 세척."""

from pathlib import Path

from pipeline import paths
from pipeline.phase1 import regex_clean, session_split, term_clean_gemini


def run_phase1(
    raw_dir: Path | None = None,
    out_dir: Path | None = None,
) -> None:
    """Phase 1 전체 실행."""
    src = raw_dir or paths.DATA_RAW
    dst = out_dir or paths.DATA_PHASE1_SESSIONS
    dst.mkdir(parents=True, exist_ok=True)

    # TODO: 실제 실행 순서는 구현자가 조정:
    # 1) regex_clean.regex_clean
    # 2) term_clean_gemini.clean_terms
    # 3) session_split.run
    _ = src, dst


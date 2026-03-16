"""Phase 1: 정규식 기반 물리적 세척 스켈레톤."""

from pathlib import Path

from pipeline import paths


def regex_clean(input_dir: Path | None = None, output_dir: Path | None = None) -> None:
    """화자 ID, 특수문자, 반복 잡음 등을 제거."""
    src = input_dir or paths.DATA_RAW
    dst = output_dir or paths.DATA_PHASE1_SESSIONS
    dst.mkdir(parents=True, exist_ok=True)
    # TODO: 구현자가 구체 정규식 및 처리 로직을 채울 것.
    _ = src, dst


"""Phase 1: 세션 분리 모듈 스켈레톤."""

from pathlib import Path

from pipeline import paths


def run(input_dir: Path | None = None, output_path: Path | None = None) -> None:
    """강의 스크립트를 세션 단위 JSONL 로 분리."""
    src = input_dir or paths.DATA_RAW
    dst = output_path or paths.DATA_PHASE1_SESSIONS
    dst.mkdir(parents=True, exist_ok=True)
    # TODO: 구현자가 세션 분리 로직을 채울 것.
    _ = src, dst


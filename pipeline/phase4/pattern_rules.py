"""Phase 4: 패턴 기반 명제 추출 스켈레톤."""

from pathlib import Path

from pipeline import paths


def select_by_pattern(input_dir: Path | None = None, output_dir: Path | None = None) -> None:
    """정의/역할/절차/비교 패턴을 이용해 문장 후보를 1차 선별."""
    src = input_dir or paths.DATA_PHASE3_CHUNKS
    dst = output_dir or paths.DATA_PHASE4_PROPOSITIONS
    dst.mkdir(parents=True, exist_ok=True)
    # TODO: 구현자가 패턴 매칭 로직을 채울 것.
    _ = src, dst


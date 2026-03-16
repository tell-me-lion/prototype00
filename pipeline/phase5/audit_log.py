"""Phase 5: 변경 로그(Traceability) 기록 스켈레톤."""

from pathlib import Path

from pipeline import paths


def write_audit_log(input_dir: Path | None = None, output_dir: Path | None = None) -> None:
    """각 Fact 에 대해 원문 대비 변경 이력을 기록."""
    src = input_dir or paths.DATA_PHASE5_FACTS
    dst = output_dir or paths.DATA_PHASE5_FACTS
    dst.mkdir(parents=True, exist_ok=True)
    # TODO: 구현자가 단계별 trace 정보 집계 로직을 채울 것.
    _ = src, dst


"""Phase 5 러너: 데이터 규격화 및 검증."""

from pathlib import Path

from pipeline import paths
from pipeline.phase5 import audit_log, standardize


def run_phase5(
    in_dir: Path | None = None,
    out_dir: Path | None = None,
) -> None:
    """Phase 5 전체 실행."""
    src = in_dir or paths.DATA_PHASE4_PROPOSITIONS
    dst = out_dir or paths.DATA_PHASE5_FACTS
    dst.mkdir(parents=True, exist_ok=True)

    # TODO: 구현자가 실제 실행 순서를 채울 것.
    _ = src, dst
    # 예: standardize.standardize_facts(src, dst); audit_log.write_audit_log(dst, dst)


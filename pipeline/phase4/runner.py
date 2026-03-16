"""Phase 4 러너: 지식 명제 추출 및 구조화."""

from pathlib import Path

from pipeline import paths
from pipeline.phase4 import concept_matching, pattern_rules, slm_fact_extractor


def run_phase4(
    in_dir: Path | None = None,
    out_dir: Path | None = None,
) -> None:
    """Phase 4 전체 실행."""
    src = in_dir or paths.DATA_PHASE3_CHUNKS
    dst = out_dir or paths.DATA_PHASE4_PROPOSITIONS
    dst.mkdir(parents=True, exist_ok=True)

    # TODO: 구현자가 실제 실행 순서를 채울 것.
    _ = src, dst
    # 예: pattern_rules.select_by_pattern(src, dst); slm_fact_extractor.extract_facts(src, dst); concept_matching.match_concepts(dst, dst)


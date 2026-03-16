"""Phase 5: 데이터 정규화/검증 스켈레톤."""

from pathlib import Path

from pipeline import paths


def standardize_facts(input_dir: Path | None = None, output_dir: Path | None = None) -> None:
    """Fact 후보를 최종 스키마에 맞춰 정규화."""
    src = input_dir or paths.DATA_PHASE4_PROPOSITIONS
    dst = output_dir or paths.DATA_PHASE5_FACTS
    dst.mkdir(parents=True, exist_ok=True)
    # TODO: 구현자가 Pydantic/Instructor 기반 정규화 및 검증 로직을 채울 것.
    _ = src, dst


"""Phase 4: 핵심 개념-설명 매칭 스켈레톤."""

from pathlib import Path

from pipeline import paths


def match_concepts(input_dir: Path | None = None, output_dir: Path | None = None) -> None:
    """TF-IDF 키워드와 SLM Fact 를 매칭해 개념-설명 쌍을 구성."""
    src = input_dir or paths.DATA_PHASE4_PROPOSITIONS
    dst = output_dir or paths.DATA_PHASE4_PROPOSITIONS
    dst.mkdir(parents=True, exist_ok=True)
    # TODO: 구현자가 매칭 및 스코어링 로직을 채울 것.
    _ = src, dst


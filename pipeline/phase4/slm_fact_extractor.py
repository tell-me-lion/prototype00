"""Phase 4: 로컬 SLM 기반 Fact 추출 스켈레톤."""

from pathlib import Path

from pipeline import paths


def extract_facts(input_dir: Path | None = None, output_dir: Path | None = None) -> None:
    """로컬 SLM을 사용해 텍스트에서 Fact 명제를 추출."""
    src = input_dir or paths.DATA_PHASE3_CHUNKS
    dst = output_dir or paths.DATA_PHASE4_PROPOSITIONS
    dst.mkdir(parents=True, exist_ok=True)
    # TODO: 구현자가 로컬 SLM 호출 및 후처리 로직을 채울 것.
    _ = src, dst


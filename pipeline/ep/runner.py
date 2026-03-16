"""EP 러너: 핵심 개념/학습 포인트 식별."""

from pathlib import Path

from pipeline import paths


def run_ep(
    in_dir: Path | None = None,
    out_dir: Path | None = None,
) -> None:
    """Fact 레벨 데이터에서 핵심 개념/학습 포인트를 식별."""
    src = in_dir or paths.DATA_PHASE5_FACTS
    dst = out_dir or paths.DATA_EP_CONCEPTS
    dst.mkdir(parents=True, exist_ok=True)
    # TODO: 구현자가 개념 중요도 계산/집계 로직을 채울 것.
    _ = src, dst


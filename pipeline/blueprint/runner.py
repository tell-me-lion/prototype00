"""Blueprint 러너: 문제 설계 및 전략 선택."""

from pathlib import Path

from pipeline import paths


def run_blueprint(
    in_dir: Path | None = None,
    out_dir: Path | None = None,
) -> None:
    """핵심 개념/학습 포인트를 입력으로 문제 블루프린트를 생성."""
    src = in_dir or paths.DATA_EP_CONCEPTS
    dst = out_dir or paths.DATA_BLUEPRINTS
    dst.mkdir(parents=True, exist_ok=True)
    # TODO: 구현자가 퀴즈 수, 유형, 난이도 등을 결정하는 로직을 채울 것.
    _ = src, dst


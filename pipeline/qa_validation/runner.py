"""QA validation 러너: 퀴즈 품질/사실 검증."""

from pathlib import Path

from pipeline import paths


def run_validation(
    in_dir: Path | None = None,
    out_dir: Path | None = None,
) -> None:
    """퀴즈의 사실성, 품질을 검증하고 통과/실패 결과를 기록."""
    src = in_dir or paths.DATA_QUIZZES_RAW
    dst = out_dir or paths.DATA_QUIZZES_VALIDATED
    dst.mkdir(parents=True, exist_ok=True)
    # TODO: 구현자가 사실 검증 및 품질 기준 로직을 채울 것.
    _ = src, dst


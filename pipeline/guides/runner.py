"""Guides 러너: 학습 가이드 및 핵심 요약 생성."""

from pathlib import Path

from pipeline import paths


def run_guides(
    concepts_dir: Path | None = None,
    quizzes_dir: Path | None = None,
    out_dir: Path | None = None,
) -> None:
    """EP + 검증된 퀴즈를 활용해 주차별 학습 가이드를 생성."""
    ep_src = concepts_dir or paths.DATA_EP_CONCEPTS
    quiz_src = quizzes_dir or paths.DATA_QUIZZES_VALIDATED
    dst = out_dir or paths.DATA_LEARNING_GUIDES
    dst.mkdir(parents=True, exist_ok=True)
    # TODO: 구현자가 요약/가이드 생성 로직을 채울 것.
    _ = ep_src, quiz_src, dst


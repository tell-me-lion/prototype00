"""Guides 러너: 학습 가이드 및 핵심 요약 생성."""

from pathlib import Path

from pipeline import paths


def run_guides(
    in_dir: Path | None = None,
    out_dir: Path | None = None,
) -> None:
    """전처리 결과(Phase 5 Fact)만을 입력으로 주차별 학습 가이드를 생성.

    Mode B 전용. Mode A 출력(EP 개념, 퀴즈)을 읽지 않는다.
    """
    src = in_dir or paths.DATA_PHASE5_FACTS
    dst = out_dir or paths.DATA_LEARNING_GUIDES
    dst.mkdir(parents=True, exist_ok=True)
    # TODO: 구현자가 주차 단위 집계 및 가이드 생성 로직을 채울 것.
    _ = src, dst


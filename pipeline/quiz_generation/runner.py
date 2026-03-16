"""Quiz generation 러너: 퀴즈 및 해설 생성."""

from pathlib import Path

from pipeline import paths


def run_quiz_generation(
    in_dir: Path | None = None,
    out_dir: Path | None = None,
) -> None:
    """블루프린트와 RAG 를 이용해 퀴즈/해설을 생성."""
    src = in_dir or paths.DATA_BLUEPRINTS
    dst = out_dir or paths.DATA_QUIZZES_RAW
    dst.mkdir(parents=True, exist_ok=True)
    # TODO: 구현자가 LLM/SLM 호출 및 RAG 연동 로직을 채울 것.
    _ = src, dst


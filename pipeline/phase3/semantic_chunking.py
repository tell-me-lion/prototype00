"""Phase 3: 시맨틱 청킹 스켈레톤."""

from pathlib import Path

from pipeline import paths


def chunk_sentences(input_dir: Path | None = None, output_dir: Path | None = None) -> None:
    """문장 간 시맨틱 유사도를 기반으로 청크를 생성."""
    src = input_dir or paths.DATA_PHASE2_SENTENCES
    dst = output_dir or paths.DATA_PHASE3_CHUNKS
    dst.mkdir(parents=True, exist_ok=True)
    # TODO: 구현자가 임베딩/코사인 유사도 기반 청킹 로직을 채울 것.
    _ = src, dst


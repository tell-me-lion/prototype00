"""Phase 1: Gemini 기반 용어 클렌징 스켈레톤."""

from pathlib import Path


def clean_terms(input_path: Path, output_path: Path) -> None:
    """STT 오인식 용어를 정식 용어로 복원."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    # TODO: 구현자가 Gemini API 호출 및 클렌징 로직을 채울 것.
    _ = input_path, output_path


"""Preprocessor Phase 1~5 함수형 래퍼.

각 Phase의 argparse 기반 main()을 우회하고,
클래스를 직접 인스턴스화하여 프로그래밍 방식으로 호출한다.

사용법:
    from pipeline.preprocessor.wrapper import run_preprocess
    run_preprocess("2026-02-11_kdt-backend-21th")
"""

import importlib
import logging
from pathlib import Path

from pipeline import paths

logger = logging.getLogger(__name__)


def run_preprocess(
    lecture_id: str,
    *,
    use_gemini_clean: bool = False,
    use_gemini_embed: bool = True,
    threshold: float = 0.40,
) -> None:
    """단일 강의에 대해 Phase 1~5 전처리를 순차 실행.

    Args:
        lecture_id: 강의 ID (예: "2026-02-11_kdt-backend-21th").
        use_gemini_clean: Phase 1에서 Gemini API로 텍스트 교정할지 여부.
        use_gemini_embed: Phase 3에서 Gemini Embedding API 사용 여부.
                          False면 로컬 SROBERTa (5GB+ sentence-transformers 필요).
        threshold: Phase 3 의미 청킹 코사인 유사도 임계값.
    """
    raw_file = paths.DATA_RAW / f"{lecture_id}.txt"
    if not raw_file.exists():
        raise FileNotFoundError(f"원본 파일 없음: {raw_file}")

    # Phase 1: Cleaner
    logger.info("[Phase 1] Cleaner 시작: %s", lecture_id)
    mod1 = importlib.import_module("pipeline.preprocessor.01_cleaner")
    Cleaner = mod1.Cleaner

    import shutil
    date_part = lecture_id.split("_")[0]

    cleaner = Cleaner(use_gemini=use_gemini_clean)
    cleaner.process_file(raw_file, paths.DATA_PHASE1_SESSIONS)
    logger.info("[Phase 1] Cleaner 완료")

    # Phase 1 출력 파일을 lecture_id 기반 파일명으로 정규화
    # (Cleaner가 {date}.jsonl 로 저장하므로 {lecture_id}.jsonl 로 이동)
    phase1_src = paths.DATA_PHASE1_SESSIONS / f"{date_part}.jsonl"
    phase1_dst = paths.DATA_PHASE1_SESSIONS / f"{lecture_id}.jsonl"
    if phase1_src.exists() and phase1_src != phase1_dst:
        shutil.move(str(phase1_src), phase1_dst)
        logger.info("[Phase 1] 파일명 정규화: %s → %s", phase1_src.name, phase1_dst.name)

    # Phase 1 출력 파일 찾기
    phase1_file = _find_output_file(paths.DATA_PHASE1_SESSIONS, lecture_id)
    if not phase1_file:
        raise FileNotFoundError(f"Phase 1 출력 없음: {lecture_id}")

    # Phase 2: Segmenter
    logger.info("[Phase 2] Segmenter 시작")
    mod2 = importlib.import_module("pipeline.preprocessor.02_segmenter")
    Segmenter = mod2.Segmenter

    segmenter = Segmenter()
    segmenter.process_file(phase1_file, paths.DATA_PHASE2_SENTENCES)
    logger.info("[Phase 2] Segmenter 완료")

    phase2_file = _find_output_file(paths.DATA_PHASE2_SENTENCES, lecture_id)
    if not phase2_file:
        raise FileNotFoundError(f"Phase 2 출력 없음: {lecture_id}")

    # Phase 3: SemanticChunker
    logger.info("[Phase 3] SemanticChunker 시작")
    mod3 = importlib.import_module("pipeline.preprocessor.03_chunker")
    SemanticChunker = mod3.SemanticChunker

    chunker = SemanticChunker(
        threshold=threshold,
        use_gemini_embed=use_gemini_embed,
    )
    chunker.process_file(phase2_file, paths.DATA_PHASE3_CHUNKS)
    logger.info("[Phase 3] SemanticChunker 완료")

    phase3_file = _find_output_file(paths.DATA_PHASE3_CHUNKS, lecture_id)
    if not phase3_file:
        raise FileNotFoundError(f"Phase 3 출력 없음: {lecture_id}")

    # Phase 4: FactExtractor
    logger.info("[Phase 4] FactExtractor 시작")
    mod4 = importlib.import_module("pipeline.preprocessor.04_extractor")
    FactExtractor = mod4.FactExtractor

    extractor = FactExtractor(use_gemini=True, use_ollama=False)
    extractor.process_file(phase3_file, paths.DATA_PHASE4_PROPOSITIONS)
    logger.info("[Phase 4] FactExtractor 완료")

    phase4_file = _find_output_file(paths.DATA_PHASE4_PROPOSITIONS, lecture_id)
    if not phase4_file:
        raise FileNotFoundError(f"Phase 4 출력 없음: {lecture_id}")

    # Phase 5: Formatter
    logger.info("[Phase 5] Formatter 시작")
    mod5 = importlib.import_module("pipeline.preprocessor.05_formatter")
    Formatter = mod5.Formatter

    formatter = Formatter()
    formatter.format_documents(phase3_file, phase4_file, paths.DATA_PHASE5_FACTS)
    logger.info("[Phase 5] Formatter 완료")

    # Phase 5 출력 파일을 lecture_id 기반 파일명으로 정규화
    # (Formatter가 {date}_chunks_formatted.jsonl 로 저장하므로 {lecture_id}.jsonl 로 복사)
    chunks_src = paths.DATA_PHASE5_FACTS / f"{date_part}_chunks_formatted.jsonl"
    chunks_dst = paths.DATA_PHASE5_FACTS / f"{lecture_id}.jsonl"
    if chunks_src.exists() and chunks_src != chunks_dst:
        shutil.copy2(chunks_src, chunks_dst)
        logger.info("[Phase 5] 파일명 정규화: %s → %s", chunks_src.name, chunks_dst.name)


def _find_output_file(directory: Path, lecture_id: str) -> Path | None:
    """출력 디렉터리에서 lecture_id와 매칭되는 JSONL 파일을 찾는다.

    파일명 규칙:
    - 정확히 일치: {lecture_id}.jsonl
    - 날짜 기반: {date}.jsonl (lecture_id에서 date 부분 추출)
    """
    # 정확한 파일명 매칭
    exact = directory / f"{lecture_id}.jsonl"
    if exact.exists():
        return exact

    # 날짜 기반 매칭 (lecture_id = "2026-02-11_kdt-backend-21th" → date = "2026-02-11")
    date_part = lecture_id.split("_")[0] if "_" in lecture_id else lecture_id
    date_file = directory / f"{date_part}.jsonl"
    if date_file.exists():
        return date_file

    # 부분 매칭 (lecture_id가 포함된 파일)
    candidates = list(directory.glob(f"*{date_part}*.jsonl"))
    if candidates:
        return candidates[0]

    return None

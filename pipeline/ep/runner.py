"""EP 러너: 핵심 개념/학습 포인트 식별."""

import json
import re
from pathlib import Path

from pipeline import paths

from .concept_extractor import extract_concepts


def run_ep(
    in_dir: Path | None = None,
    out_dir: Path | None = None,
) -> None:
    """phase5_facts에서 핵심 개념을 추출해 ConceptDocument 생성.

    입력: data/phase5_facts/*.jsonl
    출력: data/ep_concepts/*.jsonl
    """
    src = in_dir or paths.DATA_PHASE5_FACTS
    dst = out_dir or paths.DATA_EP_CONCEPTS
    dst.mkdir(parents=True, exist_ok=True)

    # 입력 파일 목록
    jsonl_files = sorted(src.glob("*.jsonl"))

    for jsonl_file in jsonl_files:
        # 파일명 파싱
        lecture_id, week = _parse_filename(jsonl_file.stem)

        # JSONL 읽기
        chunks = []
        with jsonl_file.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                chunks.append(json.loads(line))

        if not chunks:
            print(f"[SKIP] {jsonl_file.name} — 입력 데이터 없음")
            continue

        # 개념 추출
        concepts = extract_concepts(chunks, lecture_id, week)

        # 결과 저장 (JSONL 형식)
        out_file = dst / jsonl_file.name
        with out_file.open("w", encoding="utf-8") as f:
            for concept in concepts:
                json_str = concept.model_dump_json(ensure_ascii=False)
                f.write(json_str + "\n")

        # 로그
        print(f"[OK] {jsonl_file.name} | {len(concepts)} concepts")


def _parse_filename(stem: str) -> tuple[str, int]:
    """파일명에서 lecture_id, week 추출.

    예: "2026-02-11_kdt-backend-21th" → ("2026-02-11_kdt-backend-21th", 21)
    파일명에 주차 정보가 없으면 week=0
    """
    lecture_id = stem

    # week 추출: "21th" 같은 패턴에서 숫자
    match = re.search(r"(\d+)th", stem)
    week = int(match.group(1)) if match else 0

    return lecture_id, week


"""Blueprint 러너: 문제 설계.

Mode A 블록. EP 블록의 출력(ep_concepts)을 읽어 문제 블루프린트를 생성한다.

입력: data/ep_concepts/*.jsonl  (ConceptDocument)
입력: data/phase5_facts/*.jsonl   (청크 and 팩트)
출력: data/blueprints/*.jsonl   (BlueprintDocument)
"""

import json
from pathlib import Path

from pipeline import paths
from pipeline.ep.schema import ConceptDocument

from .blueprint_designer import design_blueprints


def run_blueprint(
    in_dir: Path | None = None,
    out_dir: Path | None = None,
    input_file: Path | None = None,
    output_file: Path | None = None,
) -> None:
    """ep_concepts/*.jsonl을 읽어 blueprints/*.jsonl을 생성.

    Args:
        in_dir: ep_concepts 디렉터리. None이면 paths.DATA_EP_CONCEPTS 사용.
        out_dir: blueprints 출력 디렉터리. None이면 paths.DATA_BLUEPRINTS 사용.
        input_file: 특정 파일만 처리할 때 사용. 지정 시 in_dir 무시.
        output_file: 특정 파일명으로 저장할 때 사용. 지정 시 out_dir의 원본 파일명 대신 사용.
    """
    dst = out_dir or paths.DATA_BLUEPRINTS
    facts_dir = paths.DATA_PHASE5_FACTS
    dst.mkdir(parents=True, exist_ok=True)

    # input_file 지정 시 해당 파일만, 아니면 in_dir 전체
    if input_file is not None:
        jsonl_files = [input_file]
    else:
        src = in_dir or paths.DATA_EP_CONCEPTS
        jsonl_files = sorted(src.glob("*.jsonl"))

    if not jsonl_files:
        print("[WARN] 처리할 JSONL 파일이 없습니다.")
        return

    for jsonl_file in jsonl_files:
        # ConceptDocument 로드
        concepts: list[ConceptDocument] = []
        for line in jsonl_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                concepts.append(ConceptDocument(**json.loads(line)))
            except Exception as e:
                print(f"[WARN] {jsonl_file.name} - ConceptDocument 파싱 실패: {e}")

        if not concepts:
            print(f"[SKIP] {jsonl_file.name} - 개념 없음")
            continue

        # phase5_facts 로드 (청크 소스, 파일명 기준으로 매핑)
        facts_file = facts_dir / jsonl_file.name
        chunks: list[dict] = []

        if facts_file.exists():
            for line in facts_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line:
                    try:
                        chunks.append(json.loads(line))
                    except Exception as e:
                        print(f"[WARN] {facts_file.name} - 청크 파싱 실패: {e}")
        else:
            print(f"[WARN] {jsonl_file.name} - facts 파일 없음, 청크 링킹 불가")

        # 블루프린트 생성
        blueprints, skipped = design_blueprints(concepts, chunks)

        # 결과 저장
        out_file = output_file if output_file is not None else dst / jsonl_file.name
        with out_file.open("w", encoding="utf-8") as f:
            for bp in blueprints:
                f.write(bp.model_dump_json(ensure_ascii=False) + "\n")

        # 로깅
        skip_ratio = (
            len(skipped) / len(concepts) * 100
            if concepts
            else 0
        )
        print(
            f"[OK]   {out_file.name} | "
            f"{len(blueprints)} blueprints | "
            f"[SKIP] {len(skipped)}/{len(concepts)} ({skip_ratio:.1f}%)"
        )

        if skipped:
            for reason in skipped:
                print(f"       - {reason}")


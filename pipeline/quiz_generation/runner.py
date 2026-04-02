"""Quiz Generation 러너: 전체 BP + Chunk → LLM 단일 호출 → QuizDocument 배치 생성.

Mode A 블록.
입력: data/blueprints/*.jsonl        (BlueprintDocument)
입력: data/phase5_facts/*.jsonl      (청크 원문 + facts)
출력: data/quizzes_raw/*.jsonl       (QuizDocument)
"""

import json
from pathlib import Path
from typing import Callable
from uuid import uuid4

from pipeline import paths

from .prompt_builder import build_batch_prompt
from .quiz_generator import MODEL_NAME, call_gemini_batch
from .schema import Choice, QuizDocument, QuizMeta
from .validator import validate_batch

QUIZ_COUNT = 30
"""한 번 LLM 호출로 생성할 퀴즈 수."""


def run_quiz_generation(
    in_dir: Path | None = None,
    out_dir: Path | None = None,
    input_file: Path | None = None,
    output_file: Path | None = None,
    facts_file: Path | None = None,
    detail_callback: Callable[[str], None] | None = None,
) -> None:
    """BlueprintDocument 전체 + Chunk 전체를 LLM에 넣어 퀴즈를 배치 생성.

    Args:
        in_dir: blueprints 디렉터리. None이면 paths.DATA_BLUEPRINTS 사용.
        out_dir: quizzes_raw 출력 디렉터리. None이면 paths.DATA_QUIZZES_RAW 사용.
        input_file: 특정 blueprint 파일만 처리. 지정 시 in_dir 무시.
        output_file: 출력 파일명. 지정 시 out_dir의 원본 파일명 대신 사용.
        facts_file: 특정 phase5_facts 파일. None이면 파일명 기준 자동 매핑.
    """
    dst = out_dir or paths.DATA_QUIZZES_RAW
    dst.mkdir(parents=True, exist_ok=True)

    # 입력 파일 목록 결정
    if input_file is not None:
        bp_files = [input_file]
    else:
        src = in_dir or paths.DATA_BLUEPRINTS
        bp_files = sorted(src.glob("*.jsonl"))

    if not bp_files:
        print("[WARN] 처리할 blueprint 파일이 없습니다.")
        return

    for bp_file in bp_files:
        # Blueprint 전체 로드
        blueprints = _load_jsonl(bp_file)
        if not blueprints:
            print(f"[SKIP] {bp_file.name} — blueprint 없음")
            continue

        # Phase5 facts(chunk) 전체 로드
        f_file = facts_file or (paths.DATA_PHASE5_FACTS / bp_file.name)
        chunks = _load_jsonl(f_file) if f_file.exists() else []
        if not chunks:
            print(f"[WARN] {bp_file.name} — facts 파일 없음, chunk 컨텍스트 없이 진행")

        # 출력 파일 경로
        out_file = output_file if output_file is not None else dst / bp_file.name

        print(f"[RUN]  {bp_file.name} | bp={len(blueprints)}, chunks={len(chunks)}")

        # 단일 LLM 호출 (잘림 시 퀴즈 수를 줄여 적응형 재시도)
        prompt = build_batch_prompt(blueprints, chunks, quiz_count=QUIZ_COUNT)
        if detail_callback:
            detail_callback(f"LLM 호출 중... (목표 {QUIZ_COUNT}개)")
        raw_quizzes = call_gemini_batch(
            prompt,
            rebuild_prompt=lambda qc: build_batch_prompt(blueprints, chunks, quiz_count=qc),
        )

        # 검증
        if detail_callback:
            detail_callback(f"검증 중 (응답 {len(raw_quizzes)}개)")
        valid_quizzes, errors = validate_batch(raw_quizzes)
        for err in errors:
            print(f"  [INVALID] {err}")

        # QuizDocument 조립
        lecture_id = blueprints[0].get("lecture_id", "") if blueprints else ""
        week = blueprints[0].get("week", 0) if blueprints else 0
        quizzes = [
            _assemble_quiz(q, lecture_id=lecture_id, week=week)
            for q in valid_quizzes
        ]

        # 저장
        with out_file.open("w", encoding="utf-8") as f:
            for quiz in quizzes:
                f.write(quiz.model_dump_json(ensure_ascii=False) + "\n")

        if detail_callback:
            detail_callback(f"퀴즈 {len(quizzes)}개 생성 완료")
        print(
            f"[OK]   {out_file.name} | "
            f"{len(quizzes)}/{len(raw_quizzes)} quizzes "
            f"(invalid={len(errors)})"
        )


# ================== 내부 함수 ==================


def _load_jsonl(path: Path) -> list[dict]:
    """JSONL 파일을 dict 목록으로 로드."""
    results: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            results.append(json.loads(line))
        except Exception as e:
            print(f"[WARN] {path.name} 파싱 실패: {e}")
    return results


def _assemble_quiz(
    data: dict,
    lecture_id: str,
    week: int,
) -> QuizDocument:
    """검증된 dict → QuizDocument 조립."""
    quiz_type = data.get("question_type", "mcq")

    choices: list[Choice] | None = None
    raw_choices = data.get("choices")
    if raw_choices and isinstance(raw_choices, list):
        choices = [
            Choice(
                id=c.get("id", i),
                text=str(c.get("text", "")),
                is_answer=bool(c.get("is_answer", False)),
            )
            for i, c in enumerate(raw_choices)
        ]

    return QuizDocument(
        quiz_id="q_" + uuid4().hex[:8],
        blueprint_id=data.get("blueprint_id", ""),
        lecture_id=lecture_id,
        week=week,
        question_type=quiz_type,
        question_format=data.get("question_format", ""),
        difficulty=data.get("difficulty", "중"),
        question=data.get("question", ""),
        choices=choices,
        answers=data.get("answers"),
        code_template=data.get("code_template"),
        source_text=data.get("source_text", ""),
        explanation=data.get("explanation", ""),
        meta=QuizMeta(
            attempt_count=1,
            llm_model=MODEL_NAME,
            used_fact_ids=data.get("used_fact_ids", []),
        ),
    )

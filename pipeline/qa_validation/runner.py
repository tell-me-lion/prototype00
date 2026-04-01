"""QA Validation 러너: 5단계 검증 및 최적 10개 선발 파이프라인 오케스트레이션.

입력:
  data/quizzes_raw/*.jsonl      (QuizDocument)
  data/phase5_facts/*.jsonl     (chunk 원문)

출력:
  data/quizzes_validated/*.jsonl     (단계 1~4 pass 전체)
  data/quizzes_validated/top10.jsonl (최적 10개)
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from pipeline import paths

from .difficulty_checker import check_difficulty
from .discriminability_checker import check_discriminability
from .duplicate_checker import check_duplicate
from .grounding_checker import check_grounding
from .selector import select_top

MAX_RETRY = 3


def run_validation(
    in_dir: Path | None = None,
    out_dir: Path | None = None,
    input_file: Path | None = None,
    facts_file: Path | None = None,
) -> None:
    """전체 QA Validation 파이프라인을 실행한다.

    Args:
        in_dir: quizzes_raw 디렉터리. None이면 paths.DATA_QUIZZES_RAW 사용.
        out_dir: quizzes_validated 출력 디렉터리. None이면 paths.DATA_QUIZZES_VALIDATED 사용.
        input_file: 특정 quizzes_raw 파일만 처리.
        facts_file: 특정 phase5_facts 파일. None이면 파일명 기준 자동 매핑.
    """
    dst = out_dir or paths.DATA_QUIZZES_VALIDATED
    dst.mkdir(parents=True, exist_ok=True)

    if input_file is not None:
        qg_files = [input_file]
    else:
        src = in_dir or paths.DATA_QUIZZES_RAW
        qg_files = sorted(src.glob("*.jsonl"))

    if not qg_files:
        print("[WARN] 처리할 quizzes_raw 파일이 없습니다.")
        return

    for qg_file in qg_files:
        quizzes = _load_jsonl(qg_file)
        if not quizzes:
            print(f"[SKIP] {qg_file.name} — 퀴즈 없음")
            continue

        # chunk 로드
        f_file = facts_file or (paths.DATA_PHASE5_FACTS / qg_file.name)
        if not f_file.exists():
            # lecture_id 기반 자동 매핑 시도 (e.g. qg_v7.jsonl → ep_v13.jsonl)
            lecture_id = quizzes[0].get("lecture_id", "")
            candidate = paths.DATA_PHASE5_FACTS / f"{lecture_id}.jsonl"
            f_file = candidate if candidate.exists() else f_file

        chunks = _load_jsonl(f_file) if f_file.exists() else []
        if not chunks:
            print(f"[WARN] {qg_file.name} — chunk 파일 없음: {f_file}")

        print(f"\n[RUN]  {qg_file.name} | quizzes={len(quizzes)}, chunks={len(chunks)}")

        # blueprint별 used_count 추적
        blueprint_used: dict[str, int] = defaultdict(int)
        blueprint_ungenerable: dict[str, bool] = defaultdict(bool)
        # 중복 검사용: blueprint별 통과된 question 목록
        seen_questions: dict[str, list[str]] = defaultdict(list)

        pass_records: list[dict] = []
        fail_stats = {"grounding": 0, "duplicate": 0, "difficulty": 0, "discriminability": 0}

        for quiz in quizzes:
            quiz_id = quiz.get("quiz_id", "")
            bp_id = quiz.get("blueprint_id", "")

            if blueprint_ungenerable.get(bp_id):
                print(f"  [SKIP] {quiz_id} — blueprint {bp_id} ungenerable")
                continue

            validation_log: dict = {}

            # ── 단계 1: 근거성 ──────────────────────────────────────────────
            g_passed, g_score = check_grounding(quiz, chunks)
            validation_log["grounding_check"] = g_passed
            validation_log["grounding_score"] = g_score

            if not g_passed:
                print(f"  [FAIL:grounding]  {quiz_id} score={g_score:.3f}")
                fail_stats["grounding"] += 1
                _handle_fail(bp_id, blueprint_used, blueprint_ungenerable)
                continue

            # ── 단계 2: 중복 ────────────────────────────────────────────────
            d_passed, d_sim = check_duplicate(quiz, seen_questions[bp_id])
            validation_log["duplicate_check"] = d_passed
            validation_log["duplicate_max_sim"] = d_sim

            if not d_passed:
                print(f"  [FAIL:duplicate]  {quiz_id} sim={d_sim:.3f} (폐기, used_count 미증가)")
                fail_stats["duplicate"] += 1
                # 중복 fail: used_count 증가 없음, 즉시 폐기
                continue

            # ── 단계 3: 난이도 ──────────────────────────────────────────────
            df_passed, error_rate = check_difficulty(quiz)
            validation_log["difficulty_check"] = df_passed
            validation_log["predicted_error_rate"] = error_rate

            if not df_passed:
                print(f"  [FAIL:difficulty] {quiz_id} error_rate={error_rate:.3f}")
                fail_stats["difficulty"] += 1
                _handle_fail(bp_id, blueprint_used, blueprint_ungenerable)
                continue

            # ── 단계 4: 변별력 ──────────────────────────────────────────────
            disc_passed, disc_log = check_discriminability(quiz)
            validation_log["discriminability_check"] = disc_passed
            validation_log.update({
                k: v for k, v in disc_log.items() if v is not None
            })

            if not disc_passed:
                print(
                    f"  [FAIL:discrim]    {quiz_id} "
                    f"distractor={disc_log.get('distractor_score')} "
                    f"elim_risk={disc_log.get('elimination_risk')}"
                )
                fail_stats["discriminability"] += 1
                _handle_fail(bp_id, blueprint_used, blueprint_ungenerable)
                continue

            # ── 모든 단계 통과 ──────────────────────────────────────────────
            seen_questions[bp_id].append(quiz.get("question", ""))

            record = {
                "quiz_id": quiz_id,
                "status": "pass",
                "validation_log": validation_log,
                "quiz": quiz,
            }
            pass_records.append(record)
            print(f"  [PASS]            {quiz_id} grounding={g_score:.3f} error_rate={error_rate:.3f}")

        # ── 저장: 단계 1~4 pass 전체 ────────────────────────────────────────
        out_file = dst / qg_file.name
        with out_file.open("w", encoding="utf-8") as f:
            for rec in pass_records:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")

        pass_rate = len(pass_records) / len(quizzes) if quizzes else 0
        print(
            f"\n[RESULT] {qg_file.name} | "
            f"pass={len(pass_records)}/{len(quizzes)} ({pass_rate:.0%}) | "
            f"fail={fail_stats}"
        )

        if pass_rate < 0.7:
            print(f"  [WARN] pass율 {pass_rate:.0%} < 70% 기준 미달")

        # ── 단계 5: 최적 10개 선발 ──────────────────────────────────────────
        if not pass_records:
            print("  [WARN] pass된 퀴즈가 없어 top10 선발 불가")
            continue

        print(f"\n[SELECT] {len(pass_records)}개 → 최적 10개 선발 중...")
        top10 = select_top(pass_records)

        top10_file = dst / "top10.jsonl"
        with top10_file.open("w", encoding="utf-8") as f:
            for rec in top10:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")

        print(f"[DONE]  top10.jsonl 저장 완료 ({len(top10)}개)")
        _print_top10_summary(top10)


# ================== 내부 유틸 ==================

def _handle_fail(
    bp_id: str,
    blueprint_used: dict[str, int],
    blueprint_ungenerable: dict[str, bool],
) -> None:
    """재생성 대상 fail: used_count를 증가시키고 MAX_RETRY 초과 시 ungenerable 마킹."""
    blueprint_used[bp_id] += 1
    if blueprint_used[bp_id] > MAX_RETRY:
        blueprint_ungenerable[bp_id] = True
        print(f"  [UNGENERABLE] blueprint {bp_id} (used_count={blueprint_used[bp_id]})")


def _load_jsonl(path: Path) -> list[dict]:
    results: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            results.append(json.loads(line))
        except Exception as e:
            print(f"  [WARN] {path.name} 파싱 실패: {e}")
    return results


def _print_top10_summary(top10: list[dict]) -> None:
    type_counts: dict[str, int] = {}
    diff_counts: dict[str, int] = {}
    scores = []

    for rec in top10:
        quiz = rec.get("quiz", {})
        t = quiz.get("question_type", "?")
        d = quiz.get("difficulty", "?")
        type_counts[t] = type_counts.get(t, 0) + 1
        diff_counts[d] = diff_counts.get(d, 0) + 1
        scores.append(rec.get("selection_score", 0.0))

    avg_score = sum(scores) / len(scores) if scores else 0
    print(f"  유형 분포: {type_counts}")
    print(f"  난이도 분포: {diff_counts}")
    print(f"  selection_score 평균: {avg_score:.4f}")

    for rec in top10:
        quiz = rec.get("quiz", {})
        log = rec.get("validation_log", {})
        print(
            f"  #{rec.get('rank'):2d} [{quiz.get('question_type'):10s}|{quiz.get('difficulty')}] "
            f"score={rec.get('selection_score'):.3f} "
            f"g={log.get('grounding_score', 0):.2f} "
            f"d={log.get('distractor_score', '-')} "
            f"e={log.get('elimination_risk', '-')} "
            f"| {quiz.get('question', '')[:50]}"
        )

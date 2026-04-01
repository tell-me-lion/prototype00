"""단계 5 — 최적 10개 선발: selection_score 계산 + 다양성 제약 greedy.

검증 pass된 퀴즈들을 selection_score로 정렬한 뒤,
유형·난이도·blueprint 다양성 제약을 만족하면서 10개를 greedy 선발한다.
"""

from __future__ import annotations

TARGET_COUNT = 10

# selection_score 가중치
WEIGHTS = {
    "grounding":      0.25,
    "distractor":     0.25,
    "discrimination": 0.30,
    "difficulty_fit": 0.20,
}

# 다양성 제약
TYPE_LIMITS: dict[str, tuple[int, int]] = {
    "mcq":        (3, 5),
    "ox_quiz":    (1, 3),
    "fill_blank": (2, 3),
}
DIFF_MIN: dict[str, int] = {"상": 1, "중": 3, "하": 1}
BLUEPRINT_MAX = 2


def _compute_difficulty_fit(predicted_error_rate: float) -> float:
    """오답률이 0.3~0.7 구간에 가까울수록 1.0에 가까운 점수."""
    fit = 1.0 - abs(predicted_error_rate - 0.5) / 0.5
    return max(0.0, min(1.0, fit))


def compute_selection_score(validated: dict) -> float:
    """검증 완료 레코드에서 selection_score를 계산한다.

    Args:
        validated: runner가 조립한 validated record.
                   validation_log에 grounding_score, predicted_error_rate,
                   distractor_score, elimination_risk 포함.

    Returns:
        0.0~1.0 selection_score
    """
    log = validated.get("validation_log", {})
    q_type = validated.get("quiz", {}).get("question_type", "")

    grounding_score = float(log.get("grounding_score", 0.75))
    predicted_error = float(log.get("predicted_error_rate", 0.5))

    # MCQ는 실제 distractor_score 사용, 나머지는 0.6 고정
    raw_distractor = log.get("distractor_score")
    if q_type == "mcq" and raw_distractor is not None:
        distractor_score = float(raw_distractor)
    else:
        distractor_score = 0.6

    # MCQ는 실제 elimination_risk 사용, 나머지는 0.2 고정 (소거법 리스크 낮음)
    raw_elim = log.get("elimination_risk")
    if q_type == "mcq" and raw_elim is not None:
        discrimination = 1.0 - float(raw_elim)
    else:
        discrimination = 0.8

    difficulty_fit = _compute_difficulty_fit(predicted_error)

    score = (
        grounding_score   * WEIGHTS["grounding"]
        + distractor_score  * WEIGHTS["distractor"]
        + discrimination    * WEIGHTS["discrimination"]
        + difficulty_fit    * WEIGHTS["difficulty_fit"]
    )
    return round(score, 4)


def _violates_constraints(
    candidate: dict,
    selected: list[dict],
    blueprint_max: int,
) -> bool:
    """candidate를 선발했을 때 제약을 위반하는지 확인한다."""
    quiz = candidate.get("quiz", {})
    q_type = quiz.get("question_type", "")
    difficulty = quiz.get("difficulty", "중")
    bp_id = quiz.get("blueprint_id", "")

    current_types: dict[str, int] = {}
    current_diffs: dict[str, int] = {}
    current_bps: dict[str, int] = {}

    for s in selected:
        sq = s.get("quiz", {})
        t = sq.get("question_type", "")
        d = sq.get("difficulty", "중")
        b = sq.get("blueprint_id", "")
        current_types[t] = current_types.get(t, 0) + 1
        current_diffs[d] = current_diffs.get(d, 0) + 1
        current_bps[b] = current_bps.get(b, 0) + 1

    # 유형 최대 초과
    if q_type in TYPE_LIMITS:
        _, type_max = TYPE_LIMITS[q_type]
        if current_types.get(q_type, 0) >= type_max:
            return True

    # blueprint 최대 초과
    if current_bps.get(bp_id, 0) >= blueprint_max:
        return True

    return False


def _check_min_constraints_satisfied(selected: list[dict]) -> bool:
    """선발된 목록이 최솟값 제약을 모두 충족하는지 확인한다."""
    type_counts: dict[str, int] = {}
    diff_counts: dict[str, int] = {}

    for s in selected:
        sq = s.get("quiz", {})
        t = sq.get("question_type", "")
        d = sq.get("difficulty", "중")
        type_counts[t] = type_counts.get(t, 0) + 1
        diff_counts[d] = diff_counts.get(d, 0) + 1

    for q_type, (type_min, _) in TYPE_LIMITS.items():
        if type_counts.get(q_type, 0) < type_min:
            return False
    for diff, diff_min in DIFF_MIN.items():
        if diff_counts.get(diff, 0) < diff_min:
            return False
    return True


def select_top(validated_records: list[dict]) -> list[dict]:
    """검증 pass 퀴즈에서 최적 10개를 선발한다.

    Args:
        validated_records: runner가 생성한 validated record 목록 (status="pass"만).

    Returns:
        selection_score 기준 상위 10개 (다양성 제약 적용). rank 필드 추가됨.
    """
    # selection_score 계산 및 정렬
    for rec in validated_records:
        rec["selection_score"] = compute_selection_score(rec)
    sorted_records = sorted(
        validated_records, key=lambda r: r["selection_score"], reverse=True
    )

    # 1차 시도: blueprint_max = BLUEPRINT_MAX(2)
    selected = _greedy_select(sorted_records, BLUEPRINT_MAX)

    # 10개 못 채우면 blueprint_max 완화 (3)
    if len(selected) < TARGET_COUNT:
        print(f"  [WARN] 제약 완화: blueprint_max {BLUEPRINT_MAX} → 3 (현재 {len(selected)}개)")
        selected = _greedy_select(sorted_records, 3)

    # 그래도 부족하면 전체 제약 무시하고 score 순으로 채움
    if len(selected) < TARGET_COUNT:
        print(f"  [WARN] 다양성 제약 무시하고 score 순으로 채움 (현재 {len(selected)}개)")
        existing_ids = {r["quiz_id"] for r in selected}
        for rec in sorted_records:
            if len(selected) >= TARGET_COUNT:
                break
            if rec["quiz_id"] not in existing_ids:
                selected.append(rec)
                existing_ids.add(rec["quiz_id"])

    # rank 부여
    for i, rec in enumerate(selected, start=1):
        rec["rank"] = i

    if not _check_min_constraints_satisfied(selected):
        print("  [WARN] 최솟값 제약 미충족 — 퀴즈 수가 부족할 수 있습니다.")

    return selected


def _greedy_select(sorted_records: list[dict], blueprint_max: int) -> list[dict]:
    selected: list[dict] = []
    for rec in sorted_records:
        if len(selected) >= TARGET_COUNT:
            break
        if _violates_constraints(rec, selected, blueprint_max):
            continue
        selected.append(rec)
    return selected

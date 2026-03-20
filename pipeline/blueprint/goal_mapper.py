"""Blueprint 블록: dominant_type → 학습 목표 & 퀴즈 유형 매핑."""


def map_learning_goal_and_types(
    concept: str,
    dominant_type: str,
) -> tuple[str, list[str]]:
    """dominant_type과 개념명으로 learning_goal과 question_type_candidates 결정.

    매핑 규칙:
    - definition   → "개념과 정의를 이해한다" + ["mcq_definition", "fill_blank", "ox_quiz"]
    - comparison   → "개념 간 차이점을 비교 분석한다" + ["mcq_comparison", "ox_quiz"]
    - warning      → "주의할 점을 인식한다" + ["mcq_warning", "short_answer"]
    - procedure    → "절차·단계를 이해한다" + ["fill_blank", "short_answer", "sequence"]
    - example      → "구체적 사례를 이해한다" + ["mcq_example", "fill_blank"]
    - unknown/기타 → "개념을 이해한다" + ["mcq_definition"]

    Args:
        concept: 개념명 (예: "UNION", "조인", "서브쿼리").
        dominant_type: resolve_dominant_type() 결과.

    Returns:
        (learning_goal: str, question_type_candidates: list[str])
    """
    mappings: dict[str, tuple[str, list[str]]] = {
        "definition": (
            f"{concept}의 개념과 정의를 이해한다",
            ["mcq_definition", "fill_blank", "ox_quiz"],
        ),
        "comparison": (
            f"{concept}과 관련 개념의 차이점을 비교 분석한다",
            ["mcq_comparison", "ox_quiz"],
        ),
        "warning": (
            f"{concept} 사용 시 주의할 점을 인식한다",
            ["mcq_warning", "short_answer"],
        ),
        "procedure": (
            f"{concept}의 절차·단계를 이해한다",
            ["fill_blank", "short_answer", "sequence"],
        ),
        "example": (
            f"{concept}의 구체적 사례를 이해한다",
            ["mcq_example", "fill_blank"],
        ),
    }

    if dominant_type in mappings:
        return mappings[dominant_type]
    else:
        # unknown 또는 기타 타입
        return (f"{concept}의 개념을 이해한다", ["mcq_definition"])

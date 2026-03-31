"""Quiz Generation 블록: 개별 퀴즈 응답 검증."""


def validate_quiz(data: dict) -> None:
    """LLM이 반환한 단일 퀴즈 dict를 검증. 문제 있으면 ValueError 발생.

    검증 항목:
    - source_text 비어있지 않음
    - question 비어있지 않음
    - explanation 비어있지 않음
    - mcq: choices 존재, is_answer=True 정확히 1개
    - fill_blank / ox_quiz: answers 비어있지 않음
    - used_fact_ids 최소 1개

    Args:
        data: 단일 퀴즈 dict.

    Raises:
        ValueError: 검증 실패 시.
    """
    quiz_type = data.get("question_type", "")

    if not data.get("source_text", "").strip():
        raise ValueError("source_text가 비어있습니다.")

    if not data.get("question", "").strip():
        raise ValueError("question이 비어있습니다.")

    if not data.get("explanation", "").strip():
        raise ValueError("explanation이 비어있습니다.")

    if quiz_type == "mcq":
        choices = data.get("choices")
        if not choices or not isinstance(choices, list):
            raise ValueError("MCQ choices가 없거나 잘못된 형식입니다.")

        answer_count = sum(1 for c in choices if c.get("is_answer") is True)
        if answer_count != 1:
            raise ValueError(
                f"MCQ is_answer=True 항목이 {answer_count}개입니다. 정확히 1개여야 합니다."
            )

        if len(choices) < 2:
            raise ValueError(f"MCQ choices가 {len(choices)}개입니다. 최소 2개 이상 필요합니다.")

    elif quiz_type in ("fill_blank", "ox_quiz"):
        if not str(data.get("answers", "")).strip():
            raise ValueError(f"{quiz_type}의 answers 필드가 비어있습니다.")

    if not data.get("used_fact_ids"):
        raise ValueError("used_fact_ids가 비어있습니다.")


def validate_batch(quizzes: list[dict]) -> tuple[list[dict], list[str]]:
    """퀴즈 배열 전체를 검증. 통과한 것만 반환.

    Args:
        quizzes: LLM이 반환한 퀴즈 dict 목록.

    Returns:
        (valid: list[dict], errors: list[str])
        - valid: 검증 통과한 퀴즈 목록
        - errors: 실패 메시지 목록 (로깅용)
    """
    valid: list[dict] = []
    errors: list[str] = []

    for i, quiz in enumerate(quizzes):
        try:
            validate_quiz(quiz)
            valid.append(quiz)
        except ValueError as e:
            concept = quiz.get("blueprint_id", f"quiz[{i}]")
            errors.append(f"{concept}: {e}")

    return valid, errors

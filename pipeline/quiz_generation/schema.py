"""Quiz Generation 블록 출력 스키마: QuizDocument."""

from pydantic import BaseModel, field_validator


class Choice(BaseModel):
    """객관식 선지."""

    id: int
    text: str
    is_answer: bool


class QuizMeta(BaseModel):
    """퀴즈 생성 메타데이터."""

    attempt_count: int
    """LLM 호출 시도 횟수."""

    llm_model: str
    """사용된 LLM 모델명. 예: "gemini-2.5-flash"."""

    used_fact_ids: list[str]
    """이 퀴즈에 사용된 fact 문장 목록. used_facts 관리용."""


class QuizDocument(BaseModel):
    """퀴즈 문서.

    BlueprintDocument를 기반으로 LLM이 생성하는 실제 퀴즈 문항.
    """

    quiz_id: str
    """퀴즈 ID. 형식: "q_" + uuid4().hex[:8]."""

    blueprint_id: str
    """원본 BlueprintDocument.blueprint_id."""

    lecture_id: str
    """강의 ID."""

    week: int
    """강의 주차."""

    question_type: str
    """퀴즈 유형.

    "mcq_definition" | "mcq_misconception" | "fill_blank" | "ox_quiz" | "code_execution"
    """

    question_format: str
    """출제 형식 문구. 예: "옳지 않은 것은?", "빈칸 채우기", "O/X 퀴즈"."""

    difficulty: str
    """난이도. "상" | "중" | "하". LLM이 판단."""

    question: str
    """문항 본문."""

    choices: list[Choice] | None = None
    """선지 목록. mcq 유형만 사용."""

    answers: str | None = None
    """정답 문자열. fill_blank, ox_quiz, code_execution 유형에서 사용."""

    code_template: str | None = None
    """코드 템플릿. code_execution 유형만 사용."""

    source_text: str
    """정답 근거 원문. 반드시 비어있지 않아야 함."""

    explanation: str
    """해설."""

    meta: QuizMeta
    """생성 메타데이터."""

    @field_validator("source_text")
    @classmethod
    def validate_source_text(cls, v: str) -> str:
        """source_text가 비어있으면 오류."""
        if not v or not v.strip():
            raise ValueError("source_text가 비어있습니다.")
        return v

    @field_validator("difficulty")
    @classmethod
    def validate_difficulty(cls, v: str) -> str:
        """difficulty가 허용된 값인지 확인."""
        allowed = {"상", "중", "하"}
        if v not in allowed:
            raise ValueError(f"difficulty={v!r}는 허용되지 않습니다. 허용값: {allowed}")
        return v

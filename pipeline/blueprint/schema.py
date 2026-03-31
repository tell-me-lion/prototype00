"""Blueprint 블록 출력 스키마: BlueprintDocument (v6)."""

from pydantic import BaseModel, field_validator


class Evidence(BaseModel):
    """문항 생성에 필요한 근거 자료."""

    chunk_ids: list[str]
    """근거로 사용된 chunk ID 목록."""

    correct_facts: list[str]
    """정답 근거 facts. 개념이 주어인 문장들."""

    distractor_facts: list[str]
    """오답 재료 facts. LLM이 선지 재조합용으로 사용."""

    distractor_sources: dict[str, int]
    """distractor_facts 출처 추적.

    예: {"same_chunk": 2, "related": 1}
    - same_chunk: 같은 청크의 나머지 facts
    - related: related_concepts의 correct_facts
    """


class BlueprintDocument(BaseModel):
    """퀴즈 블루프린트 문서 (v6 슬림화).

    EP 블록의 ConceptDocument를 기반으로 생성되며,
    Evidence 분리(correct_facts / distractor_facts)가 핵심 역할이다.
    dominant_type, learning_goal, difficulty, review_point 등의 판단은
    Quiz Generation 블록의 LLM이 담당한다.
    """

    blueprint_id: str
    """블루프린트 ID. 형식: "bp_" + concept.lower().replace(" ", "_")."""

    lecture_id: str
    """강의 ID. 파일명(확장자 제외)."""

    week: int
    """강의 주차."""

    concept: str
    """개념명. 예: "UNION", "조인", "서브쿼리"."""

    definition: str
    """개념의 정의. ConceptDocument.definition 그대로 전달."""

    importance: float
    """중요도 점수. 0.0 ~ 1.0. ConceptDocument.importance 그대로 전달."""

    related_concepts: list[str]
    """관련 개념 ID 목록. ConceptDocument.related_concepts 그대로 전달."""

    chunk_distance_minutes: float
    """첫 번째 청크(시간순)와 마지막 청크 사이의 시간 거리(분)."""

    evidence: Evidence
    """문항 생성을 위한 근거 자료."""

    used_count: int = 0
    """이 blueprint로 생성된 퀴즈 수."""

    ungenerable: bool = False
    """생성 불가 여부. 정답이나 보기가 부족할 때 True."""

    @field_validator("blueprint_id")
    @classmethod
    def validate_blueprint_id(cls, v: str, info) -> str:
        """blueprint_id가 규칙을 따르는지 확인."""
        data = info.data
        if "concept" in data:
            expected = "bp_" + data["concept"].lower().replace(" ", "_")
            if v != expected:
                raise ValueError(f"blueprint_id={v!r} 이 규칙에 맞지 않습니다.")
        return v

    class Config:
        """Pydantic 설정."""

        json_schema_extra = {
            "example": {
                "blueprint_id": "bp_union",
                "lecture_id": "2026-02-11_kdt-backend-21th",
                "week": 21,
                "concept": "UNION",
                "definition": "두 SELECT 결과를 세로로 병합하면서 중복 행을 제거하는 집합 연산자이다.",
                "importance": 0.87,
                "related_concepts": ["concept_join", "concept_cast"],
                "chunk_distance_minutes": 23.5,
                "evidence": {
                    "chunk_ids": ["S01-C02"],
                    "correct_facts": [
                        "UNION은 두 SELECT 결과를 합치면서 중복 행을 제거하여 출력한다"
                    ],
                    "distractor_facts": [
                        "UNION ALL은 중복 제거 없이 모든 행을 출력하여 UNION보다 처리 속도가 빠르다"
                    ],
                    "distractor_sources": {"same_chunk": 1, "related": 0},
                },
                "used_count": 0,
                "ungenerable": False,
            }
        }

"""EP 블록 출력 스키마: ConceptDocument."""

from pydantic import BaseModel, field_validator


class ConceptDocument(BaseModel):
    """핵심 개념 문서.

    강의에서 추출한 핵심 개념을 표현하며, blueprint 생성 및 퀴즈 생성의 기초 자료로 사용된다.
    """

    concept_id: str
    """개념 ID. 규칙: "concept_" + concept.lower().replace(" ", "_")."""

    concept: str
    """개념명. 예: "UNION", "조인", "서브쿼리"."""

    definition: str
    """개념의 정의. type="definition" fact 우선, 없으면 가장 긴 fact 문장."""

    related_concepts: list[str]
    """관련 개념 ID 목록. 코사인 유사도 기반으로 연결된 개념들."""

    source_chunk_ids: list[str]
    """이 개념이 등장한 chunk ID 목록. 예: ["S01-C01", "S01-C03"]."""

    week: int
    """강의 주차. 파일명에서 추출."""

    lecture_id: str
    """강의 ID. 파일명(확장자 제외)."""

    importance: float
    """중요도 점수. 0.0 ~ 1.0 범위."""

    @field_validator("concept_id")
    @classmethod
    def validate_concept_id(cls, v: str, info) -> str:
        """concept_id가 규칙을 따르는지 확인.

        규칙: "concept_" + concept.lower().replace(" ", "_")
        """
        data = info.data
        if "concept" in data:
            expected = "concept_" + data["concept"].lower().replace(" ", "_")
            if v != expected:
                raise ValueError(
                    f"concept_id={v} does not match rule. Expected: {expected}"
                )
        return v

    @field_validator("importance")
    @classmethod
    def validate_importance(cls, v: float) -> float:
        """importance가 0~1 범위인지 확인."""
        if not (0.0 <= v <= 1.0):
            raise ValueError(f"importance must be 0.0~1.0, got {v}")
        return v

    class Config:
        """Pydantic 설정."""

        json_schema_extra = {
            "example": {
                "concept_id": "concept_union",
                "concept": "UNION",
                "definition": "두 SELECT 결과를 세로로 병합하면서 중복 행을 제거하는 집합 연산자이다.",
                "related_concepts": ["concept_join", "concept_cast"],
                "source_chunk_ids": ["S01-C03", "S01-C04"],
                "week": 21,
                "lecture_id": "2026-02-11_kdt-backend-21th",
                "importance": 0.87,
            }
        }

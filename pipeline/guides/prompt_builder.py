"""Guides 블록: 학습 가이드 프롬프트 조립."""

SYSTEM_INSTRUCTION = (
    "당신은 IT 프로그래밍 교육 과정의 주차별 학습 가이드를 작성하는 전문가입니다.\n"
    "수강생이 이번 주에 무엇을 배웠는지 구조적으로 이해하고, "
    "스스로 복습 계획을 세울 수 있도록 돕는 가이드를 생성합니다.\n"
    "반드시 응답은 JSON 객체만 출력합니다. 설명, 마크다운, 백틱 없이 순수 JSON만 반환합니다."
)


def build_guide_prompt(
    week: int,
    facts: list[dict],
    concepts: list[dict] | None = None,
    learning_points: list[dict] | None = None,
    prev_overview: str | None = None,
) -> str:
    """학습 가이드 생성 프롬프트 조립.

    Args:
        week: 주차 번호.
        facts: phase5_facts chunk dict 목록.
        concepts: ep_concepts dict 목록 (importance >= 0.3 필터링 済).
        learning_points: ep_learning_points dict 목록.
        prev_overview: 이전 주차 가이드의 overview (없으면 None).

    Returns:
        LLM에 전달할 프롬프트 문자열.
    """
    facts_section = _format_facts(facts)
    concepts_section = _format_concepts(concepts or [])
    lp_section = _format_learning_points(learning_points or [])
    prev_section = f"\n===== 이전 주차({week - 1}주차) 학습 개요 =====\n{prev_overview}\n" if prev_overview else ""

    return f"""아래 {week}주차 강의 자료를 바탕으로 주차별 학습 가이드를 JSON 객체로 생성하세요.

===== 핵심 개념 (EP Concepts) =====
{concepts_section}

===== 학습 포인트 (EP Learning Points) =====
{lp_section}

===== 강의 원문 팩트 =====
{facts_section}
{prev_section}
===== 학습 가이드 생성 원칙 =====

1. **섹션(sections) 작성 원칙**
   - 날짜순 나열 금지. 주제별로 그룹핑 (같은 개념이 여러 강의에 걸치면 하나의 섹션으로 통합)
   - 섹션 수: 2~5개 (너무 적으면 뭉뚱그림, 너무 많으면 산만)
   - 섹션 제목(title): 핵심 키워드 포함, 15자 이내 (예: "UNION과 집합 연산", "서브쿼리 활용")
   - 섹션 요약(summary): 해요체, 2~3문장, "이번 주에는 ~를 배웠어요. ~가 핵심이에요." 패턴
   - key_takeaways: "~입니다" 종결, 구체적 사실 기반 (추상적 서술 금지)
     - 좋은 예: "UNION은 두 SELECT 결과를 세로로 병합하며, 기본적으로 중복 행을 제거합니다"
     - 나쁜 예: "UNION은 중요한 연산자입니다"
   - related_concepts: 해당 섹션과 관련된 concept_id 목록 (EP Concepts에서 선택)

2. **개념 연결(connections)**
   - "A를 이해하면 B와의 차이가 명확해집니다" 패턴 사용
   - 단순 나열("A와 B가 관련됩니다") 금지
   - 구체적 관계 유형 명시: 상위/하위, 대비, 전제 조건, 확장 관계

3. **학습 팁(study_tips) 3~5개**
   - "주의하세요" 수준의 일반론 금지
   - 구체적 실습 행동으로 작성
     - 좋은 예: "UNION과 UNION ALL의 차이를 직접 실행해서 행 수가 달라지는 것을 확인해 보세요"
     - 나쁜 예: "UNION을 잘 이해해 두세요"
   - 최소 1개는 "직접 코드를 작성/실행" 형태의 실습 팁

4. **복습 우선순위(review_priorities) 상위 3개**
   - EP concepts의 importance 기반, "개념명: 왜 중요한지 한 줄"
   - 예: "JOIN: 실무에서 거의 모든 쿼리에 사용되는 핵심 연산"

5. **자가 점검(self_check) 3~5개**
   - 퀴즈가 아님. "이걸 설명할 수 있으면 이해한 것" 수준의 열린 질문
   - question: 해요체, "~를 설명할 수 있나요?", "~의 차이를 알고 있나요?"
   - hint: 사고 방향 제시, 답을 직접 주지 않음 ("~를 기준으로 비교해 보세요")

6. **선수 지식(prerequisites)**
   - 이전 주차 overview가 있으면 그 내용을 참고하여 작성
   - 형식: "N주차에서 배운 개념명" (예: "3주차에서 배운 SELECT 기초 문법")
   - 이전 주차 정보 없으면 빈 배열

7. **난이도 안내(difficulty_note)**
   - 이번 주에서 특히 어려운 부분과 그 이유를 구체적으로 서술
   - 어떻게 접근하면 좋은지 한 줄 조언 포함

8. **STT 노이즈/비유 표현 처리**
   - "3번 패키지", "저기", "이 밑에 있는 것" 등 화면 지칭 대명사 → 표준 기술 용어로 치환
   - 의미 해석 불가한 단어는 IT 도메인 지식으로 대체, 불가능하면 생략

===== 응답 형식 (JSON 객체 only) =====

```json
{{
  "overview": "이번 주 학습 한줄 요약 (해요체, 1~2문장)",
  "sections": [
    {{
      "title": "섹션 제목 (15자 이내)",
      "summary": "해요체 2~3문장 요약",
      "key_takeaways": ["~입니다", "~입니다"],
      "related_concepts": ["concept_id_1", "concept_id_2"]
    }}
  ],
  "connections": "개념 간 관계 설명 (2~3문장)",
  "study_tips": ["구체적 실습 팁 1", "구체적 실습 팁 2"],
  "difficulty_note": "난이도 안내 + 접근 조언",
  "review_priorities": ["개념명: 왜 중요한지", "개념명: 왜 중요한지"],
  "self_check": [
    {{"question": "~를 설명할 수 있나요?", "hint": "~를 기준으로 비교해 보세요"}}
  ],
  "prerequisites": ["N주차에서 배운 X"],
  "key_concepts": ["핵심 개념명1", "핵심 개념명2"]
}}
```

위 형식을 엄격히 지켜 JSON 객체만 반환하세요."""


def _format_facts(chunks: list[dict]) -> str:
    """Facts chunk 목록을 LLM 입력용 텍스트로 포맷."""
    lines: list[str] = []
    for chunk in chunks:
        chunk_id = chunk.get("chunk_id", "")
        facts = chunk.get("facts", [])
        if not facts:
            continue
        lines.append(f"[{chunk_id}]")
        for fact in facts[:4]:
            lines.append(f"  - {fact}")
        lines.append("")
    return "\n".join(lines) if lines else "(없음)"


def _format_concepts(concepts: list[dict]) -> str:
    """EP concepts를 importance순 정렬 후 포맷."""
    if not concepts:
        return "(없음)"
    sorted_concepts = sorted(concepts, key=lambda c: c.get("importance", 0), reverse=True)[:20]
    lines: list[str] = []
    for c in sorted_concepts:
        cid = c.get("concept_id", "")
        name = c.get("concept", "")
        definition = c.get("definition", "")
        importance = c.get("importance", 0)
        related = c.get("related_concepts", [])[:3]
        lines.append(f"[{cid}] {name} (importance={importance:.2f})")
        if definition:
            lines.append(f"  정의: {definition}")
        if related:
            lines.append(f"  관련: {', '.join(related)}")
        lines.append("")
    return "\n".join(lines)


def _format_learning_points(points: list[dict]) -> str:
    """EP learning points를 포맷."""
    if not points:
        return "(없음)"
    sorted_pts = sorted(points, key=lambda p: p.get("importance", 0), reverse=True)[:15]
    lines: list[str] = []
    for p in sorted_pts:
        name = p.get("concept", "")
        definition = p.get("definition", "")
        importance = p.get("importance", 0)
        lines.append(f"- {name} (importance={importance:.2f}): {definition}")
    return "\n".join(lines)

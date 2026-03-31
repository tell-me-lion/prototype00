"""Quiz Generation 블록: 전체 BP + Chunk → 단일 LLM 프롬프트 조립."""

SYSTEM_INSTRUCTION = (
    "당신은 IT 프로그래밍 교육 문항 출제 전문가입니다.\n"
    "강의 자료를 분석해 학습 효과가 높은 퀴즈를 생성합니다.\n"
    "반드시 응답은 JSON 배열만 출력합니다. 설명, 마크다운, 백틱 없이 순수 JSON 배열만 반환합니다."
)


def build_batch_prompt(
    blueprints: list[dict],
    chunks: list[dict],
    quiz_count: int = 30,
) -> str:
    """전체 blueprint + chunk를 컨텍스트로 하는 단일 배치 프롬프트 조립.

    LLM이 전체 강의 내용을 보고:
    - 출제할 개념과 유형을 자체 판단
    - 오답지 맥락 일관성도 자체 점검

    Args:
        blueprints: BlueprintDocument dict 목록 (전체 또는 importance 필터링).
        chunks: phase5_facts chunk dict 목록.
        quiz_count: 생성할 퀴즈 수.

    Returns:
        LLM에 전달할 프롬프트 문자열.
    """
    bp_section = _format_blueprints(blueprints)
    chunk_section = _format_chunks(chunks)

    return f"""아래 강의 자료를 바탕으로 퀴즈 {quiz_count}문제를 생성하세요.

===== 핵심 개념 목록 (Blueprint) =====
{bp_section}

===== 강의 원문 청크 =====
{chunk_section}

===== 퀴즈 생성 원칙 =====

정확히 {quiz_count}문제를 생성하되, 다음 원칙을 엄격하게 지키세요:

1. **출제 대상(개념) 우선순위 강제 (초핵심 도메인 필터링)**
   - 전달받은 핵심 개념 목록 중 일상 범용 명사나 포괄적 단어(예: 데이터, 코드, 시스템, 스템, 변수 등)는 중요도(importance)가 높게 들어왔더라도 **문제 출제를 건너뛸 것(SKIP)**.

2. **문제 유형 및 구조 (오프라인 통계 기준)**
   - 객관식(`mcq`)의 보기(선지) 개수는 **기본 5지선다(5개)**로 구성하되, [하] 난이도(단일 확인형) 문제에만 예외적으로 4지선다를 허용.
   - 객관식 질문 포맷은 "옳은 것은?"(약 70~80%), "틀린 것은?/아닌 것은?"(약 20~30%) 비율이 되도록 분배.
   - 유형 쿼터: 전체 {quiz_count}문제 중 O/X(`ox_quiz`)는 최대 20%로 제한, 빈칸 채우기(`fill_blank`)는 최소 20% 이상 생성.
   - 난이도 분배: 상/중/하 난이도가 골고루 나오도록 분배하며, 결과 JSON에 `"difficulty"` 필드(상/중/하)를 정확히 명시할 것.
   - distractor로 쓸 수 있는 문장이 2개 이상일 때만 객관식(`mcq`) 출제, 코드 관련이면 `code_execution` 고려.

3. **난이도별 문항 설계 및 정답/보기 작법 (데이터셋 가이드라인)**
   - **(공통 필수)** 퀴즈 설계 시 단편적인 한 문장에만 의존하지 말 것. 반드시 '핵심 개념(Blueprint)'의 요약 정보와 하단의 '강의 원문 청크' 전체를 교차 검증하여 앞뒤 문맥과 강사의 진짜 의도를 완벽히 파악한 후 출제할 것.
   - **[하] 난이도 (기초 문법/키워드 식별)**: 질문은 15~24자 내외로 짧게 구성. 정답/오답 보기도 서술형이 아닌 짧은 `개념어`, `영문 키워드`, `메서드 기호`(예: String, start()) 위주로 구성.
   - **[중] 난이도 (개념 정의 및 특징 판단)**: 질문은 21~30자 내외로 구성. 정답/오답 보기는 `명사구(Phrase)`나 특징을 설명하는 짧은 `서술형 문장`으로 구성.
   - **[상] 난이도 (복수 조건 및 예외 판별)**: 질문은 30자 이상(상세한 묻기)으로 구성. 정답/오답 보기는 예외나 세부 동작을 다루는 긴 `복합 서술형 문장`으로 구성.
   - **(공통 문체)** 원래 문장 형태를 완전히 파괴하더라도 문맥을 추론해 **IT 표준 기술 용어와 전문 서적 문체(다나까체)로 전면 재작성**하여 기술적 정확성을 최우선할 것. 보기 간 길이 밸런스를 유지할 것.

4. **오답(Distractor) 설계 4대 패턴 (중의성/복수정답 엄격 차단)**
   - 오답 선지는 우연히 맞는(참인) 사실이 포함되어 복수 정답 논란이 생기지 않도록 철저히 통제해야 함.
   - 아래 오프라인 4가지 패턴을 응용해 **명백하고 치명적인 '거짓' 문구로 왜곡(Distortion)** 창작할 것.
   ① **인접 개념 함정 (Sibling Concepts)**: 질문과 같은 범주 내의 다른 유사 개념 특징을 가져와 헷갈리게 함.
   ② **속성 반전 함정 (Property Swap)**: 정답만의 핵심 속성(예: 읽기 전용)을 완전 반대(쓰기 가능)로 바꿈.
   ③ **키워드 중첩 함정**: 질문/정답에 나온 올바른 키워드로 시작하되, 후반부의 성질이나 용도를 전혀 다르게 조작함.
   ④ **과장형 함정 (Overstated/Partially True)**: 문장의 대부분은 맞게 두고 "반드시 ~해야만 한다", "~에서만 지원된다" 등 조건부/절대적/예외적 표현을 끼워 넣어 부분 모순되게 만듦.

5. **문장 재사용 금지**
   - 이미 사용된 문장(정답/오답 모두 포함)은 다른 문제에 절대 다시 쓰지 말 것.
   - 의미가 동일한 문장은 표현이 달라도 재사용으로 간주함.
   - 재사용 없이 만들 수 있는 문제가 없으면 → 해당 blueprint는 문제 생성을 건너뛸 것 (SKIP).

6. **한 blueprint에서 여러 문제 생성 시**
   - 같은 사실을 다른 각도로 묻는 것은 허용 지정.
   - 단, 정답이 완전히 동일한 문제는 생성 금지.
   - 각 문제의 `source_text`에는 교정/왜곡 등을 적용하기 전의 원시 문장을 그대로 기재할 것.

7. **기타 (STT 노이즈 및 비유적 표현 초강력 검열)**
   - "3번 패키지", "저기", "이 밑에 있는 것", "속성에 객체가 들어있다" 등 강사의 화면 지칭 대명사나 개인적 비유는 **절대 퀴즈에 복사하지 말 것**.
   - 해당 비유는 앞뒤 문맥을 파악하여 표준 기술 용어로 능동적으로 치환(예: 3번 패키지 -> java.util 패키지 등)하거나 생략.
   - 의미 해석이 안 되는 생소한 단어는 100% STT 오류임을 인지하고 IT 도메인 지식을 총동원해 능동적으로 대체하거나, 대체가 불가능하면 해당 개념은 출제하지 말 것.
   - **IT 전문 용어 사전에 없는 정체불명의 단어는 문제 생성 시 무조건 건너뛸 것(SKIP).** 이런 단어가 정답(`answers`)이나 지문에 포함되는 것을 엄격히 금지함.

===== 문제 품질 자체 점검 (MCQ 생성 후 반드시 확인) =====

각 MCQ 문제를 완성한 후, 다음 항목을 스스로 점검하고 문제가 있으면 즉시 수정하세요:

- [ ] **출처**: 오답 선지는 강의 원문(청크)에서 실제로 언급된 내용만 사용. 없는 내용 창작 금지.
- [ ] **문맥**: 오답 선지가 문제 문장과 문맥이 자연스럽게 이어지는가? (예: "~의 역할은?" 질문에 역할이 아닌 내용이 선지에 있으면 안 됨)
- [ ] **변별력**: 오답끼리 너무 유사하지 않은가? 각 선지가 독립적으로 의미를 가지는가?
- [ ] **길이 균형**: 정답 선지가 오답보다 유독 길거나 짧으면 수정.

===== 응답 형식 (JSON 배열 only) =====

```json
[
  {{
    "blueprint_id": "bp_xxx",
    "question_type": "mcq",
    "question_format": "옳지 않은 것은?",
    "difficulty": "중",
    "question": "다음 중 XXX에 대한 설명으로 옳지 않은 것은?",
    "choices": [
      {{"id": 0, "text": "...", "is_answer": false}},
      {{"id": 1, "text": "...", "is_answer": true}},
      {{"id": 2, "text": "...", "is_answer": false}},
      {{"id": 3, "text": "...", "is_answer": false}}
    ],
    "answers": null,
    "source_text": "정답 근거가 된 강의 원문 문장",
    "explanation": "왜 해당 선지가 정답인지 설명",
    "used_fact_ids": ["근거로 사용한 원문 문장1", "원문 문장2"]
  }},
  {{
    "blueprint_id": "bp_yyy",
    "question_type": "fill_blank",
    "question_format": "빈칸 채우기",
    "difficulty": "하",
    "question": "( )은(는) ...",
    "choices": null,
    "answers": "정답 단어",
    "source_text": "정답 근거가 된 강의 원문 문장",
    "explanation": "해설",
    "used_fact_ids": ["근거로 사용한 원문 문장"]
  }},
  {{
    "blueprint_id": "bp_zzz",
    "question_type": "ox_quiz",
    "question_format": "O/X 퀴즈",
    "difficulty": "하",
    "question": "다음 설명이 맞으면 O, 틀리면 X를 고르세요. ...",
    "choices": null,
    "answers": "O",
    "source_text": "정답 근거가 된 강의 원문 문장",
    "explanation": "해설",
    "used_fact_ids": ["근거로 사용한 원문 문장"]
  }}
]
```

위 형식을 엄격히 지켜 JSON 배열만 반환하세요."""


def _format_blueprints(blueprints: list[dict]) -> str:
    """Blueprint 목록을 LLM 입력용 텍스트로 포맷.

    importance 내림차순 정렬. 각 BP에서 핵심 필드만 추출.
    """
    sorted_bps = sorted(blueprints, key=lambda b: b.get("importance", 0), reverse=True)
    lines: list[str] = []
    for bp in sorted_bps:
        concept = bp.get("concept", "")
        bp_id = bp.get("blueprint_id", "")
        definition = bp.get("definition", "")
        importance = bp.get("importance", 0)
        related = [
            cid.replace("concept_", "").replace("_", " ")
            for cid in bp.get("related_concepts", [])[:4]
        ]
        correct = bp.get("evidence", {}).get("correct_facts", [])
        distractor = bp.get("evidence", {}).get("distractor_facts", [])[:6]

        lines.append(f"[{bp_id}] {concept} (importance={importance:.2f})")
        lines.append(f"  정의: {definition}")
        if related:
            lines.append(f"  관련 개념: {', '.join(related)}")
        if correct:
            lines.append(f"  정답 근거: {correct[0]}")
        if distractor:
            lines.append(f"  오답 재료({len(distractor)}개): " + " / ".join(distractor[:3]))
        lines.append("")

    return "\n".join(lines)


def _format_chunks(chunks: list[dict]) -> str:
    """Chunk 목록을 LLM 입력용 텍스트로 포맷.

    각 청크에서 chunk_id, text, facts만 추출.
    """
    lines: list[str] = []
    for chunk in chunks:
        chunk_id = chunk.get("chunk_id", "")
        text = chunk.get("text", "").strip()
        facts = chunk.get("facts", [])

        if not text and not facts:
            continue

        lines.append(f"[{chunk_id}]")
        if text:
            # 너무 긴 텍스트는 앞 200자만
            lines.append(f"  원문: {text[:200]}{'...' if len(text) > 200 else ''}")
        if facts:
            for fact in facts[:4]:  # 청크당 최대 4개
                lines.append(f"  - {fact}")
        lines.append("")

    return "\n".join(lines)

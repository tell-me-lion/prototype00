"""단계 3 — 난이도 검사: LLM 예측 오답률.

Gemini에게 퀴즈를 제시하고 일반 학생의 예상 오답률(0.0~1.0)을 반환받는다.
- 오답률 < 0.2: 너무 쉬움 → 난이도 조정 후 재생성
- 오답률 > 0.95: 문제 이상 또는 극도로 어려움 → 재생성
- 0.2 ~ 0.95: pass
"""

from __future__ import annotations

import json
import os

import google.genai as genai
from dotenv import load_dotenv
from google.genai import types

load_dotenv()

MODEL_NAME = "gemini-2.5-flash"
DIFFICULTY_MIN = 0.2
DIFFICULTY_MAX = 0.95

_client: genai.Client | None = None

_SYSTEM_INSTRUCTION = """\
당신은 교육 평가 전문가입니다.
주어진 퀴즈를 분석하여 JSON으로만 응답하세요. 추가 설명 없이 JSON만 출력하세요.
"""

_PROMPT_TEMPLATE = """\
다음 퀴즈를 Java 강의를 수강 중인 일반 학생 100명이 풀었을 때,
몇 명이 오답을 선택할지 예측하세요.

퀴즈 유형: {question_type}
난이도 표시: {difficulty}
문제: {question}
{choices_section}
정답 근거(source_text): {source_text}

응답 형식 (JSON만, 설명 없이):
{{"predicted_error_rate": 0.45}}

- 0.0 = 모두 정답 (너무 쉬움)
- 1.0 = 모두 오답 (너무 어렵거나 문제 이상)
- 0.3~0.6 = 적절한 변별력
"""


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise RuntimeError("GOOGLE_API_KEY 환경변수가 설정되지 않았습니다.")
        _client = genai.Client(api_key=api_key)
    return _client


def _build_choices_section(quiz: dict) -> str:
    choices = quiz.get("choices")
    if not choices:
        answers = quiz.get("answers", "")
        return f"정답: {answers}" if answers else ""
    lines = []
    for c in choices:
        marker = "[정답]" if c.get("is_answer") else "      "
        lines.append(f"  {marker} {c.get('id', '')}) {c.get('text', '')}")
    return "선택지:\n" + "\n".join(lines)


def check_difficulty(quiz: dict) -> tuple[bool, float]:
    """Gemini LLM으로 예상 오답률을 측정하고 pass/fail을 판단한다.

    Args:
        quiz: QuizDocument dict.

    Returns:
        (passed, predicted_error_rate)
        - passed: DIFFICULTY_MIN <= rate <= DIFFICULTY_MAX
        - predicted_error_rate: 0.0~1.0
    """
    prompt = _PROMPT_TEMPLATE.format(
        question_type=quiz.get("question_type", ""),
        difficulty=quiz.get("difficulty", ""),
        question=quiz.get("question", ""),
        choices_section=_build_choices_section(quiz),
        source_text=quiz.get("source_text", ""),
    )

    client = _get_client()
    config = types.GenerateContentConfig(
        system_instruction=_SYSTEM_INSTRUCTION,
        temperature=0.2,
        response_mime_type="application/json",
    )

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
        config=config,
    )

    raw = response.text.strip()
    if raw.startswith("```"):
        lines = raw.splitlines()
        raw = "\n".join(l for l in lines if not l.startswith("```")).strip()

    try:
        data = json.loads(raw)
        rate = float(data["predicted_error_rate"])
        rate = max(0.0, min(1.0, rate))
    except Exception as e:
        print(f"  [WARN] difficulty_checker 파싱 실패: {e} | raw={raw[:100]}")
        rate = 0.5  # 파싱 실패 시 중간값으로 pass 처리

    passed = DIFFICULTY_MIN <= rate <= DIFFICULTY_MAX
    return passed, round(rate, 4)

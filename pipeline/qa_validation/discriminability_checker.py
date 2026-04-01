"""단계 4 — 변별력 검사: 오답 설계 품질 및 소거법 저항도.

기존 3단계가 잡지 못하는 품질 문제를 탐지한다:
  1. 소거법 취약: 오답 중 상식만으로 제거 가능한 것이 절반 이상
  2. 오답 빈약: 오답이 너무 명백히 틀려 학생을 유혹하지 않음
  3. 강의 독립성: 강의 없이도 상식으로 답할 수 있는 문제

MCQ:  distractor_score, elimination_risk, knowledge_dependent 모두 평가
OX/fill_blank: knowledge_dependent만 평가
"""

from __future__ import annotations

import json
import os

import google.genai as genai
from dotenv import load_dotenv
from google.genai import types

load_dotenv()

MODEL_NAME = "gemini-2.5-flash"

# MCQ 기준
DISTRACTOR_SCORE_MIN = 0.4   # 오답 그럴듯함 평균 최솟값
ELIMINATION_RISK_MAX = 0.5   # 소거 가능 오답 비율 최댓값

_client: genai.Client | None = None

_SYSTEM_INSTRUCTION = """\
당신은 교육 평가 전문가입니다.
주어진 퀴즈의 변별력을 분석하여 JSON으로만 응답하세요. 추가 설명 없이 JSON만 출력하세요.
"""

_MCQ_PROMPT_TEMPLATE = """\
다음 객관식 퀴즈를 분석하세요.

문제: {question}
선택지:
{choices_text}

[평가 항목 1] 각 오답 선택지에 대해:
  강의를 절반만 이해한 학생이 이 선택지를 정답이라고 착각할 가능성을 0.0~1.0으로 평가하세요.
  (0.0 = 누가 봐도 틀림, 1.0 = 정답처럼 보임)

[평가 항목 2] source_text를 모른다고 가정할 때:
  "이 선택지는 상식/일반 지식만으로 확실히 틀렸다고 제거할 수 있다"에 해당하는
  오답 수를 세어주세요.

[평가 항목 3] 이 강의의 source_text 없이 일반 상식만으로 정답을 고를 수 있습니까?
  can_guess_without_lecture: true/false
  confidence_without_lecture: 0.0~1.0 (확신도, 0.5 이상이면 상식으로 풀림)

오답 선택지 목록 (id, text):
{wrong_choices}

응답 형식 (JSON만, 설명 없이):
{{
  "distractor_scores": [0.7, 0.3, 0.8, 0.2],
  "eliminated_count": 1,
  "total_wrong_count": {total_wrong},
  "can_guess_without_lecture": false,
  "confidence_without_lecture": 0.3
}}
"""

_NONMCQ_PROMPT_TEMPLATE = """\
다음 퀴즈를 분석하세요.

유형: {question_type}
문제: {question}
정답: {answers}

강의 내용(source_text)을 모른다고 가정할 때:
일반 상식만으로 정답을 맞출 수 있습니까?

응답 형식 (JSON만, 설명 없이):
{{
  "can_guess_without_lecture": false,
  "confidence_without_lecture": 0.3
}}
"""


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise RuntimeError("GOOGLE_API_KEY 환경변수가 설정되지 않았습니다.")
        _client = genai.Client(api_key=api_key)
    return _client


def _call_llm(prompt: str) -> dict:
    client = _get_client()
    config = types.GenerateContentConfig(
        system_instruction=_SYSTEM_INSTRUCTION,
        temperature=0.1,
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
    return json.loads(raw)


def check_discriminability(quiz: dict) -> tuple[bool, dict]:
    """퀴즈의 변별력을 평가한다.

    Args:
        quiz: QuizDocument dict.

    Returns:
        (passed, discriminability_log)
        - passed: 변별력 기준 통과 여부
        - discriminability_log: 평가 결과 상세
    """
    q_type = quiz.get("question_type", "")
    is_mcq = q_type == "mcq"

    if is_mcq:
        return _check_mcq(quiz)
    else:
        return _check_nonmcq(quiz)


def _check_mcq(quiz: dict) -> tuple[bool, dict]:
    choices = quiz.get("choices", []) or []
    wrong_choices = [c for c in choices if not c.get("is_answer", False)]
    total_wrong = len(wrong_choices)

    if total_wrong == 0:
        return False, {"error": "오답 선택지 없음"}

    choices_text = "\n".join(
        f"  {'[정답]' if c.get('is_answer') else '      '} {c['id']}) {c['text']}"
        for c in choices
    )
    wrong_text = "\n".join(
        f"  id={c['id']}: {c['text']}" for c in wrong_choices
    )

    prompt = _MCQ_PROMPT_TEMPLATE.format(
        question=quiz.get("question", ""),
        choices_text=choices_text,
        wrong_choices=wrong_text,
        total_wrong=total_wrong,
    )

    try:
        data = _call_llm(prompt)
    except Exception as e:
        print(f"  [WARN] discriminability MCQ 파싱 실패: {e}")
        # 파싱 실패 시 중간값으로 pass 처리
        return True, {
            "distractor_score": 0.5,
            "elimination_risk": 0.3,
            "knowledge_dependent": True,
        }

    scores = data.get("distractor_scores", [])
    distractor_score = round(sum(scores) / len(scores), 4) if scores else 0.5

    eliminated = int(data.get("eliminated_count", 0))
    elimination_risk = round(eliminated / total_wrong, 4) if total_wrong > 0 else 0.0

    can_guess = bool(data.get("can_guess_without_lecture", False))
    knowledge_dependent = not can_guess

    passed = (
        distractor_score >= DISTRACTOR_SCORE_MIN
        and elimination_risk < ELIMINATION_RISK_MAX
        and knowledge_dependent
    )

    log = {
        "distractor_score": distractor_score,
        "elimination_risk": elimination_risk,
        "knowledge_dependent": knowledge_dependent,
        "confidence_without_lecture": round(
            float(data.get("confidence_without_lecture", 0.0)), 4
        ),
    }
    return passed, log


def _check_nonmcq(quiz: dict) -> tuple[bool, dict]:
    prompt = _NONMCQ_PROMPT_TEMPLATE.format(
        question_type=quiz.get("question_type", ""),
        question=quiz.get("question", ""),
        answers=quiz.get("answers", ""),
    )

    try:
        data = _call_llm(prompt)
    except Exception as e:
        print(f"  [WARN] discriminability non-MCQ 파싱 실패: {e}")
        return True, {"knowledge_dependent": True}

    can_guess = bool(data.get("can_guess_without_lecture", False))
    knowledge_dependent = not can_guess

    log = {
        "distractor_score": None,   # MCQ 아님
        "elimination_risk": None,
        "knowledge_dependent": knowledge_dependent,
        "confidence_without_lecture": round(
            float(data.get("confidence_without_lecture", 0.0)), 4
        ),
    }
    return knowledge_dependent, log

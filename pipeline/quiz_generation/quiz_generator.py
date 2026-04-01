"""Quiz Generation 블록: Gemini API 호출 및 JSON 배열 파싱."""

import json
import os

import google.genai as genai
from dotenv import load_dotenv
from google.genai import types

from .prompt_builder import SYSTEM_INSTRUCTION

load_dotenv()

MODEL_NAME = "gemini-2.5-flash"
_client: genai.Client | None = None


def _get_client() -> genai.Client:
    """Gemini 클라이언트 싱글턴 반환."""
    global _client
    if _client is None:
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise RuntimeError("GOOGLE_API_KEY 환경변수가 설정되지 않았습니다.")
        _client = genai.Client(api_key=api_key)
    return _client


def call_gemini_batch(prompt: str) -> list[dict]:
    """Gemini API를 호출하고 JSON 배열 응답을 파싱해 반환.

    Args:
        prompt: 배치 퀴즈 생성 프롬프트.

    Returns:
        파싱된 퀴즈 dict 목록. 파싱 실패 시 빈 리스트.

    Raises:
        RuntimeError: API 키 없음 또는 API 호출 실패.
    """
    client = _get_client()
    gen_config = types.GenerateContentConfig(
        system_instruction=SYSTEM_INSTRUCTION,
        temperature=0.7,
        top_p=0.95,
        response_mime_type="application/json",
        max_output_tokens=8192,
    )

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
        config=gen_config,
    )

    raw_text = response.text.strip()

    # 마크다운 코드블록 제거
    if raw_text.startswith("```"):
        lines = raw_text.splitlines()
        raw_text = "\n".join(
            line for line in lines if not line.startswith("```")
        ).strip()

    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON 파싱 실패: {e}\n원문(앞 300자): {raw_text[:300]}") from e

    if not isinstance(parsed, list):
        raise ValueError(f"응답이 배열이 아닙니다. 타입: {type(parsed)}")

    return parsed

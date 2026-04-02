"""Guides 블록: Gemini API 호출 및 JSON 객체 파싱."""

import json
import os
import re
import time

import google.genai as genai
from dotenv import load_dotenv
from google.genai import types

from .prompt_builder import SYSTEM_INSTRUCTION

load_dotenv()

MODEL_NAME = "gemini-2.5-flash"
_client: genai.Client | None = None

_RETRYABLE_API_ERRORS = ("429", "503", "RESOURCE_EXHAUSTED", "UNAVAILABLE")
_CODE_BLOCK_RE = re.compile(r"^```[\w]*\n?", re.MULTILINE)
_CODE_BLOCK_END_RE = re.compile(r"\n?```\s*$", re.MULTILINE)


def _get_client() -> genai.Client:
    """Gemini 클라이언트 싱글턴 반환."""
    global _client
    if _client is None:
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise RuntimeError("GOOGLE_API_KEY 환경변수가 설정되지 않았습니다.")
        _client = genai.Client(api_key=api_key)
    return _client


def _strip_markdown_fences(text: str) -> str:
    """마크다운 코드블록 울타리(```json ... ```)를 제거."""
    text = _CODE_BLOCK_RE.sub("", text)
    text = _CODE_BLOCK_END_RE.sub("", text)
    return text.strip()


def _try_repair_json(raw: str) -> str:
    """흔한 LLM JSON 오류를 보정 시도."""
    repaired = re.sub(r",\s*([}\]])", r"\1", raw)
    return repaired


def call_gemini_guide(prompt: str) -> dict:
    """Gemini API를 호출하고 JSON 객체 응답을 파싱해 반환.

    API 에러(429/503) 및 JSON 파싱 에러 시 최대 3회 재시도.

    Returns:
        파싱된 가이드 dict.

    Raises:
        RuntimeError: API 호출 실패.
        ValueError: JSON 파싱 실패.
    """
    client = _get_client()
    gen_config = types.GenerateContentConfig(
        system_instruction=SYSTEM_INSTRUCTION,
        temperature=0.5,
        top_p=0.95,
        response_mime_type="application/json",
        max_output_tokens=16384,
    )

    max_retries = 3
    last_error: Exception | None = None

    for attempt in range(max_retries + 1):
        # ── 1) API 호출 ──
        try:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt,
                config=gen_config,
            )
        except Exception as e:
            last_error = e
            err_str = str(e)
            if attempt < max_retries and any(k in err_str for k in _RETRYABLE_API_ERRORS):
                wait_sec = 15.0 * (2 ** attempt)
                print(f"[Guide Gen] Gemini API 재시도 ({attempt+1}/{max_retries}) — {wait_sec:.0f}초 대기")
                time.sleep(wait_sec)
                continue
            raise RuntimeError(f"Gemini API 호출 실패: {e}") from e

        # ── 2) 응답 텍스트 정리 ──
        raw_text = response.text.strip()
        raw_text = _strip_markdown_fences(raw_text)

        # ── 3) JSON 파싱 ──
        try:
            parsed = json.loads(raw_text)
        except json.JSONDecodeError:
            try:
                parsed = json.loads(_try_repair_json(raw_text))
                print(f"[Guide Gen] JSON 자동 보정 성공 (attempt {attempt+1})")
            except json.JSONDecodeError as e2:
                last_error = e2
                if attempt < max_retries:
                    wait_sec = 10.0 * (2 ** attempt)
                    print(
                        f"[Guide Gen] JSON 파싱 실패, 재시도 ({attempt+1}/{max_retries}) — {wait_sec:.0f}초 대기\n"
                        f"  에러: {e2}\n  원문(앞 500자): {raw_text[:500]}"
                    )
                    time.sleep(wait_sec)
                    continue
                raise ValueError(
                    f"JSON 파싱 실패 ({max_retries+1}회 시도): {e2}\n원문(앞 500자): {raw_text[:500]}"
                ) from e2

        if not isinstance(parsed, dict):
            last_error = ValueError(f"응답이 객체가 아닙니다. 타입: {type(parsed)}")
            if attempt < max_retries:
                print(f"[Guide Gen] 응답이 객체가 아님, 재시도 ({attempt+1}/{max_retries})")
                time.sleep(10.0)
                continue
            raise last_error

        return parsed

    raise RuntimeError(f"Gemini 가이드 생성 {max_retries+1}회 시도 후 실패: {last_error}")

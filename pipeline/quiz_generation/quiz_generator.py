"""Quiz Generation 블록: Gemini API 호출 및 JSON 배열 파싱."""

import json
import os
import re
import time
from collections.abc import Callable

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

# 적응형 재시도: 시도별 퀴즈 수 (None = 원래 프롬프트 그대로)
_RETRY_QUIZ_COUNTS = [None, 20, 15, 10]

# 부분 복구 시 최소 퀴즈 수 — 이 이상이면 재시도 없이 사용
_MIN_PARTIAL_QUIZZES = 10


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
    """흔한 LLM JSON 오류를 보정 시도 — 잘린 JSON 복구 포함."""
    # 1) trailing comma 제거
    repaired = re.sub(r",\s*([}\]])", r"\1", raw)

    # 파싱 성공하면 즉시 반환
    try:
        json.loads(repaired)
        return repaired
    except json.JSONDecodeError:
        pass

    # 2) 미닫힌 문자열 닫기
    if repaired.count('"') % 2 != 0:
        repaired += '"'

    # 3) 미닫힌 배열/객체 닫기
    open_braces = repaired.count("{") - repaired.count("}")
    open_brackets = repaired.count("[") - repaired.count("]")
    repaired += "}" * max(0, open_braces)
    repaired += "]" * max(0, open_brackets)

    # 4) trailing comma 다시 제거
    repaired = re.sub(r",\s*([}\]])", r"\1", repaired)

    return repaired


def _extract_complete_objects(raw: str) -> list[dict] | None:
    """잘린 JSON 배열에서 완전한 객체들만 추출.

    3단계 전략으로 가능한 많은 퀴즈를 복구:
    1) 마지막 완전한 객체 경계(},)를 찾아 배열 닫기 — 가장 정확
    2) 문자 단위 파서 — 중첩 구조 추적
    3) 정규식으로 개별 객체 블록 추출 — 최후 수단
    """
    stripped = raw.strip()
    if not stripped.startswith("["):
        return None

    # ── 전략 1: 마지막 },를 찾아 배열 닫기 (역순 탐색) ──
    # 객체 사이 경계인 },를 역순으로 찾아 그 위치에서 배열을 닫아봄
    closing_positions = [m.start() + 1 for m in re.finditer(r"\}\s*,", stripped)]
    for pos in reversed(closing_positions):
        candidate = stripped[:pos] + "]"
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, list) and len(parsed) > 0:
                return parsed
        except json.JSONDecodeError:
            continue

    # ── 전략 2: 문자 단위 파서 ──
    results: list[dict] = []
    depth = 0
    in_string = False
    escape_next = False
    obj_start = -1

    for i, ch in enumerate(stripped):
        if escape_next:
            escape_next = False
            continue
        if ch == "\\":
            escape_next = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue

        if ch == "{":
            if depth == 1:
                obj_start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 1 and obj_start >= 0:
                obj_str = stripped[obj_start: i + 1]
                try:
                    results.append(json.loads(obj_str))
                except json.JSONDecodeError:
                    pass
                obj_start = -1
        elif ch == "[" and depth == 0:
            depth = 1

    if results:
        return results

    # ── 전략 3: 정규식으로 개별 블록 추출 (최후 수단) ──
    obj_pattern = re.compile(
        r'\{\s*"blueprint_id"\s*:.*?\}(?=\s*[,\]\s])', re.DOTALL
    )
    for match in obj_pattern.finditer(stripped):
        obj_str = match.group(0)
        # 중첩 braces 밸런스 맞추기
        while obj_str.count("{") > obj_str.count("}"):
            obj_str += "}"
        try:
            results.append(json.loads(obj_str))
        except json.JSONDecodeError:
            continue

    return results if results else None


def _check_finish_reason(response) -> str | None:
    """응답의 finish_reason 확인. MAX_TOKENS이면 문자열 반환, 정상이면 None."""
    try:
        candidates = response.candidates
        if candidates and len(candidates) > 0:
            reason = candidates[0].finish_reason
            # Gemini SDK에서 finish_reason은 enum 또는 문자열
            reason_str = str(reason).upper()
            if "MAX_TOKENS" in reason_str or "LENGTH" in reason_str:
                return reason_str
    except (AttributeError, IndexError):
        pass
    return None


def call_gemini_batch(
    prompt: str,
    *,
    rebuild_prompt: Callable[[int], str] | None = None,
) -> list[dict]:
    """Gemini API를 호출하고 JSON 배열 응답을 파싱해 반환.

    API 에러(429/503) 및 JSON 파싱 에러 시 최대 3회 재시도.
    잘린 응답 감지 시 퀴즈 수를 줄여 적응형 재시도.

    Args:
        prompt: 배치 퀴즈 생성 프롬프트.
        rebuild_prompt: 퀴즈 수를 줄여 프롬프트를 재조립하는 콜백.
            ``rebuild_prompt(quiz_count) -> str`` 시그니처.
            None이면 동일 프롬프트로 재시도.

    Returns:
        파싱된 퀴즈 dict 목록.

    Raises:
        RuntimeError: API 키 없음 또는 API 호출 실패.
        ValueError: 최대 재시도 후에도 JSON 파싱 실패.
    """
    client = _get_client()
    gen_config = types.GenerateContentConfig(
        system_instruction=SYSTEM_INSTRUCTION,
        temperature=0.7,
        top_p=0.95,
        response_mime_type="application/json",
        max_output_tokens=65536,
    )

    max_retries = 3
    last_error: Exception | None = None
    current_prompt = prompt
    # 이전 시도에서 부분 복구된 결과를 보관 (최종 폴백용)
    best_partial: list[dict] | None = None

    for attempt in range(max_retries + 1):
        # ── 1) API 호출 ──
        try:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=current_prompt,
                config=gen_config,
            )
        except Exception as e:
            last_error = e
            err_str = str(e)
            if attempt < max_retries and any(k in err_str for k in _RETRYABLE_API_ERRORS):
                wait_sec = 15.0 * (2 ** attempt)
                print(f"[Quiz Gen] Gemini API 재시도 ({attempt+1}/{max_retries}) — {wait_sec:.0f}초 대기")
                time.sleep(wait_sec)
                continue
            raise RuntimeError(f"Gemini API 호출 실패: {e}") from e

        # ── 2) finish_reason 확인 ──
        truncated_reason = _check_finish_reason(response)
        if truncated_reason:
            print(f"[Quiz Gen] 응답 잘림 감지 (finish_reason={truncated_reason})")

        # ── 3) 응답 텍스트 정리 ──
        raw_text = response.text.strip()
        raw_text = _strip_markdown_fences(raw_text)

        # ── 4) JSON 파싱 ──
        parsed = None
        try:
            parsed = json.loads(raw_text)
        except json.JSONDecodeError:
            # 보정 시도
            try:
                parsed = json.loads(_try_repair_json(raw_text))
                print(f"[Quiz Gen] JSON 자동 보정 성공 (attempt {attempt+1})")
            except json.JSONDecodeError:
                # 잘린 응답에서 완전한 객체 추출 시도
                partial = _extract_complete_objects(raw_text)
                if partial:
                    print(f"[Quiz Gen] 부분 복구 {len(partial)}개 퀴즈 추출")
                    if not best_partial or len(partial) > len(best_partial):
                        best_partial = partial
                    if len(partial) >= _MIN_PARTIAL_QUIZZES:
                        print(f"[Quiz Gen] {len(partial)}개 >= {_MIN_PARTIAL_QUIZZES}개 — 그대로 사용")
                        return partial

                last_error = ValueError(f"JSON 파싱 실패: {raw_text[:300]}")
                if attempt < max_retries:
                    # 적응형 재시도: 퀴즈 수 줄이기
                    next_count = _RETRY_QUIZ_COUNTS[min(attempt + 1, len(_RETRY_QUIZ_COUNTS) - 1)]
                    if next_count and rebuild_prompt:
                        current_prompt = rebuild_prompt(next_count)
                        print(
                            f"[Quiz Gen] 퀴즈 수 {next_count}개로 줄여 재시도 "
                            f"({attempt+1}/{max_retries})"
                        )
                    else:
                        print(
                            f"[Quiz Gen] JSON 파싱 실패, 재시도 ({attempt+1}/{max_retries})"
                        )
                    wait_sec = 10.0 * (2 ** attempt)
                    time.sleep(wait_sec)
                    continue
                # 최종 실패: 부분 복구 결과라도 있으면 반환
                if best_partial:
                    print(
                        f"[Quiz Gen] 최대 재시도 후에도 완전 파싱 실패 — "
                        f"부분 복구 {len(best_partial)}개로 폴백"
                    )
                    return best_partial
                raise ValueError(
                    f"JSON 파싱 실패 ({max_retries+1}회 시도): {last_error}\n"
                    f"원문(앞 500자): {raw_text[:500]}"
                ) from last_error

        if not isinstance(parsed, list):
            last_error = ValueError(f"응답이 배열이 아닙니다. 타입: {type(parsed)}")
            if attempt < max_retries:
                print(f"[Quiz Gen] 응답이 배열이 아님, 재시도 ({attempt+1}/{max_retries})")
                time.sleep(10.0)
                continue
            raise last_error

        # 잘림 감지 + 퀴즈 수 부족 시 적응형 재시도
        if truncated_reason and len(parsed) < _MIN_PARTIAL_QUIZZES and attempt < max_retries:
            if not best_partial or len(parsed) > len(best_partial):
                best_partial = parsed
            next_count = _RETRY_QUIZ_COUNTS[min(attempt + 1, len(_RETRY_QUIZ_COUNTS) - 1)]
            if next_count and rebuild_prompt:
                current_prompt = rebuild_prompt(next_count)
                print(
                    f"[Quiz Gen] 잘림으로 {len(parsed)}개만 파싱됨 — "
                    f"퀴즈 수 {next_count}개로 줄여 재시도"
                )
                wait_sec = 10.0 * (2 ** attempt)
                time.sleep(wait_sec)
                continue

        return parsed

    raise RuntimeError(f"Gemini 퀴즈 생성 {max_retries+1}회 시도 후 실패: {last_error}")

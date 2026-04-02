"""Guides 블록: 출력 품질 검증."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# 구조 제약
_MIN_SECTIONS = 2
_MAX_SECTIONS = 5
_MIN_SELF_CHECK = 1


def validate_guide(raw: dict, concept_ids: set[str] | None = None, current_week: int = 1) -> tuple[dict, bool]:
    """가이드 JSON 구조·내용 검증.

    Args:
        raw: LLM이 생성한 가이드 dict.
        concept_ids: EP에서 추출된 실제 concept_id 집합 (내용 검증용).
        current_week: 현재 주차 번호 (prerequisites 검증용).

    Returns:
        (보정된 가이드 dict, 구조_검증_통과 여부) 튜플.
        구조 검증 실패 시 False 반환 — 호출자가 재생성 판단.
    """
    structure_ok = True

    # ── 필수 문자열 필드 ──
    for field in ("overview", "connections", "difficulty_note"):
        if not raw.get(field):
            raw[field] = raw.get(field, "") or ""
            if not raw[field]:
                structure_ok = False
                logger.warning("[Validator] 필수 필드 비어 있음: %s", field)

    # ── sections 구조 ──
    sections = raw.get("sections", [])
    if not isinstance(sections, list):
        sections = []
        raw["sections"] = sections
    if len(sections) < _MIN_SECTIONS or len(sections) > _MAX_SECTIONS:
        structure_ok = False
        logger.warning("[Validator] sections 수 범위 이탈: %d (허용 %d~%d)", len(sections), _MIN_SECTIONS, _MAX_SECTIONS)

    for i, sec in enumerate(sections):
        if not isinstance(sec, dict):
            continue
        if not sec.get("key_takeaways"):
            structure_ok = False
            logger.warning("[Validator] sections[%d].key_takeaways 비어 있음", i)
        # title, summary 기본값
        sec.setdefault("title", f"섹션 {i+1}")
        sec.setdefault("summary", "")
        sec.setdefault("key_takeaways", [])
        sec.setdefault("related_concepts", [])

    # ── self_check ──
    self_check = raw.get("self_check", [])
    if not isinstance(self_check, list) or len(self_check) < _MIN_SELF_CHECK:
        structure_ok = False
        logger.warning("[Validator] self_check 부족: %d (최소 %d)", len(self_check) if isinstance(self_check, list) else 0, _MIN_SELF_CHECK)

    # ── 내용 검증 (실패해도 재생성은 하지 않고 fallback) ──

    # related_concepts가 실제 EP concept_id에 존재하는지
    if concept_ids:
        for sec in sections:
            valid_ids = [cid for cid in sec.get("related_concepts", []) if cid in concept_ids]
            if len(valid_ids) != len(sec.get("related_concepts", [])):
                removed = set(sec.get("related_concepts", [])) - set(valid_ids)
                logger.warning("[Validator] 존재하지 않는 concept_id 제거: %s", removed)
            sec["related_concepts"] = valid_ids

    # prerequisites 주차 번호 검증
    prerequisites = raw.get("prerequisites", [])
    if isinstance(prerequisites, list):
        valid_prereqs = []
        for p in prerequisites:
            if isinstance(p, str):
                # "N주차에서 배운 X" 패턴에서 N 추출
                import re
                m = re.search(r"(\d+)\s*주차", p)
                if m:
                    week_num = int(m.group(1))
                    if week_num < current_week:
                        valid_prereqs.append(p)
                    else:
                        logger.warning("[Validator] prerequisites 주차 이상: %s (현재 %d주차)", p, current_week)
                else:
                    valid_prereqs.append(p)
            raw["prerequisites"] = valid_prereqs

    # ── 리스트 필드 기본값 보장 ──
    for list_field in ("study_tips", "review_priorities", "key_concepts", "prerequisites"):
        if not isinstance(raw.get(list_field), list):
            raw[list_field] = []

    if not isinstance(raw.get("self_check"), list):
        raw["self_check"] = []

    # overview → summary 하위호환
    if raw.get("overview") and not raw.get("summary"):
        raw["summary"] = raw["overview"]

    return raw, structure_ok

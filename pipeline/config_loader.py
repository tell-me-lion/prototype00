"""공통 설정 로딩 유틸.

CURSOR.md 에 정의된 config/* 파일을 한 인터페이스로 로드하는 것을 목표로 한다.
세부 스키마는 각 설정 파일 설계 시에 맞춰 확장하면 된다.
"""

import json
from pathlib import Path
from typing import Any

from . import paths


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_regex_patterns(config_dir: Path | None = None) -> dict[str, str]:
    """Phase 1/2 에서 사용하는 정규식 패턴 로드."""
    conf = config_dir or paths.CONFIG_DIR
    data: dict[str, str] = _load_json(conf / "regex_patterns.json")  # type: ignore[assignment]
    return data


def load_stt_corrections(config_dir: Path | None = None) -> dict[str, str]:
    """STT 오인식 → 정식 용어 매핑 로드."""
    conf = config_dir or paths.CONFIG_DIR
    data: dict[str, str] = _load_json(conf / "stt_corrections.json")  # type: ignore[assignment]
    return data


def load_session_rules(config_dir: Path | None = None) -> dict[str, Any]:
    """세션 분리 규칙 로드."""
    conf = config_dir or paths.CONFIG_DIR
    return _load_json(conf / "session_rules.json")


def load_fact_schema(config_dir: Path | None = None) -> dict[str, Any]:
    """최종 Fact 스키마 정의 로드."""
    conf = config_dir or paths.CONFIG_DIR
    return _load_json(conf / "fact_schema.json")


def load_quiz_blueprint_rules(config_dir: Path | None = None) -> dict[str, Any]:
    """퀴즈 블루프린트 규칙 로드."""
    conf = config_dir or paths.CONFIG_DIR
    return _load_json(conf / "quiz_blueprint_rules.json")


def load_quiz_types(config_dir: Path | None = None) -> dict[str, Any]:
    """퀴즈 유형/템플릿 정의 로드."""
    conf = config_dir or paths.CONFIG_DIR
    return _load_json(conf / "quiz_types.json")


def load_rag_config(config_dir: Path | None = None) -> dict[str, Any]:
    """RAG 설정 로드."""
    conf = config_dir or paths.CONFIG_DIR
    return _load_json(conf / "rag_config.json")


def load_validation_rules(config_dir: Path | None = None) -> dict[str, Any]:
    """퀴즈 품질/검증 규칙 로드."""
    conf = config_dir or paths.CONFIG_DIR
    return _load_json(conf / "validation_rules.json")

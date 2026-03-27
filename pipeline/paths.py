"""
공통 경로 상수 (전체 파이프라인 버전)
- 프로젝트 루트, config, data 하위 디렉터리 한 곳에서 관리
- CLAUDE.md 에 정의된 전체 파이프라인 구조를 반영
"""

from pathlib import Path

# 프로젝트 루트 = prototype00 (pipeline/ 의 부모)
ROOT = Path(__file__).resolve().parent.parent

# 설정 디렉터리
CONFIG_DIR = ROOT / "config"

# 데이터 디렉터리 (전처리 + EP + Blueprint + Quiz + Guides)
DATA_DIR = ROOT / "data"

# Pre-processor (Phase 1~5)
DATA_RAW = DATA_DIR / "raw"
DATA_PHASE1_SESSIONS = DATA_DIR / "phase1_sessions"
DATA_PHASE2_SENTENCES = DATA_DIR / "phase2_sentences"
DATA_PHASE3_CHUNKS = DATA_DIR / "phase3_chunks"
DATA_PHASE4_PROPOSITIONS = DATA_DIR / "phase4_propositions"
DATA_PHASE5_FACTS = DATA_DIR / "phase5_facts"

# 상위 단계 (EP, Blueprint, Quiz, Guides)
DATA_EP_CONCEPTS = DATA_DIR / "ep_concepts"
DATA_EP_LEARNING_POINTS = DATA_DIR / "ep_learning_points"
DATA_BLUEPRINTS = DATA_DIR / "blueprints"
DATA_QUIZZES_RAW = DATA_DIR / "quizzes_raw"
DATA_QUIZZES_VALIDATED = DATA_DIR / "quizzes_validated"
DATA_LEARNING_GUIDES = DATA_DIR / "learning_guides"

# 개발용 더미 산출물 (실전 미사용, ARCHITECTURE.md §2.3.1)
DATA_DUMMY = DATA_DIR / "dummy"

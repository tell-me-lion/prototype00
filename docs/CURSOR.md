## prototype00 전체 파이프라인 개요 (`tell-me-lion`)

이 문서는 `prototype00` 폴더 안에 있는 **전체 파이프라인 구조**를 정의합니다.  
특히 아래 목적을 달성하기 위한 **전처리(Pre-processor) + 개념 식별 + 블루프린트/퀴즈 생성 + 품질 검증 + 학습 가이드 생성**까지의 흐름과 폴더 구조를 설명합니다.

- **목적**
  - 강의 스크립트에서 **핵심 개념과 학습 포인트를 자동 추출**
  - **주관식/객관식/빈칸 채우기/코드 실행** 등 다양한 형태의 퀴즈와 해설을 생성하는 시스템 구축
    - 퀴즈 생성 전략, 퀴즈 유형, RAG 구조 포함
  - **주차별 학습 가이드와 핵심 요약**을 자동으로 제작하여 수강생에게 제공

---

## 1. 전체 목표 및 상위 파이프라인

- **입력**: 강의 STT 스크립트 (`data/raw/*.txt`)
- **중간 산출물**:
  - 전처리 단계의 세션/문장/시맨틱 청크/지식 명제 후보
  - 핵심 개념·학습 포인트 리스트
  - 문제 블루프린트(난이도, 유형, 포맷 등 메타 정보)
  - 생성된 퀴즈와 해설, 검증 로그
- **최종 목표**:
  - 모델 학습/퀴즈 생성에 사용할 수 있는 **구조화된 지식 명제 데이터 (`data/phase5_facts/`)**
  - 수강생에게 제공할 **주차별 학습 가이드 + 핵심 요약 + 퀴즈 세트**

위 목표를 위해 전체 파이프라인은 개념적으로 아래와 같이 나뉩니다 (`graph TD` 표현을 텍스트로 풀어쓴 것):

- **Pre-processor (전처리 블록, 이 문서의 Phase 1~5)**
  - `RAW[강의 스크립트] -> PROC[전처리] -> A["JSON: Fact Chunk Unit"]`
  - 여기서 `A` 는 사실상 `data/phase5_facts/` 및 그 직전 산출물(청크/명제 후보)을 의미
- **핵심 개념/학습 포인트 식별 (EP)**
  - `A` 를 입력으로, 강의별/주차별 핵심 개념과 학습 포인트를 정리
- **Blueprint & Logic (BP_Generation)**
  - EP 결과를 바탕으로 **문제 Blueprint 작성 (BP)** → **퀴즈 생성 전략 선정 (DS)** → **실제 퀴즈 생성 (QG)**
- **QA Validation (품질 검증)**
  - 생성된 퀴즈(QG)를 **사실 검증(VAL)** 에 통과시켜
  - 실패 시 BP 단계로 되돌려 다시 생성, 성공 시 **최종 퀴즈 및 해설(FinalQuiz)** 로 확정
- **학습 가이드 생성**
  - FinalQuiz + EP 결과를 조합해 **주차별 학습 가이드/핵심 요약** 산출

---

## 2. 폴더 구조 (전체 파이프라인 기준)

### 2.1 최상위

- `prototype00/`
  - `config/` : 전처리 + 개념 식별 + 퀴즈 생성 + 검증용 설정
  - `data/` : 원본 및 각 단계 산출물 (전처리, EP, Blueprint, 퀴즈, 검증, 학습 가이드)
  - `pipeline/` : 전체 파이프라인 모듈
    - `phase1/`~`phase5/` (전처리)
    - `ep/` (핵심 개념/학습 포인트 식별)
    - `blueprint/` (문제 블루프린트 & 전략)
    - `quiz_generation/` (퀴즈/해설 생성)
    - `qa_validation/` (품질 검증)
    - `guides/` (학습 가이드/요약 생성)
    - `common/` (공통 유틸, 모델 래퍼, RAG 클라이언트 등)
  - `scripts/` : CLI 진입점 (전체/부분 실행용 스크립트)
  - `docs/` : 문서 (이 파일 포함)
  - `README.md` : 간단 사용법·폴더 구조 요약
  - `requirements.txt` : 전체 파이프라인 실행에 필요한 의존성

### 2.2 `data/` 하위 – 전처리(Pre-processor, Phase 1~5)

- `data/`
  - `raw/`
    - **설명**: 원본 강의 STT 스크립트 (`*.txt`)
    - **역할**: 파이프라인의 **최초 입력**
  - `phase1_sessions/`
    - **설명**: Phase 1 (세션 분리 + 물리적 세척) 결과
    - **예상 형식**: `*.jsonl`
      - 한 줄당 하나의 **세션 내 발화/문단 단위** 레코드
      - 필드 예시: `{"session_id": str, "timestamp": "HH:MM:SS", "speaker": str | null, "text": str, "meta": {...}}`
  - `phase2_sentences/`
    - **설명**: Phase 2 (형태소 기반 문장 복원 + 필터링) 결과
    - **예상 형식**: `*.jsonl`
      - 한 줄당 하나의 **정제된 문장**
      - 필드 예시: `{"session_id": str, "sent_id": int, "text": str, "pos_tags": list | null, "meta": {...}}`
  - `phase3_chunks/`
    - **설명**: Phase 3 (시맨틱 청킹 + 중요도 스코어링) 결과
    - **예상 형식**: `*.jsonl`
      - 한 줄당 하나의 **시맨틱 청크**
      - 필드 예시: `{"chunk_id": str, "session_id": str, "sent_ids": [int, ...], "text": str, "keywords": [str, ...], "tfidf_scores": dict, "meta": {...}}`
  - `phase4_propositions/`
    - **설명**: Phase 4 (지식 명제 추출 및 구조화 전 단계) 결과
    - **예상 형식**: `*.jsonl`
      - 한 줄당 하나의 **지식 명제 후보**
      - 필드 예시: `{"prop_id": str, "chunk_id": str, "type": "definition" | "role" | "procedure" | "comparison" | "other", "text": str, "concept_candidates": [str, ...], "meta": {...}}`
  - `phase5_facts/`
    - **설명**: Phase 5 (데이터 규격화 및 검증) 결과, 최종 Fact 레벨 데이터
    - **예상 형식**: `*.jsonl` 또는 `*.json`
      - 예: `{"id": str, "concept": str, "fact": str, "source": {...}, "trace": {...}}`

> `data/` 전체는 `.gitignore` 에 의해 버전 관리 대상에서 제외되는 것을 권장합니다.  
> 리포에는 **구조와 스키마 정의만** 남기고, 실제 데이터는 실행 환경에서만 존재하도록 합니다.

### 2.3 `data/` 하위 – EP, Blueprint, 퀴즈, 검증, 학습 가이드

- `data/`
  - `ep_concepts/`
    - **입력**: `phase5_facts/`
    - **설명**: 강의/주차별 핵심 개념·학습 포인트 리스트
    - **형식 예시**: `*.jsonl`
      - `{"week": int | null, "lecture_id": str, "concept": str, "importance": float, "evidence_facts": [fact_id,...], "meta": {...}}`
  - `blueprints/`
    - **입력**: `ep_concepts/`
    - **설명**: 퀴즈 세트를 설계한 블루프린트 (유형, 난이도, 수량, RAG 전략 등)
    - **형식 예시**: `*.json`
      - `{"blueprint_id": str, "target_week": int, "items": [...], "constraints": {...}}`
  - `quizzes_raw/`
    - **입력**: `blueprints/`
    - **설명**: LLM/SLM 을 통해 1차 생성된 퀴즈와 해설 (검증 전)
    - **형식 예시**: `*.jsonl`
      - `{"quiz_id": str, "blueprint_id": str, "type": "mcq"|"short"|"fill"|"code", "question": str, "options": [...], "answer": ..., "explanation": str, "meta": {...}}`
  - `quizzes_validated/`
    - **입력**: `quizzes_raw/`
    - **설명**: 사실 검증을 통과한 최종 퀴즈 + 검증 로그
    - **형식 예시**: `*.jsonl`
      - `{"quiz_id": str, "status": "pass"|"fail", "question": ..., "answer": ..., "validation_log": {...}, "meta": {...}}`
  - `learning_guides/`
    - **입력**: `ep_concepts/`, `quizzes_validated/`
    - **설명**: 주차별 학습 가이드, 핵심 요약, 추천 문제 세트
    - **형식 예시**: `*.json` 또는 마크다운
      - `{"week": int, "summary": str, "key_concepts": [...], "recommended_quiz_ids": [...], "meta": {...}}`

### 2.4 `config/` 하위 (예시)

- `config/regex_patterns.json`
  - **용도**: 화자 ID, 특수문자, 반복 잡음 제거 등 Phase 1/2에서 쓰이는 정규식 패턴 모음
- `config/stt_corrections.json`
  - **용도**: mysql, 잡바, 마이s큐L 등 **STT 오인식 → 정식 용어** 매핑
- `config/session_rules.json`
  - **용도**: 오전/오후, 주제별 세션 분리 규칙 (시간대 범위, 키워드 등)
- `config/keyword_tfidf.yaml`
  - **용도**: TF-IDF 관련 설정 (min_df, max_df, ngram_range 등)
- `config/fact_schema.json`
  - **용도**: Pydantic/Instructor로 강제할 **최종 Fact JSON 스키마**
- `config/quiz_blueprint_rules.json`
  - **용도**: 주차별/난이도별 퀴즈 수, 유형 비율, 타깃 개념 수 등 규칙
- `config/quiz_types.yaml`
  - **용도**: 주관식/객관식/빈칸/코드 실행 등 퀴즈 유형별 템플릿과 제약
- `config/rag_config.yaml`
  - **용도**: RAG 구조 정의 (벡터 DB 설정, 검색 파라미터, 사용 인덱스 등)
- `config/validation_rules.json`
  - **용도**: 퀴즈 품질 기준 (정답 일관성, 난이도 범위, 금지 표현 등)
- `config/guide_templates.md`
  - **용도**: 학습 가이드/요약 문서의 템플릿

정확한 스키마(키 이름, 값의 형태)는 구현자가 자유롭게 설계하되,  
아래의 공통 유틸들이 이 설정들을 참조한다는 점만 유지하면 됩니다.

---

## 3. Pre-processor (전처리) – Phase 기반 파이프라인 개념

전처리(Pre-processor) 블록은 아래 5개 Phase로 구성됩니다.  
각 Phase는 **입력 디렉터리 → 출력 디렉터리** 로 이어지는 순차 파이프라인이며,  
세부 로직 대신 **책임 영역·입출력·사용 기술** 중심으로 정의합니다.

1. **Phase 1: 데이터 분리 및 물리적 세척**
2. **Phase 2: 형태소 기반 문장 복원 및 필터링**
3. **Phase 3: 시맨틱 청킹 및 중요도 스코어링**
4. **Phase 4: 지식 명제 추출 및 구조화**
5. **Phase 5: 데이터 규격화 및 검증**

### 3.1 Phase 1 – 데이터 분리 및 물리적 세척

- **모듈 (예시)**:
  - `pipeline/phase1/session_split.py`
  - `pipeline/phase1/term_clean_gemini.py`
  - `pipeline/phase1/regex_clean.py`
- **입력**: `data/raw/*.txt`
- **출력**: `data/phase1_sessions/*.jsonl`
- **주요 역할**:
  - **세션 분리**:
    - 텍스트 내 타임스탬프(`<HH:MM:SS>`)와 `config/session_rules.json` 기반으로
    - 오전/오후, 주제별 등 **논리적 세션 단위**로 분할
  - **용어 클렌징 (Gemini 사용)**:
    - mysql, 잡바, 마이s큐L 등 STT 오인식 용어를 **정식 기술 용어**로 복원
    - Gemini API를 이용하되, 입력/출력 포맷은 `{"text": str, "suggested_correction": str}` 정도로 단순화
  - **Regex 클렌징**:
    - `re` 모듈 + `config/regex_patterns.json` 을 사용해
      - 화자 ID, 불필요 특수문자, 반복 잡음 등 제거
      - 필요시 컴파일된 패턴 캐시로 대용량 처리 효율화
- **출력 레코드 예시**:
  - `{"session_id": "2025-01-lecture-01#S01", "timestamp": "00:13:21", "speaker": "강사", "text": "...정제된 한 발화...", "meta": {...}}`

### 3.2 Phase 2 – 형태소 기반 문장 복원 및 필터링

- **모듈 (예시)**:
  - `pipeline/phase2/sentence_segment_kiwi.py`
  - `pipeline/phase2/sentence_filter_pos.py`
- **입력**: `data/phase1_sessions/*.jsonl`
- **출력**: `data/phase2_sentences/*.jsonl`
- **사용 기술**:
  - `kiwipiepy` 의 `Kiwi.split_into_sents()` 를 기본으로 사용
- **주요 역할**:
  - **문장 분리**:
    - 구어체 기준으로 마침표가 없는 긴 STT 결과를
    - Kiwi 기반 문장 경계 탐지로 **논리적 문장 단위**로 복원
  - **품사 기반 드랍**:
    - 품사 태깅 결과를 이용해
    - 명사/동사 없이 감탄사 위주의 짧은 문장 (예: "네", "아 그…") 을 필터링
    - 데이터 밀도(정보량)를 높이는 방향으로 규칙 정의
- **출력 레코드 예시**:
  - `{"session_id": "…", "sent_id": 12, "text": "데이터베이스에서 트랜잭션이란 ...", "pos_tags": [...], "meta": {...}}`

### 3.3 Phase 3 – 시맨틱 청킹 및 중요도 스코어링

- **모듈 (예시)**:
  - `pipeline/phase3/semantic_chunking.py`
  - `pipeline/phase3/embedding_models.py`
  - `pipeline/phase3/keyword_tfidf.py`
- **입력**: `data/phase2_sentences/*.jsonl`
- **출력**: `data/phase3_chunks/*.jsonl`
- **사용 기술**:
  - `KR-SBERT` 또는 `KoELECTRA` 임베딩 → 문장 간 코사인 유사도
  - `scikit-learn` TF-IDF
- **주요 역할**:
  - **시맨틱 청킹**:
    - 인접 문장들 간 임베딩 코사인 유사도를 계산
    - 유사도가 임계값 이하로 떨어지는 지점에서 **청크 경계**를 설정
    - 길이 기반이 아닌 **내용 흐름 기반** 청킹
  - **핵심어 스코어링 (TF-IDF)**:
    - 전체 강의 코퍼스를 대상으로 TF-IDF 피팅
    - 특정 청크에 집중된 고 TF-IDF 단어들을 **개념 후보 키워드**로 추출
- **출력 레코드 예시**:
  - `{"chunk_id": "S01-C03", "session_id": "S01", "sent_ids": [10,11,12], "text": "...여러 문장 합친 내용...", "keywords": ["트랜잭션", "격리성"], "tfidf_scores": {"트랜잭션": 3.21, ...}, "meta": {...}}`

### 3.4 Phase 4 – 지식 명제 추출 및 구조화

- **모듈 (예시)**:
  - `pipeline/phase4/pattern_rules.py`
  - `pipeline/phase4/slm_fact_extractor.py`
  - `pipeline/phase4/concept_matching.py`
- **입력**: `data/phase3_chunks/*.jsonl`
- **출력**: `data/phase4_propositions/*.jsonl`
- **사용 기술**:
  - 규칙 기반 패턴 매칭 (정의/역할/절차/비교)
  - 로컬 SLM (예: `Llama-3-8B`) 를 통한 Fact 추출
- **주요 역할**:
  - **패턴 매칭 (규칙 기반 1차 필터)**:
    - "~란 ...이다", "~가 중요합니다", "~하는 방법은" 등
    - 정의/역할/절차/비교 패턴을 정규식 + 간단 파서로 탐지
  - **SLM Fact 추출**:
    - "이 텍스트에서 Fact 명제 3개 추출" 과 같은 프롬프트로
    - 로컬 SLM에게 Fact 후보를 생성하게 함
    - 환각 억제를 위해 입력 텍스트와 강하게 정렬된 포맷을 사용
  - **기술 결합**:
    - SLM이 뽑은 Fact 텍스트와
    - Phase 3의 TF-IDF 기반 핵심어를 매칭하여
    - `개념-설명` 쌍 후보를 구성
- **출력 레코드 예시**:
  - `{"prop_id": "P-000123", "chunk_id": "S01-C03", "type": "definition", "text": "트랜잭션이란 ... 이다.", "concept_candidates": ["트랜잭션"], "meta": {"source_sents": [...], "slm_model": "llama-3-8b", ...}}`

### 3.5 Phase 5 – 데이터 규격화 및 검증

- **모듈 (예시)**:
  - `pipeline/phase5/schema.py`
  - `pipeline/phase5/standardize.py`
  - `pipeline/phase5/audit_log.py`
- **입력**: `data/phase4_propositions/*.jsonl`
- **출력**: `data/phase5_facts/*.jsonl` (또는 `*.json`)
- **사용 기술**:
  - `pydantic` + `Instructor` 를 통한 JSON 스키마 강제
- **주요 역할**:
  - **Pydantic 구조화**:
    - Instructor 라이브러리를 사용해
    - "FactRecord" 등 Pydantic 모델에 맞는 JSON을 강제 생성
  - **검증 및 정규화**:
    - 필드 타입/필수 여부 검증
    - 개념명/식별자 정규화, 중복 Fact 머지 등
  - **변경 로그(Traceability)**:
    - 원문 대비 어떤 수정/필터링/추출 단계가 거쳐졌는지
    - `trace` 필드에 기록 (예: `{"phase1": {...}, "phase2": {...}, ...}`)

---

## 4. 실행 진입점 구조 (`scripts/run_pipeline.py`)

`scripts/run_pipeline.py` 는 **전체 파이프라인 (전처리 + EP + Blueprint + 퀴즈 생성 + 검증 + 학습 가이드)** 을 한 번에, 혹은 일부 블록만 실행하기 위한 진입점입니다.  
내부 구현은 자유지만, 아래 정도의 인터페이스를 목표로 합니다.

- **위치**: `scripts/run_pipeline.py`
- **동작 개요 (예시)**:
  - `project_root = Path(__file__).resolve().parent.parent` 로 루트 계산 (`prototype00/`)
  - `sys.path.insert(0, str(project_root))` 로 `pipeline` 패키지 import 가능하게 설정
  - 블록/Phase 별 러너를 import:
    - `pipeline.phase1.runner.run_phase1(...)`
    - `pipeline.phase2.runner.run_phase2(...)`
    - `pipeline.phase3.runner.run_phase3(...)`
    - `pipeline.phase4.runner.run_phase4(...)`
    - `pipeline.phase5.runner.run_phase5(...)`
    - `pipeline.ep.runner.run_ep(...)`
    - `pipeline.blueprint.runner.run_blueprint(...)`
    - `pipeline.quiz_generation.runner.run_quiz_generation(...)`
    - `pipeline.qa_validation.runner.run_validation(...)`
    - `pipeline.guides.runner.run_guides(...)`
  - CLI 옵션 (예시):
    - `--from-block preproc --to-block guides`
    - `--only-block blueprint`
    - `--from-phase 1 --to-phase 5` (전처리 부분 범위 지정)
    - `--skip-block qa_validation`
- **표준 실행 흐름 (예시)**:
  1. Phase 1~5 실행 → `data/phase5_facts/` (Pre-processor 완료)
  2. EP 실행 → `data/ep_concepts/`
  3. Blueprint 실행 → `data/blueprints/`
  4. Quiz Generation 실행 → `data/quizzes_raw/`
  5. QA Validation 실행 → `data/quizzes_validated/`
  6. Guides 실행 → `data/learning_guides/`

구현자는 각 러너 내부에서 **세부 모듈 호출 순서**를 자유롭게 설계하면 됩니다.

---

## 5. 공통 유틸: 경로와 설정

### 5.1 `pipeline/paths.py` (예시 설계)

- **역할**: 프로젝트 루트와 주요 디렉터리 경로를 한 곳에서 관리
- **주요 상수 (예시)**:
  - `ROOT`
  - `CONFIG_DIR`
  - `DATA_DIR`
  - `DATA_RAW`
  - `DATA_PHASE1_SESSIONS`
  - `DATA_PHASE2_SENTENCES`
  - `DATA_PHASE3_CHUNKS`
  - `DATA_PHASE4_PROPOSITIONS`
  - `DATA_PHASE5_FACTS`
  - `DATA_EP_CONCEPTS`
  - `DATA_BLUEPRINTS`
  - `DATA_QUIZZES_RAW`
  - `DATA_QUIZZES_VALIDATED`
  - `DATA_LEARNING_GUIDES`

모든 Phase 구현에서 이 상수만 사용하도록 하면, 디렉터리 구조 변경 시 이 파일만 수정하면 됩니다.

### 5.2 `pipeline/config_loader.py` (예시 설계)

- **역할**: `config/` 안의 설정 파일들을 공통 인터페이스로 로드
- **예시 함수**:
  - `load_regex_patterns() -> dict[str, str]`
  - `load_stt_corrections() -> dict[str, str]`
  - `load_session_rules() -> dict[str, Any]`
  - `load_fact_schema() -> dict[str, Any]`
  - `load_quiz_blueprint_rules() -> dict[str, Any]`
  - `load_quiz_types() -> dict[str, Any]`
  - `load_rag_config() -> dict[str, Any]`
  - `load_validation_rules() -> dict[str, Any]`

각 블록/Phase는 필요한 설정만 골라 쓰도록 설계합니다.

---

## 6. 정리: 이 문서가 보장하는 것 vs. 구현자가 채워 넣을 것

- **이 문서가 고정하는 것**
  - 전처리 5개 Phase + EP + Blueprint + Quiz Generation + QA Validation + Guides 의 **책임 영역**
  - 각 단계의 **입출력 디렉터리/대략적인 스키마**
  - 전체 흐름:
    - `raw → phase1_sessions → phase2_sentences → phase3_chunks → phase4_propositions → phase5_facts`
    - `phase5_facts → ep_concepts → blueprints → quizzes_raw → quizzes_validated → learning_guides`
  - 주요 사용 기술 스택:
    - 전처리: `re`, Gemini API, `kiwipiepy`, KR-SBERT/KoELECTRA, `scikit-learn` TF-IDF, 로컬 SLM, `pydantic` + `Instructor`
    - 상위 단계: RAG 구조, 블루프린트 규칙, 다양한 퀴즈 유형 템플릿, 사실 검증 로직
- **구현자가 자유롭게 채울 것**
  - 각 단계 내부에서의 구체 알고리즘/프롬프트/모델·인프라 선택
  - JSONL/JSON 레코드의 세부 필드명과 보조 메타데이터 구조
  - RAG 백엔드 선택, 벡터 DB 스키마, 인덱싱 전략
  - CLI 옵션 이름, 로그 포맷, 에러 처리 전략 등

이 문서를 기준으로, 다른 구현자는  
- **어느 폴더/모듈이 어떤 책임을 가지는지**,  
- **어떤 입출력 형식을 맞춰야 상위/하위 단계와 잘 연결되는지**  
만 이해하면 자신이 맡은 부분(전처리, 개념 추출, 블루프린트, 퀴즈 생성, 검증, 가이드 생성)을 독립적으로 구현할 수 있습니다.


# CLAUDE.md

## 프로젝트 개요

**알려주사자**는 강의 텍스트(STT 스크립트)에서 핵심 개념·학습 포인트·퀴즈·학습 가이드를 자동 생성해 수강생에게 제공하는 풀스택 교육 시스템이다.

> **설계 원칙: 모든 것은 클라이언트 관점에서.**
> 클라이언트는 수강생뿐 아니라 이 서비스를 도입할 **교육 서비스 업체**도 포함한다.
> 시스템이 무엇을 할 수 있는지가 아니라, 클라이언트가 무엇을 필요로 하는지를 기준으로 판단한다.

### 두 가지 사용 모드

| 입력 | 출력 |
|------|------|
| 강의 스크립트 1개 (`.txt`) | 핵심 개념, 학습 포인트, 퀴즈 |
| 1주치 강의 스크립트 전체 | 주차별 학습 가이드, 주차별 핵심 요약 |

두 모드는 독립적으로 실행된다. **Mode B는 Mode A의 출력을 읽어선 안 된다.**

### 퀴즈 유형

객관식(MCQ), 주관식(Short Answer), 빈칸 채우기(Fill-in-the-Blank), 코드 실행형(Code Execution). 각 유형별 해설 포함.

퀴즈 생성에는 **RAG 구조**를 사용한다: 팩트·개념 DB를 검색해 근거를 찾고, 블루프린트 기반으로 문항을 생성한다.

### 현재 상태

| 영역 | 상태 | 완성도 |
|------|------|--------|
| 전처리 (Phase 1~5) | ✅ 구현 완료 | 100% |
| EP (핵심 개념 추출) | ✅ 구현 완료 | 100% |
| Blueprint (퀴즈 설계) | ✅ 구현 완료 | 100% |
| Quiz Generation | 🔲 구현 중 | 30% |
| QA Validation | 🔲 뼈대만 | 10% |
| Guides | 🔲 뼈대만 | 10% |
| 백엔드 API | ⚙️ 구조 완료 | 60% |
| 프론트엔드 | ⚙️ 초기 구현 중 | 50% |

---

## 명령어

### 백엔드
```bash
# 프로젝트 루트에서 실행
python -m uvicorn app.main:app --reload
# API: http://localhost:8000  |  Docs: http://localhost:8000/docs
```
> `uvicorn` 단독 사용 금지 — Windows PATH 문제 방지.

### 프론트엔드
```bash
cd frontend
npm install
npm run dev      # http://localhost:5173
npm run build
npm run lint
```

### 파이프라인
```bash
# Mode A: 강의 1개 → 핵심 개념·학습 포인트·퀴즈
python scripts/run_pipeline.py --mode a --input data/raw/lecture_01.txt

# Mode B: 1주치 전체 → 주차별 학습 가이드·핵심 요약
python scripts/run_pipeline.py --mode b --week 1

# 블록 범위 지정 (preproc / ep / blueprint / quiz / qa / guides)
python scripts/run_pipeline.py --mode a --from-block preproc --to-block ep

# 전처리 Phase 범위 지정 (1~5)
python scripts/run_pipeline.py --mode a --from-phase 1 --to-phase 3
```

---

## 기술 스택

### 백엔드
| 기술 | 용도 | 버전 |
|------|------|------|
| Python | 서버 언어 | 3.10+ |
| FastAPI | REST API | ≥ 0.109 |
| Uvicorn | ASGI 서버 | ≥ 0.27 |
| Pydantic | 데이터 검증·스키마 | v2 |

### 프론트엔드
| 기술 | 용도 | 버전 |
|------|------|------|
| React | UI 프레임워크 | 19.x |
| TypeScript | 타입 안전성 | 5.9 |
| Vite | 빌드 도구 | 8.x |
| Tailwind CSS | 스타일링 | 4.x |
| React Router | 라우팅 | 7.x |

### 파이프라인 (AI·데이터 처리)
| 기술 | 용도 |
|------|------|
| Google Gemini API | LLM 기반 텍스트 분석·생성 |
| KiwiPiePy | 한국어 형태소 분석 |
| Sentence Transformers (KR-SBERT) | 문장 임베딩, 시맨틱 청킹 |
| scikit-learn | TF-IDF 계산, 유사도 분석 |
| Ollama (로컬) | 로컬 LLM 대체 실행 |

---

## 아키텍처

### 3계층 구조
1. **Pipeline** (`pipeline/`) — 데이터 처리; `data/raw/*.txt` 읽기, 각 단계 디렉터리에 쓰기
2. **Backend** (`app/`) — FastAPI REST API; `data/`의 파이프라인 출력 읽기
3. **Frontend** (`frontend/src/`) — React SPA; 백엔드 API만 소비

### 백엔드 (`app/`)
- `app/main.py` — FastAPI 앱, CORS 설정 (`localhost:5173`)
- `app/api/routes.py` — 엔드포인트: `POST /api/lecture-outputs`, `POST /api/weekly-outputs`, `GET /api/concepts`, `GET /api/learning-points`, `GET /api/quizzes`, `GET /api/learning-guides`, `GET /api/learning-guides/{week}`
- `app/schemas/models.py` — Pydantic 응답 모델 (`Concept`, `LearningPoint`, `Quiz`, `LearningGuide`, `LectureOutputs`, `WeeklyOutputs`)
- `app/loaders/dummy.py` — `data/dummy/` JSON 로드 (파이프라인 연동 후 제거)

**더미 데이터** (`data/dummy/`, 파이프라인 완성 전까지 사용):

| 파일 | 모드 | 내용 |
|------|------|------|
| `concepts.json` | A | 핵심 개념 샘플 3개 |
| `learning_points.json` | A | 학습 포인트 샘플 3개 |
| `quizzes.json` | A | 퀴즈 샘플 3개 (mcq·short·fill 각 1개) |
| `learning_guides.json` | B | 주차별 학습 가이드 샘플 3개 (1~3주차) |

### 파이프라인 (`pipeline/`)

각 블록은 단일 `run_*()` 진입 함수를 가진 `runner.py`를 포함한다.

| 블록 | 디렉터리 | 모드 | 역할 | 입력 | 출력 |
|------|----------|------|------|------|------|
| Pre-processor | `preprocessor/` | A, B | STT 정제 → 문장 → 청크 → 명제 → 팩트 | `data/raw/*.txt` | `data/phase5_facts/*.jsonl` |
| EP | `ep/` | A | 핵심 개념·학습 포인트 식별 | 팩트 데이터 | `data/ep_concepts/*.jsonl` |
| Blueprint | `blueprint/` | A | 퀴즈 유형·난이도·근거 설계 | 개념 + 팩트 | `data/blueprints/*.jsonl` |
| Quiz Generation | `quiz_generation/` | A | 실제 퀴즈·해설 생성 | Blueprint | `data/quizzes_raw/*.jsonl` |
| QA Validation | `qa_validation/` | A | 퀴즈 품질·사실 검증 | 퀴즈 | `data/quizzes_validated/*.jsonl` |
| Guides | `guides/` | B | 주차 통합 → 학습 가이드·요약 | 각 파일 전처리 결과 | `data/learning_guides/*.jsonl` |

- `pipeline/paths.py` — **모든 경로 상수**. 경로를 하드코딩하지 않는다.
- `pipeline/config_loader.py` — `load_*()` 함수로 설정 파일 로드.
- `config/quiz_blueprint_rules.json` — 퀴즈 생성 규칙 (블록별 유형·난이도 배분)
- `config/rag_config.json` — RAG 검색 설정

### 전처리 Phase 상세 (`pipeline/preprocessor/`)

| Phase | 파일 | 핵심 작업 |
|-------|------|----------|
| 1 | `01_cleaner.py` | 15초 기준 발화 병합, 30분 공백 시 세션 분할, Gemini API로 오탈자·추임새 교정 |
| 2 | `02_segmenter.py` | `kiwipiepy` 형태소 분석으로 구어체 문장 복원, 무의미 감탄사 문장 필터링 |
| 3 | `03_chunker.py` | KR-SBERT 임베딩 코사인 유사도로 문맥 전환 지점 감지 → Chunk 분할, TF-IDF 핵심어 추출 |
| 4 | `04_extractor.py` | 정규식 + LLM(Gemini / 로컬 Ollama)으로 '정의·규칙·절차' 형태의 핵심 명제(Fact 후보) 추출 |
| 5 | `05_formatter.py` | 명제를 개념(`concept`) 단위로 그룹화, 역참조·연관어 추가, RAG 최적화 JSON 포맷으로 조립 |

### 데이터 스키마

**Chunk** (Phase 5 출력):
```json
{
  "chunk_id": "2026-02-03_S01_C002",
  "session": "오전",
  "session_seq": 1,
  "start_time": "09:11:04",
  "text": "...",
  "facts": ["추상 클래스는 주요 메소드인 추상 메서드를 가지고 있다."],
  "tfidf_keywords": ["추상", "메소드야", "구현"]
}
```

**Concept** (EP 출력):
```json
{
  "concept_id": "concept_union",
  "concept": "UNION",
  "definition": "두 SELECT 결과를...",
  "related_concepts": ["concept_join"],
  "source_chunk_ids": ["S01-C03"],
  "importance": 0.87,
  "week": 21,
  "lecture_id": "2026-02-11_kdt..."
}
```

**Quiz** (Quiz Generation 출력):
```json
{
  "quiz_id": "q_001",
  "type": "mcq",
  "question": "UNION의 역할은?",
  "options": ["A", "B", "C", "D"],
  "answer": "A",
  "explanation": "UNION은...",
  "status": "pass"
}
```

---

## 핵심 알고리즘 메모

### EP — 개념 추출 전략
- **Definition 주어 기반 필터링**: 팩트 문장의 주어로 등장하는 키워드만 핵심 개념 후보로 수집 (보조 개념 자동 제외)
- **중요도 4항 공식**: 등장 빈도(0.5) + TF-IDF(0.3) + 강조 표현(0.2) → 23단계 변별력
- **Definition 고유 배정**: 중요도 높은 개념이 고유 정의를 선점
- **관련 개념 연결**: 같은 문장 공동 출현 기반

### Blueprint — Evidence 분리 구조
퀴즈 생성 시 LLM에 제공하는 근거를 엄격히 분리:

| 필드 | 역할 | 수집 기준 |
|------|------|----------|
| `correct_facts` | 무결점 정답 선지 생성 근거 | 해당 개념이 주어인 문장 |
| `distractor_facts` | 정교한 오답 선지 조립 재료 | 같은 청크의 나머지 문장 + 연관 개념 문장 |

> 목적: LLM 환각(Hallucination)으로 없는 개념이 오답으로 생성되는 것을 차단.

---

## 오류 기록

반복 발생 오류와 해결 과정은 **`ERRORS.md`** 에 기록한다. 새 오류 발생 시 즉시 추가.

---

## 배포 워크플로우

**실행 순서 (절대 바꾸지 않는다):**
1. **`DEPLOY.md` 먼저 작성 또는 업데이트** — 무엇을 왜 바꾸는지 기록
2. 코드·설정 파일 작성
3. **`bash scripts/deploy-check.sh` 실행** — 의존성·빌드·환경변수·하드코딩·CORS 자동 검증 (또는 `/deploy-check` 스킬)
4. 검증 통과 후 GitHub push
5. 팀원은 `DEPLOY.md`의 로컬 셋업 순서대로 환경 구성 후 실행

> 배포 완료로 표시하기 전: `requirements.txt` / `package.json`에 새로 import한 패키지가 모두 포함됐는지 확인한다.
> 배포 URL이 제공되면 즉시 관련 설정파일·문서를 업데이트한다.

### 실행 환경

| 계층 | 실행 방법 | 주소 |
|------|-----------|------|
| 프론트엔드 | `npm run dev` (로컬) | `http://localhost:5173` |
| 백엔드 | `python -m uvicorn app.main:app --reload` (로컬) | `http://localhost:8000` |
| DB | localStorage (브라우저) | — |

---

## 프론트엔드 디자인

UI 작업(컴포넌트, 페이지, 스타일링) 시 반드시 **`frontend-design` 스킬**을 먼저 호출한다.
디자인 방향·색상·타이포그래피·컴포넌트 명세는 **`DESIGN.md`** 참고.

### Write-and-Preview 워크플로우 (UI 작업 전용)

**실행 순서 (절대 바꾸지 않는다):**
1. task 파일 읽기
2. **실제 파일 작성 + JSX Artifact 동시 제공**
3. 사용자: `npm run dev`로 브라우저 확인 후 "맞다" 또는 피드백
4. 피드백 있으면 → 파일 수정 → 3단계 반복
5. "맞다" 후 → **`/frontend-check` 스킬 실행** (format → lint → types)
6. 다음 task로 이동

> 사용자 승인("맞다")과 `/frontend-check`는 각자 독립적인 필수 관문 — 둘 중 하나가 나머지를 대체하지 않는다.

| 확인 채널 | 검증 항목 |
|-----------|----------|
| JSX Artifact | 색상 팔레트, 레이아웃 비율, 컴포넌트 구조, 전체 분위기 |
| `npm run dev` (브라우저) | 실제 폰트 로딩, Tailwind 클래스, 애니메이션 타이밍, 다크모드 전환 |

---

## 기능 구현 워크플로우

**새 기능·페이지·컴포넌트 구현 시 반드시 명세 먼저, 코드 나중.**

1. `docs/tasks/` 에 태스크 명세 파일 작성 (`_template.md` 참고)
2. 사용자 승인("맞다" 또는 "진행해") 대기
3. 승인 후 구현 시작

> 승인 없이 코드 작성 금지. 명세 없이 바로 구현에 들어간 세션에서 하드코딩·잘못된 파이프라인 흐름 등의 마찰이 반복 발생했다.

**태스크 명세 포함 항목**: 요구사항, 컴포넌트 구조, 데이터 흐름, 따라야 할 기존 패턴.

---

## 실행 원칙

- **코드 작성 요청엔 즉시 파일에 직접 작성한다.** 계획·설명·제안을 먼저 하지 않는다. 사용자가 명시적으로 "설명해줘"를 요청한 경우만 예외.
- **작성 후 Read 도구로 해당 파일을 읽어 반영 여부를 검증한다.**
- **하드코딩 금지**: 색상(`var(--tml-*)` 사용), 데이터(API 연동), URL(환경변수·설정파일). 값을 직접 삽입하지 않는다.
- 기능 구현 시 기존 파이프라인·아키텍처를 따른다 (예: Mode B는 업로드 우선 흐름, 하드코딩 목 데이터 금지).

### 스킬 사용 원칙
- 관련 스킬이 존재하면 수동 작업 전에 반드시 Skill 도구로 호출한다.
- 전역 설치 스킬이 로컬 `.claude/skills/`에 없으면 복사 후 진행한다.

---

## 핵심 코딩 규칙

### 경로 & 설정
- **모든** 경로에 `pipeline.paths.*` 상수를 사용한다. 문자열 하드코딩 금지.
- 설정 파일은 `pipeline.config_loader.load_*()`로 로드한다.
- `pathlib.Path` 사용, `os.path` 피한다.

### 데이터 I/O
- 단계 출력물은 JSONL (`*.jsonl`) 또는 JSON으로 저장한다.
- 파일 읽기/쓰기 시 항상 `encoding="utf-8"` 명시.
- 필드 명명 규칙: `session_id`, `sent_id`, `chunk_id`, `prop_id`, `fact.id`

### Python 스타일
- Python 3.10+. Union 타입에 `|` 사용 (`Path | None`, `dict[str, Any]`).
- 모든 공개 함수·러너 시그니처에 타입 힌트.
- PEP 8, 줄 길이 88–100자.
- 모듈 수준 독스트링은 한국어 (예: `"""Phase 1: 세션 분리 모듈."""`).

### 프론트엔드 스타일
- UI 텍스트와 오류 메시지는 **한국어**.
- TypeScript 인터페이스는 백엔드 Pydantic 모델과 정확히 일치.
- 색상은 `DESIGN.md`의 CSS 변수(`var(--tml-*)`) 사용. hex 하드코딩 금지.

### 라우팅 (`react-router-dom`)

페이지 전환은 **React Router v7**(`react-router-dom`)으로 관리한다. `useState`로 페이지를 전환하지 않는다.

| 경로 | 페이지 | 설명 |
|------|--------|------|
| `/` | `Home` | 홈 (소개, 모드 선택) |
| `/lecture` | `Lecture` | 단일 강의 분석 (Mode A) |
| `/weekly` | `Weekly` | 주차별 학습 가이드 (Mode B) |

- `BrowserRouter`는 `main.tsx`에서 앱 최상위를 감싼다.
- 네비게이션 활성 상태는 `useLocation()`으로 판단한다. `useState`로 관리하지 않는다.
- 새 페이지 추가 시 이 표에도 경로를 등록한다.

### 새 파이프라인 블록 추가
1. `pipeline/paths.py`에 입출력 경로 상수 추가.
2. `pipeline/config_loader.py`에 필요한 로더 함수 추가.
3. `scripts/run_pipeline.py`에 블록 등록 (해당 모드 분기에 추가).
4. 블록 모듈 상단 독스트링에 **역할·속하는 모드(A/B/공통)·입력·출력·스키마** 명시.

---

## CLAUDE.md 유지보수

CLAUDE.md를 수정할 때는 반드시 **`/claude-md-improver` 스킬**을 실행해 검토를 받는다.

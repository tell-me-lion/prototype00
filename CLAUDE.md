# CLAUDE.md

## 프로젝트 개요

**tell-me-lion**은 강의 텍스트(STT 스크립트)에서 핵심 개념·학습 포인트·퀴즈·학습 가이드를 자동 생성해 수강생에게 제공하는 풀스택 교육 시스템이다.

> **설계 원칙: 모든 것은 클라이언트 관점에서.**
> 클라이언트는 수강생뿐 아니라 이 서비스를 도입할 **교육 서비스 업체**도 포함한다.
> 시스템이 무엇을 할 수 있는지가 아니라, 클라이언트가 무엇을 필요로 하는지를 기준으로 판단한다.

### 두 가지 사용 모드

| 입력 | 출력 |
|------|------|
| 강의 스크립트 1개 (`.txt`) | 핵심 개념, 학습 포인트, 퀴즈 |
| 1주치 강의 스크립트 전체 | 주차별 학습 가이드, 주차별 핵심 요약 |

### 퀴즈 유형

객관식(MCQ), 주관식(Short Answer), 빈칸 채우기(Fill-in-the-Blank), 코드 실행형(Code Execution)을 기본으로 하되, 강의 내용과 학습 목표에 따라 더 창의적인 유형도 설계할 수 있다. 각 유형별 해설 포함.

퀴즈 생성에는 **RAG 구조**를 사용한다: 팩트·개념 DB를 검색해 근거를 찾고, 블루프린트 기반으로 문항을 생성한다.

### 파이프라인 흐름

두 모드는 독립적으로 실행된다. Mode B는 Mode A의 출력을 재사용하지 않는다.

**Mode A — 강의 1개 → 핵심 개념·학습 포인트·퀴즈**
```
스크립트 1개 → 전처리(정제·문장·청크·명제·팩트)
→ EP(핵심 개념·학습 포인트 추출)
→ 블루프린트 → 퀴즈 생성 → 퀴즈 검증
→ [출력: 핵심 개념, 학습 포인트, 퀴즈]
```

**Mode B — 1주치 전체 → 주차별 학습 가이드·핵심 요약**
```
스크립트 N개 → 각각 전처리(정제·문장·청크·명제·팩트)
→ 주차 통합
→ 학습 가이드·핵심 요약 생성
→ [출력: 주차별 학습 가이드, 주차별 핵심 요약]
```

> 구체적인 단계별 디렉터리 구조와 스키마는 파이프라인 담당 팀원의 코드가 확정되면 업데이트한다.

### 현재 상태

| 영역 | 상태 |
|------|------|
| 백엔드 API | 구조 구현 완료, 더미 데이터로 동작 중 |
| 프론트엔드 | 미생성 |
| 파이프라인 전처리 | Phase 1~5 모두 뼈대만 존재 (현재 브랜치) |
| 파이프라인 상위 블록 | EP·Blueprint·Quiz·QA·Guides 모두 뼈대만 존재 |
| 실제 입력 데이터 | `data/raw/`에 강의 스크립트 15개 존재 |

> **브랜치 현황:** `preprocessing` 브랜치에 Phase 1 구현체가 별도 존재하나, 현재 브랜치(`frontend-backend`)와 디렉터리 구조가 달라 미병합 상태. 병합 전 구조 통일 필요.

---

## 명령어

> 아래 명령어는 현재 시점 기준이며, 프로젝트 진행에 따라 변경될 수 있다.

### 백엔드
```bash
# 프로젝트 루트(tell-me-lion/)에서 실행
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
> `frontend/` 디렉터리는 아직 미생성. 처음 시작 시 React + TypeScript + Tailwind 설정 필요.

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

## 아키텍처

> 아래 구조는 현재 계획 기준이며, 파이프라인 구현이 진행됨에 따라 변경될 수 있다.

### 3계층 구조
1. **Pipeline** (`pipeline/`) — 데이터 처리; `data/raw/*.txt` 읽기, 각 단계 디렉터리에 쓰기
2. **Backend** (`app/`) — FastAPI REST API; `data/`의 파이프라인 출력 읽기
3. **Frontend** (`frontend/src/`) — React SPA; 백엔드 API만 소비

### 백엔드 (`app/`)
- `app/main.py` — FastAPI 앱, CORS 설정 (`localhost:5173`)
- `app/api/routes.py` — 엔드포인트: `POST /api/lecture-outputs`, `POST /api/weekly-outputs`, `GET /api/concepts`, `GET /api/quizzes`, `GET /api/learning-guides` 등
- `app/schemas/models.py` — Pydantic 응답 모델 (`Concept`, `LearningPoint`, `Quiz`, `LearningGuide`, `LectureOutputs`, `WeeklyOutputs`)
- `app/loaders/dummy.py` — `data/dummy/` JSON 로드 (파이프라인 연동 후 제거)

### 파이프라인 (`pipeline/`)

각 블록은 단일 `run_*()` 진입 함수를 가진 `runner.py`를 포함한다.

| 블록 | 디렉터리 | 모드 | 역할 |
|------|----------|------|------|
| Pre-processor | `phase1/` ~ `phase5/` | A, B | STT 정제 → 문장 → 청크 → 명제 → 팩트 |
| EP | `ep/` | A | 핵심 개념·학습 포인트 식별 |
| Blueprint | `blueprint/` | A | 문제 블루프린트 작성 |
| Quiz Generation | `quiz_generation/` | A | 퀴즈·해설 생성 |
| QA Validation | `qa_validation/` | A | 퀴즈 품질·사실 검증 |
| Guides | `guides/` | B | 주차 통합 → 학습 가이드·핵심 요약 생성 |

- `pipeline/paths.py` — **모든 경로 상수**. 경로를 하드코딩하지 않는다.
- `pipeline/config_loader.py` — `load_*()` 함수로 `config/*.json`/`*.yaml` 로드.

---

## 프론트엔드 디자인

프론트엔드 UI 작업(컴포넌트, 페이지, 스타일링)을 할 때는 반드시 **`frontend-design` 스킬**을 먼저 호출한다.

디자인 방향·색상·타이포그래피·컴포넌트 명세는 **`DESIGN.md`** 를 참고한다.

### Artifact-first 워크플로우 (UI 작업 전용)

시각적 결과물이 있는 모든 프론트엔드 작업에 적용한다. 파이프라인·백엔드 작업에는 해당 없음.

**실행 순서 (절대 바꾸지 않는다):**
1. task 파일 읽기
2. **JSX Artifact로 프리뷰 렌더링** — 파일을 작성하기 전에 반드시 먼저
3. 사용자 확인: "맞다" 또는 피드백
4. 승인 후 → 실제 파일 작성
5. 다음 task로 이동

**Artifact 프리뷰의 한계:**

| 항목 | Artifact 내 동작 |
|------|----------------|
| CSS custom properties (`var(--tml-*)`) | 작동 (`:root` 인라인 선언 필요) |
| Google Fonts (Playfair Display 등) | CDN 로드 불안정 → fallback 폰트로 보일 수 있음 |
| Tailwind 유틸리티 클래스 | 빌드 없이 미작동 → 인라인 스타일로 대체 |
| 애니메이션, 노이즈 그레인 | 대체로 작동 |

→ Artifact로 검증: **색상 팔레트, 레이아웃 비율, 컴포넌트 구조, 전체 분위기**
→ `npm run dev`로 검증: **폰트 로딩, Tailwind 클래스, 애니메이션 타이밍**

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

### 파이프라인 Mode A / Mode B 구분 규칙

모든 파이프라인 코드는 자신이 어느 모드에 속하는지 명확히 한다.

| 항목 | Mode A (강의 1개) | Mode B (1주치) |
|------|-------------------|----------------|
| 입력 단위 | 스크립트 파일 1개 | 주차 디렉터리 (N개 파일) |
| 출력 | 핵심 개념·학습 포인트·퀴즈 | 주차별 학습 가이드·핵심 요약 |
| 해당 블록 | Phase 1~5, EP, Blueprint, Quiz, QA | Phase 1~5, Guides |
| `run_pipeline.py` 호출 | `--mode a --input <파일>` | `--mode b --week <주차>` |

- **Mode A 블록** (`ep`, `blueprint`, `quiz_generation`, `qa_validation`): 단일 파일 단위로 처리. 입력은 항상 파일 1개 기준의 경로를 받는다.
- **Mode B 블록** (`guides`): 주차 내 모든 파일의 전처리 결과를 모아서 처리. 입력은 주차 단위 디렉터리.
- **공통 블록** (`phase1`~`phase5`): Mode A·B 모두에서 호출된다. 단일 파일 단위로 동작하며, Mode B는 N개 파일에 반복 적용한다.
- 두 모드는 서로 독립적으로 실행된다. **Mode B가 Mode A의 출력을 읽어선 안 된다.**

### 새 파이프라인 블록 추가
1. `pipeline/paths.py`에 입출력 경로 상수 추가.
2. `pipeline/config_loader.py`에 필요한 로더 함수 추가.
3. `scripts/run_pipeline.py`에 블록 등록 (해당 모드 분기에 추가).
4. 블록 모듈 상단 독스트링에 **역할·속하는 모드(A/B/공통)·입력·출력·스키마** 명시.

---

## 더미 데이터 (개발 중)

백엔드는 파이프라인이 완성되기 전까지 `data/dummy/`의 JSON 파일을 읽는다.

| 파일 | 모드 | 내용 |
|------|------|------|
| `concepts.json` | A | 핵심 개념 샘플 3개 |
| `learning_points.json` | A | 학습 포인트 샘플 3개 |
| `quizzes.json` | A | 퀴즈 샘플 3개 (mcq·short·fill 각 1개; code 타입 더미 미포함) |
| `learning_guides.json` | B | 주차별 학습 가이드 샘플 3개 (1~3주차) |

- Mode A 더미(concepts, learning_points, quizzes)와 Mode B 더미(learning_guides)는 서로 참조하지 않는다.
- 모든 더미 데이터는 실제 파이프라인 출력과 동일한 스키마를 따른다.
- **파이프라인 연동 후 `app/loaders/dummy.py`를 제거한다.**

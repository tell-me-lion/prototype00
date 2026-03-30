# CLAUDE.md

## 프로젝트 개요

**알려주사자**는 강의 녹화본에서 핵심 개념·학습 포인트·퀴즈·학습 가이드를 자동 생성해 수강생에게 제공하는 풀스택 교육 시스템이다.

> **핵심 목표: 유저가 편할 수 있도록.**
> 유저는 파일을 일일이 업로드하지 않는다. 대시보드에 강의 목록이 떠 있고, 원하는 강의를 선택하면 서버가 나머지를 모두 처리한다.
> 클라이언트는 수강생뿐 아니라 이 서비스를 도입할 **교육 서비스 업체**도 포함한다.

### 두 가지 출력 모드

| 입력 | 출력 |
|------|------|
| 강의 1개 선택 | 핵심 개념, 학습 포인트, 퀴즈 (Mode A) |
| 1주치 강의 전체 선택 | 주차별 학습 가이드, 주차별 핵심 요약 (Mode B) |

두 모드는 독립적으로 실행된다. **Mode B는 Mode A의 출력을 읽어선 안 된다.**

### 팀 역할

| 담당 | 작업 |
|------|------|
| 시훈 | 전처리 고도화 — 배포 시 용량·GPU 최적화, Gemini API 비용 관리 |
| 경현 | 전처리 데이터 기반 퀴즈 생성·핵심 개념·학습 포인트 등 고도화, 출력 형식 정의 |
| 주노 | UI/UX 개선 (대시보드 기반 UX), 프론트엔드·백엔드 연동, 배포 인프라 관리 |

> 목표·평가 기준·제출물은 **`docs/PROJECT_GOALS.md`** 참고.

---

## 명령어

### 백엔드
```bash
python -m uvicorn app.main:app --reload
# API: http://localhost:8000  |  Docs: http://localhost:8000/docs
```
> `uvicorn` 단독 사용 금지 — Windows PATH 문제 방지.

### 프론트엔드
```bash
cd frontend && npm install && npm run dev   # http://localhost:5173
npm run build
npm run lint
```

### 파이프라인
```bash
# Mode A
python scripts/run_pipeline.py --mode a --input data/raw/lecture_01.txt
# Mode B
python scripts/run_pipeline.py --mode b --week 1
# 블록 범위 지정
python scripts/run_pipeline.py --mode a --from-block preproc --to-block ep
# 전처리 Phase 범위
python scripts/run_pipeline.py --mode a --from-phase 1 --to-phase 3
```

---

## 아키텍처

### 3계층 구조
1. **Pipeline** (`pipeline/`) — STT 결과 → 전처리 → 개념 추출 → 퀴즈 생성
2. **Backend** (`app/`) — FastAPI REST API; 강의 목록 제공, 파이프라인 트리거, 결과 전달
3. **Frontend** (`frontend/src/`) — React SPA; 대시보드에서 강의 선택 → 결과 소비

### 백엔드 (`app/`)
- `app/main.py` — FastAPI 앱, CORS 설정
- `app/api/routes.py` — API 엔드포인트
- `app/schemas/models.py` — Pydantic 응답 모델
- `app/loaders/dummy.py` — `data/dummy/` JSON 로드 (파이프라인 연동 후 제거)

### 파이프라인 (`pipeline/`)

각 블록은 단일 `run_*()` 진입 함수를 가진 `runner.py`를 포함한다.

| 블록 | 디렉터리 | 모드 | 입력 → 출력 |
|------|----------|------|-------------|
| Pre-processor | `preprocessor/` | A, B | `data/raw/*.txt` → `data/phase5_facts/*.jsonl` |
| EP | `ep/` | A | 팩트 → `data/ep_concepts/*.jsonl` |
| Blueprint | `blueprint/` | A | 개념+팩트 → `data/blueprints/*.jsonl` |
| Quiz Generation | `quiz_generation/` | A | Blueprint → `data/quizzes_raw/*.jsonl` |
| QA Validation | `qa_validation/` | A | 퀴즈 → `data/quizzes_validated/*.jsonl` |
| Guides | `guides/` | B | 전처리 결과 → `data/learning_guides/*.jsonl` |

- `pipeline/paths.py` — **모든 경로 상수**
- `pipeline/config_loader.py` — `load_*()` 함수로 설정 로드
- `config/quiz_blueprint_rules.json` — 퀴즈 생성 규칙
- `config/rag_config.json` — RAG 검색 설정

---

## 배포 워크플로우

**실행 순서 (절대 바꾸지 않는다):**
1. **`DEPLOY.md` 먼저 작성 또는 업데이트** — 무엇을 왜 바꾸는지 기록
2. 코드·설정 파일 작성
3. **`bash scripts/deploy-check.sh` 실행** — 자동 검증 (또는 `/deploy-check` 스킬)
4. 검증 통과 후 GitHub push

> 배포 전: `requirements.txt` / `package.json`에 새 패키지가 모두 포함됐는지 확인.
> 배포 URL이 제공되면 즉시 `DEPLOY.md`, `frontend/.env.local`, Vercel 환경변수를 업데이트.

| 계층 | 배포 위치 | 주소 |
|------|-----------|------|
| 프론트엔드 | Vercel | `https://<vercel-domain>` / `http://localhost:5173` |
| 백엔드 + 파이프라인 | 팀원 GPU 머신 | `https://<backend-domain>` |

---

## 워크플로우

### 프론트엔드 디자인

UI 작업 시 반드시 **`frontend-design` 스킬**을 먼저 호출. 디자인 명세는 **`DESIGN.md`** 참고.

**Write-and-Preview (절대 바꾸지 않는다):**
1. task 파일 읽기
2. 실제 파일 작성 + JSX Artifact 동시 제공
3. 사용자: `npm run dev`로 확인 → "맞다" 또는 피드백
4. 피드백 → 수정 → 3단계 반복
5. "맞다" 후 → `/frontend-check` 스킬 실행
6. 다음 task

> 사용자 승인과 `/frontend-check`는 독립적 필수 관문.

### 기능 구현

**명세 먼저, 코드 나중.**
1. `docs/tasks/`에 태스크 명세 작성 (`_template.md` 참고)
2. 사용자 승인 대기
3. 승인 후 구현 시작

> 승인 없이 코드 작성 금지.

---

## 실행 원칙

- **코드 작성 요청엔 즉시 파일에 직접 작성한다.** 계획·설명을 먼저 하지 않는다.
- **작성 후 Read 도구로 반영 여부를 검증한다.**
- **하드코딩 금지**: 색상(`var(--tml-*)`), 데이터(API 연동), URL(환경변수·설정파일).
- 관련 스킬이 존재하면 수동 작업 전에 반드시 Skill 도구로 호출한다.

---

## 핵심 코딩 규칙

### 경로 & 설정
- **모든** 경로에 `pipeline.paths.*` 상수 사용. 문자열 하드코딩 금지.
- 설정은 `pipeline.config_loader.load_*()`로 로드.
- `pathlib.Path` 사용, `os.path` 피한다.

### 데이터 I/O
- 출력물은 JSONL/JSON. 항상 `encoding="utf-8"` 명시.
- 필드명: `session_id`, `sent_id`, `chunk_id`, `prop_id`, `fact.id`

### Python
- Python 3.10+, Union은 `|` 사용.
- 공개 함수에 타입 힌트. PEP 8, 줄 길이 88–100자.
- 모듈 독스트링은 한국어.

### 프론트엔드
- UI 텍스트·오류 메시지는 **한국어**.
- TypeScript 인터페이스는 백엔드 Pydantic 모델과 일치.
- 색상은 `DESIGN.md`의 CSS 변수(`var(--tml-*)`) 사용.

### 라우팅 (`react-router-dom` v7)

| 경로 | 페이지 | 설명 |
|------|--------|------|
| `/` | `Dashboard` | 대시보드 |
| `/lecture/:id` | `LectureResult` | 단일 강의 결과 (Mode A) |
| `/weekly/:week` | `WeeklyResult` | 주차별 학습 가이드 (Mode B) |
| `/lecture`, `/weekly` | → `/` 리다이렉트 | 하위 호환 |

- `BrowserRouter`는 `main.tsx` 최상위. `useState`로 페이지 전환 금지.
- 네비게이션 활성 상태는 `useLocation()` 사용.

### 새 파이프라인 블록 추가
1. `pipeline/paths.py`에 경로 상수 추가
2. `pipeline/config_loader.py`에 로더 추가
3. `scripts/run_pipeline.py`에 블록 등록
4. 모듈 독스트링에 역할·모드·입출력·스키마 명시

---

## 오류 기록

반복 오류와 해결 과정은 **`ERRORS.md`**에 기록. 새 오류 발생 시 즉시 추가.

## CLAUDE.md 유지보수

수정 시 반드시 **`/claude-md-improver` 스킬**을 실행해 검토.

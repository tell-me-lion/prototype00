# CLAUDE.md

## 프로젝트 개요

**알려주사자** — 강의 녹화본에서 핵심 개념·퀴즈·학습 가이드를 자동 생성해 수강생에게 제공하는 풀스택 교육 시스템.

> **핵심 UX: 유저가 편할 수 있도록.** 파일 업로드 없음. 대시보드에서 강의 선택 → 서버가 나머지 처리.
> 클라이언트 = 수강생 + **교육 서비스 업체**.

| 입력 | 출력 |
|------|------|
| 강의 1개 선택 | 핵심 개념, 학습 포인트, 퀴즈 (Mode A) |
| 1주치 강의 전체 | 주차별 학습 가이드 & 핵심 요약 (Mode B) |

### 팀 역할

| 담당 | 작업 |
|------|------|
| 시훈 | 전처리 고도화, 배포 최적화, Gemini API 비용 관리 |
| 경현 | 퀴즈·개념·학습포인트 생성 고도화, 출력 형식 정의 |
| 주노 | UI/UX, 프론트-백 연동, 배포 인프라 |

---

## 디렉터리 구조

```
tell-me-lion/
├── frontend/          # React + TypeScript + Vite (주노 담당)
│   └── src/
│       ├── pages/     # 라우트별 페이지 컴포넌트
│       ├── components/# 공용 컴포넌트
│       ├── services/  # API 호출 (api.ts)
│       ├── types/     # TypeScript 타입 (models.ts)
│       ├── hooks/     # 커스텀 훅
│       └── index.css  # 전역 스타일 (CSS 변수 포함)
├── app/               # FastAPI 백엔드
│   ├── api/           # 라우터
│   ├── schemas/       # Pydantic 모델
│   └── main.py        # 엔트리포인트
├── pipeline/          # 전처리 파이프라인 (시훈 담당)
├── data/              # 더미 데이터 (백엔드 연동 전 시연용)
├── docs/tasks/        # 태스크 명세 파일
├── DESIGN.md          # 색상·타이포·컴포넌트 스펙
└── PROJECT_GOALS.md   # 전체 평가 기준·제출물 목록
```

---

## 커맨드

```bash
# 프론트엔드 (frontend/ 디렉터리에서)
npm run dev        # 개발 서버 (localhost:5173)
npm run build      # 프로덕션 빌드 (tsc -b && vite build)
npm run lint       # ESLint
npm run test       # Vitest 단위 테스트
npm run preview    # 빌드 결과 미리보기

# 백엔드 (루트에서)
uvicorn app.main:app --reload   # 개발 서버 (localhost:8000)
```

---

## 실행 원칙

- **명시적 코드 작성 요청** → 즉시 파일에 직접 작성 (계획·설명 먼저 금지)
- **변경·기능 제안 시** → 유저에게 먼저 확인 → `docs/tasks/`에 태스크 파일 작성 → 승인 후 구현
- 작성 후 Read 도구로 반영 확인
- 하드코딩 금지: 색상(`var(--tml-*)`), 데이터(API 연동), URL(환경변수)
- 관련 스킬이 있으면 수동 작업 전에 Skill 도구 먼저 호출

### docs/tasks/ 태스크 파일 규칙

- 파일명: `TASK-{번호}-{간단설명}.md` (예: `TASK-001-lectures-page-redesign.md`)
- 내용: 목적, 변경 파일, 작업 항목 체크리스트
- 구현 완료 후 체크리스트 업데이트

---

## 핵심 코딩 규칙

### 프론트엔드

- TypeScript 인터페이스 ↔ 백엔드 Pydantic 모델 일치 (`types/models.ts` ↔ `app/schemas/`)
- 색상: `DESIGN.md`의 CSS 변수(`var(--tml-*)`) 사용, 하드코딩 금지
- 더미 데이터는 `data/` 디렉터리 참조 (백엔드 연동 전)

### 라우팅 (`react-router-dom` v7)

| 경로 | 페이지 | 설명 |
|------|--------|------|
| `/` | `Dashboard` | 대시보드 |
| `/lectures` | `LecturesPage` | 강의 목록 + 분석 시작 |
| `/lecture/:id` | `LectureResult` | 단일 강의 결과 (Mode A) |
| `/weekly/:week` | `WeeklyResult` | 주차별 학습 가이드 (Mode B) |
| `/lecture`, `/weekly` | → `/` 리다이렉트 | 하위 호환 |

- `BrowserRouter`는 `main.tsx` 최상위. `useState`로 페이지 전환 금지.
- 네비게이션 활성 상태: `useLocation()` 사용.

---

## 환경 변수

```bash
# frontend/.env.local (로컬 개발)
VITE_API_URL=http://localhost:8000

# Vercel 환경변수 (배포)
VITE_API_URL=http://15.165.140.229
```

---

## 배포 환경

| 레이어 | 플랫폼 | 주소 | 배포 방식 |
|--------|--------|------|-----------|
| 프론트엔드 | Vercel | `wonder-girls.vercel.app` | main push 시 Vercel 자동 배포 |
| 백엔드 | AWS EC2 | `15.165.140.229` | main push 시 GitHub Actions 자동 배포 |

### 자동 배포 상세

- **프론트엔드**: Vercel이 main 브랜치 push 감지 → 자동 빌드·배포
- **백엔드**: `.github/workflows/deploy-backend.yml` — main push 시 `app/`, `pipeline/`, `config/`, `requirements.txt`, `scripts/` 경로 변경 감지 → EC2에 SSH 접속 → `git pull` + `docker compose up -d --build` → health check(`/health`)
- **양쪽 모두 수동 배포 불필요**. PR 머지 = 배포 완료.

---

## 참고 파일

- `DESIGN.md` — 색상·타이포·컴포넌트 스펙 (UI 작업 시 반드시 읽기)
- `PROJECT_GOALS.md` — 전체 평가 기준·제출물 목록
- `docs/tasks/` — 태스크 명세

## CLAUDE.md 유지보수

수정 시 `/claude-md-improver` 스킬 실행.

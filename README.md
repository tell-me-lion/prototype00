# 알려주사자 (Tell Me Lion)

강의 텍스트(STT 스크립트)에서 핵심 개념·학습 포인트·퀴즈·학습 가이드를 자동 생성해 수강생에게 제공하는 풀스택 교육 시스템.

---

## 빠른 시작

### 백엔드

```bash
python -m uvicorn app.main:app --reload
# API: http://localhost:8000  |  Docs: http://localhost:8000/docs
```

### 프론트엔드

```bash
cd frontend
npm install
npm run dev   # http://localhost:5173
```

### 파이프라인

```bash
# Mode A: 강의 1개 → 핵심 개념·학습 포인트·퀴즈
python scripts/run_pipeline.py --mode a --input data/raw/lecture_01.txt

# Mode B: 1주치 전체 → 주차별 학습 가이드·핵심 요약
python scripts/run_pipeline.py --mode b --week 1

# 블록 범위 지정
python scripts/run_pipeline.py --mode a --from-block preproc --to-block ep

# 전처리 Phase 범위 지정
python scripts/run_pipeline.py --mode a --from-phase 1 --to-phase 3
```

---

## 구조

```
tell-me-lion/
├── app/                # FastAPI 백엔드
├── pipeline/           # 데이터 처리 파이프라인
│   ├── preprocessor/   # Phase 1~5: STT → 구조화 팩트
│   ├── ep/             # 핵심 개념·학습 포인트 추출
│   ├── blueprint/      # 퀴즈 설계
│   ├── quiz_generation/
│   ├── qa_validation/
│   └── guides/
├── frontend/           # React SPA
├── scripts/            # run_pipeline.py 등
├── config/             # 퀴즈 규칙, RAG 설정
└── data/               # 파이프라인 입출력 (git 제외)
```

---

## 두 가지 사용 모드

| 입력 | 출력 |
|------|------|
| 강의 스크립트 1개 (`.txt`) | 핵심 개념, 학습 포인트, 퀴즈 |
| 1주치 강의 스크립트 전체 | 주차별 학습 가이드, 핵심 요약 |

---

## 기술 스택

| 영역 | 기술 |
|------|------|
| 백엔드 | Python 3.10+, FastAPI, Uvicorn, Pydantic v2 |
| 프론트엔드 | React 19, TypeScript 5.9, Vite 8, Tailwind CSS 4 |
| AI·파이프라인 | Google Gemini API, KiwiPiePy, KR-SBERT, scikit-learn |
| 실행 | 로컬 환경 (팀원 PC에서 직접 실행) |

---

## 문서

- [`CLAUDE.md`](./CLAUDE.md) — 아키텍처, 코딩 규칙, 워크플로우
- [`DESIGN.md`](./DESIGN.md) — 프론트엔드 디자인 가이드
- [`DEPLOY.md`](./DEPLOY.md) — 배포 플랜 및 설정
- [`ERRORS.md`](./ERRORS.md) — 오류 기록
- [`docs/preprocessing-flow.md`](./docs/preprocessing-flow.md) — 전처리 데이터 플로우

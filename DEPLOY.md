# DEPLOY.md — 로컬 실행 가이드

> 클라우드 배포 없이 **팀원 로컬 환경**에서 직접 실행한다.
> 코드 변경 시 이 파일을 먼저 업데이트한다.

---

## 실행 환경

| 계층 | 실행 방법 | 주소 |
|------|-----------|------|
| 백엔드 | `python -m uvicorn app.main:app --reload` | `http://localhost:8000` |
| 프론트엔드 | `npm run dev` (frontend/) | `http://localhost:5173` |
| DB | 없음 (localStorage) | — |

---

## 환경변수

### 프론트엔드 (`frontend/.env.local`)

```
VITE_API_URL=http://localhost:8000
```

### 백엔드 (`.env`)

```
ALLOWED_ORIGINS=http://localhost:5173
```

> `.env.example` / `frontend/.env.example` 참고.

---

## 팀원 로컬 셋업 순서

### 1단계 — 레포 클론 및 Python 환경 구성

```bash
git clone <repo-url>
cd tell-me-lion
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### 2단계 — 환경변수 파일 생성

```bash
# 백엔드
cp .env.example .env
# 프론트엔드
cp frontend/.env.example frontend/.env.local
```

> `.env`에 `GEMINI_API_KEY` 등 필요한 키를 직접 입력한다.

### 3단계 — 백엔드 실행

```bash
python -m uvicorn app.main:app --reload
# http://localhost:8000/docs 에서 API 확인
```

### 4단계 — 프론트엔드 실행

```bash
cd frontend
npm install
npm run dev
# http://localhost:5173 에서 UI 확인
```

---

## 동작 확인

- `http://localhost:5173/` — 홈 화면 로드
- `http://localhost:5173/lecture` — 강의 분석 페이지 로드
- `http://localhost:8000/health` → `{"status": "ok"}`
- `http://localhost:8000/docs` — FastAPI Swagger UI

---

## 로컬 실행 전 체크리스트

`/deploy-check` 스킬 실행으로 자동 검증된다. 수동으로 확인할 항목:

- [ ] `.env`에 `GEMINI_API_KEY` 설정됨
- [ ] `frontend/.env.local`에 `VITE_API_URL=http://localhost:8000` 설정됨
- [ ] `npm run build` 성공 (TypeScript 오류 없음)
- [ ] `python -c "from app.main import app"` 성공
- [ ] 백엔드·프론트엔드 동시 실행 후 API 통신 정상

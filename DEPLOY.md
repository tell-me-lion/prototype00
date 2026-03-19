# DEPLOY.md — 배포 플랜

> 코드 작업 전에 이 파일을 먼저 작성한다.
> 배포 관련 변경 사항이 생길 때마다 업데이트한다.

---

## 서비스 구성

| 계층 | 서비스 | 플랜 | 비고 |
|------|--------|------|------|
| 프론트엔드 | Vercel (Hobby) | 무료 | `frontend/` 디렉터리 |
| 백엔드 | Railway (Starter) | 무료 | 레포 루트, `Procfile` 사용 |
| DB | 없음 (localStorage) | — | 이력 저장은 브라우저 로컬에 |

---

## 환경변수

### 프론트엔드 (Vercel → Settings → Environment Variables)

| 변수 | 값 | 설명 |
|------|----|------|
| `VITE_API_URL` | `https://<railway-url>` | Railway 배포 후 실제 URL로 교체 |

### 백엔드 (Railway → Variables 탭)

| 변수 | 값 | 설명 |
|------|----|------|
| `ALLOWED_ORIGINS` | `https://<vercel-url>` | Vercel 배포 후 실제 URL로 교체 |

---

## 배포 설정 파일

| 파일 | 역할 |
|------|------|
| `frontend/vercel.json` | React Router SPA 라우팅 — 새로고침 시 404 방지 |
| `Procfile` | Railway 시작 명령: `python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| `frontend/.env.example` | 프론트 환경변수 명세 |
| `.env.example` | 백엔드 환경변수 명세 |

---

## 배포 순서

> ⚠️ **Railway 먼저, Vercel 나중.** 프론트가 백엔드 URL을 참조하기 때문.

### 1단계 — Railway (백엔드)

1. [railway.app](https://railway.app) → **New Project** → **Deploy from GitHub**
2. 레포 선택, **Root Directory는 변경하지 않는다** (루트에 `Procfile` 있음)
3. 배포 완료 후 **Settings → Networking → Public Networking 활성화**
4. 생성된 URL 복사 (예: `https://tell-me-lion-production.up.railway.app`)
5. Variables 탭에서 `ALLOWED_ORIGINS` 추가 (Vercel 배포 후 설정 가능, 일단 보류)

### 2단계 — Vercel (프론트엔드)

1. [vercel.com](https://vercel.com) → **Add New Project** → GitHub 연결
2. **Root Directory: `frontend`** 로 설정
3. Framework Preset: **Vite** (자동 감지됨)
4. Environment Variables 추가:
   ```
   VITE_API_URL = https://tell-me-lion-production.up.railway.app
   ```
5. **Deploy** → 생성된 URL 복사 (예: `https://tell-me-lion.vercel.app`)

### 3단계 — CORS 업데이트

Railway 프로젝트 → Variables 탭에 추가 후 저장 (자동 재배포):
```
ALLOWED_ORIGINS = https://tell-me-lion.vercel.app
```

### 4단계 — 동작 확인

- `https://<vercel-url>/` — 홈 화면 로드
- `https://<vercel-url>/lecture` — 강의 분석 페이지 로드
- `https://<railway-url>/health` → `{"status": "ok"}` 응답
- `https://<railway-url>/docs` — FastAPI Swagger UI

---

## 주의사항

- **Supabase 무료 플랜**: 7일 비활성 시 자동 일시정지 (현재 미사용)
- Railway 무료 플랜: 월 $5 크레딧, 발표용으로는 충분
- Vercel Hobby: 빌드 타임아웃 45분, 일반적으로 문제없음
- CORS 오류 발생 시: Railway Variables에서 `ALLOWED_ORIGINS` 값 재확인

---

## 배포 전 체크리스트

`/deploy-check` 스킬 실행으로 자동 검증된다. 수동으로 확인할 항목:

- [ ] `npm run build` 성공 (TypeScript 오류 없음)
- [ ] `python -c "from app.main import app"` 성공
- [ ] `frontend/.env.example`에 `VITE_API_URL` 등록됨
- [ ] `.env.example`에 `ALLOWED_ORIGINS` 등록됨
- [ ] `frontend/vercel.json` 존재
- [ ] `Procfile` 존재
- [ ] GitHub에 최신 코드 push됨

# DEPLOY.md

## 인프라 구성

| 계층 | 플랫폼 | 주소 |
|------|--------|------|
| 프론트엔드 | Vercel | https://wonder-girls.vercel.app |
| 백엔드 + API | AWS EC2 (t3.micro, ap-northeast-2) | http://15.165.140.229 |

> HTTPS 미적용 상태. 도메인 연결 후 certbot으로 전환 예정.

---

## EC2 서버 정보

| 항목 | 값 |
|------|-----|
| 인스턴스 타입 | t3.micro (1 vCPU, 1GB RAM) |
| OS | Ubuntu 22.04 LTS |
| 리전 | ap-northeast-2 (서울) |
| Elastic IP | 15.165.140.229 |
| EBS | 30GB gp3 |
| 보안그룹 포트 | 22 (SSH), 80 (HTTP), 443 (HTTPS) |
| SSH 키 | `tellmelion-key.pem` (로컬 보관, git 미추적) |

### 서버 프로세스

| 서비스 | 설명 |
|--------|------|
| `tellmelion.service` (systemd) | uvicorn → FastAPI 앱 (port 8000) |
| nginx | 리버스 프록시 80 → localhost:8000 |

---

## 환경변수

### 백엔드 (EC2 `.env`)

| 변수 | 설명 | 예시 |
|------|------|------|
| `GOOGLE_API_KEY` | Gemini API 키 | `AIza...` |
| `ALLOWED_ORIGINS` | CORS 허용 origin (쉼표 구분) | `https://wonder-girls.vercel.app` |

### 프론트엔드

| 변수 | 설명 | 기본값 |
|------|------|--------|
| `VITE_API_URL` | 백엔드 API 엔드포인트 | `http://localhost:8000` |

- **Vercel 환경변수**: Vercel 대시보드 → Settings → Environment Variables에서 `VITE_API_URL` 설정
- **로컬 개발**: `frontend/.env.local`에 설정

---

## 배포 절차

### 백엔드 (EC2 수동 배포)

```bash
# 1. SSH 접속
ssh -i tellmelion-key.pem ubuntu@15.165.140.229

# 2. 코드 업데이트
cd ~/tell-me-lion
git pull origin main

# 3. 의존성 업데이트 (변경 시)
source venv/bin/activate
pip install -r requirements.txt

# 4. 서비스 재시작
sudo systemctl restart tellmelion

# 5. 상태 확인
sudo systemctl status tellmelion
curl http://localhost:8000/health
```

### 프론트엔드 (Vercel 자동 배포)

- `main` 브랜치 push 시 Vercel이 자동 빌드·배포
- 빌드 명령: `cd frontend && npm install && npm run build`
- 출력 디렉터리: `frontend/dist`

### 백엔드 자동 배포 (GitHub Actions)

`main` 브랜치에 백엔드 관련 파일(`app/`, `pipeline/`, `config/`, `requirements.txt`) push 시 자동 배포.

워크플로: `.github/workflows/deploy-backend.yml`

**필요한 GitHub Secrets** (Settings → Secrets and variables → Actions):

| Secret | 값 |
|--------|-----|
| `EC2_HOST` | `15.165.140.229` |
| `EC2_USER` | `ubuntu` |
| `EC2_SSH_KEY` | `tellmelion-key.pem`의 전체 내용 (PEM 형식) |

### 배포 전 체크리스트

```bash
bash scripts/deploy-check.sh
```

검증 항목:
1. `requirements.txt` 누락 패키지 확인
2. 백엔드 임포트 검증
3. TypeScript 타입 검사 + 프론트엔드 빌드
4. `.env.example` 환경변수 문서화
5. `localhost` 하드코딩 탐색

---

## 헬스 체크

```bash
# 백엔드 API
curl http://15.165.140.229/health
# 응답: {"status":"ok"}

# 프론트엔드
curl -I https://wonder-girls.vercel.app
```

---

## 주의사항

- EC2 중지 시 Elastic IP 요금 발생 → 안 쓸 때 IP 해제하거나 인스턴스 유지
- EBS 30GB 초과 시 과금
- t3.micro RAM 1GB → FastAPI만 구동, 파이프라인(GPU)은 별도 머신 권장
- AWS 프리 티어 12개월 한정 — 만료일 확인 필요

---

## 변경 이력

| 날짜 | 변경 내용 |
|------|-----------|
| 2026-03-30 | 초기 문서 작성: EC2 + Vercel 배포 구성 기록 |
| 2026-03-30 | GitHub Actions 백엔드 자동 배포 추가 |

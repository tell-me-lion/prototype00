#!/bin/bash
# 배포 전 전체 스택 사전 점검 스크립트
# 사용법: bash scripts/deploy-check.sh

set -e
PASS=0
FAIL=0

check() {
  local label="$1"
  local cmd="$2"
  if eval "$cmd" > /dev/null 2>&1; then
    echo "  ✅ $label"
    PASS=$((PASS + 1))
  else
    echo "  ❌ $label"
    FAIL=$((FAIL + 1))
  fi
}

echo ""
echo "=== 배포 사전 점검 ==="
echo ""

# 1. Python import vs requirements.txt
echo "[1] 백엔드 의존성"
MISSING_PKGS=$(python - <<'EOF'
import os, ast, re

req_file = "requirements.txt"
if not os.path.exists(req_file):
    print("requirements.txt 없음")
    exit()

with open(req_file) as f:
    req_lines = [re.split(r'[>=<!]', l.strip())[0].lower().replace('-', '_')
                 for l in f if l.strip() and not l.startswith('#')]

imports = set()
for root, _, files in os.walk("app"):
    for fn in files:
        if fn.endswith(".py"):
            try:
                tree = ast.parse(open(os.path.join(root, fn)).read())
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            imports.add(alias.name.split('.')[0].lower().replace('-','_'))
                    elif isinstance(node, ast.ImportFrom) and node.module:
                        imports.add(node.module.split('.')[0].lower().replace('-','_'))
            except:
                pass

stdlib = {'os','sys','re','json','ast','pathlib','typing','collections','functools',
          'itertools','datetime','time','math','random','hashlib','logging','io','abc',
          'copy','enum','dataclasses','contextlib','threading','subprocess','shutil'}
third_party = imports - stdlib - {'app','pipeline','config','scripts','__future__'}
missing = [p for p in sorted(third_party) if p not in req_lines]
if missing:
    print("누락:", ', '.join(missing))
EOF
)
if [ -z "$MISSING_PKGS" ]; then
  echo "  ✅ requirements.txt 완전"
  PASS=$((PASS + 1))
else
  echo "  ❌ requirements.txt 누락: $MISSING_PKGS"
  FAIL=$((FAIL + 1))
fi

# 2. 백엔드 임포트 실제 실행
check "백엔드 임포트 OK" "python -c 'from app.main import app'"

# 3. 프론트엔드 빌드
echo ""
echo "[2] 프론트엔드"
check "TypeScript 타입 검사" "cd frontend && npx tsc --noEmit"
check "프론트엔드 빌드" "cd frontend && npm run build"

# 4. 환경변수 문서화
echo ""
echo "[3] 환경변수"
if [ -f ".env.example" ]; then
  ENV_VARS_CODE=$(grep -r "import\.meta\.env\." frontend/src --include="*.ts" --include="*.tsx" -oh | sort -u)
  ENV_VARS_DOC=$(grep -o "VITE_[A-Z_]*" .env.example | sort -u)
  MISSING_ENV=$(comm -23 <(echo "$ENV_VARS_CODE" | grep -o "VITE_[A-Z_]*" | sort) <(echo "$ENV_VARS_DOC" | sort))
  if [ -z "$MISSING_ENV" ]; then
    echo "  ✅ .env.example 완전"
    PASS=$((PASS + 1))
  else
    echo "  ❌ .env.example 누락: $MISSING_ENV"
    FAIL=$((FAIL + 1))
  fi
else
  echo "  ⚠️  .env.example 없음 (건너뜀)"
fi

# 5. localhost 하드코딩 탐색
echo ""
echo "[4] 하드코딩 탐색"
HARDCODED=$(grep -r "localhost:8000" frontend/src --include="*.ts" --include="*.tsx" -l 2>/dev/null || true)
if [ -z "$HARDCODED" ]; then
  echo "  ✅ localhost 하드코딩 없음"
  PASS=$((PASS + 1))
else
  echo "  ❌ localhost 하드코딩 발견: $HARDCODED"
  FAIL=$((FAIL + 1))
fi

# 6. CLAUDE.md에 명시된 npm 스크립트 존재 확인
check "npm run dev 존재" "cd frontend && npm run --list | grep -q dev"
check "npm run build 존재" "cd frontend && npm run --list | grep -q build"
check "npm test 존재" "cd frontend && npm run --list | grep -q test"

# 결과
echo ""
echo "=== 결과: ✅ $PASS 통과 / ❌ $FAIL 실패 ==="
if [ $FAIL -eq 0 ]; then
  echo "✅ Preflight 완료 — 배포 준비 됨"
  exit 0
else
  echo "❌ 위 항목 수정 후 재실행"
  exit 1
fi

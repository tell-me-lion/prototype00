FROM python:3.12-slim

WORKDIR /app

# 시스템 의존성 (kiwipiepy 빌드에 필요)
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc g++ && \
    rm -rf /var/lib/apt/lists/*

# Python 의존성 설치 (캐시 활용을 위해 requirements.txt만 먼저 복사)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 소스 코드 복사
COPY app/ app/
COPY pipeline/ pipeline/

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

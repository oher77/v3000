# -------------------------
# 1. 베이스 이미지 선택
# -------------------------
FROM python:3.11-slim

# -------------------------
# 2. 작업 디렉토리 설정
# -------------------------
WORKDIR /app

# -------------------------
# 3. 필요한 패키지 설치
# -------------------------
# 시스템 의존성 (reportlab에 필요할 수 있음)
RUN apt-get update && apt-get install -y \
    build-essential \
    libfreetype6-dev \
    libffi-dev \
    libjpeg-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# -------------------------
# 4. requirements 설치
# -------------------------
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# -------------------------
# 5. 앱 소스 복사
# -------------------------
COPY requirements.txt ./
COPY run.py ./
COPY fonts ./fonts
COPY voca3000_account_key.json ./

# -------------------------
# 6. 컨테이너 실행 명령
# -------------------------
EXPOSE 8501

# 환경 변수 기본값 설정 (실제 배포 시 secret 관리 권장)
# ENV GA_MEASUREMENT_ID=G-XXXXXXX
# ENV GOOGLE_APPLICATION_CREDENTIALS=/app/secrets/voca3000_account_key.json

# Streamlit 기본 실행 (실행할 메인 파일 이름 맞춰주세요, 예: app.py)
CMD ["streamlit", "run", "run.py", "--server.port=8501", "--server.address=0.0.0.0"]
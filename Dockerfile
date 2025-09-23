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
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# -------------------------
# 5. 앱 소스 복사
# -------------------------
COPY run.py ./
COPY fonts ./fonts
#COPY voca3000_account_key.json ./

# -------------------------
# 6. GTM 스니펫 추가 (새로운 단계)
# -------------------------
# 6-1. 커스텀 index.html 파일을 도커 컨테이너에 복사
# 이 파일은 GTM 스니펫을 포함하고 있어야 합니다.
COPY index.html /tmp/index.html

# 6-2. entrypoint.sh 스크립트 복사
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
# 윈도우의 CR-LF 줄바꿈 문자를 제거합니다.
RUN sed -i 's/\r$//' /usr/local/bin/entrypoint.sh

# 실행 권한을 부여합니다.
RUN chmod +x /usr/local/bin/entrypoint.sh

# -------------------------
# 7. 컨테이너 실행 명령
# -------------------------
EXPOSE 8080
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
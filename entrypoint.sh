#!/bin/sh
set -e
set -x

echo "--- 스크립트 실행 시작 ---"

# GTM_ID 환경 변수 확인
if [ -z "$GTM_ID" ]; then
  echo "GTM_ID 환경 변수가 설정되지 않았습니다. 앱이 GTM 없이 실행됩니다."
else
  echo "GTM_ID 환경 변수: $GTM_ID"

  # Streamlit의 정적 파일 경로를 찾습니다.
  echo "Streamlit 정적 경로를 찾고 있습니다..."
  STREAMLIT_STATIC_PATH=$(python -c "import site; import os; print(os.path.join(site.getsitepackages()[0], 'streamlit', 'static'))")
  echo "찾은 경로: $STREAMLIT_STATIC_PATH"

  # index.html 파일의 플레이스홀더를 교체합니다.
  echo "index.html 플레이스홀더 교체 중..."
  sed -i "s/{{GTM_ID}}/$GTM_ID/g" /tmp/index.html

  # 수정된 index.html을 Streamlit의 정적 경로에 복사합니다.
  echo "수정된 index.html 파일을 복사 중..."
  cp /tmp/index.html "$STREAMLIT_STATIC_PATH/index.html"
  echo "--- 복사 성공 ---"
fi

# 스트림릿 앱 실행
echo "--- Streamlit 앱을 실행합니다 ---"
streamlit run run.py --server.port=$PORT --server.address=0.0.0.0
import streamlit as st
import pandas as pd
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

# 1. 앱 타이틀
st.title("📘 영단어 시험지 생성기")

# 2. 하루 단어 수 선택 (토글 느낌 → radio)
word_count = st.radio(
    "하루에 몇 개의 단어를 외울 계획인가요?sts",
    [15, 20, 30],
    index=0
)

# 3. Day 입력
day = st.number_input("몇째 날 시험지를 만드시겠습니까?", min_value=1, step=1)

# 4. 응원 메시지 입력
message = st.text_area("자녀에게 전할 응원 메시지", "오늘도 화이팅!")

# 5. 시험지 생성 버튼
if st.button("시험지 생성하기"):
    # (엑셀 읽기 → 단어 추출 로직 들어갈 자리)
    df = pd.DataFrame({
        "번호": range(1, word_count+1),
        "단어": [f"word{i}" for i in range(1, word_count+1)],
        "뜻": [f"뜻{i}" for i in range(1, word_count+1)],
    })

    # PDF 생성
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph(f"Day {day} 영단어 시험지", styles['Title']))
    story.append(Spacer(1, 20))

    for i, row in df.iterrows():
        story.append(Paragraph(f"{row['번호']}. {row['단어']} - ___________", styles['Normal']))
        story.append(Spacer(1, 10))

    story.append(Spacer(1, 40))
    story.append(Paragraph("응원 메시지", styles['Heading2']))
    story.append(Paragraph(message, styles['Normal']))

    doc.build(story)

    buffer.seek(0)

    # 다운로드 버튼 제공
    st.download_button(
        label="📥 시험지 다운로드",
        data=buffer,
        file_name=f"day{day}_exam.pdf",
        mime="application/pdf"
    )

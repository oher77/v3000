import streamlit as st
import pandas as pd
import gspread
from google.auth.exceptions import GoogleAuthError
from io import BytesIO
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# NotoSansKR-Regular.ttf 파일을 프로젝트에 넣고 등록
pdfmetrics.registerFont(TTFont('NotoSansKRBold', './fonts/NotoSansKR-Bold.ttf'))
pdfmetrics.registerFont(TTFont('NotoSansKR', './fonts/NotoSansKR-Regular.ttf'))

KEY_FILE_PATH = './voca3000_account_key.json'

@st.cache_data
def load_data():
    try:
        gc = gspread.service_account(filename=KEY_FILE_PATH)
        worksheet = gc.open('voca_data_m').sheet1
        rows = worksheet.get_all_values()
        df = pd.DataFrame(rows[1:], columns=rows[0])
        return df
    except gspread.SpreadsheetNotFound:
        st.error("❌ 'voca_data_m'라는 이름의 Google Sheets 파일을 찾을 수 없습니다.")
    except GoogleAuthError:
        st.error("❌ Google 인증 오류: 서비스 계정 키를 확인해주세요.")
    except Exception as e:
        st.error(f"❌ 데이터 로드 오류: {e}")
    return None

# ------------------------
# 단어 추출 함수
# ------------------------
def get_exam_words(df, day, word_per_day):
    """
    df: DataFrame (단어 목록, index = 0부터 시작)
    day: 시험 Day (정수)
    word_per_day: 하루에 외울 단어 수
    """
    total_words = len(df)

    def get_day_words(d):
        if d <= 0:
            return []
        start_idx = (d - 1) * word_per_day
        end_idx = start_idx + word_per_day
        return df.iloc[start_idx:end_idx].to_dict(orient="records")

    # 1. 당일 단어
    today_words = get_day_words(day)

    # 2. 복습 Day 후보
    review_offsets = [1, 3, 7, 14, 30, 60, 120]
    review_days = [day - i for i in review_offsets if (day - i) > 0]

    # 3. 복습 단어
    review_words = []
    for d in review_days:
        review_words.extend(get_day_words(d))

    return today_words + review_words

# ------------------------
# 이중 컬럼 데이터 만들기
# ------------------------
def build_two_column_data(words):
    """2단 구성 표 데이터를 리스트로 반환"""
    data = [["번호", "단어", "뜻 쓰기", "번호", "단어", "뜻 쓰기"]]

    for i in range(0, len(words), 2):
        left = words[i]
        left_row = [i+1, left.get("표제어",""), "  "]

        if i+1 < len(words):
            right = words[i+1]
            right_row = [i+2, right.get("표제어",""), "  "]
        else:
            right_row = ["", "", ""]

        data.append(left_row + right_row)

    return data

# ------------------------
# 미리보기 마크다운 표 생성 함수
# ------------------------
def make_markdown_table(words):
    data = build_two_column_data(words)
    md = ""
    for row in data:
        md += " | ".join(str(x) for x in row) + "\n"

    return md


# ------------------------
# PDF 디자인
# ------------------------
def make_title(day: int):
    review_offsets = [1, 3, 7, 14, 30, 60, 120]
    days = [day] + [day - o for o in review_offsets if day - o > 0]
    return "Day" + ",".join(str(d) for d in days)

def make_pdf(day, words, message, filename="시험지.pdf"):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    
   # 테이블 폰트 스타일 정의
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Noto', parent=styles['Normal'], fontName='NotoSansKR'))
    styles.add(ParagraphStyle(name='NotoTitle', parent=styles['Noto'], fontName='NotoSansKRBold', fontSize=28))
    num_style = ParagraphStyle(
        name="Body",
        fontName="NotoSansKR",
        fontSize=10,
        alignment=2  # 번호 오른쪽 정렬 0=left, 1=center, 2=right
    )     

    story = []

    # 시험지 타이틀
    title_text = make_title(day)
    story.append(Paragraph(title_text, styles['NotoTitle']))
    story.append(Spacer(1, 12))

    # 응원 메시지
    if message:
        story.append(Paragraph(f"<b>응원 메시지:</b> {message}", styles['Noto']))
        story.append(Spacer(1, 20))

    # 표 데이터
    data = build_two_column_data(words)

    # 테이블 폰트 스타일
    data_with_style = [
        [
            Paragraph(str(row[0]), num_style),          # 번호 열 우측
            Paragraph(str(row[1]), styles['Noto']),     # 단어 왼쪽
            Paragraph(str(row[2]), styles['Noto']),     # 뜻 왼쪽
            Paragraph(str(row[0]), num_style),  
            Paragraph(str(row[1]), styles['Noto']),  
            Paragraph(str(row[2]), styles['Noto'])  
        ] 
        for row in data
    ]
        
    # 테이블 스타일
    table = Table(data_with_style, colWidths=[32, 100, 120, 32, 100, 120])
    table.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.25, colors.HexColor('#ced4da')),
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor('#f1f3f5')),
        ("ALIGN", (0,0), (-1,0), "CENTER"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("FONTSIZE", (0,0), (-1,-1), 10),
    ]))

    story.append(table)
    doc.build(story)
    buffer.seek(0)
    return buffer


# ------------------------
# 앱 UI Style 지정
# ------------------------
st.markdown("""
<style>
h1 { font-size: 2.25rem!important }
h2 { font-size: 1.75rem!important }
h3 { font-size: 1.25rem!important }            
</style>
""", unsafe_allow_html=True)
# ------------------------
# 앱 UI 
# ------------------------
df = load_data()

# if df is not None:
#     st.success("✅ 데이터 불러오기 성공!")
#     st.dataframe(df.head())  # 화면에 데이터 확인

# 1. 앱 타이틀
st.header("📕 교육부 필수 영단어 3000 [2022개정]")
st.header("📃 시험지 생성기")

# 2. 하루 단어 수 선택 (토글 느낌 → radio)
num_words = st.radio("하루에 몇 개의 단어를 외울 계획인가요?", [15, 20, 30])

# 3. Day 입력
day = st.number_input("Day 몇째날의 시험지를 생성할까요?", min_value=1, step=1)

# 4. 응원 메시지 입력
message = st.text_area("자녀에게 전할 응원 메시지", "오늘도 화이팅!")

words = get_exam_words(df, day, num_words)

# 5. 시험지 생성 버튼
if words:
    # 미리보기 (Markdown 표)
    st.markdown("### 📋 시험지 미리보기")
    st.markdown(make_markdown_table(words))

    # 시험지 생성 버튼
    if st.button("시험지 생성하기"):
        start_idx = (day - 1) * num_words

        pdf_buffer = make_pdf(day, words, message)

        st.download_button(
            label="📥 PDF 다운로드",
            data=pdf_buffer,
            file_name=f"day{day}_시험지.pdf",
            mime="application/pdf"
        )
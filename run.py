import streamlit as st
import pandas as pd
import gspread
import random
from google.auth.exceptions import GoogleAuthError
from io import BytesIO
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# ------------------------
# GA4 연동 스크립트 삽입
# ------------------------
GA_MEASUREMENT_ID = "G-XXXXXXX"  # 👉 실제 발급받은 ID로 교체

st.markdown(f"""
<script async src="https://www.googletagmanager.com/gtag/js?id={GA_MEASUREMENT_ID}"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){{dataLayer.push(arguments);}}
  gtag('js', new Date());
  gtag('config', '{GA_MEASUREMENT_ID}');
</script>
""", unsafe_allow_html=True)

def send_event(event_name, params=None):
    """GA4 이벤트 로깅"""
    if params is None:
        params = {}
    js = f"""
    <script>
        if (typeof gtag !== 'undefined') {{
            gtag('event', '{event_name}', {params});
        }}
    </script>
    """
    st.markdown(js, unsafe_allow_html=True)


# NotoSansKR-Regular.ttf 파일을 프로젝트에 넣고 등록
pdfmetrics.registerFont(TTFont('NotoSansKRBold', './fonts/NotoSansKR-Bold.ttf'))
pdfmetrics.registerFont(TTFont('NotoSansKRLight', './fonts/NotoSansKR-Light.ttf'))
# pdfmetrics.registerFont(TTFont('NanumGothicExtraBold', './fonts/NanumGothic-ExtraBold.ttf'))
# pdfmetrics.registerFont(TTFont('NanumGothic', './fonts/NanumGothic-Regular.ttf'))

# 초기화
if "words" not in st.session_state:
    st.session_state.words = None

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

    def get_day_words(d):
        if d <= 0:
            return []
        start_idx = (d - 1) * word_per_day
        end_idx = start_idx + word_per_day
        day_rows = df.iloc[start_idx:end_idx]  # 표제어 기준 slice

        words = []
        for _, row in day_rows.iterrows():
            # 표제어
            val = row.get("표제어")
            if val and str(val).strip():
                words.append(str(val))

            # 파생어 (쉼표로 구분된 경우)
            val = row.get("파생어")
            if val and str(val).strip():
                derivatives = [w.strip() for w in str(val).strip("()").split(",") if w.strip()]

                for w in derivatives:
                    if w.startswith("/"):
                        words.append(w.lstrip("/ "))
                    else:
                        words.append(w)

            # 쓰기
            val = row.get("쓰기")
            if val and str(val).strip():
                words.append(str(val))
        
        return words        

    review_offsets = [1, 3, 7, 14, 30, 60, 120]
    all_days = [day] + [day - i for i in review_offsets if day - i > 0]

    all_words = []
    day_word_counts = {}
    for d in all_days:
        day_words = get_day_words(d)
        all_words.extend(day_words)
        day_word_counts[d] = len(day_words)

    return all_words, day_word_counts

# ------------------------
# 이중 컬럼 데이터 만들기 함수
# ------------------------
def build_two_column_data(words):
    """2단 구성 표 데이터를 리스트로 반환"""
    data = [["번호", "단어", "뜻 쓰기", "번호.", "단어.", "뜻 쓰기."]]

    for i in range(0, len(words), 2):
        left = words[i]
        left_row = [i+1, left, "  "]

        if i+1 < len(words):
            right = words[i+1]
            right_row = [i+2, right, "  "]
        else:
            right_row = ["", "", ""]

        data.append(left_row + right_row)

    return data

# ------------------------
# 미리보기 마크다운 표 생성 함수
# ------------------------
def make_markdown_table(words):
    data = build_two_column_data(words)
    # 헤더 행 추가
    md = "| " + " | ".join(data[0]) + " |\n"
    md += "|" + " --- |" * len(data[0]) + "\n"

    # 본문 행
    for row in data[1:]:
        md += "| " + " | ".join(str(x) for x in row) + " |\n"

    return md


# ------------------------
# PDF 생성 함수
# ------------------------

def make_pdf(words, day_word_counts, message, filename="시험지.pdf"):
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=A4,
        leftMargin = 40,
        rightMargin = 40,
        topMargin = 40,
        bottomMargin = 40,
        )
    
   # 테이블 폰트 스타일 정의
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Noto', parent=styles['Normal'], fontName='NotoSansKRLight', fontSize=9, textColor=colors.HexColor('#212529')))
    styles.add(ParagraphStyle(name='NotoTitle', parent=styles['Noto'], fontName='NotoSansKRBold', fontSize=24))
    # styles.add(ParagraphStyle(name='Noto', parent=styles['Normal'], fontName='NanumGothic', fontSize=9, textColor=colors.HexColor('#212529')))
    # styles.add(ParagraphStyle(name='NotoTitle', parent=styles['Noto'], fontName='NanumGothicExtraBold', fontSize=24))
    num_style = ParagraphStyle(
        name='NumStyle',
        parent=styles['Noto'],
        alignment=2  # 번호 오른쪽 정렬 0=left, 1=center, 2=right
    )     

    story = []

    # ------------------------
    # 시험지 타이틀
    # ------------------------

    pdf_title = "Day" + ",".join(str(d) for d in day_word_counts.keys())
    story.append(Paragraph(pdf_title, styles['NotoTitle']))
    story.append(Spacer(1, 26))

    # Day별 문제 수 표시
    counts_text = " / ".join([f"day{d}: {cnt}개" for d, cnt in day_word_counts.items()])
    story.append(Paragraph(counts_text, styles['Noto']))
    story.append(Spacer(1, 10))

    # ------------------------
    # 표
    # ------------------------    
    # 표 데이터
    data = build_two_column_data(words)

    # 테이블 폰트 스타일
    data_with_style = [
        [
            Paragraph(str(row[0]), num_style),          # 번호 열 우측
            Paragraph(str(row[1]), styles['Noto']),     # 단어 왼쪽
            Paragraph(str(row[2]), styles['Noto']),     # 뜻 왼쪽
            Paragraph(str(row[3]), num_style),  
            Paragraph(str(row[4]), styles['Noto']),  
            Paragraph(str(row[5]), styles['Noto'])  
        ] 
        for row in data
    ]
        
    # 테이블 스타일
    table = Table(data_with_style, colWidths=[33, 90, 130, 34, 90, 130],hAlign='LEFT'
                #   ,rowHeights=[20]+[22]*(len(data)-1)
                  )
    table.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.25, colors.HexColor('#adb5bd')),
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor('#f1f3f5')),
        ("ALIGN", (0,0), (-1,0), "CENTER"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("FONTSIZE", (0,0), (-1,-1), 10),
        ("TOPPADDING", (0,1),(-1,-1), 4),
        ("BOTTOMPADDING", (0,1), (-1,-1), 4),
    ]))

    story.append(table)
    story.append(Spacer(1, 20))
        
    # ------------------------
    # 응원 메세지
    # ------------------------
    if message:
        story.append(Paragraph(f"{message}", styles['Noto']))


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
.button-container {
            display: flex;
            flex-wrap: wrap;
            gap: 4px;                
}            
</style>
""", unsafe_allow_html=True)
# ------------------------
# 앱 UI 
# ------------------------

# 1. 앱 타이틀
st.header("📕 교육부 필수 영단어 3000 [2022개정]")
st.header("📃 시험지 생성기")

# 2. 조건 입력 UI
num_words = st.radio("하루에 몇 개의 단어를 외울 계획인가요?", [15, 20, 30])
day = st.number_input("Day 몇째날의 시험지를 생성할까요?", min_value=1, step=1)
message = st.text_area("자녀에게 전할 응원 메시지", "오늘도 화이팅!")

df = load_data()
# if df is not None:
#     st.success("✅ 데이터 불러오기 성공!")
#     st.dataframe(df.head())  # 화면에 데이터 확인

words, day_word_counts = get_exam_words(df, day, num_words)

# 3. 버튼 UI를 한 줄에 배치
# st.container()을 사용해 버튼을 감싸고, CSS로 내부 정렬을 제어
with st.container(horizontal=True, horizontal_alignment="left"):    
    # 미리보기 버튼
    if st.button("시험지 미리보기"):
        words, day_word_counts = get_exam_words(df, day, num_words)
        random.shuffle(words)
        st.session_state.words = words
        st.session_state.day_word_counts = day_word_counts
        send_event("exam_generate", {"day": day, "num_words": num_words})

    # 셔플 버튼
    if st.session_state.words is not None:
        if st.button("셔플"):
            random.shuffle(st.session_state.words)
            send_event("shuffle_click", {"day": day})

    # PDF 다운로드 버튼
    if st.session_state.words is not None:
        pdf_buffer = make_pdf(st.session_state.words, st.session_state.day_word_counts, message)
        st.download_button(
            label="📥 PDF 다운로드",
            data=pdf_buffer,
            file_name=f"day{day}_시험지.pdf",
            mime="application/pdf"
        )
        send_event("pdf_download", {"day": day, "num_words": num_words})
        send_event("message_write", {"message":message, "length": len(message)})

# 4. 미리표기 표시
if st.session_state.words is not None:
    st.markdown("### 📋 시험지 미리보기")
    
    # 미리보기 데이터를 pandas DataFrame으로 생성
    data = build_two_column_data(st.session_state.words)
    preview_df = pd.DataFrame(data[1:], columns=data[0])
    
    # st.dataframe을 사용하여 표를 표시
    st.dataframe(preview_df, hide_index=True)
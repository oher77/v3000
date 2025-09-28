import streamlit as st
import pandas as pd
import gspread
import random
import logging
import os
import json
from google.oauth2.service_account import Credentials
from google.auth.exceptions import GoogleAuthError
from io import BytesIO
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# NotoSansKR-Regular.ttf 파일을 프로젝트에 넣고 등록
pdfmetrics.registerFont(TTFont("NotoSansKRBold", "./fonts/NotoSansKR-Bold.ttf"))
pdfmetrics.registerFont(TTFont("NotoSansKRLight", "./fonts/NotoSansKR-Light.ttf"))
# pdfmetrics.registerFont(TTFont('NanumGothicExtraBold', './fonts/NanumGothic-ExtraBold.ttf'))
# pdfmetrics.registerFont(TTFont('NanumGothic', './fonts/NanumGothic-Regular.ttf'))

# 초기화
if "words" not in st.session_state:
    st.session_state.words = None


@st.cache_data
def load_data():
    try:
        # # Sheets와 Drive API 접근에 필요한 권한 범위 정의
        # SCOPES = [
        #     "https://www.googleapis.com/auth/spreadsheets.readonly",
        #     "https://www.googleapis.com/auth/drive.readonly",
        # ]

        # # 서비스 계정 키의 JSON 내용 가져오기
        # secrets_json = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
        # if not secrets_json:
        #     st.error("❌ GOOGLE_APPLICATION_CREDENTIALS 환경 변수를 찾을 수 없습니다.")
        #     return None

        # # JSON 내용으로 자격 증명(Credentials) 객체 생성 및 권한 범위 적용
        # credentials_info = json.loads(secrets_json)
        # credentials = Credentials.from_service_account_info(
        #     credentials_info, scopes=SCOPES
        # )

        # 권한이 적용된 자격 증명으로 gspread 인증
        # gc = gspread.authorize(credentials)
        gc = gspread.service_account("voca3000_account_key.json")
        worksheet = gc.open("voca_data").sheet1
        rows = worksheet.get_all_values()
        df = pd.DataFrame(rows[1:], columns=rows[0])
        return df

    except json.JSONDecodeError as e:
        st.error(
            f"❌ JSON 파싱 오류: Secret Manager에 저장된 키 형식을 확인해주세요. ({e})"
        )
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
def get_review_days(target_day):
    offsets = [-1, -3, -7, -14, -30, -60, -120]
    review_days = [f"{target_day + offset}" for offset in offsets if target_day + offset > 0]
    return [f"{target_day}"] + review_days

def extract_day_range(df, target_day_label):
    day_row_indices = df[df["참고 사항"].astype(str).str.contains(target_day_label, na=False)].index.tolist()
    if not day_row_indices:
        return pd.DataFrame()
    start_idx = day_row_indices[0]
    next_day_idx = (
        df[df.index > start_idx]["참고 사항"].astype(str).str.contains(r"day\d+", na=False)
    )
    try:
        end_idx = next_day_idx[next_day_idx].index[0]
        return df.iloc[start_idx:end_idx]
    except IndexError:
        return df.iloc[start_idx:start_idx + 15]
def get_exam_words(df, target_day):
    review_days = get_review_days(target_day)
    all_words = []
    day_word_counts = {}

    for day in review_days:
        try:
            day_df = extract_day_range(df, day)
            day_words = []
            for _, row in day_df[['표제어', '파생어', '쓰기']].iterrows():
                base = row['표제어']
                write = row['쓰기'] if pd.notna(row['쓰기']) else None
                if pd.notna(row['파생어']):
                    derived = row['파생어'].strip("()").split(", ")
                else:
                    derived = []
                    
                # all_words.append(base)
                # all_words.extend(derived)

                # base: 표제어 + 쓰기 둘 다 사용
                if pd.notna(base):
                    day_words.append(base)
                if pd.notna(write) and write != base:
                    day_words.append(write)

                day_words.extend([w for w in derived if pd.notna(w)])

            # 누적 리스트 및 개별 카운트 기록
            all_words.extend(day_words)
            day_word_counts[day] = len(day_words)
                
        except Exception:
            continue

    # 중복 제거
    seen = set()
    unique_words = []
    for word in all_words:
        if word not in seen:
            seen.add(word)
            unique_words.append(word)

    title_days = ",".join(sorted([d.replace("day", "") for d in review_days], key=int, reverse=True))
    return unique_words, day_word_counts

# ------------------------
# 이중 컬럼 데이터 만들기 함수
# ------------------------
def build_two_column_data(words):
    """2단 구성 표 데이터를 리스트로 반환"""
    data = [["번호", "단어", "뜻 쓰기", "번호.", "단어.", "뜻 쓰기."]]

    for i in range(0, len(words), 2):
        left = words[i]
        left_row = [i + 1, left, "  "]

        if i + 1 < len(words):
            right = words[i + 1]
            right_row = [i + 2, right, "  "]
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

# -------------------------------------------------------------------
# 사용자 행동을 GCP Cloud Logging에 기록하는 함수
# -------------------------------------------------------------------
# GCP Cloud Logging이 로그를 안정적으로 수집하도록 로깅 레벨 설정
logging.basicConfig(level=logging.INFO)

def track_user_action(event_name: str, **event_params):
    """
    사용자 행동을 일관된 JSON 형식으로 로깅하여 GCP Cloud Logging에 저장합니다.
    (timestamp는 GCP가 자동으로 추가합니다.)
    """
    log_data = {
        "event": event_name, 
        "level": "INFO",
        "user_params": event_params
    }
    
    # 이 로그 메시지는 GCP Cloud Logging에 자동으로 수집됩니다.
    logging.info(f"USER_ACTION_TRACKING: {log_data}")

# ------------------------
# PDF 생성 함수
# ------------------------

def make_pdf(words, day_word_counts, message):
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=40,
        rightMargin=40,
        topMargin=40,
        bottomMargin=40,
    )

    # 테이블 폰트 스타일 정의
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="Noto",
            parent=styles["Normal"],
            fontName="NotoSansKRLight",
            fontSize=9,
            textColor=colors.HexColor("#212529"),
        )
    )
    styles.add(
        ParagraphStyle(
            name="NotoTitle",
            parent=styles["Noto"],
            fontName="NotoSansKRBold",
            fontSize=24,
        )
    )
    # styles.add(ParagraphStyle(name='Noto', parent=styles['Normal'], fontName='NanumGothic', fontSize=9, textColor=colors.HexColor('#212529')))
    # styles.add(ParagraphStyle(name='NotoTitle', parent=styles['Noto'], fontName='NanumGothicExtraBold', fontSize=24))
    num_style = ParagraphStyle(
        name="NumStyle",
        parent=styles["Noto"],
        alignment=2,  # 번호 오른쪽 정렬 0=left, 1=center, 2=right
    )

    story = []

    # ------------------------
    # 시험지 타이틀
    # ------------------------

    pdf_title = "Day" + ",".join(str(d) for d in day_word_counts.keys())
    story.append(Paragraph(pdf_title, styles["NotoTitle"]))
    story.append(Spacer(1, 26))

    # # Day별 문제 수 표시
    # counts_text = " / ".join([f"day{d}: {cnt}개" for d, cnt in day_word_counts.items()])
    # story.append(Paragraph(counts_text, styles["Noto"]))
    # story.append(Spacer(1, 10))

    # ------------------------
    # 표
    # ------------------------
    # 표 데이터
    data = build_two_column_data(words)

    # 테이블 폰트 스타일
    data_with_style = [
        [
            Paragraph(str(row[0]), num_style),  # 번호 열 우측
            Paragraph(str(row[1]), styles["Noto"]),  # 단어 왼쪽
            Paragraph(str(row[2]), styles["Noto"]),  # 뜻 왼쪽
            Paragraph(str(row[3]), num_style),
            Paragraph(str(row[4]), styles["Noto"]),
            Paragraph(str(row[5]), styles["Noto"]),
        ]
        for row in data
    ]

    # 테이블 스타일
    table = Table(
        data_with_style,
        colWidths=[33, 90, 130, 34, 90, 130],
        hAlign="LEFT",
        #   ,rowHeights=[20]+[22]*(len(data)-1)
    )
    table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#adb5bd")),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f3f5")),
                ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 1), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 1), (-1, -1), 4),
            ]
        )
    )

    story.append(table)
    story.append(Spacer(1, 20))

    # ------------------------
    # 응원 메세지
    # ------------------------
    if message:
        story.append(Paragraph(f"{message}", styles["Noto"]))

    doc.build(story)
    buffer.seek(0)
    return buffer

# ------------------------
# 앱 UI Style 지정
# ------------------------
st.markdown(
    """
<style>
h1 { font-size: 2.25rem!important }
h2 { font-size: 1.75rem!important }
h3 { font-size: 1.25rem!important }
.p-it {
    color: #805905; 
    font-size: 0.87rem!important; 
    background: #fcf3d4;
    padding:8px 12px; 
    border-radius: 0.5rem;            
</style>
""",
    unsafe_allow_html=True,
)
# ------------------------
# 앱 UI
# ------------------------

# <head> <title> 지정
st.set_page_config(page_title="교육부 필수영단어3000[2022개ㅋ정]")

# 1. 앱 타이틀
st.header("🧠 뇌쏙쏙 voca3000")
st.header("📃 오늘의 최종 인출")

target_day = st.number_input("Day 몇째날의 시험지를 생성할까요?", min_value=1, step=1)
# 최대 글자 수 설정
MAX_CHARS = 250
message = st.text_area("하연이에게.", "You are braver than you believe, stronger than you seem and smarter than you think.🐱", max_chars=MAX_CHARS)
# st.markdown(f"<p style='text-align:right; font-size:0.9rem;margin-top:-10px'>글자 수: {len(message)}/{MAX_CHARS}</p>",unsafe_allow_html=True)
df = load_data()
# if df is not None:
#     st.success("✅ 데이터 불러오기 성공!")
#     st.dataframe(df.head())  # 화면에 데이터 확인

words, day_word_counts = get_exam_words(df, target_day)

# 3. 버튼 UI를 한 줄에 배치
# st.container()을 사용해 버튼을 감싸고, CSS로 내부 정렬을 제어
with st.container(horizontal=True, horizontal_alignment="left"):
    # 미리보기 버튼
    if st.button("시험지 미리보기"):
        track_user_action(
                event_name="exam_preview_generated",
                day=target_day,
                message_length=len(message)
        )
        words, day_word_counts = get_exam_words(df, target_day)
        random.shuffle(words)
        st.session_state.words = words
        st.session_state.day_word_counts = day_word_counts
 
    # 셔플 버튼
    if st.session_state.words is not None:
        if st.button("셔플"):
            track_user_action(
                event_name="exam_shuffled",
                day=target_day
            )            
            random.shuffle(st.session_state.words)

    # PDF 다운로드 버튼
    if st.session_state.words is not None:
        pdf_buffer = make_pdf(st.session_state.words, st.session_state.day_word_counts, message)
        st.download_button(
            label="📥 PDF 다운로드",
            data=pdf_buffer,
            file_name=f"day{target_day}_시험지.pdf",
            mime="application/pdf",
        )
# 4. 미리표기 표시
if st.session_state.words is not None:
    pdf_title = "Day" + ",".join(str(d) for d in st.session_state.day_word_counts.keys())
    st.markdown("### 📋 시험지 미리보기")
    st.markdown(f"### {pdf_title}")
    # 미리보기 데이터를 pandas DataFrame으로 생성
    data = build_two_column_data(st.session_state.words)
    preview_df = pd.DataFrame(data[1:], columns=data[0])

    # st.dataframe을 사용하여 표를 표시
    st.dataframe(preview_df, hide_index=True)

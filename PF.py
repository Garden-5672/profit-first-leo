import streamlit as st
import pandas as pd
from datetime import datetime
import io
import re

# 구글 연동 라이브러리
import gspread
from google.oauth2.service_account import Credentials

# 1. 페이지 설정
st.set_page_config(
    page_title="Profit First Dashboard", 
    layout="wide",
    page_icon="🌸"
)

# ----------------- [보안] 구매자 전용 비밀번호 잠금 -----------------
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state.password_correct = False
    if st.session_state.password_correct:
        return True

    st.markdown("""
        <style>
        .password-container {
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 40px 20px;
        }
        .password-box {
            background: linear-gradient(135deg, #FFF6F7 0%, #FFF0F2 100%);
            padding: 40px;
            border-radius: 20px;
            border: 2px solid #FFCCD5;
            box-shadow: 0px 10px 25px rgba(255, 183, 197, 0.3);
            max-width: 480px;
            width: 100%;
            text-align: center;
            font-family: 'Malgun Gothic', sans-serif;
        }
        .password-box h2 {
            color: #D36B8C !important;
            margin-bottom: 5px !important;
        }
        .password-box p {
            color: #7F5F68;
            font-size: 0.95rem;
            margin-bottom: 25px;
        }
        /* 스트림릿 기본 입력창 포커스 스타일 보완 */
        div[data-baseweb="input"] {
            border-radius: 10px !important;
        }
        /* 입장 버튼 커스텀 스타일 및 호버 효과 */
        .stButton>button.css-edgvbq, .stButton>button {
            width: 100% !important;
            background: linear-gradient(90deg, #E28F9D 0%, #F1A7B4 100%) !important;
            color: white !important;
            border-radius: 12px !important;
            border: none !important;
            font-weight: bold !important;
            padding: 12px 0px !important;
            font-size: 1.05rem !important;
            box-shadow: 0px 4px 10px rgba(226, 143, 157, 0.3) !important;
            transition: all 0.3s ease !important;
        }
        .stButton>button:hover {
            transform: translateY(-2px) !important;
            box-shadow: 0px 6px 15px rgba(226, 143, 157, 0.5) !important;
            opacity: 0.9;
        }
        </style>
    """, unsafe_allow_html=True)

    # UI 렌더링
    st.markdown("<div class='password-container'>", unsafe_allow_html=True)
    st.markdown("<div class='password-box'>", unsafe_allow_html=True)
    st.markdown("<h2>🐶 비밀번호를 입력하시츄! 🌸</h2>", unsafe_allow_html=True)
    st.markdown("<p>본 대시보드는 <b>구매자 전용</b> 독점 대시보드입니다.</p>", unsafe_allow_html=True)

    password = st.text_input("🔑 열쇠 비밀번호 입력", type="password", key="pwd_input", label_visibility="collapsed")
    st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
    
    SECRET_PASSWORD = "leo-1234567"
    
    if st.button("🌸 레오의 정원 입장하기"):
        if password == SECRET_PASSWORD:
            st.session_state.password_correct = True
            st.rerun()
        else:
            st.error("앗! 비밀번호가 틀렸습니다. 다시 입력해 주시츄! 😢")
            
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
    return False

if not check_password():
    st.stop()
# -------------------------------------------------------------------------

# ⚙️ 구글 스프레드시트 연동 함수 (캐싱 적용으로 연결 최적화)
@st.cache_resource(ttl=3600)  # 1시간 동안 커넥션 캐싱하여 속도 향상
def get_google_client():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    
    # 💡 Secrets에서 구글 키 정보를 복사해옵니다.
    creds_dict = dict(st.secrets["google_creds"])
    
    # 🛡️ 텍스트로 박힌 \\n 기호를 파이썬이 인식하는 진짜 엔터(줄바꿈)로 강제 치환합니다!
    creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
    
    # 최신 공식 라이브러리로 인증을 처리합니다.
    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    
    return gspread.authorize(creds)
    
def get_google_sheets(sheet_url):
    try:
        client = get_google_client()
        sheet_id_match = re.search(r"/d/([a-zA-Z0-9-_]+)", sheet_url)
        if not sheet_id_match:
            return None, None, "올바른 구글 시트 URL 형식이 아닙니다시츄!"
            
        sheet_id = sheet_id_match.group(1)
        spreadsheet = client.open_by_key(sheet_id)
        
        sheet_distribution = spreadsheet.worksheet("실시간분배")
        sheet_assessment = spreadsheet.worksheet("즉각평가")
        
        return sheet_distribution, sheet_assessment, "OK"
    except gspread.exceptions.SpreadsheetNotFound:
        return None, None, "시트를 찾을 수 없습니다. 레오 이메일을 편집자로 초대했는지 확인해 주세요!"
    except gspread.exceptions.WorksheetNotFound:
        return None, None, "시트 안에 '실시간분배' 또는 '즉각평가' 탭이 없습니다시츄!"
    except Exception as e:
        return None, None, f"연결 실패: {e}"

# 고정된 통장 이름 정의
NAME_INCOME = "매출 통장 (Income)"
NAME_PROFIT = "수익 통장 (Profit)"
NAME_OWNER = "오너 보상 통장 (Owner's Comp)"
NAME_TAX = "세금 통장 (Tax)"
NAME_OPEX = "운영비 통장 (OPEX)"

# 스타일 및 디자인
st.markdown("""
    <style>
    .main { background-color: #FFF9F9; }
    h1 { color: #D36B8C !important; font-family: 'Malgun Gothic', sans-serif; }
    h2, h3 { color: #E28F9D !important; }
    .shih-tzu-box {
        background-color: #FFF0F2;
        border-left: 5px solid #FFB7C5;
        padding: 20px;
        border-radius: 12px;
        margin-bottom: 25px;
    }
    .assessment-card {
        padding: 18px;
        border-radius: 10px;
        margin-bottom: 12px;
        color: #333333;
        box-shadow: 1px 1px 6px rgba(0,0,0,0.05);
    }
    .stButton>button {
        background-color: #E28F9D !important;
        color: white !important;
        border-radius: 20px !important;
        border: none !important;
        font-weight: bold !important;
        padding: 10px 24px !important;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown(f"""
<div class='shih-tzu-box'>
    <span style='font-size: 3rem; float: left; margin-right: 15px;'>🐶🌸</span>
    <h2 style='margin: 0; padding-top: 5px; color: #D36B8C;'>레오와 함께하는 꽃길만 걷는 Profit First</h2>
    <p style='margin: 5px 0 0 0; color: #7F5F68; font-size: 1.05rem;'>
        <b>"대표님! 12개월간의 재무 데이터를 바탕으로 비즈니스의 건강 점검(즉각 평가)을 받아보시츄!"</b>
    </p>
    <div style='clear: both;'></div>
</div>
""", unsafe_allow_html=True)

# 2. 사이드바 설정
st.sidebar.markdown("<h2 style='color:#D36B8C;'>🐾 레오의 정원 설정</h2>", unsafe_allow_html=True)

st.sidebar.markdown("<h4 style='color:#E28F9D;'>🔗 내 구글 시트 연동</h4>", unsafe_allow_html=True)
user_sheet_url = st.sidebar.text_input(
    "개인 구글 시트 URL 주소를 입력해 주시츄", 
    placeholder="https://docs.google.com/spreadsheets/d/...",
    key="user_url"
)

ws_dist, ws_assess = None, None
if user_sheet_url:
    ws_dist, ws_assess, status_msg = get_google_sheets(user_sheet_url)
    if status_msg == "OK":
        st.sidebar.success("✅ 구글 시트 정원 연결 성공!")
    else:
        st.sidebar.error(f"⚠️ {status_msg}")
else:
    st.sidebar.warning("📢 가이드 2단계를 완료한 후 대표님의 구글 시트 주소를 붙여넣어 주시츄!")

st.sidebar.markdown("---")
total_revenue = st.sidebar.number_input("🌸 이번 분배할 총 매출액 (원)", min_value=0, value=10000000, step=100000)

st.sidebar.markdown("---")
st.sidebar.markdown("<h4 style='color:#E28F9D;'>💐 통장별 꽃밭 비율 (%)</h4>", unsafe_allow_html=True)
p_profit = st.sidebar.slider(f"🌸 {NAME_PROFIT}", 0, 100, 5)
p_owner = st.sidebar.slider(f"🦴 {NAME_OWNER}", 0, 100, 50)
p_tax = st.sidebar.slider(f"📝 {NAME_TAX}", 0, 100, 15)
p_opex = st.sidebar.slider(f"⚙️ {NAME_OPEX}", 0, 100, 30)

total_percentage = p_profit + p_owner + p_tax + p_opex
if total_percentage != 100:
    st.sidebar.error(f"⚠️ 총합이 {total_percentage}%입니다. 100%로 맞춰주세요!")
else:
    st.sidebar.success("✅ 완벽한 100% 꽃밭 비율 완성!")

st.sidebar.markdown("---")
day_1 = st.sidebar.number_input("첫 번째 분배일", min_value=1, max_value=31, value=10)
day_2 = st.sidebar.number_input("두 번째 분배일", min_value=1, max_value=31, value=25)

calc_profit = total_revenue * (p_profit / 100)
calc_owner = total_revenue * (p_owner / 100)
calc_tax = total_revenue * (p_tax / 100)
calc_opex = total_revenue * (p_opex / 100)

current_date = datetime.now().strftime("%Y-%m-%d")

# 3. 메인 화면 상단: 이체 설계서 및 기록
col_left, col_right = st.columns([3, 2])

with col_left:
    st.subheader(f"📅 기준일: {current_date} | 🌸 고정 분배일: 매월 {day_1}일, {day_2}일")
    df_data = [
        {"통장 구분 🌸": f"1. {NAME_INCOME}", "꽃밭 비율 (%)": "100%", "이체 금액 (원)": f"{int(total_revenue):,}", "꽃밭의 역할": "모든 매출이 피어나는 출발지"},
        {"통장 구분 🌸": f"2. {NAME_PROFIT}", "꽃밭 비율 (%)": f"{p_profit}%", "이체 금액 (원)": f"{int(calc_profit):,}", "꽃밭의 역할": "대표님이 보관할 비상금 꽃밭"},
        {"통장 구분 🌸": f"3. {NAME_OWNER}", "꽃밭 비율 (%)": f"{p_owner}%", "이체 금액 (원)": f"{int(calc_owner):,}", "꽃밭의 역할": "대표님을 위한 정당한 영양가 보상"},
        {"통장 구분 🌸": f"4. {NAME_TAX}", "꽃밭 비율 (%)": f"{p_tax}%", "이체 금액 (원)": f"{int(calc_tax):,}", "꽃밭의 역할": "추후 나라에 바칠 세금 항아리"},
        {"통장 구분 🌸": f"5. {NAME_OPEX}", "꽃밭 비율 (%)": f"{p_opex}%", "이체 금액 (원)": f"{int(calc_opex):,}", "꽃밭의 역할": "남은 씨앗으로 가꾸는 알뜰 운영 정원"}
    ]
    st.table(pd.DataFrame(df_data))

with col_right:
    st.markdown("<div style='background-color:#FFF5F7; border: 2px dashed #FFCCD5; padding:20px; border-radius:10px;'>", unsafe_allow_html=True)
    st.markdown("### 💾 실시간 분배 구글 시트에 기록")
    memo = st.text_input("📝 분배 메모", value=f"{current_date} 분배")
    
    if st.button("🌸 이체 완료 및 구글 시트 저장"):
        if ws_dist is None:
            st.error("구글 시트 주소가 올바르게 연결되지 않았시츄!")
        elif total_percentage != 100:
            st.error("비율 합이 100%가 아니면 기록할 수 없으시츄!")
        elif total_revenue <= 0:
            st.error("매출액이 0원보다 커야 기록할 수 있시츄!")
        else:
            ws_dist.append_row([
                current_date, 
                f"{int(total_revenue):,}", 
                f"{int(calc_profit):,}", 
                f"{int(calc_owner):,}", 
                f"{int(calc_tax):,}", 
                f"{int(calc_opex):,}", 
                memo
            ])
            st.toast("🎉 '실시간분배' 탭에 저장 완료되었시츄! 🐾")
    st.markdown("</div>", unsafe_allow_html=True)

# 4. 실시간 이체 가이드 매트릭
st.markdown("---")
st.markdown(f"### 💡 레오의 실시간 이체 가이드 (목표 금액)")
col1, col2, col3, col4 = st.columns(4)
with col1: st.metric(label=f"{NAME_PROFIT} 🌸", value=f"{int(calc_profit):,} 원", delta=f"{p_profit}%")
with col2: st.metric(label=f"{NAME_OWNER} 🦴", value=f"{int(calc_owner):,} 원", delta=f"{p_owner}%")
with col3: st.metric(label=f"{NAME_TAX} 📝", value=f"{int(calc_tax):,} 원", delta=f"{p_tax}%")
with col4: st.metric(label=f"{NAME_OPEX} ⚙️", value=f"{int(calc_opex):,} 원", delta=f"{p_opex}%")


# -----------------------------------------------------------------------------
# 5. ✨ 레오의 즉각 평가 (Instant Assessment) 기능 영역
# -----------------------------------------------------------------------------
st.markdown("---")
st.markdown("### 🔍 레오의 12개월 즉각 평가 (Instant Assessment)")
st.write("지난 12개월 동안의 비즈니스 실제 재무 성과를 바탕으로 **목표 대비 과부족 상태**를 진단해 드립니다.")

tab_col1, tab_col2 = st.columns(2)

with tab_col1:
    st.markdown("#### 📊 지난 12개월 실제 재무 데이터 (A열)")
    a1_total_rev = st.number_input("A1. 12개월 간의 총 매출액 (원)", min_value=0, value=120000000, step=1000000)
    a2_material_cost = st.number_input("A2. 12개월 간의 재료비/하도급비 등 (원)", min_value=0, value=20000000, step=1000000)
    
    a3_real_rev = a1_total_rev - a2_material_cost
    st.info(f"💡 **A3. 12개월 간의 실질 순매출 (A1 - A2)**: {a3_real_rev:,} 원")
    
    a4_profit = st.number_input("A4. 12개월 간의 실제 수익 통장 적립금 (원)", min_value=0, value=5000000, step=100000)
    a5_owner_comp = st.number_input("A5. 12개월 간의 실제 대표님 급여/보상 (원)", min_value=0, value=35000000, step=500000)
    a6_tax = st.number_input("A6. 12개월 간의 실제 납부한 세금 (원)", min_value=0, value=10000000, step=500000)
    a7_opex = st.number_input("A7. 12개월 간의 실제 사용한 비용/운영비 (원)", min_value=0, value=50000000, step=1000000)
    
    actual_sum = a4_profit + a5_owner_comp + a6_tax + a7_opex
    if actual_sum != a3_real_rev:
        st.warning(f"⚠️ A4~A7의 합계({actual_sum:,}원)가 순매출(A3: {a3_real_rev:,}원)과 일치하지 않습니다.")

with tab_col2:
    st.markdown("#### 🎯 목표 배분 비율 설정 (B열)")
    b4_ratio = st.slider("B4. 수익(Profit) 통장 목표 비율 (%)", 0, 100, 10, key="b4")
    b5_ratio = st.slider("B5. 오너 보상(Owner's Comp) 목표 비율 (%)", 0, 100, 45, key="b5")
    b6_ratio = st.slider("B6. 세금(Tax) 목표 비율 (%)", 0, 100, 15, key="b6")
    b7_ratio = st.slider("B7. 운영비(OPEX) 목표 비율 (%)", 0, 100, 30, key="b7")
    
    ratio_sum = b4_ratio + b5_ratio + b6_ratio + b7_ratio
    if ratio_sum != 100:
        st.error(f"⚠️ 목표 비율의 합이 {ratio_sum}%입니다. 100%가 되도록 맞춰주시츄!")
    else:
        st.success("✅ 완벽한 100% 평가 비율 세팅 완료!")

if ratio_sum == 100:
    st.markdown("---")
    st.markdown("### 🐾 레오의 12개월 즉각 평가 진단표")
    
    c4_target_profit = a3_real_rev * (b4_ratio / 100)
    c5_target_owner = a3_real_rev * (b5_ratio / 100)
    c6_target_tax = a3_real_rev * (b6_ratio / 100)
    c7_target_opex = a3_real_rev * (b7_ratio / 100)
    
    d4_diff = a4_profit - c4_target_profit
    d5_diff = a5_owner_comp - c5_target_owner
    d6_diff = a6_tax - c6_target_tax
    d7_diff = a7_opex - c7_target_opex
    
    eval_data = [
        {"category": "수익 (Profit)", "actual": a4_profit, "ratio": b4_ratio, "target": c4_target_profit, "diff": d4_diff, "is_opex": False},
        {"category": "오너 보상 (Owner's Comp)", "actual": a5_owner_comp, "ratio": b5_ratio, "target": c5_target_owner, "diff": d5_diff, "is_opex": False},
        {"category": "세금 (Tax)", "actual": a6_tax, "ratio": b6_ratio, "target": c6_target_tax, "diff": d6_diff, "is_opex": False},
        {"category": "운영비 (OPEX)", "actual": a7_opex, "ratio": b7_ratio, "target": c7_target_opex, "diff": d7_diff, "is_opex": True}
    ]
    
    col_eval1, col_eval2 = st.columns(2)
    
    for idx, item in enumerate(eval_data):
        if item["diff"] < 0:
            action_status = "증가"
            if item["is_opex"]:
                card_color = "#D4EDDA"
                border_color = "#C3E6CB"
                description = f"🎉 **훌륭합니다시츄!** 운영비가 목표보다 **{int(abs(item['diff'])):,}원** 절감되었습니다."
            else:
                card_color = "#FFF3CD"
                border_color = "#FFEEBA"
                description = f"⚠️ **조정 제안 ({action_status})**: 해당 통장이 목표보다 **{int(abs(item['diff'])):,}원** 부족합니다. 배분율을 **{action_status}**시켜야 합니다시츄!"
        else:
            action_status = "감소"
            if item["is_opex"]:
                card_color = "#FFD2D2"
                border_color = "#FF8080"
                description = f"🚨 **과다 지출 ({action_status} 필요)**: 운영비가 목표보다 **{int(item['diff']):,}원** 초과 사용되었습니다!"
            else:
                card_color = "#D4EDDA"
                border_color = "#C3E6CB"
                description = f"✅ **안전**: 목표보다 **{int(item['diff']):,}원** 더 든든하게 비축되어 있어 여유롭습니다시츄!"

        with (col_eval1 if idx % 2 == 0 else col_eval2):
            st.markdown(f"""
            <div class="assessment-card" style="background-color: {card_color}; border: 1px solid {border_color};">
                <h4 style="margin: 0 0 8px 0; color: #4A1E27;">{item['category']} (목표비율: {item['ratio']}%)</h4>
                <p style="margin: 0; font-size: 0.95rem; line-height: 1.5;">
                    📍 <b>12개월 실제 (A):</b> {int(item['actual']):,} 원<br>
                    📍 <b>원칙 목표 (C):</b> {int(item['target']):,} 원<br>
                    📍 <b>차이 금액 (D):</b> {int(item['diff']):+,} 원<br>
                    ✨ <b>레오의 피드백:</b> {description}
                </p>
            </div>
            """, unsafe_allow_html=True)
            
    st.markdown("#### 📋 12개월 즉각 평가 요약표")
    summary_rows = []
    for item in eval_data:
        action = "증가 필요" if item["diff"] < 0 else "감소/통제 필요"
        summary_rows.append({
            "구분": item["category"],
            "목표 비율 (B)": f"{item['ratio']}%",
            "실제 지출액 (A)": f"{int(item['actual']):,} 원",
            "원칙적 목표액 (C)": f"{int(item['target']):,} 원",
            "차이 (D)": f"{int(item['diff']):+,} 원",
            "처방 조치 (E)": action
        })
    st.table(pd.DataFrame(summary_rows))

    # -------------------------------------------------------------------------
    # 💾 초고속 일괄(Batch) 저장 방식으로 대폭 개선된 즉각 평가 단락
    # -------------------------------------------------------------------------
    st.markdown("<div style='background-color:#F5F9FF; border: 2px dashed #BEE3F8; padding:20px; border-radius:10px; margin-top:20px;'>", unsafe_allow_html=True)
    st.markdown("#### 💾 12개월 진단 결과 구글 시트에 기록하기")
    assess_memo = st.text_input("📝 진단 기록용 메모", placeholder="필요하시면 작성해주세요.")
    
    if st.button("🌸 즉각 평가 결과 구글 시트 저장"):
        if ws_assess is None:
            st.error("구글 시트 주소가 올바르게 연결되지 않았시츄!")
        else:
            try:
                rows_to_append = []
                for item in eval_data:
                    action = "증가 필요" if item["diff"] < 0 else "감소/통제 필요"
                    rows_to_append.append([
                        current_date, 
                        f"{int(a1_total_rev):,}", 
                        f"{int(a2_material_cost):,}", 
                        f"{int(a3_real_rev):,}", 
                        item['category'], 
                        f"{int(item['actual']):,}", 
                        f"{item['ratio']}%", 
                        f"{int(item['target']):,}", 
                        f"{int(item['diff']):+,}", 
                        f"{assess_memo} ({action})"
                    ])
                
                # 초고속 1회 대량 이체API 호출
                ws_assess.append_rows(rows_to_append)
                
                # 🎉 새로고침 에러를 원천 차단하기 위해 리프레시 없는 toast 메시지 사용
                st.toast("🎉 '즉각평가' 탭에 1초 만에 진단 데이터 누적이 완료되었시츄! 🐾")
            except Exception as save_err:
                st.error(f"⚠️ 저장 실패시츄: {save_err}")
                
    st.markdown("</div>", unsafe_allow_html=True)

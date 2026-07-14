import sqlite3
import pandas as pd
import streamlit as st
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import yeta_utils
import math
import os
import datetime
import hashlib
import string
import random
import re
import smtplib
import time
import base64
import json
import gspread
from google.oauth2.service_account import Credentials
from email.mime.text import MIMEText
import signup_agreement

import html
from yeta_db import (
    hash_password, generate_temp_password, check_login, change_user_password,
    upgrade_user_password_to_hash, get_gspread_client, run_gspread_with_retry,
    get_cached_visit_logs, get_event_settings, sync_db_from_sheets,
    get_all_users, delete_user, add_user, log_to_sheets, restore_from_deleted_sheet,
    update_user_full_info, get_db_connection
)
from yeta_email import (
    send_tax_invoice_request_email, send_password_recovery_email, send_approval_email
)
from yeta_payment import (
    get_quotation_html, get_yeta_login_redirect_html, get_yeta_portone_payment_html,
    get_yeta_portone_custom_services_html
)

# Helper function for Korean translation fallback
# --- AUTH & DB UTILITIES ---




# --- MISSING HELPERS ADDED ---
def num_to_kor(num):
    units = ["", "십", "백", "천"]
    g_units = ["", "만", "억", "조"]
    digits = ["", "일", "이", "삼", "사", "오", "육", "칠", "팔", "구"]
    
    if num == 0:
        return "영"
        
    num_str = str(num)
    length = len(num_str)
    result = []
    
    for i, char in enumerate(num_str):
        power = length - i - 1
        digit = int(char)
        if digit != 0:
            result.append(digits[digit] + units[power % 4])
        if power % 4 == 0:
            g_idx = power // 4
            if g_idx > 0:
                result.append(g_units[g_idx])
                
    kor = "".join(result)
    if kor.startswith("일십"):
        kor = kor[1:]
    return f"일금 {kor}원정"



# -----------------------------



# -----------------------------
def validate_email(email):
    return re.match(r"[^@]+@[^@]+\.[^@]+", email)

def validate_password(password):
    if len(password) < 4: return False
    has_char = re.search(r'[a-zA-Z]', password)
    has_special = re.search(r'[!@#$%^&*(),.?":{}|<>]', password)
    return has_char and has_special


# --- GOOGLE SHEETS & MEMBER MANAGEMENT ---












# --- CORE ROUTING ACTION ---
def run():
    # Inject custom CSS for sidebar tabs
    st.markdown("""
        <style>
            [data-testid="stSidebar"] .stTabs [data-baseweb="tab-list"] button[aria-selected="true"] {
                color: white !important;
            }
            [data-testid="stSidebar"] .stTabs [data-baseweb="tab-highlight"] {
                background-color: white !important;
            }
        </style>
    """, unsafe_allow_html=True)
    
    # Initialize session state variables
    if 'user_id' not in st.session_state:
        st.session_state.user_id = None
    if 'user_role' not in st.session_state:
        st.session_state.user_role = None
    if 'expiry_date' not in st.session_state:
        st.session_state.expiry_date = None
    if 'plan_type' not in st.session_state:
        st.session_state.plan_type = None
    if 'admin_mode' not in st.session_state:
        st.session_state.admin_mode = False

    # Get query parameters
    q_params = st.query_params

    # 1. Automatic Login and Token Verification (Query Param-based)
    if "login_user" in q_params and "login_token" in q_params:
        login_user_val = q_params["login_user"]
        if isinstance(login_user_val, list): login_user_val = login_user_val[0]
        login_token_val = q_params["login_token"]
        if isinstance(login_token_val, list): login_token_val = login_token_val[0]
        
        expected_token = hashlib.sha256(f"{login_user_val}:AHP_MASTER_SECURE_SALT_2026_!@#".encode()).hexdigest()
        if login_token_val == expected_token:
            conn = get_db_connection('users.db')
            c = conn.cursor()
            c.execute("SELECT role, expiry_date FROM users WHERE id=?", (login_user_val,))
            db_user = c.fetchone()
            conn.close()
            if db_user:
                role_changed = (st.session_state.user_id != login_user_val) or (st.session_state.user_role != db_user[0])
                st.session_state.user_id = login_user_val
                st.session_state.user_role = db_user[0]
                st.session_state.expiry_date = db_user[1]
                
                st.query_params.pop("login_user", None)
                st.query_params.pop("login_token", None)
                
                if role_changed:
                    st.toast("🎉 Account status updated!")
                    st.rerun()

    # 2. Inactivity Timeout Check (30 minutes)
    TIMEOUT_LIMIT = 1800
    current_time = int(time.time())
    if st.session_state.user_id is not None:
        last_act = q_params.get("last_activity")
        if isinstance(last_act, list): last_act = last_act[0]
        
        if last_act:
            try:
                elapsed = current_time - int(last_act)
                if elapsed > TIMEOUT_LIMIT:
                    st.session_state.user_id = None
                    st.session_state.user_role = None
                    st.session_state.expiry_date = None
                    st.session_state.admin_mode = False
                    st.query_params.clear()
                    st.toast(" 30분간 활동이 없어 보안을 위해 자동 로그아웃되었습니다.")
                    st.rerun()
                else:
                    st.query_params["last_activity"] = str(current_time)
            except ValueError:
                st.query_params["last_activity"] = str(current_time)

    # 3. Custom CSS Styling (Premium Corporate Theme)
    st.markdown("""
    <style>

    /* =============================================================================
       AHP 마스터 프리미엄 엔터프라이즈 UI 테마 (v3.0) - 예타 모듈용
       ============================================================================= */
    @import url("https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css");
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap');

    /* --- 글로벌 폰트 & 기본 텍스트 --- */
    html, body, [class*="css"], .stMarkdown, .stTextInput label,
    .stSelectbox label, .stRadio label, .stCheckbox label,
    div[data-testid="stSidebar"], div[data-testid="stAppViewBlockContainer"] {
        font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, system-ui, sans-serif !important;
        letter-spacing: -0.015em;
        color: #1e293b !important;
    }

    /* --- 메인 배경색 흰색으로 강제 설정 --- */
    .stApp, 
    .stApp > header,
    .main,
    [data-testid="stAppViewContainer"], 
    [data-testid="stAppViewBlockContainer"], 
    [data-testid="stHeader"], 
    .block-container {
        background-color: #ffffff !important;
        background: #ffffff !important;
    }

    /* --- 메인 제목 스타일링 (전문적이고 차분하게) --- */
    h1 {
        font-weight: 700 !important;
        font-size: 1.6rem !important;
        color: #0f172a !important;
        letter-spacing: -0.02em !important;
        border-bottom: none !important;
        padding-bottom: 0.5rem !important;
        margin-bottom: 1.5rem !important;
        margin-top: 0 !important;
        padding-top: 0 !important;
    }
    h2 {
        font-weight: 600 !important;
        font-size: 1.3rem !important;
        color: #1e293b !important;
        letter-spacing: -0.01em !important;
        margin-bottom: 1rem !important;
    }
    h3 {
        font-weight: 600 !important;
        font-size: 1.15rem !important;
        color: #1e293b !important;
        letter-spacing: -0.01em !important;
        margin-top: 2.5rem !important;
        margin-bottom: 0.25rem !important;
    }
    h4 {
        font-weight: 600 !important;
        font-size: 1.05rem !important;
        color: #1e293b !important;
        letter-spacing: -0.01em !important;
        margin-top: 2rem !important;
        margin-bottom: 0.25rem !important;
    }
    h5, h6 {
        font-weight: 600 !important;
        font-size: 0.95rem !important;
        color: #334155 !important;
        letter-spacing: -0.01em !important;
        margin-bottom: 0.5rem !important;
    }

    /* --- 안내창(Alert/Info Box) 및 본문 폰트 크기 일관성 유지 --- */
    div[data-testid="stAlert"] p,
    div[data-testid="stAlert"] div,
    div[data-testid="stMarkdownContainer"] p,
    div[data-testid="stMarkdownContainer"] li {
        font-size: 0.95rem !important;
        line-height: 1.6 !important;
    }

    /* --- 경고창/안내창(Alert/Info Box) 패널 스타일로 단정하게 통일 --- */
    div[data-testid="stAlert"] {
        background-color: #ffffff !important; 
        border: 1px solid #e2e8f0 !important; 
        border-radius: 8px !important;
    }

    div[data-testid="stAlert"] > div {
        border-left: none !important; 
        background-color: transparent !important;
        padding-top: 1.5rem !important;
        padding-bottom: 1.5rem !important;
    }

    div[data-testid="stAlert"] div[data-testid="stMarkdownContainer"] > p:first-child {
        margin-top: 0 !important; 
    }
    div[data-testid="stAlert"] div[data-testid="stMarkdownContainer"] > p:last-child {
        margin-bottom: 0 !important;
    }

    div[data-testid="stAlert"] svg {
        display: none !important; 
    }

    /* --- 스트림릿 기본 크롬 숨기기 --- */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header[data-testid="stHeader"] {
        background: #ffffff !important;
        background-color: #ffffff !important;
        border-bottom: none !important;
        box-shadow: none !important;
    }
    header[data-testid="stHeader"]::before {
        display: none !important;
        background: none !important;
        height: 0 !important;
    }

    /* --- 메인 레이아웃 폭(간격) 및 여백 최적화 --- */
    .block-container {
        padding-top: 1rem !important;
        padding-left: 3rem !important;
        padding-right: 3rem !important;
        max-width: 1600px !important; 
    }

    @media (max-width: 768px) {
        .block-container {
            padding-left: 1rem !important;
            padding-right: 1rem !important;
        }
    }

    /* --- 사이드바 프리미엄 스타일 --- */
    section[data-testid="stSidebar"] {
        background-color: #2d3436 !important;
        border-right: 1px solid #222829 !important;
    }
    section[data-testid="stSidebar"] > div:first-child {
        padding-top: 1.5rem !important;
    }
    section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
    section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] span,
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] h3,
    section[data-testid="stSidebar"] h4,
    section[data-testid="stSidebar"] h5 {
        color: #f8fafc !important;
    }
    section[data-testid="stSidebar"] input {
        color: #0f172a !important;
    }
    /* 사이드바 내의 일반 버튼 */
    section[data-testid="stSidebar"] div.stButton > button {
        background-color: #2c5282 !important;
        color: #ffffff !important;
        border: 1px solid #2c5282 !important;
    }
    section[data-testid="stSidebar"] div.stButton > button:hover {
        background-color: #3182ce !important;
        border-color: #3182ce !important;
        color: #ffffff !important;
    }
    /* 사이드바 내의 Expander */
    section[data-testid="stSidebar"] [data-testid="stExpander"] {
        background-color: rgba(255, 255, 255, 0.05) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
    }
    section[data-testid="stSidebar"] [data-testid="stExpander"] details summary p,
    section[data-testid="stSidebar"] [data-testid="stExpander"] details summary span {
        color: #ffffff !important;
    }

    /* --- 프리미엄 버튼 (기본) - 플랫/단정 --- */
    div.stButton > button {
        border-radius: 4px !important; 
        font-weight: 600 !important;
        font-size: 0.875rem !important;
        padding: 0.5rem 1rem !important;
        transition: all 0.2s ease !important;
        border: 1px solid #cbd5e1 !important;
        background: #ffffff !important;
        color: #334155 !important;
        box-shadow: none !important;
    }
    div.stButton > button:hover {
        border-color: #0f172a !important;
        background: #f1f5f9 !important;
        color: #0f172a !important;
    }

    /* --- Primary 버튼 (type=primary) --- */
    div.stButton > button[kind="primary"],
    div.stButton > button[data-testid="stBaseButton-primary"] {
        background: #1e3a8a !important; 
        color: #ffffff !important;
        border: 1px solid #1e3a8a !important;
        font-weight: 600 !important;
        box-shadow: none !important;
    }
    div.stButton > button[kind="primary"]:hover,
    div.stButton > button[data-testid="stBaseButton-primary"]:hover {
        background: #172554 !important; 
        border-color: #172554 !important;
    }

    /* --- 입력 필드 고급 스타일링 --- */
    div.stTextInput > div > div > input {
        border-radius: 4px !important;
        border: 1px solid #cbd5e1 !important;
        padding: 0.5rem 0.75rem !important;
        font-size: 0.9rem !important;
        background: #ffffff !important;
        box-shadow: none !important;
    }
    div.stTextInput > div > div > input:focus {
        border-color: #1e3a8a !important;
        box-shadow: 0 0 0 1px #1e3a8a !important;
    }

    /* --- 셀렉트박스 스타일 --- */
    div.stSelectbox > div > div {
        border-radius: 4px !important;
        border: 1px solid #cbd5e1 !important;
        background: #ffffff !important;
    }
    div.stSelectbox > div > div:hover {
        border-color: #1e3a8a !important;
    }

    /* --- 탭 고급 스타일 --- */
    div[data-baseweb="tab-list"] {
        gap: 0.2rem !important;
    }
    button[data-baseweb="tab"] {
        font-family: 'Pretendard', sans-serif !important;
        font-weight: 600 !important;
        font-size: 0.85rem !important;
        padding: 0.5rem 0.6rem !important;
        border-radius: 0 !important; 
        border-bottom: 2px solid transparent !important;
        background: transparent !important;
        color: #64748b !important;
        white-space: nowrap !important;
    }
    button[data-baseweb="tab"]:hover {
        color: #0f172a !important;
    }

    /* --- 카드형 Expander 스타일 --- */
    details[data-testid="stExpander"] {
        border: 1px solid #cbd5e1 !important;
        border-radius: 4px !important;
        background: #ffffff !important;
        box-shadow: none !important;
        margin-bottom: 0.5rem !important;
    }
    details[data-testid="stExpander"] summary {
        font-weight: 600 !important;
        color: #1e293b !important;
        background: #f8fafc !important;
        padding: 0.5rem 1rem !important;
        border-bottom: 1px solid transparent;
    }
    details[data-testid="stExpander"][open] summary {
        border-bottom: 1px solid #cbd5e1 !important;
    }

    /* --- 알림 박스 --- */
    div[data-testid="stAlert"] {
        border-radius: 4px !important;
        border: 1px solid rgba(0,0,0,0.1) !important;
        box-shadow: none !important;
    }

    /* --- 메트릭 카드 스타일 --- */
    div[data-testid="stMetric"] {
        background: #ffffff !important;
        border: 1px solid #cbd5e1 !important;
        border-left: 4px solid #1e3a8a !important; 
        border-radius: 4px !important;
        padding: 1rem !important;
        box-shadow: none !important;
    }

    /* --- 다운로드 버튼 --- */
    div.stDownloadButton > button {
        border-radius: 4px !important;
        border: 1px solid #cbd5e1 !important;
        color: #1e293b !important;
        background: #f8fafc !important;
        font-weight: 600 !important;
        min-height: 52px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        text-align: center !important;
        white-space: normal !important;
        line-height: 1.3 !important;
        box-shadow: none !important;
    }
    div.stDownloadButton > button:hover {
        background: #e2e8f0 !important;
        border-color: #94a3b8 !important;
        color: #0f172a !important;
    }

    /* --- 스크롤바 커스텀 --- */
    ::-webkit-scrollbar { width: 8px; height: 8px; }
    ::-webkit-scrollbar-track { background: #f1f5f9; }
    ::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 4px; }
    ::-webkit-scrollbar-thumb:hover { background: #94a3b8; }

    /* --- 사이드바 구분선 --- */
    section[data-testid="stSidebar"] hr {
        border: none !important;
        border-top: 1px solid #cbd5e1 !important;
        margin: 1rem 0 !important;
    }

    /* --- 링크 색상 통일 --- */
    a {
        color: #1e3a8a !important;
        text-decoration: none !important;
    }
    a:hover {
        text-decoration: underline !important;
    }

    /* 사이드바 탭 글자 크기 축소 & 여백 줄이기 & 색상 통일 */
    section[data-testid="stSidebar"] button[data-baseweb="tab"] {
        flex: 1 !important;
        justify-content: center !important;
        font-size: 0.85rem !important;
        padding: 0.5rem 0 !important;
        margin: 0 !important;
        min-height: unset !important;
        color: #cbd5e1 !important;
        background-color: transparent !important;
        border-bottom: 2px solid transparent !important;
    }
    section[data-testid="stSidebar"] button[data-baseweb="tab"][aria-selected="true"] {
        color: #ffffff !important;
        border-bottom: 2px solid #ffffff !important;
    }
    section[data-testid="stSidebar"] button[data-baseweb="tab"]:hover {
        color: #ffffff !important;
    }
    section[data-testid="stSidebar"] div[data-baseweb="tab-list"] {
        display: flex !important;
        justify-content: center !important;
        width: 100% !important;
        gap: 0.2rem !important;
    }
    section[data-testid="stSidebar"] img {
        margin-bottom: 0.25rem !important;
    }
    section[data-testid="stSidebar"] div[data-testid="stMarkdownContainer"] {
        margin-bottom: 0 !important;
    }
    section[data-testid="stSidebar"] > div:first-child {
        padding-top: 0.75rem !important;
        padding-bottom: 0.5rem !important;
    }

    /* --- 비밀번호 가시성 토글 버튼 --- */
    div[data-baseweb="input"] {
        background-color: transparent !important;
        border: none !important;
    }
    div[data-testid="stTextInput"] button,
    [data-testid="stTextInputPasswordVisibilityButton"] {
        background-color: transparent !important;
        border: none !important;
        box-shadow: none !important;
        color: #475569 !important;
    }

    /* =============================================================================
       예타 전용 커스텀 클래스
       ============================================================================= */
    .yeta-body {
        font-family: 'Pretendard', 'Outfit', sans-serif;
    }
    .yeta-header {
        background-color: #1A365D;
        color: white;
        padding: 30px;
        border-radius: 12px;
        margin-bottom: 30px;
        border-left: 6px solid #3182CE;
    }
    .yeta-header h1 {
        color: white !important;
        margin: 0 !important;
        font-size: 2.2rem !important;
        font-weight: 700 !important;
    }
    .yeta-header p {
        margin: 10px 0 0 0 !important;
        font-size: 1.1rem !important;
        color: #E2E8F0 !important;
    }
    .verdict-card {
        padding: 25px;
        border-radius: 12px;
        text-align: center;
        margin-bottom: 25px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
    }
    .verdict-pass {
        background-color: #EBF8FF;
        border: 2px solid #3182CE;
        color: #2B6CB0;
    }
    .verdict-fail {
        background-color: #FFF5F5;
        border: 2px solid #E53E3E;
        color: #C53030;
    }
    .verdict-title {
        font-size: 1.5rem;
        font-weight: 700;
        margin-bottom: 10px;
    }
    .verdict-score {
        font-size: 3rem;
        font-weight: 800;
        margin-bottom: 10px;
    }

    /* B2B Pricing Cards */
    .pricing-grid {
        display: flex;
        gap: 20px;
        flex-wrap: wrap;
        margin-bottom: 30px;
    }
    .price-card {
        flex: 1;
        min-width: 280px;
        background: white;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 25px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.02);
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }
    .price-card-tier {
        font-size: 1.2rem;
        font-weight: 700;
        color: #4A5568;
        margin-bottom: 10px;
    }
    .price-card-amount {
        font-size: 2.2rem;
        font-weight: 800;
        color: #1A202C;
        margin-bottom: 15px;
    }
    .price-card-features {
        list-style: none;
        padding-left: 0;
        margin-bottom: 25px;
    }
    .price-card-features li {
        margin-bottom: 8px;
        font-size: 0.9rem;
        color: #4A5568;
        display: flex;
        align-items: center;
    }
    .price-card-features li::before {
        content: "✓";
        color: #3182CE;
        margin-right: 8px;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

    # 4. Handle PortOne Payment Callback inside Yeta
    if "portone_paid" in q_params and "user_id" in q_params:
        user_id_param = q_params.get("user_id")
        plan_name_param = q_params.get("plan_name", "단건 분석권")
        kst_now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
        new_expiry_date = (kst_now + datetime.timedelta(days=365)).strftime("%Y-%m-%d")
        
        try:
            conn = get_db_connection('users.db')
            c = conn.cursor()
            c.execute("UPDATE users SET role='official', expiry_date=?, plan_type=? WHERE id=?", 
                      (new_expiry_date, plan_name_param, user_id_param))
            conn.commit()
            conn.close()
            
            st.success(f"🎉 {plan_name_param} 결제가 완료되어 정식 회원(예타 기능 잠금해제)으로 승급되었습니다!")
            if st.button("예타 분석 홈으로 가기"):
                st.query_params.pop("portone_paid", None)
                st.query_params.pop("user_id", None)
                st.query_params.pop("plan_name", None)
                st.rerun()
            st.stop()
        except Exception as e:
            st.error(f"결제 데이터 데이터베이스 저장 실패: {str(e)}")

    # 5. Page Header Section
    st.markdown(f"""
    <div style='margin-top: 55px;'>
        <h1>{'국가 예비타당성조사 종합평가(AHP) 솔루션'}</h1>
        <p style='color: #666; font-size: 1.05rem; margin-bottom: 30px;'>{'기획재정부 및 KDI 표준 지침을 준수하는 공공투자사업 AHP 종합 평가 모듈입니다.'}</p>
    </div>
    """, unsafe_allow_html=True)

    # 6. Sidebar Configuration (Authentication & Yeta Settings)
    with st.sidebar:
        # AHP Master Logo
        try:
            with open("ahp_master_logo_white.png", "rb") as f:
                encoded_logo = base64.b64encode(f.read()).decode()
            st.markdown(
                f'<a href="https://www.ahpmaster.com/" target="_blank">'
                f'<img src="data:image/png;base64,{encoded_logo}" style="width:100%; border-radius: 4px; display: block; margin-bottom: 10px;">'
                f'</a>',
                unsafe_allow_html=True
            )
        except:
            st.markdown(
                f'<a href="https://www.ahpmaster.com/" target="_blank" style="text-decoration: none; color: inherit;">'
                f'<h3 style="margin-top: -5px; margin-bottom: 10px;">{" AHP 마스터"}</h3>'
                f'</a>',
                unsafe_allow_html=True
            )

        # Login / Session panel
        if st.session_state.user_id is None:
            tab_login, tab_find_pw = st.tabs(["로그인", "비밀번호 찾기"])
            
            with tab_login:
                l_id = st.text_input("아이디 (이메일 주소)", key="l_id")
                l_pw = st.text_input("비밀번호 (PW)", type="password", key="l_pw")
                if st.button("로그인 실행", key="btn_login_yeta"):
                    result = check_login(l_id.strip(), l_pw)
                    if result:
                        today = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).date()
                        expiry_date_val = datetime.datetime.strptime(result[1], "%Y-%m-%d").date()
                        if today > expiry_date_val:
                            if result[0] == 'official':
                                try:
                                    update_user_full_info(l_id.strip(), None, "temp", "9999-12-31")
                                    st.session_state.user_id = l_id.strip()
                                    st.session_state.user_role = "temp"
                                    st.session_state.expiry_date = "9999-12-31"
                                    st.query_params["login_user"] = l_id.strip()
                                    st.query_params["login_token"] = hashlib.sha256(f"{l_id.strip()}:AHP_MASTER_SECURE_SALT_2026_!@#".encode()).hexdigest()
                                    st.query_params["last_activity"] = str(int(time.time()))
                                    st.toast("📅 정식 이용 기간이 만료되어 무료사용자 권한으로 자동 전환되었습니다.")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"만료 회원 자동 전환 처리 중 오류가 발생했습니다: {e}")
                            else:
                                st.error(f"❌ 이용 기간이 만료되었습니다. (만료일: {result[1]})")
                        else:
                            st.session_state.user_id = l_id.strip()
                            st.session_state.user_role = result[0]
                            st.session_state.expiry_date = result[1]
                            st.session_state.plan_type = result[2] if len(result) > 2 else None
                            st.query_params["login_user"] = l_id.strip()
                            st.query_params["login_token"] = hashlib.sha256(f"{l_id.strip()}:AHP_MASTER_SECURE_SALT_2026_!@#".encode()).hexdigest()
                            st.query_params["last_activity"] = str(int(time.time()))
                            st.success(f"환영합니다, {l_id}님!")
                            st.rerun()
                    else:
                        st.error("아이디 또는 비밀번호가 일치하지 않습니다.")
            
            with tab_find_pw:
                st.write("가입 시 사용한 이메일 주소를 입력해주세요. 이메일로 새로운 임시 비밀번호가 발송됩니다.")
                f_id = st.text_input("가입한 아이디 (이메일)", key="f_id")
                if st.button("임시 비밀번호 전송", key="btn_find_pw_yeta"):
                    if not f_id:
                        st.warning("이메일 주소를 입력해주세요.")
                    else:
                        conn = get_db_connection('users.db')
                        c = conn.cursor()
                        c.execute("SELECT id FROM users WHERE id=?", (f_id.strip(),))
                        user_exists = c.fetchone()
                        conn.close()
                        
                        if user_exists:
                            temp_pw = generate_temp_password()
                            change_user_password(f_id.strip(), temp_pw)
                            
                            if send_password_recovery_email(f_id.strip(), temp_pw):
                                st.success(f"'{f_id}'로 임시 비밀번호를 전송했습니다.\n이메일을 확인해주세요.")
                            else:
                                st.error("이메일 전송 중 오류가 발생했습니다.")
                        else:
                            st.error("등록되지 않은 아이디입니다.")
        else:
            if st.session_state.user_role == 'admin':
                role_disp = "관리자"
            elif st.session_state.user_role == 'official':
                pt = st.session_state.get('plan_type')
                role_disp = f"{'정식 사용자'} ({pt})" if pt else "정식 사용자"
            else:
                role_disp = "무료사용자"
            
            expiry_info = ""
            if st.session_state.expiry_date:
                expiry_label = "만료일: "
                expiry_info = f' | {expiry_label}{st.session_state.expiry_date}'
                
            info_html = f"""<div style="background-color: #e8f5e9; border: 1px solid #c8e6c9; border-radius: 6px; color: #2e7d32; font-weight: bold; font-size: 0.85rem; padding: 8px 10px; text-align: center; margin-bottom: 8px;">
            👤 {st.session_state.user_id} ({role_disp}{expiry_info})
            </div>"""
            st.markdown(info_html, unsafe_allow_html=True)
            
            if st.session_state.user_role == 'admin':
                btn_label = "🔧 관리자 화면 닫기" if st.session_state.get('admin_mode', False) else "🔧 관리자 화면 접속"
                if st.button(btn_label):
                    st.session_state.admin_mode = not st.session_state.admin_mode
                    st.rerun()

            with st.expander("🔐 비밀번호 변경"):
                cur_pw = st.text_input("현재 비밀번호", type="password", key="chg_cur_yeta")
                new_pw_val = st.text_input("새 비밀번호", type="password", key="chg_new_yeta")
                confirm_pw = st.text_input("새 비밀번호 확인", type="password", key="chg_conf_yeta")
                
                if st.button("비밀번호 변경", key="btn_chg_pw_yeta"):
                    if new_pw_val != confirm_pw:
                        st.error("새 비밀번호가 일치하지 않습니다.")
                    elif not validate_password(new_pw_val):
                        st.error("비밀번호는 4자 이상, 영문+특수문자를 포함해야 합니다.")
                    else:
                        chk_res = check_login(st.session_state.user_id, cur_pw)
                        if chk_res:
                            change_user_password(st.session_state.user_id, new_pw_val)
                            st.success("비밀번호가 변경되었습니다.")
                        else:
                            st.error("현재 비밀번호가 올바르지 않습니다.")

            if st.button("로그아웃", key="btn_logout_yeta"):
                st.session_state.user_id = None
                st.session_state.user_role = None
                st.session_state.expiry_date = None
                st.session_state.plan_type = None
                st.session_state.admin_mode = False
                st.query_params.pop("login_user", None)
                st.query_params.pop("login_token", None)
                st.rerun()

            with st.expander("📄 견적서 출력"):
                q_client = st.text_input("의뢰기관명 (수신)", placeholder="예: (주)에이치피테크", key="q_client_yeta")
                q_project = st.text_input("과제명 (프로젝트명)", placeholder="예: 예타 가중치 평가 분석", key="q_project_yeta")
                
                q_tier = st.selectbox(
                    "서비스 구분 (요금제)",
                    options=[
                        ("월간 이용권 (300,000원)", 300000, "월간 이용권"),
                        ("연간 이용권 (2,800,000원)", 2800000, "연간 이용권")
                    ],
                    format_func=lambda x: x[0],
                    key="q_tier_select_yeta"
                )
                
                clean_client = q_client.strip()
                clean_project = q_project.strip()
                
                if clean_client and clean_project:
                    plan_label, amount, plan_name = q_tier
                    q_html = get_quotation_html(clean_client, clean_project, amount, plan_name)
                    
                    import json
                    escaped_html = json.dumps(q_html)
                    
                    button_iframe = f"""
                    <script src="https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.10.1/html2pdf.bundle.min.js"></script>
                    <style>

                        .btn {{
                            width: 100%;
                            height: 38px;
                            background-color: #000000;
                            color: white;
                            border: 1px solid #000000;
                            border-radius: 4px;
                            font-weight: bold;
                            cursor: pointer;
                            font-size: 14px;
                            display: flex;
                            align-items: center;
                            justify-content: center;
                            font-family: sans-serif;
                        }}
                    </style>
                    <button class="btn" id="dl-pdf-btn">📄 견적서 다운로드 (PDF)</button>
                    <div id="hidden-q-container" style="display: none; width: 720px; background: white; padding: 10px;"></div>
                    
                    <script>
                        document.getElementById('dl-pdf-btn').onclick = function() {{
                            var container = document.getElementById('hidden-q-container');
                            container.innerHTML = {escaped_html};
                            container.style.display = 'block';
                            
                            var opt = {{
                                margin:       [10, 10, 10, 10],
                                filename:     '견적서_{clean_client}.pdf',
                                image:        {{ type: 'jpeg', quality: 0.98 }},
                                html2canvas:  {{ scale: 2.2, useCORS: true, logging: false }},
                                jsPDF:        {{ unit: 'mm', format: 'a4', orientation: 'portrait' }}
                            }};
                            
                            html2pdf().from(container).set(opt).save().then(function() {{
                                container.style.display = 'none';
                            }});
                        }};
                    </script>
                    """
                    st.components.v1.html(button_iframe, height=45)
                else:
                    st.warning("견적서 다운로드를 위해 의뢰기관명과 과제명을 먼저 입력해 주세요.")

            with st.expander("📄 계산서 발행 신청"):
                t_biz_num = st.text_input("사업자 등록번호", placeholder="000-00-00000", key="t_biz_num_yeta")
                t_biz_name = st.text_input("상호 (회사명)", key="t_biz_name_yeta")
                t_rep_name = st.text_input("대표자명", key="t_rep_name_yeta")
                t_address = st.text_input("사업장 주소", key="t_address_yeta")
                t_biz_type = st.text_input("업태 / 업종", key="t_biz_type_yeta")
                t_email = st.text_input("계산서 수신 이메일", key="t_email_yeta")
                
                t_tier = st.selectbox(
                    "신청 서비스 (요금제)",
                    options=[
                        ("월간 이용권 (300,000원)", "월간 이용권"),
                        ("연간 이용권 (2,800,000원)", "연간 이용권")
                    ],
                    format_func=lambda x: x[0],
                    key="t_tier_select_yeta"
                )
                
                if st.button("계산서 발행 신청하기", use_container_width=True, key="btn_request_tax_yeta"):
                    if not t_biz_num.strip():
                        st.error("사업자 등록번호를 입력해 주세요.")
                    elif not t_biz_name.strip():
                        st.error("상호를 입력해 주세요.")
                    elif not t_rep_name.strip():
                        st.error("대표자명을 입력해 주세요.")
                    elif not t_email.strip():
                        st.error("이메일을 입력해 주세요.")
                    elif not validate_email(t_email.strip()):
                        st.error("올바른 이메일 형식이 아닙니다.")
                    else:
                        with st.spinner("신청서를 제출하는 중..."):
                            conn = get_db_connection('users.db')
                            c = conn.cursor()
                            try:
                                now_str = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).strftime("%Y-%m-%d %H:%M:%S")
                                c.execute("""
                                    INSERT INTO tax_invoice_requests 
                                    (user_id, biz_num, biz_name, rep_name, address, biz_type, email, plan_name, request_date, status)
                                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                """, (st.session_state.user_id, t_biz_num.strip(), t_biz_name.strip(), t_rep_name.strip(), t_address.strip(), t_biz_type.strip(), t_email.strip(), t_tier[1], now_str, 'pending'))
                                conn.commit()
                                
                                mail_success = send_tax_invoice_request_email(
                                    st.session_state.user_id, t_biz_num.strip(), t_biz_name.strip(), t_rep_name.strip(), 
                                    t_address.strip(), t_biz_type.strip(), t_email.strip(), t_tier[0]
                                )
                                
                                if mail_success:
                                    st.success("계산서 신청이 접수되었습니다! 관리자 확인 후 계산서가 발행됩니다.")
                                else:
                                    st.warning("DB 저장은 성공했으나 알림 메일 발송에 실패했습니다. 관리자가 확인 후 순차 처리해 드리겠습니다.")
                            except Exception as e:
                                st.error(f"신청 중 오류가 발생했습니다: {e}")
                            finally:
                                conn.close()

        # Business Info
        st.markdown("---")
        biz_info_html = f"""
        <div style="font-size: 0.75rem; color: #888; line-height: 1.5; padding: 10px 5px; border-top: 1px solid #eeeeee; margin-top: 15px;">
            <div style="font-weight: bold; margin-bottom: 5px; color: #555;">사업자 정보</div>
            • <b>상호</b>: 프레쉬인사이트<br>
            • <b>대표자</b>: 전상현<br>
            • <b>사업자등록번호</b>: 683-27-00122<br>
            • <b>주소</b>: 인천시 부평구 원길로 12, 가동 203호<br>
            • <b>전화번호</b>: 0507-1347-2610<br>
            • <b>이메일</b>: jeon080423@gmail.com<br>
            • <b>개인정보관리책임자</b>: 전상현<br>
            • <b>통신판매업 신고번호</b>: 간이과세자
        </div>
        """
        st.markdown(biz_info_html, unsafe_allow_html=True)

    # 7. Navigation Tabs
    # --- ADMIN MODE INTERCEPTOR ---
    if st.session_state.get('admin_mode', False) and st.session_state.user_role == 'admin':
        st.subheader("👥 가입자 현황 및 관리 (예타 전용 뷰)")
        
        col_sync1, col_sync2 = st.columns([2, 8])
        with col_sync1:
            if st.button("🔄 구글 시트와 동기화"):
                with st.spinner("구글 시트 데이터 불러오는 중..."):
                    sync_count = sync_db_from_sheets()
                if sync_count >= 0:
                    st.success(f"🎉 동기화 완료! (보정 및 복구된 데이터: {sync_count}건)")
                    st.rerun()
                else:
                    st.error("동기화 중 오류가 발생했습니다. 화면상의 에러 메시지를 확인해 주세요.")

        try:
            spreadsheet_id = st.secrets.get("SPREADSHEET_ID")
            visit_data_gs = get_cached_visit_logs(spreadsheet_id) if spreadsheet_id else []
            if not visit_data_gs:
                try:
                    conn = get_db_connection('users.db')
                    df_local = pd.read_sql_query("SELECT ip_address as IP, visit_date as Date FROM visit_logs", conn)
                    conn.close()
                    if not df_local.empty:
                        df_local['Country'] = ""
                        df_local['Region'] = ""
                        df_local['City'] = ""
                        df_local['Latitude'] = ""
                        df_local['Longitude'] = ""
                        visit_data_gs = df_local.to_dict(orient='records')
                except Exception:
                    pass
            
            daily_df_logs = pd.DataFrame(visit_data_gs)
            if not daily_df_logs.empty:
                daily_df_logs['Date_Only'] = daily_df_logs['Date'].astype(str).str[:10]
                daily_df_counts = daily_df_logs.groupby('Date_Only').size().reset_index(name='count')
                total_visits = len(daily_df_logs)
                
                st.write(f"**누적 방문자:** {total_visits:,}명")
                st.write("#### 📅 일별 방문자 현황")
                fig_visit = px.bar(daily_df_counts, x='Date_Only', y='count', text='count',
                                    labels={'Date_Only': '날짜', 'count': '방문자 수'})
                fig_visit.update_traces(textposition='outside')
                fig_visit.update_layout(xaxis_title="날짜", yaxis_title="방문자 수", showlegend=False, xaxis={'type': 'category'})
                st.plotly_chart(fig_visit, use_container_width=True)
            else:
                st.info("방문 기록이 없습니다.")
        except Exception as e:
            st.error(f"통계 오류: {e}")
            
        st.divider()
        st.write("### 👥 가입자 현황 및 최종 배포 링크")
        
        users_df = get_all_users()
        if 'survey_count' not in users_df.columns:
            users_df['survey_count'] = 0
        if 'last_survey_link' not in users_df.columns:
            users_df['last_survey_link'] = ""
        users_df['survey_count'] = pd.to_numeric(users_df['survey_count'].fillna(0)).astype(int)
        
        display_df = users_df[['id', 'role', 'signup_date', 'pw', 'survey_count', 'last_survey_link', 'expiry_date', 'agree_info', 'customer_type']].copy()
        st.dataframe(
            display_df,
            column_config={
                "id": "회원 ID",
                "role": "권한",
                "signup_date": "가입일",
                "pw": "비밀번호",
                "survey_count": "배포 횟수",
                "last_survey_link": st.column_config.LinkColumn("최종 배포 설문지 링크", display_text="설문지 바로가기"),
                "expiry_date": "만료일",
                "agree_info": "동의여부",
                "customer_type": "고객군"
            },
            hide_index=True,
            use_container_width=True
        )

        with st.expander("회원 정보 수정 (비밀번호 초기화 포함)"):
            edit_id = st.selectbox("수정할 회원 ID", users_df['id'].unique())
            selected_user = users_df[users_df['id'] == edit_id].iloc[0]
            new_role_val = st.selectbox("권한 변경", ['temp', 'official', 'admin'], 
                                    index=['temp', 'official', 'admin'].index(selected_user['role']))
            
            if new_role_val == 'official' and selected_user['role'] != 'official':
                new_expiry_val_default = str(datetime.date.today() + datetime.timedelta(days=60))
            else:
                new_expiry_val_default = selected_user['expiry_date']
                
            new_expiry_val = st.text_input("만료일 설정/변경 (YYYY-MM-DD)", value=new_expiry_val_default)
            new_pw_edit = st.text_input("새 비밀번호 (입력 시 변경됨)", type="password", placeholder="변경하지 않으려면 비워두세요")
            
            col_admin_act1, col_admin_act2 = st.columns(2)
            with col_admin_act1:
                if st.button("정보 수정 적용", use_container_width=True):
                    update_user_full_info(edit_id, new_pw_edit, new_role_val, new_expiry_val)
                    if new_role_val == 'official' and selected_user['role'] != 'official':
                        send_approval_email(edit_id)
                    st.success(f"{edit_id} 회원의 정보가 수정되었습니다.")
                    st.rerun()
            with col_admin_act2:
                if st.button("🔑 이 계정으로 로그인", use_container_width=True, type="secondary"):
                    st.session_state.user_id = edit_id
                    st.session_state.user_role = selected_user['role']
                    st.session_state.expiry_date = selected_user['expiry_date']
                    st.session_state.admin_mode = False
                    st.toast(f"🔑 {edit_id} 계정으로 로그인했습니다.")
                    st.rerun()

        with st.expander("회원 삭제"):
            del_id = st.selectbox("삭제할 회원 ID 선택", users_df['id'].unique(), key='del_user_select')
            if st.button("선택한 회원 삭제"):
                if del_id == st.session_state.user_id:
                    st.error("본인은 삭제할 수 없습니다.")
                else:
                    delete_user(del_id)
                    st.success("삭제 완료")
                    st.rerun()

        with st.expander("🎁 학위논문 할인 이벤트 설정 및 제어"):
            event_cfg = get_event_settings()
            new_active = st.checkbox("이벤트 활성화 여부", value=event_cfg["active"], key="admin_event_active")
            new_title = st.text_input("이벤트 제목", value=event_cfg["title"], key="admin_event_title")
            new_desc = st.text_area("이벤트 내용/설명", value=event_cfg["desc"], key="admin_event_desc")
            
            try:
                default_deadline_date = datetime.datetime.strptime(event_cfg["deadline"], "%Y-%m-%d").date()
            except Exception:
                default_deadline_date = datetime.date(2026, 7, 30)
            new_deadline_date = st.date_input("이벤트 종료일", value=default_deadline_date, key="admin_event_deadline")
            new_deadline_str = str(new_deadline_date)
            new_discount = st.number_input("할인 금액 (원)", min_value=0, max_value=500000, value=event_cfg["discount"], step=5000, key="admin_event_discount")
            
            if st.button("이벤트 설정 저장", use_container_width=True):
                conn = get_db_connection('users.db')
                c = conn.cursor()
                try:
                    c.execute("UPDATE event_settings SET event_active=?, event_title=?, event_desc=?, event_deadline=?, event_discount=? WHERE id=1",
                              (1 if new_active else 0, new_title, new_desc, new_deadline_str, int(new_discount)))
                    conn.commit()
                    st.success("🎉 이벤트 설정이 성공적으로 저장되었습니다!")
                    st.rerun()
                except Exception as e:
                    st.error(f"설정 저장 실패: {e}")
                finally:
                    conn.close()

        st.stop()

    if st.session_state.user_id:
        tab_guide, tab_analysis, tab_excel, tab_survey_create, tab_live_response, tab_pricing = st.tabs([
            "예타 AHP 지침 안내",
            "예타 종합평가(AHP) 분석",
            "예타 코딩 엑셀 양식",
            "예타 전용 AHP 설문 작성 및 배포",
            "실시간 응답 현황",
            "서비스 요금"
        ])
    else:
        tab_guide, tab_analysis, tab_excel, tab_survey_create, tab_live_response, tab_pricing, tab_signup = st.tabs([
            "예타 AHP 지침 안내",
            "예타 종합평가(AHP) 분석",
            "예타 코딩 엑셀 양식",
            "예타 전용 AHP 설문 작성 및 배포",
            "실시간 응답 현황",
            "서비스 요금",
            "회원가입"
        ])

    # =========================================================================
    # TAB 1: Analysis Tool
    # =========================================================================
    with tab_analysis:
        st.write("### " + "예비타당성 종합평가(AHP)")
        st.markdown("<br>", unsafe_allow_html=True)
        
        main_col, settings_col = st.columns([3.0, 1.2], gap="large")
        
        with settings_col:
            # ==========================================
            # SECTION 1: 분석 환경 설정 (Settings)
            # ==========================================
            with st.container(border=True):
                st.markdown(f"<div style='font-size: 1.1rem; font-weight: bold; color: #1e3a8a; margin-bottom: 15px;'><i class='fas fa-cogs'></i> {'예타 종합평가(AHP) 가중치 설정'}</div>", unsafe_allow_html=True)
                
                project_type = st.selectbox(
                    "사업 유형(모델) 선택",
                    options=[
                        ("construction_non_capital", "건설사업 (비수도권)"),
                        ("construction_capital", "건설사업 (수도권)"),
                        ("rnd_bc", "R&D사업 (B/C)"),
                        ("rnd_ec", "R&D사업 (E/C)"),
                        ("other_bc", "기타 재정사업 (B/C)"),
                        ("other_ec", "기타 재정사업 (E/C)")
                    ],
                    format_func=lambda x: x[1],
                    key="yeta_project_type_select"
                )
                p_type = project_type[0]
                
                st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)
                
                st.markdown(f"<div style='font-size: 0.95rem; font-weight: 600; margin-bottom: 8px;'>{'A. 정량 데이터 (B/C, 지역낙후도)'}</div>", unsafe_allow_html=True)
                bc_ratio = st.number_input("경제성 분석 결과 (B/C 비율)", min_value=0.0, max_value=10.0, value=1.05, step=0.05)
                
                has_regional = "non_capital" in p_type or p_type == "other_bc" or p_type == "other_ec"
                if has_regional:
                    lir_value = st.number_input("지역낙후도 지수 (LIR/MIR)", min_value=-3.0, max_value=3.0, value=0.0, step=0.1)
                else:
                    lir_value = 0.0
                    st.text_input("지역낙후도 지수 (LIR/MIR)", value="수도권/해당없음", disabled=True)
                
                st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)
                
                st.markdown(f"<div style='font-size: 0.95rem; font-weight: 600; margin-bottom: 8px;'>{'B. 1계층 상수합 가중치 (%)'}</div>", unsafe_allow_html=True)
                if p_type == "rnd_bc":
                    econ_w = st.slider("경제성 가중치", 0, 100, 45) / 100.0
                    tech_w = st.slider("과학기술적 타당성", 0, 100, 35) / 100.0
                    policy_w = st.slider("정책적 타당성", 0, 100, 20) / 100.0
                    regional_w = 0.0
                elif p_type == "rnd_ec":
                    econ_w = st.slider("경제성 가중치", 0, 100, 35) / 100.0
                    tech_w = st.slider("과학기술적 타당성", 0, 100, 45) / 100.0
                    policy_w = st.slider("정책적 타당성", 0, 100, 20) / 100.0
                    regional_w = 0.0
                elif p_type == "construction_capital":
                    tech_w = 0.0
                    econ_w = st.slider("경제성 가중치", 0, 100, 65) / 100.0
                    policy_w = st.slider("정책적 가중치", 0, 100, 35) / 100.0
                    regional_w = 0.0
                    st.slider("지역균형발전 가중치", 0, 100, 0, disabled=True)
                elif p_type == "other_bc":
                    tech_w = 0.0
                    econ_w = st.slider("경제성 가중치", 0, 100, 40) / 100.0
                    policy_w = st.slider("정책적 가중치", 0, 100, 60) / 100.0
                    regional_w = 0.0
                elif p_type == "other_ec":
                    tech_w = 0.0
                    econ_w = st.slider("경제성 가중치", 0, 100, 30) / 100.0
                    policy_w = st.slider("정책적 가중치", 0, 100, 70) / 100.0
                    regional_w = 0.0
                else: # construction_non_capital
                    tech_w = 0.0
                    econ_w = st.slider("경제성 가중치", 0, 100, 40) / 100.0
                    policy_w = st.slider("정책적 가중치", 0, 100, 30) / 100.0
                    regional_w = st.slider("지역균형발전 가중치", 0, 100, 30) / 100.0

                valid_w, w_msg = yeta_utils.validate_yeta_level1_weights(p_type, econ_w, policy_w, regional_w, tech_w)
                if valid_w:
                    st.markdown(f"<div style='color: green; font-size: 0.8rem; margin-top: -10px;'>✔️ {'KDI 지침 가중치 범위 부합'}</div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div style='color: red; font-size: 0.8rem; margin-top: -10px;'>⚠️ {w_msg}</div>", unsafe_allow_html=True)


        with main_col:
            # ==========================================
            # SECTION 3: 엑셀 데이터 업로드 및 분석 (Upload & Analyze)
            # ==========================================
            with st.container(border=True):
                st.markdown(f"<h3 style='color: #b91c1c; margin-bottom: 10px; font-size: 1.3rem;'><i class='fas fa-chart-line'></i> {'2. 데이터 업로드 및 종합평가 분석'}</h3>", unsafe_allow_html=True)
                st.markdown("<span style='font-size: 0.95rem; color: #4b5563;'>템플릿에 작성이 완료된 AHP 엑셀 데이터를 업로드하면 즉시 예비타당성조사 종합평가 결과가 산출됩니다.</span>", unsafe_allow_html=True)
                
                st.markdown("<br>", unsafe_allow_html=True)
                
                # User Tier Check
                is_official = False
                if st.session_state.get("user_id"):
                    if st.session_state.get("user_role") in ["official", "admin"]:
                        is_official = True
                    else:
                        try:
                            conn = get_db_connection('users.db')
                            c = conn.cursor()
                            c.execute("SELECT role FROM users WHERE id=?", (st.session_state.user_id,))
                            res = c.fetchone()
                            if res and res[0] in ["official", "admin"]:
                                is_official = True
                            conn.close()
                        except:
                            pass

                auto_correct_cr = st.checkbox("CR 0.15 초과 시 행렬 자동 보정", value=True, help="평가자의 일관성 비율(CR)이 0.15를 초과하는 경우, AHP 보정 알고리즘을 통해 일관성 있는 행렬로 자동 조정합니다.")
                
                data_source = st.radio(
                    "데이터 소스 선택",
                    ["📂 엑셀 파일 직접 업로드", "🌐 배포된 온라인 설문 데이터 연동"],
                    horizontal=True
                )
                
                df = None
                if data_source == "📂 엑셀 파일 직접 업로드":
                    uploaded_file = st.file_uploader("응답이 완료된 AHP 엑셀 파일 첨부", type=["xlsx"])
                    if uploaded_file is not None:
                        try:
                            df = pd.read_excel(uploaded_file)
                            
                            # --- [사업 모델 및 계층 구조 자동 인식 로직 시작] ---
                            inferred_p_type = "construction_capital"
                            has_reg = "1계층_지역균형발전(%)" in df.columns
                            has_tech = "1계층_기술성(%)" in df.columns
                            
                            if has_tech:
                                inferred_p_type = "rnd"
                            elif has_reg:
                                inferred_p_type = "construction_non_capital"
                            
                            # 하위 요인 추출
                            inferred_factors = {}
                            for col in df.columns:
                                if col.startswith("대안평가_[") and "]_" in col:
                                    cat = col.split("]_")[0].replace("대안평가_[", "")
                                    factor = col.split("]_")[1].split("(시행선호")[0]
                                    if cat not in inferred_factors: inferred_factors[cat] = set()
                                    inferred_factors[cat].add(factor)
                                    
                            factor_msg = []
                            for cat, factors in inferred_factors.items():
                                factor_msg.append(f"**{cat}**: {', '.join(list(factors))}")
                                
                            p_type_ko = "R&D 사업" if inferred_p_type == "rnd" else ("비수도권 사업 (지역균형발전 포함)" if inferred_p_type == "construction_non_capital" else "수도권 사업 (경제성/정책성 위주)")
                            
                            st.success(f"데이터 로드 성공! 엑셀 데이터를 통해 사업 모델을 자동으로 인식했습니다.\n\n* **인식된 사업 유형**: {p_type_ko}\n* **분석 요인**: {', '.join(inferred_factors.keys())}")
                            with st.expander("인식된 하위 계층 구조 보기"):
                                for msg in factor_msg:
                                    st.markdown("- " + msg)
                            # -----------------------------------------------------
                            
                            # Override p_type with inferred one for accurate processing
                            p_type = inferred_p_type
                            
                        except Exception as e:
                            st.error(f"엑셀 로드 중 오류가 발생했습니다: {str(e)}")
                else:
                    if st.session_state.user_id is None:
                        st.warning("온라인 설문 데이터 연동 분석은 회원 전용 기능입니다. 로그인해 주세요.")
                    else:
                        try:
                            from survey_manager import sync_short_codes_from_gs, get_admin_surveys_from_gsheet, load_survey_metadata, get_survey_gspread_client
                            sync_short_codes_from_gs()
                        except:
                            pass
                        
                        conn = get_db_connection('users.db')
                        cur = conn.cursor()
                        cur.execute("SELECT survey_id, title, created_at FROM admin_surveys WHERE admin_id = ? ORDER BY created_at DESC", (st.session_state.user_id,))
                        sqlite_surveys = cur.fetchall()
                        conn.close()
                        
                        gs_surveys = []
                        try:
                            from survey_manager import get_admin_surveys_from_gsheet
                            gs_surveys = get_admin_surveys_from_gsheet(st.session_state.user_id)
                        except:
                            pass
                        
                        merged_surveys = {}
                        for s in gs_surveys + sqlite_surveys:
                            if s[0] not in merged_surveys:
                                merged_surveys[s[0]] = s
                        admin_surveys = list(merged_surveys.values())
                        admin_surveys.sort(key=lambda x: x[2], reverse=True)
                    
                        if not admin_surveys:
                            st.warning("배포된 온라인 설문이 없습니다.")
                        else:
                            survey_options = {f"{row[1]} ({row[2]})": row[0] for row in admin_surveys}
                            selected_survey_label = st.selectbox(
                                "분석할 온라인 설문 선택",
                                list(survey_options.keys())
                            )
                            selected_sheet_id = survey_options[selected_survey_label]
                            
                            if st.button("🔄 구글 시트에서 실시간 응답 가져오기", type="primary", use_container_width=True):
                                with st.spinner("구글 시트에서 설문 데이터를 가져오는 중..."):
                                    from survey_manager import get_survey_gspread_client
                                    g_client = get_survey_gspread_client()
                                    if g_client:
                                        try:
                                            spreadsheet = g_client.open_by_key(selected_sheet_id)
                                            raw_sheet = spreadsheet.worksheet("Raw_Data")
                                            all_rows = raw_sheet.get_all_values()
                                            if len(all_rows) > 1:
                                                headers = all_rows[0]
                                                rows = all_rows[1:]
                                                df = pd.DataFrame(rows, columns=headers)
                                                
                                                # --- [사업 모델 및 계층 구조 자동 인식 로직 시작] ---
                                                inferred_p_type = "construction_capital"
                                                has_reg = "1계층_지역균형발전(%)" in df.columns
                                                has_tech = "1계층_기술성(%)" in df.columns
                                                
                                                if has_tech:
                                                    inferred_p_type = "rnd"
                                                elif has_reg:
                                                    inferred_p_type = "construction_non_capital"
                                                
                                                inferred_factors = {}
                                                for col in df.columns:
                                                    if col.startswith("대안평가_[") and "]_" in col:
                                                        cat = col.split("]_")[0].replace("대안평가_[", "")
                                                        factor = col.split("]_")[1].split("(시행선호")[0]
                                                        if cat not in inferred_factors: inferred_factors[cat] = set()
                                                        inferred_factors[cat].add(factor)
                                                        
                                                factor_msg = []
                                                for cat, factors in inferred_factors.items():
                                                    factor_msg.append(f"**{cat}**: {', '.join(list(factors))}")
                                                    
                                                p_type_ko = "R&D 사업" if inferred_p_type == "rnd" else ("비수도권 사업 (지역균형발전 포함)" if inferred_p_type == "construction_non_capital" else "수도권 사업 (경제성/정책성 위주)")
                                                
                                                st.success(f"온라인 설문 데이터를 성공적으로 불러왔습니다! 사업 모델을 자동으로 인식했습니다.\n\n* **인식된 사업 유형**: {p_type_ko}\n* **분석 요인**: {', '.join(inferred_factors.keys())}")
                                                with st.expander("인식된 하위 계층 구조 보기"):
                                                    for msg in factor_msg:
                                                        st.markdown("- " + msg)
                                                        
                                                p_type = inferred_p_type
                                                # -----------------------------------------------------
                                                
                                            else:
                                                st.warning("아직 수집된 응답 데이터가 없습니다.")
                                        except Exception as e:
                                            st.error(f"구글 시트 데이터를 가져오는 중 오류가 발생했습니다: {str(e)}")

                if df is not None:
                    try:
                        max_free_evals = 3
                        if not is_official and len(df) > max_free_evals:
                            st.warning(f"⚠️ 무료 사용자는 최대 {max_free_evals}명의 설문 데이터만 분석 가능합니다. (정식 결제 시 무제한 분석 가능)")
                            df = df.head(max_free_evals)
                            
                        res_df, final_yeta_score = yeta_utils.process_yeta_ahp_data(df, p_type, bc_ratio, lir_value, auto_correct_cr=auto_correct_cr)
                        
                        # 웹 출력용으로만 소수점 포맷팅 적용 (데이터 원본 보존)
                        st.markdown("---")
                        st.markdown("### " + "📊 종합평가(AHP) 최종 결과")
                        
                        # --- Create standard AHP summary table ---
                        passed_evals = res_df[res_df["CR 통과"] == "PASS"]
                        if len(passed_evals) > 0:
                            avg_w_econ = passed_evals["경제성 가중치"].mean()
                            avg_w_policy = passed_evals["정책성 가중치"].mean()
                            avg_w_reg = passed_evals["지역균형 가중치"].mean()
                            avg_w_tech = passed_evals["기술성 가중치"].mean()
                            
                            avg_s_econ = passed_evals["경제성 점수"].mean()
                            avg_s_policy = passed_evals["정책성 점수"].mean()
                            avg_s_reg = passed_evals["지역균형 점수"].mean()
                            avg_s_tech = passed_evals["기술성 점수"].mean()
                            
                            summary_data = []
                            summary_data.append({"평가항목": "경제성 분석", "가중치": avg_w_econ, "평가 결과 (점수)": avg_s_econ, "비고": "B/C, NPV 등 반영"})
                            summary_data.append({"평가항목": "정책성 분석", "가중치": avg_w_policy, "평가 결과 (점수)": avg_s_policy, "비고": "정책효과, 추진여건 등"})
                            
                            if "rnd" in p_type:
                                summary_data.append({"평가항목": "기술성 분석", "가중치": avg_w_tech, "평가 결과 (점수)": avg_s_tech, "비고": "기술개발 성공가능성 등"})
                            if "non_capital" in p_type or p_type in ["other_bc", "other_ec"]:
                                summary_data.append({"평가항목": "지역균형발전 분석", "가중치": avg_w_reg, "평가 결과 (점수)": avg_s_reg, "비고": "지역낙후도, 파급효과 등"})
                                
                            summary_data.append({"평가항목": "**종합평가 (AHP)**", "가중치": 1.000, "평가 결과 (점수)": final_yeta_score, "비고": "**최종 결과값**"})
                            
                            st.write("#### " + "[표] AHP를 이용한 종합평가 결과")
                            summary_df_for_excel = pd.DataFrame(summary_data)
                            
                            # 웹 출력 시 소수점 3자리 고정
                            format_dict = {"가중치": "{:.3f}", "평가 결과 (점수)": "{:.3f}"}
                            st.table(summary_df_for_excel.style.format(format_dict))
                            
                            # Add Excel Download Button
                            try:
                                from yeta_utils import export_yeta_result_excel
                                
                                # 미리 is_pass 계산
                                is_pass = final_yeta_score >= 0.5
                                excel_data = export_yeta_result_excel(summary_df_for_excel, res_df, final_score=final_yeta_score, is_pass=is_pass)
                                
                                st.download_button(
                                    label="📥 종합평가(AHP) 엑셀 결과 다운로드",
                                    data=excel_data,
                                    file_name="예비타당성조사_AHP_최종결과.xlsx",
                                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                    type="primary",
                                    use_container_width=True
                                )
                            except Exception as ex:
                                st.error(f"엑셀 다운로드 기능 로드 중 오류 발생: {ex}")
                                
                            st.markdown("<br>", unsafe_allow_html=True)
                        # ----------------------------------------
                        
                        is_pass = final_yeta_score >= 0.5
                        card_class = "verdict-pass" if is_pass else "verdict-fail"
                        verdict_text = "사업 타당성 확보 (시행)" if is_pass else "사업 타당성 미흡 (미시행)"
                        
                        st.markdown(f"""
                        <div class="verdict-card {card_class}">
                            <div class="verdict-title">{"최종 종합 평가 판정"}</div>
                            <div class="verdict-score">{final_yeta_score:.3f}</div>
                            <div style="font-size: 1.3rem; font-weight: bold;">{verdict_text}</div>
                            <div style="font-size: 0.9rem; margin-top: 10px; opacity: 0.85;">
                                {"KDI 지침 기준: AHP 종합점수 0.5 이상일 때 타당성 확보"}
                            </div>
                        </div>
                        <br>
                        """, unsafe_allow_html=True)
                        
                        st.info(f"💡 **조사 결과 해석**: 본 예비타당성조사는 응답자 {len(res_df)}명의 설문 결과를 바탕으로, 극단값(최고점 1명, 최저점 1명)을 제외한 {max(1, len(res_df)-2 if len(res_df) >= 3 else len(res_df))}명의 점수를 종합하여 도출되었습니다. 최종 AHP 종합점수가 {final_yeta_score:.3f}으로 0.5를 {'넘어 사업 타당성을 확보했습니다' if is_pass else '넘지 못해 사업 타당성이 미흡한 것으로 분석되었습니다'}.")
                        
                        with st.expander("📚 AHP 산출식 및 변환 공식 안내"):
                            st.markdown("""
                            #### 1. 정량 데이터 쌍대비교 척도 변환
                            경제성 등 정량적 수치를 설문조사의 9점 척도와 동등하게 맞추기 위해 KDI 표준 공식을 사용합니다.
                            - **B/C 비율 변환**: `표준점수 = 8.592933 × ln(B/C비율) ± 1`
                            - **지역낙후도(LIR) 변환**: `표준점수 = 2.0 × LIR + 1.0`
                            
                            #### 2. 쌍대비교 척도의 가중치(AHP 점수) 변환
                            위에서 도출된 표준점수(`Score`)를 바탕으로 '시행(Go)' 대안의 평가 결과(점수)를 계산합니다.
                            - **시행(Go) 가중치** = `Score / (Score + 1.0)`
                            - 예) B/C 환산 표준점수가 1.419라면, 시행 점수는 `1.419 / (1.419 + 1) = 0.5866`
                            
                            #### 3. 개인별 점수 합산 및 최종 종합점수 산출
                            각 평가자의 항목별 가중치와 위에서 구한 각 항목별 점수를 곱해 개인별 최종 점수를 계산합니다. 
                            이후 응답자가 3명 이상일 경우, 가장 높은 점수 1명과 가장 낮은 점수 1명을 집계에서 배제(극단값 배제)한 뒤 남은 인원들의 점수를 **기하평균(Geometric Mean)**하여 최종 AHP 평점을 산출합니다.
                            """)
                        
                        st.markdown("<br>", unsafe_allow_html=True)
                        st.write("#### " + "👨‍🔬 평가자별 점수 분포 및 극단값 배제 현황")
                        st.dataframe(res_df, use_container_width=True)
                        
                    except Exception as e:
                        st.error(f"분석 중 오류가 발생했습니다: {str(e)}")




    # =========================================================================
    # =========================================================================
    # TAB 1.5: Yeta Excel Template Generator
    # =========================================================================
    with tab_excel:
        st.write("### " + "예비타당성조사 AHP 코딩 엑셀 양식 설정 및 다운로드")
        st.markdown("<br>", unsafe_allow_html=True)
        
        st.markdown(f"<h4 style='color: #1e3a8a; margin-top: 10px;'><i class='fas fa-check-circle'></i> 1단계: 분석 모델(사업 유형) 선택</h4>", unsafe_allow_html=True)
        with st.container(border=True):
            excel_project_type = st.selectbox(
                "대상 사업 유형",
                options=[
                    ("construction_non_capital", "건설사업 (비수도권)"),
                    ("construction_capital", "건설사업 (수도권)"),
                    ("rnd_bc", "R&D사업 (B/C)"),
                    ("rnd_ec", "R&D사업 (E/C)"),
                    ("other_bc", "기타 재정사업 (B/C)"),
                    ("other_ec", "기타 재정사업 (E/C)")
                ],
                format_func=lambda x: x[1],
                key="yeta_excel_project_type_select"
            )
            ex_p_type = excel_project_type[0]
            
            if "rnd" in ex_p_type:
                st.info("📊 1계층 고정 항목: 경제성, 정책성, 과학기술성")
            elif "capital" in ex_p_type and "non" not in ex_p_type:
                st.info("📊 1계층 고정 항목: 경제성, 정책성")
            else:
                st.info("📊 1계층 고정 항목: 경제성, 정책성, 지역균형발전")
        
        st.markdown(f"<h4 style='color: #1e3a8a; margin-top: 25px;'><i class='fas fa-list'></i> 2단계: 2계층 평가 요인 커스터마이징</h4>", unsafe_allow_html=True)
        with st.container(border=True):
            st.caption("대상 사업 특성에 맞춰 세부 평가 항목을 쉼표(,)로 구분하여 입력하세요. 입력한 요인 개수에 맞춰 쌍대비교 폼이 자동 계산됩니다.")
            
            policy_input = st.text_input("정책성 하위 요인", value="정책의 일관성, 사업추진상의 위험요인")
            policy_factors = [x.strip() for x in policy_input.split(",") if x.strip()]
            
            regional_factors = []
            if "non_capital" in ex_p_type or "other" in ex_p_type:
                reg_input = st.text_input("지역균형발전 하위 요인", value="지역경제 파급효과, 지역개발계획과의 부합성")
                regional_factors = [x.strip() for x in reg_input.split(",") if x.strip()]
                
            tech_factors = []
            if "rnd" in ex_p_type:
                tech_input = st.text_input("과학기술성 하위 요인", value="기술개발계획의 적절성, 기술개발 성공가능성, 기존 사업과의 중복성")
                tech_factors = [x.strip() for x in tech_input.split(",") if x.strip()]

        st.markdown(f"<h4 style='color: #047857; margin-top: 25px;'><i class='fas fa-file-excel'></i> 3단계: 맞춤형 엑셀 폼 생성 및 다운로드</h4>", unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown("<span style='font-size: 0.95rem; color: #4b5563;'>위 1단계와 2단계에서 설정한 <b>예비타당성조사 분석 모델 및 요인</b>에 맞춰진 전용 엑셀 펀칭 폼입니다.</span>", unsafe_allow_html=True)
            
            st.markdown("""
            <div style='background-color: #f9fafb; padding: 15px; border-radius: 5px; margin-top: 15px; border-left: 4px solid #3b82f6; margin-bottom: 20px;'>
                <strong>[양식 구조 안내]</strong><br>
                ✔️ <b>동일한 부분</b>: 2계층 이후 항목들 간의 쌍대비교 입력 방식 및 CR 검증 로직은 일반 AHP와 동일합니다.<br>
                ✔️ <b>달라지는 부분</b>: 예타 지침에 따라 1계층(경제/정책/지역) 가중치는 쌍대비교가 아닌 <b>100점 상수합법</b> 비율로 기입합니다.<br><br>
                <strong>[📝 데이터 입력 가이드]</strong><br>
                다운로드하시는 엑셀 폼에 데이터를 기입하실 때 아래 규칙을 따르세요.<br>
                ✔️ 왼쪽(시행) 항목이 더 중요하면: <b>음수</b> 입력 (예: -3)<br>
                ✔️ 오른쪽(미시행) 항목이 더 중요하면: <b>양수</b> 입력 (예: 3)<br>
                ✔️ 두 항목이 동등하게 중요하면: <b>1</b> 입력
            </div>
            """, unsafe_allow_html=True)
            
            img_file = "ahp_input_guide.png"
            caption_text = "[참고] 설문 응답을 엑셀에 입력하는 방법"
            if os.path.exists(img_file):
                st.image(img_file, caption=caption_text)
            
            template_bytes = yeta_utils.generate_yeta_excel_template(ex_p_type, policy_factors, regional_factors, tech_factors)
            st.download_button(
                label="👉 맞춤형 예타 AHP 엑셀 템플릿 다운로드 (.xlsx)",
                data=template_bytes,
                file_name=f"yeta_ahp_template_{ex_p_type}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary",
                use_container_width=True
            )

    # =========================================================================
    # TAB 2: Yeta Survey Creator
    # =========================================================================
    with tab_survey_create:
        st.write("### 예비타당성조사 AHP 전문가 설문지 제작 및 배포")
        st.info("KDI 지침에 명시된 요인을 바탕으로 예타 전용 설문지를 쉽게 구성하고 구글 시트와 연동하여 배포할 수 있습니다.")
        
        # ------------------------------------------------------------
        # 0. 설문 관리 (1인 1설문 모드)
        # ------------------------------------------------------------
        st.subheader("섹션 0: 내 설문 관리")

        # Initialize states
        if 'yeta_editing_survey_id' not in st.session_state:
            st.session_state.yeta_editing_survey_id = None
        if 'yeta_survey_auto_loaded' not in st.session_state:
            st.session_state.yeta_survey_auto_loaded = False

        if '_cached_user_surveys_yeta' not in st.session_state or st.session_state.get('_survey_cache_dirty_yeta'):
            sqlite_surveys = []
            try:
                import sqlite3
                conn = sqlite3.connect('users.db')
                cur = conn.cursor()
                cur.execute("SELECT survey_id, title, created_at FROM admin_surveys WHERE admin_id = ? AND title LIKE '[예타]%' ORDER BY created_at DESC", (st.session_state.user_id,))
                sqlite_surveys = cur.fetchall()
                conn.close()
            except Exception:
                pass

            gs_surveys = []
            try:
                from survey_manager import get_admin_surveys_from_gsheet
                gs_surveys = get_admin_surveys_from_gsheet(st.session_state.user_id)
                gs_surveys = [s for s in gs_surveys if str(s[1]).startswith("[예타]")]
            except Exception:
                pass
            
            merged_surveys = {}
            for s in gs_surveys + sqlite_surveys:
                if s[0] not in merged_surveys:
                    merged_surveys[s[0]] = s
            user_surveys = list(merged_surveys.values())
            user_surveys.sort(key=lambda x: x[2], reverse=True)
            st.session_state._cached_user_surveys_yeta = user_surveys
            st.session_state._survey_cache_dirty_yeta = False
        else:
            user_surveys = st.session_state._cached_user_surveys_yeta
        
        has_survey = len(user_surveys) > 0

        # Auto-load logic
        if has_survey and not st.session_state.yeta_survey_auto_loaded:
            sel_id = user_surveys[0][0]
            from survey_manager import load_survey_metadata
            meta = load_survey_metadata(sel_id)
            if meta:
                st.session_state.yeta_editing_survey_id = sel_id
                st.session_state.edit_yeta_title = meta.get("Title", "").replace("[예타] ", "")
                st.session_state.edit_yeta_desc = meta.get("Description", "")
                st.session_state.edit_yeta_admin_email = meta.get("Admin_Email", "")

                demo = meta.get("Demographics", {})
                st.session_state.edit_yeta_type_question = demo.get("type_question", "")
                st.session_state.edit_yeta_type_options = ", ".join(demo.get("type_options", []))
                if "type_questions" in demo:
                    tqs = []
                    for tq in demo["type_questions"]:
                        tqs.append({"q": tq["q"], "opts": ", ".join(tq["opts"])})
                    st.session_state.edit_yeta_type_questions = tqs
            
                ahp_model = meta.get("AHP_Model_JSON", {})
                st.session_state.edit_yeta_main_input = ", ".join(ahp_model.get("main", []))
                st.session_state.edit_yeta_sub_inputs = {}
                for mc, subs in ahp_model.get("subs", {}).items():
                    st.session_state.edit_yeta_sub_inputs[mc] = ", ".join(subs)
                    
                st.session_state.edit_yeta_sub_sub_inputs = {}
                for mc, subs in ahp_model.get("sub_subs", {}).items():
                    st.session_state.edit_yeta_sub_sub_inputs[mc] = ", ".join(subs)
                
                st.session_state.edit_yeta_p_type = ahp_model.get("yeta_p_type", "건설사업 (비수도권)")
                
                definitions = meta.get("Definitions", {})
                for k, v in definitions.items():
                    st.session_state[f"edit_yeta_desc_{k}"] = v
                
            st.session_state.yeta_survey_auto_loaded = True
            st.rerun()

        @st.dialog("🚨 [경고] 기존 설문 영구 삭제 안내")
        def confirm_new_survey_yeta():
            st.error("새로운 예타 설문을 작성하시면 기존 연동된 모든 데이터가 삭제됩니다.")
            agree = st.checkbox("네, 기존 데이터 백업을 완료했거나 불필요하며, 모든 데이터 삭제에 동의합니다.")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("❌ 취소", use_container_width=True):
                    st.rerun()
            with col2:
                if st.button("✅ 동의 및 초기화", type="primary", use_container_width=True, disabled=not agree):
                    with st.spinner("기존 데이터를 삭제하는 중입니다..."):
                        from survey_manager import delete_admin_survey
                        if user_surveys:
                            delete_admin_survey(user_surveys[0][0], st.session_state.user_id)
                        st.session_state.yeta_editing_survey_id = None
                        keys_to_clear = [k for k in st.session_state.keys() if k.startswith('edit_yeta_')]
                        for k in keys_to_clear:
                            del st.session_state[k]
                        st.session_state.yeta_survey_auto_loaded = False
                        st.session_state._survey_cache_dirty_yeta = True
                    st.success("완료되었습니다. 화면이 새로고침됩니다.")
                    import time
                    time.sleep(1.5)
                    st.rerun()

        if has_survey:
            st.success(f" 현재 배포된 예타 설문이 있습니다. 자동으로 불러왔습니다: **{user_surveys[0][1]}**")
            if st.button("✨ 처음부터 새 설문 작성하기 (기존 데이터 삭제)", type="secondary"):
                 confirm_new_survey_yeta()
        else:
            st.info(" 작성 중인 새 예타 설문입니다.")
            if st.button("✨ 폼 내용 모두 지우기 (초기화)", type="secondary"):
                st.session_state.yeta_editing_survey_id = None
                keys_to_clear = [k for k in st.session_state.keys() if k.startswith('edit_yeta_')]
                for k in keys_to_clear:
                    del st.session_state[k]
                st.rerun()

        st.divider()

        tab1, tab2, tab3 = st.tabs(["📌 1. 기본 정보 & 모델 설계", "📝 2. 평가 항목 설명", "⚙️ 3. 부가 설정 및 배포"])

        with tab1:
            st.markdown("#### 1. 사업 기본 정보 및 자료 첨부")
            survey_title = st.text_input("설문지 제목", value=st.session_state.get("edit_yeta_title", "재정투자사업 종합평가(AHP) 전문가 설문"))
            
            default_survey_desc = (
                "안녕하십니까, 전문가님.\n"
                "본 설문은 KDI 예비타당성조사 수행 지침에 의거하여, 해당 재정투자사업의 타당성 및 추진 여부를 최종 판단하기 위한 '종합평가(AHP)' 용도로 기획되었습니다.\n\n"
                "전문가님께서는 제공된 'AHP 자료집' 및 사업 개요를 충분히 숙지하신 후, 각 평가항목(경제성, 정책성, 지역균형발전, 기술성 등) 간의 상대적 중요도를 평가해주시기 바랍니다.\n\n"
                "■ 주요 평가 유의사항\n"
                "1. (제1계층 평가) 대분류 항목 간의 상대적 중요도를 '총합이 100'이 되도록 배분해 주십시오. (상수합법)\n"
                "   ※ 단, KDI 예비타당성조사 종합평가 지침에 명시된 사업 유형별 가이드라인에 따라 부문별 입력 가능한 점수 범위(상하한선)가 시스템적으로 제한되어 있으니 이 점 널리 양해 부탁드립니다.\n"
                "2. (제2계층 평가) 세부 항목 간 쌍대비교 시, 두 항목 중 더 중요하다고 판단되는 쪽으로 9점 척도 기준 가중치를 부여해 주십시오.\n"
                "3. 설문 응답의 일관성 비율(CR)이 권고 수준(0.15 미만)을 유지할 수 있도록 논리적인 평가를 당부드립니다.\n\n"
                "주관기관: OOOO\n"
                "문의처: OOO, sample@test.co.kr, 00)000-0000\n\n"
                "바쁘신 일정 중에도 국가 공공투자사업의 합리적 의사결정을 위해 귀중한 시간을 내어 주셔서 진심으로 감사드립니다."
            )
            from streamlit_quill import st_quill
            st.markdown("**설문 안내문**")
            survey_desc = st_quill(value=st.session_state.get("edit_yeta_desc", default_survey_desc), html=True, key="quill_yeta_desc")
            
            st.markdown("#### 2. 예타 사업 유형 및 계층구조 모델 설정")
            yeta_p_type = st.selectbox(
                "평가 대상 사업 유형",
                options=["건설사업 (비수도권)", "건설사업 (수도권)", "R&D사업 (B/C)", "R&D사업 (E/C)", "정보화사업", "기타사업 (B/C)", "기타사업 (E/C)"],
                index=["건설사업 (비수도권)", "건설사업 (수도권)", "R&D사업 (B/C)", "R&D사업 (E/C)", "정보화사업", "기타사업 (B/C)", "기타사업 (E/C)"].index(st.session_state.get("edit_yeta_p_type", "건설사업 (비수도권)"))
            )
            
            tier_level = 3
            st.info("💡 **예타 모델 동적 설정**: 일반 모드와 동일하게 각 계층을 쉼표(,)로 구분하여 입력하세요. (1계층은 예타 기본 뼈대를 유지합니다)")

            default_yeta_main = "경제성, 정책성, 지역균형발전"
            if "수도권" in yeta_p_type and "비수도권" not in yeta_p_type: default_yeta_main = "경제성, 정책성"
            elif "R&D" in yeta_p_type: default_yeta_main = "기술성, 경제성, 정책성"
            elif "정보화" in yeta_p_type: default_yeta_main = "기술성, 경제성, 정책성"
            elif "기타" in yeta_p_type: default_yeta_main = "경제성, 정책성, 지역균형발전"
            
            main_input = st.text_input("1계층 (대항목)", value=st.session_state.get("edit_yeta_main_input", default_yeta_main), help="이 항목들은 쌍대비교 대신 100점 분배(상수합법)로 평가됩니다.")
            main_list = [x.strip().replace("_", " ") for x in main_input.split(",") if x.strip()]

            model_structure = {"main": main_list, "subs": {}, "sub_subs": {}, "yeta_p_type": yeta_p_type}

            for mc in main_list:
                if mc == "경제성": 
                    model_structure["subs"][mc] = []
                    st.caption(f"✓ '{mc}' 하위 요인은 일반적으로 편익/비용(B/C)으로 일괄 산출되므로 입력하지 않습니다.")
                    continue
                
                default_sub_val = ""
                if mc == "정책성": default_sub_val = "사업추진 여건, 정책효과"
                elif mc == "지역균형발전": default_sub_val = "지역 낙후도, 지역경제 파급효과"
                elif mc == "기술성": default_sub_val = "기술개발계획의 적절성, 기술개발 성공가능성, 기존 사업과의 중복성"
                
                sub_input = st.text_input(f"'{mc}'의 하위 요인 (2계층)", value=st.session_state.get("edit_yeta_sub_inputs", {}).get(mc, default_sub_val))
                subs_list = [x.strip().replace("_", " ") for x in sub_input.split(",") if x.strip()]
                model_structure["subs"][mc] = subs_list

                if subs_list:
                    with st.expander(f"↳ '{mc}' 하위의 3계층 (소분류) 입력", expanded=False):
                        st.info("💡 소분류(3계층)가 없는 항목은 비워두시면 자동으로 2계층으로 처리됩니다.")
                        for sub_c in subs_list:
                            sub_sub_val = ""
                            if sub_c == "사업추진 여건": sub_sub_val = "정책일치성 등 내부여건, 지역주민 사업태도 등 외부여건"
                            elif sub_c == "정책효과": sub_sub_val = "사업특화항목, 일자리 효과, 생활여건 영향, 환경성 평가, 안전성 평가"
                            
                            sub_sub_input = st.text_input(
                                f"👉 '{sub_c}'의 하위 요인 (쉼표 구분)", 
                                value=st.session_state.get("edit_yeta_sub_sub_inputs", {}).get(sub_c, sub_sub_val),
                                placeholder="예: 항목1, 항목2",
                                key=f"yeta_sub_sub_{sub_c}"
                            )
                            parsed_sub_subs = [x.strip().replace("_", " ") for x in sub_sub_input.split(",") if x.strip()]
                            if parsed_sub_subs:
                                model_structure["sub_subs"][sub_c] = parsed_sub_subs

        with tab2:
            st.markdown("#### 2. 평가 항목 상세 설명")
            st.caption("응답자가 각 항목의 의미를 명확히 이해할 수 있도록 항목별 상세 설명을 입력할 수 있습니다.")
            
            definitions_map = {}
            
            st.markdown("**📌 1계층 (대항목) 설명**")
            for mc in main_list:
                default_desc = ""
                if mc == "경제성": default_desc = "편익/비용(B/C) 비율 등을 바탕으로 사업의 경제적 타당성을 평가합니다."
                elif mc == "정책성": default_desc = "사업의 정책일치성, 추진여건, 정책효과 등 정책적 타당성을 평가합니다."
                elif mc == "지역균형발전": default_desc = "지역낙후도 및 지역경제 파급효과 등을 바탕으로 지역 균형 발전에 미치는 영향을 평가합니다."
                elif mc == "기술성": default_desc = "기술개발계획의 적절성, 기술개발 성공가능성, 기존 사업과의 중복성 등을 평가합니다."
                
                key_cached = f"edit_yeta_desc_{mc}"
                desc_val = st.text_input(
                    f"'{mc}' 요인 설명",
                    value=st.session_state.get(key_cached, default_desc),
                    key=f"yeta_desc_input_{mc}"
                )
                definitions_map[mc] = desc_val
                st.session_state[key_cached] = desc_val
                
            has_sub_desc = False
            for mc in main_list:
                subs = model_structure["subs"].get(mc, [])
                if subs:
                    has_sub_desc = True
                    break
            
            if has_sub_desc:
                st.markdown("---")
                st.markdown("**📌 2계층 및 3계층 하위 요인 설명**")
                
                for mc in main_list:
                    subs = model_structure["subs"].get(mc, [])
                    if subs:
                        with st.container(border=True):
                            st.markdown(f"##### 💡 [{mc}] 하위 요인 설명")
                            for sub_c in subs:
                                sub_subs = model_structure["sub_subs"].get(sub_c, [])
                                
                                default_sub_desc = ""
                                if sub_c == "사업추진 여건": default_sub_desc = "정부 정책과의 일치성, 추진 의지, 지역 주민 및 지자체의 태도 등을 평가합니다."
                                elif sub_c == "정책효과": default_sub_desc = "일자리 창출 효과, 주민 생활 여건 향상, 환경성 및 안전성 영향 등을 평가합니다."
                                elif sub_c == "지역 낙후도": default_sub_desc = "개발 수준 및 낙후 상태를 정량적으로 비교 분석합니다."
                                elif sub_c == "지역경제 파급효과": default_sub_desc = "지역 내 총생산, 생산 유발, 고용 유발 효과 등을 평가합니다."
                                
                                key_cached_sub = f"edit_yeta_desc_{sub_c}"
                                sub_desc_val = st.text_input(
                                    f"'{mc} ➔ {sub_c}' 요인 설명",
                                    value=st.session_state.get(key_cached_sub, default_sub_desc),
                                    key=f"yeta_desc_input_{sub_c}"
                                )
                                definitions_map[sub_c] = sub_desc_val
                                st.session_state[key_cached_sub] = sub_desc_val
                                
                                if sub_subs:
                                    for t3 in sub_subs:
                                        default_t3_desc = ""
                                        if t3 == "정책일치성 등 내부여건": default_t3_desc = "상위 계획과의 부합성 및 추진 체계의 준비 정도를 평가합니다."
                                        elif t3 == "지역주민 사업태도 등 외부여건": default_t3_desc = "사업 대상 지역 주민의 여론 및 지자체의 추진 태도를 평가합니다."
                                        elif t3 == "일자리 효과": default_t3_desc = "건설 단계 및 운영 단계의 신규 고용 창출 능력을 평가합니다."
                                        
                                        key_cached_t3 = f"edit_yeta_desc_{t3}"
                                        t3_desc_val = st.text_input(
                                            f"↳ '{sub_c} ➔ {t3}' 요인 설명",
                                            value=st.session_state.get(key_cached_t3, default_t3_desc),
                                            key=f"yeta_desc_input_{t3}"
                                        )
                                        definitions_map[t3] = t3_desc_val
                                        st.session_state[key_cached_t3] = t3_desc_val

        with tab3:
            st.markdown("#### 3. 응답자 수집 정보 및 그룹 분류")
            with st.container(border=True):
                st.markdown("**그룹 분류 문항 설정**")
                default_type_q = "귀하의 소속은 어떻게 되십니까?"
                default_type_opts = "전문가, 일반, 공무원, 기타"

                if "edit_yeta_type_questions" not in st.session_state:
                    st.session_state["edit_yeta_type_questions"] = [{"q": default_type_q, "opts": default_type_opts}]

                type_questions_state = st.session_state["edit_yeta_type_questions"]
                num_types = len(type_questions_state)

                col1, col2, col3 = st.columns([6, 2, 2])
                with col2:
                    if st.button("+ 문항 추가", use_container_width=True, disabled=num_types >= 3, key="yeta_add_q_dyn"):
                        st.session_state["edit_yeta_type_questions"].append({"q": "", "opts": ""})
                        st.rerun()
                with col3:
                    if st.button("- 문항 삭제", use_container_width=True, disabled=num_types <= 1, key="yeta_rem_q_dyn"):
                        st.session_state["edit_yeta_type_questions"].pop()
                        st.rerun()

                type_questions = []
                for i in range(num_types):
                    st.markdown(f"**{i+1}.**")
                    q_label = "그룹 분류 질문 제목" if i == 0 else "추가 설문 문항"
                    opts_label = "보기 옵션 (콤마로 구분)"

                    q_val = st.text_input(f"{q_label} ({i+1})", value=type_questions_state[i]["q"], key=f"yeta_dyn_tq_q_{i}")
                    opts_val = st.text_input(f"{opts_label} ({i+1})", value=type_questions_state[i]["opts"], key=f"yeta_dyn_tq_opts_{i}")

                    type_questions_state[i]["q"] = q_val
                    type_questions_state[i]["opts"] = opts_val
                    type_questions.append({"q": q_val, "opts": [x.strip() for x in opts_val.split(",") if x.strip()]})

            st.markdown("#### 4. 온라인 배포 및 구글 시트 연동 설정")
            if st.session_state.user_id is None:
                st.warning("온라인 배포 및 구글 시트 연동은 회원 전용 기능입니다. 로그인해 주세요.")
            else:
                survey_admin_email = st.text_input("설문 담당자 이메일 (구글 드라이브 소유자 권한 부여용)", value=st.session_state.get("edit_yeta_admin_email", st.session_state.user_id))
                st.session_state.edit_yeta_admin_email = survey_admin_email

                existing_id = st.session_state.yeta_editing_survey_id

                if existing_id:
                    st.info(f"현재 **기존 설문 수정 모드**입니다. 수정한 설정은 기존 연동 시트에 반영됩니다.\n\n**연동된 시트 ID:** {existing_id}")
                    existing_sheet_id_input = existing_id
                else:
                    past_surveys = []
                    try:
                        import sqlite3
                        conn = sqlite3.connect('users.db')
                        c = conn.cursor()
                        c.execute("SELECT title, survey_id, created_at FROM admin_surveys WHERE admin_id=? AND title LIKE '[예타]%' ORDER BY created_at DESC", (st.session_state.user_id,))
                        past_surveys = c.fetchall()
                        conn.close()
                    except Exception:
                        pass

                    existing_sheet_id_input = ""
                    show_manual_input = True

                    if len(past_surveys) > 0:
                        deploy_option = st.radio(
                            "배포 방식을 선택해 주세요.",
                            options=[
                                "새로운 구글 시트 URL 연동 (신규 발급)",
                                "기존 배포했던 설문 URL 재사용 (덮어쓰기)"
                            ],
                            index=0,
                            key="yeta_deploy_option_radio_new"
                        )
                        st.write("")

                        if "재사용" in deploy_option:
                            show_manual_input = False
                            st.markdown("##### ⚙️ 재사용할 기존 설문 선택")
                            survey_options = {f"{row[0]} ({row[2][:16]})" : row[1] for row in past_surveys}
                            selected_survey_label = st.selectbox(
                                "과거에 배포했던 설문 목록",
                                options=list(survey_options.keys()),
                                key="yeta_past_survey_select"
                            )
                            existing_sheet_id_input = survey_options[selected_survey_label]
                            st.info("선택한 설문의 구글 스프레드시트에 새로운 내용을 덮어씌웁니다. 기존 응답 URL은 그대로 유지됩니다.")

                    if show_manual_input:
                        st.markdown("##### ⚙️ 연동할 본인의 구글 스프레드시트 설정 *")
                        st.info("""
                        **💡 연동 방법:**
                        1. 본인의 구글 드라이브에서 **새 구글 스프레드시트**를 하나 생성합니다.
                        2. 우측 상단의 '공유' 버튼을 눌러 아래의 서비스 계정 이메일을 **편집자** (Editor)로 추가합니다.
                           * 서비스 계정 이메일: `ahp2-75@ahp2-486703.iam.gserviceaccount.com`
                        3. 생성한 스프레드시트의 **URL 주소** 또는 **시트 ID**를 복사하여 아래에 붙여넣어 주세요.
                        """)
                        if os.path.exists("manual_sheet_url_guide.png"):
                            st.image("manual_sheet_url_guide.png", caption="구글 스프레드시트 URL 주소창 복사 예시", width=650)
                        existing_sheet_id_input = st.text_input("연동할 구글 스프레드시트 URL 또는 ID *", placeholder="https://docs.google.com/spreadsheets/d/...", key="yeta_sheet_url_input")

                # Save state for preview
                preview_id = f"preview_yeta_{st.session_state.user_id}"
                preview_data = {
                    "Title": survey_title,
                    "Description": survey_desc,
                    "Admin_Email": survey_admin_email,
                    "AHP_Model_JSON": model_structure,
                    "Tier_Level": 3,
                    "Demographics": {"type_questions": type_questions},
                    "Is_Yeta": True,
                    "Definitions": definitions_map
                }

                import json
                os.makedirs("temp_previews", exist_ok=True)
                with open(f"temp_previews/{preview_id}.json", "w", encoding="utf-8") as f:
                    json.dump(preview_data, f, ensure_ascii=False)

                col_p1, col_p2 = st.columns(2)
                with col_p1:
                    # Preview Link
                    preview_link_html = f"""
                    <a href="/?preview_id={preview_id}" target="_blank" style="text-decoration: none;">
                        <div style="
                            display: flex;
                            align-items: center;
                            justify-content: center;
                            width: 100%;
                            padding: 0.375rem 0.75rem;
                            border: 1px solid rgba(49, 51, 63, 0.2);
                            border-radius: 4px;
                            background-color: #ffffff;
                            color: #31333f;
                            font-size: 14px;
                            font-weight: 400;
                            line-height: 1.6;
                            cursor: pointer;
                            text-align: center;
                            box-sizing: border-box;
                            transition: border-color 0.2s, color 0.2s, background-color 0.2s;
                        "
                        onmouseover="this.style.borderColor='#ff4b4b'; this.style.color='#ff4b4b';"
                        onmouseout="this.style.borderColor='rgba(49, 51, 63, 0.2)'; this.style.color='#31333f';"
                        >
                            👁️ 설문지 응답 화면 미리보기
                        </div>
                    </a>
                    """
                    st.markdown(preview_link_html, unsafe_allow_html=True)

                with col_p2:
                    deploy_btn_label = "🚀 배포 및 구글 시트 연동 (수정 내용 적용)" if existing_id else "🚀 배포 및 구글 시트 연동"
                    if st.button(deploy_btn_label, type="primary", use_container_width=True, key="yeta_deploy_btn"):
                        target_sheet_id = existing_sheet_id_input.strip()
                        if "docs.google.com/spreadsheets" in target_sheet_id:
                            parts = target_sheet_id.split("/d/")
                            if len(parts) > 1:
                                target_sheet_id = parts[1].split("/")[0]

                        if not target_sheet_id:
                            st.error("연동할 구글 스프레드시트 URL 또는 ID를 입력해 주세요.")
                        else:
                            with st.spinner("구글 스프레드시트 생성 및 설문지 연동 중..."):
                                try:
                                    from survey_manager_v3 import create_yeta_survey_sheet_v3
                                    import sqlite3

                                    new_sheet_id = create_yeta_survey_sheet_v3(
                                        title=survey_title,
                                        admin_email=survey_admin_email,
                                        ahp_model=model_structure,
                                        demographics={"type_questions": type_questions},
                                        definitions_map=definitions_map,
                                        description=survey_desc,
                                        existing_sheet_id=target_sheet_id,
                                        user_id=st.session_state.user_id
                                    )

                                    if new_sheet_id:
                                        conn = sqlite3.connect('users.db')
                                        cur = conn.cursor()
                                        if existing_id:
                                            cur.execute("UPDATE admin_surveys SET title = ? WHERE survey_id = ?", (f"[예타] {survey_title}", existing_id))
                                        else:
                                            cur.execute("INSERT OR IGNORE INTO admin_surveys (survey_id, title, admin_id, created_at) VALUES (?, ?, ?, datetime('now'))",
                                                        (new_sheet_id, f"[예타] {survey_title}", st.session_state.user_id))
                                        conn.commit()
                                        conn.close()

                                        st.session_state.yeta_editing_survey_id = new_sheet_id
                                        st.session_state._survey_cache_dirty_yeta = True

                                        base_url = "https://ahpkrj.streamlit.app/"
                                        try:
                                            base_url = st.query_params.get("base_url", "https://ahpkrj.streamlit.app/")
                                            if isinstance(base_url, list): base_url = base_url[0]
                                        except:
                                            pass
                                        if not base_url.endswith("/"):
                                            base_url += "/"

                                        link = f"{base_url}?survey_id={new_sheet_id}"
                                        st.success("🎉 예타 AHP 설문지 배포가 성공적으로 완료되었습니다!")
                                        st.markdown(f"**🔗 응답자 배포용 설문조사 링크:** [{link}]({link})")
                                        st.code(link)
                                    else:
                                        st.error("구글 시트 연동에 실패했습니다. 구글 계정 권한 또는 서비스 계정 설정을 확인해 주세요.")
                                except Exception as e:
                                    st.error(f"오류 발생: {e}")

    # =========================================================================
    # 실시간 응답 현황 탭
    # =========================================================================
    with tab_live_response:
        st.header("실시간 응답 현황")
        selected_sheet_id = None
        
        if st.session_state.user_id is None:
            st.warning(" **실시간 응답 현황 기능은 회원 전용 서비스입니다.**")
            st.info("무료 회원가입 및 로그인을 완료하시면 본인이 배포한 설문지의 실시간 응답 상태 및 누적 데이터를 모니터링하고 다운로드할 수 있습니다. (무료 회원도 기능 제한 없이 모든 기능 사용 가능)  \n**좌측 사이드바의 로그인/회원가입 패널**을 이용해 주세요.")
        else:
            # DB에서 해당 관리자가 생성한 설문 목록 조회

            try:
                sync_short_codes_from_gs()
            except Exception:
                pass

            admin_surveys = []
            try:
                conn = get_db_connection('users.db')
                cur = conn.cursor()
                cur.execute("SELECT survey_id, title, created_at FROM admin_surveys WHERE admin_id = ? ORDER BY created_at DESC", (st.session_state.user_id,))
                sqlite_surveys = cur.fetchall()
                conn.close()
                
                gs_surveys = []
                try:
                    from survey_manager import get_admin_surveys_from_gsheet
                    gs_surveys = get_admin_surveys_from_gsheet(st.session_state.user_id)
                except Exception:
                    pass
                
                merged_surveys = {}
                for s in gs_surveys + sqlite_surveys:
                    if s[0] not in merged_surveys:
                        merged_surveys[s[0]] = s
                admin_surveys = list(merged_surveys.values())
                admin_surveys.sort(key=lambda x: x[2], reverse=True)
            except Exception as e:
                st.error(f"설문 목록 조회 실패: {e}")

            if not admin_surveys:
                st.warning("배포된 설문지가 존재하지 않습니다. '온라인 설문지 제작' 탭에서 설문을 먼저 배포해 주세요.")
            else:
                # 로그인한 아이디에 맞춰 본인의 설문들만 드롭다운에 노출시킵니다.
                survey_options = {f"{row[1]} ({row[2]})": row[0] for row in admin_surveys}
                selected_label = st.selectbox(
                    "실시간 현황을 확인할 설문 선택",
                    list(survey_options.keys()),
                    key="tab3_survey_select"
                )
                selected_sheet_id = survey_options[selected_label]
                
                selected_survey_info = next(s for s in admin_surveys if s[0] == selected_sheet_id)
                survey_title = selected_survey_info[1]
                created_at = selected_survey_info[2]
                
                st.success(f" 현재 선택된 설문: **{survey_title}** (배포일시: {created_at})")
                st.divider()

        # 대시보드 렌더링
        if selected_sheet_id:

            st.info(" 구글 API 일일 호출 할당량 초과(Quota Exceeded 429 에러)를 방지하기 위해, 데이터는 자동으로 불러오지 않습니다. 아래 버튼을 눌러 최신 데이터를 갱신하세요.")
            if st.button("🔄 실시간 설문 대시보드 및 응답 데이터 불러오기 / 새로고침", type="primary"):
                from survey_manager import get_survey_stats, get_survey_gspread_client
                with st.spinner("실시간 설문 현황 로딩 중..."):
                    # 1. Stats Loading
                    st.session_state["survey_stats"] = get_survey_stats(selected_sheet_id.strip())
                    
                    # 2. Raw Data Loading
                    g_client = get_survey_gspread_client()
                    if g_client:
                        try:
                            spreadsheet = g_client.open_by_key(selected_sheet_id.strip())
                            raw_sheet = spreadsheet.worksheet("Raw_Data")
                            all_rows = raw_sheet.get_all_values()

                            try:
                                demo_sheet = spreadsheet.worksheet("Demographic_Data")
                                demo_rows = demo_sheet.get_all_values()
                            except Exception:
                                demo_rows = []

                            if len(all_rows) > 0:
                                headers = all_rows[0]
                                rows = all_rows[1:]
                                st.session_state["live_df"] = pd.DataFrame(rows, columns=headers)

                                if len(demo_rows) > 0:
                                    demo_headers = demo_rows[0]
                                    demo_vals = demo_rows[1:]
                                    st.session_state["demo_df"] = pd.DataFrame(demo_vals, columns=demo_headers)
                                else:
                                    st.session_state["demo_df"] = None
                            else:
                                st.session_state["live_df"] = pd.DataFrame()
                                st.session_state["demo_df"] = None

                        except Exception as g_err:
                            st.error(f"구글 시트에서 데이터를 읽어오는 중 에러 발생: {g_err}")
                            st.session_state["live_df"] = None
                    else:
                        st.warning("구글 Sheets API 클라이언트 연결 실패로 인해 구글 시트 내 데이터를 직접 다운로드할 수 없습니다.")
                        st.session_state["live_df"] = None

            if "survey_stats" in st.session_state:
                stats = st.session_state["survey_stats"]
                col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
                with col_stat1:
                    st.metric("총 접속자 수 (Visits)", f"{stats['visits']}" + "명")
                with col_stat2:
                    st.metric("완료 응답자 수 (Completed)", f"{stats['completed']}" + "명")
                with col_stat3:
                    st.metric("일관성 초과 중단자 (CR Fail)", f"{stats['abandoned_cr']}" + "회")
                with col_stat4:
                    st.metric("단순 이탈 중단자 (Bounce)", f"{stats['abandoned_bounce']}" + "명")

                # 시각화 차트 추가

                chart_data = pd.DataFrame({
                    "구분": ["응답 완료", "일관성 초과 중단", "단순 페이지 이탈"],
                    "인원수": [stats['completed'], stats['abandoned_cr'], stats['abandoned_bounce']]
                })

                fig_stats = px.bar(
                    chart_data,
                    x="구분",
                    y="인원수",
                    text="인원수",
                    color="구분",
                    color_discrete_map={
                        "응답 완료": "#2E7D32",
                        "일관성 초과 중단": "#C62828",
                        "단순 페이지 이탈": "#EF6C00"
                    },
                    title="설문 참여 상태별 분포"
                )
                fig_stats.update_layout(showlegend=False)
                st.plotly_chart(fig_stats, use_container_width=True)

            if "live_df" in st.session_state and st.session_state["live_df"] is not None:
                live_df = st.session_state["live_df"]
                demo_df = st.session_state.get("demo_df", None)

                # 구글 시트에서 실시간 응답 로데이터(Raw_Data) 다운로드 기능 추가
                with st.expander("📥 실시간 구글 시트 응답 데이터 다운로드 센터", expanded=True):
                    if not live_df.empty:
                        st.success(f"구글 스프레드시트에서 실시간 응답 데이터를 성공적으로 불러왔습니다. (Raw_Data: {len(live_df)}건" + (f", Demographic_Data: {len(demo_df)}건" if demo_df is not None else "") + ")")
                        
                        # 📊 AHP 분석 연동 단축 버튼 추가
                        if st.button("📊 이 온라인 설문 데이터로 즉시 AHP 분석 수행하기 (분석 도구로 연동)", type="primary", use_container_width=True):
                            st.session_state["selected_survey_for_analysis"] = selected_sheet_id
                            from survey_manager import load_survey_metadata
                            survey_meta = load_survey_metadata(selected_sheet_id)
                            if survey_meta:
                                ahp_model = survey_meta["AHP_Model_JSON"]
                                base_cols = ["ID", "Type"]
                                main_criteria = ahp_model.get("main", [])
                                main_pairs = []
                                for i in range(len(main_criteria)):
                                    for j in range(i + 1, len(main_criteria)):
                                        main_pairs.append(f"{main_criteria[i]}_{main_criteria[j]}")
                                main_cols = [c for c in base_cols if c in live_df.columns] + [p for p in main_pairs if p in live_df.columns]
                                
                                st.session_state["ahp_df_main"] = live_df[main_cols].copy()
                                for col in st.session_state["ahp_df_main"].columns:
                                    if col not in ["ID", "Type"]:
                                        st.session_state["ahp_df_main"][col] = pd.to_numeric(st.session_state["ahp_df_main"][col], errors='coerce')
                                
                                 # 중분류 복사
                                st.session_state["ahp_sub_dfs"] = {}
                                sub_criteria_map = ahp_model.get("subs", {})
                                for main_c, subs in sub_criteria_map.items():
                                    if len(subs) >= 2:
                                        sub_pairs = []
                                        for i in range(len(subs)):
                                            for j in range(i + 1, len(subs)):
                                                sub_pairs.append(f"{subs[i]}_{subs[j]}")
                                        sub_cols = [c for c in base_cols if c in live_df.columns] + [p for p in sub_pairs if p in live_df.columns]
                                        st.session_state["ahp_sub_dfs"][main_c] = live_df[sub_cols].copy()
                                        for col in st.session_state["ahp_sub_dfs"][main_c].columns:
                                            if col not in ["ID", "Type"]:
                                                st.session_state["ahp_sub_dfs"][main_c][col] = pd.to_numeric(st.session_state["ahp_sub_dfs"][main_c][col], errors='coerce')
                                                
                                st.session_state["ahp_sheet_names"] = ["Main_Criteria"] + list(st.session_state["ahp_sub_dfs"].keys())
                                st.info("📊 데이터 분석 준비가 완료되었습니다! **상단의 '📊 AHP 분석 도구' 탭**을 선택하고 **'🌐 배포된 온라인 설문 데이터 연동'** 라디오 버튼을 선택하여 분석 결과를 바로 확인하십시오.")

                        tab_raw, tab_demo = st.tabs(["📊 Raw_Data (AHP 쌍대비교 데이터)", "👤 Demographic_Data (인구통계/사전순위)"])
                        with tab_raw:
                            st.dataframe(live_df, use_container_width=True)
                        with tab_demo:
                            if demo_df is not None:
                                st.dataframe(demo_df, use_container_width=True)
                            else:
                                st.info("수집된 인구통계 데이터가 없거나 Demographic_Data 시트가 생성되지 않았습니다.")

                        # Excel 및 CSV 내보내기 버튼 제공
                        import io

                        # 1. Excel 내보내기 (두 개의 시트를 모두 포함)
                        excel_buffer = io.BytesIO()
                        with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                            from survey_manager import load_survey_metadata
                            survey_meta = load_survey_metadata(selected_sheet_id)
                            parsed_ok = False
                            
                            if survey_meta:
                                ahp_model = survey_meta.get("AHP_Model_JSON", {})
                                tier_level = int(survey_meta.get("Tier_Level", 2))
                                base_cols = ["ID", "Type"]
                                main_criteria = ahp_model.get("main", [])
                                main_pairs = []
                                for i in range(len(main_criteria)):
                                    for j in range(i + 1, len(main_criteria)):
                                        main_pairs.append(f"{main_criteria[i]}_{main_criteria[j]}")
                                main_cols = [c for c in base_cols if c in live_df.columns] + [p for p in main_pairs if p in live_df.columns]
                                
                                if len(main_cols) > 2:
                                    df_main_dl = live_df[main_cols].copy()
                                    df_main_dl.to_excel(writer, index=False, sheet_name="Main_Criteria")
                                    
                                    sub_criteria_map = ahp_model.get("subs", {})
                                    for main_c, subs in sub_criteria_map.items():
                                        if len(subs) >= 2:
                                            sub_pairs = []
                                            for i in range(len(subs)):
                                                for j in range(i + 1, len(subs)):
                                                    sub_pairs.append(f"{subs[i]}_{subs[j]}")
                                            sub_cols = [c for c in base_cols if c in live_df.columns] + [p for p in sub_pairs if p in live_df.columns]
                                            df_sub_dl = live_df[sub_cols].copy()
                                            df_sub_dl.to_excel(writer, index=False, sheet_name=main_c[:31])
                                            
                                    if tier_level == 3:
                                        sub_sub_map = ahp_model.get("sub_subs", {})
                                        for main_c, subs in sub_criteria_map.items():
                                            for sub_c in subs:
                                                sub_subs = sub_sub_map.get(sub_c, [])
                                                if len(sub_subs) >= 2:
                                                    sub_sub_pairs = []
                                                    for i in range(len(sub_subs)):
                                                        for j in range(i + 1, len(sub_subs)):
                                                            sub_sub_pairs.append(f"{sub_subs[i]}_{sub_subs[j]}")
                                                    ss_cols = [c for c in base_cols if c in live_df.columns] + [p for p in sub_sub_pairs if p in live_df.columns]
                                                    df_ss_dl = live_df[ss_cols].copy()
                                                    df_ss_dl.to_excel(writer, index=False, sheet_name=sub_c[:31])
                                    parsed_ok = True
                            
                            if not parsed_ok:
                                live_df.to_excel(writer, index=False, sheet_name='Raw_Data')
                            else:
                                live_df.to_excel(writer, index=False, sheet_name='Raw_Data_Dump')
                                
                            if demo_df is not None:
                                demo_df.to_excel(writer, index=False, sheet_name='Demographic_Data')

                        col_dl1, col_dl2 = st.columns(2)
                        with col_dl1:
                            st.download_button(
                                "📥 실시간 응답 Excel 다운로드 (.xlsx)",
                                data=excel_buffer.getvalue(),
                                file_name=f"Survey_Live_Data_{selected_sheet_id.strip()[:6]}.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                use_container_width=True,
                                type="primary"
                            )
                        # 2. CSV 내보내기 (Raw_Data 우선 내보내기)
                        csv_buffer = io.StringIO()
                        live_df.to_csv(csv_buffer, index=False, header=True)
                        with col_dl2:
                            st.download_button(
                                "📥 실시간 응답 CSV 다운로드 (.csv)",
                                data=csv_buffer.getvalue().encode('utf-8-sig'),
                                file_name=f"Survey_Live_Data_{selected_sheet_id.strip()[:6]}.csv",
                                mime="text/csv",
                                use_container_width=True
                            )
                    else:
                        st.info("구글 시트에 수집된 응답 로데이터가 아직 비어 있습니다.")

            # 로컬 안전 백업 데이터 조회 및 추출 유틸리티
            try:
                conn = get_db_connection('users.db')
                backup_df = pd.read_sql_query(
                    "SELECT id, respondent_id, response_json, created_at FROM survey_backup_responses WHERE survey_id = ?",
                    conn, params=(selected_sheet_id.strip(),)
                )
                conn.close()

                if not backup_df.empty:
                    with st.expander("🛡️ 서버 로컬 안전 백업 관리 센터"):
                        st.success(f"구글 시트 연동과 관계없이 서버 로컬 데이터베이스에 저장된 안전 백업 데이터가 총 {len(backup_df)}건 존재합니다.")
                        st.dataframe(backup_df[["id", "respondent_id", "created_at"]], use_container_width=True)

                        # 전체 로 데이터 복구 엑셀/CSV 데이터 빌드
                        recovered_raw_rows = []
                        recovered_demo_rows = []
                        for idx_b, r_b in backup_df.iterrows():
                            payload = json.loads(r_b["response_json"])
                            if "raw_row_data" in payload:
                                recovered_raw_rows.append(payload["raw_row_data"])
                            elif "row_data" in payload:
                                # 하위 호환성
                                recovered_raw_rows.append(payload["row_data"])

                            if "demo_row_data" in payload:
                                recovered_demo_rows.append(payload["demo_row_data"])

                        if recovered_raw_rows:
                            import io

                            # 헤더 복구 로직 추가
                            raw_headers = None
                            demo_headers = None
                            from survey_manager import load_survey_metadata
                            survey_meta = load_survey_metadata(selected_sheet_id.strip())
                            if survey_meta:
                                ahp_model = survey_meta.get("AHP_Model_JSON", {})
                                demographics = survey_meta.get("Demographics", {})
                                rewards_info = survey_meta.get("Rewards_Info", {})
                                tier_level = str(survey_meta.get("Tier_Level", "2"))
                                
                                raw_headers = ["ID", "Type"]
                                main_criteria = ahp_model.get("main", [])
                                for i in range(len(main_criteria)):
                                    for j in range(i + 1, len(main_criteria)):
                                        raw_headers.append(f"{main_criteria[i]}_{main_criteria[j]}")
                                sub_criteria_map = ahp_model.get("subs", {})
                                for main_c in main_criteria:
                                    subs = sub_criteria_map.get(main_c, [])
                                    if len(subs) >= 2:
                                        for i in range(len(subs)):
                                            for j in range(i + 1, len(subs)):
                                                raw_headers.append(f"{subs[i]}_{subs[j]}")
                                if tier_level == "3":
                                    sub_sub_map = ahp_model.get("sub_subs", {})
                                    for main_c in main_criteria:
                                        subs = sub_criteria_map.get(main_c, [])
                                        for sub_c in subs:
                                            sub_subs = sub_sub_map.get(sub_c, [])
                                            if len(sub_subs) >= 2:
                                                for i in range(len(sub_subs)):
                                                    for j in range(i + 1, len(sub_subs)):
                                                        raw_headers.append(f"{sub_subs[i]}_{sub_subs[j]}")
                                raw_headers.append("제출시간")
                                
                                demo_headers = ["ID", "Type"]
                                if demographics.get("name"): demo_headers.append("성명")
                                if demographics.get("age"): demo_headers.append("연령")
                                if demographics.get("gender"): demo_headers.append("성별")
                                if demographics.get("experience"): demo_headers.append("경력년수")
                                # if demographics.get("affiliation"): demo_headers.append("소속")
                                if demographics.get("email"): demo_headers.append("이메일")
                                demo_headers.append("사전순위지정")
                                if rewards_info.get("enabled"):
                                    demo_headers.append("경품연락처" if tier_level == "3" else "답례품_연락처")
                                demo_headers.append("제출시간")

                            df_raw_backup = pd.DataFrame(recovered_raw_rows)
                            if raw_headers and len(raw_headers) == len(df_raw_backup.columns):
                                df_raw_backup.columns = raw_headers
                            elif raw_headers and len(raw_headers) > len(df_raw_backup.columns):
                                df_raw_backup.columns = raw_headers[:len(df_raw_backup.columns)]
                                
                            df_demo_backup = None
                            if recovered_demo_rows:
                                df_demo_backup = pd.DataFrame(recovered_demo_rows)
                                if demo_headers and len(demo_headers) == len(df_demo_backup.columns):
                                    df_demo_backup.columns = demo_headers
                                elif demo_headers and len(demo_headers) > len(df_demo_backup.columns):
                                    df_demo_backup.columns = demo_headers[:len(df_demo_backup.columns)]

                            # Excel로 백업 데이터를 템플릿 구조에 맞춰 분할하여 다운로드
                            if survey_meta and "AHP_Model_JSON" in survey_meta:
                                excel_backup_buffer = export_to_template_excel(df_raw_backup, df_demo_backup, survey_meta["AHP_Model_JSON"], survey_meta.get("Tier_Level", 2))
                            else:
                                excel_backup_buffer = io.BytesIO()
                                with pd.ExcelWriter(excel_backup_buffer, engine='openpyxl') as writer:
                                    df_raw_backup.to_excel(writer, index=False, header=bool(raw_headers), sheet_name='Raw_Data')
                                    if df_demo_backup is not None:
                                        df_demo_backup.to_excel(writer, index=False, header=bool(demo_headers), sheet_name='Demographic_Data')

                            col_b_dl1, col_b_dl2 = st.columns(2)
                            with col_b_dl1:
                                st.download_button(
                                    "📥 로컬 백업 Excel 다운로드 (.xlsx)",
                                    data=excel_backup_buffer.getvalue(),
                                    file_name=f"Backup_Recovery_{selected_sheet_id.strip()[:6]}.xlsx",
                                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                    use_container_width=True,
                                    type="primary"
                                )

                            with col_b_dl2:
                                # CSV 파일 형태로 복구 파일 내보내기 (Raw_Data 우선)
                                output_csv = io.StringIO()
                                df_raw_backup.to_csv(output_csv, index=False, header=bool(raw_headers))
                                st.download_button(
                                    "📥 로컬 백업 Raw_Data CSV 다운로드 (.csv)",
                                    data=output_csv.getvalue().encode('utf-8-sig'),
                                    file_name=f"Backup_Recovery_Raw_{selected_sheet_id.strip()[:6]}.csv",
                                    mime="text/csv",
                                    use_container_width=True
                                )
                else:
                    st.caption("이 설문지에 등록된 로컬 서버 백업 데이터가 없습니다. (모든 데이터 정상 적재)")
            except Exception as err:
                st.caption(f"로컬 백업 조회 불가: {err}")


    # =========================================================================
    # TAB 3: Guidelines Guide
    # =========================================================================
    with tab_guide:
        st.markdown(f"""
        <div style="padding: 10px 20px;">
        <h3 style="color: #1e3a8a; border-bottom: 2px solid #e2e8f0; padding-bottom: 8px;">1. AHP 종합평가의 개요 및 목적</h3>
        <p style="font-size: 1.05rem; line-height: 1.8;">
        예비타당성조사에서 AHP는 경제성, 정책성, 지역균형발전 분석 등<br>다양한 평가항목의 결과를 토대로 <b>다기준분석</b>을 수행하여,<br>사업의 종합적인 타당성을 계량화된 수치로 판단하는 의사결정 도구입니다.<br><br>이를 통해 평가자 간의 이견을 종합하고, 의사결정 과정의 투명성과 객관성을 확보하여<br>공공투자 사업의 시행 여부를 결정합니다.
        </p>

        <h3 style="color: #1e3a8a; border-bottom: 2px solid #e2e8f0; padding-bottom: 8px; margin-top: 35px;">2. AHP 평가 계층구조 설계</h3>
        <ul style="font-size: 1.05rem; line-height: 1.8; margin-bottom: 10px;">
        <li style="margin-bottom: 8px;"><b>제1계층 (대분류):</b><br>종합평가를 구성하는 주요 부문으로 경제성 분석, 정책성 분석, 지역균형발전 분석(수도권 사업의 경우 제외) 등으로 나뉩니다.</li>
        <li style="margin-bottom: 8px;"><b>제2·3계층 (세부 항목):</b><br>정책성 분석 하위의 사업추진 여건(정책 일치성, 주민 사업태도 등)과 정책효과(일자리 효과, 환경성, 안전성 등), 지역균형발전 하위의 지역낙후도 및 파급효과 등으로 구성됩니다.</li>
        <li><b>최하위 대안:</b><br>최종 의사결정을 위한 최하위 계층은 철저히 <b>'사업 시행'과 '사업 미시행'</b> 두 가지 대안으로 고정하여 평가를 수행합니다.</li>
        </ul>

        <h3 style="color: #1e3a8a; border-bottom: 2px solid #e2e8f0; padding-bottom: 8px; margin-top: 35px;">3. 부문별 가중치 적용 기준 (상수합법)</h3>
        <p style="font-size: 1.05rem; line-height: 1.8;">
        제1계층의 가중치는 응답자의 자의성을 줄이기 위해 100점 만점을 기준으로<br>평가자가 직접 분배하는 <b>상수합법(Constant-Sum)</b>을 사용하여 측정합니다.<br><br>예비타당성조사 수행 총괄지침에 명시된 주요 사업유형별 가중치 허용 범위는 다음과 같습니다.
        </p>
        <ul style="font-size: 1.05rem; line-height: 1.8; background-color: #f8fafc; padding: 15px 20px 15px 40px; border-radius: 8px;">
        <li><b>건설사업 (비수도권 유형):</b> 경제성 30~45%, 정책성 25~40%, 지역균형발전 30~40%</li>
        <li><b>건설사업 (수도권 유형):</b> 경제성 60~70%, 정책성 30~40% (지역균형발전 항목 제외)</li>
        <li><b>정보화/R&D 사업 (B/C 분석 시):</b> 경제성 40~50%, 기술성 30~40%, 정책성 20~30%</li>
        </ul>

        <h3 style="color: #1e3a8a; border-bottom: 2px solid #e2e8f0; padding-bottom: 8px; margin-top: 35px;">4. 조사 방법 및 조사 표본(전문가 구성)</h3>
        <ul style="font-size: 1.05rem; line-height: 1.8;">
        <li style="margin-bottom: 10px;"><b>조사 표본 (평가진 규모 및 구성):</b><br>평가의 전문성과 객관성을 확보하기 위해 사업의 특성에 맞는 관련 분야(경제, 정책, 기술, 지역 등)의<br>학계 및 연구계 전문가 등 <b>보통 7~10인 내외의 전문가 패널</b>을 구성하여 설문을 진행합니다.</li>
        <li><b>조사 방법 (정보 제공 및 브리핑):</b><br>단순한 설문조사가 아닌, 사업의 개요와 선행 분석 결과(B/C 비율, 정책성 및 지역균형 분석 자료 등)가 모두 수록된 <b>'AHP 자료집'</b>을 전문가들에게 제공합니다.<br>이를 바탕으로 평가 회의(브리핑) 또는 서면/온라인 방식을 통해 충분한 정보를 숙지한 상태에서 평가를 실시하게 됩니다.</li>
        </ul>

        <h3 style="color: #1e3a8a; border-bottom: 2px solid #e2e8f0; padding-bottom: 8px; margin-top: 35px;">5. 설문 수행 및 점수 산정 (일관성 검증 및 극단값 배제)</h3>
        <ul style="font-size: 1.05rem; line-height: 1.8;">
        <li style="margin-bottom: 10px;"><b>9점 척도 쌍대비교:</b><br>세부 항목 간의 상대적 중요도 및 대안의 선호도는 기본적으로 9점 척도를 활용하여 쌍대비교(Pairwise Comparison)를 수행합니다.</li>
        <li style="margin-bottom: 10px;"><b>객관적 지표의 표준점수화:</b><br>주관적 편향을 막기 위해 경제성(B/C 비율)과 지역낙후도 지수(LIR)는 정해진 수학적 전환식을 적용하여 일괄 반영합니다.</li>
        <li style="margin-bottom: 10px;"><b>일관성 검증 (CR):</b><br>실무적 한계를 고려해 <b>CR이 0.15 이하</b>인 경우에만 신뢰할 수 있는 유효 응답으로 인정하며, 이를 초과할 시 환류(Feedback)하여 재조사 등을 요구합니다.</li>
        <li><b>극단값 배제 지침:</b><br>집단 의사결정 시 점수 왜곡을 방지하고자, 최종 합산 과정에서 사업 시행 대안에 대해 <b style="color: #ef4444;">가장 높은 점수를 준 1인(최고점)과 가장 낮은 점수를 준 1인(최저점)의 응답을 배제</b>하고, 나머지 결과의 기하평균을 구합니다.</li>
        </ul>

        <h3 style="color: #1e3a8a; border-bottom: 2px solid #e2e8f0; padding-bottom: 8px; margin-top: 35px;">6. 최종 타당성 판단 기준 (회색영역)</h3>
        <ul style="font-size: 1.05rem; line-height: 1.8;">
        <li style="margin-bottom: 10px;">기본적으로 산출된 <b>최종 AHP 종합점수가 0.5 이상이면 사업 시행이 타당성(바람직함)이 있는 것</b>으로 판정합니다.</li>
        <li><b>회색영역(Gray Area) 운용:</b><br>의사결정의 강건성을 확보하기 위해 종합평점이 0.5 부근인 특정 구간(예: 0.473~0.527)을 '회색영역'으로 규정합니다.<br>점수가 이 구간에 위치하거나 평가자 간 의견 불일치가 뚜렷할 경우 획일적인 0.5 기준 적용을 지양하고, '약간 신중', '신중' 등의 세부 판단을 거쳐 최종 사업 추진 여부를 결정하도록 권고합니다.</li>
        </ul>

        <hr style="margin-top: 45px; margin-bottom: 25px; border: 0; border-top: 1px solid #e5e7eb;">
        
        <h3 style="color: #0f766e; margin-bottom: 15px;">7. 관련 지침 및 가이드라인 공식 다운로드 링크</h3>
        <p style="font-size: 1.05rem; line-height: 1.8; margin-bottom: 20px;">
        상기 AHP 수행 기준의 근거가 되는 공식 가이드 문서는 다음의 웹사이트에서 원문을 다운로드하실 수 있습니다.
        </p>
        
        <div style="background-color: #f8fafc; padding: 15px; border-radius: 8px; border-left: 4px solid #0f766e; margin-bottom: 15px;">
        <a href="https://pimac.kdi.re.kr/study/study_list.jsp?classcd=F1" target="_blank" style="font-size: 1.1rem; font-weight: bold; color: #0284c7; text-decoration: none;">KDI 공공투자관리센터 (PIMAC)</a>
        <p style="margin-top: 5px; color: #475569; font-size: 0.95rem; line-height: 1.6;">각 사업 부문별(일반, 도로/철도 등) 예비타당성조사 수행 세부지침 및 역대 조사보고서 다운로드</p>
        </div>
        
        <div style="background-color: #f8fafc; padding: 15px; border-radius: 8px; border-left: 4px solid #0f766e; margin-bottom: 15px;">
        <a href="https://www.kipf.re.kr/gmac/Publication/Finance/kiPublish/CA6/Center/list.do" target="_blank" style="font-size: 1.1rem; font-weight: bold; color: #0284c7; text-decoration: none;">한국조세재정연구원 정부투자분석센터 (KIPF GMAC)</a>
        <p style="margin-top: 5px; color: #475569; font-size: 0.95rem; line-height: 1.6;">정보화 등 특정 부문 사업에 대한 세부 가이드라인 및 착수회의/조사보고서 다운로드</p>
        </div>
        
        <div style="background-color: #f8fafc; padding: 15px; border-radius: 8px; border-left: 4px solid #0f766e;">
        <a href="https://www.law.go.kr" target="_blank" style="font-size: 1.1rem; font-weight: bold; color: #0284c7; text-decoration: none;">국가법령정보센터</a>
        <p style="margin-top: 5px; color: #475569; font-size: 0.95rem; line-height: 1.6;">법적 구속력을 갖춘 기획재정부 훈령인 「예비타당성조사 운용지침」 및 「예비타당성조사 수행 총괄지침」 전문 열람</p>
        </div>
        </div>
        """, unsafe_allow_html=True)

    # =========================================================================
    # TAB 4: B2B Pricing & Payment (Hybrid Pricing Applied)
    # =========================================================================
    with tab_pricing:
        st.markdown("## 서비스 요금 안내 <span style='font-size: 0.95rem; font-weight: 500; color: #0284c7; margin-left: 16px; background: #e0f2fe; padding: 6px 14px; border-radius: 20px; vertical-align: middle; box-shadow: 0 1px 2px rgba(0,0,0,0.05);'>💳 연구비/법인카드 및 계산서 100% 지원</span>", unsafe_allow_html=True)

        col_p1, col_p2, col_p3, col_p4 = st.columns(4)
        user_id = st.session_state.get("user_id")

        # 1. 무료 체험판
        with col_p1:
            inner_1 = """
                <h3 style='margin-top: 0 !important; margin-bottom: 0;'>무료 체험판</h3>
                <span style='color: #888; font-size: 1.1rem;'>기본 제공</span>
                <h2 style='margin-top: 15px; margin-bottom: 5px; color: #ff4b4b;'>0원</h2>
                <p style='font-size: 0.85rem; color: #666; min-height: 40px;'>예타 분석 솔루션의 핵심 연산과 결과물 구성을 사전에 시뮬레이션할 수 있는 무료 버전입니다.</p>
                <hr style='margin: 10px 0;'>
                <ul style='padding-left: 20px; color: #333; line-height: 1.6;'>
                    <li><span style='font-size: 0.85rem;'><b>B/C 표준점수 로그 변환 연산</b></span></li>
                    <li><span style='font-size: 0.85rem;'><b>지역낙후도 표준화지수(LIR) 변환</b></span></li>
                    <li><span style='font-size: 0.85rem;'>설문 데이터 입력 (최대 3명 제한)</span></li>
                    <li><span style='font-size: 0.85rem;'>화면 결과 리포트 출력</span></li>
                </ul>
            """
            if user_id:
                st.components.v1.html(get_yeta_portone_payment_html(user_id, "무료 체험판 (영구)", 0, 9999, inner_html=inner_1, is_best=False), height=520)
            else:
                st.components.v1.html(get_yeta_login_redirect_html("무료 체험판 (영구)", inner_html=inner_1, is_best=False), height=520)

        # 2. [Standard] 월간 이용권
        with col_p2:
            inner_2 = """
                <h3 style='margin-top: 0 !important; margin-bottom: 0;'>[Standard] 월간 이용권</h3>
                <span style='color: #888; font-size: 1.1rem;'>1개월 무제한 이용</span>
                <h2 style='margin-top: 15px; margin-bottom: 5px; color: #ff4b4b;'><span id='yeta-single-price-display-span'>300,000</span>원</h2>
                <p style='font-size: 0.85rem; color: #666; min-height: 40px;'>1개월 동안 평가자 수·분석 횟수 제한 없이 예타 AHP 전체 기능을 자유롭게 이용할 수 있습니다.</p>
                <hr style='margin: 10px 0;'>
                <ul style='padding-left: 20px; color: #333; line-height: 1.6;'>
                    <li><span style='font-size: 0.85rem;'><b>1개월간 분석 횟수 무제한</b></span></li>
                    <li><span style='font-size: 0.85rem;'>평가자 수 제한 없음 (무제한)</span></li>
                    <li><span style='font-size: 0.85rem;'>최대/최소 아웃라이어 제외 자동 연산</span></li>
                    <li><span style='font-size: 0.85rem;'>보고서 제출용 Excel 원본 내보내기</span></li>
                    <li><span style='font-size: 0.85rem;'>세금계산서 및 영수증 발행 지원</span></li>
                </ul>
            """
            if user_id:
                st.components.v1.html(get_yeta_portone_payment_html(user_id, "[Standard] 월간 이용권", 300000, 1, inner_html=inner_2, is_best=False), height=520)
            else:
                st.components.v1.html(get_yeta_login_redirect_html("[Standard] 월간 이용권", inner_html=inner_2, is_best=False), height=520)

        # 3. [Pro] 연간 이용권 (BEST)
        with col_p3:
            inner_3 = """
                <h3 style='margin-top: 0 !important; margin-bottom: 0;'>[Pro] 연간 이용권</h3>
                <span style='color: #888; font-size: 1.1rem;'>1년 무제한 이용</span>
                <h2 style='margin-top: 15px; margin-bottom: 5px; color: #ff4b4b;'>2,800,000원</h2>
                <p style='font-size: 0.85rem; color: #666; min-height: 40px;'>월간 대비 22% 절감된 비용으로 1년간 횟수 제한 없이 예타 AHP 분석과 설문 배포를 수행합니다.</p>
                <hr style='margin: 10px 0;'>
                <ul style='padding-left: 20px; color: #333; line-height: 1.6;'>
                    <li><span style='font-size: 0.85rem;'><b>1년간 분석 횟수 무제한</b></span></li>
                    <li><span style='font-size: 0.85rem;'><b>월 약 233,000원 수준 (22% 절감)</b></span></li>
                    <li><span style='font-size: 0.85rem;'>무제한 전문가 설문 및 아웃라이어 연산</span></li>
                    <li><span style='font-size: 0.85rem;'>B2B 기업용 견적서/세금계산서 발행</span></li>
                </ul>
            """
            if user_id:
                st.components.v1.html(get_yeta_portone_payment_html(user_id, "[Pro] 연간 이용권", 2800000, 12, inner_html=inner_3, is_best=True), height=520)
            else:
                st.components.v1.html(get_yeta_login_redirect_html("[Pro] 연간 이용권", inner_html=inner_3, is_best=True), height=520)

        # 4. 부가 서비스 대행
        with col_p4:
            if user_id:
                st.components.v1.html(get_yeta_portone_custom_services_html(user_id), height=520)
            else:
                st.components.v1.html(get_yeta_portone_custom_services_html(None), height=520)

        st.markdown("<br>", unsafe_allow_html=True)

        if not user_id:
            st.warning("⚠️ 결제 및 세금계산서 신청을 위해서는 로그인이 필요합니다. 메인 포털 또는 사이드바에서 로그인 후 이용해 주세요.")
        else:
            st.info(f"접속 계정: {user_id} | 라이선스 권한: {'정식 회원' if is_official else '무료 체험 회원'}")
            
            st.markdown("<div id='b2b-payment-section'></div>", unsafe_allow_html=True)
            st.write("---")
            
            with st.form("yeta_tax_form"):
                st.write("**B2B 기업/연구소 전용 지불 처리 (계좌이체 및 세금계산서 신청)**")
                st.write("세금계산서 발행 및 기관 계좌이체 승인에 필요한 정보를 입력해 주세요.")
                biz_name = st.text_input("상호 / 법인명", key="tax_biz_name")
                biz_num = st.text_input("사업자등록번호 (숫자만 입력)", key="tax_biz_num")
                rep_name = st.text_input("대표자명", key="tax_rep_name")
                address = st.text_input("사업장 주소", key="tax_address")
                biz_type = st.text_input("업태 및 종목", key="tax_biz_type")
                email = st.text_input("세금계산서 수령 이메일", key="tax_email", value=user_id if "@" in user_id else "")
                plan_choice = st.selectbox("선택 요금제 플랜", ["월간 이용권 (300,000원)", "연간 이용권 (2,800,000원)"])
                
                submit_tax = st.form_submit_button("세금계산서/인보이스 발행 요청", use_container_width=True)
                if submit_tax:
                    if not biz_name or not biz_num or not email:
                        st.error("상호명, 사업자번호, 이메일은 필수 입력 사항입니다.")
                    else:
                        try:
                            conn = get_db_connection('users.db')
                            c = conn.cursor()
                            today_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            c.execute("""
                                INSERT INTO tax_invoice_requests 
                                (user_id, biz_num, biz_name, rep_name, address, biz_type, email, plan_name, request_date, status)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, (user_id, biz_num, biz_name, rep_name, address, biz_type, email, plan_choice, today_str, "pending"))
                            conn.commit()
                            
                            # Send tax invoice email
                            send_tax_invoice_request_email(user_id, biz_num, biz_name, rep_name, address, biz_type, email, plan_choice)
                            
                            st.success("✓ 세금계산서 및 결제 요청이 접수되었습니다! 입력하신 이메일로 24시간 이내에 인보이스/견적서 발송 및 입금 계좌를 안내해 드립니다.")
                        except Exception as e:
                            st.error(f"요청 접수 실패: {str(e)}")
                        finally:
                            conn.close()

    # =========================================================================
    # TAB 5: Sign Up (Only shown when not logged in)
    # =========================================================================
    if not st.session_state.user_id:
        with tab_signup:
            st.write("### " + "AHP 마스터 예타 분석 솔루션 회원가입")
            
            agreements = signup_agreement.show_agreement_ui()
            
            s_id = st.text_input("아이디 (이메일 주소)", key="main_s_id_yeta")
            s_pw = st.text_input("비밀번호", type="password", key="main_s_pw_yeta")
            
            s_cust_type = "yeta"
            
            if st.button("가입신청", key="main_btn_signup_yeta", type="primary"):
                if not agreements.get("agree_personal_info"):
                    st.error("개인정보 수집·이용에 동의해야 가입신청할 수 있습니다.")
                elif not validate_email(s_id):
                    st.error("올바른 이메일 형식이 아닙니다.")
                elif not validate_password(s_pw):
                    st.error("비밀번호는 문자+특수문자여야 합니다.")
                else:
                    restore_from_deleted_sheet(s_id.strip())
                    if add_user(s_id.strip(), s_pw, 'temp', agree_info="Y", customer_type=s_cust_type):
                        st.success("회원가입이 완료되었습니다! 사이드바의 '로그인' 탭에서 로그인해 주시기 바랍니다.")
                        time.sleep(2)
                        st.rerun()
                    else:
                        st.error("이미 존재하는 아이디입니다.")

            st.info("🔒 **개인정보 보호 안내**\n\n예타 AHP 시스템은 사용자의 이름, 전화번호 등 불필요한 개인정보를 수집하지 않습니다. 또한 입력하신 비밀번호는 강력하게 암호화되어 저장되므로 관리자도 알 수 없습니다. 안심하고 이용해 주세요.")

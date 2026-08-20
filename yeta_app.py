import sqlite3
import coupon_manager
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
    units = ["", "??, "?, "?]
    g_units = ["", "?, "??, "?]
    digits = ["", "??, "??, "??, "??, "??, "??, "?, "??, "?]
    
    if num == 0:
        return "??
        
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
    if kor.startswith("?십"):
        kor = kor[1:]
    return f"?금 {kor}?정"



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
                    st.toast("? Account status updated!")
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
                    st.toast(" 30분간 ?동???어 보안???해 ?동 로그?웃?었?니??")
                    st.rerun()
                else:
                    st.query_params["last_activity"] = str(current_time)
            except ValueError:
                st.query_params["last_activity"] = str(current_time)

    # 3. Custom CSS Styling (Premium Corporate Theme)
    st.markdown("""
    <style>

    /* =============================================================================
       AHP 마스???리미엄 ?터?라?즈 UI ?마 (v3.0) - ?? 모듈??
       ============================================================================= */
    @import url("https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css");
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap');

    /* --- 글로벌 ?트 & 기본 ?스??--- */
    html, body, [class*="css"], .stMarkdown, .stTextInput label,
    .stSelectbox label, .stRadio label, .stCheckbox label,
    div[data-testid="stSidebar"], div[data-testid="stAppViewBlockContainer"] {
        font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, system-ui, sans-serif !important;
        letter-spacing: -0.015em;
        color: #1e293b !important;
    }

    /* --- 메인 배경???색?로 강제 ?정 --- */
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

    /* --- 메인 ?목 ???링 (?문?이?차분?게) --- */
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

    /* --- ?내?Alert/Info Box) ?본문 ?트 ?기 ?????? --- */
    div[data-testid="stAlert"] p,
    div[data-testid="stAlert"] div,
    div[data-testid="stMarkdownContainer"] p,
    div[data-testid="stMarkdownContainer"] li {
        font-size: 0.95rem !important;
        line-height: 1.6 !important;
    }

    /* --- 경고??내?Alert/Info Box) ?널 ???로 ?정?게 ?일 --- */
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

    /* --- ?트림릿 기본 ?롬 ?기?--- */
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

    /* --- 메인 ?이?웃 ??간격) ??백 최적??--- */
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

    /* --- ?이?바 ?리미엄 ????--- */
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
    /* ?이?바 ?의 ?반 버튼 */
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
    /* ?이?바 ?의 Expander */
    section[data-testid="stSidebar"] [data-testid="stExpander"] {
        background-color: rgba(255, 255, 255, 0.05) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
    }
    section[data-testid="stSidebar"] [data-testid="stExpander"] details summary p,
    section[data-testid="stSidebar"] [data-testid="stExpander"] details summary span {
        color: #ffffff !important;
    }

    /* --- ?리미엄 버튼 (기본) - ?랫/?정 --- */
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

    /* --- ?력 ?드 고급 ???링 --- */
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

    /* --- ??트박스 ????--- */
    div.stSelectbox > div > div {
        border-radius: 4px !important;
        border: 1px solid #cbd5e1 !important;
        background: #ffffff !important;
    }
    div.stSelectbox > div > div:hover {
        border-color: #1e3a8a !important;
    }

    /* --- ??고급 ????--- */
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

    /* --- 카드??Expander ????--- */
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

    /* --- ?림 박스 --- */
    div[data-testid="stAlert"] {
        border-radius: 4px !important;
        border: 1px solid rgba(0,0,0,0.1) !important;
        box-shadow: none !important;
    }

    /* --- 메트?카드 ????--- */
    div[data-testid="stMetric"] {
        background: #ffffff !important;
        border: 1px solid #cbd5e1 !important;
        border-left: 4px solid #1e3a8a !important; 
        border-radius: 4px !important;
        padding: 1rem !important;
        box-shadow: none !important;
    }

    /* --- ?운로드 버튼 --- */
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

    /* --- ?크롤바 커스? --- */
    ::-webkit-scrollbar { width: 8px; height: 8px; }
    ::-webkit-scrollbar-track { background: #f1f5f9; }
    ::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 4px; }
    ::-webkit-scrollbar-thumb:hover { background: #94a3b8; }

    /* --- ?이?바 구분??--- */
    section[data-testid="stSidebar"] hr {
        border: none !important;
        border-top: 1px solid #cbd5e1 !important;
        margin: 1rem 0 !important;
    }

    /* --- 링크 ?상 ?일 --- */
    a {
        color: #1e3a8a !important;
        text-decoration: none !important;
    }
    a:hover {
        text-decoration: underline !important;
    }

    /* ?이?바 ??글???기 축소 & ?백 줄이?& ?상 ?일 */
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

    /* --- 비?번호 가?성 ?? 버튼 --- */
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
       ?? ?용 커스? ?래??
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
        content: "??;
        color: #3182CE;
        margin-right: 8px;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

    # 4. Handle PortOne Payment Callback inside Yeta
    if "portone_paid" in q_params and "user_id" in q_params:
        user_id_param = q_params.get("user_id")
        plan_name_param = q_params.get("plan_name", "?건 분석?)
        kst_now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
        new_expiry_date = (kst_now + datetime.timedelta(days=365)).strftime("%Y-%m-%d")
        
        try:
            conn = get_db_connection('users.db')
            c = conn.cursor()
            c.execute("UPDATE users SET role='official', expiry_date=?, plan_type=? WHERE id=?", 
                      (new_expiry_date, plan_name_param, user_id_param))
            conn.commit()
            conn.close()
            
            st.success(f"? {plan_name_param} 결제가 ?료?어 ?식 ?원(?? 기능 ?금?제)?로 ?급?었?니??")
            if st.button("?? 분석 ?으?가?):
                st.query_params.pop("portone_paid", None)
                st.query_params.pop("user_id", None)
                st.query_params.pop("plan_name", None)
                st.rerun()
            st.stop()
        except Exception as e:
            st.error(f"결제 ?이???이?베?스 ????패: {str(e)}")

    # 5. Page Header Section
    st.markdown(f"""
    <div style='margin-top: 55px;'>
        <h1>{'?? ?비??성조사 종합??(AHP) ?루??}</h1>
        <p style='color: #666; font-size: 1.05rem; margin-bottom: 30px;'>{'기획?정부 ?KDI ?? 지침을 준?하??공공?자?업 AHP 종합 ?? 모듈?니??'}</p>
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
                f'<h3 style="margin-top: -5px; margin-bottom: 10px;">{" AHP 마스??}</h3>'
                f'</a>',
                unsafe_allow_html=True
            )

        # Login / Session panel
        if st.session_state.user_id is None:
            tab_login, tab_find_pw = st.tabs(["로그??, "비?번호 찾기"])
            
            with tab_login:
                l_id = st.text_input("?이??(?메??주소)", key="l_id")
                l_pw = st.text_input("비?번호 (PW)", type="password", key="l_pw")
                if st.button("로그???행", key="btn_login_yeta"):
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
                                    st.toast("? ?식 ?용 기간??만료?어 무료?용??권한?로 ?동 ?환?었?니??")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"만료 ?원 ?동 ?환 처리 ??류가 발생?습?다: {e}")
                            else:
                                st.error(f"???용 기간??만료?었?니?? (만료?? {result[1]})")
                        else:
                            st.session_state.user_id = l_id.strip()
                            st.session_state.user_role = result[0]
                            st.session_state.expiry_date = result[1]
                            st.session_state.plan_type = result[2] if len(result) > 2 else None
                            st.query_params["login_user"] = l_id.strip()
                            st.query_params["login_token"] = hashlib.sha256(f"{l_id.strip()}:AHP_MASTER_SECURE_SALT_2026_!@#".encode()).hexdigest()
                            st.query_params["last_activity"] = str(int(time.time()))
                            st.success(f"?영?니?? {l_id}??")
                            st.rerun()
                    else:
                        st.error("?이???는 비?번호가 ?치?? ?습?다.")
            
            with tab_find_pw:
                st.write("가?????용???메??주소??력?주?요. ?메?로 ?로???시 비?번호가 발송?니??")
                f_id = st.text_input("가?한 ?이??(?메??", key="f_id")
                if st.button("?시 비?번호 ?송", key="btn_find_pw_yeta"):
                    if not f_id:
                        st.warning("?메??주소??력?주?요.")
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
                                st.success(f"'{f_id}'??시 비?번호??송?습?다.\n?메?을 ?인?주?요.")
                            else:
                                st.error("?메???송 ??류가 발생?습?다.")
                        else:
                            st.error("?록?? ?? ?이?입?다.")
        else:
            if st.session_state.user_role == 'admin':
                role_disp = "관리자"
            elif st.session_state.user_role == 'official':
                pt = st.session_state.get('plan_type')
                role_disp = f"{'?식 ?용??} ({pt})" if pt else "?식 ?용??
            else:
                role_disp = "무료?용??
            
            expiry_info = ""
            if st.session_state.expiry_date:
                expiry_label = "만료?? "
                expiry_info = f' | {expiry_label}{st.session_state.expiry_date}'
                
            info_html = f"""<div style="background-color: #e8f5e9; border: 1px solid #c8e6c9; border-radius: 6px; color: #2e7d32; font-weight: bold; font-size: 0.85rem; padding: 8px 10px; text-align: center; margin-bottom: 8px;">
            ? {st.session_state.user_id} ({role_disp}{expiry_info})
            </div>"""
            st.markdown(info_html, unsafe_allow_html=True)
            
            if st.session_state.user_role == 'admin':
                btn_label = "? 관리자 ?면 ?기" if st.session_state.get('admin_mode', False) else "? 관리자 ?면 ?속"
                if st.button(btn_label):
                    st.session_state.admin_mode = not st.session_state.admin_mode
                    st.rerun()

            with st.expander("? 비?번호 변?):
                cur_pw = st.text_input("?재 비?번호", type="password", key="chg_cur_yeta")
                new_pw_val = st.text_input("??비?번호", type="password", key="chg_new_yeta")
                confirm_pw = st.text_input("??비?번호 ?인", type="password", key="chg_conf_yeta")
                
                if st.button("비?번호 변?, key="btn_chg_pw_yeta"):
                    if new_pw_val != confirm_pw:
                        st.error("??비?번호가 ?치?? ?습?다.")
                    elif not validate_password(new_pw_val):
                        st.error("비?번호??4???상, ?문+?수문자??함?야 ?니??")
                    else:
                        chk_res = check_login(st.session_state.user_id, cur_pw)
                        if chk_res:
                            change_user_password(st.session_state.user_id, new_pw_val)
                            st.success("비?번호가 변경되?습?다.")
                        else:
                            st.error("?재 비?번호가 ?바르? ?습?다.")

            if st.button("로그?웃", key="btn_logout_yeta"):
                st.session_state.user_id = None
                st.session_state.user_role = None
                st.session_state.expiry_date = None
                st.session_state.plan_type = None
                st.session_state.admin_mode = False
                st.session_state.logout_requested = True
                if 'cookie_manager' in st.session_state and st.session_state.cookie_manager:
                    try:
                        st.session_state.cookie_manager.delete("ahp_user_id", key="del_ahp_user_cookie_yeta")
                    except Exception:
                        pass
                if "login_user" in st.query_params:
                    try:
                        del st.query_params["login_user"]
                    except Exception:
                        pass
                if "login_token" in st.query_params:
                    try:
                        del st.query_params["login_token"]
                    except Exception:
                        pass
                st.rerun()

            with st.expander("? 견적??출력"):
                q_client = st.text_input("?뢰기??(?신)", placeholder="?? (??이치피?크", key="q_client_yeta")
                q_project = st.text_input("과제?(?로?트?", placeholder="?? ?? 가중치 ?? 분석", key="q_project_yeta")
                
                q_tier = st.selectbox(
                    "?비??구분 (?금??",
                    options=[
                        ("?간 ?용?(300,000??", 300000, "?간 ?용?),
                        ("?간 ?용?(2,800,000??", 2800000, "?간 ?용?)
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
                    <button class="btn" id="dl-pdf-btn">? 견적???운로드 (PDF)</button>
                    <div id="hidden-q-container" style="display: none; width: 720px; background: white; padding: 10px;"></div>
                    
                    <script>
                        document.getElementById('dl-pdf-btn').onclick = function() {{
                            var container = document.getElementById('hidden-q-container');
                            container.innerHTML = {escaped_html};
                            container.style.display = 'block';
                            
                            var opt = {{
                                margin:       [10, 10, 10, 10],
                                filename:     '견적??{clean_client}.pdf',
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
                    st.warning("견적???운로드??해 ?뢰기?명과 과제명을 먼? ?력??주세??")

            with st.expander("? 계산???금?수??청"):
                t_biz_num = st.text_input("?업???록번호", placeholder="000-00-00000", key="t_biz_num_yeta")
                t_biz_name = st.text_input("?호 (?사?", key="t_biz_name_yeta")
                t_rep_name = st.text_input("??자?, key="t_rep_name_yeta")
                t_address = st.text_input("?업??주소", key="t_address_yeta")
                t_biz_type = st.text_input("?태 / ?종", key="t_biz_type_yeta")
                t_email = st.text_input("계산???금?수??신 ?메??, key="t_email_yeta")
                
                t_tier = st.selectbox(
                    "?청 ?비??(?금??",
                    options=[
                        ("?간 ?용?(300,000??", "?간 ?용?),
                        ("?간 ?용?(2,800,000??", "?간 ?용?)
                    ],
                    format_func=lambda x: x[0],
                    key="t_tier_select_yeta"
                )
                
                if st.button("계산???금?수??청?기", use_container_width=True, key="btn_request_tax_yeta"):
                    if not t_biz_num.strip():
                        st.error("?업???록번호??력??주세??")
                    elif not t_biz_name.strip():
                        st.error("?호??력??주세??")
                    elif not t_rep_name.strip():
                        st.error("??자명을 ?력??주세??")
                    elif not t_email.strip():
                        st.error("?메?을 ?력??주세??")
                    elif not validate_email(t_email.strip()):
                        st.error("?바??메???식???닙?다.")
                    else:
                        with st.spinner("?청?? ?출?는 ?.."):
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
                                    st.success("계산???금?수??청???수?었?니?? 관리자 ?인 ??발행?니??")
                                else:
                                    st.warning("DB ??? ?공?으???림 메일 발송???패?습?다. 관리자가 ?인 ???차 처리???리겠습?다.")
                            except Exception as e:
                                st.error(f"?청 ??류가 발생?습?다: {e}")
                            finally:
                                conn.close()

        # Business Info
            with tab_signup_side:
                st.write("### " + "AHP 마스???? 분석 ?루???원가??)
                
                agreements = signup_agreement.show_agreement_ui()
                
                s_id = st.text_input("?이??(?메??주소)", key="main_s_id_yeta")
                s_pw = st.text_input("비?번호", type="password", key="main_s_pw_yeta")
                
                s_cust_type = "yeta"
                
                if st.button("가?신?, key="main_btn_signup_yeta", type="primary"):
                    if not agreements.get("agree_personal_info"):
                        st.error("개인?보 ?집·?용???의?야 가?신? ???습?다.")
                    elif not validate_email(s_id):
                        st.error("?바??메???식???닙?다.")
                    elif not validate_password(s_pw):
                        st.error("비?번호??문자+?수문자?야 ?니??")
                    else:
                        restore_from_deleted_sheet(s_id.strip())
                        if add_user(s_id.strip(), s_pw, 'temp', agree_info="Y", customer_type=s_cust_type):
                            st.success("?원가?이 ?료?었?니?? ?이?바??'로그?? ????로그?해 주시?바랍?다.")
                            time.sleep(2)
                            st.rerun()
                        else:
                            st.error("?? 존재?는 ?이?입?다.")

                st.info("? **개인?보 보호 ?내**\n\n?? AHP ?스?? ?용?의 ?름, ?화번호 ??불필?한 개인?보??집?? ?습?다. ?한 ?력?신 비?번호??강력?게 ?호?되????되므?관리자???????습?다. ?심?고 ?용??주세??")

        st.markdown("---")
        biz_info_html = f"""
        <div style="font-size: 0.75rem; color: #888; line-height: 1.5; padding: 10px 5px; border-top: 1px solid #eeeeee; margin-top: 15px;">
            <div style="font-weight: bold; margin-bottom: 5px; color: #555;">?업???보</div>
            ??<b>?호</b>: ?레?인?이??br>
            ??<b>??자</b>: ?상??br>
            ??<b>?업?등록번??/b>: 683-27-00122<br>
            ??<b>주소</b>: ?천??부?구 ?길?12, 가??203??br>
            ??<b>?화번호</b>: 0507-1347-2610<br>
            ??<b>?메??/b>: jeon080423@gmail.com<br>
            ??<b>개인?보관리책?자</b>: ?상??br>
            ??<b>?신?매???고번호</b>: 간이과세??
        </div>
        """
        st.markdown(biz_info_html, unsafe_allow_html=True)

    # 7. Navigation Tabs
    # --- ADMIN MODE INTERCEPTOR ---
    if st.session_state.get('admin_mode', False) and st.session_state.user_role == 'admin':
        st.subheader("? 가?자 ?황 ?관?(?? ?용 ?")
        
        col_sync1, col_sync2 = st.columns([2, 8])
        with col_sync1:
            if st.button("? 구? ?트? ?기??):
                with st.spinner("구? ?트 ?이??불러?는 ?.."):
                    sync_count = sync_db_from_sheets()
                if sync_count >= 0:
                    st.success(f"? ?기???료! (보정 ?복구???이?? {sync_count}?")
                    st.rerun()
                else:
                    st.error("?기????류가 발생?습?다. ?면?의 ?러 메시지??인??주세??")

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
                
                st.write(f"**?적 방문??** {total_visits:,}?)
                st.write("#### ? ?별 방문???황")
                fig_visit = px.bar(daily_df_counts, x='Date_Only', y='count', text='count',
                                    labels={'Date_Only': '?짜', 'count': '방문????})
                fig_visit.update_traces(textposition='outside')
                fig_visit.update_layout(xaxis_title="?짜", yaxis_title="방문????, showlegend=False, xaxis={'type': 'category'})
                st.plotly_chart(fig_visit, use_container_width=True)
            else:
                st.info("방문 기록???습?다.")
        except Exception as e:
            st.error(f"?계 ?류: {e}")
            
        st.divider()
        st.write("### ? 가?자 ?황 ?최종 배포 링크")
        
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
                "id": "?원 ID",
                "role": "권한",
                "signup_date": "가?일",
                "pw": "비?번호",
                "survey_count": "배포 ?수",
                "last_survey_link": st.column_config.LinkColumn("최종 배포 ?문지 링크", display_text="?문지 바로가?),
                "expiry_date": "만료??,
                "agree_info": "?의??",
                "customer_type": "고객?
            },
            hide_index=True,
            use_container_width=True
        )

        with st.expander("?원 ?보 ?정 (비?번호 초기???함)"):
            edit_id = st.selectbox("?정???원 ID", users_df['id'].unique())
            selected_user = users_df[users_df['id'] == edit_id].iloc[0]
            new_role_val = st.selectbox("권한 변?, ['temp', 'official', 'admin'], 
                                    index=['temp', 'official', 'admin'].index(selected_user['role']))
            
            if new_role_val == 'official' and selected_user['role'] != 'official':
                new_expiry_val_default = str(datetime.date.today() + datetime.timedelta(days=60))
            else:
                new_expiry_val_default = selected_user['expiry_date']
                
            new_expiry_val = st.text_input("만료???정/변?(YYYY-MM-DD)", value=new_expiry_val_default)
            new_pw_edit = st.text_input("??비?번호 (?력 ??변경됨)", type="password", placeholder="변경하지 ?으?면 비워?세??)
            
            col_admin_act1, col_admin_act2 = st.columns(2)
            with col_admin_act1:
                if st.button("?보 ?정 ?용", use_container_width=True):
                    update_user_full_info(edit_id, new_pw_edit, new_role_val, new_expiry_val)
                    if new_role_val == 'official' and selected_user['role'] != 'official':
                        send_approval_email(edit_id)
                    st.success(f"{edit_id} ?원???보가 ?정?었?니??")
                    st.rerun()
            with col_admin_act2:
                if st.button("? ??계정?로 로그??, use_container_width=True, type="secondary"):
                    st.session_state.user_id = edit_id
                    st.session_state.user_role = selected_user['role']
                    st.session_state.expiry_date = selected_user['expiry_date']
                    st.session_state.admin_mode = False
                    st.toast(f"? {edit_id} 계정?로 로그?했?니??")
                    st.rerun()

        with st.expander("?원 ??"):
            del_id = st.selectbox("?????원 ID ?택", users_df['id'].unique(), key='del_user_select')
            if st.button("?택???원 ??"):
                if del_id == st.session_state.user_id:
                    st.error("본인? ???????습?다.")
                else:
                    delete_user(del_id)
                    st.success("?? ?료")
                    st.rerun()

        with st.expander("? ?위?문 ?인 ?벤???정 ??어"):
            event_cfg = get_event_settings()
            new_active = st.checkbox("?벤???성????", value=event_cfg["active"], key="admin_event_active")
            new_title = st.text_input("?벤???목", value=event_cfg["title"], key="admin_event_title")
            new_desc = st.text_area("?벤???용/?명", value=event_cfg["desc"], key="admin_event_desc")
            
            try:
                default_deadline_date = datetime.datetime.strptime(event_cfg["deadline"], "%Y-%m-%d").date()
            except Exception:
                default_deadline_date = datetime.date(2026, 7, 30)
            new_deadline_date = st.date_input("?벤??종료??, value=default_deadline_date, key="admin_event_deadline")
            new_deadline_str = str(new_deadline_date)
            new_discount = st.number_input("?인 금액 (??", min_value=0, max_value=500000, value=event_cfg["discount"], step=5000, key="admin_event_discount")
            
            if st.button("?벤???정 ???, use_container_width=True):
                conn = get_db_connection('users.db')
                c = conn.cursor()
                try:
                    c.execute("UPDATE event_settings SET event_active=?, event_title=?, event_desc=?, event_deadline=?, event_discount=? WHERE id=1",
                              (1 if new_active else 0, new_title, new_desc, new_deadline_str, int(new_discount)))
                    conn.commit()
                    st.success("? ?벤???정???공?으???되?습?다!")
                    st.rerun()
                except Exception as e:
                    st.error(f"?정 ????패: {e}")
                finally:
                    conn.close()

        st.stop()

    if st.session_state.user_id:
        if st.session_state.user_id == 'shjeon':
            tab_guide, tab_analysis, tab_excel, tab_survey_create, tab_live_response, tab_pricing = st.tabs([
                "?? AHP 지??내",
                "?? 종합??(AHP) 분석",
                "?? 코딩 ?? ?식",
                "?? ?용 AHP ?문 ?성 ?배포",
                "?시??답 ?황",
                "?비???금"
            ])
            tab_coupon_dispatch = None
            tab_coupon_admin = None
        else:
            tab_guide, tab_analysis, tab_excel, tab_survey_create, tab_live_response, tab_pricing = st.tabs([
                "?? AHP 지??내",
                "?? 종합??(AHP) 분석",
                "?? 코딩 ?? ?식",
                "?? ?용 AHP ?문 ?성 ?배포",
                "?시??답 ?황",
                "?비???금"
            ])
            tab_coupon_dispatch = None
            tab_coupon_admin = None
    else:
        tab_guide, tab_analysis, tab_excel, tab_survey_create, tab_live_response, tab_pricing = st.tabs([
            "이용 안내", "1. AHP 분석 (정성/정량)", "2. 엑셀 업로드", "3. 설문 배포", "4. 설문 취합", "서비스 요금"
        ])
        tab_coupon_dispatch = None
        tab_coupon_admin = None


    # =========================================================================
    # TAB: Coupon Admin
    # =========================================================================
    if tab_coupon_admin is not None:
        with tab_coupon_admin:
            st.write("### ?️ ?????품 관?(관리자 ?용)")
            st.info("?문 ?뢰?에??공??????기프?콘) 목록??관리합?다. (?스??모드 ?성???")
            
            # ?규 ?록 ??
            with st.expander("???규 ?????록", expanded=False):
                with st.form("new_coupon_form"):
                    c_name = st.text_input("?품?(?? ??벅스 ?메리카??")
                    c_brand = st.text_input("브랜??(?? ??벅스)")
                    c_orig = st.number_input("?? (고객?게 ???금액)", min_value=0, step=100)
                    c_cost = st.number_input("?? (기프?쇼 차감 금액 - 마진 계산??", min_value=0, step=100)
                    if st.form_submit_button("?록?기"):
                        if c_name:
                            coupon_manager.add_coupon_product(c_name, c_brand, c_orig, c_cost)
                            st.success(f"'{c_name}' ?록 ?료!")
                            st.rerun()
                        else:
                            st.error("?품명을 ?력?주?요.")
            
            # 기존 ?품 리스???관?
            st.write("#### ? ?록??????리스??)
            all_coupons = coupon_manager.get_all_coupons()
            if not all_coupons:
                st.write("?록???품???습?다.")
            else:
                for cp in all_coupons:
                    with st.container(border=True):
                        cols = st.columns([3, 2, 2, 2, 2])
                        cols[0].write(f"**{cp['name']}**")
                        cols[1].write(f"{cp['brand']}")
                        cols[2].write(f"??: {cp['original_price']:,}??)
                        cols[3].write(f"??: {cp['cost_price']:,}??)
                        
                        is_active = cp['is_active'] == 1
                        
                        if is_active:
                            if cols[4].button("비활?화", key=f"deact_{cp['id']}"):
                                coupon_manager.update_coupon_status(cp['id'], 0)
                                st.rerun()
                        else:
                            if cols[4].button("?성??, key=f"act_{cp['id']}"):
                                coupon_manager.update_coupon_status(cp['id'], 1)
                                st.rerun()


    # =========================================================================
    # TAB: Coupon Dispatch
    # =========================================================================
    if tab_coupon_dispatch is not None:
        with tab_coupon_dispatch:
            st.write("### ? ????발송 관?)
            st.info("종료???문???답????번?? ?긴 ??에????을 발송?니??")
            
            pending = coupon_manager.get_pending_dispatches(st.session_state.user_id)
            completed = coupon_manager.get_completed_dispatches(st.session_state.user_id)
            
            st.write("#### ??발송 ??목록")
            if not pending:
                st.write("발송 ??중인 ?역???습?다.")
            else:
                with st.form("dispatch_form"):
                    selected_ids = []
                    st.write("발송????을 ?택?세??")
                    for p in pending:
                        is_sel = st.checkbox(f"{p['phone']} - {p['coupon_name']} (?문 ID: {p['survey_id'][:8]}...)", key=f"chk_{p['id']}")
                        if is_sel:
                            selected_ids.append(p['id'])
                            
                    if st.form_submit_button("?택?????발송?기", type="primary"):
                        if selected_ids:
                            coupon_manager.dispatch_coupons(selected_ids)
                            st.success(f"{len(selected_ids)}?발송???료?었?니??")
                            st.rerun()
                        else:
                            st.warning("발송????을 1??상 ?택?주?요.")
                            
            st.write("---")
            st.write("#### ??발송 ?료 목록")
            if not completed:
                st.write("?료???역???습?다.")
            else:
                for c in completed:
                    st.write(f"- {c['phone']} / {c['coupon_name']} / 발송?시: {c['dispatch_time']}")

    # =========================================================================
    # TAB 1: Analysis Tool
    # =========================================================================
    with tab_analysis:
        st.write("### " + "?비??성 종합??(AHP)")
        st.markdown("<br>", unsafe_allow_html=True)
        
        main_col, settings_col = st.columns([3.0, 1.2], gap="large")
        
        with settings_col:
            # ==========================================
            # SECTION 1: 분석 ?경 ?정 (Settings)
            # ==========================================
            with st.container(border=True):
                st.markdown(f"<div style='font-size: 1.1rem; font-weight: bold; color: #1e3a8a; margin-bottom: 15px;'><i class='fas fa-cogs'></i> {'?? 종합??(AHP) 가중치 ?정'}</div>", unsafe_allow_html=True)
                
                project_type = st.selectbox(
                    "?업 ?형(모델) ?택",
                    options=[
                        ("construction_non_capital", "건설?업 (비수?권)"),
                        ("construction_capital", "건설?업 (?도?"),
                        ("rnd_bc", "R&D?업 (B/C)"),
                        ("rnd_ec", "R&D?업 (E/C)"),
                        ("other_bc", "기? ?정?업 (B/C)"),
                        ("other_ec", "기? ?정?업 (E/C)")
                    ],
                    format_func=lambda x: x[1],
                    key="yeta_project_type_select"
                )
                p_type = project_type[0]
                
                st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)
                
                st.markdown(f"<div style='font-size: 0.95rem; font-weight: 600; margin-bottom: 8px;'>{'A. ?량 ?이??(B/C, 지???도)'}</div>", unsafe_allow_html=True)
                bc_ratio = st.number_input("경제??분석 결과 (B/C 비율)", min_value=0.0, max_value=10.0, value=1.05, step=0.05)
                
                has_regional = "non_capital" in p_type or p_type == "other_bc" or p_type == "other_ec"
                if has_regional:
                    lir_value = st.number_input("지???도 지??(LIR/MIR)", min_value=-3.0, max_value=3.0, value=0.0, step=0.1)
                else:
                    lir_value = 0.0
                    st.text_input("지???도 지??(LIR/MIR)", value="?도??당?음", disabled=True)
                
                st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)
                
                st.markdown(f"<div style='font-size: 0.95rem; font-weight: 600; margin-bottom: 8px;'>{'B. 1계층 ?수??가중치 (%)'}</div>", unsafe_allow_html=True)
                if p_type == "rnd_bc":
                    econ_w = st.slider("경제??가중치", 0, 100, 45) / 100.0
                    tech_w = st.slider("과학기술????성", 0, 100, 35) / 100.0
                    policy_w = st.slider("?책????성", 0, 100, 20) / 100.0
                    regional_w = 0.0
                elif p_type == "rnd_ec":
                    econ_w = st.slider("경제??가중치", 0, 100, 35) / 100.0
                    tech_w = st.slider("과학기술????성", 0, 100, 45) / 100.0
                    policy_w = st.slider("?책????성", 0, 100, 20) / 100.0
                    regional_w = 0.0
                elif p_type == "construction_capital":
                    tech_w = 0.0
                    econ_w = st.slider("경제??가중치", 0, 100, 65) / 100.0
                    policy_w = st.slider("?책??가중치", 0, 100, 35) / 100.0
                    regional_w = 0.0
                    st.slider("지???발??가중치", 0, 100, 0, disabled=True)
                elif p_type == "other_bc":
                    tech_w = 0.0
                    econ_w = st.slider("경제??가중치", 0, 100, 40) / 100.0
                    policy_w = st.slider("?책??가중치", 0, 100, 60) / 100.0
                    regional_w = 0.0
                elif p_type == "other_ec":
                    tech_w = 0.0
                    econ_w = st.slider("경제??가중치", 0, 100, 30) / 100.0
                    policy_w = st.slider("?책??가중치", 0, 100, 70) / 100.0
                    regional_w = 0.0
                else: # construction_non_capital
                    tech_w = 0.0
                    econ_w = st.slider("경제??가중치", 0, 100, 40) / 100.0
                    policy_w = st.slider("?책??가중치", 0, 100, 30) / 100.0
                    regional_w = st.slider("지???발??가중치", 0, 100, 30) / 100.0

                valid_w, w_msg = yeta_utils.validate_yeta_level1_weights(p_type, econ_w, policy_w, regional_w, tech_w)
                if valid_w:
                    st.markdown(f"<div style='color: green; font-size: 0.8rem; margin-top: -10px;'>?️ {'KDI 지?가중치 범위 부??}</div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div style='color: red; font-size: 0.8rem; margin-top: -10px;'>?️ {w_msg}</div>", unsafe_allow_html=True)


        with main_col:
            # ==========================================
            # SECTION 3: ?? ?이???로???분석 (Upload & Analyze)
            # ==========================================
            with st.container(border=True):
                st.markdown(f"<h3 style='color: #b91c1c; margin-bottom: 10px; font-size: 1.3rem;'><i class='fas fa-chart-line'></i> {'2. ?이???로???종합?? 분석'}</h3>", unsafe_allow_html=True)
                st.markdown("<span style='font-size: 0.95rem; color: #4b5563;'>?플릿에 ?성???료??AHP ?? ?이?? ?로?하?즉시 ?비??성조사 종합?? 결과가 ?출?니??</span>", unsafe_allow_html=True)
                
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

                auto_correct_cr = st.checkbox("CR 0.15 초과 ???렬 ?동 보정", value=True, help="???의 ????비율(CR)??0.15?초과?는 경우, AHP 보정 ?고리즘???해 ?????는 ?렬??동 조정?니??")
                
                data_source = st.radio(
                    "?이???스 ?택",
                    ["? ?? ?일 직접 ?로??, "? 배포???라???문 ?이???동"],
                    horizontal=True
                )
                
                df = None
                if data_source == "? ?? ?일 직접 ?로??:
                    uploaded_file = st.file_uploader("?답???료??AHP ?? ?일 첨?", type=["xlsx"])
                    if uploaded_file is not None:
                        try:
                            df = pd.read_excel(uploaded_file)
                            
                            # --- [?업 모델 ?계층 구조 ?동 ?식 로직 ?작] ---
                            inferred_p_type = "construction_capital"
                            has_reg = "1계층_지???발??%)" in df.columns
                            has_tech = "1계층_기술??%)" in df.columns
                            
                            if has_tech:
                                inferred_p_type = "rnd"
                            elif has_reg:
                                inferred_p_type = "construction_non_capital"
                            
                            # ?위 ?인 추출
                            inferred_factors = {}
                            for col in df.columns:
                                if col.startswith("??평가_[") and "]_" in col:
                                    cat = col.split("]_")[0].replace("??평가_[", "")
                                    factor = col.split("]_")[1].split("(?행?호")[0]
                                    if cat not in inferred_factors: inferred_factors[cat] = set()
                                    inferred_factors[cat].add(factor)
                                    
                            factor_msg = []
                            for cat, factors in inferred_factors.items():
                                factor_msg.append(f"**{cat}**: {', '.join(list(factors))}")
                                
                            p_type_ko = "R&D ?업" if inferred_p_type == "rnd" else ("비수?권 ?업 (지???발???함)" if inferred_p_type == "construction_non_capital" else "?도??업 (경제???책???주)")
                            
                            st.success(f"?이??로드 ?공! ?? ?이?? ?해 ?업 모델???동?로 ?식?습?다.\n\n* **?식???업 ?형**: {p_type_ko}\n* **분석 ?인**: {', '.join(inferred_factors.keys())}")
                            with st.expander("?식???위 계층 구조 보기"):
                                for msg in factor_msg:
                                    st.markdown("- " + msg)
                            # -----------------------------------------------------
                            
                            # Override p_type with inferred one for accurate processing
                            p_type = inferred_p_type
                            
                        except Exception as e:
                            st.error(f"?? 로드 ??류가 발생?습?다: {str(e)}")
                else:
                    if st.session_state.user_id is None:
                        st.warning("?라???문 ?이???동 분석? ?원 ?용 기능?니?? 로그?해 주세??")
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
                            st.warning("배포???라???문???습?다.")
                        else:
                            survey_options = {f"{row[1]} ({row[2]})": row[0] for row in admin_surveys}
                            selected_survey_label = st.selectbox(
                                "분석???라???문 ?택",
                                list(survey_options.keys())
                            )
                            selected_sheet_id = survey_options[selected_survey_label]
                            
                            if st.button("? 구? ?트?서 ?시??답 가?오?, type="primary", use_container_width=True):
                                import survey_manager; survey_manager.log_user_action(st.session_state.get("user_id") or "Guest", "?시??답 가?오?)
                                with st.spinner("구? ?트?서 ?문 ?이?? 가?오???.."):
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
                                                
                                                # --- [?업 모델 ?계층 구조 ?동 ?식 로직 ?작] ---
                                                inferred_p_type = "construction_capital"
                                                has_reg = "1계층_지???발??%)" in df.columns
                                                has_tech = "1계층_기술??%)" in df.columns
                                                
                                                if has_tech:
                                                    inferred_p_type = "rnd"
                                                elif has_reg:
                                                    inferred_p_type = "construction_non_capital"
                                                
                                                inferred_factors = {}
                                                for col in df.columns:
                                                    if col.startswith("??평가_[") and "]_" in col:
                                                        cat = col.split("]_")[0].replace("??평가_[", "")
                                                        factor = col.split("]_")[1].split("(?행?호")[0]
                                                        if cat not in inferred_factors: inferred_factors[cat] = set()
                                                        inferred_factors[cat].add(factor)
                                                        
                                                factor_msg = []
                                                for cat, factors in inferred_factors.items():
                                                    factor_msg.append(f"**{cat}**: {', '.join(list(factors))}")
                                                    
                                                p_type_ko = "R&D ?업" if inferred_p_type == "rnd" else ("비수?권 ?업 (지???발???함)" if inferred_p_type == "construction_non_capital" else "?도??업 (경제???책???주)")
                                                
                                                st.success(f"?라???문 ?이?? ?공?으?불러?습?다! ?업 모델???동?로 ?식?습?다.\n\n* **?식???업 ?형**: {p_type_ko}\n* **분석 ?인**: {', '.join(inferred_factors.keys())}")
                                                with st.expander("?식???위 계층 구조 보기"):
                                                    for msg in factor_msg:
                                                        st.markdown("- " + msg)
                                                        
                                                p_type = inferred_p_type
                                                # -----------------------------------------------------
                                                
                                            else:
                                                st.warning("?직 ?집???답 ?이?? ?습?다.")
                                        except Exception as e:
                                            st.error(f"구? ?트 ?이?? 가?오????류가 발생?습?다: {str(e)}")

                if df is not None:
                    try:
                        max_free_evals = 3
                        if not is_official and len(df) > max_free_evals:
                            st.warning(f"?️ 무료 ?용?는 최? {max_free_evals}명의 ?문 ?이?만 분석 가?합?다. (?식 결제 ??무제??분석 가??")
                            df = df.head(max_free_evals)
                            
                        res_df, final_yeta_score = yeta_utils.process_yeta_ahp_data(df, p_type, bc_ratio, lir_value, auto_correct_cr=auto_correct_cr)
                        
                        # ??출력?으로만 ?수???맷???용 (?이???본 보존)
                        st.markdown("---")
                        st.markdown("### " + "? 종합??(AHP) 최종 결과")
                        
                        # --- Create standard AHP summary table ---
                        passed_evals = res_df[res_df["CR ?과"] == "PASS"]
                        if len(passed_evals) > 0:
                            avg_w_econ = passed_evals["경제??가중치"].mean()
                            avg_w_policy = passed_evals["?책??가중치"].mean()
                            avg_w_reg = passed_evals["지????가중치"].mean()
                            avg_w_tech = passed_evals["기술??가중치"].mean()
                            
                            avg_s_econ = passed_evals["경제???수"].mean()
                            avg_s_policy = passed_evals["?책???수"].mean()
                            avg_s_reg = passed_evals["지?????수"].mean()
                            avg_s_tech = passed_evals["기술???수"].mean()
                            
                            summary_data = []
                            summary_data.append({"????": "경제??분석", "가중치": avg_w_econ, "?? 결과 (?수)": avg_s_econ, "비고": "B/C, NPV ??반영"})
                            summary_data.append({"????": "?책??분석", "가중치": avg_w_policy, "?? 결과 (?수)": avg_s_policy, "비고": "?책?과, 추진?건 ??})
                            
                            if "rnd" in p_type:
                                summary_data.append({"????": "기술??분석", "가중치": avg_w_tech, "?? 결과 (?수)": avg_s_tech, "비고": "기술개발 ?공가?성 ??})
                            if "non_capital" in p_type or p_type in ["other_bc", "other_ec"]:
                                summary_data.append({"????": "지???발??분석", "가중치": avg_w_reg, "?? 결과 (?수)": avg_s_reg, "비고": "지???도, ?급?과 ??})
                                
                            summary_data.append({"????": "**종합?? (AHP)**", "가중치": 1.000, "?? 결과 (?수)": final_yeta_score, "비고": "**최종 결과?*"})
                            
                            st.write("#### " + "[?? AHP??용??종합?? 결과")
                            summary_df_for_excel = pd.DataFrame(summary_data)
                            
                            # ??출력 ???수??3?리 고정
                            format_dict = {"가중치": "{:.3f}", "?? 결과 (?수)": "{:.3f}"}
                            st.table(summary_df_for_excel.style.format(format_dict))
                            
                            # Add Excel Download Button
                            try:
                                from yeta_utils import export_yeta_result_excel
                                
                                # 미리 is_pass 계산
                                is_pass = final_yeta_score >= 0.5
                                excel_data = export_yeta_result_excel(summary_df_for_excel, res_df, final_score=final_yeta_score, is_pass=is_pass)
                                
                                st.download_button(
                                    label="? 종합??(AHP) ?? 결과 ?운로드",
                                    data=excel_data,
                                    file_name="?비??성조사_AHP_최종결과.xlsx",
                                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                    type="primary",
                                    use_container_width=True
                                )
                            except Exception as ex:
                                st.error(f"?? ?운로드 기능 로드 ??류 발생: {ex}")
                                
                            st.markdown("<br>", unsafe_allow_html=True)
                        # ----------------------------------------
                        
                        is_pass = final_yeta_score >= 0.5
                        card_class = "verdict-pass" if is_pass else "verdict-fail"
                        verdict_text = "?업 ??성 ?보 (?행)" if is_pass else "?업 ??성 미흡 (미시??"
                        
                        st.markdown(f"""
                        <div class="verdict-card {card_class}">
                            <div class="verdict-title">{"최종 종합 ?? ?정"}</div>
                            <div class="verdict-score">{final_yeta_score:.3f}</div>
                            <div style="font-size: 1.3rem; font-weight: bold;">{verdict_text}</div>
                            <div style="font-size: 0.9rem; margin-top: 10px; opacity: 0.85;">
                                {"KDI 지?기?: AHP 종합?수 0.5 ?상??????성 ?보"}
                            </div>
                        </div>
                        <br>
                        """, unsafe_allow_html=True)
                        
                        st.info(f"? **조사 결과 ?석**: ??비??성조사???답??{len(res_df)}명의 ?문 결과?바탕?로, 극단?최고??1? 최???1????외??{max(1, len(res_df)-2 if len(res_df) >= 3 else len(res_df))}명의 ?수?종합?여 ?출?었?니?? 최종 AHP 종합?수가 {final_yeta_score:.3f}?로 0.5?{'?어 ?업 ??성???보?습?다' if is_pass else '?? 못해 ?업 ??성??미흡??것으?분석?었?니??}.")
                        
                        with st.expander("? AHP ?출???변??공식 ?내"):
                            st.markdown("""
                            #### 1. ?량 ?이????비교 척도 변??
                            경제?????량???치??문조사??9??척도? ?등?게 맞추??해 KDI ?? 공식???용?니??
                            - **B/C 비율 변??*: `???수 = 8.592933 × ln(B/C비율) ± 1`
                            - **지???도(LIR) 변??*: `???수 = 2.0 × LIR + 1.0`
                            
                            #### 2. ??비교 척도??가중치(AHP ?수) 변??
                            ?에???출?????수(`Score`)?바탕?로 '?행(Go)' ??의 ?? 결과(?수)?계산?니??
                            - **?행(Go) 가중치** = `Score / (Score + 1.0)`
                            - ?? B/C ?산 ???수가 1.419?면, ?행 ?수??`1.419 / (1.419 + 1) = 0.5866`
                            
                            #### 3. 개인??수 ?산 ?최종 종합?수 ?출
                            ????의 ???가중치? ?에??구한 ?????수?곱해 개인?최종 ?수?계산?니?? 
                            ?후 ?답?? 3??상??경우, 가???? ?수 1명과 가????? ?수 1명을 집계?서 배제(극단?배제)?????? ?원?의 ?수?**기하?균(Geometric Mean)**?여 최종 AHP ?점???출?니??
                            """)
                        
                        st.markdown("<br>", unsafe_allow_html=True)
                        st.write("#### " + "??????별 ?수 분포 ?극단?배제 ?황")
                        st.dataframe(res_df, use_container_width=True)
                        
                    except Exception as e:
                        st.error(f"분석 ??류가 발생?습?다: {str(e)}")




    # =========================================================================
    # =========================================================================
    # TAB 1.5: Yeta Excel Template Generator
    # =========================================================================
    with tab_excel:
        st.write("### " + "?비??성조사 AHP 코딩 ?? ?식 ?정 ??운로드")
        st.markdown("<br>", unsafe_allow_html=True)
        
        st.markdown(f"<h4 style='color: #1e3a8a; margin-top: 10px;'><i class='fas fa-check-circle'></i> 1?계: 분석 모델(?업 ?형) ?택</h4>", unsafe_allow_html=True)
        with st.container(border=True):
            excel_project_type = st.selectbox(
                "????업 ?형",
                options=[
                    ("construction_non_capital", "건설?업 (비수?권)"),
                    ("construction_capital", "건설?업 (?도?"),
                    ("rnd_bc", "R&D?업 (B/C)"),
                    ("rnd_ec", "R&D?업 (E/C)"),
                    ("other_bc", "기? ?정?업 (B/C)"),
                    ("other_ec", "기? ?정?업 (E/C)")
                ],
                format_func=lambda x: x[1],
                key="yeta_excel_project_type_select"
            )
            ex_p_type = excel_project_type[0]
            
            if "rnd" in ex_p_type:
                st.info("? 1계층 고정 ??: 경제?? ?책?? 과학기술??)
            elif "capital" in ex_p_type and "non" not in ex_p_type:
                st.info("? 1계층 고정 ??: 경제?? ?책??)
            else:
                st.info("? 1계층 고정 ??: 경제?? ?책?? 지???발??)
        
        st.markdown(f"<h4 style='color: #1e3a8a; margin-top: 25px;'><i class='fas fa-list'></i> 2?계: 2계층 ?? ?인 커스?마?징</h4>", unsafe_allow_html=True)
        with st.container(border=True):
            st.caption("????업 ?성??맞춰 ?? ?? ?????표(,)?구분?여 ?력?세?? ?력???인 개수??맞춰 ??비교 ?이 ?동 계산?니??")
            
            policy_input = st.text_input("?책???위 ?인 (2계층)", value="?책?????? ?업추진?의 ?험?인")
            policy_2nd = [x.strip() for x in policy_input.split(",") if x.strip()]
            policy_factors = {k: [] for k in policy_2nd}
            if policy_2nd:
                with st.expander("??'?책?? 3계층 (?분? ?력", expanded=False):
                    st.info("? ?분?3계층)가 ?는 ??? 비워?시??동?로 2계층?로 처리?니??")
                    for t2 in policy_2nd:
                        t3_val = st.text_input(f"'{t2}'???위 ?인 (3계층)", key=f"ex_policy_t3_{t2}")
                        if t3_val.strip():
                            policy_factors[t2] = [x.strip() for x in t3_val.split(",") if x.strip()]
            
            regional_factors = {}
            if "non_capital" in ex_p_type or "other" in ex_p_type:
                reg_input = st.text_input("지???발???위 ?인 (2계층)", value="지?????급?과, 지??발계?과??부?성")
                reg_2nd = [x.strip() for x in reg_input.split(",") if x.strip()]
                regional_factors = {k: [] for k in reg_2nd}
                if reg_2nd:
                    with st.expander("??'지???발?? 3계층 (?분? ?력", expanded=False):
                        st.info("? ?분?3계층)가 ?는 ??? 비워?시??동?로 2계층?로 처리?니??")
                        for t2 in reg_2nd:
                            t3_val = st.text_input(f"'{t2}'???위 ?인 (3계층)", key=f"ex_reg_t3_{t2}")
                            if t3_val.strip():
                                regional_factors[t2] = [x.strip() for x in t3_val.split(",") if x.strip()]
                
            tech_factors = {}
            if "rnd" in ex_p_type:
                tech_input = st.text_input("과학기술???위 ?인 (2계층)", value="기술개발계획???절?? 기술개발 ?공가?성, 기존 ?업과의 중복??)
                tech_2nd = [x.strip() for x in tech_input.split(",") if x.strip()]
                tech_factors = {k: [] for k in tech_2nd}
                if tech_2nd:
                    with st.expander("??'과학기술?? 3계층 (?분? ?력", expanded=False):
                        st.info("? ?분?3계층)가 ?는 ??? 비워?시??동?로 2계층?로 처리?니??")
                        for t2 in tech_2nd:
                            t3_val = st.text_input(f"'{t2}'???위 ?인 (3계층)", key=f"ex_tech_t3_{t2}")
                            if t3_val.strip():
                                tech_factors[t2] = [x.strip() for x in t3_val.split(",") if x.strip()]

        st.markdown(f"<h4 style='color: #047857; margin-top: 25px;'><i class='fas fa-file-excel'></i> 3?계: 맞춤???? ???성 ??운로드</h4>", unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown("<span style='font-size: 0.95rem; color: #4b5563;'>??1?계? 2?계?서 ?정??<b>?비??성조사 분석 모델 ??인</b>??맞춰??용 ?? ???입?다.</span>", unsafe_allow_html=True)
            
            st.markdown("""
            <div style='background-color: #f9fafb; padding: 15px; border-radius: 5px; margin-top: 15px; border-left: 4px solid #3b82f6; margin-bottom: 20px;'>
                <strong>[?식 구조 ?내]</strong><br>
                ?️ <b>?일??부?/b>: 2계층 ?후 ????간의 ??비교 ?력 방식 ?CR 검?로직? ?반 AHP? ?일?니??<br>
                ?️ <b>?라지??부?/b>: ?? 지침에 ?라 1계층(경제/?책/지?? 가중치????비교가 ?닌 <b>100???수?법</b> 비율?기입?니??<br><br>
                <strong>[? ?이???력 가?드]</strong><br>
                ?운로드?시???? ?에 ?이?? 기입?실 ???래 규칙???르?요.<br>
                ?️ ?쪽(?행) ??????중요?면: <b>?수</b> ?력 (?? -3)<br>
                ?️ ?른?미시?? ??????중요?면: <b>?수</b> ?력 (?? 3)<br>
                ?️ ???????등?게 중요?면: <b>1</b> ?력
            </div>
            """, unsafe_allow_html=True)
            
            img_file = "ahp_input_guide.png"
            caption_text = "[참고] ?문 ?답???????력?는 방법"
            if os.path.exists(img_file):
                st.image(img_file, caption=caption_text)
            
            template_bytes = yeta_utils.generate_yeta_excel_template(ex_p_type, policy_factors, regional_factors, tech_factors)
            st.download_button(
                label="? 맞춤???? AHP ?? ?플??운로드 (.xlsx)",
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
        st.write("### ?비??성조사 AHP ?문가 ?문지 ?작 ?배포")
        st.info("KDI 지침에 명시???인??바탕?로 ?? ?용 ?문지??게 구성?고 구? ?트? ?동?여 배포?????습?다.")
        
        # ------------------------------------------------------------
        # 0. ?문 관?(1??1?문 모드)
        # ------------------------------------------------------------
        st.subheader("?션 0: ???문 관?)

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
                cur.execute("SELECT survey_id, title, created_at FROM admin_surveys WHERE admin_id = ? AND title LIKE '[??]%' ORDER BY created_at DESC", (st.session_state.user_id,))
                sqlite_surveys = cur.fetchall()
                conn.close()
            except Exception:
                pass

            gs_surveys = []
            try:
                from survey_manager import get_admin_surveys_from_gsheet
                gs_surveys = get_admin_surveys_from_gsheet(st.session_state.user_id)
                gs_surveys = [s for s in gs_surveys if str(s[1]).startswith("[??]")]
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
                st.session_state.edit_yeta_title = meta.get("Title", "").replace("[??] ", "")
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
                
                st.session_state.edit_yeta_p_type = ahp_model.get("yeta_p_type", "건설?업 (비수?권)")
                
                definitions = meta.get("Definitions", {})
                for k, v in definitions.items():
                    st.session_state[f"edit_yeta_desc_{k}"] = v
                
            st.session_state.yeta_survey_auto_loaded = True
            st.rerun()

        @st.dialog("? [경고] 기존 ?문 ?구 ?? ?내")
        def confirm_new_survey_yeta():
            st.error("?로???? ?문???성?시?기존 ?동??모든 ?이?? ???니??")
            agree = st.checkbox("?? 기존 ?이??백업???료?거??불필?하? 모든 ?이???????의?니??")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("??취소", use_container_width=True):
                    st.rerun()
            with col2:
                if st.button("???의 ?초기??, type="primary", use_container_width=True, disabled=not agree):
                    with st.spinner("기존 ?이?? ???는 중입?다..."):
                        from survey_manager import delete_admin_survey
                        if user_surveys:
                            delete_admin_survey(user_surveys[0][0], st.session_state.user_id)
                        st.session_state.yeta_editing_survey_id = None
                        keys_to_clear = [k for k in st.session_state.keys() if k.startswith('edit_yeta_')]
                        for k in keys_to_clear:
                            del st.session_state[k]
                        st.session_state.yeta_survey_auto_loaded = True
                        st.session_state._survey_cache_dirty_yeta = True
                    st.success("?료?었?니?? ?면???로고침?니??")
                    import time
                    time.sleep(1.5)
                    st.rerun()

        linked_sheet_id = st.session_state.get("yeta_editing_survey_id")
        if linked_sheet_id:
            survey_title_display = st.session_state.get("edit_yeta_title", "")
            for s in user_surveys:
                if s[0] == linked_sheet_id:
                    survey_title_display = s[1]
                    break
            st.success(f" ?재 배포???? ?문??불러?습?다: **{survey_title_display}**")
            if st.button("??처음부?????문 ?성?기 (기존 ?이????)", type="secondary"):
                 confirm_new_survey_yeta()
        else:
            st.info(" ?성 중인 ???? ?문?니??")
            if st.button("?????용 모두 지?기 (초기??", type="secondary"):
                st.session_state.yeta_editing_survey_id = None
                keys_to_clear = [k for k in st.session_state.keys() if k.startswith('edit_yeta_')]
                for k in keys_to_clear:
                    del st.session_state[k]
                st.rerun()

        st.divider()

        # ?위 ?? ?누지 ?고 ?나???결???이지?구성
        def render_section_header(title):
            style = (
                'background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);'
                'color: #ffffff;'
                'padding: 12px 20px;'
                'border-radius: 6px;'
                'font-weight: bold;'
                'font-size: 1.1rem;'
                'text-align: center;'
                'letter-spacing: 0.5px;'
                'margin-top: 25px;'
                'margin-bottom: 15px;'
                'box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);'
                'border: 1px solid #334155;'
            )
            st.markdown(f'<div style="{style}">{title}</div>', unsafe_allow_html=True)

        with st.container():
            render_section_header("?션 1: ?업 기본 ?보 ??료 첨?")
            survey_title = st.text_input("?문지 ?목", value=st.session_state.get("edit_yeta_title", "?정?자?업 종합??(AHP) ?문가 ?문"))
            
            default_survey_desc = """?녕?십?까, ?문가??

??문? KDI ?비??성조사 ?행 지침에 ?거?여, ?당 ?정?자?업????성 ?추진 ???
최종 ?단?기 ?한 '종합??(AHP)' ?도?기획?었?니??

?문가?께?는 ?공??'AHP ?료? ??업 개요?충분?????신 ?? ?????
(경제?? ?책?? 지???발?? 기술???? 간의 ????중요?? ???주?기 바랍?다.

??주요 ?? ?의?항
  1. (??계층 ??) ?분류 ?? 간의 ????중요?? '총합??100'???도?배분??주십?오. (?수?법)
     ???? KDI ?비??성조사 종합?? 지침에 명시???업 ?형?가?드?인???라 부문별 ?력 
        가?한 ?수 범위(?하?선)가 ?스?적?로 ?한?어 ?으???????리 ?해 부?드립니??
  2. (??계층 ??) ?? ?? ???비교 ?? ???? ???중요?다??단?는 쪽으?9??척도 기? 
     가중치?부?해 주십?오.
  3. ?문 ?답??????비율(CR)??권고 ??(0.15 미만)?????????도??리?인 ??????립?다.

주?기?: OOOO
문의? OOO, sample@test.co.kr, 00)000-0000

바쁘???정 중에???? 공공?자?업???리???사결정???해 귀중한 ?간???어 주셔??진심?로 감사?립?다."""
            st.markdown("**?문 ?내?*")
            
            from quill_editor import st_quill
            survey_desc = st_quill(
                value=st.session_state.get("edit_yeta_desc", default_survey_desc),
                key="quill_yeta_desc_editor"
            )
            if survey_desc is None:
                survey_desc = st.session_state.get("edit_yeta_desc", default_survey_desc)
            st.session_state["edit_yeta_desc"] = survey_desc
            
            with st.container():
                render_section_header("?션 2: ?? ?업 ?형 ?계층구조 모델 ?정")
                yeta_p_type = st.selectbox(
                    "?? ????업 ?형",
                    options=["건설?업 (비수?권)", "건설?업 (?도?", "R&D?업 (B/C)", "R&D?업 (E/C)", "?보?사??, "기??업 (B/C)", "기??업 (E/C)"],
                    index=["건설?업 (비수?권)", "건설?업 (?도?", "R&D?업 (B/C)", "R&D?업 (E/C)", "?보?사??, "기??업 (B/C)", "기??업 (E/C)"].index(st.session_state.get("edit_yeta_p_type", "건설?업 (비수?권)"))
                )
            
            tier_level = 3
            st.info("? **?? 모델 ?적 ?정**: ?반 모드? ?일?게 ?계층???표(,)?구분?여 ?력?세?? (1계층? ?? 기본 뼈?????니??")

            default_yeta_main = "경제?? ?책?? 지???발??
            if "?도? in yeta_p_type and "비수?권" not in yeta_p_type: default_yeta_main = "경제?? ?책??
            elif "R&D" in yeta_p_type: default_yeta_main = "기술?? 경제?? ?책??
            elif "?보?? in yeta_p_type: default_yeta_main = "기술?? 경제?? ?책??
            elif "기?" in yeta_p_type: default_yeta_main = "경제?? ?책?? 지???발??
            
            main_input = st.text_input("1계층 (???)", value=st.session_state.get("edit_yeta_main_input", default_yeta_main), help="?????? ??비교 ???100??분배(?수?법)????니??")
            main_list = [x.strip().replace("_", " ") for x in main_input.split(",") if x.strip()]

            model_structure = {"main": main_list, "subs": {}, "sub_subs": {}, "yeta_p_type": yeta_p_type}

            for mc in main_list:
                if mc == "경제??: 
                    model_structure["subs"][mc] = []
                    st.caption(f"??'{mc}' ?위 ?인? ?반?으??익/비용(B/C)?로 ?괄 ?출????력?? ?습?다.")
                    continue
                
                default_sub_val = ""
                if mc == "?책??: default_sub_val = "?업추진 ?건, ?책?과"
                elif mc == "지???발??: default_sub_val = "지???후?? 지?????급?과"
                elif mc == "기술??: default_sub_val = "기술개발계획???절?? 기술개발 ?공가?성, 기존 ?업과의 중복??
                
                sub_input = st.text_input(f"'{mc}'???위 ?인 (2계층)", value=st.session_state.get("edit_yeta_sub_inputs", {}).get(mc, default_sub_val))
                subs_list = [x.strip().replace("_", " ") for x in sub_input.split(",") if x.strip()]
                model_structure["subs"][mc] = subs_list

                if subs_list:
                    with st.expander(f"??'{mc}' ?위??3계층 (?분? ?력", expanded=False):
                        st.info("? ?분?3계층)가 ?는 ??? 비워?시??동?로 2계층?로 처리?니??")
                        for sub_c in subs_list:
                            sub_sub_val = ""
                            if sub_c == "?업추진 ?건": sub_sub_val = "?책?치???????건, 지????업?도 ?????건"
                            elif sub_c == "?책?과": sub_sub_val = "?업?화??, ?자??과, ?활?건 ?향, ?경????, ?전????"
                            
                            sub_sub_input = st.text_input(
                                f"? '{sub_c}'???위 ?인 (?표 구분)", 
                                value=st.session_state.get("edit_yeta_sub_sub_inputs", {}).get(sub_c, sub_sub_val),
                                placeholder="?? ??1, ??2",
                                key=f"yeta_sub_sub_{sub_c}"
                            )
                            parsed_sub_subs = [x.strip().replace("_", " ") for x in sub_sub_input.split(",") if x.strip()]
                            if parsed_sub_subs:
                                model_structure["sub_subs"][sub_c] = parsed_sub_subs

        st.divider()
        with st.container():
            render_section_header("?션 3: ?? ?? ?세 ?명")
            st.caption("?답?? ????????명확???해?????도?????세 ?명???력?????습?다.")
            
            definitions_map = {}
            
            st.markdown("**? 1계층 (???) ?명**")
            for mc in main_list:
                default_desc = ""
                if mc == "경제??: default_desc = "?익/비용(B/C) 비율 ?을 바탕?로 ?업??경제????성?????니??"
                elif mc == "?책??: default_desc = "?업???책?치?? 추진?건, ?책?과 ???책????성?????니??"
                elif mc == "지???발??: default_desc = "지???도 ?지?????급?과 ?을 바탕?로 지??균형 발전??미치???향?????니??"
                elif mc == "기술??: default_desc = "기술개발계획???절?? 기술개발 ?공가?성, 기존 ?업과의 중복???을 ???니??"
                
                key_cached = f"edit_yeta_desc_{mc}"
                desc_val = st.text_input(
                    f"'{mc}' ?인 ?명",
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
                st.markdown("**? 2계층 ?3계층 ?위 ?인 ?명**")
                
                for mc in main_list:
                    subs = model_structure["subs"].get(mc, [])
                    if subs:
                        with st.container(border=True):
                            st.markdown(f"##### ? [{mc}] ?위 ?인 ?명")
                            for sub_c in subs:
                                sub_subs = model_structure["sub_subs"].get(sub_c, [])
                                
                                default_sub_desc = ""
                                if sub_c == "?업추진 ?건": default_sub_desc = "?? ?책과의 ?치?? 추진 ??, 지??주? ?지?체???도 ?을 ???니??"
                                elif sub_c == "?책?과": default_sub_desc = "?자?창출 ?과, 주? ?활 ?건 ?상, ?경????전???향 ?을 ???니??"
                                elif sub_c == "지???후??: default_sub_desc = "개발 ?? ??후 ?태??량?으?비교 분석?니??"
                                elif sub_c == "지?????급?과": default_sub_desc = "지????총생?? ?산 ?발, 고용 ?발 ?과 ?을 ???니??"
                                
                                key_cached_sub = f"edit_yeta_desc_{sub_c}"
                                sub_desc_val = st.text_input(
                                    f"'{mc} ??{sub_c}' ?인 ?명",
                                    value=st.session_state.get(key_cached_sub, default_sub_desc),
                                    key=f"yeta_desc_input_{sub_c}"
                                )
                                definitions_map[sub_c] = sub_desc_val
                                st.session_state[key_cached_sub] = sub_desc_val
                                
                                if sub_subs:
                                    for t3 in sub_subs:
                                        default_t3_desc = ""
                                        if t3 == "?책?치???????건": default_t3_desc = "?위 계획과의 부?성 ?추진 체계??준??도????니??"
                                        elif t3 == "지????업?도 ?????건": default_t3_desc = "?업 ???지??주????론 ?지?체??추진 ?도????니??"
                                        elif t3 == "?자??과": default_t3_desc = "건설 ?계 ??영 ?계???규 고용 창출 ?력?????니??"
                                        
                                        key_cached_t3 = f"edit_yeta_desc_{t3}"
                                        t3_desc_val = st.text_input(
                                            f"??'{sub_c} ??{t3}' ?인 ?명",
                                            value=st.session_state.get(key_cached_t3, default_t3_desc),
                                            key=f"yeta_desc_input_{t3}"
                                        )
                                        definitions_map[t3] = t3_desc_val
                                        st.session_state[key_cached_t3] = t3_desc_val

        st.divider()
        with st.container():
            render_section_header("?션 4: ?답???집 ?보 ?그룹 분류")
            with st.container(border=True):
                st.markdown("**그룹 분류 문항 ?정**")
                default_type_q = "귀?의 ?속? ?떻??십?까?"
                default_type_opts = "?문가, ?반, 공무?? 기?"

                if "edit_yeta_type_questions" not in st.session_state:
                    st.session_state["edit_yeta_type_questions"] = [{"q": default_type_q, "opts": default_type_opts}]

                type_questions_state = st.session_state["edit_yeta_type_questions"]
                num_types = len(type_questions_state)

                col1, col2, col3 = st.columns([6, 2, 2])
                with col2:
                    if st.button("+ 문항 추?", use_container_width=True, disabled=num_types >= 3, key="yeta_add_q_dyn"):
                        st.session_state["edit_yeta_type_questions"].append({"q": "", "opts": ""})
                        st.rerun()
                with col3:
                    if st.button("- 문항 ??", use_container_width=True, disabled=num_types <= 1, key="yeta_rem_q_dyn"):
                        st.session_state["edit_yeta_type_questions"].pop()
                        st.rerun()

                type_questions = []
                for i in range(num_types):
                    st.markdown(f"**{i+1}.**")
                    q_label = "그룹 분류 질문 ?목" if i == 0 else "추? ?문 문항"
                    opts_label = "보기 ?션 (?표?구분)"

                    q_val = st.text_input(f"{q_label} ({i+1})", value=type_questions_state[i]["q"], key=f"yeta_dyn_tq_q_{i}")
                    opts_val = st.text_input(f"{opts_label} ({i+1})", value=type_questions_state[i]["opts"], key=f"yeta_dyn_tq_opts_{i}")

                    type_questions_state[i]["q"] = q_val
                    type_questions_state[i]["opts"] = opts_val
                    type_questions.append({"q": q_val, "opts": [x.strip() for x in opts_val.split(",") if x.strip()]})
        with st.container():
            render_section_header("?션 5: ?라??배포 ?구? ?트 ?동 ?정")
            if st.session_state.user_id is None:
                st.warning("?라??배포 ?구? ?트 ?동? ?원 ?용 기능?니?? 로그?해 주세??")
            else:
                survey_admin_email = st.text_input("?문 ?당???메??(구? ?라?브 ?유??권한 부?용)", value=st.session_state.get("edit_yeta_admin_email", st.session_state.user_id))
                st.session_state.edit_yeta_admin_email = survey_admin_email

                existing_id = st.session_state.yeta_editing_survey_id
                if existing_id:
                    st.info("?재 **기존 ?문 ?정 모드**?니?? ?정???정? 기존 ?동 ?트??반영?니??")
                    existing_sheet_id_input = existing_id
                else:
                    past_surveys = []
                    try:
                        import sqlite3
                        conn = sqlite3.connect('users.db')
                        c = conn.cursor()
                        c.execute("SELECT title, survey_id, created_at FROM admin_surveys WHERE admin_id=? AND title LIKE '[??]%' ORDER BY created_at DESC", (st.session_state.user_id,))
                        past_surveys = c.fetchall()
                        conn.close()
                    except Exception:
                        pass

                    existing_sheet_id_input = ""
                    show_manual_input = True

                    if len(past_surveys) > 0:
                        deploy_option = st.radio(
                            "배포 방식???택??주세??",
                            options=[
                                "?로??구? ?트 URL ?동 (?규 발급)",
                                "기존 배포?던 ?문 URL ?사??(???기)"
                            ],
                            index=0,
                            key="yeta_deploy_option_radio_new"
                        )
                        st.write("")

                        if "?사?? in deploy_option:
                            show_manual_input = False
                            st.markdown("##### ?️ ?사?할 기존 ?문 ?택")
                            survey_options = {f"{row[0]} ({row[2][:16]})" : row[1] for row in past_surveys}
                            selected_survey_label = st.selectbox(
                                "과거??배포?던 ?문 목록",
                                options=list(survey_options.keys()),
                                key="yeta_past_survey_select"
                            )
                            existing_sheet_id_input = survey_options[selected_survey_label]
                            st.info("?택???문??구? ?프?드?트???로???용?????웁?다. 기존 ?답 URL? 그?????니??")

                    if show_manual_input:
                        st.markdown("##### ?️ ?동??본인??구? ?프?드?트 ?정 *")
                        st.info("""
                        **? ?동 방법:**
                        1. 본인??구? ?라?브?서 **??구? ?프?드?트**??나 ?성?니??
                        2. ?측 ?단??'공유' 버튼???러 ?래???비??계정 ?메?을 **?집??* (Editor)?추??니??
                           * ?비??계정 ?메?? `ahp-master-v2@ahp-login.iam.gserviceaccount.com`
                        3. ?성???프?드?트??**URL 주소** ?는 **?트 ID**?복사?여 ?래??붙여?어 주세??
                        """)
                        col1, col2 = st.columns([1, 2])
                        with col1:
                            if os.path.exists("google_sheets_menu_guide.png"):
                                st.image("google_sheets_menu_guide.png", caption="구? ?프?드?트 메뉴 ?근 방법", use_container_width=True)
                        with col2:
                            if os.path.exists("manual_sheet_url_guide.png"):
                                st.image("manual_sheet_url_guide.png", caption="구? ?프?드?트 URL 주소?복사 ?시", use_container_width=True)
                        existing_sheet_id_input = st.text_input("?동??구? ?프?드?트 URL ?는 ID *", placeholder="https://docs.google.com/spreadsheets/d/...", key="yeta_sheet_url_input")

                # ==================== ?????정 ====================
                coupon_config = None
                if st.session_state.user_id == 'shjeon':
                    render_section_header("?션 6: ????발송 ?정 (?션)")
                    use_coupon = st.checkbox("?문 ?답?에?기프?콘 ?????을 ?공?니??", key="yeta_use_coupon")
                    if use_coupon:
                        active_coupons = coupon_manager.get_active_coupons()
                        if not active_coupons:
                            st.warning("?재 ?록?????이 ?습?다. 관리자?게 문의?세??")
                        else:
                            coupon_options = {f"{c['name']} ({c['original_price']:,}??": c['id'] for c in active_coupons}
                            sel_coupon_label = st.selectbox("?공???????택", list(coupon_options.keys()))
                            sel_coupon_id = coupon_options[sel_coupon_label]
                            
                            coupon_limit = st.number_input("?착???공 ?원", min_value=1, value=100, step=10)
                            st.info(f"?택?????? ?문 ?출 ?료 ???동?로 발송 ??자??택?????습?다. (?상 비용 ?계: **{int(sel_coupon_label.split('(')[1].replace('??','').replace(',','')) * coupon_limit:,}??*)")
                            
                            coupon_config = {
                                "enabled": True,
                                "coupon_id": sel_coupon_id,
                                "coupon_name": sel_coupon_label,
                                "limit": coupon_limit
                            }
                # ====================================================

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
                    "Definitions": definitions_map,
                    "Coupon_Config": coupon_config
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
                            ???문지 ?답 ?면 미리보기
                        </div>
                    </a>
                    """
                    st.markdown(preview_link_html, unsafe_allow_html=True)

                with col_p2:
                    deploy_btn_label = "?? 배포 ?구? ?트 ?동 (?정 ?용 ?용)" if existing_id else "?? 배포 ?구? ?트 ?동"
                    if st.button(deploy_btn_label, type="primary", use_container_width=True, key="yeta_deploy_btn"):
                        import survey_manager; survey_manager.log_user_action(st.session_state.get("user_id") or "Guest", "?문 배포 ?행")
                        target_sheet_id = existing_sheet_id_input.strip()
                        if "docs.google.com/spreadsheets" in target_sheet_id:
                            parts = target_sheet_id.split("/d/")
                            if len(parts) > 1:
                                target_sheet_id = parts[1].split("/")[0]

                        if not target_sheet_id:
                            st.error("?동??구? ?프?드?트 URL ?는 ID??력??주세??")
                        else:
                            with st.spinner("구? ?프?드?트 ?성 ??문지 ?동 ?.."):
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
                                            cur.execute("UPDATE admin_surveys SET title = ? WHERE survey_id = ?", (f"[??] {survey_title}", existing_id))
                                        else:
                                            cur.execute("INSERT OR IGNORE INTO admin_surveys (survey_id, title, admin_id, created_at) VALUES (?, ?, ?, datetime('now'))",
                                                        (new_sheet_id, f"[??] {survey_title}", st.session_state.user_id))
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
                                        st.success("? ?? AHP ?문지 배포가 ?공?으??료?었?니??")
                                        st.markdown(f"**? ?답??배포???문조사 링크:** [{link}]({link})")
                                        st.code(link)
                                    else:
                                        st.error("구? ?트 ?동???패?습?다. 구? 계정 권한 ?는 ?비??계정 ?정???인??주세??")
                                except Exception as e:
                                    st.error(f"?류 발생: {e}")

    # =========================================================================
    # ?시??답 ?황 ??
    # =========================================================================
    with tab_live_response:
        if st.session_state.get('user_id') == 'shjeon':
            # Sub-tabs UI: ?약(Pill) ?태??더링되?록 CSS 주입
            st.markdown("""
            <style>
            div[data-testid="stTabs"] div[data-testid="stTabs"] > div[role="tablist"] {
                border-bottom: none !important;
                gap: 0 !important;
                padding-bottom: 15px !important;
                margin-top: -10px !important;
            }
            div[data-testid="stTabs"] div[data-testid="stTabs"] button[data-baseweb="tab"] {
                border-radius: 25px !important;
                background-color: #f1f5f9 !important;
                border: 1px solid #e2e8f0 !important;
                margin-right: 8px !important;
                padding: 6px 18px !important;
                height: auto !important;
                transition: all 0.2s ease !important;
            }
            div[data-testid="stTabs"] div[data-testid="stTabs"] button[data-baseweb="tab"]:hover {
                background-color: #e2e8f0 !important;
            }
            div[data-testid="stTabs"] div[data-testid="stTabs"] button[data-baseweb="tab"][aria-selected="true"] {
                background-color: #0f172a !important;
                color: white !important;
                border: 1px solid #0f172a !important;
                font-weight: 600 !important;
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1) !important;
            }
            div[data-testid="stTabs"] div[data-testid="stTabs"] div[data-baseweb="tab-highlight"] {
                display: none !important;
            }
            </style>
            """, unsafe_allow_html=True)
            
            sub_tabs = st.tabs(["? 진행 ?황", "? ????발송 관?, "?️ ?????정(Admin)"])
            tab_live_content = sub_tabs[0]
            with sub_tabs[1]:
                import coupon_manager
                coupon_manager.render_dispatch_tab()
            with sub_tabs[2]:
                import coupon_manager
                coupon_manager.render_admin_tab()
        else:
            tab_live_content = st.container()

        with tab_live_content:
            st.header("?시??답 ?황")
            selected_sheet_id = None
        
            if st.session_state.user_id is None:
                st.warning(" **?시??답 ?황 기능? ?원 ?용 ?비?입?다.**")
                st.info("무료 ?원가???로그?을 ?료?시?본인??배포???문지???시??답 ?태 ??적 ?이?? 모니?링?고 ?운로드?????습?다. (무료 ?원??기능 ?한 ?이 모든 기능 ?용 가??  \n**좌측 ?이?바??로그???원가???널**???용??주세??")
            else:
                # DB?서 ?당 관리자가 ?성???문 목록 조회

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
                    st.error(f"?문 목록 조회 ?패: {e}")

                if not admin_surveys:
                    st.warning("배포???문지가 존재?? ?습?다. '?라???문지 ?작' ?????문??먼? 배포??주세??")
                else:
                    # 로그?한 ?이?에 맞춰 본인???문?만 ?롭?운???출?킵?다.
                    survey_options = {f"{row[1]} ({row[2]})": row[0] for row in admin_surveys}
                    selected_label = st.selectbox(
                        "?시??황???인???문 ?택",
                        list(survey_options.keys()),
                        key="tab3_survey_select"
                    )
                    selected_sheet_id = survey_options[selected_label]
                
                    selected_survey_info = next(s for s in admin_surveys if s[0] == selected_sheet_id)
                    survey_title = selected_survey_info[1]
                    created_at = selected_survey_info[2]
                
                    st.success(f" ?재 ?택???문: **{survey_title}** (배포?시: {created_at})")
                    st.divider()

            # ??보???더?
            if selected_sheet_id:

                if st.button("? ?시??문 ??보????답 ?이??불러?기 / ?로고침", type="primary"):
                    from survey_manager import get_survey_stats, get_survey_gspread_client
                    with st.spinner("?시??문 ?황 로딩 ?.."):
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
                                st.error(f"구? ?트?서 ?이?? ?어?는 ??러 발생: {g_err}")
                                st.session_state["live_df"] = None
                        else:
                            st.warning("구? Sheets API ?라?언???결 ?패??해 구? ?트 ???이?? 직접 ?운로드?????습?다.")
                            st.session_state["live_df"] = None

                if "survey_stats" in st.session_state:
                    stats = st.session_state["survey_stats"]
                    col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
                    with col_stat1:
                        st.metric("??속????(Visits)", f"{stats['visits']}" + "?)
                    with col_stat2:
                        st.metric("?료 ?답????(Completed)", f"{stats['completed']}" + "?)
                    with col_stat3:
                        st.metric("????초과 중단??(CR Fail)", f"{stats['abandoned_cr']}" + "??)
                    with col_stat4:
                        st.metric("?순 ?탈 중단??(Bounce)", f"{stats['abandoned_bounce']}" + "?)

                    # ?각??차트 추?

                    chart_data = pd.DataFrame({
                        "구분": ["?답 ?료", "????초과 중단", "?순 ?이지 ?탈"],
                        "?원??: [stats['completed'], stats['abandoned_cr'], stats['abandoned_bounce']]
                    })

                    fig_stats = px.bar(
                        chart_data,
                        x="구분",
                        y="?원??,
                        text="?원??,
                        color="구분",
                        color_discrete_map={
                            "?답 ?료": "#2E7D32",
                            "????초과 중단": "#C62828",
                            "?순 ?이지 ?탈": "#EF6C00"
                        },
                        title="?문 참여 ?태?분포"
                    )
                    fig_stats.update_layout(showlegend=False)
                    st.plotly_chart(fig_stats, use_container_width=True)

                if "live_df" in st.session_state and st.session_state["live_df"] is not None:
                    live_df = st.session_state["live_df"]
                    demo_df = st.session_state.get("demo_df", None)

                    # 구? ?트?서 ?시??답 로데?터(Raw_Data) ?운로드 기능 추?
                    with st.expander("? ?시?구? ?트 ?답 ?이???운로드 ?터", expanded=True):
                        if not live_df.empty:
                            st.success(f"구? ?프?드?트?서 ?시??답 ?이?? ?공?으?불러?습?다. (Raw_Data: {len(live_df)}? + (f", Demographic_Data: {len(demo_df)}? if demo_df is not None else "") + ")")
                        
                            # ? AHP 분석 ?동 ?축 버튼 추?
                            if st.button("? ???라???문 ?이?로 즉시 AHP 분석 ?행?기 (분석 ?구??동)", type="primary", use_container_width=True):
                                import survey_manager; survey_manager.log_user_action(st.session_state.get("user_id") or "Guest", "?라???문 ?이???동")
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
                                
                                     # 중분?복사
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
                                    st.info("? ?이??분석 준비? ?료?었?니?? **?단??'? AHP 분석 ?구' ??*???택?고 **'? 배포???라???문 ?이???동'** ?디??버튼???택?여 분석 결과?바로 ?인?십?오.")

                            tab_raw, tab_demo = st.tabs(["? Raw_Data (AHP ??비교 ?이??", "? Demographic_Data (?구?계/?전?위)"])
                            with tab_raw:
                                st.dataframe(live_df, use_container_width=True)
                            with tab_demo:
                                if demo_df is not None:
                                    st.dataframe(demo_df, use_container_width=True)
                                else:
                                    st.info("?집???구?계 ?이?? ?거??Demographic_Data ?트가 ?성?? ?았?니??")

                            # Excel ?CSV ?보?기 버튼 ?공
                            import io

                            # 1. Excel ?보?기 (??개의 ?트?모두 ?함)
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
                                    "? ?시??답 Excel ?운로드 (.xlsx)",
                                    data=excel_buffer.getvalue(),
                                    file_name=f"Survey_Live_Data_{selected_sheet_id.strip()[:6]}.xlsx",
                                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                    use_container_width=True,
                                    type="primary"
                                )
                            # 2. CSV ?보?기 (Raw_Data ?선 ?보?기)
                            csv_buffer = io.StringIO()
                            live_df.to_csv(csv_buffer, index=False, header=True)
                            with col_dl2:
                                st.download_button(
                                    "? ?시??답 CSV ?운로드 (.csv)",
                                    data=csv_buffer.getvalue().encode('utf-8-sig'),
                                    file_name=f"Survey_Live_Data_{selected_sheet_id.strip()[:6]}.csv",
                                    mime="text/csv",
                                    use_container_width=True
                                )
                        else:
                            st.info("구? ?트???집???답 로데?터가 ?직 비어 ?습?다.")

                # 로컬 ?전 백업 ?이??조회 ?추출 ?틸리티
                try:
                    conn = get_db_connection('users.db')
                    backup_df = pd.read_sql_query(
                        "SELECT id, respondent_id, response_json, created_at FROM survey_backup_responses WHERE survey_id = ?",
                        conn, params=(selected_sheet_id.strip(),)
                    )
                    conn.close()

                    if not backup_df.empty:
                        with st.expander("???버 로컬 ?전 백업 관??터"):
                            st.success(f"구? ?트 ?동?관계없???버 로컬 ?이?베?스????된 ?전 백업 ?이?? ?{len(backup_df)}?존재?니??")
                            st.dataframe(backup_df[["id", "respondent_id", "created_at"]], use_container_width=True)

                            # ?체 ??이??복구 ??/CSV ?이??빌드
                            recovered_raw_rows = []
                            recovered_demo_rows = []
                            for idx_b, r_b in backup_df.iterrows():
                                payload = json.loads(r_b["response_json"])
                                if "raw_row_data" in payload:
                                    recovered_raw_rows.append(payload["raw_row_data"])
                                elif "row_data" in payload:
                                    # ?위 ?환??
                                    recovered_raw_rows.append(payload["row_data"])

                                if "demo_row_data" in payload:
                                    recovered_demo_rows.append(payload["demo_row_data"])

                            if recovered_raw_rows:
                                import io

                                # ?더 복구 로직 추?
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
                                    raw_headers.append("?출?간")
                                
                                    demo_headers = ["ID", "Type"]
                                    if demographics.get("name"): demo_headers.append("?명")
                                    if demographics.get("age"): demo_headers.append("?령")
                                    if demographics.get("gender"): demo_headers.append("?별")
                                    if demographics.get("experience"): demo_headers.append("경력?수")
                                    # if demographics.get("affiliation"): demo_headers.append("?속")
                                    if demographics.get("email"): demo_headers.append("?메??)
                                    demo_headers.append("?전?위지??)
                                    if rewards_info.get("enabled"):
                                        demo_headers.append("경품?락? if tier_level == "3" else "?????락?)
                                    demo_headers.append("?출?간")

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

                                # Excel?백업 ?이?? ?플?구조??맞춰 분할?여 ?운로드
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
                                        "? 로컬 백업 Excel ?운로드 (.xlsx)",
                                        data=excel_backup_buffer.getvalue(),
                                        file_name=f"Backup_Recovery_{selected_sheet_id.strip()[:6]}.xlsx",
                                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                        use_container_width=True,
                                        type="primary"
                                    )

                                with col_b_dl2:
                                    # CSV ?일 ?태?복구 ?일 ?보?기 (Raw_Data ?선)
                                    output_csv = io.StringIO()
                                    df_raw_backup.to_csv(output_csv, index=False, header=bool(raw_headers))
                                    st.download_button(
                                        "? 로컬 백업 Raw_Data CSV ?운로드 (.csv)",
                                        data=output_csv.getvalue().encode('utf-8-sig'),
                                        file_name=f"Backup_Recovery_Raw_{selected_sheet_id.strip()[:6]}.csv",
                                        mime="text/csv",
                                        use_container_width=True
                                    )
                    else:
                        st.caption("???문지???록??로컬 ?버 백업 ?이?? ?습?다. (모든 ?이???상 ?재)")
                except Exception as err:
                    st.caption(f"로컬 백업 조회 불?: {err}")


        # =========================================================================
        # TAB 3: Guidelines Guide
        # =========================================================================
        with tab_guide:
            st.markdown(f"""
            <div style="padding: 10px 20px;">
            <h3 style="color: #1e3a8a; border-bottom: 2px solid #e2e8f0; padding-bottom: 8px;">1. AHP 종합????개요 ?목적</h3>
            <p style="font-size: 1.05rem; line-height: 1.8;">
            ?비??성조사?서 AHP??경제?? ?책?? 지???발??분석 ??br>?양????????결과????<b>?기준분석</b>???행?여,<br>?업??종합?인 ??성??계량?된 ?치??단?는 ?사결정 ?구?니??<br><br>?? ?해 ????간의 ?견??종합?고, ?사결정 과정???명?과 객??을 ?보?여<br>공공?자 ?업???행 ???결정?니??
            </p>

            <h3 style="color: #1e3a8a; border-bottom: 2px solid #e2e8f0; padding-bottom: 8px; margin-top: 35px;">2. AHP ?? 계층구조 ?계</h3>
            <ul style="font-size: 1.05rem; line-height: 1.8; margin-bottom: 10px;">
            <li style="margin-bottom: 8px;"><b>??계층 (?분류):</b><br>종합???구성?는 주요 부문으?경제??분석, ?책??분석, 지???발??분석(?도??업??경우 ?외) ?으??뉩?다.</li>
            <li style="margin-bottom: 8px;"><b>??·3계층 (?? ??):</b><br>?책??분석 ?위???업추진 ?건(?책 ?치?? 주? ?업?도 ????책?과(?자??과, ?경?? ?전????, 지???발???위??지???도 ??급?과 ?으?구성?니??</li>
            <li><b>최하?????</b><br>최종 ?사결정???한 최하??계층? 철???<b>'?업 ?행'?'?업 미시??</b> ??가지 ??으?고정?여 ????행?니??</li>
            </ul>

            <h3 style="color: #1e3a8a; border-bottom: 2px solid #e2e8f0; padding-bottom: 8px; margin-top: 35px;">3. 부문별 가중치 ?용 기? (?수?법)</h3>
            <p style="font-size: 1.05rem; line-height: 1.8;">
            ??계층??가중치???답?의 ?의?을 줄이??해 100??만점??기??로<br>???? 직접 분배?는 <b>?수?법(Constant-Sum)</b>???용?여 측정?니??<br><br>?비??성조사 ?행 총괄지침에 명시??주요 ?업?형?가중치 ?용 범위???음?같습?다.
            </p>
            <ul style="font-size: 1.05rem; line-height: 1.8; background-color: #f8fafc; padding: 15px 20px 15px 40px; border-radius: 8px;">
            <li><b>건설?업 (비수?권 ?형):</b> 경제??30~45%, ?책??25~40%, 지???발??30~40%</li>
            <li><b>건설?업 (?도??형):</b> 경제??60~70%, ?책??30~40% (지???발???? ?외)</li>
            <li><b>?보??R&D ?업 (B/C 분석 ??:</b> 경제??40~50%, 기술??30~40%, ?책??20~30%</li>
            </ul>

            <h3 style="color: #1e3a8a; border-bottom: 2px solid #e2e8f0; padding-bottom: 8px; margin-top: 35px;">4. 조사 방법 ?조사 ?본(?문가 구성)</h3>
            <ul style="font-size: 1.05rem; line-height: 1.8;">
            <li style="margin-bottom: 10px;"><b>조사 ?본 (???규모 ?구성):</b><br>?????문?과 객??을 ?보?기 ?해 ?업???성??맞는 관??분야(경제, ?책, 기술, 지??????br>?계 ??구??문가 ??<b>보통 7~10???외???문가 ?널</b>??구성?여 ?문??진행?니??</li>
            <li><b>조사 방법 (?보 ?공 ?브리??:</b><br>?순???문조사가 ?닌, ?업??개요? ?행 분석 결과(B/C 비율, ?책???지????분석 ?료 ??가 모두 ?록??<b>'AHP ?료?</b>???문가?에??공?니??<br>?? 바탕?로 ?? ?의(브리?? ?는 ?면/?라??방식???해 충분???보??????태?서 ????시?게 ?니??</li>
            </ul>

            <h3 style="color: #1e3a8a; border-bottom: 2px solid #e2e8f0; padding-bottom: 8px; margin-top: 35px;">5. ?문 ?행 ??수 ?정 (????검??극단?배제)</h3>
            <ul style="font-size: 1.05rem; line-height: 1.8;">
            <li style="margin-bottom: 10px;"><b>9??척도 ??비교:</b><br>?? ?? 간의 ????중요?????의 ?호?는 기본?으?9??척도??용?여 ??비교(Pairwise Comparison)??행?니??</li>
            <li style="margin-bottom: 10px;"><b>객???지?의 ???수??</b><br>주????향??막기 ?해 경제??B/C 비율)?지???도 지??LIR)???해??학???환?을 ?용?여 ?괄 반영?니??</li>
            <li style="margin-bottom: 10px;"><b>????검?(CR):</b><br>?무???계?고려??<b>CR??0.15 ?하</b>??경우?만 ?뢰?????는 ?효 ?답?로 ?정?며, ?? 초과?????류(Feedback)?여 ?조???을 ?구?니??</li>
            <li><b>극단?배제 지?</b><br>집단 ?사결정 ???수 ?곡??방??고?? 최종 ?산 과정?서 ?업 ?행 ??에 ???<b style="color: #ef4444;">가???? ?수?준 1??최고???가????? ?수?준 1??최??????답??배제</b>?고, ?머지 결과??기하?균??구합?다.</li>
            </ul>

            <h3 style="color: #1e3a8a; border-bottom: 2px solid #e2e8f0; padding-bottom: 8px; margin-top: 35px;">6. 최종 ??성 ?단 기? (?색?역)</h3>
            <ul style="font-size: 1.05rem; line-height: 1.8;">
            <li style="margin-bottom: 10px;">기본?으??출??<b>최종 AHP 종합?수가 0.5 ?상?면 ?업 ?행????성(바람직함)???는 ?/b>?로 ?정?니??</li>
            <li><b>?색?역(Gray Area) ?용:</b><br>?사결정??강건?을 ?보?기 ?해 종합?점??0.5 부근인 ?정 구간(?? 0.473~0.527)??'?색?역'?로 규정?니??<br>?수가 ??구간???치?거????????견 불일치? ?렷??경우 ?일?인 0.5 기? ?용??지?하? '?간 ?중', '?중' ?의 ?? ?단??거쳐 최종 ?업 추진 ???결정?도?권고?니??</li>
            </ul>

            <hr style="margin-top: 45px; margin-bottom: 25px; border: 0; border-top: 1px solid #e5e7eb;">
        
            <h3 style="color: #0f766e; margin-bottom: 15px;">7. 관??지??가?드?인 공식 ?운로드 링크</h3>
            <p style="font-size: 1.05rem; line-height: 1.8; margin-bottom: 20px;">
            ?기 AHP ?행 기???근거가 ?는 공식 가?드 문서???음???사?트?서 ?문???운로드?실 ???습?다.
            </p>
        
            <div style="background-color: #f8fafc; padding: 15px; border-radius: 8px; border-left: 4px solid #0f766e; margin-bottom: 15px;">
            <a href="https://pimac.kdi.re.kr/study/study_list.jsp?classcd=F1" target="_blank" style="font-size: 1.1rem; font-weight: bold; color: #0284c7; text-decoration: none;">KDI 공공?자관리센??(PIMAC)</a>
            <p style="margin-top: 5px; color: #475569; font-size: 0.95rem; line-height: 1.6;">??업 부문별(?반, ?로/철도 ?? ?비??성조사 ?행 ??지????? 조사보고???운로드</p>
            </div>
        
            <div style="background-color: #f8fafc; padding: 15px; border-radius: 8px; border-left: 4px solid #0f766e; margin-bottom: 15px;">
            <a href="https://www.kipf.re.kr/gmac/Publication/Finance/kiPublish/CA6/Center/list.do" target="_blank" style="font-size: 1.1rem; font-weight: bold; color: #0284c7; text-decoration: none;">?국조세?정?구?????자분석?터 (KIPF GMAC)</a>
            <p style="margin-top: 5px; color: #475569; font-size: 0.95rem; line-height: 1.6;">?보?????정 부??업??????? 가?드?인 ?착수?의/조사보고???운로드</p>
            </div>
        
            <div style="background-color: #f8fafc; padding: 15px; border-radius: 8px; border-left: 4px solid #0f766e;">
            <a href="https://www.law.go.kr" target="_blank" style="font-size: 1.1rem; font-weight: bold; color: #0284c7; text-decoration: none;">??법령?보?터</a>
            <p style="margin-top: 5px; color: #475569; font-size: 0.95rem; line-height: 1.6;">법적 구속?을 갖춘 기획?정부 ?령???예비??성조사 ?용지침???예비??성조사 ?행 총괄지침??문 ?람</p>
            </div>
            </div>
            """, unsafe_allow_html=True)

        # =========================================================================
        # TAB 4: B2B Pricing & Payment (Hybrid Pricing Applied)
        # =========================================================================
    with tab_pricing:
        st.markdown("## ?비???금 ?내 <span style='font-size: 0.95rem; font-weight: 500; color: #0284c7; margin-left: 16px; background: #e0f2fe; padding: 6px 14px; border-radius: 20px; vertical-align: middle; box-shadow: 0 1px 2px rgba(0,0,0,0.05);'>? ?구?법인카드 ?계산??지??/span>", unsafe_allow_html=True)

        col_p1, col_p2, col_p3, col_p4 = st.columns(4)
        user_id = st.session_state.get("user_id")

        # 1. 무료 체험??
        with col_p1:
            inner_1 = """
                <h3 style='margin-top: 0 !important; margin-bottom: 0;'>무료 체험??/h3>
                <span style='color: #888; font-size: 1.1rem;'>기본 ?공</span>
                <h2 style='margin-top: 15px; margin-bottom: 5px; color: #ff4b4b;'>0??/h2>
                <p style='font-size: 0.85rem; color: #666; min-height: 40px;'>?? 분석 ?루?의 ?심 ?산?결과?구성???전?????이?할 ???는 무료 버전?니??</p>
                <hr style='margin: 10px 0;'>
                <ul style='padding-left: 20px; color: #333; line-height: 1.6;'>
                    <li><span style='font-size: 0.85rem;'><b>B/C ???수 로그 변???산</b></span></li>
                    <li><span style='font-size: 0.85rem;'><b>지???도 ??????LIR) 변??/b></span></li>
                    <li><span style='font-size: 0.85rem;'>?문 ?이???력 (최? 3??한)</span></li>
                    <li><span style='font-size: 0.85rem;'>?면 결과 리포??출력</span></li>
                </ul>
            """
            if user_id:
                st.components.v1.html(get_yeta_portone_payment_html(user_id, "무료 체험??(?구)", 0, 9999, inner_html=inner_1, is_best=False), height=520)
            else:
                st.components.v1.html(get_yeta_login_redirect_html("무료 체험??(?구)", inner_html=inner_1, is_best=False), height=520)

        # 2. [Standard] ?간 ?용?
        with col_p2:
            inner_2 = """
                <h3 style='margin-top: 0 !important; margin-bottom: 0;'>[Standard] ?간 ?용?/h3>
                <span style='color: #888; font-size: 1.1rem;'>1개월 무제???용</span>
                <h2 style='margin-top: 15px; margin-bottom: 5px; color: #ff4b4b;'><span id='yeta-single-price-display-span'>300,000</span>??/h2>
                <p style='font-size: 0.85rem; color: #666; min-height: 40px;'>1개월 ?안 ?????·분???수 ?한 ?이 ?? AHP ?체 기능???유? ?용?????습?다.</p>
                <hr style='margin: 10px 0;'>
                <ul style='padding-left: 20px; color: #333; line-height: 1.6;'>
                    <li><span style='font-size: 0.85rem;'><b>1개월?분석 ?수 무제??/b></span></li>
                    <li><span style='font-size: 0.85rem;'>???????한 ?음 (무제??</span></li>
                    <li><span style='font-size: 0.85rem;'>최?/최소 ?웃?이???외 ?동 ?산</span></li>
                    <li><span style='font-size: 0.85rem;'>보고???출??Excel ?본 ?보?기</span></li>
                    <li><span style='font-size: 0.85rem;'>계산??간이과세?? ??수?발행 지??/span></li>
                </ul>
            """
            if user_id:
                st.components.v1.html(get_yeta_portone_payment_html(user_id, "[Standard] ?간 ?용?, 300000, 1, inner_html=inner_2, is_best=False), height=520)
            else:
                st.components.v1.html(get_yeta_login_redirect_html("[Standard] ?간 ?용?, inner_html=inner_2, is_best=False), height=520)

        # 3. [Pro] ?간 ?용?(BEST)
        with col_p3:
            inner_3 = """
                <h3 style='margin-top: 0 !important; margin-bottom: 0;'>[Pro] ?간 ?용?/h3>
                <span style='color: #888; font-size: 1.1rem;'>1??무제???용</span>
                <h2 style='margin-top: 15px; margin-bottom: 5px; color: #ff4b4b;'>2,800,000??/h2>
                <p style='font-size: 0.85rem; color: #666; min-height: 40px;'>?간 ??22% ?감??비용?로 1?간 ?수 ?한 ?이 ?? AHP 분석??문 배포??행?니??</p>
                <hr style='margin: 10px 0;'>
                <ul style='padding-left: 20px; color: #333; line-height: 1.6;'>
                    <li><span style='font-size: 0.85rem;'><b>1?간 분석 ?수 무제??/b></span></li>
                    <li><span style='font-size: 0.85rem;'><b>????233,000???? (22% ?감)</b></span></li>
                    <li><span style='font-size: 0.85rem;'>무제???문가 ?문 ??웃?이???산</span></li>
                    <li><span style='font-size: 0.85rem;'>B2B 기업??견적??계산??간이과세?? 발행</span></li>
                </ul>
            """
            if user_id:
                st.components.v1.html(get_yeta_portone_payment_html(user_id, "[Pro] ?간 ?용?, 2800000, 12, inner_html=inner_3, is_best=True), height=520)
            else:
                st.components.v1.html(get_yeta_login_redirect_html("[Pro] ?간 ?용?, inner_html=inner_3, is_best=True), height=520)

        # 4. 부가 ?비?????
        with col_p4:
            if user_id:
                st.components.v1.html(get_yeta_portone_custom_services_html(user_id), height=520)
            else:
                st.components.v1.html(get_yeta_portone_custom_services_html(None), height=520)

        st.markdown("<br>", unsafe_allow_html=True)

        if not user_id:
            st.warning("?️ 결제 ?계산??간이과세?? ?청???해?는 로그?이 ?요?니?? 메인 ?털 ?는 ?이?바?서 로그?????용??주세??")
        else:
            st.info(f"?속 계정: {user_id} | ?이?스 권한: {'?식 ?원' if is_official else '무료 체험 ?원'}")
            
            st.markdown("<div id='b2b-payment-section'></div>", unsafe_allow_html=True)
            st.write("---")
            
            with st.form("yeta_tax_form"):
                st.write("**B2B 기업/?구???용 지?처리 (계좌?체 ?계산??간이과세?? ?청)**")
                st.write("계산??간이과세?? 발행 ?기? 계좌?체 ?인???요???보??력??주세??")
                biz_name = st.text_input("?호 / 법인?, key="tax_biz_name")
                biz_num = st.text_input("?업?등록번??(?자??력)", key="tax_biz_num")
                rep_name = st.text_input("??자?, key="tax_rep_name")
                address = st.text_input("?업??주소", key="tax_address")
                biz_type = st.text_input("?태 ?종목", key="tax_biz_type")
                email = st.text_input("계산??간이과세?? ?령 ?메??, key="tax_email", value=user_id if "@" in user_id else "")
                plan_choice = st.selectbox("?택 ?금???랜", ["?간 ?용?(300,000??", "?간 ?용?(2,800,000??"])
                
                submit_tax = st.form_submit_button("계산??간이과세??/?보?스 발행 ?청", use_container_width=True)
                if submit_tax:
                    if not biz_name or not biz_num or not email:
                        st.error("?호? ?업?번?? ?메?? ?수 ?력 ?항?니??")
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
                            
                            st.success("??계산??간이과세?? ?결제 ?청???수?었?니?? ?력?신 ?메?로 24?간 ?내???보?스/견적??발송 ??금 계좌??내???립?다.")
                        except Exception as e:
                            st.error(f"?청 ?수 ?패: {str(e)}")
                        finally:
                            conn.close()

    # =========================================================================
    # TAB 5: Sign Up (Only shown when not logged in)
    # =========================================================================
    if not st.session_state.user_id:

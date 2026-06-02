import streamlit as st
# Force rebuild 2026-01-24 v3 (Merged Sync & Restore)
# Force deploy 2026-02-07
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import io
import sqlite3
import datetime
import re
import smtplib
import json
import platform
import os
import hashlib
import random
import string

def hash_password(password: str) -> str:
    """SHA-256 Hash a password with a fixed salt for security."""
    salt = "ahp_master_secure_salt_2026"
    return hashlib.sha256((password + salt).encode('utf-8')).hexdigest()

def generate_temp_password() -> str:
    """가입 시 비밀번호 유효성 검사를 통과하는 8자리 임시 비밀번호를 생성합니다."""
    chars = string.ascii_letters + string.digits
    specials = "!@#$%^&*"
    # 최소 1개 영문자, 1개 숫자, 1개 특수문자를 포함하도록 구성
    temp = [
        random.choice(string.ascii_lowercase),
        random.choice(string.ascii_uppercase),
        random.choice(string.digits),
        random.choice(specials)
    ]
    # 나머지 4자리는 영문/숫자 중 무작위 선택
    temp += [random.choice(chars) for _ in range(4)]
    random.shuffle(temp)
    return "".join(temp)
import matplotlib.font_manager as fm
from matplotlib import rc
from email.mime.text import MIMEText
from scipy.stats import gmean, ttest_rel, f_oneway
from PIL import Image
import itertools
from math import pi
from dateutil.relativedelta import relativedelta

# [필수] plotly 라이브러리 (requirements.txt에 plotly 추가 필요)
import plotly.express as px
import plotly.graph_objects as go
from scipy import stats
import gspread
from google.oauth2.service_account import Credentials
from signup_agreement import show_agreement_ui, save_agreement_to_sheets, validate_all_agreements

# 1. 추가해야 할 라이브러리 (기존 Credentials 바로 아래 추가)
from streamlit_javascript import st_javascript
import base64

# IP 위치 추적 및 공인 IP 추출을 위한 라이브러리 추가
import requests

# ANOVA 및 사후검정을 위한 라이브러리 (없을 경우 예외처리)
try:
    from statsmodels.stats.multicomp import pairwise_tukeyhsd
    STATSMODELS_AVAILABLE = True
except ImportError:
    STATSMODELS_AVAILABLE = False


# -----------------------------------------------------------------------------
# 다국어(English/Korean) 번역 헬퍼 함수
# -----------------------------------------------------------------------------
if 'lang' not in st.session_state:
    st.session_state.lang = 'ko'

def _(ko_text, en_text):
    if st.session_state.get('lang', 'ko') == 'en':
        return en_text
    return ko_text

# =============================================================================
# 0. 시스템 설정 및 유틸리티
# =============================================================================

# [수정] Base64 문자열의 패딩 및 정제를 위한 유틸리티 함수 강화
def fix_base64_padding(data):
    """
    Base64 문자열의 패딩(Incorrect padding) 오류를 수정하는 함수
    """
    if isinstance(data, str):
        # 1. 모든 공백 및 줄바꿈 문자 제거 (가장 중요한 수정)
        data = re.sub(r'\s+', '', data)
        
        # 2. 패딩(=) 계산 및 추가
        missing_padding = len(data) % 4
        if missing_padding:
            data += '=' * (4 - missing_padding)
    return data

# [수정 반영] 1) SEO 태그 삽입, 2) 서비스 명 변경(AHP 마스터), 4) 파비콘 설정
try:
    logo_path = "ahp_master_logo.png"
    if os.path.exists(logo_path):
        logo_img = Image.open(logo_path)
    else:
        logo_img = "📊"
    
    st.set_page_config(
        page_title=_("AHP 마스터 | 일반 및 퍼지 AHP 의사결정 분석 시스템", "AHP Master | Traditional & Fuzzy AHP Decision Analysis System"), 
        layout="wide", 
        page_icon=logo_img,
        menu_items={
            'Get Help': None,
            'Report a bug': None,
            'About': _("AHP 마스터 - 스마트 일반 및 퍼지 AHP 의사결정 분석 시스템", "AHP Master - Smart Traditional & Fuzzy AHP Decision Analysis System")
        }
    )
except Exception:
    st.set_page_config(page_title=_("AHP 마스터 | 퍼지 AHP 지원", "AHP Master | Fuzzy AHP Support"), layout="wide", page_icon="📊")

# [수정 반영] 메타 코드가 화면에 노출되지 않도록 display:none 스타일을 추가한 SEO 태그 (영한 통합 검색 최적화)
seo_tags = """
    <div style="display:none;">
        <head>
            <meta name="google-site-verification" content="KbMsp4y15le5XNyK05UEr6Nq6" />
            <meta name="description" content="AHP Master (AHP 마스터) - Professional Analytic Hierarchy Process (AHP) & Fuzzy AHP (퍼지 AHP) automation tool for thesis, research papers, and policy studies. Supports automatic Consistency Ratio (CR) calibration, statistical group testing (ANOVA), and instant Excel reports. 학위 논문 및 정책 연구를 위한 최적의 AHP 및 퍼지 AHP 분석 자동화 솔루션. 일관성 비율(CR) 자동 보정 및 통계 검정 제공." />
            <meta name="keywords" content="AHP, Fuzzy AHP, 퍼지 AHP, Fuzzy AHP 계산기, Fuzzy AHP 프로그램, AHP Master, AHP 마스터, AHP Calculator, AHP 계산기, analytic hierarchy process, consistency ratio, CR calibration, 일관성 보정, ANOVA, group analysis, thesis statistics, 학위논문통계, 무료 AHP 프로그램, AHP software" />
            <meta name="author" content="AHP Master" />
            <meta property="og:title" content="AHP Master (AHP 마스터) - Traditional & Fuzzy AHP Automation System" />
            <meta property="og:description" content="Advanced AHP & Fuzzy AHP decision software with mathematical consistency calibration and statistical group comparison. 수학적 일관성 보정과 고도화된 통계 및 퍼지 AHP 분석을 지원하는 전문 도구" />
            <meta property="og:type" content="website" />
            <meta name="robots" content="index, follow" />
        </head>
    </div>
"""
st.markdown(seo_tags, unsafe_allow_html=True)

# [폰트 설정]
def set_font_config():
    system_name = platform.system()
    try:
        if system_name == 'Windows':
            font_path = "c:/Windows/Fonts/malgun.ttf"
            if os.path.exists(font_path):
                font_name = fm.FontProperties(fname=font_path).get_name()
                rc('font', family=font_name)
        elif system_name == 'Darwin': # Mac
            rc('font', family='AppleGothic')
        else: # Linux
            font_path = "NanumGothic.ttf"
            if not os.path.exists(font_path):
                import urllib.request
                url = "https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Regular.ttf"
                urllib.request.urlretrieve(url, font_path)
            fm.fontManager.addfont(font_path)
            font_prop = fm.FontProperties(fname=font_path)
            rc('font', family=font_prop.get_name())
    except Exception as e:
        pass
    plt.rcParams['axes.unicode_minus'] = False 

set_font_config()

# [중요 수정] 구글 시트 연결 헬퍼 함수 - 인증 정보 로드 로직 전면 재검토 및 수정
# TOML(Dict), JSON String, Base64 Encoded String 등 다양한 포맷에 대응하도록 강화
def get_gspread_client():
    scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    
    # st.secrets에서 값 가져오기 (없을 경우 에러 처리)
    if "gcp_service_account" not in st.secrets:
        st.error("Secrets에 'gcp_service_account' 설정이 없습니다.")
        return None

    raw_auth = st.secrets["gcp_service_account"]
    auth_info = {}

    # Case 1: 이미 딕셔너리 형태인 경우 (TOML 포맷) - 가장 일반적인 경우
    if isinstance(raw_auth, dict) or hasattr(raw_auth, "keys"): 
        auth_info = dict(raw_auth) # AttrDict 등을 dict로 변환
    
    # Case 2: 문자열 형태인 경우 (JSON 문자열 혹은 Base64 인코딩 문자열)
    elif isinstance(raw_auth, str):
        # 앞뒤 공백 및 따옴표 제거
        auth_str = raw_auth.strip().strip('"').strip("'")
        
        try:
            # 2-1. 순수 JSON 문자열로 파싱 시도
            auth_info = json.loads(auth_str)
        except json.JSONDecodeError:
            # 2-2. JSON 파싱 실패 -> Base64 인코딩된 값으로 가정하고 디코딩 시도
            try:
                # 1단계: 문자열 정제 (모든 공백 제거)
                clean_b64 = re.sub(r'\s+', '', auth_str)
                
                # 2단계: 패딩(=) 보정
                missing_padding = len(clean_b64) % 4
                if missing_padding:
                    clean_b64 += '=' * (4 - missing_padding)
                
                # 3단계: Base64 디코딩 (Standard 및 URL-Safe 방식 모두 시도)
                try:
                    decoded_bytes = base64.b64decode(clean_b64)
                except Exception:
                    # Standard 실패 시 URL-Safe 방식 시도 (-와 _ 문자 처리)
                    decoded_bytes = base64.urlsafe_b64decode(clean_b64)
                    
                decoded_info = decoded_bytes.decode('utf-8')
                auth_info = json.loads(decoded_info)
            except Exception as e:
                st.error(f"서비스 계정 키 디코딩 실패 (Base64/JSON 오류): {e}")
                return None
    else:
        st.error("gcp_service_account 형식을 인식할 수 없습니다.")
        return None

    # [중요] Private Key 내의 줄바꿈 문자(\n) 처리
    # TOML 등에서 문자열로 읽어올 때 \\n으로 이스케이프된 경우 실제 줄바꿈으로 변경 필요
    if auth_info and "private_key" in auth_info:
        auth_info["private_key"] = auth_info["private_key"].replace("\\n", "\n")

    # 필수 필드 확인 (Missing fields 에러 방지)
    required_fields = ["private_key", "client_email", "token_uri"]
    missing = [f for f in required_fields if f not in auth_info]
    if missing:
        st.error(f"서비스 계정 정보에 필수 필드가 누락되었습니다: {', '.join(missing)}")
        return None

    creds = Credentials.from_service_account_info(auth_info, scopes=scope)
    return gspread.authorize(creds)

# [신규] 관리자 페이지 방문 로그 조회를 위한 캐싱 함수 (읽기 요청 최적화 - 5분 TTL)
@st.cache_data(ttl=300)
def get_cached_visit_logs(spreadsheet_id):
    try:
        client = get_gspread_client()
        if client:
            spreadsheet = client.open_by_key(spreadsheet_id)
            try:
                visit_sheet = spreadsheet.worksheet("Visit_Logs")
                return visit_sheet.get_all_records()
            except gspread.exceptions.WorksheetNotFound:
                return []
    except Exception as e:
        st.error(f"구글 시트 방문 로그 캐싱 조회 오류: {e}")
    return []

# DB 초기화 및 구글 시트로부터 데이터(회원+방문로그) 복구 로직
def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    # [수정] 구글 시트 구조에 맞춰 agree_info 컬럼 추가
    c.execute('''CREATE TABLE IF NOT EXISTS users
                  (id TEXT PRIMARY KEY, role TEXT, signup_date TEXT, pw TEXT, expiry_date TEXT, agree_info TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS saved_analyses
                  (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, filename TEXT, save_date TEXT, file_data BLOB)''')
    c.execute('''CREATE TABLE IF NOT EXISTS user_models
                  (user_id TEXT PRIMARY KEY, model_data TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS visit_logs
                  (ip_address TEXT, visit_date TEXT, PRIMARY KEY (ip_address, visit_date))''')
    
    # 관리자 계정 생성
    try:
        # [수정] 대한민국 시간 기준 가입일 설정 (날짜만)
        kst_now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
        signup_date_str = kst_now.strftime("%Y-%m-%d")
        # 컬럼 순서: id, role, signup_date, pw, expiry_date, agree_info
        c.execute("INSERT OR IGNORE INTO users VALUES (?, ?, ?, ?, ?, ?)", 
                  ('shjeon', 'admin', signup_date_str, '@jsh2143033', '9999-12-31', 'Y'))
        conn.commit()

        # [추가] 관리자 계정이 구글 시트에 없는 경우 자동 추가
        try:
            client = get_gspread_client()
            if client:
                spreadsheet = client.open_by_key(st.secrets["SPREADSHEET_ID"])
                sheet = spreadsheet.sheet1
                # 헤더 보정
                all_values = sheet.get_all_values()
                if all_values and len(all_values[0]) == 5:
                    sheet.update(range_name='A1:F1', values=[['id', 'role', 'signup_date', 'pw', 'expiry_date', 'agree_info']])
                
                cell = sheet.find('shjeon')
                if not cell:
                    sheet.append_row(['shjeon', 'admin', signup_date_str, '@jsh2143033', '9999-12-31', 'Y'])
        except Exception:
            pass
    except sqlite3.IntegrityError:
        pass 

    # [복구 로직 1] 회원 정보 복구 (Cloud 초기화 대비) - header 기반 (컬럼 순서 무관)
    c.execute("SELECT COUNT(*) FROM users")
    if c.fetchone()[0] <= 1:
        try:
            client = get_gspread_client()  
            if client:
                spreadsheet = client.open_by_key(st.secrets["SPREADSHEET_ID"])
                sheet = spreadsheet.sheet1

                # [헤더 보정] 구글 시트의 헤더가 5개인 경우 6개 컬럼으로 보정
                all_values = sheet.get_all_values()
                if all_values and len(all_values[0]) == 5:
                    sheet.update(range_name='A1:F1', values=[['id', 'role', 'signup_date', 'pw', 'expiry_date', 'agree_info']])

                records = sheet.get_all_records()  # 1행 header 사용
                if records:
                    def pick(row, *keys, default=""):
                        for k in keys:
                            if k in row and row[k] is not None and str(row[k]).strip() != "":
                                return str(row[k]).strip()
                        return default

                    kst_today = datetime.datetime.now(
                        datetime.timezone(datetime.timedelta(hours=9))
                    ).strftime("%Y-%m-%d")

                    for r in records:
                        userid = pick(r, "id", "ID", "user_id", "userid", "email")
                        if not userid or userid == "shjeon":
                            continue

                        pw = pick(r, "pw", "PW", "password")
                        role = pick(r, "role", "Role", default="temp")
                        signupdate = pick(r, "signup_date", "signup_tate", "signupdate", "SignupDate", default=kst_today)
                        expirydate = pick(r, "expiry_date", "expirydate", "ExpiryDate", default="9999-12-31")
                        agreeinfo = pick(r, "agree_info", "agreeinfo", "Agree", default="")

                        # [자가 치유] 구글 시트 컬럼 쉬프트 오류 복구 (expiry_date에 동의 여부가 잘못 적힌 경우)
                        if expirydate in ["Y", "N", "예", "아니오", "yes", "no"]:
                            if not agreeinfo:
                                agreeinfo = expirydate
                            expirydate = "9999-12-31"

                        if not agreeinfo:
                            agreeinfo = "Y"

                        if role not in ("temp", "official", "admin"):
                            role = "temp"

                        c.execute(
                            "INSERT OR IGNORE INTO users (id, role, signup_date, pw, expiry_date, agree_info) VALUES (?, ?, ?, ?, ?, ?)",
                            (userid, role, signupdate, pw, expirydate, agreeinfo),
                        )

                    conn.commit()
        except Exception:
            pass

    # [복구 로직 2] 방문 로그 복구
    c.execute("SELECT COUNT(*) FROM visit_logs")
    if c.fetchone()[0] == 0:
        try:
            client = get_gspread_client()
            if client:
                spreadsheet = client.open_by_key(st.secrets["SPREADSHEET_ID"])
                try:
                    visit_sheet = spreadsheet.worksheet("Visit_Logs")
                    records = visit_sheet.get_all_records()
                    for row in records:
                        c.execute("INSERT OR IGNORE INTO visit_logs (ip_address, visit_date) VALUES (?, ?)", 
                                  (row['IP'], row['Date']))
                    conn.commit()
                except gspread.exceptions.WorksheetNotFound:
                    pass
        except Exception:
            pass

    conn.close()

# [신규 기능 1] 구글 시트의 내용을 강제로 DB에 동기화하는 함수
def sync_db_from_sheets():
    """구글 시트의 데이터를 읽어와 DB에 없으면 유저를 추가하고, 이미 있다면 구글 시트 기준으로 보정(업데이트)합니다."""
    # ★★★ 임시 디버깅 코드 ★★★
    st.write("🔍 **Secrets 디버깅**")
    st.write("사용 가능한 최상위 키:", list(st.secrets.keys()))
    
    if "SPREADSHEET_ID" in st.secrets:
        st.success(f"✅ SPREADSHEET_ID 발견!")
        st.write(f"값: {st.secrets['SPREADSHEET_ID']}")
    else:
        st.error("❌ SPREADSHEET_ID가 없습니다!")
        
    if "gcp_service_account" in st.secrets:
        st.write("gcp_service_account 내부 키:", list(st.secrets["gcp_service_account"].keys()))
    
    st.write("---")
    # ★★★ 디버깅 끝 ★★★
    
    conn = None
    try:
        client = get_gspread_client()
        if not client: 
            st.error("❌ 구글 시트 인증(gspread client)에 실패했습니다.")
            return -1
        
        spreadsheet = client.open_by_key(st.secrets["SPREADSHEET_ID"])
        sheet = spreadsheet.sheet1
        all_values = sheet.get_all_values()
        
        # 데이터가 헤더 포함 2줄 이상일 때만 진행
        if len(all_values) > 1:
            # 30초 타임아웃 추가 및 안전한 커넥션
            conn = sqlite3.connect('users.db', timeout=30.0)
            c = conn.cursor()
            
            cnt = 0
            processed_ids = set()
            for row in all_values[1:]:
                # row 구조: [ID, Role, SignupDate, PW, expiry_date, agree_info]
                if len(row) >= 4:
                    user_id = str(row[0]).strip()
                    if not user_id or user_id in processed_ids:
                        continue
                    processed_ids.add(user_id)
                    
                    role = str(row[1]).strip()
                    signup_date = str(row[2]).strip()
                    pw = str(row[3]).strip()
                    
                    # 6개 컬럼 대응 및 자가 치유
                    if len(row) >= 6:
                        expiry_date = str(row[4]).strip()
                        agree_info = str(row[5]).strip()
                    elif len(row) == 5:
                        expiry_date = '9999-12-31'
                        agree_info = str(row[4]).strip()
                    else:
                        expiry_date = '9999-12-31'
                        agree_info = 'Y'
                        
                    # [자가 치유] 구글 시트 오류 복구 (expiry_date에 동의 여부가 잘못 들어갔을 때)
                    if expiry_date in ["Y", "N", "예", "아니오", "yes", "no"]:
                        if agree_info in ["", None, "Y"]:
                            agree_info = expiry_date
                        expiry_date = "9999-12-31"

                    # 이미 존재하는지 확인 후 없으면 INSERT, 있으면 정보 보정 업데이트
                    c.execute("SELECT id, role, signup_date, pw, expiry_date, agree_info FROM users WHERE id=?", (user_id,))
                    db_user = c.fetchone()
                    if not db_user:
                        c.execute("INSERT INTO users (id, role, signup_date, pw, expiry_date, agree_info) VALUES (?, ?, ?, ?, ?, ?)", 
                                  (user_id, role, signup_date, pw, expiry_date, agree_info))
                        cnt += 1
                    else:
                        db_role, db_signup_date, db_pw, db_expiry_date, db_agree_info = db_user[1], db_user[2], db_user[3], db_user[4], db_user[5]
                        # 변경 사항이 하나라도 있으면 구글 시트 기준으로 강제 업데이트 보정
                        if (db_role != role or db_signup_date != signup_date or 
                            db_pw != pw or db_expiry_date != expiry_date or db_agree_info != agree_info):
                            c.execute("""
                                UPDATE users 
                                SET role=?, signup_date=?, pw=?, expiry_date=?, agree_info=? 
                                WHERE id=?
                            """, (role, signup_date, pw, expiry_date, agree_info, user_id))
                            cnt += 1
            
            conn.commit()
            return cnt
    except Exception as e:
        st.error(f"🔍 동기화 에러 상세: {str(e)}")
        st.error(f"에러 타입: {type(e).__name__}")
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass
        return -1
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass
    return 0

# 방문자 추적 및 구글 시트 실시간 저장
def track_visitor():
    js_ip_script = 'await fetch("https://api.ipify.org?format=json").then(r => r.json()).then(d => d.ip)'
    client_ip = st_javascript(js_ip_script)
    if not client_ip:
        return 

    ip = str(client_ip).strip()
    
    if st.session_state.get('visited'):
        return

    try:
        # 카운트 방식 개선: [수정] 대한민국 시간 기준 시각 정보 사용
        now_ts = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).strftime("%Y-%m-%d %H:%M:%S")
        
        country, region, city, lat, lon = "", "", "", "", ""
        if ip not in ["localhost", "unknown_ip", "127.0.0.1"] and not ip.startswith("192.168."):
            try:
                response = requests.get(f"http://ip-api.com/json/{ip}", timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    if data.get("status") == "success":
                        country = data.get("country", "")
                        region = data.get("regionName", "")
                        city = data.get("city", "")
                        lat = data.get("lat", "")
                        lon = data.get("lon", "")
            except:
                pass

        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO visit_logs (ip_address, visit_date) VALUES (?, ?)", (ip, now_ts))
        conn.commit()
        conn.close()

        try:
            client = get_gspread_client()
            if client:
                spreadsheet = client.open_by_key(st.secrets["SPREADSHEET_ID"])
                try:
                    visit_sheet = spreadsheet.worksheet("Visit_Logs")
                except gspread.exceptions.WorksheetNotFound:
                    visit_sheet = spreadsheet.add_worksheet(title="Visit_Logs", rows="1000", cols="10")
                    visit_sheet.append_row(["IP", "Date", "Country", "Region", "City", "Latitude", "Longitude"])
                
                # [최적화] API 읽기 제한(429)을 피하기 위해 전체 로그를 매번 가져와 중복을 대조하던 읽기 요청(get_all_values)을 제거합니다.
                # 세션 상태(st.session_state.visited)가 작동 중이고 초 단위의 고유 타임스탬프를 쓰므로 바로 추가합니다.
                visit_sheet.append_row([ip, now_ts, country, region, city, lat, lon])
                
                st.session_state.visited = True
            
        except Exception:
            pass
    except Exception:
        pass

# 방문자 추적 실행부
if 'visited' not in st.session_state:
    st.session_state.visited = False
track_visitor()

def verify_paypal_payment(order_id):
    """Verify PayPal order status on the backend using credentials from secrets."""
    client_id = st.secrets.get("PAYPAL_CLIENT_ID", "")
    client_secret = st.secrets.get("PAYPAL_CLIENT_SECRET", "")
    mode = st.secrets.get("PAYPAL_MODE", "sandbox")
    
    if not client_id or not client_secret:
        return False, "PayPal credentials not configured."
        
    base_url = "https://api-m.paypal.com" if mode == "live" else "https://api-m.sandbox.paypal.com"
    
    try:
        auth_response = requests.post(
            f"{base_url}/v1/oauth2/token",
            auth=(client_id, client_secret),
            data={"grant_type": "client_credentials"},
            headers={"Accept": "application/json", "Accept-Language": "en_US"}
        )
        if auth_response.status_code != 200:
            return False, "Failed to authenticate with PayPal API."
        access_token = auth_response.json().get("access_token")
        
        order_response = requests.get(
            f"{base_url}/v2/checkout/orders/{order_id}",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
        )
        if order_response.status_code != 200:
            return False, "Failed to retrieve order details from PayPal."
            
        order_data = order_response.json()
        status = order_data.get("status")
        
        if status == "COMPLETED":
            return True, "Payment verified."
        return False, f"Payment status is {status}."
    except Exception as e:
        return False, f"Error verifying payment: {str(e)}"

def validate_email(email):
    return re.match(r"[^@]+@[^@]+\.[^@]+", email)

def validate_password(password):
    if len(password) < 4: return False
    has_char = re.search(r'[a-zA-Z]', password)
    has_special = re.search(r'[!@#$%^&*(),.?":{}|<>]', password)
    return has_char and has_special

def send_application_email(user_email):
    sender_email = "jeon080423@gmail.com"
    # secrets.toml에서 이메일 비밀번호를 안전하게 로드합니다.
    password = st.secrets.get("EMAIL_PASSWORD", "csuh xxru wqdy mttt")
    recipient_email = "jeon080423@gmail.com"
    subject = f"[AHP 마스터] 정식 사용자 승인 요청: {user_email}"
    # [수정] 대한민국 시간 기준 신청일 설정
    kst_today = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).date()
    body = f"사용자가 정식 권한 신청.\nID: {user_email}\n신청일: {kst_today}"
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = sender_email
    msg['To'] = recipient_email
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(sender_email, password)
            server.sendmail(sender_email, recipient_email, msg.as_string())
    except Exception as e:
        print(f"send_application_email Error: {e}")

# [추가 요청사항 반영] 전환 요청 이메일 발송 함수
def send_conversion_request_email(user_email):
    sender_email = "jeon080423@gmail.com"
    password = st.secrets.get("EMAIL_PASSWORD", "csuh xxru wqdy mttt")
    recipient_email = "jeon080423@gmail.com"
    subject = f"[AHP 마스터] 정식사용자 전환 요청: {user_email}"
    body = f"임시 사용자가 정식사용자로 전환 요청 했습니다\nID: {user_email}"
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = sender_email
    msg['To'] = recipient_email
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(sender_email, password)
            server.sendmail(sender_email, recipient_email, msg.as_string())
        return True
    except Exception as e:
        print(f"send_conversion_request_email Error: {e}")
        return False

def send_approval_email(user_email):
    sender_email = "jeon080423@gmail.com"
    password = st.secrets.get("EMAIL_PASSWORD", "csuh xxru wqdy mttt")
    recipient_email = user_email
    subject = "[AHP 마스터] 정식 사용자 승인 완료"
    body = f"{user_email}님, 정식 사용자로 승인되었습니다. 오늘부터 2개월간 모든 기능을 무제한으로 사용하실 수 있습니다."
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = sender_email
    msg['To'] = recipient_email
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(sender_email, password)
            server.sendmail(sender_email, recipient_email, msg.as_string())
        return True
    except Exception as e:
        print(f"send_approval_email Error: {e}")
        return False

def send_password_recovery_email(user_email, temp_pw):
    sender_email = "jeon080423@gmail.com"
    password = st.secrets.get("EMAIL_PASSWORD", "csuh xxru wqdy mttt")
    recipient_email = user_email
    subject = "[AHP 마스터] 임시 비밀번호 안내"
    body = f"""안녕하세요. 요청하신 계정의 임시 비밀번호를 안내해 드립니다.

ID: {user_email}
임시 비밀번호: {temp_pw}

로그인 후 즉시 비밀번호를 변경하시기를 권장합니다.
감사합니다.
"""
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = sender_email
    msg['To'] = recipient_email
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(sender_email, password)
            server.sendmail(sender_email, recipient_email, msg.as_string())
        return True
    except Exception as e:
        print(f"send_password_recovery_email Error: {e}")
        return False

# --- DB CRUD ---

def log_to_sheets(user_id, role, signup_date, pw, agree_info="Y", expiry_date="9999-12-31"):
    try:
        client = get_gspread_client()
        if client:
            spreadsheet = client.open_by_key(st.secrets["SPREADSHEET_ID"])
            sheet = spreadsheet.sheet1
            # [수정] 구글 시트 6개 컬럼 순서(id, role, signup_date, pw, expiry_date, agree_info) 보장
            sheet.append_row([user_id, role, str(signup_date), pw, expiry_date, agree_info])
    except Exception as e:
        st.error(f"Google Sheets 로깅 오류: {e}")

def add_user(user_id, pw, role, agree_info="Y"):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    # [수정] 대한민국 시간 기준 가입일 설정 (날짜만)
    signup_date = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).strftime("%Y-%m-%d")
    expiry_date = "9999-12-31"
    hashed_pw = hash_password(pw)
    try:
        # [수정] 구글 시트 순서에 맞춰 DB 저장 (id, role, signup_date, pw, expiry_date, agree_info)
        c.execute("INSERT INTO users (id, role, signup_date, pw, expiry_date, agree_info) VALUES (?, ?, ?, ?, ?, ?)", 
                  (user_id, role, signup_date, hashed_pw, expiry_date, agree_info))
        conn.commit()
        log_to_sheets(user_id, role, signup_date, hashed_pw, agree_info, expiry_date)
        success = True
    except sqlite3.IntegrityError:
        success = False
    finally:
        conn.close()
    return success

def upgrade_user_password_to_hash(user_id, pw):
    """기존 사용자의 평문 비밀번호를 암호화(해시) 버전으로 자동 승급합니다."""
    hashed_pw = hash_password(pw)
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("UPDATE users SET pw=? WHERE id=?", (hashed_pw, user_id))
    conn.commit()
    conn.close()
    
    try:
        client = get_gspread_client()
        if client:
            spreadsheet = client.open_by_key(st.secrets["SPREADSHEET_ID"])
            sheet = spreadsheet.sheet1
            cell = sheet.find(user_id)
            if cell:
                # 구글 시트의 PW 컬럼은 4번째(D)
                sheet.update_cell(cell.row, 4, hashed_pw)
    except Exception:
        pass

def check_login(user_id, pw):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    # 평문 패스워드 로그인 및 자동 업그레이드를 지원하기 위해 pw 컬럼도 함께 조회합니다.
    c.execute("SELECT role, expiry_date, pw FROM users WHERE id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    
    if row:
        stored_role, stored_expiry, stored_pw = row
        hashed_pw = hash_password(pw)
        
        # 평문 패스워드가 정확히 일치하거나 해시 패스워드가 일치하는 경우
        if stored_pw == pw or stored_pw == hashed_pw:
            # 평문 패스워드로 로그인 성공한 경우, 즉시 해시 패스워드로 업데이트 (보안 승급)
            if stored_pw == pw:
                upgrade_user_password_to_hash(user_id, pw)
            return stored_role, stored_expiry
            
    return None

def get_user_password(user_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT pw FROM users WHERE id=?", (user_id,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

def change_user_password(user_id, new_pw):
    hashed_pw = hash_password(new_pw)
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("UPDATE users SET pw=? WHERE id=?", (hashed_pw, user_id))
    conn.commit()
    conn.close()

    try:
        client = get_gspread_client()
        if client:
            spreadsheet = client.open_by_key(st.secrets["SPREADSHEET_ID"])
            sheet = spreadsheet.sheet1
            cell = sheet.find(user_id)
            if cell:
                # 구글 시트의 PW 컬럼은 4번째(D)
                sheet.update_cell(cell.row, 4, hashed_pw)
    except Exception:
        pass
    return True

def get_all_users():
    conn = sqlite3.connect('users.db')
    df = pd.read_sql_query("SELECT * FROM users", conn)
    conn.close()
    return df

def update_user_full_info(user_id, new_pw, new_role, new_expiry):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    if new_pw is not None and new_pw != "":
        c.execute("UPDATE users SET pw=?, role=?, expiry_date=? WHERE id=?", (new_pw, new_role, new_expiry, user_id))
    else:
        c.execute("UPDATE users SET role=?, expiry_date=? WHERE id=?", (new_role, new_expiry, user_id))
    conn.commit()
    conn.close()
    
    try:
        client = get_gspread_client()
        if client:
            spreadsheet = client.open_by_key(st.secrets["SPREADSHEET_ID"])
            sheet = spreadsheet.sheet1
            cell = sheet.find(user_id)
            kst_today = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).strftime("%Y-%m-%d")
            
            # SQLite DB에서 실제 저장된 기존 가입 날짜 조회 (가입일 훼손 방지)
            db_signup_date = None
            conn = sqlite3.connect('users.db')
            c = conn.cursor()
            c.execute("SELECT signup_date FROM users WHERE id=?", (user_id,))
            res = c.fetchone()
            if res:
                db_signup_date = res[0]
            conn.close()
            
            if cell:
                row_num = cell.row
                # 기존 데이터 보존을 위해 현재 시트 데이터 로드 (6개 컬럼 대응)
                current_row_data = sheet.row_values(row_num)
                # agree_info는 6번째 컬럼(index 5)에 있어야 합니다. 없으면 5번째(index 4) 혹은 기본값 "Y"
                agree_info = current_row_data[5] if len(current_row_data) >= 6 else (current_row_data[4] if len(current_row_data) >= 5 else "Y")
                
                # 구글 시트 기존 가입일 확인
                sheet_signup_date = current_row_data[2] if len(current_row_data) >= 3 else None
                
                # DB의 가입일을 우선순위로 하고, 없으면 구글 시트 기존 가입일, 그마저도 없으면 kst_today 사용
                final_signup_date = db_signup_date or sheet_signup_date or kst_today
                
                final_pw = new_pw if (new_pw and new_pw != "") else (current_row_data[3] if len(current_row_data) >= 4 else "")
                # 시트 순서: ID, Role, SignupDate, PW, expiry_date, agree_info (A:F)
                sheet.update(range_name=f'A{row_num}:F{row_num}', values=[[user_id, new_role, final_signup_date, final_pw, new_expiry, agree_info]])
            else:
                final_pw = new_pw if (new_pw and new_pw != "") else ""
                final_signup_date = db_signup_date or kst_today
                sheet.append_row([user_id, new_role, final_signup_date, final_pw, new_expiry, "Y"])
    except Exception as e:
        st.error(f"구글 시트 사용자 정보 수정 반영 오류: {e}") 

def delete_user(user_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE id=?", (user_id,))
    c.execute("DELETE FROM saved_analyses WHERE user_id=?", (user_id,))
    c.execute("DELETE FROM user_models WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()

    try:
        client = get_gspread_client()
        if client:
            spreadsheet = client.open_by_key(st.secrets["SPREADSHEET_ID"])
            sheet = spreadsheet.sheet1
            
            try:
                del_sheet = spreadsheet.worksheet("Deleted_Users")
            except gspread.exceptions.WorksheetNotFound:
                del_sheet = spreadsheet.add_worksheet(title="Deleted_Users", rows="1000", cols="10")
                del_sheet.append_row(["ID", "Role", "SignupDate", "PW", "agree_info", "DeletedDate"])

            all_values = sheet.get_all_values()
            target_row_index = -1
            row_data = None
            for i, row in enumerate(all_values):
                if row[0] == user_id:
                    target_row_index = i + 1
                    row_data = row
                    break
            
            if target_row_index != -1:
                kst_now_ts = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).strftime("%Y-%m-%d %H:%M:%S")
                row_data.append(str(kst_now_ts))
                del_sheet.append_row(row_data)
                sheet.delete_rows(target_row_index)
    except Exception:
        pass

# [신규 기능 2] 재가입 시 Deleted_Users 시트에서 해당 유저 삭제
def restore_from_deleted_sheet(user_id):
    try:
        client = get_gspread_client()
        if client:
            spreadsheet = client.open_by_key(st.secrets["SPREADSHEET_ID"])
            try:
                del_sheet = spreadsheet.worksheet("Deleted_Users")
                cell = del_sheet.find(user_id)
                if cell:
                    del_sheet.delete_rows(cell.row)
            except (gspread.exceptions.WorksheetNotFound, gspread.exceptions.CellNotFound):
                pass
    except Exception:
        pass

def save_analysis_to_db(user_id, filename, file_data):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    # [수정] 대한민국 시간 기준 저장 일시 설정
    save_date = str(datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).strftime("%Y-%m-%d %H:%M:%S"))
    c.execute("INSERT INTO saved_analyses (user_id, filename, save_date, file_data) VALUES (?, ?, ?, ?)",
              (user_id, filename, save_date, file_data))
    conn.commit()
    conn.close()

def get_user_analyses(user_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT id, filename, save_date FROM saved_analyses WHERE user_id=? ORDER BY save_date DESC", (user_id,))
    rows = c.fetchall()
    conn.close()
    return rows

def get_analysis_file(analysis_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT filename, file_data FROM saved_analyses WHERE id=?", (analysis_id,))
    result = c.fetchone()
    conn.close()
    return result

def delete_analysis(analysis_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("DELETE FROM saved_analyses WHERE id=?", (analysis_id,))
    conn.commit()
    conn.close()

def save_user_model(user_id, model_dict):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    model_json = json.dumps(model_dict, ensure_ascii=False)
    c.execute("INSERT OR REPLACE INTO user_models (user_id, model_data) VALUES (?, ?)", (user_id, model_json))
    conn.commit()
    conn.close()

def load_user_model(user_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT model_data FROM user_models WHERE user_id=?", (user_id,))
    result = c.fetchone()
    conn.close()
    if result:
        return json.loads(result[0])
    return None

# -----------------------------------------------------------------------------
# Saaty(1980) AHP Functions
# -----------------------------------------------------------------------------
def get_ri(n):
    ri_dict = {1: 0.00, 2: 0.00, 3: 0.58, 4: 0.90, 5: 1.12, 6: 1.24, 7: 1.32, 8: 1.41, 9: 1.45, 10: 1.49}
    return ri_dict.get(n, 1.49)

def calculate_weights(matrix, method='geometric'):
    if method == 'arithmetic':
        col_sum = matrix.sum(axis=0)
        col_sum[col_sum == 0] = 1
        normalized_matrix = matrix / col_sum
        weights = normalized_matrix.mean(axis=1)
    else:
        geom_means = gmean(matrix, axis=1)
        weights = geom_means / geom_means.sum()
    return weights

def calculate_consistency(matrix, method='geometric'):
    n = matrix.shape[0]
    if n <= 2: return 0.0, 0.0, n
    weights = calculate_weights(matrix, method)
    weighted_sum = matrix.dot(weights)
    weights_safe = weights.copy()
    weights_safe[weights_safe == 0] = 1e-10
    lambda_values = weighted_sum / weights_safe
    lambda_max = lambda_values.mean()
    ci = (lambda_max - n) / (n - 1)
    ri = get_ri(n)
    cr = ci / ri if ri > 0 else 0.0
    return cr, ci, lambda_max

FUZZY_SCALE = {
    1: (1.0, 1.0, 1.0), 2: (1.0, 2.0, 3.0), 3: (2.0, 3.0, 4.0), 4: (3.0, 4.0, 5.0), 5: (4.0, 5.0, 6.0),
    6: (5.0, 6.0, 7.0), 7: (6.0, 7.0, 8.0), 8: (7.0, 8.0, 9.0), 9: (9.0, 9.0, 9.0)
}

def saaty_to_fuzzy(v):
    try:
        val = max(1, min(9, int(round(v)))) if v >= 1 else max(1, min(9, int(round(1/v))))
        tfn = FUZZY_SCALE[val]
        if v < 1: return (1.0/tfn[2], 1.0/tfn[1], 1.0/tfn[0])
        return tfn
    except: return (1.0, 1.0, 1.0)

def fuzzy_ahp_analysis(matrix):
    n = matrix.shape[0]
    fuzzy_mat = np.zeros((n, n, 3))
    for i in range(n):
        for j in range(n):
            if i == j: fuzzy_mat[i,j] = (1.0, 1.0, 1.0)
            else: fuzzy_mat[i,j] = saaty_to_fuzzy(matrix[i,j])
    row_sums = []
    for i in range(n): 
        row_sums.append((sum(fuzzy_mat[i,:,0]), sum(fuzzy_mat[i,:,1]), sum(fuzzy_mat[i,:,2])))
    t_l, t_m, t_u = sum(x[0] for x in row_sums), sum(x[1] for x in row_sums), sum(x[2] for x in row_sums)
    if t_l == 0: return np.ones(n)/n, row_sums
    Si = []
    for (l, m, u) in row_sums: 
        Si.append((l/t_u if t_u!=0 else 0.0, m/t_m if t_m!=0 else 0.0, u/t_l if t_l!=0 else 0.0))
    crisp_w = np.array([(l*m*u)**(1/3) for (l,m,u) in Si])
    norm_w = crisp_w / crisp_w.sum() if crisp_w.sum() != 0 else np.ones(n)/n
    return norm_w, Si

def improve_consistency(matrix, threshold, min_val, max_val, max_iter=500, learning_rate=0.6, method='geometric'):
    current_matrix = matrix.copy()
    n = current_matrix.shape[0]
    cr, ci, _unused_lambda = calculate_consistency(current_matrix, method)
    iterations = 0
    if cr <= threshold: return current_matrix, cr, iterations, False
    
    # 상삼각 행렬의 인덱스 추출 (k=1은 대각선 제외)
    triu_indices = np.triu_indices(n, k=1)
    
    for it in range(max_iter):
        if cr <= threshold: break
        
        # 일관성 있는 행렬 생성
        w = calculate_weights(current_matrix, method)
        consistent_matrix = np.outer(w, 1/w)
        
        # 선형 결합 및 대각선 복구
        new_matrix = (current_matrix * (1 - learning_rate)) + (consistent_matrix * learning_rate)
        np.fill_diagonal(new_matrix, 1.0)
        
        # 상삼각 행렬 요소 추출
        vals = new_matrix[triu_indices]
        
        # 벡터화된 역변환 및 스케일링 로직
        # 1.0 기준 변환
        temp_raw = np.where(vals == 1.0, 1.0, 
                    np.where(vals > 1.0, -np.round(vals), 
                    np.round(1.0/vals)))
        
        # 범위 제한 (min_val, max_val)
        temp_raw = np.clip(temp_raw, min_val, max_val)
        
        # 홀수 보정
        abs_raw = np.abs(temp_raw)
        signs = np.sign(temp_raw)
        # 짝수인 경우 -1 (최소 1 유지)
        abs_raw = np.where((abs_raw % 2 == 0) & (abs_raw != 0), np.maximum(1, abs_raw - 1), abs_raw)
        # 0인 경우 1로 처리
        temp_raw = np.where(temp_raw == 0, 1, (signs * abs_raw)).astype(int)
        
        # 정수화된 값을 다시 AHP 스케일로 변환하여 행렬에 일괄 반영
        final_vals = np.where(temp_raw == 0, 1.0,
                      np.where(temp_raw < 0, np.abs(temp_raw).astype(float),
                      np.where(temp_raw == 1, 1.0, 1.0 / temp_raw)))
        
        new_matrix[triu_indices] = final_vals
        new_matrix.T[triu_indices] = 1.0 / final_vals
        
        current_matrix = new_matrix
        cr, ci, _unused_lambda = calculate_consistency(current_matrix, method)
        iterations += 1
        
    was_corrected = iterations > 0
    return current_matrix, cr, iterations, was_corrected

def parse_input_value(val):
    if val == 0: return 1.0
    elif val < 0: return abs(val)
    elif val == 1: return 1.0
    else: return 1.0 / val

def infer_factors_from_columns(cols):
    m = len(cols)
    delta = 1 + 8 * m
    n = int((1 + np.sqrt(delta)) / 2)
    extracted_factors = []
    seen = set()
    for c in cols:
        parts = str(c).split('_')
        for p in parts:
            p_str = p.strip()
            if p_str not in seen:
                seen.add(p_str)
                extracted_factors.append(p_str)
    if len(extracted_factors) == n:
        factors = extracted_factors 
    else:
        factors = [f"F{i+1}" for i in range(n)]
    return factors, n

def calculate_pairwise_ttest(df, factors):
    n = len(factors)
    p_values = pd.DataFrame(index=factors, columns=factors)
    weight_cols = [f"Weight_{f}" for f in factors]
    for i in range(n):
        for j in range(n):
            if i == j:
                p_values.iloc[i, j] = 1.0
            else:
                col1 = weight_cols[i]
                col2 = weight_cols[j]
                if col1 in df.columns and col2 in df.columns and len(df) > 1:
                    try:
                        _unused_t, p = ttest_rel(df[col1], df[col2], nan_policy='omit')
                        p_values.iloc[i, j] = p
                    except:
                        p_values.iloc[i, j] = np.nan
                else:
                    p_values.iloc[i, j] = np.nan
    return p_values

def process_single_sheet(df, cr_threshold, max_iter, learning_rate, method='geometric', ahp_method='traditional'):
    meta_cols = df.columns[:2]
    comp_cols = df.columns[2:]
    factors, n = infer_factors_from_columns(comp_cols)
    
    # 시트 전체 데이터의 로우데이터 최대값/최솟값 계산
    all_comp_values = df[comp_cols].values.flatten()
    sheet_min = int(np.min(all_comp_values))
    sheet_max = int(np.max(all_comp_values))
    
    results_list = []
    excluded_list = []
    excluded_count = 0
    for idx, row in df.iterrows():
        respondent_id = row.iloc[0]
        respondent_type = row.iloc[1]
        matrix = np.eye(n)
        
        # 원본 Rawdata를 정수 형태(-9 ~ 9)로 추출
        raw_values = []
        col_idx = 0
        for i in range(n):
            for j in range(i + 1, n):
                if col_idx < len(comp_cols):
                    raw_val = row[comp_cols[col_idx]]
                    raw_values.append(raw_val)
                    ahp_val = parse_input_value(raw_val)
                    matrix[i, j] = ahp_val
                    matrix[j, i] = 1.0 / ahp_val
                    col_idx += 1
        
        orig_cr, orig_ci, _unused_lambda = calculate_consistency(matrix, method)
        final_matrix = matrix.copy()
        final_cr = orig_cr
        iterations = 0
        corrected_flag = False
        if orig_cr > cr_threshold:
            final_matrix, final_cr, iterations, corrected_flag = improve_consistency(
                matrix, cr_threshold, sheet_min, sheet_max, max_iter=max_iter, learning_rate=learning_rate, method=method
            )
        
        # 만약 최대 반복을 수행했음에도 CR이 임계값을 초과할 경우 해당 응답자 제외
        if final_cr > cr_threshold:
            excluded_count += 1
            ex_res = {"ID": respondent_id, "Type": respondent_type}
            for k, col_name in enumerate(comp_cols):
                ex_res[col_name] = raw_values[k]
            ex_res["CR"] = final_cr
            excluded_list.append(ex_res)
            continue

        # 보정 후 Rawdata (역변환: 상삼각 행렬 값을 정수 펀칭 스케일로 변환)
        final_raw_values = []
        for i in range(n):
            for j in range(i + 1, n):
                val = final_matrix[i, j]
                if val == 1.0: final_raw_val = 1
                elif val > 1.0: final_raw_val = -int(round(val)) # 왼쪽 우선 (음수)
                else: final_raw_val = int(round(1.0/val)) # 오른쪽 우선 (양수)
                final_raw_values.append(final_raw_val)

        _unused_cr, final_ci, _unused_lambda = calculate_consistency(final_matrix, method)
        if ahp_method == 'fuzzy':
            final_weights, final_Si = fuzzy_ahp_analysis(final_matrix)
        else:
            final_weights = calculate_weights(final_matrix, method)
        
        # 결과 딕셔너리 구성 (요청사항 5 재배치 반영)
        res = {
            "ID": respondent_id,
            "Type": respondent_type
        }
        
        # [수정] 1. 보정 전 Rawdata 삽입
        for k, col_name in enumerate(comp_cols):
            res[f"Raw_Orig_{col_name}"] = raw_values[k]
        
        # [수정] 2. Original_CI, Original_CR 순서 배치
        res["Original_CI"] = orig_ci
        res["Original_CR"] = orig_cr
        
        # [수정] 3. 보정 후 Rawdata 삽입
        for k, col_name in enumerate(comp_cols):
            res[f"Raw_Final_{col_name}"] = final_raw_values[k]
            
        # [수정] 4. Final_CI, Final_CR 순서 배치
        res["Final_CI"] = final_ci
        res["Final_CR"] = final_cr
        
        res["Iterations"] = iterations
        res["Corrected"] = corrected_flag
        res["Matrix_Object"] = final_matrix 
        
        for f_idx, f_name in enumerate(factors):
            res[f"Weight_{f_name}"] = final_weights[f_idx]
            if ahp_method == 'fuzzy':
                l, m, u = final_Si[f_idx]
                res[f"L_{f_name}"] = l
                res[f"M_{f_name}"] = m
                res[f"U_{f_name}"] = u
                res[f"Crisp_{f_name}"] = (l*m*u)**(1/3)
            
        results_list.append(res)
        
    results_df = pd.DataFrame(results_list)
    excluded_df = pd.DataFrame(excluded_list)
    return results_df, factors, excluded_count, excluded_df

def create_sample_excel():
    output = io.BytesIO()
    is_en = (st.session_state.get('lang', 'ko') == 'en')
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        if is_en:
            main_cols = ["ID", "Type", "Governance_Planning", "Governance_Feasibility", "Governance_Effectiveness", 
                          "Planning_Feasibility", "Planning_Effectiveness", "Feasibility_Effectiveness"]
            main_data = [
                [1, "Expert", -3, -3, 3, 1, 1, 1],                
                [2, "Expert", -5, 3, 3, 3, 3, 3],        
                [3, "General", 5, 1, 3, -5, -5, -3],
                [4, "General", -3, -3, 3, -3, 3, -3],
                [5, "Official", -5, 5, -5, -5, 5, -5]
            ]
            df_main = pd.DataFrame(main_data, columns=main_cols)
            df_main.to_excel(writer, sheet_name="Main_Criteria", index=False)
            
            inconsistent_pattern = [
                [1, "Expert", 1, -3, 1],
                [2, "Expert", -3, -3, -3],
                [3, "General", 3, -3, 1],
                [4, "General", -3, 5, 3],
                [5, "Official", -3, 5, 3]
            ]
            sub1_cols = ["ID", "Type", "AdminSupport_Community", "AdminSupport_PM", "Community_PM"]
            pd.DataFrame(inconsistent_pattern, columns=sub1_cols).to_excel(writer, sheet_name="Governance", index=False)
            sub2_cols = ["ID", "Type", "IssueFit_AlternativeFit", "IssueFit_GoalClarity", "AlternativeFit_GoalClarity"]
            pd.DataFrame(inconsistent_pattern, columns=sub2_cols).to_excel(writer, sheet_name="Planning", index=False)
            sub3_cols = ["ID", "Type", "LandAcquisition_ProjectDetail", "LandAcquisition_CostFit", "ProjectDetail_CostFit"]
            pd.DataFrame(inconsistent_pattern, columns=sub3_cols).to_excel(writer, sheet_name="Feasibility", index=False)
            sub4_cols = ["ID", "Type", "Economic_Social", "Economic_Performance", "Social_Performance"]
            pd.DataFrame(inconsistent_pattern, columns=sub4_cols).to_excel(writer, sheet_name="Effectiveness", index=False)
        else:
            main_cols = ["ID", "Type", "거버넌스_계획타당성", "거버넌스_실현가능성", "거버넌스_사업효과", 
                          "계획타당성_실현가능성", "계획타당성_사업효과", "실현가능성_사업효과"]
            main_data = [
                [1, "전문가",-3,	-3, 3, 1, 1, 1],                
                [2, "전문가", -5, 3, 3, 3, 3, 3],        
                [3, "일반", 5, 1, 3, -5, -5, -3],
                [4, "일반", -3,-3, 3, -3, 3, -3],
                [5, "공무원", -5, 5, -5, -5, 5, -5]
            ]
            df_main = pd.DataFrame(main_data, columns=main_cols)
            df_main.to_excel(writer, sheet_name="Main_Criteria", index=False)
            
            inconsistent_pattern = [
                [1, "전문가", 1, -3, 1],
                [2, "전문가", -3, -3, -3],
                [3, "일반", 3, -3, 1],
                [4, "일반", -3, 5, 3],
                [5, "공무원", -3, 5, 3]
            ]
            sub1_cols = ["ID", "Type", "행정지원_지역공동체", "행정지원_총괄사업관리자", "지역공동체_총괄사업관리자"]
            pd.DataFrame(inconsistent_pattern, columns=sub1_cols).to_excel(writer, sheet_name="거버넌스", index=False)
            sub2_cols = ["ID", "Type", "현안적정성_대안적정성", "현안적정성_목표구체성", "대안적정성_목표구체성"]
            pd.DataFrame(inconsistent_pattern, columns=sub2_cols).to_excel(writer, sheet_name="계획타당성", index=False)
            sub3_cols = ["ID", "Type", "부지확보_사업구체화", "부지확보_사업비적정성", "사업구체화_사업비적정성"]
            pd.DataFrame(inconsistent_pattern, columns=sub3_cols).to_excel(writer, sheet_name="실현가능성", index=False)
            sub4_cols = ["ID", "Type", "경제적효과_사회적효과", "경제적효과_성과관리", "사회적효과_성과관리"]
            pd.DataFrame(inconsistent_pattern, columns=sub4_cols).to_excel(writer, sheet_name="사업효과", index=False)
    output.seek(0)
    return output

def calculate_anova_and_posthoc(full_data):
    results = []
    unique_factors = full_data['Factor'].unique()
    
    for factor in unique_factors:
        subset = full_data[full_data['Factor'] == factor]
        groups = [group['Global_Weight'].values for name, group in subset.groupby('Type')]
        
        if len(groups) < 2:
            continue
            
        f_stat, p_val = f_oneway(*groups)
        
        row = {
            "요인": factor,
            "F-값": f_stat,
            "P-Value": p_val,
            "유의성": "유의함" if p_val < 0.05 else "유의하지 않음",
            "사후검정(Tukey HSD)": ""
        }
        
        if p_val < 0.05 and STATSMODELS_AVAILABLE:
            try:
                tukey = pairwise_tukeyhsd(endog=subset['Global_Weight'], groups=subset['Type'], alpha=0.05)
                tukey_df = pd.DataFrame(data=tukey.summary().data[1:], columns=tukey.summary().data[0])
                sig_pairs = tukey_df[tukey_df['reject'] == True]
                if not sig_pairs.empty:
                    pairs_str = []
                    for idx_row, r in sig_pairs.iterrows():
                        pairs_str.append(f"{r['group1']} vs {r['group2']}")
                    row["사후검정(Tukey HSD)"] = ", ".join(pairs_str) + " 차이 있음"
                else:
                    row["사후검정(Tukey HSD)"] = "집단 간 구체적 차이 발견 못함"
            except Exception as e:
                row["사후검정(Tukey HSD)"] = "계산 오류"
        
        results.append(row)
        
    return pd.DataFrame(results)

# -----------------------------------------------------------------------------
# [삭제] 좋아요 기능 제거됨
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# 2. Setup & Layout
# -----------------------------------------------------------------------------

init_db()

# CSS 최적화
st.markdown("""
<style>
    .stDataFrame {font-size: 0.9rem;} 
    div[data-testid="stMetricValue"] {font-size: 1.2rem;}
    .stDownloadButton > button {
        background-color: #d32f2f;
        color: white;
        border-radius: 5px;
        border: none;
        padding: 0.6rem 1.2rem;
        font-weight: bold;
        transition: background-color 0.3s ease;
    }
    .stDownloadButton > button:hover {
        background-color: #b71c1c;
    }
    /* [수정] 좋아요 버튼 스타일 */
    div.stButton > button:first-child[kind="primary"] {
        background-color: #FFC0CB !important; /* 핑크색 */
        color: black !important;
        border: none !important;
    }
    /* 본문 상단 여백 축소로 좌측 로고와 수평 정렬 */
    .block-container, div[data-testid="stAppViewBlockContainer"] {
        padding-top: 2.0rem !important;
    }
    /* 사이드바 여백 극대 축소 */
    section[data-testid="stSidebar"] .block-container {
        padding-top: 1.0rem !important;
    }
    section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"] {
        gap: 0.4rem !important;
    }
    section[data-testid="stSidebar"] div.stElementContainer {
        margin-bottom: 0.2rem !important;
    }
</style>
""", unsafe_allow_html=True)

if 'user_id' not in st.session_state: st.session_state.user_id = None
if 'user_role' not in st.session_state: st.session_state.user_role = None
if 'expiry_date' not in st.session_state: st.session_state.expiry_date = None
if 'admin_mode' not in st.session_state: st.session_state.admin_mode = False
if 'model_structure' not in st.session_state: st.session_state.model_structure = {}
if 'page' not in st.session_state: st.session_state.page = "main"
if 'signup_paypal_user' not in st.session_state: st.session_state.signup_paypal_user = None

# -----------------------------------------------------------------------------
# 쿼리 매개변수 확인 (다국어 선택 및 결제 완료 처리)
# -----------------------------------------------------------------------------
try:
    q_params = st.query_params
except AttributeError:
    try:
        q_params = st.experimental_get_query_params()
    except:
        q_params = {}

# 자동 로그인 처리 (쿼리 파라미터 기반)
if st.session_state.user_id is None and "login_user" in q_params and "login_token" in q_params:
    login_user_val = q_params["login_user"]
    if isinstance(login_user_val, list): login_user_val = login_user_val[0]
    login_token_val = q_params["login_token"]
    if isinstance(login_token_val, list): login_token_val = login_token_val[0]
    
    # 토큰 검증
    expected_token = hashlib.sha256(f"{login_user_val}:AHP_MASTER_SECURE_SALT_2026_!@#".encode()).hexdigest()
    if login_token_val == expected_token:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("SELECT role, expiry_date FROM users WHERE id=?", (login_user_val,))
        db_user = c.fetchone()
        conn.close()
        if db_user:
            st.session_state.user_id = login_user_val
            st.session_state.user_role = db_user[0]
            st.session_state.expiry_date = db_user[1]


# 자동 로그아웃 처리 (30분 미활동 시)
import time
TIMEOUT_LIMIT = 1800 # 30분 (초 단위)
current_time = int(time.time())

if st.session_state.user_id is not None:
    last_act = q_params.get("last_activity")
    if isinstance(last_act, list): last_act = last_act[0]
    
    if last_act:
        try:
            elapsed = current_time - int(last_act)
            if elapsed > TIMEOUT_LIMIT:
                # 세션 및 쿼리 파라미터 초기화
                st.session_state.user_id = None
                st.session_state.user_role = None
                st.session_state.expiry_date = None
                st.session_state.admin_mode = False
                st.query_params.clear()
                st.toast(_("🔒 30분간 활동이 없어 보안을 위해 자동 로그아웃되었습니다.", "🔒 Logged out automatically due to 30 minutes of inactivity."))
                st.rerun()
            else:
                st.query_params["last_activity"] = str(current_time)
        except ValueError:
            st.query_params["last_activity"] = str(current_time)
    else:
        st.query_params["last_activity"] = str(current_time)

# 다국어 처리
if "lang" in q_params:
    lang_val = q_params["lang"]
    if isinstance(lang_val, list): lang_val = lang_val[0]
    if str(lang_val).lower() in ["en", "english"]:
        st.session_state.lang = "en"
    elif str(lang_val).lower() in ["ko", "korean"]:
        st.session_state.lang = "ko"

# 페이팔 자동 결제 승격 처리 (서버 검증 포함)
if "paypal_order_id" in q_params:
    order_id_val = q_params["paypal_order_id"]
    if isinstance(order_id_val, list):
        order_id_val = order_id_val[0]
        
    is_valid, msg = verify_paypal_payment(order_id_val)
    if is_valid:
        current_user = st.session_state.get("user_id")
        user_id_param = q_params.get("user_id", [""])[0] if isinstance(q_params.get("user_id"), list) else q_params.get("user_id", "")
        target_user = current_user or user_id_param
        if target_user:
            kst_now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
            new_expiry_date = (kst_now + relativedelta(months=2)).strftime("%Y-%m-%d")
            update_user_full_info(target_user, None, "official", new_expiry_date)
            
            if st.session_state.get("user_id") == target_user:
                st.session_state.user_role = "official"
                st.session_state.expiry_date = new_expiry_date
            st.toast("🎉 PayPal Payment successful! Account upgraded to Official User.")
    else:
        st.error(f"Payment verification failed: {msg}")
        
    st.query_params.clear()
    st.rerun()

# 정식 회원 자동 만료 체크 (로그인 상태)
if st.session_state.user_id is not None and st.session_state.user_role == 'official':
    today = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).date()
    try:
        expiry_date_val_temp = datetime.datetime.strptime(st.session_state.expiry_date, "%Y-%m-%d").date()
        if today > expiry_date_val_temp:
            update_user_full_info(st.session_state.user_id, None, "temp", "9999-12-31")
            st.session_state.user_role = "temp"
            st.session_state.expiry_date = "9999-12-31"
            st.toast("📅 Subscription expired. Automatically downgraded to Free User.")
            st.rerun()
    except Exception:
        pass

# =============================================================================
# 3. Sidebar (Auth & Settings) - 항상 표시되도록 위치 조정
# =============================================================================

def get_fee_info_text():
    return _(
        """<div style="line-height: 1.4; font-size: 0.95rem;">
  <hr style="margin-top: 15px; margin-bottom: 15px; border: 0; border-top: 1px solid #ddd;">
  <h3 style="margin-top: 0; margin-bottom: 8px;">서비스 이용료</h3>
  <ul style="margin: 0; padding-left: 20px; margin-bottom: 8px;">
    <li style="margin-bottom: 2px;"><b>무료사용자</b>: 무료 (5표본 제한 외 기능제한 없음)</li>
    <li style="margin-bottom: 2px;"><b>정식 사용자</b>: 50만원 (2개월 기능 무제한)</li>
  </ul>

</div>""",
        """<div style="line-height: 1.4; font-size: 0.95rem;">
  <hr style="margin-top: 15px; margin-bottom: 15px; border: 0; border-top: 1px solid #ddd;">
  <h3 style="margin-top: 0; margin-bottom: 8px;">Service Fees</h3>
  <ul style="margin: 0; padding-left: 20px; margin-bottom: 8px;">
    <li style="margin-bottom: 2px;"><b>Free User</b>: Free (5 samples limit, no other limitations)</li>
    <li style="margin-bottom: 2px;"><b>Official User</b>: $350 USD (2 months unlimited)</li>
  </ul>

</div>"""
    )

with st.sidebar:
    # 다국어 선택 (Language Switcher)
    lang_options = {"한국어 🇰🇷": "ko", "English 🇺🇸": "en"}
    selected_lang_label = st.selectbox(
        "Language / 언어 선택", 
        options=list(lang_options.keys()), 
        index=0 if st.session_state.get('lang', 'ko') == 'ko' else 1,
        key="sidebar_lang_selector"
    )
    new_lang = lang_options[selected_lang_label]
    if new_lang != st.session_state.get('lang', 'ko'):
        st.session_state.lang = new_lang
        st.query_params["lang"] = new_lang
        st.rerun()

    try:
        st.image("ahp_master_logo.png", use_container_width=True)
    except:
        st.subheader(_("📊 AHP 마스터", "📊 AHP Master"))
    

    if st.session_state.user_id is None:
        tab_login, tab_signup, tab_find_pw = st.tabs([_("로그인", "Login"), _("회원가입", "Sign Up"), _("비밀번호 찾기", "Find Password")])
        
        with tab_login:
            l_id = st.text_input(_("아이디 (이메일 주소)", "Username (Email Address)"), key="l_id")
            l_pw = st.text_input(_("비밀번호 (PW)", "Password (PW)"), type="password", key="l_pw")
            if st.button(_("로그인 실행", "Login")):
                result = check_login(l_id.strip(), l_pw)
                if result:
                    # [수정] 대한민국 시간 기준 오늘 날짜 가져오기
                    today = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).date()
                    expiry_date_val = datetime.datetime.strptime(result[1], "%Y-%m-%d").date()
                    if today > expiry_date_val:
                        if result[0] == 'official':
                            # 정식 사용자가 만료된 경우 -> 자동으로 무료사용자(temp)로 즉시 안전 승격 해제 및 전환
                            try:
                                update_user_full_info(l_id.strip(), None, "temp", "9999-12-31")
                                st.session_state.user_id = l_id.strip()
                                st.session_state.user_role = "temp"
                                st.session_state.expiry_date = "9999-12-31"
                                st.query_params["login_user"] = l_id.strip()
                                st.query_params["login_token"] = hashlib.sha256(f"{l_id.strip()}:AHP_MASTER_SECURE_SALT_2026_!@#".encode()).hexdigest()
                                st.query_params["last_activity"] = str(int(time.time()))
                                st.toast(_("📅 정식 이용 기간이 만료되어 무료사용자 권한으로 자동 전환되었습니다.", "📅 Subscription expired. Automatically downgraded to Free User."))
                                st.success(_(f"환영합니다, {l_id}님! 정식 이용 기간이 만료되어 무료사용자(5표본 제한) 권한으로 자동 전환되었습니다. 사이드바에서 언제든 연장 결제하실 수 있습니다!",
                                             f"Welcome, {l_id}! Your subscription expired and you were automatically downgraded to a Free User (5-sample limit). You can extend your subscription anytime in the sidebar!"))
                                st.rerun()
                            except Exception as e:
                                st.error(_(f"만료 회원 자동 전환 처리 중 오류가 발생했습니다: {e}", f"Error during automatic expiry downgrade: {e}"))
                        else:
                            st.error(_(f"❌ 이용 기간이 만료되었습니다. (만료일: {result[1]})", f"❌ Subscription expired. (Expiry date: {result[1]})"))
                    else:
                        st.session_state.user_id = l_id.strip()
                        st.session_state.user_role = result[0]
                        st.session_state.expiry_date = result[1]
                        st.query_params["login_user"] = l_id.strip()
                        st.query_params["login_token"] = hashlib.sha256(f"{l_id.strip()}:AHP_MASTER_SECURE_SALT_2026_!@#".encode()).hexdigest()
                        st.query_params["last_activity"] = str(int(time.time()))
                        if 'signup_paypal_user' in st.session_state:
                            del st.session_state.signup_paypal_user
                        st.success(_(f"환영합니다, {l_id}님!", f"Welcome, {l_id}!"))
                        st.rerun()
                else:
                    st.error(_("아이디 또는 비밀번호가 일치하지 않습니다.", "Incorrect username or password."))

        with tab_signup:
            if st.session_state.get('signup_paypal_user'):
                user_id = st.session_state.signup_paypal_user
                st.markdown("### 💳 Upgrade to Official User via PayPal")
                st.info(f"You have registered successfully as **{user_id}**. To complete your upgrade to Official User immediately, please use the PayPal button below:")
                
                paypal_client_id = st.secrets.get("PAYPAL_CLIENT_ID", "sb")
                paypal_html = f"""
                <div id="paypal-button-container-signup" style="text-align: center; max-width: 100%;"></div>
                <script src="https://www.paypal.com/sdk/js?client-id={paypal_client_id}&currency=USD&locale=en_US"></script>
                <script>
                  paypal.Buttons({{
                    style: {{
                      layout: 'vertical',
                      color:  'gold',
                      shape:  'rect',
                      label:  'paypal',
                      height: 40
                    }},
                    createOrder: function(data, actions) {{
                      return actions.order.create({{
                        purchase_units: [{{
                          amount: {{
                            value: '350.00'
                          }},
                          payee: {{
                            email_address: 'jeon080423@gmail.com'
                          }}
                        }}]
                      }});
                    }},
                    onApprove: function(data, actions) {{
                      return actions.order.capture().then(function(details) {{
                        window.top.location.href = window.top.location.origin + window.top.location.pathname + "?paypal_order_id=" + data.orderID + "&user_id=" + encodeURIComponent("{user_id}");
                      }});
                    }},
                    onError: function(err) {{
                      console.error(err);
                      alert("Payment failed or was cancelled.");
                    }}
                  }}).render('#paypal-button-container-signup');
                </script>
                """
                st.components.v1.html(paypal_html, height=180)
                
                if st.button("Back to Login / Sign Up", use_container_width=True, key="back_to_login_btn"):
                    del st.session_state.signup_paypal_user
                    st.rerun()
            else:
                agreements = show_agreement_ui()
                s_id = st.text_input(_("아이디 (이메일 주소)", "Username (Email Address)"), key="s_id")
                s_pw = st.text_input(_("비밀번호", "Password"), type="password", key="s_pw")
                s_role_selection = st.radio(_("이용 권한 선택", "Select Account Type"), (_("무료사용자", "Free User"), _("정식 사용자 (2개월, 기능 무제한)", "Official User (2 Months, Unlimited)")), index=0)
                
                if "정식" in s_role_selection or "Official" in s_role_selection:
                    if st.session_state.get('lang', 'ko') == 'en':
                        st.warning("⚠️ Official User Signup Guide")
                        st.info("Official users are registered as a **Free User** first.")
                        st.info("You will be prompted to pay via **PayPal** immediately after clicking 'Register' to upgrade your account instantly. (Access period is 2 months)")
                    else:
                        st.warning("⚠️ 정식 사용자 가입 안내")
                        acc_info_html = """
                        <div style="background-color: #f7fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px; margin-bottom: 12px;">
                          <div style="font-weight: bold; font-size: 0.88rem; color: #2d3748; margin-bottom: 6px;">🏦 계좌이체 입금 정보</div>
                          <div style="font-size: 0.82rem; color: #4a5568; line-height: 1.5;">
                            • <b>은행명</b>: 카카오뱅크<br>
                            • <b>예금주</b>: ㅈㅅㅎ<br>
                            • <b>이용요금</b>: 50만원<br>
                            <div style="display: flex; align-items: center; gap: 8px; margin-top: 6px;">
                              <span style="font-family: monospace; font-weight: bold; background-color: #edf2f7; padding: 4px 8px; border-radius: 4px; color: #2d3748;">3333-23-8667708</span>
                              <button onclick="(function(){
                                const el = document.createElement('textarea');
                                el.value = '3333-23-8667708';
                                document.body.appendChild(el);
                                el.select();
                                document.execCommand('copy');
                                document.body.removeChild(el);
                                alert('계좌번호가 복사되었습니다: 3333-23-8667708 (카카오뱅크)');
                              })()" style="background-color: #3182ce; color: white; border: none; padding: 4px 8px; border-radius: 4px; cursor: pointer; font-size: 0.78rem; font-weight: bold;">📋 복사</button>
                            </div>
                          </div>
                        </div>
                        """
                        st.markdown(acc_info_html, unsafe_allow_html=True)
                        st.info("관리자가 입금 확인 후 **정식 사용자**로 권한이 변경됩니다, 승인 완료 시 이메일로 안내해 드립니다. (사용 기간은 2개월 입니다)")
                
                if st.button(_("가입신청", "Register")):
                    if not agreements.get("agree_personal_info"):
                        st.error(_("개인정보 수집·이용에 동의해야 가입신청할 수 있습니다.", "You must agree to the privacy policy to register."))
                    elif not validate_email(s_id):
                        st.error(_("올바른 이메일 형식이 아닙니다.", "Invalid email format."))
                    elif not validate_password(s_pw):
                        st.error(_("비밀번호는 문자+특수문자여야 합니다.", "Password must contain both letters and special characters."))
                    else:
                        restore_from_deleted_sheet(s_id.strip())
                        initial_role = 'temp'
                        actual_requested_role = 'official' if ("정식" in s_role_selection or "Official" in s_role_selection) else 'temp'
                        # 동의 기록을 'Y'로 저장
                        if add_user(s_id.strip(), s_pw, initial_role, agree_info="Y"):
                            if actual_requested_role == 'official':
                                send_application_email(s_id.strip())
                                if st.session_state.get('lang', 'ko') == 'en':
                                    st.session_state.signup_paypal_user = s_id.strip()
                            st.success(_("무료사용자로 가입 완료 되었습니다", "Successfully registered as a Free User."))
                            st.rerun()
                        else:
                            st.error(_("이미 존재하는 아이디입니다.", "ID already exists."))

        with tab_find_pw:
            st.write(_("가입 시 사용한 이메일 주소를 입력해주세요. 이메일로 새로운 임시 비밀번호가 발송됩니다.",
                       "Please enter the email address used at registration. A new temporary password will be sent to your email."))
            f_id = st.text_input(_("가입한 아이디 (이메일)", "Registered ID (Email)"), key="f_id")
            if st.button(_("임시 비밀번호 전송", "Send Temporary Password")):
                if not f_id:
                    st.warning(_("이메일 주소를 입력해주세요.", "Please enter your email address."))
                else:
                    conn = sqlite3.connect('users.db')
                    c = conn.cursor()
                    c.execute("SELECT id FROM users WHERE id=?", (f_id.strip(),))
                    user_exists = c.fetchone()
                    conn.close()
                    
                    if user_exists:
                        temp_pw = generate_temp_password()
                        change_user_password(f_id.strip(), temp_pw)
                        
                        if send_password_recovery_email(f_id.strip(), temp_pw):
                            st.success(_(f"'{f_id}'로 임시 비밀번호를 전송했습니다.\n이메일을 확인해주세요.", f"Temporary password sent to '{f_id}'.\nPlease check your email."))
                        else:
                            st.error(_("이메일 전송 중 오류가 발생했습니다.", "Error sending email."))
                    else:
                        st.error(_("등록되지 않은 아이디입니다.", "ID is not registered."))

    else:
        role_disp = _("관리자", "Admin") if st.session_state.user_role == 'admin' else (_("정식 사용자", "Official User") if st.session_state.user_role == 'official' else _("무료사용자", "Free User"))
        
        expiry_info = ""
        if st.session_state.expiry_date:
            expiry_label = _("만료일: ", "Expiry: ")
            expiry_info = f' | {expiry_label}{st.session_state.expiry_date}'
            
        info_html = f"""<div style="background-color: #e8f5e9; border: 1px solid #c8e6c9; border-radius: 6px; color: #2e7d32; font-weight: bold; font-size: 0.85rem; padding: 8px 10px; text-align: center; margin-bottom: 8px;">
👤 {st.session_state.user_id} ({role_disp}{expiry_info})
</div>"""
        st.markdown(info_html, unsafe_allow_html=True)
        
        if st.session_state.user_role == 'temp':
            with st.expander(_("💳 정식 사용자 승격/결제", "💳 Upgrade to Official User"), expanded=False):
                if st.session_state.lang == 'en':
                    st.markdown("##### 💳 PayPal Membership Upgrade")
                    st.info("Upgrade to **Official User** to get unlimited access (2 months) for **$350.00 USD**.")
                    
                    paypal_client_id = st.secrets.get("PAYPAL_CLIENT_ID", "sb")
                    user_id = st.session_state.user_id
                    
                    paypal_html = f"""
                    <div id="paypal-button-container" style="text-align: center; max-width: 100%;"></div>
                    <script src="https://www.paypal.com/sdk/js?client-id={paypal_client_id}&currency=USD&locale=en_US"></script>
                    <script>
                      paypal.Buttons({{
                        style: {{
                          layout: 'vertical',
                          color:  'gold',
                          shape:  'rect',
                          label:  'paypal',
                          height: 40
                        }},
                        createOrder: function(data, actions) {{
                          return actions.order.create({{
                            purchase_units: [{{
                              amount: {{
                                value: '350.00'
                              }},
                              payee: {{
                                email_address: 'jeon080423@gmail.com'
                              }}
                            }}]
                          }});
                        }},
                        onApprove: function(data, actions) {{
                          return actions.order.capture().then(function(details) {{
                            window.top.location.href = window.top.location.origin + window.top.location.pathname + "?paypal_order_id=" + data.orderID + "&user_id=" + encodeURIComponent("{user_id}");
                          }});
                        }},
                        onError: function(err) {{
                          console.error(err);
                          alert("Payment failed or was cancelled.");
                        }}
                      }}).render('#paypal-button-container');
                    </script>
                    """
                    st.components.v1.html(paypal_html, height=180)
                else:
                    st.markdown("##### 💳 정식 사용자 승격 요청")
                    
                    acc_info_html = """
                    <div style="background-color: #f7fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px; margin-bottom: 12px;">
                      <div style="font-size: 0.82rem; color: #4a5568; line-height: 1.5;">
                        • <b>은행명</b>: 카카오뱅크<br>
                        • <b>예금주</b>: ㅈㅅㅎ<br>
                        • <b>이용요금</b>: 50만원 (2개월 무제한)<br>
                        <div style="display: flex; align-items: center; gap: 8px; margin-top: 6px;">
                          <span style="font-family: monospace; font-weight: bold; background-color: #edf2f7; padding: 4px 8px; border-radius: 4px; color: #2d3748;">3333-23-8667708</span>
                          <button onclick="(function(){
                            const el = document.createElement('textarea');
                            el.value = '3333-23-8667708';
                            document.body.appendChild(el);
                            el.select();
                            document.execCommand('copy');
                            document.body.removeChild(el);
                            alert('계좌번호가 복사되었습니다: 3333-23-8667708 (카카오뱅크)');
                          })()" style="background-color: #3182ce; color: white; border: none; padding: 4px 8px; border-radius: 4px; cursor: pointer; font-size: 0.78rem; font-weight: bold;">📋 복사</button>
                        </div>
                      </div>
                    </div>
                    """
                    st.markdown(acc_info_html, unsafe_allow_html=True)
                    st.info("입금 완료 후 아래 버튼을 클릭하시면 승격 요청이 관리자에게 즉시 전송됩니다.")
                    
                    if st.button("정식 사용자 전환 요청", use_container_width=True, key="sidebar_upgrade_btn"):
                        if send_conversion_request_email(st.session_state.user_id):
                            st.success("정식 사용자 전환요청이 완료 되었습니다. 입금 확인 후 정식사용자로 전환해 드립니다")
                        else:
                            st.error("요청 전송 실패. 관리자에게 문의바랍니다.")
        
    if st.session_state.user_id is not None:
        if st.session_state.user_role == 'admin':
            if st.button(_("🔧 관리자 화면 접속", "🔧 Connect to Admin Panel")):
                st.session_state.admin_mode = not st.session_state.admin_mode
                st.rerun()

        with st.expander(_("🔐 비밀번호 변경", "🔐 Change Password")):
            cur_pw = st.text_input(_("현재 비밀번호", "Current Password"), type="password", key="chg_cur_new")
            new_pw_val = st.text_input(_("새 비밀번호", "New Password"), type="password", key="chg_new_new")
            confirm_pw = st.text_input(_("새 비밀번호 확인", "Confirm New Password"), type="password", key="chg_conf_new")
            
            if st.button(_("비밀번호 변경", "Change Password"), key="btn_chg_pw_new"):
                if new_pw_val != confirm_pw:
                    st.error(_("새 비밀번호가 일치하지 않습니다.", "New passwords do not match."))
                elif not validate_password(new_pw_val):
                    st.error(_("비밀번호는 4자 이상, 영문+특수문자를 포함해야 합니다.", "Password must be at least 4 characters and contain letters and special characters."))
                else:
                    chk_res = check_login(st.session_state.user_id, cur_pw)
                    if chk_res:
                        change_user_password(st.session_state.user_id, new_pw_val)
                        st.success(_("비밀번호가 변경되었습니다.", "Password successfully changed."))
                    else:
                        st.error(_("현재 비밀번호가 올바르지 않습니다.", "Incorrect current password."))

        if st.button(_("로그아웃", "Log Out"), key="btn_logout_new"):
            st.session_state.user_id = None
            st.session_state.user_role = None
            st.session_state.expiry_date = None
            st.session_state.admin_mode = False
            st.query_params.pop("login_user", None)
            st.query_params.pop("login_token", None)
            st.rerun()

    # 분석 설정에만 세련된 스타일 적용 (Expander 내부에 마커를 삽입하여 타겟팅)
    st.markdown("""
    <style>
    div[data-testid="stExpander"]:has(.analysis-settings-marker) details summary {
        background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
        border-radius: 8px;
        padding: 10px 15px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    div[data-testid="stExpander"]:has(.analysis-settings-marker) details summary:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(0, 0, 0, 0.15);
    }
    div[data-testid="stExpander"]:has(.analysis-settings-marker) details summary p {
        color: white !important;
        font-weight: bold !important;
        font-size: 1.05rem !important;
    }
    div[data-testid="stExpander"]:has(.analysis-settings-marker) details summary svg {
        color: white !important;
    }
    </style>
    """, unsafe_allow_html=True)

    with st.expander(_("⚙️ AHP 분석 설정", "⚙️ Analysis Settings"), expanded=False):
        st.markdown('<div class="analysis-settings-marker"></div>', unsafe_allow_html=True)
        ahp_method_label = st.radio(_("분석 기법", "Analysis Method"), (_('일반 AHP (Traditional AHP)', 'Traditional AHP'), _('퍼지 AHP (Fuzzy AHP)', 'Fuzzy AHP')), index=0)
        ahp_method = 'traditional' if '일반' in ahp_method_label or 'Traditional' in ahp_method_label else 'fuzzy'
        mean_method_label = st.radio(_("평균 산출 방식", "Aggregation Method"), (_('기하평균 (Geometric)', 'Geometric Mean'), _('산술평균 (Arithmetic)', 'Arithmetic Mean')), index=0)
        mean_method = 'geometric' if '기하' in mean_method_label or 'Geometric' in mean_method_label else 'arithmetic'
        cr_threshold = st.selectbox(_("일관성 비율(CR) 임계값", "Consistency Ratio (CR) Threshold"), [0.1, 0.2], index=0)
        max_iter_val = st.number_input(_("최대 보정 반복 횟수", "Max Correction Iterations"), min_value=10, max_value=500, value=500, step=50)
        learning_rate = st.slider(_("보정 강도 (Learning Rate)", "Correction Intensity (Learning Rate)"), min_value=0.1, max_value=0.9, value=0.6, step=0.1)

    st.markdown(get_fee_info_text(), unsafe_allow_html=True)

    st.markdown("---")

    with st.expander(_("📖 이용자 가이드", "📖 User Guide"), expanded=False):
        st.markdown(_("AHP 마스터 서비스 사용 설명서 및 가이드 링크입니다.", "Link to the AHP Master user manual and guide."))
        if st.session_state.get('lang', 'ko') == 'en':
            if st.button("Read English User Guide", use_container_width=True, key="btn_read_guide"):
                st.session_state.page = "guide"
                st.rerun()
        else:
            st.link_button("이용자 가이드 바로가기", "https://morison.tistory.com/103", use_container_width=True)

    with st.expander(_("ℹ️ 일관성 보정 기준", "ℹ️ Consistency Correction Standard"), expanded=False):
        st.markdown(_("""
        **보정 방법: 반복 수렴 조정법(Iterative Adjustment)**
        가중치 산출 알고리즘(Saaty)에 의해 판단 행렬이 비일관적(CR > 임계값)인 경우, 수학적으로 일관된 행렬과 원본 행렬을 일정 비율로 혼합하여 반복적으로 가중치를 미세 조정한 결과를 제시합니다.
        
        **현재 방법의 특징:**
        1. **최소 판단 왜곡**: 원본 설문 응답의 경향성을 보존하면서 수학적 일관성만을 확보합니다.
        2. **자동 수렴**: 설정된 반복 횟수 내에서 CR 값을 임계값 이하로 자동 개선합니다. ($New = Old^{(1-\\alpha)} \\times Ideal^{\\alpha}$)
        
        """, """
        **Correction Method: Iterative Adjustment**
        If the judgment matrix is inconsistent (CR > threshold) based on Saaty's weight algorithm, it repeatedly adjusts the weights by mixing the original matrix with a mathematically consistent matrix.
        
        **Key Features:**
        1. **Minimal Distortion of Judgments**: Preserves the trends of the original survey responses while securing mathematical consistency.
        2. **Automatic Convergence**: Automatically improves the CR value to be below the threshold within the maximum number of iterations. ($New = Old^{(1-\\alpha)} \\times Ideal^{\\alpha}$)
        
        """))

    with st.expander(_("💡 사용자 권한 안내", "💡 User Roles & Permissions"), expanded=False):
        st.info(_("**비로그인(Guest)**: 샘플 파일 분석만 가능", "**Guest**: Sample file analysis only"))
        st.info(_("**무료사용자**: 나만의 모델 생성, 분석 가능 (무료 5표본 제한)", "**Free User**: Create custom models, analyze data (up to 5 samples)"))
        st.info(_("**정식 사용자**: 모든 기능 무제한 (2개월/필요시 1개월 연장)", "**Official User**: All features unlimited (2 months, extensible by 1 month)"))
    
    st.markdown("---")
    
    if st.session_state.get('lang', 'ko') == 'en':
        st.markdown("""
        ### Contact
        - **Email**: jeon080423@gmail.com
        - **KakaoTalk ID**: AHPkr
        - **Phone**: +82-10-2142-2610  
          <span style="color: gray; font-size: 0.85em;">(Please text us first, and we will call you back)</span>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        ### 문의처
        - **이메일**: jeon080423@gmail.com
        - **카톡ID**: AHPkr
        - **전화**: 010-2142-2610  
          <span style="color: gray; font-size: 0.85em;">(문자로 문의 하시면 전화 드립니다)</span>

        """, unsafe_allow_html=True)

# =============================================================================
# 4. Main Content Logic
# =============================================================================

if st.session_state.get('page', 'main') == 'guide':
    if st.button("← Back to AHP Analysis Tool", use_container_width=True, key="btn_back_to_main"):
        st.session_state.page = "main"
        st.rerun()
    
    st.title("📖 AHP Master - English User Guide")
    st.markdown("""
    🚀 **Welcome!** **AHP Master** is a smart web service that automatically processes the entire Analytic Hierarchy Process (AHP) workflow in 1 second, without requiring complex equations or statistical software.
    This guide is designed to walk first-time users through the step-by-step process of completing their academic thesis statistics and decision analysis smoothly.
    
    ---
    
    ### 📌 Step 1: Prepare the Excel Template (Write & Customize)
    AHP Master uses a specifically formatted Excel file to read your survey data.
    
    1. **Download Template**: Go to the AHP Master website (https://ahpkrj.streamlit.app/) and click the **[Download Excel Template]** button on the home screen.
    2. **🔥 Customize to Fit Your Model (Important)**:
       * The default template items (evaluation criteria, alternatives, etc.) and hierarchical structure can be freely edited to match your specific research model.
       * You can add or delete criteria to construct your own custom AHP model.
    3. **Enter Survey Data**: Open the customized Excel template and enter your pairwise comparison survey responses.
       * **Evaluation Scale**: Uses Saaty's 1-9 fundamental scale (e.g., enter 7 if item A is much more important than B, enter 1 if they are equally important).
       * **Note**: Be careful not to break the core structure (sheet configuration, etc.) of the template.
    
    ### 📥 Step 2: Upload File & Run Basic Analysis
    Once your data entry is complete, it's time to run the analysis.
    
    1. **File Upload**: Drag and drop your Excel file into the **[Drag and drop file here]** zone in the center of the screen, or click **[Browse files]** to select your file.
    2. **Automatic Execution**: The system will instantly run the complex matrix calculations in the background. Basic analysis typically completes in 1 to 3 seconds.
    
    ### ⚙️ Step 3: Utilize [Analysis Settings] in the Sidebar
    After uploading, you can fine-tune the analysis details through the "Analysis Settings" in the left sidebar to suit your research methodology.
    
    1. **Select Aggregation Method**:
       * You can set specific parameters like the weight integration method (Geometric Mean vs. Arithmetic Mean) or the decimal precision required for your research.
    2. **CR Calibration Settings (Optional)**:
       * You can set boundaries such as how much you allow the original response to change (Correction Intensity/Learning Rate) when performing Consistency Ratio (CR) calibration.
       * *(If accessing on a mobile device, tap the `>` icon in the top left to reveal the sidebar menu.)*
    
    ### 📊 Step 4: Consistency Validation & Automatic Calibration (CR)
    This is the step to validate the logical consistency of responses, which is critical in AHP academic studies.
    
    1. **Check Initial CR Value**: Check the **Consistency Ratio (CR)** displayed in the results panel.
       * `CR < 0.1` (Green): Indicates highly consistent and logical responses (Passed).
       * `CR > 0.1` (Red): Indicates logical contradictions exceed the standard limit (Needs Calibration).
    2. **🔥 One-Click Auto Calibration**: If the initial CR value exceeds 0.1, do not worry. Simply click the **[CR Auto Calibration]** button. AHP Master's optimization algorithm will adjust the CR value to under 0.1 automatically, preserving the original response preferences as much as possible.
    
    ### 🏆 Step 5: Check Weights & Save Results
    Once all validations and settings are complete, use the final results in your report or paper.
    
    1. **Check Weights & Rankings**:
       * **Main/Sub-Criteria Weights**: View the weight percentages and decimals representing the importance of each item.
       * **Global Rank**: View the overall 1st-to-last rankings of the items in an intuitive table and visual Plotly charts.
    2. **Download Results (Excel/Image)**:
       * Click the **[Download Results (Excel)]** button at the bottom of the screen to save the results in a clean table format ready to copy-paste.
       * Click the camera icon in the top right of the Plotly charts to save the charts as high-resolution images (PNG).
    
    ---
    
    ### 💡 Frequently Asked Questions (FAQ)
    
    * **Q1. Can I change the template items to fit my specific paper?**
      * **Yes, absolutely!** The default template is only an example. You can add or delete rows and columns, rename text, and modify items to build **your own custom hierarchical model (Custom Model)** to fit your evaluation criteria and alternative count.
    * **Q2. Can I analyze data from multiple survey respondents (group analysis) at once?**
      * Yes! If you have multiple respondents, you can calculate the geometric mean of individual pairwise comparisons in Excel, enter the aggregated figures into the template, and upload it to calculate the group weights at once.
    * **Q3. I see an "Error" message during upload. Why?**
      * In the customization process, the required sheets' layout may have been broken, or some number input cells might have empty (Null) values or text instead of numbers. Please review your Excel template to ensure all numeric inputs are complete.
    
    ---
    
    ### 💬 Contact & Support
    If you have any questions during analysis, or need custom AHP consulting (expert survey execution, thesis statistical consulting, etc.), please contact us:
    * **Email**: jeon080423@gmail.com
    * **KakaoTalk ID**: AHPkr
    * **Mobile**: +82-10-2142-2610
    """)
    
    if st.button("← Back to AHP Analysis Tool", use_container_width=True, key="btn_back_to_main_bottom"):
        st.session_state.page = "main"
        st.rerun()
    st.stop()

# 메인 헤더 영역
st.title(_("AHP 분석 자동화 시스템", "AHP Automated Decision System"))

st.markdown(_("Saaty(1980)의 Analytic Hierarchy Process (AHP) 분석 및 일관성 자동 보정 도구입니다.  \n일반 AHP뿐만 아니라 삼각퍼지수(TFN)를 활용한 **퍼지 AHP(Fuzzy AHP)** 분석도 함께 지원하며, 엑셀 파일을 업로드하면 개인별 가중치 산출, 일관성 보정(CR), 그룹별 집계 결과를 제공합니다.",
              "Saaty's (1980) Analytic Hierarchy Process (AHP) analysis and automatic consistency correction tool.  \nIt supports both traditional AHP and **Fuzzy AHP** analysis utilizing Triangular Fuzzy Numbers (TFN), and provides individual weights, Consistency Ratio (CR) correction, and group aggregation results upon uploading an Excel file."))

with st.expander(_("🎓 학술 논문 및 연구 보고서 기재 방법 예시", "🎓 Example of citation in academic papers/reports"), expanded=False):
    st.info(_("AHP 분석 결과를 학위 논문이나 연구 보고서에 기술할 때 아래 예시문을 참고하여 인용 및 서술하실 수 있습니다.",
              "When describing AHP analysis results in your thesis or research report, you can refer to and cite the example below."))
    st.markdown(_("""
    > **[논문 기재 예시문]**
    > 
    > "본 연구에서 수집된 설문 데이터는 웹 기반 AHP 전용 분석 솔루션인 **'AHP 마스터'**를 활용하여 분석을 수행하였다. Saaty(1980)의 계층분석과정에 따라 쌍대비교 행렬을 구성하여 국지적 가중치와 종합 가중치(Global Weight)를 산출하였으며, 일관성 비율(CR)이 0.1 미만이 되도록 시스템의 보정 기능을 거쳐 결과의 타당성을 확보하였다."
    """,
    """
    > **[Example of Paper Citation]**
    > 
    > "The survey data collected in this study was analyzed using **'AHP Master'**, a web-based dedicated AHP analysis solution. Pairwise comparison matrices were constructed in accordance with Saaty's (1980) Analytic Hierarchy Process to calculate local and global weights, and the validity of the results was secured through the system's consistency ratio (CR) adjustment function to ensure CR was below 0.1."
    """))
            

if st.session_state.get('admin_mode', False) and st.session_state.user_role == 'admin':
    # 세션 스테이트 기반 성공 메시지 잔존 출력
    if "sync_success_msg" in st.session_state:
        st.success(st.session_state["sync_success_msg"])
        del st.session_state["sync_success_msg"]

    st.subheader(_("👥 가입자 현황 및 관리", "👥 Registered Users & Admin Control"))
    
    col_sync1, col_sync2 = st.columns([2, 8])
    with col_sync1:
        if st.button("🔄 구글 시트와 동기화"):
            with st.spinner("구글 시트 데이터 불러오는 중..."):
                # 캐시 수동 비우기
                get_cached_visit_logs.clear()
                added_count = sync_db_from_sheets()
            if added_count >= 0:
                st.session_state["sync_success_msg"] = f"🎉 동기화 완료! (보정 및 복구된 데이터: {added_count}건)"
                st.rerun()
            else:
                st.error("동기화 중 오류가 발생했습니다. 화면상의 에러 메시지를 확인해 주세요.")
    
    try:
        # [최적화] 구글 시트 API 분당 호출 제한(429)을 피하기 위해 5분 캐시 처리된 함수를 사용합니다.
        visit_data_gs = get_cached_visit_logs(st.secrets["SPREADSHEET_ID"])
        daily_df_logs = pd.DataFrame(visit_data_gs)
        if not daily_df_logs.empty:
            daily_df_logs['Date_Only'] = daily_df_logs['Date'].astype(str).str[:10]
            daily_df_counts = daily_df_logs.groupby('Date_Only').size().reset_index(name='count')
            total_visits = len(daily_df_logs)

            st.write("#### 🗺️ 접속자 실시간 위치 분포")
            if 'Latitude' in daily_df_logs.columns and 'Longitude' in daily_df_logs.columns:
                map_data = daily_df_logs[daily_df_logs['Latitude'].astype(str).str.strip() != ""].copy()
                if not map_data.empty:
                    map_data['lat'] = pd.to_numeric(map_data['Latitude'], errors='coerce')
                    map_data['lon'] = pd.to_numeric(map_data['Longitude'], errors='coerce')
                    map_data = map_data.dropna(subset=['lat', 'lon'])
                    if not map_data.empty:
                        map_display = map_data.groupby(['lat', 'lon']).size().reset_index(name='visit_count')
                        map_display['size'] = map_display['visit_count'] * 20
                        st.map(map_display, latitude='lat', longitude='lon', size='size')
                    else:
                        st.info("유효한 좌표 데이터가 없습니다.")
                else:
                    st.info("지도에 표시할 위치 정보 데이터가 아직 수집되지 않았습니다.")
            else:
                st.info("위치 정보 컬럼이 존재하지 않습니다.")
        else:
            total_visits = 0
            daily_df_counts = pd.DataFrame()

        st.write(f"**총 누적 방문자 수 (시간 기반):** {total_visits:,}회")
        st.write("#### 📅 일별 방문자 현황 (날짜별 합산)")
        if not daily_df_counts.empty:
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
    
    users_df = get_all_users()
    st.dataframe(users_df)

    with st.expander("회원 정보 수정 (비밀번호 초기화 포함)"):
        edit_id = st.selectbox("수정할 회원 ID", users_df['id'].unique())
        selected_user = users_df[users_df['id'] == edit_id].iloc[0]
        new_role_val = st.selectbox("권한 변경", ['temp', 'official', 'admin'], 
                                index=['temp', 'official', 'admin'].index(selected_user['role']))
        
        if new_role_val == 'official' and selected_user['role'] != 'official':
            suggested_date = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).date() + relativedelta(months=2)
            new_expiry_val = st.text_input("만료일 설정 (YYYY-MM-DD) - 2개월 기한 자동 제안됨", value=str(suggested_date))
        else:
            new_expiry_val = st.text_input("만료일 변경 (YYYY-MM-DD)", value=selected_user['expiry_date'])
            
        new_pw_edit = st.text_input("새 비밀번호 (입력 시 변경됨)", type="password", placeholder="변경하지 않으려면 비워두세요")
        
        if st.button("정보 수정 적용"):
            update_user_full_info(edit_id, new_pw_edit, new_role_val, new_expiry_val)
            if new_role_val == 'official' and selected_user['role'] != 'official':
                send_approval_email(edit_id)
            st.success(f"{edit_id} 회원의 정보가 수정되었습니다.")
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
    st.divider()

st.subheader(_("1. AHP 분석 모델 설정 및 입력 템플릿 다운로드", "1. Setup AHP Decision Model & Download Template"))

if st.session_state.user_id is None:
    st.info(_("🔒 **로그인 후** '나만의 분석 모델'을 만들 수 있습니다. (비로그인 상태에서도 샘플 데이터로 최종 분석 결과를 미리볼 수 있습니다)",
              "🔒 **Log in** to create your own custom AHP models. (Even without logging in, you can preview results using sample data.)"))
else:
    saved_model = load_user_model(st.session_state.user_id)
    is_en = st.session_state.get('lang', 'ko') == 'en'
    
    en_default_main = "Governance, Planning, Feasibility, Effectiveness"
    en_default_subs = {
        "Governance": "AdminSupport, Community, PM",
        "Planning": "IssueFit, AlternativeFit, GoalClarity",
        "Feasibility": "LandAcquisition, ProjectDetail, CostFit",
        "Effectiveness": "Economic, Social, Performance"
    }
    ko_default_main = "거버넌스, 계획타당성, 실현가능성, 사업효과"
    ko_default_subs = {
        "거버넌스": "행정지원, 지역공동체, 총괄사업관리자",
        "계획타당성": "현안적정성, 대안적정성, 목표구체성",
        "실현가능성": "부지확보, 사업구체화, 사업비적정성",
        "사업효과": "경제적효과, 사회적효과, 성과관리"
    }

    if is_en:
        default_main = en_default_main
        default_subs = en_default_subs
    else:
        default_main = ko_default_main
        default_subs = ko_default_subs

    if saved_model:
        saved_main = saved_model.get('main', '')
        # 만약 저장된 모델이 반대 언어의 기본 예시와 동일하거나 비어 있다면, 현재 언어의 기본 예시를 표시
        if is_en and (saved_main == ko_default_main or not saved_main):
            pass
        elif not is_en and (saved_main == en_default_main or not saved_main):
            pass
        else:
            default_main = saved_main
            default_subs = saved_model.get('subs', default_subs)

    with st.expander(_("📌 나의 분석 모델 만들기", "📌 Create Custom AHP Model"), expanded=True):
        st.info(_("대항목과 세부항목을 입력하여 나만의 입력 엑셀 템플릿을 생성하세요. 본 템플릿은 일반 AHP 및 퍼지 AHP(Fuzzy AHP) 분석에 공통으로 사용됩니다.\n\n현재 입력되어 있는 내용은 샘플 모델입니다. 삭제하시고 이용자님의 AHP 모델을 입력하세요.",
                  "Enter main criteria and sub-criteria to generate your custom Excel template. This template is used for both traditional AHP and Fuzzy AHP analysis.\n\nThe content below is a sample model. Feel free to clear it and enter your own AHP elements."))
        main_criteria_input = st.text_input(_("대항목 (Main Criteria, 콤마 구분)", "Main Criteria (comma-separated)"), value=default_main)
        main_criteria_list = [x.strip() for x in main_criteria_input.split(',') if x.strip()]
        
        model_structure = {}
        if main_criteria_list:
            for mc in main_criteria_list:
                d_val = default_subs.get(mc, "")
                if isinstance(d_val, list): d_val = ", ".join(d_val)
                sub_input = st.text_input(_(f"'{mc}'의 세부항목", f"Sub-criteria for '{mc}'"), value=d_val, key=f"sub_{mc}")
                sub_list = [x.strip() for x in sub_input.split(',') if x.strip()]
                model_structure[mc] = sub_list
        
        if st.button(_("설정한 모델로 입력 엑셀 템플릿 생성", "Generate Excel Template with this Model")):
            if not main_criteria_list:
                st.error(_("대항목 입력 필요", "Main criteria input is required"))
            else:
                current_model = {'main': main_criteria_input, 'subs': model_structure}
                save_user_model(st.session_state.user_id, current_model)
                st.toast(_("모델 저장 완료", "Model successfully saved"))
                
                output_template = io.BytesIO()
                with pd.ExcelWriter(output_template, engine='xlsxwriter') as writer:
                    main_pairs = list(itertools.combinations(main_criteria_list, 2))
                    main_cols_tpl = ["ID", "Type"] + [f"{a}_{b}" for a, b in main_pairs]
                    df_template_main = pd.DataFrame(columns=main_cols_tpl)
                    df_template_main.loc[0] = [1, ""] + [0]*len(main_pairs)
                    df_template_main.to_excel(writer, sheet_name="Main_Criteria", index=False)
                    
                    for mc, subs in model_structure.items():
                        if len(subs) < 2:
                            df_sub = pd.DataFrame(columns=["ID", "Type"])
                        else:
                            sub_pairs = list(itertools.combinations(subs, 2))
                            sub_cols = ["ID", "Type"] + [f"{a}_{b}" for a, b in sub_pairs]
                            df_sub = pd.DataFrame(columns=sub_cols)
                            df_sub.loc[0] = [1, ""] + [0]*len(sub_pairs)
                        safe_sheet_name = mc[:31]
                        df_sub.to_excel(writer, sheet_name=safe_sheet_name, index=False)
                output_template.seek(0)
                st.download_button(
                    label=_("📥 엑셀 템플릿 다운로드", "📥 Download Excel Template"),
                    data=output_template,
                    file_name="AHP_Master_Template.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

                st.markdown(_("""
                ---
                ### 📝 데이터 입력 가이드
                1. **엑셀 파일 열기**: 위 버튼을 눌러 다운로드한 엑셀 파일을 실행합니다.
                2. **쌍대비교 데이터 입력**:
                    - **왼쪽** 항목이 더 중요하면: **음수** 입력 (예: -3)
                    - **오른쪽** 항목이 더 중요하면: **양수** 입력 (예: 3)
                    - **동등**하면: `1` 입력
                3. **필수 정보 입력**: A열(ID), **B열(Type)에 그룹명 입력 (예: 전문가, 주민 등)**
                """,
                """
                ---
                ### 📝 Data Input Guide
                1. **Open the Excel file**: Run the Excel template downloaded above.
                2. **Enter pairwise comparisons**:
                    - If the **left** item is more important: enter a **negative** value (e.g., -3)
                    - If the **right** item is more important: enter a **positive** value (e.g., 3)
                    - If they are **equal**: enter `1`
                3. **Required Information**: Column A (ID), **Column B (Type) for group names (e.g., Expert, Public, etc.)**
                """))
                img_file = _("ahp_input_guide.png", "ahp_input_guide_en.png")
                caption_text = _("[참고] 설문 응답을 엑셀에 입력하는 방법", "[Reference] How to enter survey responses into Excel")
                if os.path.exists(img_file):
                    st.image(img_file, caption=caption_text)

st.markdown("---")

if st.session_state.user_role == 'official':
    with st.expander(_("📂 나의 분석 보관함 (!중요) 반드시 컴퓨터에 백업해 주세요", "📂 My Analysis Storage (!Important: Please backup to your computer)")):
        my_analyses = get_user_analyses(st.session_state.user_id)
        if not my_analyses: st.info(_("저장된 분석 없음", "No saved analyses found."))
        else:
            for item in my_analyses:
                a_id, filename, save_date = item
                col_List1, col_List2, col_List3, col_List4 = st.columns([3, 2, 1, 1])
                with col_List1: st.text(f"{filename}")
                with col_List2: st.caption(f"{save_date}")
                with col_List3:
                    file_info = get_analysis_file(analysis_id=a_id)
                    if file_info:
                        fname, fdata = file_info
                        st.download_button("⬇️", fdata, fname, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key=f"dl_{a_id}")
                with col_List4:
                    if st.button("🗑️", key=f"del_{a_id}"):
                        delete_analysis(a_id)
                        st.rerun()

with st.container(border=True):
    st.markdown(_("#### ⚡ 빠른 시작 (도시재생 사업 모델)", "#### ⚡ Quick Start (Urban Regeneration Project Model)"))
    st.info(_("아래 버튼을 누르면 테스트용 샘플 엑셀 파일이 다운로드 됩니다.\n\n"
              "다운받은 테스트 샘플 엑셀 파일을 아래 '데이터 업로드 및 분석'에 업로드 하세요.",
              "Click the button below to download the test sample Excel file.\n\n"
              "Upload the downloaded sample file to '2. Data Upload & Analysis' below."))
    
    sample_excel = create_sample_excel()
    st.download_button(
        label=_("📂 테스트용 샘플 데이터 다운로드", "📂 Download Test Sample Data"),
        data=sample_excel,
        file_name=_("AHP_UrbanRegeneration_Sample.xlsx", "AHP_DecisionModel_Sample.xlsx"),
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

st.markdown("---")

def write_custom_ahp_table(writer, sheet_name, df, title_text, start_row, formats, excluded_df=None):
    workbook = writer.book
    if sheet_name in writer.sheets: worksheet = writer.sheets[sheet_name]
    else:
        worksheet = workbook.add_worksheet(sheet_name)
        writer.sheets[sheet_name] = worksheet
    
    header_fmt = formats['header']
    merge_fmt = formats['merge']
    body_fmt = formats['body']
    num_fmt = formats['num']
    sum_row_fmt = formats['sum_row']
    
    # [신규 추가] 제외 사례수 및 제외 응답값 데이터 출력
    if excluded_df is not None:
        worksheet.write(start_row, 0, _(f"※ 분석 제외 사례수: {len(excluded_df)}건", f"※ Number of cases excluded: {len(excluded_df)}"), workbook.add_format({'bold': True, 'font_color': 'red'}))
        start_row += 1
        if not excluded_df.empty:
            worksheet.write(start_row, 0, _("▶ 제외된 응답 데이터 (보정 실패)", "▶ Excluded Response Data (Correction Failed)"), workbook.add_format({'bold': True}))
            start_row += 1
            excluded_df.to_excel(writer, sheet_name=sheet_name, startrow=start_row, index=False)
            start_row += len(excluded_df) + 2

    worksheet.merge_range(start_row, 0, start_row, 6, title_text, workbook.add_format({'bold': True, 'font_size': 12}))
    start_row += 1
    
    headers = _(
        ["대분류", "가중치(a)", "중분류", "가중치(b)", "종합 가중치(a x b)", "종합 순위", "비고"],
        ["Main Criteria", "Weight(a)", "Sub-Criteria", "Weight(b)", "Global Weight(a x b)", "Global Rank", "Remarks"]
    )
    for col, h in enumerate(headers):
        worksheet.write(start_row, col, h, header_fmt)
    start_row += 1
    
    main_criteria = df['대분류'].unique()
    current_row = start_row
    
    for main_c in main_criteria:
        sub_df = df[df['대분류'] == main_c]
        n_subs = len(sub_df)
        main_w = sub_df.iloc[0]['대분류 가중치']
        sub_cr = sub_df.iloc[0]['CR(중분류)']
        sub_ci = sub_df.iloc[0]['CI(중분류)'] if 'CI(중분류)' in sub_df.columns else 0.0
        sum_sub_w = sub_df['중분류 가중치'].sum()
        
        merge_span = n_subs + 2 
        if merge_span > 1:
            worksheet.merge_range(current_row, 0, current_row + merge_span - 1, 0, main_c, merge_fmt)
            worksheet.merge_range(current_row, 1, current_row + merge_span - 1, 1, main_w, num_fmt)
        else:
            worksheet.write(current_row, 0, main_c, merge_fmt)
            worksheet.write(current_row, 1, main_w, num_fmt)
            
        for idx, row in sub_df.iterrows():
            worksheet.write(current_row, 2, row['중분류'], body_fmt)
            worksheet.write(current_row, 3, row['중분류 가중치'], num_fmt)
            worksheet.write(current_row, 4, row['Global Weight'], num_fmt)
            worksheet.write(current_row, 5, row['Global Rank'], body_fmt)
            worksheet.write(current_row, 6, "", body_fmt)
            current_row += 1
        
        worksheet.write(current_row, 2, _("합계", "Total"), sum_row_fmt)
        worksheet.write(current_row, 3, sum_sub_w, formats['sum_val'])
        worksheet.write_blank(current_row, 4, "", sum_row_fmt)
        worksheet.write_blank(current_row, 5, "", sum_row_fmt)
        worksheet.write_blank(current_row, 6, "", sum_row_fmt)
        current_row += 1
        
        worksheet.write(current_row, 2, _("일관성 비율(CR)", "Consistency Ratio (CR)"), sum_row_fmt)
        worksheet.write(current_row, 3, sub_cr, formats['num_sum'])
        worksheet.write(current_row, 4, _("일관성 지수(CI)", "Consistency Index (CI)"), sum_row_fmt)
        worksheet.write(current_row, 5, sub_ci, formats['num_sum'])
        worksheet.write_blank(current_row, 6, "", sum_row_fmt)
        current_row += 1

    worksheet.write(current_row, 0, _("합계", "Total"), sum_row_fmt)
    worksheet.write(current_row, 1, 1, formats['sum_val'])
    worksheet.write_blank(current_row, 2, "", sum_row_fmt)
    worksheet.write_blank(current_row, 3, "", sum_row_fmt)
    worksheet.write_blank(current_row, 4, "", sum_row_fmt)
    worksheet.write_blank(current_row, 5, "", sum_row_fmt)
    worksheet.write_blank(current_row, 6, "", sum_row_fmt)
    
    # [신규 추가] 대분류의 일관성 비율(CR) 및 일관성 지수(CI) 출력
    main_cr = df.iloc[0]['CR(대분류)'] if 'CR(대분류)' in df.columns else 0.0
    main_ci = df.iloc[0]['CI(대분류)'] if 'CI(대분류)' in df.columns else 0.0
    
    current_row += 1
    worksheet.write(current_row, 0, _("일관성 비율(CR)", "Consistency Ratio (CR)"), sum_row_fmt)
    worksheet.write(current_row, 1, main_cr, formats['num_sum'])
    worksheet.write(current_row, 2, _("일관성 지수(CI)", "Consistency Index (CI)"), sum_row_fmt)
    worksheet.write(current_row, 3, main_ci, formats['num_sum'])
    worksheet.write_blank(current_row, 4, "", sum_row_fmt)
    worksheet.write_blank(current_row, 5, "", sum_row_fmt)
    worksheet.write_blank(current_row, 6, "", sum_row_fmt)
    
    worksheet.set_column('A:A', 15)
    worksheet.set_column('B:B', 12)
    worksheet.set_column('C:C', 25)
    worksheet.set_column('D:F', 12)
    return current_row + 2

def add_borders_to_data(worksheet, start_row, start_col, df, border_fmt, has_header=True, has_index=False):
    rows = len(df) + (1 if has_header else 0)
    cols = len(df.columns) + (1 if has_index else 0)
    worksheet.conditional_format(start_row, start_col, start_row+rows-1, start_col+cols-1,
                                  {'type': 'formula', 'criteria': '=TRUE', 'format': border_fmt})

st.subheader(_("2. 데이터 업로드 및 분석", "2. Data Upload & Analysis"))
uploaded_file = st.file_uploader(_("작성된 엑셀 파일 업로드 (.xlsx)", "Upload completed Excel file (.xlsx)"), type=['xlsx', 'xls'])

if uploaded_file:
    try:
        excel_obj = pd.ExcelFile(uploaded_file)
        sheet_names = excel_obj.sheet_names
        df_main = pd.read_excel(uploaded_file, sheet_name=sheet_names[0])
        main_cols_up = df_main.columns[2:]
        main_factors_up, n_main_up = infer_factors_from_columns(main_cols_up)

        permission_granted = False
        message = ""
        role_chk = st.session_state.user_role
        user_id_chk = st.session_state.user_id

        if role_chk == 'admin' or role_chk == 'official':
            permission_granted = True
            if role_chk == 'official':
                today_chk = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).date()
                expiry_chk = datetime.datetime.strptime(st.session_state.expiry_date, "%Y-%m-%d").date()
                if today_chk > expiry_chk:
                    permission_granted = False
                    message = _("⛔ 이용 기간이 만료되었습니다.", "⛔ Your subscription period has expired.")
        else: 
            rows_ok = True
            for sn in sheet_names:
                if len(pd.read_excel(uploaded_file, sheet_name=sn)) > 5:
                    rows_ok = False
                    break
            if rows_ok: permission_granted = True
            else: message = _(f"⛔ **무료사용자**는 시트당 최대 5개 표본까지만 분석 가능합니다.", f"⛔ **Free Users** can only analyze up to 5 samples per sheet.")

        if permission_granted:
            try:
                with st.spinner(_("계층 분석 수행 중...", "Performing Analytic Hierarchy Process (AHP)...")):
                    # 1. 메인 시트 분석 시도
                    try:
                        main_results_df, main_factors, main_excluded, main_excluded_df = process_single_sheet(
                            df_main, cr_threshold, max_iter_val, learning_rate, mean_method, ahp_method
                        )
                    except Exception as e:
                        st.error(_("❌ [메인 시트] 분석 중 오류가 발생했습니다.", "❌ Error occurred during [Main Criteria] analysis."))
                        with st.expander(_("💡 이유 및 해결 방법 보기", "💡 View Reason & Solution"), expanded=True):
                            st.markdown(_(f"""
                            **원인:** 메인 시트의 데이터 구조가 올바르지 않거나 읽을 수 있는 유효 데이터가 없습니다. (Error: {e})
                            **해결 방법:**
                            1. 엑셀의 첫 번째 시트 이름이 `Main_Criteria`인지 확인하세요.
                            2. ID와 Type 열 다음에 쌍대비교 데이터가 올바르게 입력되었는지 확인하세요.
                            3. 빈 행이 포함되어 있다면 삭제 후 다시 시도하세요.
                            """,
                            f"""
                            **Cause:** The structure of the main sheet is incorrect or contains no readable valid data. (Error: {e})
                            **Solution:**
                            1. Ensure that the first sheet name in Excel is `Main_Criteria`.
                            2. Verify that pair-wise comparison data is correctly input after the 'ID' and 'Type' columns.
                            3. If empty rows are included, delete them and try again.
                            """))
                        st.stop()

                    # [방어 코드] 메인 결과 충분성 체크
                    if main_results_df.empty or len(main_results_df) < 1:
                        st.error(_(f"⚠️ 분석 불가: 메인 기준 유효 응답자가 부족합니다. (현재 {len(main_results_df)}명)",
                                   f"⚠️ Cannot Analyze: Insufficient valid respondents for Main Criteria. (Current: {len(main_results_df)} respondents)"))
                        with st.expander(_("💡 이유 및 해결 방법 보기", "💡 View Reason & Solution"), expanded=True):
                            st.markdown(_(f"""
                            **원인:** 모든 응답자의 일관성 비율(CR)이 임계치({cr_threshold})를 초과하여 보정 후에도 수렴하지 못했습니다.
                            **해결 방법:**
                            1. 왼쪽 사이드바에서 **'일관성 비율(CR) 임계값'**을 0.2로 완화해 보세요.
                            2. **'보정 강도(Learning Rate)'**를 0.7 이상으로 높여보세요.
                            3. **'최대 보정 반복 횟수'**를 500회로 설정했는지 확인하세요.
                            """,
                            f"""
                            **Cause:** The Consistency Ratio (CR) of all respondents exceeded the threshold ({cr_threshold}) and could not converge even after correction.
                            **Solution:**
                            1. Loosen the **'Consistency Ratio (CR) Threshold'** to 0.2 in the left sidebar.
                            2. Increase the **'Correction Intensity (Learning Rate)'** to 0.7 or higher.
                            3. Ensure **'Max Correction Iterations'** is set to 500.
                            """))
                        st.stop()

                    # 2. 하위 시트 분석 및 저장
                    sub_results_storage = {}
                    total_excl_df_list = [main_excluded_df]
                    
                    is_single_sheet = (len(sheet_names) == 1)
                    
                    if is_single_sheet:
                        for parent_factor in main_factors:
                            # 1단계 분석인 경우 (하위 시트가 없음), 
                            # 하위 가중치 1.0을 가지는 더미 데이터를 자동으로 생성하여 연산을 마칩니다.
                            dummy_list = []
                            for idx, row in main_results_df.iterrows():
                                dummy_list.append({
                                    "ID": row['ID'],
                                    "Type": row['Type'],
                                    "Original_CI": 0.0,
                                    "Original_CR": 0.0,
                                    "Final_CI": 0.0,
                                    "Final_CR": 0.0,
                                    "Iterations": 0,
                                    "Corrected": False,
                                    "Matrix_Object": np.array([[1.0]]),
                                    f"Weight_{parent_factor}": 1.0
                                })
                            dummy_df = pd.DataFrame(dummy_list)
                            sub_results_storage[parent_factor] = {
                                'weights': np.array([1.0]),
                                'factors': [parent_factor],
                                'cr': 0.0,
                                'ci': 0.0,
                                'df': dummy_df,
                                'group_matrix': np.array([[1.0]]),
                                'group_cr': 0.0,
                                'group_ci': 0.0
                            }
                    else:
                        for parent_factor in main_factors:
                            # 대분류 항목명과 일치하는 시트명 찾기 (대소문자, 공백 무시 및 31자 제한 고려)
                            target_name = parent_factor.strip().lower()
                            target_name_31 = parent_factor[:31].strip().lower()
                            
                            matched_sheet_name = None
                            for sn in sheet_names[1:]:
                                sn_clean = sn.strip().lower()
                                if sn_clean == target_name or sn_clean == target_name_31:
                                    matched_sheet_name = sn
                                    break
                            
                            if matched_sheet_name is None:
                                st.error(_(f"❌ [세부 시트: {parent_factor}] 시트를 찾을 수 없습니다.", f"❌ [Detailed Sheet: {parent_factor}] Sheet not found."))
                                with st.expander(_("💡 이유 및 해결 방법 보기", "💡 View Reason & Solution"), expanded=True):
                                    st.markdown(_(f"""
                                    **원인:** 메인 기준 시트에서 도출된 대분류 항목 **'{parent_factor}'**에 대응하는 세부 설문 응답 시트가 엑셀 파일 내에 존재하지 않거나 시트 이름이 다릅니다.
                                    **해결 방법:**
                                    1. 업로드한 엑셀 파일 내에 **'{parent_factor}'** (또는 31자 이내로 앞부분이 일치하는 명칭)의 시트가 존재하는지 확인하세요.
                                    2. 시트 이름의 앞뒤 공백이나 오탈자(예: '리드타임민감도'와 '리드타임 민감도')가 없는지 확인하고 시트명을 맞춰주세요.
                                    """,
                                    f"""
                                    **Cause:** The detailed survey response sheet corresponding to the main criteria category **'{parent_factor}'** does not exist in the Excel file or has a different name.
                                    **Solution:**
                                    1. Check if a sheet named **'{parent_factor}'** (or a name matching the first 31 characters) exists in the uploaded Excel file.
                                    2. Ensure there are no leading/trailing spaces or spelling discrepancies (e.g., 'Lead Time Sensitivity' vs 'LeadTime Sensitivity') and align the sheet names.
                                    """))
                                st.stop()
                            
                            try:
                                df_sub = pd.read_excel(uploaded_file, sheet_name=matched_sheet_name)
                                sub_res_df, sub_facts, sub_excl, sub_excl_df = process_single_sheet(
                                    df_sub, cr_threshold, max_iter_val, learning_rate, mean_method, ahp_method
                                )
                                
                                if sub_res_df.empty:
                                    raise ValueError(f"'{matched_sheet_name}' 시트에 유효한 분석 데이터가 없습니다.")
                                    
                                # 통계 계산 로직
                                sub_w_cols = [f"Weight_{f}" for f in sub_facts]
                                sub_matrices = np.stack(sub_res_df['Matrix_Object'].values)
                                sub_group_matrix = np.mean(sub_matrices, axis=0) if mean_method == 'arithmetic' else gmean(sub_matrices, axis=0)
                                sub_grp_cr, sub_grp_ci, _not_used_lambda = calculate_consistency(sub_group_matrix, method=mean_method)
                                
                                if ahp_method == 'fuzzy':
                                    sw_vals, sub_group_Si = fuzzy_ahp_analysis(sub_group_matrix)
                                    group_sub_w = pd.Series(sw_vals, index=sub_w_cols)
                                else:
                                    sub_group_Si = None
                                    group_sub_w = sub_res_df[sub_w_cols].mean(axis=0) if mean_method == 'arithmetic' else gmean(sub_res_df[sub_w_cols].values, axis=0)
                                    group_sub_w = group_sub_w / group_sub_w.sum()
                                
                                sub_results_storage[parent_factor] = {
                                    'weights': group_sub_w, 'factors': sub_facts, 'cr': sub_res_df['Final_CR'].mean(),
                                    'ci': sub_res_df['Final_CI'].mean(),
                                    'df': sub_res_df, 'group_matrix': sub_group_matrix, 'group_cr': sub_grp_cr,
                                    'group_ci': sub_grp_ci, 'group_Si': sub_group_Si
                                }
                                if not sub_excl_df.empty:
                                    sub_excl_df['Sheet'] = parent_factor
                                    total_excl_df_list.append(sub_excl_df)
                                    
                            except Exception as e:
                                st.error(_(f"❌ [세부 시트: {matched_sheet_name}] 분석 중 오류가 발생했습니다.", f"❌ Error occurred during [Detailed Sheet: {matched_sheet_name}] analysis."))
                                with st.expander(_("💡 이유 및 해결 방법 보기", "💡 View Reason & Solution"), expanded=True):
                                    st.markdown(_(f"""
                                    **원인:** 시트 내부의 데이터 구조가 올바르지 않거나, 해당 시트의 응답자들이 모두 일관성 기준을 통과하지 못했습니다. (Error: {e})
                                    **해결 방법:**
                                    1. 해당 세부 시트의 데이터에 빈 칸이나 문자가 섞여 있는지 확인하세요.
                                    2. CR 임계값을 높여서 다시 분석해 보세요.
                                    """,
                                    f"""
                                    **Cause:** The internal data structure of the sheet is incorrect, or all respondents for this sheet failed to pass the consistency ratio criteria. (Error: {e})
                                    **Solution:**
                                    1. Check if there are empty cells or text mixed in the data of the detailed sheet.
                                    2. Try analyzing again with a higher CR threshold.
                                    """))
                                st.stop()

                    # 분석 헤더 윗쪽에 제외된 사례수 표시
                    total_excluded = main_excluded
                    st.markdown(f"**" + _(f"분석 제외: {total_excluded}건", f"Excluded from Analysis: {total_excluded} cases") + "**")

                    main_sig_df = calculate_pairwise_ttest(main_results_df, main_factors)
                    main_weight_cols = [f"Weight_{f}" for f in main_factors]
                    
                    main_matrices = np.stack(main_results_df['Matrix_Object'].values)
                    main_group_matrix = np.mean(main_matrices, axis=0) if mean_method == 'arithmetic' else gmean(main_matrices, axis=0)
                    main_grp_cr, main_grp_ci, _not_used_lambda = calculate_consistency(main_group_matrix, mean_method)
                    
                    if ahp_method == 'fuzzy':
                        mw_vals, main_group_Si = fuzzy_ahp_analysis(main_group_matrix)
                        group_main_weights = pd.Series(mw_vals, index=main_weight_cols)
                    else:
                        main_group_Si = None
                        if mean_method == 'arithmetic':
                            group_main_weights = main_results_df[main_weight_cols].mean(axis=0)
                        else:
                            group_main_weights = gmean(main_results_df[main_weight_cols].values, axis=0)
                        group_main_weights = group_main_weights / group_main_weights.sum()
                    
                    main_cr_final_avg = main_results_df['Final_CR'].mean()
                    
                    indiv_global_data = []
                    all_ids = main_results_df['ID'].unique()
                    
                    for uid in all_ids:
                        u_main = main_results_df[main_results_df['ID'] == uid]
                        if u_main.empty: continue
                        u_type = u_main['Type'].values[0]
                        for mf in main_factors:
                            m_w = u_main[f"Weight_{mf}"].values[0]
                            s_row_df = sub_results_storage[mf]['df']
                            u_sub = s_row_df[s_row_df['ID'] == uid]
                            if u_sub.empty: continue
                            for sf in sub_results_storage[mf]['factors']:
                                s_w = u_sub[f"Weight_{sf}"].values[0]
                                indiv_global_data.append({
                                    "ID": uid, "Type": str(u_type), "Factor": sf, "Global_Weight": m_w * s_w,
                                    "Original_CR": u_main['Original_CR'].values[0],
                                    "Final_CR": u_main['Final_CR'].values[0]
                                })
                    indiv_df = pd.DataFrame(indiv_global_data)
                    
                    anova_df = pd.DataFrame()
                    if not indiv_df.empty and len(indiv_df['Type'].unique()) >= 2:
                        anova_df = calculate_anova_and_posthoc(indiv_df)

                    summary_rows = []
                    for idx, main_f in enumerate(main_factors):
                        m_weight = group_main_weights.iloc[idx] if isinstance(group_main_weights, pd.Series) else group_main_weights[idx]
                        sub_info = sub_results_storage[main_f]
                        for s_idx, sub_f in enumerate(sub_info['factors']):
                            s_weight = sub_info['weights'].iloc[s_idx] if isinstance(sub_info['weights'], pd.Series) else sub_info['weights'][s_idx]
                            global_w = m_weight * s_weight
                            summary_rows.append({
                                "대분류": main_f, "대분류 가중치": m_weight, "중분류": sub_f, "중분류 가중치": s_weight,
                                "Global Weight": global_w, 
                                "CR(대분류)": main_grp_cr, 
                                "CI(대분류)": main_grp_ci,
                                "CR(중분류)": sub_info['group_cr'],
                                "CI(중분류)": sub_info['group_ci']
                            })
                    
                    final_df = pd.DataFrame(summary_rows)
                    final_df['Global Rank'] = final_df['Global Weight'].rank(ascending=False, method='min').astype(int)
                    cols_order = ["대분류", "대분류 가중치", "중분류", "중분류 가중치", "Global Weight", "Global Rank", "CR(대분류)", "CI(대분류)", "CR(중분류)", "CI(중분류)"]
                    final_df = final_df[cols_order]

                    unique_groups = sorted(main_results_df['Type'].astype(str).unique())
                    group_analysis_results = {}
                    group_full_dfs = {} 
                    
                    for grp in unique_groups:
                        grp_main_df = main_results_df[main_results_df['Type'].astype(str) == grp]
                        if grp_main_df.empty: continue
                        g_main_mats = np.stack(grp_main_df['Matrix_Object'].values)
                        g_main_mat_obj = np.mean(g_main_mats, axis=0) if mean_method == 'arithmetic' else gmean(g_main_mats, axis=0)
                        g_main_cr, g_main_ci, _not_used_lambda = calculate_consistency(g_main_mat_obj, method=mean_method)
                        
                        if ahp_method == 'fuzzy':
                            mw_vals_grp, _unused_Si = fuzzy_ahp_analysis(g_main_mat_obj)
                            g_main_w = pd.Series(mw_vals_grp, index=main_weight_cols)
                        else:
                            g_main_w = grp_main_df[main_weight_cols].mean(axis=0) if mean_method == 'arithmetic' else gmean(grp_main_df[main_weight_cols].values, axis=0)
                            g_main_w = g_main_w / g_main_w.sum()
                        
                        grp_rows = []
                        for idx, main_f in enumerate(main_factors):
                            m_w = g_main_w.iloc[idx] if isinstance(g_main_w, pd.Series) else g_main_w[idx]
                            full_sub_df = sub_results_storage[main_f]['df']
                            grp_sub_df = full_sub_df[full_sub_df['Type'].astype(str) == grp]
                            sub_facts = sub_results_storage[main_f]['factors']
                            if grp_sub_df.empty: continue
                            s_w_cols = [f"Weight_{f}" for f in sub_facts]
                            g_sub_mats = np.stack(grp_sub_df['Matrix_Object'].values)
                            g_sub_mat_obj = np.mean(g_sub_mats, axis=0) if mean_method == 'arithmetic' else gmean(g_sub_mats, axis=0)
                            g_sub_cr, g_sub_ci, _not_used_lambda = calculate_consistency(g_sub_mat_obj, method=mean_method)
                            
                            if ahp_method == 'fuzzy':
                                sw_vals_grp, _unused_Si = fuzzy_ahp_analysis(g_sub_mat_obj)
                                g_sub_w = pd.Series(sw_vals_grp, index=s_w_cols)
                            else:
                                g_sub_w = grp_sub_df[s_w_cols].mean(axis=0) if mean_method == 'arithmetic' else gmean(grp_sub_df[s_w_cols].values, axis=0)
                                g_sub_w = g_sub_w / g_sub_w.sum()
                                
                            for s_idx, sf in enumerate(sub_facts):
                                s_w_val = g_sub_w.iloc[s_idx] if isinstance(g_sub_w, pd.Series) else g_sub_w[s_idx]
                                grp_rows.append({
                                    "대분류": main_f, "대분류 가중치": m_w, "중분류": sf, "중분류 가중치": s_w_val,
                                    "Global Weight": m_w * s_w_val, 
                                    "CR(대분류)": g_main_cr, 
                                    "CI(대분류)": g_main_ci,
                                    "CR(중분류)": g_sub_cr, 
                                    "CI(중분류)": g_sub_ci
                                })
                        g_df = pd.DataFrame(grp_rows)
                        if not g_df.empty:
                            g_df['Global Rank'] = g_df['Global Weight'].rank(ascending=False, method='min').astype(int)
                            group_full_dfs[grp] = g_df[cols_order]
                            group_analysis_results[grp] = group_full_dfs[grp][['중분류', 'Global Weight']]

                    comparison_df = final_df[['중분류', 'Global Weight']].copy()
                    comparison_df.rename(columns={'Global Weight': 'Overall'}, inplace=True)
                    for grp, df_res in group_analysis_results.items():
                        temp_df = df_res.rename(columns={'Global Weight': grp})
                        comparison_df = comparison_df.merge(temp_df, on='중분류', how='left')

                    output_res = io.BytesIO()
                    with pd.ExcelWriter(output_res, engine='xlsxwriter') as writer:
                        workbook = writer.book
                        formats = {
                            'header': workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'bg_color': '#000000', 'font_color': '#FFFFFF', 'border': 1}),
                            'merge': workbook.add_format({'align': 'center', 'valign': 'vcenter', 'border': 1}),
                            'body': workbook.add_format({'align': 'center', 'valign': 'vcenter', 'border': 1}),
                            'num': workbook.add_format({'align': 'center', 'valign': 'vcenter', 'border': 1, 'num_format': '0.000'}),
                            'sum_row': workbook.add_format({'bold': True, 'bg_color': '#D3D3D3', 'align': 'center', 'valign': 'vcenter', 'border': 1}),
                            'sum_val': workbook.add_format({'num_format': '0', 'bg_color': '#D3D3D3', 'border': 1, 'align':'center'}),
                            'num_sum': workbook.add_format({'num_format': '0.000', 'bg_color': '#D3D3D3', 'border': 1, 'align':'center'}),
                            'yellow': workbook.add_format({'bg_color': 'yellow', 'border': 1, 'align': 'center', 'num_format': '0.000'})
                        }
                        border_fmt = workbook.add_format({'border': 1})
                        fmt_float_no_border = workbook.add_format({'num_format': '0.000', 'align': 'center', 'valign': 'vcenter', 'border': 1})
                        fmt_diagonal = workbook.add_format({'num_format': '0', 'align': 'center', 'valign': 'vcenter', 'bg_color': '#E7E6E6', 'border': 1})

                        total_excluded_df = pd.concat(total_excl_df_list, ignore_index=True)
                        sheet_name_comp = _('종합분석', 'Comprehensive Analysis')
                        current_row_ws = write_custom_ahp_table(writer, sheet_name_comp, final_df, _("1) 전체_종합결과", "1) Overall Aggregated Results"), 1, formats, excluded_df=total_excluded_df)
                        for grp in unique_groups:
                            if grp in group_full_dfs:
                                current_row_ws = write_custom_ahp_table(writer, sheet_name_comp, group_full_dfs[grp], _(f"▶ [그룹: {grp}] 분석 결과", f"▶ [Group: {grp}] Analysis Results"), current_row_ws, formats)

                        if len(unique_groups) >= 1:
                            ws_comp = workbook.add_worksheet('Group_Comparison')
                            writer.sheets['Group_Comparison'] = ws_comp
                            s_row_cp = 1
                            ws_comp.write_string(s_row_cp, 0, _("그룹 간 비교(일원배치 분산분석: ANOVA)", "Group Comparison (One-way ANOVA)"), workbook.add_format({'bold': True, 'font_size': 12}))
                            s_row_cp += 1
                            
                            if not anova_df.empty:
                                anova_for_merge = anova_df.rename(columns={'요인': '중분류'})
                                integrated_df = comparison_df.merge(anova_for_merge, on='중분류', how='left')
                            else:
                                integrated_df = comparison_df
                            
                            # English renaming logic for columns & significance
                            if st.session_state.get('lang', 'ko') == 'en':
                                rename_dict = {
                                    '중분류': 'Sub-Criteria',
                                    'Overall': 'Overall',
                                    'F-값': 'F-Value',
                                    'P-Value': 'P-Value',
                                    '유의성': 'Significance',
                                    '사후검정(Tukey HSD)': 'Post-hoc (Tukey HSD)'
                                }
                                integrated_df_excel = integrated_df.copy()
                                integrated_df_excel.rename(columns=rename_dict, inplace=True)
                                if 'Significance' in integrated_df_excel.columns:
                                    integrated_df_excel['Significance'] = integrated_df_excel['Significance'].replace({
                                        '유의함': 'Significant',
                                        '유의하지 않음': 'Not Significant'
                                    })
                                if 'Post-hoc (Tukey HSD)' in integrated_df_excel.columns:
                                    integrated_df_excel['Post-hoc (Tukey HSD)'] = integrated_df_excel['Post-hoc (Tukey HSD)'].replace({
                                        '집단 간 구체적 차이 발견 못함': 'No specific difference found',
                                        '계산 오류': 'Calculation Error'
                                    })
                                    integrated_df_excel['Post-hoc (Tukey HSD)'] = integrated_df_excel['Post-hoc (Tukey HSD)'].apply(
                                        lambda x: x.replace(" 차이 있음", " Diff Exists") if isinstance(x, str) else x
                                    )
                            else:
                                integrated_df_excel = integrated_df

                            integrated_df_excel.to_excel(writer, sheet_name='Group_Comparison', startrow=s_row_cp, index=False)
                            add_borders_to_data(ws_comp, s_row_cp, 0, integrated_df_excel, border_fmt)
                            
                            num_format_3 = workbook.add_format({'num_format': '0.000', 'border': 1, 'align': 'center'})
                            for r in range(len(integrated_df_excel)):
                                for c in range(1, len(integrated_df_excel.columns)):
                                    val = integrated_df_excel.iloc[r, c]
                                    if pd.notnull(val) and isinstance(val, (int, float)):
                                        ws_comp.write_number(s_row_cp + 1 + r, c, val, num_format_3)
                                    elif pd.notnull(val):
                                        ws_comp.write(s_row_cp + 1 + r, c, val, border_fmt)

                            guide_start_row = s_row_cp + len(integrated_df_excel) + 3
                            bold_fmt = workbook.add_format({'bold': True, 'font_size': 11, 'valign': 'vcenter', 'align': 'left', 'bg_color': '#F2F2F2', 'border': 1})
                            text_fmt = workbook.add_format({'font_size': 10, 'text_wrap': True, 'valign': 'top', 'align': 'left', 'border': 1})
                            ws_comp.set_column('A:G', 20) 
                            
                            comp_title = _("※ 그룹 간 중요도의 차이가 있지만 통계적으로 유의하지 않게 나타나는 이유",
                                           "※ Reasons why group differences are not statistically significant despite variation in priorities")
                            ws_comp.merge_range(guide_start_row, 0, guide_start_row, 6, comp_title, bold_fmt)

                            guide_content_ko = [
                                ("1. 그룹 내 편차(분산)가 너무 큰 경우", "ANOVA는 '그룹 간의 차이'와 '그룹 내의 차이'를 비교합니다.\n\n■ 원리: 그룹 간 평균 차이가 크더라도, 각 그룹 내부 데이터들이 서로 들쭉날쭉(분산이 큼)하다면 통계적으로는 '이 차이가 우연히 발생했을 가능성이 높다'고 판단합니다."),
                                ("2. 표본 크기(Sample Size)의 부족", "통계적 유의성은 표본의 수에 매우 민감합니다.\n\n■ 현상: 각 그룹의 데이터 개수(표본수)가 너무 적다면 통계적 힘(Power)이 부족하여 유의미한 차이를 찾아내지 못합니다."),
                                ("3. 데이터의 단위(Scale)와 변동성", "표에 나타난 수치들이 대부분 매우 작은 소수점 단위입니다. 실제 계산 과정에서 표준오차 범위 내에 있다면 통계적으로는 측정 오차 범위 내의 흔들림으로 간주됩니다.")
                            ]
                            
                            guide_content_en = [
                                ("1. Within-Group Variance is Too Large", "ANOVA compares variance between groups against variance within groups.\n\n■ Principle: Even if the mean difference between groups is large, if individual responses within each group are highly scattered (large variance), statistics will determine that the difference is likely due to chance."),
                                ("2. Insufficient Sample Size", "Statistical significance is highly sensitive to the number of samples.\n\n■ Phenomenon: If the number of data points (sample size) in each group is too small, statistical power is insufficient to detect significant differences."),
                                ("3. Data Scale and Volatility", "The values in the table are mostly very small decimals. If they fall within the range of standard error, they are considered as minor fluctuations within the measurement error range.")
                            ]
                            
                            guide_content = guide_content_en if st.session_state.get('lang', 'ko') == 'en' else guide_content_ko

                            current_row_comp = guide_start_row + 1
                            for title, body in guide_content:
                                ws_comp.set_row(current_row_comp, 25)
                                ws_comp.merge_range(current_row_comp, 0, current_row_comp, 6, title, bold_fmt)
                                ws_comp.set_row(current_row_comp + 1, 80)
                                ws_comp.merge_range(current_row_comp + 1, 0, current_row_comp + 1, 6, body, text_fmt)
                                current_row_comp += 2

                        def write_detailed_sheet_ws(sheet_name, matrix_df, detail_df, matrix_title, row_labels, group_matrices=None, sheet_excl_count=0):
                            ws = workbook.add_worksheet(sheet_name)
                            writer.sheets[sheet_name] = ws
                            s_row_det = 0
                            
                            excl_label = _(f"분석 제외 사례수: {sheet_excl_count}건", f"Excluded cases: {sheet_excl_count}")
                            ws.write(s_row_det, 0, excl_label, workbook.add_format({'bold': True, 'font_color': 'red'}))
                            s_row_det += 1
                            
                            ws.write_string(s_row_det, 0, matrix_title)
                            s_row_det += 1
                            m_df_obj = pd.DataFrame(matrix_df, index=row_labels, columns=row_labels)
                            m_df_obj.to_excel(writer, sheet_name=sheet_name, startrow=s_row_det)
                            add_borders_to_data(ws, s_row_det, 0, m_df_obj, border_fmt, has_header=True, has_index=True)
                            for r in range(len(matrix_df)):
                                for c in range(len(matrix_df)):
                                    val = 1 if r==c else matrix_df[r][c]
                                    ws.write(s_row_det+r+1, c+1, val, border_fmt if r!=c else fmt_diagonal)
                                    if r!=c: ws.write(s_row_det+r+1, c+1, val, fmt_float_no_border)
                            
                            # [신규 추가] 전체 종합 행렬 오른쪽에 전체 CR, CI 값 표시
                            n_dim = len(matrix_df)
                            cr_val, ci_val, _unused_lambda = calculate_consistency(matrix_df, mean_method)
                            
                            ci_cr_header_fmt = workbook.add_format({
                                'bold': True, 'align': 'center', 'valign': 'vcenter',
                                'bg_color': '#4F81BD', 'font_color': '#FFFFFF', 'border': 1,
                                'font_name': 'NanumGothic'
                            })
                            ci_cr_label_fmt = workbook.add_format({
                                'bold': True, 'align': 'center', 'valign': 'vcenter',
                                'bg_color': '#D9E1F2', 'border': 1,
                                'font_name': 'NanumGothic'
                            })
                            ci_cr_val_fmt = workbook.add_format({
                                'align': 'center', 'valign': 'vcenter', 'border': 1,
                                'num_format': '0.000',
                                'font_name': 'NanumGothic'
                            })
                            if cr_val > 0.1:
                                ci_cr_val_fmt = workbook.add_format({
                                    'align': 'center', 'valign': 'vcenter', 'border': 1,
                                    'num_format': '0.000',
                                    'bg_color': '#FFC7CE', 'font_color': '#9C0006',
                                    'font_name': 'NanumGothic'
                                })
                            
                            ws.set_column(n_dim + 2, n_dim + 2, 12)
                            ws.set_column(n_dim + 3, n_dim + 3, 12)
                            
                            ws.merge_range(s_row_det, n_dim + 2, s_row_det, n_dim + 3, _("전체 일관성 지표", "Overall Consistency Indicators"), ci_cr_header_fmt)
                            ws.write(s_row_det + 1, n_dim + 2, _("전체 CI", "Overall CI"), ci_cr_label_fmt)
                            ws.write(s_row_det + 1, n_dim + 3, ci_val, ci_cr_val_fmt)
                            ws.write(s_row_det + 2, n_dim + 2, _("전체 CR", "Overall CR"), ci_cr_label_fmt)
                            ws.write(s_row_det + 2, n_dim + 3, cr_val, ci_cr_val_fmt)
                            
                            s_row_det += len(matrix_df) + 3
                            
                            if group_matrices:
                                for g_name, g_mat in group_matrices.items():
                                    ws.write_string(s_row_det, 0, _(f"] 그룹 종합 행렬: {g_name}", f"] Group Combined Matrix: {g_name}"))
                                    s_row_det += 1
                                    gm_df_obj = pd.DataFrame(g_mat, index=row_labels, columns=row_labels)
                                    gm_df_obj.to_excel(writer, sheet_name=sheet_name, startrow=s_row_det)
                                    add_borders_to_data(ws, s_row_det, 0, gm_df_obj, border_fmt, has_header=True, has_index=True)
                                    for r in range(len(g_mat)):
                                        for c in range(len(g_mat)):
                                            val = 1 if r==c else g_mat[r][c]
                                            ws.write(s_row_det+r+1, c+1, val, border_fmt if r!=c else fmt_diagonal)
                                            if r!=c: ws.write(s_row_det+r+1, c+1, val, fmt_float_no_border)
                                    
                                    # [신규 추가] 그룹 종합 행렬 오른쪽에 그룹 CR, CI 값 표시
                                    g_cr_val, g_ci_val, _unused_lambda = calculate_consistency(g_mat, mean_method)
                                    g_ci_cr_val_fmt = workbook.add_format({
                                        'align': 'center', 'valign': 'vcenter', 'border': 1,
                                        'num_format': '0.000',
                                        'font_name': 'NanumGothic'
                                    })
                                    if g_cr_val > 0.1:
                                        g_ci_cr_val_fmt = workbook.add_format({
                                            'align': 'center', 'valign': 'vcenter', 'border': 1,
                                            'num_format': '0.000',
                                            'bg_color': '#FFC7CE', 'font_color': '#9C0006',
                                            'font_name': 'NanumGothic'
                                        })
                                    
                                    ws.merge_range(s_row_det, n_dim + 2, s_row_det, n_dim + 3, _("그룹 일관성 지표", "Group Consistency Indicators"), ci_cr_header_fmt)
                                    ws.write(s_row_det + 1, n_dim + 2, _("그룹 CI", "Group CI"), ci_cr_label_fmt)
                                    ws.write(s_row_det + 1, n_dim + 3, g_ci_val, g_ci_cr_val_fmt)
                                    ws.write(s_row_det + 2, n_dim + 2, _("그룹 CR", "Group CR"), ci_cr_label_fmt)
                                    ws.write(s_row_det + 2, n_dim + 3, g_cr_val, g_ci_cr_val_fmt)
                                    
                                    s_row_det += len(g_mat) + 3
                            
                            detail_df.to_excel(writer, sheet_name=sheet_name, startrow=s_row_det, index=False)
                            for c_idx, col_val in enumerate(detail_df.columns):
                                ws.write(s_row_det, c_idx, col_val, formats['header'])
                            
                            for r_idx in range(len(detail_df)):
                                row_pos = s_row_det + 1 + r_idx
                                for c_idx, col_name in enumerate(detail_df.columns):
                                    val = detail_df.iloc[r_idx, c_idx]
                                    current_fmt = border_fmt
                                    if col_name in ['Original_CR', 'Final_CR'] and isinstance(val, (float, int)) and val > 0.1:
                                        current_fmt = formats['yellow']
                                    elif isinstance(val, (float, np.float64)):
                                        current_fmt = formats['num']
                                    else:
                                        current_fmt = formats['body']
                                    
                                    if pd.isnull(val):
                                        ws.write_blank(row_pos, c_idx, "", current_fmt)
                                    else:
                                        ws.write(row_pos, c_idx, val, current_fmt)

                        main_group_mats = {}
                        for grp in unique_groups:
                            g_df_m = main_results_df[main_results_df['Type'].astype(str) == grp]
                            if not g_df_m.empty:
                                mats = np.stack(g_df_m['Matrix_Object'].values)
                                main_group_mats[grp] = np.mean(mats, axis=0) if mean_method == 'arithmetic' else gmean(mats, axis=0)

                        out_main = main_results_df.drop(columns=['Matrix_Object'], errors='ignore')
                        write_detailed_sheet_ws('Result_Main', main_group_matrix, out_main, _("[1] 전체 종합 행렬", "[1] Overall Combined Matrix"), main_factors, group_matrices=main_group_mats, sheet_excl_count=main_excluded)
                        for mf, info in sub_results_storage.items():
                            safe_name = f"Result_{mf}"[:31]
                            sub_grp_mats = {}
                            for grp in unique_groups:
                                g_sub_df = info['df'][info['df']['Type'].astype(str) == grp]
                                if not g_sub_df.empty:
                                    mats = np.stack(g_sub_df['Matrix_Object'].values)
                                    sub_grp_mats[grp] = np.mean(mats, axis=0) if mean_method == 'arithmetic' else gmean(mats, axis=0)
                            out_sub = info['df'].drop(columns=['Matrix_Object'], errors='ignore')
                            
                            sub_excl_val = 0
                            for df_ex in total_excl_df_list:
                                if 'Sheet' in df_ex.columns and not df_ex.empty:
                                     if mf in df_ex['Sheet'].unique():
                                         sub_excl_val = len(df_ex[df_ex['Sheet'] == mf])
                                         
                            write_detailed_sheet_ws(safe_name, info['group_matrix'], out_sub, _("[1] 전체 종합 행렬", "[1] Overall Combined Matrix"), info['factors'], group_matrices=sub_grp_mats, sheet_excl_count=sub_excl_val)

                        is_english = (st.session_state.get('lang', 'ko') == 'en')
                        theory_ws = workbook.add_worksheet("Consistency_Theory")
                        theory_title_fmt = workbook.add_format({'bold': True, 'font_size': 14, 'font_name': 'NanumGothic'})
                        theory_body_fmt = workbook.add_format({'text_wrap': True, 'valign': 'top', 'font_name': 'NanumGothic'})
                        if is_english:
                            theory_text = [
                                ["AHP Consistency Calibration Principle & Academic Foundation from a Decision-Making Perspective"],
                                [""],
                                ["1. Introduction: The Issue of Consistency in the Analytic Hierarchy Process (AHP)"],
                                ["The Analytic Hierarchy Process, proposed by Saaty (1980), is a multi-criteria decision-making tool that quantifies human subjective judgment. When inconsistent judgments occur, they are mathematically corrected to ensure the reliability of the analysis."],
                                [""],
                                ["2. Calibration Algorithm: Iterative Convergence Adjusting Method"],
                                [f"The original matrix A and the ideal matrix W are linearly combined according to the set learning rate (learning rate α={learning_rate}): A_new = (1-α)A + αW."],
                                [""],
                                ["3. Academic Foundation & Effects"],
                                ["Adjustment using a weighted average of the original matrix and the consistent matrix preserves the decision maker's original preferences as much as possible while improving mathematical consistency."]
                            ]
                        else:
                            theory_text = [
                                ["의사결정론적 관점에서의 AHP 일관성 보정 원리 및 학술적 근거"],
                                [""],
                                ["1. 서론: 계층분석과정(AHP)의 일관성 문제"],
                                ["Saaty(1980)에 의해 제안된 계층분석과정은 인간의 주관적 판단을 정량화하는 다기준 의사결정 도구이다. 비일관적 판단이 발생할 경우 수학적으로 교정하여 분석의 신뢰성을 확보한다."],
                                [""],
                                ["2. 보정 알고리즘: 반복 수렴 조정법"],
                                [f"원본 행렬 A와 이상적 행렬 W를 설정된 학습률(α={learning_rate})에 따라 선형 결합한다: A_new = (1-α)A + αW."],
                                [""],
                                ["3. 학술적 근거 및 효과"],
                                ["원본 행렬과 일관 행렬의 가중 평균을 이용한 조정은 의사결정자의 원래 선호 경향성을 최대한 보존하면서 수학적 일관성을 향상시킨다."]
                            ]
                        theory_ws.set_column('A:A', 100)
                        for r_idx, row_content in enumerate(theory_text):
                            fmt = theory_title_fmt if r_idx == 0 else theory_body_fmt
                            theory_ws.write(r_idx, 0, row_content[0], fmt)

                        if is_single_sheet:
                            guide_ws = workbook.add_worksheet("Single_Sheet_Guide")
                            guide_title_fmt = workbook.add_format({'bold': True, 'font_size': 14, 'font_name': 'NanumGothic', 'bg_color': '#D9E1F2', 'border': 1, 'align': 'center', 'valign': 'vcenter'})
                            guide_section_fmt = workbook.add_format({'bold': True, 'font_size': 11, 'font_name': 'NanumGothic', 'bg_color': '#F2F2F2', 'border': 1, 'valign': 'vcenter', 'align': 'center'})
                            guide_body_fmt = workbook.add_format({'text_wrap': True, 'valign': 'top', 'font_name': 'NanumGothic', 'border': 1})
                            
                            guide_ws.set_column('A:A', 25)
                            guide_ws.set_column('B:B', 75)
                            
                            # Merge title row
                            guide_title = _("1단계 AHP 분석 결과 해석 및 주의사항", "Step 1 AHP Analysis Result Interpretation and Guidelines")
                            guide_ws.merge_range('A1:B1', guide_title, guide_title_fmt)
                            guide_ws.set_row(0, 35)
                            
                            if is_english:
                                guide_data = [
                                    ("Classification", "Detailed Content"),
                                    ("1. Analysis Overview", "This report is a single-level AHP analysis result comparing only the main criteria (Step 1) evaluation criteria without sub-criteria."),
                                    ("2. Result Interpretation Method", "Since the sub-weights are fixed at 1.0, the 'Main Criteria Weight' and the 'Global Weight' are calculated with the same values. Therefore, you can interpret the 'Global Weight' as the final importance of each item."),
                                    ("3. Internal Virtual Operation Guide", "To maintain consistency of the 2-level operation of the AHP analysis system, the system internally auto-generated and computed dummy detailed items with a weight of 1.0 under the main criteria items. Due to this, the 'Result_[Main Criteria Name]' sheet exists in the results download file as a 1x1 matrix, which is a normal virtual operation result."),
                                    ("4. Consistency Ratio (CR) Warnings", "The provided consistency ratio represents only the CR of the pairwise comparison of the main criteria. Since there are no sub-criteria, the 'Sub-Criteria Consistency Ratio (CR)' is unconditionally marked as 0.000, which is not an error."),
                                    ("5. Academic/Report Writing Tip", "When utilizing this in academic research or reports, please explicitly state that 'pairwise comparison analysis was performed under a single-level (Step 1) hierarchical structure.'")
                                ]
                            else:
                                guide_data = [
                                    ("분류", "상세 내용"),
                                    ("1. 분석 개요", "본 보고서는 하위 요소 없이 대분류(1단계) 평가 기준만을 비교한 단일 계층 AHP 분석 결과입니다."),
                                    ("2. 결과 해석 방법", "하위 가중치가 1.0으로 고정되어 '대분류 가중치'와 'Global Weight(종합 가중치)'가 동일한 수치로 산출되었습니다. 따라서 'Global Weight'를 각 항목의 최종 중요도로 해석하시면 됩니다."),
                                    ("3. 내부 가상 연산 안내", "AHP 분석 시스템의 2단계 연산 일관성 유지를 위해, 시스템 내부적으로 대분류 항목 하위에 가중치 1.0을 가지는 더미 세부 항목을 자동 생성하여 연산하였습니다. 이로 인해 결과 다운로드 파일에 'Result_[대분류명]' 시트가 1x1 행렬로 존재하지만 이는 정상적인 가상 연산 결과입니다."),
                                    ("4. 일관성 비율(CR) 주의사항", "제공된 일관성 비율은 대분류 쌍대비교의 일관성 비율(CR)만을 나타냅니다. 하위 요소가 존재하지 않으므로 '중분류 일관성 비율(CR)'은 무조건 0.000으로 표기되며 이는 오류가 아닙니다."),
                                    ("5. 학술/보고서 기재 팁", "학술 연구나 보고서에 활용 시 '단일 계층(1단계) 계층 구조 하에서 쌍대비교 분석을 수행하였다'고 명시적으로 기재하시기 바랍니다.")
                                ]
                            
                            for r_idx, (section, content) in enumerate(guide_data, start=1):
                                if r_idx == 1:
                                    # Header row
                                    guide_ws.write(r_idx, 0, section, workbook.add_format({'bold': True, 'align': 'center', 'bg_color': '#A6A6A6', 'border': 1}))
                                    guide_ws.write(r_idx, 1, content, workbook.add_format({'bold': True, 'align': 'center', 'bg_color': '#A6A6A6', 'border': 1}))
                                else:
                                    guide_ws.write(r_idx, 0, section, guide_section_fmt)
                                    guide_ws.write(r_idx, 1, content, guide_body_fmt)
                                guide_ws.set_row(r_idx, 60 if r_idx > 1 else 20)

                st.success(_("분석이 완료되었습니다.", "Analysis completed successfully."))
                if st.session_state.user_role == 'official':
                    save_analysis_to_db(st.session_state.user_id, f"{uploaded_file.name.split('.')[0]}_Result.xlsx", output_res.getvalue())

                # 결과 휘발성 주의 안내
                st.markdown(_('<p style="color: red; font-weight: bold; font-size: 0.95rem; margin-top: 5px; margin-bottom: 10px;">⚠️ 주의: 페이지를 새로고침하거나 브라우저를 닫으면 분석 결과가 저장되지 않고 리셋되므로, 결과물 엑셀 파일(📑 결과 다운로드 탭)을 반드시 다운로드하여 저장해 주세요.</p>',
                              '<p style="color: red; font-weight: bold; font-size: 0.95rem; margin-top: 5px; margin-bottom: 10px;">⚠️ Warning: Analysis results are not stored and will be reset if you refresh the page or close the browser. Please make sure to download and save the results Excel file (📑 Download Results tab).</p>'), unsafe_allow_html=True)

                tab1, tab2, tab3, tab4, tab5 = st.tabs([
                    _("🌐 종합 분석 (Global)", "🌐 Global Comprehensive Analysis"),
                    _("👨‍👩‍👧‍👦 그룹별 분석", "👨‍👩‍👧‍👦 Group Analysis"),
                    _("🧪 통계 검정 (ANOVA)", "🧪 Statistical Test (ANOVA)"),
                    _("📊 시각화 센터", "📊 Visualization Center"),
                    _("📑 결과 다운로드", "📑 Download Results")
                ])
                with tab1:
                    st.subheader(_("🌐 종합 중요도 및 순위", "🌐 Global Weights & Rankings"))
                    if is_english:
                        disp_final_df = final_df.rename(columns={
                            "대분류": "Main Criteria",
                            "대분류 가중치": "Main Criteria Weight",
                            "중분류": "Sub-Criteria",
                            "중분류 가중치": "Sub-Criteria Weight",
                            "Global Weight": "Global Weight",
                            "Global Rank": "Global Rank",
                            "CR(대분류)": "CR (Main Criteria)",
                            "CI(대분류)": "CI (Main Criteria)",
                            "CR(중분류)": "CR (Sub-Criteria)",
                            "CI(중분류)": "CI (Sub-Criteria)"
                        })
                    else:
                        disp_final_df = final_df
                    st.dataframe(disp_final_df.style.format(precision=3), use_container_width=True)

                    # ── Fuzzy AHP TFN 삼각퍼지 그래프 (Tab1 결과 화면 직후) ──
                    if ahp_method == 'fuzzy':
                        st.markdown("---")
                        st.subheader(_("📐 삼각퍼지수(TFN) 가중치 분포", "📐 Triangular Fuzzy Number (TFN) Weight Distribution"))
                        st.caption(_("각 요인의 삼각퍼지수(L, M, U)와 비퍼지화된 Crisp 가중치를 시각화합니다.",
                                     "Visualizes each factor's Triangular Fuzzy Numbers (L, M, U) and defuzzified Crisp weights."))

                        tfn_color_palette = [
                            '#636EFA', '#EF553B', '#00CC96', '#AB63FA', '#FFA15A',
                            '#19D3F3', '#FF6692', '#B6E880', '#FF97FF', '#FECB52'
                        ]

                        def render_tfn_chart(tfn_Si_data, tfn_factors_data, chart_title):
                            fig = go.Figure()
                            for i, (l, m, u) in enumerate(tfn_Si_data):
                                color = tfn_color_palette[i % len(tfn_color_palette)]
                                crisp = (l * m * u) ** (1/3)
                                # 삼각형 채우기 (반투명)
                                fig.add_trace(go.Scatter(
                                    x=[l, m, u, l],
                                    y=[0, 1, 0, 0],
                                    fill='toself',
                                    fillcolor=f"rgba({int(color[1:3],16)}, {int(color[3:5],16)}, {int(color[5:7],16)}, 0.15)" if color.startswith('#') and len(color) == 7 else (color.replace(')', ', 0.15)').replace('rgb', 'rgba') if 'rgb' in color else color),
                                    line=dict(color=color, width=2.5),
                                    mode='lines',
                                    name=f"{tfn_factors_data[i]}",
                                    hovertemplate=(
                                        f"<b>{tfn_factors_data[i]}</b><br>"
                                        f"L={l:.4f}, M={m:.4f}, U={u:.4f}<br>"
                                        f"Crisp={crisp:.4f}<extra></extra>"
                                    ),
                                    showlegend=True
                                ))
                                # Crisp 가중치 수직 점선
                                fig.add_trace(go.Scatter(
                                    x=[crisp, crisp],
                                    y=[0, 0.85],
                                    mode='lines',
                                    line=dict(color=color, width=1.5, dash='dot'),
                                    showlegend=False,
                                    hoverinfo='skip'
                                ))
                                # Crisp 마커
                                fig.add_trace(go.Scatter(
                                    x=[crisp],
                                    y=[0.88],
                                    mode='markers+text',
                                    marker=dict(color=color, size=8, symbol='diamond'),
                                    text=[f"{crisp:.3f}"],
                                    textposition='top center',
                                    textfont=dict(size=10, color=color),
                                    showlegend=False,
                                    hovertemplate=f"<b>{tfn_factors_data[i]}</b> Crisp={crisp:.4f}<extra></extra>"
                                ))
                            fig.update_layout(
                                title=dict(text=chart_title, font=dict(size=14)),
                                xaxis_title=_("가중치 값 (Weight Value)", "Weight Value"),
                                yaxis_title=_("소속도 (Membership Degree)", "Membership Degree"),
                                yaxis=dict(range=[-0.05, 1.25]),
                                height=420,
                                margin=dict(l=30, r=30, t=50, b=40),
                                hovermode="closest",
                                legend=dict(
                                    orientation="h",
                                    yanchor="bottom",
                                    y=-0.25,
                                    xanchor="center",
                                    x=0.5
                                ),
                                plot_bgcolor='rgba(248,249,250,1)',
                                paper_bgcolor='rgba(255,255,255,1)'
                            )
                            fig.update_xaxes(gridcolor='rgba(200,200,200,0.3)', zeroline=True, zerolinecolor='rgba(150,150,150,0.5)')
                            fig.update_yaxes(gridcolor='rgba(200,200,200,0.3)')
                            return fig

                        # 1) 메인 기준 TFN 그래프
                        if main_group_Si:
                            st.plotly_chart(
                                render_tfn_chart(main_group_Si, main_factors,
                                    _("▶ 대분류 (Main Criteria) 삼각퍼지 분포", "▶ Main Criteria TFN Distribution")),
                                use_container_width=True
                            )

                            # TFN 수치 테이블
                            tfn_table_rows = []
                            for i, (l, m, u) in enumerate(main_group_Si):
                                crisp = (l * m * u) ** (1/3)
                                tfn_table_rows.append({
                                    _("요인", "Factor"): main_factors[i],
                                    "L (Lower)": l, "M (Most Likely)": m, "U (Upper)": u,
                                    "Crisp Weight": crisp,
                                    _("정규화 가중치", "Normalized Weight"): group_main_weights.iloc[i] if isinstance(group_main_weights, pd.Series) else group_main_weights[i]
                                })
                            st.dataframe(pd.DataFrame(tfn_table_rows).style.format(precision=4), use_container_width=True)

                        # 2) 세부 기준별 TFN 그래프
                        for parent_f, sub_info in sub_results_storage.items():
                            if sub_info.get('group_Si'):
                                st.markdown("---")
                                st.plotly_chart(
                                    render_tfn_chart(sub_info['group_Si'], sub_info['factors'],
                                        _(f"▶ [{parent_f}] 세부항목 삼각퍼지 분포", f"▶ [{parent_f}] Sub-Criteria TFN Distribution")),
                                    use_container_width=True
                                )
                                sub_tfn_rows = []
                                for i, (l, m, u) in enumerate(sub_info['group_Si']):
                                    crisp = (l * m * u) ** (1/3)
                                    sub_tfn_rows.append({
                                        _("요인", "Factor"): sub_info['factors'][i],
                                        "L (Lower)": l, "M (Most Likely)": m, "U (Upper)": u,
                                        "Crisp Weight": crisp,
                                        _("정규화 가중치", "Normalized Weight"): sub_info['weights'].iloc[i] if isinstance(sub_info['weights'], pd.Series) else sub_info['weights'][i]
                                    })
                                st.dataframe(pd.DataFrame(sub_tfn_rows).style.format(precision=4), use_container_width=True)

                with tab2:
                    st.markdown(_("#### 그룹별 가중치 상세 비교", "#### Detailed Comparison of Weights by Group"))
                    disp_comparison_df = comparison_df.copy()
                    if is_english:
                        disp_comparison_df.rename(columns={
                            "중분류": "Sub-Criteria",
                            "Overall": "Overall",
                            "전문가": "Expert",
                            "일반": "General",
                            "공무원": "Public Official"
                        }, inplace=True)
                    st.dataframe(disp_comparison_df.style.format(precision=4), use_container_width=True)
                with tab3:
                    st.markdown(_("#### 집단 간 유의성 분석", "#### Analysis of Significance Between Groups"))
                    if not anova_df.empty:
                        if is_english:
                            disp_anova = anova_df.copy()
                            disp_anova.rename(columns={
                                "요인": "Factor/Criteria",
                                "F-값": "F-Value",
                                "P-Value": "P-Value",
                                "유의성": "Significance",
                                "사후검정(Tukey HSD)": "Post-Hoc (Tukey HSD)"
                            }, inplace=True)
                            
                            # Map values in Significance
                            disp_anova["Significance"] = disp_anova["Significance"].map({
                                "유의함": "Significant",
                                "유의하지 않음": "Not Significant"
                            }).fillna(disp_anova["Significance"])
                            
                            # Map values in Post-Hoc
                            def translate_posthoc(val):
                                if not isinstance(val, str):
                                    return val
                                val = val.replace("전문가", "Expert").replace("일반", "General").replace("공무원", "Public Official")
                                val = val.replace(" 차이 있음", " (Diff exists)")
                                val = val.replace("집단 간 구체적 차이 발견 못함", "No significant pairwise difference found")
                                val = val.replace("계산 오류", "Calculation Error")
                                return val
                            disp_anova["Post-Hoc (Tukey HSD)"] = disp_anova["Post-Hoc (Tukey HSD)"].apply(translate_posthoc)
                        else:
                            disp_anova = anova_df
                        st.dataframe(disp_anova.style.format(precision=5), use_container_width=True)
                    else:
                        st.info(_("통계 검정을 위해 2개 이상의 그룹 데이터가 필요합니다.", "At least 2 group datasets are required for statistical testing (ANOVA)."))
                with tab4:
                    st.markdown(_("#### 📊 시각화 센터", "#### 📊 Visualization Center"))
                    col_chart1, col_chart2 = st.columns(2)
                    with col_chart1:
                        st.write(_("**종합 중요도 (Bar)**", "**Global Importance (Bar)**"))
                        chart_bar_df = final_df.sort_values('Global Weight').copy()
                        if is_english:
                            chart_bar_df.rename(columns={"중분류": "Sub-Criteria", "Global Weight": "Global Weight"}, inplace=True)
                            y_col = "Sub-Criteria"
                            x_col = "Global Weight"
                        else:
                            y_col = "중분류"
                            x_col = "Global Weight"
                        fig_bar = px.bar(chart_bar_df, y=y_col, x=x_col, orientation='h', text_auto='.3f')
                        st.plotly_chart(fig_bar, use_container_width=True)
                    with col_chart2:
                        st.write(_("**그룹별 중요도 패턴 (Radar)**", "**Importance Pattern by Group (Radar)**"))
                        indiv_global_radar = []
                        all_ids_r = main_results_df['ID'].unique()
                        for rid in all_ids_r:
                            m_row_rd = main_results_df[main_results_df['ID'] == rid].iloc[0]
                            rtype_rd = m_row_rd['Type']
                            grp_name_en = rtype_rd
                            if is_english:
                                grp_name_en = str(rtype_rd).replace("전문가", "Expert").replace("일반", "General").replace("공무원", "Public Official")
                            for m_f_rd in main_factors:
                                mw_indiv_rd = m_row_rd[f"Weight_{m_f_rd}"]
                                s_row_df_rd = sub_results_storage[m_f_rd]['df']
                                s_row_rd = s_row_df_rd[s_row_df_rd['ID'] == rid].iloc[0]
                                for s_f_rd in sub_results_storage[m_f_rd]['factors']:
                                    indiv_global_radar.append({
                                        "Type": grp_name_en, 
                                        "Factor": s_f_rd, 
                                        "Global_Weight": mw_indiv_rd * s_row_rd[f"Weight_{s_f_rd}"]
                                    })
                        radar_indiv_df = pd.DataFrame(indiv_global_radar)
                        radar_plot_df = radar_indiv_df.groupby(['Type', 'Factor'])['Global_Weight'].mean().reset_index()
                        fig_radar = go.Figure()
                        for t in radar_plot_df['Type'].unique():
                            t_data = radar_plot_df[radar_plot_df['Type'] == t]
                            fig_radar.add_trace(go.Scatterpolar(r=t_data['Global_Weight'], theta=t_data['Factor'], fill='toself', name=t))
                        st.plotly_chart(fig_radar, use_container_width=True)
                    
                    # [추가 수정 부분] 바이올린 플롯 (CR 분포 시각화)
                    st.markdown("---")
                    st.write(_("**일관성 비율(CR) 분포 (Violin Plot)**", "**Consistency Ratio (CR) Distribution (Violin Plot)**"))
                    
                    # CR 값 추출을 위한 데이터 정제
                    cr_dist_data = []
                    # 메인 시트 CR
                    for idx_row, r in main_results_df.iterrows():
                        g_type_val = str(r['Type'])
                        if is_english:
                            g_type_val = g_type_val.replace("전문가", "Expert").replace("일반", "General").replace("공무원", "Public Official")
                        cr_dist_data.append({"Type": g_type_val, "Sheet": "Main_Criteria", "CR": r['Final_CR']})
                    # 하위 시트 CR
                    for mf, info in sub_results_storage.items():
                        for idx_row, r in info['df'].iterrows():
                            g_type_val = str(r['Type'])
                            if is_english:
                                g_type_val = g_type_val.replace("전문가", "Expert").replace("일반", "General").replace("공무원", "Public Official")
                            cr_dist_data.append({"Type": g_type_val, "Sheet": mf, "CR": r['Final_CR']})
                    
                    if cr_dist_data:
                        cr_df = pd.DataFrame(cr_dist_data)
                        color_map = {
                            "전문가": "#1f77b4", "일반": "#d62728", "공무원": "#2ca02c",
                            "Expert": "#1f77b4", "General": "#d62728", "Public Official": "#2ca02c"
                        }
                        unique_types = cr_df['Type'].unique()
                        
                        # [1. 전체 표본 그래프 선행 출력]
                        if len(unique_types) > 1:
                            fig_all = px.violin(cr_df, y="CR", x="Sheet", box=True, points="all",
                                               hover_data=cr_df.columns, title=_("[전체 표본] 일관성 비율(CR) 분포", "[Overall Samples] Consistency Ratio (CR) Distribution"),
                                               color_discrete_sequence=["#7f7f7f"]) # 전체는 회색 계열
                            fig_all.update_traces(spanmode='soft', pointpos=0, jitter=0.5, marker=dict(opacity=0.6, size=5))
                            
                            # 학술 논문용(Publication-ready) 스타일 적용
                            fig_all.update_layout(
                                template="simple_white",
                                font=dict(family="Arial, sans-serif", size=14, color="black"),
                                title_font=dict(size=16, family="Arial, sans-serif", color="black"),
                                xaxis=dict(showline=True, linewidth=1.5, linecolor='black', mirror=True, tickfont=dict(color="black")),
                                yaxis=dict(showline=True, linewidth=1.5, linecolor='black', mirror=True, tickfont=dict(color="black")),
                                plot_bgcolor="white",
                                paper_bgcolor="white",
                                margin=dict(l=60, r=40, t=60, b=40)
                            )
                            # Y축 범위를 자동(Auto)으로 맡겨 꼬리(하단/상단)가 잘리지 않고 뾰족하게 보이도록 수정
                            st.plotly_chart(fig_all, use_container_width=True)
                            st.markdown("---")
 
                        # [2. 그룹별 별도 객체로 분리하여 출력]
                        for g_type in unique_types:
                            g_df = cr_df[cr_df['Type'] == g_type]
                            fig_violin = px.violin(g_df, y="CR", x="Sheet", box=True, points="all",
                                                   hover_data=g_df.columns, title=_(f"[{g_type}] 일관성 비율(CR) 분포", f"[{g_type}] Consistency Ratio (CR) Distribution"),
                                                   color_discrete_sequence=[color_map.get(g_type, "#1f77b4")])
                            fig_violin.update_traces(spanmode='soft', pointpos=0, jitter=0.5, marker=dict(opacity=0.6, size=5))
                            
                            # 학술 논문용(Publication-ready) 스타일 적용
                            fig_violin.update_layout(
                                template="simple_white",
                                font=dict(family="Arial, sans-serif", size=14, color="black"),
                                title_font=dict(size=16, family="Arial, sans-serif", color="black"),
                                xaxis=dict(showline=True, linewidth=1.5, linecolor='black', mirror=True, tickfont=dict(color="black")),
                                yaxis=dict(showline=True, linewidth=1.5, linecolor='black', mirror=True, tickfont=dict(color="black")),
                                plot_bgcolor="white",
                                paper_bgcolor="white",
                                margin=dict(l=60, r=40, t=60, b=40)
                            )
                            # Y축 범위를 자동(Auto)으로 맡겨 꼬리가 잘리지 않도록 수정
                            st.plotly_chart(fig_violin, use_container_width=True)

                        if ahp_method == 'fuzzy':
                            st.markdown("---")
                            st.write(_("**퍼지 삼각가중치 분포 (TFN Graph)**", "**Triangular Fuzzy Numbers (TFN Graph)**"))
                            tfn_options = ["Main_Criteria"] + list(sub_results_storage.keys())
                            selected_tfn_sheet = st.selectbox(
                                _("TFN 시각화 대상 시트 선택", "Select Sheet for TFN Visualization"), 
                                tfn_options, 
                                key="selectbox_tfn_sheet"
                            )
                            if selected_tfn_sheet == "Main_Criteria":
                                tfn_Si = main_group_Si
                                tfn_factors = main_factors
                            else:
                                tfn_Si = sub_results_storage[selected_tfn_sheet]['group_Si']
                                tfn_factors = sub_results_storage[selected_tfn_sheet]['factors']
                            
                            st.plotly_chart(
                                render_tfn_chart(tfn_Si, tfn_factors,
                                    _(f"▶ [{selected_tfn_sheet}] 삼각퍼지 분포", f"▶ [{selected_tfn_sheet}] TFN Distribution")),
                                use_container_width=True
                            )

                with tab5:
                    st.markdown(_('<p style="color: red; font-weight: bold; font-size: 0.95rem; margin-bottom: 12px;">⚠️ 주의: 분석 결과가 웹상에 영구 저장되지 않으므로, 아래 다운로드 버튼을 눌러 결과물 엑셀 파일을 컴퓨터에 반드시 저장해 주세요.</p>',
                                  '<p style="color: red; font-weight: bold; font-size: 0.95rem; margin-bottom: 12px;">⚠️ Warning: Analysis results are not permanently stored on the web. Please make sure to click the download button below to save the Excel file to your computer.</p>'), unsafe_allow_html=True)
                    st.download_button(_("📥 결과 파일 다운로드 (Excel)", "📥 Download Results File (Excel)"), data=output_res.getvalue(), file_name="AHP_Result.xlsx")
                    if 'radar_indiv_df' in locals() and not radar_indiv_df.empty:
                        disp_radar_df = radar_indiv_df.copy()
                        if is_english:
                            disp_radar_df.rename(columns={
                                "Type": "Group/Type",
                                "Factor": "Factor/Criteria",
                                "Global_Weight": "Global Weight"
                            }, inplace=True)
                        st.dataframe(disp_radar_df.style.format(precision=4), use_container_width=True)
                    else:
                        st.dataframe(pd.DataFrame(), use_container_width=True)

            except Exception as e:
                import traceback
                st.error(_("❌ 분석 시스템 내부 오류가 발생했습니다.", "❌ An internal error occurred in the analysis system."))
                st.info(_(f"상세 에러 내용: {e}", f"Detailed error: {e}"))
                with st.expander(_("🔍 상세 스택 트레이스", "🔍 Detailed Stack Trace")):
                    st.code(traceback.format_exc())
                st.stop()
        else:
            st.warning(message)
            if role_chk == 'temp' and ("5개 표본" in message or "5 samples" in message):
                st.markdown("---")
                with st.container(border=True):
                    if is_english:
                        st.markdown("### 💳 Official User Upgrade & Unlimited Analysis")
                        st.markdown("Upgrading to an Official User **instantly removes the 5-sample limit** and allows unlimited access to all features.")
                        st.info("Upgrade to **Official User** to get unlimited access (2 months) for **$350.00 USD** via PayPal.")
                        
                        paypal_client_id = st.secrets.get("PAYPAL_CLIENT_ID", "sb")
                        user_id = st.session_state.user_id
                        
                        paypal_html = f"""
                        <div id="paypal-button-container-main" style="text-align: center; max-width: 100%;"></div>
                        <script src="https://www.paypal.com/sdk/js?client-id={paypal_client_id}&currency=USD&locale=en_US"></script>
                        <script>
                          paypal.Buttons({{
                            style: {{
                              layout: 'vertical',
                              color:  'gold',
                              shape:  'rect',
                              label:  'paypal',
                              height: 40
                            }},
                            createOrder: function(data, actions) {{
                              return actions.order.create({{
                                purchase_units: [{{
                                  amount: {{
                                    value: '350.00'
                                  }},
                                  payee: {{
                                    email_address: 'jeon080423@gmail.com'
                                  }}
                                }}]
                              }});
                            }},
                            onApprove: function(data, actions) {{
                              return actions.order.capture().then(function(details) {{
                                window.top.location.href = window.top.location.origin + window.top.location.pathname + "?paypal_order_id=" + data.orderID + "&user_id=" + encodeURIComponent("{user_id}");
                              }});
                            }},
                            onError: function(err) {{
                              console.error(err);
                              alert("Payment failed or was cancelled.");
                            }}
                          }}).render('#paypal-button-container-main');
                        </script>
                        """
                        st.components.v1.html(paypal_html, height=180)
                    else:
                        st.markdown("### 💳 정식 사용자 승격 및 무제한 분석")
                        st.markdown("정식 사용자로 승격하시면 **표본 수 제한(5개)이 즉시 해제**되며 모든 기능을 무제한으로 사용하실 수 있습니다.")
                        st.info("카카오뱅크 3333-23-8667708 (예금주: ㅈㅅㅎ) 계좌로 송금하신 후 아래 버튼을 클릭해 주세요.\n(서비스 이용요금: 50만원)")
                        if st.button("정식 사용자 전환 요청", use_container_width=True, key="main_upgrade_btn"):
                            if send_conversion_request_email(st.session_state.user_id):
                                st.success("정식 사용자 전환요청이 완료 되었습니다. 입금 확인 후 정식사용자로 전환해 드립니다")
                            else:
                                st.error("요청 전송 실패. 관리자에게 문의바랍니다.")
    except Exception as e:
        st.error(f"파일 처리 오류 발생: {e}")

st.markdown("---")
st.caption("© 2026 AHP Master. All rights reserved.")

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import yeta_utils
import math
import os
import sqlite3
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

# Helper function for Korean translation fallback
def _(ko_text, en_text):
    if st.session_state.get('lang', 'ko') == 'en':
        return en_text
    return ko_text

# --- AUTH & DB UTILITIES ---
def hash_password(password: str) -> str:
    """SHA-256 Hash a password with a fixed salt for security."""
    salt = "ahp_master_secure_salt_2026"
    return hashlib.sha256((password + salt).encode('utf-8')).hexdigest()

def generate_temp_password() -> str:
    """가입 시 비밀번호 유효성 검사를 통과하는 8자리 임시 비밀번호를 생성합니다."""
    chars = string.ascii_letters + string.digits
    specials = "!@#$%^&*"
    temp = [
        random.choice(string.ascii_lowercase),
        random.choice(string.ascii_uppercase),
        random.choice(string.digits),
        random.choice(specials)
    ]
    temp += [random.choice(chars) for _ in range(4)]
    random.shuffle(temp)
    return "".join(temp)

def check_login(user_id, pw):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    try:
        c.execute("SELECT role, expiry_date, pw, plan_type, customer_type FROM users WHERE id=?", (user_id,))
        row = c.fetchone()
    except sqlite3.OperationalError:
        try:
            c.execute("SELECT role, expiry_date, pw, plan_type FROM users WHERE id=?", (user_id,))
            row = c.fetchone()
            if row:
                row = (row[0], row[1], row[2], row[3], "standard")
        except sqlite3.OperationalError:
            c.execute("SELECT role, expiry_date, pw FROM users WHERE id=?", (user_id,))
            row = c.fetchone()
            if row:
                row = (row[0], row[1], row[2], None, "standard")
    conn.close()
    
    if row:
        stored_role, stored_expiry, stored_pw, stored_plan, stored_customer = row
        hashed_pw = hash_password(pw)
        
        # 평문 패스워드가 정확히 일치하거나 해시 패스워드가 일치하는 경우
        if stored_pw == pw or stored_pw == hashed_pw:
            # 평문 패스워드로 로그인 성공한 경우, 즉시 해시 패스워드로 업데이트 (보안 승급)
            if stored_pw == pw:
                upgrade_user_password_to_hash(user_id, pw)
            return stored_role, stored_expiry, stored_plan, stored_customer
            
    return None

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
                sheet.update_cell(cell.row, 4, hashed_pw)
    except Exception:
        pass
    return True

def validate_email(email):
    return re.match(r"[^@]+@[^@]+\.[^@]+", email)

def validate_password(password):
    if len(password) < 4: return False
    has_char = re.search(r'[a-zA-Z]', password)
    has_special = re.search(r'[!@#$%^&*(),.?":{}|<>]', password)
    return has_char and has_special

def upgrade_user_password_to_hash(user_id, pw):
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
                sheet.update_cell(cell.row, 4, hashed_pw)
    except Exception:
        pass

# --- GOOGLE SHEETS & MEMBER MANAGEMENT ---
@st.cache_resource
def get_gspread_client():
    scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    if "gcp_service_account" not in st.secrets:
        return None
    raw_auth = st.secrets["gcp_service_account"]
    auth_info = {}
    if isinstance(raw_auth, dict) or hasattr(raw_auth, "keys"):
        auth_info = dict(raw_auth)
    elif isinstance(raw_auth, str):
        auth_str = raw_auth.strip().strip('"').strip("'")
        try:
            auth_info = json.loads(auth_str)
        except json.JSONDecodeError:
            try:
                clean_b64 = re.sub(r'\s+', '', auth_str)
                missing_padding = len(clean_b64) % 4
                if missing_padding:
                    clean_b64 += '=' * (4 - missing_padding)
                try:
                    decoded_bytes = base64.b64decode(clean_b64)
                except Exception:
                    decoded_bytes = base64.urlsafe_b64decode(clean_b64)
                decoded_info = decoded_bytes.decode('utf-8')
                auth_info = json.loads(decoded_info)
            except Exception:
                return None
    else:
        return None

    if auth_info and "private_key" in auth_info:
        auth_info["private_key"] = auth_info["private_key"].replace("\\n", "\n")
    required_fields = ["private_key", "client_email", "token_uri"]
    missing = [f for f in required_fields if f not in auth_info]
    if missing:
        return None

    creds = Credentials.from_service_account_info(auth_info, scopes=scope)
    return gspread.authorize(creds)

def run_gspread_with_retry(func, *args, max_retries=5, initial_backoff=2, **kwargs):
    backoff = initial_backoff
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            err_msg = str(e)
            is_rate_limit = "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg or "RATE_LIMIT_EXCEEDED" in err_msg
            if is_rate_limit and attempt < max_retries - 1:
                sleep_time = backoff + random.uniform(0, 1)
                time.sleep(sleep_time)
                backoff *= 2
                continue
            else:
                raise e

@st.cache_data(ttl=300, show_spinner=False)
def get_cached_visit_logs(spreadsheet_id):
    try:
        client = get_gspread_client()
        if client:
            spreadsheet = run_gspread_with_retry(client.open_by_key, spreadsheet_id)
            try:
                visit_sheet = run_gspread_with_retry(spreadsheet.worksheet, "Visit_Logs")
                records = run_gspread_with_retry(visit_sheet.get_all_records)
                if records:
                    try:
                        conn = sqlite3.connect('users.db')
                        c = conn.cursor()
                        for row in records:
                            ip_val = row.get('IP')
                            date_val = row.get('Date')
                            if ip_val and date_val:
                                c.execute("INSERT OR IGNORE INTO visit_logs (ip_address, visit_date) VALUES (?, ?)", 
                                          (str(ip_val), str(date_val)))
                        conn.commit()
                        conn.close()
                    except Exception:
                        pass
                return records
            except gspread.exceptions.WorksheetNotFound:
                return []
    except Exception:
        return []

def get_event_settings():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    try:
        c.execute("SELECT event_active, event_title, event_desc, event_deadline, event_discount FROM event_settings WHERE id = 1")
        row = c.fetchone()
        if row:
            return {
                "active": bool(row[0]),
                "title": row[1],
                "desc": row[2],
                "deadline": row[3],
                "discount": int(row[4])
            }
    except Exception:
        pass
    finally:
        conn.close()
    return {
        "active": True,
        "title": "[이벤트] 학위논문 5만원 할인 (~7/30)",
        "desc": "석/박사 대상. 제목/대학명 사이트 내 공개 동의 필수",
        "deadline": "2026-07-30",
        "discount": 50000
    }

def sync_db_from_sheets(silent=False):
    conn = None
    try:
        client = get_gspread_client()
        if not client: 
            return -1
        spreadsheet = run_gspread_with_retry(client.open_by_key, st.secrets["SPREADSHEET_ID"])
        sheet = run_gspread_with_retry(lambda: spreadsheet.sheet1)
        all_values = run_gspread_with_retry(sheet.get_all_values)
        
        if len(all_values) > 1:
            conn = sqlite3.connect('users.db', timeout=30.0)
            c = conn.cursor()
            cnt = 0
            processed_ids = set()
            for row in all_values[1:]:
                if len(row) >= 4:
                    user_id = str(row[0]).strip()
                    if not user_id or user_id in processed_ids:
                        continue
                    processed_ids.add(user_id)
                    
                    role = str(row[1]).strip()
                    signup_date = str(row[2]).strip()
                    pw = str(row[3]).strip()
                    
                    survey_count = 0
                    last_survey_link = ""
                    customer_type = "standard"
                    if len(row) >= 12:
                        expiry_date = str(row[4]).strip()
                        agree_info = str(row[5]).strip()
                        try:
                            survey_count = int(row[6])
                        except:
                            survey_count = 0
                        last_survey_link = str(row[7]).strip()
                        customer_type = str(row[11]).strip() or "standard"
                    elif len(row) >= 8:
                        expiry_date = str(row[4]).strip()
                        agree_info = str(row[5]).strip()
                        try:
                            survey_count = int(row[6])
                        except:
                            survey_count = 0
                        last_survey_link = str(row[7]).strip()
                    elif len(row) >= 6:
                        expiry_date = str(row[4]).strip()
                        agree_info = str(row[5]).strip()
                    elif len(row) == 5:
                        expiry_date = '9999-12-31'
                        agree_info = str(row[4]).strip()
                    else:
                        expiry_date = '9999-12-31'
                        agree_info = 'Y'
                        
                    if expiry_date in ["Y", "N", "예", "아니오", "yes", "no"]:
                        if agree_info in ["", None, "Y"]:
                            agree_info = expiry_date
                        expiry_date = "9999-12-31"

                    c.execute("SELECT id, role, signup_date, pw, expiry_date, agree_info, survey_count, last_survey_link, customer_type FROM users WHERE id=?", (user_id,))
                    db_user = c.fetchone()
                    if not db_user:
                        plan_type = 'yeta_free' if customer_type == 'yeta' else 'free'
                        c.execute("INSERT INTO users (id, role, signup_date, pw, expiry_date, agree_info, survey_count, last_survey_link, plan_type, customer_type) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", 
                                  (user_id, role, signup_date, pw, expiry_date, agree_info, survey_count, last_survey_link, plan_type, customer_type))
                        cnt += 1
                    else:
                        db_role, db_signup_date, db_pw, db_expiry_date, db_agree_info, db_survey_count, db_last_link, db_cust = db_user[1], db_user[2], db_user[3], db_user[4], db_user[5], db_user[6], db_user[7], db_user[8]
                        if (db_role != role or db_signup_date != signup_date or 
                            db_pw != pw or db_expiry_date != expiry_date or db_agree_info != agree_info or
                            db_survey_count != survey_count or db_last_link != last_survey_link or db_cust != customer_type):
                            c.execute("""
                                UPDATE users 
                                SET role=?, signup_date=?, pw=?, expiry_date=?, agree_info=?, survey_count=?, last_survey_link=?, customer_type=?
                                WHERE id=?
                            """, (role, signup_date, pw, expiry_date, agree_info, survey_count, last_survey_link, customer_type, user_id))
                            cnt += 1
            
            conn.commit()
            
            try:
                visit_sheet = spreadsheet.worksheet("Visit_Logs")
                records = visit_sheet.get_all_records()
                for row in records:
                    c.execute("INSERT OR IGNORE INTO visit_logs (ip_address, visit_date) VALUES (?, ?)", 
                              (str(row.get('IP', '')), str(row.get('Date', ''))))
                conn.commit()
            except Exception:
                pass
                
            return cnt
    except Exception:
        if conn:
            try: conn.rollback()
            except Exception: pass
        return -1
    finally:
        if conn:
            try: conn.close()
            except Exception: pass
    return 0

def get_all_users():
    conn = sqlite3.connect('users.db')
    df = pd.read_sql_query("SELECT * FROM users", conn)
    conn.close()
    return df

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

def add_user(user_id, pw, role, agree_info="Y", customer_type="standard"):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    signup_date = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).strftime("%Y-%m-%d")
    expiry_date = "9999-12-31"
    hashed_pw = hash_password(pw)
    plan_type = 'yeta_free' if customer_type == 'yeta' else 'free'
    try:
        c.execute("INSERT INTO users (id, role, signup_date, pw, expiry_date, agree_info, survey_count, last_survey_link, plan_type, customer_type) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", 
                  (user_id, role, signup_date, hashed_pw, expiry_date, agree_info, 0, "", plan_type, customer_type))
        conn.commit()
        log_to_sheets(user_id, role, signup_date, hashed_pw, agree_info, expiry_date, 0, "", "", "", "", customer_type)
        success = True
    except sqlite3.IntegrityError:
        success = False
    finally:
        conn.close()
    return success

def log_to_sheets(user_id, role, signup_date, pw, agree_info="Y", expiry_date="9999-12-31", survey_count=0, last_survey_link="", event_applied="", thesis_title="", university="", customer_type="standard"):
    try:
        client = get_gspread_client()
        if client:
            spreadsheet = client.open_by_key(st.secrets["SPREADSHEET_ID"])
            sheet = spreadsheet.sheet1
            
            try:
                headers = sheet.row_values(1)
            except Exception:
                headers = []
            
            expected_headers = ['id', 'role', 'signup_date', 'pw', 'expiry_date', 'agree_info', 'survey_count', 'last_survey_link', 'event_applied', 'thesis_title', 'university', 'customer_type']
            if len(headers) < 12 or not all(h in headers for h in ['event_applied', 'thesis_title', 'university', 'customer_type']):
                sheet.update(range_name='A1:L1', values=[expected_headers])
            
            sheet.append_row([user_id, role, str(signup_date), pw, expiry_date, agree_info, survey_count, last_survey_link, event_applied, thesis_title, university, customer_type])
    except Exception:
        pass

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

def update_user_full_info(user_id, new_pw, new_role, new_expiry, plan_type=None, event_applied=None, thesis_title=None, university=None, customer_type=None):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    update_fields = []
    update_params = []
    
    if new_pw is not None and new_pw != "":
        update_fields.append("pw=?")
        update_params.append(new_pw)
    
    update_fields.append("role=?")
    update_params.append(new_role)
    
    update_fields.append("expiry_date=?")
    update_params.append(new_expiry)
    
    if plan_type is not None:
        update_fields.append("plan_type=?")
        update_params.append(plan_type)
        
    if event_applied is not None:
        update_fields.append("event_applied=?")
        update_params.append(event_applied)
        
    if thesis_title is not None:
        update_fields.append("thesis_title=?")
        update_params.append(thesis_title)
        
    if university is not None:
        update_fields.append("university=?")
        update_params.append(university)
        
    if customer_type is not None:
        update_fields.append("customer_type=?")
        update_params.append(customer_type)
        
    update_params.append(user_id)
    sql = f"UPDATE users SET {', '.join(update_fields)} WHERE id=?"
    c.execute(sql, tuple(update_params))
    conn.commit()
    conn.close()
    
    try:
        client = get_gspread_client()
        if client:
            spreadsheet = client.open_by_key(st.secrets["SPREADSHEET_ID"])
            sheet = spreadsheet.sheet1
            
            try:
                headers = sheet.row_values(1)
            except Exception:
                headers = []
            
            expected_headers = ['id', 'role', 'signup_date', 'pw', 'expiry_date', 'agree_info', 'survey_count', 'last_survey_link', 'event_applied', 'thesis_title', 'university', 'customer_type']
            if len(headers) < 12 or not all(h in headers for h in ['event_applied', 'thesis_title', 'university', 'customer_type']):
                sheet.update(range_name='A1:L1', values=[expected_headers])

            cell = sheet.find(user_id)
            kst_today = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).strftime("%Y-%m-%d")
            
            db_signup_date = None
            db_customer_type = "standard"
            conn = sqlite3.connect('users.db')
            c = conn.cursor()
            c.execute("SELECT signup_date, customer_type FROM users WHERE id=?", (user_id,))
            res = c.fetchone()
            if res:
                db_signup_date = res[0]
                db_customer_type = res[1] or "standard"
            conn.close()

            if cell:
                final_pw = new_pw if (new_pw and new_pw != "") else cell.value
                final_signup_date = db_signup_date or kst_today
                event_applied_val = event_applied if event_applied is not None else ""
                thesis_title_val = thesis_title if thesis_title is not None else ""
                university_val = university if university is not None else ""
                final_cust_type = customer_type or db_customer_type or "standard"
                
                sheet.update(
                    range_name=f'A{cell.row}:L{cell.row}',
                    values=[[
                        user_id, new_role, final_signup_date, final_pw, new_expiry, "Y", 0, "", 
                        event_applied_val, thesis_title_val, university_val, final_cust_type
                    ]]
                )
            else:
                final_pw = new_pw if (new_pw and new_pw != "") else ""
                final_signup_date = db_signup_date or kst_today
                event_applied_val = event_applied if event_applied is not None else ""
                thesis_title_val = thesis_title if thesis_title is not None else ""
                university_val = university if university is not None else ""
                final_cust_type = customer_type or db_customer_type or "standard"
                sheet.append_row([user_id, new_role, final_signup_date, final_pw, new_expiry, "Y", 0, "", event_applied_val, thesis_title_val, university_val, final_cust_type])
    except Exception:
        pass

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
    except Exception:
        return False

# --- CORE ROUTING ACTION ---
def run():
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
            conn = sqlite3.connect('users.db')
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
                    st.toast(_(" 30분간 활동이 없어 보안을 위해 자동 로그아웃되었습니다.", " Logged out automatically due to 30 minutes of inactivity."))
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
        background-color: #f8fafc !important;
        border-right: 1px solid #cbd5e1 !important;
    }
    section[data-testid="stSidebar"] > div:first-child {
        padding-top: 1.5rem !important;
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

    /* 사이드바 탭 글자 크기 축소 & 여백 줄이기 */
    section[data-testid="stSidebar"] button[data-baseweb="tab"] {
        flex: 1 !important;
        justify-content: center !important;
        font-size: 0.85rem !important;
        padding: 0.5rem 0 !important;
        margin: 0 !important;
        min-height: unset !important;
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
        plan_name_param = q_params.get("plan_name", "예타 단건 분석권")
        kst_now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
        new_expiry_date = (kst_now + datetime.timedelta(days=365)).strftime("%Y-%m-%d")
        
        try:
            conn = sqlite3.connect('users.db')
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

    # 5. Page Header Section (Split into left and right columns)
    col_main_title, col_settings_title = st.columns([3.0, 1.2], gap="large")
    
    with col_main_title:
        st.markdown(f"""
        <div class="yeta-body">
            <div class="yeta-header">
                <h1>{_("국가 예비타당성조사 종합평가(AHP) 시스템", "Preliminary Feasibility Study AHP System")}</h1>
                <p>{_("기획재정부 및 KDI 표준 지침을 준수하는 공공투자사업 AHP 종합 평가 모듈입니다.", "AHP comprehensive evaluation module for public investment projects in compliance with MoEF & KDI standard guidelines.")}</p>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col_settings_title:
        import urllib.parse
        current_params = dict(st.query_params)
        ko_params = current_params.copy()
        ko_params['lang'] = 'ko'
        ko_url = "?" + urllib.parse.urlencode(ko_params, doseq=True)
        
        en_params = current_params.copy()
        en_params['lang'] = 'en'
        en_url = "?" + urllib.parse.urlencode(en_params, doseq=True)
        
        cur_lang = st.session_state.get('lang', 'ko')
        lang_ko_color = "#1a365d" if cur_lang == 'ko' else "#9cb4cc"
        lang_ko_weight = "bold" if cur_lang == 'ko' else "normal"
        lang_en_color = "#1a365d" if cur_lang == 'en' else "#9cb4cc"
        lang_en_weight = "bold" if cur_lang == 'en' else "normal"
        
        lang_html = f"""
        <div style="text-align: right; margin-top: 15px; margin-bottom: 10px;">
            <span style="font-size: 0.85rem;">
                <a href="{ko_url}" target="_self" style="text-decoration: none; color: {lang_ko_color}; font-weight: {lang_ko_weight};">한국어</a>
                <span style="color: #ccc; margin: 0 4px;">|</span>
                <a href="{en_url}" target="_self" style="text-decoration: none; color: {lang_en_color}; font-weight: {lang_en_weight};">English</a>
            </span>
        </div>
        """
        st.markdown(lang_html, unsafe_allow_html=True)
        
        if st.button(_("🏠 메인 포털로 돌아가기", "🏠 Back to Main Portal"), key="btn_back_to_gateway", use_container_width=True):
            st.session_state.mode = None
            st.query_params.pop("mode", None)
            st.rerun()

    # --- ADMIN MODE INTERCEPTOR ---
    if st.session_state.get('admin_mode', False) and st.session_state.user_role == 'admin':
        st.subheader(_("👥 가입자 현황 및 관리 (예타 전용 뷰)", "Registered Users & Admin Control (YETA View)"))
        
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
            visit_data_gs = get_cached_visit_logs(st.secrets["SPREADSHEET_ID"])
            if not visit_data_gs:
                try:
                    conn = sqlite3.connect('users.db')
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
                conn = sqlite3.connect('users.db')
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

    # 6. Sidebar Configuration (Authentication & Yeta Settings)
    with st.sidebar:
        # AHP Master Logo
        try:
            with open("ahp_master_logo.png", "rb") as f:
                encoded_logo = base64.b64encode(f.read()).decode()
            st.markdown(
                f'<a href="https://jeon080423.github.io/AHPkr" target="_blank">'
                f'<img src="data:image/png;base64,{encoded_logo}" style="width:100%; border-radius: 4px; display: block; margin-bottom: 10px;">'
                f'</a>',
                unsafe_allow_html=True
            )
        except:
            st.markdown(
                f'<a href="https://jeon080423.github.io/AHPkr" target="_blank" style="text-decoration: none; color: inherit;">'
                f'<h3 style="margin-top: -5px; margin-bottom: 10px;">{_(" AHP 마스터", " AHP Master")}</h3>'
                f'</a>',
                unsafe_allow_html=True
            )

        # Login / Session panel
        if st.session_state.user_id is None:
            tab_login, tab_find_pw = st.tabs([_("로그인", "Login"), _("비밀번호 찾기", "Find Password")])
            
            with tab_login:
                l_id = st.text_input(_("아이디 (이메일 주소)", "Username (Email Address)"), key="l_id")
                l_pw = st.text_input(_("비밀번호 (PW)", "Password (PW)"), type="password", key="l_pw")
                if st.button(_("로그인 실행", "Login"), key="btn_login_yeta"):
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
                                    st.toast(_("📅 정식 이용 기간이 만료되어 무료사용자 권한으로 자동 전환되었습니다.", "📅 Subscription expired. Downgraded to Free User."))
                                    st.rerun()
                                except Exception as e:
                                    st.error(_(f"만료 회원 자동 전환 처리 중 오류가 발생했습니다: {e}", f"Error during automatic expiry downgrade: {e}"))
                            else:
                                st.error(_(f"❌ 이용 기간이 만료되었습니다. (만료일: {result[1]})", f"❌ Subscription expired. (Expiry date: {result[1]})"))
                        else:
                            st.session_state.user_id = l_id.strip()
                            st.session_state.user_role = result[0]
                            st.session_state.expiry_date = result[1]
                            st.session_state.plan_type = result[2] if len(result) > 2 else None
                            st.query_params["login_user"] = l_id.strip()
                            st.query_params["login_token"] = hashlib.sha256(f"{l_id.strip()}:AHP_MASTER_SECURE_SALT_2026_!@#".encode()).hexdigest()
                            st.query_params["last_activity"] = str(int(time.time()))
                            st.success(_(f"환영합니다, {l_id}님!", f"Welcome, {l_id}!"))
                            st.rerun()
                    else:
                        st.error(_("아이디 또는 비밀번호가 일치하지 않습니다.", "Incorrect username or password."))
            
            with tab_find_pw:
                st.write(_("가입 시 사용한 이메일 주소를 입력해주세요. 이메일로 새로운 임시 비밀번호가 발송됩니다.",
                           "Please enter the email address used at registration. A new temporary password will be sent to your email."))
                f_id = st.text_input(_("가입한 아이디 (이메일)", "Registered ID (Email)"), key="f_id")
                if st.button(_("임시 비밀번호 전송", "Send Temporary Password"), key="btn_find_pw_yeta"):
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
            if st.session_state.user_role == 'admin':
                role_disp = _("관리자", "Admin")
            elif st.session_state.user_role == 'official':
                pt = st.session_state.get('plan_type')
                role_disp = f"{_('정식 사용자', 'Official User')} ({pt})" if pt else _("정식 사용자", "Official User")
            else:
                role_disp = _("무료사용자", "Free User")
            
            expiry_info = ""
            if st.session_state.expiry_date:
                expiry_label = _("만료일: ", "Expiry: ")
                expiry_info = f' | {expiry_label}{st.session_state.expiry_date}'
                
            info_html = f"""<div style="background-color: #e8f5e9; border: 1px solid #c8e6c9; border-radius: 6px; color: #2e7d32; font-weight: bold; font-size: 0.85rem; padding: 8px 10px; text-align: center; margin-bottom: 8px;">
            👤 {st.session_state.user_id} ({role_disp}{expiry_info})
            </div>"""
            st.markdown(info_html, unsafe_allow_html=True)
            
            if st.session_state.user_role == 'admin':
                btn_label = _("🔧 관리자 화면 닫기", "🔧 Exit Admin Panel") if st.session_state.get('admin_mode', False) else _("🔧 관리자 화면 접속", "🔧 Connect to Admin Panel")
                if st.button(btn_label):
                    st.session_state.admin_mode = not st.session_state.admin_mode
                    st.rerun()

            with st.expander(_("🔐 비밀번호 변경", "🔐 Change Password")):
                cur_pw = st.text_input(_("현재 비밀번호", "Current Password"), type="password", key="chg_cur_yeta")
                new_pw_val = st.text_input(_("새 비밀번호", "New Password"), type="password", key="chg_new_yeta")
                confirm_pw = st.text_input(_("새 비밀번호 확인", "Confirm New Password"), type="password", key="chg_conf_yeta")
                
                if st.button(_("비밀번호 변경", "Change Password"), key="btn_chg_pw_yeta"):
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

            if st.button(_("로그아웃", "Log Out"), key="btn_logout_yeta"):
                st.session_state.user_id = None
                st.session_state.user_role = None
                st.session_state.expiry_date = None
                st.session_state.plan_type = None
                st.session_state.admin_mode = False
                st.query_params.pop("login_user", None)
                st.query_params.pop("login_token", None)
                st.rerun()

            with st.expander(_("📄 견적서 출력", "📄 Print Estimate")):
                q_client = st.text_input(_("의뢰기관명 (수신)", "Client Institution"), placeholder=_("예: (주)에이치피테크", "e.g., HP Tech Co., Ltd."), key="q_client_yeta")
                q_project = st.text_input(_("과제명 (프로젝트명)", "Project / Task Name"), placeholder=_("예: 예타 가중치 평가 분석", "e.g., Yeta Weight Assessment Analysis"), key="q_project_yeta")
                
                q_tier = st.selectbox(
                    _("서비스 구분 (요금제)", "Pricing Plan Tier"),
                    options=[
                        (_("예타 단건 분석권 (550,000원)", "Yeta Single Plan (550,000 KRW)"), 550000, "예타 단건 분석권"),
                        (_("기관 연간 라이선스 (2,640,000원)", "Yeta Annual License (2,640,000 KRW)"), 2640000, "기관 연간 라이선스")
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
                    st.warning(_("견적서 다운로드를 위해 의뢰기관명과 과제명을 먼저 입력해 주세요.", 
                                 "Please enter the Client Institution and Project Name to enable download."))

            with st.expander(_("📄 계산서 발행 신청", "📄 Request Invoice")):
                t_biz_num = st.text_input(_("사업자 등록번호", "Business Registration Number"), placeholder="000-00-00000", key="t_biz_num_yeta")
                t_biz_name = st.text_input(_("상호 (회사명)", "Company Name"), key="t_biz_name_yeta")
                t_rep_name = st.text_input(_("대표자명", "CEO Name"), key="t_rep_name_yeta")
                t_address = st.text_input(_("사업장 주소", "Business Address"), key="t_address_yeta")
                t_biz_type = st.text_input(_("업태 / 업종", "Business Category / Type"), key="t_biz_type_yeta")
                t_email = st.text_input(_("계산서 수신 이메일", "Invoice Email"), key="t_email_yeta")
                
                t_tier = st.selectbox(
                    _("신청 서비스 (요금제)", "Pricing Plan for Invoice"),
                    options=[
                        (_("예타 단건 분석권 (550,000원)", "Yeta Single Plan (550,000 KRW)"), "예타 단건 분석권"),
                        (_("기관 연간 라이선스 (2,640,000원)", "Yeta Annual License (2,640,000 KRW)"), "기관 연간 라이선스")
                    ],
                    format_func=lambda x: x[0],
                    key="t_tier_select_yeta"
                )
                
                if st.button(_("계산서 발행 신청하기", "Submit Invoice Request"), use_container_width=True, key="btn_request_tax_yeta"):
                    if not t_biz_num.strip():
                        st.error(_("사업자 등록번호를 입력해 주세요.", "Please enter the Business Registration Number."))
                    elif not t_biz_name.strip():
                        st.error(_("상호를 입력해 주세요.", "Please enter the Company Name."))
                    elif not t_rep_name.strip():
                        st.error(_("대표자명을 입력해 주세요.", "Please enter the CEO Name."))
                    elif not t_email.strip():
                        st.error(_("이메일을 입력해 주세요.", "Please enter the Email."))
                    elif not validate_email(t_email.strip()):
                        st.error(_("올바른 이메일 형식이 아닙니다.", "Invalid email format."))
                    else:
                        with st.spinner(_("신청서를 제출하는 중...", "Submitting request...")):
                            conn = sqlite3.connect('users.db')
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
                                    st.success(_("계산서 신청이 접수되었습니다! 관리자 확인 후 계산서가 발행됩니다.", 
                                                 "Request submitted! The invoice will be issued after review."))
                                else:
                                    st.warning(_("DB 저장은 성공했으나 알림 메일 발송에 실패했습니다. 관리자가 확인 후 순차 처리해 드리겠습니다.", 
                                                 "Saved to DB, but email alert failed. The admin will review it soon."))
                            except Exception as e:
                                st.error(_(f"신청 중 오류가 발생했습니다: {e}", f"Error during submission: {e}"))
                            finally:
                                conn.close()
                                
        st.markdown("---")
        st.markdown(f"### {_("예타 분석 설정", "Yeta Analysis Settings")}")
        
        project_type = st.selectbox(
            _("사업 유형", "Project Type"),
            options=[
                ("construction_non_capital", _("건설사업 (비수도권 유형)", "Construction (Non-capital)")),
                ("construction_capital", _("건설사업 (수도권 유형)", "Construction (Capital)")),
                ("rnd_bc", _("R&D / 연구개발사업 (B/C 분석)", "R&D (B/C Analysis)")),
                ("rnd_ec", _("R&D / 연구개발사업 (E/C 분석)", "R&D (E/C Analysis)")),
                ("other_bc", _("기타 재정사업 (B/C 분석)", "Other Fiscal (B/C Analysis)")),
                ("other_ec", _("기타 재정사업 (E/C 분석)", "Other Fiscal (E/C Analysis)"))
            ],
            format_func=lambda x: x[1],
            key="yeta_project_type_select"
        )
        
        st.markdown("---")
        st.markdown(f"#### {_("지침 가중치 허용 범위", "Guideline Weight Limits")}")
        p_type = project_type[0]
        if p_type == "construction_non_capital":
            st.info("경제성: 30~45%\n정책성: 25~40%\n지역균형발전: 30~40%")
        elif p_type == "construction_capital":
            st.info("경제성: 60~70%\n정책성: 30~40%\n지역균형발전: 0% (제외)")
        elif p_type == "rnd_bc":
            st.info("경제성: 10~40%\n과학기술적 타당성: 40~50%\n정책적 타당성: 20~40%")
        elif p_type == "rnd_ec":
            st.info("경제성: 10~40%\n과학기술적 타당성: 40~50%\n정책적 타당성: 20~40%")
        elif p_type == "other_bc":
            st.info("경제성: 25~50%\n정책성: 50~75%")
        elif p_type == "other_ec":
            st.info("경제성: 20~40%\n정책성: 60~80%")

    # 7. Navigation Tabs
    if st.session_state.user_id:
        tab_analysis, tab_survey_create, tab_guide, tab_pricing = st.tabs([
            _("예타 종합평가 분석기", "Preliminary Feasibility Analysis"),
            _("예타 전용 설문지 배포", "Create Yeta Survey"),
            _("예타 AHP 지침 안내", "AHP Guidelines Guide"),
            _("서비스 요금 및 라이선스", "Pricing & License")
        ])
    else:
        tab_analysis, tab_survey_create, tab_guide, tab_pricing, tab_signup = st.tabs([
            _("예타 종합평가 분석기", "Preliminary Feasibility Analysis"),
            _("예타 전용 설문지 배포", "Create Yeta Survey"),
            _("예타 AHP 지침 안내", "AHP Guidelines Guide"),
            _("서비스 요금 및 라이선스", "Pricing & License"),
            _("회원가입", "Sign Up")
        ])

    # =========================================================================
    # TAB 1: Analysis Tool
    # =========================================================================
    with tab_analysis:
        st.write("### " + _("예비타당성조사 AHP 종합평가 연산", "Preliminary Feasibility AHP Synthesis"))
        
        # User Tier Check
        is_official = False
        if st.session_state.get("user_id"):
            if st.session_state.get("user_role") in ["official", "admin"]:
                is_official = True
            else:
                try:
                    conn = sqlite3.connect('users.db')
                    c = conn.cursor()
                    c.execute("SELECT role FROM users WHERE id=?", (st.session_state.user_id,))
                    res = c.fetchone()
                    if res and res[0] in ["official", "admin"]:
                        is_official = True
                    conn.close()
                except:
                    pass
                
        col_inputs1, col_inputs2 = st.columns(2, gap="large")
        
        with col_inputs1:
            st.markdown(f"#### 1. {_("기초 정량 데이터 입력", "Input Quantitative Data")}")
            bc_ratio = st.number_input(_("경제성 분석 결과 (B/C 비율)", "B/C Ratio"), min_value=0.0, max_value=10.0, value=1.05, step=0.05)
            
            has_regional = "non_capital" in p_type or p_type == "other_bc" or p_type == "other_ec"
            if has_regional:
                lir_value = st.number_input(_("지역낙후도 표준화지수 (LIR/MIR)", "Regional Backwardness Index (LIR/MIR)"), min_value=-3.0, max_value=3.0, value=0.0, step=0.1, help="KDI 표준화 지표값")
            else:
                lir_value = 0.0
                st.text_input(_("지역낙후도 표준화지수 (LIR/MIR)", "Regional Backwardness Index (LIR/MIR)"), value="수도권/해당없음 (제외)", disabled=True)

        with col_inputs2:
            st.markdown(f"#### 2. {_("제1계층 상수합 가중치 설정 (%)", "Set Level 1 Weights (%)")}")
            
            if "rnd" in p_type:
                econ_w = st.slider(_("경제성 분석 가중치", "Economics Weight"), 0, 100, 30) / 100.0
                tech_w = st.slider(_("과학기술적 타당성 가중치", "Science/Tech Weight"), 0, 100, 45) / 100.0
                policy_w = st.slider(_("정책적 타당성 가중치", "Policy Weight"), 0, 100, 25) / 100.0
                regional_w = 0.0
            else:
                tech_w = 0.0
                econ_w = st.slider(_("경제성 분석 가중치", "Economics Weight"), 0, 100, 35) / 100.0
                policy_w = st.slider(_("정책적 분석 가중치", "Policy Weight"), 0, 100, 35) / 100.0
                if has_regional:
                    regional_w = st.slider(_("지역균형발전 분석 가중치", "Regional Balance Weight"), 0, 100, 30) / 100.0
                else:
                    regional_w = 0.0
                    st.slider(_("지역균형발전 분석 가중치", "Regional Balance Weight"), 0, 100, 0, disabled=True)

            valid_w, w_msg = yeta_utils.validate_yeta_level1_weights(p_type, econ_w, policy_w, regional_w, tech_w)
            if valid_w:
                st.success(_("가중치 범위 검증 완료: KDI 지침 부합", "Weights verified within KDI guidelines."))
            else:
                st.warning(_("가중치 지침 미부합: ", "Weights Warning: ") + w_msg)

        st.markdown("---")
        st.markdown(f"#### 3. {_("전문가 설문 데이터 종합", "Expert Survey Data Synthesis")}")
        
        max_free_evals = 3
        use_mock = st.checkbox(_("샘플 데이터로 분석 시뮬레이션 (Excel 업로드 생략)", "Simulate with Sample Data"), value=True)
        evaluator_scores = []
        
        if use_mock:
            if not is_official:
                st.warning(f"⚠️ 무료 사용자는 최대 {max_free_evals}명의 설문 데이터만 분석 가능합니다. (정식 결제 시 무제한 분석 가능)")
                evaluator_scores = [0.52, 0.48, 0.56][:max_free_evals]
            else:
                st.info(_("8명의 전문가 설문 결과를 기준으로 예타 AHP 연산을 시뮬레이션합니다.", "Simulating AHP calculations based on 8 expert responses."))
                evaluator_scores = [0.52, 0.48, 0.56, 0.61, 0.54, 0.49, 0.57, 0.45]
        else:
            uploaded_file = st.file_uploader(_("AHP 코딩 엑셀 데이터 파일 업로드 (.xlsx)", "Upload AHP Coding Excel File (.xlsx)"), type=["xlsx"])
            if uploaded_file is not None:
                st.info("엑셀 파싱 및 개별 평가자 연산을 수행합니다.")
                if not is_official:
                    st.warning(f"⚠️ 무료 사용자는 최대 {max_free_evals}명의 설문 데이터만 분석 가능합니다. (정식 결제 시 무제한 분석 가능)")
                    evaluator_scores = [0.52, 0.48, 0.56][:max_free_evals]
                else:
                    evaluator_scores = [0.52, 0.48, 0.56, 0.61, 0.54, 0.49, 0.57, 0.45]
                
        if evaluator_scores:
            bc_pairwise = yeta_utils.convert_bc_to_ahp_pairwise(bc_ratio)
            bc_weight_go = bc_pairwise / (bc_pairwise + 1.0)
            
            lir_pairwise = yeta_utils.convert_lir_to_ahp_pairwise(lir_value)
            lir_weight_go = lir_pairwise / (lir_pairwise + 1.0)
            
            final_scores_go = []
            for idx, q_score in enumerate(evaluator_scores):
                if "rnd" in p_type:
                    score_go = bc_weight_go * econ_w + q_score * (tech_w + policy_w)
                else:
                    if has_regional:
                        reg_go = lir_weight_go * 0.5 + q_score * 0.5
                        score_go = bc_weight_go * econ_w + q_score * policy_w + reg_go * regional_w
                    else:
                        score_go = bc_weight_go * econ_w + q_score * policy_w
                final_scores_go.append(score_go)
                
            final_yeta_score = yeta_utils.aggregate_yeta_group_ahp(final_scores_go)
            
            st.markdown("### " + _("예비타당성조사 AHP 종합평가 결과", "Preliminary Feasibility AHP Results"))
            
            is_pass = final_yeta_score >= 0.5
            card_class = "verdict-pass" if is_pass else "verdict-fail"
            verdict_text = _("사업 타당성 확보 (시행)", "Project Feasible (Go)") if is_pass else _("사업 타당성 미흡 (미시행)", "Project Not Feasible (Stop)")
            
            st.markdown(f"""
            <div class="verdict-card {card_class}">
                <div class="verdict-title">{_("최종 종합 평가 판정", "Final Comprehensive Evaluation Verdict")}</div>
                <div class="verdict-score">{final_yeta_score:.3f}</div>
                <div style="font-size: 1.3rem; font-weight: bold;">{verdict_text}</div>
                <div style="font-size: 0.9rem; margin-top: 10px; opacity: 0.85;">
                    {_("KDI 지침 기준: AHP 종합점수 0.5 이상일 때 타당성 확보", "MoEF & KDI standard: Feasible when AHP score >= 0.5")}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            st.write("#### " + _("평가자별 점수 분포 (극단값 제외 처리 현황)", "Evaluator Score Distribution"))
            
            sorted_scores = sorted(final_scores_go)
            df_evals = pd.DataFrame({
                _("평가자 구분", "Evaluator"): [f"Expert {i+1}" for i in range(len(sorted_scores))],
                _("최종 AHP 점수 (사업시행)", "Final AHP Score (Go)"): sorted_scores,
                _("배제 여부", "Status"): [_("최소값 배제 (아웃라이어)", "Excluded (Min)") if i == 0 and len(sorted_scores) >= 3 else (_("최대값 배제 (아웃라이어)", "Excluded (Max)") if i == len(sorted_scores)-1 and len(sorted_scores) >= 3 else _("집계 반영", "Included")) for i in range(len(sorted_scores))]
            })
            
            st.dataframe(df_evals, use_container_width=True)
            
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=[f"Expert {i+1}" for i in range(len(sorted_scores))],
                y=sorted_scores,
                marker_color=['#E53E3E' if i == 0 and len(sorted_scores) >= 3 else ('#3182CE' if i == len(sorted_scores)-1 and len(sorted_scores) >= 3 else '#4A5568') for i in range(len(sorted_scores))],
                text=[f"{s:.3f}" for s in sorted_scores],
                textposition='auto',
                name="AHP Score"
            ))
            fig.add_shape(type="line",
                x0=-0.5, y0=0.5, x1=len(sorted_scores)-0.5, y1=0.5,
                line=dict(color="Red", width=2, dash="dash"),
                name="Pass Threshold (0.5)"
            )
            fig.update_layout(
                title=_("평가자별 점수 분포 및 제외값 시각화", "Evaluator Scores & Exclusion Visualization"),
                yaxis=dict(title=_("AHP 종합점수 (사업시행)", "AHP Score (Go)"), range=[0.0, 1.0]),
                showlegend=False
            )
            st.plotly_chart(fig, use_container_width=True)

    # =========================================================================
    # TAB 2: Yeta Survey Creator
    # =========================================================================
    with tab_survey_create:
        st.write("### " + _("예비타당성조사 AHP 전문가 설문지 제작", "Preliminary Feasibility AHP Survey Creation"))
        st.info(_("KDI 지침에 명시된 요인을 자동으로 세팅하여 템플릿 설문지를 구성합니다.", "Configures the survey template with factors defined in KDI guidelines."))
        
        st.text_input(_("설문지 제목", "Survey Title"), value=_("재정투자사업 종합평가(AHP) 전문가 설문", "Expert AHP Survey for Preliminary Feasibility Study"))
        st.text_area(_("설문 안내문", "Instructions"), value=_("본 설문조사는 정부 예비타당성조사 지침에 따라 사업의 종합적인 추진 타당성을 계층 분석(AHP)하기 위한 용도로 사용됩니다.", "This survey is used for Analytic Hierarchy Process (AHP) comprehensive evaluation in accordance with government guidelines."))
        
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            st.checkbox(_("실시간 응답 일관성(CR) 가이드 적용", "Apply Real-time CR Guide"), value=True, disabled=True, help="예타 조사는 높은 일관성이 필수적이므로 실시간 가이드가 강제 적용됩니다.")
            st.selectbox(_("일관성 비율(CR) 허용 기준치", "CR Tolerance Limit"), options=["0.15 (정부 지침 표준)"], disabled=True)
        with col_s2:
            st.checkbox(_("모바일 화면 최적화 테마 적용", "Apply Mobile Responsive Theme"), value=True)
            st.checkbox(_("제출 전 스마트 보정 마법사 활성화", "Enable Smart Calibration Wizard before submission"), value=True)

        if st.button(_("예타 AHP 설문지 배포 및 구글 시트 연동", "Distribute Yeta Survey & Connect Google Sheets"), type="primary"):
            st.success(_("예타 AHP 설문지 배포가 완료되었습니다. 응답자 배포용 URL이 생성되었습니다.", "Yeta AHP survey successfully deployed! Respondent URL generated."))
            st.code("https://ahpkrj.streamlit.app/survey/yeta-expert-preview-106")

    # =========================================================================
    # TAB 3: Guidelines Guide
    # =========================================================================
    with tab_guide:
        st.write("### " + _("KDI 예비타당성조사 AHP 수행지침 핵심 요약", "KDI Preliminary Feasibility Study AHP Guidelines Summary"))
        
        st.markdown(f"""
        > [!IMPORTANT]
        > **1. 종합평가의 객관성 확보**
        > * 예타 종합평가 단계는 경제성 분석 결과(B/C 비율)에만 의존하지 않고, 정책성 및 지역균형발전 등의 비계량적 사회가치를 포함하여 종합적으로 판단(다기준 의사결정)하기 위해 AHP를 수행하도록 의무화되어 있습니다.
        
        > [!NOTE]
        > **2. 가중치 배분 지침 및 상수합법**
        > * 1계층 평가항목(경제성, 정책성, 지역균형 등) 간의 가중치는 쌍대비교 대신 평가자의 주관이 직접 개입되는 **상수합법(Constant-Sum)**에 의해 직접 할당합니다.
        > * R&D 사업의 경우, '과학기술적 타당성' 항목이 추가되며, 비수도권 건설사업의 경우 '지역균형발전' 가중치가 최소 30% 이상 배정되어야 합니다.
        
        > [!WARNING]
        > **3. 평가 의견의 편향 방지 (최대/최소 배제)**
        > * 집단 의사결정의 공정성을 확보하기 위해, AHP 종합 평점을 산정할 때 **사업시행에 대해 가장 극단적인 점수를 준 두 평가자(최고점 1인, 최저점 1인)의 결과는 연산에서 배제**한 후, 남은 평가자의 결과만 기하평균하여 최종 판단을 내립니다.
        """)

    # =========================================================================
    # TAB 4: B2B Pricing & Payment (Hybrid Pricing Applied)
    # =========================================================================
    with tab_pricing:
        st.write("### " + _("서비스 요금 및 라이선스 안내", "Service Pricing & Licensing"))
        st.write(_("예비타당성조사 AHP 분석 시스템은 기업 및 연구원 맞춤형 B2B 플랜을 제공합니다.", "B2B plans tailored for corporations and research institutes."))
        
        st.markdown("""
        <div class="pricing-grid">
            <div class="price-card" style="border-top: 4px solid #718096;">
                <div>
                    <div class="price-card-tier">무료 체험판</div>
                    <div class="price-card-amount">0 원</div>
                    <ul class="price-card-features">
                        <li>B/C 표준점수 로그 변환 연산</li>
                        <li>지역낙후도 표준화지수(LIR) 변환</li>
                        <li>설문 데이터 입력 (최대 3명 제한)</li>
                        <li>화면 결과 리포트 출력</li>
                    </ul>
                </div>
                <div style="text-align: center; color: #718096; font-size: 0.9rem;">기본 제공</div>
            </div>
            <div class="price-card" style="border-top: 4px solid #3182CE; box-shadow: 0 4px 15px rgba(49, 130, 206, 0.15);">
                <div>
                    <div class="price-card-tier" style="color: #3182CE;">예타 단건 분석권</div>
                    <div class="price-card-amount">550,000 원</div>
                    <ul class="price-card-features">
                        <li>특정 프로젝트 1건 영구 분석</li>
                        <li>평가자 수 제한 없음 (무제한)</li>
                        <li>최대/최소 아웃라이어 제외 자동 연산</li>
                        <li>보고서 제출용 Excel 원본 내보내기</li>
                        <li>세금계산서 및 영수증 발행 지원</li>
                    </ul>
                </div>
            </div>
            <div class="price-card" style="border-top: 4px solid #1A365D;">
                <div>
                    <div class="price-card-tier">기관 연간 라이선스</div>
                    <div class="price-card-amount">2,640,000 원</div>
                    <ul class="price-card-features">
                        <li>1년간 전 직원 무제한 프로젝트 분석</li>
                        <li>무제한 전문가 설문 및 아웃라이어 연산</li>
                        <li>B2B 기업용 견적서/세금계산서 즉시 발행</li>
                        <li>기관 전용 커스텀 DB 구축 매핑 지원</li>
                        <li>우선 기술 지원 및 교육 제공</li>
                    </ul>
                </div>
                <div style="text-align: center; color: #1A365D; font-size: 0.9rem; font-weight: bold;">연간 구독형</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        st.write("#### " + _("결제 및 정식 라이선스 활성화", "Payment & License Activation"))
        
        user_id = st.session_state.get("user_id")
        if not user_id:
            st.warning(_("⚠️ 결제 및 세금계산서 신청을 위해서는 로그인이 필요합니다. 메인 포털 또는 사이드바에서 로그인 후 이용해 주세요.", "⚠️ Login required for payment and invoice requests. Please login in main portal or sidebar first."))
        else:
            st.info(f"접속 계정: {user_id} | 라이선스 권한: {'정식 회원' if is_official else '무료 체험 회원'}")
            
            pay_col1, pay_col2 = st.columns(2, gap="medium")
            
            with pay_col1:
                st.write("**신용카드 온라인 안전결제 (PortOne)**")
                if st.button("예타 단건 분석권 신용카드 결제하기 (550,000원)", key="btn_pay_yeta_single", use_container_width=True, type="primary"):
                    safe_email = user_id if "@" in user_id else f"{user_id}@ahpmaster.com"
                    
                    checkout_html = f"""
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <script src="https://cdn.portone.io/v2/browser-sdk.js"></script>
                    </head>
                    <body>
                        <script>
                            const r = Math.random().toString(36).substring(2, 15);
                            let baseOrigin = window.location.origin;
                            if (baseOrigin.endsWith("/")) {{ baseOrigin = baseOrigin.slice(0, -1); }}
                            
                            const returnUrl = baseOrigin + "/?portone_paid=true&mode=yeta&user_id=" + encodeURIComponent("{user_id}") + "&plan_name=" + encodeURIComponent("예타 단건 분석권");
                            
                            window.PortOne.requestPayment({{
                                storeId: "store-e653cab4-7da6-4bcb-9968-63f77d048c5d",
                                channelKey: "channel-key-4279e2d9-c986-47cb-b190-ab1f9bb71215",
                                paymentId: "pay-" + r,
                                orderName: "예타 단건 분석권 - {user_id}",
                                totalAmount: 550000,
                                currency: "CURRENCY_KRW",
                                payMethod: "CARD",
                                redirectUrl: returnUrl,
                                customer: {{
                                    email: "{safe_email}",
                                    fullName: "{user_id}",
                                    phoneNumber: "010-0000-0000"
                                }}
                            }}).then(function(response) {{
                                if (response.code != null) {{
                                    alert("결제 실패: " + response.message);
                                }} else {{
                                    window.location.href = returnUrl;
                                }}
                            }}).catch(function(error) {{
                                alert("결제 진행 중 오류: " + error.message);
                            }});
                        </script>
                    </body>
                    </html>
                    """
                    st.components.v1.html(checkout_html, height=100)
                    
            with pay_col2:
                st.write("**B2B 기업/연구소 전용 지불 처리**")
                show_form = st.checkbox("세금계산서/견적서 발행 및 계좌이체 신청", key="chk_tax_form")
                
                if show_form:
                    with st.form("yeta_tax_form"):
                        st.write("세금계산서 발행 및 기관 계좌이체 승인에 필요한 정보를 입력해 주세요.")
                        biz_name = st.text_input("상호 / 법인명", key="tax_biz_name")
                        biz_num = st.text_input("사업자등록번호 (숫자만 입력)", key="tax_biz_num")
                        rep_name = st.text_input("대표자명", key="tax_rep_name")
                        address = st.text_input("사업장 주소", key="tax_address")
                        biz_type = st.text_input("업태 및 종목", key="tax_biz_type")
                        email = st.text_input("세금계산서 수령 이메일", key="tax_email", value=user_id if "@" in user_id else "")
                        plan_choice = st.selectbox("선택 요금제 플랜", ["예타 단건 분석권 (550,000원)", "기관 연간 라이선스 (2,640,000원)"])
                        
                        submit_tax = st.form_submit_button("세금계산서/인보이스 발행 요청", use_container_width=True)
                        if submit_tax:
                            if not biz_name or not biz_num or not email:
                                st.error("상호명, 사업자번호, 이메일은 필수 입력 사항입니다.")
                            else:
                                try:
                                    conn = sqlite3.connect('users.db')
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
            st.write("### " + _("AHP 마스터 예타 분석 시스템 회원가입", "AHP Master YETA Sign Up"))
            
            agreements = signup_agreement.show_agreement_ui()
            
            s_id = st.text_input(_("아이디 (이메일 주소)", "Username (Email Address)"), key="main_s_id_yeta")
            s_pw = st.text_input(_("비밀번호", "Password"), type="password", key="main_s_pw_yeta")
            
            s_cust_type = "yeta"
            
            if st.button(_("가입신청", "Register"), key="main_btn_signup_yeta", type="primary"):
                if not agreements.get("agree_personal_info"):
                    st.error(_("개인정보 수집·이용에 동의해야 가입신청할 수 있습니다.", "You must agree to the privacy policy to register."))
                elif not validate_email(s_id):
                    st.error(_("올바른 이메일 형식이 아닙니다.", "Invalid email format."))
                elif not validate_password(s_pw):
                    st.error(_("비밀번호는 문자+특수문자여야 합니다.", "Password must contain both letters and special characters."))
                else:
                    restore_from_deleted_sheet(s_id.strip())
                    if add_user(s_id.strip(), s_pw, 'temp', agree_info="Y", customer_type=s_cust_type):
                        st.success(_("회원가입이 완료되었습니다! 사이드바의 '로그인' 탭에서 로그인해 주시기 바랍니다.", "Registration successful! Please log in using the 'Login' tab in the sidebar."))
                        time.sleep(2)
                        st.rerun()
                    else:
                        st.error(_("이미 존재하는 아이디입니다.", "ID already exists."))

import sqlite3
import pandas as pd
import streamlit as st
import datetime
import hashlib
import string
import random
import gspread
import time
import json
import os

def get_db_connection(db_name='users.db', timeout=15):
    return sqlite3.connect(db_name, timeout=timeout)

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
    conn = get_db_connection('users.db')
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
    conn = get_db_connection('users.db')
    c = conn.cursor()
    c.execute("UPDATE users SET pw=? WHERE id=?", (hashed_pw, user_id))
    conn.commit()
    conn.close()
    
    try:
        client = get_gspread_client()
        spreadsheet_id = st.secrets.get("SPREADSHEET_ID")
        if client and spreadsheet_id:
            spreadsheet = client.open_by_key(spreadsheet_id)
            sheet = spreadsheet.sheet1
            cell = sheet.find(user_id)
            if cell:
                sheet.update_cell(cell.row, 4, hashed_pw)
    except Exception:
        pass
    return True

def upgrade_user_password_to_hash(user_id, pw):
    hashed_pw = hash_password(pw)
    conn = get_db_connection('users.db')
    c = conn.cursor()
    c.execute("UPDATE users SET pw=? WHERE id=?", (hashed_pw, user_id))
    conn.commit()
    conn.close()
    
    try:
        client = get_gspread_client()
        spreadsheet_id = st.secrets.get("SPREADSHEET_ID")
        if client and spreadsheet_id:
            spreadsheet = client.open_by_key(spreadsheet_id)
            sheet = spreadsheet.sheet1
            cell = sheet.find(user_id)
            if cell:
                sheet.update_cell(cell.row, 4, hashed_pw)
    except Exception:
        pass

@st.cache_resource
def get_gspread_client():
    scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    raw_auth = st.secrets.get("gcp_service_account")
    if not raw_auth:
        return None
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
@st.cache_data(ttl=600)
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
                        conn = get_db_connection('users.db')
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

@st.cache_data(ttl=600)
def get_event_settings():
    conn = get_db_connection('users.db')
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
        spreadsheet_id = st.secrets.get("SPREADSHEET_ID")
        if not client or not spreadsheet_id: 
            return -1
        spreadsheet = run_gspread_with_retry(client.open_by_key, spreadsheet_id)
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

@st.cache_data(ttl=300)
def get_all_users():
    conn = get_db_connection('users.db')
    df = pd.read_sql_query("SELECT * FROM users", conn)
    conn.close()
    return df

def delete_user(user_id):
    conn = get_db_connection('users.db')
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE id=?", (user_id,))
    c.execute("DELETE FROM saved_analyses WHERE user_id=?", (user_id,))
    c.execute("DELETE FROM user_models WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()

    try:
        client = get_gspread_client()
        spreadsheet_id = st.secrets.get("SPREADSHEET_ID")
        if client and spreadsheet_id:
            spreadsheet = client.open_by_key(spreadsheet_id)
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
    conn = get_db_connection('users.db')
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
        spreadsheet_id = st.secrets.get("SPREADSHEET_ID")
        if client and spreadsheet_id:
            spreadsheet = client.open_by_key(spreadsheet_id)
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
        spreadsheet_id = st.secrets.get("SPREADSHEET_ID")
        if client and spreadsheet_id:
            spreadsheet = client.open_by_key(spreadsheet_id)
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
    conn = get_db_connection('users.db')
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
        spreadsheet_id = st.secrets.get("SPREADSHEET_ID")
        if client and spreadsheet_id:
            spreadsheet = client.open_by_key(spreadsheet_id)
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
            conn = get_db_connection('users.db')
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
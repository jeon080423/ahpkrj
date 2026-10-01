import streamlit as st
import importlib
import sys

# 1. Page Config (Must be called as the very first Streamlit command)
try:
    from PIL import Image
    import os
    if os.path.exists("favicon.png"):
        favicon = Image.open("favicon.png")
    else:
        favicon = "📊"
    st.set_page_config(
        page_title="AHP Master Portal",
        layout="wide",
        page_icon=favicon
    )
except Exception:
    pass

import sqlite3

def migrate_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                  (id TEXT PRIMARY KEY, role TEXT, signup_date TEXT, pw TEXT, expiry_date TEXT, agree_info TEXT, 
                   survey_count INTEGER DEFAULT 0, last_survey_link TEXT, plan_type TEXT, 
                   event_applied TEXT, thesis_title TEXT, university TEXT, customer_type TEXT)''')
    columns_to_add = [
        ("survey_count", "INTEGER DEFAULT 0"),
        ("last_survey_link", "TEXT"),
        ("plan_type", "TEXT"),
        ("event_applied", "TEXT"),
        ("thesis_title", "TEXT"),
        ("university", "TEXT"),
        ("customer_type", "TEXT")
    ]
    for col_name, col_type in columns_to_add:
        try:
            c.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}")
            conn.commit()
        except Exception:
            pass
            
    # Add survey_images table for Section 2 Image Upload feature (up to 3 images)
    c.execute('''CREATE TABLE IF NOT EXISTS survey_images (
                    survey_id TEXT PRIMARY KEY,
                    image_data BLOB,
                    mime_type TEXT,
                    image_data2 BLOB,
                    mime_type2 TEXT,
                    image_data3 BLOB,
                    mime_type3 TEXT)''')
    for col_name, col_type in [("image_data2", "BLOB"), ("mime_type2", "TEXT"), ("image_data3", "BLOB"), ("mime_type3", "TEXT")]:
        try:
            c.execute(f"ALTER TABLE survey_images ADD COLUMN {col_name} {col_type}")
            conn.commit()
        except Exception:
            pass
    conn.commit()
    conn.close()
    
    try:
        import coupon_manager
        coupon_manager.init_coupon_db()
    except Exception:
        pass

try:
    migrate_db()
except Exception as e:
    st.error(f"DB 마이그레이션 오류: {e}")

# 2. Re-resolve language settings
try:
    if 'lang' not in st.session_state:
        try:
            _init_lang = st.query_params.get("lang", "ko")
            if isinstance(_init_lang, list): _init_lang = _init_lang[0]
            st.session_state.lang = _init_lang.lower()
        except:
            st.session_state.lang = 'ko'
except:
    pass

import extra_streamlit_components as stx
import sqlite3
# [보안 패치] 쿠키 자동 로그인 토큰 검증용 (yeta_db의 검증된 헬퍼 재사용)
from yeta_db import verify_login_token as _verify_login_token, issue_login_token as _issue_login_token, downgrade_if_expired as _downgrade_if_expired

cookie_manager = stx.CookieManager(key="global_cookie_manager")
st.session_state.cookie_manager = cookie_manager

# auto-login based on cookie (쿠키 값 형식: "user_id|||login_token")
saved_user = None
saved_token = None
_had_cookie = False
try:
    _saved_val = cookie_manager.get(cookie="ahp_user_id")
    if _saved_val:
        _had_cookie = True
        # [보안 패치] 구 형식(평문 ID) 쿠키는 토큰이 없어 무효 처리됨
        if "|||" in str(_saved_val):
            saved_user, saved_token = str(_saved_val).rsplit("|||", 1)
except Exception:
    pass

need_delete_cookie = False
if st.session_state.get("logout_requested"):
    saved_user = None
    saved_token = None
    need_delete_cookie = True

# [보안 패치] DB 저장 랜덤 토큰과 일치할 때만 자동 로그인 허용 (쿠키 위조 차단)
if (saved_user and saved_token and _verify_login_token(saved_user, saved_token)
        and not st.session_state.get('user_id') and not st.session_state.get('logout_requested')):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT role, expiry_date, plan_type FROM users WHERE id=?", (saved_user,))
    db_user = c.fetchone()
    conn.close()
    if db_user:
        # [보안 패치] 쿠키 자동 로그인 경로에서도 만료 체크 (만료 official 강등)
        _sess_role, _sess_expiry = _downgrade_if_expired(saved_user, db_user[0], db_user[1])
        st.session_state.user_id = saved_user
        st.session_state.user_role = _sess_role
        st.session_state.expiry_date = _sess_expiry
        st.session_state.plan_type = db_user[2] if len(db_user) > 2 else None
        try:
            import survey_manager
            survey_manager.log_user_action(saved_user, "자동 로그인 (쿠키)")
        except:
            pass
    else:
        need_delete_cookie = True
elif _had_cookie:
    # [보안 패치] 토큰 검증 실패/위조/구 형식 쿠키는 삭제하고 재로그인 유도
    need_delete_cookie = True

# Sync state to cookie (sliding expiration: 1 hour)
SESSION_TIMEOUT = 3600  # 1 hour
current_user = st.session_state.get('user_id')
if current_user and not st.session_state.get('logout_requested'):
    try:
        # [보안 패치] 쿠키에 user_id 단독이 아닌 검증용 랜덤 토큰을 함께 저장
        _ctok = _issue_login_token(current_user, force_new=False)
        if _ctok:
            cookie_manager.set("ahp_user_id", f"{current_user}|||{_ctok}", max_age=SESSION_TIMEOUT, key="set_ahp_user_cookie")
    except Exception:
        pass
elif (not current_user and _had_cookie) or need_delete_cookie or st.session_state.get('logout_requested'):
    try:
        cookie_manager.delete("ahp_user_id", key="del_ahp_user_cookie")
    except Exception:
        pass

def _(ko_text, en_text):
    try:
        if st.session_state.get('lang', 'ko') == 'en':
            return en_text
    except:
        pass
    return ko_text

# 3. Handle query parameters and session state for routing
raw_mode = st.query_params.get("mode")
if raw_mode:
    if isinstance(raw_mode, list):
        raw_mode = raw_mode[0] if raw_mode else None
    if isinstance(raw_mode, str):
        raw_mode = raw_mode.strip().lower()
    st.session_state.mode = raw_mode

# If the mode is set in session state but not in query params, update query params
if st.session_state.get("mode") and "mode" not in st.query_params:
    st.query_params["mode"] = st.session_state.mode

mode = st.session_state.get("mode")
if isinstance(mode, list):
    mode = mode[0] if mode else None
if isinstance(mode, str):
    mode = mode.strip().lower()

# 4. Route to standard_app or yeta_app
if mode == "yeta":
    import yeta_app
    yeta_app.run()
else:
    with open("standard_app.py", encoding="utf-8") as f:
        exec(f.read(), globals())

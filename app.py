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
    conn.close()

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

cookie_manager = stx.CookieManager(key="global_cookie_manager")
st.session_state.cookie_manager = cookie_manager

# auto-login based on cookie
saved_user = None
try:
    saved_user = cookie_manager.get(cookie="ahp_user_id")
except Exception:
    pass

need_delete_cookie = False
if saved_user and not st.session_state.get('user_id'):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT role, expiry_date, plan_type FROM users WHERE id=?", (saved_user,))
    db_user = c.fetchone()
    conn.close()
    if db_user:
        st.session_state.user_id = saved_user
        st.session_state.user_role = db_user[0]
        st.session_state.expiry_date = db_user[1]
        st.session_state.plan_type = db_user[2] if len(db_user) > 2 else None
        try:
            import survey_manager
            survey_manager.log_user_action(saved_user, "자동 로그인 (쿠키)")
        except:
            pass
    else:
        need_delete_cookie = True

# Sync state to cookie
current_user = st.session_state.get('user_id')
if current_user and current_user != saved_user:
    try:
        cookie_manager.set("ahp_user_id", current_user, max_age=86400 * 30, key="set_ahp_user_cookie")
    except Exception:
        pass
elif (not current_user and saved_user) or need_delete_cookie:
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
    import standard_app
    import importlib
    importlib.reload(standard_app)

import re

app_file = "f:/app/4. AHP마스터/app.py"

with open(app_file, "r", encoding="utf-8") as f:
    content = f.read()

oauth_code = """
# --- 소셜 로그인 콜백 처리 ---
try:
    _q = st.query_params
    if "code" in _q and "state" in _q:
        import auth_social
        import time
        oauth_code = _q["code"]
        oauth_state = _q["state"]
        
        if oauth_state == "google":
            user_info = auth_social.get_google_user_info(oauth_code, auth_social.get_redirect_uri())
            if "error" not in user_info and "email" in user_info:
                email = user_info["email"].strip()
                
                # DB 연동 처리
                conn = sqlite3.connect('users.db')
                c = conn.cursor()
                c.execute("SELECT id FROM users WHERE id=?", (email,))
                user_exists = c.fetchone()
                
                if not user_exists:
                    # 신규가입
                    signup_date = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).strftime("%Y-%m-%d")
                    expiry_date = "9999-12-31"
                    hashed_pw = hash_password("OAUTH_USER")
                    c.execute("INSERT INTO users (id, role, signup_date, pw, expiry_date, agree_info, survey_count, last_survey_link, plan_type) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", 
                              (email, "temp", signup_date, hashed_pw, expiry_date, "Y", 0, "", None))
                    conn.commit()
                    try:
                        log_to_sheets(email, "temp", signup_date, hashed_pw, "Y", expiry_date, 0, "")
                    except:
                        pass
                conn.close()
                
                conn2 = sqlite3.connect('users.db')
                c2 = conn2.cursor()
                c2.execute("SELECT role, expiry_date, plan_type FROM users WHERE id=?", (email,))
                u_row = c2.fetchone()
                conn2.close()
                
                st.session_state.user_id = email
                st.session_state.user_role = u_row[0] if u_row else "temp"
                st.session_state.expiry_date = u_row[1] if u_row else "9999-12-31"
                st.session_state.plan_type = u_row[2] if u_row and len(u_row)>2 else None
                
                st.query_params.clear()
                st.query_params["login_user"] = email
                st.query_params["login_token"] = hashlib.sha256(f"{email}:AHP_MASTER_SECURE_SALT_2026_!@#".encode()).hexdigest()
                st.query_params["last_activity"] = str(int(time.time()))
                
                st.rerun()
except Exception as e:
    print(f"OAuth Callback Error: {e}")
"""

target = '_is_survey_or_preview = "preview_id" in _q or "survey_id" in _q'

if "# --- 소셜 로그인 콜백 처리 ---" not in content:
    new_content = content.replace(target, target + "\n\n" + oauth_code)
    with open(app_file, "w", encoding="utf-8") as f:
        f.write(new_content)
    print("OAuth callback injected.")
else:
    print("OAuth callback already exists.")

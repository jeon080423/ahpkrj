import sys

target = """                conn = sqlite3.connect('users.db')
                cur = conn.cursor()
                cur.execute("SELECT survey_id, title, created_at FROM admin_surveys WHERE admin_id = ? ORDER BY created_at DESC", (st.session_state.user_id,))
                admin_surveys = cur.fetchall()
                conn.close()"""

replacement = """                conn = sqlite3.connect('users.db')
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
                admin_surveys.sort(key=lambda x: x[2], reverse=True)"""

with open('f:/app/4. AHP마스터/app.py', 'r', encoding='utf-8') as f:
    content = f.read()

if target in content:
    content = content.replace(target, replacement)
    with open('f:/app/4. AHP마스터/app.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Replaced successfully")
else:
    print("Target not found")

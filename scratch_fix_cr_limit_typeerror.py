import re

with open('f:/app/4. AHP마스터/app.py', 'r', encoding='utf-8') as f:
    content = f.read()

target = 'st.session_state.edit_cr_limit = float(meta.get("CR_Limit", 0.1))'
replacement = '''cr_limit_raw = meta.get("CR_Limit", 0.1)
                            st.session_state.edit_cr_limit = float(cr_limit_raw) if cr_limit_raw is not None and str(cr_limit_raw).lower() != "none" else None'''

if target in content:
    content = content.replace(target, replacement)
    with open('f:/app/4. AHP마스터/app.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Replaced CR_Limit loading logic successfully")
else:
    print("Target CR_Limit loading logic not found")

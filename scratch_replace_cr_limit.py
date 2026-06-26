import re

with open('f:/app/4. AHP마스터/app.py', 'r', encoding='utf-8') as f:
    content = f.read()

target = """            cr_limit_opt = st.selectbox("일관성 비율(CR) 허용 기준치", [
                "제한하지 않음 (이탈률 감소용)",
                "0.1 이하 (매우 엄격함)",
                "0.2 이하 (보통)",
                "0.3 이하 (일부 허용)"
            ], index=0)"""

replacement = """            # Get default index from edit state if editing, otherwise default to index 3 (0.3 이하)
            default_cr_idx = 3
            if st.session_state.get("editing_survey_id") and st.session_state.get("edit_cr_limit") is not None:
                cr_val = float(st.session_state.get("edit_cr_limit"))
                if cr_val <= 0.1: default_cr_idx = 1
                elif cr_val <= 0.2: default_cr_idx = 2
                elif cr_val <= 0.3: default_cr_idx = 3
            elif st.session_state.get("editing_survey_id") and st.session_state.get("edit_cr_limit") is None:
                default_cr_idx = 0
                
            cr_limit_opt = st.selectbox("일관성 비율(CR) 허용 기준치", [
                "제한하지 않음 (이탈률 감소용)",
                "0.1 이하 (매우 엄격함)",
                "0.2 이하 (보통)",
                "0.3 이하 (일부 허용)"
            ], index=default_cr_idx)"""

if target in content:
    content = content.replace(target, replacement)
    with open('f:/app/4. AHP마스터/app.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Replaced CR limit selectbox successfully")
else:
    print("Target CR limit selectbox not found")

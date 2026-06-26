import re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

target = """                for i in range(num_types):
                    st.markdown(f"**{i+1}.**")
                    q_val = st.text_input(_("그룹 분류 질문 제목", "Group Classification Question Title") + f" ({i+1})", value=type_questions_state[i]["q"], key=f"tq_q_{i}")
                    opts_val = st.text_input(_("그룹 분류 보기 옵션 (콤마로 구분)", "Group Classification Options (comma-separated)") + f" ({i+1})", value=type_questions_state[i]["opts"], key=f"tq_opts_{i}")"""

replacement = """                for i in range(num_types):
                    st.markdown(f"**{i+1}.**")
                    if i == 0:
                        q_label = _("그룹 분류 질문 제목", "Group Classification Question Title")
                        opts_label = _("그룹 분류 보기 옵션 (콤마로 구분)", "Group Classification Options (comma-separated)")
                    else:
                        q_label = _("추가 설문 문항", "Additional Survey Question")
                        opts_label = _("추가 문항 보기 옵션 (콤마로 구분)", "Additional Question Options (comma-separated)")
                        
                    q_val = st.text_input(q_label + f" ({i+1})", value=type_questions_state[i]["q"], key=f"tq_q_{i}")
                    opts_val = st.text_input(opts_label + f" ({i+1})", value=type_questions_state[i]["opts"], key=f"tq_opts_{i}")"""

if target in content:
    content = content.replace(target, replacement)
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Successfully replaced labels in app.py")
else:
    print("Target not found in app.py")

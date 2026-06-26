import re

with open('f:/app/4. AHP마스터/app.py', 'r', encoding='utf-8') as f:
    content = f.read()

replacements = [
    (r'definitions_map\[mc\] = st\.text_input\(\n\s+f"\[\{mc\}\] 대항목 조작적 정의",\n\s+value=f"\{mc\}에 대한 설명"\n\s+\)',
     r'definitions_map[mc] = st.text_input(\n                f"[{mc}] 대항목 조작적 정의",\n                value=st.session_state.get("edit_definitions", {}).get(mc, f"{mc}에 대한 설명")\n            )'),
     
    (r'definitions_map\[f"\{mc\}_\{sub\}"\] = st\.text_input\(\n\s+f"\[\{sub\}\] 소항목 조작적 정의",\n\s+value=f"\{sub\}에 대한 설명"\n\s+\)',
     r'definitions_map[f"{mc}_{sub}"] = st.text_input(\n                f"[{sub}] 소항목 조작적 정의",\n                value=st.session_state.get("edit_definitions", {}).get(f"{mc}_{sub}", f"{sub}에 대한 설명")\n            )'),
     
    (r'cr_limit = float\(st\.number_input\("허용 CR 값 \(기본 0\.1\)", min_value=0\.05, max_value=0\.3, value=0\.1, step=0\.01\)\)',
     r'cr_limit = float(st.number_input("허용 CR 값 (기본 0.1)", min_value=0.05, max_value=0.3, value=float(st.session_state.get("edit_cr_limit", 0.1)), step=0.01))')
]

for t, r in replacements:
    content = re.sub(t, r, content, count=1)

with open('f:/app/4. AHP마스터/app.py', 'w', encoding='utf-8') as f:
    f.write(content)

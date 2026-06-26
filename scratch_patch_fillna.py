import sys

file_path = r'f:\app\4. AHP마스터\app.py'

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if 'fillna(1.0)' in line and ('raw_df' in line or 'st.session_state' in line):
        lines[i] = line.replace('.fillna(1.0)', '')
        print(f"Patched line {i}: {lines[i].strip()}")

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("Patching fillna complete.")

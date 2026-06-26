import re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find NEW block
new_start_idx = content.find('        # 그룹 분류 문항 설정\n        with st.container(border=True):\n            st.markdown(_("** 그룹 분류 문항 설정**", "** Group Classification Setup**"))')
new_end_str = '            type_options = ", ".join(type_questions[0]["opts"]) if type_questions else ""\n'
new_end_idx = content.find(new_end_str) + len(new_end_str)

if new_start_idx == -1 or new_end_idx == -1:
    print(f"Error: NEW block not found. start={new_start_idx}, end={new_end_idx}")
    exit(1)

new_block = content[new_start_idx:new_end_idx]

# Remove NEW block from its original location
content = content[:new_start_idx] + content[new_end_idx:]

# Find OLD block
old_start_idx = content.find('            # 그룹 분류 설정\n            with st.container(border=True):\n                st.markdown(_("** 그룹 분류 문항 설정**", "** Group Classification Setup**"))')
old_end_str = '                type_options = st.text_input(_("그룹 분류 보기 옵션 (콤마로 구분)", "Group Classification Options (comma-separated)"), value=type_opts_val)\n'
old_end_idx = content.find(old_end_str) + len(old_end_str)

if old_start_idx == -1 or old_end_idx == -1:
    print(f"Error: OLD block not found. start={old_start_idx}, end={old_end_idx}")
    exit(1)

# Indent the NEW block to match the OLD block (add 4 spaces)
indented_new_block = []
for line in new_block.split('\n'):
    if line:
        indented_new_block.append('    ' + line)
    else:
        indented_new_block.append(line)
indented_new_block_str = '\n'.join(indented_new_block)

# Replace OLD block with indented NEW block
content = content[:old_start_idx] + indented_new_block_str + content[old_end_idx:]

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Successfully moved and indented the group classification block.")

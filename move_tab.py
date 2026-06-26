import sys

with open('app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 1. Update the st.tabs declaration
for i, line in enumerate(lines):
    if "main_tab1, main_tab2, main_tab3 = st.tabs([" in line:
        lines[i] = line.replace("main_tab1, main_tab2, main_tab3", "main_tab1, main_tab_coding, main_tab2, main_tab3")
        # insert the new tab right after main_tab1
        lines.insert(i + 2, '        _("AHP 코딩 엑셀 양식", "AHP Coding Excel Form"), \n')
        break

# 2. Extract the block
start_idx = -1
end_idx = -1

for i, line in enumerate(lines):
    if "# [신규] 온라인 설문지 제작 탭 (Tab 2) 상세 구현" in line:
        start_idx = i - 1 # include the previous dash line
        break

if start_idx != -1:
    for i in range(start_idx + 1, len(lines)):
        if 'st.markdown("---")' in lines[i] and 'if st.session_state.user_role == \'official\':' in lines[i+2]:
            end_idx = i
            break

if start_idx != -1 and end_idx != -1:
    block = lines[start_idx:end_idx]
    
    # 3. Create the new tab block
    new_tab_block = [
        "    # -------------------------------------------------------------------------\n",
        "    # [신규] 코딩 엑셀 양식 탭\n",
        "    # -------------------------------------------------------------------------\n",
        "    with main_tab_coding:\n"
    ] + block + ["\n"]
    
    # find where to insert main_tab_coding (right before with main_tab2)
    insert_idx = -1
    for i in range(end_idx, len(lines)):
        if "with main_tab2:" in lines[i]:
            insert_idx = i
            break
            
    if insert_idx != -1:
        # construct new lines
        # First, remove the block from its original location
        modified_lines = lines[:start_idx] + lines[end_idx:insert_idx] + new_tab_block + lines[insert_idx:]
        
        with open('app.py', 'w', encoding='utf-8') as f:
            f.writelines(modified_lines)
        print("Success")
    else:
        print("Could not find with main_tab2:")
else:
    print(f"Could not find block boundaries: start={start_idx}, end={end_idx}")

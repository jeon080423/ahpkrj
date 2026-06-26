import sys

file_path = "f:\\app\\4. AHP마스터\\app.py"
with open(file_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

new_lines = []

# We need to find `if not existing_sheet_id_input.strip():` around line 6894
# and then indent everything below it that belongs to the button block by 4 spaces.

in_button_block = False
for i, line in enumerate(lines):
    if 'if not existing_sheet_id_input.strip():' in line and i > 6890:
        new_lines.append(line)
        in_button_block = True
        continue
    
    if in_button_block:
        # Stop indenting when we reach `with main_tab3:`
        if 'with main_tab3:' in line:
            in_button_block = False
            new_lines.append(line)
            continue
            
        # The line right before `with main_tab3:` is `    # -------------------------------------------------------------------------`
        if line.strip() == "" or line.strip().startswith("# -------------------------------------------------------------------------") or line.strip().startswith("# [신규] 응답현황 대시보드 탭"):
            # Don't indent blank lines or the tab separator comments
            if 'main_tab3' in "".join(lines[i:i+3]):
                in_button_block = False
            new_lines.append(line)
        else:
            # Indent by 4 spaces
            new_lines.append("    " + line)
    else:
        new_lines.append(line)

with open(file_path, "w", encoding="utf-8") as f:
    f.writelines(new_lines)

print("Done fixing indentation.")

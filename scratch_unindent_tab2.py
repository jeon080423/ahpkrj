import sys
import re

file_path = "f:\\app\\4. AHP마스터\\app.py"
with open(file_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

new_lines = []
in_tab2 = False
skip_else = False

for i, line in enumerate(lines):
    if "with main_tab2:" in line:
        in_tab2 = True
        new_lines.append(line)
        continue
    
    if in_tab2 and "with main_tab3:" in line:
        in_tab2 = False
        new_lines.append(line)
        continue
        
    if in_tab2:
        # We need to change the if condition block
        if 'st.warning(_("🔒 **회원가입하시면 온라인 설문 작성 및 배포를 기능제한 없이 사용할 수 있습니다.**"' in line:
            new_lines.append('            st.warning(_("🔒 **비회원도 온라인 설문 폼을 미리 작성해 볼 수 있습니다.**", "🔒 **Non-members can also preview and fill out the online survey form.**"))\n')
            continue
        if 'st.info(_("무료 회원가입 및 로그인을 완료하시면 제한 없이 AHP 온라인 설문지를 자동 생성하고' in line:
            new_lines.append('            st.info(_("작성하신 내용은 좌측 사이드바에서 회원가입 및 로그인을 하시면 그대로 유지되어 바로 배포하실 수 있습니다. (무료 회원도 기능 제한 없이 모든 기능 사용 가능)", "Once you sign up and log in from the left sidebar, the contents you have written will be maintained and you can deploy immediately. (Free members can also use all features without restriction)"))\n')
            continue
        if line.strip() == "else:" and "st.info(_(" in lines[i-1]:
            # Skip the else line
            continue
        
        # Unindent lines below else
        # The line right after else is line 6268 which starts with `            st.info(`
        # So we unindent by 4 spaces
        if line.startswith("            ") and i > 6265:
            new_lines.append(line[4:])
        else:
            new_lines.append(line)
    else:
        new_lines.append(line)

with open(file_path, "w", encoding="utf-8") as f:
    f.writelines(new_lines)

print("Done unindenting.")

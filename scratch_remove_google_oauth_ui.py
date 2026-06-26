import re

with open('f:/app/4. AHP마스터/app.py', 'r', encoding='utf-8') as f:
    content = f.read()

target_start = '        # [추가] 구글 계정 연동 설정 UI (구글 드라이브/스프레드시트 개별 연동)'
target_end = '                            st.rerun()' # This is the end of the expander block

start_idx = content.find(target_start)
if start_idx != -1:
    # Find the end of the expander block. The expander block ends when the indentation goes back to 8 spaces
    # or we can just search for the specific end of the block.
    # The block ends with:
    #                             st.success(_("구글 계정 연동에 실패했습니다. 코드를 다시 확인해 주세요.", "Google account linking failed. Please check the code again."))
    #                             st.rerun()
    # 
    # Let's use regex to find the block until the next identical indentation level or just a specific string
    
    specific_end = 'st.success(_("구글 계정 연동에 실패했습니다. 코드를 다시 확인해 주세요.", "Google account linking failed. Please check the code again."))\n                            st.rerun()'
    end_idx = content.find(specific_end, start_idx)
    
    if end_idx != -1:
        end_idx += len(specific_end)
        new_content = content[:start_idx] + content[end_idx:]
        
        # Remove extra blank lines that might be left over
        new_content = re.sub(r'\n\s*\n\s*\n', '\n\n', new_content)
        
        with open('f:/app/4. AHP마스터/app.py', 'w', encoding='utf-8') as f:
            f.write(new_content)
        print("Removed Google Account Integration UI successfully.")
    else:
        print("Could not find the end of the block.")
else:
    print("Could not find the start of the block.")

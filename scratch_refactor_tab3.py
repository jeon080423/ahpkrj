import re

with open('f:/app/4. AHP마스터/app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# We want to replace the block from `if not admin_surveys:` down to `if selected_sheet_id:`
target_start = """            if not admin_surveys:
                st.warning("자동으로 조회된 배포 설문 목록이 없습니다. 먼저 '온라인 설문지 제작' 탭에서 설문을 배포하시거나, 아래에 구글 스프레드시트 URL을 직접 입력해 주세요.")"""

target_end = """        # 대시보드 렌더링
        if selected_sheet_id:
            st.markdown(f"**선택된 설문 스프레드시트 ID**: `{selected_sheet_id}`")"""

start_idx = content.find(target_start)
end_idx = content.find(target_end)

if start_idx != -1 and end_idx != -1:
    replacement = """            if not admin_surveys:
                st.warning("아직 배포된 설문이 없습니다. '온라인 설문지 제작' 탭에서 먼저 설문을 완성하고 배포해 주세요.")
            else:
                selected_sheet_id = admin_surveys[0][0]
                survey_title = admin_surveys[0][1]
                created_at = admin_surveys[0][2]
                
                st.success(f"📌 현재 배포 중인 설문: **{survey_title}** (배포일시: {created_at})")
                st.divider()

        # 대시보드 렌더링
        if selected_sheet_id:
"""
    new_content = content[:start_idx] + replacement + content[end_idx + len(target_end):]
    with open('f:/app/4. AHP마스터/app.py', 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("Replaced Tab 3 dashboard logic successfully.")
else:
    print("Could not find target strings.")
    print("start:", start_idx, "end:", end_idx)

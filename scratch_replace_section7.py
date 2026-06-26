import sys

target = """            # [추가] 구글 스프레드시트 연동 설정
            st.markdown("##### ⚙️ 연동할 본인의 구글 스프레드시트 설정 *")
            st.info(\"\"\"
            **💡 연동 방법:**
            1. 본인의 구글 드라이브에서 **새 구글 스프레드시트**를 하나 생성합니다. (본인 계정 용량 내에서 생성되므로 용량 초과 오류가 발생하지 않습니다.)
            2. 우측 상단의 '공유' 버튼을 눌러 아래의 서비스 계정 이메일을 **편집자** (Editor)로 추가합니다.
               * 서비스 계정 이메일: `ahp2-75@ahp2-486703.iam.gserviceaccount.com`
            3. 생성한 스프레드시트의 **URL 주소** 또는 **시트 ID**를 복사하여 아래에 붙여넣어 주세요. (아래 예시 이미지 참고)
            \"\"\")
            st.image("manual_sheet_url_guide.png", caption="구글 스프레드시트 URL 주소창 복사 예시", width=650)
            existing_sheet_id_input = st.text_input("연동할 구글 스프레드시트 URL 또는 ID *", placeholder="https://docs.google.com/spreadsheets/d/...")"""

replacement = """            # [추가] 구글 스프레드시트 연동 설정
            if st.session_state.get('editing_survey_id'):
                st.markdown("##### ⚙️ 기존 구글 스프레드시트 연동 (수정 모드)")
                st.info("현재 **기존 설문 수정 모드**로 진입했습니다. 수정한 설정 내용은 기존 연동된 구글 스프레드시트에 안전하게 덮어씌워집니다.\\n\\n**연동된 시트 ID:** " + st.session_state.editing_survey_id)
                existing_sheet_id_input = st.session_state.editing_survey_id
            else:
                st.markdown("##### ⚙️ 연동할 본인의 구글 스프레드시트 설정 *")
                st.info(\"\"\"
                **💡 연동 방법:**
                1. 본인의 구글 드라이브에서 **새 구글 스프레드시트**를 하나 생성합니다. (본인 계정 용량 내에서 생성되므로 용량 초과 오류가 발생하지 않습니다.)
                2. 우측 상단의 '공유' 버튼을 눌러 아래의 서비스 계정 이메일을 **편집자** (Editor)로 추가합니다.
                   * 서비스 계정 이메일: `ahp2-75@ahp2-486703.iam.gserviceaccount.com`
                3. 생성한 스프레드시트의 **URL 주소** 또는 **시트 ID**를 복사하여 아래에 붙여넣어 주세요. (아래 예시 이미지 참고)
                \"\"\")
                st.image("manual_sheet_url_guide.png", caption="구글 스프레드시트 URL 주소창 복사 예시", width=650)
                existing_sheet_id_input = st.text_input("연동할 구글 스프레드시트 URL 또는 ID *", placeholder="https://docs.google.com/spreadsheets/d/...")"""

with open('f:/app/4. AHP마스터/app.py', 'r', encoding='utf-8') as f:
    content = f.read()

if target in content:
    content = content.replace(target, replacement)
    
    target_btn = 'if st.button("🚀 배포 및 DB 연동", type="primary", use_container_width=True):'
    replacement_btn = 'if st.button("🚀 배포 및 DB 연동 (수정 내용 적용)" if st.session_state.get("editing_survey_id") else "🚀 배포 및 DB 연동", type="primary", use_container_width=True):'
    content = content.replace(target_btn, replacement_btn)
    
    target_success = 'st.success("🎉 AHP 온라인 설문지 및 연동 구글 시트 생성이 완료되었습니다!")'
    replacement_success = 'st.success("🎉 AHP 온라인 설문지가 성공적으로 업데이트(수정) 되었습니다!" if st.session_state.get("editing_survey_id") else "🎉 AHP 온라인 설문지 및 연동 구글 시트 생성이 완료되었습니다!")'
    content = content.replace(target_success, replacement_success)
    
    with open('f:/app/4. AHP마스터/app.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Replaced section 7 successfully")
else:
    print("Target section 7 not found")

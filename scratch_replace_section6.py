import re

with open('f:/app/4. AHP마스터/app.py', 'r', encoding='utf-8') as f:
    content = f.read()

target = """            st.subheader("섹션 6: 설문 최종 배포 방식 설정")
            
            # 수동으로 생성한 구글 스프레드시트의 URL을 입력받는 입력칸 추가
            st.markdown("현재 서비스 계정 권한 문제로 자동 시트 생성이 원활하지 않을 수 있습니다. 본인의 구글 스프레드시트를 직접 생성하여 연동하는 방식을 권장합니다.")
            st.info(\"\"\"
            **수동 구글 스프레드시트 연동 가이드**
            1. 브라우저에서 새 구글 스프레드시트(빈 문서)를 생성합니다. (주소창에 `sheets.new` 입력)
            2. 우측 상단의 '공유' 버튼을 눌러 아래의 서비스 계정 이메일을 **편집자** (Editor)로 추가합니다.
               * 서비스 계정 이메일: `ahp2-75@ahp2-486703.iam.gserviceaccount.com`
            3. 생성한 스프레드시트의 **URL 주소** 또는 **시트 ID**를 복사하여 아래에 붙여넣어 주세요. (아래 예시 이미지 참고)
            \"\"\")
            st.image("manual_sheet_url_guide.png", caption="구글 스프레드시트 URL 주소창 복사 예시", width=650)
            existing_sheet_id_input = st.text_input("연동할 구글 스프레드시트 URL 또는 ID *", placeholder="https://docs.google.com/spreadsheets/d/...")"""

replacement = """            st.subheader("섹션 6: 설문 최종 배포 방식 설정")
            
            if st.session_state.editing_survey_id:
                st.info("현재 **기존 설문 수정 모드**로 진입했습니다. 수정한 설정 내용은 기존 구글 스프레드시트에 안전하게 덮어씌워집니다.\\n\\n**연동된 시트 ID:** " + st.session_state.editing_survey_id)
                existing_sheet_id_input = st.session_state.editing_survey_id
            else:
                # 수동으로 생성한 구글 스프레드시트의 URL을 입력받는 입력칸 추가
                st.markdown("현재 서비스 계정 권한 문제로 자동 시트 생성이 원활하지 않을 수 있습니다. 본인의 구글 스프레드시트를 직접 생성하여 연동하는 방식을 권장합니다.")
                st.info(\"\"\"
                **수동 구글 스프레드시트 연동 가이드**
                1. 브라우저에서 새 구글 스프레드시트(빈 문서)를 생성합니다. (주소창에 `sheets.new` 입력)
                2. 우측 상단의 '공유' 버튼을 눌러 아래의 서비스 계정 이메일을 **편집자** (Editor)로 추가합니다.
                   * 서비스 계정 이메일: `ahp2-75@ahp2-486703.iam.gserviceaccount.com`
                3. 생성한 스프레드시트의 **URL 주소** 또는 **시트 ID**를 복사하여 아래에 붙여넣어 주세요. (아래 예시 이미지 참고)
                \"\"\")
                st.image("manual_sheet_url_guide.png", caption="구글 스프레드시트 URL 주소창 복사 예시", width=650)
                existing_sheet_id_input = st.text_input("연동할 구글 스프레드시트 URL 또는 ID *", placeholder="https://docs.google.com/spreadsheets/d/...")"""

if target in content:
    content = content.replace(target, replacement)
    with open('f:/app/4. AHP마스터/app.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Replaced section 6 successfully")
else:
    print("Target section 6 not found")

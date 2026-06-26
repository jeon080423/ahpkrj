import re

with open('f:/app/4. AHP마스터/app.py', 'r', encoding='utf-8') as f:
    content = f.read()

replacements = [
    (r'survey_title = st\.text_input\("설문지 제목", value="제조용 협동로봇 도입 요인 중요도 분석을 위한 전문가 AHP 설문"\)',
     r'survey_title = st.text_input("설문지 제목", value=st.session_state.get("edit_title", "제조용 협동로봇 도입 요인 중요도 분석을 위한 전문가 AHP 설문"))'),
     
    (r'survey_desc = st\.text_area\("조사 목적 및 안내문", value=default_survey_desc, height=350\)',
     r'survey_desc = st.text_area("조사 목적 및 안내문", value=st.session_state.get("edit_desc", default_survey_desc), height=350)'),
     
    (r'survey_admin_email = st\.text_input\("설문조사 담당자 이메일 주소 \*", value=default_admin_email, placeholder="example@gmail.com"\)',
     r'survey_admin_email = st.text_input("설문조사 담당자 이메일 주소 *", value=st.session_state.get("edit_admin_email", default_admin_email), placeholder="example@gmail.com")'),
     
    (r'type_question = st\.text_input\("그룹 분류 질문 제목", value="그룹 분류 \(Type\)"\)',
     r'type_question = st.text_input("그룹 분류 질문 제목", value=st.session_state.get("edit_type_question", "그룹 분류 (Type)"))'),
     
    (r'type_options = st\.text_input\("그룹 분류 보기 옵션 \(콤마로 구분\)", value="전문가, 일반, 공무원, 기타"\)',
     r'type_options = st.text_input("그룹 분류 보기 옵션 (콤마로 구분)", value=st.session_state.get("edit_type_options", "전문가, 일반, 공무원, 기타"))'),
     
    (r'demo_gender = st\.checkbox\("성별 수집", value=True\)',
     r'demo_gender = st.checkbox("성별 수집", value=st.session_state.get("edit_demo_gender", True))'),
     
    (r'demo_aff = st\.checkbox\("소속 수집", value=True\)',
     r'demo_aff = st.checkbox("소속 수집", value=st.session_state.get("edit_demo_aff", True))'),
     
    (r'demo_email = st\.checkbox\("이메일 수집", value=True\)',
     r'demo_email = st.checkbox("이메일 수집", value=st.session_state.get("edit_demo_email", True))'),
     
    (r'demo_age = st\.checkbox\("연령 수집", value=True\)',
     r'demo_age = st.checkbox("연령 수집", value=st.session_state.get("edit_demo_age", True))'),
     
    (r'demo_exp = st\.checkbox\("경력년수 수집", value=True\)',
     r'demo_exp = st.checkbox("경력년수 수집", value=st.session_state.get("edit_demo_exp", True))'),
     
    (r'age_type = st\.radio\("연령 수집 방식", \["개방형 \(숫자 직접 입력\)", "10세 단위 선택형"\], index=0, horizontal=True, key="survey_age_type_setup"\)',
     r'age_type = st.radio("연령 수집 방식", ["개방형 (숫자 직접 입력)", "10세 단위 선택형"], index=0 if st.session_state.get("edit_age_type", "개방형 (숫자 직접 입력)") == "개방형 (숫자 직접 입력)" else 1, horizontal=True, key="survey_age_type_setup")'),
     
    (r'exp_type = st\.radio\("경력년수 수집 방식", \["개방형 \(숫자 직접 입력\)", "5년 단위 선택형"\], index=0, horizontal=True, key="survey_exp_type_setup"\)',
     r'exp_type = st.radio("경력년수 수집 방식", ["개방형 (숫자 직접 입력)", "5년 단위 선택형"], index=0 if st.session_state.get("edit_exp_type", "개방형 (숫자 직접 입력)") == "개방형 (숫자 직접 입력)" else 1, horizontal=True, key="survey_exp_type_setup")'),
     
    (r'main_input = st\.text_input\("대항목 \(Main Criteria\)", value="기술 요인, 조직 요인, 환경 요인, 혁신 요인"\)',
     r'main_input = st.text_input("대항목 (Main Criteria)", value=st.session_state.get("edit_main_input", "기술 요인, 조직 요인, 환경 요인, 혁신 요인"))'),
     
    (r'sub_input = st\.text_input\(f"\'\{mc\}\'의 하위 요인 \(Sub-criteria\)", value=default_sub_val\)',
     r'sub_input = st.text_input(f"\'{mc}\'의 하위 요인 (Sub-criteria)", value=st.session_state.get("edit_sub_inputs", {}).get(mc, default_sub_val))'),
     
    (r'scale_option = st\.radio\("응답 척도 타입", \[\n\s+"1-9 Continuous", "1-7 Continuous", "1-5 Continuous"\n\s+\], index=0\)',
     r'scale_idx = ["1-9 Continuous", "1-7 Continuous", "1-5 Continuous"].index(st.session_state.get("edit_scale_type", "1-9 Continuous")) if st.session_state.get("edit_scale_type", "1-9 Continuous") in ["1-9 Continuous", "1-7 Continuous", "1-5 Continuous"] else 0\n            scale_option = st.radio("응답 척도 타입", [\n                "1-9 Continuous", "1-7 Continuous", "1-5 Continuous"\n            ], index=scale_idx)'),
]

for t, r in replacements:
    content = re.sub(t, r, content, count=1)

with open('f:/app/4. AHP마스터/app.py', 'w', encoding='utf-8') as f:
    f.write(content)

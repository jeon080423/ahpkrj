import sys

target = """            st.divider()

            from survey_manager import create_survey_sheet, generate_pairwise_combinations

            # 7개 섹션 설문지 생성 폼 구성
            # 섹션 1: 기본 정보
            st.subheader("섹션 1: 설문 기본 정보 설정")"""

replacement = """            st.divider()
            
            # ------------------------------------------------------------
            # 0. 설문 관리 (새로 작성 / 기존 수정 모드)
            # ------------------------------------------------------------
            st.subheader("섹션 0: 설문 작성 방식 선택")
            
            if 'editing_survey_id' not in st.session_state:
                st.session_state.editing_survey_id = None
                
            col_mode1, col_mode2 = st.columns(2)
            with col_mode1:
                if st.button("✨ 새 설문 작성하기 (초기화)", use_container_width=True, type="primary" if st.session_state.editing_survey_id is None else "secondary"):
                    st.session_state.editing_survey_id = None
                    keys_to_clear = [k for k in st.session_state.keys() if k.startswith('edit_')]
                    for k in keys_to_clear:
                        del st.session_state[k]
                    st.rerun()
                    
            with col_mode2:
                st.markdown("**기존 설문 불러와서 수정하기:**")
                gs_surveys = []
                try:
                    from survey_manager import get_admin_surveys_from_gsheet
                    gs_surveys = get_admin_surveys_from_gsheet(st.session_state.user_id)
                except Exception:
                    pass
                
                if gs_surveys:
                    survey_options = {f"{s[1]} ({s[2]})": s[0] for s in gs_surveys}
                    selected_edit_sheet = st.selectbox("수정할 설문을 선택하세요", options=list(survey_options.keys()), key="edit_survey_selectbox")
                    if st.button("📂 선택한 설문 불러오기", use_container_width=True):
                        sel_id = survey_options[selected_edit_sheet]
                        with st.spinner("설문 데이터를 불러오는 중입니다..."):
                            from survey_manager import load_survey_metadata
                            meta = load_survey_metadata(sel_id)
                            if meta:
                                st.session_state.editing_survey_id = sel_id
                                st.session_state.edit_title = meta.get("Title", "")
                                st.session_state.edit_desc = meta.get("Description", "")
                                st.session_state.edit_admin_email = meta.get("Admin_Email", "")
                                
                                demo = meta.get("Demographics", {})
                                st.session_state.edit_type_question = demo.get("type_question", "")
                                st.session_state.edit_type_options = ", ".join(demo.get("type_options", []))
                                st.session_state.edit_demo_gender = demo.get("gender", False)
                                st.session_state.edit_demo_aff = demo.get("affiliation", False)
                                st.session_state.edit_demo_email = demo.get("email", False)
                                st.session_state.edit_demo_name = demo.get("name", False)
                                st.session_state.edit_demo_age = demo.get("age", False)
                                st.session_state.edit_demo_exp = demo.get("experience", False)
                                st.session_state.edit_age_type = demo.get("age_type", "개방형 (숫자 직접 입력)")
                                st.session_state.edit_exp_type = demo.get("experience_type", "개방형 (숫자 직접 입력)")
                                
                                st.session_state.edit_scale_type = meta.get("Scale_Type", "1-9 Continuous")
                                st.session_state.edit_cr_limit = float(meta.get("CR_Limit", 0.1))
                                
                                ahp_model = meta.get("AHP_Model_JSON", {})
                                st.session_state.edit_main_input = ", ".join(ahp_model.get("main", []))
                                st.session_state.edit_sub_inputs = {}
                                for mc, subs in ahp_model.get("subs", {}).items():
                                    st.session_state.edit_sub_inputs[mc] = ", ".join(subs)
                                    
                                definitions = meta.get("Definitions", {})
                                st.session_state.edit_definitions = definitions
                                
                                st.success("성공적으로 불러왔습니다!")
                                st.rerun()
                            else:
                                st.error("설문 데이터를 불러오지 못했습니다.")
                else:
                    st.info("수정할 수 있는 배포된 설문이 없습니다.")
                    
            if st.session_state.editing_survey_id:
                st.warning("⚠️ **주의:** 대항목/소항목 등 AHP 모델 구조를 수정하고 업데이트하면 기존에 수집된 응답 데이터와 열(Column) 불일치로 인한 오류가 발생할 수 있습니다. 모델 구조를 변경하실 경우 가급적 '새 설문 작성'을 권장합니다.")
            
            st.divider()

            from survey_manager import create_survey_sheet, generate_pairwise_combinations

            # 7개 섹션 설문지 생성 폼 구성
            # 섹션 1: 기본 정보
            st.subheader("섹션 1: 설문 기본 정보 설정")"""

with open('f:/app/4. AHP마스터/app.py', 'r', encoding='utf-8') as f:
    content = f.read()

if target in content:
    content = content.replace(target, replacement)
    with open('f:/app/4. AHP마스터/app.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Replaced header successfully")
else:
    print("Target header not found")

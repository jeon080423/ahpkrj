import re

with open('f:/app/4. AHP마스터/app.py', 'r', encoding='utf-8') as f:
    content = f.read()

target = """            # ------------------------------------------------------------
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
                                cr_limit_raw = meta.get("CR_Limit", 0.1)
                                st.session_state.edit_cr_limit = float(cr_limit_raw) if cr_limit_raw is not None and str(cr_limit_raw).lower() != "none" else None
                                
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
                st.warning("⚠️ **주의:** 대항목/소항목 등 AHP 모델 구조를 수정하고 업데이트하면 기존에 수집된 응답 데이터와 열(Column) 불일치로 인한 오류가 발생할 수 있습니다. 모델 구조를 변경하실 경우 가급적 '새 설문 작성'을 권장합니다.")"""

replacement = """            # ------------------------------------------------------------
            # 0. 설문 관리 (1인 1설문 모드)
            # ------------------------------------------------------------
            st.subheader("섹션 0: 내 설문 관리")

            # Initialize states
            if 'editing_survey_id' not in st.session_state:
                st.session_state.editing_survey_id = None
            if 'survey_auto_loaded' not in st.session_state:
                st.session_state.survey_auto_loaded = False

            # Check existing surveys
            gs_surveys = []
            try:
                from survey_manager import get_admin_surveys_from_gsheet
                gs_surveys = get_admin_surveys_from_gsheet(st.session_state.user_id)
            except Exception:
                pass
                
            has_survey = len(gs_surveys) > 0

            # Auto-load logic
            if has_survey and not st.session_state.survey_auto_loaded:
                sel_id = gs_surveys[0][0] # Load the most recent one
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
                    cr_limit_raw = meta.get("CR_Limit", 0.1)
                    st.session_state.edit_cr_limit = float(cr_limit_raw) if cr_limit_raw is not None and str(cr_limit_raw).lower() != "none" else None
                    
                    ahp_model = meta.get("AHP_Model_JSON", {})
                    st.session_state.edit_main_input = ", ".join(ahp_model.get("main", []))
                    st.session_state.edit_sub_inputs = {}
                    for mc, subs in ahp_model.get("subs", {}).items():
                        st.session_state.edit_sub_inputs[mc] = ", ".join(subs)
                        
                    definitions = meta.get("Definitions", {})
                    st.session_state.edit_definitions = definitions
                st.session_state.survey_auto_loaded = True
                st.rerun()

            @st.dialog("⚠️ 기존 설문 삭제 및 새 설문 작성 안내")
            def confirm_new_survey():
                st.warning("새로운 설문을 작성하시면 기존 구글 시트에 저장된 **설문 구조 및 수집된 응답자 데이터 전체**가 영구적으로 삭제됩니다.\\n\\n이 작업은 취소할 수 없습니다.")
                agree = st.checkbox("네, 모든 기존 데이터가 삭제된다는 것을 이해하며 새 설문 작성에 동의합니다.")
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("❌ 취소", use_container_width=True):
                        st.rerun()
                with col2:
                    if st.button("✅ 동의 및 초기화", type="primary", use_container_width=True, disabled=not agree):
                        with st.spinner("기존 데이터를 삭제하는 중입니다..."):
                            from survey_manager import delete_admin_survey
                            if gs_surveys:
                                delete_admin_survey(gs_surveys[0][0], st.session_state.user_id)
                            st.session_state.editing_survey_id = None
                            keys_to_clear = [k for k in st.session_state.keys() if k.startswith('edit_')]
                            for k in keys_to_clear:
                                del st.session_state[k]
                            st.session_state.survey_auto_loaded = False
                        st.success("완료되었습니다. 화면이 새로고침됩니다.")
                        import time
                        time.sleep(1.5)
                        st.rerun()

            if has_survey:
                st.success(f"📌 현재 배포된 설문이 있습니다. 자동으로 불러왔습니다: **{gs_surveys[0][1]}**")
                st.info("아래 폼에서 내용을 수정하신 뒤 하단의 **[배포 및 DB 연동 (수정 내용 적용)]** 버튼을 누르시면 기존 시트에 내용이 덮어씌워집니다.")
                if st.button("✨ 처음부터 새 설문 작성하기 (기존 데이터 삭제)", type="secondary"):
                    confirm_new_survey()
            else:
                st.info("📌 작성 중인 새 설문입니다. 내용을 작성한 뒤 배포해 주세요.")
                if st.button("✨ 폼 내용 모두 지우기 (초기화)", type="secondary"):
                    st.session_state.editing_survey_id = None
                    keys_to_clear = [k for k in st.session_state.keys() if k.startswith('edit_')]
                    for k in keys_to_clear:
                        del st.session_state[k]
                    st.rerun()
"""

# Let's replace the block
# To avoid exact match failing due to minor spacing, I'll use index finding.
start_idx = content.find("            # ------------------------------------------------------------\n            # 0. 설문 관리 (새로 작성 / 기존 수정 모드)")
end_idx = content.find("            st.divider()\n\n            from survey_manager import create_survey_sheet")

if start_idx != -1 and end_idx != -1:
    new_content = content[:start_idx] + replacement + "\n" + content[end_idx:]
    with open('f:/app/4. AHP마스터/app.py', 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("Replaced Section 0 successfully.")
else:
    print("Could not find the start or end index.")

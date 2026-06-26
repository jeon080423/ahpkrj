import sys

def modify_tab1(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Add Tier Level choice to Tab 1
    target1 = """        with st.expander(_("📌 나의 분석 모델 만들기", "📌 Create Custom AHP Model"), expanded=True):
            st.info(_("대항목과 세부항목을 입력하여 나만의 입력 엑셀 템플릿을 생성하세요. 본 템플릿은 일반 AHP 및 퍼지 AHP(Fuzzy AHP) 분석에 공통으로 사용됩니다.\\n\\n현재 입력되어 있는 내용은 샘플 모델입니다. 이용자님의 AHP 모델로 수정할 수 있습니다.",
                      "Enter main criteria and sub-criteria to generate your custom Excel template. This template is used for both traditional AHP and Fuzzy AHP analysis.\\n\\nThe content below is a sample model. You can modify it with your own AHP model."))"""

    replacement1 = """        with st.expander(_("📌 나의 분석 모델 만들기", "📌 Create Custom AHP Model"), expanded=True):
            st.info(_("대항목과 세부항목을 입력하여 나만의 입력 엑셀 템플릿을 생성하세요. 본 템플릿은 일반 AHP 및 퍼지 AHP(Fuzzy AHP) 분석에 공통으로 사용됩니다.\\n\\n현재 입력되어 있는 내용은 샘플 모델입니다. 이용자님의 AHP 모델로 수정할 수 있습니다.",
                      "Enter main criteria and sub-criteria to generate your custom Excel template. This template is used for both traditional AHP and Fuzzy AHP analysis.\\n\\nThe content below is a sample model. You can modify it with your own AHP model."))
            
            # [신규] 3계층 오프라인 지원
            st.markdown("##### ▶ [신규] 계층 구조 설정")
            tier_choice = st.radio(
                "계층 레벨을 선택하세요.", 
                ["2계층 (대분류 - 중분류)", "3계층 (대분류 - 중분류 - 소분류)"], 
                index=0,
                horizontal=True,
                key="tab1_tier_choice"
            )
            tier_level = 3 if "3계층" in tier_choice else 2
            st.markdown("---")"""

    if target1 in content:
        content = content.replace(target1, replacement1)
    else:
        print("Target 1 not found")
        sys.exit(1)

    # 2. Add Sub-subs to model_structure
    target2 = """            model_structure = {}
            if main_criteria_list:
                for mc in main_criteria_list:
                    d_val = default_subs.get(mc, "")
                    if isinstance(d_val, list): d_val = ", ".join(d_val)
                    sub_input = st.text_input(_(f"'{mc}'의 세부항목", f"Sub-criteria for '{mc}'"), value=d_val, key=f"sub_{mc}")
                    sub_list = [x.strip() for x in sub_input.split(',') if x.strip()]
                    model_structure[mc] = sub_list"""

    replacement2 = """            model_structure = {}
            sub_sub_structure = {}
            if main_criteria_list:
                for mc in main_criteria_list:
                    d_val = default_subs.get(mc, "")
                    if isinstance(d_val, list): d_val = ", ".join(d_val)
                    sub_input = st.text_input(_(f"'{mc}'의 세부항목", f"Sub-criteria for '{mc}'"), value=d_val, key=f"tab1_sub_{mc}")
                    sub_list = [x.strip() for x in sub_input.split(',') if x.strip()]
                    model_structure[mc] = sub_list
                    
                    if tier_level == 3 and sub_list:
                        with st.expander(f"▶ '{mc}'의 소분류 (Sub-sub-criteria) 입력", expanded=True):
                            for sub_c in sub_list:
                                sub_sub_input = st.text_input(
                                    f"▶ '{sub_c}'의 소분류 (콤마 구분)", 
                                    value="",
                                    key=f"tab1_sub_sub_{sub_c}"
                                )
                                parsed_sub_subs = [x.strip().replace("_", " ") for x in sub_sub_input.split(",") if x.strip()]
                                if parsed_sub_subs:
                                    sub_sub_structure[sub_c] = parsed_sub_subs"""

    if target2 in content:
        content = content.replace(target2, replacement2)
    else:
        print("Target 2 not found")
        sys.exit(1)

    # 3. Add to save user model and write to excel
    target3 = """                else:
                    current_model = {'main': main_criteria_input, 'subs': model_structure}
                    save_user_model(st.session_state.user_id, current_model)
                    st.toast(_("모델 저장 완료", "Model successfully saved"))
                    
                    output_template = io.BytesIO()
                    with pd.ExcelWriter(output_template, engine='xlsxwriter') as writer:
                        main_pairs = list(itertools.combinations(main_criteria_list, 2))
                        main_cols_tpl = ["ID", "Type"] + [f"{a}_{b}" for a, b in main_pairs]
                        df_template_main = pd.DataFrame(columns=main_cols_tpl)
                        df_template_main.loc[0] = [1, ""] + [0]*len(main_pairs)
                        df_template_main.to_excel(writer, sheet_name="Main_Criteria", index=False)
                        
                        for mc, subs in model_structure.items():
                            if len(subs) < 2:
                                df_sub = pd.DataFrame(columns=["ID", "Type"])
                            else:
                                sub_pairs = list(itertools.combinations(subs, 2))
                                sub_cols = ["ID", "Type"] + [f"{a}_{b}" for a, b in sub_pairs]
                                df_sub = pd.DataFrame(columns=sub_cols)
                                df_sub.loc[0] = [1, ""] + [0]*len(sub_pairs)
                            safe_sheet_name = mc[:31]
                            df_sub.to_excel(writer, sheet_name=safe_sheet_name, index=False)
                    output_template.seek(0)"""

    replacement3 = """                else:
                    current_model = {'main': main_criteria_input, 'subs': model_structure, 'sub_subs': sub_sub_structure, 'Tier_Level': tier_level}
                    save_user_model(st.session_state.user_id, current_model)
                    st.toast(_("모델 저장 완료", "Model successfully saved"))
                    
                    output_template = io.BytesIO()
                    with pd.ExcelWriter(output_template, engine='xlsxwriter') as writer:
                        main_pairs = list(itertools.combinations(main_criteria_list, 2))
                        main_cols_tpl = ["ID", "Type"] + [f"{a}_{b}" for a, b in main_pairs]
                        df_template_main = pd.DataFrame(columns=main_cols_tpl)
                        df_template_main.loc[0] = [1, ""] + [0]*len(main_pairs)
                        df_template_main.to_excel(writer, sheet_name="Main_Criteria", index=False)
                        
                        for mc, subs in model_structure.items():
                            if len(subs) < 2:
                                df_sub = pd.DataFrame(columns=["ID", "Type"])
                            else:
                                sub_pairs = list(itertools.combinations(subs, 2))
                                sub_cols = ["ID", "Type"] + [f"{a}_{b}" for a, b in sub_pairs]
                                df_sub = pd.DataFrame(columns=sub_cols)
                                df_sub.loc[0] = [1, ""] + [0]*len(sub_pairs)
                            safe_sheet_name = mc[:31]
                            df_sub.to_excel(writer, sheet_name=safe_sheet_name, index=False)
                            
                        # 3계층 시트 생성
                        if tier_level == 3:
                            for mc, subs in model_structure.items():
                                for sub_c in subs:
                                    ss_list = sub_sub_structure.get(sub_c, [])
                                    if len(ss_list) < 2:
                                        df_ss = pd.DataFrame(columns=["ID", "Type"])
                                    else:
                                        ss_pairs = list(itertools.combinations(ss_list, 2))
                                        ss_cols = ["ID", "Type"] + [f"{a}_{b}" for a, b in ss_pairs]
                                        df_ss = pd.DataFrame(columns=ss_cols)
                                        df_ss.loc[0] = [1, ""] + [0]*len(ss_pairs)
                                    safe_ss_name = sub_c[:31]
                                    df_ss.to_excel(writer, sheet_name=safe_ss_name, index=False)
                                    
                    output_template.seek(0)"""

    if target3 in content:
        content = content.replace(target3, replacement3)
    else:
        print("Target 3 not found")
        sys.exit(1)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
        
    print("Tab 1 model generator updated.")

if __name__ == "__main__":
    modify_tab1("f:/app/4. AHP마스터/app.py")

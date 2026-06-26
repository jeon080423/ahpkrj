import sys

def modify_excel_parsing(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Target 1: Excel parsing logic
    target1 = """        if data_source == _("📂 엑셀 파일 직접 업로드", "Upload Excel File"):
            uploaded_file = st.file_uploader(_("작성된 엑셀 파일 업로드 (.xlsx)", "Upload completed Excel file (.xlsx)"), type=['xlsx', 'xls'])
            if uploaded_file:
                try:
                    excel_obj = pd.ExcelFile(uploaded_file)
                    sheet_names = excel_obj.sheet_names
                    df_main = pd.read_excel(uploaded_file, sheet_name=sheet_names[0])
                    for sn in sheet_names[1:]:
                        sub_dfs[sn] = pd.read_excel(uploaded_file, sheet_name=sn)
                    filename_base = uploaded_file.name.split('.')[0]
                except Exception as e:
                    st.error(f"엑셀 파일 로드 실패: {e}")"""

    replacement1 = """        if data_source == _("📂 엑셀 파일 직접 업로드", "Upload Excel File"):
            uploaded_file = st.file_uploader(_("작성된 엑셀 파일 업로드 (.xlsx)", "Upload completed Excel file (.xlsx)"), type=['xlsx', 'xls'])
            if uploaded_file:
                try:
                    excel_obj = pd.ExcelFile(uploaded_file)
                    sheet_names = excel_obj.sheet_names
                    df_main = pd.read_excel(uploaded_file, sheet_name=sheet_names[0])
                    
                    # 3계층 식별 로직 (df_main 컬럼에서 _ 포함된 것으로 대분류 요인 도출)
                    main_criteria_infer = set()
                    for col in df_main.columns:
                        if '_' in col:
                            parts = col.split('_')
                            if len(parts) == 2:
                                main_criteria_infer.add(parts[0])
                                main_criteria_infer.add(parts[1])
                    
                    inferred_sub_sub_dfs = {}
                    for sn in sheet_names[1:]:
                        df_sheet = pd.read_excel(uploaded_file, sheet_name=sn)
                        # 안전한 시트명(safe_sheet_name)을 위해 앞부분이 일치하는지 확인
                        is_sub = any(sn == mc[:31] for mc in main_criteria_infer)
                        if is_sub:
                            sub_dfs[sn] = df_sheet
                        else:
                            inferred_sub_sub_dfs[sn] = df_sheet
                    
                    if len(inferred_sub_sub_dfs) > 0:
                        st.session_state["ahp_sub_sub_dfs"] = inferred_sub_sub_dfs
                        st.session_state["inferred_tier_level"] = 3
                    else:
                        st.session_state["inferred_tier_level"] = 2
                        
                    filename_base = uploaded_file.name.split('.')[0]
                except Exception as e:
                    st.error(f"엑셀 파일 로드 실패: {e}")"""

    if target1 in content:
        content = content.replace(target1, replacement1)
    else:
        print("Target 1 not found")
        sys.exit(1)

    # Target 2: tier_level determination before analysis
    target2 = """                if permission_granted:
                    try:
                        tier_level = int(survey_meta.get("Tier_Level", 2)) if 'survey_meta' in locals() else 2
                        
                        if tier_level == 3:"""

    replacement2 = """                if permission_granted:
                    try:
                        if data_source == _("📂 엑셀 파일 직접 업로드", "Upload Excel File"):
                            tier_level = st.session_state.get("inferred_tier_level", 2)
                        else:
                            tier_level = int(survey_meta.get("Tier_Level", 2)) if 'survey_meta' in locals() else 2
                        
                        if tier_level == 3:"""

    if target2 in content:
        content = content.replace(target2, replacement2)
    else:
        print("Target 2 not found")
        sys.exit(1)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
        
    print("Excel parsing logic updated for 3-tier.")

if __name__ == "__main__":
    modify_excel_parsing("f:/app/4. AHP마스터/app.py")

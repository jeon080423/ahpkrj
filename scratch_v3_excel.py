import sys

def rewrite_ahp_utils_v3(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. First, we need to capture main_excluded_df, s_excl_df, ss_excl_df, etc.
    # In run_ahp_analysis_v3, they are already returned!
    # e.g., main_results_df, main_factors, main_excluded, main_excluded_df = fn_process_single_sheet(...)
    # We just need to store them.
    
    # Let's add storage dictionaries at the beginning of run_ahp_analysis_v3
    target_start = "    main_weight_cols = [f\"Weight_{f}\" for f in main_factors]"
    replacement_start = """    # --- Excel Export Data Storage ---
    export_data = {
        "Main": {
            "res_df": main_results_df,
            "excl_df": main_excluded_df,
            "factors": main_factors,
            "group_matrix": None # We will set it below
        },
        "Sub": {},
        "Sub_Sub": {}
    }
    # ---------------------------------
    
    main_weight_cols = [f"Weight_{f}" for f in main_factors]"""
    
    if target_start in content:
        content = content.replace(target_start, replacement_start)
    
    # Store group matrix for Main
    target_main_gm = "    main_group_matrix = np.mean(main_matrices, axis=0) if mean_method == 'arithmetic' else gmean(main_matrices, axis=0)"
    replacement_main_gm = target_main_gm + "\n    export_data['Main']['group_matrix'] = main_group_matrix"
    if target_main_gm in content:
        content = content.replace(target_main_gm, replacement_main_gm)
        
    # Store for Sub
    target_sub_gm = "        s_group_matrix = np.mean(s_matrices, axis=0) if mean_method == 'arithmetic' else gmean(s_matrices, axis=0)"
    replacement_sub_gm = target_sub_gm + """
        export_data['Sub'][parent_factor] = {
            "res_df": s_res_df,
            "excl_df": s_excl_df,
            "factors": s_factors,
            "group_matrix": s_group_matrix
        }"""
    if target_sub_gm in content:
        content = content.replace(target_sub_gm, replacement_sub_gm)
        
    # Store for Sub_Sub
    target_ss_gm = "            ss_group_matrix = np.mean(ss_matrices, axis=0) if mean_method == 'arithmetic' else gmean(ss_matrices, axis=0)"
    replacement_ss_gm = target_ss_gm + """
            export_data['Sub_Sub'][sub_f] = {
                "res_df": ss_res_df,
                "excl_df": ss_excl_df,
                "factors": ss_factors,
                "group_matrix": ss_group_matrix
            }"""
    if target_ss_gm in content:
        content = content.replace(target_ss_gm, replacement_ss_gm)

    # 2. Add write_detailed_sheet_v3 and replace the Excel generation logic
    target_excel_start = "    output_res = io.BytesIO()"
    # We will replace everything from target_excel_start to the end of the function.
    idx = content.find(target_excel_start)
    if idx == -1:
        print("Could not find excel generation logic.")
        return
        
    excel_logic = """    output_res = io.BytesIO()
    is_en = st.session_state.get('lang', 'ko') == 'en'
    
    def add_borders_to_data(worksheet, start_row, start_col, df, border_fmt, has_header=True, has_index=False):
        rows = len(df) + (1 if has_header else 0)
        cols = len(df.columns) + (1 if has_index else 0)
        worksheet.conditional_format(start_row, start_col, start_row+rows-1, start_col+cols-1,
                                      {'type': 'formula', 'criteria': '=TRUE', 'format': border_fmt})

    def write_detailed_sheet_v3(writer, sheet_name, data_dict, is_en=False):
        workbook = writer.book
        res_df = data_dict['res_df']
        excl_df = data_dict['excl_df']
        factors = data_dict['factors']
        g_mat = data_dict['group_matrix']
        
        # Ensure safe sheet name (max 31 chars)
        sheet_name = sheet_name[:31]
        
        # We need an empty dataframe just to create the sheet or write directly
        res_df_no_matrix = res_df.drop(columns=['Matrix_Object']) if 'Matrix_Object' in res_df.columns else res_df
        
        # Just use to_excel with an empty df to initialize the sheet
        pd.DataFrame().to_excel(writer, sheet_name=sheet_name)
        ws = writer.sheets[sheet_name]
        
        formats = {
            'header': workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'bg_color': '#D3D3D3', 'border': 1}),
            'title': workbook.add_format({'bold': True, 'font_size': 12}),
            'border': workbook.add_format({'border': 1}),
            'num': workbook.add_format({'num_format': '0.000', 'border': 1, 'align': 'center'}),
            'center': workbook.add_format({'align': 'center', 'border': 1})
        }
        
        s_row = 1
        # 1. Individual Matrices
        title_text = "📌 Individual Respondent Data & Corrected Matrices" if is_en else "📌 개별 응답자 데이터 및 보정 매트릭스"
        ws.write_string(s_row, 0, title_text, formats['title'])
        s_row += 2
        
        for idx_row, row in res_df.iterrows():
            r_id = row['ID']
            r_type = row['Type']
            r_cr = row.get('CR', row.get('CR(대분류)', row.get('CR(중분류)', row.get('CR(소분류)', 0))))
            matrix = row['Matrix_Object']
            
            label_text = f"🔸 [ID: {r_id}] Type: {r_type} - CR: {r_cr:.4f}"
            ws.write_string(s_row, 0, label_text)
            s_row += 1
            
            m_df = pd.DataFrame(matrix, index=factors, columns=factors)
            m_df.to_excel(writer, sheet_name=sheet_name, startrow=s_row)
            add_borders_to_data(ws, s_row, 0, m_df, formats['border'], has_header=True, has_index=True)
            
            for r in range(len(matrix)):
                for c in range(len(matrix)):
                    ws.write_number(s_row + 1 + r, c + 1, matrix[r][c], formats['num'])
            
            s_row += len(matrix) + 2
            
        # 2. Group Matrix
        title_text = "📌 Group Combined Matrix" if is_en else "📌 그룹 종합 분석 매트릭스"
        ws.write_string(s_row, 0, title_text, formats['title'])
        s_row += 2
        
        gm_df = pd.DataFrame(g_mat, index=factors, columns=factors)
        gm_df.to_excel(writer, sheet_name=sheet_name, startrow=s_row)
        add_borders_to_data(ws, s_row, 0, gm_df, formats['border'], has_header=True, has_index=True)
        
        for r in range(len(g_mat)):
            for c in range(len(g_mat)):
                ws.write_number(s_row + 1 + r, c + 1, g_mat[r][c], formats['num'])
                
        s_row += len(g_mat) + 3
        
        # 3. Detail DataFrame
        title_text = "📌 Individual Response Details" if is_en else "📌 개별 응답 상세 데이터"
        ws.write_string(s_row, 0, title_text, formats['title'])
        s_row += 2
        
        res_df_no_matrix.to_excel(writer, sheet_name=sheet_name, startrow=s_row, index=False)
        for c_idx, col_val in enumerate(res_df_no_matrix.columns):
            ws.write(s_row, c_idx, col_val, formats['header'])
        add_borders_to_data(ws, s_row, 0, res_df_no_matrix, formats['border'], has_header=True, has_index=False)
        s_row += len(res_df_no_matrix) + 3
        
        # 4. Excluded DataFrame
        title_text = "📌 Excluded Data (CR Threshold Exceeded)" if is_en else "📌 일관성 미달 제외 데이터"
        ws.write_string(s_row, 0, title_text, formats['title'])
        s_row += 1
        
        count_text = f"Excluded cases: {len(excl_df)}" if is_en else f"제외된 응답 수: {len(excl_df)}건"
        ws.write_string(s_row, 0, count_text)
        s_row += 1
        
        if len(excl_df) > 0:
            excl_df.to_excel(writer, sheet_name=sheet_name, startrow=s_row, index=False)
            for c_idx, col_val in enumerate(excl_df.columns):
                ws.write(s_row, c_idx, col_val, formats['header'])
            add_borders_to_data(ws, s_row, 0, excl_df, formats['border'], has_header=True, has_index=False)
            
        ws.set_column('A:A', 25)
        ws.set_column('B:Z', 15)

    with pd.ExcelWriter(output_res, engine='xlsxwriter') as writer:
        workbook = writer.book
        
        # Format definitions for summary
        header_fmt = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'bg_color': '#4F81BD', 'font_color': '#FFFFFF', 'border': 1})
        num_fmt = workbook.add_format({'num_format': '0.000', 'align': 'center', 'border': 1})
        center_fmt = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'border': 1})

        # --- 1. 3-Tier Results Sheet (Summary) ---
        sheet_name = '3-Tier 종합결과' if not is_en else '3-Tier Summary'
        final_df.to_excel(writer, sheet_name=sheet_name, index=False, startrow=1)
        ws = writer.sheets[sheet_name]
        
        title_text = "[V3 엔진] 3계층 AHP 종합 가중치 분석 결과" if not is_en else "[V3 Engine] 3-Tier AHP Global Weights Result"
        ws.write_string(0, 0, title_text, workbook.add_format({'bold': True, 'font_size': 14}))
        
        for col_num, value in enumerate(final_df.columns.values):
            ws.write(1, col_num, value, header_fmt)
            
        for row_num in range(len(final_df)):
            for col_num, value in enumerate(final_df.iloc[row_num]):
                if isinstance(value, (int, float)):
                    if col_num == len(final_df.columns) - 1: # Rank
                        ws.write(row_num + 2, col_num, value, center_fmt)
                    else:
                        ws.write(row_num + 2, col_num, value, num_fmt)
                else:
                    ws.write(row_num + 2, col_num, value, center_fmt)
                    
        ws.set_column('A:A', 20)
        ws.set_column('B:B', 15)
        ws.set_column('C:C', 20)
        ws.set_column('D:D', 15)
        ws.set_column('E:E', 25)
        ws.set_column('F:F', 15)
        ws.set_column('G:G', 15)
        ws.set_column('H:H', 15)

        # --- 2. Detailed Sheets ---
        # Main
        if export_data['Main']['res_df'] is not None and not export_data['Main']['res_df'].empty:
            write_detailed_sheet_v3(writer, 'Main_Criteria', export_data['Main'], is_en)
            
        # Sub
        for k, v in export_data['Sub'].items():
            if v['res_df'] is not None and not v['res_df'].empty:
                write_detailed_sheet_v3(writer, str(k), v, is_en)
                
        # Sub_Sub
        for k, v in export_data['Sub_Sub'].items():
            if v['res_df'] is not None and not v['res_df'].empty:
                write_detailed_sheet_v3(writer, str(k), v, is_en)

    output_res.seek(0)
    
    return True, "Analysis Successful" if is_en else "분석 성공", final_df, output_res
"""
    
    content = content[:idx] + excel_logic
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
        
    print("Done")

if __name__ == "__main__":
    rewrite_ahp_utils_v3("f:/app/4. AHP마스터/ahp_utils_v3.py")

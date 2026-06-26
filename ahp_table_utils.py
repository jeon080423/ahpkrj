import streamlit as st
def _(ko_text, en_text):
    if st.session_state.get("lang", "ko") == "en": return en_text
    return ko_text

def write_custom_ahp_table(writer, sheet_name, df, title_text, start_row, formats, excluded_df=None):
    workbook = writer.book
    if sheet_name in writer.sheets: worksheet = writer.sheets[sheet_name]
    else:
        worksheet = workbook.add_worksheet(sheet_name)
        writer.sheets[sheet_name] = worksheet

    header_fmt = formats['header']
    merge_fmt = formats['merge']
    body_fmt = formats['body']
    num_fmt = formats['num']
    sum_row_fmt = formats['sum_row']

    # [신규 추가] 제외 사례수 및 제외 응답값 데이터 출력
    if excluded_df is not None:
        worksheet.write(start_row, 0, _(f"※ 분석 제외 사례수: {len(excluded_df)}건", f"※ Number of cases excluded: {len(excluded_df)}"), workbook.add_format({'bold': True, 'font_color': 'red'}))
        start_row += 1
        if not excluded_df.empty:
            worksheet.write(start_row, 0, _("▶ 제외된 응답 데이터 (보정 실패)", "▶ Excluded Response Data (Correction Failed)"), workbook.add_format({'bold': True}))
            start_row += 1
            excluded_df.to_excel(writer, sheet_name=sheet_name, startrow=start_row, index=False)
            start_row += len(excluded_df) + 2
    
    worksheet.merge_range(start_row, 0, start_row, 6, title_text, workbook.add_format({'bold': True, 'font_size': 12}))
    start_row += 1

    headers = _(
        ["대분류", "가중치(a)", "중분류", "가중치(b)", "종합 가중치(a x b)", "종합 순위", "비고"],
        ["Main Criteria", "Weight(a)", "Sub-Criteria", "Weight(b)", "Global Weight(a x b)", "Global Rank", "Remarks"]
    )
    for col, h in enumerate(headers):
        worksheet.write(start_row, col, h, header_fmt)
    start_row += 1

    main_criteria = df['대분류'].unique()
    current_row = start_row

    for main_c in main_criteria:
        sub_df = df[df['대분류'] == main_c]
        n_subs = len(sub_df)
        main_w = sub_df.iloc[0]['대분류 가중치']
        sub_cr = sub_df.iloc[0]['CR(중분류)']
        sub_ci = sub_df.iloc[0]['CI(중분류)'] if 'CI(중분류)' in sub_df.columns else 0.0
        sum_sub_w = sub_df['중분류 가중치'].sum()
    
        merge_span = n_subs + 2 
        if merge_span > 1:
            worksheet.merge_range(current_row, 0, current_row + merge_span - 1, 0, main_c, merge_fmt)
            worksheet.merge_range(current_row, 1, current_row + merge_span - 1, 1, main_w, num_fmt)
        else:
            worksheet.write(current_row, 0, main_c, merge_fmt)
            worksheet.write(current_row, 1, main_w, num_fmt)
        
        for idx, row in sub_df.iterrows():
            worksheet.write(current_row, 2, row['중분류'], body_fmt)
            worksheet.write(current_row, 3, row['중분류 가중치'], num_fmt)
            worksheet.write(current_row, 4, row['Global Weight'], num_fmt)
            worksheet.write(current_row, 5, row['Global Rank'], body_fmt)
            worksheet.write(current_row, 6, "", body_fmt)
            current_row += 1
    
        worksheet.write(current_row, 2, _("합계", "Total"), sum_row_fmt)
        worksheet.write(current_row, 3, sum_sub_w, formats['sum_val'])
        worksheet.write_blank(current_row, 4, "", sum_row_fmt)
        worksheet.write_blank(current_row, 5, "", sum_row_fmt)
        worksheet.write_blank(current_row, 6, "", sum_row_fmt)
        current_row += 1
    
        worksheet.write(current_row, 2, _("일관성 비율(CR)", "Consistency Ratio (CR)"), sum_row_fmt)
        worksheet.write(current_row, 3, sub_cr, formats['num_sum'])
        worksheet.write(current_row, 4, _("일관성 지수(CI)", "Consistency Index (CI)"), sum_row_fmt)
        worksheet.write(current_row, 5, sub_ci, formats['num_sum'])
        worksheet.write_blank(current_row, 6, "", sum_row_fmt)
        current_row += 1
    
    worksheet.write(current_row, 0, _("합계", "Total"), sum_row_fmt)
    worksheet.write(current_row, 1, 1, formats['sum_val'])
    worksheet.write_blank(current_row, 2, "", sum_row_fmt)
    worksheet.write_blank(current_row, 3, "", sum_row_fmt)
    worksheet.write_blank(current_row, 4, "", sum_row_fmt)
    worksheet.write_blank(current_row, 5, "", sum_row_fmt)
    worksheet.write_blank(current_row, 6, "", sum_row_fmt)

    # [신규 추가] 대분류의 일관성 비율(CR) 및 일관성 지수(CI) 출력
    main_cr = df.iloc[0]['CR(대분류)'] if 'CR(대분류)' in df.columns else 0.0
    main_ci = df.iloc[0]['CI(대분류)'] if 'CI(대분류)' in df.columns else 0.0

    current_row += 1
    worksheet.write(current_row, 0, _("일관성 비율(CR)", "Consistency Ratio (CR)"), sum_row_fmt)
    worksheet.write(current_row, 1, main_cr, formats['num_sum'])
    worksheet.write(current_row, 2, _("일관성 지수(CI)", "Consistency Index (CI)"), sum_row_fmt)
    worksheet.write(current_row, 3, main_ci, formats['num_sum'])
    worksheet.write_blank(current_row, 4, "", sum_row_fmt)
    worksheet.write_blank(current_row, 5, "", sum_row_fmt)
    worksheet.write_blank(current_row, 6, "", sum_row_fmt)

    worksheet.set_column('A:A', 15)
    worksheet.set_column('B:B', 12)
    worksheet.set_column('C:C', 25)
    worksheet.set_column('D:F', 12)
    return current_row + 2
    
def add_borders_to_data(worksheet, start_row, start_col, df, border_fmt, has_header=True, has_index=False):
    rows = len(df) + (1 if has_header else 0)
    cols = len(df.columns) + (1 if has_index else 0)
    worksheet.conditional_format(start_row, start_col, start_row+rows-1, start_col+cols-1,
                                  {'type': 'formula', 'criteria': '=TRUE', 'format': border_fmt})
    
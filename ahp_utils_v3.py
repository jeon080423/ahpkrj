import pandas as pd
import numpy as np
from scipy.stats import gmean, f_oneway
import io
import streamlit as st
import itertools

# ANOVA and post-hoc library
try:
    from statsmodels.stats.multicomp import pairwise_tukeyhsd
    STATSMODELS_AVAILABLE = True
except ImportError:
    STATSMODELS_AVAILABLE = False

# Translation helper function matching app.py
def _(ko_text, en_text):
    if st.session_state.get('lang', 'ko') == 'en':
        return en_text
    return ko_text

# Saaty's consistency calculations to prevent circular imports
def get_ri(n):
    ri_dict = {1: 0.00, 2: 0.00, 3: 0.58, 4: 0.90, 5: 1.12, 6: 1.24, 7: 1.32, 8: 1.41, 9: 1.45, 10: 1.49}
    return ri_dict.get(n, 1.49)

def calculate_weights(matrix, method='geometric'):
    n = matrix.shape[0]
    if method == 'arithmetic':
        # Handle zero or negative values safely
        matrix_safe = np.where(matrix <= 0, 1e-5, matrix)
        col_sum = matrix_safe.sum(axis=0)
        col_sum[col_sum == 0] = 1
        normalized_matrix = matrix_safe / col_sum
        weights = normalized_matrix.mean(axis=1)
    else:
        # Handle zero or negative values safely
        matrix_safe = np.where(matrix <= 0, 1e-5, matrix)
        geom_means = gmean(matrix_safe, axis=1)
        geom_sum = geom_means.sum()
        if geom_sum == 0 or np.isnan(geom_sum) or np.isinf(geom_sum):
            weights = np.ones(n) / n
        else:
            weights = geom_means / geom_sum
    return weights

def calculate_consistency(matrix, method='geometric'):
    n = matrix.shape[0]
    if n <= 2: return 0.0, 0.0, n
    weights = calculate_weights(matrix, method)
    # Ensure no NaNs or Infs in matrix/weights before dot product
    matrix_safe = np.where(np.isnan(matrix) | np.isinf(matrix), 1.0, matrix)
    weights_safe = np.where(np.isnan(weights) | np.isinf(weights), 1.0 / n, weights)
    weights_safe[weights_safe == 0] = 1e-10
    
    weighted_sum = matrix_safe.dot(weights_safe)
    lambda_values = weighted_sum / weights_safe
    lambda_max = lambda_values.mean()
    if np.isnan(lambda_max) or np.isinf(lambda_max):
        lambda_max = n
        
    ci = (lambda_max - n) / (n - 1)
    ri = get_ri(n)
    cr = ci / ri if ri > 0 else 0.0
    
    if np.isnan(cr) or np.isinf(cr):
        cr = 0.0
    if np.isnan(ci) or np.isinf(ci):
        ci = 0.0
        
    return cr, ci, lambda_max

def calculate_anova_and_posthoc(full_data):
    results = []
    unique_factors = full_data['Factor'].unique()
    
    for factor in unique_factors:
        subset = full_data[full_data['Factor'] == factor]
        groups = [group['Global_Weight'].values for name, group in subset.groupby('Type')]
        
        if len(groups) < 2:
            continue
            
        f_stat, p_val = f_oneway(*groups)
        
        row = {
            "요인": factor,
            "F-값": f_stat,
            "P-Value": p_val,
            "유의성": "유의함" if p_val < 0.05 else "유의하지 않음",
            "사후검정(Tukey HSD)": ""
        }
        
        if p_val < 0.05 and STATSMODELS_AVAILABLE:
            try:
                # statsmodels pairwise Tukey HSD
                tukey = pairwise_tukeyhsd(endog=subset['Global_Weight'], groups=subset['Type'], alpha=0.05)
                tukey_df = pd.DataFrame(data=tukey.summary().data[1:], columns=tukey.summary().data[0])
                sig_pairs = tukey_df[tukey_df['reject'] == True]
                if not sig_pairs.empty:
                    pairs_str = []
                    for idx_row, r in sig_pairs.iterrows():
                        pairs_str.append(f"{r['group1']} vs {r['group2']}")
                    row["사후검정(Tukey HSD)"] = ", ".join(pairs_str) + " 차이 있음"
                else:
                    row["사후검정(Tukey HSD)"] = "집단 간 구체적 차이 발견 못함"
            except Exception as e:
                row["사후검정(Tukey HSD)"] = "계산 오류"
        
        results.append(row)
        
    return pd.DataFrame(results)

def safe_float(val):
    if pd.isnull(val) or np.isnan(val) or np.isinf(val):
        return 0.0
    return float(val)

def write_custom_ahp_table_v3(writer, sheet_name, df, title_text, start_row, formats, excluded_df=None):
    workbook = writer.book
    if sheet_name in writer.sheets: 
        worksheet = writer.sheets[sheet_name]
    else:
        worksheet = workbook.add_worksheet(sheet_name)
        writer.sheets[sheet_name] = worksheet

    header_fmt = formats['header']
    merge_fmt = formats['merge']
    body_fmt = formats['body']
    num_fmt = formats['num']
    sum_row_fmt = formats['sum_row']
    sum_val_fmt = formats['sum_val']
    num_sum_fmt = formats['num_sum']

    # Show excluded cases count
    if excluded_df is not None:
        worksheet.write(start_row, 0, _(f"※ 분석 제외 사례수: {len(excluded_df)}건", f"※ Number of cases excluded: {len(excluded_df)}"), workbook.add_format({'bold': True, 'font_color': 'red'}))
        start_row += 1
        if not excluded_df.empty:
            worksheet.write(start_row, 0, _("▶ 제외된 응답 데이터 (보정 실패)", "▶ Excluded Response Data (Correction Failed)"), workbook.add_format({'bold': True}))
            start_row += 1
            # Filter Matrix_Object columns out
            ex_cols = [c for c in excluded_df.columns if c not in ['Matrix_Object', 'Orig_Matrix_Object', 'Sheet']]
            excluded_df[ex_cols].to_excel(writer, sheet_name=sheet_name, startrow=start_row, index=False)
            start_row += len(excluded_df) + 2

    # Draw table title
    worksheet.merge_range(start_row, 0, start_row, 8, title_text, workbook.add_format({'bold': True, 'font_size': 12}))
    start_row += 1

    # Table headers
    headers = _(
        ["대분류", "가중치(a)", "중분류", "가중치(b)", "소분류", "가중치(c)", "종합 가중치(a x b x c)", "종합 순위", "비고"],
        ["Main Criteria", "Weight(a)", "Sub-Criteria", "Weight(b)", "Sub-sub-Criteria", "Weight(c)", "Global Weight(a x b x c)", "Global Rank", "Remarks"]
    )
    for col, h in enumerate(headers):
        worksheet.write(start_row, col, h, header_fmt)
    start_row += 1

    current_row = start_row
    main_criteria = df['대분류'].unique()

    for main_c in main_criteria:
        sub_df = df[df['대분류'] == main_c]
        main_w = sub_df.iloc[0]['대분류 가중치']
        main_cr = sub_df.iloc[0]['CR(대분류)'] if 'CR(대분류)' in sub_df.columns else 0.0
        main_ci = sub_df.iloc[0]['CI(대분류)'] if 'CI(대분류)' in sub_df.columns else 0.0

        main_start_row = current_row

        unique_subs = sub_df['중분류'].unique()
        for sub_c in unique_subs:
            sub_sub_df = sub_df[sub_df['중분류'] == sub_c]
            sub_w = sub_sub_df.iloc[0]['중분류 가중치']
            sub_cr = sub_sub_df.iloc[0]['CR(중분류)'] if 'CR(중분류)' in sub_sub_df.columns else 0.0
            sub_ci = sub_sub_df.iloc[0]['CI(중분류)'] if 'CI(중분류)' in sub_sub_df.columns else 0.0

            sub_start_row = current_row

            # Check if this sub-criteria is a leaf node (dummy sub-sub-criteria)
            is_leaf = len(sub_sub_df) == 1 and (
                str(sub_sub_df.iloc[0]['소분류']).endswith("_단일항목") or
                str(sub_sub_df.iloc[0]['소분류']).endswith("단일항목")
            )

            if is_leaf:
                # Leaf node: write single row without sub-sub total or consistency
                worksheet.write(current_row, 4, "-", body_fmt)
                worksheet.write(current_row, 5, "-", body_fmt)
                worksheet.write(current_row, 6, safe_float(sub_sub_df.iloc[0]['Global Weight']), num_fmt)
                worksheet.write(current_row, 7, sub_sub_df.iloc[0]['Global Rank'], body_fmt)
                worksheet.write(current_row, 8, "", body_fmt)
                current_row += 1
            else:
                for idx, row in sub_sub_df.iterrows():
                    worksheet.write(current_row, 4, row['소분류'], body_fmt)
                    worksheet.write(current_row, 5, safe_float(row['소분류 가중치']), num_fmt)
                    worksheet.write(current_row, 6, safe_float(row['Global Weight']), num_fmt)
                    worksheet.write(current_row, 7, row['Global Rank'], body_fmt)
                    worksheet.write(current_row, 8, "", body_fmt)
                    current_row += 1

                # Sub-Sub Total
                worksheet.write(current_row, 4, _("합계", "Total"), sum_row_fmt)
                worksheet.write(current_row, 5, safe_float(sub_sub_df['소분류 가중치'].sum()), sum_val_fmt)
                worksheet.write_blank(current_row, 6, "", sum_row_fmt)
                worksheet.write_blank(current_row, 7, "", sum_row_fmt)
                worksheet.write_blank(current_row, 8, "", sum_row_fmt)
                current_row += 1

                # Sub-Sub CR / CI
                sub_sub_cr = sub_sub_df.iloc[0]['CR(소분류)'] if 'CR(소분류)' in sub_sub_df.columns else 0.0
                sub_sub_ci = sub_sub_df.iloc[0]['CI(소분류)'] if 'CI(소분류)' in sub_sub_df.columns else 0.0
                worksheet.write(current_row, 4, _("일관성 비율(CR)", "Consistency Ratio (CR)"), sum_row_fmt)
                worksheet.write(current_row, 5, safe_float(sub_sub_cr), num_sum_fmt)
                worksheet.write(current_row, 6, _("일관성 지수(CI)", "Consistency Index (CI)"), sum_row_fmt)
                worksheet.write(current_row, 7, safe_float(sub_sub_ci), num_sum_fmt)
                worksheet.write_blank(current_row, 8, "", sum_row_fmt)
                current_row += 1

            sub_end_row = current_row - 1

            # Merge Sub-Criteria Name and Weight
            if sub_start_row < sub_end_row:
                worksheet.merge_range(sub_start_row, 2, sub_end_row, 2, sub_c, merge_fmt)
                worksheet.merge_range(sub_start_row, 3, sub_end_row, 3, safe_float(sub_w), num_fmt)
            else:
                worksheet.write(sub_start_row, 2, sub_c, merge_fmt)
                worksheet.write(sub_start_row, 3, safe_float(sub_w), num_fmt)

        # Sub Total
        worksheet.write(current_row, 2, _("합계", "Total"), sum_row_fmt)
        worksheet.write(current_row, 3, safe_float(sub_df.drop_duplicates(subset=['중분류'])['중분류 가중치'].sum()), sum_val_fmt)
        worksheet.write_blank(current_row, 4, "", sum_row_fmt)
        worksheet.write_blank(current_row, 5, "", sum_row_fmt)
        worksheet.write_blank(current_row, 6, "", sum_row_fmt)
        worksheet.write_blank(current_row, 7, "", sum_row_fmt)
        worksheet.write_blank(current_row, 8, "", sum_row_fmt)
        current_row += 1

        # Sub CR / CI
        worksheet.write(current_row, 2, _("일관성 비율(CR)", "Consistency Ratio (CR)"), sum_row_fmt)
        worksheet.write(current_row, 3, safe_float(sub_cr), num_sum_fmt)
        worksheet.write(current_row, 4, _("일관성 지수(CI)", "Consistency Index (CI)"), sum_row_fmt)
        worksheet.write(current_row, 5, safe_float(sub_ci), num_sum_fmt)
        worksheet.write_blank(current_row, 6, "", sum_row_fmt)
        worksheet.write_blank(current_row, 7, "", sum_row_fmt)
        worksheet.write_blank(current_row, 8, "", sum_row_fmt)
        current_row += 1

        main_end_row = current_row - 1

        # Merge Main Criteria Name and Weight
        if main_start_row < main_end_row:
            worksheet.merge_range(main_start_row, 0, main_end_row, 0, main_c, merge_fmt)
            worksheet.merge_range(main_start_row, 1, main_end_row, 1, safe_float(main_w), num_fmt)
        else:
            worksheet.write(main_start_row, 0, main_c, merge_fmt)
            worksheet.write(main_start_row, 1, safe_float(main_w), num_fmt)

    # Main Total
    worksheet.write(current_row, 0, _("합계", "Total"), sum_row_fmt)
    worksheet.write(current_row, 1, 1, formats['sum_val'])
    worksheet.write_blank(current_row, 2, "", sum_row_fmt)
    worksheet.write_blank(current_row, 3, "", sum_row_fmt)
    worksheet.write_blank(current_row, 4, "", sum_row_fmt)
    worksheet.write_blank(current_row, 5, "", sum_row_fmt)
    worksheet.write_blank(current_row, 6, "", sum_row_fmt)
    worksheet.write_blank(current_row, 7, "", sum_row_fmt)
    worksheet.write_blank(current_row, 8, "", sum_row_fmt)
    current_row += 1

    # Main CR / CI
    main_cr_global = df.iloc[0]['CR(대분류)'] if 'CR(대분류)' in df.columns else 0.0
    main_ci_global = df.iloc[0]['CI(대분류)'] if 'CI(대분류)' in df.columns else 0.0
    worksheet.write(current_row, 0, _("일관성 비율(CR)", "Consistency Ratio (CR)"), sum_row_fmt)
    worksheet.write(current_row, 1, safe_float(main_cr_global), num_sum_fmt)
    worksheet.write(current_row, 2, _("일관성 지수(CI)", "Consistency Index (CI)"), sum_row_fmt)
    worksheet.write(current_row, 3, safe_float(main_ci_global), num_sum_fmt)
    worksheet.write_blank(current_row, 4, "", sum_row_fmt)
    worksheet.write_blank(current_row, 5, "", sum_row_fmt)
    worksheet.write_blank(current_row, 6, "", sum_row_fmt)
    worksheet.write_blank(current_row, 7, "", sum_row_fmt)
    worksheet.write_blank(current_row, 8, "", sum_row_fmt)
    
    # Auto-fit columns
    worksheet.set_column('A:A', 15)
    worksheet.set_column('B:B', 12)
    worksheet.set_column('C:C', 20)
    worksheet.set_column('D:D', 12)
    worksheet.set_column('E:E', 25)
    worksheet.set_column('F:I', 12)

    return current_row + 2

def write_detailed_sheet_ws(writer, sheet_name, matrix_df, detail_df, matrix_title, row_labels, group_matrices=None, sheet_excl_count=0, mean_method='geometric'):
    workbook = writer.book
    ws = workbook.add_worksheet(sheet_name)
    writer.sheets[sheet_name] = ws
    s_row_det = 0

    border_fmt = workbook.add_format({'border': 1})
    fmt_diagonal = workbook.add_format({'num_format': '0', 'align': 'center', 'valign': 'vcenter', 'bg_color': '#E7E6E6', 'border': 1})
    fmt_float_no_border = workbook.add_format({'num_format': '0.000', 'align': 'center', 'valign': 'vcenter', 'border': 1})
    
    ci_cr_header_fmt = workbook.add_format({
        'bold': True, 'align': 'center', 'valign': 'vcenter',
        'bg_color': '#4F81BD', 'font_color': '#FFFFFF', 'border': 1,
        'font_name': 'NanumGothic'
    })
    ci_cr_label_fmt = workbook.add_format({
        'bold': True, 'align': 'center', 'valign': 'vcenter',
        'bg_color': '#D9E1F2', 'border': 1,
        'font_name': 'NanumGothic'
    })
    
    # Excluded cases count
    excl_label = _(f"분석 제외 사례수: {sheet_excl_count}건", f"Excluded cases: {sheet_excl_count}")
    ws.write(s_row_det, 0, excl_label, workbook.add_format({'bold': True, 'font_color': 'red'}))
    s_row_det += 1

    ws.write_string(s_row_det, 0, matrix_title)
    s_row_det += 1
    
    m_df_obj = pd.DataFrame(matrix_df, index=row_labels, columns=row_labels)
    m_df_obj.to_excel(writer, sheet_name=sheet_name, startrow=s_row_det)
    
    ws.conditional_format(s_row_det, 0, s_row_det + len(matrix_df), len(matrix_df), {'type': 'formula', 'criteria': '=TRUE', 'format': border_fmt})
    
    for r in range(len(matrix_df)):
        for c in range(len(matrix_df)):
            val = 1.0 if r == c else matrix_df[r][c]
            ws.write(s_row_det + r + 1, c + 1, safe_float(val), border_fmt if r != c else fmt_diagonal)
            if r != c: 
                ws.write(s_row_det + r + 1, c + 1, safe_float(val), fmt_float_no_border)

    # CR, CI indicators for overall matrix
    n_dim = len(matrix_df)
    cr_val, ci_val, _unused = calculate_consistency(matrix_df, mean_method)
    
    ci_cr_val_fmt = workbook.add_format({
        'align': 'center', 'valign': 'vcenter', 'border': 1,
        'num_format': '0.000',
        'font_name': 'NanumGothic'
    })
    if cr_val > 0.1:
        ci_cr_val_fmt = workbook.add_format({
            'align': 'center', 'valign': 'vcenter', 'border': 1,
            'num_format': '0.000',
            'bg_color': '#FFC7CE', 'font_color': '#9C0006',
            'font_name': 'NanumGothic'
        })

    ws.set_column(n_dim + 2, n_dim + 2, 12)
    ws.set_column(n_dim + 3, n_dim + 3, 12)

    ws.merge_range(s_row_det, n_dim + 2, s_row_det, n_dim + 3, _("전체 일관성 지표", "Overall Consistency Indicators"), ci_cr_header_fmt)
    ws.write(s_row_det + 1, n_dim + 2, _("전체 CI", "Overall CI"), ci_cr_label_fmt)
    ws.write(s_row_det + 1, n_dim + 3, safe_float(ci_val), ci_cr_val_fmt)
    ws.write(s_row_det + 2, n_dim + 2, _("전체 CR", "Overall CR"), ci_cr_label_fmt)
    ws.write(s_row_det + 2, n_dim + 3, safe_float(cr_val), ci_cr_val_fmt)

    s_row_det += len(matrix_df) + 3

    # Group matrices
    if group_matrices:
        for g_name, g_mat in group_matrices.items():
            ws.write_string(s_row_det, 0, _(f"] 그룹 종합 행렬: {g_name}", f"] Group Combined Matrix: {g_name}"))
            s_row_det += 1
            gm_df_obj = pd.DataFrame(g_mat, index=row_labels, columns=row_labels)
            gm_df_obj.to_excel(writer, sheet_name=sheet_name, startrow=s_row_det)
            
            ws.conditional_format(s_row_det, 0, s_row_det + len(g_mat), len(g_mat), {'type': 'formula', 'criteria': '=TRUE', 'format': border_fmt})
            
            for r in range(len(g_mat)):
                for c in range(len(g_mat)):
                    val = 1.0 if r == c else g_mat[r][c]
                    ws.write(s_row_det + r + 1, c + 1, safe_float(val), border_fmt if r != c else fmt_diagonal)
                    if r != c: 
                        ws.write(s_row_det + r + 1, c + 1, safe_float(val), fmt_float_no_border)
            
            g_cr_val, g_ci_val, _unused2 = calculate_consistency(g_mat, mean_method)
            g_ci_cr_val_fmt = workbook.add_format({
                'align': 'center', 'valign': 'vcenter', 'border': 1,
                'num_format': '0.000',
                'font_name': 'NanumGothic'
            })
            if g_cr_val > 0.1:
                g_ci_cr_val_fmt = workbook.add_format({
                    'align': 'center', 'valign': 'vcenter', 'border': 1,
                    'num_format': '0.000',
                    'bg_color': '#FFC7CE', 'font_color': '#9C0006',
                    'font_name': 'NanumGothic'
                })

            ws.merge_range(s_row_det, n_dim + 2, s_row_det, n_dim + 3, _("그룹 일관성 지표", "Group Consistency Indicators"), ci_cr_header_fmt)
            ws.write(s_row_det + 1, n_dim + 2, _("그룹 CI", "Group CI"), ci_cr_label_fmt)
            ws.write(s_row_det + 1, n_dim + 3, safe_float(g_ci_val), g_ci_cr_val_fmt)
            ws.write(s_row_det + 2, n_dim + 2, _("그룹 CR", "Group CR"), ci_cr_label_fmt)
            ws.write(s_row_det + 2, n_dim + 3, safe_float(g_cr_val), g_ci_cr_val_fmt)
            
            s_row_det += len(g_mat) + 3

    # Individual details DataFrame
    detail_df.to_excel(writer, sheet_name=sheet_name, startrow=s_row_det, index=False)
    
    header_style = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'bg_color': '#D3D3D3', 'border': 1})
    body_style = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'border': 1})
    num_style = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'border': 1, 'num_format': '0.000'})
    yellow_style = workbook.add_format({'bg_color': 'yellow', 'border': 1, 'align': 'center', 'num_format': '0.000'})

    for c_idx, col_val in enumerate(detail_df.columns):
        ws.write(s_row_det, c_idx, col_val, header_style)

    ws.conditional_format(s_row_det + 1, 0, s_row_det + len(detail_df), len(detail_df.columns) - 1, {'type': 'formula', 'criteria': '=TRUE', 'format': border_fmt})

    for r_idx in range(len(detail_df)):
        row_pos = s_row_det + 1 + r_idx
        for c_idx, col_name in enumerate(detail_df.columns):
            val = detail_df.iloc[r_idx, c_idx]
            current_fmt = border_fmt
            if col_name in ['Original_CR', 'Final_CR'] and isinstance(val, (float, int)) and val > 0.1:
                current_fmt = yellow_style
            elif isinstance(val, (float, np.float64)):
                current_fmt = num_style
            else:
                current_fmt = body_style
            
            if pd.isnull(val):
                ws.write_blank(row_pos, c_idx, "", current_fmt)
            else:
                ws.write(row_pos, c_idx, val, current_fmt)

    ws.set_column('A:A', 25)
    ws.set_column('B:Z', 15)

def run_ahp_analysis_v3(df_main, sub_dfs, sub_sub_dfs, cr_threshold, max_iter_val, learning_rate, mean_method, ahp_method, fn_process_single_sheet, fn_fuzzy_ahp):
    """
    [3계층 전용] 고도화된 AHP 분석 및 엑셀 다운로드 파일 생성 엔진.
    """
    st.info("⚙️ 3계층 AHP 종합 분석 및 결과물 고도화 연산을 수행합니다...")

    # 1. 대분류 분석
    try:
        main_results_df, main_factors, main_excluded, main_excluded_df = fn_process_single_sheet(
            df_main, cr_threshold, max_iter_val, learning_rate, mean_method, ahp_method
        )
    except Exception as e:
        return False, f"대분류 분석 중 오류가 발생했습니다: {e}", None, None

    if main_results_df.empty:
        return False, "대분류 유효 응답이 부족하여 분석을 진행할 수 없습니다.", None, None

    # Excluded files storage list
    total_excl_df_list = [main_excluded_df]

    # Overall Main Matrix and Weights
    main_weight_cols = [f"Weight_{f}" for f in main_factors]
    main_matrices = np.stack(main_results_df['Matrix_Object'].values)
    main_group_matrix = np.mean(main_matrices, axis=0) if mean_method == 'arithmetic' else gmean(main_matrices, axis=0)
    main_grp_cr, main_grp_ci, _unused = calculate_consistency(main_group_matrix, method=mean_method)

    if ahp_method == 'fuzzy':
        mw_vals, main_group_Si = fn_fuzzy_ahp(main_group_matrix)
        group_main_weights = pd.Series(mw_vals, index=main_weight_cols)
    else:
        main_group_Si = None
        if mean_method == 'arithmetic':
            group_main_weights = main_results_df[main_weight_cols].mean(axis=0)
        else:
            group_main_weights = gmean(main_results_df[main_weight_cols].values, axis=0)
        group_main_weights = group_main_weights / group_main_weights.sum()

    # Storage for export
    export_data = {
        "Main": {
            "res_df": main_results_df,
            "excl_df": main_excluded_df,
            "factors": main_factors,
            "group_matrix": main_group_matrix,
            "group_Si": main_group_Si,
            "group_w": group_main_weights
        },
        "Sub": {},
        "Sub_Sub": {}
    }

    # 2. 중분류 분석
    sub_results_storage = {}
    for parent_factor in main_factors:
        sdf = sub_dfs.get(parent_factor)
        if sdf is None or len(sdf) == 0:
            continue
        
        s_res_df, s_factors, s_excl, s_excl_df = fn_process_single_sheet(sdf, cr_threshold, max_iter_val, learning_rate, mean_method, ahp_method)
        if s_res_df.empty:
            continue

        if not s_excl_df.empty:
            s_excl_df['Sheet'] = parent_factor
            total_excl_df_list.append(s_excl_df)
            
        s_weight_cols = [f"Weight_{f}" for f in s_factors]
        s_matrices = np.stack(s_res_df['Matrix_Object'].values)
        s_group_matrix = np.mean(s_matrices, axis=0) if mean_method == 'arithmetic' else gmean(s_matrices, axis=0)
        s_grp_cr, s_grp_ci, _unused2 = calculate_consistency(s_group_matrix, method=mean_method)
        
        if ahp_method == 'fuzzy':
            sw_vals, sub_group_Si = fn_fuzzy_ahp(s_group_matrix)
            group_sub_weights = pd.Series(sw_vals, index=s_weight_cols)
        else:
            sub_group_Si = None
            if mean_method == 'arithmetic':
                group_sub_weights = s_res_df[s_weight_cols].mean(axis=0)
            else:
                group_sub_weights = gmean(s_res_df[s_weight_cols].values, axis=0)
            group_sub_weights = group_sub_weights / group_sub_weights.sum()
            
        sub_results_storage[parent_factor] = {
            "factors": s_factors,
            "weights": group_sub_weights,
            "df": s_res_df,
            "group_matrix": s_group_matrix,
            "group_cr": s_grp_cr,
            "group_ci": s_grp_ci
        }

        export_data['Sub'][parent_factor] = {
            "res_df": s_res_df,
            "excl_df": s_excl_df,
            "factors": s_factors,
            "group_matrix": s_group_matrix,
            "group_Si": sub_group_Si,
            "group_w": group_sub_weights
        }

    # 3. 소분류 분석 (3계층)
    sub_sub_results_storage = {}
    for main_f, s_info in sub_results_storage.items():
        for sub_f in s_info['factors']:
            ss_df = sub_sub_dfs.get(sub_f)
            if ss_df is None:
                for k, v in sub_sub_dfs.items():
                    if str(k).endswith(sub_f) or k == f"{main_f}_{sub_f}" or k == f"{main_f[:15]}_{sub_f[:15]}":
                        ss_df = v
                        break
            
            # Virtual leaf node (dummy sub-sub-criteria)
            if ss_df is None or len(ss_df) == 0:
                sub_sub_results_storage[sub_f] = {
                    "factors": [f"{sub_f}_단일항목"],
                    "weights": pd.Series([1.0], index=[f"Weight_{sub_f}_단일항목"]),
                    "df": None,
                    "group_matrix": np.array([[1.0]]),
                    "group_cr": 0.0,
                    "group_ci": 0.0
                }
                continue
                
            ss_res_df, ss_factors, ss_excl, ss_excl_df = fn_process_single_sheet(ss_df, cr_threshold, max_iter_val, learning_rate, mean_method, ahp_method)
            
            if ss_res_df.empty:
                sub_sub_results_storage[sub_f] = {
                    "factors": [f"{sub_f}_단일항목"],
                    "weights": pd.Series([1.0], index=[f"Weight_{sub_f}_단일항목"]),
                    "df": None,
                    "group_matrix": np.array([[1.0]]),
                    "group_cr": 0.0,
                    "group_ci": 0.0
                }
                continue

            if not ss_excl_df.empty:
                ss_excl_df['Sheet'] = sub_f
                total_excl_df_list.append(ss_excl_df)

            ss_weight_cols = [f"Weight_{f}" for f in ss_factors]
            ss_matrices = np.stack(ss_res_df['Matrix_Object'].values)
            ss_group_matrix = np.mean(ss_matrices, axis=0) if mean_method == 'arithmetic' else gmean(ss_matrices, axis=0)
            ss_grp_cr, ss_grp_ci, _unused3 = calculate_consistency(ss_group_matrix, method=mean_method)
            
            if ahp_method == 'fuzzy':
                ssw_vals, sub_sub_group_Si = fn_fuzzy_ahp(ss_group_matrix)
                group_sub_sub_weights = pd.Series(ssw_vals, index=ss_weight_cols)
            else:
                sub_sub_group_Si = None
                if mean_method == 'arithmetic':
                    group_sub_sub_weights = ss_res_df[ss_weight_cols].mean(axis=0)
                else:
                    group_sub_sub_weights = gmean(ss_res_df[ss_weight_cols].values, axis=0)
                group_sub_sub_weights = group_sub_sub_weights / group_sub_sub_weights.sum()
                
            sub_sub_results_storage[sub_f] = {
                "factors": ss_factors,
                "weights": group_sub_sub_weights,
                "df": ss_res_df,
                "group_matrix": ss_group_matrix,
                "group_cr": ss_grp_cr,
                "group_ci": ss_grp_ci
            }

            export_data['Sub_Sub'][sub_f] = {
                "res_df": ss_res_df,
                "excl_df": ss_excl_df,
                "factors": ss_factors,
                "group_matrix": ss_group_matrix,
                "group_Si": sub_sub_group_Si,
                "group_w": group_sub_sub_weights
            }

    # 4. Overall Global Weights integration
    summary_rows = []
    for idx, main_f in enumerate(main_factors):
        m_weight = group_main_weights.iloc[idx] if isinstance(group_main_weights, pd.Series) else group_main_weights[idx]
        if main_f not in sub_results_storage:
            continue
        
        s_info = sub_results_storage[main_f]
        for s_idx, sub_f in enumerate(s_info['factors']):
            s_weight = s_info['weights'].iloc[s_idx] if isinstance(s_info['weights'], pd.Series) else s_info['weights'][s_idx]
            
            ss_info = sub_sub_results_storage.get(sub_f)
            if not ss_info:
                continue
                
            for ss_idx, sub_sub_f in enumerate(ss_info['factors']):
                ss_weight = ss_info['weights'].iloc[ss_idx] if isinstance(ss_info['weights'], pd.Series) else ss_info['weights'][ss_idx]
                
                global_w = m_weight * s_weight * ss_weight
                summary_rows.append({
                    "대분류": main_f, "대분류 가중치": m_weight, 
                    "중분류": sub_f, "중분류 가중치": s_weight,
                    "소분류": sub_sub_f, "소분류 가중치": ss_weight,
                    "Global Weight": global_w,
                    "CR(대분류)": main_grp_cr, "CI(대분류)": main_grp_ci,
                    "CR(중분류)": s_info['group_cr'], "CI(중분류)": s_info['group_ci'],
                    "CR(소분류)": ss_info['group_cr'], "CI(소분류)": ss_info['group_ci']
                })

    final_df = pd.DataFrame(summary_rows)
    final_df['Global Rank'] = final_df['Global Weight'].round(3).rank(ascending=False, method='min').astype(int)
    cols_order = ["대분류", "대분류 가중치", "중분류", "중분류 가중치", "소분류", "소분류 가중치", "Global Weight", "Global Rank",
                  "CR(대분류)", "CI(대분류)", "CR(중분류)", "CI(중분류)", "CR(소분류)", "CI(소분류)"]
    final_df = final_df[cols_order]
    
    # Keep original hierarchical order, do not sort by rank
    # final_df = final_df.sort_values(by="Global Rank")

    # Group Analysis
    unique_groups = sorted(main_results_df['Type'].astype(str).unique())
    group_analysis_results = {}
    group_full_dfs = {}
    group_matrices_by_sheet = {}

    for grp in unique_groups:
        grp_main_df = main_results_df[main_results_df['Type'].astype(str) == grp]
        if grp_main_df.empty: continue
        
        g_main_mats = np.stack(grp_main_df['Matrix_Object'].values)
        g_main_mat_obj = np.mean(g_main_mats, axis=0) if mean_method == 'arithmetic' else gmean(g_main_mats, axis=0)
        g_main_cr, g_main_ci, _unused4 = calculate_consistency(g_main_mat_obj, method=mean_method)
        
        group_matrices_by_sheet.setdefault('Main_Criteria', {})[grp] = g_main_mat_obj
        
        if ahp_method == 'fuzzy':
            mw_vals_grp, mw_Si_grp = fn_fuzzy_ahp(g_main_mat_obj)
            g_main_w = pd.Series(mw_vals_grp, index=main_weight_cols)
        else:
            mw_Si_grp = None
            g_main_w = grp_main_df[main_weight_cols].mean(axis=0) if mean_method == 'arithmetic' else gmean(grp_main_df[main_weight_cols].values, axis=0)
            g_main_w = g_main_w / g_main_w.sum()
            
        if ahp_method == 'fuzzy':
            export_data['Main'].setdefault('group_Si_grp', {})[grp] = mw_Si_grp
            export_data['Main'].setdefault('group_w_grp', {})[grp] = g_main_w
            
        grp_sub_weights = {}
        grp_sub_cr_ci = {}
        
        for parent_factor in main_factors:
            if parent_factor not in sub_results_storage: continue
            info = sub_results_storage[parent_factor]
            s_facts = info['factors']
            s_w_cols = [f"Weight_{f}" for f in s_facts]
            
            grp_s_df = info['df'][info['df']['Type'].astype(str) == grp]
            if grp_s_df.empty:
                grp_sub_weights[parent_factor] = pd.Series(1.0 / len(s_facts), index=s_w_cols)
                grp_sub_cr_ci[parent_factor] = (0.0, 0.0)
                continue
                
            g_s_mats = np.stack(grp_s_df['Matrix_Object'].values)
            g_s_mat_obj = np.mean(g_s_mats, axis=0) if mean_method == 'arithmetic' else gmean(g_s_mats, axis=0)
            g_s_cr, g_s_ci, _unused5 = calculate_consistency(g_s_mat_obj, method=mean_method)
            
            group_matrices_by_sheet.setdefault(parent_factor, {})[grp] = g_s_mat_obj
            
            if ahp_method == 'fuzzy':
                sw_vals_grp, sw_Si_grp = fn_fuzzy_ahp(g_s_mat_obj)
                g_s_w = pd.Series(sw_vals_grp, index=s_w_cols)
            else:
                sw_Si_grp = None
                g_s_w = grp_s_df[s_w_cols].mean(axis=0) if mean_method == 'arithmetic' else gmean(grp_s_df[s_w_cols].values, axis=0)
                g_s_w = g_s_w / g_s_w.sum()
                
            grp_sub_weights[parent_factor] = g_s_w
            grp_sub_cr_ci[parent_factor] = (g_s_cr, g_s_ci)
            
            if ahp_method == 'fuzzy':
                export_data['Sub'][parent_factor].setdefault('group_Si_grp', {})[grp] = sw_Si_grp
                export_data['Sub'][parent_factor].setdefault('group_w_grp', {})[grp] = g_s_w
                
        grp_sub_sub_weights = {}
        grp_sub_sub_cr_ci = {}
        
        for sf in sub_sub_results_storage.keys():
            info = sub_sub_results_storage[sf]
            ssf_facts = info['factors']
            ssf_w_cols = [f"Weight_{f}" for f in ssf_facts]
            
            if 'df' not in info or info['df'] is None or info['df'].empty:
                grp_sub_sub_weights[sf] = pd.Series([1.0], index=ssf_w_cols)
                grp_sub_sub_cr_ci[sf] = (0.0, 0.0)
                continue
                
            grp_ss_df = info['df'][info['df']['Type'].astype(str) == grp]
            if grp_ss_df.empty:
                grp_sub_sub_weights[sf] = pd.Series(1.0 / len(ssf_facts), index=ssf_w_cols)
                grp_sub_sub_cr_ci[sf] = (0.0, 0.0)
                continue
                
            g_ss_mats = np.stack(grp_ss_df['Matrix_Object'].values)
            g_ss_mat_obj = np.mean(g_ss_mats, axis=0) if mean_method == 'arithmetic' else gmean(g_ss_mats, axis=0)
            g_ss_cr, g_ss_ci, _unused6 = calculate_consistency(g_ss_mat_obj, method=mean_method)
            
            group_matrices_by_sheet.setdefault(sf, {})[grp] = g_ss_mat_obj
            
            if ahp_method == 'fuzzy':
                ssw_vals_grp, ssw_Si_grp = fn_fuzzy_ahp(g_ss_mat_obj)
                g_ss_w = pd.Series(ssw_vals_grp, index=ssf_w_cols)
            else:
                ssw_Si_grp = None
                g_ss_w = grp_ss_df[ssf_w_cols].mean(axis=0) if mean_method == 'arithmetic' else gmean(grp_ss_df[ssf_w_cols].values, axis=0)
                g_ss_w = g_ss_w / g_ss_w.sum()
                
            grp_sub_sub_weights[sf] = g_ss_w
            grp_sub_sub_cr_ci[sf] = (g_ss_cr, g_ss_ci)
            
            if ahp_method == 'fuzzy':
                export_data['Sub_Sub'][sf].setdefault('group_Si_grp', {})[grp] = ssw_Si_grp
                export_data['Sub_Sub'][sf].setdefault('group_w_grp', {})[grp] = g_ss_w

        # Calculate global weights for group
        grp_summary_rows = []
        for idx, main_f in enumerate(main_factors):
            m_weight = g_main_w.iloc[idx] if isinstance(g_main_w, pd.Series) else g_main_w[idx]
            if main_f not in sub_results_storage: continue
            
            s_info = sub_results_storage[main_f]
            s_w_series = grp_sub_weights[main_f]
            
            for s_idx, sub_f in enumerate(s_info['factors']):
                s_weight = s_w_series.iloc[s_idx] if isinstance(s_w_series, pd.Series) else s_w_series[s_idx]
                
                ss_info = sub_sub_results_storage.get(sub_f)
                if not ss_info: continue
                
                ss_w_series = grp_sub_sub_weights[sub_f]
                for ss_idx, sub_sub_f in enumerate(ss_info['factors']):
                    ss_weight = ss_w_series.iloc[ss_idx] if isinstance(ss_w_series, pd.Series) else ss_w_series[ss_idx]
                    
                    global_w = m_weight * s_weight * ss_weight
                    grp_summary_rows.append({
                        "대분류": main_f, "대분류 가중치": m_weight,
                        "중분류": sub_f, "중분류 가중치": s_weight,
                        "소분류": sub_sub_f, "소분류 가중치": ss_weight,
                        "Global Weight": global_w,
                        "CR(대분류)": g_main_cr, "CI(대분류)": g_main_ci,
                        "CR(중분류)": grp_sub_cr_ci[main_f][0], "CI(중분류)": grp_sub_cr_ci[main_f][1],
                        "CR(소분류)": grp_sub_sub_cr_ci[sub_f][0], "CI(소분류)": grp_sub_sub_cr_ci[sub_f][1]
                    })
                    
        g_df = pd.DataFrame(grp_summary_rows)
        if not g_df.empty:
            g_df['Global Rank'] = g_df['Global Weight'].round(3).rank(ascending=False, method='min').astype(int)
            group_full_dfs[grp] = g_df[cols_order]
            group_analysis_results[grp] = group_full_dfs[grp][['대분류', '중분류', '소분류', 'Global Weight']]

    # 5. ANOVA & post-hoc calculations
    anova_df = pd.DataFrame()
    indiv_global_data = []
    all_ids = main_results_df['ID'].unique()
    
    for uid in all_ids:
        u_main = main_results_df[main_results_df['ID'] == uid]
        if u_main.empty: continue
        u_type = u_main['Type'].values[0]
        
        for mf in main_factors:
            m_w = u_main[f"Weight_{mf}"].values[0]
            if mf not in sub_results_storage: continue
            
            s_row_df = sub_results_storage[mf]['df']
            u_sub = s_row_df[s_row_df['ID'] == uid]
            if u_sub.empty: continue
            
            for sf in sub_results_storage[mf]['factors']:
                s_w = u_sub[f"Weight_{sf}"].values[0]
                
                # Check sub_sub
                if sf in sub_sub_results_storage and sub_sub_results_storage[sf]['df'] is not None:
                    ss_row_df = sub_sub_results_storage[sf]['df']
                    u_ss = ss_row_df[ss_row_df['ID'] == uid]
                    if u_ss.empty:
                        # Fallback dummy for missing respondent row
                        ss_factors = sub_sub_results_storage[sf]['factors']
                        for ssf in ss_factors:
                            # If the factor is a dummy leaf node, perform ANOVA on the parent sub-criteria (sf)
                            anova_factor = sf if ssf.endswith("_단일항목") else ssf
                            indiv_global_data.append({
                                "ID": uid, "Type": str(u_type), "Factor": anova_factor, "Global_Weight": m_w * s_w * (1.0 / len(ss_factors)),
                                "Original_CR": u_main['Original_CR'].values[0],
                                "Final_CR": u_main['Final_CR'].values[0]
                            })
                    else:
                        for ssf in sub_sub_results_storage[sf]['factors']:
                            ss_w = u_ss[f"Weight_{ssf}"].values[0]
                            anova_factor = sf if ssf.endswith("_단일항목") else ssf
                            indiv_global_data.append({
                                "ID": uid, "Type": str(u_type), "Factor": anova_factor, "Global_Weight": m_w * s_w * ss_w,
                                "Original_CR": u_main['Original_CR'].values[0],
                                "Final_CR": u_main['Final_CR'].values[0]
                            })
                else:
                    # Treat sub as leaf node
                    indiv_global_data.append({
                        "ID": uid, "Type": str(u_type), "Factor": sf, "Global_Weight": m_w * s_w * 1.0,
                        "Original_CR": u_main['Original_CR'].values[0],
                        "Final_CR": u_main['Final_CR'].values[0]
                    })
                    
    indiv_df = pd.DataFrame(indiv_global_data)
    if not indiv_df.empty and len(indiv_df['Type'].unique()) >= 2:
        anova_df = calculate_anova_and_posthoc(indiv_df)

    # 6. Premium Excel Output Generation
    output_res = io.BytesIO()
    is_en = st.session_state.get('lang', 'ko') == 'en'

    with pd.ExcelWriter(output_res, engine='xlsxwriter') as writer:
        workbook = writer.book
        
        # Styles
        formats = {
            'header': workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'bg_color': '#000000', 'font_color': '#FFFFFF', 'border': 1}),
            'merge': workbook.add_format({'align': 'center', 'valign': 'vcenter', 'border': 1}),
            'body': workbook.add_format({'align': 'center', 'valign': 'vcenter', 'border': 1}),
            'num': workbook.add_format({'align': 'center', 'valign': 'vcenter', 'border': 1, 'num_format': '0.000'}),
            'sum_row': workbook.add_format({'bold': True, 'bg_color': '#D3D3D3', 'align': 'center', 'valign': 'vcenter', 'border': 1}),
            'sum_val': workbook.add_format({'num_format': '0', 'bg_color': '#D3D3D3', 'border': 1, 'align':'center'}),
            'num_sum': workbook.add_format({'num_format': '0.000', 'bg_color': '#D3D3D3', 'border': 1, 'align':'center'}),
            'yellow': workbook.add_format({'bg_color': 'yellow', 'border': 1, 'align': 'center', 'num_format': '0.000'})
        }
        border_fmt = workbook.add_format({'border': 1})

        # --- Sheet 1: Comprehensive Summary ---
        sheet_name_comp = _('종합분석', 'Comprehensive Analysis')
        total_excluded_df = pd.concat(total_excl_df_list, ignore_index=True) if len(total_excl_df_list) > 0 else pd.DataFrame()
        
        current_row_ws = write_custom_ahp_table_v3(
            writer, sheet_name_comp, final_df, _("1) 전체_종합결과", "1) Overall Aggregated Results"), 1, formats, excluded_df=total_excluded_df
        )
        
        for grp in unique_groups:
            if grp in group_full_dfs:
                current_row_ws = write_custom_ahp_table_v3(
                    writer, sheet_name_comp, group_full_dfs[grp], _(f"▶ [그룹: {grp}] 분석 결과", f"▶ [Group: {grp}] Analysis Results"), current_row_ws, formats
                )

        # --- Sheet 2: Group Comparison ---
        if len(unique_groups) >= 2:
            ws_comp = workbook.add_worksheet('Group_Comparison')
            writer.sheets['Group_Comparison'] = ws_comp
            s_row_cp = 1
            ws_comp.write_string(s_row_cp, 0, _("그룹 간 비교(일원배치 분산분석: ANOVA)", "Group Comparison (One-way ANOVA)"), workbook.add_format({'bold': True, 'font_size': 12}))
            s_row_cp += 1
            
            comparison_df = final_df[['대분류', '중분류', '소분류', 'Global Weight']].copy()
            comparison_df.rename(columns={'Global Weight': '종합평균(Overall)'}, inplace=True)
            for grp, df_res in group_analysis_results.items():
                temp_df = df_res.rename(columns={'Global Weight': grp})
                comparison_df = comparison_df.merge(temp_df, on=['대분류', '중분류', '소분류'], how='left')
                
            if not anova_df.empty:
                # Merge ANOVA results:
                # 1. For rows that are dummy/virtual leaf nodes (i.e. '소분류' ends with '_단일항목'), we want to match ANOVA result where '요인' == '중분류'
                # 2. For standard rows, we match ANOVA result where '요인' == '소분류'
                
                # Split comparison_df into dummy and standard
                dummy_mask = comparison_df['소분류'].str.endswith('_단일항목')
                comp_dummy = comparison_df[dummy_mask].copy()
                comp_std = comparison_df[~dummy_mask].copy()
                
                anova_sub = anova_df.rename(columns={'요인': '중분류'})
                anova_sub_sub = anova_df.rename(columns={'요인': '소분류'})
                
                integrated_dummy = comp_dummy.merge(anova_sub, on='중분류', how='left')
                integrated_std = comp_std.merge(anova_sub_sub, on='소분류', how='left')
                
                integrated_df = pd.concat([integrated_std, integrated_dummy], ignore_index=True)
                
                # Restore original row order from comparison_df
                # We can do this by setting index or using a merge back
                integrated_df = comparison_df.merge(
                    integrated_df,
                    on=['대분류', '중분류', '소분류', '종합평균(Overall)'] + [grp for grp in group_analysis_results.keys() if grp in comparison_df.columns],
                    how='left'
                )
            else:
                integrated_df = comparison_df
                
            if is_en:
                rename_dict = {
                    '대분류': 'Main Criteria',
                    '중분류': 'Sub-Criteria',
                    '소분류': 'Sub-sub-Criteria',
                    '종합평균(Overall)': 'Overall',
                    'F-값': 'F-Value',
                    'P-Value': 'P-Value',
                    '유의성': 'Significance',
                    '사후검정(Tukey HSD)': 'Post-hoc (Tukey HSD)'
                }
                integrated_df_excel = integrated_df.copy()
                integrated_df_excel.rename(columns=rename_dict, inplace=True)
                if 'Significance' in integrated_df_excel.columns:
                    integrated_df_excel['Significance'] = integrated_df_excel['Significance'].replace({
                        '유의함': 'Significant',
                        '유의하지 않음': 'Not Significant'
                    })
                if 'Post-hoc (Tukey HSD)' in integrated_df_excel.columns:
                    integrated_df_excel['Post-hoc (Tukey HSD)'] = integrated_df_excel['Post-hoc (Tukey HSD)'].replace({
                        '집단 간 구체적 차이 발견 못함': 'No specific difference found',
                        '계산 오류': 'Calculation Error'
                    })
                    integrated_df_excel['Post-hoc (Tukey HSD)'] = integrated_df_excel['Post-hoc (Tukey HSD)'].apply(
                        lambda x: x.replace(" 차이 있음", " Diff Exists") if isinstance(x, str) else x
                    )
            else:
                integrated_df_excel = integrated_df

            integrated_df_excel.to_excel(writer, sheet_name='Group_Comparison', startrow=s_row_cp, index=False)
            ws_comp.conditional_format(s_row_cp, 0, s_row_cp + len(integrated_df_excel), len(integrated_df_excel.columns) - 1, {'type': 'formula', 'criteria': '=TRUE', 'format': border_fmt})
            
            num_format_3 = workbook.add_format({'num_format': '0.000', 'border': 1, 'align': 'center'})
            for r in range(len(integrated_df_excel)):
                for c in range(1, len(integrated_df_excel.columns)):
                    val = integrated_df_excel.iloc[r, c]
                    if pd.notnull(val) and isinstance(val, (int, float)):
                        ws_comp.write_number(s_row_cp + 1 + r, c, val, num_format_3)
                    elif pd.notnull(val):
                        ws_comp.write(s_row_cp + 1 + r, c, val, border_fmt)

            # ANOVA Guide text
            guide_start_row = s_row_cp + len(integrated_df_excel) + 3
            bold_fmt = workbook.add_format({'bold': True, 'font_size': 11, 'valign': 'vcenter', 'align': 'left', 'bg_color': '#F2F2F2', 'border': 1})
            text_fmt = workbook.add_format({'font_size': 10, 'text_wrap': True, 'valign': 'top', 'align': 'left', 'border': 1})
            ws_comp.set_column('A:G', 20)
            
            comp_title = _("※ 그룹 간 중요도의 차이가 있지만 통계적으로 유의하지 않게 나타나는 이유",
                           "※ Reasons why group differences are not statistically significant despite variation in priorities")
            ws_comp.merge_range(guide_start_row, 0, guide_start_row, 6, comp_title, bold_fmt)
            
            guide_content_ko = [
                ("1. 그룹 내 편차(분산)가 너무 큰 경우", "ANOVA는 '그룹 간의 차이'와 '그룹 내의 차이'를 비교합니다.\n\n■ 원리: 그룹 간 평균 차이가 크더라도, 각 그룹 내부 데이터들이 서로 들쭉날쭉(분산이 큼)하다면 통계적으로는 '이 차이가 우연히 발생했을 가능성이 높다'고 판단합니다."),
                ("2. 표본 크기(Sample Size)의 부족", "통계적 유의성은 표본의 수에 매우 민감합니다.\n\n■ 현상: 각 그룹의 데이터 개수(표본수)가 너무 적다면 통계적 힘(Power)이 부족하여 유의미한 차이를 찾아내지 못합니다."),
                ("3. 데이터의 단위(Scale)와 변동성", "표에 나타난 수치들이 대부분 매우 작은 소수점 단위입니다. 실제 계산 과정에서 표준오차 범위 내에 있다면 통계적으로는 측정 오차 범위 내의 흔들림으로 간주됩니다.")
            ]
            guide_content_en = [
                ("1. Within-Group Variance is Too Large", "ANOVA compares variance between groups against variance within groups.\n\n■ Principle: Even if the mean difference between groups is large, if individual responses within each group are highly scattered (large variance), statistics will determine that the difference is likely due to chance."),
                ("2. Insufficient Sample Size", "Statistical significance is highly sensitive to the number of samples.\n\n■ Phenomenon: If the number of data points (sample size) in each group is too small, statistical power is insufficient to detect significant differences."),
                ("3. Data Scale and Volatility", "The values in the table are mostly very small decimals. If they fall within the range of standard error, they are considered as minor fluctuations within the measurement error range.")
            ]
            guide_content = guide_content_en if is_en else guide_content_ko
            
            current_row_comp = guide_start_row + 1
            for title, body in guide_content:
                ws_comp.set_row(current_row_comp, 25)
                ws_comp.merge_range(current_row_comp, 0, current_row_comp, 6, title, bold_fmt)
                ws_comp.set_row(current_row_comp + 1, 80)
                ws_comp.merge_range(current_row_comp + 1, 0, current_row_comp + 1, 6, body, text_fmt)
                current_row_comp += 2

        # --- Sheet 3: Result Detailed Sheets ---
        # Main
        out_main = main_results_df.drop(columns=['Matrix_Object', 'Orig_Matrix_Object'], errors='ignore')
        write_detailed_sheet_ws(
            writer, '(대분류) Main', main_group_matrix, out_main, _("[대분류 평가 종합 행렬]", "[Main Criteria Combined Matrix]"), main_factors,
            group_matrices=group_matrices_by_sheet.get('Main_Criteria'), sheet_excl_count=main_excluded, mean_method=mean_method
        )
        
        # Sub
        for mf, info in sub_results_storage.items():
            safe_name = f"(중분류) {mf}"[:31]
            out_sub = info['df'].drop(columns=['Matrix_Object', 'Orig_Matrix_Object'], errors='ignore')
            
            sub_excl_val = 0
            if 'Sheet' in total_excluded_df.columns:
                sub_excl_val = len(total_excluded_df[total_excluded_df['Sheet'] == mf])
                
            title_ko = f"[중분류 평가 종합 행렬]  ▶ 상위 계층: 대분류 [{mf}]"
            title_en = f"[Sub-Criteria Combined Matrix]  ▶ Parent: Main [{mf}]"
            write_detailed_sheet_ws(
                writer, safe_name, info['group_matrix'], out_sub, _(title_ko, title_en), info['factors'],
                group_matrices=group_matrices_by_sheet.get(mf), sheet_excl_count=sub_excl_val, mean_method=mean_method
            )

        # Sub_Sub
        for ssf, info in sub_sub_results_storage.items():
            if 'df' not in info or info['df'] is None or info['df'].empty: continue
            safe_name = f"(소분류) {ssf}"[:31]
            out_ss = info['df'].drop(columns=['Matrix_Object', 'Orig_Matrix_Object'], errors='ignore')
            
            ss_excl_val = 0
            if 'Sheet' in total_excluded_df.columns:
                ss_excl_val = len(total_excluded_df[total_excluded_df['Sheet'] == ssf])
                
            parent_mf = ""
            for m, s_info in sub_results_storage.items():
                if ssf in s_info['factors']:
                    parent_mf = m
                    break
                    
            title_ko = f"[소분류 평가 종합 행렬]  ▶ 상위 계층: 대분류 [{parent_mf}] ➔ 중분류 [{ssf}]"
            title_en = f"[Sub-sub-Criteria Combined Matrix]  ▶ Parent: Main [{parent_mf}] ➔ Sub [{ssf}]"
            write_detailed_sheet_ws(
                writer, safe_name, info['group_matrix'], out_ss, _(title_ko, title_en), info['factors'],
                group_matrices=group_matrices_by_sheet.get(ssf), sheet_excl_count=ss_excl_val, mean_method=mean_method
            )

        # --- Sheet 4: Consistency Theory ---
        theory_ws = workbook.add_worksheet("Consistency_Theory")
        theory_title_fmt = workbook.add_format({'bold': True, 'font_size': 14, 'font_name': 'NanumGothic'})
        theory_body_fmt = workbook.add_format({'text_wrap': True, 'valign': 'top', 'font_name': 'NanumGothic'})
        if is_en:
            theory_text = [
                ["AHP Consistency Calibration Principle & Academic Foundation from a Decision-Making Perspective"],
                [""],
                ["1. Introduction: The Issue of Consistency in the Analytic Hierarchy Process (AHP)"],
                ["The Analytic Hierarchy Process, proposed by Saaty (1980), is a multi-criteria decision-making tool that quantifies human subjective judgment. When inconsistent judgments occur, they are mathematically corrected to ensure the reliability of the analysis."],
                [""],
                ["2. Calibration Algorithm: Iterative Convergence Adjusting Method"],
                [f"The original matrix A and the ideal matrix W are linearly combined according to the set learning rate (learning rate α={learning_rate}): A_new = (1-α)A + αW."],
                [""],
                ["3. Academic Foundation & Effects"],
                ["Adjustment using a weighted average of the original matrix and the consistent matrix preserves the decision maker's original preferences as much as possible while improving mathematical consistency."]
            ]
        else:
            theory_text = [
                ["의사결정론적 관점에서의 AHP 일관성 보정 원리 및 학술적 근거"],
                [""],
                ["1. 서론: 계층분석과정(AHP)의 일관성 문제"],
                ["Saaty(1980)에 의해 제안된 계층분석과정은 인간의 주관적 판단을 정량화하는 다기준 의사결정 도구이다. 비일관적 판단이 발생할 경우 수학적으로 교정하여 분석의 신뢰성을 확보한다."],
                [""],
                ["2. 보정 알고리즘: 반복 수렴 조정법"],
                [f"원본 행렬 A와 이상적 행렬 W를 설정된 학습률(α={learning_rate})에 따라 선형 결합한다: A_new = (1-α)A + αW."],
                [""],
                ["3. 학술적 근거 및 효과"],
                ["원본 행렬과 일관 행렬의 가중 평균을 이용한 조정은 의사결정자의 원래 선호 경향성을 최대한 보존하면서 수학적 일관성을 향상시킨다."]
            ]
        theory_ws.set_column('A:A', 100)
        for r_idx, row_content in enumerate(theory_text):
            fmt = theory_title_fmt if r_idx == 0 else theory_body_fmt
            theory_ws.write(r_idx, 0, row_content[0], fmt)

        # --- Sheet 5: Fuzzy AHP Results ---
        if ahp_method == 'fuzzy':
            ws_fuzzy = workbook.add_worksheet('Fuzzy_AHP_Results')
            writer.sheets['Fuzzy_AHP_Results'] = ws_fuzzy
            ws_fuzzy.set_column('A:A', 25)
            ws_fuzzy.set_column('B:G', 20)
            
            fuzzy_header_fmt = workbook.add_format({
                'bold': True, 'align': 'center', 'valign': 'vcenter',
                'bg_color': '#1F4E78', 'font_color': '#FFFFFF', 'border': 1,
                'font_name': 'NanumGothic'
            })
            title_fmt = workbook.add_format({
                'bold': True, 'font_size': 12, 'font_name': 'NanumGothic'
            })
            
            row_idx = 1
            ws_fuzzy.write_string(row_idx, 0, _("■ 대분류 (Main Criteria) 퍼지 AHP 분석 결과 (삼각피지수 적용)", "■ Main Criteria Fuzzy AHP Results (TFN Applied)"), title_fmt)
            row_idx += 1
            
            headers = [
                _("구분", "Criteria"), 
                _("Fuzzy 가중치 (Lower)", "Fuzzy Weight (Lower)"), 
                _("Fuzzy 가중치 (Medium)", "Fuzzy Weight (Medium)"), 
                _("Fuzzy 가중치 (Upper)", "Fuzzy Weight (Upper)"), 
                _("비퍼지화 (Crisp)", "Defuzzified (Crisp)"), 
                _("최종 가중치 (Norm)", "Final Weight (Norm)"), 
                _("순위", "Rank")
            ]
            for c_idx, h in enumerate(headers):
                ws_fuzzy.write(row_idx, c_idx, h, fuzzy_header_fmt)
            row_idx += 1
            
            main_rows = []
            for i, (l, m, u) in enumerate(export_data['Main']['group_Si']):
                crisp = (l * m * u) ** (1/3)
                norm_w = group_main_weights.iloc[i] if isinstance(group_main_weights, pd.Series) else group_main_weights[i]
                main_rows.append([main_factors[i], l, m, u, crisp, norm_w])
                
            norm_w_list = [r[5] for r in main_rows]
            sorted_weights = sorted(list(set(norm_w_list)), reverse=True)
            ranks = [sorted_weights.index(w) + 1 for w in norm_w_list]
            
            for i, r in enumerate(main_rows):
                r.append(ranks[i])
                ws_fuzzy.write(row_idx, 0, r[0], formats['body'])
                for c_idx in range(1, 6):
                    ws_fuzzy.write_number(row_idx, c_idx, safe_float(r[c_idx]), formats['num'])
                ws_fuzzy.write_number(row_idx, 6, safe_float(r[6]), formats['body'])
                row_idx += 1
                
            row_idx += 2
            
            # Sub criteria fuzzy results
            for parent_f, sub_info in export_data['Sub'].items():
                if sub_info.get('group_Si') is not None:
                    ws_fuzzy.write_string(row_idx, 0, _(f"■ 세부항목 [{parent_f}] 퍼지 AHP 분석 결과 (삼각피지수 적용)", f"■ Sub-Criteria [{parent_f}] Fuzzy AHP Results (TFN Applied)"), title_fmt)
                    row_idx += 1
                    
                    for c_idx, h in enumerate(headers):
                        ws_fuzzy.write(row_idx, c_idx, h, fuzzy_header_fmt)
                    row_idx += 1
                    
                    sub_factors = sub_info['factors']
                    sub_group_Si = sub_info['group_Si']
                    group_sub_w = sub_info['group_w']
                    
                    sub_rows = []
                    for i, (l, m, u) in enumerate(sub_group_Si):
                        crisp = (l * m * u) ** (1/3)
                        norm_w = group_sub_w.iloc[i] if isinstance(group_sub_w, pd.Series) else group_sub_w[i]
                        sub_rows.append([sub_factors[i], l, m, u, crisp, norm_w])
                        
                    norm_w_list = [r[5] for r in sub_rows]
                    sorted_weights = sorted(list(set(norm_w_list)), reverse=True)
                    ranks = [sorted_weights.index(w) + 1 for w in norm_w_list]
                    
                    for i, r in enumerate(sub_rows):
                        r.append(ranks[i])
                        ws_fuzzy.write(row_idx, 0, r[0], formats['body'])
                        for c_idx in range(1, 6):
                            ws_fuzzy.write_number(row_idx, c_idx, safe_float(r[c_idx]), formats['num'])
                        ws_fuzzy.write_number(row_idx, 6, safe_float(r[6]), formats['body'])
                        row_idx += 1
                    row_idx += 2

            # Sub-Sub criteria fuzzy results
            for sub_f, ss_info in export_data['Sub_Sub'].items():
                if ss_info.get('group_Si') is not None:
                    ws_fuzzy.write_string(row_idx, 0, _(f"■ 소분류항목 [{sub_f}] 퍼지 AHP 분석 결과 (삼각피지수 적용)", f"■ Sub-sub-Criteria [{sub_f}] Fuzzy AHP Results (TFN Applied)"), title_fmt)
                    row_idx += 1
                    
                    for c_idx, h in enumerate(headers):
                        ws_fuzzy.write(row_idx, c_idx, h, fuzzy_header_fmt)
                    row_idx += 1
                    
                    ss_factors = ss_info['factors']
                    sub_sub_group_Si = ss_info['group_Si']
                    group_sub_sub_w = ss_info['group_w']
                    
                    ss_rows = []
                    for i, (l, m, u) in enumerate(sub_sub_group_Si):
                        crisp = (l * m * u) ** (1/3)
                        norm_w = group_sub_sub_w.iloc[i] if isinstance(group_sub_sub_w, pd.Series) else group_sub_sub_w[i]
                        ss_rows.append([ss_factors[i], l, m, u, crisp, norm_w])
                        
                    norm_w_list = [r[5] for r in ss_rows]
                    sorted_weights = sorted(list(set(norm_w_list)), reverse=True)
                    ranks = [sorted_weights.index(w) + 1 for w in norm_w_list]
                    
                    for i, r in enumerate(ss_rows):
                        r.append(ranks[i])
                        ws_fuzzy.write(row_idx, 0, r[0], formats['body'])
                        for c_idx in range(1, 6):
                            ws_fuzzy.write_number(row_idx, c_idx, safe_float(r[c_idx]), formats['num'])
                        ws_fuzzy.write_number(row_idx, 6, safe_float(r[6]), formats['body'])
                        row_idx += 1
                    row_idx += 2

        # --- Sheet 6: CR Distribution Summary ---
        ws_cr = workbook.add_worksheet('CR_Distribution')
        writer.sheets['CR_Distribution'] = ws_cr
        ws_cr.set_column('A:A', 25)
        ws_cr.set_column('B:H', 20)
        
        title_fmt = workbook.add_format({'bold': True, 'font_size': 12, 'font_name': 'NanumGothic'})
        cr_header_fmt = workbook.add_format({
            'bold': True, 'align': 'center', 'valign': 'vcenter',
            'bg_color': '#595959', 'font_color': '#FFFFFF', 'border': 1,
            'font_name': 'NanumGothic'
        })
        
        ws_cr.write_string(1, 0, _("■ 일관성 비율(CR) 분석 요약", "■ Consistency Ratio (CR) Analysis Summary"), title_fmt)
        
        cr_headers = [
            _("평가 시트명", "Sheet Name"),
            _("평균 CR", "Mean CR"),
            _("중앙값 CR", "Median CR"),
            _("최소 CR", "Min CR"),
            _("최대 CR", "Max CR"),
            _("통과 표본 수 (CR <= 0.1)", "Passed Samples (CR <= 0.1)"),
            _("전체 표본 수", "Total Samples"),
            _("통과율 (%)", "Pass Rate (%)")
        ]
        for c_idx, h in enumerate(cr_headers):
            ws_cr.write(2, c_idx, h, cr_header_fmt)
            
        cr_row_idx = 3
        
        sheets_to_process = [("Main_Criteria", main_results_df)]
        for mf, info in sub_results_storage.items():
            sheets_to_process.append((mf, info['df']))
        for sf, info in sub_sub_results_storage.items():
            if 'df' in info and info['df'] is not None and not info['df'].empty:
                sheets_to_process.append((sf, info['df']))
                
        for sheet_name, df_s in sheets_to_process:
            if df_s.empty: continue
            cr_vals = df_s['Final_CR'].dropna().values
            if len(cr_vals) == 0: continue
            
            mean_cr = np.mean(cr_vals)
            median_cr = np.median(cr_vals)
            min_cr = np.min(cr_vals)
            max_cr = np.max(cr_vals)
            total_cnt = len(cr_vals)
            pass_cnt = np.sum(cr_vals <= 0.1)
            pass_rate = (pass_cnt / total_cnt) * 100
            
            ws_cr.write(cr_row_idx, 0, sheet_name, formats['body'])
            ws_cr.write_number(cr_row_idx, 1, safe_float(mean_cr), formats['num'])
            ws_cr.write_number(cr_row_idx, 2, safe_float(median_cr), formats['num'])
            ws_cr.write_number(cr_row_idx, 3, safe_float(min_cr), formats['num'])
            ws_cr.write_number(cr_row_idx, 4, safe_float(max_cr), formats['num'])
            ws_cr.write_number(cr_row_idx, 5, safe_float(pass_cnt), formats['body'])
            ws_cr.write_number(cr_row_idx, 6, safe_float(total_cnt), formats['body'])
            ws_cr.write_number(cr_row_idx, 7, safe_float(pass_rate), formats['num'])
            cr_row_idx += 1
            
        cr_row_idx += 2
        ws_cr.write_string(cr_row_idx, 0, _("■ 개별 응답자별 일관성 비율(CR) 상세 내역", "■ Detailed Consistency Ratio (CR) by Respondent"), title_fmt)
        cr_row_idx += 1
        
        indiv_headers = [
            _("ID (설문자)", "Respondent ID"),
            _("그룹 (Type)", "Group Type"),
            _("평가 시트명", "Sheet Name"),
            _("일관성 비율 (CR)", "Consistency Ratio (CR)"),
            _("판정 (CR <= 0.1)", "Status (CR <= 0.1)")
        ]
        for c_idx, h in enumerate(indiv_headers):
            ws_cr.write(cr_row_idx, c_idx, h, cr_header_fmt)
        cr_row_idx += 1
        
        for sheet_name, df_s in sheets_to_process:
            if df_s.empty: continue
            for idx_row, r in df_s.iterrows():
                cr_val = r['Final_CR']
                status_text = _("통과", "Pass") if cr_val <= 0.1 else _("비일관적", "Inconsistent")
                
                ws_cr.write(cr_row_idx, 0, r['ID'], formats['body'])
                ws_cr.write(cr_row_idx, 1, str(r['Type']), formats['body'])
                ws_cr.write(cr_row_idx, 2, sheet_name, formats['body'])
                ws_cr.write_number(cr_row_idx, 3, safe_float(cr_val), formats['num'])
                ws_cr.write(cr_row_idx, 4, status_text, formats['body'])
                cr_row_idx += 1

    output_res.seek(0)
    
    # integrated_df 방어: 그룹이 2개 미만이면 정의되지 않음
    if 'integrated_df' not in dir():
        integrated_df = final_df[['대분류','중분류','소분류','Global Weight']].rename(columns={'Global Weight':'종합평균(Overall)'})

    # UI 탭 렌더링용 데이터 묶음
    ui_data = {
        "final_df": final_df,
        "comparison_df": integrated_df if len(unique_groups) >= 2 else final_df[['대분류','중분류','소분류','Global Weight']].rename(columns={'Global Weight':'종합평균(Overall)'}),
        "anova_df": anova_df,
        "group_full_dfs": group_full_dfs,
        "group_analysis_results": group_analysis_results,
        "unique_groups": unique_groups,
        "indiv_df": indiv_df,
        "main_factors": main_factors,
        "sub_results_storage": sub_results_storage,
        "sub_sub_results_storage": sub_sub_results_storage,
    }
    
    return True, "Analysis Successful" if is_en else "분석 성공", final_df, output_res, ui_data

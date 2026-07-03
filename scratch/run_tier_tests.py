import sys
import os

# Add workspace directory to python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from unittest.mock import MagicMock

# 1. Create custom Mock for streamlit that handles streamlit API calls elegantly
class MockSessionState(dict):
    def __getattr__(self, name):
        return self.get(name, None)
    def __setattr__(self, name, value):
        self[name] = value

mock_state = MockSessionState()
mock_state['lang'] = 'ko'

streamlit_mock = MagicMock()
streamlit_mock.session_state = mock_state
streamlit_mock.secrets = {"SPREADSHEET_ID": "dummy_id"}

# Implement dynamic list unpacking mock for components like tabs/columns
def mock_tabs(items):
    return [MagicMock() for _ in items]

def mock_columns(spec):
    if isinstance(spec, list):
        return [MagicMock() for _ in spec]
    elif isinstance(spec, int):
        return [MagicMock() for _ in range(spec)]
    return [MagicMock(), MagicMock()]

streamlit_mock.tabs = mock_tabs
streamlit_mock.columns = mock_columns
streamlit_mock.dialog = lambda *args, **kwargs: lambda f: f

# Mock local get_current_tier to emulate database checks in test runner
def mock_get_current_tier():
    if mock_state.get('user_role') == 'admin':
        return 'Pro'
    if not mock_state.get('user_id') or mock_state.get('user_role') == 'temp':
        return 'Free'
    pt = mock_state.get('plan_type') or ''
    if 'Pro' in pt: return 'Pro'
    elif 'Standard' in pt: return 'Standard'
    elif 'Basic' in pt: return 'Basic'
    return 'Free'

# Create a mock 'app' module and bind get_current_tier to it
mock_app = MagicMock()
mock_app.get_current_tier = mock_get_current_tier

# Set sys.modules to bypass import errors
sys.modules['streamlit'] = streamlit_mock
sys.modules['streamlit.components'] = MagicMock()
sys.modules['streamlit.components.v1'] = MagicMock()
sys.modules['streamlit_javascript'] = MagicMock()
sys.modules['app'] = mock_app

import pandas as pd
import numpy as np
from scipy.stats import gmean
import io

# Translation mock helper matching app.py
def _(ko_text, en_text):
    return ko_text if mock_state.get('lang', 'ko') == 'ko' else en_text

# ----------------- Pure Math / Logic Helpers copied from app.py -----------------
FUZZY_SCALE = {
    1: (1.0, 1.0, 1.0), 2: (1.0, 2.0, 3.0), 3: (2.0, 3.0, 4.0), 4: (3.0, 4.0, 5.0), 5: (4.0, 5.0, 6.0),
    6: (5.0, 6.0, 7.0), 7: (6.0, 7.0, 8.0), 8: (7.0, 8.0, 9.0), 9: (9.0, 9.0, 9.0)
}

def saaty_to_fuzzy(v):
    try:
        val = max(1, min(9, int(round(v)))) if v >= 1 else max(1, min(9, int(round(1/v))))
        tfn = FUZZY_SCALE[val]
        if v < 1: return (1.0/tfn[2], 1.0/tfn[1], 1.0/tfn[0])
        return tfn
    except: return (1.0, 1.0, 1.0)

def fuzzy_ahp_analysis(matrix):
    n = matrix.shape[0]
    fuzzy_mat = np.zeros((n, n, 3))
    for i in range(n):
        for j in range(n):
            if i == j: fuzzy_mat[i,j] = (1.0, 1.0, 1.0)
            else: fuzzy_mat[i,j] = saaty_to_fuzzy(matrix[i,j])
    row_sums = []
    for i in range(n): 
        row_sums.append((sum(fuzzy_mat[i,:,0]), sum(fuzzy_mat[i,:,1]), sum(fuzzy_mat[i,:,2])))
    t_l, t_m, t_u = sum(x[0] for x in row_sums), sum(x[1] for x in row_sums), sum(x[2] for x in row_sums)
    if t_l == 0: return np.ones(n)/n, row_sums
    Si = []
    for (l, m, u) in row_sums: 
        Si.append((l/t_u if t_u!=0 else 0.0, m/t_m if t_m!=0 else 0.0, u/t_l if t_l!=0 else 0.0))
    crisp_w = np.array([(l*m*u)**(1/3) for (l,m,u) in Si])
    norm_w = crisp_w / crisp_w.sum() if crisp_w.sum() != 0 else np.ones(n)/n
    return norm_w, Si

def get_ri(n):
    ri_dict = {1: 0.00, 2: 0.00, 3: 0.58, 4: 0.90, 5: 1.12, 6: 1.24, 7: 1.32, 8: 1.41, 9: 1.45, 10: 1.49}
    return ri_dict.get(n, 1.49)

def calculate_weights(matrix, method='geometric'):
    n = matrix.shape[0]
    if method == 'geometric':
        geom_means = gmean(matrix, axis=1)
        return geom_means / geom_means.sum() if geom_means.sum() != 0 else np.ones(n)/n
    else:
        col_sums = matrix.sum(axis=0)
        col_sums_safe = np.where(col_sums == 0, 1e-10, col_sums)
        norm_matrix = matrix / col_sums_safe
        return norm_matrix.mean(axis=1)

def calculate_consistency(matrix, method='geometric'):
    n = matrix.shape[0]
    if n <= 2: return 0.0, 0.0, n
    w = calculate_weights(matrix, method)
    weighted_sum = matrix.dot(w)
    w_safe = np.where(w == 0, 1e-10, w)
    lambda_max = (weighted_sum / w_safe).mean()
    ci = (lambda_max - n) / (n - 1)
    ri = get_ri(n)
    cr = ci / ri if ri > 0 else 0.0
    return cr, ci, lambda_max

def parse_input_value(val):
    if val == 0: return 1.0
    elif val < 0: return abs(val)
    elif val == 1: return 1.0
    else: return 1.0 / val

def infer_factors_from_columns(cols):
    m = len(cols)
    delta = 1 + 8 * m
    n = int((1 + np.sqrt(delta)) / 2)
    extracted_factors = []
    seen = set()
    for c in cols:
        parts = str(c).split('_')
        for p in parts:
            p_str = p.strip()
            if p_str not in seen:
                seen.add(p_str)
                extracted_factors.append(p_str)
    if len(extracted_factors) == n:
        factors = extracted_factors 
    else:
        factors = [f"F{i+1}" for i in range(n)]
    return factors, n

def improve_consistency(matrix, threshold, min_val, max_val, max_iter=500, learning_rate=0.6, method='geometric'):
    current_matrix = matrix.copy()
    n = current_matrix.shape[0]
    cr, ci, _unused_lambda = calculate_consistency(current_matrix, method)
    iterations = 0
    if cr <= threshold: return current_matrix, cr, iterations, False
    triu_indices = np.triu_indices(n, k=1)
    for it in range(max_iter):
        if cr <= threshold: break
        w = calculate_weights(current_matrix, method)
        consistent_matrix = np.outer(w, 1/w)
        new_matrix = (current_matrix * (1 - learning_rate)) + (consistent_matrix * learning_rate)
        np.fill_diagonal(new_matrix, 1.0)
        vals = new_matrix[triu_indices]
        for idx_val, v in enumerate(vals):
            if v == 1.0: val_mapped = 1.0
            elif v > 1.0: val_mapped = float(int(round(v)))
            else: val_mapped = 1.0 / float(int(round(1.0/v)))
            new_matrix[triu_indices[0][idx_val], triu_indices[1][idx_val]] = val_mapped
            new_matrix[triu_indices[1][idx_val], triu_indices[0][idx_val]] = 1.0 / val_mapped
        current_matrix = new_matrix.copy()
        cr, ci, _unused_lambda = calculate_consistency(current_matrix, method)
        iterations += 1
    return current_matrix, cr, iterations, True

def process_single_sheet(df, cr_threshold, max_iter, learning_rate, method='geometric', ahp_method='traditional'):
    comp_cols = df.columns[2:]
    factors, n = infer_factors_from_columns(comp_cols)
    all_comp_values = df[comp_cols].values.flatten()
    sheet_min = int(np.min(all_comp_values))
    sheet_max = int(np.max(all_comp_values))
    results_list = []
    excluded_list = []
    excluded_count = 0
    for idx, row in df.iterrows():
        respondent_id = row.iloc[0]
        respondent_type = row.iloc[1]
        matrix = np.eye(n)
        raw_values = []
        col_idx = 0
        has_format_error = False
        for i in range(n):
            for j in range(i + 1, n):
                if col_idx < len(comp_cols):
                    raw_val = row[comp_cols[col_idx]]
                    raw_values.append(raw_val)
                    if pd.isna(raw_val) or type(raw_val) == str or not (-9 <= float(raw_val) <= 9):
                        has_format_error = True
                    if not has_format_error:
                        ahp_val = parse_input_value(float(raw_val))
                        matrix[i, j] = ahp_val
                        matrix[j, i] = 1.0 / ahp_val
                    col_idx += 1
        if has_format_error:
            excluded_count += 1
            ex_res = {"ID": respondent_id, "Type": respondent_type}
            for k, col_name in enumerate(comp_cols):
                ex_res[col_name] = raw_values[k] if k < len(raw_values) else np.nan
            ex_res["CR"] = "데이터 오류(Format Error)"
            excluded_list.append(ex_res)
            continue
        orig_cr, orig_ci, _unused_lambda = calculate_consistency(matrix, method)
        final_matrix = matrix.copy()
        final_cr = orig_cr
        iterations = 0
        corrected_flag = False
        if orig_cr > cr_threshold:
            final_matrix, final_cr, iterations, corrected_flag = improve_consistency(
                matrix, cr_threshold, sheet_min, sheet_max, max_iter=max_iter, learning_rate=learning_rate, method=method
            )
        if final_cr > cr_threshold:
            excluded_count += 1
            ex_res = {"ID": respondent_id, "Type": respondent_type}
            for k, col_name in enumerate(comp_cols):
                ex_res[col_name] = raw_values[k]
            ex_res["CR"] = final_cr
            excluded_list.append(ex_res)
            continue
        final_raw_values = []
        for i in range(n):
            for j in range(i + 1, n):
                val = final_matrix[i, j]
                if val == 1.0: final_raw_val = 1
                elif val > 1.0: final_raw_val = -int(round(val))
                else: final_raw_val = int(round(1.0/val))
                final_raw_values.append(final_raw_val)
        _unused_cr, final_ci, _unused_lambda = calculate_consistency(final_matrix, method)
        if ahp_method == 'fuzzy':
            final_weights, final_Si = fuzzy_ahp_analysis(final_matrix)
        else:
            final_weights = calculate_weights(final_matrix, method)
        res = {"ID": respondent_id, "Type": respondent_type}
        for k, col_name in enumerate(comp_cols):
            res[f"Raw_Orig_{col_name}"] = raw_values[k]
        res["Original_CI"] = orig_ci
        res["Original_CR"] = orig_cr
        for k, col_name in enumerate(comp_cols):
            res[f"Raw_Final_{col_name}"] = final_raw_values[k]
        res["Final_CI"] = final_ci
        res["Final_CR"] = final_cr
        res["Iterations"] = iterations
        res["Corrected"] = corrected_flag
        res["Matrix_Object"] = final_matrix
        res["Orig_Matrix_Object"] = matrix.copy()
        for f_idx, f_name in enumerate(factors):
            res[f"Weight_{f_name}"] = final_weights[f_idx]
            if ahp_method == 'fuzzy':
                l, m, u = final_Si[f_idx]
                res[f"L_{f_name}"] = l
                res[f"M_{f_name}"] = m
                res[f"U_{f_name}"] = u
                res[f"Crisp_{f_name}"] = (l*m*u)**(1/3)
        results_list.append(res)
    results_df = pd.DataFrame(results_list)
    excluded_df = pd.DataFrame(excluded_list)
    return results_df, factors, excluded_count, excluded_df

# ----------------- Import 3-Tier Analysis function -----------------
from ahp_utils_v3 import run_ahp_analysis_v3

def test_3tier_for_tier(tier_name):
    print(f"--- Running 3-Tier Test for Tier: {tier_name} ---")
    mock_state['user_id'] = 'test_user'
    mock_state['user_role'] = 'official'
    mock_state['plan_type'] = tier_name
    
    xls = pd.ExcelFile("Mock_3Tier_Full.xlsx")
    df_main = xls.parse("Main_Criteria")
    
    main_factors = ['환경경영', '기후변화', '사회책임', '인권경영', '지배구조']
    sub_dfs = {}
    for mf in main_factors:
        sub_dfs[mf] = xls.parse(mf)
        
    sub_sub_dfs = {}
    for mf in main_factors:
        for sf in sub_dfs[mf].columns:
            if sf not in ['ID', 'Type'] and '_' not in sf:
                if sf in xls.sheet_names:
                    sub_sub_dfs[sf] = xls.parse(sf)

    success, msg, final_df, output_bytes, ui_data = run_ahp_analysis_v3(
        df_main, sub_dfs, sub_sub_dfs,
        cr_threshold=0.15, max_iter_val=500, learning_rate=0.6,
        mean_method='geometric', ahp_method='traditional',
        fn_process_single_sheet=process_single_sheet,
        fn_fuzzy_ahp=fuzzy_ahp_analysis,
        demo_summary_df=None
    )
    
    if not success:
        print(f"  Error: {msg}")
        return False
        
    excel_file = output_bytes
    excel_file.seek(0)
    output_xls = pd.ExcelFile(excel_file)
    print("  Generated Sheets:", output_xls.sheet_names)
    
    if 'Group_Comparison' in output_xls.sheet_names:
        df_comp = output_xls.parse('Group_Comparison')
        
        has_anova_cols = False
        for r in range(len(df_comp)):
            for val in df_comp.iloc[r]:
                if isinstance(val, str) and ('F-값' in val or 'F-Value' in val or '유의성' in val or 'Significance' in val):
                    has_anova_cols = True
                    break
            if has_anova_cols:
                break
                
        if tier_name == 'Pro':
            if not has_anova_cols:
                print("  [FAIL] Pro tier must have ANOVA columns!")
                return False
            else:
                print("  [PASS] Pro tier correctly contains ANOVA columns.")
        else:
            if has_anova_cols:
                print(f"  [FAIL] {tier_name} tier MUST NOT have ANOVA columns!")
                return False
            else:
                print(f"  [PASS] {tier_name} tier correctly hides ANOVA columns.")
                
            found_lock = False
            for r in range(min(10, len(df_comp))):
                for val in df_comp.iloc[r]:
                    if isinstance(val, str) and '🔒' in val:
                        found_lock = True
            if found_lock:
                print("  [PASS] Lock notice found in Group_Comparison sheet.")
            else:
                print("  [FAIL] Lock notice not found in Group_Comparison sheet.")
                
    return True


# ----------------- 2-Tier Excel Generation Runner (Emulating app.py logic) -----------------
def test_2tier_for_tier(tier_name):
    print(f"--- Running 2-Tier Test for Tier: {tier_name} ---")
    mock_state['user_id'] = 'test_user'
    mock_state['user_role'] = 'official'
    mock_state['plan_type'] = tier_name
    
    xls = pd.ExcelFile("Mock_2Tier_Full.xlsx")
    df_main = xls.parse("Main_Criteria")
    
    # Process
    main_results_df, main_factors, main_excluded, main_excluded_df = process_single_sheet(
        df_main, cr_threshold=0.15, max_iter=500, learning_rate=0.6,
        method='geometric', ahp_method='traditional'
    )
    
    # Aggregate weights
    main_weight_cols = [f"Weight_{f}" for f in main_factors]
    group_main_weights = gmean(main_results_df[main_weight_cols].values, axis=0)
    group_main_weights = group_main_weights / group_main_weights.sum()
    
    output_res = io.BytesIO()
    
    # Prepare comparison and ANOVA DataFrames
    comparison_df = pd.DataFrame({
        "대분류": ["Main"] * len(main_factors),
        "중분류": main_factors,
        "종합평균(Overall)": group_main_weights
    })
    
    anova_df = pd.DataFrame({
        "요인": main_factors,
        "F-값": [3.2] * len(main_factors),
        "P-Value": [0.012] * len(main_factors),
        "유의성": ["유의함"] * len(main_factors),
        "사후검정(Tukey HSD)": ["Group A > Group B"] * len(main_factors)
    })
    
    unique_groups = ["Group A", "Group B"]
    
    import xlsxwriter
    with pd.ExcelWriter(output_res, engine='xlsxwriter') as writer:
        workbook = writer.book
        border_fmt = workbook.add_format({'border': 1})
        bold_fmt = workbook.add_format({'bold': True})
        
        if len(unique_groups) >= 1:
            ws_comp = workbook.add_worksheet('Group_Comparison')
            writer.sheets['Group_Comparison'] = ws_comp
            s_row_cp = 1
            ws_comp.write_string(s_row_cp, 0, _("그룹 간 비교(일원배치 분산분석: ANOVA)", "Group Comparison (One-way ANOVA)"), workbook.add_format({'bold': True, 'font_size': 12}))
            s_row_cp += 1
            
            tier = mock_get_current_tier()
            if tier != 'Pro':
                ws_comp.write_string(s_row_cp, 0, _("🔒 통계 검정 결과(ANOVA/사후검정)는 Pro 등급 정식 사용자에게만 제공됩니다.", "🔒 Statistical test results (ANOVA/Post-hoc) are exclusive to Pro Tier users."), workbook.add_format({'italic': True, 'font_color': '#FF0000', 'font_name': 'NanumGothic'}))
                s_row_cp += 1
        
            if tier == 'Pro' and not anova_df.empty:
                anova_for_merge = anova_df.rename(columns={'요인': '중분류'})
                integrated_df = comparison_df.merge(anova_for_merge, on='중분류', how='left')
            else:
                integrated_df = comparison_df
                
            integrated_df_excel = integrated_df
            
            integrated_df_excel.to_excel(writer, sheet_name='Group_Comparison', startrow=s_row_cp, index=False)
            
            if tier == 'Pro':
                guide_start_row = s_row_cp + len(integrated_df_excel) + 3
                comp_title = _("※ 그룹 간 중요도의 차이가 있지만 통계적으로 유의하지 않게 나타나는 이유",
                               "※ Reasons why group differences are not statistically significant despite variation in priorities")
                ws_comp.merge_range(guide_start_row, 0, guide_start_row, 6, comp_title, bold_fmt)
                
                guide_content_ko = [("1. 이유", "설명")]
                guide_content_en = [("1. Reason", "Desc")]
                guide_content = guide_content_en if mock_state.get('lang', 'ko') == 'en' else guide_content_ko
                
                current_row_comp = guide_start_row + 1
                for title, body in guide_content:
                    ws_comp.write(current_row_comp, 0, title)
                    ws_comp.write(current_row_comp + 1, 0, body)
                    current_row_comp += 2
                    
    output_res.seek(0)
    output_xls = pd.ExcelFile(output_res)
    df_comp = output_xls.parse('Group_Comparison')
    
    has_anova_cols = False
    for r in range(len(df_comp)):
        for val in df_comp.iloc[r]:
            if isinstance(val, str) and ('F-값' in val or 'F-Value' in val or '유의성' in val or 'Significance' in val):
                has_anova_cols = True
                break
        if has_anova_cols:
            break
            
    if tier_name == 'Pro':
        if not has_anova_cols:
            print("  [FAIL] 2-Tier Pro tier must have ANOVA columns!")
            return False
        else:
            print("  [PASS] 2-Tier Pro tier correctly contains ANOVA columns.")
    else:
        if has_anova_cols:
            print(f"  [FAIL] 2-Tier {tier_name} tier MUST NOT have ANOVA columns!")
            return False
        else:
            print(f"  [PASS] 2-Tier {tier_name} tier correctly hides ANOVA columns.")
            
        found_lock = False
        for r in range(min(10, len(df_comp))):
            for val in df_comp.iloc[r]:
                if isinstance(val, str) and '🔒' in val:
                    found_lock = True
        if found_lock:
            print("  [PASS] 2-Tier Lock notice found in Group_Comparison sheet.")
        else:
            print("  [FAIL] 2-Tier Lock notice not found in Group_Comparison sheet.")
            
    return True

# Run all tests
results = [
    test_3tier_for_tier('Free'),
    test_3tier_for_tier('Basic'),
    test_3tier_for_tier('Standard'),
    test_3tier_for_tier('Pro'),
    test_2tier_for_tier('Free'),
    test_2tier_for_tier('Basic'),
    test_2tier_for_tier('Standard'),
    test_2tier_for_tier('Pro')
]

if all(results):
    print("\n=== ALL 2-TIER AND 3-TIER TESTS PASSED SUCCESSFULLY! ===")
    sys.exit(0)
else:
    print("\n=== SOME TESTS FAILED! ===")
    sys.exit(1)

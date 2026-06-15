import pandas as pd
import numpy as np
from scipy.stats import gmean
import io
import streamlit as st
# Dependency injected functions are used instead to avoid circular import

def run_ahp_analysis_v3(df_main, sub_dfs, sub_sub_dfs, cr_threshold, max_iter_val, learning_rate, mean_method, ahp_method, fn_process_single_sheet, fn_fuzzy_ahp):
    """
    [3계층 전용] AHP 분석 및 엑셀 다운로드 생성 로직.
    기존 2계층의 모노리틱 분석 엔진과 분리하여, 완전히 새로운 V3 엔진으로 동작합니다.
    """
    st.info("⚙️ [V3 엔진] 3계층(소분류 포함) 전용 AHP 분석을 시작합니다...")

    # 1. 메인 기준(대분류) 분석
    try:
        main_results_df, main_factors, main_excluded, main_excluded_df = fn_process_single_sheet(
            df_main, cr_threshold, max_iter_val, learning_rate, mean_method, ahp_method
        )
    except Exception as e:
        return False, f"대분류 분석 중 오류가 발생했습니다: {e}", None, None

    if main_results_df.empty:
        return False, "대분류 유효 응답이 부족하여 분석을 진행할 수 없습니다.", None, None

    main_weight_cols = [f"Weight_{f}" for f in main_factors]
    main_matrices = np.stack(main_results_df['Matrix_Object'].values)
    main_group_matrix = np.mean(main_matrices, axis=0) if mean_method == 'arithmetic' else gmean(main_matrices, axis=0)

    if ahp_method == 'fuzzy':
        mw_vals, _ = fn_fuzzy_ahp(main_group_matrix)
        group_main_weights = pd.Series(mw_vals, index=main_weight_cols)
    else:
        if mean_method == 'arithmetic':
            group_main_weights = main_results_df[main_weight_cols].mean(axis=0)
        else:
            group_main_weights = gmean(main_results_df[main_weight_cols].values, axis=0)
        group_main_weights = group_main_weights / group_main_weights.sum()

    # 2. 하위 기준(중분류) 분석
    sub_results_storage = {}
    for parent_factor in main_factors:
        sdf = sub_dfs.get(parent_factor)
        if sdf is None or len(sdf) == 0:
            continue
        
        s_res_df, s_factors, s_excl, s_excl_df = fn_process_single_sheet(sdf, cr_threshold, max_iter_val, learning_rate, mean_method, ahp_method)
        if s_res_df.empty:
            continue
            
        s_weight_cols = [f"Weight_{f}" for f in s_factors]
        s_matrices = np.stack(s_res_df['Matrix_Object'].values)
        s_group_matrix = np.mean(s_matrices, axis=0) if mean_method == 'arithmetic' else gmean(s_matrices, axis=0)
        
        if ahp_method == 'fuzzy':
            sw_vals, _ = fn_fuzzy_ahp(s_group_matrix)
            group_sub_weights = pd.Series(sw_vals, index=s_weight_cols)
        else:
            if mean_method == 'arithmetic':
                group_sub_weights = s_res_df[s_weight_cols].mean(axis=0)
            else:
                group_sub_weights = gmean(s_res_df[s_weight_cols].values, axis=0)
            group_sub_weights = group_sub_weights / group_sub_weights.sum()
            
        sub_results_storage[parent_factor] = {
            "factors": s_factors,
            "weights": group_sub_weights
        }

    # 3. 소분류 기준(3계층) 분석
    sub_sub_results_storage = {}
    for main_f, s_info in sub_results_storage.items():
        for sub_f in s_info['factors']:
            ss_df = sub_sub_dfs.get(sub_f)
            
            # 소분류 데이터가 없거나 1개인 경우 처리 (분석 불가능하므로 가중치 1.0 더미 부여)
            if ss_df is None or len(ss_df) == 0:
                sub_sub_results_storage[sub_f] = {
                    "factors": [f"{sub_f}_단일항목"],
                    "weights": pd.Series([1.0], index=[f"Weight_{sub_f}_단일항목"])
                }
                continue
                
            ss_res_df, ss_factors, ss_excl, ss_excl_df = fn_process_single_sheet(ss_df, cr_threshold, max_iter_val, learning_rate, mean_method, ahp_method)
            
            if ss_res_df.empty:
                # 유효 응답이 없으면 1.0 부여
                sub_sub_results_storage[sub_f] = {
                    "factors": [f"{sub_f}_단일항목"],
                    "weights": pd.Series([1.0], index=[f"Weight_{sub_f}_단일항목"])
                }
                continue

            ss_weight_cols = [f"Weight_{f}" for f in ss_factors]
            ss_matrices = np.stack(ss_res_df['Matrix_Object'].values)
            ss_group_matrix = np.mean(ss_matrices, axis=0) if mean_method == 'arithmetic' else gmean(ss_matrices, axis=0)
            
            if ahp_method == 'fuzzy':
                ssw_vals, _ = fn_fuzzy_ahp(ss_group_matrix)
                group_sub_sub_weights = pd.Series(ssw_vals, index=ss_weight_cols)
            else:
                if mean_method == 'arithmetic':
                    group_sub_sub_weights = ss_res_df[ss_weight_cols].mean(axis=0)
                else:
                    group_sub_sub_weights = gmean(ss_res_df[ss_weight_cols].values, axis=0)
                group_sub_sub_weights = group_sub_sub_weights / group_sub_sub_weights.sum()
                
            sub_sub_results_storage[sub_f] = {
                "factors": ss_factors,
                "weights": group_sub_sub_weights
            }

    # 4. 글로벌 가중치 (Global Weight) 통합 계산
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
                
                # 3계층 글로벌 가중치 = 대분류 * 중분류 * 소분류
                global_w = m_weight * s_weight * ss_weight
                summary_rows.append({
                    "대분류": main_f, "대분류 가중치": m_weight, 
                    "중분류": sub_f, "중분류 가중치": s_weight,
                    "소분류": sub_sub_f, "소분류 가중치": ss_weight,
                    "Global Weight": global_w
                })

    final_df = pd.DataFrame(summary_rows)
    final_df['Global Rank'] = final_df['Global Weight'].rank(ascending=False, method='min').astype(int)
    cols_order = ["대분류", "대분류 가중치", "중분류", "중분류 가중치", "소분류", "소분류 가중치", "Global Weight", "Global Rank"]
    final_df = final_df[cols_order]
    
    # 랭킹에 따라 정렬
    final_df = final_df.sort_values(by="Global Rank")

    # 5. 엑셀 파일 생성 (아주 깔끔하고 직관적인 템플릿 사용)
    output_res = io.BytesIO()
    with pd.ExcelWriter(output_res, engine='xlsxwriter') as writer:
        workbook = writer.book
        
        # Format definitions
        header_fmt = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'bg_color': '#4F81BD', 'font_color': '#FFFFFF', 'border': 1})
        num_fmt = workbook.add_format({'num_format': '0.000', 'align': 'center', 'border': 1})
        center_fmt = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'border': 1})

        # 3-Tier Results Sheet
        sheet_name = '3-Tier AHP 종합결과'
        final_df.to_excel(writer, sheet_name=sheet_name, index=False, startrow=1)
        ws = writer.sheets[sheet_name]
        
        # Title
        ws.write_string(0, 0, "[V3 엔진] 3계층 AHP 종합 가중치 분석 결과", workbook.add_format({'bold': True, 'font_size': 14}))
        
        # Apply formatting
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

    output_res.seek(0)
    
    return True, "분석 성공", final_df, output_res

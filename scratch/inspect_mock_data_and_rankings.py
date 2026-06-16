import pandas as pd
import numpy as np
import sys
import os
sys.path.append('G:\\')
from ahp_utils_v3 import run_ahp_analysis_v3

def inspect_mock():
    file_path = 'G:\\Mock_3Tier_Full.xlsx'
    
    excel_obj = pd.ExcelFile(file_path)
    sheet_names = excel_obj.sheet_names
    
    main_df = pd.read_excel(file_path, sheet_name='Main_Criteria')
    
    samples = len(main_df)
    types = main_df['Type'].nunique() if 'Type' in main_df.columns else 0
    type_counts = main_df['Type'].value_counts().to_dict() if types > 0 else {}
    
    # Get elements by parsing the columns of the sheets
    main_cols = [c for c in main_df.columns if '_' in c and c not in ['ID', 'Type']]
    main_elements = set()
    for col in main_cols:
        parts = col.split('_')
        main_elements.update(parts)
    
    sub_elements = set()
    sub_sub_elements = set()
    
    sub_sheets = []
    sub_sub_sheets = []
    
    for sheet in sheet_names:
        if sheet == 'Main_Criteria': continue
        if sheet in main_elements:
            sub_sheets.append(sheet)
        else:
            sub_sub_sheets.append(sheet)
            
    for sheet in sub_sheets:
        df = pd.read_excel(file_path, sheet_name=sheet)
        cols = [c for c in df.columns if '_' in c and c not in ['ID', 'Type']]
        for col in cols:
            sub_elements.update(col.split('_'))
            
    for sheet in sub_sub_sheets:
        df = pd.read_excel(file_path, sheet_name=sheet)
        cols = [c for c in df.columns if '_' in c and c not in ['ID', 'Type']]
        for col in cols:
            sub_sub_elements.update(col.split('_'))

    print("--- 1. 입력 데이터 개요 ---")
    print(f"전체 표본 수: {samples}")
    print(f"Type 개수: {types} (상세: {type_counts})")
    print(f"대분류 요소 수: {len(main_elements)}")
    print(f"중분류 요소 수: {len(sub_elements)}")
    print(f"소분류 요소 수: {len(sub_sub_elements)}")

    # Now run AHP analysis
    sub_dfs = {}
    sub_sub_dfs = {}
    for sheet in sub_sheets:
        sub_dfs[sheet] = pd.read_excel(file_path, sheet_name=sheet)
    for sheet in sub_sub_sheets:
        sub_sub_dfs[sheet] = pd.read_excel(file_path, sheet_name=sheet)
        
    from app import process_single_sheet, fuzzy_ahp_analysis
    
    print("\n--- 2. AHP 분석 실행 중 ---")
    result_success, result_msg, final_df, _ = run_ahp_analysis_v3(
        main_df, sub_dfs, sub_sub_dfs,
        cr_threshold=0.1, max_iter_val=500, learning_rate=0.6,
        mean_method='geometric', ahp_method='normal',
        fn_process_single_sheet=process_single_sheet,
        fn_fuzzy_ahp=fuzzy_ahp_analysis
    )
    
    print(f"성공 여부: {result_success}")
    if not result_success:
        print(f"오류 메시지: {result_msg}")
        return
        
    print("\n--- 3. 종합분석 랭킹 확인 ---")
    cols = final_df.columns.tolist()
    
    if 'Global Rank' in final_df.columns and 'Global Weight' in final_df.columns:
        sorted_df = final_df.sort_values(by='Global Rank')
        
        # Determine structure columns
        struct_cols = []
        if '대분류' in final_df.columns: struct_cols.append('대분류')
        if '중분류' in final_df.columns: struct_cols.append('중분류')
        if '소분류' in final_df.columns: struct_cols.append('소분류')
        
        print("\n[Top 5 항목]")
        print(sorted_df.head(5)[struct_cols + ['Global Weight', 'Global Rank']].to_string(index=False))
        print("\n[Bottom 5 항목]")
        print(sorted_df.tail(5)[struct_cols + ['Global Weight', 'Global Rank']].to_string(index=False))
        
        # Anomaly checks
        total_weight = final_df['Global Weight'].sum()
        print(f"\n종합가중치 합계: {total_weight:.4f} (정상: 1.0에 근접해야 함)")
        
        rank_calculated = final_df['Global Weight'].rank(ascending=False, method='min').astype(int)
        rank_mismatch = (final_df['Global Rank'] != rank_calculated).sum()
        print(f"가중치 값 기반 랭킹과 'Global Rank' 컬럼의 불일치 수: {rank_mismatch}")
        
        if total_weight < 0.99 or total_weight > 1.01:
            print("=> [이상 발생] 종합가중치 합계가 1.0에서 크게 벗어납니다.")
        elif rank_mismatch > 0:
            print("=> [이상 발생] 계산된 가중치에 따른 순위와 표시된 순위가 일치하지 않습니다.")
        else:
            print("=> [정상] 종합가중치 합이 1.0이며, 랭킹도 올바르게 계산되었습니다.")
    else:
        print(f"결과 컬럼들: {cols}")
        print("Global Rank 또는 Global Weight 컬럼이 없습니다.")

if __name__ == '__main__':
    inspect_mock()

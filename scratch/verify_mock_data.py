import pandas as pd
import numpy as np

def verify_file(file_path):
    print(f"\n--- Verifying: {file_path} ---")
    excel_obj = pd.ExcelFile(file_path)
    sheet_names = excel_obj.sheet_names
    print(f"Sheet names ({len(sheet_names)} total): {sheet_names[:10]} ...")
    
    df_main = pd.read_excel(file_path, sheet_name=sheet_names[0])
    print(f"Main Criteria columns: {df_main.columns.tolist()}")
    print(f"Number of respondents: {len(df_main)}")
    
    # 3-tier identification logic from app.py
    main_criteria_infer = set()
    for col in df_main.columns:
        if '_' in col:
            parts = col.split('_')
            if len(parts) == 2:
                main_criteria_infer.add(parts[0])
                main_criteria_infer.add(parts[1])
                
    print(f"Inferred Main Criteria elements: {list(main_criteria_infer)}")
    
    sub_dfs = {}
    inferred_sub_sub_dfs = {}
    for sn in sheet_names[1:]:
        df_sheet = pd.read_excel(file_path, sheet_name=sn)
        is_sub = any(sn == mc[:31] for mc in main_criteria_infer)
        if is_sub:
            sub_dfs[sn] = df_sheet
        else:
            inferred_sub_sub_dfs[sn] = df_sheet
            
    print(f"Detected {len(sub_dfs)} Sub-Criteria sheets (Tier 2): {list(sub_dfs.keys())}")
    print(f"Detected {len(inferred_sub_sub_dfs)} Sub-Sub-Criteria sheets (Tier 3): {list(inferred_sub_sub_dfs.keys())[:10]} ...")
    
    tier_level = 3 if len(inferred_sub_sub_dfs) > 0 else 2
    print(f"Inferred Tier Level: {tier_level}")
    
    # Check if any sheet is empty or has mismatched rows
    mismatched = []
    for sn in sheet_names:
        df_sheet = pd.read_excel(file_path, sheet_name=sn)
        if len(df_sheet) != len(df_main):
            mismatched.append((sn, len(df_sheet)))
    if mismatched:
        print(f"WARNING: Some sheets have mismatched respondent counts: {mismatched}")
    else:
        print("Success: All sheets have the same number of rows (100 respondents)!")

verify_file(r"G:\Mock_3Tier_Full.xlsx")
verify_file(r"G:\Mock_3Tier_Partial.xlsx")

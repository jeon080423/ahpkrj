import numpy as np
import pandas as pd
from scipy.stats import gmean
import os

def get_ri(n):
    ri_dict = {1: 0.00, 2: 0.00, 3: 0.58, 4: 0.90, 5: 1.12, 6: 1.24, 7: 1.32, 8: 1.41, 9: 1.45, 10: 1.49}
    return ri_dict.get(n, 1.49)

def calculate_consistency(matrix):
    n = matrix.shape[0]
    if n <= 2: return 0.0
    geom_means = gmean(matrix, axis=1)
    weights = geom_means / geom_means.sum()
    weighted_sum = matrix.dot(weights)
    weights_safe = np.where(weights == 0, 1e-10, weights)
    lambda_max = (weighted_sum / weights_safe).mean()
    ci = (lambda_max - n) / (n - 1)
    ri = get_ri(n)
    return ci / ri if ri > 0 else 0.0

def parse_val(v):
    if v == 1: return 1.0
    if v < 0: return float(abs(v))
    return 1.0 / v

def generate_respondent_row(factors, true_weights, noise_prob):
    n = len(factors)
    # Generate pairwise comparison matrix with noise
    matrix = np.eye(n)
    saaty_vals = [1, 2, 3, 4, 5, 6, 7, 8, 9, -2, -3, -4, -5, -6, -7, -8, -9]
    
    excel_values = []
    col_idx = 0
    for i in range(n):
        for j in range(i + 1, n):
            ratio = true_weights[i] / true_weights[j]
            if ratio >= 1:
                saaty_v = int(round(ratio))
                saaty_v = min(9, max(1, saaty_v))
                excel_val = -saaty_v if saaty_v > 1 else 1
            else:
                saaty_v = int(round(1.0 / ratio))
                saaty_v = min(9, max(1, saaty_v))
                excel_val = saaty_v if saaty_v > 1 else 1
            
            # Inject noise
            if np.random.rand() < noise_prob:
                excel_val = np.random.choice(saaty_vals)
                
            excel_values.append(excel_val)
            parsed = parse_val(excel_val)
            matrix[i, j] = parsed
            matrix[j, i] = 1.0 / parsed
            
    cr = calculate_consistency(matrix)
    return excel_values, cr

def generate_sheet_df(factors, num_respondents, noise_prob, group_weights):
    n = len(factors)
    comp_cols = []
    for i in range(n):
        for j in range(i + 1, n):
            comp_cols.append(f"{factors[i]}_{factors[j]}")
            
    rows = []
    crs = []
    for idx in range(1, num_respondents + 1):
        if idx <= num_respondents // 2:
            group = "Group A"
            weights = group_weights["Group A"]
        else:
            group = "Group B"
            weights = group_weights["Group B"]
            
        excel_vals, cr = generate_respondent_row(factors, weights, noise_prob)
        crs.append(cr)
        
        row_dict = {"ID": idx, "Type": group}
        for col_name, val in zip(comp_cols, excel_vals):
            row_dict[col_name] = val
        rows.append(row_dict)
        
    df = pd.DataFrame(rows)
    mean_cr = np.mean(crs)
    return df, mean_cr

def main():
    np.random.seed(42) # Set seed for reproducibility
    num_respondents = 100
    noise_prob = 0.40 # Target average CR is ~0.4
    
    # 1. Define Hierarchy
    main_factors = ['환경경영', '기후변화', '사회책임', '인권경영', '지배구조']
    
    sub_factors = {
        '환경경영': ['친환경제품', '자원순환', '유해물질', '에너지절감', '환경인증'],
        '기후변화': ['탄소배출량', '재생에너지', '온실가스', '기후위기', '친환경차량'],
        '사회책임': ['지역사회', '동반성장', '기부활동', '사회공헌', '상생협력'],
        '인권경영': ['근로조건', '안전보건', '차별금지', '노사관계', '다양성'],
        '지배구조': ['주주권리', '이사회구성', '감사제도', '윤리경영', '공시투명성']
    }
    
    # Define group weights to make ANOVA results distinct and realistic
    main_group_weights = {
        "Group A": [0.40, 0.25, 0.15, 0.12, 0.08],
        "Group B": [0.10, 0.15, 0.25, 0.35, 0.15]
    }
    
    sub_group_weights = {
        "Group A": [0.35, 0.25, 0.20, 0.12, 0.08],
        "Group B": [0.10, 0.15, 0.20, 0.25, 0.30]
    }
    
    sub_sub_group_weights = {
        "Group A": [0.40, 0.25, 0.18, 0.10, 0.07],
        "Group B": [0.08, 0.12, 0.20, 0.30, 0.30]
    }
    
    print("Generating Mock Data for Full 3-Tier Hierarchy...")
    
    # Create Full Hierarchy sheets dictionary
    full_sheets = {}
    sheet_crs = {}
    
    # Generate Main Criteria sheet
    df_main, cr = generate_sheet_df(main_factors, num_respondents, noise_prob, main_group_weights)
    full_sheets["Main_Criteria"] = df_main
    sheet_crs["Main_Criteria"] = cr
    
    # Generate Sub Criteria sheets
    for main_f in main_factors:
        df_sub, cr = generate_sheet_df(sub_factors[main_f], num_respondents, noise_prob, sub_group_weights)
        full_sheets[main_f] = df_sub
        sheet_crs[main_f] = cr
        
        # Generate Sub-Sub Criteria sheets (25 sheets)
        for sub_f in sub_factors[main_f]:
            sub_sub_factors = [f"{sub_f}_요소1", f"{sub_f}_요소2", f"{sub_f}_요소3", f"{sub_f}_요소4", f"{sub_f}_요소5"]
            df_ss, cr = generate_sheet_df(sub_sub_factors, num_respondents, noise_prob, sub_sub_group_weights)
            full_sheets[sub_f] = df_ss
            sheet_crs[sub_f] = cr

    # Save File 1: Full Hierarchy
    file_full = r"G:\Mock_3Tier_Full.xlsx"
    with pd.ExcelWriter(file_full, engine='openpyxl') as writer:
        # Main_Criteria must be the first sheet
        full_sheets["Main_Criteria"].to_excel(writer, sheet_name="Main_Criteria", index=False)
        # Write sub-criteria sheets
        for main_f in main_factors:
            full_sheets[main_f].to_excel(writer, sheet_name=main_f[:31], index=False)
        # Write sub-sub-criteria sheets
        for main_f in main_factors:
            for sub_f in sub_factors[main_f]:
                full_sheets[sub_f].to_excel(writer, sheet_name=sub_f[:31], index=False)
                
    print(f"Saved Full Hierarchy to {file_full}")
    
    # Generate Partial Hierarchy: Only 3 sub-criteria have sub-sub-criteria sheets
    # Selected 3 sub-criteria:
    # 1. '친환경제품' (under '환경경영')
    # 2. '탄소배출량' (under '기후변화')
    # 3. '지역사회' (under '사회책임')
    partial_sub_subs = ['친환경제품', '탄소배출량', '지역사회']
    
    partial_sheets = {}
    partial_sheets["Main_Criteria"] = full_sheets["Main_Criteria"]
    for main_f in main_factors:
        partial_sheets[main_f] = full_sheets[main_f]
        
    for sub_f in partial_sub_subs:
        partial_sheets[sub_f] = full_sheets[sub_f]
        
    # Save File 2: Partial Hierarchy
    file_partial = r"G:\Mock_3Tier_Partial.xlsx"
    with pd.ExcelWriter(file_partial, engine='openpyxl') as writer:
        partial_sheets["Main_Criteria"].to_excel(writer, sheet_name="Main_Criteria", index=False)
        for main_f in main_factors:
            partial_sheets[main_f].to_excel(writer, sheet_name=main_f[:31], index=False)
        for sub_f in partial_sub_subs:
            partial_sheets[sub_f].to_excel(writer, sheet_name=sub_f[:31], index=False)
            
    print(f"Saved Partial Hierarchy to {file_partial}")
    
    # Print out summary statistics
    all_crs = list(sheet_crs.values())
    print("\nGeneration Statistics:")
    print(f"Total Sheets Generated: {len(sheet_crs)}")
    print(f"Overall Average CR: {np.mean(all_crs):.4f}")
    print(f"Min CR: {np.min(all_crs):.4f} (Sheet: {min(sheet_crs, key=sheet_crs.get)})")
    print(f"Max CR: {np.max(all_crs):.4f} (Sheet: {max(sheet_crs, key=sheet_crs.get)})")
    
if __name__ == '__main__':
    main()

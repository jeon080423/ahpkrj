import pandas as pd
import numpy as np
import io
import sys
import os

# Add G:\ to path so we can import ahp_utils_v3
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock Streamlit session state and toast
import streamlit as st
if 'lang' not in st.session_state:
    st.session_state.lang = 'ko'

import ahp_utils_v3

# Mock process_single_sheet
def mock_process_single_sheet(df, cr_threshold, max_iter_val, learning_rate, mean_method, ahp_method):
    # Infer factors from columns
    cols = df.columns[2:]
    factors = []
    for c in cols:
        parts = c.split('_')
        for p in parts:
            if p not in factors:
                factors.append(p)
                
    # Create mock result dataframe
    results_list = []
    n_dim = len(factors)
    mock_matrix = np.eye(n_dim)
    for idx, row in df.iterrows():
        res = {
            "ID": row["ID"],
            "Type": row["Type"],
            "Original_CI": 0.02,
            "Original_CR": 0.03,
            "Final_CI": 0.01,
            "Final_CR": 0.01,
            "Iterations": 5,
            "Corrected": True,
            "Matrix_Object": mock_matrix
        }
        for f in factors:
            res[f"Weight_{f}"] = 1.0 / n_dim
        results_list.append(res)
        
    res_df = pd.DataFrame(results_list)
    excl_df = pd.DataFrame(columns=["ID", "Type", "Sheet"])
    return res_df, factors, 0, excl_df

# Mock fuzzy_ahp_analysis
def mock_fuzzy_ahp(matrix):
    n = matrix.shape[0]
    weights = np.ones(n) / n
    Si = [(0.1, 0.2, 0.3) for _ in range(n)]
    return weights, Si

def run_test():
    # 1. Create dummy input dataframes
    # Main Criteria: 기능성, 디자인, 경제성
    main_cols = ["ID", "Type", "기능성_디자인", "기능성_경제성", "디자인_경제성"]
    main_data = [
        [1, "전문가", 3, 5, 2],
        [2, "전문가", -3, 3, 5],
        [3, "일반", 1, -3, 3],
        [4, "일반", 5, 3, -2]
    ]
    df_main = pd.DataFrame(main_data, columns=main_cols)

    # Sub Criteria: 기능성 -> 하드웨어, 소프트웨어 / 디자인 -> 외관, 편의성 / 경제성 -> 단말기가격, 유지비용
    sub_dfs = {
        "기능성": pd.DataFrame([[1, "전문가", 3], [2, "전문가", -3], [3, "일반", 1], [4, "일반", 5]], columns=["ID", "Type", "하드웨어_소프트웨어"]),
        "디자인": pd.DataFrame([[1, "전문가", 2], [2, "전문가", -2], [3, "일반", 1], [4, "일반", 3]], columns=["ID", "Type", "외관_편의성"]),
        "경제성": pd.DataFrame([[1, "전문가", 5], [2, "전문가", -5], [3, "일반", 1], [4, "일반", -3]], columns=["ID", "Type", "단말기가격_유지비용"])
    }

    # Sub Sub Criteria
    sub_sub_dfs = {
        "하드웨어": pd.DataFrame([[1, "전문가", 3, 2, -2], [2, "전문가", -3, 1, 3], [3, "일반", 1, 2, -2], [4, "일반", -3, -5, 2]], columns=["ID", "Type", "카메라_배터리", "카메라_프로세서", "배터_프로세서"]),
        "소프트웨어": pd.DataFrame([[1, "전문가", 2], [2, "전문가", -2], [3, "일반", 1], [4, "일반", 3]], columns=["ID", "Type", "운영체제_기본앱"]),
        "외관": pd.DataFrame([[1, "전문가", 3], [2, "전문가", -3], [3, "일반", 1], [4, "일반", 2]], columns=["ID", "Type", "색상_재질"]),
        "단말기가격": pd.DataFrame([[1, "전문가", 5], [2, "전문가", -5], [3, "일반", 1], [4, "일반", -2]], columns=["ID", "Type", "일시불_할부"]),
        "유지비용": pd.DataFrame([[1, "전문가", 2], [2, "전문가", -2], [3, "일반", 1], [4, "일반", 3]], columns=["ID", "Type", "통신요금_AS비용"])
    }

    print("Running AHP Analysis V3...")
    success, msg, final_df, output_res = ahp_utils_v3.run_ahp_analysis_v3(
        df_main, sub_dfs, sub_sub_dfs,
        cr_threshold=0.1, max_iter_val=500, learning_rate=0.6,
        mean_method='geometric', ahp_method='normal',
        fn_process_single_sheet=mock_process_single_sheet,
        fn_fuzzy_ahp=mock_fuzzy_ahp
    )

    print("Result Success:", success)
    print("Result Message:", msg)
    if success:
        print("Final DataFrame preview:")
        print(final_df.head(10))
        
        # Save output to file to inspect manually
        with open("G:\\scratch\\test_output_v3.xlsx", "wb") as f:
            f.write(output_res.getvalue())
        print("Excel result saved to G:\\scratch\\test_output_v3.xlsx")

if __name__ == "__main__":
    run_test()

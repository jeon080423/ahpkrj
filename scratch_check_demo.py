import pandas as pd

def clean_id(x):
    s = str(x).strip()
    if s.endswith(".0"):
        s = s[:-2]
    return s

def generate_demographics_summary(demo_df, ahp_df_main=None):
    if demo_df is None or demo_df.empty:
        return None
    
    working_df = demo_df.copy()
    
    # 1. 최종 완료 응답자(ID)만 필터링 (미완료/이탈자 제외)
    completed_ids = set()
    if ahp_df_main is not None:
        if "ID" in ahp_df_main.columns:
            completed_ids = set(ahp_df_main["ID"].apply(clean_id))
    
    id_col = None
    for c in working_df.columns:
        if str(c).strip().lower() == "id":
            id_col = c
            break

    print("id_col:", id_col)
    print("completed_ids:", completed_ids)

    if completed_ids and id_col:
        working_df = working_df[working_df[id_col].apply(clean_id).isin(completed_ids)].copy()

    print("working_df length:", len(working_df))
    if working_df.empty:
        return None

    # 불필요한 시스템용 컬럼 제외
    exclude_keywords = ["id", "type", "사전순위", "답례품", "연락처", "제출시간"]
    target_cols = []
    for col in working_df.columns:
        col_lower = str(col).lower()
        if not any(ex in col_lower for ex in exclude_keywords):
            target_cols.append(col)
    
    print("target_cols:", target_cols)
    if not target_cols:
        return None
        
    summary_rows = []
    for col in target_cols:
        col_str = str(col).strip()
        col_data = working_df[col]
        
        valid_items = []
        for val in col_data:
            if pd.isna(val):
                continue
            val_str = str(val).strip()
            if not val_str or val_str == "미응답(N/A)":
                continue
            if val_str == col_str or (len(val_str) >= 8 and (val_str in col_str or col_str in val_str)):
                continue
            valid_items.append(val_str)
        
        print(f"Col: {col}, valid_items: {valid_items}")
        if not valid_items:
            continue
        
        series_valid = pd.Series(valid_items)
        counts = series_valid.value_counts()
        total = len(valid_items)
        for val, count in counts.items():
            pct = (count / total) * 100 if total > 0 else 0
            summary_rows.append({
                "인구통계 항목 (Demographic Field)": col,
                "응답 보기 (Value)": val,
                "빈도수 (Frequency)": count,
                "비율 (Percentage, %)": round(pct, 1)
            })
            
    if summary_rows:
        return pd.DataFrame(summary_rows)
    return None

demo_df = pd.DataFrame({
    "ID": [1, 2, 3],
    "현재 소속 또는 업무 분야는 무엇입니까?": ["현재 소속 또는 업무 분야는 무엇입니까?", "A", "B"],
    "성별": ["남", "여", "미응답(N/A)"]
})

ahp_df_main = pd.DataFrame({
    "ID": [2.0, 3.0]
})

print(generate_demographics_summary(demo_df, ahp_df_main))

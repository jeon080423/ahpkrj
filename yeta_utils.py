import math

def convert_bc_to_ahp_pairwise(bc_ratio):
    """
    KDI 예비타당성조사 지침에 따라 B/C 비율(경제성)을 AHP 쌍대비교 척도(1~9)로 변환합니다.
    공식: 표준점수 = 8.592933 * ln(B/C 비율) + i (단, B/C >= 1 -> i=1, B/C < 1 -> i=-1)
    """
    if bc_ratio <= 0:
        return 1.0 / 9.0  # 최소값 제한
        
    ln_bc = math.log(bc_ratio)
    if bc_ratio >= 1.0:
        score = 8.592933 * ln_bc + 1.0
    else:
        score = 8.592933 * ln_bc - 1.0
        
    # AHP 척도로 매핑 (1.0 ~ 9.0)
    if score >= 0:
        # 사업시행 선호
        return min(9.0, max(1.0, score))
    else:
        # 사업미시행 선호
        abs_score = -score
        bounded_abs = min(9.0, max(1.0, abs_score))
        return 1.0 / bounded_abs

def convert_lir_to_ahp_pairwise(lir_value):
    """
    지역낙후도지수 표준화값(LIR/MIR)을 AHP 쌍대비교 척도(1~9)로 변환합니다.
    지표가 높을수록 지역이 낙후되었음을 의미하므로, 사업시행 선호도가 올라갑니다.
    """
    # 임계치 기반 매핑 (2 * LIR + 1.0)
    score = 2.0 * lir_value + 1.0
    if score >= 0:
        return min(9.0, max(1.0, score))
    else:
        bounded_abs = min(9.0, max(1.0, -score))
        return 1.0 / bounded_abs

def validate_yeta_level1_weights(project_type, econ_w, policy_w, regional_w=0.0, tech_w=0.0):
    """
    KDI 예타 수행지침상의 사업유형별 제1계층 가중치 범위 적합성을 검증합니다.
    """
    total = econ_w + policy_w + regional_w + tech_w
    if abs(total - 1.0) > 0.01:
        return False, f"가중치 합계가 100%가 아닙니다. (현재 합계: {total*100:.1f}%)"
        
    if project_type == "construction_non_capital":
        # 건설사업(비수도권): 경제성 30~45%, 정책성 25~40%, 지역균형발전 30~40%
        if not (0.30 <= econ_w <= 0.45):
            return False, f"경제성 가중치 범위 초과: 30~45% (현재: {econ_w*100:.1f}%)"
        if not (0.25 <= policy_w <= 0.40):
            return False, f"정책성 가중치 범위 초과: 25~40% (현재: {policy_w*100:.1f}%)"
        if not (0.30 <= regional_w <= 0.40):
            return False, f"지역균형발전 가중치 범위 초과: 30~40% (현재: {regional_w*100:.1f}%)"
            
    elif project_type == "construction_capital":
        # 건설사업(수도권): 경제성 60~70%, 정책성 30~40% (지역균형발전은 제외)
        if not (0.60 <= econ_w <= 0.70):
            return False, f"경제성 가중치 범위 초과: 60~70% (현재: {econ_w*100:.1f}%)"
        if not (0.30 <= policy_w <= 0.40):
            return False, f"정책성 가중치 범위 초과: 30~40% (현재: {policy_w*100:.1f}%)"
        if abs(regional_w) > 0.01:
            return False, "수도권 사업은 지역균형발전 가중치를 부여할 수 없습니다."
            
    elif project_type == "rnd_bc":
        # R&D / 정보화 (B/C 분석): 경제성 40~50%, 기술성 30~40%, 정책성 20~30%
        if not (0.40 <= econ_w <= 0.50):
            return False, f"경제성 가중치 범위 초과: 40~50% (현재: {econ_w*100:.1f}%)"
        if not (0.30 <= tech_w <= 0.40):
            return False, f"기술성 가중치 범위 초과: 30~40% (현재: {tech_w*100:.1f}%)"
        if not (0.20 <= policy_w <= 0.30):
            return False, f"정책성 가중치 범위 초과: 20~30% (현재: {policy_w*100:.1f}%)"
            
    elif project_type == "rnd_ec":
        # R&D / 정보화 (E/C 분석): 경제성 30~40%, 기술성 40~50%, 정책성 20~30%
        if not (0.30 <= econ_w <= 0.40):
            return False, f"경제성 가중치 범위 초과: 30~40% (현재: {econ_w*100:.1f}%)"
        if not (0.40 <= tech_w <= 0.50):
            return False, f"기술성 가중치 범위 초과: 40~50% (현재: {tech_w*100:.1f}%)"
        if not (0.20 <= policy_w <= 0.30):
            return False, f"정책성 가중치 범위 초과: 20~30% (현재: {policy_w*100:.1f}%)"
            
    elif project_type == "other_bc":
        # 기타 재정사업 (B/C 분석): 경제성 25~50%, 정책성 50~75%
        if not (0.25 <= econ_w <= 0.50):
            return False, f"경제성 가중치 범위 초과: 25~50% (현재: {econ_w*100:.1f}%)"
        if not (0.50 <= policy_w <= 0.75):
            return False, f"정책성 가중치 범위 초과: 50~75% (현재: {policy_w*100:.1f}%)"
            
    elif project_type == "other_ec":
        # 기타 재정사업 (E/C 분석): 경제성 20~40%, 정책성 60~80%
        if not (0.20 <= econ_w <= 0.40):
            return False, f"경제성 가중치 범위 초과: 20~40% (현재: {econ_w*100:.1f}%)"
        if not (0.60 <= policy_w <= 0.80):
            return False, f"정책성 가중치 범위 초과: 60~80% (현재: {policy_w*100:.1f}%)"
            
    return True, "가중치 범위 적합성 검증 성공"

def aggregate_yeta_group_ahp(evaluator_scores):
    """
    예비타당성조사 AHP 종합평점 산정 시 최고/최저 점수를 가진 평가자(극단값 2인)를 배제하고 기하평균을 집계합니다.
    """
    n = len(evaluator_scores)
    if n >= 3:
        sorted_scores = sorted(evaluator_scores)
        # 최대값 1인, 최소값 1인 제외
        filtered_scores = sorted_scores[1:-1]
    else:
        filtered_scores = evaluator_scores
        
    if not filtered_scores:
        return 0.0
        
    log_sum = sum(math.log(s) for s in filtered_scores if s > 0)
    geom_mean = math.exp(log_sum / len(filtered_scores))
    return geom_mean


import pandas as pd
import numpy as np
import io

def calculate_ahp_eigenvector_and_cr(matrix_size, matrix_data):
    try:
        eigvals, eigvecs = np.linalg.eig(matrix_data)
        max_index = np.argmax(np.real(eigvals))
        max_eigval = np.real(eigvals[max_index])
        
        principal_eigvec = np.real(eigvecs[:, max_index])
        weights = principal_eigvec / np.sum(principal_eigvec)
        
        ri_dict = {1: 0.0, 2: 0.0, 3: 0.58, 4: 0.90, 5: 1.12, 6: 1.24, 7: 1.32, 8: 1.41, 9: 1.45, 10: 1.49}
        n = matrix_size
        if n <= 2:
            cr = 0.0
        else:
            ci = (max_eigval - n) / (n - 1)
            ri = ri_dict.get(n, 1.49)
            cr = ci / ri if ri > 0 else 0.0
            
        return weights, cr
    except Exception as e:
        return None, None

def generate_yeta_excel_template(project_type):
    columns = ["평가자_ID", "소속_및_성명", "전문_역할"]
    
    if project_type == "construction_non_capital":
        columns.extend(["1계층_경제성(%)", "1계층_정책성(%)", "1계층_지역균형발전(%)"])
    elif project_type == "construction_capital":
        columns.extend(["1계층_경제성(%)", "1계층_정책성(%)"])
    elif "rnd" in project_type:
        columns.extend(["1계층_경제성(%)", "1계층_기술성(%)", "1계층_정책성(%)"])
    else:
        columns.extend(["1계층_경제성(%)", "1계층_정책성(%)"])
        
    columns.extend([
        "쌍대비교_정책1_vs_정책2(실수형)", 
        "쌍대비교_정책1_vs_정책3(실수형)", 
        "쌍대비교_정책2_vs_정책3(실수형)"
    ])
    
    columns.extend([
        "대안평가_정책1(시행선호_1~9_역수)",
        "대안평가_정책2(시행선호_1~9_역수)",
        "대안평가_정책3(시행선호_1~9_역수)"
    ])
    
    df = pd.DataFrame(columns=columns)
    for i in range(1, 11):
        row_data = [f"E{i:02d}", "", ""]
        if project_type == "construction_non_capital":
            row_data.extend([40, 30, 30])
        elif project_type == "construction_capital":
            row_data.extend([60, 40])
        elif "rnd" in project_type:
            row_data.extend([40, 40, 20])
        else:
            row_data.extend([40, 60])
            
        row_data.extend([1.0, 3.0, 1/3])  # Sample pairwise
        row_data.extend([5.0, 1.0, 1/5])  # Sample alternatives
        df.loc[i-1] = row_data
        
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='YETA_AHP_Data')
        
    return output.getvalue()

def process_yeta_ahp_data(df, project_type, bc_ratio, lir_value):
    results = []
    
    # To avoid circular import, we call functions directly if they are in the same module
    from yeta_utils import convert_bc_to_ahp_pairwise, convert_lir_to_ahp_pairwise, aggregate_yeta_group_ahp
    
    bc_pairwise = convert_bc_to_ahp_pairwise(bc_ratio)
    bc_weight_go = bc_pairwise / (bc_pairwise + 1.0)
    
    lir_weight_go = 0.5
    has_regional = False
    if "non_capital" in project_type or project_type in ["other_bc", "other_ec"]:
        has_regional = True
        lir_pairwise = convert_lir_to_ahp_pairwise(lir_value)
        lir_weight_go = lir_pairwise / (lir_pairwise + 1.0)
        
    for idx, row in df.iterrows():
        try:
            eval_id = row.get("평가자_ID", f"Evaluator_{idx+1}")
            
            w_econ = float(row.get("1계층_경제성(%)", 0)) / 100.0
            w_policy = float(row.get("1계층_정책성(%)", 0)) / 100.0
            w_tech = float(row.get("1계층_기술성(%)", 0)) / 100.0 if "rnd" in project_type else 0.0
            w_reg = float(row.get("1계층_지역균형발전(%)", 0)) / 100.0 if has_regional else 0.0
            
            total_w = w_econ + w_policy + w_tech + w_reg
            if total_w > 0:
                w_econ /= total_w; w_policy /= total_w; w_tech /= total_w; w_reg /= total_w
                
            v12 = float(row.get("쌍대비교_정책1_vs_정책2(실수형)", 1.0))
            v13 = float(row.get("쌍대비교_정책1_vs_정책3(실수형)", 1.0))
            v23 = float(row.get("쌍대비교_정책2_vs_정책3(실수형)", 1.0))
            
            mat = np.array([
                [1.0, v12, v13],
                [1.0/v12, 1.0, v23],
                [1.0/v13, 1.0/v23, 1.0]
            ])
            
            policy_weights, cr = calculate_ahp_eigenvector_and_cr(3, mat)
            if cr is None: cr = 0.0
            
            alt_p1 = float(row.get("대안평가_정책1(시행선호_1~9_역수)", 1.0))
            alt_p2 = float(row.get("대안평가_정책2(시행선호_1~9_역수)", 1.0))
            alt_p3 = float(row.get("대안평가_정책3(시행선호_1~9_역수)", 1.0))
            
            w_alt_p1_go = alt_p1 / (alt_p1 + 1.0)
            w_alt_p2_go = alt_p2 / (alt_p2 + 1.0)
            w_alt_p3_go = alt_p3 / (alt_p3 + 1.0)
            
            policy_go = policy_weights[0]*w_alt_p1_go + policy_weights[1]*w_alt_p2_go + policy_weights[2]*w_alt_p3_go
            
            final_go = w_econ * bc_weight_go + w_policy * policy_go + w_reg * lir_weight_go
            if "rnd" in project_type:
                final_go += w_tech * 0.5  # Mock tech score
                
            cr_pass = "PASS" if cr <= 0.15 else "FAIL"
            
            results.append({
                "평가자_ID": eval_id,
                "CR": cr,
                "CR통과": cr_pass,
                "시행점수": final_go,
                "미시행점수": 1.0 - final_go
            })
            
        except Exception as e:
            results.append({
                "평가자_ID": row.get("평가자_ID", f"Row_{idx+1}"),
                "CR": 0.0,
                "CR통과": f"ERROR",
                "시행점수": 0.0,
                "미시행점수": 1.0
            })
            
    res_df = pd.DataFrame(results)
    
    valid_df = res_df[res_df["CR통과"] == "PASS"].copy()
    valid_df["극단값배제"] = "포함"
    
    if len(valid_df) >= 3:
        max_idx = valid_df["시행점수"].idxmax()
        min_idx = valid_df["시행점수"].idxmin()
        valid_df.loc[max_idx, "극단값배제"] = "배제(Max)"
        valid_df.loc[min_idx, "극단값배제"] = "배제(Min)"
        
    res_df = res_df.merge(valid_df[["평가자_ID", "극단값배제"]], on="평가자_ID", how="left")
    res_df["극단값배제"] = res_df["극단값배제"].fillna("제외(CR Fail/Error)")
    
    final_scores = valid_df[valid_df["극단값배제"] == "포함"]["시행점수"].tolist()
    geom_mean = aggregate_yeta_group_ahp(final_scores) if final_scores else 0.0
    
    return res_df, geom_mean

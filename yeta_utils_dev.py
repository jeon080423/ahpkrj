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

def generate_yeta_excel_template(project_type, policy_factors=None, regional_factors=None, tech_factors=None):
    if not policy_factors: policy_factors = ["정책1", "정책2"]
    if not regional_factors: regional_factors = ["지역균형1", "지역균형2"]
    if not tech_factors: tech_factors = ["기술1", "기술2"]
    
    columns = ["평가자_ID", "소속_및_성명", "전문_역할"]
    
    factors_map = {}
    if project_type == "construction_non_capital":
        columns.extend(["1계층_경제성(%)", "1계층_정책성(%)", "1계층_지역균형발전(%)"])
        factors_map = {"정책": policy_factors, "지역균형": regional_factors}
    elif project_type == "construction_capital":
        columns.extend(["1계층_경제성(%)", "1계층_정책성(%)"])
        factors_map = {"정책": policy_factors}
    elif "rnd" in project_type:
        columns.extend(["1계층_경제성(%)", "1계층_기술성(%)", "1계층_정책성(%)"])
        factors_map = {"기술": tech_factors, "정책": policy_factors}
    else:
        columns.extend(["1계층_경제성(%)", "1계층_정책성(%)"])
        factors_map = {"정책": policy_factors}
        
    for cat, factors in factors_map.items():
        if len(factors) > 1:
            for i in range(len(factors)):
                for j in range(i+1, len(factors)):
                    columns.append(f"쌍대비교_[{cat}]_{factors[i].strip()}_vs_{factors[j].strip()}(실수형)")
                    
    for cat, factors in factors_map.items():
        for factor in factors:
            columns.append(f"대안평가_[{cat}]_{factor.strip()}(시행선호_1~9_역수)")
            
    import pandas as pd
    import io
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
            
        for cat, factors in factors_map.items():
            if len(factors) > 1:
                pairs_count = len(factors) * (len(factors) - 1) // 2
                row_data.extend([1.0]*pairs_count)
        
        for cat, factors in factors_map.items():
            for factor in factors:
                row_data.append(5.0)
                
        df.loc[i-1] = row_data
        
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='YETA_AHP_Data')
        
    return output.getvalue()

def process_yeta_ahp_data(df, project_type, bc_ratio, lir_value):
    results = []
    
    from yeta_utils import convert_bc_to_ahp_pairwise, convert_lir_to_ahp_pairwise, aggregate_yeta_group_ahp
    import numpy as np
    
    bc_pairwise = convert_bc_to_ahp_pairwise(bc_ratio)
    bc_weight_go = bc_pairwise / (bc_pairwise + 1.0)
    
    lir_weight_go = 0.5
    has_regional = False
    if "non_capital" in project_type or project_type in ["other_bc", "other_ec"]:
        has_regional = True
        lir_pairwise = convert_lir_to_ahp_pairwise(lir_value)
        lir_weight_go = lir_pairwise / (lir_pairwise + 1.0)
        
    # Pre-parse categories from columns
    cat_factors = {}
    for col in df.columns:
        if col.startswith("대안평가_[") and "]_" in col:
            cat = col.split("]_")[0].replace("대안평가_[", "")
            factor = col.split("]_")[1].split("(시행선호")[0]
            if cat not in cat_factors: cat_factors[cat] = []
            if factor not in cat_factors[cat]: cat_factors[cat].append(factor)
            
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
                
            cat_scores = {}
            max_cr = 0.0
            
            for cat, factors in cat_factors.items():
                n = len(factors)
                if n > 1:
                    mat = np.ones((n, n))
                    for i in range(n):
                        for j in range(i+1, n):
                            col_name = f"쌍대비교_[{cat}]_{factors[i]}_vs_{factors[j]}(실수형)"
                            v = float(row.get(col_name, 1.0))
                            if v < 0: v = abs(v) # basic robust fix
                            if v == 0: v = 1.0
                            mat[i, j] = v
                            mat[j, i] = 1.0 / v
                            
                    weights, cr = calculate_ahp_eigenvector_and_cr(n, mat)
                    if cr is None: cr = 0.0
                    max_cr = max(max_cr, cr)
                elif n == 1:
                    weights = [1.0]
                else:
                    weights = []
                    
                cat_go = 0.0
                for i, factor in enumerate(factors):
                    alt_col = f"대안평가_[{cat}]_{factor}(시행선호_1~9_역수)"
                    alt_v = float(row.get(alt_col, 1.0))
                    if alt_v < 0: alt_v = abs(alt_v)
                    if alt_v == 0: alt_v = 1.0
                    alt_go = alt_v / (alt_v + 1.0)
                    cat_go += weights[i] * alt_go
                    
                cat_scores[cat] = cat_go
                
            policy_go = cat_scores.get("정책", 0.5)
            tech_go = cat_scores.get("기술", 0.5)
            reg_go = cat_scores.get("지역균형", 0.5)
            
            final_go = w_econ * bc_weight_go + w_policy * policy_go + w_reg * lir_weight_go
            if "rnd" in project_type:
                final_go += w_tech * tech_go
                
            cr_pass = "PASS" if max_cr <= 0.15 else "FAIL"
            
            results.append({
                "평가자 ID": eval_id,
                "경제성 가중치": w_econ,
                "정책성 가중치": w_policy,
                "지역균형 가중치": w_reg,
                "기술성 가중치": w_tech,
                "경제성 점수": bc_weight_go,
                "정책성 점수": policy_go,
                "지역균형 점수": lir_weight_go if has_regional else 0.0,
                "기술성 점수": tech_go if "rnd" in project_type else 0.0,
                "최대 일관성 비율(Max CR)": max_cr,
                "CR 통과": cr_pass,
                "최종 시행(Go) 평점": final_go
            })
            
        except Exception as e:
            print(f"Error processing row {idx}: {e}")
            pass
            
    import pandas as pd
    res_df = pd.DataFrame(results)
    if len(res_df) == 0:
        return res_df, 0.0
        
    passed_df = res_df[res_df["CR 통과"] == "PASS"]
    if len(passed_df) == 0:
        return res_df, 0.0
        
    scores = passed_df["최종 시행(Go) 평점"].tolist()
    final_score = aggregate_yeta_group_ahp(scores)
    
    # Mark excluded
    passed_df = passed_df.copy()
    passed_df["극단값 배제"] = "-"
    n_pass = len(scores)
    if n_pass >= 3:
        max_s = max(scores)
        min_s = min(scores)
        
        excluded_ids = []
        max_idx = passed_df.index[passed_df["최종 시행(Go) 평점"] == max_s].tolist()[0]
        min_idx = passed_df.index[passed_df["최종 시행(Go) 평점"] == min_s].tolist()[0]
        
        passed_df.loc[max_idx, "극단값 배제"] = "O (최고점)"
        passed_df.loc[min_idx, "극단값 배제"] = "O (최저점)"
        
    res_df = res_df.merge(passed_df[["평가자 ID", "극단값 배제"]], on="평가자 ID", how="left")
    res_df["극단값 배제"] = res_df["극단값 배제"].fillna("-")
    
    return res_df, final_score

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

def improve_yeta_consistency(matrix_data, threshold=0.15, max_iter=500, learning_rate=0.6):
    current_matrix = np.array(matrix_data, dtype=float)
    n = current_matrix.shape[0]
    weights, cr = calculate_ahp_eigenvector_and_cr(n, current_matrix)
    if cr is None or cr <= threshold:
        return weights, cr
        
    for _ in range(max_iter):
        consistent_matrix = np.outer(weights, 1.0 / weights)
        new_matrix = (current_matrix * (1 - learning_rate)) + (consistent_matrix * learning_rate)
        np.fill_diagonal(new_matrix, 1.0)
        
        for i in range(n):
            for j in range(i+1, n):
                val = new_matrix[i, j]
                if val < 1/9.0: val = 1/9.0
                elif val > 9.0: val = 9.0
                new_matrix[i, j] = val
                new_matrix[j, i] = 1.0 / val
                
        current_matrix = new_matrix
        weights, cr = calculate_ahp_eigenvector_and_cr(n, current_matrix)
        if cr is None or cr <= threshold:
            break
            
    return weights, cr

def generate_yeta_excel_template(project_type, policy_factors=None, regional_factors=None, tech_factors=None):
    if not policy_factors: policy_factors = {"정책1": [], "정책2": []}
    elif isinstance(policy_factors, list): policy_factors = {f: [] for f in policy_factors}
    if not regional_factors: regional_factors = {"지역균형1": [], "지역균형2": []}
    elif isinstance(regional_factors, list): regional_factors = {f: [] for f in regional_factors}
    if not tech_factors: tech_factors = {"기술1": [], "기술2": []}
    elif isinstance(tech_factors, list): tech_factors = {f: [] for f in tech_factors}
    
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
        
    for cat, factor_dict in factors_map.items():
        t2_list = list(factor_dict.keys())
        if len(t2_list) > 1:
            for i in range(len(t2_list)):
                for j in range(i+1, len(t2_list)):
                    columns.append(f"쌍대비교_[{cat}]_{t2_list[i].strip()}_vs_{t2_list[j].strip()}(실수형)")
                    
        for t2, t3_list in factor_dict.items():
            if len(t3_list) > 1:
                for i in range(len(t3_list)):
                    for j in range(i+1, len(t3_list)):
                        columns.append(f"쌍대비교_[{cat}_{t2.strip()}]_{t3_list[i].strip()}_vs_{t3_list[j].strip()}(실수형)")
                        
    for cat, factor_dict in factors_map.items():
        for t2, t3_list in factor_dict.items():
            if not t3_list:
                columns.append(f"대안평가_[{cat}]_{t2.strip()}(시행선호_1~9_역수)")
            else:
                for t3 in t3_list:
                    columns.append(f"대안평가_[{cat}_{t2.strip()}]_{t3.strip()}(시행선호_1~9_역수)")
                    
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
            
        for cat, factor_dict in factors_map.items():
            t2_list = list(factor_dict.keys())
            if len(t2_list) > 1:
                pairs_count = len(t2_list) * (len(t2_list) - 1) // 2
                row_data.extend([1.0]*pairs_count)
            for t2, t3_list in factor_dict.items():
                if len(t3_list) > 1:
                    pairs_count = len(t3_list) * (len(t3_list) - 1) // 2
                    row_data.extend([1.0]*pairs_count)
        
        for cat, factor_dict in factors_map.items():
            for t2, t3_list in factor_dict.items():
                if not t3_list:
                    row_data.append(5.0)
                else:
                    for t3 in t3_list:
                        row_data.append(5.0)
                
        df.loc[i-1] = row_data
        
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        guide_data = {
            "📊 데이터 입력 가이드": [
                "1. 쌍대비교 및 대안평가 데이터 입력 (음수/양수 활용)",
                "  - 왼쪽(시행) 항목이 더 중요하면: 음수 입력 (예: -3)",
                "  - 오른쪽(미시행) 항목이 더 중요하면: 양수 입력 (예: 3)",
                "  - 두 항목이 동등하게 중요하면: 1 입력",
                "",
                "2. 필수 정보 입력",
                "  - A열(평가자_ID), B/C열에 그룹명 등 식별 정보를 입력합니다.",
                "  - 모든 쌍대비교 칸에 빈칸 없이 숫자를 입력해 주시기 바랍니다."
            ]
        }
        pd.DataFrame(guide_data).to_excel(writer, index=False, sheet_name='입력_가이드')
        df.to_excel(writer, index=False, sheet_name='YETA_AHP_Data')
        
    return output.getvalue()

def generate_yeta_excel_template_dynamic(project_type, ahp_model):
    import pandas as pd
    import io
    columns = []
    columns.extend(["평가자_ID", "그룹명(예: 전문가, 공무원 등)", "기타_식별정보"])
    
    # 1계층 상수합
    if "non_capital" in project_type:
        columns.extend(["1계층_경제성(%)", "1계층_정책성(%)", "1계층_지역균형발전(%)"])
    elif "capital" in project_type:
        columns.extend(["1계층_경제성(%)", "1계층_정책성(%)"])
    elif "rnd" in project_type:
        columns.extend(["1계층_기술성(%)", "1계층_경제성(%)", "1계층_정책성(%)"])
    else:
        columns.extend(["1계층_경제성(%)", "1계층_정책성(%)"])
        
    main_criteria = ahp_model.get("main", [])
    sub_criteria_map = ahp_model.get("subs", {})
    sub_sub_map = ahp_model.get("sub_subs", {})
    
    # 쌍대비교 컬럼 생성 (2계층, 3계층)
    for main_c in main_criteria:
        subs = sub_criteria_map.get(main_c, [])
        if len(subs) > 1:
            for i in range(len(subs)):
                for j in range(i+1, len(subs)):
                    columns.append(f"쌍대비교_[{main_c}]_{subs[i].strip()}_vs_{subs[j].strip()}(실수형)")
                    
        for sub_c in subs:
            sub_subs = sub_sub_map.get(sub_c, [])
            if len(sub_subs) > 1:
                for i in range(len(sub_subs)):
                    for j in range(i+1, len(sub_subs)):
                        columns.append(f"쌍대비교_[{main_c}_{sub_c.strip()}]_{sub_subs[i].strip()}_vs_{sub_subs[j].strip()}(실수형)")
                        
    # 대안평가 컬럼 생성 (최하위 요인)
    for main_c in main_criteria:
        subs = sub_criteria_map.get(main_c, [])
        if not subs:
            columns.append(f"대안평가_[{main_c}]_{main_c.strip()}(시행선호_1~9_역수)")
        for sub_c in subs:
            sub_subs = sub_sub_map.get(sub_c, [])
            if not sub_subs:
                columns.append(f"대안평가_[{main_c}]_{sub_c.strip()}(시행선호_1~9_역수)")
            else:
                for t3 in sub_subs:
                    columns.append(f"대안평가_[{main_c}_{sub_c.strip()}]_{t3.strip()}(시행선호_1~9_역수)")
                    
    df = pd.DataFrame(columns=columns)
    
    # Mock data rows
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
            
        for main_c in main_criteria:
            subs = sub_criteria_map.get(main_c, [])
            if len(subs) > 1:
                pairs_count = len(subs) * (len(subs) - 1) // 2
                row_data.extend([1.0]*pairs_count)
            for sub_c in subs:
                sub_subs = sub_sub_map.get(sub_c, [])
                if len(sub_subs) > 1:
                    pairs_count = len(sub_subs) * (len(sub_subs) - 1) // 2
                    row_data.extend([1.0]*pairs_count)
        
        for main_c in main_criteria:
            subs = sub_criteria_map.get(main_c, [])
            if not subs:
                row_data.append(5.0)
            for sub_c in subs:
                sub_subs = sub_sub_map.get(sub_c, [])
                if not sub_subs:
                    row_data.append(5.0)
                else:
                    for t3 in sub_subs:
                        row_data.append(5.0)
                
        df.loc[i-1] = row_data
        
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        guide_data = {
            "📊 데이터 입력 가이드": [
                "1. 쌍대비교 및 대안평가 데이터 입력 (음수/양수 활용)",
                "  - 왼쪽(시행) 항목이 더 중요하면: 음수 입력 (예: -3)",
                "  - 오른쪽(미시행) 항목이 더 중요하면: 양수 입력 (예: 3)",
                "  - 두 항목이 동등하게 중요하면: 1 입력",
                "",
                "2. 필수 정보 입력",
                "  - A열(평가자_ID), B/C열에 그룹명 등 식별 정보를 입력합니다.",
                "  - 모든 쌍대비교 칸에 빈칸 없이 숫자를 입력해 주시기 바랍니다."
            ]
        }
        pd.DataFrame(guide_data).to_excel(writer, index=False, sheet_name='입력_가이드')
        df.to_excel(writer, index=False, sheet_name='YETA_AHP_Data')
        
    return output.getvalue()


def process_yeta_ahp_data(df, project_type, bc_ratio, lir_value, auto_correct_cr=True):
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
        
    # Build hierarchical tree from columns
    children_map = {}
    for col in df.columns:
        if col.startswith("쌍대비교_[") and "]_" in col:
            path = col.split("]_")[0].replace("쌍대비교_[", "")
            factors_str = col.split("]_")[1].split("(실수형")[0]
            f1, f2 = factors_str.split("_vs_")
            if path not in children_map: children_map[path] = []
            if f1 not in children_map[path]: children_map[path].append(f1)
            if f2 not in children_map[path]: children_map[path].append(f2)
            
    for col in df.columns:
        if col.startswith("대안평가_[") and "]_" in col:
            path = col.split("]_")[0].replace("대안평가_[", "")
            factor = col.split("]_")[1].split("(시행선호")[0]
            if path not in children_map: children_map[path] = []
            if factor not in children_map[path]: children_map[path].append(factor)
            
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
                
            max_cr = 0.0
            local_weights = {}
            
            for path, factors in children_map.items():
                n = len(factors)
                if n > 1:
                    mat = np.ones((n, n))
                    for i in range(n):
                        for j in range(i+1, n):
                            col_name = f"쌍대비교_[{path}]_{factors[i]}_vs_{factors[j]}(실수형)"
                            v = float(row.get(col_name, 1.0))
                            if v == 0 or v == 1: 
                                mat_v = 1.0
                            elif v < 0: 
                                mat_v = abs(v) # Left preferred
                            else:
                                mat_v = 1.0 / v # Right preferred
                            mat[i, j] = mat_v
                            mat[j, i] = 1.0 / mat_v
                            
                    weights, cr = calculate_ahp_eigenvector_and_cr(n, mat)
                    if cr is not None and cr > 0.15 and auto_correct_cr:
                        weights, cr = improve_yeta_consistency(mat, threshold=0.15)
                    if cr is None: cr = 0.0
                    max_cr = max(max_cr, cr)
                elif n == 1:
                    weights = [1.0]
                else:
                    weights = []
                    
                local_weights[path] = dict(zip(factors, weights))
                
            def get_go_score(path, factor_name):
                next_path = f"{path}_{factor_name}"
                if next_path in children_map:
                    child_go_sum = 0.0
                    for child_name in children_map[next_path]:
                        child_local_w = local_weights[next_path].get(child_name, 0)
                        child_go_score = get_go_score(next_path, child_name)
                        child_go_sum += child_local_w * child_go_score
                    return child_go_sum
                else:
                    alt_col = f"대안평가_[{path}]_{factor_name}(시행선호_1~9_역수)"
                    alt_v = float(row.get(alt_col, 1.0))
                    if alt_v == 0 or alt_v == 1:
                        mat_alt_v = 1.0
                    elif alt_v < 0:
                        mat_alt_v = abs(alt_v)
                    else:
                        mat_alt_v = 1.0 / alt_v
                    return mat_alt_v / (mat_alt_v + 1.0)
                    
            policy_go = 0.5
            pol_key = next((k for k in children_map.keys() if "정책" in k), None)
            if pol_key:
                policy_go = 0.0
                for child in children_map[pol_key]:
                    w = local_weights[pol_key].get(child, 0)
                    go = get_go_score(pol_key, child)
                    policy_go += w * go
                    
            tech_go = 0.5
            tech_key = next((k for k in children_map.keys() if "기술" in k), None)
            if tech_key:
                tech_go = 0.0
                for child in children_map[tech_key]:
                    w = local_weights[tech_key].get(child, 0)
                    go = get_go_score(tech_key, child)
                    tech_go += w * go
                    
            reg_go = 0.5
            reg_key = next((k for k in children_map.keys() if "지역" in k), None)
            if reg_key:
                reg_go = 0.0
                for child in children_map[reg_key]:
                    w = local_weights[reg_key].get(child, 0)
                    go = get_go_score(reg_key, child)
                    reg_go += w * go
            
            final_go = w_econ * bc_weight_go + w_policy * policy_go + w_reg * lir_weight_go
            if "rnd" in project_type:
                final_go += w_tech * tech_go
                
            cr_pass = "PASS" if max_cr <= 0.15 else "FAIL"
            
            res_row = {
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
            }
            for path, lw_dict in local_weights.items():
                for factor, w in lw_dict.items():
                    res_row[f"가중치_[{path}]_{factor}"] = w
            
            results.append(res_row)
            
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

def export_yeta_result_excel(summary_df, res_df, final_score=None, is_pass=None):
    import io
    import pandas as pd
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        workbook = writer.book
        
        # Formats
        header_format = workbook.add_format({
            'bold': True, 'text_wrap': True, 'valign': 'vcenter',
            'fg_color': '#D9E1F2', 'border': 1, 'align': 'center'
        })
        cell_format = workbook.add_format({'border': 1, 'align': 'center', 'valign': 'vcenter', 'num_format': '0.000'})
        bold_format = workbook.add_format({'bold': True, 'border': 1, 'align': 'center', 'valign': 'vcenter', 'fg_color': '#FCE4D6', 'num_format': '0.000'})
        text_format = workbook.add_format({'text_wrap': True, 'valign': 'top'})
        title_format = workbook.add_format({'bold': True, 'font_size': 11})
        
        # Sheet 1: 종합평가_결과
        summary_df.to_excel(writer, sheet_name='종합평가_결과', index=False)
        worksheet1 = writer.sheets['종합평가_결과']
        
        for col_num, value in enumerate(summary_df.columns.values):
            worksheet1.write(0, col_num, value, header_format)
            
        for row_idx in range(len(summary_df)):
            is_last = (row_idx == len(summary_df) - 1)
            fmt = bold_format if is_last else cell_format
            for col_idx in range(len(summary_df.columns)):
                val = summary_df.iloc[row_idx, col_idx]
                if pd.isna(val): val = ""
                # Remove markdown bold asterisks if present
                if isinstance(val, str): val = val.replace("**", "")
                worksheet1.write(row_idx + 1, col_idx, val, fmt)
                
        worksheet1.set_column(0, 0, 25)
        worksheet1.set_column(1, 2, 20)
        worksheet1.set_column(3, 3, 35)
        
        # 엑셀 하단 결과 해석 및 산출식 추가
        start_row = len(summary_df) + 3
        
        if final_score is not None and is_pass is not None:
            verdict_text = '사업 타당성을 확보했습니다' if is_pass else '사업 타당성이 미흡한 것으로 분석되었습니다'
            n_res = len(res_df)
            n_filtered = max(1, n_res - 2 if n_res >= 3 else n_res)
            interp_text = f"💡 조사 결과 해석: 본 예비타당성조사는 응답자 {n_res}명의 설문 결과를 바탕으로, 극단값(최고점 1명, 최저점 1명)을 제외한 {n_filtered}명의 점수를 종합하여 도출되었습니다. 최종 AHP 종합점수가 {final_score:.3f}으로 0.5를 {verdict_text}."
            worksheet1.merge_range(start_row, 0, start_row, 3, interp_text, text_format)
            worksheet1.set_row(start_row, 35)
            start_row += 2
            
        formula_title = "📚 AHP 산출식 및 변환 공식 안내"
        formula_text = (
            "1. 정량 데이터 쌍대비교 척도 변환\n"
            "   - 경제성 등 정량적 수치를 설문조사의 9점 척도와 동등하게 맞추기 위해 KDI 표준 공식을 사용합니다.\n"
            "   - B/C 비율 변환: 표준점수 = 8.592933 × ln(B/C비율) ± 1\n"
            "   - 지역낙후도(LIR) 변환: 표준점수 = 2.0 × LIR + 1.0\n\n"
            "2. 쌍대비교 척도의 가중치(AHP 점수) 변환\n"
            "   - 위에서 도출된 표준점수(Score)를 바탕으로 '시행(Go)' 대안의 가중치를 계산합니다.\n"
            "   - 시행(Go) 가중치 = Score / (Score + 1.0)\n\n"
            "3. 개인별 점수 합산 및 최종 종합점수 산출\n"
            "   - 각 평가자의 항목별 가중치와 항목별 점수를 곱해 개인별 최종 점수를 계산합니다.\n"
            "   - 이후 응답자가 3명 이상일 경우, 극단값(최고점 1명, 최저점 1명)을 제외하고 남은 인원들의 점수를 기하평균(Geometric Mean)하여 최종 AHP 평점을 산출합니다."
        )
        worksheet1.write(start_row, 0, formula_title, title_format)
        worksheet1.merge_range(start_row + 1, 0, start_row + 1, 3, formula_text, text_format)
        worksheet1.set_row(start_row + 1, 160)
        
        # Sheet 2: 로우데이터(Raw_Data)
        res_df.to_excel(writer, sheet_name='로우데이터(Raw_Data)', index=False)
        worksheet2 = writer.sheets['로우데이터(Raw_Data)']
        
        raw_cell_format = workbook.add_format({'num_format': '0.00000'})
        worksheet2.set_column(0, len(res_df.columns)-1, 15, raw_cell_format)
        
        for col_num, value in enumerate(res_df.columns.values):
            worksheet2.write(0, col_num, value, header_format)
        
    return output.getvalue()

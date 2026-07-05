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

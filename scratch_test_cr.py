import numpy as np

def get_cr_fix_suggestion(factors, answers):
    n = len(factors)
    if n <= 2:
        return None, None, None

    # 행렬 구축
    matrix = np.eye(n)
    for i in range(n):
        for j in range(i + 1, n):
            pair_key = f"{factors[i]}_{factors[j]}"
            raw_val = answers.get(pair_key, 1)
            
            if raw_val == 1:
                val = 1.0
            elif raw_val < 0:
                val = float(abs(raw_val))
            else:
                val = 1.0 / float(raw_val)
                
            matrix[i, j] = val
            matrix[j, i] = 1.0 / val

    # 고유값 계산 및 주요 고유벡터 (가중치) 도출
    eigenvalues, eigenvectors = np.linalg.eig(matrix)
    max_index = np.argmax(np.real(eigenvalues))
    w = np.real(eigenvectors[:, max_index])
    w = w / np.sum(w) # 정규화

    max_inconsistency = -1.0
    worst_pair = None
    worst_current_val = None
    suggested_val = None

    valid_raw_vals = list(range(-9, -1)) + [1] + list(range(2, 10))
    def raw_to_ratio(r):
        if r == 1: return 1.0
        if r < 0: return float(abs(r))
        return 1.0 / float(r)

    for i in range(n):
        for j in range(i + 1, n):
            expected_ratio = w[i] / w[j]
            actual_ratio = matrix[i, j]
            
            diff = max(actual_ratio / expected_ratio, expected_ratio / actual_ratio)
            
            if diff > max_inconsistency:
                max_inconsistency = diff
                worst_pair = (factors[i], factors[j])
                
                best_raw = 1
                min_dist = float('inf')
                for r in valid_raw_vals:
                    ratio = raw_to_ratio(r)
                    dist = abs(np.log(ratio) - np.log(expected_ratio))
                    if dist < min_dist:
                        min_dist = dist
                        best_raw = r
                
                suggested_val = best_raw
                worst_current_val = answers.get(f"{factors[i]}_{factors[j]}", 1)

    return worst_pair, worst_current_val, suggested_val

factors = ["A", "B", "C"]
# Intentionally inconsistent: A > B(5), B > C(5), but C > A(5 -> A < C = 5)
answers = {
    "A_B": -5,
    "A_C": 5,
    "B_C": -5
}
from survey_manager import calculate_matrix_cr
cr = calculate_matrix_cr(factors, answers)
print("CR:", cr)
print("Fix suggestion:", get_cr_fix_suggestion(factors, answers))

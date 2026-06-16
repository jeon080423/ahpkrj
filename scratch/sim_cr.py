import numpy as np
import pandas as pd
from scipy.stats import gmean

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

def test_simulation(noise_prob):
    n = 5
    crs = []
    saaty_vals = [1, 2, 3, 4, 5, 6, 7, 8, 9, -2, -3, -4, -5, -6, -7, -8, -9]
    
    def parse_val(v):
        if v == 1: return 1.0
        if v < 0: return float(abs(v))
        return 1.0 / v

    for _ in range(1000):
        # Generate true consistent matrix
        weights = np.random.uniform(0.1, 1.0, n)
        weights /= weights.sum()
        
        matrix = np.eye(n)
        for i in range(n):
            for j in range(i + 1, n):
                ratio = weights[i] / weights[j]
                # Map to Saaty scale
                if ratio >= 1:
                    saaty_v = int(round(ratio))
                    saaty_v = min(9, max(1, saaty_v))
                    # Map to Excel input convention: left important is negative, right important is positive
                    # Wait, in Excel input, if left is more important, it is negative.
                    # ratio >= 1 means left (i) is more important, so raw val in excel is negative: -saaty_v
                    excel_val = -saaty_v if saaty_v > 1 else 1
                else:
                    saaty_v = int(round(1.0 / ratio))
                    saaty_v = min(9, max(1, saaty_v))
                    # right (j) is more important, excel val is positive: saaty_v
                    excel_val = saaty_v if saaty_v > 1 else 1
                
                # Apply noise
                if np.random.rand() < noise_prob:
                    excel_val = np.random.choice(saaty_vals)
                
                # Convert back to matrix value
                parsed = parse_val(excel_val)
                matrix[i, j] = parsed
                matrix[j, i] = 1.0 / parsed
                
        crs.append(calculate_consistency(matrix))
    print(f"Noise Prob: {noise_prob:.2f} -> Mean CR: {np.mean(crs):.4f}")

for p in np.linspace(0.1, 0.9, 9):
    test_simulation(p)

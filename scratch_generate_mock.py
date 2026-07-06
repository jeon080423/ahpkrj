import sys
import os
import pandas as pd
import numpy as np

project_type = 'rnd'
policy_factors = ['정책일관성', '사업추진위험', '고용창출']
tech_factors = ['기술적합성', '기술성공가능성', '기존사업중복성', '파급효과']

columns = ['평가자_ID', '소속_및_성명', '전문_역할']
columns.extend(['1계층_경제성(%)', '1계층_기술성(%)', '1계층_정책성(%)'])
factors_map = {'기술성': tech_factors, '정책성': policy_factors}

for cat, factors in factors_map.items():
    if len(factors) > 1:
        for i in range(len(factors)):
            for j in range(i+1, len(factors)):
                columns.append(f"쌍대비교_[{cat}]_{factors[i]}_vs_{factors[j]}(실수형)")

for cat, factors in factors_map.items():
    for factor in factors:
        columns.append(f"대안평가_[{cat}]_{factor}(시행선호_1~9_역수)")

data = []
np.random.seed(42)
for i in range(1, 101):
    row = {
        '평가자_ID': f'EXPERT_{i:03d}',
        '소속_및_성명': f'전문가_{i}',
        '전문_역할': np.random.choice(['학계', '연구소', '정부', '산업계']),
    }
    
    econ = np.random.randint(40, 50)
    tech = np.random.randint(30, 40)
    policy = 100 - econ - tech
    row['1계층_경제성(%)'] = econ
    row['1계층_기술성(%)'] = tech
    row['1계층_정책성(%)'] = policy
    
    scales = [1, 3, 5, 7, 9, -3, -5, -7, -9]
    for cat, factors in factors_map.items():
        if len(factors) > 1:
            for i_idx in range(len(factors)):
                for j_idx in range(i_idx+1, len(factors)):
                    col = f"쌍대비교_[{cat}]_{factors[i_idx]}_vs_{factors[j_idx]}(실수형)"
                    row[col] = float(np.random.choice(scales))
                    
    for cat, factors in factors_map.items():
        for factor in factors:
            col = f"대안평가_[{cat}]_{factor}(시행선호_1~9_역수)"
            row[col] = float(np.random.choice(scales))
            
    data.append(row)

df = pd.DataFrame(data, columns=columns)
desktop = os.path.join(os.path.expanduser('~'), 'Desktop')
output_path = os.path.join(desktop, 'Yeta_MockData_RND_Complex_100.xlsx')
df.to_excel(output_path, index=False)
print(f'Successfully created: {output_path}')

import sys

def swap():
    filepath = r'n:\개인\1 AHP\0 AHPkr 깃허브\app.py'
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    idx_1 = -1
    idx_2 = -1
    idx_end = -1
    
    for i, line in enumerate(lines):
        if '1. Setup AHP Decision Model & Download Template' in line:
            idx_1 = i
        elif '2. Data Upload & Analysis' in line:
            idx_2 = i
        elif 'with main_tab2:' in line:
            idx_end = i
            
    if idx_1 == -1 or idx_2 == -1 or idx_end == -1:
        print("Could not find the indices:")
        print(f"idx_1={idx_1}, idx_2={idx_2}, idx_end={idx_end}")
        return
        
    chunk_prefix = lines[:idx_1]
    chunk_1 = lines[idx_1:idx_2]
    chunk_2 = lines[idx_2:idx_end]
    chunk_suffix = lines[idx_end:]
    
    # Replace titles in chunk_1
    for i in range(len(chunk_1)):
        if '1. Setup AHP Decision Model' in chunk_1[i]:
            chunk_1[i] = chunk_1[i].replace('1. AHP 분석 모델 설정', '2. AHP 분석 모델 설정')
            chunk_1[i] = chunk_1[i].replace('1. Setup AHP Decision Model', '2. Setup AHP Decision Model')
            
    # Replace titles in chunk_2
    for i in range(len(chunk_2)):
        if '2. Data Upload & Analysis' in chunk_2[i]:
            chunk_2[i] = chunk_2[i].replace('2. 데이터 업로드 및 분석', '1. 데이터 업로드 및 분석')
            chunk_2[i] = chunk_2[i].replace('2. Data Upload & Analysis', '1. Data Upload & Analysis')
            
    new_lines = chunk_prefix + chunk_2 + chunk_1 + chunk_suffix
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
        
    print("Successfully swapped sections.")

if __name__ == '__main__':
    swap()

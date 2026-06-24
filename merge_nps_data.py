import pandas as pd
import re
import os

# ==========================================
# 사용자 설정 영역
# ==========================================
# 1. 엑셀 원본 파일 경로 (DART 데이터가 추가된 파일)
EXCEL_PATH = r"N:\개인\M 연구1부 공유폴더\0■ 팀내 파일 공유\성남시\성남산업진흥원_데이터(NICE)_DART재무추가_업체명기준.xlsx"

# 2. 공공데이터포털에서 다운로드한 국민연금 CSV 파일 경로
CSV_PATH = r"N:\개인\M 연구1부 공유폴더\0■ 팀내 파일 공유\성남시\국민연금공단_국민연금 가입 사업장 내역_20260521.csv"

# 3. 최종 저장될 새 엑셀 파일 경로
OUTPUT_PATH = r"N:\개인\M 연구1부 공유폴더\0■ 팀내 파일 공유\성남시\성남산업진흥원_데이터(NICE)_DART_국민연금종업원_최종.xlsx"
# ==========================================

def clean_company_name(name):
    """
    기업명 매칭률을 높이기 위해 특수문자, (주), 주식회사, 공백 등을 제거합니다.
    """
    if not isinstance(name, str):
        return ""
    name = name.replace('(주)', '').replace('주식회사', '').replace('(유)', '').replace('유한회사', '')
    name = re.sub(r'[^가-힣A-Za-z0-9]', '', name)
    return name

def main():
    if not os.path.exists(EXCEL_PATH):
        print(f"엑셀 원본 파일을 찾을 수 없습니다: {EXCEL_PATH}")
        return
        
    if not os.path.exists(CSV_PATH):
        print(f"국민연금 CSV 파일을 찾을 수 없습니다: {CSV_PATH}")
        print("공공데이터포털에서 파일을 다운로드한 후, CSV_PATH 경로를 맞게 수정해 주세요.")
        return

    print("국민연금 CSV 데이터를 읽어오는 중입니다... (파일이 커서 약간의 시간이 걸릴 수 있습니다.)")
    try:
        # 공공데이터포털 CSV는 보통 cp949 인코딩을 사용합니다.
        nps_df = pd.read_csv(CSV_PATH, encoding='cp949', low_memory=False)
    except Exception as e:
        print(f"CSV 파일 읽기 에러: {e}")
        try:
            print("UTF-8 인코딩으로 재시도 중...")
            nps_df = pd.read_csv(CSV_PATH, encoding='utf-8', low_memory=False)
        except Exception as e:
            print(f"파일을 읽을 수 없습니다: {e}")
            return
            
    # 국민연금 데이터 컬럼 정리 (보통 '사업장명', '가입자수' 가 존재합니다)
    nps_name_col = next((col for col in nps_df.columns if '사업장명' in col.replace(' ', '')), None)
    nps_emp_col = next((col for col in nps_df.columns if '가입자수' in col.replace(' ', '')), None)
    
    if not nps_name_col or not nps_emp_col:
        print(f"CSV 파일에서 '사업장명' 또는 '가입자수' 열을 찾지 못했습니다. 현재 컬럼: {nps_df.columns.tolist()}")
        return
        
    # NPS 데이터 정제 (매칭용 키 생성 및 중복 제거)
    print("국민연금 데이터의 업체명을 정제하고 있습니다...")
    nps_df['clean_name'] = nps_df[nps_name_col].astype(str).apply(clean_company_name)
    # 중복되는 업체명이 있을 경우 가장 가입자 수가 많은(가장 큰 본점 등) 데이터를 우선 사용하도록 정렬 후 드롭
    nps_df = nps_df.sort_values(by=nps_emp_col, ascending=False).drop_duplicates(subset='clean_name')
    nps_dict = dict(zip(nps_df['clean_name'], nps_df[nps_emp_col]))

    print(f"\n엑셀 파일 읽는 중... : {EXCEL_PATH}")
    # 엑셀 헤더 찾기 (이전과 동일 로직)
    df_temp = pd.read_excel(EXCEL_PATH, nrows=15)
    header_idx = 0
    for i in range(len(df_temp)):
        row_values = [str(x).replace(' ', '') for x in df_temp.iloc[i].values]
        if any('업체명' in val for val in row_values):
            header_idx = i + 1
            break
            
    df = pd.read_excel(EXCEL_PATH, dtype=str, header=header_idx)
    excel_name_col = next((col for col in df.columns if '업체명' in str(col).replace(' ', '')), None)
    
    if not excel_name_col:
        print("엑셀 파일에서 '업체명' 컬럼을 찾지 못했습니다.")
        return

    print("종업원 수 매칭을 시작합니다...")
    emp_list = []
    match_count = 0
    
    for index, row in df.iterrows():
        raw_name = str(row[excel_name_col])
        clean_name = clean_company_name(raw_name)
        
        emp_count = nps_dict.get(clean_name, "국민연금 데이터 없음")
        
        if emp_count != "국민연금 데이터 없음":
            match_count += 1
            
        emp_list.append(emp_count)
        
    df['국민연금_종업원수'] = emp_list
    
    print(f"\n데이터 추출 완료. 총 {len(df)}건 중 {match_count}건 매칭 성공.")
    print(f"새 파일 저장 중... : {OUTPUT_PATH}")
    try:
        df.to_excel(OUTPUT_PATH, index=False)
        print("작업이 성공적으로 완료되었습니다!")
    except Exception as e:
        print(f"파일 저장 중 에러 발생: {e}")

if __name__ == "__main__":
    main()

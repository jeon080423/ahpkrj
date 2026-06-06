import gspread
import numpy as np
import json
import uuid
import streamlit as st
from google.oauth2.service_account import Credentials

def get_survey_gspread_client():
    """gspread 클라이언트를 반환합니다. st.secrets에 있는 credentials 사용."""
    scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    if "gcp_service_account" not in st.secrets:
        return None
    
    raw_auth = st.secrets["gcp_service_account"]
    auth_info = {}
    if isinstance(raw_auth, dict) or hasattr(raw_auth, "keys"):
        auth_info = dict(raw_auth)
    elif isinstance(raw_auth, str):
        import base64, json, re
        auth_str = raw_auth.strip().strip('"').strip("'")
        try:
            auth_info = json.loads(auth_str)
        except json.JSONDecodeError:
            try:
                clean_b64 = re.sub(r'\s+', '', auth_str)
                missing_padding = len(clean_b64) % 4
                if missing_padding:
                    clean_b64 += '=' * (4 - missing_padding)
                decoded_bytes = base64.b64decode(clean_b64)
                auth_info = json.loads(decoded_bytes.decode('utf-8'))
            except Exception:
                return None
    
    if auth_info and "private_key" in auth_info:
        auth_info["private_key"] = auth_info["private_key"].replace("\\n", "\n")
        
    try:
        creds = Credentials.from_service_account_info(auth_info, scopes=scope)
        return gspread.authorize(creds)
    except Exception:
        return None

def create_survey_sheet(title, admin_email, ahp_model, scale_type, demographics, definition_map, cr_limit, rewards_info):
    """
    고유한 Google Sheet를 동적으로 신규 생성하고 관리자 계정에 쓰기 권한을 부여합니다.
    """
    client = get_survey_gspread_client()
    if not client:
        raise Exception("Google Sheets API 인증 실패. secrets 설정을 확인해 주세요.")
    
    # 1. 스프레드시트 신규 생성
    spreadsheet = client.create(f"[AHP 설문] {title}")
    
    # 2. 관리자 이메일에 공유 권한(편집자) 부여
    if admin_email and "@" in admin_email:
        try:
            spreadsheet.share(admin_email, perm_type='user', role='writer', notify=False)
        except Exception as e:
            # 권한 부여 실패 시에도 계속 진행 (로그용 에러)
            st.warning(f"관리자 이메일 공유 설정 중 문제 발생: {e}")

    # 3. Sheet 1: Survey_Metadata 생성 및 설정
    meta_sheet = spreadsheet.sheet1
    meta_sheet.update_title("Survey_Metadata")
    
    metadata = [
        ["Field", "Value"],
        ["Title", title],
        ["AHP_Model_JSON", json.dumps(ahp_model, ensure_ascii=False)],
        ["Scale_Type", scale_type],
        ["Demographics", json.dumps(demographics, ensure_ascii=False)],
        ["Definitions", json.dumps(definition_map, ensure_ascii=False)],
        ["CR_Limit", str(cr_limit)],
        ["Rewards_Info", json.dumps(rewards_info, ensure_ascii=False)],
        ["Visit_Count", "0"],
        ["Abandoned_CR_Count", "0"]
    ]
    meta_sheet.update(range_name="A1:B11", values=metadata)
    
    # 4. Sheet 2: Raw_Data 생성
    raw_sheet = spreadsheet.add_worksheet(title="Raw_Data", rows="1000", cols="50")
    
    # 헤더 구성: ID, Type, (Demographic Fields...), (Pairwise Combination Fields...)
    headers = ["ID", "Type"]
    
    # 활성화된 인구통계 항목 추가
    demo_cols = []
    if demographics.get("name"): demo_cols.append("성명")
    if demographics.get("age"): demo_cols.append("연령")
    if demographics.get("gender"): demo_cols.append("성별")
    if demographics.get("experience"): demo_cols.append("경력년수")
    if demographics.get("affiliation"): demo_cols.append("소속")
    if demographics.get("email"): demo_cols.append("이메일")
    headers.extend(demo_cols)
    
    # 사전 순위 매기기 문항 정보 컬럼
    headers.append("사전순위지정")
    
    # AHP 쌍대비교 필드명 목록 구성 (엑셀 구조와 100% 매핑되도록 생성)
    # 대분류 조합
    main_criteria = ahp_model.get("main", [])
    main_pairs = []
    for i in range(len(main_criteria)):
        for j in range(i + 1, len(main_criteria)):
            main_pairs.append(f"{main_criteria[i]}_{main_criteria[j]}")
    headers.extend(main_pairs)
    
    # 중분류 조합
    sub_criteria_map = ahp_model.get("subs", {})
    for main_c in main_criteria:
        subs = sub_criteria_map.get(main_c, [])
        if len(subs) >= 2:
            sub_pairs = []
            for i in range(len(subs)):
                for j in range(i + 1, len(subs)):
                    sub_pairs.append(f"{subs[i]}_{subs[j]}")
            headers.extend(sub_pairs)
            
    # 답례품 수집용 번호/연락처
    if rewards_info.get("enabled"):
        headers.append("답례품_연락처")
        
    headers.append("제출시간")
    raw_sheet.append_row(headers)
    
    # 스프레드시트 ID 반환
    return spreadsheet.id

def load_survey_metadata(spreadsheet_id):
    """지정한 스프레드시트에서 설문지 구조 및 메타데이터를 로드합니다."""
    client = get_survey_gspread_client()
    if not client:
        return None
    
    try:
        spreadsheet = client.open_by_key(spreadsheet_id)
        meta_sheet = spreadsheet.worksheet("Survey_Metadata")
        records = meta_sheet.get_all_records()
        
        meta_dict = {}
        for row in records:
            meta_dict[row["Field"]] = row["Value"]
            
        # 디코딩
        meta_dict["AHP_Model_JSON"] = json.loads(meta_dict["AHP_Model_JSON"])
        meta_dict["Demographics"] = json.loads(meta_dict["Demographics"])
        meta_dict["Definitions"] = json.loads(meta_dict["Definitions"])
        meta_dict["Rewards_Info"] = json.loads(meta_dict["Rewards_Info"])
        meta_dict["CR_Limit"] = float(meta_dict["CR_Limit"]) if meta_dict["CR_Limit"] != "None" else None
        
        return meta_dict
    except Exception as e:
        st.error(f"설문 메타데이터 로드 실패: {e}")
        return None

def increment_survey_visit(spreadsheet_id):
    """설문 페이지 접속 시 방문 카운트를 1 증가시킵니다."""
    client = get_survey_gspread_client()
    if not client: return
    try:
        spreadsheet = client.open_by_key(spreadsheet_id)
        meta_sheet = spreadsheet.worksheet("Survey_Metadata")
        cell = meta_sheet.find("Visit_Count")
        if cell:
            current_val = int(meta_sheet.cell(cell.row, 2).value or 0)
            meta_sheet.update_cell(cell.row, 2, str(current_val + 1))
    except:
        pass

def increment_abandoned_cr(spreadsheet_id):
    """응답자가 제출했으나 CR 초과로 인해 중단(반려)된 횟수를 1 증가시킵니다."""
    client = get_survey_gspread_client()
    if not client: return
    try:
        spreadsheet = client.open_by_key(spreadsheet_id)
        meta_sheet = spreadsheet.worksheet("Survey_Metadata")
        cell = meta_sheet.find("Abandoned_CR_Count")
        if cell:
            current_val = int(meta_sheet.cell(cell.row, 2).value or 0)
            meta_sheet.update_cell(cell.row, 2, str(current_val + 1))
    except:
        pass

def get_survey_stats(spreadsheet_id):
    """설문의 응답 완료자 및 중단자 통계를 구글 시트에서 가져옵니다."""
    client = get_survey_gspread_client()
    if not client:
        return {"completed": 0, "abandoned_cr": 0, "visits": 0, "abandoned_bounce": 0}
        
    try:
        spreadsheet = client.open_by_key(spreadsheet_id)
        # 1. 완료자 수 (Raw_Data 행 개수 - 헤더행 1)
        raw_sheet = spreadsheet.worksheet("Raw_Data")
        completed_count = max(0, len(raw_sheet.get_all_values()) - 1)
        
        # 2. 메타데이터 조회 (방문 및 CR 실패 횟수)
        meta_sheet = spreadsheet.worksheet("Survey_Metadata")
        records = meta_sheet.get_all_records()
        meta_dict = {row["Field"]: row["Value"] for row in records}
        
        visits = int(meta_dict.get("Visit_Count", 0))
        abandoned_cr = int(meta_dict.get("Abandoned_CR_Count", 0))
        
        # 조기 이탈 중단자 = 방문 수 - 완료 수 (음수가 되지 않도록 방어 코드 추가)
        abandoned_bounce = max(0, visits - completed_count)
        
        return {
            "completed": completed_count,
            "abandoned_cr": abandoned_cr,
            "visits": visits,
            "abandoned_bounce": abandoned_bounce
        }
    except Exception as e:
        return {"completed": 0, "abandoned_cr": 0, "visits": 0, "abandoned_bounce": 0}

def save_response_to_sheet(spreadsheet_id, respondent_info, ahp_answers, demographics_settings, model, rewards_info):
    """응답 데이터를 구글 시트 Sheet 2에 추가합니다."""
    client = get_survey_gspread_client()
    if not client:
        return False
    
    try:
        spreadsheet = client.open_by_key(spreadsheet_id)
        raw_sheet = spreadsheet.worksheet("Raw_Data")
        
        # 행 생성
        row_data = [
            respondent_info.get("id", str(uuid.uuid4())[:8]),
            respondent_info.get("type", "일반")
        ]
        
        # 인구통계
        if demographics_settings.get("name"): row_data.append(respondent_info.get("name", ""))
        if demographics_settings.get("age"): row_data.append(respondent_info.get("age", ""))
        if demographics_settings.get("gender"): row_data.append(respondent_info.get("gender", ""))
        if demographics_settings.get("experience"): row_data.append(respondent_info.get("experience", ""))
        if demographics_settings.get("affiliation"): row_data.append(respondent_info.get("affiliation", ""))
        if demographics_settings.get("email"): row_data.append(respondent_info.get("email", ""))
        
        # 사전 순위
        row_data.append(respondent_info.get("pre_ranking", ""))
        
        # 쌍대비교 대분류 응답값 배치
        main_criteria = model.get("main", [])
        for i in range(len(main_criteria)):
            for j in range(i + 1, len(main_criteria)):
                pair_key = f"{main_criteria[i]}_{main_criteria[j]}"
                row_data.append(ahp_answers.get(pair_key, 1))
                
        # 쌍대비교 중분류 응답값 배치
        sub_criteria_map = model.get("subs", {})
        for main_c in main_criteria:
            subs = sub_criteria_map.get(main_c, [])
            if len(subs) >= 2:
                for i in range(len(subs)):
                    for j in range(i + 1, len(subs)):
                        pair_key = f"{subs[i]}_{subs[j]}"
                        row_data.append(ahp_answers.get(pair_key, 1))
                        
        # 답례품 연락처
        if rewards_info.get("enabled"):
            row_data.append(respondent_info.get("reward_contact", ""))
            
        import datetime
        kst_now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).strftime("%Y-%m-%d %H:%M:%S")
        row_data.append(kst_now)
        
        raw_sheet.append_row(row_data)
        return True
    except Exception as e:
        st.error(f"응답 데이터 저장 오류: {e}")
        return False

def generate_pairwise_combinations(model):
    """AHP 모델을 기반으로 렌더링할 쌍대비교 질문 쌍을 반환합니다."""
    combinations = []
    
    # 1. 대분류 요인 조합
    main_c = model.get("main", [])
    if len(main_c) >= 2:
        combinations.append({
            "type": "main",
            "parent": "Main",
            "factors": main_c,
            "pairs": [(main_c[i], main_c[j]) for i in range(len(main_c)) for j in range(i + 1, len(main_c))]
        })
        
    # 2. 중분류 요인 조합
    sub_map = model.get("subs", {})
    for parent, subs in sub_map.items():
        if len(subs) >= 2:
            combinations.append({
                "type": "sub",
                "parent": parent,
                "factors": subs,
                "pairs": [(subs[i], subs[j]) for i in range(len(subs)) for j in range(i + 1, len(subs))]
            })
            
    return combinations

def calculate_matrix_cr(factors, answers):
    """지정된 요인과 응답값을 바탕으로 일관성 비율(CR)을 계산합니다."""
    n = len(factors)
    if n <= 2:
        return 0.0  # 1x1 또는 2x2 행렬은 일관성 비율이 항상 0에 수렴
    
    # Saaty의 Random Index (RI) 테이블
    ri_table = {1: 0.0, 2: 0.0, 3: 0.58, 4: 0.90, 5: 1.12, 6: 1.24, 7: 1.32, 8: 1.41, 9: 1.45, 10: 1.49}
    ri = ri_table.get(n, 1.49)
    
    # 쌍대비교 행렬 구축
    matrix = np.eye(n)
    pair_idx = 0
    
    # 입력값을 파싱하여 상삼각 행렬에 값 배치 (대칭 원소에는 역수 배치)
    for i in range(n):
        for j in range(i + 1, n):
            pair_key = f"{factors[i]}_{factors[j]}"
            # 만약 answers에 없으면 기본값인 1.0(동등) 사용
            raw_val = answers.get(pair_key, 1)
            
            # 음수는 왼쪽 우선, 양수는 오른쪽 우선 스케일 변환
            if raw_val == 1:
                val = 1.0
            elif raw_val < 0:
                val = float(abs(raw_val))
            else:
                val = 1.0 / float(raw_val)
                
            matrix[i, j] = val
            matrix[j, i] = 1.0 / val
            
    # 고유값 계산
    eigenvalues = np.linalg.eigvals(matrix)
    max_eigenval = float(np.max(np.real(eigenvalues)))
    
    ci = (max_eigenval - n) / (n - 1) if n > 1 else 0.0
    cr = ci / ri if ri > 0 else 0.0
    return cr

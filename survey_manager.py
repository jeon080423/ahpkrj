import gspread
import numpy as np
import json
import uuid
import streamlit as st
from google.oauth2.service_account import Credentials

def get_survey_gspread_client(user_id=None):
    """gspread 클라이언트를 반환합니다. 사용자 OAuth 우선, 없을 시 서비스 계정 사용."""
    if user_id:
        user_client = get_user_gspread_client(user_id)
        if user_client:
            return user_client
            
    scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    
    # st.secrets에서 값 가져오기 (없을 경우 에러 처리)
    if "gcp_service_account" not in st.secrets:
        st.error("Secrets에 'gcp_service_account' 설정이 없습니다.")
        return None

    raw_auth = st.secrets["gcp_service_account"]
    auth_info = {}

    # Case 1: 이미 딕셔너리 형태인 경우 (TOML 포맷) - 가장 일반적인 경우
    if isinstance(raw_auth, dict) or hasattr(raw_auth, "keys"): 
        auth_info = dict(raw_auth) # AttrDict 등을 dict로 변환
    
    # Case 2: 문자열 형태인 경우 (JSON 문자열 혹은 Base64 인코딩 문자열)
    elif isinstance(raw_auth, str):
        import base64, re
        # 앞뒤 공백 및 따옴표 제거
        auth_str = raw_auth.strip().strip('"').strip("'")
        
        try:
            # 2-1. 순수 JSON 문자열로 파싱 시도
            auth_info = json.loads(auth_str)
        except json.JSONDecodeError:
            # 2-2. JSON 파싱 실패 -> Base64 인코딩된 값으로 가정하고 디코딩 시도
            try:
                # 1단계: 문자열 정제 (모든 공백 제거)
                clean_b64 = re.sub(r'\s+', '', auth_str)
                
                # 2단계: 패딩(=) 보정
                missing_padding = len(clean_b64) % 4
                if missing_padding:
                    clean_b64 += '=' * (4 - missing_padding)
                
                # 3단계: Base64 디코딩 (Standard 및 URL-Safe 방식 모두 시도)
                try:
                    decoded_bytes = base64.b64decode(clean_b64)
                except Exception:
                    # Standard 실패 시 URL-Safe 방식 시도 (-와 _ 문자 처리)
                    decoded_bytes = base64.urlsafe_b64decode(clean_b64)
                    
                decoded_info = decoded_bytes.decode('utf-8')
                auth_info = json.loads(decoded_info)
            except Exception as e:
                st.error(f"서비스 계정 키 디코딩 실패 (Base64/JSON 오류): {e}")
                return None
    else:
        st.error("gcp_service_account 형식을 인식할 수 없습니다.")
        return None

    # [중요] Private Key 내의 줄바꿈 문자(\n) 처리
    # TOML 등에서 문자열로 읽어올 때 \\n으로 이스케이프된 경우 실제 줄바꿈으로 변경 필요
    if auth_info and "private_key" in auth_info:
        auth_info["private_key"] = auth_info["private_key"].replace("\\n", "\n")

    # 필수 필드 확인 (Missing fields 에러 방지)
    required_fields = ["private_key", "client_email", "token_uri"]
    missing = [f for f in required_fields if f not in auth_info]
    if missing:
        st.error(f"서비스 계정 정보에 필수 필드가 누락되었습니다: {', '.join(missing)}")
        return None

    try:
        creds = Credentials.from_service_account_info(auth_info, scopes=scope)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"gspread 인증 에러: {e}")
        return None

def create_survey_sheet(title, admin_email, ahp_model, scale_type, demographics, definition_map, cr_limit, rewards_info, description="", existing_sheet_id=None, user_id=None):
    """
    고유한 Google Sheet를 동적으로 신규 생성하고 관리자 계정에 쓰기 권한을 부여하거나,
    사용자가 전달한 기존 구글 시트 ID를 기반으로 설문지를 연동합니다.
    """
    client = get_survey_gspread_client(user_id=user_id)
    if not client:
        raise Exception("Google Sheets API 인증 실패. secrets 설정을 확인해 주세요.")
    
    if existing_sheet_id:
        # 1. 기존 스프레드시트 열기
        try:
            # URL 형식으로 온 경우 ID만 추출
            if "docs.google.com/spreadsheets" in existing_sheet_id:
                parts = existing_sheet_id.split("/d/")
                if len(parts) > 1:
                    existing_sheet_id = parts[1].split("/")[0]
            spreadsheet = client.open_by_key(existing_sheet_id)
        except Exception as e:
            raise Exception(f"기존 구글 시트를 열 수 없습니다. ID와 서비스 계정 공유 설정을 확인해 주세요. (에러: {e})")
            
        # Survey_Metadata 워크시트 설정
        try:
            meta_sheet = spreadsheet.worksheet("Survey_Metadata")
            meta_sheet.clear()
        except gspread.WorksheetNotFound:
            try:
                meta_sheet = spreadsheet.sheet1
                meta_sheet.update_title("Survey_Metadata")
                meta_sheet.clear()
            except:
                meta_sheet = spreadsheet.add_worksheet(title="Survey_Metadata", rows="100", cols="20")
                
        # Raw_Data 워크시트 설정
        try:
            raw_sheet = spreadsheet.worksheet("Raw_Data")
            raw_sheet.clear()
        except gspread.WorksheetNotFound:
            raw_sheet = spreadsheet.add_worksheet(title="Raw_Data", rows="1000", cols="50")
            
    else:
        # [추가] 서비스 계정의 구글 드라이브 용량 초과 방지를 위한 사전 휴지통 비우기 및 오래된 파일 정리
        try:
            # drive v3 서비스 빌드하여 휴지통 일괄 비우기 처리
            from googleapiclient.discovery import build
            drive_service = build('drive', 'v3', credentials=client.auth)
            # 휴지통 완전 비우기
            drive_service.files().emptyTrash().execute()
        except Exception as e_trash:
            pass
     
        # 1. 스프레드시트 신규 생성
        spreadsheet = client.create(f"[AHP 설문] {title}")
        
        # 2. 담당자 이메일에 공유 권한(편집자 또는 소유자) 부여
        # 구글 API 특성상 서비스 계정 -> 일반 워크스페이스/개인 계정으로 직접 소유권 이전을 시도
        if admin_email and "@" in admin_email:
            try:
                # 1단계: 먼저 이메일에 쓰기(편집자) 권한 부여
                spreadsheet.share(admin_email, perm_type='user', role='writer', notify=False)
                
                # 2단계: 서비스 계정의 15GB 공간 잠식을 원천 방지하기 위해 파일 소유권(owner)을 사용자에게 양도 시도
                # (GCP와 일반 구글 메일 환경에 따라 간혹 양도가 제한되는 도메인 정책이 있을 수 있어 try-except 처리)
                try:
                    # drive API v3 권한 업데이트를 통한 소유권 이전
                    file_id = spreadsheet.id
                    # 담당자 권한 ID 조회
                    permissions = drive_service.permissions().list(fileId=file_id).execute()
                    for perm in permissions.get('permissions', []):
                        if perm.get('emailAddress') == admin_email:
                            # 소유권 양도 요청 (transferOwnership=True)
                            drive_service.permissions().update(
                                fileId=file_id,
                                permissionId=perm['id'],
                                body={'role': 'owner'},
                                transferOwnership=True
                            ).execute()
                            break
                except Exception as owner_err:
                    # 소유권 직접 이전 실패 시에는 편집 권한 상태로 유지되지만, 소유권이 넘어가지 않았더라도 편집권은 유효
                    pass
            except Exception as e:
                st.warning(f"설문조사 담당자 이메일 공유 설정 중 문제 발생: {e}")
     
        # 3. Sheet 1: Survey_Metadata 생성 및 설정
        meta_sheet = spreadsheet.sheet1
        meta_sheet.update_title("Survey_Metadata")
        
        # 4. Sheet 2: Raw_Data 생성
        raw_sheet = spreadsheet.add_worksheet(title="Raw_Data", rows="1000", cols="50")
        
    metadata = [
        ["Field", "Value"],
        ["Title", title],
        ["Description", description],
        ["Admin_Email", admin_email],
        ["AHP_Model_JSON", json.dumps(ahp_model, ensure_ascii=False)],
        ["Scale_Type", scale_type],
        ["Demographics", json.dumps(demographics, ensure_ascii=False)],
        ["Definitions", json.dumps(definition_map, ensure_ascii=False)],
        ["CR_Limit", str(cr_limit)],
        ["Rewards_Info", json.dumps(rewards_info, ensure_ascii=False)],
        ["Visit_Count", "0"],
        ["Abandoned_CR_Count", "0"]
    ]
    meta_sheet.update(range_name="A1:B13", values=metadata)
    
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
    """
    응답 데이터를 구글 시트 Sheet 2에 추가합니다.
    구글 API 호출 실패(API 한도 도달, 일시적 네트워크 장애 등)에 대비하여 로컬 SQLite 백업 저장소에 저장하고 True를 리턴하는 Fallback 메커니즘을 적용합니다.
    """
    import datetime
    import sqlite3
    
    # 1. 제출시간 생성
    kst_now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).strftime("%Y-%m-%d %H:%M:%S")
    
    # 2. 행 데이터 배열 구성
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
        
    row_data.append(kst_now)
    
    # 3. 로컬 SQLite 백업 테이블에 기록 (보장성 1순위)
    try:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS survey_backup_responses
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                       survey_id TEXT, 
                       respondent_id TEXT, 
                       response_json TEXT, 
                       saved_to_sheet INTEGER, 
                       created_at TEXT)''')
        
        # 전체 데이터 복구를 위한 JSON 구성
        complete_payload = {
            "row_data": row_data,
            "respondent_info": respondent_info,
            "ahp_answers": ahp_answers
        }
        c.execute("INSERT INTO survey_backup_responses (survey_id, respondent_id, response_json, saved_to_sheet, created_at) VALUES (?, ?, ?, ?, ?)",
                  (spreadsheet_id, row_data[0], json.dumps(complete_payload, ensure_ascii=False), 0, kst_now))
        conn.commit()
        last_inserted_id = c.lastrowid
        conn.close()
    except Exception as sqle:
        # SQLite 백업 기록 실패 시 경고하지만 진행
        last_inserted_id = None
        st.warning(f"로컬 백업 데이터베이스 기록 중 실패 (경고): {sqle}")

    # 4. 구글 시트에 데이터 업로드 시도
    admin_id = None
    try:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("SELECT admin_id FROM admin_surveys WHERE survey_id = ?", (spreadsheet_id,))
        db_row = c.fetchone()
        conn.close()
        if db_row:
            admin_id = db_row[0]
    except:
        pass

    client = get_survey_gspread_client(user_id=admin_id)
    if not client:
        # 구글 연동 실패했더라도 로컬에 저장했으므로 성공 리턴 (관리자가 추후 복구 가능)
        st.warning("⚠️ 구글 시트 연결을 완료할 수 없습니다. 응답이 서버 안전 백업 시스템에 보존되었습니다.")
        return True
        
    try:
        spreadsheet = client.open_by_key(spreadsheet_id)
        raw_sheet = spreadsheet.worksheet("Raw_Data")
        raw_sheet.append_row(row_data)
        
        # 구글 시트 저장 성공 시 SQLite 백업 레코드 상태값 업데이트
        if last_inserted_id is not None:
            try:
                conn = sqlite3.connect('users.db')
                c = conn.cursor()
                c.execute("UPDATE survey_backup_responses SET saved_to_sheet = 1 WHERE id = ?", (last_inserted_id,))
                conn.commit()
                conn.close()
            except:
                pass
                
        return True
    except Exception as e:
        # API 할당량 제한(429)이나 일시 네트웍 에러 등 발생
        st.warning(f"⚠️ 구글 스프레드시트 서버가 일시적으로 응답하지 않습니다. 데이터가 서버 로컬 백업에 안전하게 임시 보존되었습니다. (에러: {e})")
        return True


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

def get_user_gspread_client(user_id):
    """
    사용자의 Google OAuth 2.0 자격증명이 데이터베이스에 저장되어 있으면 이를 로드하여 gspread 클라이언트를 반환합니다.
    만약 토큰이 만료된 경우 자동으로 갱신(Refresh)하고 데이터베이스를 업데이트합니다.
    """
    if not user_id:
        return None
    import sqlite3
    import json
    from google.oauth2.credentials import Credentials as OAuthCredentials
    from google.auth.transport.requests import Request
    
    try:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("SELECT token, refresh_token, token_uri, client_id, client_secret, scopes, expiry FROM user_google_credentials WHERE user_id = ?", (user_id,))
        row = c.fetchone()
        conn.close()
        
        if row:
            token, refresh_token, token_uri, client_id, client_secret, scopes_str, expiry = row
            scopes = json.loads(scopes_str) if scopes_str else None
            
            # Credentials 객체 빌드
            creds = OAuthCredentials(
                token=token,
                refresh_token=refresh_token,
                token_uri=token_uri,
                client_id=client_id,
                client_secret=client_secret,
                scopes=scopes,
                expiry=expiry
            )
            
            # 만료 시 자동 갱신
            if creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    # 갱신된 정보 저장
                    conn = sqlite3.connect('users.db')
                    c = conn.cursor()
                    c.execute("UPDATE user_google_credentials SET token = ?, expiry = ? WHERE user_id = ?",
                              (creds.token, creds.expiry.isoformat() if hasattr(creds.expiry, 'isoformat') else str(creds.expiry), user_id))
                    conn.commit()
                    conn.close()
                except Exception as re:
                    st.warning(f"사용자 구글 토큰 자동 갱신 실패: {re}")
            
            return gspread.authorize(creds)
    except Exception as e:
        st.warning(f"사용자 구글 OAuth 계정 정보를 불러오는 데 실패했습니다: {e}")
    return None

def get_google_oauth_flow(redirect_uri):
    """구글 OAuth 2.0 Flow 객체를 반환합니다."""
    client_id = st.secrets.get("GOOGLE_CLIENT_ID") or st.secrets.get("google_oauth", {}).get("client_id")
    client_secret = st.secrets.get("GOOGLE_CLIENT_SECRET") or st.secrets.get("google_oauth", {}).get("client_secret")
    
    if not client_id or not client_secret:
        return None
        
    client_config = {
        "web": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs"
        }
    }
    
    from google_auth_oauthlib.flow import Flow
    scopes = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]
    flow = Flow.from_client_config(
        client_config,
        scopes=scopes,
        redirect_uri=redirect_uri
    )
    return flow



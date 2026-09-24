import gspread
import numpy as np
import pandas as pd
import json
import uuid
import streamlit as st
from google.oauth2.service_account import Credentials

def run_gspread_with_retry(func, *args, max_retries=5, initial_backoff=2, **kwargs):
    """
    구글 시트 API 호출 시 429(RESOURCE_EXHAUSTED) 등 일시적 오류 발생 시
    지수 백오프(Exponential Backoff) 및 지터(Jitter)를 적용하여 재시도하는 헬퍼 함수.
    """
    import time
    import random
    backoff = initial_backoff
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            err_msg = str(e)
            is_rate_limit = "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg or "RATE_LIMIT_EXCEEDED" in err_msg
            
            if is_rate_limit and attempt < max_retries - 1:
                sleep_time = backoff + random.uniform(0, 1)
                time.sleep(sleep_time)
                backoff *= 2
                continue
            else:
                raise e

@st.cache_resource
def get_survey_gspread_client(user_id=None):
    from google.oauth2.service_account import Credentials
    import gspread
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

    raw_auth = st.secrets.get("gcp_service_account", {})
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

def create_survey_sheet(title, admin_email, ahp_model, scale_type, demographics, definition_map, cr_limit, cr_guide_method, rewards_info, description="", existing_sheet_id=None, user_id=None):
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
            spreadsheet = run_gspread_with_retry(client.open_by_key, existing_sheet_id, max_retries=5, initial_backoff=3)
            # 링크가 있는 사용자에게 '조회자(reader)' 권한 부여 (권한 요청 팝업 방지 + 데이터 무단 훼손/수정 방지)
            try:
                run_gspread_with_retry(spreadsheet.share, None, perm_type='anyone', role='reader')
            except Exception:
                pass
        except Exception as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e) or "Quota exceeded" in str(e):
                raise Exception(f"구글 API 분당 요청 한도(429 Rate Limit)가 일시적으로 초과되었습니다. 약 1분 후 다시 시도해 주세요. ({e})")
            raise Exception(f"기존 구글 시트를 열 수 없습니다. ID와 서비스 계정 공유 설정을 확인해 주세요. (에러: {e})")
            
        # 기존 워크시트 목록을 1번의 API 호출로 가져와 딕셔너리로 캐싱 (중복 API 호출 90% 이상 제거)
        try:
            existing_worksheets = run_gspread_with_retry(spreadsheet.worksheets)
            ws_map = {ws.title: ws for ws in existing_worksheets}
        except Exception:
            ws_map = {}

        def get_or_create_ws(title, rows="1000", cols="50"):
            if title in ws_map:
                return ws_map[title], False
            try:
                new_ws = run_gspread_with_retry(spreadsheet.add_worksheet, title=title, rows=rows, cols=cols)
                ws_map[title] = new_ws
                return new_ws, True
            except Exception:
                try:
                    fallback_ws = run_gspread_with_retry(spreadsheet.worksheet, title)
                    ws_map[title] = fallback_ws
                    return fallback_ws, False
                except Exception:
                    raise

        # Survey_Metadata 워크시트 설정
        if "Survey_Metadata" in ws_map:
            meta_sheet = ws_map["Survey_Metadata"]
            run_gspread_with_retry(meta_sheet.clear)
        else:
            try:
                meta_sheet = run_gspread_with_retry(lambda: spreadsheet.sheet1)
                run_gspread_with_retry(meta_sheet.update_title, "Survey_Metadata")
                run_gspread_with_retry(meta_sheet.clear)
                ws_map["Survey_Metadata"] = meta_sheet
            except Exception:
                meta_sheet, _ = get_or_create_ws("Survey_Metadata", rows="100", cols="20")
                
        # Raw_Data 워크시트 설정
        raw_sheet, is_raw_new = get_or_create_ws("Raw_Data", rows="1000", cols="50")

        # Demographic_Data 워크시트 설정
        demo_sheet, is_demo_new = get_or_create_ws("Demographic_Data", rows="1000", cols="20")
            
    else:
        # [추가] 서비스 계정의 구글 드라이브 용량 초과 방지를 위한 사전 휴지통 비우기 및 오래된 파일 정리
        try:
            from googleapiclient.discovery import build
            drive_service = build('drive', 'v3', credentials=client.auth)
            drive_service.files().emptyTrash().execute()
        except Exception as e_trash:
            pass
     
        # 1. 스프레드시트 신규 생성 (파일명: [사용자ID_배포날짜] 설문제목)
        import datetime
        now_date = datetime.datetime.now().strftime("%Y-%m-%d")
        user_tag = user_id or admin_email or "User"
        sheet_title = f"[{user_tag}_{now_date}] {title}" if title else f"[{user_tag}_{now_date}] AHP 설문"
        spreadsheet = run_gspread_with_retry(client.create, sheet_title)
        
        # 2. 담당자 이메일에 편집자 권한 부여 및 링크 전체 공개 편집자 설정
        if admin_email and "@" in admin_email:
            try:
                spreadsheet.share(admin_email, perm_type='user', role='writer', notify=True)
            except Exception as e:
                st.warning(f"설문조사 담당자 이메일 공유 설정 중 문제 발생: {e}")
        try:
            spreadsheet.share(None, perm_type='anyone', role='reader')
        except Exception:
            pass
     
        # 3. Sheet 1: Survey_Metadata 생성 및 설정
        meta_sheet = spreadsheet.sheet1
        run_gspread_with_retry(meta_sheet.update_title, "Survey_Metadata")
        
        # 4. Sheet 2: Raw_Data 생성
        raw_sheet = run_gspread_with_retry(spreadsheet.add_worksheet, title="Raw_Data", rows="1000", cols="50")
        is_raw_new = True

        # 5. Sheet 3: Demographic_Data 생성
        demo_sheet = run_gspread_with_retry(spreadsheet.add_worksheet, title="Demographic_Data", rows="1000", cols="20")
        is_demo_new = True

        ws_map = {
            "Survey_Metadata": meta_sheet,
            "Raw_Data": raw_sheet,
            "Demographic_Data": demo_sheet
        }

        def get_or_create_ws(title, rows="1000", cols="50"):
            if title in ws_map:
                return ws_map[title], False
            try:
                new_ws = run_gspread_with_retry(spreadsheet.add_worksheet, title=title, rows=rows, cols=cols)
                ws_map[title] = new_ws
                return new_ws, True
            except Exception:
                try:
                    fallback_ws = run_gspread_with_retry(spreadsheet.worksheet, title)
                    ws_map[title] = fallback_ws
                    return fallback_ws, False
                except Exception:
                    raise
        
    metadata = [
        ["Field", "Value"],
        ["Title", title],
        ["Description", description],
        ["Admin_Email", admin_email],
        ["AHP_Model_JSON", json.dumps(ahp_model, ensure_ascii=False)],
        ["Tier_Level", "2"], # 2계층 식별 플래그
        ["Scale_Type", scale_type],
        ["Demographics", json.dumps(demographics, ensure_ascii=False)],
        ["Definitions", json.dumps(definition_map, ensure_ascii=False)],
        ["CR_Limit", str(cr_limit)],
        ["CR_Guide_Enabled", str(cr_guide_method == "realtime")],
        ["CR_Guide_Method", str(cr_guide_method)],
        ["Rewards_Info", json.dumps(rewards_info, ensure_ascii=False)],
        ["Visit_Count", "0"],
        ["Abandoned_CR_Count", "0"]
    ]
    meta_sheet.update(range_name="A1:B15", values=metadata)
    
    # 1. Raw_Data 헤더 구성: ID, Type, (Pairwise Combination Fields...), 제출시간

    type_headers = []
    if demographics and demographics.get("type_questions"):
        tq_list = demographics["type_questions"]
        for i, tq in enumerate(tq_list):
            q_name = tq.get("q", f"추가 문항 {i}") if i > 0 else tq.get("q", "그룹 분류")
            type_headers.append(q_name)
            if tq.get("q_type", "radio") == "radio" and any("기타" in str(opt) or "other" in str(opt).lower() for opt in tq.get("opts", [])):
                type_headers.append(f"{q_name}_기타")
    else:
        q_name = demographics.get("type_question", "그룹 분류") if demographics else "그룹 분류"
        type_headers.append(q_name)
        if demographics and any("기타" in str(opt) or "other" in str(opt).lower() for opt in demographics.get("type_options", [])):
            type_headers.append(f"{q_name}_기타")
    raw_headers = ["ID"] + type_headers

    
    # AHP 쌍대비교 필드명 목록 구성 (대분류 조합)
    main_criteria = ahp_model.get("main", [])
    main_pairs = []
    for i in range(len(main_criteria)):
        for j in range(i + 1, len(main_criteria)):
            main_pairs.append(f"{main_criteria[i]}_{main_criteria[j]}")
    raw_headers.extend(main_pairs)
    
    # 중분류 조합
    sub_criteria_map = ahp_model.get("subs", {})
    sub_sub_map = ahp_model.get("sub_subs", {})
    
    for main_c in main_criteria:
        subs = sub_criteria_map.get(main_c, [])
        if len(subs) >= 2:
            sub_pairs = []
            for i in range(len(subs)):
                for j in range(i + 1, len(subs)):
                    sub_pairs.append(f"{subs[i]}_{subs[j]}")
            raw_headers.extend(sub_pairs)
            
    # 소분류 조합 (3계층)
    for main_c, subs in sub_criteria_map.items():
        for sub_c in subs:
            sub_subs = sub_sub_map.get(sub_c, [])
            if len(sub_subs) >= 2:
                ss_pairs = []
                for i in range(len(sub_subs)):
                    for j in range(i + 1, len(sub_subs)):
                        ss_pairs.append(f"{sub_subs[i]}_{sub_subs[j]}")
                raw_headers.extend(ss_pairs)

    raw_headers.append("제출시간")
    
    # Raw_Data가 이미 존재하는지 (기존 연결 시) 확인 후 헤더 업데이트
    if is_raw_new:
        run_gspread_with_retry(raw_sheet.append_row, raw_headers)
    else:
        r1 = run_gspread_with_retry(raw_sheet.row_values, 1)
        if not r1:
            run_gspread_with_retry(raw_sheet.append_row, raw_headers)
        elif len(raw_headers) > len(r1):
            run_gspread_with_retry(raw_sheet.update, range_name="A1", values=[raw_headers])
        
    # Main_Criteria 및 하위 시트들 동적 생성 및 헤더 구성
    main_sheet, is_main_new = get_or_create_ws("Main_Criteria", rows="1000", cols="20")
    main_hdr = ["ID"] + type_headers + main_pairs + ["제출시간"]
    if is_main_new:
        run_gspread_with_retry(main_sheet.append_row, main_hdr)
    else:
        r1 = run_gspread_with_retry(main_sheet.row_values, 1)
        if not r1:
            run_gspread_with_retry(main_sheet.append_row, main_hdr)
        elif len(main_hdr) > len(r1):
            run_gspread_with_retry(main_sheet.update, range_name="A1", values=[main_hdr])
        
    # 중분류 시트 생성
    for main_c in main_criteria:
        subs = sub_criteria_map.get(main_c, [])
        if len(subs) >= 2:
            sub_pairs = []
            for i in range(len(subs)):
                for j in range(i + 1, len(subs)):
                    sub_pairs.append(f"{subs[i]}_{subs[j]}")
            safe_sheet_name = str(main_c)[:31]
            s_sheet, is_s_new = get_or_create_ws(safe_sheet_name, rows="1000", cols="20")
            if is_s_new:
                run_gspread_with_retry(s_sheet.append_row, ["ID"] + type_headers + sub_pairs + ["제출시간"])
            else:
                r1 = run_gspread_with_retry(s_sheet.row_values, 1)
                if not r1:
                    run_gspread_with_retry(s_sheet.append_row, ["ID"] + type_headers + sub_pairs + ["제출시간"])
                
    # 소분류 시트 생성
    for main_c, subs in sub_criteria_map.items():
        for sub_c in subs:
            sub_subs = sub_sub_map.get(sub_c, [])
            if len(sub_subs) >= 2:
                ss_pairs = []
                for i in range(len(sub_subs)):
                    for j in range(i + 1, len(sub_subs)):
                        ss_pairs.append(f"{sub_subs[i]}_{sub_subs[j]}")
                safe_sheet_name = str(sub_c)[:31]
                ss_sheet, is_ss_new = get_or_create_ws(safe_sheet_name, rows="1000", cols="20")
                if is_ss_new:
                    run_gspread_with_retry(ss_sheet.append_row, ["ID"] + type_headers + ss_pairs + ["제출시간"])
                else:
                    r1 = run_gspread_with_retry(ss_sheet.row_values, 1)
                    if not r1:
                        run_gspread_with_retry(ss_sheet.append_row, ["ID"] + type_headers + ss_pairs + ["제출시간"])


    # 2. Demographic_Data 헤더 구성: ID, Type, (Demographic Fields...), 사전순위지정, (답례품_연락처...), 제출시간
    demo_headers = ["ID"] + type_headers
    
    # 활성화된 인구통계 항목 추가
    demo_cols = []
    if demographics.get("name"): demo_cols.append("성명")
    if demographics.get("age"): demo_cols.append("연령")
    if demographics.get("gender"): demo_cols.append("성별")
    if demographics.get("experience"): demo_cols.append("경력년수")
    if demographics.get("affiliation"): demo_cols.append("소속")
    if demographics.get("email"): demo_cols.append("이메일")
    demo_headers.extend(demo_cols)
    
    # 사전 순위 매기기 문항 정보 컬럼
    demo_headers.append("사전순위지정")
    
    # 답례품 수집용 번호/연락처
    if rewards_info.get("enabled"):
        demo_headers.append("답례품_연락처")
        
    demo_headers.append("제출시간")
    if is_demo_new:
        run_gspread_with_retry(demo_sheet.append_row, demo_headers)
    else:
        r1 = run_gspread_with_retry(demo_sheet.row_values, 1)
        if not r1:
            run_gspread_with_retry(demo_sheet.append_row, demo_headers)
        elif len(demo_headers) > len(r1):
            run_gspread_with_retry(demo_sheet.update, range_name="A1", values=[demo_headers])
    
    # 로컬 SQLite 캐시에 백업 저장 및 Streamlit 캐시 비우기
    try:
        import sqlite3
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS survey_metadata_cache
                      (survey_id TEXT PRIMARY KEY, metadata_json TEXT, updated_at TEXT)''')
        meta_dict = {
            "Title": title,
            "Description": description,
            "Admin_Email": admin_email,
            "AHP_Model_JSON": ahp_model,
            "Scale_Type": scale_type,
            "Demographics": demographics,
            "Definitions": definition_map,
            "CR_Limit": float(cr_limit) if cr_limit is not None and str(cr_limit) != "None" else None,
            "CR_Guide_Enabled": bool(cr_guide_method == "realtime"),
            "CR_Guide_Method": str(cr_guide_method),
            "Rewards_Info": rewards_info
        }
        c.execute("INSERT OR REPLACE INTO survey_metadata_cache (survey_id, metadata_json, updated_at) VALUES (?, ?, datetime('now'))",
                  (spreadsheet.id, json.dumps(meta_dict, ensure_ascii=False)))
        conn.commit()
        conn.close()
    except Exception as db_err:
        pass

    try:
        st.cache_data.clear()
    except:
        pass
    
    # 스프레드시트 ID 반환
    return spreadsheet.id

@st.cache_data(ttl=60, show_spinner=False)
def _fetch_survey_metadata_from_sheets(spreadsheet_id):
    """구글 시트에서 실시간으로 설문 데이터를 가져와서 데코딩하고 로컬 DB 캐시를 갱신합니다."""
    import time
    client = get_survey_gspread_client()
    if not client:
        raise Exception("구글 시트 API 클라이언트를 초기화할 수 없습니다.")
        
    max_retries = 3
    records = None
    for attempt in range(max_retries):
        try:
            spreadsheet = client.open_by_key(spreadsheet_id)
            meta_sheet = spreadsheet.worksheet("Survey_Metadata")
            records = meta_sheet.get_all_records()
            break
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(1.5 ** attempt)  # 1s, 1.5s
                client = get_survey_gspread_client()
            else:
                raise e
    
    meta_dict = {}
    for row in records:
        meta_dict[row["Field"]] = row["Value"]
        
    # 디코딩
    meta_dict["AHP_Model_JSON"] = json.loads(meta_dict["AHP_Model_JSON"])
    meta_dict["Demographics"] = json.loads(meta_dict["Demographics"])
    meta_dict["Definitions"] = json.loads(meta_dict["Definitions"])
    meta_dict["Rewards_Info"] = json.loads(meta_dict["Rewards_Info"])
    meta_dict["CR_Limit"] = float(meta_dict.get("CR_Limit", "None")) if meta_dict.get("CR_Limit", "None") != "None" else None
    meta_dict["CR_Guide_Enabled"] = str(meta_dict.get("CR_Guide_Enabled", "False")).lower() == "true"
    meta_dict["CR_Guide_Method"] = str(meta_dict.get("CR_Guide_Method", "realtime" if meta_dict["CR_Guide_Enabled"] else "none"))
    
    # 로컬 SQLite 캐시에 백업/동기화 저장
    try:
        import sqlite3
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS survey_metadata_cache
                      (survey_id TEXT PRIMARY KEY, metadata_json TEXT, updated_at TEXT)''')
        c.execute("INSERT OR REPLACE INTO survey_metadata_cache (survey_id, metadata_json, updated_at) VALUES (?, ?, datetime('now'))",
                  (spreadsheet_id, json.dumps(meta_dict, ensure_ascii=False)))
        conn.commit()
        conn.close()
    except:
        pass
        
    return meta_dict

def load_survey_metadata(spreadsheet_id):
    """지정한 스프레드시트에서 설문지 구조 및 메타데이터를 로드합니다. 캐시 및 로컬 DB 백업 우선 적용."""
    try:
        # 1단계: Streamlit 캐시(Google Sheets API 실시간 호출) 시도
        return _fetch_survey_metadata_from_sheets(spreadsheet_id)
    except Exception as e:
        # 2단계: 실패 시 (429 Quota Exceeded 등) 로컬 SQLite 캐시 데이터 복구 시도
        import sqlite3
        try:
            conn = sqlite3.connect('users.db')
            c = conn.cursor()
            c.execute('''CREATE TABLE IF NOT EXISTS survey_metadata_cache
                          (survey_id TEXT PRIMARY KEY, metadata_json TEXT, updated_at TEXT)''')
            c.execute("SELECT metadata_json FROM survey_metadata_cache WHERE survey_id = ?", (spreadsheet_id,))
            row = c.fetchone()
            conn.close()
            if row:
                return json.loads(row[0])
        except Exception as db_e:
            pass
            
        # 3단계: 둘 다 실패 시 에러 표시
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
        spreadsheet = run_gspread_with_retry(client.open_by_key, spreadsheet_id)
        # 1. 완료자 수 (Raw_Data 행 개수 - 헤더행 1)
        raw_sheet = run_gspread_with_retry(spreadsheet.worksheet, "Raw_Data")
        completed_count = max(0, len(run_gspread_with_retry(raw_sheet.get_all_values)) - 1)
        
        # 2. 메타데이터 조회 (방문 및 CR 실패 횟수)
        meta_sheet = run_gspread_with_retry(spreadsheet.worksheet, "Survey_Metadata")
        records = run_gspread_with_retry(meta_sheet.get_all_records)
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

def clean_and_align_sheet_rows(rows, expected_headers=None, survey_meta=None, is_demo=False):
    """
    구글 시트의 Raw_Data 및 Demographic_Data에서
    1) 중간에 누적 삽입된 중복 헤더 행(ID로 시작하는 행)들을 제거
    2) survey_meta(설문 메타데이터)가 제공된 경우:
       - AHP 쌍대비교 열 위치와 응답자 인구통계/그룹분류(Type) 열 위치를 역방향/정방향 탐색하여
         과거 설문 버전(기타 별도열 미존재 등)과 신규 설문 버전 간의 컬럼 밀림을 완벽히 교정
       - 최신 문항명/표준 헤더 기준으로 모든 행을 재정렬
    3) survey_meta가 없는 경우:
       - 빈 셀이 아닌 유효 헤더명이 가장 많은 후보 행을 최적 헤더로 선택하고
         중복 ID 행을 제거한 후 열 정렬
    """
    if not rows:
        return pd.DataFrame(), [], False

    # 1. 빈 행 및 헤더 행 분리
    header_candidates = []
    data_rows = []

    for r in rows:
        if not r or all(str(cell).strip() == "" for cell in r):
            continue
        first_cell = str(r[0]).strip().upper() if len(r) > 0 else ""
        if first_cell == "ID":
            clean_hdr = [str(c).strip() for c in r]
            while clean_hdr and clean_hdr[-1] == "":
                clean_hdr.pop()
            if clean_hdr:
                header_candidates.append(clean_hdr)
        else:
            data_rows.append(r)

    # 2. survey_meta가 주어진 경우 구조 기반 정밀 복원
    if survey_meta:
        try:
            ahp_model = survey_meta.get("AHP_Model_JSON", {})
            tier_level = int(survey_meta.get("Tier_Level", 2))
            main_criteria = [str(c).strip() for c in ahp_model.get("main", [])]
            main_pairs = [f"{main_criteria[i]}_{main_criteria[j]}"
                          for i in range(len(main_criteria))
                          for j in range(i + 1, len(main_criteria))]
            sub_criteria_map = ahp_model.get("subs", {})
            all_sub_pairs = []
            for main_c in main_criteria:
                subs = [str(s).strip() for s in sub_criteria_map.get(main_c, [])]
                for i in range(len(subs)):
                    for j in range(i + 1, len(subs)):
                        all_sub_pairs.append(f"{subs[i]}_{subs[j]}")
            all_ss_pairs = []
            if tier_level == 3:
                sub_sub_map = ahp_model.get("sub_subs", {})
                for main_c in main_criteria:
                    subs = [str(s).strip() for s in sub_criteria_map.get(main_c, [])]
                    for sub_c in subs:
                        sub_subs = [str(ss).strip() for ss in sub_sub_map.get(sub_c, [])]
                        for i in range(len(sub_subs)):
                            for j in range(i + 1, len(sub_subs)):
                                all_ss_pairs.append(f"{sub_subs[i]}_{sub_subs[j]}")
            all_pairs = main_pairs + all_sub_pairs + all_ss_pairs
            total_pairs = len(all_pairs)

            demographics = survey_meta.get("Demographics", {})
            tq_list = demographics.get("type_questions", [])

            max_t_count = 0
            for r in data_rows:
                t_idx = -1
                for idx in range(len(r) - 1, 0, -1):
                    c = str(r[idx]).strip()
                    if "-" in c and ":" in c and len(c) >= 10:
                        t_idx = idx
                        break
                if not is_demo and total_pairs > 0:
                    comp_end = t_idx if t_idx != -1 else len(r)
                    comp_start = comp_end - total_pairs
                    t_count = max(0, comp_start - 1)
                else:
                    demo_field_count = (
                        (1 if demographics.get("name") else 0) +
                        (1 if demographics.get("age") else 0) +
                        (1 if demographics.get("gender") else 0) +
                        (1 if demographics.get("experience") else 0) +
                        (1 if demographics.get("affiliation") else 0) +
                        (1 if demographics.get("email") else 0) +
                        1 +
                        (1 if survey_meta.get("Rewards_Info", {}).get("enabled") else 0)
                    )
                    d_end = t_idx if t_idx != -1 else len(r)
                    t_count = max(0, (d_end - demo_field_count) - 1)
                if t_count > max_t_count:
                    max_t_count = t_count

            type_col_defs = []
            if tq_list:
                for i, tq in enumerate(tq_list):
                    q_name = tq.get("q", f"Type {i+1}").strip()
                    has_etc = tq.get("q_type", "radio") == "radio" and any("기타" in str(opt) or "other" in str(opt).lower() for opt in tq.get("opts", []))
                    type_col_defs.append((q_name, has_etc))
            else:
                q_name = demographics.get("type_question", "그룹 분류").strip() if demographics else "그룹 분류"
                has_etc = demographics and any("기타" in str(opt) or "other" in str(opt).lower() for opt in demographics.get("type_options", []))
                type_col_defs.append((q_name, has_etc))

            base_t_count = sum(2 if h else 1 for _, h in type_col_defs)
            if max_t_count > base_t_count and len(type_col_defs) > 0:
                type_col_defs[0] = (type_col_defs[0][0], True)

            expected_type_headers = []
            demo_type_headers = []
            for i, (q_name, has_etc) in enumerate(type_col_defs):
                expected_type_headers.append(f"Type {i+1}")
                demo_type_headers.append(q_name)
                if has_etc:
                    expected_type_headers.append(f"Type {i+1}_기타")
                    demo_type_headers.append(f"{q_name}_기타")

            if not is_demo:
                best_header = ["ID"] + expected_type_headers + all_pairs + ["제출시간"]
                aligned_rows = []
                for r in data_rows:
                    resp_id = str(r[0]).strip()
                    t_idx = -1
                    for idx in range(len(r) - 1, 0, -1):
                        c = str(r[idx]).strip()
                        if "-" in c and ":" in c and len(c) >= 10:
                            t_idx = idx
                            break
                    timestamp = str(r[t_idx]).strip() if t_idx != -1 else ""
                    comp_end = t_idx if t_idx != -1 else len(r)
                    comp_start = comp_end - total_pairs
                    comp_vals = [str(r[k]).strip() if k < len(r) else "" for k in range(comp_start, comp_end)]
                    t_vals = [str(r[k]).strip() for k in range(1, comp_start)]
                    
                    if len(t_vals) == len(expected_type_headers):
                        aligned_t = t_vals
                    elif len(t_vals) == len(expected_type_headers) - 1:
                        aligned_t = [t_vals[0], ""] + t_vals[1:]
                    elif len(t_vals) < len(expected_type_headers):
                        aligned_t = t_vals + [""] * (len(expected_type_headers) - len(t_vals))
                    else:
                        aligned_t = t_vals[:len(expected_type_headers)]
                    aligned_rows.append([resp_id] + aligned_t + comp_vals + [timestamp])

            else:
                demo_fields = []
                if demographics.get("name"): demo_fields.append("성명")
                if demographics.get("age"): demo_fields.append("연령")
                if demographics.get("gender"): demo_fields.append("성별")
                if demographics.get("experience"): demo_fields.append("경력년수")
                if demographics.get("affiliation"): demo_fields.append("소속")
                if demographics.get("email"): demo_fields.append("이메일")

                best_header = ["ID"] + demo_type_headers + demo_fields + ["사전순위지정"]
                if survey_meta.get("Rewards_Info", {}).get("enabled"):
                    best_header.append("답례품_연락처")
                best_header.append("제출시간")

                expected_demo_field_count = len(demo_fields) + 1
                if survey_meta.get("Rewards_Info", {}).get("enabled"):
                    expected_demo_field_count += 1

                aligned_rows = []
                for r in data_rows:
                    resp_id = str(r[0]).strip()
                    t_idx = -1
                    for idx in range(len(r) - 1, 0, -1):
                        c = str(r[idx]).strip()
                        if "-" in c and ":" in c and len(c) >= 10:
                            t_idx = idx
                            break
                    timestamp = str(r[t_idx]).strip() if t_idx != -1 else ""
                    d_end = t_idx if t_idx != -1 else len(r)
                    d_start = d_end - expected_demo_field_count
                    d_vals = [str(r[k]).strip() if k < len(r) else "" for k in range(d_start, d_end)]
                    t_vals = [str(r[k]).strip() for k in range(1, d_start)]
                    
                    if len(t_vals) == len(demo_type_headers):
                        aligned_t = t_vals
                    elif len(t_vals) == len(demo_type_headers) - 1:
                        aligned_t = [t_vals[0], ""] + t_vals[1:]
                    elif len(t_vals) < len(demo_type_headers):
                        aligned_t = t_vals + [""] * (len(demo_type_headers) - len(t_vals))
                    else:
                        aligned_t = t_vals[:len(demo_type_headers)]
                    aligned_rows.append([resp_id] + aligned_t + d_vals + [timestamp])

            df = pd.DataFrame(aligned_rows, columns=best_header)
            clean_matrix = [best_header] + aligned_rows
            needs_repair = (len(header_candidates) != 1) or (len(rows) > 0 and [str(c).strip() for c in rows[0] if str(c).strip() != ""] != best_header)
            return df, clean_matrix, needs_repair

        except Exception as meta_align_err:
            pass

    # 3. 휴리스틱 헤더 후보 풀에서 최적 헤더 선정 (fallback)
    candidates_pool = list(header_candidates)
    if expected_headers:
        candidates_pool.append([str(c).strip() for c in expected_headers if str(c).strip() != ""])

    if candidates_pool:
        best_header = max(candidates_pool, key=lambda h: len([c for c in h if str(c).strip() != ""]))
    elif data_rows:
        max_cols = max((len(r) for r in data_rows), default=1)
        best_header = [f"Col_{i+1}" for i in range(max_cols)]
    else:
        best_header = []

    unique_headers = []
    seen = {}
    for i, h in enumerate(best_header):
        h_str = str(h).strip() if str(h).strip() else f"Col_{i+1}"
        if h_str in seen:
            seen[h_str] += 1
            unique_headers.append(f"{h_str}_{seen[h_str]}")
        else:
            seen[h_str] = 0
            unique_headers.append(h_str)
    best_header = unique_headers

    target_len = len(best_header)
    aligned_rows = []
    for r in data_rows:
        r_list = [str(c).strip() for c in r]
        while len(r_list) > target_len and r_list[-1] == "":
            r_list.pop()
        if len(r_list) == target_len:
            aligned_rows.append(r_list)
        else:
            match_hdr = next((h for h in header_candidates if len([c for c in h if str(c).strip() != ""]) == len(r_list)), None)
            if match_hdr:
                col_map = dict(zip(match_hdr, r_list))
                aligned_rows.append([col_map.get(col, "") for col in best_header])
            elif len(r_list) < target_len:
                aligned_rows.append(r_list + [""] * (target_len - len(r_list)))
            else:
                aligned_rows.append(r_list[:target_len])

    df = pd.DataFrame(aligned_rows, columns=best_header) if best_header else pd.DataFrame(aligned_rows)
    needs_repair = (len(header_candidates) > 1) or (len(rows) > 0 and len(rows[0]) < target_len)
    clean_matrix = [best_header] + aligned_rows
    return df, clean_matrix, needs_repair

def save_response_to_sheet(spreadsheet_id, respondent_info, ahp_answers, demographics_settings, model, rewards_info):
    """
    응답 데이터를 구글 시트의 Raw_Data 시트(AHP 응답)와 Demographic_Data 시트(인구통계 및 사전순위)에 각각 분할하여 저장합니다.
    구글 API 호출 실패(API 한도 도달, 일시적 네트워크 장애 등)에 대비하여 로컬 SQLite 백업 저장소에 저장하고 True를 리턴하는 Fallback 메커니즘을 적용합니다.
    """
    import datetime
    import sqlite3
    
    # 1. 제출시간 생성
    kst_now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).strftime("%Y-%m-%d %H:%M:%S")
    
    resp_id = respondent_info.get("id", str(uuid.uuid4())[:8])

    resp_types = respondent_info.get("types", [])
    if not resp_types:
        resp_types = [respondent_info.get("type", "일반")]

    
    # 2. Raw_Data 행 데이터 구성 (ID, Type, AHP 쌍대비교 데이터, 제출시간)
    raw_row_data = [resp_id] + resp_types
    
    # 쌍대비교 대분류 응답값 배치
    main_criteria = model.get("main", [])
    main_row_data = [resp_id] + resp_types
    for i in range(len(main_criteria)):
        for j in range(i + 1, len(main_criteria)):
            pair_key = f"{main_criteria[i]}_{main_criteria[j]}"
            raw_row_data.append(ahp_answers.get(pair_key, 1))
            main_row_data.append(ahp_answers.get(pair_key, 1))
    main_row_data.append(kst_now)
            
    # 쌍대비교 중분류/소분류 응답값 배치 및 분할 데이터 구성
    sub_criteria_map = model.get("subs", {})
    sub_sub_map = model.get("sub_subs", {})
    sub_row_data_map = {}
    
    for main_c in main_criteria:
        subs = sub_criteria_map.get(main_c, [])
        if len(subs) >= 2:
            s_row = [resp_id] + resp_types
            for i in range(len(subs)):
                for j in range(i + 1, len(subs)):
                    pair_key = f"{subs[i]}_{subs[j]}"
                    raw_row_data.append(ahp_answers.get(pair_key, 1))
                    s_row.append(ahp_answers.get(pair_key, 1))
            s_row.append(kst_now)
            sub_row_data_map[str(main_c)[:31]] = s_row
            
    for main_c, subs in sub_criteria_map.items():
        for sub_c in subs:
            sub_subs = sub_sub_map.get(sub_c, [])
            if len(sub_subs) >= 2:
                ss_row = [resp_id] + resp_types
                for i in range(len(sub_subs)):
                    for j in range(i + 1, len(sub_subs)):
                        pair_key = f"{sub_subs[i]}_{sub_subs[j]}"
                        raw_row_data.append(ahp_answers.get(pair_key, 1))
                        ss_row.append(ahp_answers.get(pair_key, 1))
                ss_row.append(kst_now)
                sub_row_data_map[str(sub_c)[:31]] = ss_row
                
    raw_row_data.append(kst_now)
    
    # 3. Demographic_Data 행 데이터 구성 (ID, Type, 인구통계 필드, 사전순위, 답례품 연락처, 제출시간)
    demo_row_data = [resp_id] + resp_types
    
    # 인구통계
    if demographics_settings.get("name"): demo_row_data.append(respondent_info.get("name", ""))
    if demographics_settings.get("age"): demo_row_data.append(respondent_info.get("age", ""))
    if demographics_settings.get("gender"): demo_row_data.append(respondent_info.get("gender", ""))
    if demographics_settings.get("experience"): demo_row_data.append(respondent_info.get("experience", ""))
    if demographics_settings.get("affiliation"): demo_row_data.append(respondent_info.get("affiliation", ""))
    if demographics_settings.get("email"): demo_row_data.append(respondent_info.get("email", ""))
    
    # 사전 순위
    demo_row_data.append(respondent_info.get("pre_ranking", ""))
    
    # 답례품 연락처
    if rewards_info.get("enabled"):
        demo_row_data.append(respondent_info.get("reward_contact", ""))
        
    demo_row_data.append(kst_now)
    
    # 4. 로컬 SQLite 백업 테이블에 기록 (보장성 1순위)
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
            "raw_row_data": raw_row_data,
            "demo_row_data": demo_row_data,
            "respondent_info": respondent_info,
            "ahp_answers": ahp_answers
        }
        c.execute("INSERT INTO survey_backup_responses (survey_id, respondent_id, response_json, saved_to_sheet, created_at) VALUES (?, ?, ?, ?, ?)",
                  (spreadsheet_id, resp_id, json.dumps(complete_payload, ensure_ascii=False), 0, kst_now))
        conn.commit()
        last_inserted_id = c.lastrowid
        conn.close()
    except Exception as sqle:
        # SQLite 백업 기록 실패 시 경고하지만 진행
        last_inserted_id = None
        st.warning(f"로컬 백업 데이터베이스 기록 중 실패 (경고): {sqle}")

    # 5. 구글 시트에 데이터 업로드 시도
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
        
        # 1) Raw_Data에 추가
        try:
            raw_sheet = spreadsheet.worksheet("Raw_Data")
            r_hdr = run_gspread_with_retry(raw_sheet.row_values, 1)
            if r_hdr and len(r_hdr) > len(raw_row_data):
                diff = len(r_hdr) - len(raw_row_data)
                raw_row_data = raw_row_data[:2] + [""] * diff + raw_row_data[2:]
            raw_sheet.append_row(raw_row_data)
        except Exception as e:
            st.warning(f"Raw_Data 시트 기록 실패: {e}")
            
        # [신규] Main_Criteria 및 하위 시트에 분할 추가
        try:
            main_sheet = spreadsheet.worksheet("Main_Criteria")
            main_sheet.append_row(main_row_data)
        except gspread.WorksheetNotFound:
            pass # 이전 설문지는 시트가 없을 수 있음
            
        for s_name, s_row in sub_row_data_map.items():
            try:
                s_sheet = spreadsheet.worksheet(s_name)
                s_sheet.append_row(s_row)
            except gspread.WorksheetNotFound:
                pass
        
        # 2) Demographic_Data에 추가
        try:
            demo_sheet = spreadsheet.worksheet("Demographic_Data")
            d_hdr = run_gspread_with_retry(demo_sheet.row_values, 1)
            if d_hdr and len(d_hdr) > len(demo_row_data):
                diff = len(d_hdr) - len(demo_row_data)
                demo_row_data = demo_row_data[:2] + [""] * diff + demo_row_data[2:]
            demo_sheet.append_row(demo_row_data)
        except Exception:
            # 혹시 모를 오류 방지 (Demographic_Data 시트가 없으면 재생성)
            try:
                demo_sheet = spreadsheet.add_worksheet(title="Demographic_Data", rows="1000", cols="20")
                type_headers = []
                if demographics_settings and demographics_settings.get("type_questions"):
                    tq_list = demographics_settings["type_questions"]
                    for i, tq in enumerate(tq_list):
                        q_name = tq.get("q", f"추가 문항 {i}") if i > 0 else tq.get("q", "그룹 분류")
                        type_headers.append(q_name)
                        if tq.get("q_type", "radio") == "radio" and any("기타" in str(opt) or "other" in str(opt).lower() for opt in tq.get("opts", [])):
                            type_headers.append(f"{q_name}_기타")
                else:
                    q_name = demographics_settings.get("type_question", "그룹 분류") if demographics_settings else "그룹 분류"
                    type_headers.append(q_name)
                    if demographics_settings and any("기타" in str(opt) or "other" in str(opt).lower() for opt in demographics_settings.get("type_options", [])):
                        type_headers.append(f"{q_name}_기타")
                demo_headers = ["ID"] + type_headers
                demo_cols = []
                if demographics_settings.get("name"): demo_cols.append("성명")
                if demographics_settings.get("age"): demo_cols.append("연령")
                if demographics_settings.get("gender"): demo_cols.append("성별")
                if demographics_settings.get("experience"): demo_cols.append("경력년수")
                if demographics_settings.get("affiliation"): demo_cols.append("소속")
                if demographics_settings.get("email"): demo_cols.append("이메일")
                demo_headers.extend(demo_cols)
                demo_headers.append("사전순위지정")
                if rewards_info.get("enabled"):
                    demo_headers.append("답례품_연락처")
                demo_headers.append("제출시간")
                demo_sheet.append_row(demo_headers)
                demo_sheet.append_row(demo_row_data)
            except:
                pass
        
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

def get_cr_fix_suggestion(factors, answers, cr_limit=0.1):
    """
    CR이 한계치를 초과할 때 수정 시 CR을 가장 낮추는 쌍(pair)과 추천 값을 반환합니다.
    - 1순위: 해당 쌍 하나를 수정해서 CR <= cr_limit를 달성 가능한 쌍+값
    - 2순위: CR을 가장 크게 낮추는 쌍+값 (단 한 쌍 수정으로 limit 달성 불가 시)
    반환값: (쌍 튜플 (factor_i, factor_j), 현재 값, 추천 값)
    """
    n = len(factors)
    if n <= 2:
        return None, None, None

    import numpy as np

    # RI 테이블
    ri_table = {1: 0.0, 2: 0.0, 3: 0.58, 4: 0.90, 5: 1.12, 6: 1.24, 7: 1.32, 8: 1.41, 9: 1.45, 10: 1.49}
    ri = ri_table.get(n, 1.49)

    def build_matrix(ans):
        m = np.eye(n)
        for ii in range(n):
            for jj in range(ii + 1, n):
                pk = f"{factors[ii]}_{factors[jj]}"
                r = ans.get(pk, 1)
                if r == 1:
                    v = 1.0
                elif r < 0:
                    v = float(abs(r))
                else:
                    v = 1.0 / float(r)
                m[ii, jj] = v
                m[jj, ii] = 1.0 / v
        return m

    def calc_cr_from_matrix(m):
        ev = np.linalg.eigvals(m)
        lmax = float(np.max(np.real(ev)))
        ci = (lmax - n) / (n - 1) if n > 1 else 0.0
        return ci / ri if ri > 0 else 0.0

    valid_raw_vals = list(range(-9, -1)) + [1] + list(range(2, 10))

    cur_cr = calc_cr_from_matrix(build_matrix(answers))

    # 각 쌍 × 각 후보 값에 대해 실제 CR 시뮬레이션
    best_pair = None       # CR <= limit 달성 가능한 최선 쌍
    best_val = None
    best_cr_result = float('inf')
    fallback_pair = None   # limit 달성 불가 시 CR 최소화 쌍
    fallback_val = None
    fallback_cr = cur_cr   # 현재보다 나아야 함

    for i in range(n):
        for j in range(i + 1, n):
            pair_key = f"{factors[i]}_{factors[j]}"
            cur_raw = answers.get(pair_key, 1)

            pair_best_val = None
            pair_best_cr = float('inf')
            pair_best_cr_nolimit = float('inf')  # limit 미달 시 fallback용
            pair_best_val_nolimit = None

            for r in valid_raw_vals:
                if r == cur_raw:
                    continue  # 현재 값은 건너뜀
                test_ans = answers.copy()
                test_ans[pair_key] = r
                test_cr = calc_cr_from_matrix(build_matrix(test_ans))

                if test_cr <= cr_limit:
                    if test_cr < pair_best_cr:
                        pair_best_cr = test_cr
                        pair_best_val = r
                else:
                    if test_cr < pair_best_cr_nolimit:
                        pair_best_cr_nolimit = test_cr
                        pair_best_val_nolimit = r

            if pair_best_val is not None:
                # 이 쌍으로 limit 달성 가능
                if pair_best_cr < best_cr_result:
                    best_cr_result = pair_best_cr
                    best_pair = (factors[i], factors[j])
                    best_val = pair_best_val
            elif pair_best_val_nolimit is not None:
                # limit 달성 불가 - fallback: 가장 CR을 낮추는 쌍
                if pair_best_cr_nolimit < fallback_cr:
                    fallback_cr = pair_best_cr_nolimit
                    fallback_pair = (factors[i], factors[j])
                    fallback_val = pair_best_val_nolimit

    # 결과: 1순위(limit 달성) > 2순위(fallback)
    if best_pair is not None:
        target_pair, target_val = best_pair, best_val
    elif fallback_pair is not None:
        target_pair, target_val = fallback_pair, fallback_val
    else:
        return None, None, None

    cur_raw = answers.get(f"{target_pair[0]}_{target_pair[1]}", 1)
    return target_pair, cur_raw, target_val

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
            # 만약 answers에 없거나 값이 None이면 기본값인 1.0(동등) 사용
            raw_val = answers.get(pair_key)
            if raw_val is None:
                raw_val = 1
            
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



def save_admin_survey_to_gsheet(survey_id, title, admin_id):
    import datetime
    import gspread
    client = get_survey_gspread_client()
    if not client: return False
    try:
        master_sheet = client.open_by_key('1xLvrH6LN8Vw3dVzoguf6TkgRrsJvEpMl2Z8s8HAvrVA')
        try:
            ws = master_sheet.worksheet('Admin_Surveys')
        except gspread.exceptions.WorksheetNotFound:
            ws = master_sheet.add_worksheet(title='Admin_Surveys', rows=1000, cols=5)
            ws.append_row(['survey_id', 'title', 'admin_id', 'created_at'])
            
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ws.append_row([survey_id, title, admin_id, now_str])
        return True
    except Exception as e:
        print("save_admin_survey_to_gsheet error:", e)
        return False

def delete_admin_survey(survey_id, admin_id):
    import sqlite3
    import gspread
    client = get_survey_gspread_client()
    if not client: return False
    
    # 1. Clear data in the user's survey sheet
    try:
        spreadsheet = run_gspread_with_retry(client.open_by_key, survey_id)
        for sheet_name in ["Raw_Data", "Demographic_Data", "Survey_Metadata", "AHP_Model", "Pairwise_Data"]:
            try:
                ws = run_gspread_with_retry(spreadsheet.worksheet, sheet_name)
                run_gspread_with_retry(ws.clear)
            except gspread.exceptions.WorksheetNotFound:
                pass
    except Exception as e:
        print(f"Failed to clear survey sheet {survey_id}:", e)
        
    # 2. Remove from Admin_Surveys and Short_Urls Master Sheets
    try:
        master_sheet = run_gspread_with_retry(client.open_by_key, '1xLvrH6LN8Vw3dVzoguf6TkgRrsJvEpMl2Z8s8HAvrVA')
        
        # 2-1. Admin_Surveys 시트에서 삭제
        try:
            ws = run_gspread_with_retry(master_sheet.worksheet, 'Admin_Surveys')
            all_records = run_gspread_with_retry(ws.get_all_records)
            rows_to_delete = []
            for i, r in enumerate(all_records):
                if str(r.get('survey_id')) == str(survey_id) or str(r.get('admin_id')) == str(admin_id):
                    rows_to_delete.append(i + 2)
            for r_idx in sorted(rows_to_delete, reverse=True):
                run_gspread_with_retry(ws.delete_rows, r_idx)
        except Exception:
            pass
            
        # 2-2. Short_Urls 시트에서 삭제 (이전 누락 부분 수정: 로컬 DB에 자동 복구 방지)
        try:
            ws_short = run_gspread_with_retry(master_sheet.worksheet, 'Short_Urls')
            all_short_records = run_gspread_with_retry(ws_short.get_all_records)
            rows_to_delete_short = []
            for i, r in enumerate(all_short_records):
                if str(r.get('survey_id')) == str(survey_id) or str(r.get('admin_id')) == str(admin_id):
                    rows_to_delete_short.append(i + 2)
            for r_idx in sorted(rows_to_delete_short, reverse=True):
                run_gspread_with_retry(ws_short.delete_rows, r_idx)
        except Exception:
            pass
            
    except Exception as e:
        print("Failed to remove from Master GSheet:", e)

    # 3. Remove from Local DB
    try:
        conn = sqlite3.connect('users.db')
        cur = conn.cursor()
        cur.execute("DELETE FROM admin_surveys WHERE admin_id = ?", (admin_id,))
        conn.commit()
        conn.close()
    except Exception as e:
        print("Failed to remove from local SQLite:", e)
        
    return True

@st.cache_data(ttl=60, show_spinner=False)
def get_admin_surveys_from_gsheet(admin_id):
    import gspread
    client = get_survey_gspread_client()
    if not client: return []
    try:
        master_sheet = run_gspread_with_retry(client.open_by_key, '1xLvrH6LN8Vw3dVzoguf6TkgRrsJvEpMl2Z8s8HAvrVA')
        try:
            ws = run_gspread_with_retry(master_sheet.worksheet, 'Admin_Surveys')
        except gspread.exceptions.WorksheetNotFound:
            return []
            
        try:
            all_records = run_gspread_with_retry(ws.get_all_records)
        except Exception:
            all_records = []
        surveys = []
        for r in all_records:
            r_admin = str(r.get('admin_id') or '').strip().lower()
            target_admin = str(admin_id or '').strip().lower()
            if r_admin and r_admin == target_admin:
                surveys.append((str(r.get('survey_id')), str(r.get('title')), str(r.get('created_at'))))
        surveys.sort(key=lambda x: x[2], reverse=True)
        return surveys
    except Exception as e:
        print("get_admin_surveys_from_gsheet error:", e)
        return []


# --- User Activity Logging ---
def _bg_log_worker(user_id, is_guest, region, actions_str, action_log_row_idx, target_sheet_id):
    import datetime
    import gspread
    try:
        from survey_manager import get_survey_gspread_client, run_gspread_with_retry
        client = get_survey_gspread_client()
        if not client:
            return

        master_sheet = run_gspread_with_retry(client.open_by_key, target_sheet_id)
        sheet_name = 'Guest_Activity_Logs' if is_guest else 'User_Activity_Logs'

        try:
            ws = run_gspread_with_retry(master_sheet.worksheet, sheet_name)
        except gspread.exceptions.WorksheetNotFound:
            ws = run_gspread_with_retry(master_sheet.add_worksheet, title=sheet_name, rows=1000, cols=10)
            run_gspread_with_retry(ws.append_row, ["Timestamp", "User ID", "Region", "Action Sequence"])

        if action_log_row_idx is None:
            now_str = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).strftime("%Y-%m-%d %H:%M:%S")
            run_gspread_with_retry(ws.append_row, [now_str, user_id, region, actions_str])
        else:
            run_gspread_with_retry(ws.update_cell, action_log_row_idx, 4, actions_str)
    except Exception as e:
        with open('log_worker_err.txt', 'a', encoding='utf-8') as f:
            f.write(f"Error: {str(e)}\n")

def log_user_action(user_id, action_name):
    import streamlit as st
    import threading

    is_guest = not user_id or str(user_id).lower() == "guest"
    if is_guest and not user_id:
        user_id = "Guest"

    if 'action_log_history' not in st.session_state:
        st.session_state.action_log_history = []
    if 'action_log_counts' not in st.session_state:
        st.session_state.action_log_counts = {}
    if 'action_log_row_idx' not in st.session_state:
        st.session_state.action_log_row_idx = None

    counts = st.session_state.action_log_counts
    counts[action_name] = counts.get(action_name, 0) + 1

    if counts[action_name] > 1:
        display_name = f"{action_name}({counts[action_name]})"
    else:
        display_name = action_name

    st.session_state.action_log_history.append(display_name)
    actions_str = ", ".join(st.session_state.action_log_history)
    region = st.session_state.get('user_region', '')
    
    try:
        target_sheet_id = st.secrets.get("LOG_SPREADSHEET_ID", '1jrnOMiqNwfoqMsK9mB4NxhUSI32UUmelfBDtWz9QFVU')
        if target_sheet_id.startswith("http"):
            parts = target_sheet_id.split("/d/")
            if len(parts) > 1:
                target_sheet_id = parts[1].split("/")[0]
    except:
        target_sheet_id = '1jrnOMiqNwfoqMsK9mB4NxhUSI32UUmelfBDtWz9QFVU'

    t = threading.Thread(target=_bg_log_worker, args=(user_id, is_guest, region, actions_str, None, target_sheet_id))
    try:
        from streamlit.runtime.scriptrunner import add_script_run_ctx
        add_script_run_ctx(t)
    except Exception as e:
        pass
    t.start()


def reset_survey_responses(spreadsheet_id, create_backup=True, user_id=None):
    """
    구글 스프레드시트의 설문 구조 및 메타데이터(Survey_Metadata)는 완벽히 보존한 채,
    Raw_Data 및 Demographic_Data 시트의 응답 데이터(2행부터 마지막 행까지)를 안전하게 초기화합니다.
    
    안전장치:
    1. create_backup=True 시 구글 시트 내에 'Raw_Backup_YYYYMMDD_HHMMSS' 복제 시트 자동 생성
    2. 로컬 SQLite DB(surveys.db의 survey_responses_backup 테이블)에 원본 데이터 영구 백업
    3. 1행 헤더 보존 및 delete_rows 실행 후 기본 행(최소 50행) 자동 확보
    """
    import datetime
    import sqlite3
    import json
    
    client = get_survey_gspread_client(user_id=user_id)
    if not client:
        return {"success": False, "error": "Google Sheets API 인증 실패"}
        
    try:
        if "docs.google.com/spreadsheets" in spreadsheet_id:
            parts = spreadsheet_id.split("/d/")
            if len(parts) > 1:
                spreadsheet_id = parts[1].split("/")[0]
                
        spreadsheet = run_gspread_with_retry(client.open_by_key, spreadsheet_id)
        now_str = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).strftime("%Y%m%d_%H%M%S")
        
        raw_values = []
        raw_deleted_count = 0
        backup_sheet_name = None
        
        # 1. Raw_Data 처리
        try:
            raw_sheet = run_gspread_with_retry(spreadsheet.worksheet, "Raw_Data")
            raw_values = run_gspread_with_retry(raw_sheet.get_all_values)
            if len(raw_values) > 1:
                raw_deleted_count = len(raw_values) - 1
                
                # A. 구글 시트 복제 백업 생성
                if create_backup:
                    backup_sheet_name = f"Raw_Backup_{now_str}"
                    try:
                        run_gspread_with_retry(spreadsheet.duplicate_sheet, raw_sheet.id, new_sheet_name=backup_sheet_name)
                    except Exception:
                        pass
                
                # B. 2행부터 마지막 행까지 삭제
                run_gspread_with_retry(raw_sheet.delete_rows, 2, len(raw_values))
                
                # C. 여유 행 확보
                if raw_sheet.row_count < 50:
                    run_gspread_with_retry(raw_sheet.add_rows, 50)
        except Exception as r_err:
            pass

        # 2. Demographic_Data 처리
        demo_values = []
        demo_deleted_count = 0
        try:
            demo_sheet = run_gspread_with_retry(spreadsheet.worksheet, "Demographic_Data")
            demo_values = run_gspread_with_retry(demo_sheet.get_all_values)
            if len(demo_values) > 1:
                demo_deleted_count = len(demo_values) - 1
                
                if create_backup:
                    try:
                        run_gspread_with_retry(spreadsheet.duplicate_sheet, demo_sheet.id, new_sheet_name=f"Demo_Backup_{now_str}")
                    except Exception:
                        pass
                
                run_gspread_with_retry(demo_sheet.delete_rows, 2, len(demo_values))
                if demo_sheet.row_count < 50:
                    run_gspread_with_retry(demo_sheet.add_rows, 50)
        except Exception:
            pass

        # 3. 로컬 SQLite DB 백업 저장 (surveys.db)
        if raw_deleted_count > 0 or demo_deleted_count > 0:
            try:
                conn = sqlite3.connect('surveys.db')
                c = conn.cursor()
                c.execute('''CREATE TABLE IF NOT EXISTS survey_responses_backup (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    survey_id TEXT,
                    backup_time TEXT,
                    user_id TEXT,
                    raw_data_json TEXT,
                    demo_data_json TEXT
                )''')
                c.execute("INSERT INTO survey_responses_backup (survey_id, backup_time, user_id, raw_data_json, demo_data_json) VALUES (?, ?, ?, ?, ?)",
                          (spreadsheet_id, now_str, str(user_id or "admin"), json.dumps(raw_values, ensure_ascii=False), json.dumps(demo_values, ensure_ascii=False)))
                conn.commit()
                conn.close()
            except Exception:
                pass

        # 4. 작업 로그 기록
        try:
            log_user_action(user_id or "admin", f"설문 응답 초기화({raw_deleted_count}건)")
        except Exception:
            pass

        return {
            "success": True,
            "deleted_count": raw_deleted_count,
            "demo_deleted_count": demo_deleted_count,
            "backup_sheet_name": backup_sheet_name,
            "backup_time": now_str
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


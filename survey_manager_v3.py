import json
import uuid
import streamlit as st
import gspread
import sqlite3
import datetime
from survey_manager import get_survey_gspread_client, run_gspread_with_retry

def create_survey_sheet_v3(title, admin_email, ahp_model, scale_type, demographics, definition_map, cr_limit, cr_guide_method, rewards_info, description="", existing_sheet_id=None, user_id=None):
    """
    [3계층 전용] 구글 스프레드시트 템플릿을 생성합니다.
    (대분류 -> 중분류 -> 소분류 조합 헤더 반영)
    """
    client = get_survey_gspread_client()
    if not client:
        return None

    spreadsheet = None
    if existing_sheet_id:
        try:
            spreadsheet = client.open_by_key(existing_sheet_id)
        except Exception as e:
            st.error(f"연동 실패: 입력하신 시트 ID를 찾을 수 없거나 권한이 없습니다. 오류 내용: {e}")
            return None
            
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
                
        try:
            raw_sheet = spreadsheet.worksheet("Raw_Data")
        except gspread.WorksheetNotFound:
            raw_sheet = spreadsheet.add_worksheet(title="Raw_Data", rows="1000", cols="50")

        try:
            demo_sheet = spreadsheet.worksheet("Demographic_Data")
        except gspread.WorksheetNotFound:
            demo_sheet = spreadsheet.add_worksheet(title="Demographic_Data", rows="1000", cols="20")
            
    else:
        try:
            from googleapiclient.discovery import build
            drive_service = build('drive', 'v3', credentials=client.auth)
            drive_service.files().emptyTrash().execute()
        except Exception as e_trash:
            pass
     
        spreadsheet = client.create(f"[AHP 설문_V3] {title}")
        
        if admin_email and "@" in admin_email:
            try:
                spreadsheet.share(admin_email, perm_type='user', role='writer', notify=False)
                try:
                    file_id = spreadsheet.id
                    permissions = drive_service.permissions().list(fileId=file_id).execute()
                    for perm in permissions.get('permissions', []):
                        if perm.get('emailAddress') == admin_email:
                            drive_service.permissions().update(
                                fileId=file_id,
                                permissionId=perm['id'],
                                body={'role': 'owner'},
                                transferOwnership=True
                            ).execute()
                            break
                except Exception as owner_err:
                    pass
            except Exception as e:
                st.warning(f"설문조사 담당자 이메일 공유 중 문제 발생: {e}")
     
        meta_sheet = spreadsheet.sheet1
        meta_sheet.update_title("Survey_Metadata")
        raw_sheet = spreadsheet.add_worksheet(title="Raw_Data", rows="1000", cols="50")
        demo_sheet = spreadsheet.add_worksheet(title="Demographic_Data", rows="1000", cols="20")
        
    metadata = [
        ["Field", "Value"],
        ["Title", title],
        ["Description", description],
        ["Admin_Email", admin_email],
        ["AHP_Model_JSON", json.dumps(ahp_model, ensure_ascii=False)],
        ["Tier_Level", "3"], # 3계층 식별 플래그
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
    
    # Raw Data 헤더 생성 (대분류 -> 중분류 -> 소분류 쌍대비교 조합)

    type_headers = ["Type"]
    if demographics and demographics.get("type_questions"):
        tq_count = len(demographics["type_questions"])
        if tq_count > 0:
            type_headers = [f"Type {i+1}" for i in range(tq_count)]
    raw_headers = ["ID"] + type_headers
    
    # 1. 대분류
    main_criteria = ahp_model.get("main", [])
    for i in range(len(main_criteria)):
        for j in range(i + 1, len(main_criteria)):
            raw_headers.append(f"{main_criteria[i]}_{main_criteria[j]}")
    
    # 2. 중분류
    sub_criteria_map = ahp_model.get("subs", {})
    for main_c in main_criteria:
        subs = sub_criteria_map.get(main_c, [])
        if len(subs) >= 2:
            for i in range(len(subs)):
                for j in range(i + 1, len(subs)):
                    raw_headers.append(f"{subs[i]}_{subs[j]}")

    # 3. 소분류 [신규 로직]
    sub_sub_map = ahp_model.get("sub_subs", {})
    for main_c in main_criteria:
        subs = sub_criteria_map.get(main_c, [])
        for sub_c in subs:
            sub_subs = sub_sub_map.get(sub_c, [])
            if len(sub_subs) >= 2:
                for i in range(len(sub_subs)):
                    for j in range(i + 1, len(sub_subs)):
                        raw_headers.append(f"{sub_subs[i]}_{sub_subs[j]}")
            
    raw_headers.append("제출시간")
    
    if len(raw_sheet.get_all_values()) == 0:
        raw_sheet.append_row(raw_headers)
        
    # Main_Criteria 시트 생성
    main_pairs = []
    for i in range(len(main_criteria)):
        for j in range(i + 1, len(main_criteria)):
            main_pairs.append(f"{main_criteria[i]}_{main_criteria[j]}")
    try:
        main_sheet = spreadsheet.worksheet("Main_Criteria")
    except gspread.WorksheetNotFound:
        main_sheet = spreadsheet.add_worksheet(title="Main_Criteria", rows="1000", cols="20")
    if len(main_sheet.get_all_values()) == 0:
        main_sheet.append_row(["ID"] + type_headers + main_pairs + ["제출시간"])
        
    # 중분류 시트 생성
    for main_c in main_criteria:
        subs = sub_criteria_map.get(main_c, [])
        if len(subs) >= 2:
            sub_pairs = []
            for i in range(len(subs)):
                for j in range(i + 1, len(subs)):
                    sub_pairs.append(f"{subs[i]}_{subs[j]}")
            safe_sheet_name = str(main_c)[:31]
            try:
                s_sheet = spreadsheet.worksheet(safe_sheet_name)
            except gspread.WorksheetNotFound:
                s_sheet = spreadsheet.add_worksheet(title=safe_sheet_name, rows="1000", cols="20")
            if len(s_sheet.get_all_values()) == 0:
                s_sheet.append_row(["ID"] + type_headers + sub_pairs + ["제출시간"])
                
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
                try:
                    ss_sheet = spreadsheet.worksheet(safe_sheet_name)
                except gspread.WorksheetNotFound:
                    ss_sheet = spreadsheet.add_worksheet(title=safe_sheet_name, rows="1000", cols="20")
                if len(ss_sheet.get_all_values()) == 0:
                    ss_sheet.append_row(["ID"] + type_headers + ss_pairs + ["제출시간"])
    # Demographic Data 헤더 생성
    demo_headers = ["ID"] + type_headers
    demo_cols = []
    if demographics.get("name"): demo_cols.append("성명")
    if demographics.get("age"): demo_cols.append("연령")
    if demographics.get("gender"): demo_cols.append("성별")
    if demographics.get("experience"): demo_cols.append("경력년수")
    if demographics.get("affiliation"): demo_cols.append("소속")
    if demographics.get("email"): demo_cols.append("이메일")
    demo_headers.extend(demo_cols)
    demo_headers.append("사전순위지정")
    if rewards_info.get("enabled"):
        demo_headers.append("경품연락처")
    demo_headers.append("제출시간")
    demo_sheet.append_row(demo_headers)
    
    # 로컬 캐시 백업
    try:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS survey_metadata_cache
                      (survey_id TEXT PRIMARY KEY, metadata_json TEXT, updated_at TEXT)''')
        meta_dict = {
            "Title": title,
            "Description": description,
            "Admin_Email": admin_email,
            "AHP_Model_JSON": ahp_model,
            "Tier_Level": 3,
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

    return spreadsheet.id

def generate_pairwise_combinations_v3(model):
    combinations = []
    
    # 1. 대분류
    main_c = model.get("main", [])
    if len(main_c) >= 2:
        combinations.append({
            "type": "main",
            "parent": "Main",
            "factors": main_c,
            "pairs": [(main_c[i], main_c[j]) for i in range(len(main_c)) for j in range(i + 1, len(main_c))]
        })
        
    # 2. 중분류
    sub_map = model.get("subs", {})
    for parent, subs in sub_map.items():
        if len(subs) >= 2:
            combinations.append({
                "type": "sub",
                "parent": parent,
                "factors": subs,
                "pairs": [(subs[i], subs[j]) for i in range(len(subs)) for j in range(i + 1, len(subs))]
            })

    # 3. 소분류 (V3 전용)
    sub_sub_map = model.get("sub_subs", {})
    for parent, subs in sub_map.items():
        for sub_c in subs:
            sub_subs = sub_sub_map.get(sub_c, [])
            if len(sub_subs) >= 2:
                combinations.append({
                    "type": "sub_sub",
                    "parent": sub_c,
                    "factors": sub_subs,
                    "pairs": [(sub_subs[i], sub_subs[j]) for i in range(len(sub_subs)) for j in range(i + 1, len(sub_subs))]
                })
            
    return combinations

def save_response_to_sheet_v3(spreadsheet_id, respondent_info, ahp_answers, demographics_settings, model, rewards_info):
    import datetime
    import sqlite3
    
    kst_now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).strftime("%Y-%m-%d %H:%M:%S")
    resp_id = respondent_info.get("id", str(uuid.uuid4())[:8])

    resp_types = respondent_info.get("types", [])
    if not resp_types:
        resp_types = [respondent_info.get("type", "일반")]

    
    raw_row_data = [resp_id] + resp_types
    
    # 1. 대분류 답변
    main_criteria = model.get("main", [])
    main_row_data = [resp_id] + resp_types
    for i in range(len(main_criteria)):
        for j in range(i + 1, len(main_criteria)):
            pair_key = f"{main_criteria[i]}_{main_criteria[j]}"
            raw_row_data.append(ahp_answers.get(pair_key, 1))
            main_row_data.append(ahp_answers.get(pair_key, 1))
    main_row_data.append(kst_now)
            
    # 2. 중분류 답변
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

    # 3. 소분류 답변
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
    
    demo_row_data = [resp_id] + resp_types
    if demographics_settings.get("name"): demo_row_data.append(respondent_info.get("name", ""))
    if demographics_settings.get("age"): demo_row_data.append(respondent_info.get("age", ""))
    if demographics_settings.get("gender"): demo_row_data.append(respondent_info.get("gender", ""))
    if demographics_settings.get("experience"): demo_row_data.append(respondent_info.get("experience", ""))
    if demographics_settings.get("affiliation"): demo_row_data.append(respondent_info.get("affiliation", ""))
    if demographics_settings.get("email"): demo_row_data.append(respondent_info.get("email", ""))
    demo_row_data.append(respondent_info.get("pre_ranking", ""))
    if rewards_info.get("enabled"):
        demo_row_data.append(respondent_info.get("reward_contact", ""))
    demo_row_data.append(kst_now)
    
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
        
        complete_payload = {
            "raw_row_data": raw_row_data,
            "demo_row_data": demo_row_data,
            "ahp_answers": ahp_answers,
            "respondent_info": respondent_info
        }
        
        c.execute("INSERT INTO survey_backup_responses (survey_id, respondent_id, response_json, saved_to_sheet, created_at) VALUES (?, ?, ?, 0, datetime('now'))",
                  (spreadsheet_id, resp_id, json.dumps(complete_payload, ensure_ascii=False)))
        conn.commit()
        db_id = c.lastrowid
        conn.close()
    except Exception as db_err:
        pass

    try:
        client = get_survey_gspread_client()
        if not client: return False
        spreadsheet = run_gspread_with_retry(client.open_by_key, spreadsheet_id)
        
        try:
            raw_sheet = run_gspread_with_retry(spreadsheet.worksheet, "Raw_Data")
            run_gspread_with_retry(raw_sheet.append_row, raw_row_data)
        except Exception:
            pass

        try:
            main_sheet = run_gspread_with_retry(spreadsheet.worksheet, "Main_Criteria")
            run_gspread_with_retry(main_sheet.append_row, main_row_data)
        except Exception:
            pass
            
        for s_name, s_row in sub_row_data_map.items():
            try:
                s_sheet = run_gspread_with_retry(spreadsheet.worksheet, s_name)
                run_gspread_with_retry(s_sheet.append_row, s_row)
            except Exception:
                pass
        
        demo_sheet = run_gspread_with_retry(spreadsheet.worksheet, "Demographic_Data")
        run_gspread_with_retry(demo_sheet.append_row, demo_row_data)
        
        try:
            conn = sqlite3.connect('users.db')
            c = conn.cursor()
            c.execute("UPDATE survey_backup_responses SET saved_to_sheet = 1 WHERE id = ?", (db_id,))
            conn.commit()
            conn.close()
        except Exception:
            pass
            
        return True
    except Exception as e:
        return False


def create_yeta_survey_sheet_v3(title, admin_email, ahp_model, demographics, definitions_map, description="", existing_sheet_id=None, user_id=None, coupon_config=None):
    client = get_survey_gspread_client()
    if not client:
        return None

    spreadsheet = None
    if existing_sheet_id:
        try:
            spreadsheet = client.open_by_key(existing_sheet_id)
        except Exception as e:
            st.error(f"연동 실패: 입력하신 시트 ID를 찾을 수 없거나 권한이 없습니다. 오류 내용: {e}")
            return None
            
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
                
        try:
            raw_sheet = spreadsheet.worksheet("Raw_Data")
        except gspread.WorksheetNotFound:
            raw_sheet = spreadsheet.add_worksheet(title="Raw_Data", rows="1000", cols="50")

        try:
            demo_sheet = spreadsheet.worksheet("Demographic_Data")
        except gspread.WorksheetNotFound:
            demo_sheet = spreadsheet.add_worksheet(title="Demographic_Data", rows="1000", cols="20")
            
    else:
        try:
            from googleapiclient.discovery import build
            drive_service = build('drive', 'v3', credentials=client.auth)
            drive_service.files().emptyTrash().execute()
        except Exception:
            pass
     
        spreadsheet = client.create(f"[예타] {title}")
        
        if admin_email and "@" in admin_email:
            try:
                spreadsheet.share(admin_email, perm_type='user', role='writer', notify=False)
            except Exception as e:
                st.warning(f"설문조사 담당자 이메일 공유 중 문제 발생: {e}")
     
        meta_sheet = spreadsheet.sheet1
        meta_sheet.update_title("Survey_Metadata")
        raw_sheet = spreadsheet.add_worksheet(title="Raw_Data", rows="1000", cols="50")
        demo_sheet = spreadsheet.add_worksheet(title="Demographic_Data", rows="1000", cols="20")
        
    metadata = [
        ["Field", "Value"],
        ["Title", title],
        ["Description", description],
        ["Admin_Email", admin_email],
        ["AHP_Model_JSON", json.dumps(ahp_model, ensure_ascii=False)],
        ["Tier_Level", "3"], 
        ["Demographics", json.dumps(demographics, ensure_ascii=False)],
        ["Is_Yeta", "True"],
        ["Visit_Count", "0"],
        ["Definitions", json.dumps(definitions_map, ensure_ascii=False)],
        ["Rewards_Info", json.dumps(coupon_config if coupon_config else {"enabled": False}, ensure_ascii=False)]
    ]
    meta_sheet.update(range_name="A1:B11", values=metadata)
    
    # Raw Data 헤더 생성
    type_headers = []
    if demographics and demographics.get("type_questions"):
        tq_count = len(demographics["type_questions"])
        for i in range(tq_count):
            type_headers.append(f"Type {i+1}")
            
    raw_headers = ["ID"] + type_headers
    
    # 1계층 상수합 컬럼 추가
    yeta_p_type = ahp_model.get("yeta_p_type", "건설사업 (비수도권)")
    if "non_capital" in yeta_p_type or "비수도권" in yeta_p_type:
        raw_headers.extend(["1계층_경제성(%)", "1계층_정책성(%)", "1계층_지역균형발전(%)"])
    elif "capital" in yeta_p_type or "수도권" in yeta_p_type:
        raw_headers.extend(["1계층_경제성(%)", "1계층_정책성(%)"])
    elif "rnd" in yeta_p_type or "R&D" in yeta_p_type:
        raw_headers.extend(["1계층_기술성(%)", "1계층_경제성(%)", "1계층_정책성(%)"])
    else:
        raw_headers.extend(["1계층_경제성(%)", "1계층_정책성(%)"])
        
    main_criteria = ahp_model.get("main", [])
    sub_criteria_map = ahp_model.get("subs", {})
    sub_sub_map = ahp_model.get("sub_subs", {})
    
    # 2계층 및 3계층 쌍대비교 컬럼
    for main_c in main_criteria:
        subs = sub_criteria_map.get(main_c, [])
        if len(subs) > 1:
            for i in range(len(subs)):
                for j in range(i+1, len(subs)):
                    raw_headers.append(f"쌍대비교_[{main_c}]_{subs[i].strip()}_vs_{subs[j].strip()}(실수형)")
                    
        for sub_c in subs:
            sub_subs = sub_sub_map.get(sub_c, [])
            if len(sub_subs) > 1:
                for i in range(len(sub_subs)):
                    for j in range(i+1, len(sub_subs)):
                        raw_headers.append(f"쌍대비교_[{main_c}_{sub_c.strip()}]_{sub_subs[i].strip()}_vs_{sub_subs[j].strip()}(실수형)")
                        
    # 대안평가 컬럼
    for main_c in main_criteria:
        subs = sub_criteria_map.get(main_c, [])
        if not subs:
            raw_headers.append(f"대안평가_[{main_c}]_{main_c.strip()}(시행선호_1~9_역수)")
        for sub_c in subs:
            sub_subs = sub_sub_map.get(sub_c, [])
            if not sub_subs:
                raw_headers.append(f"대안평가_[{main_c}]_{sub_c.strip()}(시행선호_1~9_역수)")
            else:
                for t3 in sub_subs:
                    raw_headers.append(f"대안평가_[{main_c}_{sub_c.strip()}]_{t3.strip()}(시행선호_1~9_역수)")
                    
    raw_headers.append("제출시간")
    
    raw_sheet.clear()
    raw_sheet.append_row(raw_headers)
    
    # Demographic Data 헤더 생성
    demo_headers = ["ID"] + type_headers
    if coupon_config and coupon_config.get("enabled"):
        demo_headers.append("경품연락처")
    demo_headers.append("제출시간")
    
    demo_sheet.clear()
    demo_sheet.append_row(demo_headers)
    
    # 로컬 캐시 백업
    try:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS survey_metadata_cache
                      (survey_id TEXT PRIMARY KEY, metadata_json TEXT, updated_at TEXT)''')
        meta_dict = {
            "Title": title,
            "Description": description,
            "Admin_Email": admin_email,
            "AHP_Model_JSON": ahp_model,
            "Tier_Level": 3,
            "Demographics": demographics,
            "Is_Yeta": True,
            "Definitions": definitions_map,
            "Rewards_Info": coupon_config if coupon_config else {"enabled": False}
        }
        c.execute("INSERT OR REPLACE INTO survey_metadata_cache (survey_id, metadata_json, updated_at) VALUES (?, ?, datetime('now'))",
                  (spreadsheet.id, json.dumps(meta_dict, ensure_ascii=False)))
        conn.commit()
        conn.close()
    except Exception:
        pass
        
    return spreadsheet.id


def save_yeta_response_to_sheet_v3(spreadsheet_id, respondent_info, ahp_answers, model, level1_answers, rewards_info=None):
    import datetime
    import sqlite3
    import uuid
    import json
    
    kst_now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).strftime("%Y-%m-%d %H:%M:%S")
    resp_id = respondent_info.get("id", str(uuid.uuid4())[:8])
    resp_types = respondent_info.get("types", [])
    
    raw_row_data = [resp_id] + resp_types
    
    # 1. 1계층 상수합 답변
    yeta_p_type = model.get("yeta_p_type", "건설사업 (비수도권)")
    if "non_capital" in yeta_p_type or "비수도권" in yeta_p_type:
        raw_row_data.extend([
            level1_answers.get("경제성", 0),
            level1_answers.get("정책성", 0),
            level1_answers.get("지역균형발전", 0)
        ])
    elif "capital" in yeta_p_type or "수도권" in yeta_p_type:
        raw_row_data.extend([
            level1_answers.get("경제성", 0),
            level1_answers.get("정책성", 0)
        ])
    elif "rnd" in yeta_p_type or "R&D" in yeta_p_type:
        raw_row_data.extend([
            level1_answers.get("기술성", 0),
            level1_answers.get("경제성", 0),
            level1_answers.get("정책성", 0)
        ])
    else:
        raw_row_data.extend([
            level1_answers.get("경제성", 0),
            level1_answers.get("정책성", 0)
        ])
        
    main_criteria = model.get("main", [])
    sub_criteria_map = model.get("subs", {})
    sub_sub_map = model.get("sub_subs", {})
    
    # 2. 쌍대비교 답변
    for main_c in main_criteria:
        subs = sub_criteria_map.get(main_c, [])
        if len(subs) > 1:
            for i in range(len(subs)):
                for j in range(i+1, len(subs)):
                    pair_key = f"{main_c}_{subs[i]}_{subs[j]}"
                    raw_row_data.append(ahp_answers.get(pair_key, 1))
                    
        for sub_c in subs:
            sub_subs = sub_sub_map.get(sub_c, [])
            if len(sub_subs) > 1:
                for i in range(len(sub_subs)):
                    for j in range(i+1, len(sub_subs)):
                        pair_key = f"{sub_c}_{sub_subs[i]}_{sub_subs[j]}"
                        raw_row_data.append(ahp_answers.get(pair_key, 1))
                        
    # 3. 대안평가 답변
    for main_c in main_criteria:
        subs = sub_criteria_map.get(main_c, [])
        if not subs:
            alt_key = f"alt_{main_c}_{main_c}"
            raw_row_data.append(ahp_answers.get(alt_key, 5))
        for sub_c in subs:
            sub_subs = sub_sub_map.get(sub_c, [])
            if not sub_subs:
                alt_key = f"alt_{main_c}_{sub_c}"
                raw_row_data.append(ahp_answers.get(alt_key, 5))
            else:
                for t3 in sub_subs:
                    alt_key = f"alt_{sub_c}_{t3}"
                    raw_row_data.append(ahp_answers.get(alt_key, 5))
                    
    raw_row_data.append(kst_now)
    
    demo_row_data = [resp_id] + resp_types
    if rewards_info and rewards_info.get("enabled"):
        demo_row_data.append(respondent_info.get("reward_contact", ""))
    demo_row_data.append(kst_now)
    
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
        complete_payload = {
            "raw_row_data": raw_row_data,
            "demo_row_data": demo_row_data,
            "ahp_answers": ahp_answers,
            "level1_answers": level1_answers,
            "respondent_info": respondent_info
        }
        c.execute("INSERT INTO survey_backup_responses (survey_id, respondent_id, response_json, saved_to_sheet, created_at) VALUES (?, ?, ?, 0, datetime('now'))",
                  (spreadsheet_id, resp_id, json.dumps(complete_payload, ensure_ascii=False)))
        conn.commit()
        db_id = c.lastrowid
        conn.close()
    except Exception:
        db_id = None
        
    try:
        client = get_survey_gspread_client()
        if not client: return False
        spreadsheet = run_gspread_with_retry(client.open_by_key, spreadsheet_id)
        
        try:
            raw_sheet = run_gspread_with_retry(spreadsheet.worksheet, "Raw_Data")
            run_gspread_with_retry(raw_sheet.append_row, raw_row_data)
        except Exception:
            pass
            
        try:
            demo_sheet = run_gspread_with_retry(spreadsheet.worksheet, "Demographic_Data")
            run_gspread_with_retry(demo_sheet.append_row, demo_row_data)
        except Exception:
            pass
            
        if db_id is not None:
            try:
                conn = sqlite3.connect('users.db')
                c = conn.cursor()
                c.execute("UPDATE survey_backup_responses SET saved_to_sheet = 1 WHERE id = ?", (db_id,))
                conn.commit()
                conn.close()
            except Exception:
                pass
        return True
    except Exception:
        return False


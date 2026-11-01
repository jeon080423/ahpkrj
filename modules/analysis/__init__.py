"""
AHPMASTER 분석 모듈
- AHP 분석 UI (main_tab1)

[2026-11-01] Team 3: standard_app.py L9810-12662에서 추출
- 원본: 'with main_tab1:' 블록 (L9809)
- st.stop() 6개 포함 (에러 처리용, 함수 내부에서 정상 동작)
- 들여쓰기: with 블록 4칸 제거 후 함수 본문 4칸으로 정리

주의: 이 모듈은 st.session_state를 직접 사용합니다.
"""
import streamlit as st

# core 모듈 import (Phase 1)
try:
    from core.auth import get_current_tier, check_tier, is_admin_mode
    from core.i18n import _
    from core.session import get_session
except ImportError:
    # 폴백: 직접 정의 (모듈 경로 문제 시)
    def _(ko, en):
        try:
            if st.session_state.get('lang', 'ko') == 'en':
                return en
        except:
            pass
        return ko


def render_analysis_module():
    """AHP 분석 UI 렌더링.

    원본: standard_app.py L9809-12662의 'with main_tab1:' 블록
    """
    tab1_main_col, tab1_settings_col = st.columns([3.0, 1.1], gap="large")
    with tab1_settings_col:
        ahp_method, mean_method, cr_threshold, max_iter_val, learning_rate = render_ahp_analysis_settings()
    tab1_main_col.__enter__()
    # 빠른 시작 섹션을 AHP 분석도구 탭 내부 최상단에 배치

    st.header(_("빠른 시작", "Quick Start"))
    st.info(_("일반 AHP 및 :blue[**퍼지 AHP**] 분석을 지원합니다. 엑셀 업로드 → 가중치 산출, 일관성(CR) 자동 보정, 그룹 집계까지 한 번에 완료됩니다.",
              "Supports both Traditional and :blue[**Fuzzy AHP**] analysis. Upload Excel → individual weights, automatic CR correction, and group aggregation in one step."))
        
    sample_excel = create_sample_excel()
        
    is_en = st.session_state.get('lang', 'ko') == 'en'
    tahp_path = "sample_data/E_TAHP_Result.xlsx" if is_en else "sample_data/K_TAHP_Result.xlsx"
    fahp_path = "sample_data/E_FAHP_Result.xlsx" if is_en else "sample_data/K_FAHP_Result.xlsx"
        
    tahp_data, tahp_err = _load_example_file(tahp_path)
    fahp_data, fahp_err = _load_example_file(fahp_path)

        
    if tahp_err: st.error(f"TAHP Load Error: {tahp_err} | Path: {tahp_path}")
    if fahp_err: st.error(f"FAHP Load Error: {fahp_err} | Path: {fahp_path}")

    # 3계층 샘플 데이터: 권한에 따라 분기
    # - 정식/관리자: Mock_3Tier_Full.xlsx (100행, 실제 분석 가능)
    # - 무료/비로그인: create_sample_excel_v3() (3행, 3행 제한 통과)
    _role_now = st.session_state.get('user_role', None)
    sample_excel_v3 = create_sample_excel_v3()
    _v3_label = _("📂 3계층 샘플 데이터", "📂 3-Tier Sample Data")
    _v3_filename = _("AHP_3Tier_Sample.xlsx", "AHP_3Tier_Sample.xlsx")
        
    # 모든 사용자에게 2계층·3계층 샘플 데이터 + 결과 예시 버튼 4개 표시
    col_btn1, col_btn2, col_btn3, col_btn4 = st.columns(4)
    with col_btn1:
        st.download_button(
            label=_("📂 2계층 샘플 데이터", "📂 2-Tier Sample Data"),
            data=sample_excel,
            file_name=_("AHP_UrbanRegeneration_2Tier_Sample.xlsx", "AHP_UrbanRegeneration_2Tier_Sample.xlsx"),
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            type="primary"
        )
    with col_btn2:
        st.download_button(
            label=_v3_label,
            data=sample_excel_v3,
            file_name=_v3_filename,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            type="primary"
        )
    with col_btn3:
        st.download_button(
            label=_("📄 일반 AHP 분석 결과(예시)", "📄 Traditional AHP Report (Example)"),
            data=tahp_data if tahp_data else b"",
            file_name=_("E_TAHP_Result.xlsx", "E_TAHP_Result.xlsx") if is_en else _("K_TAHP_Result.xlsx", "K_TAHP_Result.xlsx"),
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            disabled=(not tahp_data)
        )
    with col_btn4:
        st.download_button(
            label=_("📄 퍼지 AHP 분석 결과(예시)", "📄 Fuzzy AHP Report (Example)"),
            data=fahp_data if fahp_data else b"",
            file_name=_("E_FAHP_Result.xlsx", "E_FAHP_Result.xlsx") if is_en else _("K_FAHP_Result.xlsx", "K_FAHP_Result.xlsx"),
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            disabled=(not fahp_data)
        )
    
    st.subheader(_("1. 데이터 업로드 및 분석", "1. Data Upload & Analysis"))
    
    if st.session_state.get('user_role') == 'admin':
        st.info(_("**혼합 계층(Mixed-Tier) 엑셀 분석 안내**: 3계층 코딩 엑셀 양식을 업로드할 때, 특정 항목에 대한 소분류 평가 시트가 없거나 응답이 비워져 있더라도 시스템이 해당 항목을 자동으로 2계층 가중치로 간주하여 에러 없이 분석을 수행합니다.", "**Mixed-Tier Excel Analysis Guide**: When uploading a 3-tier Excel template, if there are no sub-sub-criteria evaluation sheets for specific items or the responses are blank, the system automatically considers them as 2-tier weights and performs the analysis without errors."))

    # 데이터 소스 선택 추가
    _ds_options = [_("📂 엑셀 파일 직접 업로드", "Upload Excel File"), _("🌐 배포된 온라인 설문 데이터 연동", "Link Online Survey Data")]
    _ds_default_idx = 1 if st.session_state.get("_auto_switch_to_online") else 0
    data_source = st.radio(
        _("분석 데이터 소스 선택", "Select Analysis Data Source"),
        _ds_options,
        index=_ds_default_idx,
        horizontal=True
    )
    # 플래그 사용 후 해제 (수동 전환 시 간섭 방지)
    if st.session_state.get("_auto_switch_to_online"):
        st.session_state["_auto_switch_to_online"] = False

    # [신규 추가] 인구통계 빈도/비율 분석용 헬퍼 함수
    def generate_demographics_summary(demo_df):
        if demo_df is None or demo_df.empty:
            return None
        
        working_df = demo_df.copy()
        
        def _clean_id(x):
            s = str(x).strip()
            if s.endswith(".0"):
                s = s[:-2]
            return s
        
        # 1. 최종 완료 응답자(ID)만 필터링 (미완료/이탈자 제외)
        completed_ids = set()
        if "ahp_df_main" in st.session_state and st.session_state["ahp_df_main"] is not None:
            if "ID" in st.session_state["ahp_df_main"].columns:
                completed_ids = set(st.session_state["ahp_df_main"]["ID"].apply(_clean_id))
        elif "live_df" in st.session_state and st.session_state["live_df"] is not None:
            if "ID" in st.session_state["live_df"].columns:
                completed_ids = set(st.session_state["live_df"]["ID"].apply(_clean_id))
        
        id_col = None
        for c in working_df.columns:
            if str(c).strip().lower() == "id":
                id_col = c
                break

        if completed_ids and id_col:
            working_df = working_df[working_df[id_col].apply(_clean_id).isin(completed_ids)].copy()

        if working_df.empty:
            return None

        # 불필요한 시스템용 컬럼 제외
        exclude_keywords = ["id", "type", "사전순위", "답례품", "연락처", "제출시간"]
        target_cols = []
        for col in working_df.columns:
            col_lower = str(col).lower()
            if not any(ex in col_lower for ex in exclude_keywords):
                target_cols.append(col)
        
        if not target_cols:
            return None
            
        summary_rows = []
        # _기타 컬럼의 부모 질문 매핑 (비율 계산용)
        _etc_parent_counts = {}
        for col in target_cols:
            col_str = str(col).strip()
            if col_str.endswith('_기타') or col_str.endswith('(기타)'):
                # 부모 컬럼 찾기 (예: "소속_기타" -> "소속")
                parent_col = None
                base_name = col_str[:-3] if col_str.endswith('_기타') else col_str[:-4]
                for pc in target_cols:
                    pc_str = str(pc).strip()
                    if pc_str == base_name or pc_str.startswith(base_name):
                        # 정확히 일치하거나, 부모가 base_name으로 시작하고 _기타가 아닌 경우
                        if not (pc_str.endswith('_기타') or pc_str.endswith('(기타)')):
                            parent_col = pc
                            break
                if parent_col is not None:
                    # 부모에서 "기타"를 선택한 응답자 수 계산
                    parent_data = working_df[parent_col]
                    etc_count = 0
                    for val in parent_data:
                        if pd.isna(val):
                            continue
                        val_str = str(val).strip()
                        if val_str == "기타" or "기타" in val_str:
                            etc_count += 1
                    if etc_count > 0:
                        _etc_parent_counts[col_str] = etc_count
        
        for col in target_cols:
            col_str = str(col).strip()
            col_data = working_df[col]
            
            # 2. 질문 문구가 응답 보기로 들어가거나 빈 값인 항목 제거 (유효 응답만 필터링)
            valid_items = []
            for val in col_data:
                if pd.isna(val):
                    continue
                val_str = str(val).strip()
                if not val_str or val_str == "미응답(N/A)":
                    continue
                # 질문 헤더 텍스트와 동일하거나 일부 포함된 기본값 텍스트 제외
                if val_str == col_str or (len(val_str) >= 8 and (val_str in col_str or col_str in val_str)):
                    continue
                valid_items.append(val_str)
            
            if not valid_items:
                continue
            
            series_valid = pd.Series(valid_items)
            counts = series_valid.value_counts()
            total = len(valid_items)
            # _기타 컬럼인 경우: 부모의 "기타" 응답자 수를 분모로 사용하여 비율 계산
            # (예: 기타 3명 중 1명이 "개인사업가" 입력 → 33.3%)
            is_etc_col = col_str.endswith('_기타') or col_str.endswith('(기타)')
            denom = _etc_parent_counts.get(col_str, total) if is_etc_col else total
            for val, count in counts.items():
                pct = (count / denom) * 100 if denom > 0 else 0
                summary_rows.append({
                    "인구통계 항목 (Demographic Field)": col,
                    "응답 보기 (Value)": val,
                    "빈도수 (Frequency)": count,
                    "비율 (Percentage, %)": pct
                })
                
        if summary_rows:
            return pd.DataFrame(summary_rows)
        return None

    def preprocess_uploaded_df(df):
        # 1. 제출시간/타임스탬프 제거
        drop_cols = [c for c in df.columns if str(c).strip().lower() in ["타임스탬프", "제출시간", "timestamp"]]
        if drop_cols:
            df = df.drop(columns=drop_cols)
        # 다중 인구통계(Type 1, Type 2...)는 유지하여 향후 선택적 분석이 가능하도록 함
        return df
        
    df_main = None
    sub_dfs = {}
    sheet_names = []
    filename_base = "AHP_Analysis"

    if data_source == _("📂 엑셀 파일 직접 업로드", "Upload Excel File"):
        uploaded_file = st.file_uploader(_("작성된 엑셀 파일 업로드 (.xlsx)", "Upload completed Excel file (.xlsx)"), type=['xlsx', 'xls'])
        if uploaded_file:
            try:
                excel_obj = pd.ExcelFile(uploaded_file)
                sheet_names = excel_obj.sheet_names
                df_main = pd.read_excel(uploaded_file, sheet_name=sheet_names[0])
                df_main = preprocess_uploaded_df(df_main)

                # [2026-10-19] 등급별 표본 수 제한 (헬퍼로 일원화: Free 3 / Basic 10)
                df_main = apply_sample_limit(df_main, source_label="엑셀 업로드")
                
                if "Type" not in df_main.columns and len(df_main.columns) > 1:
                    col1 = df_main.columns[1]
                    if "_" not in col1 and col1 not in ["ID", "제출시간"]:
                        df_main.rename(columns={col1: "Type"}, inplace=True)

                # [신규] 엑셀 파일 내의 그룹 분석 후보 변수(ID/쌍대비교 제외 메타 컬럼) 감지
                excel_group_vars = {}
                meta_candidate_cols = [c for c in df_main.columns if '_' not in str(c) and str(c) not in ["ID", "제출시간", "timestamp"] and not str(c).endswith('_기타') and not str(c).endswith('(기타)')]
                for mc in meta_candidate_cols:
                    c_str = str(mc).strip()
                    if "ID" in df_main.columns:
                        excel_group_vars[c_str] = df_main.set_index("ID")[mc].to_dict()
                    else:
                        excel_group_vars[c_str] = {i: df_main.iloc[i][mc] for i in range(len(df_main))}
                st.session_state["available_group_vars"] = excel_group_vars
                        
                # 3계층 식별 로직 (df_main 컬럼에서 _ 포함된 것으로 대분류 요인 도출, _기타/Type 컬럼 제외)
                main_criteria_infer = set()
                for col in df_main.columns:
                    c_str = str(col).strip()
                    if '_' in c_str and not c_str.endswith('_기타') and not c_str.endswith('(기타)') and not c_str.lower().startswith('type'):
                        parts = c_str.split('_')
                        if len(parts) == 2:
                            main_criteria_infer.add(parts[0])
                            main_criteria_infer.add(parts[1])
                
                inferred_sub_sub_dfs = {}
                ignore_sheets = ["raw_data", "raw_data_dump", "demographic_data", "raw data"]
                for sn in sheet_names[1:]:
                    # [추가] 온라인 설문 배포 형식 엑셀의 원본/인구통계 데이터 시트 자동 무시 (단, 인구통계는 별도 저장)
                    sn_lower = sn.lower().strip()
                    if sn_lower in ignore_sheets:
                        if "demographic" in sn_lower:
                            demo_df = pd.read_excel(uploaded_file, sheet_name=sn)
                            demo_df = preprocess_uploaded_df(demo_df)
                            # [2026-10-19] 등급별 표본 수 제한 (헬퍼로 일원화: Free 3 / Basic 10)
                            demo_df = apply_sample_limit(demo_df, source_label="엑셀 업로드")
                            st.session_state["demo_df"] = demo_df
                        continue
                        
                    df_sheet = pd.read_excel(uploaded_file, sheet_name=sn)
                    df_sheet = preprocess_uploaded_df(df_sheet)
                    # [2026-10-19] 등급별 표본 수 제한 (헬퍼로 일원화: Free 3 / Basic 10)
                    df_sheet = apply_sample_limit(df_sheet, source_label="엑셀 업로드")
                        
                    if "Type" not in df_sheet.columns and len(df_sheet.columns) > 1:
                        col1 = df_sheet.columns[1]
                        if "_" not in col1 and col1 not in ["ID", "제출시간"]:
                            df_sheet.rename(columns={col1: "Type"}, inplace=True)
                            
                    # 안전한 시트명(safe_sheet_name)을 위해 앞부분이 일치하는지 확인
                    is_sub = any(sn == mc[:31] for mc in main_criteria_infer)
                    if is_sub:
                        sub_dfs[sn] = df_sheet
                    else:
                        inferred_sub_sub_dfs[sn] = df_sheet
                
                if len(inferred_sub_sub_dfs) > 0:
                    st.session_state["ahp_sub_sub_dfs"] = inferred_sub_sub_dfs
                    st.session_state["inferred_tier_level"] = 3
                else:
                    st.session_state["inferred_tier_level"] = 2
                    
                filename_base = uploaded_file.name.split('.')[0]
            except Exception as e:
                st.error(f"엑셀 파일 로드 실패: {e}")
    else:
        # 배포된 온라인 설문 데이터 연동
        if st.session_state.user_id is None:
            st.warning(_(" 온라인 설문 데이터 연동 분석은 회원 전용 기능입니다. 로그인해 주세요.", " Online survey integration is available for members. Please log in."))
        else:
            import sqlite3
            try:
                sync_short_codes_from_gs()
            except Exception:
                pass
            conn = sqlite3.connect('users.db')
            cur = conn.cursor()
            cur.execute("SELECT survey_id, title, created_at FROM admin_surveys WHERE admin_id = ? ORDER BY created_at DESC", (st.session_state.user_id,))
            sqlite_surveys = cur.fetchall()
            conn.close()
            
            gs_surveys = []
            try:
                from survey_manager import get_admin_surveys_from_gsheet
                gs_surveys = get_admin_surveys_from_gsheet(st.session_state.user_id)
            except Exception:
                pass
            
            merged_surveys = {}
            for s in gs_surveys + sqlite_surveys:
                if s[0] not in merged_surveys:
                    merged_surveys[s[0]] = s
            admin_surveys = list(merged_surveys.values())
            admin_surveys.sort(key=lambda x: x[2], reverse=True)
        
            if not admin_surveys:
                st.warning(_("배포된 온라인 설문이 없습니다.", "No deployed online surveys found."))
            else:
                survey_options = {f"{row[1]} ({row[2]})": row[0] for row in admin_surveys}
            
                default_idx = 0
                if st.session_state.get("selected_survey_for_analysis") in survey_options.values():
                    default_idx = list(survey_options.values()).index(st.session_state.get("selected_survey_for_analysis"))
            
                selected_survey_label = st.selectbox(
                    _("분석할 온라인 설문 선택", "Select Online Survey for Analysis"),
                    list(survey_options.keys()),
                    index=default_idx
                )
                selected_sheet_id = survey_options[selected_survey_label]
                filename_base = f"Survey_{selected_sheet_id[:6]}"
            
                if st.button(_("🔄 구글 시트에서 실시간 응답 가져오기", "🔄 Fetch Live Responses from Google Sheet"), type="primary", use_container_width=True):
                    import survey_manager; survey_manager.log_user_action(st.session_state.get("user_id") or "Guest", "실시간 응답 가져오기")
                    # [1단계] 분석 시작 이벤트
                    try:
                        from survey_manager import log_structured_event, get_anonymous_user_id, get_anonymous_survey_id, EVENT_ANALYSIS_STARTED
                        log_structured_event(EVENT_ANALYSIS_STARTED,
                            anonymous_user_id=get_anonymous_user_id(st.session_state.get("user_id") or "guest"),
                            anonymous_survey_id=get_anonymous_survey_id(selected_sheet_id))
                    except Exception:
                        pass
                    st.session_state["selected_survey_for_analysis"] = selected_sheet_id
                    from survey_manager import load_survey_metadata, get_survey_gspread_client
                    with st.spinner(_("구글 시트에서 설문 데이터 및 구조를 가져오는 중...", "Fetching survey structure and responses...")):
                        survey_meta = load_survey_metadata(selected_sheet_id)
                        g_client = get_survey_gspread_client()
                        if survey_meta and g_client:
                            try:
                                spreadsheet = run_gspread_with_retry(g_client.open_by_key, selected_sheet_id)
                                raw_sheet = run_gspread_with_retry(spreadsheet.worksheet, "Raw_Data")
                                # [2026-10-21 할당량 대응] Raw/Demographic/Alt 시트를 batchGet 1회로 일괄 조회해
                                # 읽기 요청 수를 대폭 줄이고(개별 조회 반복 시 분당 60회 쿼터 초과 빈발), 429는 재시도 헬퍼로 흡수
                                _batch_vals = {}
                                try:
                                    _titles_ld = [w.title for w in run_gspread_with_retry(spreadsheet.worksheets)]
                                    _ranges_ld = [t for t in ("Raw_Data", "Demographic_Data") if t in _titles_ld]
                                    _model_pre = survey_meta.get("AHP_Model_JSON", {}) or {}
                                    if len(_model_pre.get("alternatives", []) or []) >= 2:
                                        from survey_manager_v3 import get_leaf_criteria_v3 as _glc_pre
                                        for _lf_pre in _glc_pre(_model_pre):
                                            _t_pre = f"Alt_{_lf_pre}"[:31]
                                            if _t_pre in _titles_ld and _t_pre not in _ranges_ld:
                                                _ranges_ld.append(_t_pre)
                                    _res_ld = run_gspread_with_retry(spreadsheet.batch_get, [f"'{t}'" for t in _ranges_ld])
                                    _batch_vals = {t: [list(r) for r in (v or [])] for t, v in zip(_ranges_ld, _res_ld)}
                                except Exception as _batch_err:
                                    # [2026-10-24] 429(쿼터 소진)면 개별 조회 폴백으로 추가 요청을 만들지 말고
                                    # 그대로 올려보내 안내 메시지로 처리 (폴백이 쿼터를 더 소진시켜 실패를 확정했음)
                                    if "429" in str(_batch_err) or "RESOURCE_EXHAUSTED" in str(_batch_err) or "RATE_LIMIT" in str(_batch_err):
                                        raise
                                    _batch_vals = {}
                                all_rows = _batch_vals.get("Raw_Data")
                                if all_rows is None:
                                    all_rows = run_gspread_with_retry(raw_sheet.get_all_values)
                            
                                if len(all_rows) > 1:
                                    ahp_model = survey_meta["AHP_Model_JSON"]
                                    tier_level = int(survey_meta.get("Tier_Level", 2))
                                    demographics = survey_meta.get("Demographics", {})

                                    # 1. 정규 쌍대비교 컬럼 목록 구성 (대분류 -> 중분류 -> 소분류)
                                    main_criteria = [c.strip() for c in ahp_model.get("main", [])]
                                    main_pairs = [f"{main_criteria[i]}_{main_criteria[j]}"
                                                  for i in range(len(main_criteria))
                                                  for j in range(i + 1, len(main_criteria))]

                                    sub_criteria_map = ahp_model.get("subs", {})
                                    sub_pairs_by_main = {}
                                    all_sub_pairs = []
                                    for main_c in main_criteria:
                                        subs = [s.strip() for s in sub_criteria_map.get(main_c, [])]
                                        if len(subs) >= 2:
                                            pairs = [f"{subs[i]}_{subs[j]}"
                                                     for i in range(len(subs))
                                                     for j in range(i + 1, len(subs))]
                                            sub_pairs_by_main[main_c] = pairs
                                            all_sub_pairs.extend(pairs)

                                    sub_sub_map = ahp_model.get("sub_subs", {}) if tier_level == 3 else {}
                                    sub_sub_pairs_by_sub = {}
                                    all_ss_pairs = []
                                    if tier_level == 3:
                                        for main_c in main_criteria:
                                            subs = [s.strip() for s in sub_criteria_map.get(main_c, [])]
                                            for sub_c in subs:
                                                sub_subs = [s.strip() for s in sub_sub_map.get(sub_c, [])]
                                                if len(sub_subs) >= 2:
                                                    # [2026-10-21 버그수정] 소분류 쌍 이름이 중분류마다 반복되므로
                                                    # 위치 기반 파싱값을 담을 레코드 키를 부모 접두사로 구분 (중복 덮어쓰기 방지)
                                                    pairs = [f"SS::{sub_c}::{sub_subs[i]}_{sub_subs[j]}"
                                                             for i in range(len(sub_subs))
                                                             for j in range(i + 1, len(sub_subs))]
                                                    sub_sub_pairs_by_sub[sub_c] = pairs
                                                    all_ss_pairs.extend(pairs)

                                    all_expected_pair_cols = main_pairs + all_sub_pairs + all_ss_pairs
                                    total_expected_pairs = len(all_expected_pair_cols)

                                    # 2. 인구통계(Type) 질문 수 감지 및 행별 동적 파싱
                                    tq_list = demographics.get("type_questions", []) if demographics else []
                                    tq_count = len(tq_list)
                                    if tq_count == 0 and demographics and demographics.get("type_options"):
                                        tq_count = 1
                                        
                                    # 각 질문별 컬럼 정의 (질문명, 기타컬럼 포함 여부)
                                    tq_col_defs = []
                                    if tq_list:
                                        for i, tq in enumerate(tq_list):
                                            q_name = tq.get("q", f"인구통계 {i+1}").strip()
                                            has_etc = tq.get("q_type", "radio") == "radio" and any("기타" in str(opt) or "other" in str(opt).lower() for opt in tq.get("opts", []))
                                            tq_col_defs.append((q_name, has_etc))
                                    else:
                                        q_name = demographics.get("type_question", "그룹 분류(Type)") if demographics else "그룹 분류(Type)"
                                        has_etc = demographics and any("기타" in str(opt) or "other" in str(opt).lower() for opt in demographics.get("type_options", []))
                                        tq_col_defs.append((q_name, has_etc))

                                    expected_type_col_count = sum(2 if has_etc else 1 for _, has_etc in tq_col_defs)
                                    tq_names = [q_name for q_name, _ in tq_col_defs]

                                    parsed_records = []
                                    for r_idx, row in enumerate(all_rows[1:]):
                                        r = [str(c) for c in row]
                                        while r and r[-1] == '':
                                            r.pop()
                                        if not r or not any(r):
                                            continue

                                        resp_id = r[0]
                                        time_val = r[-1] if len(r) > 1 and ("-" in r[-1] and ":" in r[-1]) else ""
                                        comp_end = len(r) - 1 if time_val else len(r)

                                        # 인구통계 열이 여러 개이거나 기타 직접입력 열이 있어도 실제 쌍대비교 위치를 정확히 탐색
                                        comp_start = 1 + expected_type_col_count
                                        if comp_end - comp_start == total_expected_pairs:
                                            comp_vals = r[comp_start:comp_end]
                                            resp_type = r[1] if len(r) > 1 and r[1].strip() else "일반"
                                        elif comp_end >= total_expected_pairs + 1:
                                            # 역방향 정렬: 제출시간 바로 앞의 total_expected_pairs 개를 쌍대비교값으로 취함
                                            comp_start = comp_end - total_expected_pairs
                                            comp_vals = r[comp_start:comp_end]
                                            resp_type = r[1] if comp_start > 1 and r[1].strip() else "일반"
                                        else:
                                            comp_vals = r[1:comp_end] + [''] * max(0, total_expected_pairs - (comp_end - 1))
                                            resp_type = r[1] if len(r) > 1 and r[1].strip() else "일반"

                                        # 모든 인구통계 항목값 보존 (기타 직접입력값 포함)
                                        t_vals = r[1:comp_start] if comp_start > 1 else []
                                        rec = {"ID": resp_id, "Type": resp_type}
                                        val_ptr = 0
                                        for q_name, has_etc in tq_col_defs:
                                            q_val = t_vals[val_ptr].strip() if val_ptr < len(t_vals) else ""
                                            val_ptr += 1
                                            rec[f"DEMO_{q_name}"] = q_val if q_val else "미응답"
                                            if has_etc:
                                                etc_val = t_vals[val_ptr].strip() if val_ptr < len(t_vals) else ""
                                                val_ptr += 1
                                                rec[f"DEMO_{q_name}_기타"] = etc_val

                                        for k, p_col in enumerate(all_expected_pair_cols):
                                            v = comp_vals[k] if k < len(comp_vals) else np.nan
                                            rec[p_col] = pd.to_numeric(v, errors='coerce')
                                        if time_val:
                                            rec["제출시간"] = time_val
                                        parsed_records.append(rec)

                                    raw_df = pd.DataFrame(parsed_records)

                                    # [2026-10-19] 등급별 표본 수 제한 (헬퍼로 일원화: Free 3 / Basic 10)
                                    raw_df = apply_sample_limit(raw_df, source_label="온라인 설문 연동")

                                    # [신규] 그룹 분석 기준 변수 맵 구성 (인구통계 질문 + Demographic_Data 시트 항목, 주관식 기타 입력값 제외)
                                    group_vars_map = {}
                                    for d_name in tq_names:
                                        col_key = f"DEMO_{d_name}"
                                        if col_key in raw_df.columns:
                                            group_vars_map[d_name] = raw_df.set_index("ID")[col_key].to_dict()
                                    if not group_vars_map and "Type" in raw_df.columns:
                                        group_vars_map["그룹 분류(Type)"] = raw_df.set_index("ID")["Type"].to_dict()

                                    # Demographic_Data 시트에서 추가 인구통계(성별, 경력 등) 병합
                                    try:
                                        demo_all_vals = _batch_vals.get("Demographic_Data")
                                        if demo_all_vals is None:
                                            demo_sheet = spreadsheet.worksheet("Demographic_Data")
                                            demo_all_vals = run_gspread_with_retry(demo_sheet.get_all_values)
                                        if len(demo_all_vals) > 1:
                                            from survey_manager import clean_and_align_sheet_rows
                                            demo_df_loaded, clean_demo_m, demo_rep = clean_and_align_sheet_rows(demo_all_vals, survey_meta=survey_meta, is_demo=True)
                                            st.session_state["demo_df"] = demo_df_loaded
                                            for col in demo_df_loaded.columns:
                                                c_clean = col.strip()
                                                if c_clean and c_clean not in ["ID", "제출시간", "timestamp", "보상", "이메일", "전화번호"] and not c_clean.startswith("순위") and not c_clean.endswith("_기타") and not c_clean.endswith("(기타)"):
                                                    if c_clean not in group_vars_map:
                                                        group_vars_map[c_clean] = demo_df_loaded.set_index("ID")[col].to_dict()
                                    except Exception:
                                        pass

                                    st.session_state["available_group_vars"] = group_vars_map

                                    # 3. 대분류 데이터프레임 구성
                                    st.session_state["ahp_df_main"] = raw_df[["ID", "Type"] + main_pairs].copy()

                                    # 4. 중분류 데이터프레임 구성
                                    st.session_state["ahp_sub_dfs"] = {}
                                    for main_c in main_criteria:
                                        if main_c in sub_pairs_by_main:
                                            pairs = sub_pairs_by_main[main_c]
                                            st.session_state["ahp_sub_dfs"][main_c] = raw_df[["ID", "Type"] + pairs].copy()

                                    # 5. 소분류 데이터프레임 구성 (3계층 모델인 경우)
                                    st.session_state["ahp_sub_sub_dfs"] = {}
                                    if tier_level == 3:
                                        for sub_c, ss_pairs in sub_sub_pairs_by_sub.items():
                                            # [2026-10-21 버그수정] 잎별 df는 기존 분석 코드와 호환되도록 접두사를 벗긴 쌍 이름으로 복원
                                            _ss_df = raw_df[["ID", "Type"] + ss_pairs].copy()
                                            _ss_prefix = f"SS::{sub_c}::"
                                            _ss_df.columns = ["ID", "Type"] + [p[len(_ss_prefix):] if p.startswith(_ss_prefix) else p for p in ss_pairs]
                                            st.session_state["ahp_sub_sub_dfs"][sub_c] = _ss_df

                                    # [2026-10-20] 6. 대안 평가 데이터프레임 구성 (Alt 시트가 있는 설문만)
                                    st.session_state["ahp_alt_dfs"] = {}
                                    st.session_state["ahp_alternatives"] = []
                                    st.session_state["alt_analysis_result"] = None
                                    _alt_model_ld = survey_meta.get("AHP_Model_JSON", {}) if survey_meta else {}
                                    _alts_ld = _alt_model_ld.get("alternatives", []) or []
                                    if len(_alts_ld) >= 2:
                                        try:
                                            from survey_manager_v3 import get_leaf_criteria_v3 as _glc_ld
                                            _alt_pairs_ld = [f"{_alts_ld[i]}_{_alts_ld[j]}" for i in range(len(_alts_ld)) for j in range(i + 1, len(_alts_ld))]
                                            for _leaf_ld in _glc_ld(_alt_model_ld):
                                                try:
                                                    _alt_vals = _batch_vals.get(f"Alt_{_leaf_ld}"[:31])
                                                    if _alt_vals is None:
                                                        _alt_ws = spreadsheet.worksheet(f"Alt_{_leaf_ld}"[:31])
                                                        _alt_vals = run_gspread_with_retry(_alt_ws.get_all_values)
                                                    if len(_alt_vals) > 1:
                                                        _adf_ld = pd.DataFrame(_alt_vals[1:], columns=_alt_vals[0])
                                                        for _pc_ld in _alt_pairs_ld:
                                                            if _pc_ld in _adf_ld.columns:
                                                                _adf_ld[_pc_ld] = pd.to_numeric(_adf_ld[_pc_ld], errors='coerce')
                                                        # [2026-10-21 버그수정] Alt 시트의 소속 등 인구통계 컬럼이 쌍대비교 컬럼으로 오인되어
                                                        # 전 응답자가 형식 오류로 제외되던 문제 — 대분류/중분류 df와 동일하게 ID·Type·대안 쌍 컬럼만 유지
                                                        _type_src_ld = [c for c in _adf_ld.columns if c not in ["ID", "제출시간"] + _alt_pairs_ld and not str(c).endswith("_기타")]
                                                        _type_vals_ld = _adf_ld[_type_src_ld[0]] if _type_src_ld else ""
                                                        _rebuilt_ld = {"ID": _adf_ld["ID"], "Type": _type_vals_ld}
                                                        for _pc_ld in _alt_pairs_ld:
                                                            if _pc_ld in _adf_ld.columns:
                                                                _rebuilt_ld[_pc_ld] = _adf_ld[_pc_ld]
                                                        _adf_ld = pd.DataFrame(_rebuilt_ld)
                                                        _adf_ld = apply_sample_limit(_adf_ld, source_label="대안 평가")
                                                        st.session_state["ahp_alt_dfs"][_leaf_ld] = _adf_ld
                                                except Exception:
                                                    pass
                                            if st.session_state["ahp_alt_dfs"]:
                                                st.session_state["ahp_alternatives"] = _alts_ld
                                                st.session_state["ahp_alt_model"] = _alt_model_ld
                                        except Exception:
                                            pass

                                    sheet_names_list = ["Main_Criteria"] + list(st.session_state["ahp_sub_dfs"].keys())
                                    if tier_level == 3:
                                        sheet_names_list += list(st.session_state["ahp_sub_sub_dfs"].keys())

                                    st.session_state["ahp_sheet_names"] = sheet_names_list
                                    # [수정] 실제 요인명 저장 (F1/F2 폴백 방지용)
                                    st.session_state["ahp_main_criteria"] = main_criteria
                                    st.session_state["ahp_sub_criteria_map"] = {k.strip(): [s.strip() for s in v] for k, v in sub_criteria_map.items()}

                                    # [헤더 자동 동기화] 구글 시트의 Raw_Data 헤더가 불일치할 경우 백그라운드 갱신
                                    type_header_names = []
                                    if demographics and demographics.get("type_questions"):
                                        tqs = demographics["type_questions"]
                                        for i, tq in enumerate(tqs):
                                            t_col = f"Type {i+1}" if len(tqs) > 1 else "Type"
                                            type_header_names.append(t_col)
                                            if tq.get("q_type", "radio") == "radio" and any("기타" in str(opt) or "other" in str(opt).lower() for opt in tq.get("opts", [])):
                                                type_header_names.append(f"{t_col}_기타")
                                    else:
                                        type_header_names.append("Type")
                                        if demographics and any("기타" in str(opt) or "other" in str(opt).lower() for opt in demographics.get("type_options", [])):
                                            type_header_names.append("Type_기타")
                                    expected_headers = ["ID"] + type_header_names + all_expected_pair_cols + ["제출시간"]
                                    try:
                                        if all_rows and len(all_rows[0]) != len(expected_headers):
                                            padded_headers = expected_headers + [''] * max(0, len(all_rows[0]) - len(expected_headers))
                                            raw_sheet.update(range_name="A1", values=[padded_headers])
                                    except Exception:
                                        pass

                                    st.success(_(f"✅ 구글 시트에서 총 {len(raw_df)}건의 응답 데이터를 성공적으로 가져왔습니다!", f"✅ Successfully fetched {len(raw_df)} responses!"))
                                else:
                                    st.warning(_("가져올 설문 응답 데이터가 시트에 존재하지 않습니다 (헤더만 존재).", "No survey responses found in the sheet."))
                            except Exception as g_err:
                                if "429" in str(g_err) or "RESOURCE_EXHAUSTED" in str(g_err) or "RATE_LIMIT" in str(g_err):
                                    st.error("구글 시트 요청이 일시적으로 한도(분당 60회)를 초과했습니다. 약 1분 뒤에 다시 시도해 주세요.")
                                else:
                                    st.error(f"구글 시트 로드 실패: {g_err}")
                        else:
                            st.error(_("설문 메타데이터 또는 구글 API 클라이언트를 로드할 수 없습니다.", "Failed to load survey metadata or Google client."))

                with st.expander(_("⚙️ 설문 응답 데이터 초기화 및 백업 관리", "⚙️ Survey Response Data Reset & Backup"), expanded=False):
                    st.caption(_("테스트로 수집된 응답을 비우고 본 조사를 새로 시작할 때 사용합니다. 설문 설정 및 문항은 유지됩니다.",
                                 "Clears test submissions before starting the real survey. Settings and questions are preserved."))
                    if st.button(_("🗑️ 응답 로우데이터 초기화 마법사 열기", "🗑️ Open Response Data Reset Wizard"), type="secondary", use_container_width=True, key="btn_open_reset_tab1"):
                        show_reset_survey_dialog(selected_sheet_id, selected_survey_label)
            
                if "ahp_df_main" in st.session_state:
                    df_main = st.session_state["ahp_df_main"]
                    sub_dfs = st.session_state["ahp_sub_dfs"]
                    sheet_names = st.session_state["ahp_sheet_names"]

    if df_main is not None:
        try:
            main_cols_up = df_main.columns[2:]
            main_factors_up, n_main_up = infer_factors_from_columns(main_cols_up)
        
            permission_granted = False
            message = ""
            role_chk = st.session_state.user_role
            user_id_chk = st.session_state.user_id
        
            if role_chk == 'admin' or role_chk == 'official':
                permission_granted = True
                if role_chk == 'official':
                    today_chk = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).date()
                    expiry_chk = datetime.datetime.strptime(st.session_state.expiry_date, "%Y-%m-%d").date()
                    if today_chk > expiry_chk:
                        permission_granted = False
                        message = _("⛔ 이용 기간이 만료되었습니다.", "⛔ Your subscription period has expired.")
                    

            else: 
                # [수정] 무료 사용자: 차단 대신 처음 3개 표본으로 슬라이싱하여 분석 허용
                if data_source == _("📂 엑셀 파일 직접 업로드", "Upload Excel File"):
                    if len(df_main) > 3:
                        df_main = df_main.head(3)
                        st.warning(_("⚠️ 무료 사용자는 엑셀 업로드 시 최대 3표본까지 분석할 수 있습니다. 처음 3개 표본만 분석에 사용됩니다.",
                                     "⚠️ Free users can analyze up to 3 samples. Only the first 3 samples will be used."))
                    for sn in list(sub_dfs.keys()):
                        if len(sub_dfs[sn]) > 3:
                            sub_dfs[sn] = sub_dfs[sn].head(3)
                else:
                    if len(df_main) > 3:
                        df_main = df_main.head(3)
                        st.warning(_("⚠️ 무료 사용자는 온라인 설문 연동 시 최대 3표본까지 분석할 수 있습니다. 처음 3개 표본만 분석에 사용됩니다.",
                                     "⚠️ Free users can analyze up to 3 samples. Only the first 3 responses will be used."))
                    for sn in list(sub_dfs.keys()):
                        if len(sub_dfs[sn]) > 3:
                            sub_dfs[sn] = sub_dfs[sn].head(3)
                permission_granted = True
        
            if permission_granted:
                # [신규] 그룹 분석 기준 변수 선택 UI 및 동적 주입
                available_vars = st.session_state.get("available_group_vars", {})
                if available_vars and len(available_vars) > 1:
                    var_options = list(available_vars.keys())
                    saved_var = st.session_state.get("current_group_var_name")
                    default_idx = var_options.index(saved_var) if saved_var in var_options else 0

                    st.markdown(_("##### 👥 그룹 분석 기준 변수 설정", "##### 👥 Group Analysis Variable Settings"))
                    col_g1, col_g2 = st.columns([3, 1])
                    with col_g1:
                        chosen_group_var = st.selectbox(
                            _("그룹 분석(집단 비교/ANOVA/레이더 차트)에 사용할 기본 정보 변수를 선택하세요:",
                              "Select demographic variable for group comparison, ANOVA, and radar charts:"),
                            var_options,
                            index=default_idx,
                            key="sb_group_analysis_var_choice",
                            help=_("선택하신 기본 정보 문항의 응답값을 기준으로 집단별 가중치 비교, ANOVA 통계 검정, 레이더 차트가 수행됩니다.",
                                   "Performs group comparisons, ANOVA tests, and radar charts based on the selected demographic variable.")
                        )
                    with col_g2:
                        val_map = available_vars[chosen_group_var]
                        distinct_groups = sorted(list(set(str(v).strip() for v in val_map.values() if v and pd.notna(v))))
                        st.metric(_("구분 집단 수", "Group Count"), f"{len(distinct_groups)}개 집단")

                    st.session_state["current_group_var_name"] = chosen_group_var

                    # 선택된 변수 값으로 df_main, sub_dfs, sub_sub_dfs의 'Type' 열을 일괄 동적 갱신
                    if "ID" in df_main.columns:
                        df_main["Type"] = df_main["ID"].map(val_map).fillna(df_main.get("Type", "미응답"))
                    for s_name, s_df in sub_dfs.items():
                        if "ID" in s_df.columns:
                            s_df["Type"] = s_df["ID"].map(val_map).fillna(s_df.get("Type", "미응답"))
                    current_sub_subs = st.session_state.get("ahp_sub_sub_dfs", {})
                    for ss_name, ss_df in current_sub_subs.items():
                        if "ID" in ss_df.columns:
                            ss_df["Type"] = ss_df["ID"].map(val_map).fillna(ss_df.get("Type", "미응답"))
                    st.divider()
                elif available_vars and len(available_vars) == 1:
                    st.session_state["current_group_var_name"] = list(available_vars.keys())[0]

                tier = get_current_tier()
                try:
                    if data_source == _("📂 엑셀 파일 직접 업로드", "Upload Excel File"):
                        tier_level = st.session_state.get("inferred_tier_level", 2)
                    else:
                        if 'survey_meta' not in locals():
                            from survey_manager import load_survey_metadata
                            sheet_id_for_meta = st.session_state.get("selected_survey_for_analysis")
                            survey_meta = load_survey_metadata(sheet_id_for_meta) if sheet_id_for_meta else {}
                        tier_level = int(survey_meta.get("Tier_Level", 2)) if survey_meta else 2
                    
                    if tier_level == 3:
                        is_english = (st.session_state.get('lang', 'ko') == 'en')
                        success_v3 = False
                        msg_v3 = ""
                        final_df_v3 = None
                        output_res_v3 = None
                        ui_data_v3 = {}
                        with st.spinner(_("3계층(소분류 포함) AHP 종합 분석 수행 중...", "Performing 3-Tier AHP...")):
                            from ahp_utils_v3 import run_ahp_analysis_v3
                            sub_sub_dfs = st.session_state.get("ahp_sub_sub_dfs", {})

                            # [2026-10-19] 최종 방어선: 등급별 표본 수 제한을 분석 직전에 재적용
                            # (세션에 무제한 데이터가 남아있는 경우 소분류 누락 방지)
                            df_main = apply_sample_limit(df_main, source_label="3계층 분석")
                            sub_dfs = {k: apply_sample_limit(v) for k, v in sub_dfs.items()}
                            sub_sub_dfs = {k: apply_sample_limit(v) for k, v in sub_sub_dfs.items()}

                            # 인구통계 요약본 생성하여 전달
                            demo_summary_df_v3 = None
                            if "demo_df" in st.session_state and st.session_state["demo_df"] is not None:
                                demo_summary_df_v3 = generate_demographics_summary(st.session_state["demo_df"])
                                
                            success_v3, msg_v3, final_df_v3, output_res_v3, ui_data_v3 = run_ahp_analysis_v3(
                                df_main, sub_dfs, sub_sub_dfs, cr_threshold, max_iter_val, learning_rate, mean_method, ahp_method,
                                process_single_sheet, fuzzy_ahp_analysis, demo_summary_df=demo_summary_df_v3
                            )

                        if not success_v3:
                            st.error(msg_v3)
                            tab1_main_col.__exit__(None, None, None)
                            st.stop()
                        
                        if st.session_state.user_role == 'official':
                            if data_source == _("📂 엑셀 파일 직접 업로드", "Upload Excel File") and uploaded_file is not None:
                                save_data = uploaded_file.getvalue()
                                save_filename = f"{filename_base}_Raw.xlsx"
                            else:
                                uploadable_io = io.BytesIO()
                                with pd.ExcelWriter(uploadable_io, engine='openpyxl') as writer:
                                    if df_main is not None and not df_main.empty:
                                        df_main.to_excel(writer, index=False, sheet_name="Main_Criteria")
                                    for s_name, s_df in sub_dfs.items():
                                        s_df.to_excel(writer, index=False, sheet_name=s_name[:31])
                                    sub_sub_dfs_to_save = st.session_state.get("ahp_sub_sub_dfs", {})
                                    for s_name, s_df in sub_sub_dfs_to_save.items():
                                        s_df.to_excel(writer, index=False, sheet_name=s_name[:31])
                                save_data = uploadable_io.getvalue()
                                save_filename = f"{filename_base}_Raw.xlsx"
                            save_analysis_to_db(st.session_state.user_id, save_filename, save_data)

                        st.success(_("✅ 3계층 AHP 분석이 성공적으로 완료되었습니다!", "✅ 3-Tier AHP Analysis successfully completed!"))
                        if get_current_tier() == 'Basic':
                            st.info(_("**Basic 제한**: 표본 10개로 제한됩니다. Standard 이상으로 업그레이드하세요.",
                                      "💡 **Basic Limit**: Limited to 10 samples. Please upgrade to Standard or higher."))
                        st.caption(_("⚠️ 새로고침 시 결과가 리셋됩니다. 결과 다운로드 탭에서 반드시 저장하세요.",
                                     "⚠️ Results reset on refresh. Download via the Results tab."))

                        # --- 3계층 전용 5개 탭 UI ---
                        v3_unique_groups = ui_data_v3.get("unique_groups", [])
                        v3_comparison_df  = ui_data_v3.get("comparison_df", pd.DataFrame())
                        v3_anova_df       = ui_data_v3.get("anova_df", pd.DataFrame())
                        v3_group_full_dfs = ui_data_v3.get("group_full_dfs", {})
                        v3_indiv_df       = ui_data_v3.get("indiv_df", pd.DataFrame())
                        v3_main_factors   = ui_data_v3.get("main_factors", [])

                        tab3v1, tab3v2, tab3v3, tab3v4, tab3v5 = st.tabs([
                            _("종합 분석 (Global)", "Global Comprehensive Analysis"),
                            _("그룹별 분석", "Group Analysis"),
                            _("통계 검정 (ANOVA)", "Statistical Test (ANOVA)"),
                            _("시각화 센터", "Visualization Center"),
                            _("결과 다운로드", "Download Results")
                        ])

                        # ─── Tab 1: 종합 분석 ────────────────────────────────────────────
                        with tab3v1:
                            st.subheader(_(" 3계층 종합 중요도 및 순위", " 3-Tier Global Weights & Rankings"))
                            if is_english:
                                _disp_v3 = final_df_v3.rename(columns={
                                    "대분류": "Main Criteria",    "대분류 가중치": "Main Weight",
                                    "중분류": "Sub-Criteria",     "중분류 가중치": "Sub Weight",
                                    "소분류": "Sub-sub-Criteria", "소분류 가중치": "Sub-sub Weight",
                                    "CR(대분류)": "CR(Main)",     "CI(대분류)": "CI(Main)",
                                    "CR(중분류)": "CR(Sub)",      "CI(중분류)": "CI(Sub)",
                                    "CR(소분류)": "CR(Sub-sub)",  "CI(소분류)": "CI(Sub-sub)"
                                })
                            else:
                                _disp_v3 = final_df_v3
                            st.dataframe(_disp_v3.style.format(precision=4), use_container_width=True)

                            st.markdown(_("---\n####  대분류별 소분류 항목 글로벌 가중치",
                                          "---\n#### 📊 Sub-sub-Criteria Global Weights by Main Criteria"))
                            _non_dummy_v3 = final_df_v3[~final_df_v3["소분류"].str.endswith("_단일항목", na=False)].copy()
                            if _non_dummy_v3.empty:
                                _non_dummy_v3 = final_df_v3.copy()
                            for _mf_v3 in v3_main_factors:
                                _mf_subset = _non_dummy_v3[_non_dummy_v3["대분류"] == _mf_v3]
                                if _mf_subset.empty:
                                    continue
                                _mf_chart = _mf_subset.sort_values("Global Weight", ascending=True).copy()
                                if is_english:
                                    _mf_chart = _mf_chart.rename(columns={"소분류": "Sub-sub-Criteria"})
                                    _y_col_v3 = "Sub-sub-Criteria"
                                else:
                                    _y_col_v3 = "소분류"
                                _fig_v3_bar = px.bar(
                                    _mf_chart, y=_y_col_v3, x="Global Weight",
                                    orientation="h", text_auto=".4f",
                                    title=_(f"[{_mf_v3}] 소분류 항목별 글로벌 가중치", f"[{_mf_v3}] Sub-sub-Criteria Global Weights"),
                                    color_discrete_sequence=["#4F81BD"]
                                )
                                _fig_v3_bar.update_layout(height=max(300, len(_mf_chart)*40+80), margin=dict(l=0,r=10,t=40,b=20))
                                st.plotly_chart(_fig_v3_bar, use_container_width=True)

                        # ─── Tab 2: 그룹별 분석 ──────────────────────────────────────────
                        with tab3v2:
                            st.markdown(_("#### 그룹별 소분류 항목 글로벌 가중치 비교",
                                          "#### Sub-sub-Criteria Global Weight Comparison by Group"))
                            if not v3_comparison_df.empty:
                                if is_english:
                                    _disp_comp_v3 = v3_comparison_df.copy()
                                    _disp_comp_v3.rename(columns={
                                        "대분류": "Main Criteria", "중분류": "Sub-Criteria", "소분류": "Sub-sub-Criteria",
                                        "종합평균(Overall)": "Overall Avg", "F-값": "F-Value",
                                        "유의성": "Significance", "사후검정(Tukey HSD)": "Post-Hoc (Tukey HSD)"
                                    }, inplace=True)
                                    if "Significance" in _disp_comp_v3.columns:
                                        _disp_comp_v3["Significance"] = _disp_comp_v3["Significance"].map(
                                            {"유의함": "Significant", "유의하지 않음": "Not Significant"}).fillna(_disp_comp_v3["Significance"])
                                else:
                                    _disp_comp_v3 = v3_comparison_df
                                st.dataframe(_disp_comp_v3.style.format(precision=4), use_container_width=True)
                            else:
                                st.info(_("그룹별 비교 데이터가 없습니다.", "No group comparison data available."))

                            if len(v3_unique_groups) >= 2 and v3_group_full_dfs:
                                st.markdown(_("---\n#### 그룹별 대분류 가중치 비교",
                                              "---\n#### Main Criteria Weight Comparison by Group"))
                                _grp_main_rows = []
                                for _grp_v3 in v3_unique_groups:
                                    if _grp_v3 not in v3_group_full_dfs:
                                        continue
                                    _g_df_v3 = v3_group_full_dfs[_grp_v3]
                                    for _mf_v3b in v3_main_factors:
                                        _mf_sub_b = _g_df_v3[_g_df_v3["대분류"] == _mf_v3b]
                                        if not _mf_sub_b.empty:
                                            _grp_main_rows.append({
                                                _("그룹","Group"): _grp_v3,
                                                _("대분류","Main Criteria"): _mf_v3b,
                                                "Weight": float(_mf_sub_b.iloc[0]["대분류 가중치"])
                                            })
                                if _grp_main_rows:
                                    _grp_main_chart_df = pd.DataFrame(_grp_main_rows)
                                    _fig_grp_main = px.bar(
                                        _grp_main_chart_df,
                                        x=_("대분류","Main Criteria"), y="Weight",
                                        color=_("그룹","Group"), barmode="group", text_auto=".4f",
                                        title=_("그룹별 대분류 가중치 비교", "Main Criteria Weight Comparison by Group")
                                    )
                                    st.plotly_chart(_fig_grp_main, use_container_width=True)

                        # ─── Tab 3: ANOVA ─────────────────────────────────────────────────
                        with tab3v3:
                            st.markdown(_("#### 집단 간 유의성 분석 (3계층 기준)",
                                          "#### Significance Analysis Between Groups (3-Tier Level)"))
                            if not v3_anova_df.empty:
                                if is_english:
                                    _disp_anova_v3 = v3_anova_df.copy()
                                    _disp_anova_v3.rename(columns={
                                        "요인": "Factor/Criteria", "F-값": "F-Value",
                                        "유의성": "Significance", "사후검정(Tukey HSD)": "Post-Hoc (Tukey HSD)"
                                    }, inplace=True)
                                    if "Significance" in _disp_anova_v3.columns:
                                        _disp_anova_v3["Significance"] = _disp_anova_v3["Significance"].map(
                                            {"유의함": "Significant", "유의하지 않음": "Not Significant"}).fillna(_disp_anova_v3["Significance"])
                                    def _translate_ph_v3(v):
                                        if not isinstance(v, str): return v
                                        v = v.replace("전문가","Expert").replace("일반","General").replace("공무원","Public Official")
                                        v = v.replace(" 차이 있음"," (Diff exists)")
                                        v = v.replace("집단 간 구체적 차이 발견 못함","No significant pairwise difference found")
                                        v = v.replace("계산 오류","Calculation Error")
                                        return v
                                    if "Post-Hoc (Tukey HSD)" in _disp_anova_v3.columns:
                                        _disp_anova_v3["Post-Hoc (Tukey HSD)"] = _disp_anova_v3["Post-Hoc (Tukey HSD)"].apply(_translate_ph_v3)
                                else:
                                    _disp_anova_v3 = v3_anova_df
                                st.dataframe(_disp_anova_v3.style.format(precision=5), use_container_width=True)

                                _sig_col_v3 = "Significance" if is_english else "유의성"
                                _sig_val_v3 = "Significant" if is_english else "유의함"
                                if _sig_col_v3 in _disp_anova_v3.columns:
                                    _sig_items_v3 = _disp_anova_v3[_disp_anova_v3[_sig_col_v3] == _sig_val_v3]
                                    if not _sig_items_v3.empty:
                                        _fcol_v3 = "Factor/Criteria" if is_english else "요인"
                                        _snames = ", ".join(_sig_items_v3[_fcol_v3].tolist())
                                        st.success(_(f"✅ 유의한 차이 발견 항목: {_snames}", f"✅ Statistically significant factors: {_snames}"))
                                    else:
                                        st.info(_("모든 항목에서 그룹 간 유의한 차이가 없습니다.", "No statistically significant group differences found."))
                            else:
                                st.info(_("통계 검정을 위해 2개 이상의 그룹 데이터가 필요합니다.",
                                          "At least 2 group datasets are required for ANOVA."))

                        # ─── Tab 4: 시각화 센터 ──────────────────────────────────────────
                        with tab3v4:
                            st.markdown(_("####  3계층 AHP 시각화 센터", "####  3-Tier AHP Visualization Center"))

                            st.markdown(_("**① 글로벌 가중치 순위 버블 차트 (버블 크기 = 중분류 가중치, 색 = 대분류)**",
                                          "**① Global Weight Bubble Chart (bubble size = Sub weight, color = Main Criteria)**"))
                            _nd_v3 = final_df_v3[~final_df_v3["소분류"].str.endswith("_단일항목", na=False)].copy()
                            if _nd_v3.empty:
                                _nd_v3 = final_df_v3.copy()
                                _item_col_bub = "중분류"
                            else:
                                _item_col_bub = "소분류"
                            _bubble_df = _nd_v3.copy()
                            if "Global Rank" not in _bubble_df.columns:
                                _bubble_df["Global Rank"] = _bubble_df["Global Weight"].rank(ascending=False, method="min").astype(int)
                            # 버블 크기: 중분류 가중치 기반 (최소 크기 보장)
                            _bubble_df["_bubble_size"] = (_bubble_df["중분류 가중치"] * 100).clip(lower=3)
                            if is_english:
                                _bubble_df_disp = _bubble_df.rename(columns={
                                    "소분류": "Sub-sub-Criteria", "대분류": "Main Criteria",
                                    "중분류": "Sub-Criteria", "중분류 가중치": "Sub Weight"
                                })
                                _label_col_bub = "Sub-sub-Criteria" if _item_col_bub == "소분류" else "Sub-Criteria"
                                _color_bub = "Main Criteria"
                                _hover_sub_bub = "Sub-Criteria"
                                _hover_subw_bub = "Sub Weight"
                            else:
                                _bubble_df_disp = _bubble_df
                                _label_col_bub = _item_col_bub
                                _color_bub = "대분류"
                                _hover_sub_bub = "중분류"
                                _hover_subw_bub = "중분류 가중치"
                            _fig_bub = px.scatter(
                                _bubble_df_disp,
                                x="Global Rank", y="Global Weight",
                                size="_bubble_size", color=_color_bub,
                                text=_label_col_bub,
                                hover_data={
                                    _label_col_bub: True,
                                    _hover_sub_bub: True,
                                    _hover_subw_bub: ":.4f",
                                    "Global Weight": ":.4f",
                                    "Global Rank": True,
                                    "_bubble_size": False
                                },
                                title=_("소분류 글로벌 가중치 버블 차트 (버블이 클수록 중분류 비중 높음, 위로 갈수록 글로벌 가중치 높음)",
                                        "Sub-sub-Criteria Global Weight Bubble Chart (larger = higher sub weight, higher = higher global weight)"),
                                color_discrete_sequence=px.colors.qualitative.Set2,
                                size_max=55
                            )
                            _fig_bub.update_traces(textposition="top center", textfont_size=10)
                            _fig_bub.update_xaxes(
                                title=_("종합 순위 (1위 = 가장 중요)", "Global Rank (1 = Most Important)"),
                                dtick=1, autorange="reversed"
                            )
                            _fig_bub.update_yaxes(title=_("글로벌 가중치", "Global Weight"))
                            _fig_bub.update_layout(height=560, legend_title_text=_color_bub)
                            st.plotly_chart(_fig_bub, use_container_width=True)

                            st.markdown(_("**② 계층별 일관성 비율(CR) 분포 — 바이올린 플롯**",
                                          "**② Consistency Ratio (CR) Distribution by Tier — Violin Plot**"))
                            st.caption(_("계층을 선택하면 해당 수준 응답자들의 CR 분포를 표시합니다. 바이올린 폭 = 밀도, 내부 박스 = 중앙값·사분위수, 점 = 개별 응답자",
                                         "Select a tier to view respondent CR distribution. Width = density, box = median/IQR, dots = individual respondents"))

                            _vio_main_df   = ui_data_v3.get("main_results_df", pd.DataFrame())
                            _vio_sub_stor  = ui_data_v3.get("sub_results_storage", {})
                            _vio_ss_stor   = ui_data_v3.get("sub_sub_results_storage", {})
                            _vio_mf_list   = ui_data_v3.get("main_factors", [])

                            _tier_options_ko = ["대분류 (Main)", "중분류 (Sub)", "소분류 (Sub-sub)"]
                            _tier_options_en = ["Main Criteria", "Sub-Criteria", "Sub-sub-Criteria"]
                            _tier_opts = _tier_options_en if is_english else _tier_options_ko
                            _sel_tier = st.selectbox(
                                _("📂 표시할 계층 선택", "📂 Select Tier to Display"),
                                options=_tier_opts,
                                key="vio_tier_select_v3"
                            )

                            try:
                                import plotly.graph_objects as _go_vio
                                _vio_palette = [
                                    "rgba(70,130,180,0.65)",
                                    "rgba(205,92,92,0.65)",
                                    "rgba(255,182,193,0.65)",
                                    "rgba(60,179,113,0.65)",
                                    "rgba(255,165,0,0.65)",
                                    "rgba(147,112,219,0.65)",
                                    "rgba(72,209,204,0.65)",
                                    "rgba(255,215,0,0.65)",
                                ]
                                _vio_line_pal = [
                                    "#4682B4","#CD5C5C","#FFB6C1","#3CB371",
                                    "#FFA500","#9370DB","#48D1CC","#FFD700"
                                ]
                                _fig_vio = _go_vio.Figure()
                                _ci = 0

                                # ── 선택: 대분류 ─────────────────────────────────
                                if _sel_tier in [_tier_opts[0]]:
                                    if not _vio_main_df.empty and "Final_CR" in _vio_main_df.columns:
                                        _main_cr = _vio_main_df["Final_CR"].dropna().tolist()
                                        _xlbl = _("대분류", "Main Criteria")
                                        _fig_vio.add_trace(_go_vio.Violin(
                                            y=_main_cr, x=[_xlbl]*len(_main_cr),
                                            name=_xlbl, box_visible=True, meanline_visible=True,
                                            points="all", jitter=0.35, pointpos=0,
                                            line_color=_vio_line_pal[0], fillcolor=_vio_palette[0],
                                            opacity=0.75,
                                            hovertemplate="<b>" + _xlbl + "</b><br>CR: %{y:.4f}<extra></extra>",
                                            showlegend=True
                                        ))
                                    _vio_xaxis_title = _("대분류", "Main Criteria")
                                    _vio_legend_title = _("대분류", "Main Criteria")

                                # ── 선택: 중분류 ─────────────────────────────────
                                elif _sel_tier in [_tier_opts[1]]:
                                    # 대분류별로 하나의 바이올린 (해당 대분류 중분류 비교 시 CR)
                                    for _mf in _vio_mf_list:
                                        _sinfo = _vio_sub_stor.get(_mf, {})
                                        _sdf = _sinfo.get("df", None)
                                        if _sdf is None or _sdf.empty or "Final_CR" not in _sdf.columns:
                                            continue
                                        _cr_vals = _sdf["Final_CR"].dropna().tolist()
                                        if len(_cr_vals) < 2:
                                            continue
                                        _xlbl = _(f"중분류({_mf})", f"Sub({_mf})")
                                        _fig_vio.add_trace(_go_vio.Violin(
                                            y=_cr_vals, x=[_xlbl]*len(_cr_vals),
                                            name=_xlbl, box_visible=True, meanline_visible=True,
                                            points="all", jitter=0.35, pointpos=0,
                                            line_color=_vio_line_pal[_ci % len(_vio_line_pal)],
                                            fillcolor=_vio_palette[_ci % len(_vio_palette)],
                                            opacity=0.75,
                                            hovertemplate="<b>" + _xlbl + "</b><br>CR: %{y:.4f}<extra></extra>",
                                            showlegend=True
                                        ))
                                        _ci += 1
                                    _vio_xaxis_title = _("대분류 (중분류 비교 CR)", "Main Criteria (Sub-Criteria Comparison CR)")
                                    _vio_legend_title = _("중분류", "Sub-Criteria")

                                # ── 선택: 소분류 ─────────────────────────────────
                                else:
                                    # 중분류별로 하나의 바이올린 (해당 중분류 소분류 비교 시 CR)
                                    for _mf in _vio_mf_list:
                                        _sinfo = _vio_sub_stor.get(_mf, {})
                                        _sub_factors = _sinfo.get("factors", [])
                                        for _sf in _sub_factors:
                                            _ssinfo = _vio_ss_stor.get(_sf, {})
                                            _ssdf = _ssinfo.get("df", None)
                                            if _ssdf is None or _ssdf.empty or "Final_CR" not in _ssdf.columns:
                                                continue
                                            _cr_vals = _ssdf["Final_CR"].dropna().tolist()
                                            if len(_cr_vals) < 2:
                                                continue
                                            _xlbl = _(f"소분류({_sf})", f"Sub-sub({_sf})")
                                            _fig_vio.add_trace(_go_vio.Violin(
                                                y=_cr_vals, x=[_xlbl]*len(_cr_vals),
                                                name=_xlbl, box_visible=True, meanline_visible=True,
                                                points="all", jitter=0.35, pointpos=0,
                                                line_color=_vio_line_pal[_ci % len(_vio_line_pal)],
                                                fillcolor=_vio_palette[_ci % len(_vio_palette)],
                                                opacity=0.75,
                                                hovertemplate="<b>" + _xlbl + "</b><br>CR: %{y:.4f}<extra></extra>",
                                                showlegend=True
                                            ))
                                            _ci += 1
                                    _vio_xaxis_title = _("중분류 (소분류 비교 CR)", "Sub-Criteria (Sub-sub Comparison CR)")
                                    _vio_legend_title = _("소분류", "Sub-sub-Criteria")

                                if len(_fig_vio.data) == 0:
                                    st.info(_("선택한 계층의 CR 데이터가 없거나 응답 수가 부족합니다.",
                                              "No CR data available for the selected tier or insufficient responses."))
                                else:
                                    _fig_vio.add_hline(
                                        y=0.1, line_dash="dash", line_color="red",
                                        annotation_text=_("CR 임계값 (0.1)", "CR Threshold (0.1)"),
                                        annotation_position="top right"
                                    )
                                    _fig_vio.update_layout(
                                        title=_(
                                            f"바이올린플롯 CR — {_sel_tier}",
                                            f"Violin Plot CR — {_sel_tier}"
                                        ),
                                        xaxis_title=_vio_xaxis_title,
                                        yaxis_title="Final_CR",
                                        violinmode="overlay",
                                        height=540,
                                        legend_title_text=_vio_legend_title,
                                        plot_bgcolor="white",
                                        paper_bgcolor="white",
                                        xaxis=dict(showgrid=False, tickangle=-20),
                                        yaxis=dict(showgrid=True, gridcolor="#eeeeee", zeroline=False)
                                    )
                                    st.plotly_chart(_fig_vio, use_container_width=True)
                            except Exception as _e_vio:
                                st.warning(_(f"바이올린 플롯 생성 실패: {_e_vio}", f"Violin plot generation failed: {_e_vio}"))

                            if len(v3_unique_groups) >= 2 and v3_group_full_dfs:
                                st.markdown(_("**③ 그룹별 대분류 중요도 레이더 차트**",
                                              "**③ Main Criteria Importance Radar Chart by Group**"))
                                _radar_rows = []
                                for _grp_rd in v3_unique_groups:
                                    if _grp_rd not in v3_group_full_dfs: continue
                                    _gdf_rd = v3_group_full_dfs[_grp_rd]
                                    for _mf_rd in v3_main_factors:
                                        _mf_rd_sub = _gdf_rd[_gdf_rd["대분류"]==_mf_rd]
                                        _w_rd = float(_mf_rd_sub.iloc[0]["대분류 가중치"]) if not _mf_rd_sub.empty else 0.0
                                        _lbl_rd = str(_grp_rd).replace("전문가","Expert").replace("일반","General").replace("공무원","Public Official") if is_english else _grp_rd
                                        _radar_rows.append({_("그룹","Group"): _lbl_rd, _("항목","Factor"): _mf_rd, "Weight": _w_rd})
                                if _radar_rows:
                                    _radar_df_v3 = pd.DataFrame(_radar_rows)
                                    _cats_rd = _radar_df_v3[_("항목","Factor")].unique().tolist()
                                    _fig_rd = go.Figure()
                                    _colors_rd = ["#4F81BD","#C0504D","#9BBB59","#8064A2","#F79646"]
                                    for _i_rd, _grp_rdn in enumerate(_radar_df_v3[_("그룹","Group")].unique()):
                                        _g_rd = _radar_df_v3[_radar_df_v3[_("그룹","Group")]==_grp_rdn]
                                        _vals_rd = [_g_rd[_g_rd[_("항목","Factor")]==c]["Weight"].values[0] if len(_g_rd[_g_rd[_("항목","Factor")]==c])>0 else 0 for c in _cats_rd]
                                        _vals_cl = _vals_rd + [_vals_rd[0]]
                                        _cats_cl = _cats_rd + [_cats_rd[0]]
                                        _fig_rd.add_trace(go.Scatterpolar(r=_vals_cl, theta=_cats_cl, fill="toself", name=_grp_rdn, line_color=_colors_rd[_i_rd % len(_colors_rd)], opacity=0.7))
                                    _fig_rd.update_layout(
                                        polar=dict(radialaxis=dict(visible=True, range=[0, max(0.01, _radar_df_v3["Weight"].max()*1.2)])),
                                        showlegend=True,
                                        title=_("그룹별 대분류 중요도 패턴", "Main Criteria Importance Pattern by Group"),
                                        height=450
                                    )
                                    st.plotly_chart(_fig_rd, use_container_width=True)

                        # ─── Tab 5: 결과 다운로드 ────────────────────────────────────────
                        with tab3v5:
                            st.markdown(_("###  3계층 AHP 종합분석 결과 다운로드",
                                          "### 📑 Download 3-Tier AHP Comprehensive Analysis Results"))
                            st.download_button(
                                label=_("📥 3계층 AHP 종합분석 결과 다운로드 (.xlsx)", "📥 Download 3-Tier AHP Results (.xlsx)"),
                                data=output_res_v3,
                                file_name="3Tier_AHP_Result.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                type="primary",
                                use_container_width=True
                            )
                            st.info(_("📋 엑셀 파일에는 종합분석, 그룹비교, 계층별 상세행렬, CR 분포 등 전체 분석 결과가 포함됩니다.",
                                      "📋 The Excel file contains all results: comprehensive summary, group comparison, detailed matrices per tier, and CR distribution."))

                    else:
                    
                        with st.spinner(_("계층 분석 수행 중...", "Performing Analytic Hierarchy Process (AHP)...")):
                            # [2026-10-19] 최종 방어선: 등급별 표본 수 제한을 분석 직전에 재적용
                            df_main = apply_sample_limit(df_main, source_label="2계층 분석")
                            sub_dfs = {k: apply_sample_limit(v) for k, v in sub_dfs.items()}
                            # 1. 메인 시트 분석 시도
                            try:
                                main_results_df, main_factors, main_excluded, main_excluded_df = process_single_sheet(
                                    df_main, cr_threshold, max_iter_val, learning_rate, mean_method, ahp_method
                                )
                                
                                # [수정] F1..Fn 폴백 감지 시 설문 설정의 실제 요인명으로 교체
                                import re as _re
                                _stored_main = st.session_state.get("ahp_main_criteria", [])
                                if (_stored_main and len(_stored_main) == len(main_factors)
                                        and all(_re.match(r'^F\d+$', str(f)) for f in main_factors)):
                                    _rename_w = {f"Weight_F{i+1}": f"Weight_{_stored_main[i]}" for i in range(len(_stored_main))}
                                    main_results_df = main_results_df.rename(columns=_rename_w)
                                    main_factors = _stored_main
                                    # Matrix_Object 컬럼이 있으면 Weight 컬럼 순서도 보정
                                    if "Matrix_Object" in main_results_df.columns:
                                        pass  # Matrix_Object는 이름 무관, 가중치만 교체됨
                            except Exception as e:
                                st.error(_("❌ [메인 시트] 분석 중 오류가 발생했습니다.", "❌ Error occurred during [Main Criteria] analysis."))
                                with st.expander(_("💡 이유 및 해결 방법 보기", "💡 View Reason & Solution"), expanded=True):
                                    st.markdown(_(f"""
                                    **원인:** 메인 시트의 데이터 구조가 올바르지 않거나 읽을 수 있는 유효 데이터가 없습니다. (Error: {e})
                                    **해결 방법:**
                                    1. 엑셀의 첫 번째 시트 이름이 `Main_Criteria`인지 확인하세요.
                                    2. ID와 Type 열 다음에 쌍대비교 데이터가 올바르게 입력되었는지 확인하세요.
                                    3. 빈 행이 포함되어 있다면 삭제 후 다시 시도하세요.
                                    """,
                                    f"""
                                    **Cause:** The structure of the main sheet is incorrect or contains no readable valid data. (Error: {e})
                                    **Solution:**
                                    1. Ensure that the first sheet name in Excel is `Main_Criteria`.
                                    2. Verify that pair-wise comparison data is correctly input after the 'ID' and 'Type' columns.
                                    3. If empty rows are included, delete them and try again.
                                    """))
                                tab1_main_col.__exit__(None, None, None)
                                st.stop()

                            # [방어 코드] 메인 결과 충분성 체크
                            if main_results_df.empty or len(main_results_df) < 1:
                                st.error(_(f"⚠️ 분석 불가: 메인 기준 유효 응답자가 부족합니다. (현재 {len(main_results_df)}명)",
                                           f"⚠️ Cannot Analyze: Insufficient valid respondents for Main Criteria. (Current: {len(main_results_df)} respondents)"))
                                with st.expander(_("💡 이유 및 해결 방법 보기", "💡 View Reason & Solution"), expanded=True):
                                    st.markdown(_(f"""
                                    **원인:** 모든 응답자의 일관성 비율(CR)이 임계치({cr_threshold})를 초과하여 보정 후에도 수렴하지 못했습니다.
                                    **해결 방법:**
                                    1. 왼쪽 사이드바에서 **'일관성 비율(CR) 임계값'**을 0.15 또는 0.2로 완화해 보세요.
                                    2. **'보정 강도(Learning Rate)'**를 0.7 이상으로 높여보세요.
                                    3. **'최대 보정 반복 횟수'**를 500회로 설정했는지 확인하세요.
                                    """,
                                    f"""
                                    **Cause:** The Consistency Ratio (CR) of all respondents exceeded the threshold ({cr_threshold}) and could not converge even after correction.
                                    **Solution:**
                                    1. Loosen the **'Consistency Ratio (CR) Threshold'** to 0.15 or 0.2 in the left sidebar.
                                    2. Increase the **'Correction Intensity (Learning Rate)'** to 0.7 or higher.
                                    3. Ensure **'Max Correction Iterations'** is set to 500.
                                    """))
                                tab1_main_col.__exit__(None, None, None)
                                st.stop()

                            # --- Uploaded Data Matrix for CR Distortion Verification ---
                            if 'Orig_Matrix_Object' in main_results_df.columns:
                                orig_mats = np.stack(main_results_df['Orig_Matrix_Object'].values)
                                # Use geometric mean to aggregate the raw matrices of all respondents
                                agg_orig_matrix = np.exp(np.mean(np.log(orig_mats), axis=0))
                                st.session_state.uploaded_matrix = agg_orig_matrix
                            # -----------------------------------------------------------

                            # 2. 하위 시트 분석 및 저장
                            sub_results_storage = {}
                            total_excl_df_list = [main_excluded_df]
                    
                            is_single_sheet = (len(sheet_names) == 1)
                    
                            if is_single_sheet:
                                for parent_factor in main_factors:
                                    # 1단계 분석인 경우 (하위 시트가 없음), 
                                    # 하위 가중치 1.0을 가지는 더미 데이터를 자동으로 생성하여 연산을 마칩니다.
                                    dummy_list = []
                                    for idx, row in main_results_df.iterrows():
                                        dummy_list.append({
                                            "ID": row['ID'],
                                            "Type": row['Type'],
                                            "Original_CI": 0.0,
                                            "Original_CR": 0.0,
                                            "Final_CI": 0.0,
                                            "Final_CR": 0.0,
                                            "Iterations": 0,
                                            "Corrected": False,
                                            "Matrix_Object": np.array([[1.0]]),
                                            f"Weight_{parent_factor}": 1.0
                                        })
                                    dummy_df = pd.DataFrame(dummy_list)
                                    sub_results_storage[parent_factor] = {
                                        'weights': np.array([1.0]),
                                        'factors': [parent_factor],
                                        'cr': 0.0,
                                        'ci': 0.0,
                                        'df': dummy_df,
                                        'group_matrix': np.array([[1.0]]),
                                        'group_cr': 0.0,
                                        'group_ci': 0.0
                                    }
                            else:
                                # [수정] infer_factors_from_columns 폴백(F1,F2...) 감지 시 서브시트 이름으로 보정
                                import re as _re
                                _fallback_pattern = _re.compile(r'^F\d+$')
                                _all_fallback = all(_fallback_pattern.match(str(f)) for f in main_factors)
                                _sub_sheet_names = [sn for sn in sheet_names[1:] if not sn.startswith('__') and sn != 'Main_Criteria']
                                if _all_fallback and len(_sub_sheet_names) == len(main_factors):
                                    # 순서 기반 복원: 서브시트 순서를 실제 요인명으로 사용
                                    main_factors = _sub_sheet_names[:len(main_factors)]
                                    # main_results_df의 Weight_ 컬럼도 갱신
                                    rename_map = {f"Weight_F{i+1}": f"Weight_{main_factors[i]}" for i in range(len(main_factors))}
                                    main_results_df = main_results_df.rename(columns=rename_map)

                                for parent_factor in main_factors:
                                    # 대분류 항목명과 일치하는 시트명 찾기 (대소문자, 공백 무시 및 31자 제한 고려)
                                    target_name = parent_factor.strip().lower()
                                    target_name_31 = parent_factor[:31].strip().lower()
                            
                                    matched_sheet_name = None
                                    for sn in sheet_names[1:]:
                                        sn_clean = sn.strip().lower()
                                        if sn_clean == target_name or sn_clean == target_name_31:
                                            matched_sheet_name = sn
                                            break
                            
                                    if matched_sheet_name is None:
                                        # [수정] 하위 요인이 없는 대분류(리프 노드)이면 더미 처리 후 계속
                                        # - sheet_names에 해당 시트가 없으면 하위 요인 없음으로 간주
                                        # - 가중치 1.0 더미로 처리 (GW = 대분류 가중치 × 1.0)
                                        _stored_subs_map_chk = st.session_state.get("ahp_sub_criteria_map", {})
                                        _has_subs = (parent_factor in _stored_subs_map_chk and
                                                     len(_stored_subs_map_chk.get(parent_factor, [])) >= 2)
                                        
                                        if not _has_subs:
                                            # 하위 요인 없는 대분류 → 리프 노드 더미
                                            _dummy_list = []
                                            for _idx, _row in main_results_df.iterrows():
                                                _dummy_list.append({
                                                    "ID": _row['ID'],
                                                    "Type": _row['Type'],
                                                    "Original_CI": 0.0, "Original_CR": 0.0,
                                                    "Final_CI": 0.0, "Final_CR": 0.0,
                                                    "Iterations": 0, "Corrected": False,
                                                    "Matrix_Object": np.array([[1.0]]),
                                                    f"Weight_{parent_factor}": 1.0
                                                })
                                            _dummy_df = pd.DataFrame(_dummy_list)
                                            sub_results_storage[parent_factor] = {
                                                'weights': np.array([1.0]),
                                                'factors': [parent_factor],
                                                'cr': 0.0, 'ci': 0.0,
                                                'df': _dummy_df,
                                                'group_matrix': np.array([[1.0]]),
                                                'group_cr': 0.0, 'group_ci': 0.0,
                                                'group_Si': None
                                            }
                                            continue  # 다음 대분류로
                                        else:
                                            # 하위 요인이 있어야 하는데 시트가 없음 → 실제 에러
                                            available = ", ".join(f"'{s}'" for s in sheet_names[1:])
                                            st.error(_(f"❌ [세부 시트: {parent_factor}] 시트를 찾을 수 없습니다.", f"❌ [Detailed Sheet: {parent_factor}] Sheet not found."))
                                            with st.expander(_("💡 이유 및 해결 방법 보기", "💡 View Reason & Solution"), expanded=True):
                                                st.markdown(_(f"""
                                                **원인:** 메인 기준 시트에서 도출된 대분류 항목 **'{parent_factor}'**에 대응하는 세부 설문 응답 시트가 존재하지 않거나 시트 이름이 다릅니다.

                                                📋 **파일 내 실제 시트 목록:** {available}

                                                **해결 방법:**
                                                1. 메인 기준 시트(첫 번째 시트)의 **컬럼 이름**이 `대분류A_대분류B` 형식인지 확인하세요.
                                                2. 컬럼명에 밑줄(`_`)이 포함된 요인명이 있다면 공백이나 다른 구분자로 변경하세요.
                                                3. 업로드한 파일 내 서브시트 이름이 메인 시트 컬럼에서 추출된 요인명과 정확히 일치하는지 확인하세요.
                                                """,
                                                f"""
                                                **Cause:** The detailed survey response sheet for **'{parent_factor}'** does not exist or has a different name.

                                                📋 **Available sheets in file:** {available}

                                                **Solution:**
                                                1. Check that column names in the main criteria sheet follow the `FactorA_FactorB` format.
                                                2. If factor names contain underscores (`_`), replace them with spaces or other separators.
                                                3. Ensure sub-sheet names exactly match the factor names extracted from the main sheet columns.
                                                """))
                                            tab1_main_col.__exit__(None, None, None)
                                            st.stop()

                            
                                    try:
                                        if data_source == _("🌐 배포된 온라인 설문 데이터 연동", "🌐 Connect Online Survey Data"):
                                            df_sub = st.session_state["ahp_sub_dfs"][matched_sheet_name]
                                        else:
                                            df_sub = pd.read_excel(uploaded_file, sheet_name=matched_sheet_name)
                                            df_sub = preprocess_uploaded_df(df_sub)
                                        
                                        sub_res_df, sub_facts, sub_excl, sub_excl_df = process_single_sheet(
                                            df_sub, cr_threshold, max_iter_val, learning_rate, mean_method, ahp_method
                                        )
                                        
                                        # [수정] sub_facts가 F1..Fn 폴백이면 설문 설정 요인명으로 교체
                                        _stored_subs_map = st.session_state.get("ahp_sub_criteria_map", {})
                                        _real_subs = _stored_subs_map.get(parent_factor, [])
                                        if (not _real_subs and parent_factor in _stored_subs_map):
                                            _real_subs = _stored_subs_map[parent_factor]
                                        if (_real_subs and len(_real_subs) == len(sub_facts)
                                                and all(_re.match(r'^F\d+$', str(f)) for f in sub_facts)):
                                            _rename_sw = {f"Weight_F{i+1}": f"Weight_{_real_subs[i]}" for i in range(len(_real_subs))}
                                            sub_res_df = sub_res_df.rename(columns=_rename_sw)
                                            sub_facts = _real_subs
                                
                                        if sub_res_df.empty:
                                            raise ValueError(f"'{matched_sheet_name}' 시트에 유효한 분석 데이터가 없습니다.")
                                    
                                        # 통계 계산 로직
                                        sub_w_cols = [f"Weight_{f}" for f in sub_facts]
                                        sub_matrices = np.stack(sub_res_df['Matrix_Object'].values)
                                        sub_group_matrix = np.mean(sub_matrices, axis=0) if mean_method == 'arithmetic' else gmean(sub_matrices, axis=0)
                                        sub_grp_cr, sub_grp_ci, _not_used_lambda = calculate_consistency(sub_group_matrix, method=mean_method)
                                
                                        if ahp_method == 'fuzzy':
                                            sw_vals, sub_group_Si = fuzzy_ahp_analysis(sub_group_matrix)
                                            group_sub_w = pd.Series(sw_vals, index=sub_w_cols)
                                        else:
                                            sub_group_Si = None
                                            group_sub_w = sub_res_df[sub_w_cols].mean(axis=0) if mean_method == 'arithmetic' else gmean(sub_res_df[sub_w_cols].values, axis=0)
                                            group_sub_w = group_sub_w / group_sub_w.sum()
                                
                                        sub_results_storage[parent_factor] = {
                                            'weights': group_sub_w, 'factors': sub_facts, 'cr': sub_res_df['Final_CR'].mean(),
                                            'ci': sub_res_df['Final_CI'].mean(),
                                            'df': sub_res_df, 'group_matrix': sub_group_matrix, 'group_cr': sub_grp_cr,
                                            'group_ci': sub_grp_ci, 'group_Si': sub_group_Si
                                        }
                                        if not sub_excl_df.empty:
                                            sub_excl_df['Sheet'] = parent_factor
                                            total_excl_df_list.append(sub_excl_df)
                                    
                                    except Exception as e:
                                        st.error(_(f"❌ [세부 시트: {matched_sheet_name}] 분석 중 오류가 발생했습니다.", f"❌ Error occurred during [Detailed Sheet: {matched_sheet_name}] analysis."))
                                        with st.expander(_("💡 이유 및 해결 방법 보기", "💡 View Reason & Solution"), expanded=True):
                                            st.markdown(_(f"""
                                            **원인:** 시트 내부의 데이터 구조가 올바르지 않거나, 해당 시트의 응답자들이 모두 일관성 기준을 통과하지 못했습니다. (Error: {e})
                                            **해결 방법:**
                                            1. 해당 세부 시트의 데이터에 빈 칸이나 문자가 섞여 있는지 확인하세요.
                                            2. CR 임계값을 높여서 다시 분석해 보세요.
                                            """,
                                            f"""
                                            **Cause:** The internal data structure of the sheet is incorrect, or all respondents for this sheet failed to pass the consistency ratio criteria. (Error: {e})
                                            **Solution:**
                                            1. Check if there are empty cells or text mixed in the data of the detailed sheet.
                                            2. Try analyzing again with a higher CR threshold.
                                            """))
                                        tab1_main_col.__exit__(None, None, None)
                                        st.stop()


                            main_sig_df = calculate_pairwise_ttest(main_results_df, main_factors)
                            main_weight_cols = [f"Weight_{f}" for f in main_factors]
                    
                            main_matrices = np.stack(main_results_df['Matrix_Object'].values)
                            main_group_matrix = np.mean(main_matrices, axis=0) if mean_method == 'arithmetic' else gmean(main_matrices, axis=0)
                            main_grp_cr, main_grp_ci, _not_used_lambda = calculate_consistency(main_group_matrix, mean_method)
                    
                            if ahp_method == 'fuzzy':
                                mw_vals, main_group_Si = fuzzy_ahp_analysis(main_group_matrix)
                                group_main_weights = pd.Series(mw_vals, index=main_weight_cols)
                            else:
                                main_group_Si = None
                                if mean_method == 'arithmetic':
                                    group_main_weights = main_results_df[main_weight_cols].mean(axis=0)
                                else:
                                    group_main_weights = gmean(main_results_df[main_weight_cols].values, axis=0)
                                group_main_weights = group_main_weights / group_main_weights.sum()
                    
                            main_cr_final_avg = main_results_df['Final_CR'].mean()
                    
                            # --- 다중 인구통계 변수 처리 UI ---
                            tier = get_current_tier()
                            demo_cols = [c for c in main_results_df.columns if str(c).strip().lower() == 'type' or str(c).strip().lower().startswith('type ')]
                            if len(demo_cols) > 1 and tier in ['Standard', 'Pro']:
                                selected_demo = st.selectbox(_("📊 교차분석 그룹 기준 변수 선택", "📊 Select Grouping Variable for Analysis"), demo_cols)
                                main_results_df['Type'] = main_results_df[selected_demo]
                                for mf in main_factors:
                                    sub_results_storage[mf]['df']['Type'] = sub_results_storage[mf]['df'][selected_demo]
                            elif len(demo_cols) > 0:
                                main_results_df['Type'] = main_results_df[demo_cols[0]]
                                for mf in main_factors:
                                    sub_results_storage[mf]['df']['Type'] = sub_results_storage[mf]['df'][demo_cols[0]]
                            else:
                                main_results_df['Type'] = 'All'
                                for mf in main_factors:
                                    sub_results_storage[mf]['df']['Type'] = 'All'

                            indiv_global_data = []
                            all_ids = main_results_df['ID'].unique()
                    
                            for uid in all_ids:
                                u_main = main_results_df[main_results_df['ID'] == uid]
                                if u_main.empty: continue
                                u_type = u_main['Type'].values[0]
                                for mf in main_factors:
                                    m_w = u_main[f"Weight_{mf}"].values[0]
                                    s_row_df = sub_results_storage[mf]['df']
                                    u_sub = s_row_df[s_row_df['ID'] == uid]
                                    if u_sub.empty: continue
                                    for sf in sub_results_storage[mf]['factors']:
                                        s_w = u_sub[f"Weight_{sf}"].values[0]
                                        indiv_global_data.append({
                                            "ID": uid, "Type": str(u_type), "Factor": sf, "Global_Weight": m_w * s_w,
                                            "Original_CR": u_main['Original_CR'].values[0],
                                            "Final_CR": u_main['Final_CR'].values[0]
                                        })
                            indiv_df = pd.DataFrame(indiv_global_data)
                    
                            anova_df = pd.DataFrame()
                            if not indiv_df.empty and len(indiv_df['Type'].unique()) >= 2:
                                anova_df = calculate_anova_and_posthoc(indiv_df)

                            summary_rows = []
                            for idx, main_f in enumerate(main_factors):
                                m_weight = group_main_weights.iloc[idx] if isinstance(group_main_weights, pd.Series) else group_main_weights[idx]
                                sub_info = sub_results_storage[main_f]
                                for s_idx, sub_f in enumerate(sub_info['factors']):
                                    s_weight = sub_info['weights'].iloc[s_idx] if isinstance(sub_info['weights'], pd.Series) else sub_info['weights'][s_idx]
                                    global_w = m_weight * s_weight
                                    summary_rows.append({
                                        "대분류": main_f, "대분류 가중치": m_weight, "중분류": sub_f, "중분류 가중치": s_weight,
                                        "Global Weight": global_w, 
                                        "CR(대분류)": main_grp_cr, 
                                        "CI(대분류)": main_grp_ci,
                                        "CR(중분류)": sub_info['group_cr'],
                                        "CI(중분류)": sub_info['group_ci']
                                    })
                    
                            final_df = pd.DataFrame(summary_rows)
                            final_df['Global Rank'] = final_df['Global Weight'].round(3).rank(ascending=False, method='min').astype(int)
                            cols_order = ["대분류", "대분류 가중치", "중분류", "중분류 가중치", "Global Weight", "Global Rank", "CR(대분류)", "CI(대분류)", "CR(중분류)", "CI(중분류)"]
                            final_df = final_df[cols_order]

                            unique_groups = sorted(main_results_df['Type'].astype(str).unique())
                            group_analysis_results = {}
                            group_full_dfs = {} 
                    
                            for grp in unique_groups:
                                grp_main_df = main_results_df[main_results_df['Type'].astype(str) == grp]
                                if grp_main_df.empty: continue
                                g_main_mats = np.stack(grp_main_df['Matrix_Object'].values)
                                g_main_mat_obj = np.mean(g_main_mats, axis=0) if mean_method == 'arithmetic' else gmean(g_main_mats, axis=0)
                                g_main_cr, g_main_ci, _not_used_lambda = calculate_consistency(g_main_mat_obj, method=mean_method)
                        
                                if ahp_method == 'fuzzy':
                                    mw_vals_grp, _unused_Si = fuzzy_ahp_analysis(g_main_mat_obj)
                                    g_main_w = pd.Series(mw_vals_grp, index=main_weight_cols)
                                else:
                                    g_main_w = grp_main_df[main_weight_cols].mean(axis=0) if mean_method == 'arithmetic' else gmean(grp_main_df[main_weight_cols].values, axis=0)
                                    g_main_w = g_main_w / g_main_w.sum()
                        
                                grp_rows = []
                                for idx, main_f in enumerate(main_factors):
                                    m_w = g_main_w.iloc[idx] if isinstance(g_main_w, pd.Series) else g_main_w[idx]
                                    full_sub_df = sub_results_storage[main_f]['df']
                                    grp_sub_df = full_sub_df[full_sub_df['Type'].astype(str) == grp]
                                    sub_facts = sub_results_storage[main_f]['factors']
                                    if grp_sub_df.empty: continue
                                    s_w_cols = [f"Weight_{f}" for f in sub_facts]
                                    g_sub_mats = np.stack(grp_sub_df['Matrix_Object'].values)
                                    g_sub_mat_obj = np.mean(g_sub_mats, axis=0) if mean_method == 'arithmetic' else gmean(g_sub_mats, axis=0)
                                    g_sub_cr, g_sub_ci, _not_used_lambda = calculate_consistency(g_sub_mat_obj, method=mean_method)
                            
                                    if ahp_method == 'fuzzy':
                                        sw_vals_grp, _unused_Si = fuzzy_ahp_analysis(g_sub_mat_obj)
                                        g_sub_w = pd.Series(sw_vals_grp, index=s_w_cols)
                                    else:
                                        g_sub_w = grp_sub_df[s_w_cols].mean(axis=0) if mean_method == 'arithmetic' else gmean(grp_sub_df[s_w_cols].values, axis=0)
                                        g_sub_w = g_sub_w / g_sub_w.sum()
                                
                                    for s_idx, sf in enumerate(sub_facts):
                                        s_w_val = g_sub_w.iloc[s_idx] if isinstance(g_sub_w, pd.Series) else g_sub_w[s_idx]
                                        grp_rows.append({
                                            "대분류": main_f, "대분류 가중치": m_w, "중분류": sf, "중분류 가중치": s_w_val,
                                            "Global Weight": m_w * s_w_val, 
                                            "CR(대분류)": g_main_cr, 
                                            "CI(대분류)": g_main_ci,
                                            "CR(중분류)": g_sub_cr, 
                                            "CI(중분류)": g_sub_ci
                                        })
                                g_df = pd.DataFrame(grp_rows)
                                if not g_df.empty:
                                    g_df['Global Rank'] = g_df['Global Weight'].round(3).rank(ascending=False, method='min').astype(int)
                                    group_full_dfs[grp] = g_df[cols_order]
                                    group_analysis_results[grp] = group_full_dfs[grp][['대분류', '중분류', 'Global Weight']]

                            comparison_df = final_df[['대분류', '중분류', 'Global Weight']].copy()
                            comparison_df.rename(columns={'Global Weight': '종합평균(Overall)'}, inplace=True)
                            for grp, df_res in group_analysis_results.items():
                                temp_df = df_res.rename(columns={'Global Weight': grp})
                                comparison_df = comparison_df.merge(temp_df, on=['대분류', '중분류'], how='left')

                            output_res = io.BytesIO()
                            with pd.ExcelWriter(output_res, engine='xlsxwriter') as writer:
                                workbook = writer.book
                            
                                # [신규 추가] 인구통계 결과 엑셀 시트 출력
                                if "demo_df" in st.session_state and st.session_state["demo_df"] is not None:
                                    demo_summary_df = generate_demographics_summary(st.session_state["demo_df"])
                                    if demo_summary_df is not None:
                                        demo_summary_df.to_excel(writer, sheet_name='Result_Demographics', index=False)
                                        # Result_Demographics 엑셀 서식 적용
                                        ws_demo = writer.sheets['Result_Demographics']
                                        header_format_demo = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'bg_color': '#4F81BD', 'font_color': '#FFFFFF', 'border': 1})
                                        body_format_demo = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'border': 1})
                                        pct_format_demo = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'border': 1, 'num_format': '0.0'})
                                        total_format_demo = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'bg_color': '#D3D3D3', 'border': 1})
                                        total_pct_format_demo = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'bg_color': '#D3D3D3', 'border': 1, 'num_format': '0.0'})
                                        for col_num, value in enumerate(demo_summary_df.columns.values):
                                            ws_demo.write(0, col_num, value, header_format_demo)
                                        # 항목별로 그룹화하여 합계 행 추가
                                        _demo_field_col = demo_summary_df.columns[0]
                                        _demo_freq_col = demo_summary_df.columns[2]
                                        _demo_pct_col = demo_summary_df.columns[3]
                                        _excel_row = 1
                                        _prev_field = None
                                        _group_pct_sum = 0.0
                                        for _idx in range(len(demo_summary_df)):
                                            _field = demo_summary_df.iloc[_idx, 0]
                                            _pct = demo_summary_df.iloc[_idx, 3]
                                            # 새 항목 시작 시 이전 그룹의 합계 행 출력
                                            if _prev_field is not None and _field != _prev_field:
                                                ws_demo.write(_excel_row, 0, _prev_field, total_format_demo)
                                                ws_demo.write(_excel_row, 1, "합계", total_format_demo)
                                                ws_demo.write(_excel_row, 2, "-", total_format_demo)
                                                ws_demo.write(_excel_row, 3, _group_pct_sum, total_pct_format_demo)
                                                _excel_row += 1
                                                _group_pct_sum = 0.0
                                            # 데이터 행 출력 (비율 컬럼은 소수점 1자리 표시)
                                            for col in range(len(demo_summary_df.columns)):
                                                _val = demo_summary_df.iloc[_idx, col]
                                                if col == 3:
                                                    ws_demo.write(_excel_row, col, _val, pct_format_demo)
                                                else:
                                                    ws_demo.write(_excel_row, col, _val, body_format_demo)
                                            _excel_row += 1
                                            _group_pct_sum += _pct if isinstance(_pct, (int, float)) else 0
                                            _prev_field = _field
                                        # 마지막 그룹의 합계 행 출력
                                        if _prev_field is not None:
                                            ws_demo.write(_excel_row, 0, _prev_field, total_format_demo)
                                            ws_demo.write(_excel_row, 1, "합계", total_format_demo)
                                            ws_demo.write(_excel_row, 2, "-", total_format_demo)
                                            ws_demo.write(_excel_row, 3, _group_pct_sum, total_pct_format_demo)
                                            _excel_row += 1
                                        ws_demo.set_column('A:A', 30)
                                        ws_demo.set_column('B:D', 20)
                            
                                formats = {
                                    'header': workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'bg_color': '#000000', 'font_color': '#FFFFFF', 'border': 1}),
                                    'merge': workbook.add_format({'align': 'center', 'valign': 'vcenter', 'border': 1}),
                                    'body': workbook.add_format({'align': 'center', 'valign': 'vcenter', 'border': 1}),
                                    'num': workbook.add_format({'align': 'center', 'valign': 'vcenter', 'border': 1, 'num_format': '0.000'}),
                                    'sum_row': workbook.add_format({'bold': True, 'bg_color': '#D3D3D3', 'align': 'center', 'valign': 'vcenter', 'border': 1}),
                                    'sum_val': workbook.add_format({'num_format': '0', 'bg_color': '#D3D3D3', 'border': 1, 'align':'center'}),
                                    'num_sum': workbook.add_format({'num_format': '0.000', 'bg_color': '#D3D3D3', 'border': 1, 'align':'center'}),
                                    'yellow': workbook.add_format({'bg_color': 'yellow', 'border': 1, 'align': 'center', 'num_format': '0.000'})
                                }
                                border_fmt = workbook.add_format({'border': 1})
                                fmt_float_no_border = workbook.add_format({'num_format': '0.000', 'align': 'center', 'valign': 'vcenter', 'border': 1})
                                fmt_diagonal = workbook.add_format({'num_format': '0', 'align': 'center', 'valign': 'vcenter', 'bg_color': '#E7E6E6', 'border': 1})

                                total_excluded_df = pd.concat(total_excl_df_list, ignore_index=True)
                                sheet_name_comp = _('종합분석', 'Comprehensive Analysis')
                                current_row_ws = write_custom_ahp_table(writer, sheet_name_comp, final_df, _("1) 전체_종합결과", "1) Overall Aggregated Results"), 1, formats, excluded_df=total_excluded_df)
                                for grp in unique_groups:
                                    if grp in group_full_dfs:
                                        current_row_ws = write_custom_ahp_table(writer, sheet_name_comp, group_full_dfs[grp], _(f"▶ [그룹: {grp}] 분석 결과", f"▶ [Group: {grp}] Analysis Results"), current_row_ws, formats)

                                if len(unique_groups) >= 1:
                                    ws_comp = workbook.add_worksheet('Group_Comparison')
                                    writer.sheets['Group_Comparison'] = ws_comp
                                    s_row_cp = 1
                                    ws_comp.write_string(s_row_cp, 0, _("그룹 간 비교(일원배치 분산분석: ANOVA)", "Group Comparison (One-way ANOVA)"), workbook.add_format({'bold': True, 'font_size': 12}))
                                    s_row_cp += 1
                            
                                    tier = get_current_tier()
                                    if tier not in ['Standard', 'Pro']:
                                        ws_comp.write_string(s_row_cp, 0, _("🔒 통계 검정 결과(ANOVA/사후검정)는 Standard 등급 이상 정식 사용자에게만 제공됩니다.", "🔒 Statistical test results (ANOVA/Post-hoc) are exclusive to Standard and Pro Tier users."), workbook.add_format({'italic': True, 'font_color': '#FF0000', 'font_name': 'NanumGothic'}))
                                        s_row_cp += 1
                            
                                    if tier in ['Standard', 'Pro'] and not anova_df.empty:
                                        anova_for_merge = anova_df.rename(columns={'요인': '중분류'})
                                        integrated_df = comparison_df.merge(anova_for_merge, on='중분류', how='left')
                                    else:
                                        integrated_df = comparison_df
                            
                                    # English renaming logic for columns & significance
                                    if st.session_state.get('lang', 'ko') == 'en':
                                        rename_dict = {
                                            '대분류': 'Main Criteria',
                                            '중분류': 'Sub-Criteria',
                                            '종합평균(Overall)': 'Overall',
                                            'F-값': 'F-Value',
                                            'P-Value': 'P-Value',
                                            '유의성': 'Significance',
                                            '사후검정(Tukey HSD)': 'Post-hoc (Tukey HSD)'
                                        }
                                        integrated_df_excel = integrated_df.copy()
                                        integrated_df_excel.rename(columns=rename_dict, inplace=True)
                                        if 'Significance' in integrated_df_excel.columns:
                                            integrated_df_excel['Significance'] = integrated_df_excel['Significance'].replace({
                                                '유의함': 'Significant',
                                                '유의하지 않음': 'Not Significant'
                                            })
                                        if 'Post-hoc (Tukey HSD)' in integrated_df_excel.columns:
                                            integrated_df_excel['Post-hoc (Tukey HSD)'] = integrated_df_excel['Post-hoc (Tukey HSD)'].replace({
                                                '집단 간 구체적 차이 발견 못함': 'No specific difference found',
                                                '계산 오류': 'Calculation Error'
                                            })
                                            integrated_df_excel['Post-hoc (Tukey HSD)'] = integrated_df_excel['Post-hoc (Tukey HSD)'].apply(
                                                lambda x: x.replace(" 차이 있음", " Diff Exists") if isinstance(x, str) else x
                                            )
                                    else:
                                        integrated_df_excel = integrated_df

                                    integrated_df_excel.to_excel(writer, sheet_name='Group_Comparison', startrow=s_row_cp, index=False)
                                    add_borders_to_data(ws_comp, s_row_cp, 0, integrated_df_excel, border_fmt)


                            
                                    num_format_3 = workbook.add_format({'num_format': '0.000', 'border': 1, 'align': 'center'})
                                    for r in range(len(integrated_df_excel)):
                                        for c in range(1, len(integrated_df_excel.columns)):
                                            val = integrated_df_excel.iloc[r, c]
                                            if pd.notnull(val) and isinstance(val, (int, float)):
                                                ws_comp.write_number(s_row_cp + 1 + r, c, val, num_format_3)
                                            elif pd.notnull(val):
                                                ws_comp.write(s_row_cp + 1 + r, c, val, border_fmt)

                                    guide_start_row = s_row_cp + len(integrated_df_excel) + 3
                                    bold_fmt = workbook.add_format({'bold': True, 'font_size': 11, 'valign': 'vcenter', 'align': 'left', 'bg_color': '#F2F2F2', 'border': 1})
                                    text_fmt = workbook.add_format({'font_size': 10, 'text_wrap': True, 'valign': 'top', 'align': 'left', 'border': 1})
                                    ws_comp.set_column('A:G', 20) 
                            
                                    if tier in ['Standard', 'Pro']:
                                        comp_title = _("※ 그룹 간 중요도의 차이가 있지만 통계적으로 유의하지 않게 나타나는 이유",
                                                       "※ Reasons why group differences are not statistically significant despite variation in priorities")
                                        ws_comp.merge_range(guide_start_row, 0, guide_start_row, 6, comp_title, bold_fmt)

                                    guide_content_ko = [
                                        ("1. 그룹 내 편차(분산)가 너무 큰 경우", "ANOVA는 '그룹 간의 차이'와 '그룹 내의 차이'를 비교합니다.\n\n■ 원리: 그룹 간 평균 차이가 크더라도, 각 그룹 내부 데이터들이 서로 들쭉날쭉(분산이 큼)하다면 통계적으로는 '이 차이가 우연히 발생했을 가능성이 높다'고 판단합니다."),
                                        ("2. 표본 크기(Sample Size)의 부족", "통계적 유의성은 표본의 수에 매우 민감합니다.\n\n■ 현상: 각 그룹의 데이터 개수(표본수)가 너무 적다면 통계적 힘(Power)이 부족하여 유의미한 차이를 찾아내지 못합니다."),
                                        ("3. 데이터의 단위(Scale)와 변동성", "표에 나타난 수치들이 대부분 매우 작은 소수점 단위입니다. 실제 계산 과정에서 표준오차 범위 내에 있다면 통계적으로는 측정 오차 범위 내의 흔들림으로 간주됩니다.")
                                    ]
                            
                                    guide_content_en = [
                                        ("1. Within-Group Variance is Too Large", "ANOVA compares variance between groups against variance within groups.\n\n■ Principle: Even if the mean difference between groups is large, if individual responses within each group are highly scattered (large variance), statistics will determine that the difference is likely due to chance."),
                                        ("2. Insufficient Sample Size", "Statistical significance is highly sensitive to the number of samples.\n\n■ Phenomenon: If the number of data points (sample size) in each group is too small, statistical power is insufficient to detect significant differences."),
                                        ("3. Data Scale and Volatility", "The values in the table are mostly very small decimals. If they fall within the range of standard error, they are considered as minor fluctuations within the measurement error range.")
                                    ]
                            
                                    guide_content = (guide_content_en if st.session_state.get('lang', 'ko') == 'en' else guide_content_ko) if tier in ['Standard', 'Pro'] else []

                                    current_row_comp = guide_start_row + 1
                                    for title, body in guide_content:
                                        ws_comp.set_row(current_row_comp, 25)
                                        ws_comp.merge_range(current_row_comp, 0, current_row_comp, 6, title, bold_fmt)
                                        ws_comp.set_row(current_row_comp + 1, 80)
                                        ws_comp.merge_range(current_row_comp + 1, 0, current_row_comp + 1, 6, body, text_fmt)
                                        current_row_comp += 2


                                # [2026-10-05 추가] 전문가 의견 일치도 시트 (대/중/세분류 통합)
                                _fmt_title = workbook.add_format({'bold': True, 'font_size': 14, 'font_color': '#1F3864'})
                                _fmt_level = workbook.add_format({'bold': True, 'font_size': 13, 'bg_color': '#1F3864', 'font_color': '#FFFFFF', 'border': 1, 'align': 'center', 'valign': 'vcenter'})
                                _fmt_section = workbook.add_format({'bold': True, 'font_size': 12, 'bg_color': '#D9D9D9', 'border': 1, 'align': 'center', 'valign': 'vcenter'})
                                _fmt_header = workbook.add_format({'bold': True, 'bg_color': '#1F3864', 'font_color': '#FFFFFF', 'border': 1, 'align': 'center', 'valign': 'vcenter', 'text_wrap': True})
                                _fmt_body = workbook.add_format({'border': 1, 'align': 'center', 'valign': 'vcenter'})
                                _fmt_num = workbook.add_format({'border': 1, 'align': 'center', 'valign': 'vcenter', 'num_format': '0.000'})
                                _fmt_pct = workbook.add_format({'border': 1, 'align': 'center', 'valign': 'vcenter', 'num_format': '0.0%'})
                                _fmt_interp = workbook.add_format({'text_wrap': True, 'valign': 'top', 'align': 'left', 'font_size': 10})
                                _fmt_criteria_h = workbook.add_format({'bold': True, 'bg_color': '#EAEFF7', 'border': 1, 'align': 'center'})
                                _fmt_criteria_b = workbook.add_format({'border': 1, 'align': 'center', 'font_size': 10})
                                _fmt_src = workbook.add_format({'italic': True, 'font_size': 9, 'font_color': '#595959', 'text_wrap': True, 'valign': 'top'})
                                _fmt_high = workbook.add_format({'border': 1, 'align': 'center', 'bg_color': '#C6EFCE', 'font_color': '#006100'})
                                _fmt_mid = workbook.add_format({'border': 1, 'align': 'center', 'bg_color': '#FFEB9C', 'font_color': '#9C6500'})
                                _fmt_low = workbook.add_format({'border': 1, 'align': 'center', 'bg_color': '#FFC7CE', 'font_color': '#9C0006'})

                                def _write_consensus_block(ws_con, _cr, _consensus, _F):
                                    """일치도 4개 섹션을 시트에 기록. _cr(다음 행)을 반환."""
                                    # 섹션 1: 항목별 일치도
                                    ws_con.merge_range(_cr, 0, _cr, 7, "1. 항목별 가중치 일치도", _F['section'])
                                    _cr += 1
                                    for _ci, _h in enumerate(["평가기준", "평균 가중치", "표준편차", "변이계수(CV)", "최고값", "최저값", "범위", "일치도 판정"]):
                                        ws_con.write_string(_cr, _ci, _h, _F['header'])
                                    _cr += 1
                                    for _row in _consensus["summary"]:
                                        ws_con.write_string(_cr, 0, str(_row["평가기준"]), _F['body'])
                                        ws_con.write_number(_cr, 1, _row["평균 가중치"], _F['num'])
                                        ws_con.write_number(_cr, 2, _row["표준편차"], _F['num'])
                                        ws_con.write_number(_cr, 3, _row["변이계수(CV)"], _F['num'])
                                        ws_con.write_number(_cr, 4, _row["최고값"], _F['num'])
                                        ws_con.write_number(_cr, 5, _row["최저값"], _F['num'])
                                        ws_con.write_number(_cr, 6, _row["범위"], _F['num'])
                                        _jf = _F['high'] if _row["일치도 판정"] == "높음" else (_F['mid'] if _row["일치도 판정"] == "보통" else _F['low'])
                                        ws_con.write_string(_cr, 7, _row["일치도 판정"], _jf)
                                        _cr += 1
                                    _cr += 1
                                    ws_con.merge_range(_cr, 0, _cr, 7, f"[해석] {_consensus['s1']}", _F['interp'])
                                    ws_con.set_row(_cr, 30)
                                    _cr += 2
                                    ws_con.merge_range(_cr, 0, _cr, 7, "변이계수(CV) 해석 기준", _F['criteria_h'])
                                    _cr += 1
                                    for _crit, _desc in [("CV < 0.15", "합의 높음"), ("0.15 ≤ CV < 0.30", "보통"), ("CV ≥ 0.30", "의견 분산 (주의)")]:
                                        ws_con.write_string(_cr, 0, _crit, _F['criteria_b'])
                                        ws_con.merge_range(_cr, 1, _cr, 7, _desc, _F['criteria_b'])
                                        _cr += 1
                                    ws_con.merge_range(_cr, 0, _cr, 7, "이론적 근거: 기술통계량(표준편차·변이계수)을 이용한 전문가 의견 분산 측정", _F['src'])
                                    _cr += 2
                                    # 섹션 2: 1위 득표율
                                    ws_con.merge_range(_cr, 0, _cr, 7, "2. 1위 항목 득표율", _F['section'])
                                    _cr += 1
                                    for _ci, _h in enumerate(["순위", "평가기준", "1위 선택 인원", "득표율"]):
                                        ws_con.write_string(_cr, _ci, _h, _F['header'])
                                    _cr += 1
                                    _s2_start = _cr
                                    for _row in _consensus["top_votes"]:
                                        ws_con.write_number(_cr, 0, _row["순위"], _F['body'])
                                        ws_con.write_string(_cr, 1, str(_row["평가기준"]), _F['body'])
                                        ws_con.write_number(_cr, 2, _row["1위 선택 인원"], _F['body'])
                                        ws_con.write_number(_cr, 3, _row["득표율"], _F['pct'])
                                        _cr += 1
                                    ws_con.conditional_format(_s2_start, 3, _cr - 1, 3, {'type': 'data_bar', 'bar_color': '#5B9BD5'})
                                    _cr += 1
                                    ws_con.merge_range(_cr, 0, _cr, 7, f"[해석] {_consensus['s2']}", _F['interp'])
                                    ws_con.set_row(_cr, 30)
                                    _cr += 2
                                    ws_con.merge_range(_cr, 0, _cr, 7, "이론적 근거: 최빈값 기준 합의도 측정 (실무 관행)", _F['src'])
                                    _cr += 2
                                    # 섹션 3: Kendall's W
                                    ws_con.merge_range(_cr, 0, _cr, 7, "3. 켄달의 일치계수 (Kendall's W)", _F['section'])
                                    _cr += 1
                                    for _ci, _h in enumerate(["지표", "값", "해석"]):
                                        ws_con.write_string(_cr, _ci, _h, _F['header'])
                                    _cr += 1
                                    ws_con.write_string(_cr, 0, "Kendall's W", _F['body'])
                                    ws_con.write_number(_cr, 1, _consensus["kendall_w"], _F['num'])
                                    ws_con.write_string(_cr, 2, _consensus["w_judge"], _F['body'])
                                    _cr += 1
                                    ws_con.write_string(_cr, 0, "p-value", _F['body'])
                                    if _consensus["kendall_p"] is not None:
                                        ws_con.write_number(_cr, 1, _consensus["kendall_p"], _F['num'])
                                    else:
                                        ws_con.write_string(_cr, 1, "-", _F['body'])
                                    ws_con.write_string(_cr, 2, "유의함" if (_consensus["kendall_p"] is not None and _consensus["kendall_p"] < 0.05) else "-", _F['body'])
                                    _cr += 2
                                    ws_con.merge_range(_cr, 0, _cr, 7, f"[해석] {_consensus['s3']}", _F['interp'])
                                    ws_con.set_row(_cr, 30)
                                    _cr += 2
                                    ws_con.merge_range(_cr, 0, _cr, 7, "Kendall's W 해석 기준", _F['criteria_h'])
                                    _cr += 1
                                    for _crit, _desc in [("W ≥ 0.7", "상당한 합의"), ("0.5 ≤ W < 0.7", "중간 수준 합의"), ("0.3 ≤ W < 0.5", "약한 합의"), ("W < 0.3", "합의 부족")]:
                                        ws_con.write_string(_cr, 0, _crit, _F['criteria_b'])
                                        ws_con.merge_range(_cr, 1, _cr, 7, _desc, _F['criteria_b'])
                                        _cr += 1
                                    ws_con.merge_range(_cr, 0, _cr, 7, "이론적 근거: Kendall & Babington Smith (1939), \"The Problem of m Rankings\", Annals of Mathematical Statistics, 10(3), 275-287.", _F['src'])
                                    ws_con.set_row(_cr, 30)
                                    _cr += 2
                                    return _cr

                                # --- 시트 생성 및 계층별 블록 기록 ---
                                _F = {'title': _fmt_title, 'level': _fmt_level, 'section': _fmt_section,
                                      'header': _fmt_header, 'body': _fmt_body, 'num': _fmt_num, 'pct': _fmt_pct,
                                      'interp': _fmt_interp, 'criteria_h': _fmt_criteria_h, 'criteria_b': _fmt_criteria_b,
                                      'src': _fmt_src, 'high': _fmt_high, 'mid': _fmt_mid, 'low': _fmt_low}
                                _has_consensus = False
                                try:
                                    _main_con = calculate_expert_consensus(main_results_df, main_factors)
                                except Exception:
                                    _main_con = None
                                # 중분류 데이터 수집
                                _sub_consensus_map = {}
                                try:
                                    for _mf in main_factors:
                                        _sdf = sub_results_storage.get(_mf, {}).get('df')
                                        _sfs = sub_results_storage.get(_mf, {}).get('factors', [])
                                        if _sdf is not None and len(_sfs) >= 2:
                                            _sc = calculate_expert_consensus(_sdf, _sfs)
                                            if _sc is not None:
                                                _sub_consensus_map[_mf] = (_sfs, _sc)
                                except Exception:
                                    pass
                                if _main_con is not None or _sub_consensus_map:
                                    _has_consensus = True
                                    ws_con = workbook.add_worksheet('Expert_Consensus')
                                    writer.sheets['Expert_Consensus'] = ws_con
                                    _cr = 0
                                    ws_con.write_string(_cr, 0, "전문가 의견 일치도 분석 (Expert Consensus)", _fmt_title)
                                    _cr += 1
                                    _n_resp_show = _main_con["n_resp"] if _main_con else list(_sub_consensus_map.values())[0][1]["n_resp"]
                                    ws_con.write_string(_cr, 0, f"분석 대상: 유효 응답자 {_n_resp_show}명", _fmt_interp)
                                    _cr += 1
                                    ws_con.write_string(_cr, 0, "CR은 개인의 일관성, 아래 지표는 전문가 간 합의를 측정합니다.", _fmt_interp)
                                    _cr += 2
                                    # Part A: 대분류
                                    if _main_con is not None:
                                        ws_con.merge_range(_cr, 0, _cr, 7, "■ 대분류 일치도", _fmt_level)
                                        _cr += 1
                                        _cr = _write_consensus_block(ws_con, _cr, _main_con, _F)
                                    # Part B: 중분류 (대분류별)
                                    for _mf in main_factors:
                                        if _mf in _sub_consensus_map:
                                            _sfs, _sc = _sub_consensus_map[_mf]
                                            ws_con.merge_range(_cr, 0, _cr, 7, f"■ 중분류 일치도 — [{_mf}]", _fmt_level)
                                            _cr += 1
                                            _cr = _write_consensus_block(ws_con, _cr, _sc, _F)
                                    # Part C: 해석 가이드
                                    ws_con.merge_range(_cr, 0, _cr, 7, "■ 해석 가이드", _fmt_level)
                                    _cr += 1
                                    for _gl in [
                                        "· CV가 0.30 이상인 항목은 전문가 의견이 갈리는 영역입니다.",
                                        "· 이는 설문 오류가 아니라 정책적으로 논쟁적인 지점일 수 있습니다.",
                                        "· 보고서에는 \"추가 논의가 필요한 쟁점\"으로 명시하는 것을 권장합니다.",
                                        "· CR 통과 ≠ 의견 일치: 개인의 일관성과 집단의 합의는 별개로 점검해야 합니다.",
                                    ]:
                                        ws_con.merge_range(_cr, 0, _cr, 7, _gl, _fmt_interp)
                                        _cr += 1
                                    ws_con.set_column('A:A', 22)
                                    ws_con.set_column('B:H', 14)


                                def write_detailed_sheet_ws(sheet_name, matrix_df, detail_df, matrix_title, row_labels, group_matrices=None, sheet_excl_count=0):
                                    ws = workbook.add_worksheet(sheet_name)
                                    writer.sheets[sheet_name] = ws
                                    s_row_det = 0
                            
                                    excl_label = _(f"분석 제외 사례수: {sheet_excl_count}건", f"Excluded cases: {sheet_excl_count}")
                                    ws.write(s_row_det, 0, excl_label, workbook.add_format({'bold': True, 'font_color': 'red'}))
                                    s_row_det += 1
                            
                                    ws.write_string(s_row_det, 0, matrix_title)
                                    s_row_det += 1
                                    m_df_obj = pd.DataFrame(matrix_df, index=row_labels, columns=row_labels)
                                    m_df_obj.to_excel(writer, sheet_name=sheet_name, startrow=s_row_det)
                                    add_borders_to_data(ws, s_row_det, 0, m_df_obj, border_fmt, has_header=True, has_index=True)
                                    for r in range(len(matrix_df)):
                                        for c in range(len(matrix_df)):
                                            val = 1 if r==c else matrix_df[r][c]
                                            ws.write(s_row_det+r+1, c+1, val, border_fmt if r!=c else fmt_diagonal)
                                            if r!=c: ws.write(s_row_det+r+1, c+1, val, fmt_float_no_border)
                            
                                    # [신규 추가] 전체 종합 행렬 오른쪽에 전체 CR, CI 값 표시
                                    n_dim = len(matrix_df)
                                    cr_val, ci_val, _unused_lambda = calculate_consistency(matrix_df, mean_method)
                            
                                    ci_cr_header_fmt = workbook.add_format({
                                        'bold': True, 'align': 'center', 'valign': 'vcenter',
                                        'bg_color': '#4F81BD', 'font_color': '#FFFFFF', 'border': 1,
                                        'font_name': 'NanumGothic'
                                    })
                                    ci_cr_label_fmt = workbook.add_format({
                                        'bold': True, 'align': 'center', 'valign': 'vcenter',
                                        'bg_color': '#D9E1F2', 'border': 1,
                                        'font_name': 'NanumGothic'
                                    })
                                    ci_cr_val_fmt = workbook.add_format({
                                        'align': 'center', 'valign': 'vcenter', 'border': 1,
                                        'num_format': '0.000',
                                        'font_name': 'NanumGothic'
                                    })
                                    if cr_val > 0.1:
                                        ci_cr_val_fmt = workbook.add_format({
                                            'align': 'center', 'valign': 'vcenter', 'border': 1,
                                            'num_format': '0.000',
                                            'bg_color': '#FFC7CE', 'font_color': '#9C0006',
                                            'font_name': 'NanumGothic'
                                        })
                            
                                    ws.set_column(n_dim + 2, n_dim + 2, 12)
                                    ws.set_column(n_dim + 3, n_dim + 3, 12)
                            
                                    ws.merge_range(s_row_det, n_dim + 2, s_row_det, n_dim + 3, _("전체 일관성 지표", "Overall Consistency Indicators"), ci_cr_header_fmt)
                                    ws.write(s_row_det + 1, n_dim + 2, _("전체 CI", "Overall CI"), ci_cr_label_fmt)
                                    ws.write(s_row_det + 1, n_dim + 3, ci_val, ci_cr_val_fmt)
                                    ws.write(s_row_det + 2, n_dim + 2, _("전체 CR", "Overall CR"), ci_cr_label_fmt)
                                    ws.write(s_row_det + 2, n_dim + 3, cr_val, ci_cr_val_fmt)
                            
                                    s_row_det += len(matrix_df) + 3
                            
                                    if group_matrices:
                                        for g_name, g_mat in group_matrices.items():
                                            ws.write_string(s_row_det, 0, _(f"] 그룹 종합 행렬: {g_name}", f"] Group Combined Matrix: {g_name}"))
                                            s_row_det += 1
                                            gm_df_obj = pd.DataFrame(g_mat, index=row_labels, columns=row_labels)
                                            gm_df_obj.to_excel(writer, sheet_name=sheet_name, startrow=s_row_det)
                                            add_borders_to_data(ws, s_row_det, 0, gm_df_obj, border_fmt, has_header=True, has_index=True)
                                            for r in range(len(g_mat)):
                                                for c in range(len(g_mat)):
                                                    val = 1 if r==c else g_mat[r][c]
                                                    ws.write(s_row_det+r+1, c+1, val, border_fmt if r!=c else fmt_diagonal)
                                                    if r!=c: ws.write(s_row_det+r+1, c+1, val, fmt_float_no_border)
                                    
                                            # [신규 추가] 그룹 종합 행렬 오른쪽에 그룹 CR, CI 값 표시
                                            g_cr_val, g_ci_val, _unused_lambda = calculate_consistency(g_mat, mean_method)
                                            g_ci_cr_val_fmt = workbook.add_format({
                                                'align': 'center', 'valign': 'vcenter', 'border': 1,
                                                'num_format': '0.000',
                                                'font_name': 'NanumGothic'
                                            })
                                            if g_cr_val > 0.1:
                                                g_ci_cr_val_fmt = workbook.add_format({
                                                    'align': 'center', 'valign': 'vcenter', 'border': 1,
                                                    'num_format': '0.000',
                                                    'bg_color': '#FFC7CE', 'font_color': '#9C0006',
                                                    'font_name': 'NanumGothic'
                                                })
                                    
                                            ws.merge_range(s_row_det, n_dim + 2, s_row_det, n_dim + 3, _("그룹 일관성 지표", "Group Consistency Indicators"), ci_cr_header_fmt)
                                            ws.write(s_row_det + 1, n_dim + 2, _("그룹 CI", "Group CI"), ci_cr_label_fmt)
                                            ws.write(s_row_det + 1, n_dim + 3, g_ci_val, g_ci_cr_val_fmt)
                                            ws.write(s_row_det + 2, n_dim + 2, _("그룹 CR", "Group CR"), ci_cr_label_fmt)
                                            ws.write(s_row_det + 2, n_dim + 3, g_cr_val, g_ci_cr_val_fmt)
                                    
                                            s_row_det += len(g_mat) + 3
                            
                                    detail_df.to_excel(writer, sheet_name=sheet_name, startrow=s_row_det, index=False)
                                    for c_idx, col_val in enumerate(detail_df.columns):
                                        ws.write(s_row_det, c_idx, col_val, formats['header'])
                            
                                    for r_idx in range(len(detail_df)):
                                        row_pos = s_row_det + 1 + r_idx
                                        for c_idx, col_name in enumerate(detail_df.columns):
                                            val = detail_df.iloc[r_idx, c_idx]
                                            current_fmt = border_fmt
                                            if col_name in ['Original_CR', 'Final_CR'] and isinstance(val, (float, int)) and val > 0.1:
                                                current_fmt = formats['yellow']
                                            elif isinstance(val, (float, np.float64)):
                                                current_fmt = formats['num']
                                            else:
                                                current_fmt = formats['body']
                                    
                                            if pd.isnull(val):
                                                ws.write_blank(row_pos, c_idx, "", current_fmt)
                                            else:
                                                ws.write(row_pos, c_idx, val, current_fmt)

                                main_group_mats = {}
                                for grp in unique_groups:
                                    g_df_m = main_results_df[main_results_df['Type'].astype(str) == grp]
                                    if not g_df_m.empty:
                                        mats = np.stack(g_df_m['Matrix_Object'].values)
                                        main_group_mats[grp] = np.mean(mats, axis=0) if mean_method == 'arithmetic' else gmean(mats, axis=0)

                                out_main = main_results_df.drop(columns=['Matrix_Object', 'Orig_Matrix_Object'], errors='ignore')
                                write_detailed_sheet_ws('(대분류) Main', main_group_matrix, out_main, _("[대분류 평가 종합 행렬]", "[Main Criteria Combined Matrix]"), main_factors, group_matrices=main_group_mats, sheet_excl_count=main_excluded)
                                for mf, info in sub_results_storage.items():
                                    safe_name = f"(중분류) {mf}"[:31]
                                    sub_grp_mats = {}
                                    for grp in unique_groups:
                                        g_sub_df = info['df'][info['df']['Type'].astype(str) == grp]
                                        if not g_sub_df.empty:
                                            mats = np.stack(g_sub_df['Matrix_Object'].values)
                                            sub_grp_mats[grp] = np.mean(mats, axis=0) if mean_method == 'arithmetic' else gmean(mats, axis=0)
                                    out_sub = info['df'].drop(columns=['Matrix_Object', 'Orig_Matrix_Object'], errors='ignore')
                            
                                    sub_excl_val = 0
                                    for df_ex in total_excl_df_list:
                                        if 'Sheet' in df_ex.columns and not df_ex.empty:
                                             if mf in df_ex['Sheet'].unique():
                                                 sub_excl_val = len(df_ex[df_ex['Sheet'] == mf])
                                         
                                    title_ko = f"[중분류 평가 종합 행렬]  ▶ 상위 계층: 대분류 [{mf}]"
                                    title_en = f"[Sub-Criteria Combined Matrix]  ▶ Parent: Main [{mf}]"
                                    write_detailed_sheet_ws(safe_name, info['group_matrix'], out_sub, _(title_ko, title_en), info['factors'], group_matrices=sub_grp_mats, sheet_excl_count=sub_excl_val)

                                is_english = (st.session_state.get('lang', 'ko') == 'en')
                                theory_ws = workbook.add_worksheet("Consistency_Theory")
                                theory_title_fmt = workbook.add_format({'bold': True, 'font_size': 14, 'font_name': 'NanumGothic'})
                                theory_body_fmt = workbook.add_format({'text_wrap': True, 'valign': 'top', 'font_name': 'NanumGothic'})
                                if is_english:
                                    theory_text = [
                                        ["AHP Consistency Calibration Principle & Academic Foundation from a Decision-Making Perspective"],
                                        [""],
                                        ["1. Introduction: The Issue of Consistency in the Analytic Hierarchy Process (AHP)"],
                                        ["The Analytic Hierarchy Process, proposed by Saaty (1980), is a multi-criteria decision-making tool that quantifies human subjective judgment. When inconsistent judgments occur, they are mathematically corrected to ensure the reliability of the analysis."],
                                        [""],
                                        ["2. Calibration Algorithm: Iterative Convergence Adjusting Method"],
                                        [f"The original matrix A and the ideal matrix W are linearly combined according to the set learning rate (learning rate α={learning_rate}): A_new = (1-α)A + αW."],
                                        [""],
                                        ["3. Academic Foundation & Effects"],
                                        ["Adjustment using a weighted average of the original matrix and the consistent matrix preserves the decision maker's original preferences as much as possible while improving mathematical consistency."]
                                    ]
                                else:
                                    theory_text = [
                                        ["의사결정론적 관점에서의 AHP 일관성 보정 원리 및 학술적 근거"],
                                        [""],
                                        ["1. 서론: 계층분석과정(AHP)의 일관성 문제"],
                                        ["Saaty(1980)에 의해 제안된 계층분석과정은 인간의 주관적 판단을 정량화하는 다기준 의사결정 도구이다. 비일관적 판단이 발생할 경우 수학적으로 교정하여 분석의 신뢰성을 확보한다."],
                                        [""],
                                        ["2. 보정 알고리즘: 반복 수렴 조정법"],
                                        [f"원본 행렬 A와 이상적 행렬 W를 설정된 학습률(α={learning_rate})에 따라 선형 결합한다: A_new = (1-α)A + αW."],
                                        [""],
                                        ["3. 학술적 근거 및 효과"],
                                        ["원본 행렬과 일관 행렬의 가중 평균을 이용한 조정은 의사결정자의 원래 선호 경향성을 최대한 보존하면서 수학적 일관성을 향상시킨다."]
                                    ]
                                theory_ws.set_column('A:A', 100)
                                for r_idx, row_content in enumerate(theory_text):
                                    fmt = theory_title_fmt if r_idx == 0 else theory_body_fmt
                                    theory_ws.write(r_idx, 0, row_content[0], fmt)

                                if is_single_sheet:
                                    guide_ws = workbook.add_worksheet("Single_Sheet_Guide")
                                    guide_title_fmt = workbook.add_format({'bold': True, 'font_size': 14, 'font_name': 'NanumGothic', 'bg_color': '#D9E1F2', 'border': 1, 'align': 'center', 'valign': 'vcenter'})
                                    guide_section_fmt = workbook.add_format({'bold': True, 'font_size': 11, 'font_name': 'NanumGothic', 'bg_color': '#F2F2F2', 'border': 1, 'valign': 'vcenter', 'align': 'center'})
                                    guide_body_fmt = workbook.add_format({'text_wrap': True, 'valign': 'top', 'font_name': 'NanumGothic', 'border': 1})
                            
                                    guide_ws.set_column('A:A', 25)
                                    guide_ws.set_column('B:B', 75)
                            
                                    # Merge title row
                                    guide_title = _("1단계 AHP 분석 결과 해석 및 주의사항", "Step 1 AHP Analysis Result Interpretation and Guidelines")
                                    guide_ws.merge_range('A1:B1', guide_title, guide_title_fmt)
                                    guide_ws.set_row(0, 35)
                            
                                    if is_english:
                                        guide_data = [
                                            ("Classification", "Detailed Content"),
                                            ("1. Analysis Overview", "This report is a single-level AHP analysis result comparing only the main criteria (Step 1) evaluation criteria without sub-criteria."),
                                            ("2. Result Interpretation Method", "Since the sub-weights are fixed at 1.0, the 'Main Criteria Weight' and the 'Global Weight' are calculated with the same values. Therefore, you can interpret the 'Global Weight' as the final importance of each item."),
                                            ("3. Internal Virtual Operation Guide", "To maintain consistency of the 2-level operation of the AHP analysis system, the system internally auto-generated and computed dummy detailed items with a weight of 1.0 under the main criteria items. Due to this, the 'Result_[Main Criteria Name]' sheet exists in the results download file as a 1x1 matrix, which is a normal virtual operation result."),
                                            ("4. Consistency Ratio (CR) Warnings", "The provided consistency ratio represents only the CR of the pairwise comparison of the main criteria. Since there are no sub-criteria, the 'Sub-Criteria Consistency Ratio (CR)' is unconditionally marked as 0.000, which is not an error."),
                                            ("5. Academic/Report Writing Tip", "When utilizing this in academic research or reports, please explicitly state that 'pairwise comparison analysis was performed under a single-level (Step 1) hierarchical structure.'")
                                        ]
                                    else:
                                        guide_data = [
                                            ("분류", "상세 내용"),
                                            ("1. 분석 개요", "본 보고서는 하위 요소 없이 대분류(1단계) 평가 기준만을 비교한 단일 계층 AHP 분석 결과입니다."),
                                            ("2. 결과 해석 방법", "하위 가중치가 1.0으로 고정되어 '대분류 가중치'와 'Global Weight(종합 가중치)'가 동일한 수치로 산출되었습니다. 따라서 'Global Weight'를 각 항목의 최종 중요도로 해석하시면 됩니다."),
                                            ("3. 내부 가상 연산 안내", "AHP 분석 시스템의 2단계 연산 일관성 유지를 위해, 시스템 내부적으로 대분류 항목 하위에 가중치 1.0을 가지는 더미 세부 항목을 자동 생성하여 연산하였습니다. 이로 인해 결과 다운로드 파일에 'Result_[대분류명]' 시트가 1x1 행렬로 존재하지만 이는 정상적인 가상 연산 결과입니다."),
                                            ("4. 일관성 비율(CR) 주의사항", "제공된 일관성 비율은 대분류 쌍대비교의 일관성 비율(CR)만을 나타냅니다. 하위 요소가 존재하지 않으므로 '중분류 일관성 비율(CR)'은 무조건 0.000으로 표기되며 이는 오류가 아닙니다."),
                                            ("5. 학술/보고서 기재 팁", "학술 연구나 보고서에 활용 시 '단일 계층(1단계) 계층 구조 하에서 쌍대비교 분석을 수행하였다'고 명시적으로 기재하시기 바랍니다.")
                                        ]
                            
                                    for r_idx, (section, content) in enumerate(guide_data, start=1):
                                        if r_idx == 1:
                                            # Header row
                                            guide_ws.write(r_idx, 0, section, workbook.add_format({'bold': True, 'align': 'center', 'bg_color': '#A6A6A6', 'border': 1}))
                                            guide_ws.write(r_idx, 1, content, workbook.add_format({'bold': True, 'align': 'center', 'bg_color': '#A6A6A6', 'border': 1}))
                                        else:
                                            guide_ws.write(r_idx, 0, section, guide_section_fmt)
                                            guide_ws.write(r_idx, 1, content, guide_body_fmt)
                                        guide_ws.set_row(r_idx, 60 if r_idx > 1 else 20)

                                if ahp_method == 'fuzzy':
                                    # 1. Fuzzy AHP 가중치 분석 결과 시트 추가
                                    ws_fuzzy = workbook.add_worksheet('Fuzzy_AHP_Results')
                                    writer.sheets['Fuzzy_AHP_Results'] = ws_fuzzy
                                    ws_fuzzy.set_column('A:A', 25)
                                    ws_fuzzy.set_column('B:G', 20)
                            
                                    fuzzy_header_fmt = workbook.add_format({
                                        'bold': True, 'align': 'center', 'valign': 'vcenter',
                                        'bg_color': '#1F4E78', 'font_color': '#FFFFFF', 'border': 1,
                                        'font_name': 'NanumGothic'
                                    })
                                    title_fmt = workbook.add_format({
                                        'bold': True, 'font_size': 12, 'font_name': 'NanumGothic'
                                    })
                            
                                    row_idx = 1
                            
                                    ws_fuzzy.write_string(row_idx, 0, _("■ 대분류 (Main Criteria) 퍼지 AHP 분석 결과 (삼각피지수 적용)", "■ Main Criteria Fuzzy AHP Results (TFN Applied)"), title_fmt)
                                    row_idx += 1
                            
                                    headers = [
                                        _("구분", "Criteria"), 
                                        _("Fuzzy 가중치 (Lower)", "Fuzzy Weight (Lower)"), 
                                        _("Fuzzy 가중치 (Medium)", "Fuzzy Weight (Medium)"), 
                                        _("Fuzzy 가중치 (Upper)", "Fuzzy Weight (Upper)"), 
                                        _("비퍼지화 (Crisp)", "Defuzzified (Crisp)"), 
                                        _("최종 가중치 (Norm)", "Final Weight (Norm)"), 
                                        _("순위", "Rank")
                                    ]
                            
                                    for c_idx, h in enumerate(headers):
                                        ws_fuzzy.write(row_idx, c_idx, h, fuzzy_header_fmt)
                                    row_idx += 1
                            
                                    main_rows = []
                                    for i, (l, m, u) in enumerate(main_group_Si):
                                        crisp = (l * m * u) ** (1/3)
                                        norm_w = group_main_weights.iloc[i] if isinstance(group_main_weights, pd.Series) else group_main_weights[i]
                                        main_rows.append([main_factors[i], l, m, u, crisp, norm_w])
                            
                                    norm_w_list = [r[5] for r in main_rows]
                                    sorted_weights = sorted(list(set(norm_w_list)), reverse=True)
                                    ranks = [sorted_weights.index(w) + 1 for w in norm_w_list]
                            
                                    for i, r in enumerate(main_rows):
                                        r.append(ranks[i])
                                        ws_fuzzy.write(row_idx, 0, r[0], formats['body'])
                                        for c_idx in range(1, 6):
                                            ws_fuzzy.write_number(row_idx, c_idx, r[c_idx], formats['num'])
                                        ws_fuzzy.write_number(row_idx, 6, r[6], formats['body'])
                                        row_idx += 1
                                
                                    row_idx += 2
                            
                                    for parent_f, sub_info in sub_results_storage.items():
                                        if sub_info.get('group_Si'):
                                            ws_fuzzy.write_string(row_idx, 0, _(f"■ 세부항목 [{parent_f}] 퍼지 AHP 분석 결과 (삼각피지수 적용)", f"■ Sub-Criteria [{parent_f}] Fuzzy AHP Results (TFN Applied)"), title_fmt)
                                            row_idx += 1
                                    
                                            for c_idx, h in enumerate(headers):
                                                ws_fuzzy.write(row_idx, c_idx, h, fuzzy_header_fmt)
                                            row_idx += 1
                                    
                                            sub_factors = sub_info['factors']
                                            sub_group_Si = sub_info['group_Si']
                                            group_sub_w = sub_info['weights']
                                    
                                            sub_rows = []
                                            for i, (l, m, u) in enumerate(sub_group_Si):
                                                crisp = (l * m * u) ** (1/3)
                                                norm_w = group_sub_w.iloc[i] if isinstance(group_sub_w, pd.Series) else group_sub_w[i]
                                                sub_rows.append([sub_factors[i], l, m, u, crisp, norm_w])
                                        
                                            norm_w_list = [r[5] for r in sub_rows]
                                            sorted_weights = sorted(list(set(norm_w_list)), reverse=True)
                                            ranks = [sorted_weights.index(w) + 1 for w in norm_w_list]
                                    
                                            for i, r in enumerate(sub_rows):
                                                r.append(ranks[i])
                                                ws_fuzzy.write(row_idx, 0, r[0], formats['body'])
                                                for c_idx in range(1, 6):
                                                    ws_fuzzy.write_number(row_idx, c_idx, r[c_idx], formats['num'])
                                                ws_fuzzy.write_number(row_idx, 6, r[6], formats['body'])
                                                row_idx += 1
                                    
                                            row_idx += 2

                                    # 2. 일관성 비율(CR) 분포 분석 결과 시트 추가
                                    ws_cr = workbook.add_worksheet('CR_Distribution')
                                    writer.sheets['CR_Distribution'] = ws_cr
                                    ws_cr.set_column('A:A', 25)
                                    ws_cr.set_column('B:H', 20)
                            
                                    cr_header_fmt = workbook.add_format({
                                        'bold': True, 'align': 'center', 'valign': 'vcenter',
                                        'bg_color': '#595959', 'font_color': '#FFFFFF', 'border': 1,
                                        'font_name': 'NanumGothic'
                                    })
                            
                                    ws_cr.write_string(1, 0, _("■ 일관성 비율(CR) 분석 요약", "■ Consistency Ratio (CR) Analysis Summary"), title_fmt)
                            
                                    cr_headers = [
                                        _("평가 시트명", "Sheet Name"),
                                        _("평균 CR", "Mean CR"),
                                        _("중앙값 CR", "Median CR"),
                                        _("최소 CR", "Min CR"),
                                        _("최대 CR", "Max CR"),
                                        _("통과 표본 수 (CR <= 0.1)", "Passed Samples (CR <= 0.1)"),
                                        _("전체 표본 수", "Total Samples"),
                                        _("통과율 (%)", "Pass Rate (%)")
                                    ]
                            
                                    for c_idx, h in enumerate(cr_headers):
                                        ws_cr.write(2, c_idx, h, cr_header_fmt)
                                
                                    cr_row_idx = 3
                            
                                    sheets_to_process = [("Main_Criteria", main_results_df)]
                                    for mf, info in sub_results_storage.items():
                                        sheets_to_process.append((mf, info['df']))
                                
                                    for sheet_name, df_s in sheets_to_process:
                                        if df_s.empty: continue
                                        cr_vals = df_s['Final_CR'].dropna().values
                                        if len(cr_vals) == 0: continue
                                
                                        mean_cr = np.mean(cr_vals)
                                        median_cr = np.median(cr_vals)
                                        min_cr = np.min(cr_vals)
                                        max_cr = np.max(cr_vals)
                                        total_cnt = len(cr_vals)
                                        pass_cnt = np.sum(cr_vals <= 0.1)
                                        pass_rate = (pass_cnt / total_cnt) * 100
                                
                                        ws_cr.write(cr_row_idx, 0, sheet_name, formats['body'])
                                        ws_cr.write_number(cr_row_idx, 1, mean_cr, formats['num'])
                                        ws_cr.write_number(cr_row_idx, 2, median_cr, formats['num'])
                                        ws_cr.write_number(cr_row_idx, 3, min_cr, formats['num'])
                                        ws_cr.write_number(cr_row_idx, 4, max_cr, formats['num'])
                                        ws_cr.write_number(cr_row_idx, 5, pass_cnt, formats['body'])
                                        ws_cr.write_number(cr_row_idx, 6, total_cnt, formats['body'])
                                        ws_cr.write_number(cr_row_idx, 7, pass_rate, formats['num'])
                                        cr_row_idx += 1
                                
                                    cr_row_idx += 2
                                    ws_cr.write_string(cr_row_idx, 0, _("■ 개별 응답자별 일관성 비율(CR) 상세 내역", "■ Detailed Consistency Ratio (CR) by Respondent"), title_fmt)
                                    cr_row_idx += 1
                            
                                    indiv_headers = [
                                        _("ID (설문자)", "Respondent ID"),
                                        _("그룹 (Type)", "Group Type"),
                                        _("평가 시트명", "Sheet Name"),
                                        _("일관성 비율 (CR)", "Consistency Ratio (CR)"),
                                        _("판정 (CR <= 0.1)", "Status (CR <= 0.1)")
                                    ]
                                    for c_idx, h in enumerate(indiv_headers):
                                        ws_cr.write(cr_row_idx, c_idx, h, cr_header_fmt)
                                    cr_row_idx += 1
                            
                                    for idx_row, r in main_results_df.iterrows():
                                        cr_val = r['Final_CR']
                                        status = _("만족 (Pass)", "Pass") if cr_val <= 0.1 else _("불만족 (Fail)", "Fail")
                                        ws_cr.write(cr_row_idx, 0, r['ID'], formats['body'])
                                        ws_cr.write(cr_row_idx, 1, r['Type'], formats['body'])
                                        ws_cr.write(cr_row_idx, 2, "Main_Criteria", formats['body'])
                                        ws_cr.write_number(cr_row_idx, 3, cr_val, formats['num'])
                                        ws_cr.write(cr_row_idx, 4, status, formats['body'])
                                        cr_row_idx += 1
                                
                                    for mf, info in sub_results_storage.items():
                                        for idx_row, r in info['df'].iterrows():
                                            cr_val = r['Final_CR']
                                            status = _("만족 (Pass)", "Pass") if cr_val <= 0.1 else _("불만족 (Fail)", "Fail")
                                            ws_cr.write(cr_row_idx, 0, r['ID'], formats['body'])
                                            ws_cr.write(cr_row_idx, 1, r['Type'], formats['body'])
                                            ws_cr.write(cr_row_idx, 2, mf, formats['body'])
                                            ws_cr.write_number(cr_row_idx, 3, cr_val, formats['num'])
                                            ws_cr.write(cr_row_idx, 4, status, formats['body'])
                                            cr_row_idx += 1

                                # [2026-10-21 통합] 대안 분석 결과가 있으면 같은 결과 파일에 대안 보고서 시트 추가
                                try:
                                    _alt_int = st.session_state.get("alt_analysis_result")
                                    if _alt_int and _alt_int.get("alternatives"):
                                        write_alternative_sheets(workbook, _alt_int)
                                except Exception:
                                    pass

                                # 엑셀 열 때 종합분석 시트가 먼저 보이도록 설정
                                try:
                                    _comp_sheet_name = _('종합분석', 'Comprehensive Analysis')
                                    if _comp_sheet_name in writer.sheets:
                                        writer.sheets[_comp_sheet_name].activate()
                                except Exception:
                                    pass

                        if st.session_state.user_role == 'official':
                            if data_source == _("📂 엑셀 파일 직접 업로드", "Upload Excel File") and uploaded_file is not None:
                                save_data = uploaded_file.getvalue()
                                save_filename = f"{filename_base}_Raw.xlsx"
                            else:
                                uploadable_io = io.BytesIO()
                                with pd.ExcelWriter(uploadable_io, engine='openpyxl') as writer:
                                    if df_main is not None and not df_main.empty:
                                        df_main.to_excel(writer, index=False, sheet_name="Main_Criteria")
                                    for s_name, s_df in sub_dfs.items():
                                        s_df.to_excel(writer, index=False, sheet_name=s_name[:31])
                                    sub_sub_dfs_to_save = st.session_state.get("ahp_sub_sub_dfs", {})
                                    for s_name, s_df in sub_sub_dfs_to_save.items():
                                        s_df.to_excel(writer, index=False, sheet_name=s_name[:31])
                                save_data = uploadable_io.getvalue()
                                save_filename = f"{filename_base}_Raw.xlsx"
                            save_analysis_to_db(st.session_state.user_id, save_filename, save_data)

                        tab1, tab2, tab3, tab4, tab5 = st.tabs([
                            _("종합 분석 (Global)", "Global Comprehensive Analysis"),
                            _("그룹별 분석", "Group Analysis"),
                            _("통계 검정 (ANOVA)", "Statistical Test (ANOVA)"),
                            _("시각화 센터", "Visualization Center"),
                            _("결과 다운로드", "Download Results")
                        ])
                        with tab1:
                            st.subheader(_(" 종합 중요도 및 순위", " Global Weights & Rankings"))
                            if is_english:
                                disp_final_df = final_df.rename(columns={
                                    "대분류": "Main Criteria",
                                    "대분류 가중치": "Main Criteria Weight",
                                    "중분류": "Sub-Criteria",
                                    "중분류 가중치": "Sub-Criteria Weight",
                                    "Global Weight": "Global Weight",
                                    "Global Rank": "Global Rank",
                                    "CR(대분류)": "CR (Main Criteria)",
                                    "CI(대분류)": "CI (Main Criteria)",
                                    "CR(중분류)": "CR (Sub-Criteria)",
                                    "CI(중분류)": "CI (Sub-Criteria)"
                                })
                            else:
                                disp_final_df = final_df
                            st.dataframe(disp_final_df.style.format(precision=3), use_container_width=True)



                        with tab2:
                            st.markdown(_("#### 그룹별 가중치 상세 비교", "#### Detailed Comparison of Weights by Group"))
                            disp_comparison_df = comparison_df.copy()
                            if is_english:
                                disp_comparison_df.rename(columns={
                                    "중분류": "Sub-Criteria",
                                    "Overall": "Overall",
                                    "전문가": "Expert",
                                    "일반": "General",
                                    "공무원": "Public Official"
                                }, inplace=True)
                            st.dataframe(disp_comparison_df.style.format(precision=4), use_container_width=True)
                        with tab3:
                            st.markdown(_("#### 집단 간 유의성 분석", "#### Analysis of Significance Between Groups"))
                            if not anova_df.empty:
                                if is_english:
                                    disp_anova = anova_df.copy()
                                    disp_anova.rename(columns={
                                        "요인": "Factor/Criteria",
                                        "F-값": "F-Value",
                                        "P-Value": "P-Value",
                                        "유의성": "Significance",
                                        "사후검정(Tukey HSD)": "Post-Hoc (Tukey HSD)"
                                    }, inplace=True)
                            
                                    # Map values in Significance
                                    disp_anova["Significance"] = disp_anova["Significance"].map({
                                        "유의함": "Significant",
                                        "유의하지 않음": "Not Significant"
                                    }).fillna(disp_anova["Significance"])
                            
                                    # Map values in Post-Hoc
                                    def translate_posthoc(val):
                                        if not isinstance(val, str):
                                            return val
                                        val = val.replace("전문가", "Expert").replace("일반", "General").replace("공무원", "Public Official")
                                        val = val.replace(" 차이 있음", " (Diff exists)")
                                        val = val.replace("집단 간 구체적 차이 발견 못함", "No significant pairwise difference found")
                                        val = val.replace("계산 오류", "Calculation Error")
                                        return val
                                    disp_anova["Post-Hoc (Tukey HSD)"] = disp_anova["Post-Hoc (Tukey HSD)"].apply(translate_posthoc)
                                else:
                                    disp_anova = anova_df
                                st.dataframe(disp_anova.style.format(precision=5), use_container_width=True)
                            else:
                                st.info(_("통계 검정을 위해 2개 이상의 그룹 데이터가 필요합니다.", "At least 2 group datasets are required for statistical testing (ANOVA)."))
                        with tab4:
                            st.markdown(_("####  시각화 센터", "####  Visualization Center"))
                            col_chart1, col_chart2 = st.columns(2)
                            with col_chart1:
                                st.write(_("**종합 중요도 (Bar)**", "**Global Importance (Bar)**"))
                                chart_bar_df = final_df.sort_values('Global Weight').copy()
                                if is_english:
                                    chart_bar_df.rename(columns={"중분류": "Sub-Criteria", "Global Weight": "Global Weight"}, inplace=True)
                                    y_col = "Sub-Criteria"
                                    x_col = "Global Weight"
                                else:
                                    y_col = "중분류"
                                    x_col = "Global Weight"
                                fig_bar = px.bar(chart_bar_df, y=y_col, x=x_col, orientation='h', text_auto='.3f')
                                st.plotly_chart(fig_bar, use_container_width=True)
                            with col_chart2:
                                st.write(_("**그룹별 중요도 패턴 (Radar)**", "**Importance Pattern by Group (Radar)**"))
                                indiv_global_radar = []
                                all_ids_r = main_results_df['ID'].unique()
                                for rid in all_ids_r:
                                    m_row_rd = main_results_df[main_results_df['ID'] == rid].iloc[0]
                                    rtype_rd = m_row_rd['Type']
                                    grp_name_en = rtype_rd
                                    if is_english:
                                        grp_name_en = str(rtype_rd).replace("전문가", "Expert").replace("일반", "General").replace("공무원", "Public Official")
                                    for m_f_rd in main_factors:
                                        mw_indiv_rd = m_row_rd[f"Weight_{m_f_rd}"]
                                        s_row_df_rd = sub_results_storage[m_f_rd]['df']
                                        s_row_rd = s_row_df_rd[s_row_df_rd['ID'] == rid].iloc[0]
                                        for s_f_rd in sub_results_storage[m_f_rd]['factors']:
                                            indiv_global_radar.append({
                                                "Type": grp_name_en, 
                                                "Factor": s_f_rd, 
                                                "Global_Weight": mw_indiv_rd * s_row_rd[f"Weight_{s_f_rd}"]
                                            })
                                radar_indiv_df = pd.DataFrame(indiv_global_radar)
                                radar_plot_df = radar_indiv_df.groupby(['Type', 'Factor'])['Global_Weight'].mean().reset_index()
                                fig_radar = go.Figure()
                                for t in radar_plot_df['Type'].unique():
                                    t_data = radar_plot_df[radar_plot_df['Type'] == t]
                                    fig_radar.add_trace(go.Scatterpolar(r=t_data['Global_Weight'], theta=t_data['Factor'], fill='toself', name=t))
                                st.plotly_chart(fig_radar, use_container_width=True)
                    
                            # [바이올린 플롯] CR 분포 시각화 — 드롭다운 계층 선택
                            st.markdown("---")
                            st.write(_("**일관성 비율(CR) 분포 (Violin Plot)**", "**Consistency Ratio (CR) Distribution (Violin Plot)**"))
                            st.caption(_("계층을 선택하면 해당 수준 응답자들의 CR 분포를 표시합니다. 바이올린 폭 = 밀도, 내부 박스 = 중앙값·사분위수, 점 = 개별 응답자",
                                         "Select a tier to view respondent CR distribution. Width = density, box = median/IQR, dots = individual respondents"))

                            _t2_tier_opts_ko = ["대분류 (Main)", "중분류 (Sub)"]
                            _t2_tier_opts_en = ["Main Criteria", "Sub-Criteria"]
                            _t2_tier_opts = _t2_tier_opts_en if is_english else _t2_tier_opts_ko
                            _t2_sel_tier = st.selectbox(
                                _("📂 표시할 계층 선택", "📂 Select Tier to Display"),
                                options=_t2_tier_opts,
                                key="vio_tier_select_2tier"
                            )

                            _t2_vio_palette = [
                                "rgba(70,130,180,0.65)",
                                "rgba(205,92,92,0.65)",
                                "rgba(255,182,193,0.65)",
                                "rgba(60,179,113,0.65)",
                                "rgba(255,165,0,0.65)",
                                "rgba(147,112,219,0.65)",
                                "rgba(72,209,204,0.65)",
                                "rgba(255,215,0,0.65)",
                            ]
                            _t2_vio_line_pal = [
                                "#4682B4","#CD5C5C","#FFB6C1","#3CB371",
                                "#FFA500","#9370DB","#48D1CC","#FFD700"
                            ]

                            try:
                                _fig_t2_vio = go.Figure()
                                _t2_ci = 0

                                # ── 선택: 대분류 ─────────────────────────────────
                                if _t2_sel_tier == _t2_tier_opts[0]:
                                    if not main_results_df.empty and "Final_CR" in main_results_df.columns:
                                        _t2_main_cr = main_results_df["Final_CR"].dropna().tolist()
                                        _t2_xlbl = _("대분류", "Main Criteria")
                                        _fig_t2_vio.add_trace(go.Violin(
                                            y=_t2_main_cr, x=[_t2_xlbl]*len(_t2_main_cr),
                                            name=_t2_xlbl, box_visible=True, meanline_visible=True,
                                            points="all", jitter=0.35, pointpos=0,
                                            line_color=_t2_vio_line_pal[0],
                                            fillcolor=_t2_vio_palette[0],
                                            opacity=0.75,
                                            hovertemplate="<b>" + _t2_xlbl + "</b><br>CR: %{y:.4f}<extra></extra>",
                                            showlegend=True
                                        ))
                                    _t2_xaxis_title = _("대분류", "Main Criteria")
                                    _t2_legend_title = _("대분류", "Main Criteria")

                                # ── 선택: 중분류 ─────────────────────────────────
                                else:
                                    for _t2_mf, _t2_info in sub_results_storage.items():
                                        _t2_sdf = _t2_info.get("df", None)
                                        if _t2_sdf is None or _t2_sdf.empty or "Final_CR" not in _t2_sdf.columns:
                                            continue
                                        _t2_cr_vals = _t2_sdf["Final_CR"].dropna().tolist()
                                        if len(_t2_cr_vals) < 2:
                                            continue
                                        _t2_xlbl = _(f"중분류({_t2_mf})", f"Sub({_t2_mf})")
                                        _fig_t2_vio.add_trace(go.Violin(
                                            y=_t2_cr_vals, x=[_t2_xlbl]*len(_t2_cr_vals),
                                            name=_t2_xlbl, box_visible=True, meanline_visible=True,
                                            points="all", jitter=0.35, pointpos=0,
                                            line_color=_t2_vio_line_pal[_t2_ci % len(_t2_vio_line_pal)],
                                            fillcolor=_t2_vio_palette[_t2_ci % len(_t2_vio_palette)],
                                            opacity=0.75,
                                            hovertemplate="<b>" + _t2_xlbl + "</b><br>CR: %{y:.4f}<extra></extra>",
                                            showlegend=True
                                        ))
                                        _t2_ci += 1
                                    _t2_xaxis_title = _("대분류 (중분류 비교 CR)", "Main Criteria (Sub-Criteria Comparison CR)")
                                    _t2_legend_title = _("중분류", "Sub-Criteria")

                                if len(_fig_t2_vio.data) == 0:
                                    st.info(_("선택한 계층의 CR 데이터가 없거나 응답 수가 부족합니다.",
                                              "No CR data available for the selected tier or insufficient responses."))
                                else:
                                    _fig_t2_vio.add_hline(
                                        y=0.1, line_dash="dash", line_color="red",
                                        annotation_text=_("CR 임계값 (0.1)", "CR Threshold (0.1)"),
                                        annotation_position="top right"
                                    )
                                    _fig_t2_vio.update_layout(
                                        title=_(
                                            f"바이올린플롯 CR — {_t2_sel_tier}",
                                            f"Violin Plot CR — {_t2_sel_tier}"
                                        ),
                                        xaxis_title=_t2_xaxis_title,
                                        yaxis_title="Final_CR",
                                        violinmode="overlay",
                                        height=540,
                                        legend_title_text=_t2_legend_title,
                                        plot_bgcolor="white",
                                        paper_bgcolor="white",
                                        xaxis=dict(showgrid=False, tickangle=-20),
                                        yaxis=dict(showgrid=True, gridcolor="#eeeeee", zeroline=False)
                                    )
                                    st.plotly_chart(_fig_t2_vio, use_container_width=True)
                            except Exception as _e_t2_vio:
                                st.warning(_(f"바이올린 플롯 생성 실패: {_e_t2_vio}", f"Violin plot generation failed: {_e_t2_vio}"))

                            # ── Fuzzy AHP TFN 삼각퍼지 그래프 (Tab1 결과 화면 직후) ──
                            if ahp_method == 'fuzzy':
                                st.markdown("---")
                                st.subheader(_(" 삼각퍼지수(TFN) 가중치 분포", " Triangular Fuzzy Number (TFN) Weight Distribution"))
                                st.caption(_("각 요인의 삼각퍼지수(L, M, U)와 비퍼지화된 Crisp 가중치를 시각화합니다.",
                                             "Visualizes each factor's Triangular Fuzzy Numbers (L, M, U) and defuzzified Crisp weights."))

                                tfn_color_palette = [
                                    '#636EFA', '#EF553B', '#00CC96', '#AB63FA', '#FFA15A',
                                    '#19D3F3', '#FF6692', '#B6E880', '#FF97FF', '#FECB52'
                                ]

                                def render_tfn_chart(tfn_Si_data, tfn_factors_data, chart_title):
                                    fig = go.Figure()
                                    for i, (l, m, u) in enumerate(tfn_Si_data):
                                        color = tfn_color_palette[i % len(tfn_color_palette)]
                                        crisp = (l * m * u) ** (1/3)
                                        # 삼각형 채우기 (반투명)
                                        fig.add_trace(go.Scatter(
                                            x=[l, m, u, l],
                                            y=[0, 1, 0, 0],
                                            fill='toself',
                                            fillcolor=f"rgba({int(color[1:3],16)}, {int(color[3:5],16)}, {int(color[5:7],16)}, 0.15)" if color.startswith('#') and len(color) == 7 else (color.replace(')', ', 0.15)').replace('rgb', 'rgba') if 'rgb' in color else color),
                                            line=dict(color=color, width=2.5),
                                            mode='lines',
                                            name=f"{tfn_factors_data[i]}",
                                            hovertemplate=(
                                                f"<b>{tfn_factors_data[i]}</b><br>"
                                                f"L={l:.4f}, M={m:.4f}, U={u:.4f}<br>"
                                                f"Crisp={crisp:.4f}<extra></extra>"
                                            ),
                                            showlegend=True
                                        ))
                                        # Crisp 가중치 수직 점선
                                        fig.add_trace(go.Scatter(
                                            x=[crisp, crisp],
                                            y=[0, 0.85],
                                            mode='lines',
                                            line=dict(color=color, width=1.5, dash='dot'),
                                            showlegend=False,
                                            hoverinfo='skip'
                                        ))
                                        # Crisp 마커
                                        fig.add_trace(go.Scatter(
                                            x=[crisp],
                                            y=[0.88],
                                            mode='markers+text',
                                            marker=dict(color=color, size=8, symbol='diamond'),
                                            text=[f"{crisp:.3f}"],
                                            textposition='top center',
                                            textfont=dict(size=10, color=color),
                                            showlegend=False,
                                            hovertemplate=f"<b>{tfn_factors_data[i]}</b> Crisp={crisp:.4f}<extra></extra>"
                                        ))
                                    fig.update_layout(
                                        title=dict(text=chart_title, font=dict(size=14)),
                                        xaxis_title=_("가중치 값 (Weight Value)", "Weight Value"),
                                        yaxis_title=_("소속도 (Membership Degree)", "Membership Degree"),
                                        yaxis=dict(range=[-0.05, 1.25]),
                                        height=420,
                                        margin=dict(l=30, r=30, t=50, b=40),
                                        hovermode="closest",
                                        legend=dict(
                                            orientation="h",
                                            yanchor="bottom",
                                            y=-0.25,
                                            xanchor="center",
                                            x=0.5
                                        ),
                                        plot_bgcolor='rgba(248,249,250,1)',
                                        paper_bgcolor='rgba(255,255,255,1)'
                                    )
                                    fig.update_xaxes(gridcolor='rgba(200,200,200,0.3)', zeroline=True, zerolinecolor='rgba(150,150,150,0.5)')
                                    fig.update_yaxes(gridcolor='rgba(200,200,200,0.3)')
                                    return fig

                                # 1) 메인 기준 TFN 그래프
                                if main_group_Si:
                                    st.plotly_chart(
                                        render_tfn_chart(main_group_Si, main_factors,
                                            _("▶ 대분류 (Main Criteria) 삼각퍼지 분포", "▶ Main Criteria TFN Distribution")),
                                        use_container_width=True
                                    )

                                    # TFN 수치 테이블
                                    tfn_table_rows = []
                                    for i, (l, m, u) in enumerate(main_group_Si):
                                        crisp = (l * m * u) ** (1/3)
                                        tfn_table_rows.append({
                                            _("요인", "Factor"): main_factors[i],
                                            "L (Lower)": l, "M (Most Likely)": m, "U (Upper)": u,
                                            "Crisp Weight": crisp,
                                            _("정규화 가중치", "Normalized Weight"): group_main_weights.iloc[i] if isinstance(group_main_weights, pd.Series) else group_main_weights[i]
                                        })
                                    st.dataframe(pd.DataFrame(tfn_table_rows).style.format(precision=4), use_container_width=True)

                                # 2) 세부 기준별 TFN 그래프
                                for parent_f, sub_info in sub_results_storage.items():
                                    if sub_info.get('group_Si'):
                                        st.markdown("---")
                                        st.plotly_chart(
                                            render_tfn_chart(sub_info['group_Si'], sub_info['factors'],
                                                _(f"▶ [{parent_f}] 세부항목 삼각퍼지 분포", f"▶ [{parent_f}] Sub-Criteria TFN Distribution")),
                                            use_container_width=True
                                        )
                                        sub_tfn_rows = []
                                        for i, (l, m, u) in enumerate(sub_info['group_Si']):
                                            crisp = (l * m * u) ** (1/3)
                                            sub_tfn_rows.append({
                                                _("요인", "Factor"): sub_info['factors'][i],
                                                "L (Lower)": l, "M (Most Likely)": m, "U (Upper)": u,
                                                "Crisp Weight": crisp,
                                                _("정규화 가중치", "Normalized Weight"): sub_info['weights'].iloc[i] if isinstance(sub_info['weights'], pd.Series) else sub_info['weights'][i]
                                            })
                                        st.dataframe(pd.DataFrame(sub_tfn_rows).style.format(precision=4), use_container_width=True)

                        with tab5:
                            st.markdown(_('<p style="color: red; font-weight: bold; font-size: 0.95rem; margin-bottom: 12px;"> 주의: 분석 결과가 웹상에 영구 저장되지 않으므로, 아래 다운로드 버튼을 눌러 결과물 엑셀 파일을 컴퓨터에 반드시 저장해 주세요.</p>',
                                          '<p style="color: red; font-weight: bold; font-size: 0.95rem; margin-bottom: 12px;">⚠️ Warning: Analysis results are not permanently stored on the web. Please make sure to click the download button below to save the Excel file to your computer.</p>'), unsafe_allow_html=True)
                            st.download_button(_("📥 결과 파일 다운로드 (Excel)", "📥 Download Results File (Excel)"), data=output_res.getvalue(), file_name="AHP_Result.xlsx", type="primary", on_click=lambda: __import__("survey_manager").log_user_action(st.session_state.get("user_id") or "Guest", "결과 엑셀 다운로드"))
                            if 'radar_indiv_df' in locals() and not radar_indiv_df.empty:
                                disp_radar_df = radar_indiv_df.copy()
                                if is_english:
                                    disp_radar_df.rename(columns={
                                        "Type": "Group/Type",
                                        "Factor": "Factor/Criteria",
                                        "Global_Weight": "Global Weight"
                                    }, inplace=True)
                                st.dataframe(disp_radar_df.style.format(precision=4), use_container_width=True)
                            else:
                                st.dataframe(pd.DataFrame(), use_container_width=True)

                except Exception as e:
                    import traceback
                    st.error(_("❌ 분석 시스템 내부 오류가 발생했습니다.", "❌ An internal error occurred in the analysis system."))
                    st.info(_(f"상세 에러 내용: {e}", f"Detailed error: {e}"))
                    with st.expander(_("🔍 상세 스택 트레이스", "🔍 Detailed Stack Trace")):
                        st.code(traceback.format_exc())
                    tab1_main_col.__exit__(None, None, None)
                    st.stop()
            else:
                st.warning(message)
                if role_chk == 'temp' and ("3개 표본" in message or "3 samples" in message):
                    st.markdown("---")
                    with st.container(border=True):
                        is_english = (st.session_state.get('lang', 'ko') == 'en')
                        if is_english:
                            st.markdown("###  Official User Upgrade & Unlimited Analysis")
                            st.markdown("Upgrading to an Official User **instantly removes the 3-sample limit** and allows unlimited access to all features.")
                            st.info("Upgrade to **Official User** to get unlimited access (2 months) for **$350.00 USD** via PayPal.")
                        
                            paypal_client_id = st.secrets.get("PAYPAL_CLIENT_ID", "sb")
                            user_id = st.session_state.user_id
                        
                            paypal_html = f"""
                            <div id="paypal-button-container-main" style="text-align: center; max-width: 100%;"></div>
                            <script src="https://www.paypal.com/sdk/js?client-id={paypal_client_id}&currency=USD&locale=en_US"></script>
                            <script>
                              paypal.Buttons({{
                                style: {{
                                  layout: 'vertical',
                                  color:  'gold',
                                  shape:  'rect',
                                  label:  'paypal',
                                  height: 40
                                }},
                                createOrder: function(data, actions) {{
                                  return actions.order.create({{
                                    purchase_units: [{{
                                      amount: {{
                                        value: '350.00'
                                      }},
                                      payee: {{
                                        email_address: 'jeon080423@gmail.com'
                                      }}
                                    }}]
                                  }});
                                }},
                                onApprove: function(data, actions) {{
                                  return actions.order.capture().then(function(details) {{
                                    window.top.location.href = window.top.location.origin + window.top.location.pathname + "?paypal_order_id=" + data.orderID + "&user_id=" + encodeURIComponent("{user_id}");
                                  }});
                                }},
                                onError: function(err) {{
                                  console.error(err);
                                  alert("Payment failed or was cancelled.");
                                }}
                              }}).render('#paypal-button-container-main');
                            </script>
                            """
                            st.components.v1.html(paypal_html, height=180)
                        else:
                            st.markdown(_("### 💳 무제한 분석 및 즉시 해제", "### 💳 Upgrade to Official User for Unlimited Analysis"))
                            _n_total = len(df_main) if 'df_main' in dir() and df_main is not None else 0
                            st.warning(_("⚠️ 무료 플랜은 **3표본까지만** 분석할 수 있습니다. 현재 데이터는 **{n}개**로 3개를 초과했습니다.",
                                         "⚠️ The Free plan can analyze **up to 3 samples**. Your data has **{n}**, exceeding the limit.").format(n=_n_total if _n_total else "?"))
                            st.markdown(_("유료로 전환하시면:", "By upgrading:"))
                            st.markdown(_("- ✅ **표본 수 제한 즉시 해제** — 전체 데이터 분석 가능\n- ✅ T-Test/ANOVA 집단 비교 (Standard 이상)\n- ✅ 퍼지 AHP (Pro)",
                                           "- ✅ **Instant limit removal** — analyze all your data\n- ✅ T-Test/ANOVA group comparison (Standard+)\n- ✅ Fuzzy AHP (Pro)"))
                            if st.button(_("🚀 지금 업그레이드하고 이어서 분석하기", "🚀 Upgrade Now and Continue"), type="primary", use_container_width=True):
                                # '분석 요금제' 탭으로 이동 (로그인 상태 유지)
                                st.session_state["_goto_tab"] = _("요금제", "Pricing")
                                st.rerun()
        except Exception as e:
            st.error(_(f"파일 처리 오류 발생: {e}", f"File processing error: {e}"))
        
    st.markdown("---")

    # [2026-10-20] 대안 평가 분석 섹션 (Alt 시트가 로드된 온라인 설문 전용)
    _alt_dfs_ui = st.session_state.get("ahp_alt_dfs", {}) or {}
    _alt_names_ui = st.session_state.get("ahp_alternatives", []) or []
    if _alt_dfs_ui and len(_alt_names_ui) >= 2:
        st.markdown("---")
        st.subheader(_("🎯 대안 평가 분석", "🎯 Alternative Evaluation Analysis"))
        st.caption(_("최하위 요인별 대안 쌍대비교 응답을 집계해 대안 종합 우선순위를 산출합니다.",
                     "Aggregates alternative pairwise responses per leaf criterion to rank alternatives."))
        if st.button(_("🎯 대안 종합 분석 실행", "🎯 Run Alternative Analysis"), key="btn_run_alt_analysis", type="primary"):
            with st.spinner(_("대안 종합 분석 수행 중...", "Computing alternative priorities...")):
                _res_alt_ui = compute_alternative_analysis(
                    st.session_state.get("ahp_df_main"),
                    st.session_state.get("ahp_sub_dfs", {}) or {},
                    st.session_state.get("ahp_sub_sub_dfs", {}) or {},
                    _alt_dfs_ui,
                    st.session_state.get("ahp_alt_model", {}),
                    cr_threshold, max_iter_val, learning_rate, mean_method, ahp_method)
                st.session_state["alt_analysis_result"] = _res_alt_ui
                # [2026-10-21 통합] 결과 엑셀은 페이지 상단에서 먼저 생성되므로, 대안 시트를
                # 통합 파일에 반영하려면 분석 직후 1회 재실행해 엑셀을 다시 생성해야 한다
                st.rerun()
        _res_alt_ui = st.session_state.get("alt_analysis_result")
        if _res_alt_ui:
            _alts_ui = _res_alt_ui["alternatives"]
            _gs_ui = _res_alt_ui["group_scores"]
            _order_ui = sorted(_gs_ui, key=_gs_ui.get, reverse=True)
            st.markdown(_(f"**최종 대안 순위 (집단, n={_res_alt_ui['n_used']})**",
                           f"**Final Alternative Ranking (Group, n={_res_alt_ui['n_used']})**"))
            _rank_df_ui = pd.DataFrame([{"순위": i + 1, "대안": a, "종합 가중치": round(_gs_ui[a], 4)} for i, a in enumerate(_order_ui)])
            st.dataframe(_rank_df_ui, use_container_width=True, hide_index=True)
            try:
                _fig_alt = px.bar(_rank_df_ui.sort_values("종합 가중치", ascending=True), x="종합 가중치", y="대안",
                                  orientation="h", title=_("대안 종합 우선순위 (그룹)", "Group Alternative Priorities"),
                                  text_auto=".4f")
                st.plotly_chart(_fig_alt, use_container_width=True)
            except Exception:
                pass
            with st.expander(_("📊 요인별 대안 가중치 (그룹)", "📊 Alternative Weights per Criterion (Group)")):
                _leaf_df_ui = pd.DataFrame([{_("최하위 요인", "Leaf Criterion"): leaf,
                                             _("글로벌 가중치", "Global Weight"): round(_res_alt_ui["leaf_group_global"].get(leaf, 0.0), 4),
                                             **{a: round(_res_alt_ui["leaf_alt_group"].get(leaf, {}).get(a, 0.0), 4) for a in _alts_ui}}
                                            for leaf in _res_alt_ui["leaves"]])
                st.dataframe(_leaf_df_ui, use_container_width=True, hide_index=True)
            with st.expander(_("👤 개인별 대안 종합점수", "👤 Individual Alternative Scores")):
                _ind_ui = _res_alt_ui["indiv_df"].rename(columns={f"Score_{a}": a for a in _alts_ui})
                st.dataframe(_ind_ui, use_container_width=True, hide_index=True)
            st.download_button(
                label=_("📥 대안 평가 결과 다운로드 (.xlsx)", "📥 Download Alternative Results (.xlsx)"),
                data=build_alternative_excel(_res_alt_ui),
                file_name="AHP_Alternative_Result.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary", use_container_width=True, key="dl_alt_result")
        elif "alt_analysis_result" in st.session_state:
            st.warning(_("대안 응답이 분석 기준(CR 등)을 만족하지 못해 결과를 산출할 수 없습니다.",
                         "Alternative responses did not meet analysis criteria (e.g., CR)."))

    if st.session_state.user_role == 'official':
        with st.expander(_("나의 분석 보관함 (중요: 반드시 컴퓨터에 백업해 주세요)", "My Analysis Storage (Important: Please backup to your computer)")):
            my_analyses = get_user_analyses(st.session_state.user_id)
            if not my_analyses: st.info(_("저장된 분석 없음", "No saved analyses found."))
            else:
                for item in my_analyses:
                    a_id, filename, save_date = item
                    col_List1, col_List2, col_List3, col_List4 = st.columns([3, 2, 1, 1])
                    with col_List1: st.text(f"{filename}")
                    with col_List2: st.caption(f"{save_date}")
                    with col_List3:
                        file_info = get_analysis_file(analysis_id=a_id)
                        if file_info:
                            fname, fdata = file_info
                            st.download_button("⬇️", fdata, fname, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key=f"dl_{a_id}", type="primary")
                    with col_List4:
                        if st.button("🗑", key=f"del_{a_id}"):
                            delete_analysis(a_id)
                            st.rerun()



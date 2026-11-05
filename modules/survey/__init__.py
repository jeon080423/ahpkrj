"""
AHPMASTER 설문 모듈
- 설문 작성·배포 UI (main_tab_survey)

[2026-10-31] Phase 2: standard_app.py L12932-15135에서 추출
- 응답자 SPA (L4975-6768)는 제외됨 (절대 금지 구역)
- render_survey_status_dashboard()는 import로 참조 (복사 금지)
- st.stop() 0개 확인됨

주의: 이 모듈은 st.session_state를 직접 사용합니다.
"""
import streamlit as st

# 명시적 import (Phase 2 NameError 수정, 2026-11-01)
# 원본 standard_app.py는 LazyLoader 패턴 사용 — 모듈 독립성을 위해 직접 import
import numpy as np
import pandas as pd
from scipy.stats import gmean
import json
import os

# 9개 헬퍼 함수 (팀 2 리뷰 NameError 11건 수정용)
from .helpers import (
    translate_definition_if_default,
    sync_short_codes_from_gs,
    update_user_survey_distribution,
    calculate_consistency,
    process_single_sheet,
    _ss_blocks_in_order,
    _extract_ss_block_df,
    export_to_template_excel,
    show_reset_survey_dialog,
)

# core 모듈 import (Phase 1)
try:
    from core.auth import get_current_tier, check_tier, is_admin_mode
    from core.i18n import _
    from core.session import get_session
except ImportError:
    # 폴백: 직접 정의 (모듈 경로 문제 시)
    def _(ko, en, ja=None):
        try:
            lang = st.session_state.get('lang', 'ko')
            if lang == 'ja':
                return ja if ja is not None else en
            if lang == 'en':
                return en
        except:
            pass
        return ko


def render_survey_module():
    """설문 작성·배포 UI 렌더링.
    
    원본: standard_app.py L12932-15135의 'with main_tab_survey:' 블록
    """
    survey_sub_deploy, survey_sub_status, survey_sub_tools, survey_sub_projects = st.tabs([
        _("설문 작성 및 배포", "Create & Deploy Survey"),
        _("응답 현황", "Responses"),
        _("자료수집 도구", "Collection Tools"),
        _("프로젝트 관리", "Projects")
    ])
    with survey_sub_projects:
        try:
            from project_manager import render_project_manager
            render_project_manager()
        except Exception as e:
            st.error(_(f"프로젝트 관리 로드 실패: {e}", f"Failed to load project manager: {e}"))
    with survey_sub_tools:
        try:
            from collection_support import render_collection_tools
            from survey_manager import load_survey_metadata as _load_meta_tool
            # 도구 탭용 설문 선택 (응답 현황과 동일한 설문 사용)
            _tool_surveys = []
            try:
                from survey_manager import get_admin_surveys_from_gsheet
                _tool_surveys = get_admin_surveys_from_gsheet(st.session_state.get("user_id")) or []
            except Exception:
                pass
            # SQLite admin_surveys도 병합 (설문 ID로 가져오기 지원)
            try:
                import sqlite3
                _conn_t = sqlite3.connect('users.db')
                _cur_t = _conn_t.cursor()
                _cur_t.execute("SELECT survey_id, title, created_at FROM admin_surveys WHERE admin_id = ? ORDER BY created_at DESC", (st.session_state.get("user_id"),))
                _sqlite_tool_surveys = _cur_t.fetchall()
                _conn_t.close()
                _merged_tool = {}
                for s in _tool_surveys + _sqlite_tool_surveys:
                    if s[0] not in _merged_tool:
                        _merged_tool[s[0]] = s
                _tool_surveys = list(_merged_tool.values())
                _tool_surveys.sort(key=lambda x: x[2], reverse=True)
            except Exception:
                pass
            if not _tool_surveys:
                st.info(_("도구를 사용할 설문이 없습니다. 먼저 설문을 배포해 주세요.", "No surveys available for tools. Please deploy a survey first."))
            else:
                _tool_options = {f"{r[1]} ({r[2]})": r[0] for r in _tool_surveys}
                _tool_label = st.selectbox(_("설문 선택", "Select Survey"), list(_tool_options.keys()),
                                           key="tool_survey_select")
                _tool_sid = _tool_options[_tool_label].strip()
                _tool_meta = _load_meta_tool(_tool_sid) or {}
                # 완료/방문 수는 응답 현황과 동일한 로직으로 조회 (간단히 0으로)
                render_collection_tools(_tool_sid, _tool_meta, 0, 0)
        except Exception as e:
            st.error(f"자료수집 도구 로드 실패: {e}")
    with survey_sub_deploy:
        @st.fragment
        def _survey_setup_fragment():
            try:
                import retention_manager
                retention_manager.run_retention_check_silent()
            except Exception:
                pass
            st.header(_("AHP 온라인 설문 자동 생성 및 배포", "AHP Online Survey Auto-Generator & Deployer"))
            box_style = """
            <div style="background-color: #f8f9fc; border: none; border-radius: 8px; padding: 16px 20px; margin-bottom: 20px; color: #1e293b; font-size: 0.95em; line-height: 1.6; box-shadow: 0 2px 8px rgba(0,0,0,0.04);">
            """
            if st.session_state.user_id is None:
                msg = _(
                    "<strong>비회원도 온라인 설문 폼을 미리 작성해 볼 수 있습니다.</strong><br>"
                    "작성하신 내용은 좌측 사이드바에서 회원가입 및 로그인을 하시면 그대로 유지되어 바로 배포하실 수 있습니다. (무료 회원도 기능 제한 없이 모든 기능 사용 가능)<br><br>"
                    "응답 데이터는 연동하신 구글 스프레드시트에 저장됩니다. 배포 전 데이터가 정상 기록되는지 반드시 테스트해 주세요.<br>"
                    "⚠️ <strong>주의:</strong> 연동 해제나 네트워크 장애 등으로 인한 데이터 유실에 대해서는 책임지지 않으므로, 중요 데이터는 주기적으로 백업 및 보관하시기 바랍니다.",
                
                    "<strong>Non-members can also preview and fill out the online survey form.</strong><br>"
                    "Once you sign up and log in from the left sidebar, the contents you have written will be maintained and you can deploy immediately. (Free members can also use all features without restriction)<br><br>"
                    "Response data is stored in your linked Google Spreadsheet. Please test data recording before deploying the survey.<br>"
                    "⚠️ <strong>Caution:</strong> We are not responsible for data loss due to unlinking or network failures. Please backup your important data periodically."
                )
            else:
                msg = _(
                    "응답 데이터는 연동하신 구글 스프레드시트에 저장됩니다. 배포 전 데이터가 정상 기록되는지 반드시 테스트해 주세요.<br>"
                    "⚠️ <strong>주의:</strong> 연동 해제나 네트워크 장애 등으로 인한 데이터 유실에 대해서는 책임지지 않으므로, 중요 데이터는 주기적으로 백업 및 보관하시기 바랍니다.",
                
                    "Response data is stored in your linked Google Spreadsheet. Please test data recording before deploying the survey.<br>"
                    "⚠️ <strong>Caution:</strong> We are not responsible for data loss due to unlinking or network failures. Please backup your important data periodically."
                )
            st.markdown(f"{box_style}{msg}</div>", unsafe_allow_html=True)
            def render_section_header(title):
                style = (
                    'background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);'
                    'color: #ffffff;'
                    'padding: 12px 20px;'
                    'border-radius: 6px;'
                    'font-weight: bold;'
                    'font-size: 1.1rem;'
                    'text-align: center;'
                    'letter-spacing: 0.5px;'
                    'margin-top: 25px;'
                    'margin-bottom: 15px;'
                    'box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);'
                    'border: 1px solid #334155;'
                )
                st.markdown(f'<div style="{style}">{title}</div>', unsafe_allow_html=True)

            col_survey_main, col_survey_settings = st.columns([3.0, 1.1], gap="large")
            with col_survey_settings:
                with st.container(border=True):
                    st.markdown(f'<h4 style="color:black; font-family:Arial, sans-serif; font-weight:bold; margin-top:0; margin-bottom:15px; font-size:1.1rem;">{_("내 설문 관리", "My Survey Management")}</h4>', unsafe_allow_html=True)

                    # 설문 ID로 가져오기 (공유받은 설문 연결)
                    with st.expander(_("🔗 설문 ID로 가져오기", "Import Survey by ID")):
                        _import_sid = st.text_input(_("설문 ID 입력", "Enter Survey ID"), key="import_survey_id_input", placeholder="예: 1NkDZ2NEirWepjTPubG1DZ4weR0wbrWX_GfZwS0mAKl8")
                        if st.button(_("가져오기", "Import"), key="import_survey_btn"):
                            if _import_sid and _import_sid.strip():
                                _import_sid = _import_sid.strip()
                                try:
                                    import sqlite3
                                    from datetime import datetime
                                    # 설문 존재 여부 확인 (구글 시트 메타데이터)
                                    from survey_manager import load_survey_metadata
                                    _meta = load_survey_metadata(_import_sid)
                                    if _meta:
                                        _title = _meta.get("Title", _import_sid[:8])
                                        conn = sqlite3.connect('users.db')
                                        cur = conn.cursor()
                                        cur.execute("CREATE TABLE IF NOT EXISTS admin_surveys (survey_id TEXT PRIMARY KEY, admin_id TEXT, title TEXT, created_at TEXT)")
                                        cur.execute("INSERT OR REPLACE INTO admin_surveys (survey_id, admin_id, title, created_at) VALUES (?, ?, ?, ?)",
                                                    (_import_sid, st.session_state.user_id, _title, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                                        conn.commit()
                                        conn.close()
                                        st.session_state._survey_cache_dirty = True
                                        st.session_state.pop('_cached_user_surveys', None)
                                        st.success(_("설문을 가져왔습니다.", "Survey imported."))
                                        st.rerun()
                                    else:
                                        st.error(_("설문을 찾을 수 없습니다. ID를 확인해주세요.", "Survey not found. Please check the ID."))
                                except Exception as e:
                                    st.error(f"{_('오류 발생', 'Error')}: {e}")
                            else:
                                st.warning(_("설문 ID를 입력해주세요.", "Please enter a survey ID."))

                    # Initialize states
                    if 'editing_survey_id' not in st.session_state:
                        st.session_state.editing_survey_id = None
                    if 'survey_auto_loaded' not in st.session_state:
                        st.session_state.survey_auto_loaded = False

                    # Check existing surveys (SQLite와 구글 시트 모두 조회하여 병합) — 세션 캐싱
                    if st.session_state.get('_cached_user_id') != st.session_state.user_id:
                        st.session_state._cached_user_id = st.session_state.user_id
                        st.session_state.pop('_cached_user_surveys', None)
                        st.session_state._survey_cache_dirty = True
                        st.session_state.survey_auto_loaded = False
                        st.session_state.editing_survey_id = None
                        st.session_state.pop('tab2_tier_choice', None)
                        for k in [k for k in list(st.session_state.keys()) if k.startswith('edit_') or k.startswith('sub_sub_') or k.startswith('survey_image_') or k.startswith('tq_')]:
                            del st.session_state[k]

                    if '_cached_user_surveys' not in st.session_state or st.session_state.get('_survey_cache_dirty'):
                        sqlite_surveys = []
                        try:
                            import sqlite3
                            conn = sqlite3.connect('users.db')
                            cur = conn.cursor()
                            cur.execute("SELECT survey_id, title, created_at FROM admin_surveys WHERE admin_id = ? ORDER BY created_at DESC", (st.session_state.user_id,))
                            sqlite_surveys = cur.fetchall()
                            conn.close()
                        except Exception:
                            pass

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
                        user_surveys = list(merged_surveys.values())
                        user_surveys.sort(key=lambda x: x[2], reverse=True)
                        st.session_state._cached_user_surveys = user_surveys
                        st.session_state._cached_user_id = st.session_state.user_id
                        st.session_state._survey_cache_dirty = False
                    else:
                        user_surveys = st.session_state._cached_user_surveys

                    has_survey = len(user_surveys) > 0

                    # Auto-load logic
                    if has_survey and not st.session_state.survey_auto_loaded:
                        sel_id = user_surveys[0][0] # Load the most recent one
                        from survey_manager import load_survey_metadata
                        meta = load_survey_metadata(sel_id)
                        if meta:
                            st.session_state.editing_survey_id = sel_id
                            st.session_state.edit_title = meta.get("Title", "")
                            st.session_state.edit_desc = meta.get("Description", "")
                            st.session_state.edit_admin_email = meta.get("Admin_Email", "")
                        
                            try:
                                from survey_manager import get_survey_images_with_fallback
                                imgs_loaded = get_survey_images_with_fallback(sel_id, user_id=st.session_state.user_id)
                                for idx_num, suf in [(1, ""), (2, "2"), (3, "3")]:
                                    d, m = imgs_loaded.get(idx_num, (None, None))
                                    if d:
                                        st.session_state[f"edit_survey_image{suf}"] = d
                                        st.session_state[f"edit_survey_image_mime{suf}"] = m or "image/png"
                                    else:
                                        st.session_state.pop(f"edit_survey_image{suf}", None)
                                        st.session_state.pop(f"edit_survey_image_mime{suf}", None)
                            except Exception:
                                for suf in ["", "2", "3"]:
                                    st.session_state.pop(f"edit_survey_image{suf}", None)
                                    st.session_state.pop(f"edit_survey_image_mime{suf}", None)


                            demo = meta.get("Demographics", {})
                            st.session_state.edit_type_question = demo.get("type_question", "")
                            st.session_state.edit_type_options = ", ".join(demo.get("type_options", []))
                            if "type_questions" in demo:
                                tqs = []
                                for idx_tq, tq in enumerate(demo["type_questions"]):
                                    opts_str = ", ".join(tq.get("opts", [])) if isinstance(tq.get("opts", []), list) else tq.get("opts", "")
                                    q_str = tq.get("q", "")
                                    qtype_str = tq.get("q_type", "radio")
                                    tqs.append({
                                        "q": q_str,
                                        "opts": opts_str,
                                        "q_type": qtype_str  # 객관식/주관식 복원
                                    })
                                    st.session_state[f"tq_q_{idx_tq}"] = q_str
                                    st.session_state[f"tq_opts_{idx_tq}"] = opts_str
                                    st.session_state[f"tq_qtype_{idx_tq}"] = _("✏️ 주관식 (직접 입력)", "✏️ Open-ended (Text)") if qtype_str == "text" else _("📋 객관식 (보기 선택)", "📋 Multiple Choice (Radio)")
                                st.session_state.edit_type_questions = tqs
                            st.session_state.edit_demo_gender = demo.get("gender", False)
                            st.session_state.edit_demo_aff = demo.get("affiliation", False)
                            st.session_state.edit_demo_email = demo.get("email", False)
                            st.session_state.edit_demo_name = demo.get("name", False)
                            st.session_state.edit_demo_age = demo.get("age", False)
                            st.session_state.edit_demo_exp = demo.get("experience", False)
                            st.session_state.edit_age_type = demo.get("age_type", "개방형 (숫자 직접 입력)")
                            st.session_state.edit_exp_type = demo.get("experience_type", "개방형 (숫자 직접 입력)")

                            st.session_state.edit_scale_type = meta.get("Scale_Type", "1-9 Continuous")
                            cr_limit_raw = meta.get("CR_Limit", 0.1)
                            st.session_state.edit_cr_limit = float(cr_limit_raw) if cr_limit_raw is not None and str(cr_limit_raw).lower() != "none" else None
                            cr_guide_raw = meta.get("CR_Guide_Method", "realtime" if str(meta.get("CR_Guide_Enabled", "False")).lower() == "true" else "none")
                            st.session_state.edit_cr_guide_method = cr_guide_raw

                            # [신규] 계층 구조 다이어그램 표시 옵션 복원
                            show_h_raw = meta.get("Show_Hierarchy", True)
                            if isinstance(show_h_raw, str):
                                show_h_raw = (show_h_raw.lower() != "false")
                            st.session_state.edit_show_hierarchy = bool(show_h_raw)
                            st.session_state.pop("tab2_show_hierarchy_choice", None)

                            ahp_model = meta.get("AHP_Model_JSON", {})
                            st.session_state.edit_main_input = ", ".join(ahp_model.get("main", []))
                            st.session_state.edit_sub_inputs = {}
                            for mc, subs in ahp_model.get("subs", {}).items():
                                st.session_state.edit_sub_inputs[mc] = ", ".join(subs)

                            # [신규] 3계층 소분류(sub_subs) 및 Tier_Level 복원
                            sub_subs_map = ahp_model.get("sub_subs", {})
                            st.session_state.edit_sub_sub_inputs = {}
                            for sub_c, sub_subs in sub_subs_map.items():
                                joined = ", ".join(sub_subs) if isinstance(sub_subs, list) else str(sub_subs)
                                st.session_state.edit_sub_sub_inputs[sub_c] = joined
                                st.session_state[f"sub_sub_{sub_c}"] = joined

                            raw_tier = meta.get("Tier_Level")
                            if raw_tier is not None:
                                try:
                                    tier_val = int(raw_tier)
                                except Exception:
                                    tier_val = 3 if len(sub_subs_map) > 0 else 2
                            else:
                                tier_val = 3 if len(sub_subs_map) > 0 else 2

                            st.session_state.edit_tier_level = tier_val
                            tier_choice_label = _("3계층 (대분류 ➔ 중분류 ➔ 소분류)", "3-Tier (Main ➔ Sub ➔ Sub-sub)") if tier_val == 3 else _("2계층 (대분류 ➔ 중분류)", "2-Tier (Main ➔ Sub)")
                            st.session_state["tab2_tier_choice"] = tier_choice_label

                            # [2026-10-20] 대안 목록 복원
                            _edit_alts = ahp_model.get("alternatives", [])
                            st.session_state.edit_alternatives_input = ", ".join(_edit_alts) if isinstance(_edit_alts, list) else str(_edit_alts)
                            st.session_state.pop("tab2_alt_input", None)
                            st.session_state.pop("tab2_use_alt", None)

                            definitions = meta.get("Definitions", {})
                            st.session_state.edit_definitions = definitions
                            st.session_state.edit_alt_guide = meta.get("Alt_Guide", "") or ""
                        st.session_state.survey_auto_loaded = True
                        st.rerun()

                    @st.dialog(_("🚨 [경고] 기존 설문 영구 삭제 안내", "🚨 [Warning] Permanent Deletion of Existing Survey"))
                    def confirm_new_survey():
                        st.error(_("새로운 설문을 작성하시면 기존 연동된 구글 시트에 저장된 **모든 데이터(설문 구조, 문항, 수집된 전체 응답 결과)가 즉시 삭제되며 절대 복구할 수 없습니다.**", "If you create a new survey, **ALL data saved in the linked Google Sheet (survey structure, questions, collected responses) will be immediately deleted and CANNOT be recovered.**"))
                        st.info(_("**데이터 보존 안내:** 기존 설문의 응답 결과 보존을 원하신다면, 삭제에 동의하시기 전에 구글 스프레드시트에 접속하여 **[파일] -> [다운로드]** 메뉴를 통해 엑셀(.xlsx) 파일 등으로 백업본을 사용자 컴퓨터에 미리 다운로드해 두시기 바랍니다.", "**Data Preservation Guide:** If you wish to keep the existing responses, please go to the Google Spreadsheet and use the **[File] -> [Download]** menu to download a backup copy (e.g., .xlsx) to your computer before agreeing to delete."))
                        agree = st.checkbox(_("네, 기존 데이터 백업을 완료했거나 불필요하며, 모든 데이터 삭제에 동의합니다.", "Yes, I have backed up or do not need the existing data, and I agree to delete all data."))
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button(_("❌ 취소", "❌ Cancel"), use_container_width=True):
                                st.rerun()
                        with col2:
                            if st.button(_("✅ 동의 및 초기화", "✅ Agree & Initialize"), type="primary", use_container_width=True, disabled=not agree):
                                with st.spinner(_("기존 데이터를 삭제하는 중입니다...", "Deleting existing data...")):
                                    from survey_manager import delete_admin_survey
                                    if user_surveys:
                                        delete_admin_survey(user_surveys[0][0], st.session_state.user_id)
                                    st.session_state.editing_survey_id = None
                                    st.session_state.pop('tab2_tier_choice', None)
                                    keys_to_clear = [k for k in st.session_state.keys() if k.startswith('edit_') or k.startswith('sub_sub_') or k.startswith('survey_image_') or k.startswith('tq_')]
                                    for k in keys_to_clear:
                                        del st.session_state[k]
                                    st.session_state.survey_auto_loaded = True
                                    st.session_state._survey_cache_dirty = True
                                st.success(_("완료되었습니다. 화면이 새로고침됩니다.", "Completed. The screen will be refreshed."))
                                import time
                                time.sleep(1.5)
                                st.rerun()

                    linked_sheet_id = st.session_state.get("editing_survey_id")
                    if linked_sheet_id:
                        survey_title_display = st.session_state.get("edit_title", "")
                        for s in user_surveys:
                            if s[0] == linked_sheet_id:
                                survey_title_display = s[1]
                                break
                        st.success(_(f" 현재 배포된 설문을 불러왔습니다: **{survey_title_display}**", f" Loaded deployed survey: **{survey_title_display}**"))
                        _deployed_url = f"https://ahpkrj.streamlit.app/?mode=survey&survey_id={linked_sheet_id}"
                        st.link_button(_("🌐 배포된 설문 보기", "View Deployed Survey"), _deployed_url)

                        # [신규] 연동된 구글 시트 바로가기 및 온라인 설문 링크 제시
                        base_url = st.query_params.get("base_url", ["https://ahpkrj.streamlit.app/"])[0] if isinstance(st.query_params.get("base_url"), list) else "https://ahpkrj.streamlit.app/"
                        if "localhost" in base_url or "127.0.0.1" in base_url:
                            active_survey_url = f"{base_url}?survey_id={linked_sheet_id}"
                        else:
                            active_survey_url = f"https://ahpkrj.streamlit.app/?survey_id={linked_sheet_id}"

                        st.markdown(_("##### 🌐 온라인 설문지 링크 (응답자 배포용)", "##### 🌐 Online Survey Link (For Distribution)"))
                        st.code(active_survey_url, language="text")
                        st.caption(_("💡 위 설문 링크를 복사하여 이메일이나 메신저로 응답 대상자에게 전달하세요.", "💡 Copy the survey link above and send it to respondents via email or messenger."))
                        st.markdown(_(
                            "<span style='font-size:14px; color:rgba(49,51,63,0.6);'>💡 실제 조사 배포 전 테스트 응답을 <b style='color:#d32f2f;'>반드시 삭제</b>하세요.</span>",
                            "<span style='font-size:14px; color:rgba(49,51,63,0.6);'>💡 Before distributing for actual survey, <b style='color:#d32f2f;'>be sure to delete</b> test responses.</span>"
                        ), unsafe_allow_html=True)

                        gs_link = f"https://docs.google.com/spreadsheets/d/{linked_sheet_id}"
                        btn_label = _("연동된 구글 시트 바로가기", "Open Linked Google Sheet")
                        # [2026-10-19] st.link_button으로 변경 — 아래 버튼들과 곡률/스타일 완전 동일
                        st.link_button(f"\U0001F4CA {btn_label}", gs_link, use_container_width=True)

                    if st.button(_("✨ 처음부터 새 설문 작성하기", "✨ Start a new survey from scratch"), type="secondary", use_container_width=True):
                        confirm_new_survey()
                    if linked_sheet_id and st.button(_("🗑️ 응답 데이터만 초기화", "🗑️ Reset Response Data Only"), type="secondary", use_container_width=True):
                        show_reset_survey_dialog(linked_sheet_id, survey_title_display)

                    st.divider()

                    # [신규] URL 단축 및 QR코드 생성 지원 서비스 링크 (가로줄 밑 상시 배치)
                    st.markdown(_("###### 🔗 설문 배포 유용한 도구", "###### 🔗 Useful Distribution Tools"))
                    st.markdown(_(
                        "• **긴 URL 단축**: [buly.kr 바로가기 ↗️](https://buly.kr/)\n\n"
                        "• **QR코드 생성**: [qr.naver.com 바로가기 ↗️](https://qr.naver.com/)",
                        "• **Shorten Long URL**: [buly.kr ↗️](https://buly.kr/)\n\n"
                        "• **Generate QR Code**: [qr.naver.com ↗️](https://qr.naver.com/)"
                    ))

                    from survey_manager import create_survey_sheet

                    # 하위 탭을 나누지 않고 하나의 연결된 페이지로 구성

            with col_survey_main:
                # 5개 섹션 설문지 생성 폼 구성
                # 섹션 1: 기본 정보
                render_section_header(_("섹션 1: 설문 기본 정보 설정", "Section 1: Survey Basic Info Setup"))
                default_survey_title = _("제조용 협동로봇 도입 요인 중요도 분석을 위한 전문가 AHP 설문", "Expert AHP Survey on the Importance of Factors for Adopting Manufacturing Collaborative Robots")
                st.markdown(f"**{_('설문지 제목', 'Survey Title')}**")
                survey_title = st.text_input(_('설문지 제목', 'Survey Title'), value=st.session_state.get("edit_title", default_survey_title), label_visibility="collapsed")
        
                default_survey_desc_ko = """[조사 목적 및 안내문]

안녕하십니까?
본 설문조사는 [연구/프로젝트 주제]에 관한 주요 요인들의 상대적 중요도를 도출하기 위해 
전문가(또는 실무자) 여러분의 고견을 수렴하고자 마련되었습니다.

바쁘시더라도 잠시 시간을 내어 귀하의 귀중한 의견을 응답해 주시면 연구에 큰 도움이 될 것입니다.

■ 조사 목적 : [연구/프로젝트 목적 기재]
■ 조사 내용 : [조사 대상 요인] 간의 AHP(쌍대비교) 평가
■ 조사 기간 : 202X년 X월 X일 ~ 202X년 X월 X일
■ 개인정보 보호 :
  - 본 조사를 통해 수집된 모든 자료는 통계법 제33조(비밀의 보호)에 의거하여 철저히 보호되며, 
    오직 연구 및 통계 분석 목적으로만 활용됩니다.
  - 응답해주신 개인 정보 및 개별 응답 결과는 절대 외부로 유출되지 않음을 약속드립니다.

귀하의 소중한 참여에 깊은 감사를 드립니다.

- 연구 책임자 : [이름 기재]
- 문의처 : [연락처 또는 이메일 기재]"""

                default_survey_desc_en = """[Survey Purpose & Instructions]

Greetings,
This survey is designed to gather the opinions of experts (or practitioners) to derive the relative importance 
of major factors regarding [Research/Project Topic].

Even if you are busy, taking a moment to provide your valuable input will be of great help to our research.

■ Purpose : [Enter Research/Project Purpose]
■ Content : AHP (Pairwise Comparison) evaluation among [Factors to be Surveyed]
■ Period : [Start Date] ~ [End Date]
■ Privacy :
  - All data collected through this survey is strictly protected under Article 33 (Protection of Secrets) 
    of the Statistics Act and will be used solely for research and statistical analysis purposes.
  - We promise that your personal information and individual responses will never be leaked externally.

Thank you deeply for your valuable participation.

- Lead Researcher : [Enter Name]
- Contact : [Enter Phone or Email]"""

                st.markdown(f"**{_('조사 목적 및 안내문', 'Survey Purpose & Instructions')}**")
            
                from quill_editor import st_quill
                survey_desc = st_quill(
                    value=st.session_state.get("edit_desc", _(default_survey_desc_ko, default_survey_desc_en)),
                    key="quill_standard_desc_editor"
                )
                if survey_desc is None:
                    survey_desc = st.session_state.get("edit_desc", _(default_survey_desc_ko, default_survey_desc_en))
                st.session_state["edit_desc"] = survey_desc
            
                is_edit_mode = bool(st.session_state.get("editing_survey_id"))
                if not is_edit_mode:
                    if "edit_admin_email" not in st.session_state:
                        st.session_state["edit_admin_email"] = ""
                    elif st.session_state.get("edit_admin_email") in [st.session_state.user_id, "jeon080423@gmail.com"]:
                        st.session_state["edit_admin_email"] = ""
                else:
                    if "edit_admin_email" not in st.session_state:
                        st.session_state["edit_admin_email"] = ""

                # 레거시 더미 이메일(@ahpmaster.com) 정리
                if str(st.session_state.get("edit_admin_email", "")).strip().lower().endswith("@ahpmaster.com"):
                    st.session_state["edit_admin_email"] = ""

                st.write("")
                st.markdown(f"**{_('설문 담당자 문의 이메일', 'Survey Administrator Contact Email')}**")
                survey_admin_email = st.text_input(
                    _('설문 담당자 문의 이메일', 'Survey Administrator Contact Email'),
                    value=st.session_state.get("edit_admin_email", ""),
                    placeholder=_("예: researcher@university.ac.kr (미입력 시 설문지에 문의처가 표시되지 않습니다)", "e.g., researcher@university.ac.kr (Leave blank to hide)"),
                    label_visibility="collapsed"
                )
                st.session_state["edit_admin_email"] = survey_admin_email

                st.write("")
                # 응답자 수집 정보 및 그룹 분류 설정 (섹션 1로 통합)

                # 그룹 분류 문항 설정
                st.markdown(f"**{_('그룹 분류 문항 설정', 'Group Classification Setup')}**")
                st.caption(_("📌 각 문항마다 객관식(보기 선택) 또는 주관식(직접 입력) 중 원하는 방식을 선택하세요. 최대 5개 문항을 추가할 수 있습니다.", "📌 Choose between multiple-choice (radio) or open-ended (text) format for each question. Up to 5 questions can be added."))
            
                default_type_q = _("귀하의 소속은 어떻게 되십니까?", "What is your affiliation?")
                default_type_opts = _("전문가, 일반, 공무원, 기타", "Expert, General, Public Official, Other")
            
                if "edit_type_questions" not in st.session_state:
                    legacy_q = st.session_state.get("edit_type_question", "")
                    legacy_opts = st.session_state.get("edit_type_options", "")
                    # 저장된 값이 존재하면 그대로 사용 (문자열 동등 비교로 기본값 강제 교체하지 않음)
                    init_q = legacy_q if legacy_q else default_type_q
                    init_opts = legacy_opts if legacy_opts else default_type_opts
                    st.session_state["edit_type_questions"] = [{"q": init_q, "opts": init_opts, "q_type": "radio"}]

                type_questions_state = st.session_state["edit_type_questions"]
                num_types = len(type_questions_state)
            
                col1, col2, col3 = st.columns([6, 2, 2])
                with col2:
                    if st.button(_("➕ 문항 추가", "➕ Add Question"), use_container_width=True, disabled=num_types >= 5):
                        st.session_state["edit_type_questions"].append({"q": "", "opts": "", "q_type": "radio"})
                        st.rerun()
                with col3:
                    if st.button(_("➖ 문항 삭제", "➖ Remove"), use_container_width=True, disabled=num_types <= 1):
                        st.session_state["edit_type_questions"].pop()
                        st.rerun()
            
                type_questions = []
                for i in range(num_types):
                    with st.container(border=True):
                        if i == 0:
                            q_label = _("그룹 분류 질문 제목", "Group Classification Question Title")
                        else:
                            q_label = _("추가 설문 문항", "Additional Survey Question")
                    
                        # --- 객관식/주관식 선택 (직관적 토글) ---
                        cur_q_type = type_questions_state[i].get("q_type", "radio")
                        qtype_options = [_("📋 객관식 (보기 선택)", "📋 Multiple Choice (Radio)"), _("✏️ 주관식 (직접 입력)", "✏️ Open-ended (Text)")]
                        qtype_default_idx = 1 if cur_q_type == "text" else 0
                        q_type_sel = st.radio(
                            _(f"문항 {i+1} 응답 방식", f"Question {i+1} Answer Type"),
                            qtype_options,
                            index=qtype_default_idx,
                            horizontal=True,
                            key=f"tq_qtype_{i}"
                        )
                        q_type_val = "text" if _("주관식", "Open-ended") in q_type_sel else "radio"
                        type_questions_state[i]["q_type"] = q_type_val

                        q_val = st.text_input(q_label + f" ({i+1})", value=type_questions_state[i].get("q", ""), key=f"tq_q_{i}")
                        type_questions_state[i]["q"] = q_val

                        if q_type_val == "radio":
                            opts_label = _("보기 옵션 (쉼표로 구분)", "Options (comma-separated)")
                            cur_opts = type_questions_state[i].get("opts", "")
                            opts_val = st.text_input(opts_label + f" ({i+1})", value=cur_opts, key=f"tq_opts_{i}", placeholder=_("예: 전문가, 일반, 공무원, 기타", "e.g. Expert, General, Official, Other"))
                            type_questions_state[i]["opts"] = opts_val
                            opts_list = [x.strip() for x in opts_val.split(",") if x.strip()]
                        else:
                            # 주관식: 보기 입력란 숨김, opts를 빈 리스트로 저장
                            type_questions_state[i]["opts"] = ""
                            opts_list = []
                            st.caption(_("💡 주관식: 응답자가 자유롭게 텍스트를 입력하는 방식입니다. 설문 응답 시 내용 입력칸 오른쪽에 '모름/비해당' 라디오 버튼이 함께 제공됩니다.", "💡 Open-ended: Respondents type their own answer freely. A 'Don't know / Not applicable' option is provided to the right of the input box."))

                        type_questions.append({
                            "q": q_val,
                            "opts": opts_list,
                            "q_type": q_type_val
                        })
            
                type_question = type_questions[0]["q"] if type_questions else ""
                type_options = ", ".join(type_questions[0]["opts"]) if type_questions else ""


                # 인구통계학 정보 설정
                st.markdown(f"**{_('인구통계학적 문항 수집 설정', 'Demographic Questions Setup')}**")
                demo_name = st.checkbox(_("이름 수집", "Collect Name"), value=st.session_state.get("edit_demo_name", False))
                demo_gender = st.checkbox(_("성별 수집", "Collect Gender"), value=st.session_state.get("edit_demo_gender", True))
                demo_email = st.checkbox(_("이메일 수집", "Collect Email"), value=st.session_state.get("edit_demo_email", True))
                if demo_email:
                    st.caption(_("💡 설문 응답자에게 '직접 입력' 및 '응답거절' 라디오 버튼이 제공되며, 거절 시 '응답거절'로 수집됩니다.", "💡 Respondents are provided with 'Enter directly' and 'Refuse to respond' options. Refusals will be collected as 'Refuse to respond'."))




                demo_age = st.checkbox(_("연령 수집", "Collect Age"), value=st.session_state.get("edit_demo_age", False))
                age_type = "개방형 (숫자 직접 입력)"
                if demo_age:
                    age_type_options = [_("개방형 (숫자 직접 입력)", "Open-ended (Type Number)"), _("10세 단위 선택형", "Multiple Choice (10-year intervals)")]
                    age_type = st.radio(_("연령 수집 방식", "Age Collection Method"), age_type_options, index=0 if st.session_state.get("edit_age_type", "개방형 (숫자 직접 입력)") == "개방형 (숫자 직접 입력)" else 1, horizontal=True, key="survey_age_type_setup")




                demo_exp = st.checkbox(_("경력년수 수집", "Collect Years of Experience"), value=st.session_state.get("edit_demo_exp", False))
                exp_type = "개방형 (숫자 직접 입력)"
                if demo_exp:
                    exp_type_options = [_("개방형 (숫자 직접 입력)", "Open-ended (Type Number)"), _("5년 단위 선택형", "Multiple Choice (5-year intervals)")]
                    exp_type = st.radio(_("경력년수 수집 방식", "Experience Collection Method"), exp_type_options, index=0 if st.session_state.get("edit_exp_type", "개방형 (숫자 직접 입력)") == "개방형 (숫자 직접 입력)" else 1, horizontal=True, key="survey_exp_type_setup")

                demographics_settings = {
                    "name": demo_name,
                    "age": demo_age,
                    "age_type": age_type,
                    "gender": demo_gender,
                    "experience": demo_exp,
                    "experience_type": exp_type,
                    "affiliation": False,  # 소속 수집 삭제
                    "email": demo_email,
                    "type_question": type_question,
                    "type_options": [x.strip() for x in type_options.split(",") if x.strip()],
                    "type_questions": type_questions
                }






                with st.container():
                    # 섹션 2: 설문 조사 설명 이미지 삽입 (최대 3개, 선택사항)
                    render_section_header(_("섹션 2: 설문 조사 설명 이미지 삽입", "Section 2: Survey Description Image Insertion"))
                    st.markdown(_("설문 응답자에게 보여줄 설명 이미지(예: 구조도, 안내문 등)가 있다면 아래에 업로드해 주세요. (선택사항, 최대 3개)", "If you have description images (e.g., structure diagram, guide) to show to the survey respondents, please upload them below. (Optional, up to 3)"))
                
                    has_img1 = bool(st.session_state.get("survey_image_data") or st.session_state.get("edit_survey_image"))
                    has_img2 = bool(st.session_state.get("survey_image_data2") or st.session_state.get("edit_survey_image2"))
                    has_img3 = bool(st.session_state.get("survey_image_data3") or st.session_state.get("edit_survey_image3"))

                    tag1 = _(" (등록됨)", " (Uploaded)") if has_img1 else _(" (선택)", " (Optional)")
                    tag2 = _(" (등록됨)", " (Uploaded)") if has_img2 else _(" (선택)", " (Optional)")
                    tag3 = _(" (등록됨)", " (Uploaded)") if has_img3 else _(" (선택)", " (Optional)")

                    img_tabs = st.tabs([
                        _("📷 설명 이미지 1", "📷 Image 1") + tag1,
                        _("📷 설명 이미지 2", "📷 Image 2") + tag2,
                        _("📷 설명 이미지 3", "📷 Image 3") + tag3
                    ])

                    for idx_num, cur_tab in enumerate(img_tabs, 1):
                        suf = "" if idx_num == 1 else str(idx_num)
                        data_key = f"survey_image_data{suf}"
                        mime_key = f"survey_image_mime{suf}"
                        edit_key = f"edit_survey_image{suf}"
                        edit_mime_key = f"edit_survey_image_mime{suf}"
                        uploader_key = f"survey_image_uploader_{idx_num}"

                        with cur_tab:
                            f_up = st.file_uploader(
                                _(f"설문 설명 이미지 {idx_num} 업로드 (png, jpg, jpeg)", f"Upload Survey Description Image {idx_num} (png, jpg, jpeg)"),
                                type=["png", "jpg", "jpeg"],
                                key=uploader_key
                            )
                            if f_up is not None:
                                # 원본 보관 (자동 크기 맞춤의 기준 이미지)
                                _raw_bytes = f_up.getvalue()
                                st.session_state[f"survey_image_raw{suf}"] = _raw_bytes
                                st.session_state.pop(edit_key, None)
                                st.session_state.pop(edit_mime_key, None)
                                # 수동 미세조정 배율 (자동 감지 결과에 곱해져 저장됨)
                                _manual_key = f"survey_image_manual{suf}"
                                _manual = st.slider(
                                    _("🔍 이미지 크기 미세조정 (1.0 = 자동 감지 크기 그대로)", "🔍 Fine-tune image size (1.0 = auto-detected size)"),
                                    min_value=0.70, max_value=1.30,
                                    value=float(st.session_state.get(_manual_key, 1.0)),
                                    step=0.05, key=_manual_key,
                                )
                                # 자동 감지 배율 × 수동 배율로 리사이즈 후 저장.
                                # 응답자 화면 표시 시점에도 자동 감지가 적용되나,
                                # 이미 맞춰진 이미지라 배율이 ≈1.0으로 수렴해 이중 적용되지 않음.
                                try:
                                    from image_text_scale import apply_text_size_match as _its_apply
                                    from image_text_scale import detect_text_scale as _its_detect
                                    _baked, _baked_mime, _bw, _bh, _bs = _its_apply(_raw_bytes, manual_mult=_manual)
                                    _auto_scale = _its_detect(_raw_bytes)
                                except Exception:
                                    _baked, _baked_mime, _bw, _bh = _raw_bytes, (f_up.type or "image/png"), 0, 0
                                    _auto_scale = 1.0
                                st.session_state[data_key] = _baked
                                st.session_state[mime_key] = _baked_mime
                                import base64
                                encoded = base64.b64encode(_baked).decode()
                                _pv_style = f"width: {_bw}px; max-width: 100%; height: auto; border-radius: 8px;" if _bw > 0 else "max-width: 100%; height: auto; border-radius: 8px;"
                                html_str = f'<div style="text-align: center; margin-bottom: 10px;"><img src="data:{_baked_mime};base64,{encoded}" style="{_pv_style}"></div>'
                                st.markdown(html_str, unsafe_allow_html=True)
                                st.caption(_(f"업로드된 이미지 {idx_num} 미리보기 — 응답자에게 보이는 크기와 동일 (자동 조정 배율 {_auto_scale:.2f}×)", f"Uploaded image {idx_num} preview — same size respondents will see (auto scale {_auto_scale:.2f}×)"))
                            elif st.session_state.get(edit_key):
                                st.session_state[data_key] = st.session_state[edit_key]
                                st.session_state[mime_key] = st.session_state.get(edit_mime_key, 'image/png')
                                import base64
                                encoded = base64.b64encode(st.session_state[data_key]).decode()
                                mime = st.session_state[mime_key]
                                html_str = f'<div style="text-align: center; margin-bottom: 10px;"><img src="data:{mime};base64,{encoded}" style="max-width: 100%; height: auto; max-height: 400px; width: auto; border-radius: 8px;"></div>'
                                st.markdown(html_str, unsafe_allow_html=True)
                                st.caption(_(f"기존 등록된 이미지 {idx_num} 미리보기", f"Previously Registered Image {idx_num} Preview"))
                                if st.button(_(f"🗑️ 기존 이미지 {idx_num} 삭제", f"🗑️ Delete Existing Image {idx_num}"), key=f"del_img_btn_{idx_num}"):
                                    st.session_state.pop(edit_key, None)
                                    st.session_state.pop(edit_mime_key, None)
                                    st.session_state.pop(data_key, None)
                                    st.session_state.pop(mime_key, None)
                                    st.session_state.pop(f"survey_image_raw{suf}", None)
                                    st.rerun()
                            else:
                                st.session_state.pop(data_key, None)
                                st.session_state.pop(mime_key, None)
                                st.session_state.pop(f"survey_image_raw{suf}", None)

                with st.container():
                    # 섹션 3: AHP 모델 계층구조 입력 폼
                    render_section_header(_("섹션 3: AHP 요인 계층구조 및 문항 설정", "Section 3: AHP Criteria Hierarchy & Question Setup"))

                    # 계층 구조 선택 (2계층 기준과 동일하게 전체 공개)
                    tier_choice_options = [
                        _("2계층 (대분류 ➔ 중분류)", "2-Tier (Main ➔ Sub)"),
                        _("3계층 (대분류 ➔ 중분류 ➔ 소분류)", "3-Tier (Main ➔ Sub ➔ Sub-sub)")
                    ]
                    loaded_tier = st.session_state.get("edit_tier_level", 2)
                    default_tier_idx = 1 if loaded_tier == 3 else 0

                    if "tab2_tier_choice" in st.session_state and st.session_state["tab2_tier_choice"] not in tier_choice_options:
                        del st.session_state["tab2_tier_choice"]

                    st.markdown(_("#####  계층 구조 레벨 선택", "#####  Select Hierarchy Level"))
                    tier_choice_tab2 = st.radio(
                        _("설문 모델의 계층 깊이를 선택하세요.", "Select the hierarchy depth for your survey model."),
                        tier_choice_options,
                        index=default_tier_idx,
                        horizontal=True,
                        key="tab2_tier_choice"
                    )
                    tier_level = 3 if _("3계층", "3-Tier") in tier_choice_tab2 else 2



                    st.info(_(
                        "💡 현재 입력된 요인은 **예시**일 뿐이며, 사용자의 연구 모델에 맞추어 내용을 모두 수정하여 사용할 수 있습니다.\n\n"
                        "- 대분류 및 하위 요인은 반드시 **쉼표(,)** 로 구분하여 입력해 주세요.\n"
                        "- 요인명에 언더바(`_`) 기호는 시스템 내부 처리와 충돌하므로 사용할 수 없습니다. (입력 시 자동으로 공백으로 변환됩니다.)",
                        "💡 The current criteria are just **examples**. You can freely modify them to fit your research model.\n\n"
                        "- Separate Main and Sub criteria using **commas(,)**.\n"
                        "- Do not use underscores (`_`) in criteria names. (They will be automatically converted to spaces.)"
                    ))

                    default_tab2_main = _("기능성, 디자인, 경제성", "Functionality, Design, Economy") if tier_level == 3 else _("기술 요인, 조직 요인, 환경 요인, 혁신 요인", "Technological, Organizational, Environmental, Innovational")
                    main_input = st.text_input(_("대항목 (Main Criteria)", "Main Criteria"), value=st.session_state.get("edit_main_input", default_tab2_main))
                    main_list = [x.strip().replace("_", " ") for x in main_input.split(",") if x.strip()]
                    if len(main_list) <= 1:
                        st.markdown(_("🚨 :red[**경고:** 쌍대비교를 위해서는 대항목 요인이 최소 2개 이상 입력되어야 합니다.]", "🚨 :red[**Warning:** At least 2 Main Criteria are required for pairwise comparison.]"))

                    model_structure = {"main": main_list, "subs": {}}
                    if tier_level == 3:
                        model_structure["sub_subs"] = {}

                    for i, mc in enumerate(main_list):
                        # 기본값 제안 (기존 양승훈 협동로봇 및 3계층 스마트폰 구매 결정)
                        default_sub_val = ""
                        if mc in ["기술 요인", "Technological"]: default_sub_val = _("상대적이점, 호환성, 안전성, 서비스지원", "Relative Advantage, Compatibility, Security, Service Support")
                        elif mc in ["조직 요인", "Organizational"]: default_sub_val = _("경영진지원, 기술준비도, 금융자원, 교육훈련", "Top Management Support, Tech Readiness, Financial Resources, Training")
                        elif mc in ["환경 요인", "Environmental"]: default_sub_val = _("정부지원, 경쟁압력, 인력난, 외부지원", "Gov Support, Competitive Pressure, Labor Shortage, External Support")
                        elif mc in ["혁신 요인", "Innovational"]: default_sub_val = _("경영진의 혁신성, 변화수용태도, 스마트팩토리수준, 지식정도", "Management Innovativeness, Change Acceptance, Smart Factory Level, Knowledge Level")
                        elif mc in ["기능성", "Functionality"]: default_sub_val = _("하드웨어, 소프트웨어", "Hardware, Software")
                        elif mc in ["디자인", "Design"]: default_sub_val = _("외관, 편의성", "Appearance, Usability")
                        elif mc in ["경제성", "Economy"]: default_sub_val = _("단말기가격, 유지비용", "Device Price, Maintenance Cost")

                        # "하위 요인 없음" 체크박스
                        _no_sub_key = f"no_sub_{i}_{mc}"
                        no_sub = st.checkbox(
                            _(f"'{mc}' — 하위 요인 없음 (이 대분류를 단독 최하위 요인으로 처리)", f"'{mc}' — No sub-criteria (treat as standalone leaf node)"),
                            value=st.session_state.get(_no_sub_key, False),
                            key=_no_sub_key,
                            help=_("체크 시 이 대분류에 중분류를 입력하지 않아도 되며, AHP 분석에서 대분류 가중치가 그대로 종합 중요도(Global Weight)로 사용됩니다.",
                                   "When checked, no sub-criteria input is needed. The main criteria weight will be used directly as the Global Weight in AHP analysis.")
                        )

                        if no_sub:
                            st.caption(_(f"✅ '{mc}' 는 단독 최하위 요인으로 설정됩니다. 하위 요인 입력이 필요 없으며, 대분류 가중치 = 종합 중요도가 됩니다.",
                                         f"✅ '{mc}' is set as a standalone leaf node. No sub-criteria needed; its main weight equals Global Weight."))
                            model_structure["subs"][mc] = []
                        else:
                            sub_input = st.text_input(_(f"'{mc}'의 하위 요인 (Sub-criteria)", f"Sub-criteria for '{mc}'"), value=st.session_state.get("edit_sub_inputs", {}).get(mc, default_sub_val))
                            subs_list = [x.strip().replace("_", " ") for x in sub_input.split(",") if x.strip()]
                            if len(subs_list) <= 1:
                                st.markdown(_("🚨 :red[**경고:** 쌍대비교를 위해서는 하위 요인이 최소 2개 이상 입력되어야 합니다.]", "🚨 :red[**Warning:** At least 2 sub-criteria are required for pairwise comparison.]"))
                            model_structure["subs"][mc] = subs_list

                        # [신규] 3계층 선택 시 소분류 입력 필드 동적 생성
                        subs_list = model_structure["subs"].get(mc, [])
                        if tier_level == 3 and subs_list:
                            with st.expander(_(f"↳ '{mc}' 하위의 소분류 (Sub-sub-criteria) 입력", f"↳ Enter Sub-sub-criteria under '{mc}'"), expanded=True):

                                for sub_c in subs_list:
                                    sub_sub_val = "" # 3계층 기본값은 빈칸
                                    if sub_c in ["하드웨어", "Hardware"]: sub_sub_val = _("카메라, 배터리, 프로세서", "Camera, Battery, Processor")
                                    elif sub_c in ["소프트웨어", "Software"]: sub_sub_val = _("운영체제, 기본앱", "OS, Default Apps")
                                    elif sub_c in ["외관", "Appearance"]: sub_sub_val = _("색상, 재질", "Color, Material")
                                    elif sub_c in ["단말기가격", "Device Price"]: sub_sub_val = _("일시불, 할부", "Lump Sum, Installment")
                                    elif sub_c in ["유지비용", "Maintenance Cost"]: sub_sub_val = _("통신요금, AS비용", "Telecom Fee, A/S Cost")
                    
                                    sub_sub_input = st.text_input(
                                        _(f"👉 '{sub_c}'의 하위 요인 (쉼표 구분)", f"👉 Sub-factors of '{sub_c}' (comma-separated)"),
                                        value=st.session_state.get("edit_sub_sub_inputs", {}).get(sub_c, sub_sub_val),
                                        placeholder=_("예: 항목1, 항목2 (※ 하위 요인이 없다면 비워두세요)", "e.g., Item1, Item2 (leave blank if no sub-factors)"),
                                        help=_("입력칸을 비워두면 이 항목은 자동으로 2계층 구조로 간주되어 분석됩니다.", "If left blank, this item will be treated as a 2-level hierarchy."),
                                        key=f"sub_sub_{sub_c}"
                                    )
                                    # 소분류가 입력된 경우에만 저장, 없으면 무시
                                    parsed_sub_subs = [x.strip().replace("_", " ") for x in sub_sub_input.split(",") if x.strip()]
                                    if len(parsed_sub_subs) == 1:
                                        st.markdown(_("🚨 :red[**경고:** 쌍대비교를 위해서는 소분류 요인이 최소 2개 이상 입력되어야 합니다 (비워두면 2계층으로 처리됨).]", "🚨 :red[**Warning:** At least 2 sub-sub-criteria are required (leave empty for 2-tier).]"))
                                
                                    if parsed_sub_subs:
                                        model_structure["sub_subs"][sub_c] = parsed_sub_subs

                    # 기본값: 표시함 (True)
                    saved_show_h = st.session_state.get("edit_show_hierarchy", True)
                    if isinstance(saved_show_h, str):
                        saved_show_h = (saved_show_h.lower() != "false")
                    show_hierarchy = bool(saved_show_h)

                    # [2026-10-20] 대안 평가(대안 선정) 설정
                    st.markdown("---")
                    st.markdown(_("##### 🎯 대안 평가 (대안 선정) 설정", "##### 🎯 Alternative Evaluation (Selection)"))
                    _edit_alt_val = st.session_state.get("edit_alternatives_input", "")
                    use_alternatives = st.checkbox(
                        _("대안 평가 사용 — 응답자가 최하위 요인별로 대안을 쌍대비교합니다", "Use alternative evaluation — respondents pairwise-compare alternatives per leaf criterion"),
                        value=bool(_edit_alt_val),
                        key="tab2_use_alt",
                    )
                    alt_list = []
                    if use_alternatives:
                        _alt_input_val = st.text_input(
                            _("대안 목록 (쉼표로 구분, 2~5개 권장)", "Alternatives (comma separated, 2~5 recommended)"),
                            value=_edit_alt_val,
                            placeholder=_("예: 대안 A, 대안 B, 대안 C", "e.g., Option A, Option B, Option C"),
                            key="tab2_alt_input",
                        )
                        alt_list = [x.strip().replace("_", " ") for x in _alt_input_val.split(",") if x.strip()]
                        if len(alt_list) <= 1:
                            st.markdown(_("🚨 :red[**경고:** 쌍대비교를 위해서는 대안이 최소 2개 이상 입력되어야 합니다.]", "🚨 :red[**Warning:** At least 2 alternatives are required for pairwise comparison.]"))
                        else:
                            _n_alt_pairs = len(alt_list) * (len(alt_list) - 1) // 2
                            _leaf_cnt = 0
                            for _mc in main_list:
                                _m_subs = model_structure["subs"].get(_mc, [])
                                if not _m_subs:
                                    _leaf_cnt += 1
                                else:
                                    for _sc in _m_subs:
                                        _ss = model_structure.get("sub_subs", {}).get(_sc, [])
                                        _leaf_cnt += len(_ss) if len(_ss) >= 2 else 1
                            st.info(_(
                                f"📊 대안 비교 문항이 추가됩니다: 최하위 요인 {_leaf_cnt}개 × 요인당 {_n_alt_pairs}문항 = 총 {_leaf_cnt * _n_alt_pairs}문항",
                                f"📊 Alternative questions will be added: {_leaf_cnt} leaf criteria × {_n_alt_pairs} per criterion = {_leaf_cnt * _n_alt_pairs} questions total"))
                    model_structure["alternatives"] = alt_list

                    # [2026-10-22] 대안 평가 안내문 — 대안 비교 섹션 시작 시 응답자에게 표시.
                    # 대안 정의는 섹션 4에서 요인 정의와 함께 입력받아 Definitions에 저장한다.
                    alt_guide_text = ""
                    if use_alternatives and len(alt_list) >= 2:
                        _default_alt_guide = _(
                            "지금부터는 각 세부기준의 관점에서 대안들을 서로 비교합니다. 각 섹션에서는 제시된 기준 하나의 관점에서만 판단해 주시고, 다른 기준의 중요성은 고려하지 마십시오. 모든 대안에 동일한 조건이 적용되는 상황을 가정하고, 어느 대안을 우선해야 하는지 평가해 주십시오.",
                            "From here, you will compare the alternatives from the perspective of each detailed criterion. In each section, please judge only from the perspective of the given criterion, without considering other criteria. Assume that the same conditions apply to all alternatives, and evaluate which alternative should be given priority."
                        )
                        _edit_alt_guide_val = st.session_state.get("edit_alt_guide", "")
                        alt_guide_text = st.text_area(
                            _("대안 평가 안내문 (대안 비교 섹션 시작 시 응답자에게 표시됩니다)", "Alternative Evaluation Guide (shown to respondents when the alternative comparison section begins)"),
                            value=_edit_alt_guide_val if _edit_alt_guide_val else _default_alt_guide,
                            key="tab2_alt_guide",
                            height=110,
                        )

                    # ── 계층 구조 트리 시각화 ──────────────────────────────
                    if main_list:
                        st.markdown("---")
                        st.markdown(_("##### 📐 계층 구조 미리보기", "##### 📐 Hierarchy Preview"))
                        from survey_manager import generate_hierarchy_tree_html
                        tree_html = generate_hierarchy_tree_html(
                            model_structure,
                            tier_level=tier_level,
                            lang=st.session_state.get('lang', 'ko')
                        )
                        if tree_html:
                            st.markdown(tree_html, unsafe_allow_html=True)

                        # 배포 설문지 내 계층구조 다이어그램 표시 옵션 (라디오 버튼)
                        st.markdown(_("**📊 배포 설문지 내 계층 구조 다이어그램 표시 여부**", "**📊 Display Hierarchy Diagram in Deployed Survey Option**"))
                        show_h_options = [
                            _("표시함 (보이기, 기본값)", "Show (Default)"),
                            _("표시 안 함 (숨기기)", "Do not show (Hide)")
                        ]
                        default_show_h_idx = 0 if saved_show_h else 1
                        if "tab2_show_hierarchy_choice" in st.session_state and st.session_state["tab2_show_hierarchy_choice"] not in show_h_options:
                            del st.session_state["tab2_show_hierarchy_choice"]

                        show_h_selected = st.radio(
                            _("배포된 설문지(쌍대비교 시작 전)에 위 계층구조 다이어그램을 제시할지 여부를 설정합니다.", "Choose whether to display the hierarchy diagram above in the deployed survey before pairwise comparison."),
                            options=show_h_options,
                            index=default_show_h_idx,
                            key="tab2_show_hierarchy_choice",
                            horizontal=True
                        )
                        show_hierarchy = (show_h_selected == show_h_options[0])
                    # ──────────────────────────────────────────────────────

                    st.caption(_("※ 쌍대비교 시작 전 응답자가 전반적 요인 순위를 매기는 '사전 중요도 순위 지정 문항'은 자동으로 설문에 포함됩니다.", "※ A 'Prior Importance Ranking Question', where respondents rank the overall criteria before starting pairwise comparisons, is automatically included in the survey."))




                with st.container():
                    # 섹션 4: 요인 조작적 정의 설정
                    render_section_header(_("섹션 4: 요인별 상세 설명 (조작적 정의)", "Section 4: Detailed Description per Criteria (Operational Definition)"))
                    st.info(_("응답자가 요인 개념을 직관적으로 파악할 수 있도록 상세 설명을 기술해 주십시오.", "Please provide detailed descriptions so respondents can intuitively understand each criteria concept."))
                    definitions_map = {}

                    for i, mc in enumerate(main_list):
                        # 대분류명
                        st.markdown(_(f"####  :blue[**대분류: {mc}**]", f"####  :blue[**Main Criteria: {mc}**]"))
                        default_main_def = ""
                        if mc in ["기술 요인", "Technological"]: default_main_def = _("협동로봇 도입 시 기술적 성능, 호환성, 안전성 및 기술 지원 등 기술 측면의 요인", "Factors related to the technological aspect such as technical performance, compatibility, safety, and technical support.")
                        elif mc in ["조직 요인", "Organizational"]: default_main_def = _("협동로봇 도입과 관련된 조직 내부의 역량, 경영진 지원, 재무 및 교육 상태 요인", "Factors related to the internal capabilities of the organization, top management support, financial and training status.")
                        elif mc in ["환경 요인", "Environmental"]: default_main_def = _("정부 지원, 산업 내 경쟁 압력, 구인난 및 외부 협력 등 외부 환경적 요인", "External environmental factors such as government support, competitive pressure within the industry, labor shortage, and external cooperation.")
                        elif mc in ["혁신 요인", "Innovational"]: default_main_def = _("경영진의 혁신 지향성, 구성원의 변화 수용도 및 스마트 팩토리 지식/기술 수준 요인", "Factors such as the management's innovation orientation, members' acceptance of change, and smart factory knowledge/skill levels.")

                        edit_def_val = st.session_state.get("edit_definitions", {}).get(mc)
                        val_to_use = edit_def_val if edit_def_val is not None else (default_main_def or _(f"{mc}에 대한 전반적 요소를 설명합니다.", f"Overall description for {mc}."))
                        val_to_use = translate_definition_if_default(mc, val_to_use)

                        definitions_map[mc] = st.text_input(
                            _(f"👉 [{mc}] 요인의 전체적인 설명 입력", f"👉 Enter overall description for [{mc}]"),
                            value=val_to_use,
                            key=f"def_main_{mc}_{i}"
                        )

                        # 중분류들은 연관 관계를 묶을 수 있도록 시각적으로 구분된 테두리 컨테이너 안에 배치
                        with st.container(border=True):
                            for j, sc in enumerate(model_structure["subs"].get(mc, [])):
                                # 3계층일 때는 중분류 헤더를 넣어서 시각적 구분 강화
                                if tier_level == 3:
                                    st.markdown(_(f"#####  :blue[**중분류: {sc}**]", f"#####  :blue[**Sub Criteria: {sc}**]"))
                                    sc_label = _(f"👉 [{sc}] 중분류의 전체적인 설명 입력", f"👉 Enter overall description for [{sc}]")
                                else:
                                    sc_label = _(f"ㄴ 중분류 [{sc}] 설명 입력", f"👉 Enter description for sub-criteria [{sc}]")

                                # 기본 양승훈 설문 정의 적용
                                default_def = ""
                                if sc in ["상대적이점", "Relative Advantage"]: default_def = _("도입대상 협동로봇간의 상대적 이점", "Relative advantage among the collaborative robots targeted for adoption.")
                                elif sc in ["호환성", "Compatibility"]: default_def = _("기존 설비나 타사 협동로봇과의 연결성", "Connectivity with existing equipment or third-party collaborative robots.")
                                elif sc in ["안전성", "Security"]: default_def = _("작업자와 같은 공간에서 안전 펜스 없이 작업할 때의 인적 사고 예방 수준", "Level of human accident prevention when working in the same space as operators without safety fences.")
                                elif sc in ["서비스지원", "Service Support"]: default_def = _("공급사의 기술 및 A/S 지원 정도", "Degree of technical and A/S support from the supplier.")
                                elif sc in ["경영진지원", "Top Management Support"]: default_def = _("경영진의 도입 의지 및 경영철학 반영도", "The management's willingness to adopt and the degree to which management philosophy is reflected.")
                                elif sc in ["기술준비도", "Tech Readiness"]: default_def = _("조직원의 로봇 활용 기술 준비 수준", "The level of technical readiness of organizational members to utilize robots.")
                                elif sc in ["금융자원", "Financial Resources"]: default_def = _("로봇 구입을 위한 자본 여력 및 자금 조달 편의성", "Capital capacity and financing convenience for purchasing robots.")
                                elif sc in ["교육훈련", "Training"]: default_def = _("기술 향상을 위한 위탁/사내 교육 프로그램 유무", "Availability of external/internal training programs for skill improvement.")
                                elif sc in ["정부지원", "Gov Support"]: default_def = _("협동로봇 도입을 활성화하기 위한 정부의 재정 지원 및 보조금 혜택 정도", "Degree of government financial support and subsidy benefits to promote the adoption of collaborative robots.")
                                elif sc in ["경쟁압력", "Competitive Pressure"]: default_def = _("동종 업계 또는 경쟁사의 협동로봇 도입에 따른 경쟁적 압박 정도", "Degree of competitive pressure due to the adoption of collaborative robots by peers or competitors.")
                                elif sc in ["인력난", "Labor Shortage"]: default_def = _("제조 현장의 구인난 및 생산 인력 수급의 어려움 수준", "Level of difficulty in finding labor and supplying production personnel at the manufacturing site.")
                                elif sc in ["외부지원", "External Support"]: default_def = _("로봇 공급사 외의 외부 컨설팅, 연구기관 등의 기술적 지원", "Technical support from external consulting, research institutes, etc., other than the robot supplier.")
                                elif sc in ["경영진의 혁신성", "Management Innovativeness"]: default_def = _("새로운 제조 기술 및 로봇 도입에 대한 최고경영자의 적극적인 의지", "The top management's active willingness to adopt new manufacturing technologies and robots.")
                                elif sc in ["변화수용태도", "Change Acceptance"]: default_def = _("신규 장비 및 작업 프로세스 변화에 대한 구성원들의 수용 및 협조 태도", "Members' acceptance and cooperative attitude towards changes in new equipment and work processes.")
                                elif sc in ["스마트팩토리수준", "Smart Factory Level"]: default_def = _("공장 내 디지털화, 정보시스템(MES 등) 및 자동화 기술의 현재 구축 수준", "Current level of implementation of digitalization, information systems (MES, etc.), and automation technology in the factory.")
                                elif sc in ["지식정도", "Knowledge Level"]: default_def = _("협동로봇 활용 및 유지 관리에 필요한 조직 내 전문 지식 수준", "Level of internal expertise required for the utilization and maintenance of collaborative robots.")

                                edit_sub_def_val = st.session_state.get("edit_definitions", {}).get(sc)
                                sub_val_to_use = edit_sub_def_val if edit_sub_def_val is not None else (default_def or _(f"{sc}에 대한 정의입니다.", f"Definition for {sc}."))
                                sub_val_to_use = translate_definition_if_default(sc, sub_val_to_use)

                                definitions_map[sc] = st.text_input(
                                    sc_label,
                                    value=sub_val_to_use,
                                    key=f"def_sub_{mc}_{sc}_{j}"
                                )

                                # 3계층이면 소분류 루프 추가
                                if tier_level == 3:
                                    sub_subs = model_structure.get("sub_subs", {}).get(sc, [])
                                    if sub_subs:
                                        with st.container(border=True):
                                            for k, ssc in enumerate(sub_subs):
                                                edit_ssc_def_val = st.session_state.get("edit_definitions", {}).get(ssc)
                                                ssc_val_to_use = edit_ssc_def_val if edit_ssc_def_val is not None else _(f"{ssc}에 대한 정의입니다.", f"Definition for {ssc}.")
                                                definitions_map[ssc] = st.text_input(
                                                    _(f"ㄴ 소분류 [{ssc}] 설명 입력", f"👉 Enter description for sub-sub-criteria [{ssc}]"),
                                                    value=ssc_val_to_use,
                                                    key=f"def_ssc_{sc}_{ssc}_{k}"
                                                )
                        st.write("") # 섹션 간 시각적 여백 추가




                    # [2026-10-22] 대안 정의 입력 — 요인 정의와 같은 Definitions 맵에 대안명으로 저장.
                    # 응답 화면의 첫 대안 비교 섹션에서 안내문과 함께 표시된다.
                    if alt_list:
                        st.markdown(_("####  :blue[**대안 (비교 대상) 상세 설명**]", "####  :blue[**Alternative (Comparison Target) Descriptions**]"))
                        with st.container(border=True):
                            for _alt_k, _alt_name in enumerate(alt_list):
                                _edit_alt_def_val = st.session_state.get("edit_definitions", {}).get(_alt_name)
                                definitions_map[_alt_name] = st.text_input(
                                    _(f"대안 [{_alt_name}] 설명 입력", f"Enter description for alternative [{_alt_name}]"),
                                    value=_edit_alt_def_val if _edit_alt_def_val is not None else "",
                                    key=f"def_alt_{_alt_name}_{_alt_k}"
                                )

                with st.container():
                    # 섹션 5: 척도 인터페이스 설정
                    render_section_header(_("섹션 5: 쌍대비교 응답 척도 및 일관성(CR) 검증 레벨 설정", "Section 5: Scale Type & CR Validation Level Setup"))
                    scale_options = [
                        _("1-9 Continuous (1부터 9까지 연속형 스케일)", "1-9 Continuous Scale"),
                        _("1-5 Continuous (1부터 5까지 연속형 스케일)", "1-5 Continuous Scale"),
                        _("1-3-7-9 Discrete (이산형 척도)", "1-3-7-9 Discrete Scale"),
                        _("1-3-5 Discrete (이산형 척도)", "1-3-5 Discrete Scale")
                    ]
                    st.markdown(f"**{_('응답 척도 타입', 'Response Scale Type')}**")
                    default_scale = st.session_state.get("edit_scale_type", "1-9 Continuous")
                    scale_idx = 0
                    if "1-5" in default_scale and "Discrete" not in default_scale:
                        scale_idx = 1
                    elif "1-3-7-9" in default_scale:
                        scale_idx = 2
                    elif "1-3-5" in default_scale:
                        scale_idx = 3

                    scale_option = st.radio(_("응답 척도 타입", "Response Scale Type"), scale_options, index=scale_idx, label_visibility="collapsed")




                    # 섹션 5: 답례품 및 개인정보 수집 동의 설정
                    if st.session_state.get("user_id") == "shjeon":
                        st.markdown(_("#### 🎁 [선택] 답례품 및 동의 양식 설정 (shjeon 전용)", "#### 🎁 [Optional] Reward & Consent Form Setup (shjeon only)"))
                        reward_enabled = st.toggle(_("답례품(기프티콘 등) 제공 활성화", "Enable Rewards (e.g., Gifticons)"))
                        reward_desc = ""
                        if reward_enabled:
                            reward_desc = st.text_area(_("답례품 설명", "Reward Description"), value=st.session_state.get("edit_reward_desc", "모든 설문 응답을 마친 분들에게 스타벅스 아메리카노 기프티콘을 발송해 드립니다."))
            
                        rewards_info = {
                            "enabled": reward_enabled,
                            "desc": reward_desc
                        }


                    else:
                        rewards_info = {"enabled": False}

                    # 일관성 비율 (CR) 검증 레벨 설정
                    st.markdown(_("**일관성 비율 (CR) 검증 레벨 설정**", "**Consistency Ratio (CR) Validation Level Setup**"))
                    # Get default index from edit state if editing, otherwise default to index 3 (0.2 이하)
                    default_cr_idx = 3
                    if st.session_state.get("editing_survey_id") and st.session_state.get("edit_cr_limit") is not None:
                        cr_val = float(st.session_state.get("edit_cr_limit"))
                        if cr_val <= 0.1: default_cr_idx = 1
                        elif cr_val <= 0.15: default_cr_idx = 2
                        elif cr_val <= 0.2: default_cr_idx = 3
                        elif cr_val <= 0.3: default_cr_idx = 4
                    elif st.session_state.get("editing_survey_id") and st.session_state.get("edit_cr_limit") is None:
                        default_cr_idx = 0
        
                    cr_limit_opt = st.selectbox(_("일관성 비율(CR) 허용 기준치", "Consistency Ratio (CR) Tolerance Limit"), [
                        _("제한하지 않음 (이탈률 감소용)", "No Limit (To reduce drop-out rate)"),
                        _("0.1 이하 (매우 엄격함)", "0.1 or below (Very Strict)"),
                        _("0.15 이하 (엄격함)", "0.15 or below (Strict)"),
                        _("0.2 이하 (보통)", "0.2 or below (Normal)"),
                        _("0.3 이하 (일부 허용)", "0.3 or below (Somewhat Lenient)")
                    ], index=default_cr_idx)

                    cr_limit = None
                    if "0.15" in cr_limit_opt: cr_limit = 0.15
                    elif "0.1" in cr_limit_opt: cr_limit = 0.1
                    elif "0.2" in cr_limit_opt: cr_limit = 0.2
                    elif "0.3" in cr_limit_opt: cr_limit = 0.3

                    if cr_limit is not None:
                        st.warning(_("⚠️ 일관성 비율(CR) 기준을 너무 엄격하게(낮게) 설정할 경우, 논리적 모순이 있는 설문이 대거 무효 처리되어 응답자의 재검토 피로도가 극대화되고 설문 이탈률이 급증할 수 있으니 유의하시기 바랍니다. 응답자 이탈을 낮추기 위해 일관성 비율 허용 기준치를 0.3 이하로 여유롭게 설정하고, 데이터 수집 후 AHP마스터의 일관성 보정 기능을 통해 사후 보정하여 분석하시기를 적극 추천드립니다.", "⚠️ Warning: If the CR limit is set too strict (low), many logically inconsistent surveys will be invalidated. This maximizes respondent fatigue and can cause the survey drop-out rate to spike. To reduce respondent dropout, we strongly recommend setting the consistency ratio tolerance to 0.3 or less and post-calibrating the collected data using the AHP Master consistency calibration feature."))
                        # CR 가이드 방식 선택
                        st.markdown(_("**응답자 일관성 유지(CR) 가이드 방식 선택**", "**Select Consistency Ratio (CR) Guide Method for Respondents**"))
        
                        default_guide = st.session_state.get("edit_cr_guide_method", "realtime")
        
                        # Backward compatibility for old surveys that used toggle
                        if "edit_cr_guide_enabled" in st.session_state:
                            if st.session_state["edit_cr_guide_enabled"] and default_guide not in ["realtime", "post_wizard", "none"]:
                                default_guide = "realtime"
                            elif not st.session_state["edit_cr_guide_enabled"] and default_guide not in ["realtime", "post_wizard", "none"]:
                                default_guide = "none"
        
                        options_kr = {
                            "realtime": "실시간 권장 범위 시각화 안내 (이탈률 최소화, 편의성 높음)",
                            "post_wizard": "제출 후 지능형 수정 제안 마법사 (가장 학술적인 방식, 편향성 제거)",
                            "none": "일관성 가이드 없음(엄격한 검증만 수행)"
                        }
                        options_en = {
                            "realtime": "Real-time Visual Range Guide (Minimizes dropout, high convenience)",
                            "post_wizard": "Post-Submission Smart Fix Wizard (Most academic, removes bias)",
                            "none": "No Guide (Strict validation only)"
                        }
        
                        def get_idx(val):
                            keys = list(options_kr.keys())
                            return keys.index(val) if val in keys else 0
            
                        selected_idx = st.radio(
                            label=_("가이드 방식을 선택하세요", "Choose guide method"),
                            options=[0, 1, 2],
                            format_func=lambda x: options_kr[list(options_kr.keys())[x]] if _("ko", "en") == "ko" else options_en[list(options_en.keys())[x]],
                            index=get_idx(default_guide),
                            label_visibility="collapsed"
                        )
        
                        cr_guide_method = list(options_kr.keys())[selected_idx]
        
                        if cr_guide_method == "realtime":
                            st.info(_("**실시간 안내**: 응답자가 설문 중 일관성을 유지할 수 있도록 각 비교 그룹의 마지막 연계 문항에서 파란색 배경으로 권장 범위를 안내합니다. 초반 문항은 자유롭게 응답하며, 이탈률을 크게 낮출 수 있습니다.", "**Real-time Guide**: Highlights the recommended range with a blue background on the final linked question of each comparison group to help respondents maintain consistency. Reduces dropouts."))
                        elif cr_guide_method == "post_wizard":
                            st.success(_("💡 **지능형 수정 제안 (추천)**: 응답 중에는 아무런 가이드를 주지 않아 응답자의 진짜 생각을 편향 없이 수집합니다. 제출 버튼을 눌렀을 때 CR이 초과하면, 가장 모순이 큰 딱 1개 문항을 찾아내어 수정을 권고하는 마법사를 띄웁니다.", "💡 **Smart Fix Wizard (Recommended)**: Collects true thoughts without bias by providing no guide during response. If CR exceeds the limit upon submission, a wizard will appear to suggest fixing the single most contradictory question."))
                        else:
                            st.warning(_("**안내 없음**: 응답자에게 어떤 힌트도 주지 않으며, 제출 시 CR을 초과하면 에러 메시지와 함께 전체 재검토를 요구합니다. 이탈률이 높아질 수 있습니다.", "**No Guide**: Gives no hints. If CR is exceeded upon submission, an error message is shown requiring a full review. Dropouts may increase."))
                    else:
                        cr_guide_method = "none"




                    # 섹션 6: 수집 목표 설정
                    render_section_header(_("섹션 6: 수집 목표 설정", "Section 6: Collection Goal Setup"))
                    _goal_sheet_id = st.session_state.get("editing_survey_id")
                    if _goal_sheet_id:
                        try:
                            from collection_support import render_goal_setting_form
                            from survey_manager import load_survey_metadata as _load_goal_meta
                            _goal_meta = _load_goal_meta(_goal_sheet_id) or {}
                            render_goal_setting_form(_goal_sheet_id, _goal_meta, key_prefix="deploy")
                        except Exception as _ge:
                            st.warning(_("목표 설정을 불러오지 못했습니다.", "Could not load goal settings."))
                    else:
                        st.info(_("설문을 배포한 뒤 이 섹션에서 수집 목표(목표 응답 수·마감일)를 설정할 수 있습니다. 기존 설문을 수정하는 경우 목표를 바로 설정할 수 있습니다.",
                                  "After deploying the survey, you can set collection goals (target responses & deadline) in this section. When editing an existing survey, you can set goals right away."))

                    # 섹션 7: 최종 미리보기 및 배포
                    render_section_header(_("섹션 7: 저장 전 최종 미리보기 및 배포", "Section 7: Final Preview & Deployment Before Saving"))

                    # [추가] 구글 스프레드시트 연동 설정
                    if st.session_state.get('editing_survey_id'):
                        st.markdown(_("#####  기존 구글 스프레드시트 연동 (수정 모드)", "#####  Existing Google Spreadsheet Integration (Edit Mode)"))
                        st.info(_("현재 **기존 설문 수정 모드**로 진입했습니다. 수정한 설정 내용은 기존 연동된 구글 스프레드시트에 안전하게 덮어씌워집니다.", "You have entered **Existing Survey Edit Mode**. The modified settings will be safely overwritten to the existing linked Google Spreadsheet."))
                        existing_sheet_id_input = st.session_state.editing_survey_id
                    else:
                        past_surveys = []
                        valid_ids = list(set(filter(None, [st.session_state.user_id, survey_admin_email])))
                        if valid_ids:
                            import sqlite3
                            try:
                                conn = sqlite3.connect('users.db')
                                c = conn.cursor()
                                placeholders = ','.join(['?'] * len(valid_ids))
                                c.execute(f"SELECT DISTINCT title, survey_id, created_at FROM admin_surveys WHERE admin_id IN ({placeholders}) ORDER BY created_at DESC", valid_ids)
                                past_surveys = c.fetchall()
                                conn.close()
                            except Exception:
                                pass
                    
                        existing_sheet_id_input = ""
                        deploy_opts = [
                            _("새 구글 스프레드시트 연동 (직접 URL 입력)", "Link New Google Spreadsheet (Manual URL Input)")
                        ]
                        if len(past_surveys) > 0:
                            deploy_opts.append(_("기존 배포했던 설문 URL 재사용 (덮어쓰기)", "Reuse Existing Deployed Survey URL (Overwrite)"))
                    
                        if len(deploy_opts) > 1:
                            st.markdown(_("##### 🔗 배포 방식 선택 (Deployment Method)", "##### 🔗 Deployment Method"))
                            deploy_option = st.radio(
                                _("배포 방식을 선택해 주세요.", "Please select a deployment method."),
                                options=deploy_opts,
                                index=0,
                                key="deploy_option_radio",
                                label_visibility="collapsed"
                            )
                            st.write("")
                        else:
                            deploy_option = deploy_opts[0]
            
                        if "재사용" in deploy_option or "Reuse" in deploy_option:
                            st.markdown(_("##### ⚙️ 재사용할 기존 설문 선택", "##### ⚙️ Select Existing Survey to Reuse"))
                            survey_options = {f"{row[0]} ({row[2][:16]})" : row[1] for row in past_surveys}
                            selected_survey_label = st.selectbox(
                                _("과거에 배포했던 설문 목록", "List of previously deployed surveys"),
                                options=list(survey_options.keys())
                            )
                            existing_sheet_id_input = survey_options[selected_survey_label]
                            st.info(_("선택한 설문의 구글 스프레드시트에 새로운 내용을 덮어씌웁니다. 기존 응답 URL은 그대로 유지됩니다.", "The new content will be overwritten on the Google Spreadsheet of the selected survey. The existing response URL will be maintained."))
                        
                        else:
                            st.markdown(_("##### 📝 구글 스프레드시트 직접 연동", "##### 📝 Link Google Spreadsheet Manually"))
                            st.warning(_(
                                "1. 본인 구글 드라이브에서 '빈 스프레드시트'를 새로 만듭니다.\n"
                                f"2. 우측 상단 [공유] 버튼을 눌러 `{st.secrets.get('gcp_service_account', {}).get('client_email', 'service account email')}` 계정을 **편집자**로 추가합니다.\n"
                                "3. 해당 스프레드시트의 주소(URL)를 복사하여 아래에 붙여넣습니다.",
                                "1. Create a 'Blank Spreadsheet' in your Google Drive.\n"
                                f"2. Click [Share] and add `{st.secrets.get('gcp_service_account', {}).get('client_email', 'service account email')}` as an **Editor**.\n"
                                "3. Copy and paste the spreadsheet URL below."
                            ))
                            import os
                            col1, col2 = st.columns([1, 2])
                            with col1:
                                if os.path.exists("google_sheets_menu_guide.png"):
                                    st.image("google_sheets_menu_guide.png", caption=_("구글 스프레드시트 메뉴 접근 방법", "How to access Google Sheets menu"), use_container_width=True)
                            with col2:
                                if os.path.exists("manual_sheet_url_guide.png"):
                                    st.image("manual_sheet_url_guide.png", caption=_("구글 스프레드시트 URL 주소창 복사 예시", "Google Spreadsheet URL Copy Example"), use_container_width=True)
                            manual_url = st.text_input(_("스프레드시트 URL 입력", "Input Spreadsheet URL"), placeholder="https://docs.google.com/spreadsheets/d/...")
                            if manual_url:
                                existing_sheet_id_input = manual_url.strip()
                            else:
                                existing_sheet_id_input = ""




                    # Save current state for preview tab
                    preview_id = f"preview_{st.session_state.user_id if st.session_state.user_id else 'guest'}"
                
                    # [신규] 미리보기용 이미지 데이터 준비 (Base64 인코딩)
                    preview_imgs_dict = {}
                    import base64
                    for idx_num, suf in [(1, ""), (2, "2"), (3, "3")]:
                        cur_img = st.session_state.get(f'survey_image_data{suf}') or st.session_state.get(f'edit_survey_image{suf}')
                        cur_mime = st.session_state.get(f'survey_image_mime{suf}') or st.session_state.get(f'edit_survey_image_mime{suf}', 'image/png')
                        if cur_img:
                            if isinstance(cur_img, bytes):
                                b64_str = base64.b64encode(cur_img).decode('ascii')
                            elif isinstance(cur_img, str):
                                b64_str = cur_img
                            else:
                                b64_str = ""
                            if b64_str:
                                preview_imgs_dict[str(idx_num)] = {
                                    "data_b64": b64_str,
                                    "mime": cur_mime or "image/png"
                                }

                    preview_data = {
                        "Title": survey_title,
                        "Description": survey_desc,
                        "Admin_Email": survey_admin_email,
                        "AHP_Model_JSON": model_structure,
                        "Tier_Level": tier_level, # [신규] 3계층 구분용
                        "Scale_Type": scale_option,
                        "Demographics": demographics_settings,
                        "Definitions": definitions_map,
                        "Alt_Guide": alt_guide_text,
                        "CR_Limit": cr_limit,
                        "CR_Guide_Method": cr_guide_method,
                        "Show_Hierarchy": show_hierarchy,
                        "Rewards_Info": rewards_info,
                        "Preview_Images": preview_imgs_dict,
                        "Sheet_ID": st.session_state.get("editing_survey_id", "")
                    }

                    st.session_state[f"_preview_data_{preview_id}"] = preview_data

                    import json, os
                    os.makedirs("temp_previews", exist_ok=True)
                    with open(f"temp_previews/{preview_id}.json", "w", encoding="utf-8") as f:
                        json.dump(preview_data, f, ensure_ascii=False)

                    # [추가] 미리보기 용으로 이미지 DB에 임시 저장 (Respondent UI는 f"preview_{preview_id}"로 조회함, 최대 3개)
                    try:
                        conn_prev = sqlite3.connect('users.db')
                        c_prev = conn_prev.cursor()
                        c_prev.execute('''CREATE TABLE IF NOT EXISTS survey_images (
                                            survey_id TEXT PRIMARY KEY,
                                            image_data BLOB,
                                            mime_type TEXT,
                                            image_data2 BLOB,
                                            mime_type2 TEXT,
                                            image_data3 BLOB,
                                            mime_type3 TEXT
                                        )''')
                        preview_survey_id_param = f"preview_{preview_id}"
                        prev_img1 = st.session_state.get('survey_image_data') or st.session_state.get('edit_survey_image')
                        prev_mime1 = st.session_state.get('survey_image_mime') or st.session_state.get('edit_survey_image_mime', 'image/png')
                        prev_img2 = st.session_state.get('survey_image_data2') or st.session_state.get('edit_survey_image2')
                        prev_mime2 = st.session_state.get('survey_image_mime2') or st.session_state.get('edit_survey_image_mime2', 'image/png')
                        prev_img3 = st.session_state.get('survey_image_data3') or st.session_state.get('edit_survey_image3')
                        prev_mime3 = st.session_state.get('survey_image_mime3') or st.session_state.get('edit_survey_image_mime3', 'image/png')

                        if prev_img1 or prev_img2 or prev_img3:
                            for pid in [preview_id, preview_survey_id_param]:
                                c_prev.execute("""INSERT OR REPLACE INTO survey_images 
                                                (survey_id, image_data, mime_type, image_data2, mime_type2, image_data3, mime_type3) 
                                                VALUES (?, ?, ?, ?, ?, ?, ?)""",
                                                (pid, prev_img1, prev_mime1, prev_img2, prev_mime2, prev_img3, prev_mime3))
                        else:
                            for pid in [preview_id, preview_survey_id_param]:
                                c_prev.execute("DELETE FROM survey_images WHERE survey_id=?", (pid,))
                        conn_prev.commit()
                        conn_prev.close()
                    except Exception:
                        pass

                    # 미리보기 link_button과 일반 button의 모양을 완전히 통일
                    st.markdown("""
                    <style>
                    section[data-testid="stSidebar"] ~ div div[data-testid="stLinkButton"],
                    div[data-testid="stLinkButton"] {
                        width: 100% !important;
                    }
                    div[data-testid="stLinkButton"] a,
                    div[data-testid="stLinkButton"] > a {
                        border-radius: 8px !important;
                        -webkit-border-radius: 8px !important;
                        min-height: 40px !important;
                        height: 40px !important;
                        max-height: 40px !important;
                        padding: 4px 12px !important;
                        border-width: 1px !important;
                        border-style: solid !important;
                        border-color: rgba(49, 51, 63, 0.2) !important;
                        background-color: rgb(255, 255, 255) !important;
                        display: inline-flex !important;
                        align-items: center !important;
                        justify-content: center !important;
                        width: 100% !important;
                        box-sizing: border-box !important;
                        text-decoration: none !important;
                    }
                    div[data-testid="stLinkButton"] a > div,
                    div[data-testid="stLinkButton"] > a > div {
                        font-size: 14px !important;
                        font-weight: 400 !important;
                        line-height: 1.6 !important;
                        color: rgb(49, 51, 63) !important;
                    }
                    div[data-testid="stLinkButton"] a:hover,
                    div[data-testid="stLinkButton"] > a:hover {
                        border-color: rgb(255, 75, 75) !important;
                        color: rgb(255, 75, 75) !important;
                    }
                    div[data-testid="stLinkButton"] a:hover > div,
                    div[data-testid="stLinkButton"] > a:hover > div {
                        color: rgb(255, 75, 75) !important;
                    }
                    </style>
                    """, unsafe_allow_html=True)

                    col_save, col_p1, col_p2 = st.columns(3)

                    # ── 버튼 1: 저장 ─────────────────────────────────────
                    with col_save:
                        _has_editing_id = bool(st.session_state.get("editing_survey_id"))
                        save_btn_label = _("💾 설정 저장", "💾 Save Settings") if _has_editing_id else _("💾 저장 (배포 후 활성화)", "💾 Save (Active After Deploy)")
                        if st.button(save_btn_label, use_container_width=True, disabled=not _has_editing_id, key="section6_save_btn"):
                            _s_sheet_id = st.session_state.editing_survey_id
                            with st.spinner(_("저장 중...", "Saving...")):
                                try:
                                    import sqlite3
                                    # 이미지 보존 저장 (최대 3개)
                                    _s_img1 = st.session_state.get('survey_image_data') or st.session_state.get('edit_survey_image')
                                    _s_mime1 = st.session_state.get('survey_image_mime') or st.session_state.get('edit_survey_image_mime', 'image/png')
                                    _s_img2 = st.session_state.get('survey_image_data2') or st.session_state.get('edit_survey_image2')
                                    _s_mime2 = st.session_state.get('survey_image_mime2') or st.session_state.get('edit_survey_image_mime2', 'image/png')
                                    _s_img3 = st.session_state.get('survey_image_data3') or st.session_state.get('edit_survey_image3')
                                    _s_mime3 = st.session_state.get('survey_image_mime3') or st.session_state.get('edit_survey_image_mime3', 'image/png')

                                    _s_conn = sqlite3.connect('users.db')
                                    _s_cur = _s_conn.cursor()
                                    _s_cur.execute('''CREATE TABLE IF NOT EXISTS survey_images (
                                                    survey_id TEXT PRIMARY KEY,
                                                    image_data BLOB,
                                                    mime_type TEXT,
                                                    image_data2 BLOB,
                                                    mime_type2 TEXT,
                                                    image_data3 BLOB,
                                                    mime_type3 TEXT
                                                )''')
                                    if _s_img1 or _s_img2 or _s_img3:
                                        _s_cur.execute("""INSERT OR REPLACE INTO survey_images 
                                                       (survey_id, image_data, mime_type, image_data2, mime_type2, image_data3, mime_type3) 
                                                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                                                       (_s_sheet_id, _s_img1, _s_mime1, _s_img2, _s_mime2, _s_img3, _s_mime3))
                                    else:
                                        _s_cur.execute("DELETE FROM survey_images WHERE survey_id=?", (_s_sheet_id,))
                                    _s_conn.commit()
                                    _s_conn.close()

                                    # 세션 상태 및 미리보기 JSON 파일 동기화
                                    if _s_img1:
                                        st.session_state['edit_survey_image'] = _s_img1
                                        st.session_state['edit_survey_image_mime'] = _s_mime1
                                    if _s_img2:
                                        st.session_state['edit_survey_image2'] = _s_img2
                                        st.session_state['edit_survey_image_mime2'] = _s_mime2
                                    if _s_img3:
                                        st.session_state['edit_survey_image3'] = _s_img3
                                        st.session_state['edit_survey_image_mime3'] = _s_mime3

                                    try:
                                        _s_p_imgs = {}
                                        for _idx, (_im, _mi) in [(1, (_s_img1, _s_mime1)), (2, (_s_img2, _s_mime2)), (3, (_s_img3, _s_mime3))]:
                                            if _im:
                                                _b64 = base64.b64encode(_im).decode('ascii') if isinstance(_im, bytes) else str(_im)
                                                _s_p_imgs[str(_idx)] = {"data_b64": _b64, "mime": _mi or "image/png"}
                                        preview_data["Preview_Images"] = _s_p_imgs
                                        preview_data["Sheet_ID"] = _s_sheet_id
                                        with open(f"temp_previews/{preview_id}.json", "w", encoding="utf-8") as _pf:
                                            json.dump(preview_data, _pf, ensure_ascii=False)
                                    except Exception:
                                        pass

                                    # 구글 시트에 이미지 영구 저장 동기화 (클라우드 재배포 시 보존)
                                    try:
                                        from survey_manager import save_survey_images_to_gsheet
                                        save_survey_images_to_gsheet(_s_sheet_id, {
                                            1: (_s_img1, _s_mime1),
                                            2: (_s_img2, _s_mime2),
                                            3: (_s_img3, _s_mime3)
                                        }, user_id=st.session_state.user_id)
                                    except Exception:
                                        pass

                                    # 구글 시트 메타데이터 업데이트
                                    if tier_level == 3:
                                        from survey_manager_v3 import create_survey_sheet_v3
                                        create_survey_sheet_v3(
                                            title=survey_title, admin_email=survey_admin_email,
                                            ahp_model=model_structure, scale_type=scale_option,
                                            demographics=demographics_settings, definition_map=definitions_map,
                                            cr_limit=cr_limit, cr_guide_method=cr_guide_method,
                                            rewards_info=rewards_info, description=survey_desc,
                                            existing_sheet_id=_s_sheet_id, user_id=st.session_state.user_id,
                                            show_hierarchy=show_hierarchy, alt_guide=alt_guide_text
                                        )
                                    else:
                                        create_survey_sheet(
                                            title=survey_title, admin_email=survey_admin_email,
                                            ahp_model=model_structure, scale_type=scale_option,
                                            demographics=demographics_settings, definition_map=definitions_map,
                                            cr_limit=cr_limit, cr_guide_method=cr_guide_method,
                                            rewards_info=rewards_info, description=survey_desc,
                                            existing_sheet_id=_s_sheet_id, user_id=st.session_state.user_id,
                                            show_hierarchy=show_hierarchy, alt_guide=alt_guide_text
                                        )
                                    st.session_state._survey_cache_dirty = True
                                    st.success(_("✅ 저장 완료!", "✅ Saved successfully!"))
                                except Exception as _s_err:
                                    st.error(_("저장 오류: ", "Save error: ") + str(_s_err))

                    # ── 버튼 2: 미리보기 ──────────────────────────────────
                    with col_p1:
                        st.link_button(_("👁️ 설문지 미리보기", "👁️ Preview Survey Form"), f"/?preview_id={preview_id}", use_container_width=True)

                    # ── 버튼 3: 배포 ──────────────────────────────────────
                    with col_p2:
                        if st.session_state.user_id is None:
                            btn_label = _(" 무료 회원가입 후 배포하기", " Deploy after Free Sign Up")
                            if st.button(btn_label, type="primary", use_container_width=True):
                                import survey_manager; survey_manager.log_user_action(st.session_state.get("user_id") or "Guest", "설문 배포 실행")
                                st.warning(_(" 배포 및 DB 연동은 회원가입 후 가능합니다. (무료 사용자도 제한 없이 배포 및 연동 가능함)", " Deployment and DB integration are available after sign-up. (Free users can also deploy and link DB)"))
                                st.info(_("안심하세요. 현재 작성하신 내용은 창을 닫지 않고 왼쪽 사이드바에서 회원가입/로그인을 완료하시면 날아가지 않고 그대로 유지되어 즉시 배포하실 수 있습니다.", "Rest assured. The contents you have written will be maintained if you sign up and log in from the left sidebar without closing the window, allowing you to deploy immediately."))
                
                                pass
                        else:
                            btn_label = _("🚀 배포 및 DB 연동 (수정 내용 적용)", "🚀 Deploy & Link DB (Apply Changes)") if st.session_state.get("editing_survey_id") else _("🚀 배포 및 DB 연동", "🚀 Deploy & Link DB")
                            if st.button(btn_label, type="primary", use_container_width=True):
                                import survey_manager; survey_manager.log_user_action(st.session_state.get("user_id") or "Guest", "설문 배포 실행")
                                if not existing_sheet_id_input.strip():
                                    st.error(_("연동할 구글 스프레드시트 URL 주소를 입력하거나, 재사용할 기존 설문을 선택해 주세요.", "Please enter a valid Spreadsheet URL or select an existing survey to reuse."))
                                else:
                                    with st.spinner(_("구글 스프레드시트와 설문 구조를 연동하는 중...", "Linking survey structure with Google Spreadsheet...")):
                                        try:
                                            target_sheet_id = existing_sheet_id_input.strip()
                                            if "docs.google.com/spreadsheets" in target_sheet_id:
                                                parts = target_sheet_id.split("/d/")
                                                if len(parts) > 1:
                                                    target_sheet_id = parts[1].split("/")[0]

                                            # [2026-10-20] 대안 평가 요금 게이트: 스탠다드·프로 포함, 무료·베이직은 애드온 필요
                                            if len(model_structure.get("alternatives", []) or []) >= 2:
                                                _alt_tier = get_current_tier()
                                                if _alt_tier not in ("Standard", "Pro"):
                                                    raise Exception("ALT_TIER_GATE: 대안 평가(대안 선정)는 스탠다드·프로 요금제에 포함된 기능입니다. 무료·베이직 회원은 대안 평가 애드온 구매 후 사용하실 수 있습니다. (요금제 탭에서 업그레이드하거나 문의해 주세요.)")

                                            import os
                                            override_flag = 'sonwook_override.flag'
                                            if survey_admin_email == 'sonwook@gmail.com' and not target_sheet_id and os.path.exists(override_flag):
                                                target_sheet_id = '1Ux7_iZ4TCMIQPfnl4hfdkA8fUlpJcCM8OLp7xQD-wl4'
                                                os.remove(override_flag)

                                            if tier_level == 3:
                                                from survey_manager_v3 import create_survey_sheet_v3
                                                sheet_id = create_survey_sheet_v3(
                                                    title=survey_title,
                                                    admin_email=survey_admin_email,
                                                    ahp_model=model_structure,
                                                    scale_type=scale_option,
                                                    demographics=demographics_settings,
                                                    definition_map=definitions_map,
                                                    cr_limit=cr_limit,
                                                    cr_guide_method=cr_guide_method,
                                                    rewards_info=rewards_info,
                                                    description=survey_desc,
                                                    existing_sheet_id=target_sheet_id,
                                                    user_id=st.session_state.user_id,
                                                    show_hierarchy=show_hierarchy, alt_guide=alt_guide_text
                                                )
                                            else:
                                                sheet_id = create_survey_sheet(
                                                    title=survey_title,
                                                    admin_email=survey_admin_email,
                                                    ahp_model=model_structure,
                                                    scale_type=scale_option,
                                                    demographics=demographics_settings,
                                                    definition_map=definitions_map,
                                                    cr_limit=cr_limit,
                                                    cr_guide_method=cr_guide_method,
                                                    rewards_info=rewards_info,
                                                    description=survey_desc,
                                                    existing_sheet_id=target_sheet_id,
                                                    user_id=st.session_state.user_id,
                                                    show_hierarchy=show_hierarchy, alt_guide=alt_guide_text
                                                )



                                            # admin_surveys 테이블에 신규 설문 자동 등록 및 마스터 구글 시트 백업
                                            try:
                                                from survey_manager import save_admin_survey_to_gsheet
                                                save_admin_survey_to_gsheet(sheet_id, survey_title, st.session_state.user_id)
                            
                                                conn = sqlite3.connect('users.db')
                                                cur = conn.cursor()
                                                cur.execute("INSERT INTO admin_surveys (survey_id, title, admin_id, created_at) VALUES (?, ?, ?, datetime('now'))",
                                                            (sheet_id, survey_title, st.session_state.user_id))
                                                conn.commit()
                                                conn.close()
                                            except Exception as dbe:
                                                pass

                                            # 이미지 저장 로직 (최대 3개)
                                            # survey_image_data(2,3): 새로 업로드한 이미지
                                            # edit_survey_image(2,3): 기존에 저장된 이미지 (수정 없이 재저장할 때)
                                            try:
                                                conn_img = sqlite3.connect('users.db')
                                                cur_img = conn_img.cursor()
                                                cur_img.execute('''CREATE TABLE IF NOT EXISTS survey_images (
                                                                survey_id TEXT PRIMARY KEY,
                                                                image_data BLOB,
                                                                mime_type TEXT,
                                                                image_data2 BLOB,
                                                                mime_type2 TEXT,
                                                                image_data3 BLOB,
                                                                mime_type3 TEXT
                                                            )''')
                                                img_to_save1 = st.session_state.get('survey_image_data') or st.session_state.get('edit_survey_image')
                                                mime_to_save1 = st.session_state.get('survey_image_mime') or st.session_state.get('edit_survey_image_mime', 'image/png')
                                                img_to_save2 = st.session_state.get('survey_image_data2') or st.session_state.get('edit_survey_image2')
                                                mime_to_save2 = st.session_state.get('survey_image_mime2') or st.session_state.get('edit_survey_image_mime2', 'image/png')
                                                img_to_save3 = st.session_state.get('survey_image_data3') or st.session_state.get('edit_survey_image3')
                                                mime_to_save3 = st.session_state.get('survey_image_mime3') or st.session_state.get('edit_survey_image_mime3', 'image/png')

                                                if img_to_save1 or img_to_save2 or img_to_save3:
                                                    cur_img.execute("""INSERT OR REPLACE INTO survey_images 
                                                                    (survey_id, image_data, mime_type, image_data2, mime_type2, image_data3, mime_type3) 
                                                                    VALUES (?, ?, ?, ?, ?, ?, ?)""", 
                                                                    (sheet_id, img_to_save1, mime_to_save1, img_to_save2, mime_to_save2, img_to_save3, mime_to_save3))
                                                else:
                                                    cur_img.execute("DELETE FROM survey_images WHERE survey_id=?", (sheet_id,))
                                                conn_img.commit()
                                                conn_img.close()

                                                if img_to_save1:
                                                    st.session_state['edit_survey_image'] = img_to_save1
                                                    st.session_state['edit_survey_image_mime'] = mime_to_save1
                                                if img_to_save2:
                                                    st.session_state['edit_survey_image2'] = img_to_save2
                                                    st.session_state['edit_survey_image_mime2'] = mime_to_save2
                                                if img_to_save3:
                                                    st.session_state['edit_survey_image3'] = img_to_save3
                                                    st.session_state['edit_survey_image_mime3'] = mime_to_save3

                                                # 구글 시트에 이미지 영구 저장 동기화 (클라우드 재배포 시 보존)
                                                try:
                                                    from survey_manager import save_survey_images_to_gsheet
                                                    save_survey_images_to_gsheet(sheet_id, {
                                                        1: (img_to_save1, mime_to_save1),
                                                        2: (img_to_save2, mime_to_save2),
                                                        3: (img_to_save3, mime_to_save3)
                                                    }, user_id=st.session_state.user_id)
                                                except Exception:
                                                    pass
                                            except Exception as img_e:
                                                pass


                                            # 배포 주소 생성
                                            base_url = st.query_params.get("base_url", ["https://ahpkrj.streamlit.app/"])[0] if isinstance(st.query_params.get("base_url"), list) else "https://ahpkrj.streamlit.app/"
                                            if "localhost" in base_url or "127.0.0.1" in base_url:
                                                short_url = f"{base_url}?survey_id={sheet_id}"
                                            else:
                                                short_url = f"https://ahpkrj.streamlit.app/?survey_id={sheet_id}"

                                            # 사용자 배포 통계 및 설문 링크 기록
                                            update_user_survey_distribution(st.session_state.user_id, short_url)
                                            st.session_state._survey_cache_dirty = True  # 설문 목록 캐시 무효화
                                            st.session_state.pop('_cached_user_surveys', None)
                                            try:
                                                from survey_manager import get_admin_surveys_from_gsheet
                                                get_admin_surveys_from_gsheet.clear()
                                            except Exception:
                                                pass

                                            st.balloons()
                                            st.success(_("🎉 AHP 온라인 설문지가 성공적으로 업데이트(수정) 되었습니다!", "🎉 AHP online survey has been successfully updated!") if st.session_state.get("editing_survey_id") else _("🎉 AHP 온라인 설문지 및 연동 구글 시트 생성이 완료되었습니다!", "🎉 AHP online survey and linked Google Sheet creation are complete!"))

                                            st.code(short_url, language="text")
                                            st.info(_("**설문 전달 안내:** 생성된 설문조사 링크를 복사하여 이메일이나 메신저(카카오톡 등)로 응답 대상자에게 전달해 주세요.", "**Survey Sharing Guide:** Please copy the generated survey link and send it to respondents via email or messenger."))

                                            # [1단계] 응답 수집 시작하기 (목표 설정·QR·초대/리마인드 문구)
                                            try:
                                                from collection_support import render_collection_kickoff
                                                render_collection_kickoff(sheet_id, short_url, survey_title)
                                            except Exception as _cs_err:
                                                pass
                                        
                                            sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}"
                                            st.write("")
                                            st.markdown(f'''

                                            <div class="gs-nav-btn-box2">
                                                <a href="{sheet_url}" target="_blank">
                                                    📊 연동된 구글 시트 바로가기 (응답 데이터 실시간 확인)
                                                </a>
                                            </div>
                                            ''', unsafe_allow_html=True)
                                        except Exception as ex:
                                            if "ALT_TIER_GATE" in str(ex):
                                                st.error("🎯 " + str(ex).replace("ALT_TIER_GATE: ", ""))
                                            else:
                                                st.error(f"구글 시트 연동 실패: {ex}")
                                                import streamlit.components.v1 as components
                                                error_msg = str(ex).replace("'", "\\'").replace("\\n", " ")
                                                if any(token in str(ex) for token in ["429", "RESOURCE_EXHAUSTED", "Quota exceeded", "Rate Limit"]):
                                                    components.html(f"<script>alert('⏳ 구글 API 분당 요청 한도(429 Rate Limit)가 일시적으로 초과되었습니다.\\n\\n구글 API 정책상 서비스 계정의 1분당 API 요청 횟수(분당 60회)가 일시적으로 초과되어 발생한 대기 현상입니다.\\n서비스 계정 편집자 공유 권한 문제는 아니오니 안심하시기 바랍니다.\\n\\n약 30초~1분 정도 잠시 기다리신 후 [구글 시트 연동] 버튼을 다시 클릭해 주시기 바랍니다.\\n\\n상세 에러: {error_msg}');</script>", height=0, width=0)
                                                else:
                                                    components.html(f"<script>alert('❌ 구글 스프레드시트 연동에 실패했습니다.\\n\\n입력하신 URL의 스프레드시트에 접근할 수 없습니다.\\n안내된 서비스 계정 이메일(ahp-master-v2@ahp-login.iam.gserviceaccount.com)을 반드시 [편집자]로 추가하고 공유해 주셔야 연동 및 배포가 가능합니다.\\n\\n상세 에러: {error_msg}');</script>", height=0, width=0)


        _survey_setup_fragment()

    # -------------------------------------------------------------------------
    # [신규] 응답현황 대시보드 탭 (Tab 3) 상세 구현
    # -------------------------------------------------------------------------
    with survey_sub_status:
        if st.session_state.get('user_id') == 'shjeon':
            # Sub-tabs UI: pill CSS는 글로벌 테마(global_ahp_css)에 통합됨
        
            sub_tabs = st.tabs(["진행 현황", "답례품 발송 관리", "답례품 설정(Admin)"])
            tab_live_content = sub_tabs[0]
            with sub_tabs[1]:
                import coupon_manager
                coupon_manager.render_dispatch_tab()
            with sub_tabs[2]:
                import coupon_manager
                coupon_manager.render_admin_tab()
        else:
            tab_live_content = st.container()

        with tab_live_content:
            st.header(_("실시간 응답 현황", "Real-time Response Status"))
            selected_sheet_id = None
    
            if st.session_state.user_id is None:
                st.warning(_("로그인 후 이용 가능한 회원 전용 서비스입니다. (무료 회원도 모든 기능 사용 가능)",
                             "Member-only service. Log in to monitor responses. (Free members can use all features)"))
            else:
                # DB에서 해당 관리자가 생성한 설문 목록 조회
                import sqlite3
                import pandas as pd

                try:
                    sync_short_codes_from_gs()
                except Exception:
                    pass

                admin_surveys = []
                try:
                    conn = sqlite3.connect('users.db')
                    cur = conn.cursor()
                    cur.execute("SELECT survey_id, title, created_at FROM admin_surveys WHERE admin_id = ? ORDER BY created_at DESC", (st.session_state.user_id,))
                    sqlite_surveys = cur.fetchall()
                    conn.close()
            
                    gs_surveys = []
                    try:
                        from survey_manager import get_admin_surveys_from_gsheet
                        gs_surveys = get_admin_surveys_from_gsheet(st.session_state.user_id)
                    except Exception as gs_err:
                        st.warning(f"구글 스프레드시트 설문 동기화 실패: {gs_err}")
            
                    merged_surveys = {}
                    for s in gs_surveys + sqlite_surveys:
                        if s[0] not in merged_surveys:
                            merged_surveys[s[0]] = s
                    admin_surveys = list(merged_surveys.values())
                    admin_surveys.sort(key=lambda x: x[2], reverse=True)
                except Exception as e:
                    st.error(f"설문 목록 조회 실패: {e}")

                if not admin_surveys:
                    st.warning(_("배포된 설문지가 존재하지 않습니다. '온라인 설문지 제작' 탭에서 설문을 먼저 배포해 주세요.", "No surveys have been deployed. Please deploy a survey from the 'Online Survey Builder' tab first."))
                else:
                    tab3_main_col, tab3_side_col = st.columns([3.0, 1.1], gap="large")
                    with tab3_main_col:
                        # 로그인한 아이디에 맞춰 본인의 설문들만 드롭다운에 노출시킵니다.
                        survey_options = {f"{row[1]} ({row[2]})": row[0] for row in admin_surveys}
                        selected_label = st.selectbox(
                            "실시간 현황을 확인할 설문 선택",
                            list(survey_options.keys()),
                            key="tab3_survey_select"
                        )
                        selected_sheet_id = survey_options[selected_label]
                
                        selected_survey_info = next(s for s in admin_surveys if s[0] == selected_sheet_id)
                        survey_title = selected_survey_info[1]
                        created_at = selected_survey_info[2]
                
                        st.success(_(f" 현재 선택된 설문: **{survey_title}** (배포일시: {created_at})", f" Selected survey: **{survey_title}** (Deployed: {created_at})"))
                        st.divider()

                    with tab3_side_col:
                        if selected_sheet_id:
                            _status_url = f"https://ahpkrj.streamlit.app/?mode=status&survey_id={selected_sheet_id.strip()}"
                            with st.container(border=True):
                                st.markdown(f'<h4 style="color:black; font-family:Arial, sans-serif; font-weight:bold; margin-top:0; margin-bottom:15px; font-size:1.1rem;">{_("실시간 모니터링", "Live Monitoring")}</h4>', unsafe_allow_html=True)
                                st.markdown(
                                    f'<p style="color:#4b5563; font-size:0.875rem; line-height:1.5; margin-bottom:12px;">'
                                    f'{_("로그인 없이 외부 공동연구자나 의뢰인이 설문 응답 현황을 실시간으로 확인할 수 있는 전용 링크입니다.", "Dedicated real-time link for external collaborators or clients to view survey progress without login.")}'
                                    f'</p>',
                                    unsafe_allow_html=True
                                )
                                st.caption(_("실시간 현황 링크 (우측 상단 복사 아이콘):", "Live Status Link (Click top-right icon to copy):"))
                                st.code(_status_url, language="text")
                                st.link_button(_("↗️ 실시간 링크 바로 열기", "↗️ Open Live Link"), _status_url, use_container_width=True)

                            with st.expander(_("실시간 링크 안내", "Live Link Guide"), expanded=False):
                                st.markdown(_(
                                    "- **비회원 열람**: 로그인 없이 실시간 응답 통계 및 진행률을 확인할 수 있습니다.\n"
                                    "- **조회 전용**: 응답 데이터 수정 권한 없이 안전하게 대시보드만 조회됩니다.\n"
                                    "- **실시간 자동 반영**: 새로운 응답이 제출되면 링크 화면에서도 최신 데이터가 반영됩니다.",
                                    "- **Public View**: View response stats and progress without logging in.\n"
                                    "- **Read-Only**: Secure dashboard view without editing permissions.\n"
                                    "- **Auto-Sync**: Automatically reflects new responses as they arrive."
                                ))

            # 대시보드 렌더링
            if selected_sheet_id:
                tab3_main_col.__enter__()

                col_dash_btn1, col_dash_btn2 = st.columns([3, 1])
                with col_dash_btn1:
                    do_load_dash = st.button(_("🔄 실시간 설문 대시보드 및 응답 데이터 불러오기 / 새로고침", "🔄 Load/Refresh Live Survey Dashboard & Responses"), type="primary", use_container_width=True)
                with col_dash_btn2:
                    # [2026-11-05] 다이얼로그가 위젯 조작 시 닫히는 문제 수정 — 세션 상태로 열림 유지
                    if st.button(_("🗑️ 응답 데이터 초기화", "🗑️ Reset Responses"), type="secondary", use_container_width=True, key="btn_open_reset_tab3"):
                        st.session_state["show_reset_dialog"] = True
                        st.session_state["reset_dialog_sheet_id"] = selected_sheet_id
                        st.session_state["reset_dialog_title"] = survey_title
                        st.rerun()
                    # 세션 상태 플래그로 다이얼로그 유지 (버튼 클릭 후 리런에도 열림)
                    if st.session_state.get("show_reset_dialog"):
                        _dlg_sheet = st.session_state.get("reset_dialog_sheet_id")
                        _dlg_title = st.session_state.get("reset_dialog_title", "")
                        if _dlg_sheet:
                            show_reset_survey_dialog(_dlg_sheet, _dlg_title)
                        else:
                            st.session_state["show_reset_dialog"] = False

                if do_load_dash:
                    from survey_manager import get_survey_stats, get_survey_gspread_client, load_survey_metadata, clean_and_align_sheet_rows
                    with st.spinner("실시간 설문 현황 로딩 중..."):
                        # 1. Stats Loading
                        st.session_state["survey_stats"] = get_survey_stats(selected_sheet_id.strip())
                
                        # 2. Raw Data Loading
                        g_client = get_survey_gspread_client()
                        if g_client:
                            try:
                                survey_meta = load_survey_metadata(selected_sheet_id.strip())
                                spreadsheet = g_client.open_by_key(selected_sheet_id.strip())
                                raw_sheet = spreadsheet.worksheet("Raw_Data")
                                all_rows = raw_sheet.get_all_values()

                                try:
                                    demo_sheet = spreadsheet.worksheet("Demographic_Data")
                                    demo_rows = demo_sheet.get_all_values()
                                except Exception:
                                    demo_rows = []

                                live_df, clean_raw_matrix, raw_needs_repair = clean_and_align_sheet_rows(all_rows, survey_meta=survey_meta, is_demo=False)
                                demo_df, clean_demo_matrix, demo_needs_repair = clean_and_align_sheet_rows(demo_rows, survey_meta=survey_meta, is_demo=True)

                                if "Type" not in live_df.columns and "Type 1" in live_df.columns:
                                    live_df["Type"] = live_df["Type 1"]

                                st.session_state["live_df"] = live_df
                                st.session_state["demo_df"] = demo_df if not demo_df.empty else None

                                # 구글 시트에 중간에 삽입된 중복 헤더 행(ID)이 있거나 1행 헤더가 축소되어 있는 경우 자동 수복(Repair)
                                if raw_needs_repair and clean_raw_matrix:
                                    try:
                                        raw_sheet.clear()
                                        raw_sheet.update(range_name="A1", values=clean_raw_matrix)
                                    except Exception:
                                        pass

                                if demo_needs_repair and clean_demo_matrix and demo_sheet is not None:
                                    try:
                                        demo_sheet.clear()
                                        demo_sheet.update(range_name="A1", values=clean_demo_matrix)
                                    except Exception:
                                        pass

                            except Exception as g_err:
                                st.error(f"구글 시트에서 데이터를 읽어오는 중 에러 발생: {g_err}")
                                st.session_state["live_df"] = None
                        else:
                            st.warning("구글 Sheets API 클라이언트 연결 실패로 인해 구글 시트 내 데이터를 직접 다운로드할 수 없습니다.")
                            st.session_state["live_df"] = None

                if "survey_stats" in st.session_state:
                    stats = st.session_state["survey_stats"]
                    _t_visits = stats.get('visits', 0)
                    _t_comp = stats.get('completed', 0)
                    # [1단계] 현황판 조회 이벤트 (대시보드 로드 1회)
                    try:
                        _dash_flag = f"_dash_viewed_{selected_sheet_id}"
                        if not st.session_state.get(_dash_flag):
                            from survey_manager import log_structured_event, get_anonymous_user_id, get_anonymous_survey_id, EVENT_OWNER_DASHBOARD_VIEWED
                            log_structured_event(EVENT_OWNER_DASHBOARD_VIEWED,
                                anonymous_user_id=get_anonymous_user_id(st.session_state.get("user_id") or "guest"),
                                anonymous_survey_id=get_anonymous_survey_id(selected_sheet_id),
                                properties={"completed": _t_comp, "visits": _t_visits})
                            st.session_state[_dash_flag] = True
                    except Exception:
                        pass
                    # [1단계] 수집 진행 현황 (목표 대비 진행률·마감일·다음 행동) + 분석 준비 리포트
                    try:
                        from collection_support import render_collection_progress, render_analysis_readiness_entry
                        from survey_manager import load_survey_metadata as _load_meta_cs
                        _cs_meta = _load_meta_cs(selected_sheet_id.strip()) or {}
                        render_collection_progress(selected_sheet_id.strip(), _cs_meta, _t_comp, _t_visits)
                        render_analysis_readiness_entry(selected_sheet_id.strip(), _t_comp)
                        st.divider()
                    except Exception as _cs_e:
                        st.error(f"수집 현황 로드 실패: {_cs_e}")
                    _t_crate = f" ({(_t_comp / _t_visits * 100):.1f}%)" if _t_visits > 0 else ""
                    col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
                    with col_stat1:
                        st.metric(_("총 접속자 수 (Visits)", "Total Visits"), f"{_t_visits}" + _("명", ""))
                    with col_stat2:
                        st.metric(_("완료 응답자 수 (Completed)", "Completed Responses"), f"{_t_comp}" + _("명", "") + _t_crate)
                    with col_stat3:
                        st.metric(_("일관성 초과 중단자 (CR Fail)", "CR Fail Abandonments"), f"{stats.get('abandoned_cr', 0)}" + _("회", " times"))
                    with col_stat4:
                        st.metric(_("단순 이탈 중단자 (Bounce)", "Bounced Visitors"), f"{stats.get('abandoned_bounce', 0)}" + _("명", ""))

                    if _t_comp > 0:
                        st.warning(_("⚠️ 응답 {}건이 있습니다. 실제 조사 시작 전 '응답 데이터 초기화' 버튼으로 삭제하세요.", "⚠️ There are {} responses. Please delete them with the 'Reset Responses' button before starting the actual survey.").format(_t_comp))

                    # 시각화 차트 추가
                    import plotly.express as px

                    chart_data = pd.DataFrame({
                        "구분": ["응답 완료", "일관성 초과 중단", "단순 페이지 이탈"],
                        "인원수": [stats['completed'], stats['abandoned_cr'], stats['abandoned_bounce']]
                    })

                    fig_stats = px.bar(
                        chart_data,
                        x="구분",
                        y="인원수",
                        text="인원수",
                        color="구분",
                        color_discrete_map={
                            "응답 완료": "#2E7D32",
                            "일관성 초과 중단": "#C62828",
                            "단순 페이지 이탈": "#EF6C00"
                        },
                        title="설문 참여 상태별 분포"
                    )
                    fig_stats.update_layout(showlegend=False)
                    st.plotly_chart(fig_stats, use_container_width=True)

                if "live_df" in st.session_state and st.session_state["live_df"] is not None:
                    live_df = st.session_state["live_df"]
                    demo_df = st.session_state.get("demo_df", None)

                    # 구글 시트에서 실시간 응답 로데이터(Raw_Data) 다운로드 기능 추가
                    with st.expander(_("📥 실시간 구글 시트 응답 데이터 다운로드 센터", "📥 Real-time Google Sheet Response Data Download Center"), expanded=True):
                        if not live_df.empty:
                            st.success(f"구글 스프레드시트에서 실시간 응답 데이터를 성공적으로 불러왔습니다. (Raw_Data: {len(live_df)}건" + (f", Demographic_Data: {len(demo_df)}건" if demo_df is not None else "") + ")")
                    

                            # ── 인라인 AHP 분석 결과 표시 ──
                            if st.session_state.get("_run_inline_analysis") and st.session_state.get("ahp_df_main") is not None:
                                st.session_state["_run_inline_analysis"] = False
                                st.divider()
                                st.subheader(_("📊 AHP 분석 결과 (빠른 미리보기)", "📊 AHP Analysis Results (Quick Preview)"))
                            
                                _inline_cr = 0.1
                                _inline_max_iter = 500
                                _inline_lr = 0.6
                                _inline_mean = 'geometric'
                                _inline_method = 'traditional'
                            
                                try:
                                    _df_main = st.session_state["ahp_df_main"]
                                    _main_res, _main_facts, _main_excl, _main_excl_df = process_single_sheet(
                                        _df_main, _inline_cr, _inline_max_iter, _inline_lr, _inline_mean, _inline_method
                                    )
                                
                                    if not _main_res.empty:
                                        _w_cols = [f"Weight_{f}" for f in _main_facts]
                                        _main_matrices = np.stack(_main_res['Matrix_Object'].values)
                                        _grp_matrix = gmean(_main_matrices, axis=0)
                                        _grp_cr, _grp_ci, _not_used = calculate_consistency(_grp_matrix, method=_inline_mean)
                                        _grp_w = _main_res[_w_cols].apply(lambda x: gmean(x), axis=0)
                                        _grp_w = _grp_w / _grp_w.sum()
                                    
                                        # 상위 기준 가중치 표시
                                        st.markdown(_("#### 📋 상위 기준 가중치", "#### 📋 Main Criteria Weights"))
                                    
                                        _weight_data = []
                                        for i, f in enumerate(_main_facts):
                                            _weight_data.append({
                                                _("순위", "Rank"): i + 1,
                                                _("평가 기준", "Criteria"): f,
                                                _("가중치", "Weight"): round(float(_grp_w.iloc[i] if hasattr(_grp_w, 'iloc') else _grp_w[i]), 4),
                                            })
                                        _weight_data.sort(key=lambda x: x[_("가중치", "Weight")], reverse=True)
                                        for rank_i, item in enumerate(_weight_data):
                                            item[_("순위", "Rank")] = rank_i + 1
                                    
                                        _weight_df = pd.DataFrame(_weight_data)
                                        st.dataframe(_weight_df, use_container_width=True, hide_index=True)
                                    
                                        col_cr1, col_cr2, col_cr3 = st.columns(3)
                                        col_cr1.metric(_("유효 응답자 수", "Valid Respondents"), f"{len(_main_res)}명")
                                        col_cr2.metric(_("제외 응답자 수", "Excluded"), f"{len(_main_excl_df) if not _main_excl_df.empty else 0}명")
                                        col_cr3.metric(_("그룹 CR", "Group CR"), f"{_grp_cr:.4f}")
                                    
                                        # 가중치 막대 차트
                                        import plotly.express as px
                                        _chart_df = _weight_df.sort_values(_("가중치", "Weight"), ascending=True)
                                        _fig = px.bar(_chart_df, x=_("가중치", "Weight"), y=_("평가 기준", "Criteria"),
                                                      orientation='h', text=_("가중치", "Weight"),
                                                      title=_("상위 기준 가중치 비교", "Main Criteria Weight Comparison"))
                                        _fig.update_traces(texttemplate='%{text:.4f}', textposition='outside')
                                        _fig.update_layout(height=max(300, len(_main_facts) * 50), yaxis={'categoryorder': 'total ascending'})
                                        st.plotly_chart(_fig, use_container_width=True)
                                    
                                        # 하위 기준 분석
                                        _sub_dfs = st.session_state.get("ahp_sub_dfs", {})
                                        if _sub_dfs:
                                            st.markdown(_("#### 📋 하위 기준 가중치", "#### 📋 Sub-Criteria Weights"))
                                            for _parent, _sub_df in _sub_dfs.items():
                                                try:
                                                    _sub_res, _sub_facts, _sub_excl, _sub_excl_df = process_single_sheet(
                                                        _sub_df, _inline_cr, _inline_max_iter, _inline_lr, _inline_mean, _inline_method
                                                    )
                                                    if not _sub_res.empty:
                                                        _sw_cols = [f"Weight_{f}" for f in _sub_facts]
                                                        _sw = _sub_res[_sw_cols].apply(lambda x: gmean(x), axis=0)
                                                        _sw = _sw / _sw.sum()
                                                        _sub_weight_data = []
                                                        for si, sf in enumerate(_sub_facts):
                                                            _sub_weight_data.append({
                                                                _("순위", "Rank"): si + 1,
                                                                _("상위 기준", "Parent"): _parent,
                                                                _("하위 기준", "Sub-Criteria"): sf,
                                                                _("가중치", "Weight"): round(float(_sw.iloc[si] if hasattr(_sw, 'iloc') else _sw[si]), 4),
                                                            })
                                                        _sub_weight_data.sort(key=lambda x: x[_("가중치", "Weight")], reverse=True)
                                                        for ri, si_item in enumerate(_sub_weight_data):
                                                            si_item[_("순위", "Rank")] = ri + 1
                                                    
                                                        with st.expander(f"📂 {_parent}", expanded=True):
                                                            st.dataframe(pd.DataFrame(_sub_weight_data), use_container_width=True, hide_index=True)
                                                except Exception:
                                                    pass
                                    
                                        st.info(_("💡 상세 분석 결과는 상단의 **'엑셀 업로드 분석'** 탭에서 **'🌐 배포된 온라인 설문 데이터 연동'**을 선택하면 전체 결과(CR 보정, ANOVA, 엑셀 다운로드 등)를 확인할 수 있습니다.",
                                                  "💡 For detailed results (CR correction, ANOVA, Excel download), go to the **'Upload & Analyze'** tab and select **'Link Online Survey Data'**."))
                                    else:
                                        st.warning(_("유효한 분석 데이터가 없습니다.", "No valid analysis data found."))
                                except Exception as _inline_err:
                                    st.error(f"인라인 분석 실행 중 오류: {_inline_err}")

                            tab_raw, tab_demo = st.tabs(["📊 Raw_Data (AHP 쌍대비교 데이터)", "👤 Demographic_Data (인구통계/사전순위)"])
                            with tab_raw:
                                # Prevent duplicate column name error (PyArrow ValueError)
                                _display_df = live_df.copy()
                                if _display_df.columns.duplicated().any():
                                    cols = list(_display_df.columns)
                                    seen = {}
                                    for i, c in enumerate(cols):
                                        if c in seen:
                                            seen[c] += 1
                                            cols[i] = f"{c}_{seen[c]}"
                                        else:
                                            seen[c] = 0
                                    _display_df.columns = cols
                                st.dataframe(_display_df, use_container_width=True)
                            with tab_demo:
                                if demo_df is not None:
                                    _demo_display = demo_df.copy()
                                    if _demo_display.columns.duplicated().any():
                                        cols = list(_demo_display.columns)
                                        seen = {}
                                        for i, c in enumerate(cols):
                                            if c in seen:
                                                seen[c] += 1
                                                cols[i] = f"{c}_{seen[c]}"
                                            else:
                                                seen[c] = 0
                                        _demo_display.columns = cols
                                    st.dataframe(_demo_display, use_container_width=True)
                                else:
                                    st.info("수집된 인구통계 데이터가 없거나 Demographic_Data 시트가 생성되지 않았습니다.")

                            # Excel 및 CSV 내보내기 버튼 제공
                            import io

                            # 1. Excel 내보내기 (두 개의 시트를 모두 포함)
                            excel_buffer = io.BytesIO()
                            with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                                from survey_manager import load_survey_metadata
                                survey_meta = load_survey_metadata(selected_sheet_id)
                                parsed_ok = False
                        
                                if survey_meta:
                                    ahp_model = survey_meta.get("AHP_Model_JSON", {})
                                    tier_level = int(survey_meta.get("Tier_Level", 2))
                                    base_cols = ["ID", "Type"]
                                    main_criteria = ahp_model.get("main", [])
                                    main_pairs = []
                                    for i in range(len(main_criteria)):
                                        for j in range(i + 1, len(main_criteria)):
                                            main_pairs.append(f"{main_criteria[i]}_{main_criteria[j]}")
                                    main_cols = [c for c in base_cols if c in live_df.columns] + [p for p in main_pairs if p in live_df.columns]
                            
                                    if len(main_cols) > 2:
                                        df_main_dl = live_df[main_cols].copy()
                                        df_main_dl.to_excel(writer, index=False, sheet_name="Main_Criteria")
                                
                                        sub_criteria_map = ahp_model.get("subs", {})
                                        for main_c, subs in sub_criteria_map.items():
                                            if len(subs) >= 2:
                                                sub_pairs = []
                                                for i in range(len(subs)):
                                                    for j in range(i + 1, len(subs)):
                                                        sub_pairs.append(f"{subs[i]}_{subs[j]}")
                                                sub_cols = [c for c in base_cols if c in live_df.columns] + [p for p in sub_pairs if p in live_df.columns]
                                                df_sub_dl = live_df[sub_cols].copy()
                                                df_sub_dl.to_excel(writer, index=False, sheet_name=main_c[:31])
                                        
                                        if tier_level == 3:
                                            sub_sub_map = ahp_model.get("sub_subs", {})
                                            _ss_blocks_dl = _ss_blocks_in_order(ahp_model)
                                            for main_c, subs in sub_criteria_map.items():
                                                for sub_c in subs:
                                                    sub_subs = sub_sub_map.get(sub_c, [])
                                                    if len(sub_subs) >= 2:
                                                        sub_sub_pairs = []
                                                        for i in range(len(sub_subs)):
                                                            for j in range(i + 1, len(sub_subs)):
                                                                sub_sub_pairs.append(f"{sub_subs[i]}_{sub_subs[j]}")
                                                        df_ss_dl = _extract_ss_block_df(live_df, base_cols, _ss_blocks_dl, sub_c, sub_sub_pairs)
                                                        df_ss_dl.to_excel(writer, index=False, sheet_name=sub_c[:31])
                                        parsed_ok = True
                        
                                if not parsed_ok:
                                    live_df.to_excel(writer, index=False, sheet_name='Raw_Data')
                                else:
                                    live_df.to_excel(writer, index=False, sheet_name='Raw_Data_Dump')
                            
                                if demo_df is not None:
                                    demo_df.to_excel(writer, index=False, sheet_name='Demographic_Data')

                            col_dl1, col_dl2 = st.columns(2)
                            with col_dl1:
                                st.download_button(
                                    "📥 실시간 응답 Excel 다운로드 (.xlsx)",
                                    data=excel_buffer.getvalue(),
                                    file_name=f"Survey_Live_Data_{selected_sheet_id.strip()[:6]}.xlsx",
                                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                    use_container_width=True,
                                    type="primary"
                                )
                            # 2. CSV 내보내기 (Raw_Data 우선 내보내기)
                            csv_buffer = io.StringIO()
                            live_df.to_csv(csv_buffer, index=False, header=True)
                            with col_dl2:
                                st.download_button(
                                    "📥 실시간 응답 CSV 다운로드 (.csv)",
                                    data=csv_buffer.getvalue().encode('utf-8-sig'),
                                    file_name=f"Survey_Live_Data_{selected_sheet_id.strip()[:6]}.csv",
                                    mime="text/csv",
                                    use_container_width=True
                                )
                        else:
                            st.info("구글 시트에 수집된 응답 로데이터가 아직 비어 있습니다.")

                # 로컬 안전 백업 데이터 조회 및 추출 유틸리티
                try:
                    conn = sqlite3.connect('users.db')
                    backup_df = pd.read_sql_query(
                        "SELECT id, respondent_id, response_json, created_at FROM survey_backup_responses WHERE survey_id = ?",
                        conn, params=(selected_sheet_id.strip(),)
                    )
                    conn.close()

                    if not backup_df.empty:
                        with st.expander("🛡️ 서버 로컬 안전 백업 관리 센터"):
                            st.success(f"구글 시트 연동과 관계없이 서버 로컬 데이터베이스에 저장된 안전 백업 데이터가 총 {len(backup_df)}건 존재합니다.")
                            st.dataframe(backup_df[["id", "respondent_id", "created_at"]], use_container_width=True)

                            # 전체 로 데이터 복구 엑셀/CSV 데이터 빌드
                            recovered_raw_rows = []
                            recovered_demo_rows = []
                            for idx_b, r_b in backup_df.iterrows():
                                payload = json.loads(r_b["response_json"])
                                if "raw_row_data" in payload:
                                    recovered_raw_rows.append(payload["raw_row_data"])
                                elif "row_data" in payload:
                                    # 하위 호환성
                                    recovered_raw_rows.append(payload["row_data"])

                                if "demo_row_data" in payload:
                                    recovered_demo_rows.append(payload["demo_row_data"])

                            if recovered_raw_rows:
                                import io

                                # 헤더 복구 로직 추가
                                raw_headers = None
                                demo_headers = None
                                from survey_manager import load_survey_metadata
                                survey_meta = load_survey_metadata(selected_sheet_id.strip())
                                if survey_meta:
                                    ahp_model = survey_meta.get("AHP_Model_JSON", {})
                                    demographics = survey_meta.get("Demographics", {})
                                    rewards_info = survey_meta.get("Rewards_Info", {})
                                    tier_level = str(survey_meta.get("Tier_Level", "2"))
                            
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
                                    main_criteria = ahp_model.get("main", [])
                                    for i in range(len(main_criteria)):
                                        for j in range(i + 1, len(main_criteria)):
                                            raw_headers.append(f"{main_criteria[i]}_{main_criteria[j]}")
                                    sub_criteria_map = ahp_model.get("subs", {})
                                    for main_c in main_criteria:
                                        subs = sub_criteria_map.get(main_c, [])
                                        if len(subs) >= 2:
                                            for i in range(len(subs)):
                                                for j in range(i + 1, len(subs)):
                                                    raw_headers.append(f"{subs[i]}_{subs[j]}")
                                    if tier_level == "3":
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
                            
                                    demo_headers = ["ID"] + type_headers
                                    if demographics.get("name"): demo_headers.append("성명")
                                    if demographics.get("age"): demo_headers.append("연령")
                                    if demographics.get("gender"): demo_headers.append("성별")
                                    if demographics.get("experience"): demo_headers.append("경력년수")
                                    # if demographics.get("affiliation"): demo_headers.append("소속")
                                    if demographics.get("email"): demo_headers.append("이메일")
                                    demo_headers.append("사전순위지정")
                                    if rewards_info.get("enabled"):
                                        demo_headers.append("경품연락처" if tier_level == "3" else "답례품_연락처")
                                    demo_headers.append("제출시간")

                                df_raw_backup = pd.DataFrame(recovered_raw_rows)
                                if raw_headers and len(raw_headers) == len(df_raw_backup.columns):
                                    df_raw_backup.columns = raw_headers
                                elif raw_headers and len(raw_headers) > len(df_raw_backup.columns):
                                    df_raw_backup.columns = raw_headers[:len(df_raw_backup.columns)]
                            
                                df_demo_backup = None
                                if recovered_demo_rows:
                                    df_demo_backup = pd.DataFrame(recovered_demo_rows)
                                    if demo_headers and len(demo_headers) == len(df_demo_backup.columns):
                                        df_demo_backup.columns = demo_headers
                                    elif demo_headers and len(demo_headers) > len(df_demo_backup.columns):
                                        df_demo_backup.columns = demo_headers[:len(df_demo_backup.columns)]

                                # Excel로 백업 데이터를 템플릿 구조에 맞춰 분할하여 다운로드
                                if survey_meta and "AHP_Model_JSON" in survey_meta:
                                    excel_backup_buffer = export_to_template_excel(df_raw_backup, df_demo_backup, survey_meta["AHP_Model_JSON"], survey_meta.get("Tier_Level", 2))
                                else:
                                    excel_backup_buffer = io.BytesIO()
                                    with pd.ExcelWriter(excel_backup_buffer, engine='openpyxl') as writer:
                                        df_raw_backup.to_excel(writer, index=False, header=bool(raw_headers), sheet_name='Raw_Data')
                                        if df_demo_backup is not None:
                                            df_demo_backup.to_excel(writer, index=False, header=bool(demo_headers), sheet_name='Demographic_Data')

                                col_b_dl1, col_b_dl2 = st.columns(2)
                                with col_b_dl1:
                                    st.download_button(
                                        "📥 로컬 백업 Excel 다운로드 (.xlsx)",
                                        data=excel_backup_buffer.getvalue(),
                                        file_name=f"Backup_Recovery_{selected_sheet_id.strip()[:6]}.xlsx",
                                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                        use_container_width=True,
                                        type="primary"
                                    )

                                with col_b_dl2:
                                    # CSV 파일 형태로 복구 파일 내보내기 (Raw_Data 우선)
                                    output_csv = io.StringIO()
                                    df_raw_backup.to_csv(output_csv, index=False, header=bool(raw_headers))
                                    st.download_button(
                                        "📥 로컬 백업 Raw_Data CSV 다운로드 (.csv)",
                                        data=output_csv.getvalue().encode('utf-8-sig'),
                                        file_name=f"Backup_Recovery_Raw_{selected_sheet_id.strip()[:6]}.csv",
                                        mime="text/csv",
                                        use_container_width=True
                                    )
                    else:
                        st.caption("이 설문지에 등록된 로컬 서버 백업 데이터가 없습니다. (모든 데이터 정상 적재)")
                except Exception as err:
                    st.caption(f"로컬 백업 조회 불가: {err}")

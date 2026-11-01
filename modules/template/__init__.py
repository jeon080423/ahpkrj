"""
AHPMASTER 템플릿 모듈
- 데이터 입력 양식 만들기 UI (main_tab_coding)

[2026-11-01] Team 4: standard_app.py L12667-12931에서 추출
- st.stop() 0개 확인됨
- 264줄

주의: 이 모듈은 st.session_state를 직접 사용합니다.
"""
import streamlit as st
import os

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


def render_template_module():
    """데이터 입력 양식 만들기 UI 렌더링.
    
    원본: standard_app.py L12667-12931의 'with main_tab_coding:' 블록
    """
    # -------------------------------------------------------------------------
    # [신규] 온라인 설문지 제작 탭 (Tab 2) 상세 구현
    # -------------------------------------------------------------------------
    st.header(_("AHP 분석 모델 설정 및 코딩 양식 다운로드", "Setup AHP Decision Model & Download Coding Form"))
    
    saved_model = None
    if st.session_state.user_id is None:
        st.info(_("로그인 후 나만의 분석 모델을 저장할 수 있습니다. (비로그인에서도 샘플 데이터로 미리보기 가능)",
                  "Log in to save your custom models. (Preview with sample data available without login)"))
    else:
        saved_model = load_user_model(st.session_state.user_id)
        is_en = st.session_state.get('lang', 'ko') == 'en'
    
    en_default_main = "Governance, Planning, Feasibility, Effectiveness"
    en_default_subs = {
        "Governance": "AdminSupport, Community, PM",
        "Planning": "IssueFit, AlternativeFit, GoalClarity",
        "Feasibility": "LandAcquisition, ProjectDetail, CostFit",
        "Effectiveness": "Economic, Social, Performance"
    }
    ko_default_main = "거버넌스, 계획타당성, 실현가능성, 사업효과"
    ko_default_subs = {
        "거버넌스": "행정지원, 지역공동체, 총괄사업관리자",
        "계획타당성": "현안적정성, 대안적정성, 목표구체성",
        "실현가능성": "부지확보, 사업구체화, 사업비적정성",
        "사업효과": "경제적효과, 사회적효과, 성과관리"
    }

    # [신규] 3계층(V3) 샘플 데이터 (스마트폰 구매 결정)
    en_default_main_v3 = "Functionality, Design, Economy"
    en_default_subs_v3 = {
        "Functionality": "Hardware, Software",
        "Design": "Appearance, Usability",
        "Economy": "Device Price, Maintenance"
    }
    en_default_sub_subs_v3 = {
        "Hardware": "Camera, Battery, Processor",
        "Software": "OS, Default Apps",
        "Appearance": "Color, Material",
        "Usability": "", 
        "Device Price": "Lump Sum, Installment",
        "Maintenance": "Plan, Repair"
    }

    ko_default_main_v3 = "기능성, 디자인, 경제성"
    ko_default_subs_v3 = {
        "기능성": "하드웨어, 소프트웨어",
        "디자인": "외관, 편의성",
        "경제성": "단말기가격, 유지비용"
    }
    ko_default_sub_subs_v3 = {
        "하드웨어": "카메라, 배터리, 프로세서",
        "소프트웨어": "운영체제, 기본앱",
        "외관": "색상, 재질",
        "편의성": "", 
        "단말기가격": "일시불, 할부",
        "유지비용": "통신요금, AS비용"
    }


    with st.expander(_("나의 분석 모델 만들기", "Create Custom AHP Model"), expanded=True):
        st.info(_("대항목과 세부항목을 입력하여 코딩 엑셀 양식을 생성하세요. (일반 AHP / 퍼지 AHP 공용)",
                  "Enter criteria to generate your coding Excel template. (For both Traditional and Fuzzy AHP)"))
        
        # 계층 구조 설정 (2계층 기준과 동일하게 전체 공개)
        tier_level = 2
        st.markdown(_("#####  계층 구조 설정", "##### Hierarchy Setup"))
        tier_choice = st.radio(
            _("계층 레벨을 선택하세요.", "Select Hierarchy Level."),
            [_("2계층 (대분류 - 중분류)", "2-Tier (Main - Sub)"),
             _("3계층 (대분류 - 중분류 - 소분류)", "3-Tier (Main - Sub - Sub-sub)")],
            index=0,
            horizontal=True,
            key="tab1_tier_choice"
        )
        if _("3계층", "3-Tier") in tier_choice:
            tier_level = 3
        st.markdown("---")
            
        # [신규] tier_level에 따라 샘플 데이터 스위칭
        if is_en:
            default_main = en_default_main_v3 if tier_level == 3 else en_default_main
            default_subs = en_default_subs_v3 if tier_level == 3 else en_default_subs
            default_sub_subs = en_default_sub_subs_v3 if tier_level == 3 else {}
        else:
            default_main = ko_default_main_v3 if tier_level == 3 else ko_default_main
            default_subs = ko_default_subs_v3 if tier_level == 3 else ko_default_subs
            default_sub_subs = ko_default_sub_subs_v3 if tier_level == 3 else {}
            
        if saved_model:
            saved_main = saved_model.get('main', '')
            if is_en and (saved_main == ko_default_main or saved_main == ko_default_main_v3 or not saved_main):
                pass
            elif not is_en and (saved_main == en_default_main or saved_main == en_default_main_v3 or not saved_main):
                pass
            else:
                default_main = saved_main
                default_subs = saved_model.get('subs', default_subs)
                
        main_criteria_input = st.text_input(_("대항목 (Main Criteria, 쉼표 구분)", "Main Criteria (comma-separated)"), value=default_main)
        main_criteria_list = [x.strip() for x in main_criteria_input.split(',') if x.strip()]
        
        model_structure = {}
        sub_sub_structure = {}
        if main_criteria_list:
            for mc in main_criteria_list:
                d_val = default_subs.get(mc, "")
                if isinstance(d_val, list): d_val = ", ".join(d_val)
                sub_input = st.text_input(_(f"'{mc}'의 세부항목", f"Sub-criteria for '{mc}'"), value=d_val, key=f"tab1_sub_{mc}")
                sub_list = [x.strip() for x in sub_input.split(',') if x.strip()]
                model_structure[mc] = sub_list
                
                if tier_level == 3 and sub_list:
                    with st.expander(_(f"▶ '{mc}'의 소분류 (Sub-sub-criteria) 입력", f"▶ Enter Sub-sub-criteria for '{mc}'"), expanded=True):

                        for sub_c in sub_list:
                            sub_sub_input = st.text_input(
                                _(f"▶ '{sub_c}'의 소분류 (쉼표 구분)", f"▶ Sub-factors of '{sub_c}' (comma-separated)"),
                                value=default_sub_subs.get(sub_c, ""),
                                placeholder=_("예: 항목1, 항목2 (※ 하위 요인이 없다면 비워두세요)", "e.g., Item1, Item2 (leave blank if no sub-factors)"),
                                help=_("입력칸을 비워두면 이 항목은 자동으로 2계층 구조로 간주되어 분석됩니다.", "If left blank, this item will be treated as a 2-level hierarchy."),
                                key=f"tab1_sub_sub_{sub_c}"
                            )
                            parsed_sub_subs = [x.strip().replace("_", " ") for x in sub_sub_input.split(",") if x.strip()]
                            if parsed_sub_subs:
                                sub_sub_structure[sub_c] = parsed_sub_subs
        
        # ── 계층 구조 트리 시각화 ──────────────────────────────────────
        if main_criteria_list:
            st.markdown("---")
            st.markdown(_("##### 📐 계층 구조 미리보기", "##### 📐 Hierarchy Preview"))
            from survey_manager import generate_hierarchy_tree_html
            tab1_model_dict = {
                "main": main_criteria_list,
                "subs": model_structure,
                "sub_subs": sub_sub_structure if tier_level == 3 else {}
            }
            tree_html = generate_hierarchy_tree_html(tab1_model_dict, tier_level=tier_level, lang=st.session_state.get('lang', 'ko'))
            if tree_html:
                st.markdown(tree_html, unsafe_allow_html=True)
        # ─────────────────────────────────────────────────────────────

        # ── 데이터 입력 가이드 (항상 노출) ────────────────────────────
        with st.expander(_("📝 다운로드한 엑셀에 데이터를 입력하는 방법", "📝 How to enter data in the downloaded Excel"), expanded=False):
            st.markdown(_("""
**① 엑셀 파일 열기**: 아래 버튼으로 다운로드한 엑셀 파일을 실행합니다.

**② 쌍대비교 데이터 입력**:
- **왼쪽(시행)** 항목이 더 중요하면: **음수** 입력 (예: `-3`)
- **오른쪽(미시행)** 항목이 더 중요하면: **양수** 입력 (예: `3`)
- 두 항목이 **동등**하면: `1` 입력

**③ 필수 정보 입력**:
- A열(`ID`): 응답자 번호 (1, 2, 3, ...)
- B열(`Type`): 그룹명 (예: 전문가, 주민, 공무원 등)
            """, """
**① Open the Excel file**: Run the template downloaded via the button below.

**② Enter pairwise comparison data**:
- If the **left** item is more important: enter a **negative** value (e.g., `-3`)
- If the **right** item is more important: enter a **positive** value (e.g., `3`)
- If they are **equal**: enter `1`

**③ Required information**:
- Column A (`ID`): Respondent number (1, 2, 3, ...)
- Column B (`Type`): Group name (e.g., Expert, Public, Official)
            """))
            img_file = _("ahp_input_guide.png", "ahp_input_guide_en.png")
            if os.path.exists(img_file):
                st.image(img_file, caption=_("[참고] 설문 응답을 엑셀에 입력하는 방법", "[Reference] How to enter survey responses into Excel"))
        # ─────────────────────────────────────────────────────────────

        col1, col2 = st.columns(2)
        with col1:
            generate_clicked = st.button(_("1️⃣ 설정한 모델로 AHP 코딩 엑셀 양식 생성", "1️⃣ Generate Excel Template with this Model"), use_container_width=True)
            if generate_clicked:
                import survey_manager; survey_manager.log_user_action(st.session_state.get("user_id") or "Guest", "AHP 엑셀 양식 생성")
        
        if generate_clicked:
            if st.session_state.user_id is None:
                st.warning(_("코딩 엑셀 양식 생성 및 다운로드는 로그인한 사용자(무료 회원 포함)만 이용 가능합니다. 왼쪽 메뉴에서 로그인하거나 회원가입을 해주세요.", "Generating and downloading Excel templates is only available to logged-in users (including free members). Please log in or sign up from the left menu."))
            elif not main_criteria_list:
                st.error(_("대항목 입력 필요", "Main criteria input is required"))
            else:
                current_model = {'main': main_criteria_input, 'subs': model_structure, 'sub_subs': sub_sub_structure, 'Tier_Level': tier_level}
                save_user_model(st.session_state.user_id, current_model)
                st.toast(_("모델 저장 완료", "Model successfully saved"))
                
                output_template = io.BytesIO()
                with pd.ExcelWriter(output_template, engine='xlsxwriter') as writer:
                    main_pairs = list(itertools.combinations(main_criteria_list, 2))
                    main_cols_tpl = ["ID", "Type"] + [f"{a}_{b}" for a, b in main_pairs]
                    df_template_main = pd.DataFrame(columns=main_cols_tpl)
                    df_template_main.loc[0] = [1, ""] + [0]*len(main_pairs)
                    df_template_main.to_excel(writer, sheet_name="Main_Criteria", index=False)
                    
                    for mc, subs in model_structure.items():
                        if len(subs) < 2:
                            df_sub = pd.DataFrame(columns=["ID", "Type"])
                        else:
                            sub_pairs = list(itertools.combinations(subs, 2))
                            sub_cols = ["ID", "Type"] + [f"{a}_{b}" for a, b in sub_pairs]
                            df_sub = pd.DataFrame(columns=sub_cols)
                            df_sub.loc[0] = [1, ""] + [0]*len(sub_pairs)
                        safe_sheet_name = mc[:31]
                        df_sub.to_excel(writer, sheet_name=safe_sheet_name, index=False)
                        
                    # 3계층 시트 생성
                    if tier_level == 3:
                        for mc, subs in model_structure.items():
                            for sub_c in subs:
                                ss_list = sub_sub_structure.get(sub_c, [])
                                if len(ss_list) < 2:
                                    df_ss = pd.DataFrame(columns=["ID", "Type"])
                                else:
                                    ss_pairs = list(itertools.combinations(ss_list, 2))
                                    ss_cols = ["ID", "Type"] + [f"{a}_{b}" for a, b in ss_pairs]
                                    df_ss = pd.DataFrame(columns=ss_cols)
                                    df_ss.loc[0] = [1, ""] + [0]*len(ss_pairs)
                                safe_ss_name = sub_c[:31]
                                df_ss.to_excel(writer, sheet_name=safe_ss_name, index=False)
                                
                output_template.seek(0)
                
                with col2:
                    st.download_button(
                        label=_("2️⃣ 📥 코딩 엑셀 양식 다운로드", "2️⃣ 📥 Download Excel Template"),
                        data=output_template,
                        file_name="AHP_Master_Template.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                        type="primary"
                    )
                
                st.info(_("**안내:** 1번 버튼을 눌러 모델을 생성 및 저장했습니다. 우측의 2번 버튼을 클릭하여 컴퓨터에 코딩 엑셀 양식 파일을 저장하세요.", 
                          "💡 **Info:** The model has been generated and saved. Click the 2nd button on the right to download the Excel template file to your computer."))

                st.markdown(_("""
                ---
                ### 📝 데이터 입력 가이드
                1. **엑셀 파일 열기**: 위 버튼을 눌러 다운로드한 엑셀 파일을 실행합니다.
                2. **쌍대비교 데이터 입력**:
                    - **왼쪽** 항목이 더 중요하면: **음수** 입력 (예: -3)
                    - **오른쪽** 항목이 더 중요하면: **양수** 입력 (예: 3)
                    - **동등**하면: `1` 입력
                3. **필수 정보 입력**: A열(ID), **B열(Type)에 그룹명 입력 (예: 전문가, 주민 등)**
                """,
                """
                ---
                ### 📝 Data Input Guide
                1. **Open the Excel file**: Run the Excel template downloaded above.
                2. **Enter pairwise comparisons**:
                    - If the **left** item is more important: enter a **negative** value (e.g., -3)
                    - If the **right** item is more important: enter a **positive** value (e.g., 3)
                    - If they are **equal**: enter `1`
                3. **Required Information**: Column A (ID), **Column B (Type) for group names (e.g., Expert, Public, etc.)**
                """))
                img_file = _("ahp_input_guide.png", "ahp_input_guide_en.png")
                caption_text = _("[참고] 설문 응답을 엑셀에 입력하는 방법", "[Reference] How to enter survey responses into Excel")
                if os.path.exists(img_file):
                    st.image(img_file, caption=caption_text)
    tab1_main_col.__exit__(None, None, None)



import streamlit as st
import json
import uuid
import datetime
import os
from survey_manager import calculate_matrix_cr

def _(ko_text, en_text):
    if st.session_state.get('lang', 'ko') == 'en':
        return en_text
    return ko_text

def render_yeta_survey(survey_meta, is_preview_mode=False, survey_id_param=""):
    survey_title = survey_meta.get('Title', '예타 AHP 온라인 설문조사')
    st.title(survey_title)
    
    survey_desc = survey_meta.get("Description", "")
    survey_email = survey_meta.get("Admin_Email", "temp@ahpmaster.com")
    
    if survey_desc or survey_email:
        email_html = (
            f"<div style='margin-top: 16px; padding-top: 16px; border-top: 1px solid #e2e8f0; font-weight: bold;'>"
            f"📧 " + _("설문 담당자 문의:", "Contact Survey Administrator:") + " "
            f"<a href='mailto:{survey_email}' style='color: #2563eb; text-decoration: none;'>{survey_email}</a>"
            f"</div>"
        ) if survey_email else ""
        
        mobile_hint_html = (
            f"<div style='margin-top: 16px; padding: 12px; background-color: #f1f5f9; border-radius: 6px; font-size: 0.9rem; color: #334155; display: flex; gap: 8px; align-items: center;'>"
            f"<span style='font-size: 1.2rem;'>📱</span> <span>" + _("스마트폰으로 접속하신 경우, <b>기기를 가로로 회전</b>하시면 더욱 편리하게 설문에 응답하실 수 있습니다.", "If you are using a smartphone, you can respond to the survey more conveniently by <b>rotating the screen horizontally</b>.") + "</span>"
            f"</div>"
        )
        box_html = f'<div style="border: 1px solid #cbd5e1; border-radius: 8px; padding: 24px; background-color: #ffffff; color: #1e293b; font-size: 0.95rem; line-height: 1.6; margin-bottom: 24px; white-space: pre-wrap;">{survey_desc}\n{email_html}\n{mobile_hint_html}</div>'
        st.markdown(box_html, unsafe_allow_html=True)

    ahp_model = survey_meta["AHP_Model_JSON"]
    demographics = survey_meta["Demographics"]
    
    yeta_p_type = ahp_model.get("yeta_p_type", "건설사업 (비수도권)")
    main_criteria = ahp_model.get("main", [])
    sub_criteria_map = ahp_model.get("subs", {})
    sub_sub_map = ahp_model.get("sub_subs", {})
    
    # 1. 응답자 기본 정보
    st.subheader("1. " + _("응답자 기본 정보", "Respondent Demographic Information"))
    resp_data = {}
    
    if "survey_resp_uuid" not in st.session_state:
        st.session_state.survey_resp_uuid = str(uuid.uuid4())[:8]
    resp_data["id"] = st.session_state.survey_resp_uuid
    
    sq_idx = 1
    
    # 성명
    if demographics.get("name"):
        name_label = f"SQ{sq_idx}. " + _("성명 *", "Name *")
        sq_idx += 1
        col1, col2 = st.columns([1, 3])
        with col1:
            resp_data["name"] = st.text_input(name_label, key="yeta_survey_resp_name")
            
    # 그룹 분류 문항
    type_questions_data = demographics.get("type_questions")
    resp_data["types"] = []
    
    if type_questions_data and isinstance(type_questions_data, list):
        for i, tq in enumerate(type_questions_data):
            sq_idx = i + 1
            tq_q = tq.get("q", "")
            tq_opts = tq.get("opts", [])
            if tq_opts:
                ans = st.radio(f"SQ{sq_idx}. {tq_q}", tq_opts, index=0, key=f"yeta_survey_resp_type_{i}", horizontal=True)
            else:
                ans = st.text_input(f"SQ{sq_idx}. {tq_q}", key=f"yeta_survey_resp_type_{i}")
            resp_data["types"].append(ans)
    st.subheader("2. " + _("제1계층 평가: 상수합법 (100점 배분)", "Tier 1 Evaluation: Constant Sum (Allocate 100 points)"))
    st.caption(_("아래 1계층 평가항목의 합이 정확히 100이 되도록 중요도를 직접 분배해주십시오.", "Please distribute the importance so that the sum of the following Tier 1 items is exactly 100."))
    
    definitions = survey_meta.get("Definitions", {})
    main_rows_html = ""
    for mc in main_criteria:
        mc_desc = definitions.get(mc, "")
        if mc_desc:
            main_rows_html += f"""
            <div style="display: flex; align-items: flex-start; gap: 8px; padding: 8px 0; border-bottom: 1px dashed #f1f5f9;">
                <span style="color: #334155; font-weight: bold; min-width: 140px; font-size: 0.9rem; border-right: 2px solid #cbd5e1; padding-right: 8px; display: inline-block;">{mc}</span>
                <span style="color: #334155; font-size: 0.88rem; padding-left: 4px; flex: 1;">{mc_desc}</span>
            </div>
            """
    if main_rows_html:
        card_html = f"""
        <div style="background-color: #f8fafc; border: 1px solid #e2e8f0; padding: 16px; border-radius: 8px; margin-bottom: 15px;">
            <h5 style="margin: 0 0 12px 0; color: #1e293b; font-size: 1.0rem; font-weight: bold;">대분류 요인 정의</h5>
            <div style="display: flex; flex-direction: column; gap: 2px; background-color: #ffffff; padding: 12px; border-radius: 6px; border: 1px solid #e2e8f0;">
                {main_rows_html}
            </div>
        </div>
        """
        st.markdown(card_html.replace("\n", " "), unsafe_allow_html=True)

    # KDI 가이드라인에 따른 가중치 제약조건 설정
    if "비수도권" in yeta_p_type and "건설" in yeta_p_type:
        b_eco, b_pol, b_reg = (30, 45, 35), (25, 40, 30), (30, 40, 35)
        # 경제성, 정책성, 지역균형발전
    elif "수도권" in yeta_p_type and "건설" in yeta_p_type:
        b_eco, b_pol, b_reg = (60, 70, 65), (30, 40, 35), None
        # 경제성, 정책성
    elif "R&D" in yeta_p_type or "기술" in main_criteria:
        b_eco, b_pol, b_reg = (40, 50, 45), (20, 30, 25), (30, 40, 30) # 경제, 정책, 기술성
    else:
        b_eco, b_pol, b_reg = (0, 100, 40), (0, 100, 30), (0, 100, 30)
        
    level1_answers = {}
    col1, col2 = st.columns(2)
    
    with col1:
        if "경제성" in main_criteria:
            level1_answers["경제성"] = st.slider(f"경제성 (허용범위: {b_eco[0]}% ~ {b_eco[1]}%)", b_eco[0], b_eco[1], b_eco[2], key="yeta_l1_eco")
        if "정책성" in main_criteria:
            level1_answers["정책성"] = st.slider(f"정책성 (허용범위: {b_pol[0]}% ~ {b_pol[1]}%)", b_pol[0], b_pol[1], b_pol[2], key="yeta_l1_pol")
            
    with col2:
        if "지역균형발전" in main_criteria:
            level1_answers["지역균형발전"] = st.slider(f"지역균형발전 (허용범위: {b_reg[0]}% ~ {b_reg[1]}%)", b_reg[0], b_reg[1], b_reg[2], key="yeta_l1_reg")
        if "기술성" in main_criteria:
            level1_answers["기술성"] = st.slider(f"기술성 (허용범위: {b_reg[0]}% ~ {b_reg[1]}%)", b_reg[0], b_reg[1], b_reg[2], key="yeta_l1_tech")
            
    current_sum = sum(level1_answers.values())
    if current_sum == 100:
        st.success(f"✓ 점수 합계가 100%입니다.")
    else:
        st.error(f"⚠️ 현재 점수 합계가 {current_sum}% 입니다. 합계가 정확히 100%가 되도록 조정해 주세요.")
        
    st.divider()
    
    # 3. 요인 간 상대적 중요도 평가 (쌍대비교)
    st.subheader("3. " + _("요인 간 상대적 중요도 평가 (쌍대비교)", "Relative Importance Evaluation (Pairwise Comparison)"))
    st.caption(_("왼쪽 요인과 오른쪽 요인 중 더 중요하다고 생각하는 쪽으로 중요도를 평가해 주십시오. (1=동등, 숫자가 클수록 해당 방향이 더 중요함)", "Please evaluate which factor is more important. (1=Equal, higher number means more important in that direction)"))
    
    ahp_answers = {}
    
    # Generate pairwise combinations for Sub-criteria (subs & sub_subs)
    for main_c in main_criteria:
        subs = sub_criteria_map.get(main_c, [])
        if len(subs) > 1:
            main_desc = definitions.get(main_c, "")
            sub_rows_html = ""
            for sub_c in subs:
                sub_desc = definitions.get(sub_c, "")
                if sub_desc:
                    sub_rows_html += f"""
                    <div style="display: flex; align-items: flex-start; gap: 8px; padding: 6px 0; border-bottom: 1px dashed #f1f5f9;">
                        <span style="color: #1e40af; font-weight: bold; min-width: 140px; font-size: 0.9rem; border-right: 2px solid #bfdbfe; padding-right: 8px; display: inline-block;">{sub_c}</span>
                        <span style="color: #334155; font-size: 0.88rem; padding-left: 4px; flex: 1;">{sub_desc}</span>
                    </div>
                    """
            if main_desc or sub_rows_html:
                main_desc_html = f'<p style="margin: 0 0 12px 0; color: #475569; font-size: 0.95rem; font-style: italic; font-weight: 500;">{main_desc}</p>' if main_desc else ""
                sub_container_html = f'<div style="display: flex; flex-direction: column; gap: 2px; background-color: #ffffff; padding: 12px; border-radius: 6px; border: 1px solid #e2e8f0;">{sub_rows_html}</div>' if sub_rows_html else ""
                
                card_html = f"""
                <div style="background-color: #eff6ff; border: 1px solid #bfdbfe; border-left: 6px solid #1e40af; padding: 16px; border-radius: 8px; margin-top: 10px; margin-bottom: 15px;">
                    <h4 style="margin: 0 0 8px 0; color: #1e40af; font-size: 1.1rem; font-weight: bold;">{main_c}</h4>
                    {main_desc_html}
                    {sub_container_html}
                </div>
                """
                st.markdown(card_html.replace("\n", " "), unsafe_allow_html=True)

            st.markdown(f"#### [{main_c}] 하위 요인 비교")
            for i in range(len(subs)):
                for j in range(i+1, len(subs)):
                    pair_key = f"{main_c}_{subs[i]}_{subs[j]}"
                    col_l, col_m, col_r = st.columns([3, 6, 3])
                    with col_l:
                        st.markdown(f"<div style='text-align:right; font-weight:bold;'>{subs[i]}</div>", unsafe_allow_html=True)
                    with col_m:
                        ans_val = st.radio(
                            label=pair_key,
                            options=list(range(-9, 0)) + list(range(1, 10)),
                            index=8, # Default to 1 (equal)
                            format_func=lambda x: f"← {abs(x)}" if x < 0 else ("동등 (1)" if x == 1 else f"{x} →"),
                            key=f"yeta_pair_{pair_key}",
                            horizontal=True,
                            label_visibility="collapsed"
                        )
                    with col_r:
                        st.markdown(f"<div style='text-align:left; font-weight:bold;'>{subs[j]}</div>", unsafe_allow_html=True)
                    ahp_answers[pair_key] = ans_val
                    
        for sub_c in subs:
            sub_subs = sub_sub_map.get(sub_c, [])
            if len(sub_subs) > 1:
                sub_desc = definitions.get(sub_c, "")
                t3_rows_html = ""
                for t3 in sub_subs:
                    t3_desc = definitions.get(t3, "")
                    if t3_desc:
                        t3_rows_html += f"""
                        <div style="display: flex; align-items: flex-start; gap: 8px; padding: 6px 0; border-bottom: 1px dashed #f1f5f9;">
                            <span style="color: #166534; font-weight: bold; min-width: 140px; font-size: 0.9rem; border-right: 2px solid #bbf7d0; padding-right: 8px; display: inline-block;">{t3}</span>
                            <span style="color: #334155; font-size: 0.88rem; padding-left: 4px; flex: 1;">{t3_desc}</span>
                        </div>
                        """
                if sub_desc or t3_rows_html:
                    sub_desc_html = f'<p style="margin: 0 0 12px 0; color: #475569; font-size: 0.95rem; font-style: italic; font-weight: 500;">{sub_desc}</p>' if sub_desc else ""
                    t3_container_html = f'<div style="display: flex; flex-direction: column; gap: 2px; background-color: #ffffff; padding: 12px; border-radius: 6px; border: 1px solid #e2e8f0;">{t3_rows_html}</div>' if t3_rows_html else ""
                    
                    card_html = f"""
                    <div style="background-color: #f0fdf4; border: 1px solid #bbf7d0; border-left: 6px solid #166534; padding: 16px; border-radius: 8px; margin-top: 10px; margin-bottom: 15px;">
                        <h4 style="margin: 0 0 8px 0; color: #166534; font-size: 1.1rem; font-weight: bold;">{main_c} ➔ {sub_c}</h4>
                        {sub_desc_html}
                        {t3_container_html}
                    </div>
                    """
                    st.markdown(card_html.replace("\n", " "), unsafe_allow_html=True)

                st.markdown(f"#### [{main_c} ➔ {sub_c}] 하위 요인 비교")
                for i in range(len(sub_subs)):
                    for j in range(i+1, len(sub_subs)):
                        pair_key = f"{sub_c}_{sub_subs[i]}_{sub_subs[j]}"
                        col_l, col_m, col_r = st.columns([3, 6, 3])
                        with col_l:
                            st.markdown(f"<div style='text-align:right; font-weight:bold;'>{sub_subs[i]}</div>", unsafe_allow_html=True)
                        with col_m:
                            ans_val = st.radio(
                                label=pair_key,
                                options=list(range(-9, 0)) + list(range(1, 10)),
                                index=8,
                                format_func=lambda x: f"← {abs(x)}" if x < 0 else ("동등 (1)" if x == 1 else f"{x} →"),
                                key=f"yeta_pair_{pair_key}",
                                horizontal=True,
                                label_visibility="collapsed"
                            )
                        with col_r:
                            st.markdown(f"<div style='text-align:left; font-weight:bold;'>{sub_subs[j]}</div>", unsafe_allow_html=True)
                        ahp_answers[pair_key] = ans_val
                        
    st.divider()
    
    # 4. 대안평가 (시행 vs 미시행 선호도)
    st.subheader("4. " + _("최종 대안평가 (시행선호도 평가)", "Final Alternative Evaluation (Preference for Implementation)"))
    st.caption(_("각 최하위 평가요인에 대해 '사업 시행(Left)'과 '사업 미시행(Right)' 중 어느 쪽이 더 타당한지 비교해주십시오.", "For each bottom-level factor, please compare whether 'Project Implementation (Left)' or 'No Project (Right)' is more appropriate."))
    
    for main_c in main_criteria:
        subs = sub_criteria_map.get(main_c, [])
        if not subs:
            alt_key = f"alt_{main_c}_{main_c}"
            st.markdown(f"##### 요인: **{main_c}**")
            col_l, col_m, col_r = st.columns([3, 6, 3])
            with col_l:
                st.markdown("<div style='text-align:right; font-weight:bold; color:#1e40af;'>사업 시행 (Implementation)</div>", unsafe_allow_html=True)
            with col_m:
                ans_val = st.radio(
                    label=alt_key,
                    options=list(range(-9, 0)) + list(range(1, 10)),
                    index=8,
                    format_func=lambda x: f"← {abs(x)}" if x < 0 else ("동등 (1)" if x == 1 else f"{x} →"),
                    key=f"yeta_alt_{alt_key}",
                    horizontal=True,
                    label_visibility="collapsed"
                )
            with col_r:
                st.markdown("<div style='text-align:left; font-weight:bold; color:#b91c1c;'>사업 미시행 (No Project)</div>", unsafe_allow_html=True)
            ahp_answers[alt_key] = ans_val
            
        for sub_c in subs:
            sub_subs = sub_sub_map.get(sub_c, [])
            if not sub_subs:
                alt_key = f"alt_{main_c}_{sub_c}"
                st.markdown(f"##### 요인: **{main_c} ➔ {sub_c}**")
                col_l, col_m, col_r = st.columns([3, 6, 3])
                with col_l:
                    st.markdown("<div style='text-align:right; font-weight:bold; color:#1e40af;'>사업 시행 (Implementation)</div>", unsafe_allow_html=True)
                with col_m:
                    ans_val = st.radio(
                        label=alt_key,
                        options=list(range(-9, 0)) + list(range(1, 10)),
                        index=8,
                        format_func=lambda x: f"← {abs(x)}" if x < 0 else ("동등 (1)" if x == 1 else f"{x} →"),
                        key=f"yeta_alt_{alt_key}",
                        horizontal=True,
                        label_visibility="collapsed"
                    )
                with col_r:
                    st.markdown("<div style='text-align:left; font-weight:bold; color:#b91c1c;'>사업 미시행 (No Project)</div>", unsafe_allow_html=True)
                ahp_answers[alt_key] = ans_val
            else:
                for t3 in sub_subs:
                    alt_key = f"alt_{sub_c}_{t3}"
                    st.markdown(f"##### 요인: **{main_c} ➔ {sub_c} ➔ {t3}**")
                    col_l, col_m, col_r = st.columns([3, 6, 3])
                    with col_l:
                        st.markdown("<div style='text-align:right; font-weight:bold; color:#1e40af;'>사업 시행 (Implementation)</div>", unsafe_allow_html=True)
                    with col_m:
                        ans_val = st.radio(
                            label=alt_key,
                            options=list(range(-9, 0)) + list(range(1, 10)),
                            index=8,
                            format_func=lambda x: f"← {abs(x)}" if x < 0 else ("동등 (1)" if x == 1 else f"{x} →"),
                            key=f"yeta_alt_{alt_key}",
                            horizontal=True,
                            label_visibility="collapsed"
                        )
                    with col_r:
                        st.markdown("<div style='text-align:left; font-weight:bold; color:#b91c1c;'>사업 미시행 (No Project)</div>", unsafe_allow_html=True)
                    ahp_answers[alt_key] = ans_val
                    
    st.divider()
    
    # 5. 제출하기
    submit_btn = st.button(_("설문지 제출하기", "Submit Survey"), type="primary", use_container_width=True)
    if submit_btn:
        if current_sum != 100:
            st.error(_("1계층 가중치 합계가 100%가 아닙니다. 조정 후 다시 시도해 주세요.", "The sum of Tier 1 weights is not 100%. Please adjust it and try again."))
            st.stop()
            
        if demographics.get("name") and not resp_data.get("name"):
            st.error(_("성명을 입력해 주십시오.", "Please enter your name."))
            st.stop()
            
        with st.spinner(_("응답을 전송 중입니다...", "Submitting response...")):
            if is_preview_mode:
                import time
                time.sleep(1.0)
                st.session_state[f"survey_submitted_{survey_id_param}"] = True
                st.rerun()
            else:
                from survey_manager_v3 import save_yeta_response_to_sheet_v3
                success = save_yeta_response_to_sheet_v3(
                    survey_id_param, resp_data, ahp_answers, ahp_model, level1_answers
                )
                if success:
                    st.session_state[f"survey_submitted_{survey_id_param}"] = True
                    st.rerun()
                else:
                    st.error(_("저장 중 오류가 발생했습니다. 다시 시도해 주세요.", "Error saving response. Please try again."))

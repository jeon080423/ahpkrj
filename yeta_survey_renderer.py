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


def render_yeta_pairwise_matrix(title, factors, pairs, definitions, prefix_key, ahp_answers):

    PASTEL_PALETTES = [
        {"bg": "#eff6ff", "text": "#1e40af", "border": "#bfdbfe"}, # Soft Blue
        {"bg": "#f0fdf4", "text": "#166534", "border": "#bbf7d0"}, # Soft Green
        {"bg": "#fff7ed", "text": "#c2410c", "border": "#fed7aa"}, # Soft Orange
        {"bg": "#faf5ff", "text": "#6b21a8", "border": "#e9d5ff"}, # Soft Purple
        {"bg": "#fdf2f8", "text": "#be185d", "border": "#fbcfe8"}, # Soft Pink
        {"bg": "#f0fdfa", "text": "#0f766e", "border": "#ccfbf1"}, # Soft Teal
        {"bg": "#fffbeb", "text": "#b45309", "border": "#fef3c7"}, # Soft Amber
        {"bg": "#f8fafc", "text": "#334155", "border": "#cbd5e1"}, # Soft Slate/Gray
    ]
    
    factor_colors = {}
    if len(factors) >= 3:
        for i, f_name in enumerate(factors):
            factor_colors[f_name] = PASTEL_PALETTES[i % len(PASTEL_PALETTES)]
    st.markdown(f"#### {title}")
    
    with st.container(key=f"ahp_survey_matrix_{uuid.uuid4().hex[:8]}"):
        left_cols = ["9", "8", "7", "6", "5", "4", "3", "2"]
        right_cols = ["2", "3", "4", "5", "6", "7", "8", "9"]
        scale_width = 70 / 17
        colgroup_html = "".join([
            '<col style="width: 15%;" />',
            "".join([f'<col style="width: {scale_width}%;" />' for _ in left_cols]),
            f'<col style="width: {scale_width}%;" />',
            "".join([f'<col style="width: {scale_width}%;" />' for _ in right_cols]),
            f'<col style="width: 15%;" />'
        ])
        
        header_html = f'''
        <table style="width:100%; border-collapse: collapse; text-align: center; font-size: 12px; font-family: sans-serif; border: 1px solid #cbd5e1; table-layout: fixed; margin: 0px; padding: 0px;">
            <colgroup>
                {colgroup_html}
            </colgroup>
            <tr style="background-color: #1e293b; color: #ffffff; font-weight: bold; border-bottom: 1px solid #cbd5e1;">
                <th style="border: 1px solid #334155; padding: 6px; font-size: 12px;" rowspan="2">비교 요인</th>
                <th style="border: 1px solid #334155; padding: 4px; color: #93c5fd; font-size: 12px;" colspan="{len(left_cols)}">← 좌측 요인 중요도</th>
                <th style="border: 1px solid #334155; padding: 4px; background-color: #3b82f6; color: #ffffff; font-size: 12px;" rowspan="2">동등<br>(1)</th>
                <th style="border: 1px solid #334155; padding: 4px; color: #93c5fd; font-size: 12px;" colspan="{len(right_cols)}">우측 요인 중요도 →</th>
                <th style="border: 1px solid #334155; padding: 6px; font-size: 12px;" rowspan="2">비교 요인</th>
            </tr>
            <tr style="background-color: #334155; color: #cbd5e1; font-weight: bold; border-bottom: 1px solid #cbd5e1;">
                {"".join([f"<td style='border: 1px solid #475569; padding: 4px 0; font-size: 12px;'>{val}</td>" for val in left_cols])}
                {"".join([f"<td style='border: 1px solid #475569; padding: 4px 0; font-size: 12px;'>{val}</td>" for val in right_cols])}
            </tr>
        </table>
        '''
        st.markdown(header_html, unsafe_allow_html=True)

        options = list(range(-9, 0)) + list(range(1, 10))
        clean_options = [x for x in options if x != -1]
        
        for left_f, right_f in pairs:
            pair_key = f"{prefix_key}_{left_f}_{right_f}"
            row_cols = st.columns([15, 70, 15])
            
            with row_cols[0]:
                left_desc = definitions.get(left_f, "")
                left_desc_esc = left_desc.replace('"', '&quot;')
                left_style = factor_colors.get(left_f, {"bg": "#f8fafc", "text": "#334155", "border": "#cbd5e1"})
                st.markdown(f'''
                <div title="{left_desc_esc}" style='text-align:center; font-weight:600; border: 1px solid {left_style["border"]}; 
                            background-color: {left_style["bg"]}; color: {left_style["text"]}; 
                            border-radius: 4px; min-height: 28px; height: auto; padding: 4px 8px; display: flex; align-items: center; 
                            justify-content: center; font-size: 12px; margin: 0px; box-shadow: 0 1px 2px rgba(0,0,0,0.02); cursor: help;'>
                        {left_f}
                </div>
                ''', unsafe_allow_html=True)
                
            with row_cols[1]:
                # 일관성 응답 가이드 산출
                valid_options = set()
                min_cr_opt = 1
                min_cr_val = float('inf')
                other_missing = False
                group_answers = {}
                
                for p_left, p_right in pairs:
                    k = f"{prefix_key}_{p_left}_{p_right}"
                    val = st.session_state.get(f"yeta_pair_{k}", None)
                    group_answers[f"{p_left}_{p_right}"] = val
                    if k != pair_key and val is None:
                        other_missing = True
                        
                if len(factors) > 2 and not other_missing:
                    for opt in clean_options:
                        test_answers = group_answers.copy()
                        test_answers[f"{left_f}_{right_f}"] = opt
                        try:
                            test_cr = calculate_matrix_cr(factors, test_answers)
                            if test_cr <= 0.15:
                                valid_options.add(opt)
                            if test_cr < min_cr_val:
                                min_cr_val = test_cr
                                min_cr_opt = opt
                        except: pass
                
                bar_html = ""
                if len(factors) > 2 and not other_missing:
                    valid_sorted = [x for x in clean_options if x in valid_options]
                    if valid_sorted:
                        start_idx = clean_options.index(valid_sorted[0])
                        end_idx = clean_options.index(valid_sorted[-1])
                    else:
                        start_idx = end_idx = clean_options.index(min_cr_opt)
                    
                    bar_html = '<div style="display: flex; width: 100%; height: 32px; margin-top: -32px; z-index: 10; position: relative; pointer-events: none;">'
                    for j, opt in enumerate(clean_options):
                        is_valid = start_idx <= j <= end_idx
                        bg_color = "rgba(59, 130, 246, 0.25)" if is_valid else "transparent"
                        radius = ""
                        if j == start_idx: radius += "border-top-left-radius: 6px; border-bottom-left-radius: 6px; "
                        if j == end_idx: radius += "border-top-right-radius: 6px; border-bottom-right-radius: 6px; "
                        bar_html += f'<div style="flex: 1 1 0%; background-color: {bg_color}; {radius}"></div>'
                    bar_html += '</div>'
                
                def format_option(opt):
                    return str(abs(opt)) + "\u200B" if opt < 0 else str(opt)

                current_val = st.session_state.get(f"yeta_pair_{pair_key}", None)
                current_idx = clean_options.index(current_val) if current_val in clean_options else None

                ans_val = st.radio(
                    label=pair_key,
                    options=clean_options,
                    index=current_idx,
                    format_func=format_option,
                    key=f"yeta_pair_{pair_key}",
                    horizontal=True,
                    label_visibility="collapsed"
                )
                if len(factors) > 2 and not other_missing:
                    st.markdown(bar_html, unsafe_allow_html=True)
                    
            with row_cols[2]:
                right_desc = definitions.get(right_f, "")
                right_desc_esc = right_desc.replace('"', '&quot;')
                right_style = factor_colors.get(right_f, {"bg": "#f8fafc", "text": "#334155", "border": "#cbd5e1"})
                st.markdown(f'''
                <div title="{right_desc_esc}" style='text-align:center; font-weight:600; border: 1px solid {right_style["border"]}; 
                            background-color: {right_style["bg"]}; color: {right_style["text"]}; 
                            border-radius: 4px; min-height: 28px; height: auto; padding: 4px 8px; display: flex; align-items: center; 
                            justify-content: center; font-size: 12px; margin: 0px; box-shadow: 0 1px 2px rgba(0,0,0,0.02); cursor: help;'>
                        {right_f}
                </div>
                ''', unsafe_allow_html=True)
                
            ahp_answers[pair_key] = ans_val

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


    # --- 쌍대비교 라디오 버튼 CSS 주입 ---
    st.markdown('''
    <style>
/* 0. 메인 수직 컨테이너(줄간격) 초밀착 및 마진 축소 */
div[class*="st-key-ahp_survey_matrix"] {
    gap: 4px !important;
    row-gap: 4px !important;
}

/* 1. 수직 정렬 & 레이아웃 배분 */
div[class*="st-key-ahp_survey_matrix"] div[data-testid="stHorizontalBlock"] {
    gap: 0px !important;
    align-items: center !important;
    width: 100% !important;
    margin-top: 0px !important;
    margin-bottom: 0px !important;
    padding-top: 4px !important;
    padding-bottom: 4px !important;
    border-bottom: 1px solid #e2e8f0 !important;
}

div[class*="st-key-ahp_survey_matrix"] div[data-testid="column"] {
    padding: 0px !important;
}

/* 2. 라디오 그룹 전체 100% 분배 강제 및 줄바꿈 원천 차단 */
div[class*="st-key-ahp_survey_matrix"] div[data-testid="stElementContainer"],
div[class*="st-key-ahp_survey_matrix"] div[data-testid="stRadio"],
div[class*="st-key-ahp_survey_matrix"] .stRadio {
    width: 100% !important;
    margin: 0px !important;
    padding: 0px !important;
}

div[class*="st-key-ahp_survey_matrix"] div[data-testid="stRadio"] > div,
div[class*="st-key-ahp_survey_matrix"] div[role="radiogroup"] {
    display: flex !important;
    flex-direction: row !important;
    flex-wrap: nowrap !important;
    justify-content: space-between !important;
    align-items: center !important;
    width: 100% !important;
    gap: 0px !important;
    padding: 0px !important; 
    margin: 0px !important;
}

/* 2.5. AHP 컨테이너 내부의 수직 요소 간격 초밀착 */
div[class*="st-key-ahp_survey_matrix"] div[data-testid="stVerticalBlock"] {
    gap: 0px !important;
}

/* 3. 각 척도 라디오 버튼 1:1 완벽 정렬 */
div[class*="st-key-ahp_survey_matrix"] div[role="radiogroup"] > div,
div[class*="st-key-ahp_survey_matrix"] div[role="radiogroup"] > label,
div[class*="st-key-ahp_survey_matrix"] div[data-testid="stRadioHorizontalOption"],
div[class*="st-key-ahp_survey_matrix"] div[role="radiogroup"] label {
    flex: 1 1 0% !important;
    display: flex !important;
    flex-direction: column !important;
    align-items: center !important;
    justify-content: center !important;
    height: 32px !important; 
    margin: 0px !important;
    padding: 0px !important;
    min-width: 0px !important;
    width: 100% !important;
    border-radius: 2px !important;
    transition: background-color 0.1s ease-in-out !important;
    background-color: transparent !important;
}

/* 3.5. 라디오 그룹 최소 높이 해제 */
div[class*="st-key-ahp_survey_matrix"] div[role="radiogroup"] {
    min-height: 32px !important;
}

/* 감싸는 div가 있을 경우 그 내부의 실제 label도 100% 채우도록 지시 */
div[class*="st-key-ahp_survey_matrix"] div[role="radiogroup"] > div label,
div[class*="st-key-ahp_survey_matrix"] div[data-testid="stRadioHorizontalOption"] label {
    width: 100% !important;
    height: 100% !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    margin: 0px !important;
    padding: 0px !important;
}

/* 4. 기존 텍스트 찌꺼기 완벽 제거 */
div[class*="st-key-ahp_survey_matrix"] label[data-testid="stWidgetLabel"],
div[class*="st-key-ahp_survey_matrix"] label p {
    display: none !important;
    height: 0px !important;
    width: 0px !important;
    margin: 0px !important;
    padding: 0px !important;
    opacity: 0 !important;
    overflow: hidden !important;
    position: absolute !important;
}

/* stMarkdownContainer의 negative margin 제거하여 컬럼간 수직 평행 맞춤 */
div[class*="st-key-ahp_survey_matrix"] div[data-testid="stMarkdownContainer"] {
    margin-bottom: 0px !important;
    padding-bottom: 0px !important;
}

/* 라디오 항목 내부의 markdown 컨테이너(텍스트용) 완전히 감추기 */
div[class*="st-key-ahp_survey_matrix"] div[role="radiogroup"] div[data-testid="stMarkdownContainer"] {
    display: none !important;
    height: 0px !important;
    width: 0px !important;
    margin: 0px !important;
    padding: 0px !important;
    opacity: 0 !important;
    overflow: hidden !important;
    position: absolute !important;
}

/* 동그라미 컨테이너 중앙 정렬 및 여백 마진 제거 */
div[class*="st-key-ahp_survey_matrix"] label span {
    margin: 0px !important;
    padding: 0px !important;
}

/* 5. Hover 및 Zebra 효과 */
div[class*="st-key-ahp_survey_matrix"] label:hover {
    background-color: #f1f5f9 !important;
    cursor: pointer !important;
}

/* 6. 모바일 가로 스크롤 허용 및 붕괴 방지 */
@media (max-width: 768px) {
    .stApp > header + div, 
    .block-container,
    div[data-testid="stDialog"] {
        overflow-x: auto !important;
        -webkit-overflow-scrolling: touch;
    }
    div[class*="st-key-ahp_survey_matrix"] div[data-testid="stHorizontalBlock"] {
        flex-wrap: nowrap !important;
        min-width: 100% !important;
    }
    div[class*="st-key-ahp_survey_matrix"] div[data-testid="column"] {
        flex: 0 0 auto !important;
    }
    div[class*="st-key-ahp_survey_matrix"] div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(1),
    div[class*="st-key-ahp_survey_matrix"] div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(3) {
        width: 25% !important; 
        white-space: normal !important;
        word-break: break-all !important;
        font-size: 0.9em !important;
    }
    div[class*="st-key-ahp_survey_matrix"] div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(2) {
        width: 50% !important;
    }

    </style>
    ''', unsafe_allow_html=True)

    # 모바일 가로 모드 강제 전환 오버레이
    import streamlit.components.v1 as components
    
    title_text = _("가로 모드 최적화", "Landscape Mode Optimized")
    desc_text = _("이 설문(AHP 쌍대비교)은 가로 화면에서<br>가장 편하게 응답하실 수 있습니다.", 
                  "This survey (AHP Pairwise Comparison) is best experienced<br>in landscape mode.")
    btn_text = _("🔄 화면을 가로로 돌리고 설문 계속하기", "🔄 Rotate to Landscape & Continue")
    note_text = _("""※ <b>아이폰(iOS) 사용자 안내</b><br>
                    위 버튼이 작동하지 않을 수 있습니다.<br>
                    기기의 <b>'자동 회전'을 켜고</b> 스마트폰을 눕혀주시면 안내창이 사라집니다.""",
                  """※ <b>iPhone (iOS) User Guide</b><br>
                    The above button may not work.<br>
                    Please enable <b>'Auto-Rotate'</b> and turn your phone sideways.""")

    mobile_landscape_overlay_html = f"""
    <script>
    try {{
        const parent = window.parent.document;
        if (!parent.getElementById('mobile-landscape-overlay')) {{
            const overlay = parent.createElement('div');
            overlay.id = 'mobile-landscape-overlay';
            
            const style = parent.createElement('style');
            style.innerHTML = `
                #mobile-landscape-overlay {{
                    display: none;
                    position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
                    background-color: rgba(255,255,255,0.98);
                    z-index: 999999; flex-direction: column;
                    justify-content: center; align-items: center; text-align: center;
                    padding: 20px; box-sizing: border-box;
                }}
                @media (orientation: portrait) and (max-width: 768px) {{
                    #mobile-landscape-overlay {{ display: flex; }}
                }}
                .landscape-btn {{
                    background-color: #ff4b4b; color: white; border: none; border-radius: 8px;
                    padding: 15px 25px; font-size: 18px; font-weight: bold; margin-top: 20px;
                    cursor: pointer; box-shadow: 0 4px 6px rgba(0,0,0,0.1); width: 100%; max-width: 320px;
                }}
                .landscape-note {{
                    font-size: 13.5px; color: #555; margin-top: 20px; line-height: 1.5; word-break: keep-all; background: #f8f9fa; padding: 15px; border-radius: 8px; max-width: 320px; text-align: left;
                }}
            `;
            parent.head.appendChild(style);

            overlay.innerHTML = `
                <div style="font-size: 50px; margin-bottom: 15px;">📱🔄</div>
                <h2 style="color: #333; margin-bottom: 10px; font-size: 22px;">{title_text}</h2>
                <p style="color: #444; font-size: 15px; margin-bottom: 5px;">{desc_text}</p>
                <button class="landscape-btn" id="btn-force-landscape">{btn_text}</button>
                <div class="landscape-note">
                    {note_text}
                </div>
            `;
            parent.body.appendChild(overlay);

            parent.getElementById('btn-force-landscape').addEventListener('click', function() {{
                const docElm = parent.documentElement;
                if (docElm.requestFullscreen) {{
                    docElm.requestFullscreen().then(() => {{
                        if (window.screen.orientation && window.screen.orientation.lock) {{
                            window.screen.orientation.lock('landscape').catch(e => console.log(e));
                        }} else if (parent.screen.orientation && parent.screen.orientation.lock) {{
                            parent.screen.orientation.lock('landscape').catch(e => console.log(e));
                        }}
                    }}).catch(e => console.log(e));
                }} else if (docElm.webkitRequestFullscreen) {{
                    docElm.webkitRequestFullscreen();
                    if (parent.screen.orientation && parent.screen.orientation.lock) {{
                        parent.screen.orientation.lock('landscape').catch(e => console.log(e));
                    }}
                }}
            }});
        }}
    }} catch(e) {{
        console.log("Error injecting overlay:", e);
    }}
    </script>
    """
    components.html(mobile_landscape_overlay_html, height=0)

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

            pairs = []
            for i in range(len(subs)):
                for j in range(i+1, len(subs)):
                    pairs.append((subs[i], subs[j]))
            if pairs:
                render_yeta_pairwise_matrix(f"[{main_c}] 하위 요인 비교", subs, pairs, definitions, main_c, ahp_answers)
                    
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

                pairs = []
                for i in range(len(sub_subs)):
                    for j in range(i+1, len(sub_subs)):
                        pairs.append((sub_subs[i], sub_subs[j]))
                if pairs:
                    render_yeta_pairwise_matrix(f"[{main_c} ➔ {sub_c}] 하위 요인 비교", sub_subs, pairs, definitions, sub_c, ahp_answers)
                        
    st.divider()
    
    # 4. 대안평가 (시행 vs 미시행 선호도)
    st.subheader("4. " + _("최종 대안평가 (시행선호도 평가)", "Final Alternative Evaluation (Preference for Implementation)"))
    st.caption(_("각 최하위 평가요인에 대해 '사업 시행(Left)'과 '사업 미시행(Right)' 중 어느 쪽이 더 타당한지 비교해주십시오.", "For each bottom-level factor, please compare whether 'Project Implementation (Left)' or 'No Project (Right)' is more appropriate."))
    
    for main_c in main_criteria:
        subs = sub_criteria_map.get(main_c, [])
        if not subs:
            alt_key = f"alt_{main_c}_{main_c}"
            st.markdown(f"##### 요인: **{main_c}**")
            with st.container(key=f"ahp_survey_matrix_{uuid.uuid4().hex[:8]}"):
                left_cols = ["9", "8", "7", "6", "5", "4", "3", "2"]
                right_cols = ["2", "3", "4", "5", "6", "7", "8", "9"]
                scale_width = 70 / 17
                colgroup_html = "".join([
                    '<col style="width: 15%;" />',
                    "".join([f'<col style="width: {scale_width}%;" />' for _ in left_cols]),
                    f'<col style="width: {scale_width}%;" />',
                    "".join([f'<col style="width: {scale_width}%;" />' for _ in right_cols]),
                    f'<col style="width: 15%;" />'
                ])
                header_html = f'''
                <table style="width:100%; border-collapse: collapse; text-align: center; font-size: 12px; font-family: sans-serif; border: 1px solid #cbd5e1; table-layout: fixed; margin: 0px 0px 10px 0px; padding: 0px;">
                    <colgroup>{colgroup_html}</colgroup>
                    <thead>
                        <tr style="background-color: #f1f5f9; border-bottom: 1px solid #cbd5e1;">
                            <th style="border-right: 1px solid #cbd5e1; padding: 4px; font-weight: 600; color: #1e293b; vertical-align: middle;">시행 선호</th>
                            {"".join([f'<th style="padding: 4px; font-weight: normal; color: #64748b; border-right: 1px solid #e2e8f0;">{c}</th>' for c in left_cols])}
                            <th style="padding: 4px; font-weight: 600; color: #3b82f6; border-right: 1px solid #e2e8f0; border-left: 1px solid #e2e8f0; background-color: #e0f2fe;">1</th>
                            {"".join([f'<th style="padding: 4px; font-weight: normal; color: #64748b; border-right: 1px solid #e2e8f0;">{c}</th>' for c in right_cols])}
                            <th style="border-left: 1px solid #cbd5e1; padding: 4px; font-weight: 600; color: #1e293b; vertical-align: middle;">미시행 선호</th>
                        </tr>
                    </thead>
                </table>
                '''
                st.markdown(header_html, unsafe_allow_html=True)
                
                row_cols = st.columns([1.5, 7, 1.5])
                with row_cols[0]:
                    st.markdown(f'''
                    <div style='text-align:center; font-weight:600; border: 1px solid #cbd5e1; background-color: #f8fafc; color: #1e40af; border-radius: 4px; padding: 4px 8px; min-height: 28px; display: flex; align-items: center; justify-content: center; font-size: 12px;'>사업 시행</div>
                    ''', unsafe_allow_html=True)
                with row_cols[1]:
                    ans_val = st.radio(
                        label=alt_key,
                        options=list(range(-9, 0)) + list(range(1, 10)),
                        index=None,
                        format_func=lambda x: str(abs(x)) + "​" if x < 0 else str(x),
                        key=f"yeta_alt_{alt_key}",
                        horizontal=True,
                        label_visibility="collapsed"
                    )
                with row_cols[2]:
                    st.markdown(f'''
                    <div style='text-align:center; font-weight:600; border: 1px solid #cbd5e1; background-color: #f8fafc; color: #b91c1c; border-radius: 4px; padding: 4px 8px; min-height: 28px; display: flex; align-items: center; justify-content: center; font-size: 12px;'>사업 미시행</div>
                    ''', unsafe_allow_html=True)
                ahp_answers[alt_key] = ans_val
            
        for sub_c in subs:
            sub_subs = sub_sub_map.get(sub_c, [])
            if not sub_subs:
                alt_key = f"alt_{main_c}_{sub_c}"
                st.markdown(f"##### 요인: **{main_c} ➔ {sub_c}**")
                with st.container(key=f"ahp_survey_matrix_{uuid.uuid4().hex[:8]}"):
                    left_cols = ["9", "8", "7", "6", "5", "4", "3", "2"]
                    right_cols = ["2", "3", "4", "5", "6", "7", "8", "9"]
                    scale_width = 70 / 17
                    colgroup_html = "".join([
                        '<col style="width: 15%;" />',
                        "".join([f'<col style="width: {scale_width}%;" />' for _ in left_cols]),
                        f'<col style="width: {scale_width}%;" />',
                        "".join([f'<col style="width: {scale_width}%;" />' for _ in right_cols]),
                        f'<col style="width: 15%;" />'
                    ])
                    header_html = f'''
                    <table style="width:100%; border-collapse: collapse; text-align: center; font-size: 12px; font-family: sans-serif; border: 1px solid #cbd5e1; table-layout: fixed; margin: 0px; padding: 0px;">
                        <colgroup>
                            {colgroup_html}
                        </colgroup>
                        <tr style="background-color: #1e293b; color: #ffffff; font-weight: bold; border-bottom: 1px solid #cbd5e1;">
                            <th style="border: 1px solid #334155; padding: 6px; font-size: 12px;" rowspan="2">대안</th>
                            <th style="border: 1px solid #334155; padding: 4px; color: #93c5fd; font-size: 12px;" colspan="{len(left_cols)}">← 사업 시행 선호</th>
                            <th style="border: 1px solid #334155; padding: 4px; background-color: #3b82f6; color: #ffffff; font-size: 12px;" rowspan="2">동등<br>(1)</th>
                            <th style="border: 1px solid #334155; padding: 4px; color: #93c5fd; font-size: 12px;" colspan="{len(right_cols)}">사업 미시행 선호 →</th>
                            <th style="border: 1px solid #334155; padding: 6px; font-size: 12px;" rowspan="2">대안</th>
                        </tr>
                        <tr style="background-color: #334155; color: #cbd5e1; font-weight: bold; border-bottom: 1px solid #cbd5e1;">
                            {"".join([f"<td style='border: 1px solid #475569; padding: 4px 0; font-size: 12px;'>{val}</td>" for val in left_cols])}
                            {"".join([f"<td style='border: 1px solid #475569; padding: 4px 0; font-size: 12px;'>{val}</td>" for val in right_cols])}
                        </tr>
                    </table>
                    '''
                    st.markdown(header_html, unsafe_allow_html=True)
                    
                    row_cols = st.columns([1.5, 7, 1.5])
                    with row_cols[0]:
                        st.markdown(f'''
                        <div style='text-align:center; font-weight:600; border: 1px solid #cbd5e1; background-color: #f8fafc; color: #1e40af; border-radius: 4px; padding: 4px 8px; min-height: 28px; display: flex; align-items: center; justify-content: center; font-size: 12px;'>사업 시행</div>
                        ''', unsafe_allow_html=True)
                    with row_cols[1]:
                        ans_val = st.radio(
                            label=alt_key,
                            options=list(range(-9, 0)) + list(range(1, 10)),
                            index=None,
                            format_func=lambda x: str(abs(x)) + "​" if x < 0 else str(x),
                            key=f"yeta_alt_{alt_key}",
                            horizontal=True,
                            label_visibility="collapsed"
                        )
                    with row_cols[2]:
                        st.markdown(f'''
                        <div style='text-align:center; font-weight:600; border: 1px solid #cbd5e1; background-color: #f8fafc; color: #b91c1c; border-radius: 4px; padding: 4px 8px; min-height: 28px; display: flex; align-items: center; justify-content: center; font-size: 12px;'>사업 미시행</div>
                        ''', unsafe_allow_html=True)
                    ahp_answers[alt_key] = ans_val
            else:
                for t3 in sub_subs:
                    alt_key = f"alt_{sub_c}_{t3}"
                    st.markdown(f"##### 요인: **{main_c} ➔ {sub_c} ➔ {t3}**")
                    with st.container(key=f"ahp_survey_matrix_{uuid.uuid4().hex[:8]}"):
                        left_cols = ["9", "8", "7", "6", "5", "4", "3", "2"]
                        right_cols = ["2", "3", "4", "5", "6", "7", "8", "9"]
                        scale_width = 70 / 17
                        colgroup_html = "".join([
                            '<col style="width: 15%;" />',
                            "".join([f'<col style="width: {scale_width}%;" />' for _ in left_cols]),
                            f'<col style="width: {scale_width}%;" />',
                            "".join([f'<col style="width: {scale_width}%;" />' for _ in right_cols]),
                            f'<col style="width: 15%;" />'
                        ])
                        header_html = f'''
                        <table style="width:100%; border-collapse: collapse; text-align: center; font-size: 12px; font-family: sans-serif; border: 1px solid #cbd5e1; table-layout: fixed; margin: 0px 0px 10px 0px; padding: 0px;">
                            <colgroup>{colgroup_html}</colgroup>
                            <thead>
                                <tr style="background-color: #f1f5f9; border-bottom: 1px solid #cbd5e1;">
                                    <th style="border-right: 1px solid #cbd5e1; padding: 4px; font-weight: 600; color: #1e293b; vertical-align: middle;">시행 선호</th>
                                    {"".join([f'<th style="padding: 4px; font-weight: normal; color: #64748b; border-right: 1px solid #e2e8f0;">{c}</th>' for c in left_cols])}
                                    <th style="padding: 4px; font-weight: 600; color: #3b82f6; border-right: 1px solid #e2e8f0; border-left: 1px solid #e2e8f0; background-color: #e0f2fe;">1</th>
                                    {"".join([f'<th style="padding: 4px; font-weight: normal; color: #64748b; border-right: 1px solid #e2e8f0;">{c}</th>' for c in right_cols])}
                                    <th style="border-left: 1px solid #cbd5e1; padding: 4px; font-weight: 600; color: #1e293b; vertical-align: middle;">미시행 선호</th>
                                </tr>
                            </thead>
                        </table>
                        '''
                        st.markdown(header_html, unsafe_allow_html=True)
                        
                        row_cols = st.columns([1.5, 7, 1.5])
                        with row_cols[0]:
                            st.markdown(f'''
                            <div style='text-align:center; font-weight:600; border: 1px solid #cbd5e1; background-color: #f8fafc; color: #1e40af; border-radius: 4px; padding: 4px 8px; min-height: 28px; display: flex; align-items: center; justify-content: center; font-size: 12px;'>사업 시행</div>
                            ''', unsafe_allow_html=True)
                        with row_cols[1]:
                            ans_val = st.radio(
                                label=alt_key,
                                options=list(range(-9, 0)) + list(range(1, 10)),
                                index=None,
                                format_func=lambda x: str(abs(x)) + "​" if x < 0 else str(x),
                                key=f"yeta_alt_{alt_key}",
                                horizontal=True,
                                label_visibility="collapsed"
                            )
                        with row_cols[2]:
                            st.markdown(f'''
                            <div style='text-align:center; font-weight:600; border: 1px solid #cbd5e1; background-color: #f8fafc; color: #b91c1c; border-radius: 4px; padding: 4px 8px; min-height: 28px; display: flex; align-items: center; justify-content: center; font-size: 12px;'>사업 미시행</div>
                            ''', unsafe_allow_html=True)
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

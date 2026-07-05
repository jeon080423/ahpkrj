import streamlit as st
import importlib
import sys

# 1. Page Config (Must be called as the very first Streamlit command)
try:
    from PIL import Image
    import os
    if os.path.exists("favicon.png"):
        favicon = Image.open("favicon.png")
    else:
        favicon = "📊"
    st.set_page_config(
        page_title="AHP Master Portal",
        layout="wide",
        page_icon=favicon
    )
except Exception:
    pass

# 2. Re-resolve language settings
if 'lang' not in st.session_state:
    try:
        _init_lang = st.query_params.get("lang", "ko")
        if isinstance(_init_lang, list): _init_lang = _init_lang[0]
        st.session_state.lang = _init_lang.lower()
    except:
        st.session_state.lang = 'ko'

def _(ko_text, en_text):
    if st.session_state.get('lang', 'ko') == 'en':
        return en_text
    return ko_text

# 3. Handle query parameters and session state for routing
if "mode" in st.query_params:
    st.session_state.mode = st.query_params.get("mode")

# If the mode is set in session state but not in query params, update query params
if st.session_state.get("mode") and "mode" not in st.query_params:
    st.query_params["mode"] = st.session_state.mode

mode = st.session_state.get("mode")

# 4. Route to standard_app or yeta_app
if mode == "standard":
    import standard_app
    importlib.reload(standard_app)
elif mode == "yeta":
    import yeta_app
    importlib.reload(yeta_app)
else:
    # 5. Render Gateway Landing Page
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&family=Noto+Sans+KR:wght@300;400;700&display=swap');
    
    .gateway-container {
        font-family: 'Outfit', 'Noto Sans KR', sans-serif;
        max-width: 1200px;
        margin: 0 auto;
        padding: 40px 20px;
        text-align: center;
    }
    .gateway-title {
        font-size: 2.8rem;
        font-weight: 800;
        background: linear-gradient(135deg, #1A365D, #2B6CB0, #319795);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 12px;
        line-height: 1.2;
    }
    .gateway-subtitle {
        font-size: 1.2rem;
        color: #4A5568;
        margin-bottom: 50px;
    }
    .card-container {
        display: flex;
        justify-content: center;
        gap: 40px;
        flex-wrap: wrap;
        margin-bottom: 40px;
    }
    .portal-card {
        background: white;
        border-radius: 20px;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.05);
        border: 1px solid #E2E8F0;
        width: 100%;
        padding: 35px 30px;
        text-align: left;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        margin-bottom: 20px;
    }
    .card-title {
        font-size: 1.6rem;
        font-weight: 700;
        color: #1A202C;
        margin-bottom: 15px;
    }
    .card-desc {
        font-size: 1rem;
        color: #718096;
        line-height: 1.6;
        margin-bottom: 25px;
        min-height: 80px;
    }
    .card-features {
        margin-bottom: 30px;
        list-style-type: none;
        padding-left: 0;
    }
    .card-features li {
        margin-bottom: 10px;
        font-size: 0.95rem;
        color: #4A5568;
        display: flex;
        align-items: center;
    }
    .card-features li::before {
        content: "✓";
        color: #319795;
        font-weight: bold;
        margin-right: 10px;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown(f"""
    <div class="gateway-container">
        <h1 class="gateway-title">{_("AHP 의사결정 분석 솔루션 포털", "AHP Decision Analysis Solution Portal")}</h1>
        <p class="gateway-subtitle">{_("귀하의 분석 목적에 최적화된 전문 서비스를 선택해 주세요.", "Please select the specialized service optimized for your analysis purpose.")}</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2, gap="large")
    
    with col1:
        st.markdown(f"""
        <div class="portal-card" style="border-top: 5px solid #2B6CB0;">
            <div class="card-title">{_("일반 & 학술 AHP 마스터", "Standard & Academic AHP Master")}</div>
            <p class="card-desc">{_("대학원 학위논문 통계, 기업 및 학술 연구용 일반 AHP 및 퍼지 AHP(Fuzzy AHP) 분석에 최적화되어 있습니다.", "Optimized for graduate thesis statistics, corporate, and academic research general AHP and Fuzzy AHP analysis.")}</p>
            <ul class="card-features">
                <li>{_("2계층 & 3계층 모델 자유 구성 및 분석", "Free configuration & analysis of 2-tier & 3-tier models")}</li>
                <li>{_("퍼지(Fuzzy) AHP 의사결정 모형 완벽 지원", "Full Fuzzy AHP decision model support")}</li>
                <li>{_("집단 가중치 기하평균 및 ANOVA 사후 검정", "Group weights geometric mean & ANOVA post-hoc test")}</li>
                <li>{_("온라인 쌍대비교 설문지 자동 제작 및 배포", "Automatic creation & distribution of online surveys")}</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        if st.button(_("일반/학술 AHP 분석 시작하기 →", "Start Standard/Academic AHP →"), use_container_width=True, type="primary", key="btn_standard_mode"):
            st.session_state.mode = "standard"
            st.query_params["mode"] = "standard"
            st.rerun()
            
    with col2:
        st.markdown(f"""
        <div class="portal-card" style="border-top: 5px solid #1A365D;">
            <div class="card-title">{_("국가 예비타당성조사 종합평가(AHP)", "Preliminary Feasibility Study AHP")}</div>
            <p class="card-desc">{_("기획재정부 및 KDI 표준 지침에 완벽하게 부합하는 재정투자사업, SOC, R&D 예비타당성조사 전용 AHP 분석 모듈입니다.", "AHP analysis module dedicated to preliminary feasibility studies for fiscal investment projects, SOC, and R&D, in full compliance with MoEF and KDI standard guidelines.")}</p>
            <ul class="card-features">
                <li>{_("B/C 비율(경제성) 로그 표준점수 자동 전환", "B/C ratio log standard score auto conversion")}</li>
                <li>{_("지역낙후도지수 표준점수 전환 및 1계층 범위 검증", "Regional backwardness standard score & Level 1 limits check")}</li>
                <li>{_("집단 의사결정 시 최대/최소 평가자(2인) 제외 배제 처리", "Exclusion of max/min outlier evaluators (2 persons)")}</li>
                <li>{_("예타 전문가용 설문 실시간 일관성(CR 0.15) 가이드", "Real-time consistency (CR 0.15) guide for experts")}</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        if st.button(_("예비타당성조사 AHP 분석 시작하기 →", "Start Preliminary Feasibility AHP →"), use_container_width=True, type="primary", key="btn_yeta_mode"):
            st.session_state.mode = "yeta"
            st.query_params["mode"] = "yeta"
            st.rerun()

    # Footer and Language switcher
    st.markdown("<hr style='margin-top: 40px;'>", unsafe_allow_html=True)
    f_col1, f_col2 = st.columns([8, 2])
    with f_col1:
        st.caption("© 2026 AHP Master. All rights reserved.")
    with f_col2:
        lang_label = "Switch to English" if st.session_state.lang == "ko" else "한국어로 전환"
        if st.button(lang_label, key="gateway_lang_btn", use_container_width=True):
            st.session_state.lang = "en" if st.session_state.lang == "ko" else "ko"
            st.query_params["lang"] = st.session_state.lang
            st.rerun()

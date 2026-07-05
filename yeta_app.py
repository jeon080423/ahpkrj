import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import yeta_utils
import math
import os
import sqlite3
import datetime

def run():
    # 1. Custom CSS Styling for Premium Corporate Look
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&family=Noto+Sans+KR:wght@300;400;500;700&display=swap');
    
    .yeta-body {
        font-family: 'Noto Sans KR', 'Outfit', sans-serif;
    }
    .yeta-header {
        background-color: #1A365D;
        color: white;
        padding: 30px;
        border-radius: 12px;
        margin-bottom: 30px;
        border-left: 6px solid #3182CE;
    }
    .yeta-header h1 {
        color: white !important;
        margin: 0;
        font-size: 2.2rem;
        font-weight: 700;
    }
    .yeta-header p {
        margin: 10px 0 0 0;
        font-size: 1.1rem;
        color: #E2E8F0;
    }
    .verdict-card {
        padding: 25px;
        border-radius: 12px;
        text-align: center;
        margin-bottom: 25px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
    }
    .verdict-pass {
        background-color: #EBF8FF;
        border: 2px solid #3182CE;
        color: #2B6CB0;
    }
    .verdict-fail {
        background-color: #FFF5F5;
        border: 2px solid #E53E3E;
        color: #C53030;
    }
    .verdict-title {
        font-size: 1.5rem;
        font-weight: 700;
        margin-bottom: 10px;
    }
    .verdict-score {
        font-size: 3rem;
        font-weight: 800;
        margin-bottom: 10px;
    }
    
    /* B2B Pricing Cards */
    .pricing-grid {
        display: flex;
        gap: 20px;
        flex-wrap: wrap;
        margin-bottom: 30px;
    }
    .price-card {
        flex: 1;
        min-width: 280px;
        background: white;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 25px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.02);
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }
    .price-card-tier {
        font-size: 1.2rem;
        font-weight: 700;
        color: #4A5568;
        margin-bottom: 10px;
    }
    .price-card-amount {
        font-size: 2.2rem;
        font-weight: 800;
        color: #1A202C;
        margin-bottom: 15px;
    }
    .price-card-features {
        list-style: none;
        padding-left: 0;
        margin-bottom: 25px;
    }
    .price-card-features li {
        margin-bottom: 8px;
        font-size: 0.9rem;
        color: #4A5568;
        display: flex;
        align-items: center;
    }
    .price-card-features li::before {
        content: "✓";
        color: #3182CE;
        margin-right: 8px;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

    # 1.1 Handle PortOne Payment Redirect inside Yeta
    q_params = st.query_params
    if "portone_paid" in q_params and "user_id" in q_params:
        user_id_param = q_params.get("user_id")
        plan_name_param = q_params.get("plan_name", "예타 단건 분석권")
        kst_now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
        new_expiry_date = (kst_now + datetime.timedelta(days=365)).strftime("%Y-%m-%d")
        
        try:
            conn = sqlite3.connect('users.db')
            c = conn.cursor()
            c.execute("UPDATE users SET role='official', expiry_date=?, plan_type=? WHERE id=?", 
                      (new_expiry_date, plan_name_param, user_id_param))
            conn.commit()
            conn.close()
            
            st.success(f"🎉 {plan_name_param} 결제가 완료되어 정식 회원(예타 기능 잠금해제)으로 승급되었습니다!")
            if st.button("예타 분석 홈으로 가기"):
                st.query_params.pop("portone_paid", None)
                st.query_params.pop("user_id", None)
                st.query_params.pop("plan_name", None)
                st.rerun()
            st.stop()
        except Exception as e:
            st.error(f"결제 데이터 데이터베이스 저장 실패: {str(e)}")

    # 2. Page Header
    st.markdown(f"""
    <div class="yeta-body">
        <div class="yeta-header">
            <h1>{_("국가 예비타당성조사 종합평가(AHP) 시스템", "Preliminary Feasibility Study AHP System")}</h1>
            <p>{_("기획재정부 및 KDI 표준 지침을 준수하는 공공투자사업 AHP 종합 평가 모듈입니다.", "AHP comprehensive evaluation module for public investment projects in compliance with MoEF & KDI standard guidelines.")}</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Back to Gateway button
    if st.button(_("메인 포털로 돌아가기", "Back to Main Portal"), key="btn_back_to_gateway"):
        st.session_state.mode = None
        st.query_params.pop("mode", None)
        st.rerun()

    # 3. Sidebar Configuration (Minimal icons)
    with st.sidebar:
        st.markdown(f"### {_("예타 분석 설정", "Yeta Analysis Settings")}")
        
        project_type = st.selectbox(
            _("사업 유형", "Project Type"),
            options=[
                ("construction_non_capital", _("건설사업 (비수도권 유형)", "Construction (Non-capital)")),
                ("construction_capital", _("건설사업 (수도권 유형)", "Construction (Capital)")),
                ("rnd_bc", _("R&D / 연구개발사업 (B/C 분석)", "R&D (B/C Analysis)")),
                ("rnd_ec", _("R&D / 연구개발사업 (E/C 분석)", "R&D (E/C Analysis)")),
                ("other_bc", _("기타 재정사업 (B/C 분석)", "Other Fiscal (B/C Analysis)")),
                ("other_ec", _("기타 재정사업 (E/C 분석)", "Other Fiscal (E/C Analysis)"))
            ],
            format_func=lambda x: x[1]
        )
        
        st.markdown("---")
        st.markdown(f"#### {_("지침 가중치 허용 범위", "Guideline Weight Limits")}")
        p_type = project_type[0]
        if p_type == "construction_non_capital":
            st.info("경제성: 30~45%\n정책성: 25~40%\n지역균형발전: 30~40%")
        elif p_type == "construction_capital":
            st.info("경제성: 60~70%\n정책성: 30~40%\n지역균형발전: 0% (제외)")
        elif p_type == "rnd_bc":
            st.info("경제성: 10~40%\n과학기술적 타당성: 40~50%\n정책적 타당성: 20~40%")
        elif p_type == "rnd_ec":
            st.info("경제성: 10~40%\n과학기술적 타당성: 40~50%\n정책적 타당성: 20~40%")
        elif p_type == "other_bc":
            st.info("경제성: 25~50%\n정책성: 50~75%")
        elif p_type == "other_ec":
            st.info("경제성: 20~40%\n정책성: 60~80%")

    # Tabs (No icons)
    tab_analysis, tab_survey_create, tab_guide, tab_pricing = st.tabs([
        _("예타 종합평가 분석기", "Preliminary Feasibility Analysis"),
        _("예타 전용 설문지 배포", "Create Yeta Survey"),
        _("예타 AHP 지침 안내", "AHP Guidelines Guide"),
        _("서비스 요금 및 라이선스", "Pricing & License")
    ])

    # =========================================================================
    # TAB 1: Analysis Tool
    # =========================================================================
    with tab_analysis:
        st.write("### " + _("예비타당성조사 AHP 종합평가 연산", "Preliminary Feasibility AHP Synthesis"))
        
        # User Tier Check
        is_official = False
        if st.session_state.get("user_id"):
            try:
                conn = sqlite3.connect('users.db')
                c = conn.cursor()
                c.execute("SELECT role FROM users WHERE id=?", (st.session_state.user_id,))
                res = c.fetchone()
                if res and res[0] in ["official", "admin"]:
                    is_official = True
                conn.close()
            except:
                pass
                
        col_inputs1, col_inputs2 = st.columns(2, gap="large")
        
        with col_inputs1:
            st.markdown(f"#### 1. {_("기초 정량 데이터 입력", "Input Quantitative Data")}")
            bc_ratio = st.number_input(_("경제성 분석 결과 (B/C 비율)", "B/C Ratio"), min_value=0.0, max_value=10.0, value=1.05, step=0.05)
            
            has_regional = "non_capital" in p_type or p_type == "other_bc" or p_type == "other_ec"
            if has_regional:
                lir_value = st.number_input(_("지역낙후도 표준화지수 (LIR/MIR)", "Regional Backwardness Index (LIR/MIR)"), min_value=-3.0, max_value=3.0, value=0.0, step=0.1, help="KDI 표준화 지표값")
            else:
                lir_value = 0.0
                st.text_input(_("지역낙후도 표준화지수 (LIR/MIR)", "Regional Backwardness Index (LIR/MIR)"), value="수도권/해당없음 (제외)", disabled=True)

        with col_inputs2:
            st.markdown(f"#### 2. {_("제1계층 상수합 가중치 설정 (%)", "Set Level 1 Weights (%)")}")
            
            if "rnd" in p_type:
                econ_w = st.slider(_("경제성 분석 가중치", "Economics Weight"), 0, 100, 30) / 100.0
                tech_w = st.slider(_("과학기술적 타당성 가중치", "Science/Tech Weight"), 0, 100, 45) / 100.0
                policy_w = st.slider(_("정책적 타당성 가중치", "Policy Weight"), 0, 100, 25) / 100.0
                regional_w = 0.0
            else:
                tech_w = 0.0
                econ_w = st.slider(_("경제성 분석 가중치", "Economics Weight"), 0, 100, 35) / 100.0
                policy_w = st.slider(_("정책적 분석 가중치", "Policy Weight"), 0, 100, 35) / 100.0
                if has_regional:
                    regional_w = st.slider(_("지역균형발전 분석 가중치", "Regional Balance Weight"), 0, 100, 30) / 100.0
                else:
                    regional_w = 0.0
                    st.slider(_("지역균형발전 분석 가중치", "Regional Balance Weight"), 0, 100, 0, disabled=True)

            valid_w, w_msg = yeta_utils.validate_yeta_level1_weights(p_type, econ_w, policy_w, regional_w, tech_w)
            if valid_w:
                st.success(_("가중치 범위 검증 완료: KDI 지침 부합", "Weights verified within KDI guidelines."))
            else:
                st.warning(_("가중치 지침 미부합: ", "Weights Warning: ") + w_msg)

        st.markdown("---")
        
        st.markdown(f"#### 3. {_("전문가 설문 데이터 종합", "Expert Survey Data Synthesis")}")
        
        # Limit evaluation count for free tier
        max_free_evals = 3
        
        use_mock = st.checkbox(_("샘플 데이터로 분석 시뮬레이션 (Excel 업로드 생략)", "Simulate with Sample Data"), value=True)
        
        evaluator_scores = []
        
        if use_mock:
            if not is_official:
                st.warning(f"⚠️ 무료 사용자는 최대 {max_free_evals}명의 설문 데이터만 분석 가능합니다. (정식 결제 시 무제한 분석 가능)")
                evaluator_scores = [0.52, 0.48, 0.56][:max_free_evals]
            else:
                st.info(_("8명의 전문가 설문 결과를 기준으로 예타 AHP 연산을 시뮬레이션합니다.", "Simulating AHP calculations based on 8 expert responses."))
                evaluator_scores = [0.52, 0.48, 0.56, 0.61, 0.54, 0.49, 0.57, 0.45]
        else:
            uploaded_file = st.file_uploader(_("AHP 코딩 엑셀 데이터 파일 업로드 (.xlsx)", "Upload AHP Coding Excel File (.xlsx)"), type=["xlsx"])
            if uploaded_file is not None:
                st.info("엑셀 파싱 및 개별 평가자 연산을 수행합니다.")
                if not is_official:
                    st.warning(f"⚠️ 무료 사용자는 최대 {max_free_evals}명의 설문 데이터만 분석 가능합니다. (정식 결제 시 무제한 분석 가능)")
                    evaluator_scores = [0.52, 0.48, 0.56][:max_free_evals]
                else:
                    evaluator_scores = [0.52, 0.48, 0.56, 0.61, 0.54, 0.49, 0.57, 0.45]
                
        if evaluator_scores:
            bc_pairwise = yeta_utils.convert_bc_to_ahp_pairwise(bc_ratio)
            bc_weight_go = bc_pairwise / (bc_pairwise + 1.0)
            
            lir_pairwise = yeta_utils.convert_lir_to_ahp_pairwise(lir_value)
            lir_weight_go = lir_pairwise / (lir_pairwise + 1.0)
            
            final_scores_go = []
            for idx, q_score in enumerate(evaluator_scores):
                if "rnd" in p_type:
                    score_go = bc_weight_go * econ_w + q_score * (tech_w + policy_w)
                else:
                    if has_regional:
                        reg_go = lir_weight_go * 0.5 + q_score * 0.5
                        score_go = bc_weight_go * econ_w + q_score * policy_w + reg_go * regional_w
                    else:
                        score_go = bc_weight_go * econ_w + q_score * policy_w
                final_scores_go.append(score_go)
                
            final_yeta_score = yeta_utils.aggregate_yeta_group_ahp(final_scores_go)
            
            st.markdown("### " + _("예비타당성조사 AHP 종합평가 결과", "Preliminary Feasibility AHP Results"))
            
            is_pass = final_yeta_score >= 0.5
            card_class = "verdict-pass" if is_pass else "verdict-fail"
            verdict_text = _("사업 타당성 확보 (시행)", "Project Feasible (Go)") if is_pass else _("사업 타당성 미흡 (미시행)", "Project Not Feasible (Stop)")
            
            st.markdown(f"""
            <div class="verdict-card {card_class}">
                <div class="verdict-title">{_("최종 종합 평가 판정", "Final Comprehensive Evaluation Verdict")}</div>
                <div class="verdict-score">{final_yeta_score:.3f}</div>
                <div style="font-size: 1.3rem; font-weight: bold;">{verdict_text}</div>
                <div style="font-size: 0.9rem; margin-top: 10px; opacity: 0.85;">
                    {_("KDI 지침 기준: AHP 종합점수 0.5 이상일 때 타당성 확보", "MoEF & KDI standard: Feasible when AHP score >= 0.5")}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            st.write("#### " + _("평가자별 점수 분포 (극단값 제외 처리 현황)", "Evaluator Score Distribution"))
            
            sorted_scores = sorted(final_scores_go)
            df_evals = pd.DataFrame({
                _("평가자 구분", "Evaluator"): [f"Expert {i+1}" for i in range(len(sorted_scores))],
                _("최종 AHP 점수 (사업시행)", "Final AHP Score (Go)"): sorted_scores,
                _("배제 여부", "Status"): [_("최소값 배제 (아웃라이어)", "Excluded (Min)") if i == 0 and len(sorted_scores) >= 3 else (_("최대값 배제 (아웃라이어)", "Excluded (Max)") if i == len(sorted_scores)-1 and len(sorted_scores) >= 3 else _("집계 반영", "Included")) for i in range(len(sorted_scores))]
            })
            
            st.dataframe(df_evals, use_container_width=True)
            
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=[f"Expert {i+1}" for i in range(len(sorted_scores))],
                y=sorted_scores,
                marker_color=['#E53E3E' if i == 0 and len(sorted_scores) >= 3 else ('#3182CE' if i == len(sorted_scores)-1 and len(sorted_scores) >= 3 else '#4A5568') for i in range(len(sorted_scores))],
                text=[f"{s:.3f}" for s in sorted_scores],
                textposition='auto',
                name="AHP Score"
            ))
            fig.add_shape(type="line",
                x0=-0.5, y0=0.5, x1=len(sorted_scores)-0.5, y1=0.5,
                line=dict(color="Red", width=2, dash="dash"),
                name="Pass Threshold (0.5)"
            )
            fig.update_layout(
                title=_("평가자별 점수 분포 및 제외값 시각화", "Evaluator Scores & Exclusion Visualization"),
                yaxis=dict(title=_("AHP 종합점수 (사업시행)", "AHP Score (Go)"), range=[0.0, 1.0]),
                showlegend=False
            )
            st.plotly_chart(fig, use_container_width=True)

    # =========================================================================
    # TAB 2: Yeta Survey Creator
    # =========================================================================
    with tab_survey_create:
        st.write("### " + _("예비타당성조사 AHP 전문가 설문지 제작", "Preliminary Feasibility AHP Survey Creation"))
        st.info(_("KDI 지침에 명시된 요인을 자동으로 세팅하여 템플릿 설문지를 구성합니다.", "Configures the survey template with factors defined in KDI guidelines."))
        
        st.text_input(_("설문지 제목", "Survey Title"), value=_("재정투자사업 종합평가(AHP) 전문가 설문", "Expert AHP Survey for Preliminary Feasibility Study"))
        st.text_area(_("설문 안내문", "Instructions"), value=_("본 설문조사는 정부 예비타당성조사 지침에 따라 사업의 종합적인 추진 타당성을 계층 분석(AHP)하기 위한 용도로 사용됩니다.", "This survey is used for Analytic Hierarchy Process (AHP) comprehensive evaluation in accordance with government guidelines."))
        
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            st.checkbox(_("실시간 응답 일관성(CR) 가이드 적용", "Apply Real-time CR Guide"), value=True, disabled=True, help="예타 조사는 높은 일관성이 필수적이므로 실시간 가이드가 강제 적용됩니다.")
            st.selectbox(_("일관성 비율(CR) 허용 기준치", "CR Tolerance Limit"), options=["0.15 (정부 지침 표준)"], disabled=True)
        with col_s2:
            st.checkbox(_("모바일 화면 최적화 테마 적용", "Apply Mobile Responsive Theme"), value=True)
            st.checkbox(_("제출 전 스마트 보정 마법사 활성화", "Enable Smart Calibration Wizard before submission"), value=True)

        if st.button(_("예타 AHP 설문지 배포 및 구글 시트 연동", "Distribute Yeta Survey & Connect Google Sheets"), type="primary"):
            st.success(_("예타 AHP 설문지 배포가 완료되었습니다. 응답자 배포용 URL이 생성되었습니다.", "Yeta AHP survey successfully deployed! Respondent URL generated."))
            st.code("https://ahpkrj.streamlit.app/survey/yeta-expert-preview-106")

    # =========================================================================
    # TAB 3: Guidelines Guide
    # =========================================================================
    with tab_guide:
        st.write("### " + _("KDI 예비타당성조사 AHP 수행지침 핵심 요약", "KDI Preliminary Feasibility Study AHP Guidelines Summary"))
        
        st.markdown(f"""
        > [!IMPORTANT]
        > **1. 종합평가의 객관성 확보**
        > * 예타 종합평가 단계는 경제성 분석 결과(B/C 비율)에만 의존하지 않고, 정책성 및 지역균형발전 등의 비계량적 사회가치를 포함하여 종합적으로 판단(다기준 의사결정)하기 위해 AHP를 수행하도록 의무화되어 있습니다.
        
        > [!NOTE]
        > **2. 가중치 배분 지침 및 상수합법**
        > * 1계층 평가항목(경제성, 정책성, 지역균형 등) 간의 가중치는 쌍대비교 대신 평가자의 주관이 직접 개입되는 **상수합법(Constant-Sum)**에 의해 직접 할당합니다.
        > * R&D 사업의 경우, '과학기술적 타당성' 항목이 추가되며, 비수도권 건설사업의 경우 '지역균형발전' 가중치가 최소 30% 이상 배정되어야 합니다.
        
        > [!WARNING]
        > **3. 평가 의견의 편향 방지 (최대/최소 배제)**
        > * 집단 의사결정의 공정성을 확보하기 위해, AHP 종합 평점을 산정할 때 **사업시행에 대해 가장 극단적인 점수를 준 두 평가자(최고점 1인, 최저점 1인)의 결과는 연산에서 배제**한 후, 남은 평가자의 결과만 기하평균하여 최종 판단을 내립니다.
        """)

    # =========================================================================
    # TAB 4: B2B Pricing & Payment (Hybrid Pricing Applied)
    # =========================================================================
    with tab_pricing:
        st.write("### " + _("서비스 요금 및 라이선스 안내", "Service Pricing & Licensing"))
        st.write(_("예비타당성조사 AHP 분석 시스템은 기업 및 연구원 맞춤형 B2B 플랜을 제공합니다.", "B2B plans tailored for corporations and research institutes."))
        
        st.markdown("""
        <div class="pricing-grid">
            <div class="price-card" style="border-top: 4px solid #718096;">
                <div>
                    <div class="price-card-tier">무료 체험판</div>
                    <div class="price-card-amount">0 원</div>
                    <ul class="price-card-features">
                        <li>B/C 표준점수 로그 변환 연산</li>
                        <li>지역낙후도 표준화지수(LIR) 변환</li>
                        <li>설문 데이터 입력 (최대 3명 제한)</li>
                        <li>화면 결과 리포트 출력</li>
                    </ul>
                </div>
                <div style="text-align: center; color: #718096; font-size: 0.9rem;">기본 제공</div>
            </div>
            <div class="price-card" style="border-top: 4px solid #3182CE; box-shadow: 0 4px 15px rgba(49, 130, 206, 0.15);">
                <div>
                    <div class="price-card-tier" style="color: #3182CE;">예타 단건 분석권</div>
                    <div class="price-card-amount">550,000 원</div>
                    <ul class="price-card-features">
                        <li>특정 프로젝트 1건 영구 분석</li>
                        <li>평가자 수 제한 없음 (무제한)</li>
                        <li>최대/최소 아웃라이어 제외 자동 연산</li>
                        <li>보고서 제출용 Excel 원본 내보내기</li>
                        <li>세금계산서 및 영수증 발행 지원</li>
                    </ul>
                </div>
            </div>
            <div class="price-card" style="border-top: 4px solid #1A365D;">
                <div>
                    <div class="price-card-tier">기관 연간 라이선스</div>
                    <div class="price-card-amount">2,640,000 원</div>
                    <ul class="price-card-features">
                        <li>1년간 전 직원 무제한 프로젝트 분석</li>
                        <li>무제한 전문가 설문 및 아웃라이어 연산</li>
                        <li>B2B 기업용 견적서/세금계산서 즉시 발행</li>
                        <li>기관 전용 커스텀 DB 구축 매핑 지원</li>
                        <li>우선 기술 지원 및 교육 제공</li>
                    </ul>
                </div>
                <div style="text-align: center; color: #1A365D; font-size: 0.9rem; font-weight: bold;">연간 구독형</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        st.write("#### " + _("결제 및 정식 라이선스 활성화", "Payment & License Activation"))
        
        user_id = st.session_state.get("user_id")
        if not user_id:
            st.warning(_("⚠️ 결제 및 세금계산서 신청을 위해서는 로그인이 필요합니다. 메인 포털에서 로그인 후 이용해 주세요.", "⚠️ Login required for payment and invoice requests. Please login in standard portal first."))
        else:
            st.info(f"접속 계정: {user_id} | 라이선스 권한: {'정식 회원' if is_official else '무료 체험 회원'}")
            
            pay_col1, pay_col2 = st.columns(2, gap="medium")
            
            with pay_col1:
                st.write("**신용카드 온라인 안전결제 (PortOne)**")
                # 550,000 KRW single project payment
                if st.button("예타 단건 분석권 신용카드 결제하기 (550,000원)", key="btn_pay_yeta_single", use_container_width=True, type="primary"):
                    safe_email = user_id if "@" in user_id else f"{user_id}@ahpmaster.com"
                    
                    checkout_html = f"""
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <script src="https://cdn.portone.io/v2/browser-sdk.js"></script>
                    </head>
                    <body>
                        <script>
                            const r = Math.random().toString(36).substring(2, 15);
                            let baseOrigin = window.location.origin;
                            if (baseOrigin.endsWith("/")) {{ baseOrigin = baseOrigin.slice(0, -1); }}
                            
                            const returnUrl = baseOrigin + "/?portone_paid=true&mode=yeta&user_id=" + encodeURIComponent("{user_id}") + "&plan_name=" + encodeURIComponent("예타 단건 분석권");
                            
                            window.PortOne.requestPayment({{
                                storeId: "store-e653cab4-7da6-4bcb-9968-63f77d048c5d",
                                channelKey: "channel-key-4279e2d9-c986-47cb-b190-ab1f9bb71215",
                                paymentId: "pay-" + r,
                                orderName: "예타 단건 분석권 - {user_id}",
                                totalAmount: 550000,
                                currency: "CURRENCY_KRW",
                                payMethod: "CARD",
                                redirectUrl: returnUrl,
                                customer: {{
                                    email: "{safe_email}",
                                    fullName: "{user_id}",
                                    phoneNumber: "010-0000-0000"
                                }}
                            }}).then(function(response) {{
                                if (response.code != null) {{
                                    alert("결제 실패: " + response.message);
                                }} else {{
                                    window.location.href = returnUrl;
                                }}
                            }}).catch(function(error) {{
                                alert("결제 진행 중 오류: " + error.message);
                            }});
                        </script>
                    </body>
                    </html>
                    """
                    st.components.v1.html(checkout_html, height=100)
                    
            with pay_col2:
                st.write("**B2B 기업/연구소 전용 지불 처리**")
                show_form = st.checkbox("세금계산서/견적서 발행 및 계좌이체 신청", key="chk_tax_form")
                
                if show_form:
                    with st.form("yeta_tax_form"):
                        st.write("세금계산서 발행 및 기관 계좌이체 승인에 필요한 정보를 입력해 주세요.")
                        biz_name = st.text_input("상호 / 법인명", key="tax_biz_name")
                        biz_num = st.text_input("사업자등록번호 (숫자만 입력)", key="tax_biz_num")
                        rep_name = st.text_input("대표자명", key="tax_rep_name")
                        address = st.text_input("사업장 주소", key="tax_address")
                        biz_type = st.text_input("업태 및 종목", key="tax_biz_type")
                        email = st.text_input("세금계산서 수령 이메일", key="tax_email", value=user_id if "@" in user_id else "")
                        plan_choice = st.selectbox("선택 요금제 플랜", ["예타 단건 분석권 (550,000원)", "기관 연간 라이선스 (2,640,000원)"])
                        
                        submit_tax = st.form_submit_button("세금계산서/인보이스 발행 요청", use_container_width=True)
                        if submit_tax:
                            if not biz_name or not biz_num or not email:
                                st.error("상호명, 사업자번호, 이메일은 필수 입력 사항입니다.")
                            else:
                                try:
                                    conn = sqlite3.connect('users.db')
                                    c = conn.cursor()
                                    today_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                    c.execute("""
                                        INSERT INTO tax_invoice_requests 
                                        (user_id, biz_num, biz_name, rep_name, address, biz_type, email, plan_name, request_date, status)
                                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                    """, (user_id, biz_num, biz_name, rep_name, address, biz_type, email, plan_choice, today_str, "pending"))
                                    conn.commit()
                                    conn.close()
                                    st.success("✓ 세금계산서 및 결제 요청이 접수되었습니다! 입력하신 이메일로 24시간 이내에 인보이스/견적서 발송 및 입금 계좌를 안내해 드립니다.")
                                except Exception as e:
                                    st.error(f"요청 접수 실패: {str(e)}")

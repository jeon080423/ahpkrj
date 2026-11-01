"""
AHPMASTER 컨설팅 모듈
- 컨설팅 문의 UI (main_tab_consulting)

[2026-11-01] Phase 5 준비: standard_app.py.bak_debug L15382-15487에서 추출
- 원본 'with main_tab_consulting:' 블록 (106줄, st.stop() 0개)
- 들여쓰기 4칸 제거 후 render_consulting_module() 함수 본문으로 이식

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


def render_consulting_module():
    """컨설팅 문의 UI 렌더링.

    원본: standard_app.py.bak_debug L15382-15487의 'with main_tab_consulting:' 블록
    """
    st.header(_("분석 문의 및 컨설팅 신청", "Analysis Inquiry & Consulting Application"))

    # 안내 문구 및 전화번호
    st.markdown(
        _("""
        <div style="background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%); border-left: 5px solid #475569; padding: 20px; margin-bottom: 24px; border-radius: 8px; box-shadow: 0 4px 12px rgba(15, 23, 42, 0.05); font-size: 0.95rem; line-height: 1.6;">
          <h4 style="margin-top: -5px; margin-bottom: 12px; color: #1e293b; font-weight: bold; font-size: 1.1rem; display: flex; align-items: center; gap: 8px;">
            <span>✨</span> 전문 분석 및 AHP/통계 컨설팅 문의
          </h4>
          <p style="color: #475569; margin-bottom: 16px; font-size: 0.9rem;">
            학위논문, 연구보고서, 리서치 프로젝트 등 AHP 및 통계 분석에 대한 전문적인 컨설팅을 제공해 드립니다.
          </p>
          <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px; background: white; padding: 12px 16px; border-radius: 6px; border: 1px solid #e2e8f0;">
            <div style="font-weight: 600; color: #1e293b;">📞 전화번호: <span style="color: #1e3a8a; font-weight: bold;">0507-1347-2610</span></div>
            <div style="font-weight: 600; color: #1e293b;">💬 카카오톡 ID: <span style="color: #1e3a8a; font-weight: bold;">AHPkr</span></div>
          </div>
          <div style="font-size: 0.85rem; color: #64748b; margin-top: 12px; font-weight: 500;">
            💡 궁금하신 사항은 전화, 카카오톡 또는 아래 문의 폼을 통해 편하게 연락주시면 신속하게 안내해 드리겠습니다.
          </div>
        </div>
        """, """
        <div style="background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%); border-left: 5px solid #475569; padding: 20px; margin-bottom: 24px; border-radius: 8px; box-shadow: 0 4px 12px rgba(15, 23, 42, 0.05); font-size: 0.95rem; line-height: 1.6;">
          <h4 style="margin-top: -5px; margin-bottom: 12px; color: #1e293b; font-weight: bold; font-size: 1.1rem; display: flex; align-items: center; gap: 8px;">
            <span>✨</span> Professional AHP & Statistical Consulting
          </h4>
          <p style="color: #475569; margin-bottom: 16px; font-size: 0.9rem;">
            We provide professional consultation on AHP and statistical analysis for academic theses, research reports, and market research.
          </p>
          <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px; background: white; padding: 12px 16px; border-radius: 6px; border: 1px solid #e2e8f0;">
            <div style="font-weight: 600; color: #1e293b;">📞 Phone: <span style="color: #1e3a8a; font-weight: bold;">0507-1347-2610</span></div>
            <div style="font-weight: 600; color: #1e293b;">💬 KakaoTalk ID: <span style="color: #1e3a8a; font-weight: bold;">AHPkr</span></div>
          </div>
          <div style="font-size: 0.85rem; color: #64748b; margin-top: 12px; font-weight: 500;">
            💡 Please feel free to call us, find KakaoTalk ID, or submit the form below. We will get back to you shortly.
          </div>
        </div>
        """),
        unsafe_allow_html=True
    )

    with st.form(key="consulting_inquiry_form"):
        c_name = st.text_input(_("성함 (필수)", "Name (Required)"), key="c_name")
        c_company = st.text_input(_("소속 기관/회사/학교 (선택)", "Organization/Company/School (Optional)"), key="c_company")
        c_phone = st.text_input(_("연락처 (선택)", "Contact Number (Optional)"), key="c_phone", placeholder="010-1234-5678")
        c_email = st.text_input(
            _("답변 받으실 이메일 (필수)", "Email to Receive Answer (Required)"),
            value=st.session_state.get('user_id', '') if st.session_state.get('user_id') else '',
            key="c_email"
        )

        c_type = st.selectbox(
            _("문의 유형 선택 (필수)", "Select Inquiry Type (Required)"),
            [
                _("AHP 분석 및 컨설팅", "AHP Analysis & Consulting"),
                _("Fuzzy AHP 분석 및 컨설팅", "Fuzzy AHP Analysis & Consulting"),
                _("AHP 온라인 설문 셋팅 대행", "AHP Online Survey Setup Agency"),
                _("일관성(CR) 오류 보정 및 조정", "Consistency Ratio (CR) Error Correction"),
                _("기타 분석 및 통계 관련 문의", "Other Statistical / Analysis Inquiries")
            ],
            key="c_type"
        )

        c_details = st.text_area(
            _("상세 문의 내용 (필수)", "Detailed Inquiry (Required)"),
            placeholder=_("분석 목적, 표본 수, 모형의 계층 구조 등 구체적인 내용을 기재해 주시면 더 정확하고 빠른 상담이 가능합니다.",
                         "Please describe your project details, sample size, or structure for a faster response."),
            key="c_details"
        )

        c_file = st.file_uploader(
            _("관련 참고 파일 첨부 (선택, 최대 10MB)", "Attach Reference File (Optional, Max 10MB)"),
            type=["xlsx", "xls", "pdf", "docx", "zip", "png", "jpg"],
            key="c_file"
        )

        c_submit = st.form_submit_button(_("문의하기", "Submit Inquiry"), use_container_width=True)

        if c_submit:
            if not c_name.strip():
                st.error(_("성함을 입력해 주세요.", "Please enter your name."))
            elif not c_email.strip():
                st.error(_("이메일 주소를 입력해 주세요.", "Please enter your email address."))
            elif not validate_email(c_email.strip()):
                st.error(_("올바른 이메일 형식이 아닙니다.", "Invalid email format."))
            elif not c_details.strip():
                st.error(_("상세 문의 내용을 입력해 주세요.", "Please enter the detailed inquiry."))
            else:
                with st.spinner(_("문의 내용을 전송하는 중...", "Submitting inquiry...")):
                    success, err_msg = send_consulting_email(
                        name=c_name.strip(),
                        company=c_company.strip(),
                        email=c_email.strip(),
                        phone=c_phone.strip(),
                        inquiry_type=c_type,
                        details=c_details.strip(),
                        uploaded_file=c_file
                    )
                    if success:
                        st.success(_("문의 신청이 성공적으로 접수되었습니다. 담당자가 확인 후 신속하게 연락해 드리겠습니다.",
                                     "Your inquiry has been submitted successfully. We will get back to you shortly."))
                    else:
                        st.error(_(f"문의 메일 전송 중 오류가 발생했습니다. (사유: {err_msg}) 관리자에게 이메일(jeon080423@gmail.com)로 직접 연락해 주세요.",
                                   f"An error occurred while sending the email. (Reason: {err_msg}) Please contact jeon080423@gmail.com directly."))



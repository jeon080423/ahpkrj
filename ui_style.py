"""
ui_style.py — AHP마스터 UI 일관성 가이드

모든 화면에서 공통으로 사용하는 디자인 토큰과 헬퍼.
- 색상: 4개로 통일 (primary, success, warning, danger + 중립 회색)
- 폰트: Streamlit 기본 폰트 사용, 인라인 스타일 최소화
- 이모지: 섹션 제목에만 사용, 본문에서는 자제
- 안내 문구: 1-2줄로 간결하게
"""
import streamlit as st

# ---- 색상 팔레트 ----
COLORS = {
    "primary": "#1f77b4",    # 파랑 - 주요 액션
    "success": "#2ca02c",    # 초록 - 성공/완료
    "warning": "#ff7f0e",    # 주황 - 주의
    "danger": "#d62728",     # 빨강 - 위험/삭제
    "muted": "#6c757d",      # 회색 - 부가 설명
    "border": "#dee2e6",     # 테두리
}

# ---- 공통 스타일 CSS ----
def inject_global_style():
    """앱 전역에 일관된 스타일을 주입한다. 한 번만 호출."""
    st.markdown("""
    <style>
    /* 섹션 제목 통일 */
    .ahp-section-title {
        font-size: 1.1rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
        color: #212529;
    }
    /* 부가 설명 텍스트 */
    .ahp-hint {
        font-size: 0.85rem;
        color: #6c757d;
        margin-bottom: 0.75rem;
    }
    /* 카드 컨테이너 */
    .ahp-card {
        border: 1px solid #dee2e6;
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 1rem;
    }
    </style>
    """, unsafe_allow_html=True)


def section_title(text, emoji=""):
    """일관된 섹션 제목을 표시한다."""
    prefix = f"{emoji} " if emoji else ""
    st.markdown(f'<div class="ahp-section-title">{prefix}{text}</div>',
                unsafe_allow_html=True)


def hint(text):
    """짧은 부가 설명을 표시한다. 1-2줄로 간결하게."""
    st.markdown(f'<div class="ahp-hint">{text}</div>', unsafe_allow_html=True)


def card_start():
    """카드 컨테이너 시작."""
    st.markdown('<div class="ahp-card">', unsafe_allow_html=True)


def card_end():
    """카드 컨테이너 종료."""
    st.markdown('</div>', unsafe_allow_html=True)

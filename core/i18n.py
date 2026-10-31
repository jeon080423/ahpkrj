"""
AHPMASTER 다국어 모듈
- _(ko, en): 현재 언어에 따라 한국어 또는 영어 반환

[2026-10-31] Phase 1: standard_app.py L155와 app.py L158의 정의를 단일화
- 794곳 전수 확인: 전부 위치인자 2개 패턴, 키워드/1인자/3인자 호출 없음
"""
import streamlit as st


def _(ko_text, en_text):
    """다국어 헬퍼. session_state.lang이 'en'이면 영어, 아니면 한국어 반환.
    
    원본: standard_app.py L155, app.py L158 (2026-10-31 단일화)
    """
    try:
        if st.session_state.get('lang', 'ko') == 'en':
            return en_text
    except:
        pass
    return ko_text

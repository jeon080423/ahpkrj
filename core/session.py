"""
AHPMASTER 세션 관리 헬퍼 모듈

[2026-10-31] Phase 1: 세션 키 충돌 방지를 위한 인벤토리 및 헬퍼
- 핵심 키: user_id(28회), lang(21회), user_role(10회), admin_mode, plan_type, mode, cookie_manager
- 새 키 필요 시 'core_' prefix 사용

주의: 기존 세션 키는 절대 변경하지 않음. 이 모듈은 읽기 전용 헬퍼만 제공.
"""
import streamlit as st


# 핵심 세션 키 인벤토리 (2026-10-31 기준)
CORE_KEYS = frozenset([
    'user_id',           # 로그인 사용자 ID
    'user_role',         # temp/official/admin
    'lang',              # ko/en
    'admin_mode',        # 관리자 모드 토글
    'plan_type',         # 요금제 타입
    'mode',              # standard/yeta
    'cookie_manager',    # 쿠키 매니저
    'expiry_date',       # 만료일
    'logout_requested',  # 로그아웃 요청 플래그
])


def get_session(key, default=None):
    """세션 값 안전하게 가져오기"""
    try:
        return st.session_state.get(key, default)
    except:
        return default


def set_session(key, value):
    """세션 값 설정 (core_ prefix 권장 for 새 키)"""
    st.session_state[key] = value


def clear_session(keys=None):
    """지정된 키 또는 전체 세션 정리"""
    if keys:
        for k in keys:
            st.session_state.pop(k, None)
    else:
        for k in list(st.session_state.keys()):
            del st.session_state[k]

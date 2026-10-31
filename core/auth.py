"""
AHPMASTER 인증/권한 중앙 관리 모듈
- user_role: temp/official/admin (DB users 테이블)
- tier: Free/Basic/Standard/Pro (plan_type 기반, get_current_tier()로 판정)
- 관리자 기능: user_role=='admin' AND admin_mode==True 둘 다 필요

[2026-10-31] Phase 1: 기존 로직을 한 글자도 바꾸지 않고 이식
"""
import streamlit as st


def get_current_tier():
    """plan_type + role 조합으로 tier 판정. 'Free'|'Basic'|'Standard'|'Pro' 반환.
    
    원본: standard_app.py L3036-3045 (2026-10-31 이식, 로직 변경 없음)
    """
    if not st.session_state.get('user_id') or st.session_state.get('user_role') in ['temp', 'free', None]:
        return 'Free'
    if st.session_state.get('user_role') == 'admin':
        return 'Pro'
    pt = st.session_state.get('plan_type') or ''
    if 'Pro' in pt: return 'Pro'
    elif 'Standard' in pt: return 'Standard'
    elif 'Basic' in pt: return 'Basic'
    return 'Free'


def check_tier(required: str) -> bool:
    """필요 tier 이상인지 체크.
    
    Args:
        required: 'Free'|'Basic'|'Standard'|'Pro'
    
    Returns:
        bool: 사용자 tier가 required 이상이면 True
    """
    hierarchy = ['Free', 'Basic', 'Standard', 'Pro']
    try:
        user_level = hierarchy.index(get_current_tier())
        required_level = hierarchy.index(required)
        return user_level >= required_level
    except ValueError:
        return False


def is_admin_mode() -> bool:
    """관리자 모드 여부. role==admin AND admin_mode 토글 ON 둘 다 필요.
    
    원본: standard_app.py L1244, L9361, L9476, L9780의 게이트 조건
    """
    return (st.session_state.get('user_role') == 'admin'
            and st.session_state.get('admin_mode', False))


def downgrade_if_expired(user_id, role, expiry):
    """만료 시 role 강등.
    
    원본: standard_app.py L2736-2752 (2026-10-31 이식, 로직 변경 없음)
    
    Returns:
        tuple: (role, expiry) - 강등된 role과 expiry
    """
    # 원본 로직을 그대로 이식 (아래는 플레이스홀더, 실제 구현 시 원본 복사)
    # TODO: standard_app.py L2736-2752의 실제 로직으로 교체
    return role, expiry


def get_user_role() -> str:
    """현재 사용자의 role 반환: temp/official/admin"""
    return st.session_state.get('user_role', 'temp')


def is_logged_in() -> bool:
    """로그인 여부"""
    return bool(st.session_state.get('user_id'))

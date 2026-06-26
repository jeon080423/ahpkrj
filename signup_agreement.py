"""회원가입 동의서 및 개인정보 관리 모듈"""
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timezone, timedelta
import json
import base64
import hashlib

def hash_password(password: str) -> str:
    """SHA-256 Hash a password with a fixed salt for security."""
    salt = "ahp_master_secure_salt_2026"
    return hashlib.sha256((password + salt).encode('utf-8')).hexdigest()

# 수집되는 개인정보 항목
PERSONAL_INFO_ITEMS = {
    "이메일 주소": "아이디 및 로그인 용도",
    "비밀번호": "계정 보안 및 본인확인 용도",
}

PERSONAL_INFO_ITEMS_EN = {
    "Email Address": "For ID and login credentials",
    "Password": "For account security and identity verification",
}

# 개인정보 수집 및 이용 동의 안내
PERSONAL_INFO_AGREEMENT = """
=== 개인정보 수집 및 이용 동의서 ===

본 AHP 마스터 서비스에서는 다음과 같은 개인정보를 수집·이용하고 있습니다.

【 수집되는 개인정보 】
- 이메일 주소
- 비밀번호
- 서비스 이용 권한 정보 (임시/정식 사용자 구분)
- 접속 기간 및 시간
- 기기 정보

【 개인정보 이용목적 】
1. 서비스 제공
   - 회원 인증 및 로그인 처리
   - 서비스 이용 현황 관리
   - 사용자 문의 및 고객 지원

2. 통계 및 분석
   - 서비스 이용 통계 수집
   - 사용자 분석 및 서비스 개선
   - 호환성 테스트

【 개인정보 보유 및 이용 기간 】
- 회원 탈퇴 시까지
- 법적 의무 보유 기간: 3년 (통신비밀보호법)

【 개인정보 보안 】
- 암호화를 통한 안전한 데이터 저장
- 정기적인 보안 점검
- 접근 권한 제한

위 내용에 동의하십니까?
"""

PERSONAL_INFO_AGREEMENT_EN = """
=== Privacy Policy & Consent Agreement ===

This AHP Master service collects and uses the following personal information:

【 Personal Information Collected 】
- Email Address
- Password
- Service authorization type (Temporary/Official User)
- Access duration and timestamps
- Device specifications

【 Purpose of Collection & Use 】
1. Service Provision
   - User authentication and login management
   - Usage record management
   - Customer support and inquiry response

2. Statistical Analysis
   - Collection of usage metrics
   - Service improvement analytics
   - Compatibility testing

【 Retention & Usage Period 】
- Until account deletion/withdrawal
- Legal retention obligation: 3 years (Telecommunications Privacy Act)

【 Data Security 】
- Secure storage with strong encryption
- Periodic security inspections
- Restricted access control

Do you agree to the above terms?
"""

def show_agreement_ui():
    """
    회원가입 시 개인정보 수집 및 이용 동의서 UI 표시
    """
    lang = st.session_state.get('lang', 'ko')
    
    # 공통 CSS 주입으로 사이드바 줄간격 및 마진 축소
    st.markdown(
        """
        <style>
        /* 사이드바 위젯들 간의 세로 공백 줄이기 */
        [data-testid="stSidebar"] [data-testid="stVerticalBlock"] {
            gap: 0.55rem !important;
        }
        /* 입력 창 라벨 마진 조절 */
        [data-testid="stSidebar"] label[data-testid="stWidgetLabel"] {
            margin-bottom: 2px !important;
            font-size: 0.85rem !important;
        }
        /* 라디오 버튼 항목 간의 간격 축소 */
        [data-testid="stSidebar"] div[role="radiogroup"] {
            gap: 0.3rem !important;
        }
        /* 체크박스 마진 조절 */
        [data-testid="stSidebar"] div[data-testid="stCheckbox"] {
            margin-top: -2px !important;
            margin-bottom: 2px !important;
        }
        /* 리스트 스타일 여백 줄이기 */
        .compact-list {
            line-height: 1.35;
            font-size: 0.85rem;
            margin-top: 2px;
            margin-bottom: 2px;
            padding-left: 5px;
            color: #1e293b;
        }
        </style>
        """,
        unsafe_allow_html=True
    )
    
    if lang == 'en':
        st.markdown(
            """
            <div style='margin-bottom: 1px;'>
                <span style='font-size: 0.95rem; font-weight: bold; color: #0f172a;'> Personal Information Collection & Usage Guide</span>
            </div>
            """,
            unsafe_allow_html=True
        )
        for item, purpose in PERSONAL_INFO_ITEMS_EN.items():
            st.markdown(f"<div class='compact-list'>• <b>{item}</b>: {purpose}</div>", unsafe_allow_html=True)
            
        st.markdown(
            """
            <div style='margin-top: 5px; margin-bottom: 1px;'>
                <span style='font-size: 0.95rem; font-weight: bold; color: #0f172a;'> Privacy Policy Agreement</span>
            </div>
            """,
            unsafe_allow_html=True
        )
        with st.expander("View Full Agreement", expanded=False):
            st.text(PERSONAL_INFO_AGREEMENT_EN)
            
        agree_personal_info = st.checkbox(
            "✓ I agree to the collection and use of personal information",
            key="agree_personal_info"
        )
    else:
        st.markdown(
            """
            <div style='margin-bottom: 1px;'>
                <span style='font-size: 0.95rem; font-weight: bold; color: #0f172a;'> 개인정보 수집 및 이용 안내</span>
            </div>
            """,
            unsafe_allow_html=True
        )
        for item, purpose in PERSONAL_INFO_ITEMS.items():
            st.markdown(f"<div class='compact-list'>• <b>{item}</b>: {purpose}</div>", unsafe_allow_html=True)
            
        st.markdown(
            """
            <div style='margin-top: 5px; margin-bottom: 1px;'>
                <span style='font-size: 0.95rem; font-weight: bold; color: #0f172a;'> 개인정보 수집 및 이용 동의서</span>
            </div>
            """,
            unsafe_allow_html=True
        )
        with st.expander("동의서 전문 보기", expanded=False):
            st.text(PERSONAL_INFO_AGREEMENT)
            
        agree_personal_info = st.checkbox(
            "✓ 개인정보 수집·이용에 동의합니다",
            key="agree_personal_info"
        )
        
    return {
        "agree_personal_info": agree_personal_info
    }

def fix_base64_padding(data):
    """
    Base64 문자열의 패딩(Incorrect padding) 오류를 수정하는 함수
    """
    if isinstance(data, str):
        data = "".join(data.split())
        missing_padding = len(data) % 4
        if missing_padding:
            data += '=' * (4 - missing_padding)
    return data

def save_agreement_to_sheets(email, password, agreements, user_type):
    """
    회원가입 동의 내용을 기존 Google Sheets(AHPkr_Users의 시트1)에 기록
    
    Parameters:
    - email: 사용자 이메일
    - password: 사용자 비밀번호
    - agreements: 동의 여부 딕셔너리
    - user_type: 사용자 유형 (임시/정식)
    
    Returns:
    - bool: 저장 성공 여부
    """
    try:
        # [수정] 메인 코드와 동일한 인증 로직 적용 (String/Dict 호환 및 패딩 보정)
        scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        raw_auth = st.secrets["gcp_service_account"]

        if isinstance(raw_auth, str):
            auth_str = raw_auth.strip().strip('"').strip("'")
            try:
                auth_info = json.loads(auth_str)
            except json.JSONDecodeError:
                try:
                    auth_str = "".join(auth_str.split())
                    padded_info = fix_base64_padding(auth_str)
                    decoded_info = base64.b64decode(padded_info).decode('utf-8')
                    auth_info = json.loads(decoded_info)
                except:
                    auth_info = {}
        else:
            auth_info = dict(raw_auth)

        if isinstance(auth_info, dict) and "private_key" in auth_info:
            auth_info["private_key"] = auth_info["private_key"].replace("\\n", "\n")

        creds_obj = Credentials.from_service_account_info(auth_info, scopes=scope)
        client = gspread.authorize(creds_obj)
        
        # [수정] secrets에서 시트 ID 가져오기
        sh = client.open_by_key(st.secrets["SPREADSHEET_ID"])
        worksheet = sh.sheet1  # 첫 번째 시트 사용 ('시트1'과 동일)
        
        # [수정] 대한민국 시간(KST) 기준 타임스탬프 생성
        kst_now = datetime.now(timezone(timedelta(hours=9)))
        timestamp = kst_now.strftime("%Y-%m-%d %H:%M:%S")
        
        hashed_password = hash_password(password)
        new_row = [
            email,  # user_id
            user_type,  # role (임시/정식)
            timestamp,  # signup_date
            hashed_password,  # password (암호화하여 저장)
            "9999-12-31", # expiry_date (기본 만료일 추가로 컬럼 쉬프트 수정)
            "예" if agreements["agree_personal_info"] else "아니오",  # agree_info
        ]
        
        worksheet.append_row(new_row)
        return True
    
    except Exception as e:
        # 디버깅을 위해 에러 메시지를 출력하거나 로그로 남길 수 있음
        # st.error(f"Sheet Save Error: {e}")
        return False

def validate_all_agreements(agreements):
    """
    모든 필수 동의항목이 선택되었는지 확인
    
    Parameters:
    - agreements: 동의 여부 딕셔너리
    
    Returns:
    - bool: 모든 항목 동의 여부
    """
    return agreements.get("agree_personal_info", False)

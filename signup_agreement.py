"""?뚯썝媛???숈쓽??諛?媛쒖씤?뺣낫 愿由?紐⑤뱢"""
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

# ?섏쭛?섎뒗 媛쒖씤?뺣낫 ??ぉ
PERSONAL_INFO_ITEMS = {
    "?대찓??二쇱냼": "?꾩씠??諛?濡쒓렇???⑸룄",
    "鍮꾨?踰덊샇": "怨꾩젙 蹂댁븞 諛?蹂몄씤?뺤씤 ?⑸룄",
}

PERSONAL_INFO_ITEMS_EN = {
    "Email Address": "For ID and login credentials",
    "Password": "For account security and identity verification",
}

# 媛쒖씤?뺣낫 ?섏쭛 諛??댁슜 ?숈쓽 ?덈궡
PERSONAL_INFO_AGREEMENT = """
=== 媛쒖씤?뺣낫 ?섏쭛 諛??댁슜 ?숈쓽??===

蹂?AHP 留덉뒪???쒕퉬?ㅼ뿉?쒕뒗 ?ㅼ쓬怨?媛숈? 媛쒖씤?뺣낫瑜??섏쭛쨌?댁슜?섍퀬 ?덉뒿?덈떎.

???섏쭛?섎뒗 媛쒖씤?뺣낫 ??- ?대찓??二쇱냼
- 鍮꾨?踰덊샇
- ?쒕퉬???댁슜 沅뚰븳 ?뺣낫 (?꾩떆/?뺤떇 ?ъ슜??援щ텇)
- ?묒냽 湲곌컙 諛??쒓컙
- 湲곌린 ?뺣낫

??媛쒖씤?뺣낫 ?댁슜紐⑹쟻 ??1. ?쒕퉬???쒓났
   - ?뚯썝 ?몄쬆 諛?濡쒓렇??泥섎━
   - ?쒕퉬???댁슜 ?꾪솴 愿由?   - ?ъ슜??臾몄쓽 諛?怨좉컼 吏??
2. ?듦퀎 諛?遺꾩꽍
   - ?쒕퉬???댁슜 ?듦퀎 ?섏쭛
   - ?ъ슜??遺꾩꽍 諛??쒕퉬??媛쒖꽑
   - ?명솚???뚯뒪??
??媛쒖씤?뺣낫 蹂댁쑀 諛??댁슜 湲곌컙 ??- ?뚯썝 ?덊눜 ?쒓퉴吏
- 踰뺤쟻 ?섎Т 蹂댁쑀 湲곌컙: 3??(?듭떊鍮꾨?蹂댄샇踰?

??媛쒖씤?뺣낫 蹂댁븞 ??- ?뷀샇?붾? ?듯븳 ?덉쟾???곗씠?????- ?뺢린?곸씤 蹂댁븞 ?먭?
- ?묎렐 沅뚰븳 ?쒗븳

???댁슜???숈쓽?섏떗?덇퉴?
"""

PERSONAL_INFO_AGREEMENT_EN = """
=== Privacy Policy & Consent Agreement ===

This AHP Master service collects and uses the following personal information:

??Personal Information Collected ??- Email Address
- Password
- Service authorization type (Temporary/Official User)
- Access duration and timestamps
- Device specifications

??Purpose of Collection & Use ??1. Service Provision
   - User authentication and login management
   - Usage record management
   - Customer support and inquiry response

2. Statistical Analysis
   - Collection of usage metrics
   - Service improvement analytics
   - Compatibility testing

??Retention & Usage Period ??- Until account deletion/withdrawal
- Legal retention obligation: 3 years (Telecommunications Privacy Act)

??Data Security ??- Secure storage with strong encryption
- Periodic security inspections
- Restricted access control

Do you agree to the above terms?
"""

def show_agreement_ui():
    """
    ?뚯썝媛????媛쒖씤?뺣낫 ?섏쭛 諛??댁슜 ?숈쓽??UI ?쒖떆
    """
    lang = st.session_state.get('lang', 'ko')
    
    # 怨듯넻 CSS 二쇱엯?쇰줈 ?ъ씠?쒕컮 以꾧컙寃?諛?留덉쭊 異뺤냼
    st.markdown(
        """
        <style>
        /* ?ъ씠?쒕컮 ?꾩젽??媛꾩쓽 ?몃줈 怨듬갚 以꾩씠湲?*/
        [data-testid="stSidebar"] [data-testid="stVerticalBlock"] {
            gap: 0.55rem !important;
        }
        /* ?낅젰 李??쇰꺼 留덉쭊 議곗젅 */
        [data-testid="stSidebar"] label[data-testid="stWidgetLabel"] {
            margin-bottom: 2px !important;
            font-size: 0.85rem !important;
        }
        /* ?쇰뵒??踰꾪듉 ??ぉ 媛꾩쓽 媛꾧꺽 異뺤냼 */
        [data-testid="stSidebar"] div[role="radiogroup"] {
            gap: 0.3rem !important;
        }
        /* 泥댄겕諛뺤뒪 留덉쭊 議곗젅 */
        [data-testid="stSidebar"] div[data-testid="stCheckbox"] {
            margin-top: -2px !important;
            margin-bottom: 2px !important;
        }
        /* 由ъ뒪???ㅽ????щ갚 以꾩씠湲?*/
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
            st.markdown(f"<div class='compact-list'>??<b>{item}</b>: {purpose}</div>", unsafe_allow_html=True)
            
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
            "??I agree to the collection and use of personal information",
            key="agree_personal_info"
        )
    else:
        st.markdown(
            """
            <div style='margin-bottom: 1px;'>
                <span style='font-size: 0.95rem; font-weight: bold; color: #0f172a;'> 媛쒖씤?뺣낫 ?섏쭛 諛??댁슜 ?덈궡</span>
            </div>
            """,
            unsafe_allow_html=True
        )
        for item, purpose in PERSONAL_INFO_ITEMS.items():
            st.markdown(f"<div class='compact-list'>??<b>{item}</b>: {purpose}</div>", unsafe_allow_html=True)
            
        st.markdown(
            """
            <div style='margin-top: 5px; margin-bottom: 1px;'>
                <span style='font-size: 0.95rem; font-weight: bold; color: #0f172a;'> 媛쒖씤?뺣낫 ?섏쭛 諛??댁슜 ?숈쓽??/span>
            </div>
            """,
            unsafe_allow_html=True
        )
        with st.expander("?숈쓽???꾨Ц 蹂닿린", expanded=False):
            st.text(PERSONAL_INFO_AGREEMENT)
            
        agree_personal_info = st.checkbox(
            "??媛쒖씤?뺣낫 ?섏쭛쨌?댁슜???숈쓽?⑸땲??,
            key="agree_personal_info"
        )
        
    return {
        "agree_personal_info": agree_personal_info
    }

def fix_base64_padding(data):
    """
    Base64 臾몄옄?댁쓽 ?⑤뵫(Incorrect padding) ?ㅻ쪟瑜??섏젙?섎뒗 ?⑥닔
    """
    if isinstance(data, str):
        data = "".join(data.split())
        missing_padding = len(data) % 4
        if missing_padding:
            data += '=' * (4 - missing_padding)
    return data

def save_agreement_to_sheets(email, password, agreements, user_type):
    """
    ?뚯썝媛???숈쓽 ?댁슜??湲곗〈 Google Sheets(AHPkr_Users???쒗듃1)??湲곕줉
    
    Parameters:
    - email: ?ъ슜???대찓??    - password: ?ъ슜??鍮꾨?踰덊샇
    - agreements: ?숈쓽 ?щ? ?뺤뀛?덈━
    - user_type: ?ъ슜???좏삎 (?꾩떆/?뺤떇)
    
    Returns:
    - bool: ????깃났 ?щ?
    """
    try:
        # [?섏젙] 硫붿씤 肄붾뱶? ?숈씪???몄쬆 濡쒖쭅 ?곸슜 (String/Dict ?명솚 諛??⑤뵫 蹂댁젙)
        scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        raw_auth = st.secrets.get("gcp_service_account")
        if not raw_auth:
            return False

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
        
        # [?섏젙] secrets?먯꽌 ?쒗듃 ID 媛?몄삤湲?        spreadsheet_id = st.secrets.get("SPREADSHEET_ID")
        if not spreadsheet_id:
            return False
        sh = client.open_by_key(spreadsheet_id)
        try:
            worksheet = sh.worksheet('Registered_Users')
        except:
            worksheet = sh.worksheet('시트1')  # 泥?踰덉㎏ ?쒗듃 ?ъ슜 ('?쒗듃1'怨??숈씪)
        
        # [?섏젙] ??쒕?援??쒓컙(KST) 湲곗? ??꾩뒪?ы봽 ?앹꽦
        kst_now = datetime.now(timezone(timedelta(hours=9)))
        timestamp = kst_now.strftime("%Y-%m-%d %H:%M:%S")
        
        hashed_password = hash_password(password)
        new_row = [
            email,  # user_id
            user_type,  # role (?꾩떆/?뺤떇)
            timestamp,  # signup_date
            hashed_password,  # password (?뷀샇?뷀븯?????
            "9999-12-31", # expiry_date (湲곕낯 留뚮즺??異붽?濡?而щ읆 ?ы봽???섏젙)
            "?? if agreements["agree_personal_info"] else "?꾨땲??,  # agree_info
        ]
        
        worksheet.append_row(new_row)
        return True
    
    except Exception as e:
        # ?붾쾭源낆쓣 ?꾪빐 ?먮윭 硫붿떆吏瑜?異쒕젰?섍굅??濡쒓렇濡??④만 ???덉쓬
        # st.error(f"Sheet Save Error: {e}")
        return False

def validate_all_agreements(agreements):
    """
    紐⑤뱺 ?꾩닔 ?숈쓽??ぉ???좏깮?섏뿀?붿? ?뺤씤
    
    Parameters:
    - agreements: ?숈쓽 ?щ? ?뺤뀛?덈━
    
    Returns:
    - bool: 紐⑤뱺 ??ぉ ?숈쓽 ?щ?
    """
    return agreements.get("agree_personal_info", False)


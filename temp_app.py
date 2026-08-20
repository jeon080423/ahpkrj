import streamlit as st
import survey_manager
import survey_manager_v3
# Force rebuild 2026-01-24 v3 (Merged Sync & Restore)
# Force deploy 2026-02-07
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import io
import sqlite3
import datetime
import re
import smtplib
import json
import platform
import os
import hashlib
import random
import string

def hash_password(password: str) -> str:
    """SHA-256 Hash a password with a fixed salt for security."""
    salt = "ahp_master_secure_salt_2026"
    return hashlib.sha256((password + salt).encode('utf-8')).hexdigest()

def generate_temp_password() -> str:
    """ê°€????ë¹„ë?ë²ˆí˜¸ ? íš¨??ê²€?¬ë? ?µê³¼?˜ëŠ” 8?ë¦¬ ?„ì‹œ ë¹„ë?ë²ˆí˜¸ë¥??ì„±?©ë‹ˆ??"""
    chars = string.ascii_letters + string.digits
    specials = "!@#$%^&*"
    # ìµœì†Œ 1ê°??ë¬¸?? 1ê°??«ì, 1ê°??¹ìˆ˜ë¬¸ìë¥??¬í•¨?˜ë„ë¡?êµ¬ì„±
    temp = [
        random.choice(string.ascii_lowercase),
        random.choice(string.ascii_uppercase),
        random.choice(string.digits),
        random.choice(specials)
    ]
    # ?˜ë¨¸ì§€ 4?ë¦¬???ë¬¸/?«ì ì¤?ë¬´ì‘??? íƒ
    temp += [random.choice(chars) for _ in range(4)]
    random.shuffle(temp)
    return "".join(temp)
import matplotlib.font_manager as fm
from matplotlib import rc
from email.mime.text import MIMEText
from scipy.stats import gmean, ttest_rel, f_oneway
from PIL import Image
import itertools
from math import pi
from dateutil.relativedelta import relativedelta

# [?„ìˆ˜] plotly ?¼ì´ë¸ŒëŸ¬ë¦?(requirements.txt??plotly ì¶”ê? ?„ìš”)
import plotly.express as px
import plotly.graph_objects as go
from scipy import stats
import gspread
from google.oauth2.service_account import Credentials
from signup_agreement import show_agreement_ui, save_agreement_to_sheets, validate_all_agreements

# 1. ì¶”ê??´ì•¼ ???¼ì´ë¸ŒëŸ¬ë¦?(ê¸°ì¡´ Credentials ë°”ë¡œ ?„ë˜ ì¶”ê?)
from streamlit_javascript import st_javascript
import base64

# IP ?„ì¹˜ ì¶”ì  ë°?ê³µì¸ IP ì¶”ì¶œ???„í•œ ?¼ì´ë¸ŒëŸ¬ë¦?ì¶”ê?
import requests

# ANOVA ë°??¬í›„ê²€?•ì„ ?„í•œ ?¼ì´ë¸ŒëŸ¬ë¦?(?†ì„ ê²½ìš° ?ˆì™¸ì²˜ë¦¬)
try:
    from statsmodels.stats.multicomp import pairwise_tukeyhsd
    STATSMODELS_AVAILABLE = True
except ImportError:
    STATSMODELS_AVAILABLE = False


# -----------------------------------------------------------------------------
# ?¤êµ­??English/Korean) ë²ˆì—­ ?¬í¼ ?¨ìˆ˜
# -----------------------------------------------------------------------------
if 'lang' not in st.session_state:
    st.session_state.lang = 'ko'

def _(ko_text, en_text):
    if st.session_state.get('lang', 'ko') == 'en':
        return en_text
    return ko_text

DEFAULT_SURVEY_DESC_KO = """[ì¡°ì‚¬ ëª©ì  ë°??ˆë‚´ë¬?

?ˆë…•?˜ì‹­?ˆê¹Œ?
ë³??¤ë¬¸ì¡°ì‚¬??[?°êµ¬/?„ë¡œ?íŠ¸ ì£¼ì œ]??ê´€??ì£¼ìš” ?”ì¸?¤ì˜ ?ë???ì¤‘ìš”?„ë? ?„ì¶œ?˜ê¸° ?„í•´ ?„ë¬¸ê°€(?ëŠ” ?¤ë¬´?? ?¬ëŸ¬ë¶„ì˜ ê³ ê²¬???˜ë ´?˜ê³ ??ë§ˆë ¨?˜ì—ˆ?µë‹ˆ?? 
ë°”ì˜?œë”?¼ë„ ? ì‹œ ?œê°„???´ì–´ ê·€?˜ì˜ ê·€ì¤‘í•œ ?˜ê²¬???‘ë‹µ??ì£¼ì‹œë©??°êµ¬?????„ì?????ê²ƒì…?ˆë‹¤.

??ì¡°ì‚¬ ëª©ì  : [?°êµ¬/?„ë¡œ?íŠ¸ ëª©ì  ê¸°ì¬]
??ì¡°ì‚¬ ?´ìš© : [ì¡°ì‚¬ ?€???”ì¸] ê°„ì˜ AHP(?ë?ë¹„êµ) ?‰ê?
??ì¡°ì‚¬ ê¸°ê°„ : 202X??X??X??~ 202X??X??X??
??ê°œì¸?•ë³´ ë³´í˜¸ : 
ë³?ì¡°ì‚¬ë¥??µí•´ ?˜ì§‘??ëª¨ë“  ?ë£Œ???µê³„ë²???3ì¡?ë¹„ë???ë³´í˜¸)???˜ê±°?˜ì—¬ ì² ì???ë³´í˜¸?˜ë©°, ?¤ì§ ?°êµ¬ ë°??µê³„ ë¶„ì„ ëª©ì ?¼ë¡œë§??œìš©?©ë‹ˆ?? ?‘ë‹µ?´ì£¼??ê°œì¸ ?•ë³´ ë°?ê°œë³„ ?‘ë‹µ ê²°ê³¼???ˆë? ?¸ë?ë¡?? ì¶œ?˜ì? ?ŠìŒ???½ì†?œë¦½?ˆë‹¤.

ê·€?˜ì˜ ?Œì¤‘??ì°¸ì—¬??ê¹Šì? ê°ì‚¬ë¥??œë¦½?ˆë‹¤.

- ?°êµ¬ ì±…ì„??: [?´ë¦„ ê¸°ì¬]
- ë¬¸ì˜ì²?: [?°ë½ì²??ëŠ” ?´ë©”??ê¸°ì¬]"""

DEFAULT_SURVEY_DESC_EN = """[Survey Purpose & Instructions]

Greetings,
This survey is designed to collect the valuable opinions of experts (or practitioners) to derive the relative importance of key factors regarding [Research/Project Topic].
Your participation will be of great help to our research, and we would deeply appreciate it if you could take a moment out of your busy schedule to respond.

??Purpose : [Enter Research/Project Purpose]
??Content : AHP (Pairwise Comparison) evaluation among [Target Factors]
??Period : 202X-XX-XX ~ 202X-XX-XX
??Privacy Policy : 
All data collected through this survey will be strictly protected in accordance with privacy laws and used solely for research and statistical analysis purposes. We promise that your personal information and individual responses will never be leaked externally.

Thank you very much for your valuable participation.

- Lead Researcher : [Enter Name]
- Contact : [Enter Phone or Email]"""

# Default definition mappings for auto-translation to English when survey is loaded in English mode
DEFAULT_TRANSLATED_DEFS = {
    DEFAULT_SURVEY_DESC_KO: DEFAULT_SURVEY_DESC_EN,
    "?œì¡°???‘ë™ë¡œë´‡ ?„ì… ?”ì¸ ì¤‘ìš”??ë¶„ì„???„í•œ ?„ë¬¸ê°€ AHP ?¤ë¬¸": "Expert AHP Survey on the Importance of Factors for Adopting Manufacturing Collaborative Robots",
    "?‘ë™ë¡œë´‡ ?„ì… ??ê¸°ìˆ ???±ëŠ¥, ?¸í™˜?? ?ˆì „??ë°?ê¸°ìˆ  ì§€????ê¸°ìˆ  ì¸¡ë©´???”ì¸": "Factors related to the technological aspect such as technical performance, compatibility, safety, and technical support.",
    "?‘ë™ë¡œë´‡ ?„ì…ê³?ê´€?¨ëœ ì¡°ì§ ?´ë?????Ÿ‰, ê²½ì˜ì§?ì§€?? ?¬ë¬´ ë°?êµìœ¡ ?íƒœ ?”ì¸": "Factors related to the internal capabilities of the organization, top management support, financial and training status.",
    "?•ë? ì§€?? ?°ì—… ??ê²½ìŸ ?•ë ¥, êµ¬ì¸??ë°??¸ë? ?‘ë ¥ ???¸ë? ?˜ê²½???”ì¸": "External environmental factors such as government support, competitive pressure within the industry, labor shortage, and external cooperation.",
    "ê²½ì˜ì§„ì˜ ?ì‹  ì§€?¥ì„±, êµ¬ì„±?ì˜ ë³€???˜ìš©??ë°??¤ë§ˆ???©í† ë¦?ì§€??ê¸°ìˆ  ?˜ì? ?”ì¸": "Factors such as the management's innovation orientation, members' acceptance of change, and smart factory knowledge/skill levels.",
    "?„ì…?€???‘ë™ë¡œë´‡ê°„ì˜ ?ë????´ì ": "Relative advantage among the collaborative robots targeted for adoption.",
    "ê¸°ì¡´ ?¤ë¹„???€???‘ë™ë¡œë´‡ê³¼ì˜ ?°ê²°??: "Connectivity with existing equipment or third-party collaborative robots.",
    "?‘ì—…?ì? ê°™ì? ê³µê°„?ì„œ ?ˆì „ ?œìŠ¤ ?†ì´ ?‘ì—…???Œì˜ ?¸ì  ?¬ê³  ?ˆë°© ?˜ì?": "Level of human accident prevention when working in the same space as operators without safety fences.",
    "ê³µê¸‰?¬ì˜ ê¸°ìˆ  ë°?A/S ì§€???•ë„": "Degree of technical and A/S support from the supplier.",
    "ê²½ì˜ì§„ì˜ ?„ì… ?˜ì? ë°?ê²½ì˜ì² í•™ ë°˜ì˜??: "The management's willingness to adopt and the degree to which management philosophy is reflected.",
    "ì¡°ì§?ì˜ ë¡œë´‡ ?œìš© ê¸°ìˆ  ì¤€ë¹??˜ì?": "The level of technical readiness of organizational members to utilize robots.",
    "ë¡œë´‡ êµ¬ì…???„í•œ ?ë³¸ ?¬ë ¥ ë°??ê¸ˆ ì¡°ë‹¬ ?¸ì˜??: "Capital capacity and financing convenience for purchasing robots.",
    "ê¸°ìˆ  ?¥ìƒ???„í•œ ?„íƒ/?¬ë‚´ êµìœ¡ ?„ë¡œê·¸ë¨ ? ë¬´": "Availability of external/internal training programs for skill improvement.",
    "?‘ë™ë¡œë´‡ ?„ì…???œì„±?”í•˜ê¸??„í•œ ?•ë????¬ì • ì§€??ë°?ë³´ì¡°ê¸??œíƒ ?•ë„": "Degree of government financial support and subsidy benefits to promote the adoption of collaborative robots.",
    "?™ì¢… ?…ê³„ ?ëŠ” ê²½ìŸ?¬ì˜ ?‘ë™ë¡œë´‡ ?„ì…???°ë¥¸ ê²½ìŸ???•ë°• ?•ë„": "Degree of competitive pressure due to the adoption of collaborative robots by peers or competitors.",
    "?œì¡° ?„ì¥??êµ¬ì¸??ë°??ì‚° ?¸ë ¥ ?˜ê¸‰???´ë ¤?€ ?˜ì?": "Level of difficulty in finding labor and supplying production personnel at the manufacturing site.",
    "ë¡œë´‡ ê³µê¸‰???¸ì˜ ?¸ë? ì»¨ì„¤?? ?°êµ¬ê¸°ê? ?±ì˜ ê¸°ìˆ ??êµìœ¡??ì§€??: "Technical/educational support from external consulting, research institutes, etc., other than the robot supplier.",
    "ìµœê³ ê²½ì˜?ì˜ ?ê·¹?ì¸ ?˜ì?": "The top management's active willingness to adopt new manufacturing technologies and robots.",
    "?ˆë¡œ???œì¡° ê¸°ìˆ  ë°?ë¡œë´‡ ?„ì…???€??ìµœê³ ê²½ì˜?ì˜ ?ê·¹?ì¸ ?˜ì?": "The top management's active willingness to adopt new manufacturing technologies and robots.",
    "? ê·œ ?¥ë¹„ ë°??‘ì—… ?„ë¡œ?¸ìŠ¤ ë³€?”ì— ?€??êµ¬ì„±?ë“¤???˜ìš© ë°??‘ì¡° ?œë„": "Members' acceptance and cooperative attitude towards changes in new equipment and work processes.",
    "ê³µì¥ ???”ì??¸í™”, ?•ë³´?œìŠ¤??MES ?? ë°??ë™??ê¸°ìˆ ???„ì¬ êµ¬ì¶• ?˜ì?": "Current level of implementation of digitalization, information systems (MES, etc.), and automation technology in the factory.",
    "?‘ë™ë¡œë´‡ ?œìš© ë°?? ì? ê´€ë¦¬ì— ?„ìš”??ì¡°ì§ ???„ë¬¸ ì§€???˜ì?": "Level of internal expertise required for the utilization and maintenance of collaborative robots.",
    "ê¸°ëŠ¥??: "Functionality",
    "?”ì??: "Design",
    "ê²½ì œ??: "Economy",
    "?˜ë“œ?¨ì–´": "Hardware",
    "?Œí”„?¸ì›¨??: "Software",
    "?¸ê?": "Appearance",
    "?¸ì˜??: "Usability",
    "?¨ë§ê¸°ê?ê²?: "Device Price",
    "? ì?ë¹„ìš©": "Maintenance Cost",
    "ê¸°ìˆ  ?”ì¸": "Technological",
    "ì¡°ì§ ?”ì¸": "Organizational",
    "?˜ê²½ ?”ì¸": "Environmental",
    "?ì‹  ?”ì¸": "Innovational",
    "?ë??ì´??: "Relative Advantage",
    "?¸í™˜??: "Compatibility",
    "?ˆì „??: "Security",
    "?œë¹„?¤ì???: "Service Support",
    "ê²½ì˜ì§„ì???: "Top Management Support",
    "ê¸°ìˆ ì¤€ë¹„ë„": "Tech Readiness",
    "ê¸ˆìœµ?ì›": "Financial Resources",
    "êµìœ¡?ˆë ¨": "Training",
    "?•ë?ì§€??: "Gov Support",
    "ê²½ìŸ?•ë ¥": "Competitive Pressure",
    "?¸ë ¥??: "Labor Shortage",
    "?¸ë?ì§€??: "External Support",
    "ê²½ì˜ì§„ì˜ ?ì‹ ??: "Management Innovativeness",
    "ë³€?”ìˆ˜?©íƒœ??: "Change Acceptance",
    "?¤ë§ˆ?¸íŒ©? ë¦¬?˜ì?": "Smart Factory Level",
    "ì§€?ì •??: "Knowledge Level"
}

def translate_definition_if_default(factor_name, def_text):
    if st.session_state.get('lang', 'ko') != 'en' or not def_text:
        return def_text
    
    import re
    # Clean up whitespace
    clean_def = re.sub(r'\s+', ' ', def_text).strip()
    
    # 1. Direct match in dictionary
    if clean_def in DEFAULT_TRANSLATED_DEFS:
        return DEFAULT_TRANSLATED_DEFS[clean_def]
        
    # Translate the factor_name in pattern matching to match Korean if it's saved in Korean
    trans_factor = DEFAULT_TRANSLATED_DEFS.get(factor_name, factor_name)
    
    # 2. Pattern matches for "{factor}???€???•ì˜?…ë‹ˆ??" or "{factor}???€???•ì˜ ?…ë‹ˆ??"
    pattern1 = rf"^(?:{re.escape(factor_name)}|{re.escape(trans_factor)})\s*??s*?€??s*?•ì˜\s*?…ë‹ˆ??.?$"
    if re.match(pattern1, clean_def):
        return f"Definition for {trans_factor}."
        
    pattern2 = rf"^(?:{re.escape(factor_name)}|{re.escape(trans_factor)})\s*??s*?€??s*?„ë°˜??s*?”ì†Œë¥?s*?¤ëª…?©ë‹ˆ??.?$"
    if re.match(pattern2, clean_def):
        return f"Overall description for {trans_factor}."
        
    return def_text

def translate_factor_if_default(factor_name):
    if st.session_state.get('lang', 'ko') != 'en' or not factor_name:
        return factor_name
    return DEFAULT_TRANSLATED_DEFS.get(factor_name, factor_name)

# =============================================================================
# 0. ?œìŠ¤???¤ì • ë°?? í‹¸ë¦¬í‹°
# =============================================================================

# [?˜ì •] Base64 ë¬¸ì?´ì˜ ?¨ë”© ë°??•ì œë¥??„í•œ ? í‹¸ë¦¬í‹° ?¨ìˆ˜ ê°•í™”
def fix_base64_padding(data):
    """
    Base64 ë¬¸ì?´ì˜ ?¨ë”©(Incorrect padding) ?¤ë¥˜ë¥??˜ì •?˜ëŠ” ?¨ìˆ˜
    """
    if isinstance(data, str):
        # 1. ëª¨ë“  ê³µë°± ë°?ì¤„ë°”ê¿?ë¬¸ì ?œê±° (ê°€??ì¤‘ìš”???˜ì •)
        data = re.sub(r'\s+', '', data)
        
        # 2. ?¨ë”©(=) ê³„ì‚° ë°?ì¶”ê?
        missing_padding = len(data) % 4
        if missing_padding:
            data += '=' * (4 - missing_padding)
    return data

# [?˜ì • ë°˜ì˜] 1) SEO ?œê·¸ ?½ì…, 2) ?œë¹„??ëª?ë³€ê²?AHP ë§ˆìŠ¤??, 4) ?Œë¹„ì½??¤ì •
try:
    logo_path = "ahp_master_logo.png"
    if os.path.exists(logo_path):
        logo_img = Image.open(logo_path)
    else:
        logo_img = "?“Š"
    
    st.set_page_config(
        page_title=_("AHP ë§ˆìŠ¤??| ?¼ë°˜ ë°??¼ì? AHP ?˜ì‚¬ê²°ì • ë¶„ì„ ?œìŠ¤??, "AHP Master | Traditional & Fuzzy AHP Decision Analysis System"), 
        layout="wide", 
        page_icon=logo_img,
        menu_items={
            'Get Help': None,
            'Report a bug': None,
            'About': _("AHP ë§ˆìŠ¤??- ?¤ë§ˆ???¼ë°˜ ë°??¼ì? AHP ?˜ì‚¬ê²°ì • ë¶„ì„ ?œìŠ¤??, "AHP Master - Smart Traditional & Fuzzy AHP Decision Analysis System")
        }
    )
except Exception:
    st.set_page_config(page_title=_("AHP ë§ˆìŠ¤??| ?¼ì? AHP ì§€??, "AHP Master | Fuzzy AHP Support"), layout="wide", page_icon="?“Š")

# [?˜ì • ë°˜ì˜] ë©”í? ì½”ë“œê°€ ?”ë©´???¸ì¶œ?˜ì? ?Šë„ë¡?display:none ?¤í??¼ì„ ì¶”ê???SEO ?œê·¸ (?í•œ ?µí•© ê²€??ìµœì ??
# [ì¶”ê?] ?¤ì´ë²??œì¹˜?´ë“œë°”ì´?€ ë°?ê²€???”ì§„ ?¬ë¡¤???˜ì§‘???„í•´ ë©”í? ?œê·¸, canonical, JSON-LD êµ¬ì¡°???°ì´?°ë? ?¤ì œ ?¤ë“œ(Parent Head)???™ì ?¼ë¡œ ?½ì…?˜ëŠ” 1x1 ?´ë?ì§€ ë¡œë” ?¤í¬ë¦½íŠ¸ ?‘ì¬
seo_tags = """<div style="display:none;">
<title>AHP Master | Traditional & Fuzzy AHP Decision Analysis System (AHP ë§ˆìŠ¤?? å±‚æ¬¡?†æë²? ?å±¤?†ææ³? Proceso de AnÃ¡lisis JerÃ¡rquico)</title>
<!-- Multilingual Description -->
<meta name="description" content="AHP Master - Professional Analytic Hierarchy Process (AHP) & Fuzzy AHP automation software tool for thesis, academic papers, and research. Supports Consistency Ratio (CR) calibration, group geometric mean calculation, ANOVA testing. ?™ìœ„?¼ë¬¸ ë°??°êµ¬??AHP/?¼ì? AHP ë¶„ì„ ?”ë£¨?? ä¸“ä¸šå±‚æ¬¡?†ææ³?AHP)?Šæ¨¡ç³Šå±‚æ¬¡åˆ†?æ³•?¨çº¿è½?»¶ä¸è?ç®—å™¨?‚éšå±¤åˆ†?æ³•(AHP)?„ãƒ¼?«ã€‚Software del Proceso de AnÃ¡lisis JerÃ¡rquico (AHP). Processus d'Analyse HiÃ©rarchique. Analytischer Hierarchieprozess. QuÃ¡ trÃ¬nh PhÃ¢n tÃ­ch PhÃ¢n cáº¥p. à¤µà¤¿à¤¶à¥à¤²à¥‡à¤·à¤£à¤¾à¤¤à¥à¤®à¤?à¤ªà¤¦à¤¾à¤¨à¥à¤•à¥à¤°à¤?à¤ªà¥à¤°à¤•à¥à¤°à¤¿à¤¯à¤? Analitiese HiÃ«rargieproses. ?Ğµ?Ğ¾Ğ´ Ğ°Ğ½Ğ°Ğ»Ğ¸Ğ·Ğ° Ğ¸Ğµ?Ğ°??Ğ¸Ğ¹." />
<!-- Multilingual Keywords -->
<meta name="keywords" content="AHP, Fuzzy AHP, AHP calculator, Fuzzy AHP calculator, Analytic Hierarchy Process software, Consistency Ratio, CR calibration, AHP group consensus, AHP software for thesis, AHP excel template, AHP ë§ˆìŠ¤?? AHP ?¼ë¬¸ ë¶„ì„, AHP ?¼ê???ë¹„ìœ¨ ë³´ì •, AHP ê°€ì¤‘ì¹˜ ê³„ì‚°, ?™ìœ„?¼ë¬¸ AHP ?µê³„, å±‚æ¬¡?†ææ³? æ¨¡ç³Šå±‚æ¬¡?†ææ³? å±‚æ¬¡?†æë²•è?ç®—å™¨, å±‚æ¬¡?†æë²•è½¯ä»? è®ºæ–‡AHP?†æ, ä¸€?´æ€§æ¯”ä¾? ?å±¤?†ææ³? ?•ã‚¡?¸ã‚£AHP, AHP?½ãƒ•?ˆã‚¦?§ã‚¢, AHP?„ãƒ¼?? Proceso de AnÃ¡lisis JerÃ¡rquico, AHP Difuso, Software AHP, Calculadora AHP, Processus d'Analyse HiÃ©rarchique, AHP Flou, Logiciel AHP, QuÃ¡ trÃ¬nh PhÃ¢n tÃ­ch PhÃ¢n cáº¥p, AHP má»? Pháº§n má»m AHP, Analytischer Hierarchieprozess, AHP-Software, AHP Rechner, à¤µà¤¿à¤¶à¥à¤²à¥‡à¤·à¤£à¤¾à¤¤à¥à¤®à¤?à¤ªà¤¦à¤¾à¤¨à¥à¤•à¥à¤°à¤?à¤ªà¥à¤°à¤•à¥à¤°à¤¿à¤¯à¤? à¤«à¤¼à¤œà¤¼à¥€ AHP, AHP SOFTWARE, Analitiese HiÃ«rargieproses, Vae AHP, AHP-sagteware, ?Ğµ?Ğ¾Ğ´ Ğ°Ğ½Ğ°Ğ»Ğ¸Ğ·Ğ° Ğ¸Ğµ?Ğ°??Ğ¸Ğ¹, ?Ğµ?Ğµ?ĞºĞ¸Ğ¹ AHP, ??Ğ¾Ğ³?Ğ°Ğ¼Ğ¼Ğ½Ğ¾Ğµ Ğ¾Ğ±Ğµ?Ğ¿Ğµ?ĞµĞ½Ğ¸Ğµ AHP, Ø¹???Ø© Ø§?ØªØ­??? Ø§??Ø±??, Ø¹???Ø© Ø§?ØªØ­??? Ø§??Ø±?? Ø§?Ø¶Ø¨Ø§Ø¨?, Ø¨Ø±?Ø§?Ø¬ AHP" />
<meta name="author" content="AHP Master" />
<meta name="robots" content="index, follow" />
<meta name="google-site-verification" content="KbMsp4y15le5XNyK05UEr6Nq6" />
<meta name="naver-site-verification" content="f0561d996c39ca52dcc47cf2aad128c5e586a1d6" />
<!-- Open Graph Tags -->
<meta property="og:title" content="AHP Master - Global AHP & Fuzzy AHP Analysis Software (å±‚æ¬¡?†æë²? ?å±¤?†ææ³?" />
<meta property="og:description" content="Advanced AHP & Fuzzy AHP decision software with mathematical consistency ratio (CR) calibration, group consensus, and statistical comparison for global researchers." />
<meta property="og:type" content="website" />
<meta property="og:url" content="https://ahpkrj.streamlit.app/" />
<!-- Hidden content for deep indexing -->
<h1>AHP Master - Analytic Hierarchy Process & Fuzzy AHP Calculator</h1>
<p>AHP Master is a powerful online software for Traditional AHP and Fuzzy AHP analysis. Perfect for academic thesis, research papers, and corporate decision making. Features automatic consistency ratio (CR) improvement and Excel exports.</p>
<h2>å±‚æ¬¡?†æë²?(AHP) & æ¨¡ç³Šå±‚æ¬¡?†ææ³??¨çº¿è®¡ç®—?¨ê³¼ ?Œí”„?¸ì›¨??/h2>
<p>ä¸“ä¸ºå­?œ¯è®ºæ–‡?€ ?°êµ¬ë¥??„í•´ ?¤ê³„??ê³„ì¸µë¶„ì„ê³¼ì •(AHP) ?ë™??ë¶„ì„ ?„êµ¬?…ë‹ˆ?? ?¼ê???ë¹„ìœ¨(CR) ?ë™ ë³´ì •, ê·¸ë£¹ ê¸°í•˜?‰ê·  ê³„ì‚°, ANOVA ë¶„ì„ ë°??‘ì? ë³´ê³ ???´ë³´?´ê¸°ë¥?ì§€?í•©?ˆë‹¤.</p>
<h2>?å±¤?†æë²?(AHP) & ?•ã‚¡?¸ã‚£AHP ?½ãƒ•?ˆã‚¦?§ã‚¢</h2>
<p>è«–æ–‡?„ç ”ç©¶ã®?Ÿã‚??šå±¤åˆ†?ë²•(AHP)?ªå‹•?”íˆ´. ä¸€è²«ì„±æ¯”ç‡(CR)??ì¡°ì •?´ë‚˜ Excel?¬ãƒ?¼ãƒˆ?ºåŠ›?«å?å¿œã€?/p>
<h2>Proceso de AnÃ¡lisis JerÃ¡rquico (AHP) y AHP Difuso</h2>
<p>Software y calculadora en lÃ­nea para el Proceso de AnÃ¡lisis JerÃ¡rquico (AHP). Ideal para tesis y toma de decisiones, con calibraciÃ³n automÃ¡tica de la RelaciÃ³n de Consistencia (CR).</p>
<h2>Processus d'Analyse HiÃ©rarchique (AHP) et AHP Flou</h2>
<p>Logiciel et calculatrice en ligne pour le Processus d'Analyse HiÃ©rarchique (AHP). IdÃ©al pour les thÃ¨ses acadÃ©miques et la prise de dÃ©cision, con calibrage automatique du ratio de cohÃ©rence (CR).</p>
<h2>Analytischer Hierarchieprozess (AHP) und Fuzzy AHP</h2>
<p>AHP-Software und Rechner fÃ¼r akademische Arbeiten und Forschung. UnterstÃ¼tzt automatische Anpassung der Konsistenzrate (CR).</p>
<h2>QuÃ¡ trÃ¬nh PhÃ¢n tÃ­ch PhÃ¢n cáº¥p (AHP) & AHP má»?/h2>
<p>Pháº§n má»m tá»?Ä‘á»™ng hÃ³a phÃ¢n tÃ­ch AHP vÃ  AHP má»?(Fuzzy AHP) chuyÃªn nghiá»‡p dÃ nh for luáº­n vÄƒn vÃ  nghiÃªn cá»©u.</p>
<h2>à¤µà¤¿à¤¶à¥à¤²à¥‡à¤·à¤£à¤¾à¤¤à¥à¤®à¤?à¤ªà¤¦à¤¾à¤¨à¥à¤•à¥à¤°à¤?à¤ªà¥à¤°à¤•à¥à¤°à¤¿à¤¯à¤?(AHP) à¤”à¤° à¤«à¤¼à¤œà¤¼à¥€ AHP</h2>
<p>à¤¶à¥‹à¤?à¤ªà¥à¤°à¤¬à¤‚à¤§, à¤…à¤•à¤¾à¤¦à¤?¤¿à¤?à¤ªà¤¤à¥à¤°à¥‹à¤‚ à¤”à¤° à¤…à¤¨à¥à¤¸à¤‚à¤§à¤¾à¤¨ à¤•à¥‡ à¤²à¤¿à¤?à¤ªà¥‡à¤¶à¥‡à¤µà¤° AHP à¤”à¤° à¤«à¤¼à¤œà¤¼à¥€ AHP à¤¸à¥à¤µà¤šà¤¾à¤²à¤¿à¤¤ à¤¸à¥‰à¤«à¥à¤Ÿà¤µà¥‡à¤¯à¤?à¤Ÿà¥‚à¤²ã€?/p>
<h2>Analitiese HiÃ«rargieproses (AHP) en Vae AHP</h2>
<p>AHP-sagteware instrument vir proefskrifte en navorsing. Ondersteun outomatiese CR kalibrasie en groep geometriese gemiddelde berekening.</p>
<h2>?Ğµ?Ğ¾Ğ´ Ğ°Ğ½Ğ°Ğ»Ğ¸Ğ·Ğ° Ğ¸Ğµ?Ğ°??Ğ¸Ğ¹ (AHP) ë°??Ğµ?Ğµ?ĞºĞ¸Ğ¹ AHP</h2>
<p>??Ğ¾Ğ³?Ğ°Ğ¼Ğ¼Ğ½Ğ¾Ğµ Ğ¾Ğ±Ğµ?Ğ¿Ğµ?ĞµĞ½Ğ¸Ğµ Ğ¸ ĞºĞ°Ğ»?Ğº?Ğ»??Ğ¾? Ğ´Ğ»? Ğ¼Ğµ?Ğ¾Ğ´Ğ° Ğ°Ğ½Ğ°Ğ»Ğ¸Ğ·Ğ° Ğ¸Ğµ?Ğ°??Ğ¸Ğ¹ (AHP). ?Ğ´ĞµĞ°Ğ»?Ğ½Ğ¾ Ğ¿Ğ¾Ğ´?Ğ¾Ğ´Ğ¸? Ğ´Ğ»? Ğ°ĞºĞ°Ğ´ĞµĞ¼Ğ¸?Ğµ?ĞºĞ¸? Ğ´Ğ¸??Ğµ??Ğ°?Ğ¸Ğ¹.</p>
<h2>Ø¹???Ø© Ø§?ØªØ­??? Ø§??Ø±?? (AHP) ? Ø¹???Ø© Ø§?ØªØ­??? Ø§??Ø±?? Ø§?Ø¶Ø¨Ø§Ø¨?</h2>
<p>Ø¨Ø±?Ø§?Ø¬ Ø¢?? ?Ø¹???Ø© Ø§?ØªØ­??? Ø§??Ø±?? (AHP) ??Ø±Ø³Ø§Ø¦? Ø§?Ø£?Ø§Ø¯???Ø© ?Ø§?Ø¨Ø­?Ø«.</p>
<img src="data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7" onload="(function(){const metaTags=[{name:'naver-site-verification',content:'f0561d996c39ca52dcc47cf2aad128c5e586a1d6'},{name:'google-site-verification',content:'KbMsp4y15le5XNyK05UEr6Nq6'},{name:'description',content:'AHP Master - ?™ìœ„?¼ë¬¸ ë°??°êµ¬???¼ë°˜ ë°??¼ì? AHP ?˜ì‚¬ê²°ì • ë¶„ì„ ?œìŠ¤?? ?¼ê???ë¹„ìœ¨(CR) ë³´ì •, ê¸°í•˜?‰ê· , ë¶„ì‚°ë¶„ì„(ANOVA) ì§€??'},{name:'keywords',content:'AHP, Fuzzy AHP, AHP calculator, AHP ë§ˆìŠ¤?? AHP ë¶„ì„, ?¼ê???ë¹„ìœ¨, ê³„ì¸µë¶„ì„ê³¼ì •, ?¼ì? AHP'},{property:'og:title',content:'AHP ë§ˆìŠ¤??| ?¼ë°˜ ë°??¼ì? AHP ?˜ì‚¬ê²°ì • ë¶„ì„ ?œìŠ¤??},{property:'og:description',content:'?™ìœ„?¼ë¬¸ ë°??°êµ¬ë¥??„í•œ ?¤ë§ˆ???¼ë°˜ ë°??¼ì? AHP ë¶„ì„ ?”ë£¨??},{property:'og:type',content:'website'},{property:'og:url',content:'https://ahpkrj.streamlit.app/'}];const jsonLd={'@context':'https://schema.org','@type':'WebApplication','name':'AHP Master','alternateName':'AHP ë§ˆìŠ¤??,'url':'https://ahpkrj.streamlit.app/','applicationCategory':'BusinessApplication','operatingSystem':'All','description':'?™ìœ„?¼ë¬¸ ë°??°êµ¬???¼ë°˜ ë°??¼ì? AHP ?˜ì‚¬ê²°ì • ë¶„ì„ ?œìŠ¤?? ?¼ê???ë¹„ìœ¨(CR) ë³´ì •, ê¸°í•˜?‰ê· , ë¶„ì‚°ë¶„ì„(ANOVA) ì§€??','offers':{'@type':'Offer','price':'0','priceCurrency':'KRW'}};function injectToDoc(doc){if(!doc||!doc.head)return;try{doc.documentElement.setAttribute('lang','ko');}catch(e){}metaTags.forEach(tag=>{const key=tag.name?'name':'property';const val=tag[key];let existing=false;const metas=doc.head.getElementsByTagName('meta');for(let i=0;i<metas.length;i++){if(metas[i].getAttribute(key)===val){existing=true;break;}}if(!existing){const newMeta=doc.createElement('meta');newMeta.setAttribute(key,val);newMeta.setAttribute('content',tag.content);doc.head.appendChild(newMeta);}});let existingCanonical=false;const links=doc.head.getElementsByTagName('link');for(let i=0;i<links.length;i++){if(links[i].getAttribute('rel')==='canonical'){existingCanonical=true;break;}}if(!existingCanonical){const canonicalLink=doc.createElement('link');canonicalLink.setAttribute('rel','canonical');canonicalLink.setAttribute('href','https://ahpkrj.streamlit.app/');doc.head.appendChild(canonicalLink);}let existingJsonLd=false;const scripts=doc.head.getElementsByTagName('script');for(let i=0;i<scripts.length;i++){if(scripts[i].getAttribute('type')==='application/ld+json'){existingJsonLd=true;break;}}if(!existingJsonLd){const script=doc.createElement('script');script.type='application/ld+json';script.text=JSON.stringify(jsonLd);doc.head.appendChild(script);}}try{injectToDoc(document);}catch(e){}try{if(window.parent&&window.parent.document){injectToDoc(window.parent.document);}}catch(e){}})();" style="display:none;"/>
</div>"""
st.markdown(seo_tags, unsafe_allow_html=True)

# =============================================================================
# ?„ì—­ AHP ì²™ë„ CSS ì£¼ì… (ë©”ì¸ ?”ë©´ ë°?ë¯¸ë¦¬ë³´ê¸° ëª¨ë‹¬ ëª¨ë‘??ê°•ì œ ?ìš©)
# =============================================================================
global_ahp_css = """
<style>
/* =============================================================================
   AHP ì²™ë„ ?„ìš© ê³ ìœ  ?´ë˜???€ê²ŸíŒ… (.st-key-ahp_survey_matrix)
   ============================================================================= */

/* 0. ë©”ì¸ ?˜ì§ ì»¨í…Œ?´ë„ˆ(ì¤„ê°„ê²? ì´ˆë?ì°?ë°?ë§ˆì§„ ì¶•ì†Œ */
div.st-key-ahp_survey_matrix {
    gap: 4px !important;
    row-gap: 4px !important;
}

/* 1. ?˜ì§ ?•ë ¬ & ?ˆì´?„ì›ƒ ë°°ë¶„ */
.st-key-ahp_survey_matrix div[data-testid="stHorizontalBlock"] {
    gap: 0px !important;
    align-items: center !important;
    width: 100% !important;
    margin-top: 0px !important;
    margin-bottom: 0px !important;
    padding-top: 2px !important;
    padding-bottom: 2px !important;
    border-bottom: 1px dashed #e2e8f0 !important;
}

.st-key-ahp_survey_matrix div[data-testid="column"] {
    padding: 0px !important;
}

/* 2. ?¼ë””??ê·¸ë£¹ ?„ì²´ 100% ë¶„ë°° ê°•ì œ ë°?ì¤„ë°”ê¿??ì²œ ì°¨ë‹¨ */
.st-key-ahp_survey_matrix div[data-testid="stElementContainer"],
.st-key-ahp_survey_matrix div[data-testid="stRadio"],
.st-key-ahp_survey_matrix .stRadio {
    width: 100% !important;
    margin: 0px !important;
    padding: 0px !important;
}

.st-key-ahp_survey_matrix div[data-testid="stRadio"] > div,
.st-key-ahp_survey_matrix div[role="radiogroup"] {
    display: flex !important;
    flex-direction: row !important;
    flex-wrap: nowrap !important; /* ?µì‹¬: ëª¨ë‹¬?ì„œ???ˆë? ì¤„ë°”ê¿??˜ì? ?ŠìŒ */
    justify-content: space-between !important;
    align-items: center !important;
    width: 100% !important;
    gap: 0px !important;
    padding: 0px !important; 
    margin: 0px !important;
}

/* 2.5. AHP ì»¨í…Œ?´ë„ˆ ?´ë????˜ì§ ?”ì†Œ ê°„ê²© ì´ˆë?ì°?*/
.st-key-ahp_survey_matrix div[data-testid="stVerticalBlock"] {
    gap: 0px !important;
}

/* 3. ê°?ì²™ë„ ?¼ë””??ë²„íŠ¼ 1:1 ?„ë²½ ?•ë ¬ */
/* Streamlit ë²„ì „???°ë¼ option?¤ì„ div(stRadioHorizontalOption)ë¡?ê°ì‹¸??ê²½ìš°?€ direct label??ê²½ìš°ê°€ ?ˆìœ¼ë¯€ë¡?ëª¨ë‘ stretch ?ìš© */
.st-key-ahp_survey_matrix div[role="radiogroup"] > div,
.st-key-ahp_survey_matrix div[role="radiogroup"] > label,
.st-key-ahp_survey_matrix div[data-testid="stRadioHorizontalOption"],
.st-key-ahp_survey_matrix div[role="radiogroup"] label {
    flex: 1 1 0% !important;
    display: flex !important;
    flex-direction: column !important;
    align-items: center !important;
    justify-content: center !important;
    height: 28px !important; /* ?”ì¸ ë°•ìŠ¤?€ ?™ì¼?˜ê²Œ 28pxë¡??•ë ¬ */
    margin: 0px !important;
    padding: 0px !important;
    min-width: 0px !important;
    width: 100% !important;
    border-radius: 4px !important;
    transition: background-color 0.2s ease-in-out !important;
    background-color: transparent !important;
}

/* 3.5. ?¼ë””??ê·¸ë£¹ ìµœì†Œ ?’ì´ ?´ì œ */
.st-key-ahp_survey_matrix div[role="radiogroup"] {
    min-height: 28px !important;
}

/* ê°ì‹¸??divê°€ ?ˆì„ ê²½ìš° ê·??´ë????¤ì œ label??100% ì±„ìš°?„ë¡ ì§€??*/
.st-key-ahp_survey_matrix div[role="radiogroup"] > div label,
.st-key-ahp_survey_matrix div[data-testid="stRadioHorizontalOption"] label {
    width: 100% !important;
    height: 100% !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    margin: 0px !important;
    padding: 0px !important;
}

/* 4. ê¸°ì¡´ ?ìŠ¤??ì°Œêº¼ê¸??„ë²½ ?œê±° */
.st-key-ahp_survey_matrix label[data-testid="stWidgetLabel"],
.st-key-ahp_survey_matrix label p {
    display: none !important;
    height: 0px !important;
    width: 0px !important;
    margin: 0px !important;
    padding: 0px !important;
    opacity: 0 !important;
    overflow: hidden !important;
    position: absolute !important;
}

/* stMarkdownContainer??negative margin ?œê±°?˜ì—¬ ì»¬ëŸ¼ê°??˜ì§ ?‰í–‰ ë§ì¶¤ */
.st-key-ahp_survey_matrix div[data-testid="stMarkdownContainer"] {
    margin-bottom: 0px !important;
    padding-bottom: 0px !important;
}

/* ?¼ë””????ª© ?´ë???markdown ì»¨í…Œ?´ë„ˆ(?ìŠ¤?¸ìš©) ?„ì „??ê°ì¶”ê¸?*/
.st-key-ahp_survey_matrix div[role="radiogroup"] div[data-testid="stMarkdownContainer"] {
    display: none !important;
    height: 0px !important;
    width: 0px !important;
    margin: 0px !important;
    padding: 0px !important;
    opacity: 0 !important;
    overflow: hidden !important;
    position: absolute !important;
}

/* ?™ê·¸?¼ë? ì»¨í…Œ?´ë„ˆ ì¤‘ì•™ ?•ë ¬ ë°??¬ë°± ë§ˆì§„ ?œê±° */
.st-key-ahp_survey_matrix label span {
    margin: 0px !important;
    padding: 0px !important;
}

/* 5. Hover ë°?Zebra ?¨ê³¼ */
.st-key-ahp_survey_matrix label:hover {
    background-color: #e2e8f0 !important;
    cursor: pointer !important;
}



/* 6. ëª¨ë°”??ê°€ë¡??¤í¬ë¡??ˆìš© ë°?ë¶•ê´´ ë°©ì? */
@media (max-width: 768px) {
    .stApp > header + div, 
    .block-container,
    div[data-testid="stDialog"] {
        overflow-x: auto !important;
        -webkit-overflow-scrolling: touch;
    }
    .st-key-ahp_survey_matrix div[data-testid="stHorizontalBlock"] {
        flex-wrap: nowrap !important;
        min-width: 100% !important;
    }
    .st-key-ahp_survey_matrix div[data-testid="column"] {
        flex: 0 0 auto !important;
    }
    .st-key-ahp_survey_matrix div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(1),
    .st-key-ahp_survey_matrix div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(3) {
        width: 25% !important; 
        white-space: normal !important;
        word-break: break-all !important;
    }
    .st-key-ahp_survey_matrix div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(2) {
        width: 50% !important;
    }
}
/* ?„ì—­ ?ë‹¨ ?¬ë°± ?¤ì • (?ë‹¨ ?„ì´ì½?ê²¹ì¹¨ ë°©ì?) */
.block-container {
    padding-top: 3.5rem !important;
}
header[data-testid="stHeader"] {
    background-color: transparent !important;
}
</style>
"""
st.markdown(global_ahp_css, unsafe_allow_html=True)


# [?°íŠ¸ ?¤ì •]
@st.cache_resource
def set_font_config():
    system_name = platform.system()
    try:
        if system_name == 'Windows':
            font_path = "c:/Windows/Fonts/malgun.ttf"
            if os.path.exists(font_path):
                font_name = fm.FontProperties(fname=font_path).get_name()
                rc('font', family=font_name)
        elif system_name == 'Darwin': # Mac
            rc('font', family='AppleGothic')
        else: # Linux
            font_path = "NanumGothic.ttf"
            if not os.path.exists(font_path):
                import urllib.request
                url = "https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Regular.ttf"
                urllib.request.urlretrieve(url, font_path)
            fm.fontManager.addfont(font_path)
            font_prop = fm.FontProperties(fname=font_path)
            rc('font', family=font_prop.get_name())
    except Exception as e:
        pass
    plt.rcParams['axes.unicode_minus'] = False 

set_font_config()

# [ì¤‘ìš” ?˜ì •] êµ¬ê? ?œíŠ¸ ?°ê²° ?¬í¼ ?¨ìˆ˜ - ?¸ì¦ ?•ë³´ ë¡œë“œ ë¡œì§ ?„ë©´ ?¬ê???ë°??˜ì •
# TOML(Dict), JSON String, Base64 Encoded String ???¤ì–‘???¬ë§·???€?‘í•˜?„ë¡ ê°•í™”
def get_gspread_client():
    scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    
    # st.secrets?ì„œ ê°?ê°€?¸ì˜¤ê¸?(?†ì„ ê²½ìš° ?ëŸ¬ ì²˜ë¦¬)
    if "gcp_service_account" not in st.secrets:
        st.error("Secrets??'gcp_service_account' ?¤ì •???†ìŠµ?ˆë‹¤.")
        return None

    raw_auth = st.secrets["gcp_service_account"]
    auth_info = {}

    # Case 1: ?´ë? ?•ì…”?ˆë¦¬ ?•íƒœ??ê²½ìš° (TOML ?¬ë§·) - ê°€???¼ë°˜?ì¸ ê²½ìš°
    if isinstance(raw_auth, dict) or hasattr(raw_auth, "keys"): 
        auth_info = dict(raw_auth) # AttrDict ?±ì„ dictë¡?ë³€??
    
    # Case 2: ë¬¸ì???•íƒœ??ê²½ìš° (JSON ë¬¸ì???¹ì? Base64 ?¸ì½”??ë¬¸ì??
    elif isinstance(raw_auth, str):
        # ?ë’¤ ê³µë°± ë°??°ì˜´???œê±°
        auth_str = raw_auth.strip().strip('"').strip("'")
        
        try:
            # 2-1. ?œìˆ˜ JSON ë¬¸ì?´ë¡œ ?Œì‹± ?œë„
            auth_info = json.loads(auth_str)
        except json.JSONDecodeError:
            # 2-2. JSON ?Œì‹± ?¤íŒ¨ -> Base64 ?¸ì½”?©ëœ ê°’ìœ¼ë¡?ê°€?•í•˜ê³??”ì½”???œë„
            try:
                # 1?¨ê³„: ë¬¸ì???•ì œ (ëª¨ë“  ê³µë°± ?œê±°)
                clean_b64 = re.sub(r'\s+', '', auth_str)
                
                # 2?¨ê³„: ?¨ë”©(=) ë³´ì •
                missing_padding = len(clean_b64) % 4
                if missing_padding:
                    clean_b64 += '=' * (4 - missing_padding)
                
                # 3?¨ê³„: Base64 ?”ì½”??(Standard ë°?URL-Safe ë°©ì‹ ëª¨ë‘ ?œë„)
                try:
                    decoded_bytes = base64.b64decode(clean_b64)
                except Exception:
                    # Standard ?¤íŒ¨ ??URL-Safe ë°©ì‹ ?œë„ (-?€ _ ë¬¸ì ì²˜ë¦¬)
                    decoded_bytes = base64.urlsafe_b64decode(clean_b64)
                    
                decoded_info = decoded_bytes.decode('utf-8')
                auth_info = json.loads(decoded_info)
            except Exception as e:
                st.error(f"?œë¹„??ê³„ì • ???”ì½”???¤íŒ¨ (Base64/JSON ?¤ë¥˜): {e}")
                return None
    else:
        st.error("gcp_service_account ?•ì‹???¸ì‹?????†ìŠµ?ˆë‹¤.")
        return None

    # [ì¤‘ìš”] Private Key ?´ì˜ ì¤„ë°”ê¿?ë¬¸ì(\n) ì²˜ë¦¬
    # TOML ?±ì—??ë¬¸ì?´ë¡œ ?½ì–´????\\n?¼ë¡œ ?´ìŠ¤ì¼€?´í”„??ê²½ìš° ?¤ì œ ì¤„ë°”ê¿ˆìœ¼ë¡?ë³€ê²??„ìš”
    if auth_info and "private_key" in auth_info:
        auth_info["private_key"] = auth_info["private_key"].replace("\\n", "\n")

    # ?„ìˆ˜ ?„ë“œ ?•ì¸ (Missing fields ?ëŸ¬ ë°©ì?)
    required_fields = ["private_key", "client_email", "token_uri"]
    missing = [f for f in required_fields if f not in auth_info]
    if missing:
        st.error(f"?œë¹„??ê³„ì • ?•ë³´???„ìˆ˜ ?„ë“œê°€ ?„ë½?˜ì—ˆ?µë‹ˆ?? {', '.join(missing)}")
        return None

    creds = Credentials.from_service_account_info(auth_info, scopes=scope)
    return gspread.authorize(creds)

def run_gspread_with_retry(func, *args, max_retries=5, initial_backoff=2, **kwargs):
    """
    êµ¬ê? ?œíŠ¸ API ?¸ì¶œ ??429(RESOURCE_EXHAUSTED) ???¼ì‹œ???¤ë¥˜ ë°œìƒ ??
    ì§€??ë°±ì˜¤??Exponential Backoff) ë°?ì§€??Jitter)ë¥??ìš©?˜ì—¬ ?¬ì‹œ?„í•˜???¬í¼ ?¨ìˆ˜.
    """
    import time
    import random
    backoff = initial_backoff
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            err_msg = str(e)
            is_rate_limit = "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg or "RATE_LIMIT_EXCEEDED" in err_msg
            
            if is_rate_limit and attempt < max_retries - 1:
                sleep_time = backoff + random.uniform(0, 1)
                time.sleep(sleep_time)
                backoff *= 2
                continue
            else:
                raise e

# [? ê·œ] ê´€ë¦¬ì ?˜ì´ì§€ ë°©ë¬¸ ë¡œê·¸ ì¡°íšŒë¥??„í•œ ìºì‹± ?¨ìˆ˜ (?½ê¸° ?”ì²­ ìµœì ??- 5ë¶?TTL)
@st.cache_data(ttl=300, show_spinner=False)
def get_cached_visit_logs(spreadsheet_id):
    try:
        client = get_gspread_client()
        if client:
            spreadsheet = run_gspread_with_retry(client.open_by_key, spreadsheet_id)
            try:
                visit_sheet = run_gspread_with_retry(spreadsheet.worksheet, "Visit_Logs")
                records = run_gspread_with_retry(visit_sheet.get_all_records)
                # êµ¬ê? ?œíŠ¸?ì„œ ê°€?¸ì˜¨ ?„ì²´ ë¡œê·¸ë¥?ë¡œì»¬ DB???ë™?¼ë¡œ ?±í¬??ì±„ì›Œ?£ìŠµ?ˆë‹¤.
                if records:
                    try:
                        conn = sqlite3.connect('users.db')
                        c = conn.cursor()
                        for row in records:
                            ip_val = row.get('IP')
                            date_val = row.get('Date')
                            if ip_val and date_val:
                                c.execute("INSERT OR IGNORE INTO visit_logs (ip_address, visit_date) VALUES (?, ?)", 
                                          (str(ip_val), str(date_val)))
                        conn.commit()
                        conn.close()
                    except Exception:
                        pass
                return records
            except gspread.exceptions.WorksheetNotFound:
                return []
    except Exception as e:
        # ?¼ë°˜ ?¬ìš©???”ë©´??429/500 ?ëŸ¬ ë°•ìŠ¤ê°€ ë¬´ë¶„ë³„í•˜ê²??¸ì¶œ?˜ëŠ” ê²ƒì„ ë°©ì??©ë‹ˆ??
        # ê´€ë¦¬ì ë¡œê·¸???íƒœ?´ê±°??ê´€ë¦¬ì ëª¨ë“œ??ê²½ìš°?ë§Œ st.warning?¼ë¡œ ê²½ê³ ?˜ê³ , ?‰ì†Œ?ëŠ” ì½˜ì†”??ê¸°ë¡?©ë‹ˆ??
        import logging
        logging.error(f"êµ¬ê? ?œíŠ¸ ë°©ë¬¸ ë¡œê·¸ ìºì‹± ì¡°íšŒ ?¤ë¥˜: {e}")
        if st.session_state.get('admin_mode', False) and st.session_state.get('user_role') == 'admin':
            st.warning(f"? ï¸ êµ¬ê? ?œíŠ¸ ë°©ë¬¸ ë¡œê·¸ ìºì‹± ì¡°íšŒ ?¤ë¥˜ (ê´€ë¦¬ì ëª¨ë“œ): {e}")
    return []

def save_short_code_to_gs(short_code, survey_id, title, admin_id):
    try:
        client = get_gspread_client()
        if client and "SPREADSHEET_ID" in st.secrets:
            spreadsheet = client.open_by_key(st.secrets["SPREADSHEET_ID"])
            try:
                sheet = spreadsheet.worksheet("Short_Urls")
            except gspread.exceptions.WorksheetNotFound:
                sheet = spreadsheet.add_worksheet(title="Short_Urls", rows="1000", cols="5")
                sheet.append_row(["short_code", "survey_id", "title", "admin_id", "created_at"])
            
            import datetime
            kst_now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).strftime("%Y-%m-%d %H:%M:%S")
            sheet.append_row([short_code, survey_id, title, admin_id, kst_now])
    except Exception as e:
        pass

def sync_short_codes_from_gs():
    try:
        client = get_gspread_client()
        if client and "SPREADSHEET_ID" in st.secrets:
            spreadsheet = client.open_by_key(st.secrets["SPREADSHEET_ID"])
            try:
                sheet = spreadsheet.worksheet("Short_Urls")
                records = sheet.get_all_records()
                if records:
                    conn = sqlite3.connect('users.db')
                    cur = conn.cursor()
                    for r in records:
                        short_code = str(r.get("short_code", "")).strip()
                        survey_id = str(r.get("survey_id", "")).strip()
                        title = str(r.get("title", "")).strip()
                        admin_id = str(r.get("admin_id", "")).strip()
                        created_at = str(r.get("created_at", "")).strip()
                        if short_code and survey_id:
                            cur.execute("INSERT OR IGNORE INTO admin_surveys (survey_id, title, admin_id, created_at, short_code) VALUES (?, ?, ?, ?, ?)",
                                        (survey_id, title, admin_id, created_at, short_code))
                            cur.execute("UPDATE admin_surveys SET short_code = ? WHERE survey_id = ? AND (short_code IS NULL OR short_code = '')", (short_code, survey_id))
                    conn.commit()
                    conn.close()
            except gspread.exceptions.WorksheetNotFound:
                pass
    except Exception as e:
        pass

# ?¤ë¬¸/ë¯¸ë¦¬ë³´ê¸° ?˜ì´ì§€ ?¬ë? ì¡°ê¸° ê°ì? (Google Sheets API ?ˆì•½??
try:
    _q = st.query_params
except AttributeError:
    try:
        _q = st.experimental_get_query_params()
    except:
        _q = {}
_is_survey_or_preview = "preview_id" in _q or "survey_id" in _q

# DB ì´ˆê¸°??ë°?êµ¬ê? ?œíŠ¸ë¡œë????°ì´???Œì›+ë°©ë¬¸ë¡œê·¸) ë³µêµ¬ ë¡œì§
def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    # [?˜ì •] êµ¬ê? ?œíŠ¸ êµ¬ì¡°??ë§ì¶° agree_info ë°?ë°°í¬?µê³„ ì»¬ëŸ¼ ì¶”ê?
    c.execute('''CREATE TABLE IF NOT EXISTS users
                  (id TEXT PRIMARY KEY, role TEXT, signup_date TEXT, pw TEXT, expiry_date TEXT, agree_info TEXT, 
                   survey_count INTEGER DEFAULT 0, last_survey_link TEXT)''')
    try:
        c.execute("ALTER TABLE users ADD COLUMN survey_count INTEGER DEFAULT 0")
        conn.commit()
    except Exception:
        pass
    try:
        c.execute("ALTER TABLE users ADD COLUMN last_survey_link TEXT")
        conn.commit()
    except Exception:
        pass

    c.execute('''CREATE TABLE IF NOT EXISTS saved_analyses
                  (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, filename TEXT, save_date TEXT, file_data BLOB)''')
    c.execute('''CREATE TABLE IF NOT EXISTS user_models
                  (user_id TEXT PRIMARY KEY, model_data TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS visit_logs
                  (ip_address TEXT, visit_date TEXT, PRIMARY KEY (ip_address, visit_date))''')
    c.execute('''CREATE TABLE IF NOT EXISTS admin_surveys
                  (survey_id TEXT PRIMARY KEY, title TEXT, admin_id TEXT, created_at TEXT, short_code TEXT)''')
    try:
        c.execute("ALTER TABLE admin_surveys ADD COLUMN short_code TEXT")
        conn.commit()
    except Exception:
        pass

    # ê¸°ì¡´ ?°ì´?°ì— short_code ê°€ ?†ëŠ” ê²½ìš° ì±„ì›Œ?£ê¸°
    try:
        c.execute("SELECT survey_id FROM admin_surveys WHERE short_code IS NULL OR short_code = ''")
        rows = c.fetchall()
        if rows:
            for row in rows:
                sid = row[0]
                scode = "".join(random.choice(string.ascii_letters + string.digits) for _ in range(6))
                c.execute("UPDATE admin_surveys SET short_code = ? WHERE survey_id = ?", (scode, sid))
            conn.commit()
    except Exception:
        pass
        
    c.execute('''CREATE TABLE IF NOT EXISTS user_google_credentials
                  (user_id TEXT PRIMARY KEY, token TEXT, refresh_token TEXT, token_uri TEXT, client_id TEXT, client_secret TEXT, scopes TEXT, expiry TEXT)''')
    
    # ê´€ë¦¬ì ê³„ì • ?ì„±
    try:
        # [?˜ì •] ?€?œë?êµ??œê°„ ê¸°ì? ê°€?…ì¼ ?¤ì • (? ì§œë§?
        kst_now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
        signup_date_str = kst_now.strftime("%Y-%m-%d")
        # ì»¬ëŸ¼ ?œì„œ: id, role, signup_date, pw, expiry_date, agree_info, survey_count, last_survey_link
        c.execute("INSERT OR IGNORE INTO users (id, role, signup_date, pw, expiry_date, agree_info, survey_count, last_survey_link) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", 
                  ('shjeon', 'admin', signup_date_str, '@jsh2143033', '9999-12-31', 'Y', 0, ''))
        conn.commit()

        # [ì¶”ê?] ê´€ë¦¬ì ê³„ì •??êµ¬ê? ?œíŠ¸???†ëŠ” ê²½ìš° ?ë™ ì¶”ê? (?¸ì…˜??1?? ?¤ë¬¸/ë¯¸ë¦¬ë³´ê¸° ?˜ì´ì§€ ?œì™¸)
        if not _is_survey_or_preview and not st.session_state.get('_init_gs_done'):
            try:
                client = get_gspread_client()
                if client:
                    spreadsheet = client.open_by_key(st.secrets["SPREADSHEET_ID"])
                    sheet = spreadsheet.sheet1
                    # ?¤ë” ë³´ì •
                    all_values = sheet.get_all_values()
                    if all_values and len(all_values[0]) < 8:
                        sheet.update(range_name='A1:H1', values=[['id', 'role', 'signup_date', 'pw', 'expiry_date', 'agree_info', 'survey_count', 'last_survey_link']])
                    
                    cell = sheet.find('shjeon')
                    if not cell:
                        sheet.append_row(['shjeon', 'admin', signup_date_str, '@jsh2143033', '9999-12-31', 'Y', 0, ''])
            except Exception:
                pass
    except sqlite3.IntegrityError:
        pass 

    # [ë³µêµ¬ ë¡œì§ 1~2 ë°?short_code ?™ê¸°?? ?¸ì…˜??1?Œë§Œ ?¤í–‰ (?¤ë¬¸/ë¯¸ë¦¬ë³´ê¸° ?˜ì´ì§€ ?œì™¸)
    if not _is_survey_or_preview and not st.session_state.get('_init_gs_done'):
        c.execute("SELECT COUNT(*) FROM users")
        if c.fetchone()[0] <= 1:
            try:
                client = get_gspread_client()  
                if client:
                    spreadsheet = client.open_by_key(st.secrets["SPREADSHEET_ID"])
                    sheet = spreadsheet.sheet1

                    # [?¤ë” ë³´ì •] êµ¬ê? ?œíŠ¸???¤ë” ì»¬ëŸ¼ ë³´ì •
                    all_values = sheet.get_all_values()
                    if all_values and len(all_values[0]) < 8:
                        sheet.update(range_name='A1:H1', values=[['id', 'role', 'signup_date', 'pw', 'expiry_date', 'agree_info', 'survey_count', 'last_survey_link']])

                    records = sheet.get_all_records()  # 1??header ?¬ìš©
                    if records:
                        def pick(row, *keys, default=""):
                            for k in keys:
                                if k in row and row[k] is not None and str(row[k]).strip() != "":
                                        return str(row[k]).strip()
                            return default

                        kst_today = datetime.datetime.now(
                            datetime.timezone(datetime.timedelta(hours=9))
                        ).strftime("%Y-%m-%d")

                        for r in records:
                            userid = pick(r, "id", "ID", "user_id", "userid", "email")
                            if not userid or userid == "shjeon":
                                continue

                            pw = pick(r, "pw", "PW", "password")
                            role = pick(r, "role", "Role", default="temp")
                            signupdate = pick(r, "signup_date", "signup_tate", "signupdate", "SignupDate", default=kst_today)
                            expirydate = pick(r, "expiry_date", "expirydate", "ExpiryDate", default="9999-12-31")
                            agreeinfo = pick(r, "agree_info", "agreeinfo", "Agree", default="")
                            survey_count = int(pick(r, "survey_count", "surveycount", default="0"))
                            last_survey_link = pick(r, "last_survey_link", "lastsurveylink", default="")

                            # [?ê? ì¹˜ìœ ] êµ¬ê? ?œíŠ¸ ì»¬ëŸ¼ ?¬í”„???¤ë¥˜ ë³µêµ¬
                            if expirydate in ["Y", "N", "??, "?„ë‹ˆ??, "yes", "no"]:
                                if not agreeinfo:
                                    agreeinfo = expirydate
                                expirydate = "9999-12-31"

                            if not agreeinfo:
                                agreeinfo = "Y"

                            if role not in ("temp", "official", "admin"):
                                role = "temp"

                            c.execute(
                                "INSERT OR IGNORE INTO users (id, role, signup_date, pw, expiry_date, agree_info, survey_count, last_survey_link) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                                (userid, role, signupdate, pw, expirydate, agreeinfo, survey_count, last_survey_link),
                            )

                        conn.commit()
            except Exception:
                pass

        # [ë³µêµ¬ ë¡œì§ 2] ë°©ë¬¸ ë¡œê·¸ ë³µêµ¬
        c.execute("SELECT COUNT(*) FROM visit_logs")
        if c.fetchone()[0] == 0:
            try:
                client = get_gspread_client()
                if client:
                    spreadsheet = client.open_by_key(st.secrets["SPREADSHEET_ID"])
                    try:
                        visit_sheet = spreadsheet.worksheet("Visit_Logs")
                        records = visit_sheet.get_all_records()
                        for row in records:
                            c.execute("INSERT OR IGNORE INTO visit_logs (ip_address, visit_date) VALUES (?, ?)", 
                                      (row['IP'], row['Date']))
                        conn.commit()
                    except gspread.exceptions.WorksheetNotFound:
                        pass
            except Exception:
                pass

        try:
            sync_short_codes_from_gs()
        except Exception:
            pass
        
        # ?¸ì…˜??1???¤í–‰ ?„ë£Œ ?œì‹œ
        st.session_state._init_gs_done = True
    conn.close()

# [? ê·œ ê¸°ëŠ¥ 1] êµ¬ê? ?œíŠ¸???´ìš©??ê°•ì œë¡?DB???™ê¸°?”í•˜???¨ìˆ˜
def sync_db_from_sheets():
    """êµ¬ê? ?œíŠ¸???°ì´?°ë? ?½ì–´?€ DB???†ìœ¼ë©?? ì?ë¥?ì¶”ê??˜ê³ , ?´ë? ?ˆë‹¤ë©?êµ¬ê? ?œíŠ¸ ê¸°ì??¼ë¡œ ë³´ì •(?…ë°?´íŠ¸)?©ë‹ˆ??"""
    # ?…â˜…???„ì‹œ ?”ë²„ê¹?ì½”ë“œ ?…â˜…??
    st.write("?” **Secrets ?”ë²„ê¹?*")
    st.write("?¬ìš© ê°€?¥í•œ ìµœìƒ????", list(st.secrets.keys()))
    
    if "SPREADSHEET_ID" in st.secrets:
        st.success(f"??SPREADSHEET_ID ë°œê²¬!")
        st.write(f"ê°? {st.secrets['SPREADSHEET_ID']}")
    else:
        st.error("??SPREADSHEET_IDê°€ ?†ìŠµ?ˆë‹¤!")
        
    if "gcp_service_account" in st.secrets:
        st.write("gcp_service_account ?´ë? ??", list(st.secrets["gcp_service_account"].keys()))
    
    st.write("---")
    # ?…â˜…???”ë²„ê¹????…â˜…??
    
    conn = None
    try:
        client = get_gspread_client()
        if not client: 
            st.error("??êµ¬ê? ?œíŠ¸ ?¸ì¦(gspread client)???¤íŒ¨?ˆìŠµ?ˆë‹¤.")
            return -1
        
        spreadsheet = run_gspread_with_retry(client.open_by_key, st.secrets["SPREADSHEET_ID"])
        sheet = run_gspread_with_retry(lambda: spreadsheet.sheet1)
        all_values = run_gspread_with_retry(sheet.get_all_values)
        
        # ?°ì´?°ê? ?¤ë” ?¬í•¨ 2ì¤??´ìƒ???Œë§Œ ì§„í–‰
        if len(all_values) > 1:
            # 30ì´??€?„ì•„??ì¶”ê? ë°??ˆì „??ì»¤ë„¥??
            conn = sqlite3.connect('users.db', timeout=30.0)
            c = conn.cursor()
            
            cnt = 0
            processed_ids = set()
            for row in all_values[1:]:
                # row êµ¬ì¡°: [ID, Role, SignupDate, PW, expiry_date, agree_info, survey_count, last_survey_link]
                if len(row) >= 4:
                    user_id = str(row[0]).strip()
                    if not user_id or user_id in processed_ids:
                        continue
                    processed_ids.add(user_id)
                    
                    role = str(row[1]).strip()
                    signup_date = str(row[2]).strip()
                    pw = str(row[3]).strip()
                    
                    # 8ê°?ì»¬ëŸ¼ ?€??ë°??ê? ì¹˜ìœ 
                    survey_count = 0
                    last_survey_link = ""
                    if len(row) >= 8:
                        expiry_date = str(row[4]).strip()
                        agree_info = str(row[5]).strip()
                        try:
                            survey_count = int(row[6])
                        except:
                            survey_count = 0
                        last_survey_link = str(row[7]).strip()
                    elif len(row) >= 6:
                        expiry_date = str(row[4]).strip()
                        agree_info = str(row[5]).strip()
                    elif len(row) == 5:
                        expiry_date = '9999-12-31'
                        agree_info = str(row[4]).strip()
                    else:
                        expiry_date = '9999-12-31'
                        agree_info = 'Y'
                        
                    # [?ê? ì¹˜ìœ ] êµ¬ê? ?œíŠ¸ ?¤ë¥˜ ë³µêµ¬ (expiry_date???™ì˜ ?¬ë?ê°€ ?˜ëª» ?¤ì–´ê°”ì„ ??
                    if expiry_date in ["Y", "N", "??, "?„ë‹ˆ??, "yes", "no"]:
                        if agree_info in ["", None, "Y"]:
                            agree_info = expiry_date
                        expiry_date = "9999-12-31"

                    # ?´ë? ì¡´ì¬?˜ëŠ”ì§€ ?•ì¸ ???†ìœ¼ë©?INSERT, ?ˆìœ¼ë©??•ë³´ ë³´ì • ?…ë°?´íŠ¸
                    c.execute("SELECT id, role, signup_date, pw, expiry_date, agree_info, survey_count, last_survey_link FROM users WHERE id=?", (user_id,))
                    db_user = c.fetchone()
                    if not db_user:
                        c.execute("INSERT INTO users (id, role, signup_date, pw, expiry_date, agree_info, survey_count, last_survey_link) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", 
                                  (user_id, role, signup_date, pw, expiry_date, agree_info, survey_count, last_survey_link))
                        cnt += 1
                    else:
                        db_role, db_signup_date, db_pw, db_expiry_date, db_agree_info, db_survey_count, db_last_link = db_user[1], db_user[2], db_user[3], db_user[4], db_user[5], db_user[6], db_user[7]
                        # ë³€ê²??¬í•­???˜ë‚˜?¼ë„ ?ˆìœ¼ë©?êµ¬ê? ?œíŠ¸ ê¸°ì??¼ë¡œ ê°•ì œ ?…ë°?´íŠ¸ ë³´ì •
                        if (db_role != role or db_signup_date != signup_date or 
                            db_pw != pw or db_expiry_date != expiry_date or db_agree_info != agree_info or
                            db_survey_count != survey_count or db_last_link != last_survey_link):
                            c.execute("""
                                UPDATE users 
                                SET role=?, signup_date=?, pw=?, expiry_date=?, agree_info=?, survey_count=?, last_survey_link=? 
                                WHERE id=?
                            """, (role, signup_date, pw, expiry_date, agree_info, survey_count, last_survey_link, user_id))
                            cnt += 1
            
            conn.commit()
            return cnt
    except Exception as e:
        st.error(f"?” ?™ê¸°???ëŸ¬ ?ì„¸: {str(e)}")
        st.error(f"?ëŸ¬ ?€?? {type(e).__name__}")
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass
        return -1
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass
    return 0

# ë°©ë¬¸??ì¶”ì  ë°?êµ¬ê? ?œíŠ¸ ?¤ì‹œê°??€??
def track_visitor():
    js_ip_script = 'await fetch("https://api.ipify.org?format=json").then(r => r.json()).then(d => d.ip)'
    client_ip = st_javascript(js_ip_script)
    if not client_ip:
        return 

    ip = str(client_ip).strip()
    
    if st.session_state.get('visited'):
        return

    try:
        # ì¹´ìš´??ë°©ì‹ ê°œì„ : [?˜ì •] ?€?œë?êµ??œê°„ ê¸°ì? ?œê° ?•ë³´ ?¬ìš©
        now_ts = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).strftime("%Y-%m-%d %H:%M:%S")
        
        country, region, city, lat, lon = "", "", "", "", ""
        if ip not in ["localhost", "unknown_ip", "127.0.0.1"] and not ip.startswith("192.168."):
            try:
                response = requests.get(f"http://ip-api.com/json/{ip}", timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    if data.get("status") == "success":
                        country = data.get("country", "")
                        region = data.get("regionName", "")
                        city = data.get("city", "")
                        lat = data.get("lat", "")
                        lon = data.get("lon", "")
            except:
                pass

        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO visit_logs (ip_address, visit_date) VALUES (?, ?)", (ip, now_ts))
        conn.commit()
        conn.close()

        # ?¤ë¬¸/ë¯¸ë¦¬ë³´ê¸° ?˜ì´ì§€?ì„œ??êµ¬ê? ?œíŠ¸??ë°©ë¬¸ ë¡œê·¸ë¥?ê¸°ë¡?˜ì? ?ŠìŒ (API ?ˆì•½)
        if not _is_survey_or_preview:
            try:
                client = get_gspread_client()
                if client:
                    spreadsheet = client.open_by_key(st.secrets["SPREADSHEET_ID"])
                    try:
                        visit_sheet = spreadsheet.worksheet("Visit_Logs")
                    except gspread.exceptions.WorksheetNotFound:
                        visit_sheet = spreadsheet.add_worksheet(title="Visit_Logs", rows="1000", cols="10")
                        visit_sheet.append_row(["IP", "Date", "Country", "Region", "City", "Latitude", "Longitude"])
                    
                    visit_sheet.append_row([ip, now_ts, country, region, city, lat, lon])
                    
            except Exception:
                pass
        st.session_state.visited = True
    except Exception:
        pass

# ë°©ë¬¸??ì¶”ì  ?¤í–‰ë¶€
if 'visited' not in st.session_state:
    st.session_state.visited = False
track_visitor()

def verify_paypal_payment(order_id):
    """Verify PayPal order status on the backend using credentials from secrets."""
    client_id = st.secrets.get("PAYPAL_CLIENT_ID", "")
    client_secret = st.secrets.get("PAYPAL_CLIENT_SECRET", "")
    mode = st.secrets.get("PAYPAL_MODE", "sandbox")
    
    if not client_id or not client_secret:
        return False, "PayPal credentials not configured."
        
    base_url = "https://api-m.paypal.com" if mode == "live" else "https://api-m.sandbox.paypal.com"
    
    try:
        auth_response = requests.post(
            f"{base_url}/v1/oauth2/token",
            auth=(client_id, client_secret),
            data={"grant_type": "client_credentials"},
            headers={"Accept": "application/json", "Accept-Language": "en_US"}
        )
        if auth_response.status_code != 200:
            return False, "Failed to authenticate with PayPal API."
        access_token = auth_response.json().get("access_token")
        
        order_response = requests.get(
            f"{base_url}/v2/checkout/orders/{order_id}",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
        )
        if order_response.status_code != 200:
            return False, "Failed to retrieve order details from PayPal."
            
        order_data = order_response.json()
        status = order_data.get("status")
        
        if status == "COMPLETED":
            return True, "Payment verified."
        return False, f"Payment status is {status}."
    except Exception as e:
        return False, f"Error verifying payment: {str(e)}"

def validate_email(email):
    return re.match(r"[^@]+@[^@]+\.[^@]+", email)

def validate_password(password):
    if len(password) < 4: return False
    has_char = re.search(r'[a-zA-Z]', password)
    has_special = re.search(r'[!@#$%^&*(),.?":{}|<>]', password)
    return has_char and has_special

def send_foreign_access_email(ip, country, region, kst_time):
    sender_email = "jeon080423@gmail.com"
    password = st.secrets.get("EMAIL_PASSWORD", "csuh xxru wqdy mttt")
    recipient_email = "jeon080423@gmail.com"
    subject = f"[AHP ë§ˆìŠ¤?? ? ï¸ ?´ì™¸ ?‘ì† ê°ì?: {country}"
    
    body = f"""AHP ë§ˆìŠ¤?°ì— ?´ì™¸ ?‘ì†??ê°ì??˜ì—ˆ?µë‹ˆ??

?‘ì† ?œê°„ (KST): {kst_time}
?‘ì† êµ??: {country}
?‘ì† ì§€?? {region}
?‘ì† IP: {ip}
"""
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = sender_email
    msg['To'] = recipient_email
    
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender_email, password)
            server.sendmail(sender_email, recipient_email, msg.as_string())
    except Exception as e:
        print(f"Failed to send foreign access email: {e}")

def check_foreign_access():
    if "foreign_access_checked" not in st.session_state:
        st.session_state.foreign_access_checked = True
        try:
            # st.context.headers is available in Streamlit 1.30+
            if hasattr(st, 'context') and hasattr(st.context, 'headers'):
                headers = st.context.headers
                ip = headers.get("X-Forwarded-For", "").split(",")[0].strip()
                if not ip:
                    ip = headers.get("X-Real-IP", "").split(",")[0].strip()
                    
                if ip and ip not in ["127.0.0.1", "::1", "localhost"]:
                    import requests
                    res = requests.get(f"https://get.geojs.io/v1/ip/geo/{ip}.json", timeout=3)
                    if res.status_code == 200:
                        data = res.json()
                        country_code = data.get("country_code", "")
                        country = data.get("country", "Unknown Country")
                        region = data.get("region", "Unknown Region")
                        
                        if country_code and country_code != "KR":
                            kst_time = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).strftime("%Y-%m-%d %H:%M:%S")
                            send_foreign_access_email(ip, country, region, kst_time)
        except Exception as e:
            print(f"Error checking foreign access: {e}")


def send_application_email(user_email):
    sender_email = "jeon080423@gmail.com"
    # secrets.toml?ì„œ ?´ë©”??ë¹„ë?ë²ˆí˜¸ë¥??ˆì „?˜ê²Œ ë¡œë“œ?©ë‹ˆ??
    password = st.secrets.get("EMAIL_PASSWORD", "csuh xxru wqdy mttt")
    recipient_email = "jeon080423@gmail.com"
    subject = f"[AHP ë§ˆìŠ¤?? ?•ì‹ ?¬ìš©???¹ì¸ ?”ì²­: {user_email}"
    # [?˜ì •] ?€?œë?êµ??œê°„ ê¸°ì? ? ì²­???¤ì •
    kst_today = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).date()
    body = f"?¬ìš©?ê? ?•ì‹ ê¶Œí•œ ? ì²­.\nID: {user_email}\n? ì²­?? {kst_today}"
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = sender_email
    msg['To'] = recipient_email
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(sender_email, password)
            server.sendmail(sender_email, recipient_email, msg.as_string())
    except Exception as e:
        print(f"send_application_email Error: {e}")

# [ì¶”ê? ?”ì²­?¬í•­ ë°˜ì˜] ?„í™˜ ?”ì²­ ?´ë©”??ë°œì†¡ ?¨ìˆ˜
def send_conversion_request_email(user_email):
    sender_email = "jeon080423@gmail.com"
    password = st.secrets.get("EMAIL_PASSWORD", "csuh xxru wqdy mttt")
    recipient_email = "jeon080423@gmail.com"
    subject = f"[AHP ë§ˆìŠ¤?? ?•ì‹?¬ìš©???„í™˜ ?”ì²­: {user_email}"
    body = f"?„ì‹œ ?¬ìš©?ê? ?•ì‹?¬ìš©?ë¡œ ?„í™˜ ?”ì²­ ?ˆìŠµ?ˆë‹¤\nID: {user_email}"
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = sender_email
    msg['To'] = recipient_email
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(sender_email, password)
            server.sendmail(sender_email, recipient_email, msg.as_string())
        return True
    except Exception as e:
        print(f"send_conversion_request_email Error: {e}")
        return False

def send_approval_email(user_email):
    sender_email = "jeon080423@gmail.com"
    password = st.secrets.get("EMAIL_PASSWORD", "csuh xxru wqdy mttt")
    recipient_email = user_email
    subject = "[AHP ë§ˆìŠ¤?? ?•ì‹ ?¬ìš©???¹ì¸ ?„ë£Œ"
    body = f"{user_email}?? ?•ì‹ ?¬ìš©?ë¡œ ?¹ì¸?˜ì—ˆ?µë‹ˆ?? ?¤ëŠ˜ë¶€??3ê°œì›”ê°?ëª¨ë“  ê¸°ëŠ¥??ë¬´ì œ?œìœ¼ë¡??¬ìš©?˜ì‹¤ ???ˆìŠµ?ˆë‹¤."
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = sender_email
    msg['To'] = recipient_email
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(sender_email, password)
            server.sendmail(sender_email, recipient_email, msg.as_string())
        return True
    except Exception as e:
        print(f"send_approval_email Error: {e}")
        return False

def send_password_recovery_email(user_email, temp_pw):
    sender_email = "jeon080423@gmail.com"
    password = st.secrets.get("EMAIL_PASSWORD", "csuh xxru wqdy mttt")
    recipient_email = user_email
    subject = "[AHP ë§ˆìŠ¤?? ?„ì‹œ ë¹„ë?ë²ˆí˜¸ ?ˆë‚´"
    body = f"""?ˆë…•?˜ì„¸?? ?”ì²­?˜ì‹  ê³„ì •???„ì‹œ ë¹„ë?ë²ˆí˜¸ë¥??ˆë‚´???œë¦½?ˆë‹¤.

ID: {user_email}
?„ì‹œ ë¹„ë?ë²ˆí˜¸: {temp_pw}

ë¡œê·¸????ì¦‰ì‹œ ë¹„ë?ë²ˆí˜¸ë¥?ë³€ê²½í•˜?œê¸°ë¥?ê¶Œì¥?©ë‹ˆ??
ê°ì‚¬?©ë‹ˆ??
"""
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = sender_email
    msg['To'] = recipient_email
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(sender_email, password)
            server.sendmail(sender_email, recipient_email, msg.as_string())
        return True
    except Exception as e:
        print(f"send_password_recovery_email Error: {e}")
        return False

# --- DB CRUD ---

def log_to_sheets(user_id, role, signup_date, pw, agree_info="Y", expiry_date="9999-12-31", survey_count=0, last_survey_link=""):
    try:
        client = get_gspread_client()
        if client:
            spreadsheet = client.open_by_key(st.secrets["SPREADSHEET_ID"])
            sheet = spreadsheet.sheet1
            # [?˜ì •] êµ¬ê? ?œíŠ¸ 8ê°?ì»¬ëŸ¼ ?œì„œ(id, role, signup_date, pw, expiry_date, agree_info, survey_count, last_survey_link) ë³´ì¥
            sheet.append_row([user_id, role, str(signup_date), pw, expiry_date, agree_info, survey_count, last_survey_link])
    except Exception as e:
        st.error(f"Google Sheets ë¡œê¹… ?¤ë¥˜: {e}")

def add_user(user_id, pw, role, agree_info="Y"):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    # [?˜ì •] ?€?œë?êµ??œê°„ ê¸°ì? ê°€?…ì¼ ?¤ì • (? ì§œë§?
    signup_date = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).strftime("%Y-%m-%d")
    expiry_date = "9999-12-31"
    hashed_pw = hash_password(pw)
    try:
        # [?˜ì •] êµ¬ê? ?œíŠ¸ ?œì„œ??ë§ì¶° DB ?€??(id, role, signup_date, pw, expiry_date, agree_info, survey_count, last_survey_link)
        c.execute("INSERT INTO users (id, role, signup_date, pw, expiry_date, agree_info, survey_count, last_survey_link) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", 
                  (user_id, role, signup_date, hashed_pw, expiry_date, agree_info, 0, ""))
        conn.commit()
        log_to_sheets(user_id, role, signup_date, hashed_pw, agree_info, expiry_date, 0, "")
        success = True
    except sqlite3.IntegrityError:
        success = False
    finally:
        conn.close()
    return success

def update_user_survey_distribution(user_id, survey_link):
    """
    ?¬ìš©?ê? ?¤ë¬¸??ë°°í¬?????¸ì¶œ?˜ì—¬
    SQLite DB ë°?ê´€ë¦¬ì êµ¬ê? ?œíŠ¸??ë°°í¬ ?Ÿìˆ˜?€ ìµœì¢… ë°°í¬ ?¤ë¬¸ì§€ ë§í¬ë¥??…ë°?´íŠ¸?©ë‹ˆ??
    """
    if not user_id:
        return
    try:
        # 1. SQLite DB ?…ë°?´íŠ¸
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        
        c.execute("SELECT survey_count FROM users WHERE id = ?", (user_id,))
        row = c.fetchone()
        current_count = 0
        if row and row[0] is not None:
            current_count = int(row[0])
            
        new_count = current_count + 1
        c.execute("UPDATE users SET survey_count = ?, last_survey_link = ? WHERE id = ?", (new_count, survey_link, user_id))
        conn.commit()
        conn.close()
        
        # 2. ê´€ë¦¬ì êµ¬ê? ?œíŠ¸ ?…ë°?´íŠ¸
        client = get_gspread_client()
        if client:
            spreadsheet = run_gspread_with_retry(client.open_by_key, st.secrets["SPREADSHEET_ID"])
            sheet = run_gspread_with_retry(lambda: spreadsheet.sheet1)
            
            # ?¤ë” ?•ì¸ ë°?ì»¬ëŸ¼ ì¶”ê? ë³´ì •
            headers = run_gspread_with_retry(sheet.row_values, 1)
            headers_updated = False
            if 'survey_count' not in headers:
                headers.append('survey_count')
                headers_updated = True
            if 'last_survey_link' not in headers:
                headers.append('last_survey_link')
                headers_updated = True
                
            if headers_updated:
                run_gspread_with_retry(sheet.update, range_name='A1:H1', values=[headers[:8]])
                
            try:
                cell = run_gspread_with_retry(sheet.find, user_id)
                if cell:
                    run_gspread_with_retry(sheet.update_cell, cell.row, 7, new_count)
                    run_gspread_with_retry(sheet.update_cell, cell.row, 8, survey_link)
            except Exception:
                pass
    except Exception as e:
        import logging
        logging.error(f"update_user_survey_distribution Error: {e}")

def upgrade_user_password_to_hash(user_id, pw):
    """ê¸°ì¡´ ?¬ìš©?ì˜ ?‰ë¬¸ ë¹„ë?ë²ˆí˜¸ë¥??”í˜¸???´ì‹œ) ë²„ì „?¼ë¡œ ?ë™ ?¹ê¸‰?©ë‹ˆ??"""
    hashed_pw = hash_password(pw)
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("UPDATE users SET pw=? WHERE id=?", (hashed_pw, user_id))
    conn.commit()
    conn.close()
    
    try:
        client = get_gspread_client()
        if client:
            spreadsheet = client.open_by_key(st.secrets["SPREADSHEET_ID"])
            sheet = spreadsheet.sheet1
            cell = sheet.find(user_id)
            if cell:
                # êµ¬ê? ?œíŠ¸??PW ì»¬ëŸ¼?€ 4ë²ˆì§¸(D)
                sheet.update_cell(cell.row, 4, hashed_pw)
    except Exception:
        pass

def check_login(user_id, pw):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    # ?‰ë¬¸ ?¨ìŠ¤?Œë“œ ë¡œê·¸??ë°??ë™ ?…ê·¸?ˆì´?œë? ì§€?í•˜ê¸??„í•´ pw ì»¬ëŸ¼???¨ê»˜ ì¡°íšŒ?©ë‹ˆ??
    c.execute("SELECT role, expiry_date, pw FROM users WHERE id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    
    if row:
        stored_role, stored_expiry, stored_pw = row
        hashed_pw = hash_password(pw)
        
        # ?‰ë¬¸ ?¨ìŠ¤?Œë“œê°€ ?•í™•???¼ì¹˜?˜ê±°???´ì‹œ ?¨ìŠ¤?Œë“œê°€ ?¼ì¹˜?˜ëŠ” ê²½ìš°
        if stored_pw == pw or stored_pw == hashed_pw:
            # ?‰ë¬¸ ?¨ìŠ¤?Œë“œë¡?ë¡œê·¸???±ê³µ??ê²½ìš°, ì¦‰ì‹œ ?´ì‹œ ?¨ìŠ¤?Œë“œë¡??…ë°?´íŠ¸ (ë³´ì•ˆ ?¹ê¸‰)
            if stored_pw == pw:
                upgrade_user_password_to_hash(user_id, pw)
            return stored_role, stored_expiry
            
    return None

def get_user_password(user_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT pw FROM users WHERE id=?", (user_id,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

def change_user_password(user_id, new_pw):
    hashed_pw = hash_password(new_pw)
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("UPDATE users SET pw=? WHERE id=?", (hashed_pw, user_id))
    conn.commit()
    conn.close()

    try:
        client = get_gspread_client()
        if client:
            spreadsheet = client.open_by_key(st.secrets["SPREADSHEET_ID"])
            sheet = spreadsheet.sheet1
            cell = sheet.find(user_id)
            if cell:
                # êµ¬ê? ?œíŠ¸??PW ì»¬ëŸ¼?€ 4ë²ˆì§¸(D)
                sheet.update_cell(cell.row, 4, hashed_pw)
    except Exception:
        pass
    return True

def get_all_users():
    conn = sqlite3.connect('users.db')
    df = pd.read_sql_query("SELECT * FROM users", conn)
    conn.close()
    return df

def update_user_full_info(user_id, new_pw, new_role, new_expiry):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    if new_pw is not None and new_pw != "":
        c.execute("UPDATE users SET pw=?, role=?, expiry_date=? WHERE id=?", (new_pw, new_role, new_expiry, user_id))
    else:
        c.execute("UPDATE users SET role=?, expiry_date=? WHERE id=?", (new_role, new_expiry, user_id))
    conn.commit()
    conn.close()
    
    try:
        client = get_gspread_client()
        if client:
            spreadsheet = client.open_by_key(st.secrets["SPREADSHEET_ID"])
            sheet = spreadsheet.sheet1
            cell = sheet.find(user_id)
            kst_today = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).strftime("%Y-%m-%d")
            
            # SQLite DB?ì„œ ?¤ì œ ?€?¥ëœ ê¸°ì¡´ ê°€??? ì§œ ì¡°íšŒ (ê°€?…ì¼ ?¼ì† ë°©ì?)
            db_signup_date = None
            conn = sqlite3.connect('users.db')
            c = conn.cursor()
            c.execute("SELECT signup_date FROM users WHERE id=?", (user_id,))
            res = c.fetchone()
            if res:
                db_signup_date = res[0]
            conn.close()
            
            if cell:
                row_num = cell.row
                # ê¸°ì¡´ ?°ì´??ë³´ì¡´???„í•´ ?„ì¬ ?œíŠ¸ ?°ì´??ë¡œë“œ (6ê°?ì»¬ëŸ¼ ?€??
                current_row_data = sheet.row_values(row_num)
                # agree_info??6ë²ˆì§¸ ì»¬ëŸ¼(index 5)???ˆì–´???©ë‹ˆ?? ?†ìœ¼ë©?5ë²ˆì§¸(index 4) ?¹ì? ê¸°ë³¸ê°?"Y"
                agree_info = current_row_data[5] if len(current_row_data) >= 6 else (current_row_data[4] if len(current_row_data) >= 5 else "Y")
                
                # êµ¬ê? ?œíŠ¸ ê¸°ì¡´ ê°€?…ì¼ ?•ì¸
                sheet_signup_date = current_row_data[2] if len(current_row_data) >= 3 else None
                
                # DB??ê°€?…ì¼???°ì„ ?œìœ„ë¡??˜ê³ , ?†ìœ¼ë©?êµ¬ê? ?œíŠ¸ ê¸°ì¡´ ê°€?…ì¼, ê·¸ë§ˆ?€???†ìœ¼ë©?kst_today ?¬ìš©
                final_signup_date = db_signup_date or sheet_signup_date or kst_today
                
                final_pw = new_pw if (new_pw and new_pw != "") else (current_row_data[3] if len(current_row_data) >= 4 else "")
                
                # ë°°í¬ ?µê³„ ë°??¤ë¬¸ ë§í¬ ë³´ì¡´ (G:H ì»¬ëŸ¼ ?€??
                survey_count_val = current_row_data[6] if len(current_row_data) >= 7 else 0
                last_survey_link_val = current_row_data[7] if len(current_row_data) >= 8 else ""
                
                # ?œíŠ¸ ?œì„œ: ID, Role, SignupDate, PW, expiry_date, agree_info, survey_count, last_survey_link (A:H)
                sheet.update(range_name=f'A{row_num}:H{row_num}', values=[[user_id, new_role, final_signup_date, final_pw, new_expiry, agree_info, survey_count_val, last_survey_link_val]])
            else:
                final_pw = new_pw if (new_pw and new_pw != "") else ""
                final_signup_date = db_signup_date or kst_today
                sheet.append_row([user_id, new_role, final_signup_date, final_pw, new_expiry, "Y", 0, ""])
    except Exception as e:
        st.error(f"êµ¬ê? ?œíŠ¸ ?¬ìš©???•ë³´ ?˜ì • ë°˜ì˜ ?¤ë¥˜: {e}") 

def delete_user(user_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE id=?", (user_id,))
    c.execute("DELETE FROM saved_analyses WHERE user_id=?", (user_id,))
    c.execute("DELETE FROM user_models WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()

    try:
        client = get_gspread_client()
        if client:
            spreadsheet = client.open_by_key(st.secrets["SPREADSHEET_ID"])
            sheet = spreadsheet.sheet1
            
            try:
                del_sheet = spreadsheet.worksheet("Deleted_Users")
            except gspread.exceptions.WorksheetNotFound:
                del_sheet = spreadsheet.add_worksheet(title="Deleted_Users", rows="1000", cols="10")
                del_sheet.append_row(["ID", "Role", "SignupDate", "PW", "agree_info", "DeletedDate"])

            all_values = sheet.get_all_values()
            target_row_index = -1
            row_data = None
            for i, row in enumerate(all_values):
                if row[0] == user_id:
                    target_row_index = i + 1
                    row_data = row
                    break
            
            if target_row_index != -1:
                kst_now_ts = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).strftime("%Y-%m-%d %H:%M:%S")
                # Extract only necessary columns: ID, Role, SignupDate, PW, agree_info, DeletedDate
                clean_row = [row_data[0], row_data[1], row_data[2], row_data[3], row_data[5] if len(row_data) > 5 else '', str(kst_now_ts)]
                del_sheet.append_row(clean_row)
                sheet.delete_rows(target_row_index)
    except Exception:
        pass

# [? ê·œ ê¸°ëŠ¥ 2] ?¬ê?????Deleted_Users ?œíŠ¸?ì„œ ?´ë‹¹ ? ì? ?? œ
def restore_from_deleted_sheet(user_id):
    try:
        client = get_gspread_client()
        if client:
            spreadsheet = client.open_by_key(st.secrets["SPREADSHEET_ID"])
            try:
                del_sheet = spreadsheet.worksheet("Deleted_Users")
                cell = del_sheet.find(user_id)
                if cell:
                    del_sheet.delete_rows(cell.row)
            except (gspread.exceptions.WorksheetNotFound, gspread.exceptions.CellNotFound):
                pass
    except Exception:
        pass

def save_analysis_to_db(user_id, filename, file_data):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    # [?˜ì •] ?€?œë?êµ??œê°„ ê¸°ì? ?€???¼ì‹œ ?¤ì •
    save_date = str(datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).strftime("%Y-%m-%d %H:%M:%S"))
    c.execute("INSERT INTO saved_analyses (user_id, filename, save_date, file_data) VALUES (?, ?, ?, ?)",
              (user_id, filename, save_date, file_data))
    conn.commit()
    conn.close()

def get_user_analyses(user_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT id, filename, save_date FROM saved_analyses WHERE user_id=? ORDER BY save_date DESC", (user_id,))
    rows = c.fetchall()
    conn.close()
    return rows

def get_analysis_file(analysis_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT filename, file_data FROM saved_analyses WHERE id=?", (analysis_id,))
    result = c.fetchone()
    conn.close()
    return result

def delete_analysis(analysis_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("DELETE FROM saved_analyses WHERE id=?", (analysis_id,))
    conn.commit()
    conn.close()

def save_user_model(user_id, model_dict):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    model_json = json.dumps(model_dict, ensure_ascii=False)
    c.execute("INSERT OR REPLACE INTO user_models (user_id, model_data) VALUES (?, ?)", (user_id, model_json))
    conn.commit()
    conn.close()

def load_user_model(user_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT model_data FROM user_models WHERE user_id=?", (user_id,))
    result = c.fetchone()
    conn.close()
    if result:
        return json.loads(result[0])
    return None

# -----------------------------------------------------------------------------
# Saaty(1980) AHP Functions
# -----------------------------------------------------------------------------
def get_ri(n):
    ri_dict = {1: 0.00, 2: 0.00, 3: 0.58, 4: 0.90, 5: 1.12, 6: 1.24, 7: 1.32, 8: 1.41, 9: 1.45, 10: 1.49}
    return ri_dict.get(n, 1.49)

def calculate_weights(matrix, method='geometric'):
    if method == 'arithmetic':
        col_sum = matrix.sum(axis=0)
        col_sum[col_sum == 0] = 1
        normalized_matrix = matrix / col_sum
        weights = normalized_matrix.mean(axis=1)
    else:
        geom_means = gmean(matrix, axis=1)
        weights = geom_means / geom_means.sum()
    return weights

def calculate_consistency(matrix, method='geometric'):
    n = matrix.shape[0]
    if n <= 2: return 0.0, 0.0, n
    weights = calculate_weights(matrix, method)
    weighted_sum = matrix.dot(weights)
    weights_safe = weights.copy()
    weights_safe[weights_safe == 0] = 1e-10
    lambda_values = weighted_sum / weights_safe
    lambda_max = lambda_values.mean()
    ci = (lambda_max - n) / (n - 1)
    ri = get_ri(n)
    cr = ci / ri if ri > 0 else 0.0
    return cr, ci, lambda_max

FUZZY_SCALE = {
    1: (1.0, 1.0, 1.0), 2: (1.0, 2.0, 3.0), 3: (2.0, 3.0, 4.0), 4: (3.0, 4.0, 5.0), 5: (4.0, 5.0, 6.0),
    6: (5.0, 6.0, 7.0), 7: (6.0, 7.0, 8.0), 8: (7.0, 8.0, 9.0), 9: (9.0, 9.0, 9.0)
}

def saaty_to_fuzzy(v):
    try:
        val = max(1, min(9, int(round(v)))) if v >= 1 else max(1, min(9, int(round(1/v))))
        tfn = FUZZY_SCALE[val]
        if v < 1: return (1.0/tfn[2], 1.0/tfn[1], 1.0/tfn[0])
        return tfn
    except: return (1.0, 1.0, 1.0)

def fuzzy_ahp_analysis(matrix):
    n = matrix.shape[0]
    fuzzy_mat = np.zeros((n, n, 3))
    for i in range(n):
        for j in range(n):
            if i == j: fuzzy_mat[i,j] = (1.0, 1.0, 1.0)
            else: fuzzy_mat[i,j] = saaty_to_fuzzy(matrix[i,j])
    row_sums = []
    for i in range(n): 
        row_sums.append((sum(fuzzy_mat[i,:,0]), sum(fuzzy_mat[i,:,1]), sum(fuzzy_mat[i,:,2])))
    t_l, t_m, t_u = sum(x[0] for x in row_sums), sum(x[1] for x in row_sums), sum(x[2] for x in row_sums)
    if t_l == 0: return np.ones(n)/n, row_sums
    Si = []
    for (l, m, u) in row_sums: 
        Si.append((l/t_u if t_u!=0 else 0.0, m/t_m if t_m!=0 else 0.0, u/t_l if t_l!=0 else 0.0))
    crisp_w = np.array([(l*m*u)**(1/3) for (l,m,u) in Si])
    norm_w = crisp_w / crisp_w.sum() if crisp_w.sum() != 0 else np.ones(n)/n
    return norm_w, Si

def improve_consistency(matrix, threshold, min_val, max_val, max_iter=500, learning_rate=0.6, method='geometric'):
    current_matrix = matrix.copy()
    n = current_matrix.shape[0]
    cr, ci, _unused_lambda = calculate_consistency(current_matrix, method)
    iterations = 0
    if cr <= threshold: return current_matrix, cr, iterations, False
    
    # ?ì‚¼ê°??‰ë ¬???¸ë±??ì¶”ì¶œ (k=1?€ ?€ê°ì„  ?œì™¸)
    triu_indices = np.triu_indices(n, k=1)
    
    for it in range(max_iter):
        if cr <= threshold: break
        
        # ?¼ê????ˆëŠ” ?‰ë ¬ ?ì„±
        w = calculate_weights(current_matrix, method)
        consistent_matrix = np.outer(w, 1/w)
        
        # ? í˜• ê²°í•© ë°??€ê°ì„  ë³µêµ¬
        new_matrix = (current_matrix * (1 - learning_rate)) + (consistent_matrix * learning_rate)
        np.fill_diagonal(new_matrix, 1.0)
        
        # ?ì‚¼ê°??‰ë ¬ ?”ì†Œ ì¶”ì¶œ
        vals = new_matrix[triu_indices]
        
        # ë²¡í„°?”ëœ ?????ë°??¤ì??¼ë§ ë¡œì§
        # 1.0 ê¸°ì? ë³€??
        temp_raw = np.where(vals == 1.0, 1.0, 
                    np.where(vals > 1.0, -np.round(vals), 
                    np.round(1.0/vals)))
        
        # ë²”ìœ„ ?œí•œ (min_val, max_val)
        temp_raw = np.clip(temp_raw, min_val, max_val)
        
        # ?€??ë³´ì •
        abs_raw = np.abs(temp_raw)
        signs = np.sign(temp_raw)
        # ì§ìˆ˜??ê²½ìš° -1 (ìµœì†Œ 1 ? ì?)
        abs_raw = np.where((abs_raw % 2 == 0) & (abs_raw != 0), np.maximum(1, abs_raw - 1), abs_raw)
        # 0??ê²½ìš° 1ë¡?ì²˜ë¦¬
        temp_raw = np.where(temp_raw == 0, 1, (signs * abs_raw)).astype(int)
        
        # ?•ìˆ˜?”ëœ ê°’ì„ ?¤ì‹œ AHP ?¤ì??¼ë¡œ ë³€?˜í•˜???‰ë ¬???¼ê´„ ë°˜ì˜
        final_vals = np.where(temp_raw == 0, 1.0,
                      np.where(temp_raw < 0, np.abs(temp_raw).astype(float),
                      np.where(temp_raw == 1, 1.0, 1.0 / temp_raw)))
        
        new_matrix[triu_indices] = final_vals
        new_matrix.T[triu_indices] = 1.0 / final_vals
        
        current_matrix = new_matrix
        cr, ci, _unused_lambda = calculate_consistency(current_matrix, method)
        iterations += 1
        
    was_corrected = iterations > 0
    return current_matrix, cr, iterations, was_corrected

def parse_input_value(val):
    if val == 0: return 1.0
    elif val < 0: return abs(val)
    elif val == 1: return 1.0
    else: return 1.0 / val

def infer_factors_from_columns(cols):
    m = len(cols)
    delta = 1 + 8 * m
    n = int((1 + np.sqrt(delta)) / 2)
    extracted_factors = []
    seen = set()
    for c in cols:
        parts = str(c).split('_')
        for p in parts:
            p_str = p.strip()
            if p_str not in seen:
                seen.add(p_str)
                extracted_factors.append(p_str)
    if len(extracted_factors) == n:
        factors = extracted_factors 
    else:
        factors = [f"F{i+1}" for i in range(n)]
    return factors, n

def calculate_pairwise_ttest(df, factors):
    n = len(factors)
    p_values = pd.DataFrame(index=factors, columns=factors)
    weight_cols = [f"Weight_{f}" for f in factors]
    for i in range(n):
        for j in range(n):
            if i == j:
                p_values.iloc[i, j] = 1.0
            else:
                col1 = weight_cols[i]
                col2 = weight_cols[j]
                if col1 in df.columns and col2 in df.columns and len(df) > 1:
                    try:
                        _unused_t, p = ttest_rel(df[col1], df[col2], nan_policy='omit')
                        p_values.iloc[i, j] = p
                    except:
                        p_values.iloc[i, j] = np.nan
                else:
                    p_values.iloc[i, j] = np.nan
    return p_values

def process_single_sheet(df, cr_threshold, max_iter, learning_rate, method='geometric', ahp_method='traditional'):
    meta_cols = df.columns[:2]
    comp_cols = df.columns[2:]
    factors, n = infer_factors_from_columns(comp_cols)
    
    # ?œíŠ¸ ?„ì²´ ?°ì´?°ì˜ ë¡œìš°?°ì´??ìµœë?ê°?ìµœì†Ÿê°?ê³„ì‚°
    all_comp_values = pd.to_numeric(df[comp_cols].values.flatten(), errors='coerce')
    valid_comp_values = all_comp_values[~np.isnan(all_comp_values)]
    if len(valid_comp_values) > 0:
        sheet_min = int(np.min(valid_comp_values))
        sheet_max = int(np.max(valid_comp_values))
    else:
        sheet_min = -9
        sheet_max = 9
    
    results_list = []
    excluded_list = []
    excluded_count = 0
    for idx, row in df.iterrows():
        respondent_id = row.iloc[0]
        respondent_type = row.iloc[1]
        matrix = np.eye(n)
        
        # ?ë³¸ Rawdataë¥??•ìˆ˜ ?•íƒœ(-9 ~ 9)ë¡?ì¶”ì¶œ
        raw_values = []
        col_idx = 0
        for i in range(n):
            for j in range(i + 1, n):
                if col_idx < len(comp_cols):
                    raw_val = row[comp_cols[col_idx]]
                    raw_values.append(raw_val)
                    ahp_val = parse_input_value(raw_val)
                    matrix[i, j] = ahp_val
                    matrix[j, i] = 1.0 / ahp_val
                    col_idx += 1
        
        orig_cr, orig_ci, _unused_lambda = calculate_consistency(matrix, method)
        final_matrix = matrix.copy()
        final_cr = orig_cr
        iterations = 0
        corrected_flag = False
        if orig_cr > cr_threshold:
            final_matrix, final_cr, iterations, corrected_flag = improve_consistency(
                matrix, cr_threshold, sheet_min, sheet_max, max_iter=max_iter, learning_rate=learning_rate, method=method
            )
        
        # ë§Œì•½ ìµœë? ë°˜ë³µ???˜í–‰?ˆìŒ?ë„ CR???„ê³„ê°’ì„ ì´ˆê³¼??ê²½ìš° ?´ë‹¹ ?‘ë‹µ???œì™¸
        if final_cr > cr_threshold:
            excluded_count += 1
            ex_res = {"ID": respondent_id, "Type": respondent_type}
            for k, col_name in enumerate(comp_cols):
                ex_res[col_name] = raw_values[k]
            ex_res["CR"] = final_cr
            excluded_list.append(ex_res)
            continue

        # ë³´ì • ??Rawdata (????? ?ì‚¼ê°??‰ë ¬ ê°’ì„ ?•ìˆ˜ ?€ì¹??¤ì??¼ë¡œ ë³€??
        final_raw_values = []
        for i in range(n):
            for j in range(i + 1, n):
                val = final_matrix[i, j]
                if val == 1.0: final_raw_val = 1
                elif val > 1.0: final_raw_val = -int(round(val)) # ?¼ìª½ ?°ì„  (?Œìˆ˜)
                else: final_raw_val = int(round(1.0/val)) # ?¤ë¥¸ìª??°ì„  (?‘ìˆ˜)
                final_raw_values.append(final_raw_val)

        _unused_cr, final_ci, _unused_lambda = calculate_consistency(final_matrix, method)
        if ahp_method == 'fuzzy':
            final_weights, final_Si = fuzzy_ahp_analysis(final_matrix)
        else:
            final_weights = calculate_weights(final_matrix, method)
        
        # ê²°ê³¼ ?•ì…”?ˆë¦¬ êµ¬ì„± (?”ì²­?¬í•­ 5 ?¬ë°°ì¹?ë°˜ì˜)
        res = {
            "ID": respondent_id,
            "Type": respondent_type
        }
        
        # [?˜ì •] 1. ë³´ì • ??Rawdata ?½ì…
        for k, col_name in enumerate(comp_cols):
            res[f"Raw_Orig_{col_name}"] = raw_values[k]
        
        # [?˜ì •] 2. Original_CI, Original_CR ?œì„œ ë°°ì¹˜
        res["Original_CI"] = orig_ci
        res["Original_CR"] = orig_cr
        
        # [?˜ì •] 3. ë³´ì • ??Rawdata ?½ì…
        for k, col_name in enumerate(comp_cols):
            res[f"Raw_Final_{col_name}"] = final_raw_values[k]
            
        # [?˜ì •] 4. Final_CI, Final_CR ?œì„œ ë°°ì¹˜
        res["Final_CI"] = final_ci
        res["Final_CR"] = final_cr
        
        res["Iterations"] = iterations
        res["Corrected"] = corrected_flag
        res["Matrix_Object"] = final_matrix 
        res["Orig_Matrix_Object"] = matrix.copy()
        
        for f_idx, f_name in enumerate(factors):
            res[f"Weight_{f_name}"] = final_weights[f_idx]
            if ahp_method == 'fuzzy':
                l, m, u = final_Si[f_idx]
                res[f"L_{f_name}"] = l
                res[f"M_{f_name}"] = m
                res[f"U_{f_name}"] = u
                res[f"Crisp_{f_name}"] = (l*m*u)**(1/3)
            
        results_list.append(res)
        
    results_df = pd.DataFrame(results_list)
    excluded_df = pd.DataFrame(excluded_list)
    return results_df, factors, excluded_count, excluded_df

import itertools
import numpy as np

def export_to_template_excel(raw_df, demo_df, ahp_model, tier_level=2):
    import io
    import pandas as pd
    
    excel_buffer = io.BytesIO()
    with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
        base_cols = ["ID", "Type"]
        
        # 1. Main Criteria
        main_criteria = ahp_model.get("main", [])
        main_pairs = []
        for i in range(len(main_criteria)):
            for j in range(i + 1, len(main_criteria)):
                main_pairs.append(f"{main_criteria[i]}_{main_criteria[j]}")
        main_cols = [c for c in base_cols if c in raw_df.columns] + [p for p in main_pairs if p in raw_df.columns]
        
        df_main = raw_df[main_cols].copy()
        df_main.to_excel(writer, index=False, sheet_name="Main_Criteria")
        
        # 2. Sub Criteria
        sub_criteria_map = ahp_model.get("subs", {})
        for main_c, subs in sub_criteria_map.items():
            if len(subs) >= 2:
                sub_pairs = []
                for i in range(len(subs)):
                    for j in range(i + 1, len(subs)):
                        sub_pairs.append(f"{subs[i]}_{subs[j]}")
                sub_cols = [c for c in base_cols if c in raw_df.columns] + [p for p in sub_pairs if p in raw_df.columns]
                
                df_sub = raw_df[sub_cols].copy()
                safe_sheet_name = str(main_c)[:31]
                df_sub.to_excel(writer, index=False, sheet_name=safe_sheet_name)
                
        # 3. Sub-sub Criteria (Tier 3)
        if int(tier_level) == 3:
            sub_sub_map = ahp_model.get("sub_subs", {})
            for main_c, subs in sub_criteria_map.items():
                for sub_c in subs:
                    sub_subs = sub_sub_map.get(sub_c, [])
                    if len(sub_subs) >= 2:
                        sub_sub_pairs = []
                        for i in range(len(sub_subs)):
                            for j in range(i + 1, len(sub_subs)):
                                sub_sub_pairs.append(f"{sub_subs[i]}_{sub_subs[j]}")
                        ss_cols = [c for c in base_cols if c in raw_df.columns] + [p for p in sub_sub_pairs if p in raw_df.columns]
                        
                        df_sub_sub = raw_df[ss_cols].copy()
                        safe_sheet_name = str(sub_c)[:31]
                        df_sub_sub.to_excel(writer, index=False, sheet_name=safe_sheet_name)
                        
        # 4. Demographic Data
        if demo_df is not None and not demo_df.empty:
            demo_df.to_excel(writer, index=False, sheet_name="Demographic_Data")
            
    return excel_buffer

def create_sample_excel_v3():
    output = io.BytesIO()
    is_en = (st.session_state.get('lang', 'ko') == 'en')
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        if is_en:
            main_list = ["Functionality", "Design", "Economy"]
            subs = {"Functionality": ["Hardware", "Software"], "Design": ["Appearance", "Usability"], "Economy": ["Device Price", "Maintenance"]}
            sub_subs = {"Hardware": ["Camera", "Battery", "Processor"], "Software": ["OS", "Default Apps"], "Appearance": ["Color", "Material"], "Usability": [], "Device Price": ["Lump Sum", "Installment"], "Maintenance": ["Plan", "Repair"]}
        else:
            main_list = ["ê¸°ëŠ¥??, "?”ì??, "ê²½ì œ??]
            subs = {"ê¸°ëŠ¥??: ["?˜ë“œ?¨ì–´", "?Œí”„?¸ì›¨??], "?”ì??: ["?¸ê?", "?¸ì˜??], "ê²½ì œ??: ["?¨ë§ê¸°ê?ê²?, "? ì?ë¹„ìš©"]}
            sub_subs = {"?˜ë“œ?¨ì–´": ["ì¹´ë©”??, "ë°°í„°ë¦?, "?„ë¡œ?¸ì„œ"], "?Œí”„?¸ì›¨??: ["?´ì˜ì²´ì œ", "ê¸°ë³¸??], "?¸ê?": ["?‰ìƒ", "?¬ì§ˆ"], "?¸ì˜??: [], "?¨ë§ê¸°ê?ê²?: ["?¼ì‹œë¶?, "? ë?"], "? ì?ë¹„ìš©": ["?µì‹ ?”ê¸ˆ", "ASë¹„ìš©"]}
            
        def _get_dummy_data(cols, num_respondents=5):
            # cols contains ["ID", "Type", pair1, pair2...]
            data = []
            for i in range(num_respondents):
                row = [i+1, "?„ë¬¸ê°€" if not is_en else "Expert"]
                for _ in range(len(cols)-2):
                    row.append(int(np.random.choice([1, 3, 5, -3, -5])))
                data.append(row)
            return data
            
        main_pairs = list(itertools.combinations(main_list, 2))
        main_cols = ["ID", "Type"] + [f"{a}_{b}" for a, b in main_pairs]
        df_main = pd.DataFrame(_get_dummy_data(main_cols), columns=main_cols)
        df_main.to_excel(writer, sheet_name="Main_Criteria", index=False)
        
        for mc in main_list:
            sub_list = subs.get(mc, [])
            if len(sub_list) < 2:
                df_sub = pd.DataFrame(columns=["ID", "Type"])
            else:
                sub_pairs = list(itertools.combinations(sub_list, 2))
                sub_cols = ["ID", "Type"] + [f"{a}_{b}" for a, b in sub_pairs]
                df_sub = pd.DataFrame(_get_dummy_data(sub_cols), columns=sub_cols)
            df_sub.to_excel(writer, sheet_name=mc[:31], index=False)
            
            for sub_c in sub_list:
                ss_list = sub_subs.get(sub_c, [])
                if len(ss_list) < 2:
                    df_ss = pd.DataFrame(columns=["ID", "Type"])
                else:
                    ss_pairs = list(itertools.combinations(ss_list, 2))
                    ss_cols = ["ID", "Type"] + [f"{a}_{b}" for a, b in ss_pairs]
                    df_ss = pd.DataFrame(_get_dummy_data(ss_cols), columns=ss_cols)
                df_ss.to_excel(writer, sheet_name=f"{mc[:15]}_{sub_c[:15]}", index=False)
                
    output.seek(0)
    return output.getvalue()

def create_sample_excel():
    output = io.BytesIO()
    is_en = (st.session_state.get('lang', 'ko') == 'en')
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        if is_en:
            main_cols = ["ID", "Type", "Governance_Planning", "Governance_Feasibility", "Governance_Effectiveness", 
                          "Planning_Feasibility", "Planning_Effectiveness", "Feasibility_Effectiveness"]
            main_data = [
                [1, "Expert", -3, -3, 3, 1, 1, 1],                
                [2, "Expert", -5, 3, 3, 3, 3, 3],        
                [3, "General", 5, 1, 3, -5, -5, -3],
                [4, "General", -3, -3, 3, -3, 3, -3],
                [5, "Official", -5, 5, -5, -5, 5, -5]
            ]
            df_main = pd.DataFrame(main_data, columns=main_cols)
            df_main.to_excel(writer, sheet_name="Main_Criteria", index=False)
            
            inconsistent_pattern = [
                [1, "Expert", 1, -3, 1],
                [2, "Expert", -3, -3, -3],
                [3, "General", 3, -3, 1],
                [4, "General", -3, 5, 3],
                [5, "Official", -3, 5, 3]
            ]
            sub1_cols = ["ID", "Type", "AdminSupport_Community", "AdminSupport_PM", "Community_PM"]
            pd.DataFrame(inconsistent_pattern, columns=sub1_cols).to_excel(writer, sheet_name="Governance", index=False)
            sub2_cols = ["ID", "Type", "IssueFit_AlternativeFit", "IssueFit_GoalClarity", "AlternativeFit_GoalClarity"]
            pd.DataFrame(inconsistent_pattern, columns=sub2_cols).to_excel(writer, sheet_name="Planning", index=False)
            sub3_cols = ["ID", "Type", "LandAcquisition_ProjectDetail", "LandAcquisition_CostFit", "ProjectDetail_CostFit"]
            pd.DataFrame(inconsistent_pattern, columns=sub3_cols).to_excel(writer, sheet_name="Feasibility", index=False)
            sub4_cols = ["ID", "Type", "Economic_Social", "Economic_Performance", "Social_Performance"]
            pd.DataFrame(inconsistent_pattern, columns=sub4_cols).to_excel(writer, sheet_name="Effectiveness", index=False)
        else:
            main_cols = ["ID", "Type", "ê±°ë²„?ŒìŠ¤_ê³„íš?€?¹ì„±", "ê±°ë²„?ŒìŠ¤_?¤í˜„ê°€?¥ì„±", "ê±°ë²„?ŒìŠ¤_?¬ì—…?¨ê³¼", 
                          "ê³„íš?€?¹ì„±_?¤í˜„ê°€?¥ì„±", "ê³„íš?€?¹ì„±_?¬ì—…?¨ê³¼", "?¤í˜„ê°€?¥ì„±_?¬ì—…?¨ê³¼"]
            main_data = [
                [1, "?„ë¬¸ê°€",-3,	-3, 3, 1, 1, 1],                
                [2, "?„ë¬¸ê°€", -5, 3, 3, 3, 3, 3],        
                [3, "?¼ë°˜", 5, 1, 3, -5, -5, -3],
                [4, "?¼ë°˜", -3,-3, 3, -3, 3, -3],
                [5, "ê³µë¬´??, -5, 5, -5, -5, 5, -5]
            ]
            df_main = pd.DataFrame(main_data, columns=main_cols)
            df_main.to_excel(writer, sheet_name="Main_Criteria", index=False)
            
            inconsistent_pattern = [
                [1, "?„ë¬¸ê°€", 1, -3, 1],
                [2, "?„ë¬¸ê°€", -3, -3, -3],
                [3, "?¼ë°˜", 3, -3, 1],
                [4, "?¼ë°˜", -3, 5, 3],
                [5, "ê³µë¬´??, -3, 5, 3]
            ]
            sub1_cols = ["ID", "Type", "?‰ì •ì§€??ì§€??³µ?™ì²´", "?‰ì •ì§€??ì´ê´„?¬ì—…ê´€ë¦¬ì", "ì§€??³µ?™ì²´_ì´ê´„?¬ì—…ê´€ë¦¬ì"]
            pd.DataFrame(inconsistent_pattern, columns=sub1_cols).to_excel(writer, sheet_name="ê±°ë²„?ŒìŠ¤", index=False)
            sub2_cols = ["ID", "Type", "?„ì•ˆ?ì •???€?ˆì ?•ì„±", "?„ì•ˆ?ì •??ëª©í‘œêµ¬ì²´??, "?€?ˆì ?•ì„±_ëª©í‘œêµ¬ì²´??]
            pd.DataFrame(inconsistent_pattern, columns=sub2_cols).to_excel(writer, sheet_name="ê³„íš?€?¹ì„±", index=False)
            sub3_cols = ["ID", "Type", "ë¶€ì§€?•ë³´_?¬ì—…êµ¬ì²´??, "ë¶€ì§€?•ë³´_?¬ì—…ë¹„ì ?•ì„±", "?¬ì—…êµ¬ì²´???¬ì—…ë¹„ì ?•ì„±"]
            pd.DataFrame(inconsistent_pattern, columns=sub3_cols).to_excel(writer, sheet_name="?¤í˜„ê°€?¥ì„±", index=False)
            sub4_cols = ["ID", "Type", "ê²½ì œ?íš¨ê³??¬íšŒ?íš¨ê³?, "ê²½ì œ?íš¨ê³??±ê³¼ê´€ë¦?, "?¬íšŒ?íš¨ê³??±ê³¼ê´€ë¦?]
            pd.DataFrame(inconsistent_pattern, columns=sub4_cols).to_excel(writer, sheet_name="?¬ì—…?¨ê³¼", index=False)
    output.seek(0)
    return output

def calculate_anova_and_posthoc(full_data):
    results = []
    unique_factors = full_data['Factor'].unique()
    
    for factor in unique_factors:
        subset = full_data[full_data['Factor'] == factor]
        groups = [group['Global_Weight'].values for name, group in subset.groupby('Type')]
        
        if len(groups) < 2:
            continue
            
        f_stat, p_val = f_oneway(*groups)
        
        row = {
            "?”ì¸": factor,
            "F-ê°?: f_stat,
            "P-Value": p_val,
            "? ì˜??: "? ì˜?? if p_val < 0.05 else "? ì˜?˜ì? ?ŠìŒ",
            "?¬í›„ê²€??Tukey HSD)": ""
        }
        
        if p_val < 0.05 and STATSMODELS_AVAILABLE:
            try:
                tukey = pairwise_tukeyhsd(endog=subset['Global_Weight'], groups=subset['Type'], alpha=0.05)
                tukey_df = pd.DataFrame(data=tukey.summary().data[1:], columns=tukey.summary().data[0])
                sig_pairs = tukey_df[tukey_df['reject'] == True]
                if not sig_pairs.empty:
                    pairs_str = []
                    for idx_row, r in sig_pairs.iterrows():
                        pairs_str.append(f"{r['group1']} vs {r['group2']}")
                    row["?¬í›„ê²€??Tukey HSD)"] = ", ".join(pairs_str) + " ì°¨ì´ ?ˆìŒ"
                else:
                    row["?¬í›„ê²€??Tukey HSD)"] = "ì§‘ë‹¨ ê°?êµ¬ì²´??ì°¨ì´ ë°œê²¬ ëª»í•¨"
            except Exception as e:
                row["?¬í›„ê²€??Tukey HSD)"] = "ê³„ì‚° ?¤ë¥˜"
        
        results.append(row)
        
    return pd.DataFrame(results)

# -----------------------------------------------------------------------------
# [?? œ] ì¢‹ì•„??ê¸°ëŠ¥ ?œê±°??
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# 2. Setup & Layout
# -----------------------------------------------------------------------------

if not st.session_state.get('_db_initialized'):
    init_db()
    st.session_state._db_initialized = True

# CSS ìµœì ??


if 'user_id' not in st.session_state: st.session_state.user_id = None
if 'user_role' not in st.session_state: st.session_state.user_role = None
if 'expiry_date' not in st.session_state: st.session_state.expiry_date = None
if 'admin_mode' not in st.session_state: st.session_state.admin_mode = False
if 'model_structure' not in st.session_state: st.session_state.model_structure = {}
if 'page' not in st.session_state: st.session_state.page = "main"
if 'signup_paypal_user' not in st.session_state: st.session_state.signup_paypal_user = None

# Check for foreign access once per session
check_foreign_access()

# -----------------------------------------------------------------------------
# ì¿¼ë¦¬ ë§¤ê°œë³€???•ì¸ (?¤êµ­??? íƒ ë°?ê²°ì œ ?„ë£Œ ì²˜ë¦¬)
# -----------------------------------------------------------------------------
try:
    q_params = st.query_params
except AttributeError:
    try:
        q_params = st.experimental_get_query_params()
    except:
        q_params = {}

# -----------------------------------------------------------------------------
# êµ¬ê? OAuth 2.0 ì½œë°± ì²˜ë¦¬
# -----------------------------------------------------------------------------
if "code" in q_params and st.session_state.user_id:
    import os
    if os.name == 'nt':
        redirect_uri = "http://localhost:8501/"
    else:
        redirect_uri = "https://ahpkrj.streamlit.app/"
        
    code_val = q_params["code"]
    if isinstance(code_val, list):
        code_val = code_val[0]
        
    from survey_manager import get_google_oauth_flow
    flow = get_google_oauth_flow(redirect_uri)
    if flow:
        try:
            flow.fetch_token(code=code_val)
            creds = flow.credentials
            
            import sqlite3
            import json
            conn = sqlite3.connect('users.db')
            c = conn.cursor()
            c.execute("""
                INSERT OR REPLACE INTO user_google_credentials 
                (user_id, token, refresh_token, token_uri, client_id, client_secret, scopes, expiry)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                st.session_state.user_id,
                creds.token,
                creds.refresh_token,
                creds.token_uri,
                creds.client_id,
                creds.client_secret,
                json.dumps(creds.scopes),
                creds.expiry.isoformat() if hasattr(creds.expiry, 'isoformat') else str(creds.expiry)
            ))
            conn.commit()
            conn.close()
            
            st.success("?‰ êµ¬ê? ê³„ì • ?°ë™???„ë£Œ?˜ì—ˆ?µë‹ˆ??")
            st.query_params.clear()
            st.rerun()
        except Exception as oauth_err:
            st.error(f"êµ¬ê? ê³„ì • ?°ë™ ?¤íŒ¨: {oauth_err}")
            st.query_params.clear()


# -----------------------------------------------------------------------------
# [? ê·œ] ?™ì  ?¼ìš°??- ?‘ë‹µ???¤ë¬¸ ì°¸ì—¬ SPA (Single Page Application)
# -----------------------------------------------------------------------------


if "preview_id" in q_params or "survey_id" in q_params:
    is_preview_mode = "preview_id" in q_params
    
    from survey_manager import load_survey_metadata, save_response_to_sheet, generate_pairwise_combinations, calculate_matrix_cr
    
    if is_preview_mode:
        preview_id_param = q_params["preview_id"]
        if isinstance(preview_id_param, list):
            preview_id_param = preview_id_param[0]
            
        st.info("? ï¸ [ë¯¸ë¦¬ë³´ê¸° ëª¨ë“œ] ???”ë©´?€ ?‘ë‹µ?ê? ë³´ê²Œ ???”ë©´???¤ì‹œê°?ë¯¸ë¦¬ë³´ê¸°?…ë‹ˆ?? ?…ë ¥???°ì´?°ëŠ” ?œì¶œ?˜ì? ?ŠìŠµ?ˆë‹¤.")
        
        preview_file_path = f"temp_previews/preview_{preview_id_param}.json"
        if os.path.exists(preview_file_path):
            with open(preview_file_path, "r", encoding="utf-8") as f:
                survey_meta = json.load(f)
        else:
            st.warning("? ï¸ ë¯¸ë¦¬ë³´ê¸° ?°ì´?°ë? ë¶ˆëŸ¬?????†ìŠµ?ˆë‹¤.")
            st.markdown("""
#### ?“‹ ë¯¸ë¦¬ë³´ê¸° ?„ì— ?„ë˜ ?¬í•­??ë¨¼ì? ?„ë£Œ??ì£¼ì„¸??

1. **?¤ë¬¸ì§€ ?¤ì • ?„ë£Œ** ??ë©”ì¸ ?˜ì´ì§€?ì„œ AHP ëª¨ë¸ êµ¬ì¡°, ?”ì¸, ì²™ë„ ???¤ë¬¸ ?¤ì •??ëª¨ë‘ ?…ë ¥?©ë‹ˆ??
2. **êµ¬ê? ?¤í”„?ˆë“œ?œíŠ¸ ?°ë™** ???¹ì…˜ 7?ì„œ ë³¸ì¸??êµ¬ê? ?¤í”„?ˆë“œ?œíŠ¸ URL ?ëŠ” IDë¥??…ë ¥?˜ê³ , ?œë¹„??ê³„ì • ?´ë©”??`ahp-master-v2@ahp-login.iam.gserviceaccount.com`)???¸ì§‘?ë¡œ ê³µìœ ?©ë‹ˆ??
3. **ë¯¸ë¦¬ë³´ê¸° ë²„íŠ¼ ?´ë¦­** ???¤ì •???„ë£Œ????"?‘ï¸??¤ë¬¸ì§€ ?‘ë‹µ ?”ë©´ ë¯¸ë¦¬ë³´ê¸°" ë²„íŠ¼???¤ì‹œ ?ŒëŸ¬ ì£¼ì„¸??

> ?’¡ ?¤ë¬¸ ?¤ì • ?˜ì´ì§€?ì„œ ?´ìš©???…ë ¥????ë¯¸ë¦¬ë³´ê¸°ë¥??ŒëŸ¬???•ìƒ?ìœ¼ë¡??œì‹œ?©ë‹ˆ??
            """)
            st.stop()
            
        survey_id_param = f"preview_{preview_id_param}"
    else:
        survey_id_param = q_params["survey_id"]
        if isinstance(survey_id_param, list):
            survey_id_param = survey_id_param[0]

    submitted_key = f"survey_submitted_{survey_id_param}"
    if st.session_state.get(submitted_key):
        # 1. HTML/CSSë¥??´ìš©??ëª¨ë˜?˜ê³  ?˜ë ¤??ê°ì‚¬ ì¹´ë“œ UI ?Œë”ë§?
        thank_you_title = _("?¤ë¬¸ ?œì¶œ???±ê³µ?ìœ¼ë¡??„ë£Œ?˜ì—ˆ?µë‹ˆ??", "Survey Submitted Successfully!")
        thank_you_body = _(
            "?˜ì‚¬ê²°ì • ?°ì„ ?œìœ„ ë¶„ì„???„í•´ ?Œì¤‘???œê°„ ?´ì–´ ?‘ë‹µ??ì£¼ì…”???€?¨íˆ ê°ì‚¬?©ë‹ˆ?? <br>ë³´ë‚´ì£¼ì‹  ?µë??€ ?ˆì „?˜ê²Œ ê¸°ë¡?˜ì—ˆ?¼ë©° ?°êµ¬ ë¶„ì„??ê·€ì¤‘í•œ ?ë£Œë¡??œìš©?©ë‹ˆ??",
            "Thank you very much for taking your valuable time to respond for decision-making priority analysis. <br>Your responses have been safely recorded and will be used as valuable data for research analysis."
        )
        thank_you_note = _(
            "??ë¸Œë¼?°ì? ë³´ì•ˆ ê·œì •???°ë¼ 'ì°??«ê¸°' ë²„íŠ¼???™ì‘?˜ì? ?Šì„ ???ˆìŠµ?ˆë‹¤. <br>?™ì‘?˜ì? ?Šì„ ê²½ìš° ?„ì¬ ?´ë ¤?ˆëŠ” <strong>ë¸Œë¼?°ì? ??˜ X ë²„íŠ¼</strong>??ì§ì ‘ ?ŒëŸ¬ ì¢…ë£Œ??ì£¼ì„¸??",
            "??Depending on browser security policies, the 'Close Window' button may not work. <br>If it does not work, please close the current <strong>browser tab</strong> manually."
        )
        st.markdown(f"""
        <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 60px 20px; text-align: center; font-family: 'Inter', sans-serif; background-color: #ffffff; border-radius: 12px; box-shadow: 0 4px 24px rgba(0,0,0,0.06); margin-top: 40px; border: 1px solid #e2e8f0;">
            <div style="background-color: #ecfdf5; border: 1px solid #a7f3d0; border-radius: 50%; width: 90px; height: 90px; display: flex; align-items: center; justify-content: center; margin-bottom: 24px; box-shadow: 0 4px 10px rgba(16, 185, 129, 0.1);">
                <span style="font-size: 45px; color: #10b981;">?‰</span>
            </div>
            <h1 style="font-size: 2.2rem; color: #1f2937; font-weight: 800; margin-bottom: 16px; font-family: 'Outfit', sans-serif;">{thank_you_title}</h1>
            <p style="font-size: 1.1rem; color: #4b5563; max-width: 550px; line-height: 1.6; margin-bottom: 30px; word-break: keep-all;">
                {thank_you_body}
            </p>
            <div style="font-size: 0.85rem; color: #9ca3af; margin-top: 5px; margin-bottom: 15px; line-height: 1.5; word-break: keep-all;">
                {thank_you_note}
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # 2. ì°??«ê¸° ë²„íŠ¼ ?Œë”ë§?ë°??ë°”?¤í¬ë¦½íŠ¸ ?¤í–‰ ?¸ë¦¬ê±?
        import streamlit.components.v1 as components
        close_clicked = st.button(_("?šª ì°??«ê¸°", "?šª Close Window"), use_container_width=True)
        if close_clicked:
            components.html("""
            <script>
                // Try standard close
                window.close();
                // Try parent window close
                try {
                    window.parent.close();
                } catch(e) {}
                // Workaround for some browsers
                try {
                    window.open('', '_self', '').close();
                } catch(e) {}
                // Fallback: redirect to a blank page if closing fails (which is highly likely)
                setTimeout(function() {
                    window.location.href = "about:blank";
                }, 300);
            </script>
            """, height=0, width=0)
            
        st.stop()
            
    st.info(_("? ï¸ ?˜ì´ì§€ë¥??ˆë¡œê³ ì¹¨?˜ê±°???´íƒˆ ???…ë ¥???•ë³´ê°€ ëª¨ë‘ ì´ˆê¸°?”ë˜??ì£¼ì˜ ë°”ë?ˆë‹¤.", "? ï¸ Please note that all entered information will be initialized if you refresh or leave the page."))
    
    # ë¯¸ë¦¬ë³´ê¸° ëª¨ë“œê°€ ?„ë‹Œ ê²½ìš°?ë§Œ êµ¬ê? ?œíŠ¸?ì„œ ë©”í??°ì´?°ë? ë¡œë“œ
    if not is_preview_mode:
        survey_meta = load_survey_metadata(survey_id_param)
        if not survey_meta:
            st.error(_("?¤ë¬¸ì§€ë¥?ë¶ˆëŸ¬?????†ìŠµ?ˆë‹¤. ?¬ë°”ë¥?ë§í¬?¸ì? ?•ì¸??ì£¼ì„¸??", "Failed to load the survey. Please check if the link is correct."))
            st.stop()
        
        # ?¸ì…˜ ?íƒœ ê¸°ë°˜ 1?Œì„± ë°©ë¬¸ ì¹´ìš´??ì¦ê? ì²˜ë¦¬ (?ˆë¡œê³ ì¹¨ ë°©ì????¸ì…˜ë³€???œìš©)
        if f"visited_survey_{survey_id_param}" not in st.session_state:
            from survey_manager import increment_survey_visit
            increment_survey_visit(survey_id_param)
            st.session_state[f"visited_survey_{survey_id_param}"] = True
        
    survey_title = survey_meta.get('Title', 'AHP ?¨ë¼???¤ë¬¸ì¡°ì‚¬')
    if survey_title in ['AHP ?¨ë¼???¤ë¬¸ì¡°ì‚¬', '?œì¡°???‘ë™ë¡œë´‡ ?„ì… ?”ì¸ ì¤‘ìš”??ë¶„ì„???„í•œ ?„ë¬¸ê°€ AHP ?¤ë¬¸']:
        survey_title = _(survey_title, 'Expert AHP Survey on the Importance of Factors for Adopting Manufacturing Collaborative Robots')
    st.title(survey_title)
    
    # ì¡°ì‚¬ ëª©ì  ë°??ˆë‚´ë¬? ?¤ë¬¸ ?´ë‹¹???´ë©”???œì‹œ (ê¹”ë”???”ì???ìš©)
    survey_desc = survey_meta.get("Description", "")
    survey_desc = translate_definition_if_default("Description", survey_desc)
    
    survey_email = survey_meta.get("Admin_Email", "temp@ahpmaster.com")
    if not survey_email or str(survey_email).strip() == "":
        survey_email = "temp@ahpmaster.com"
    
    if survey_desc or survey_email:
        email_html = (
            f'<div style="margin-top: 10px; font-size: 0.88rem; color: #475569; border-top: 1px solid #e2e8f0; padding-top: 8px; display: flex; align-items: center; gap: 6px;">'
            f'<span style="font-weight: 600;">?“§ ' + _("?¤ë¬¸ ?´ë‹¹??ë¬¸ì˜:", "Contact Survey Administrator:") + '</span>'
            f'<a href="mailto:{survey_email}" style="color: #2563eb; text-decoration: none; font-weight: 500;">{survey_email}</a>'
            f'</div>'
        ) if survey_email else ""
        
        desc_box_html = (
            f'<div style="background-color: #f8fafc; border: 1px solid #e2e8f0; padding: 16px; border-radius: 8px; margin-bottom: 20px; line-height: 1.6; box-shadow: 0 1px 3px rgba(0,0,0,0.02);">'
            f'<div style="font-size: 0.95rem; color: #334155; font-weight: 400; white-space: pre-wrap;">{survey_desc}</div>'
            f'{email_html}'
            f'</div>'
        )
        st.markdown(desc_box_html, unsafe_allow_html=True)

    
    # ëª¨ë¸ ?•ë³´?€ ?¸êµ¬?µê³„ ì¶”ì¶œ
    ahp_model = survey_meta["AHP_Model_JSON"]
    demographics = survey_meta["Demographics"]
    definitions = survey_meta["Definitions"]
    cr_limit = survey_meta.get("CR_Limit")
    if cr_limit is not None and str(cr_limit).lower() != "none":
        try:
            cr_limit = float(cr_limit)
        except ValueError:
            cr_limit = None
    else:
        cr_limit = None
    cr_guide_method = survey_meta.get("CR_Guide_Method", "realtime" if survey_meta.get("CR_Guide_Enabled", False) else "none")
    rewards_info = survey_meta["Rewards_Info"]
    scale_type = survey_meta.get("Scale_Type", "1-9 Continuous")
    
    # AHP ?ë?ë¹„êµ ê¸°ë³¸ ? íƒê°’ì„ 1(?™ë“±)ë¡??¤ì •?˜ê¸° ?„í•´ session_state ?¬ì „ ì´ˆê¸°??(ë²„ì „ v3 ?ìš©?¼ë¡œ ?¸ì…˜ ìºì‹œ ê°±ì‹ )
    tier_level = int(survey_meta.get("Tier_Level", 2))
    
    init_key = f"init_survey_{survey_id_param}_v5"
    if init_key not in st.session_state:
        st.session_state[init_key] = True
        
        if tier_level == 3:
            from survey_manager_v3 import generate_pairwise_combinations_v3
            combinations = generate_pairwise_combinations_v3(ahp_model)
        else:
            combinations = generate_pairwise_combinations(ahp_model)
            
        for comb in combinations:
            for left_f, right_f in comb["pairs"]:
                pair_key = f"{left_f}_{right_f}"
                st.session_state[f"pair_ans_{pair_key.replace(' ', '_')}"] = None
    
    # ?¨ì¼ ?¤í¬ë¡????ì„±
    # respondent_survey_form context split - sections 1,2,3 are now outside the form
    # Define professional soft pastel colors for factor boxes
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
    
    # Extract all unique factors to ensure consistent coloring
    all_factors = []
    for main_f in ahp_model.get("main", []):
        if main_f not in all_factors:
            all_factors.append(main_f)
    for sub_list in ahp_model.get("subs", {}).values():
        for sub_f in sub_list:
            if sub_f not in all_factors:
                all_factors.append(sub_f)
                
    factor_colors = {}
    for i, f_name in enumerate(all_factors):
        factor_colors[f_name] = PASTEL_PALETTES[i % len(PASTEL_PALETTES)]

    section_num = 1

    # 1. ?‘ë‹µ??ê¸°ë³¸ ?•ë³´
    st.subheader(f"{section_num}. " + _("?‘ë‹µ??ê¸°ë³¸ ?•ë³´", "Respondent Demographic Information"))
    section_num += 1
    resp_data = {}
    
    # ?„ì´?”ëŠ” ?‘ë‹µ?ì—ê²??œì‹œ?˜ì? ë§ê³  ?„ì˜ë¡?ë¬´ì‘???ë™ ë¶€??
    if "survey_resp_uuid" not in st.session_state:
        import uuid
        st.session_state.survey_resp_uuid = str(uuid.uuid4())[:8]
    resp_data["id"] = st.session_state.survey_resp_uuid
    
    # ê·¸ë£¹ ë¶„ë¥˜???¤ê³„?ê? ?¤ì •??ë¬¸í•­ê³?ë³´ê¸°ë¥??ìš©
    type_q = demographics.get("type_question", "")
    if not type_q or type_q == "ê·€?˜ì˜ ?Œì†?€ ?´ë–»ê²??˜ì‹­?ˆê¹Œ?":
        type_q = _("ê·€?˜ì˜ ?Œì†?€ ?´ë–»ê²??˜ì‹­?ˆê¹Œ?", "What is your affiliation?")
    
    type_opts = demographics.get("type_options", [])
    if not isinstance(type_opts, list) or not type_opts or type_opts == ["?„ë¬¸ê°€", "?¼ë°˜", "ê³µë¬´??, "ê¸°í?"]:
        type_opts = [_("?„ë¬¸ê°€", "Expert"), _("?¼ë°˜", "General"), _("ê³µë¬´??, "Public Official"), _("ê¸°í?", "Other")]
    else:
        type_opts = [translate_factor_if_default(opt) for opt in type_opts]
        
    sq_idx = 1
    resp_data["type"] = st.radio(f"SQ{sq_idx}. {type_q}", type_opts, index=0, key="survey_resp_type", horizontal=True)
    sq_idx += 1
    
    if demographics.get("name"):
        resp_data["name"] = st.text_input(f"SQ{sq_idx}. " + _("?±ëª… *", "Name *"), key="survey_resp_name")
        sq_idx += 1
    
    # ?°ë ¹: ê°œë°©??vs 10???¨ìœ„ ? íƒ??
    if demographics.get("age"):
        age_label = f"SQ{sq_idx}. " + _("?°ë ¹ *", "Age *")
        sq_idx += 1
        age_type = demographics.get("age_type", "ê°œë°©??(?«ì ì§ì ‘ ?…ë ¥)")
        if age_type == "10???¨ìœ„ ? íƒ??:
            age_options = [_("20?€ ë¯¸ë§Œ", "Under 20s"), _("20?€ (20~29??", "20s (20-29)"), _("30?€ (30~39??", "30s (30-39)"), _("40?€ (40~49??", "40s (40-49)"), _("50?€ (50~59??", "50s (50-59)"), _("60?€ ?´ìƒ", "60s or older")]
            resp_data["age"] = st.radio(age_label, age_options, index=0, key="survey_resp_age", horizontal=True)
        else:
            resp_data["age"] = st.number_input(f"{age_label} " + _("(??", "(Years)"), min_value=1, max_value=120, value=30, key="survey_resp_age")
            
    if demographics.get("gender"):
        resp_data["gender"] = st.radio(f"SQ{sq_idx}. " + _("?±ë³„ *", "Gender *"), [_("?¨ì", "Male"), _("?¬ì", "Female")], key="survey_resp_gender", horizontal=True)
        sq_idx += 1
    
    # ê²½ë ¥?„ìˆ˜: ê°œë°©??vs 5???¨ìœ„ ? íƒ??
    if demographics.get("experience"):
        exp_label = f"SQ{sq_idx}. " + _("ê²½ë ¥?„ìˆ˜ *", "Years of Experience *")
        sq_idx += 1
        exp_type = demographics.get("experience_type", "ê°œë°©??(?«ì ì§ì ‘ ?…ë ¥)")
        if exp_type == "5???¨ìœ„ ? íƒ??:
            exp_options = [_("5??ë¯¸ë§Œ", "Less than 5 years"), _("5???´ìƒ ~ 10??ë¯¸ë§Œ", "5 to 10 years"), _("10???´ìƒ ~ 15??ë¯¸ë§Œ", "10 to 15 years"), _("15???´ìƒ ~ 20??ë¯¸ë§Œ", "15 to 20 years"), _("20???´ìƒ", "20 years or more")]
            resp_data["experience"] = st.radio(exp_label, exp_options, index=0, key="survey_resp_experience", horizontal=True)
        else:
            resp_data["experience"] = st.number_input(f"{exp_label} " + _("(??", "(Years)"), min_value=0, max_value=60, value=5, key="survey_resp_experience")
            
    # ?Œì† ë¬¸í•­ ?? œ??
    # if demographics.get("affiliation"):
    #     resp_data["affiliation"] = st.text_input(f"SQ{sq_idx}. " + _("?Œì† *", "Affiliation *"), key="survey_resp_affiliation")
    #     sq_idx += 1
        
    if demographics.get("email"):
        resp_data["email"] = st.text_input(f"SQ{sq_idx}. " + _("?´ë©”??*", "Email *"), key="survey_resp_email")
        sq_idx += 1
    
    st.divider()
    
    main_criteria = ahp_model.get("main", [])
    
    with st.container():
        # 4. AHP ?ë?ë¹„êµ ë¬¸í•­ ?ì„±
        st.subheader(f"{section_num}. " + _("?”ì¸ ê°??ë???ì¤‘ìš”???‰ê? (?ë?ë¹„êµ)", "Evaluation of Relative Importance between Factors (Pairwise Comparison)"))
        ahp_section_prefix = f"{section_num}"
        section_num += 1
        
        st.info(_("""
        **?‘ë‹µ ë°©ë²•**: ?¼ìª½ ?”ì¸ê³??¤ë¥¸ìª??”ì¸ ì¤?**??ì¤‘ìš”?˜ë‹¤ê³??ê°?˜ëŠ” ë°©í–¥**?¼ë¡œ ?«ìë¥?? íƒ??ì£¼ì„¸?? ?«ìê°€ ?´ìˆ˜ë¡??´ë‹¹ ?”ì¸????ì¤‘ìš”?¨ì„ ?˜ë??©ë‹ˆ??

        - **?™ë“±(1)**: ?‘ìª½ ?”ì¸???‘ê°™??ì¤‘ìš”????ê°€?´ë° **1**??? íƒ?˜ì„¸??
        - **?¼ìª½ ?”ì¸????ì¤‘ìš”????*: ?¼ìª½ ë°©í–¥(??)???«ìë¥?? íƒ?˜ì„¸?? ?«ìê°€ ?´ìˆ˜ë¡??¼ìª½ ?”ì¸???¨ì”¬ ì¤‘ìš”?¨ì„ ?˜í??…ë‹ˆ??
        - **?¤ë¥¸ìª??”ì¸????ì¤‘ìš”????*: ?¤ë¥¸ìª?ë°©í–¥( ?????«ìë¥?? íƒ?˜ì„¸?? ?«ìê°€ ?´ìˆ˜ë¡??¤ë¥¸ìª??”ì¸???¨ì”¬ ì¤‘ìš”?¨ì„ ?˜í??…ë‹ˆ??
        """ + ("""\n        ?’¡ :blue[**?Œë???ë°°ê²½ ê°€?´ë“œ: ?ì„  ?‘ë‹µ?¤ê³¼???¼ë¦¬???¼ê???CR)??ìµœì ?¼ë¡œ ? ì??????ˆëŠ”**] :red[**ê¶Œì¥ ? íƒ êµ¬ê°„**]:blue[**?…ë‹ˆ??**]""" if cr_guide_method == "realtime" else ""), """
        **Response Method**: Please select the number in the direction of **the factor you think is more important** between the left factor and the right factor. A larger number means that factor is more important.

        - **Equal (1)**: Choose the middle **1** when both factors are equally important.
        - **When the left factor is more important**: Choose a number on the left side (??. A larger number indicates the left factor is much more important.
        - **When the right factor is more important**: Choose a number on the right side (??. A larger number indicates the right factor is much more important.
        """ + ("""\n        ?’¡ :blue[**Blue Background Guide: Indicates the**] :red[**recommended selection range**] :blue[**to optimally maintain logical consistency (CR) with your previous answers.**]""" if cr_guide_method == "realtime" else "")))
        
        if tier_level == 3:
            from survey_manager_v3 import generate_pairwise_combinations_v3
            combinations = generate_pairwise_combinations_v3(ahp_model)
        else:
            combinations = generate_pairwise_combinations(ahp_model)
            
        ahp_answers = {}
        
        with st.container(key="ahp_survey_matrix"):
            comp_idx = 1
            for comb in combinations:
                parent_trans = translate_factor_if_default(comb['parent'])
                parent_lbl = f"{ahp_section_prefix}.{comp_idx}. " + (
                    _((f"[{parent_trans}] ?˜ìœ„ ?”ì¸ ë¹„êµ"), f"Sub-criteria Comparison under [{parent_trans}]")
                    if comb['type'] == 'sub'
                    else _("?€ë¶„ë¥˜(?µì‹¬) ?”ì¸ ë¹„êµ", "Main Criteria (Core) Comparison")
                )
                st.markdown(f"#### {parent_lbl}")
                
                # [?˜ì •] ?‰ê? ?”ì¸ ?•ì˜ ë°??¤ëª…??ê°?ì²™ë„ ?‰ê? ë°”ë¡œ ?„ìª½?¼ë¡œ ?´ë™
                if comb['type'] == 'sub':
                    # ?´ë‹¹ ?€ë¶„ë¥˜(parent) ì¹´ë“œ ì¶œë ¥
                    main_factor = comb['parent']
                    main_criteria = ahp_model.get("main", [])
                    try:
                        i = main_criteria.index(main_factor)
                    except ValueError:
                        i = 0
                    palette = PASTEL_PALETTES[i % len(PASTEL_PALETTES)]
                    bg = palette["bg"]
                    text_color = palette["text"]
                    border = palette["border"]
                    
                    main_desc = translate_definition_if_default(main_factor, definitions.get(main_factor, "")) if definitions else ""
                    subs = ahp_model.get("subs", {}).get(main_factor, [])
                    sub_rows_html = ""
                    if definitions:
                        for sub_factor in subs:
                            sub_desc = translate_definition_if_default(sub_factor, definitions.get(sub_factor, ""))
                            sub_factor_trans = translate_factor_if_default(sub_factor)
                            if sub_desc:
                                sub_rows_html += f"""
                                <div style="display: flex; align-items: flex-start; gap: 8px; padding: 6px 0; border-bottom: 1px dashed #f1f5f9;">
                                    <span style="color: {text_color}; font-weight: bold; min-width: 140px; font-size: 0.9rem; border-right: 2px solid {border}; padding-right: 8px; display: inline-block;">{sub_factor_trans}</span>
                                    <span style="color: #334155; font-size: 0.88rem; padding-left: 4px; flex: 1;">{sub_desc}</span>
                                </div>
                                """
                    
                    main_factor_trans = translate_factor_if_default(main_factor)
                    if main_desc or sub_rows_html:
                        main_desc_html = f'<p style="margin: 0 0 12px 0; color: #475569; font-size: 0.95rem; font-style: italic; font-weight: 500;">{main_desc}</p>' if main_desc else ""
                        sub_container_html = f'<div style="display: flex; flex-direction: column; gap: 2px; background-color: #ffffff; padding: 12px; border-radius: 6px; border: 1px solid #e2e8f0;">{sub_rows_html}</div>' if sub_rows_html else ""
                        
                        card_html = f"""
                        <div style="background-color: {bg}; border: 1px solid {border}; border-left: 6px solid {text_color}; padding: 16px; border-radius: 8px; margin-top: 10px; margin-bottom: 15px;">
                            <h4 style="margin: 0 0 8px 0; color: {text_color}; font-size: 1.1rem; font-weight: bold; display: flex; align-items: center; gap: 6px;">
                                {main_factor_trans}
                            </h4>
                            {main_desc_html}
                            {sub_container_html}
                        </div>
                        """
                        st.markdown(card_html.replace("\n", " "), unsafe_allow_html=True)
                else:
                    # ?€ë¶„ë¥˜ ?µì‹¬ ?”ì¸ ë¹„êµ???? ë¹„êµ ?€???€ë¶„ë¥˜?¤ì˜ ?„ì²´ ?¤ëª… ?¸ì¶œ (?Œì´ë¸??•íƒœ ì¹´ë“œë¡??¼ì¹˜??
                    main_rows_html = ""
                    if definitions:
                        for i, mc in enumerate(ahp_model.get("main", [])):
                            palette = PASTEL_PALETTES[i % len(PASTEL_PALETTES)]
                            text_color = palette["text"]
                            border = palette["border"]
                            mc_desc = translate_definition_if_default(mc, definitions.get(mc, ""))
                            mc_trans = translate_factor_if_default(mc)
                            if mc_desc:
                                main_rows_html += f"""
                                <div style="display: flex; align-items: flex-start; gap: 8px; padding: 8px 0; border-bottom: 1px dashed #f1f5f9;">
                                    <span style="color: {text_color}; font-weight: bold; min-width: 140px; font-size: 0.9rem; border-right: 2px solid {border}; padding-right: 8px; display: inline-block;">{mc_trans}</span>
                                    <span style="color: #334155; font-size: 0.88rem; padding-left: 4px; flex: 1;">{mc_desc}</span>
                                </div>
                                """
                    if main_rows_html:
                        card_html = f"""
                        <div style="background-color: #f8fafc; border: 1px solid #cbd5e1; border-left: 6px solid #1e40af; padding: 16px; border-radius: 8px; margin-top: 10px; margin-bottom: 15px;">
                            <h5 style="margin: 0 0 12px 0; color: #1e40af; font-size: 1.0rem; font-weight: bold;">{_("?€ë¶„ë¥˜ ?”ì¸ ?•ì˜", "Main Criteria Definitions")}</h5>
                            <div style="display: flex; flex-direction: column; gap: 2px; background-color: #ffffff; padding: 12px; border-radius: 6px; border: 1px solid #e2e8f0;">
                                {main_rows_html}
                            </div>
                        </div>
                        """
                        st.markdown(card_html.replace("\n", " "), unsafe_allow_html=True)
                
                comp_idx += 1
            
                # ì²™ë„ ?¸í„°?˜ì´???¤ì •???°ë¥¸ ? íƒ ?¼ë””??ë²„íŠ¼ ?µì…˜ ë§¤í•‘
                if scale_type == "1-3-5 Discrete":
                    options = [-5, -3, 1, 3, 5]
                    format_func = lambda x: _("?¼ìª½ ?”ì¸???¨ì”¬ ì¤‘ìš” (-5)", "Left factor is much more important (-5)") if x == -5 else (_("?¼ìª½ ?”ì¸???½ê°„ ì¤‘ìš” (-3)", "Left factor is slightly more important (-3)") if x == -3 else (_("?‘ì¸¡???™ë“±??(1)", "Equal importance (1)") if x == 1 else (_("?¤ë¥¸ìª??”ì¸???½ê°„ ì¤‘ìš” (3)", "Right factor is slightly more important (3)") if x == 3 else _("?¤ë¥¸ìª??”ì¸???¨ì”¬ ì¤‘ìš” (5)", "Right factor is much more important (5)"))))
                elif scale_type == "1-3-7-9 Discrete":
                    options = [-9, -7, -3, 1, 3, 7, 9]
                    format_func = lambda x: _("?¼ìª½ ?ˆë???ì¤‘ìš” (-9)", "Left is absolutely more important (-9)") if x == -9 else (_("?¼ìª½ ?€?¨íˆ ì¤‘ìš” (-7)", "Left is strongly more important (-7)") if x == -7 else (_("?¼ìª½ ?½ê°„ ì¤‘ìš” (-3)", "Left is slightly more important (-3)") if x == -3 else (_("?™ë“±??(1)", "Equal (1)") if x == 1 else (_("?¤ë¥¸ìª??½ê°„ ì¤‘ìš” (3)", "Right is slightly more important (3)") if x == 3 else (_("?¤ë¥¸ìª??€?¨íˆ ì¤‘ìš” (7)", "Right is strongly more important (7)") if x == 7 else _("?¤ë¥¸ìª??ˆë???ì¤‘ìš” (9)", "Right is absolutely more important (9)"))))))
                else: # 1-9 Continuous (Default)
                    options = list(range(-9, -1)) + list(range(1, 10))
                    options = sorted(list(set(options))) # -9 ~ -2, 1, 2 ~ 9
                    format_func = lambda x: _(f"?¼ìª½ ì¤‘ìš”??{abs(x)}", f"Left importance {abs(x)}") if x < 0 else (_("?™ë“± (1)", "Equal (1)") if x == 1 else _(f"?¤ë¥¸ìª?ì¤‘ìš”??{x}", f"Right importance {x}"))
                
                # PDF ?¤ë¬¸ì§€?€ ? ì‚¬???¤ë” ?¤í??????ì„±
                # ì²™ë„ ?µì…˜??ë§ì¶”?????ë‹¨???œì‹œ???¤ë” ë°?ì²™ë„ ê°?êµ¬ì„±
                if scale_type == "1-3-5 Discrete":
                    left_cols = ["5", "3"]
                    right_cols = ["3", "5"]
                    options = [-5, -3, 1, 3, 5]
                    col_headers = ["5", "3", "1", "3", "5"]
                elif scale_type == "1-3-7-9 Discrete":
                    left_cols = ["9", "7", "3"]
                    right_cols = ["3", "7", "9"]
                    options = [-9, -7, -3, 1, 3, 7, 9]
                    col_headers = ["9", "7", "3", "1", "3", "7", "9"]
                else: # 1-9 Continuous (Default)
                    left_cols = ["9", "8", "7", "6", "5", "4", "3", "2"]
                    right_cols = ["2", "3", "4", "5", "6", "7", "8", "9"]
                    options = list(range(-9, -1)) + list(range(1, 10))
                    options = sorted(list(set(options))) # -9 ~ -2, 1, 2 ~ 9
                    col_headers = ["9", "8", "7", "6", "5", "4", "3", "2", "1", "2", "3", "4", "5", "6", "7", "8", "9"]
            
                # ì²™ë„ ?˜ì— ë§ì¶”??ë¹„ìœ¨ ?™ì  ê³„ì‚° (left_cols + ?™ì¼(1) + right_cols)
                header_cells = left_cols + ["1"] + right_cols
                total_scale_count = len(header_cells)
                scale_width = 70.0 / total_scale_count
                left_width = scale_width * len(left_cols)
                right_width = scale_width * len(right_cols)

                # CSS ì£¼ì…: ì»¬ëŸ¼ ê°„ì˜ gap??0?¼ë¡œ ì°¨ë‹¨?˜ê³  ?¼ë””??ê·¸ë£¹??100% ë¶„ë°°
            

                # HTML ???¤ë” êµ¬ì¡°
                # fixed table layout?ì„œ colspan ?¬ìš© ??ê°?ì»¬ëŸ¼ ?ˆë¹„ë¥??™ì¼ ë°°ë¶„?˜ë„ë¡?colgroup ?•ì˜
                colgroup_html = "".join([
                    f'<col style="width: 15%;" />',
                    "".join([f'<col style="width: {scale_width}%;" />' for _ in left_cols]),
                    f'<col style="width: {scale_width}%;" />',
                    "".join([f'<col style="width: {scale_width}%;" />' for _ in right_cols]),
                    f'<col style="width: 15%;" />'
                ])
                
                header_html = f"""
                <table style="width:100%; border-collapse: collapse; text-align: center; font-size: 12px; font-family: sans-serif; border: 1px solid #cbd5e1; table-layout: fixed; margin: 0px; padding: 0px;">
                    <colgroup>
                        {colgroup_html}
                    </colgroup>
                    <tr style="background-color: #1e293b; color: #ffffff; font-weight: bold; border-bottom: 1px solid #cbd5e1;">
                        <th style="border: 1px solid #334155; padding: 6px; font-size: 12px;" rowspan="2">{_("ë¹„êµ ?”ì¸", "Comparison Criteria")}</th>
                        <th style="border: 1px solid #334155; padding: 4px; color: #93c5fd; font-size: 12px;" colspan="{len(left_cols)}">{_("??ì¢Œì¸¡ ?”ì¸ ì¤‘ìš”??, "??Left Criteria Importance")}</th>
                        <th style="border: 1px solid #334155; padding: 4px; background-color: #3b82f6; color: #ffffff; font-size: 12px;" rowspan="2">{_("?™ë“±<br>(1)", "Equal<br>(1)")}</th>
                        <th style="border: 1px solid #334155; padding: 4px; color: #93c5fd; font-size: 12px;" colspan="{len(right_cols)}">{_("?°ì¸¡ ?”ì¸ ì¤‘ìš”????, "Right Criteria Importance ??)}</th>
                        <th style="border: 1px solid #334155; padding: 6px; font-size: 12px;" rowspan="2">{_("ë¹„êµ ?”ì¸", "Comparison Criteria")}</th>
                    </tr>
                    <tr style="background-color: #334155; color: #cbd5e1; font-weight: bold; border-bottom: 1px solid #cbd5e1;">
                        {"".join([f"<td style='border: 1px solid #475569; padding: 4px 0; font-size: 12px;'>{val}</td>" for val in left_cols])}
                        {"".join([f"<td style='border: 1px solid #475569; padding: 4px 0; font-size: 12px;'>{val}</td>" for val in right_cols])}
                    </tr>
                </table>
                """
                st.markdown(header_html, unsafe_allow_html=True)

                # 3??ì»¬ëŸ¼ ë°°ì¹˜: [?¼ìª½ ?”ì¸ëª?ì»¬ëŸ¼ (15%)] - [ì²™ë„ ?¼ë””??ë²„íŠ¼ ?ì—­ ì»¬ëŸ¼ (70%)] - [?¤ë¥¸ìª??”ì¸ëª?ì»¬ëŸ¼ (15%)]
                for left_f, right_f in comb["pairs"]:
                    pair_key = f"{left_f}_{right_f}"
                    clean_id = pair_key.replace(" ", "_")
                    st.markdown(f"<div id='anchor_{clean_id}'></div>", unsafe_allow_html=True)
                
                    row_cols = st.columns([15, 70, 15])
                
                    # ?¼ìª½ ?”ì¸ëª?ì¶œë ¥
                    with row_cols[0]:
                        left_style = factor_colors.get(left_f, {"bg": "#f8fafc", "text": "#334155", "border": "#cbd5e1"})
                        left_desc = translate_definition_if_default(left_f, definitions.get(left_f, "")) if definitions else ""
                        left_desc_esc = left_desc.replace('"', '&quot;')
                        left_trans = translate_factor_if_default(left_f)
                        st.markdown(f"""
                        <div title="{left_desc_esc}" style='text-align:center; font-weight:600; border: 1px solid {left_style["border"]}; 
                                    padding: 0px 8px; background-color: {left_style["bg"]}; color: {left_style["text"]}; 
                                    border-radius: 4px; min-height: 28px; height: auto; padding: 4px 8px; display: flex; align-items: center; 
                                    justify-content: center; font-size: 12px; margin: 0px; box-shadow: 0 1px 2px rgba(0,0,0,0.02); cursor: help;'>
                                {left_trans}
                        </div>
                        """, unsafe_allow_html=True)
                
                    # ?¼ë””??ë²„íŠ¼?¤ì„ ê°€ë¡œë¡œ ?„ì „ ?•ë ¬?˜ì—¬ 1?´ë¡œ ë°°ì¹˜
                    with row_cols[1]:
                        # ?ˆì „???„í•´ options?ì„œ ì¤‘ë³µ ë°?-1 ê°?ëª…ì‹œ???œì™¸
                        clean_options = [x for x in options if x != -1]
                        
                        valid_options = set()
                        is_highlight_target = st.session_state.get("highlight_target") == pair_key
                        should_show_guide = (cr_guide_method == "realtime" or is_highlight_target) and cr_limit is not None
                        if should_show_guide:
                            try:
                                group_factors = comb["factors"]
                                group_answers = {}
                                other_missing = False
                                for p_left, p_right in comb["pairs"]:
                                    k = f"{p_left}_{p_right}"
                                    val = st.session_state.get(f"pair_ans_{k.replace(' ', '_')}", None)
                                    group_answers[k] = val
                                    if k != pair_key and val is None:
                                        other_missing = True
                                
                                min_cr_opt = 1
                                min_cr_val = float('inf')
                                
                                # ë¹„êµ ?”ì¸??2ê°?ì´ˆê³¼?´ê³ , ê·¸ë£¹ ?´ì˜ ?¤ë¥¸ ë¬¸í•­?¤ì´ ëª¨ë‘ ?‘ë‹µ??ê²½ìš°?ë§Œ ê¶Œì¥ ë²”ìœ„ë¥??°ì¶œ?©ë‹ˆ??
                                if len(group_factors) > 2 and not other_missing:
                                    for opt in clean_options:
                                        test_answers = group_answers.copy()
                                        test_answers[pair_key] = opt
                                        test_cr = calculate_matrix_cr(group_factors, test_answers)
                                        if test_cr <= cr_limit:
                                            valid_options.add(opt)
                                        if test_cr < min_cr_val:
                                            min_cr_val = test_cr
                                            min_cr_opt = opt
                            except Exception:
                                pass
                                
                        def format_option(opt):
                            # Streamlit st.radio ?¼ë²¨ ì¤‘ë³µ(?•ê? ?„ìƒ) ë°©ì?ë¥??„í•´ ?Œìˆ˜ ìª½ì— ë³´ì´ì§€ ?ŠëŠ” ê³µë°±(Zero-width space) ì¶”ê?
                            return str(abs(opt)) + "\u200B" if opt < 0 else str(opt)

                        ans_key = f"pair_ans_{pair_key.replace(' ', '_')}"
                        if should_show_guide and len(comb["factors"]) > 2:
                            if not other_missing:
                                valid_sorted = [x for x in clean_options if x in valid_options]
                                if valid_sorted:
                                    min_val = valid_sorted[0]
                                    max_val = valid_sorted[-1]
                                else:
                                    min_val = min_cr_opt
                                    max_val = min_cr_opt
                                start_idx = clean_options.index(min_val)
                                end_idx = clean_options.index(max_val)
                                bar_html = '<div style="display: flex; width: 100%; height: 32px; margin-top: -32px; z-index: 10; position: relative; pointer-events: none;">'
                                for j, opt in enumerate(clean_options):
                                    is_valid = start_idx <= j <= end_idx
                                    bg_color = "rgba(59, 130, 246, 0.25)" if is_valid else "transparent"
                                    radius = ""
                                    if j == start_idx:
                                        radius += "border-top-left-radius: 6px; border-bottom-left-radius: 6px; "
                                    if j == end_idx:
                                        radius += "border-top-right-radius: 6px; border-bottom-right-radius: 6px; "
                                    bar_html += f'<div style="flex: 1 1 0%; background-color: {bg_color}; {radius}"></div>'
                                bar_html += '</div>'
                        current_val = st.session_state.get(ans_key, None)
                        current_idx = clean_options.index(current_val) if current_val in clean_options else None

                        ans_val = st.radio(
                            label=f"select_{pair_key}",
                            options=clean_options,
                            index=current_idx,
                            format_func=format_option,
                            key=ans_key,
                            horizontal=True,
                            label_visibility="collapsed"
                        )
                        if should_show_guide and len(comb["factors"]) > 2:
                            if not other_missing:
                                st.markdown(bar_html, unsafe_allow_html=True)
                
                    # ?¤ë¥¸ìª??”ì¸ëª?ì¶œë ¥
                    with row_cols[2]:
                        right_style = factor_colors.get(right_f, {"bg": "#f8fafc", "text": "#334155", "border": "#cbd5e1"})
                        right_desc = translate_definition_if_default(right_f, definitions.get(right_f, "")) if definitions else ""
                        right_desc_esc = right_desc.replace('"', '&quot;')
                        right_trans = translate_factor_if_default(right_f)
                        st.markdown(f"""
                        <div title="{right_desc_esc}" style='text-align:center; font-weight:600; border: 1px solid {right_style["border"]}; 
                                    padding: 0px 8px; background-color: {right_style["bg"]}; color: {right_style["text"]}; 
                                    border-radius: 4px; min-height: 28px; height: auto; padding: 4px 8px; display: flex; align-items: center; 
                                    justify-content: center; font-size: 12px; margin: 0px; box-shadow: 0 1px 2px rgba(0,0,0,0.02); cursor: help;'>
                                {right_trans}
                        </div>
                        """, unsafe_allow_html=True)
                
                    ahp_answers[pair_key] = ans_val
            st.divider()
            
            target = st.session_state.get("scroll_target")
            if target:
                import streamlit.components.v1 as components
                clean_target = target.replace(" ", "_")
                components.html(
                    f"<script>window.parent.document.getElementById('anchor_{clean_target}').scrollIntoView({{behavior: 'smooth', block: 'center'}});</script>",
                    height=0
                )
                st.session_state["scroll_target"] = None
            
        # 5. ê°œì¸?•ë³´ ?˜ì§‘ ë°??µë????™ì  ?¸ì¶œ ë°?ë¬¸êµ¬ ?¤ì •
        has_demographics = any(demographics.values()) if demographics else False
        has_rewards = rewards_info.get("enabled", False) if rewards_info else False
        
        agree_check = _("?™ì˜", "Agree")
        if has_demographics or has_rewards:
            if has_rewards:
                subheader_text = f"{section_num}. " + _("ê°œì¸?•ë³´ ?˜ì§‘ ë°??µë???, "Personal Information Collection & Reward")
                radio_label = _("ê°œì¸?•ë³´ ?˜ì§‘ ë°??µë???ì§€ê¸‰ì„ ?„í•œ ?´ìš© ?™ì˜???™ì˜?˜ì‹­?ˆê¹Œ? *", "Do you agree to the collection of personal information and use for reward distribution? *")
            else:
                subheader_text = f"{section_num}. " + _("ê°œì¸?•ë³´ ?˜ì§‘ ?™ì˜", "Consent to Personal Information Collection")
                radio_label = _("ê°œì¸?•ë³´ ?˜ì§‘ ë°??´ìš©???™ì˜?˜ì‹­?ˆê¹Œ? *", "Do you agree to the collection and use of personal information? *")
                
            st.subheader(subheader_text)
            section_num += 1
            
            if has_rewards:
                st.info(f"**" + _("?µë????ˆë‚´", "Reward Info") + f"**: {rewards_info.get('desc', _('?¤ë¬¸ ?„ë£Œ ???µë??ˆì„ ?œê³µ?©ë‹ˆ??', 'A reward will be provided upon survey completion.'))}")
                reward_contact = st.text_input(_("?µë???ì§€ê¸‰ìš© ?°ë½ì²??´ë???ë²ˆí˜¸ ?ëŠ” ?´ë©”?? *", "Contact for Reward (Mobile number or Email) *"), key="survey_reward_contact")
                resp_data["reward_contact"] = reward_contact
                
            agree_check = st.radio(radio_label, [_("?™ì˜", "Agree"), _("ë¹„ë™??, "Disagree")], index=1, key="survey_agree_check")
        
        # ë§ˆë²•???íƒœ ?•ì¸
        wizard_state_key = f"cr_wizard_state_{survey_id_param}"
        wizard_state = st.session_state.get(wizard_state_key, {"active": False})
        
        if wizard_state.get("active"):
            st.warning(_("? ï¸ ?¼ê???ë¹„ìœ¨(CR) ?ê?", "? ï¸ Consistency Ratio (CR) Check"))
            st.error(_(f"ë¶„ì„ ê²°ê³¼, **[{wizard_state['failed_group']}]** ë¬¸í•­?¤ì˜ ?‘ë‹µ ?¼ê??±ì´ ë¶€ì¡±í•©?ˆë‹¤. (?„ì¬ CR: {wizard_state['cr']:.3f} > ê¸°ì?ì¹? {cr_limit})", f"Analysis shows inconsistent responses for **[{wizard_state['failed_group']}]**. (Current CR: {wizard_state['cr']:.3f} > Limit: {cr_limit})"))
            
            w_pair = wizard_state['worst_pair']
            cur_v = wizard_state['current_val']
            sug_v = wizard_state['suggested_val']
            
            def val_to_text(v, p1, p2):
                if v == 1: return _("?™ë“±??(1)", "Equal (1)")
                if v < 0: return f"{p1} ë°©í–¥?¼ë¡œ {abs(v)}"
                return f"{p2} ë°©í–¥?¼ë¡œ {v}"
                
            cur_txt = val_to_text(cur_v, w_pair[0], w_pair[1])
            sug_txt = val_to_text(sug_v, w_pair[0], w_pair[1])
            
            st.info(_(f"""
            ?’¡ **ì§€?¥í˜• ?˜ì • ?œì•ˆ**: 
            ?„ì¬ [{w_pair[0]}]?€ [{w_pair[1]}]??ë¹„êµ ?‘ë‹µ???¤ë¥¸ ?‘ë‹µ?¤ê³¼ ?˜í•™??ëª¨ìˆœ??ê°€???½ë‹ˆ??
            * ?„ì¬ ? íƒ?˜ì‹  ê°? **{cur_txt}**
            * ?¼ë¦¬???¼ê??±ì„ ?„í•œ ì¶”ì²œ ê°? **{sug_txt}**
            """, f"""
            ?’¡ **Smart Fix Suggestion**: 
            Your comparison between [{w_pair[0]}] and [{w_pair[1]}] has the highest mathematical contradiction with your other answers.
            * Your current selection: **{cur_txt}**
            * Suggested value for logical consistency: **{sug_txt}**
            """))
            
            if st.button(_("?¤ì‹œ ê²€??, "Review again"), use_container_width=True):
                st.session_state[wizard_state_key]["active"] = False
                target_key = f"{w_pair[0]}_{w_pair[1]}"
                st.session_state["scroll_target"] = target_key
                st.session_state["highlight_target"] = target_key
                st.rerun()
                    
            submit_btn = False # ë§ˆë²•???œì‹œ ì¤‘ì—???¼ë°˜ ?œì¶œ ?ˆí•¨
        else:
            # ?œì¶œ ë²„íŠ¼
            submit_btn = st.button(_("?¤ë¬¸ì§€ ?œì¶œ?˜ê¸°", "Submit Survey"), type="primary")
        if submit_btn:
            # ?„ìˆ˜ê°?? íš¨??ê²€ì¦?
            missing = False
            
            # AHP ?‘ë‹µ ?„ë½ ê²€ì¦?
            missing_ahp = [k for k, v in ahp_answers.items() if v is None]
            
            # ?¸êµ¬?µê³„ ?„ìˆ˜ê°?
            if demographics.get("name") and not resp_data.get("name"): missing = True
            # if demographics.get("affiliation") and not resp_data.get("affiliation"): missing = True
            if demographics.get("email") and not resp_data.get("email"): missing = True
            if rewards_info.get("enabled") and not resp_data.get("reward_contact"): missing = True
            
            if agree_check not in ["?™ì˜", "Agree"]:
                st.error(_("?¤ë¬¸?œì¶œ???„í•´ ê°œì¸?•ë³´ ?˜ì§‘ ?™ì˜??ì²´í¬??ì£¼ì„¸??", "Please agree to the personal information collection to submit the survey."))
                st.stop()
                
            if missing_ahp:
                st.error(_("?µë??˜ì? ?Šì? AHP ?ë?ë¹„êµ ë¬¸í•­???ˆìŠµ?ˆë‹¤. ëª¨ë“  ë¬¸í•­???‘ë‹µ??ì£¼ì‹­?œì˜¤.", "There are unanswered AHP pairwise comparison questions. Please answer all questions."))
                st.stop()

            if missing:
                st.error(_("?…ë ¥?˜ì? ?Šì? ?„ìˆ˜ ë¬¸í•­(*)???ˆìŠµ?ˆë‹¤. ?¼ì„ ?¤ì‹œ ??ë²??•ì¸??ì£¼ì„¸??", "There are missing required fields (*). Please check the form again."))
                st.stop()
                
            # CR ê³„ì‚° ë°?ë§ˆë²•??ë¡œì§
            if cr_limit is not None:
                cr_failed = False
                failed_factors = []
                failed_group_name = ""
                failed_cr = 0.0
                
                # ?€ë¶„ë¥˜ CR ì²´í¬
                main_cr = calculate_matrix_cr(main_criteria, ahp_answers)
                if main_cr > cr_limit:
                    cr_failed = True
                    failed_factors = main_criteria
                    failed_group_name = "?€ë¶„ë¥˜"
                    failed_cr = main_cr
                
                # ?˜ìœ„ë¶„ë¥˜ CR ì²´í¬
                if not cr_failed:
                    for parent, subs in ahp_model.get("subs", {}).items():
                        if len(subs) >= 3:
                            sub_cr = calculate_matrix_cr(subs, ahp_answers)
                            if sub_cr > cr_limit:
                                cr_failed = True
                                failed_factors = subs
                                failed_group_name = parent
                                failed_cr = sub_cr
                                break

                if cr_failed:
                    if cr_guide_method == "post_wizard":
                        from survey_manager import get_cr_fix_suggestion
                        worst_pair, current_val, suggested_val = get_cr_fix_suggestion(failed_factors, ahp_answers)
                        
                        if worst_pair:
                            st.session_state[f"cr_wizard_state_{survey_id_param}"] = {
                                "active": True,
                                "failed_group": failed_group_name,
                                "cr": failed_cr,
                                "worst_pair": worst_pair,
                                "current_val": current_val,
                                "suggested_val": suggested_val
                            }
                            st.rerun()
                    
                    # ë§ˆë²•?¬ê? ?†ê±°??ë§ˆë²•???œì•ˆ??ê³„ì‚°?????†ëŠ” ê²½ìš° (ê¸°ì¡´ ë¡œì§)
                    if not is_preview_mode:
                        from survey_manager import increment_abandoned_cr
                        increment_abandoned_cr(survey_id_param)
                    st.error(_(f"[{failed_group_name}] ??ª©???‘ë‹µ ?¼ê??±ì´ ë¶€ì¡±í•©?ˆë‹¤. (?¼ê???ë¹„ìœ¨: {failed_cr:.3f} > ?¤ì • ?„ê³„ê°? {cr_limit}) ?¼ë? ë¬¸í•­???¤ì‹œ ê²€? í•´ ì£¼ì‹­?œì˜¤.", f"The consistency of your responses for [{failed_group_name}] is insufficient. (CR: {failed_cr:.3f} > threshold: {cr_limit}) Please review some questions again."))
                    st.stop()
            
            # ?€??ì§„í–‰
            with st.spinner(_("?‘ë‹µ???ˆì „?˜ê²Œ ?„ì†¡ ì¤‘ì…?ˆë‹¤...", "Submitting your response safely...")):
                if is_preview_mode:
                    import time
                    time.sleep(1.0)
                    st.session_state[f"survey_submitted_{survey_id_param}"] = True
                    st.rerun()
                else:
                    if tier_level == 3:
                        from survey_manager_v3 import save_response_to_sheet_v3
                        success = save_response_to_sheet_v3(
                            survey_id_param, resp_data, ahp_answers, demographics, ahp_model, rewards_info
                        )
                    else:
                        success = save_response_to_sheet(
                            survey_id_param, resp_data, ahp_answers, demographics, ahp_model, rewards_info
                        )
                    if success:
                        st.session_state[f"survey_submitted_{survey_id_param}"] = True
                        st.rerun()
                    else:
                        st.error(_("?°ì´???€??ì¤??œë²„ ?ëŸ¬ê°€ ë°œìƒ?ˆìŠµ?ˆë‹¤. ? ì‹œ ???¤ì‹œ ?œë„??ì£¼ì„¸??", "A server error occurred while saving data. Please try again later."))
                    
    st.stop()

# ?ë™ ë¡œê·¸??ì²˜ë¦¬ (ì¿¼ë¦¬ ?Œë¼ë¯¸í„° ê¸°ë°˜)
if st.session_state.user_id is None and "login_user" in q_params and "login_token" in q_params:
    login_user_val = q_params["login_user"]
    if isinstance(login_user_val, list): login_user_val = login_user_val[0]
    login_token_val = q_params["login_token"]
    if isinstance(login_token_val, list): login_token_val = login_token_val[0]
    
    # ? í° ê²€ì¦?
    expected_token = hashlib.sha256(f"{login_user_val}:AHP_MASTER_SECURE_SALT_2026_!@#".encode()).hexdigest()
    if login_token_val == expected_token:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("SELECT role, expiry_date FROM users WHERE id=?", (login_user_val,))
        db_user = c.fetchone()
        conn.close()
        if db_user:
            st.session_state.user_id = login_user_val
            st.session_state.user_role = db_user[0]
            st.session_state.expiry_date = db_user[1]


# ?ë™ ë¡œê·¸?„ì›ƒ ì²˜ë¦¬ (30ë¶?ë¯¸í™œ????
import time
TIMEOUT_LIMIT = 1800 # 30ë¶?(ì´??¨ìœ„)
current_time = int(time.time())

if st.session_state.user_id is not None:
    last_act = q_params.get("last_activity")
    if isinstance(last_act, list): last_act = last_act[0]
    
    if last_act:
        try:
            elapsed = current_time - int(last_act)
            if elapsed > TIMEOUT_LIMIT:
                # ?¸ì…˜ ë°?ì¿¼ë¦¬ ?Œë¼ë¯¸í„° ì´ˆê¸°??
                st.session_state.user_id = None
                st.session_state.user_role = None
                st.session_state.expiry_date = None
                st.session_state.admin_mode = False
                st.query_params.clear()
                st.toast(_("?”’ 30ë¶„ê°„ ?œë™???†ì–´ ë³´ì•ˆ???„í•´ ?ë™ ë¡œê·¸?„ì›ƒ?˜ì—ˆ?µë‹ˆ??", "?”’ Logged out automatically due to 30 minutes of inactivity."))
                st.rerun()
            else:
                st.query_params["last_activity"] = str(current_time)
        except ValueError:
            st.query_params["last_activity"] = str(current_time)
    else:
        st.query_params["last_activity"] = str(current_time)

# ?¤êµ­??ì²˜ë¦¬
if "lang" in q_params:
    lang_val = q_params["lang"]
    if isinstance(lang_val, list): lang_val = lang_val[0]
    if str(lang_val).lower() in ["en", "english"]:
        st.session_state.lang = "en"
    elif str(lang_val).lower() in ["ko", "korean"]:
        st.session_state.lang = "ko"

# ?˜ì´???ë™ ê²°ì œ ?¹ê²© ì²˜ë¦¬ (?œë²„ ê²€ì¦??¬í•¨)
if "paypal_order_id" in q_params:
    order_id_val = q_params["paypal_order_id"]
    if isinstance(order_id_val, list):
        order_id_val = order_id_val[0]
        
    is_valid, msg = verify_paypal_payment(order_id_val)
    if is_valid:
        current_user = st.session_state.get("user_id")
        user_id_param = q_params.get("user_id", [""])[0] if isinstance(q_params.get("user_id"), list) else q_params.get("user_id", "")
        target_user = current_user or user_id_param
        if target_user:
            kst_now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
            new_expiry_date = (kst_now + relativedelta(months=3)).strftime("%Y-%m-%d")
            update_user_full_info(target_user, None, "official", new_expiry_date)
            
            if st.session_state.get("user_id") == target_user:
                st.session_state.user_role = "official"
                st.session_state.expiry_date = new_expiry_date
            st.toast("?‰ PayPal Payment successful! Account upgraded to Official User.")
    else:
        st.error(f"Payment verification failed: {msg}")
        
    st.query_params.clear()
    st.rerun()

# ?•ì‹ ?Œì› ?ë™ ë§Œë£Œ ì²´í¬ (ë¡œê·¸???íƒœ)
if st.session_state.user_id is not None and st.session_state.user_role == 'official':
    today = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).date()
    try:
        expiry_date_val_temp = datetime.datetime.strptime(st.session_state.expiry_date, "%Y-%m-%d").date()
        if today > expiry_date_val_temp:
            update_user_full_info(st.session_state.user_id, None, "temp", "9999-12-31")
            st.session_state.user_role = "temp"
            st.session_state.expiry_date = "9999-12-31"
            st.toast("?“… Subscription expired. Automatically downgraded to Free User.")
            st.rerun()
    except Exception:
        pass

# =============================================================================
# 3. Sidebar (Auth & Settings) - ??ƒ ?œì‹œ?˜ë„ë¡??„ì¹˜ ì¡°ì •
# =============================================================================

def get_fee_info_text():
    return _(
        """<div style="line-height: 1.4; font-size: 0.95rem;">
  <hr style="margin-top: 15px; margin-bottom: 15px; border: 0; border-top: 1px solid #ddd;">
  <h3 style="margin-top: 0; margin-bottom: 8px;">?œë¹„???´ìš©ë£?/h3>
  <ul style="margin: 0; padding-left: 20px; margin-bottom: 8px;">
    <li style="margin-bottom: 2px;"><b>ë¬´ë£Œ?¬ìš©??/b>: 5?œë³¸ ë¶„ì„ ê°€??/li>
    <li style="margin-bottom: 2px;"><b>?•ì‹ ?¬ìš©??/b>: 50ë§Œì› (3ê°œì›”)<br><span style="font-size: 0.85rem; color: #555; display: inline-block; padding-left: 0; text-indent: 0; margin-top: 2px; white-space: nowrap;">(?¨ë¼???¤ë¬¸ ?‹íŒ… ?€??5ë§Œì›, ?€??ë¬´ë£Œ)</span></li>
  </ul>
  <div style="margin-top: 10px; color: #e65100; font-size: 0.85rem; font-weight: 600;">
    ?’¡ ê°€????3????ë¶ˆë§Œì¡???100% ?˜ë¶ˆ
  </div>
</div>""",
        """<div style="line-height: 1.4; font-size: 0.95rem;">
  <hr style="margin-top: 15px; margin-bottom: 15px; border: 0; border-top: 1px solid #ddd;">
  <h3 style="margin-top: 0; margin-bottom: 8px;">Service Fees</h3>
  <ul style="margin: 0; padding-left: 20px; margin-bottom: 8px;">
    <li style="margin-bottom: 2px;"><b>Free User</b>: Free (5 samples limit, no other limitations)</li>
    <li style="margin-bottom: 2px;"><b>Official User</b>: $350 USD (3 months unlimited)</li>
  </ul>

</div>"""
    )

with st.sidebar:
    # ?¤êµ­??? íƒ (Language Switcher)
    lang_options = {"?œêµ­???‡°?‡·": "ko", "English ?‡º?‡¸": "en"}
    selected_lang_label = st.selectbox(
        "Language / ?¸ì–´ ? íƒ", 
        options=list(lang_options.keys()), 
        index=0 if st.session_state.get('lang', 'ko') == 'ko' else 1,
        key="sidebar_lang_selector"
    )
    new_lang = lang_options[selected_lang_label]
    if new_lang != st.session_state.get('lang', 'ko'):
        st.session_state.lang = new_lang
        st.query_params["lang"] = new_lang
        st.rerun()

    try:
        st.image("ahp_master_logo.png", use_container_width=True)
    except:
        st.subheader(_("?“Š AHP ë§ˆìŠ¤??, "?“Š AHP Master"))


    if st.session_state.user_id is None:
        tab_login, tab_signup, tab_find_pw = st.tabs([_("ë¡œê·¸??, "Login"), _("?Œì›ê°€??, "Sign Up"), _("ë¹„ë?ë²ˆí˜¸ ì°¾ê¸°", "Find Password")])
        
        with tab_login:
            l_id = st.text_input(_("?„ì´??(?´ë©”??ì£¼ì†Œ)", "Username (Email Address)"), key="l_id")
            l_pw = st.text_input(_("ë¹„ë?ë²ˆí˜¸ (PW)", "Password (PW)"), type="password", key="l_pw")
            if st.button(_("ë¡œê·¸???¤í–‰", "Login")):
                result = check_login(l_id.strip(), l_pw)
                if result:
                    # [?˜ì •] ?€?œë?êµ??œê°„ ê¸°ì? ?¤ëŠ˜ ? ì§œ ê°€?¸ì˜¤ê¸?
                    today = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).date()
                    expiry_date_val = datetime.datetime.strptime(result[1], "%Y-%m-%d").date()
                    if today > expiry_date_val:
                        if result[0] == 'official':
                            # ?•ì‹ ?¬ìš©?ê? ë§Œë£Œ??ê²½ìš° -> ?ë™?¼ë¡œ ë¬´ë£Œ?¬ìš©??temp)ë¡?ì¦‰ì‹œ ?ˆì „ ?¹ê²© ?´ì œ ë°??„í™˜
                            try:
                                update_user_full_info(l_id.strip(), None, "temp", "9999-12-31")
                                st.session_state.user_id = l_id.strip()
                                st.session_state.user_role = "temp"
                                st.session_state.expiry_date = "9999-12-31"
                                st.query_params["login_user"] = l_id.strip()
                                st.query_params["login_token"] = hashlib.sha256(f"{l_id.strip()}:AHP_MASTER_SECURE_SALT_2026_!@#".encode()).hexdigest()
                                st.query_params["last_activity"] = str(int(time.time()))
                                st.toast(_("?“… ?•ì‹ ?´ìš© ê¸°ê°„??ë§Œë£Œ?˜ì–´ ë¬´ë£Œ?¬ìš©??ê¶Œí•œ?¼ë¡œ ?ë™ ?„í™˜?˜ì—ˆ?µë‹ˆ??", "?“… Subscription expired. Automatically downgraded to Free User."))
                                st.success(_(f"?˜ì˜?©ë‹ˆ?? {l_id}?? ?•ì‹ ?´ìš© ê¸°ê°„??ë§Œë£Œ?˜ì–´ ë¬´ë£Œ?¬ìš©??5?œë³¸ ë¶„ì„ ê°€?? ê¶Œí•œ?¼ë¡œ ?ë™ ?„í™˜?˜ì—ˆ?µë‹ˆ?? ?¬ì´?œë°”?ì„œ ?¸ì œ???°ì¥ ê²°ì œ?˜ì‹¤ ???ˆìŠµ?ˆë‹¤!",
                                             f"Welcome, {l_id}! Your subscription expired and you were automatically downgraded to a Free User (5-sample analysis possible). You can extend your subscription anytime in the sidebar!"))
                                st.rerun()
                            except Exception as e:
                                st.error(_(f"ë§Œë£Œ ?Œì› ?ë™ ?„í™˜ ì²˜ë¦¬ ì¤??¤ë¥˜ê°€ ë°œìƒ?ˆìŠµ?ˆë‹¤: {e}", f"Error during automatic expiry downgrade: {e}"))
                        else:
                            st.error(_(f"???´ìš© ê¸°ê°„??ë§Œë£Œ?˜ì—ˆ?µë‹ˆ?? (ë§Œë£Œ?? {result[1]})", f"??Subscription expired. (Expiry date: {result[1]})"))
                    else:
                        st.session_state.user_id = l_id.strip()
                        st.session_state.user_role = result[0]
                        st.session_state.expiry_date = result[1]
                        st.query_params["login_user"] = l_id.strip()
                        st.query_params["login_token"] = hashlib.sha256(f"{l_id.strip()}:AHP_MASTER_SECURE_SALT_2026_!@#".encode()).hexdigest()
                        st.query_params["last_activity"] = str(int(time.time()))
                        if 'signup_paypal_user' in st.session_state:
                            del st.session_state.signup_paypal_user
                        st.success(_(f"?˜ì˜?©ë‹ˆ?? {l_id}??", f"Welcome, {l_id}!"))
                        st.rerun()
                else:
                    st.error(_("?„ì´???ëŠ” ë¹„ë?ë²ˆí˜¸ê°€ ?¼ì¹˜?˜ì? ?ŠìŠµ?ˆë‹¤.", "Incorrect username or password."))

        with tab_signup:
            if st.session_state.get('signup_paypal_user'):
                user_id = st.session_state.signup_paypal_user
                st.markdown("### ?’³ Upgrade to Official User via PayPal")
                st.info(f"You have registered successfully as **{user_id}**. To complete your upgrade to Official User immediately, please use the PayPal button below:")
                
                paypal_client_id = st.secrets.get("PAYPAL_CLIENT_ID", "sb")
                paypal_html = f"""
                <div id="paypal-button-container-signup" style="text-align: center; max-width: 100%;"></div>
                <script src="https://www.paypal.com/sdk/js?client-id={paypal_client_id}&currency=USD&locale=en_US"></script>
                <script>
                  paypal.Buttons({{
                    style: {{
                      layout: 'vertical',
                      color:  'gold',
                      shape:  'rect',
                      label:  'paypal',
                      height: 40
                    }},
                    createOrder: function(data, actions) {{
                      return actions.order.create({{
                        purchase_units: [{{
                          amount: {{
                            value: '350.00'
                          }},
                          payee: {{
                            email_address: 'jeon080423@gmail.com'
                          }}
                        }}]
                      }});
                    }},
                    onApprove: function(data, actions) {{
                      return actions.order.capture().then(function(details) {{
                        window.top.location.href = window.top.location.origin + window.top.location.pathname + "?paypal_order_id=" + data.orderID + "&user_id=" + encodeURIComponent("{user_id}");
                      }});
                    }},
                    onError: function(err) {{
                      console.error(err);
                      alert("Payment failed or was cancelled.");
                    }}
                  }}).render('#paypal-button-container-signup');
                </script>
                """
                st.components.v1.html(paypal_html, height=180)
                
                if st.button("Back to Login / Sign Up", use_container_width=True, key="back_to_login_btn"):
                    del st.session_state.signup_paypal_user
                    st.rerun()
            else:
                agreements = show_agreement_ui()
                s_id = st.text_input(_("?„ì´??(?´ë©”??ì£¼ì†Œ)", "Username (Email Address)"), key="s_id")
                s_pw = st.text_input(_("ë¹„ë?ë²ˆí˜¸", "Password"), type="password", key="s_pw")
                s_role_selection = st.radio(_("?´ìš© ê¶Œí•œ ? íƒ", "Select Account Type"), (_("ë¬´ë£Œ?¬ìš©??, "Free User"), _("?•ì‹ ?¬ìš©??(3ê°œì›”, ê¸°ëŠ¥ ë¬´ì œ??", "Official User (3 Months, Unlimited)")), index=0)
                
                if "?•ì‹" in s_role_selection or "Official" in s_role_selection:
                    if st.session_state.get('lang', 'ko') == 'en':
                        st.warning("? ï¸ Official User Signup Guide")
                        st.info("Official users are registered as a **Free User** first.")
                        st.info("You will be prompted to pay via **PayPal** immediately after clicking 'Register' to upgrade your account instantly. (Access period is 3 months)")
                    else:
                        st.warning("? ï¸ ?•ì‹ ?¬ìš©??ê°€???ˆë‚´")
                        acc_info_html = """
                        <div style="background-color: #f7fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px; margin-bottom: 12px;">
                          <div style="font-weight: bold; font-size: 0.88rem; color: #2d3748; margin-bottom: 6px;">?¦ ê³„ì¢Œ?´ì²´ ?…ê¸ˆ ?•ë³´</div>
                          <div style="font-size: 0.82rem; color: #4a5568; line-height: 1.5;">
                            ??<b>?€?‰ëª…</b>: ì¹´ì¹´?¤ë±…??br>
                            ??<b>?ˆê¸ˆì£?/b>: ?ˆã……??br>
                            ??<b>?´ìš©?”ê¸ˆ</b>: 50ë§Œì›<br>
                            <div style="display: flex; align-items: center; gap: 8px; margin-top: 6px;">
                              <span style="font-family: monospace; font-weight: bold; background-color: #edf2f7; padding: 4px 8px; border-radius: 4px; color: #2d3748;">3333-23-8667708</span>
                              <button onclick="(function(){
                                const el = document.createElement('textarea');
                                el.value = '3333-23-8667708';
                                document.body.appendChild(el);
                                el.select();
                                document.execCommand('copy');
                                document.body.removeChild(el);
                                alert('ê³„ì¢Œë²ˆí˜¸ê°€ ë³µì‚¬?˜ì—ˆ?µë‹ˆ?? 3333-23-8667708 (ì¹´ì¹´?¤ë±…??');
                              })()" style="background-color: #3182ce; color: white; border: none; padding: 4px 8px; border-radius: 4px; cursor: pointer; font-size: 0.78rem; font-weight: bold;">?“‹ ë³µì‚¬</button>
                            </div>
                          </div>
                        </div>
                        """
                        st.markdown(acc_info_html, unsafe_allow_html=True)
                        st.info("ê´€ë¦¬ìê°€ ?…ê¸ˆ ?•ì¸ ??**?•ì‹ ?¬ìš©??*ë¡?ê¶Œí•œ??ë³€ê²½ë©?ˆë‹¤, ?¹ì¸ ?„ë£Œ ???´ë©”?¼ë¡œ ?ˆë‚´???œë¦½?ˆë‹¤. (?¬ìš© ê¸°ê°„?€ 3ê°œì›” ?…ë‹ˆ??")
                
                if st.button(_("ê°€?…ì‹ ì²?, "Register")):
                    if not agreements.get("agree_personal_info"):
                        st.error(_("ê°œì¸?•ë³´ ?˜ì§‘Â·?´ìš©???™ì˜?´ì•¼ ê°€?…ì‹ ì²?•  ???ˆìŠµ?ˆë‹¤.", "You must agree to the privacy policy to register."))
                    elif not validate_email(s_id):
                        st.error(_("?¬ë°”ë¥??´ë©”???•ì‹???„ë‹™?ˆë‹¤.", "Invalid email format."))
                    elif not validate_password(s_pw):
                        st.error(_("ë¹„ë?ë²ˆí˜¸??ë¬¸ì+?¹ìˆ˜ë¬¸ì?¬ì•¼ ?©ë‹ˆ??", "Password must contain both letters and special characters."))
                    else:
                        restore_from_deleted_sheet(s_id.strip())
                        initial_role = 'temp'
                        actual_requested_role = 'official' if ("?•ì‹" in s_role_selection or "Official" in s_role_selection) else 'temp'
                        # ?™ì˜ ê¸°ë¡??'Y'ë¡??€??
                        if add_user(s_id.strip(), s_pw, initial_role, agree_info="Y"):
                            if actual_requested_role == 'official':
                                send_application_email(s_id.strip())
                                if st.session_state.get('lang', 'ko') == 'en':
                                    st.session_state.signup_paypal_user = s_id.strip()
                            st.success(_("ë¬´ë£Œ?¬ìš©?ë¡œ ê°€???„ë£Œ ?˜ì—ˆ?µë‹ˆ??, "Successfully registered as a Free User."))
                            st.rerun()
                        else:
                            st.error(_("?´ë? ì¡´ì¬?˜ëŠ” ?„ì´?”ì…?ˆë‹¤.", "ID already exists."))

        with tab_find_pw:
            st.write(_("ê°€?????¬ìš©???´ë©”??ì£¼ì†Œë¥??…ë ¥?´ì£¼?¸ìš”. ?´ë©”?¼ë¡œ ?ˆë¡œ???„ì‹œ ë¹„ë?ë²ˆí˜¸ê°€ ë°œì†¡?©ë‹ˆ??",
                       "Please enter the email address used at registration. A new temporary password will be sent to your email."))
            f_id = st.text_input(_("ê°€?…í•œ ?„ì´??(?´ë©”??", "Registered ID (Email)"), key="f_id")
            if st.button(_("?„ì‹œ ë¹„ë?ë²ˆí˜¸ ?„ì†¡", "Send Temporary Password")):
                if not f_id:
                    st.warning(_("?´ë©”??ì£¼ì†Œë¥??…ë ¥?´ì£¼?¸ìš”.", "Please enter your email address."))
                else:
                    conn = sqlite3.connect('users.db')
                    c = conn.cursor()
                    c.execute("SELECT id FROM users WHERE id=?", (f_id.strip(),))
                    user_exists = c.fetchone()
                    conn.close()
                    
                    if user_exists:
                        temp_pw = generate_temp_password()
                        change_user_password(f_id.strip(), temp_pw)
                        
                        if send_password_recovery_email(f_id.strip(), temp_pw):
                            st.success(_(f"'{f_id}'ë¡??„ì‹œ ë¹„ë?ë²ˆí˜¸ë¥??„ì†¡?ˆìŠµ?ˆë‹¤.\n?´ë©”?¼ì„ ?•ì¸?´ì£¼?¸ìš”.", f"Temporary password sent to '{f_id}'.\nPlease check your email."))
                        else:
                            st.error(_("?´ë©”???„ì†¡ ì¤??¤ë¥˜ê°€ ë°œìƒ?ˆìŠµ?ˆë‹¤.", "Error sending email."))
                    else:
                        st.error(_("?±ë¡?˜ì? ?Šì? ?„ì´?”ì…?ˆë‹¤.", "ID is not registered."))

    else:
        role_disp = _("ê´€ë¦¬ì", "Admin") if st.session_state.user_role == 'admin' else (_("?•ì‹ ?¬ìš©??, "Official User") if st.session_state.user_role == 'official' else _("ë¬´ë£Œ?¬ìš©??, "Free User"))
        
        expiry_info = ""
        if st.session_state.expiry_date:
            expiry_label = _("ë§Œë£Œ?? ", "Expiry: ")
            expiry_info = f' | {expiry_label}{st.session_state.expiry_date}'
            
        info_html = f"""<div style="background-color: #e8f5e9; border: 1px solid #c8e6c9; border-radius: 6px; color: #2e7d32; font-weight: bold; font-size: 0.85rem; padding: 8px 10px; text-align: center; margin-bottom: 8px;">
?‘¤ {st.session_state.user_id} ({role_disp}{expiry_info})
</div>"""
        st.markdown(info_html, unsafe_allow_html=True)
        
        if st.session_state.user_role == 'temp':
            with st.expander(_("?’³ ?•ì‹ ?¬ìš©???¹ê²©/ê²°ì œ", "?’³ Upgrade to Official User"), expanded=False):
                if st.session_state.lang == 'en':
                    st.markdown("##### ?’³ PayPal Membership Upgrade")
                    st.info("Upgrade to **Official User** to get unlimited access (3 months) for **$350.00 USD**.")
                    
                    paypal_client_id = st.secrets.get("PAYPAL_CLIENT_ID", "sb")
                    user_id = st.session_state.user_id
                    
                    paypal_html = f"""
                    <div id="paypal-button-container" style="text-align: center; max-width: 100%;"></div>
                    <script src="https://www.paypal.com/sdk/js?client-id={paypal_client_id}&currency=USD&locale=en_US"></script>
                    <script>
                      paypal.Buttons({{
                        style: {{
                          layout: 'vertical',
                          color:  'gold',
                          shape:  'rect',
                          label:  'paypal',
                          height: 40
                        }},
                        createOrder: function(data, actions) {{
                          return actions.order.create({{
                            purchase_units: [{{
                              amount: {{
                                value: '350.00'
                              }},
                              payee: {{
                                email_address: 'jeon080423@gmail.com'
                              }}
                            }}]
                          }});
                        }},
                        onApprove: function(data, actions) {{
                          return actions.order.capture().then(function(details) {{
                            window.top.location.href = window.top.location.origin + window.top.location.pathname + "?paypal_order_id=" + data.orderID + "&user_id=" + encodeURIComponent("{user_id}");
                          }});
                        }},
                        onError: function(err) {{
                          console.error(err);
                          alert("Payment failed or was cancelled.");
                        }}
                      }}).render('#paypal-button-container');
                    </script>
                    """
                    st.components.v1.html(paypal_html, height=180)
                else:
                    st.markdown("##### ?’³ ?•ì‹ ?¬ìš©???¹ê²© ?”ì²­")
                    
                    acc_info_html = """
                    <div style="background-color: #f7fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px; margin-bottom: 12px;">
                      <div style="font-size: 0.82rem; color: #4a5568; line-height: 1.5;">
                        ??<b>?€?‰ëª…</b>: ì¹´ì¹´?¤ë±…??br>
                        ??<b>?ˆê¸ˆì£?/b>: ?ˆã……??br>
                        ??<b>?´ìš©?”ê¸ˆ</b>: 50ë§Œì› (3ê°œì›”)<br>
                        <div style="display: flex; align-items: center; gap: 8px; margin-top: 6px;">
                          <span style="font-family: monospace; font-weight: bold; background-color: #edf2f7; padding: 4px 8px; border-radius: 4px; color: #2d3748;">3333-23-8667708</span>
                          <button onclick="(function(){
                            const el = document.createElement('textarea');
                            el.value = '3333-23-8667708';
                            document.body.appendChild(el);
                            el.select();
                            document.execCommand('copy');
                            document.body.removeChild(el);
                            alert('ê³„ì¢Œë²ˆí˜¸ê°€ ë³µì‚¬?˜ì—ˆ?µë‹ˆ?? 3333-23-8667708 (ì¹´ì¹´?¤ë±…??');
                          })()" style="background-color: #3182ce; color: white; border: none; padding: 4px 8px; border-radius: 4px; cursor: pointer; font-size: 0.78rem; font-weight: bold;">?“‹ ë³µì‚¬</button>
                        </div>
                      </div>
                    </div>
                    """
                    st.markdown(acc_info_html, unsafe_allow_html=True)
                    st.info("?…ê¸ˆ ?„ë£Œ ???„ë˜ ë²„íŠ¼???´ë¦­?˜ì‹œë©??¹ê²© ?”ì²­??ê´€ë¦¬ì?ê²Œ ì¦‰ì‹œ ?„ì†¡?©ë‹ˆ??")
                    
                    if st.button("?•ì‹ ?¬ìš©???„í™˜ ?”ì²­", use_container_width=True, key="sidebar_upgrade_btn"):
                        if send_conversion_request_email(st.session_state.user_id):
                            st.success("?•ì‹ ?¬ìš©???„í™˜?”ì²­???„ë£Œ ?˜ì—ˆ?µë‹ˆ?? ?…ê¸ˆ ?•ì¸ ???•ì‹?¬ìš©?ë¡œ ?„í™˜???œë¦½?ˆë‹¤")
                        else:
                            st.error("?”ì²­ ?„ì†¡ ?¤íŒ¨. ê´€ë¦¬ì?ê²Œ ë¬¸ì˜ë°”ë?ˆë‹¤.")
        
    if st.session_state.user_id is not None:
        if st.session_state.user_role == 'admin':
            btn_label = _("?”§ ê´€ë¦¬ì ?”ë©´ ?«ê¸°", "?”§ Exit Admin Panel") if st.session_state.get('admin_mode', False) else _("?”§ ê´€ë¦¬ì ?”ë©´ ?‘ì†", "?”§ Connect to Admin Panel")
            if st.button(btn_label):
                st.session_state.admin_mode = not st.session_state.admin_mode
                st.rerun()

        with st.expander(_("?” ë¹„ë?ë²ˆí˜¸ ë³€ê²?, "?” Change Password")):
            cur_pw = st.text_input(_("?„ì¬ ë¹„ë?ë²ˆí˜¸", "Current Password"), type="password", key="chg_cur_new")
            new_pw_val = st.text_input(_("??ë¹„ë?ë²ˆí˜¸", "New Password"), type="password", key="chg_new_new")
            confirm_pw = st.text_input(_("??ë¹„ë?ë²ˆí˜¸ ?•ì¸", "Confirm New Password"), type="password", key="chg_conf_new")
            
            if st.button(_("ë¹„ë?ë²ˆí˜¸ ë³€ê²?, "Change Password"), key="btn_chg_pw_new"):
                if new_pw_val != confirm_pw:
                    st.error(_("??ë¹„ë?ë²ˆí˜¸ê°€ ?¼ì¹˜?˜ì? ?ŠìŠµ?ˆë‹¤.", "New passwords do not match."))
                elif not validate_password(new_pw_val):
                    st.error(_("ë¹„ë?ë²ˆí˜¸??4???´ìƒ, ?ë¬¸+?¹ìˆ˜ë¬¸ìë¥??¬í•¨?´ì•¼ ?©ë‹ˆ??", "Password must be at least 4 characters and contain letters and special characters."))
                else:
                    chk_res = check_login(st.session_state.user_id, cur_pw)
                    if chk_res:
                        change_user_password(st.session_state.user_id, new_pw_val)
                        st.success(_("ë¹„ë?ë²ˆí˜¸ê°€ ë³€ê²½ë˜?ˆìŠµ?ˆë‹¤.", "Password successfully changed."))
                    else:
                        st.error(_("?„ì¬ ë¹„ë?ë²ˆí˜¸ê°€ ?¬ë°”ë¥´ì? ?ŠìŠµ?ˆë‹¤.", "Incorrect current password."))


        if st.button(_("ë¡œê·¸?„ì›ƒ", "Log Out"), key="btn_logout_new"):
            st.session_state.user_id = None
            st.session_state.user_role = None
            st.session_state.expiry_date = None
            st.session_state.admin_mode = False
            st.query_params.pop("login_user", None)
            st.query_params.pop("login_token", None)
            st.rerun()



    st.markdown(get_fee_info_text(), unsafe_allow_html=True)

    st.markdown("---")


    
    if st.session_state.get('lang', 'ko') == 'en':
        st.markdown("""
        ### Contact
        - **Email**: jeon080423@gmail.com
        - **KakaoTalk ID**: AHPkr
        - **Homepage**: [morison.tistory.com](https://morison.tistory.com/)
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        ### ë¬¸ì˜ì²?
        - **?´ë©”??*: jeon080423@gmail.com
        - **ì¹´í†¡ID**: AHPkr
        - **?ˆí˜?´ì?**: [morison.tistory.com](https://morison.tistory.com/)

        """, unsafe_allow_html=True)

# =============================================================================
# 4. Main Content Logic
# =============================================================================

if st.session_state.get('page', 'main') == 'guide':
    if st.button("??Back to AHP Analysis Tool", use_container_width=True, key="btn_back_to_main"):
        st.session_state.page = "main"
        st.rerun()
    
    st.title("?“– AHP Master - English User Guide")
    st.markdown("""
    ?? **Welcome!** **AHP Master** is a smart web service that automatically processes the entire Analytic Hierarchy Process (AHP) workflow in 1 second, without requiring complex equations or statistical software.
    This guide is designed to walk first-time users through the step-by-step process of completing their academic thesis statistics and decision analysis smoothly.
    
    ---
    
    ### ?“Œ Step 1: Prepare the Excel Template (Write & Customize)
    AHP Master uses a specifically formatted Excel file to read your survey data.
    
    1. **Download Template**: Go to the AHP Master website (https://ahpkrj.streamlit.app/) and click the **[Download Excel Template]** button on the home screen.
    2. **?”¥ Customize to Fit Your Model (Important)**:
       * The default template items (evaluation criteria, alternatives, etc.) and hierarchical structure can be freely edited to match your specific research model.
       * You can add or delete criteria to construct your own custom AHP model.
    3. **Enter Survey Data**: Open the customized Excel template and enter your pairwise comparison survey responses.
       * **Evaluation Scale**: Uses Saaty's 1-9 fundamental scale (e.g., enter 7 if item A is much more important than B, enter 1 if they are equally important).
       * **Note**: Be careful not to break the core structure (sheet configuration, etc.) of the template.
    
    ### ?“¥ Step 2: Upload File & Run Basic Analysis
    Once your data entry is complete, it's time to run the analysis.
    
    1. **File Upload**: Drag and drop your Excel file into the **[Drag and drop file here]** zone in the center of the screen, or click **[Browse files]** to select your file.
    2. **Automatic Execution**: The system will instantly run the complex matrix calculations in the background. Basic analysis typically completes in 1 to 3 seconds.
    
    ### ?™ï¸ Step 3: Utilize [Analysis Settings] in the Sidebar
    After uploading, you can fine-tune the analysis details through the "Analysis Settings" in the left sidebar to suit your research methodology.
    
    1. **Select Aggregation Method**:
       * You can set specific parameters like the weight integration method (Geometric Mean vs. Arithmetic Mean) or the decimal precision required for your research.
    2. **CR Calibration Settings (Optional)**:
       * You can set boundaries such as how much you allow the original response to change (Correction Intensity/Learning Rate) when performing Consistency Ratio (CR) calibration.
       * *(If accessing on a mobile device, tap the `>` icon in the top left to reveal the sidebar menu.)*
    
    ### ?“Š Step 4: Consistency Validation & Automatic Calibration (CR)
    This is the step to validate the logical consistency of responses, which is critical in AHP academic studies.
    
    1. **Check Initial CR Value**: Check the **Consistency Ratio (CR)** displayed in the results panel.
       * `CR < 0.1` (Green): Indicates highly consistent and logical responses (Passed).
       * `CR > 0.1` (Red): Indicates logical contradictions exceed the standard limit (Needs Calibration).
    2. **?”¥ One-Click Auto Calibration**: If the initial CR value exceeds 0.1, do not worry. Simply click the **[CR Auto Calibration]** button. AHP Master's optimization algorithm will adjust the CR value to under 0.1 automatically, preserving the original response preferences as much as possible.
    
    ### ?† Step 5: Check Weights & Save Results
    Once all validations and settings are complete, use the final results in your report or paper.
    
    1. **Check Weights & Rankings**:
       * **Main/Sub-Criteria Weights**: View the weight percentages and decimals representing the importance of each item.
       * **Global Rank**: View the overall 1st-to-last rankings of the items in an intuitive table and visual Plotly charts.
    2. **Download Results (Excel/Image)**:
       * Click the **[Download Results (Excel)]** button at the bottom of the screen to save the results in a clean table format ready to copy-paste.
       * Click the camera icon in the top right of the Plotly charts to save the charts as high-resolution images (PNG).
    
    ---
    
    ### ?’¡ Frequently Asked Questions (FAQ)
    
    * **Q1. Can I change the template items to fit my specific paper?**
      * **Yes, absolutely!** The default template is only an example. You can add or delete rows and columns, rename text, and modify items to build **your own custom hierarchical model (Custom Model)** to fit your evaluation criteria and alternative count.
    * **Q2. Can I analyze data from multiple survey respondents (group analysis) at once?**
      * Yes! If you have multiple respondents, you can calculate the geometric mean of individual pairwise comparisons in Excel, enter the aggregated figures into the template, and upload it to calculate the group weights at once.
    * **Q3. I see an "Error" message during upload. Why?**
      * In the customization process, the required sheets' layout may have been broken, or some number input cells might have empty (Null) values or text instead of numbers. Please review your Excel template to ensure all numeric inputs are complete.
    
    ---
    
    ### ?’¬ Contact & Support
    If you have any questions during analysis, or need custom AHP consulting (expert survey execution, thesis statistical consulting, etc.), please contact us:
    * **Email**: jeon080423@gmail.com
    * **KakaoTalk ID**: AHPkr
    * **Mobile**: +82-10-2142-2610
    """)
    
    if st.button("??Back to AHP Analysis Tool", use_container_width=True, key="btn_back_to_main_bottom"):
        st.session_state.page = "main"
        st.rerun()
    st.stop()

# ë©”ì¸ ?¤ë” ?ì—­
try:
    # ?±ëŠ¥ ìµœì ?”ë? ?„í•´ ë©”ì¸ ?”ë©´?ì„œ??êµ¬ê? ?œíŠ¸ ?€??ë¡œì»¬ DB??ë°©ë¬¸ ë¡œê·¸ ?˜ë§Œ ì¦‰ì‹œ ì§‘ê³„?©ë‹ˆ??
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM visit_logs")
    total_visits = c.fetchone()[0]
    conn.close()
except Exception:
    total_visits = 0

col_main_title, col_settings_title = st.columns([3.0, 1.1], gap="large")
with col_main_title:
    st.title(_("AHP ?˜ì‚¬ê²°ì • ë¶„ì„ ?”ë£¨??, "AHP Decision Analysis Solution"))

with col_settings_title:
    visitor_label = _("ì´??„ì  ë°©ë¬¸????, "Total Visitors")
    visitor_unit = _("ëª?, " visitors")
    counter_html = f"""
    <div style="text-align: right; margin-top: 32px;">
        <span style="font-size: 0.85rem; color: #0369a1; font-weight: bold;">
            {visitor_label} : {total_visits:,}{visitor_unit}
        </span>
    </div>
    """
    st.markdown(counter_html, unsafe_allow_html=True)

col_main, col_settings = st.columns([3.0, 1.1], gap="large")
@st.dialog(_("?Œë¦¼", "Notice"))
def show_warning_dialog():
    st.warning(_("? ï¸ ë¶„ì„ ???•ì¸ ê°€?¥í•©?ˆë‹¤. (?°ì´?°ë? ë¨¼ì? ?…ë¡œ?œí•˜?¸ìš”)", "? ï¸ Available after analysis. (Please upload data first)"))

# ---------- CR Distortion Verification Dialog ----------
@st.dialog(_("?” CR ë³´ì • ê²°ê³¼ ?œê³¡ ê²€ì¦?, "?” CR Consistency Distortion Verification"), width="large")
def show_cr_distortion_dialog():
    import numpy as np
    from cr_analysis import run_analysis, generate_report, matrix_to_heatmap_img
        
    st.info(_("?“Š ?…ë¡œ?œëœ ë©”ì¸ ê¸°ì? ?°ì´???‘ë‹µ???„ì²´ ê¸°í•˜?‰ê·  ?‰ë ¬)ë¥?ë°”íƒ•?¼ë¡œ ê²€ì¦ì„ ?˜í–‰?©ë‹ˆ??", "?“Š Performing verification based on the uploaded Main Criteria data (geometric mean matrix of all respondents)."))
    original_matrix = st.session_state.uploaded_matrix

    # Determine selected CR option
    option = st.session_state.get('cr_threshold_label', '0.1')
    if option in ["ë³´ì • ?˜ì? ?ŠìŒ", "Do Not Correct"]:
        corrected_matrix = original_matrix.copy()
        option_name = _("ë³´ì • ????, "Do Not Correct")
    else:
        corrected_matrix, cr_val, iters, _unused = improve_consistency(
            original_matrix,
            threshold=float(option),
            min_val=-9,
            max_val=9
        )
        option_name = option

    metrics = run_analysis(original_matrix, corrected_matrix, option_name)

    # --- Two-column layout: left=explanation, right=results ---
    left_col, right_col = st.columns([1.2, 1])

    with right_col:
        st.subheader(_("?“Š ê²€ì¦?ê²°ê³¼", "?“Š Verification Results"))
        st.dataframe(pd.DataFrame([metrics]), use_container_width=True)

        # Heatmaps side by side
        orig_img = matrix_to_heatmap_img(original_matrix, _("?ë³¸ ?‰ë ¬", "Original Matrix"))
        corr_img = matrix_to_heatmap_img(corrected_matrix, option_name)
        hm1, hm2 = st.columns(2)
        with hm1:
            st.image(f"data:image/png;base64,{orig_img}", caption=_("?ë³¸ ?‰ë ¬", "Original Matrix"), use_container_width=True)
        with hm2:
            st.image(f"data:image/png;base64,{corr_img}", caption=_("ë³´ì • ?‰ë ¬", "Corrected Matrix"), use_container_width=True)

    with left_col:
        st.subheader(_("?§ª ê²€ì¦?ë°©ë²•", "?§ª Verification Method"))
        st.markdown(_(
            f"""
ë³?ê²€ì¦ì? CR(?¼ê???ë¹„ìœ¨) ë³´ì • ê³¼ì •?ì„œ **?ë³¸ ?‘ë‹µ ?°ì´?°ê? ?¼ë§ˆ??ë³€?•ë˜?ˆëŠ”ì§€**ë¥??•ëŸ‰?ìœ¼ë¡?ì¸¡ì •?©ë‹ˆ??

**ê²€ì¦??ˆì°¨:**
1. **?ë³¸ ?‰ë ¬ ?•ë³´** ???¤ë¬¸ ?‘ë‹µ?ì˜ ?ë?ë¹„êµ ?ë‹¨ ?‰ë ¬??ê·¸ë?ë¡??¬ìš©?©ë‹ˆ??
2. **ë³´ì • ?‰ë ¬ ?ì„±** ??? íƒ??CR ?„ê³„ê°?`{option_name}`)???°ë¼ ë°˜ë³µ ?˜ë ´ ì¡°ì •ë²?Iterative Adjustment)?¼ë¡œ ë³´ì •???‰ë ¬???ì„±?©ë‹ˆ??
3. **ì°¨ì´ ë¶„ì„** ???ë³¸ê³?ë³´ì • ?‰ë ¬ ê°?4ê°€ì§€ ?˜ë¦¬??ì§€?œë? ê³„ì‚°?©ë‹ˆ??
   - **? í´ë¦¬ë“œ ê±°ë¦¬**: ?‰ë ¬ ?ì†Œ ê°?ì§ì„  ê±°ë¦¬
   - **ë§¨í•´??ê±°ë¦¬**: ?‰ë ¬ ?ì†Œ ê°??ˆë? ì°¨ì´????
   - **ì½”ì‚¬??? ì‚¬??*: ???‰ë ¬ ë²¡í„°??ë°©í–¥ ?¼ì¹˜??
   - **?œê³¡ ?ìˆ˜**: ??ì§€?œë“¤??ì¢…í•©???œê³¡ ?˜ì? ì§€??
4. **ì¢…í•© ?ì •** ???œê³¡ ?ìˆ˜ë¥?ê¸°ì??¼ë¡œ ë³´ì •??? ë¢°?±ì„ ?‰ê??©ë‹ˆ??

> ?’¡ ?œê³¡ ?ìˆ˜ê°€ ??„?˜ë¡ ë³´ì •???ë³¸ ?‘ë‹µ??ê²½í–¥?±ì„ ??ë³´ì¡´?ˆìŒ???˜ë??©ë‹ˆ??

---
""",
            f"""
This verification quantitatively measures **how much the original response data was altered** during the CR (Consistency Ratio) correction process.

**Verification Procedure:**
1. **Obtain Original Matrix** ??Use the respondent's raw pairwise comparison judgment matrix as-is.
2. **Generate Corrected Matrix** ??Apply the Iterative Adjustment method based on the selected CR threshold (`{option_name}`) to produce a corrected matrix.
3. **Difference Analysis** ??Calculate 4 mathematical metrics between the original and corrected matrices:
   - **Euclidean Distance**: Straight-line distance between matrix elements
   - **Manhattan Distance**: Sum of absolute element-wise differences
   - **Cosine Similarity**: Directional alignment of the two matrix vectors
   - **Distortion Score**: Composite index summarizing overall distortion
4. **Overall Verdict** ??Evaluate the reliability of the correction based on the Distortion Score.

> ?’¡ A lower Distortion Score means the correction better preserved the original response patterns.

---
"""))

        st.subheader(_("?“ ê²°ê³¼ ?´ì„", "?“ Interpretation"))

        # Extract metric values
        euc = metrics.get("euclidean", 0)
        man = metrics.get("manhattan", 0)
        cos = metrics.get("cosine_similarity", 1)
        dist = metrics.get("distortion_score", 0)

        st.markdown(_( 
            f"""
**1. ? í´ë¦¬ë“œ ê±°ë¦¬ (Euclidean Distance): `{euc:.6f}`**  
?ë³¸ ?‰ë ¬ê³?ë³´ì • ?‰ë ¬ ?¬ì´??ì§ì„  ê±°ë¦¬?…ë‹ˆ??  
ê°’ì´ **0??ê°€ê¹Œìš¸?˜ë¡** ë³´ì •???ë³¸??ê±°ì˜ ë³€?•í•˜ì§€ ?Šì•˜?Œì„ ?˜ë??©ë‹ˆ??

**2. ë§¨í•´??ê±°ë¦¬ (Manhattan Distance): `{man:.6f}`**  
ê°??ì†Œë³?ì°¨ì´???ˆë?ê°??©ì…?ˆë‹¤.  
? í´ë¦¬ë“œ ê±°ë¦¬?€ ?¨ê»˜ ë³´ì •??**?„ì²´?ì¸ ë³€???¬ê¸°**ë¥??˜í??…ë‹ˆ??

**3. ì½”ì‚¬??? ì‚¬??(Cosine Similarity): `{cos:.6f}`**  
???‰ë ¬ ë²¡í„° ê°„ì˜ ë°©í–¥ ? ì‚¬?„ì…?ˆë‹¤.  
**1.0??ê°€ê¹Œìš¸?˜ë¡** ë³´ì • ?„í›„ ?‘ë‹µ ?¨í„´???™ì¼??ë°©í–¥??? ì??˜ê³  ?ˆìŠµ?ˆë‹¤.

**4. ?œê³¡ ?ìˆ˜ (Distortion Score): `{dist:.6f}`**  
ì¢…í•©?ì¸ ?œê³¡ ?˜ì????˜í??´ëŠ” ì§€?œì…?ˆë‹¤.

---

""",
            f"""
**1. Euclidean Distance: `{euc:.6f}`**  
The straight-line distance between the original and corrected matrices.  
A value **close to 0** means the correction barely altered the original.

**2. Manhattan Distance: `{man:.6f}`**  
The sum of absolute element-wise differences.  
Together with Euclidean distance, it shows the **overall magnitude of change**.

**3. Cosine Similarity: `{cos:.6f}`**  
The directional similarity between the two matrix vectors.  
A value **close to 1.0** means the response pattern is preserved after correction.

**4. Distortion Score: `{dist:.6f}`**  
A composite index representing the overall distortion level.

---

"""))

        # Verdict
        if dist < 0.01:
            verdict_icon = "??
            verdict = _("?œê³¡ ?˜ì?: **ë§¤ìš° ??Œ** ??ë³´ì •???ë³¸ ?‘ë‹µ??ê±°ì˜ ë³€?•í•˜ì§€ ?Šì•˜?µë‹ˆ?? ? ë¢°?????ˆëŠ” ê²°ê³¼?…ë‹ˆ??",
                        "Distortion Level: **Very Low** ??The correction barely altered the original responses. The result is reliable.")
        elif dist < 0.05:
            verdict_icon = "?Ÿ¡"
            verdict = _("?œê³¡ ?˜ì?: **??Œ** ??ê²½ë???ì¡°ì •???ˆì—ˆ?¼ë‚˜ ?ë³¸ ê²½í–¥?±ì´ ??ë³´ì¡´?˜ì—ˆ?µë‹ˆ??",
                        "Distortion Level: **Low** ??Minor adjustments were made, but the original trends are well preserved.")
        elif dist < 0.15:
            verdict_icon = "?Ÿ "
            verdict = _("?œê³¡ ?˜ì?: **ë³´í†µ** ???¼ë? ë³€?•ì´ ë°œìƒ?ˆìŠµ?ˆë‹¤. ê²°ê³¼ ?´ì„??ì£¼ì˜ê°€ ?„ìš”?©ë‹ˆ??",
                        "Distortion Level: **Moderate** ??Some distortion occurred. Interpret results with caution.")
        else:
            verdict_icon = "?”´"
            verdict = _("?œê³¡ ?˜ì?: **?’ìŒ** ??ë³´ì • ê³¼ì •?ì„œ ?ë‹¹??ë³€?•ì´ ë°œìƒ?ˆìŠµ?ˆë‹¤. CR ?„ê³„ê°’ì„ ì¡°ì •?˜ê±°???ë³¸ ?°ì´?°ë? ?¬ê?? í•˜?¸ìš”.",
                        "Distortion Level: **High** ??Significant distortion occurred during correction. Consider adjusting the CR threshold or reviewing the original data.")

        st.markdown(f"### {verdict_icon} {_('ì¢…í•© ?ì •', 'Overall Verdict')}")
        st.info(verdict)


with col_settings:
    if st.session_state.get('admin_mode', False) and st.session_state.get('user_role') == 'admin':
        pass
    else:
        with st.container(border=True):
            st.markdown(f'<h4 style="color:black; font-family:Arial, sans-serif; font-weight:bold; margin-top:0; margin-bottom:15px; font-size:1.1rem;">{_("AHP ë¶„ì„ ?¤ì •", "Analysis Settings")}</h4>', unsafe_allow_html=True)
            ahp_method_label = st.radio(_("ë¶„ì„ ê¸°ë²•", "Analysis Method"), (_('?¼ë°˜ AHP (Traditional AHP)', 'Traditional AHP'), _('?¼ì? AHP (Fuzzy AHP)', 'Fuzzy AHP')), index=0)
            ahp_method = 'traditional' if '?¼ë°˜' in ahp_method_label or 'Traditional' in ahp_method_label else 'fuzzy'
            mean_method_label = st.radio(_("?‰ê·  ?°ì¶œ ë°©ì‹", "Aggregation Method"), (_('ê¸°í•˜?‰ê·  (Geometric)', 'Geometric Mean'), _('?°ìˆ ?‰ê·  (Arithmetic)', 'Arithmetic Mean')), index=0)
            mean_method = 'geometric' if 'ê¸°í•˜' in mean_method_label or 'Geometric' in mean_method_label else 'arithmetic'
            cr_threshold_label = st.selectbox(
                _("?¼ê???ë¹„ìœ¨(CR) ?„ê³„ê°?, "Consistency Ratio (CR) Threshold"), 
                [_("0.1", "0.1"), _("0.15", "0.15"), _("0.2", "0.2"), _("ë³´ì • ?˜ì? ?ŠìŒ", "Do Not Correct")], 
                index=0,
                key="cr_threshold_label",
                help=_(
                    "?„ê³„ê°??¤ì •(0.1, 0.15 ?ëŠ” 0.2)?€ ?¼ê???ë¹„ìœ¨(CR)???´ë‹¹ ?˜ì¹˜ë¡??•í™•?˜ê²Œ ?¼ì¹˜?œí‚¤??ê²ƒì´ ?„ë‹ˆ?? ?´ë‹¹ ?„ê³„ê°??´í•˜ë¡?ë§Œë“œ??ê²ƒì„ ?˜ë??©ë‹ˆ?? ?´ë? ?„ê³„ê°??´í•˜???°ì´?°ëŠ” ë³´ì •?˜ì? ?Šìœ¼ë©? ?´ë? ?µí•´ ?ë³¸ ?‘ë‹µ??ê³¼ë„?˜ê²Œ ?œê³¡?˜ëŠ” ê²ƒì„ ë°©ì??©ë‹ˆ??",
                    "The threshold setting (0.1, 0.15 or 0.2) does not force the consistency ratio (CR) to equal that value. Instead, it adjusts the CR to be less than or equal to the threshold. If a matrix is already within the threshold, no correction is applied, preventing excessive distortion of the original responses."
                )
            )
            if "ë³´ì • ?˜ì? ?ŠìŒ" in cr_threshold_label or "Do Not Correct" in cr_threshold_label:
                cr_threshold = 999.0
                learning_rate = 0.0
            else:
                cr_threshold = float(cr_threshold_label)
            if "ë³´ì • ?˜ì? ?ŠìŒ" in cr_threshold_label or "Do Not Correct" in cr_threshold_label:
                max_iter_val = 0
                st.number_input(_("ìµœë? ë³´ì • ë°˜ë³µ ?Ÿìˆ˜", "Max Correction Iterations"), min_value=0, max_value=500, value=0, step=50, disabled=True, key="max_iter_disabled")
            else:
                max_iter_val = st.number_input(_("ìµœë? ë³´ì • ë°˜ë³µ ?Ÿìˆ˜", "Max Correction Iterations"), min_value=10, max_value=500, value=500, step=50, key="max_iter_enabled")
        
            if "ë³´ì • ?˜ì? ?ŠìŒ" in cr_threshold_label or "Do Not Correct" in cr_threshold_label:
                st.slider(_("ë³´ì • ê°•ë„ (Learning Rate)", "Correction Intensity (Learning Rate)"), min_value=0.0, max_value=0.9, value=0.0, step=0.1, disabled=True, key="learning_rate_disabled")
            else:
                learning_rate = st.slider(_("ë³´ì • ê°•ë„ (Learning Rate)", "Correction Intensity (Learning Rate)"), min_value=0.1, max_value=0.9, value=0.6, step=0.1, key="learning_rate_enabled")


        # 1. CR ë³´ì • ê²°ê³¼ ?œê³¡ ê²€ì¦?
        with st.expander(_("?” CR ë³´ì • ê²°ê³¼ ?œê³¡ ê²€ì¦?, "?” CR Consistency Distortion Verification"), expanded=False):
            if st.button(_("??ê²€ì¦??¤í–‰", "??Run Verification"), use_container_width=True, key="btn_cr_verify"):
                if "uploaded_matrix" not in st.session_state:
                    show_warning_dialog()
                else:
                    show_cr_distortion_dialog()

        # 2. ?¼ê???ë³´ì • ê¸°ì?
        with st.expander(_("?¹ï¸ ?¼ê???ë³´ì • ê¸°ì?", "?¹ï¸ Consistency Correction Standard"), expanded=False):
            st.markdown(_(r"""
            **ë³´ì • ë°©ë²•: ë°˜ë³µ ?˜ë ´ ì¡°ì •ë²?Iterative Adjustment)**
            ê°€ì¤‘ì¹˜ ?°ì¶œ ?Œê³ ë¦¬ì¦˜(Saaty)???˜í•´ ?ë‹¨ ?‰ë ¬??ë¹„ì¼ê´€??CR > ?„ê³„ê°???ê²½ìš°, ?˜í•™?ìœ¼ë¡??¼ê????‰ë ¬ê³??ë³¸ ?‰ë ¬???¼ì • ë¹„ìœ¨ë¡??¼í•©?˜ì—¬ ë°˜ë³µ?ìœ¼ë¡?ê°€ì¤‘ì¹˜ë¥?ë¯¸ì„¸ ì¡°ì •??ê²°ê³¼ë¥??œì‹œ?©ë‹ˆ??
        
            **?„ì¬ ë°©ë²•???¹ì§•:**
            1. **ìµœì†Œ ?ë‹¨ ?œê³¡**: ?ë³¸ ?¤ë¬¸ ?‘ë‹µ??ê²½í–¥?±ì„ ë³´ì¡´?˜ë©´???˜í•™???¼ê??±ë§Œ???•ë³´?©ë‹ˆ??
            2. **?ë™ ?˜ë ´**: ?¤ì •??ë°˜ë³µ ?Ÿìˆ˜ ?´ì—??CR ê°’ì„ ?„ê³„ê°??´í•˜ë¡??ë™ ê°œì„ ?©ë‹ˆ?? ($New = (1-\alpha) \times Old + \alpha \times Ideal$)
            3. **ê³¼ë„??ë³´ì • ë°©ì?**: ?„ê³„ê°??¤ì •(0.1, 0.15 ?ëŠ” 0.2)?€ CR ê°’ì„ ?•í™•??ë§ì¶”??ê²ƒì´ ?„ë‹ˆ???„ê³„ê°?'?´í•˜'ë¡?ë§Œë“œ??ê²ƒì„ ëª©í‘œë¡??©ë‹ˆ?? ?´ë? ?„ê³„ê°??´í•˜???‘ë‹µ?€ ë³´ì •???˜í–‰?˜ì? ?Šì•„ ?ë³¸ ?ë‹¨??ìµœë???ë³´ì¡´?©ë‹ˆ??
        
            """, r"""
            **Correction Method: Iterative Adjustment**
            If the judgment matrix is inconsistent (CR > threshold) based on Saaty's weight algorithm, it repeatedly adjusts the weights by mixing the original matrix with a mathematically consistent matrix.
        
            **Key Features:**
            1. **Minimal Distortion of Judgments**: Preserves the trends of the original survey responses while securing mathematical consistency.
            2. **Automatic Convergence**: Automatically improves the CR value to be below the threshold within the maximum number of iterations. ($New = (1-\alpha) \times Old + \alpha \times Ideal$)
            3. **Prevention of Excessive Correction**: The threshold setting (0.1, 0.15 or 0.2) targets bringing the CR 'below or equal to' the threshold, rather than matching it exactly. Responses already below the threshold are left uncorrected to preserve the original judgments as much as possible.
        
            """))

        # 3. ?´ìš©??ê°€?´ë“œ
        with st.expander(_("?“– ?´ìš©??ê°€?´ë“œ", "?“– User Guide"), expanded=False):
            st.markdown(_("AHP ë§ˆìŠ¤???œë¹„???¬ìš© ?¤ëª…??ë°?ê°€?´ë“œ ë§í¬?…ë‹ˆ??", "Link to the AHP Master user manual and guide."))
            if st.session_state.get('lang', 'ko') == 'en':
                if st.button("Read English User Guide", use_container_width=True, key="btn_read_guide"):
                    st.session_state.page = "guide"
                    st.rerun()
            else:
                st.link_button("?´ìš©??ê°€?´ë“œ ë°”ë¡œê°€ê¸?, "https://morison.tistory.com/103", use_container_width=True)

        with st.expander(_("?“ ?™ìˆ  ?¼ë¬¸ ë°??°êµ¬ ë³´ê³ ??ê¸°ì¬ ë°©ë²• ?ˆì‹œ", "?“ Example of citation in academic papers/reports"), expanded=False):
            st.info(_("AHP ë¶„ì„ ê²°ê³¼ë¥??™ìœ„ ?¼ë¬¸?´ë‚˜ ?°êµ¬ ë³´ê³ ?œì— ê¸°ìˆ ?????„ë˜ ?ˆì‹œë¬¸ì„ ì°¸ê³ ?˜ì—¬ ?¸ìš© ë°??œìˆ ?˜ì‹¤ ???ˆìŠµ?ˆë‹¤.",
                      "When describing AHP analysis results in your thesis or research report, you can refer to and cite the example below."))
            st.markdown(_("""
            > **[?¼ë¬¸ ê¸°ì¬ ?ˆì‹œë¬?**
            > 
            > "ë³??°êµ¬?ì„œ ?˜ì§‘???¤ë¬¸ ?°ì´?°ëŠ” ??ê¸°ë°˜ AHP ?„ìš© ë¶„ì„ ?”ë£¨?˜ì¸ 'AHP ë§ˆìŠ¤??ë¥??œìš©?˜ì—¬ ë¶„ì„???˜í–‰?˜ì??? Saaty(1980)??ê³„ì¸µë¶„ì„ê³¼ì •???°ë¼ ?ë?ë¹„êµ ?‰ë ¬??êµ¬ì„±?˜ì—¬ êµ????ê°€ì¤‘ì¹˜?€ ì¢…í•© ê°€ì¤‘ì¹˜(Global Weight)ë¥??°ì¶œ?˜ì??¼ë©°, ?¼ê???ë¹„ìœ¨(CR)??0.1 ë¯¸ë§Œ???˜ë„ë¡??œìŠ¤?œì˜ ë³´ì • ê¸°ëŠ¥??ê±°ì³ ê²°ê³¼???€?¹ì„±???•ë³´?˜ì???"
            """,
            """
            > **[Example of Paper Citation]**
            > 
            > "The survey data collected in this study was analyzed using 'AHP Master', a web-based dedicated AHP analysis solution. Pairwise comparison matrices were constructed in accordance with Saaty's (1980) Analytic Hierarchy Process to calculate local and global weights, and the validity of the results was secured through the system's consistency ratio (CR) adjustment function to ensure CR was below 0.1."
            """))

        if st.session_state.get('lang', 'ko') == 'ko':
            pdf_path = "AHP_Master_Accuracy_Paper.pdf"
            if os.path.exists(pdf_path):
                with open(pdf_path, "rb") as f:
                    base64_pdf = base64.b64encode(f.read()).decode('utf-8')
                pdf_html = f'<a href="data:application/pdf;base64,{base64_pdf}" download="AHP_Master_Accuracy_Paper.pdf" style="text-decoration: underline; font-weight: bold; font-size: 14px; color: #1B2A4A;">?“„ AHP ?•í™•??ê²€ì¦??¼ë¬¸ (PDF) ?¤ìš´ë¡œë“œ</a>'
                st.markdown("<br/>", unsafe_allow_html=True)
                st.markdown(pdf_html, unsafe_allow_html=True)

with col_main:
                
    
    if st.session_state.get('admin_mode', False) and st.session_state.user_role == 'admin':
        # ?¸ì…˜ ?¤í…Œ?´íŠ¸ ê¸°ë°˜ ?±ê³µ ë©”ì‹œì§€ ?”ì¡´ ì¶œë ¥
        if "sync_success_msg" in st.session_state:
            st.success(st.session_state["sync_success_msg"])
            del st.session_state["sync_success_msg"]
    
        st.subheader(_("?‘¥ ê°€?…ì ?„í™© ë°?ê´€ë¦?, "?‘¥ Registered Users & Admin Control"))
        
        col_sync1, col_sync2 = st.columns([2, 8])
        with col_sync1:
            if st.button("?”„ êµ¬ê? ?œíŠ¸?€ ?™ê¸°??):
                with st.spinner("êµ¬ê? ?œíŠ¸ ?°ì´??ë¶ˆëŸ¬?¤ëŠ” ì¤?.."):
                    # ìºì‹œ ?˜ë™ ë¹„ìš°ê¸?
                    get_cached_visit_logs.clear()
                    added_count = sync_db_from_sheets()
                if added_count >= 0:
                    st.session_state["sync_success_msg"] = f"?‰ ?™ê¸°???„ë£Œ! (ë³´ì • ë°?ë³µêµ¬???°ì´?? {added_count}ê±?"
                    st.rerun()
                else:
                    st.error("?™ê¸°??ì¤??¤ë¥˜ê°€ ë°œìƒ?ˆìŠµ?ˆë‹¤. ?”ë©´?ì˜ ?ëŸ¬ ë©”ì‹œì§€ë¥??•ì¸??ì£¼ì„¸??")
        
        try:
            # [ìµœì ?? êµ¬ê? ?œíŠ¸ API ë¶„ë‹¹ ?¸ì¶œ ?œí•œ(429)???¼í•˜ê¸??„í•´ 5ë¶?ìºì‹œ ì²˜ë¦¬???¨ìˆ˜ë¥??¬ìš©?©ë‹ˆ??
            visit_data_gs = get_cached_visit_logs(st.secrets["SPREADSHEET_ID"])
            if not visit_data_gs:
                try:
                    conn = sqlite3.connect('users.db')
                    df_local = pd.read_sql_query("SELECT ip_address as IP, visit_date as Date FROM visit_logs", conn)
                    conn.close()
                    if not df_local.empty:
                        # ì§€???œê°???±ì— ?„ìš”??ì»¬ëŸ¼ ë¹ˆê°’ ë³´ì •
                        df_local['Country'] = ""
                        df_local['Region'] = ""
                        df_local['City'] = ""
                        df_local['Latitude'] = ""
                        df_local['Longitude'] = ""
                        visit_data_gs = df_local.to_dict(orient='records')
                except Exception:
                    pass
            daily_df_logs = pd.DataFrame(visit_data_gs)
            if not daily_df_logs.empty:
                daily_df_logs['Date_Only'] = daily_df_logs['Date'].astype(str).str[:10]
                daily_df_counts = daily_df_logs.groupby('Date_Only').size().reset_index(name='count')
                # total_visits remains as calculated from local db above
    
                st.write("#### ?—ºï¸??‘ì†???¤ì‹œê°??„ì¹˜ ë¶„í¬")
                if 'Latitude' in daily_df_logs.columns and 'Longitude' in daily_df_logs.columns:
                    map_data = daily_df_logs[daily_df_logs['Latitude'].astype(str).str.strip() != ""].copy()
                    if not map_data.empty:
                        map_data['lat'] = pd.to_numeric(map_data['Latitude'], errors='coerce')
                        map_data['lon'] = pd.to_numeric(map_data['Longitude'], errors='coerce')
                        map_data = map_data.dropna(subset=['lat', 'lon'])
                        if not map_data.empty:
                            map_display = map_data.groupby(['lat', 'lon']).size().reset_index(name='visit_count')
                            map_display['size'] = map_display['visit_count'] * 20
                            st.map(map_display, latitude='lat', longitude='lon', size='size')
                        else:
                            st.info("? íš¨??ì¢Œí‘œ ?°ì´?°ê? ?†ìŠµ?ˆë‹¤.")
                    else:
                        st.info("ì§€?„ì— ?œì‹œ???„ì¹˜ ?•ë³´ ?°ì´?°ê? ?„ì§ ?˜ì§‘?˜ì? ?Šì•˜?µë‹ˆ??")
                else:
                    st.info("?„ì¹˜ ?•ë³´ ì»¬ëŸ¼??ì¡´ì¬?˜ì? ?ŠìŠµ?ˆë‹¤.")
            else:
                total_visits = 0
                daily_df_counts = pd.DataFrame()
    
            st.write(f"**ì´??„ì  ë°©ë¬¸????** {total_visits:,}ëª?)
            st.write("#### ?“… ?¼ë³„ ë°©ë¬¸???„í™© (? ì§œë³??©ì‚°)")
            if not daily_df_counts.empty:
                fig_visit = px.bar(daily_df_counts, x='Date_Only', y='count', text='count',
                                    labels={'Date_Only': '? ì§œ', 'count': 'ë°©ë¬¸????})
                fig_visit.update_traces(textposition='outside')
                fig_visit.update_layout(xaxis_title="? ì§œ", yaxis_title="ë°©ë¬¸????, showlegend=False, xaxis={'type': 'category'})
                st.plotly_chart(fig_visit, use_container_width=True)
            else:
                st.info("ë°©ë¬¸ ê¸°ë¡???†ìŠµ?ˆë‹¤.")
        except Exception as e:
            st.error(f"?µê³„ ?¤ë¥˜: {e}")
        st.divider()
        
        # ë°°í¬ ?µê³„ ì§‘ê³„ ë°??œê°??
        st.write("---")
        st.write(_("### ?“Š ?¤ë¬¸ì§€ ë°°í¬ ?µê³„", "### ?“Š Survey Distribution Statistics"))
        users_df = get_all_users()
        
        # ì»¬ëŸ¼ ì¡´ì¬ ?•ì¸ ë°?ê²°ì¸¡ì¹?ë³´ì •
        if 'survey_count' not in users_df.columns:
            users_df['survey_count'] = 0
        if 'last_survey_link' not in users_df.columns:
            users_df['last_survey_link'] = ""
            
        users_df['survey_count'] = pd.to_numeric(users_df['survey_count'].fillna(0)).astype(int)
        
        # 1. ?”ì•½ ?µê³„
        total_dist_surveys = users_df['survey_count'].sum()
        active_users_count = (users_df['survey_count'] > 0).sum()
        total_registered_users = len(users_df)
        
        col_stat1, col_stat2, col_stat3 = st.columns(3)
        with col_stat1:
            st.metric(_("ì´??¤ë¬¸ ë°°í¬ ê±´ìˆ˜", "Total Distributed Surveys"), f"{total_dist_surveys}" + _("ê±?, ""))
        with col_stat2:
            st.metric(_("?¤ë¬¸ ë°°í¬ ê²½í—˜ ?Œì› ??, "Members with Distribution Experience"), f"{active_users_count}" + _("ëª?, ""))
        with col_stat3:
            st.metric(_("ì´?ê°€???Œì› ??, "Total Registered Members"), f"{total_registered_users}" + _("ëª?, ""))
            
        # 2. ?¬ìš©?ë³„ ë°°í¬ ?Ÿìˆ˜ ì°¨íŠ¸
        active_users_df = users_df[users_df['survey_count'] > 0].copy()
        if not active_users_df.empty:
            active_users_df = active_users_df.sort_values(by='survey_count', ascending=False)
            fig_dist = px.bar(active_users_df, x='id', y='survey_count', text='survey_count',
                              labels={'id': '?Œì› ID', 'survey_count': 'ë°°í¬ ê±´ìˆ˜'},
                              title="?Œì›ë³??¤ë¬¸ì§€ ë°°í¬ ?„í™© (1ê±??´ìƒ ë°°í¬ ?Œì›)")
            fig_dist.update_traces(textposition='outside')
            fig_dist.update_layout(xaxis_title="?Œì› ID", yaxis_title="ë°°í¬ ê±´ìˆ˜")
            st.plotly_chart(fig_dist, use_container_width=True)
        else:
            st.info(_("?„ì§ ?¤ë¬¸??ë°°í¬???¬ìš©?ê? ?†ìŠµ?ˆë‹¤.", "No users have distributed a survey yet."))
            
        st.write("---")
        st.write(_("### ?‘¥ ê°€?…ì ?„í™© ë°?ìµœì¢… ë°°í¬ ë§í¬", "### ?‘¥ Subscriber Status and Latest Distribution Links"))
        
        # ì»¬ëŸ¼ ?œì„œ ë°?êµ¬ì„± ?¬ì¡°?•í•˜???°ì´?°í”„?ˆì„?¼ë¡œ ì¶œë ¥
        display_df = users_df[['id', 'role', 'signup_date', 'pw', 'survey_count', 'last_survey_link', 'expiry_date', 'agree_info']].copy()
        st.dataframe(
            display_df,
            column_config={
                "id": "?Œì› ID",
                "role": "ê¶Œí•œ",
                "signup_date": "ê°€?…ì¼",
                "pw": "ë¹„ë?ë²ˆí˜¸",
                "survey_count": "ë°°í¬ ?Ÿìˆ˜",
                "last_survey_link": st.column_config.LinkColumn("ìµœì¢… ë°°í¬ ?¤ë¬¸ì§€ ë§í¬", display_text="?¤ë¬¸ì§€ ë°”ë¡œê°€ê¸?),
                "expiry_date": "ë§Œë£Œ??,
                "agree_info": "?™ì˜?¬ë?"
            },
            hide_index=True,
            use_container_width=True
        )
    
        with st.expander("?Œì› ?•ë³´ ?˜ì • (ë¹„ë?ë²ˆí˜¸ ì´ˆê¸°???¬í•¨)"):
            edit_id = st.selectbox("?˜ì •???Œì› ID", users_df['id'].unique())
            selected_user = users_df[users_df['id'] == edit_id].iloc[0]
            new_role_val = st.selectbox("ê¶Œí•œ ë³€ê²?, ['temp', 'official', 'admin'], 
                                    index=['temp', 'official', 'admin'].index(selected_user['role']))
            
            if new_role_val == 'official' and selected_user['role'] != 'official':
                suggested_date = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).date() + relativedelta(months=3)
                new_expiry_val = st.text_input("ë§Œë£Œ???¤ì • (YYYY-MM-DD) - 3ê°œì›” ê¸°í•œ ?ë™ ?œì•ˆ??, value=str(suggested_date))
            else:
                new_expiry_val = st.text_input("ë§Œë£Œ??ë³€ê²?(YYYY-MM-DD)", value=selected_user['expiry_date'])
                
            new_pw_edit = st.text_input("??ë¹„ë?ë²ˆí˜¸ (?…ë ¥ ??ë³€ê²½ë¨)", type="password", placeholder="ë³€ê²½í•˜ì§€ ?Šìœ¼?¤ë©´ ë¹„ì›Œ?ì„¸??)
            
            col_admin_act1, col_admin_act2 = st.columns(2)
            with col_admin_act1:
                if st.button("?•ë³´ ?˜ì • ?ìš©", use_container_width=True):
                    update_user_full_info(edit_id, new_pw_edit, new_role_val, new_expiry_val)
                    if new_role_val == 'official' and selected_user['role'] != 'official':
                        send_approval_email(edit_id)
                    st.success(f"{edit_id} ?Œì›???•ë³´ê°€ ?˜ì •?˜ì—ˆ?µë‹ˆ??")
                    st.rerun()
            with col_admin_act2:
                if st.button("?”‘ ??ê³„ì •?¼ë¡œ ë¡œê·¸??, use_container_width=True, type="secondary", help="ë¹„ë?ë²ˆí˜¸ ?†ì´ ???¬ìš©?ì˜ ê³„ì •?¼ë¡œ ?¸ì…˜??ì¦‰ì‹œ ?„í™˜?©ë‹ˆ??"):
                    st.session_state.user_id = edit_id
                    st.session_state.user_role = selected_user['role']
                    st.session_state.expiry_date = selected_user['expiry_date']
                    st.session_state.admin_mode = False  # ?¼ë°˜ ?¬ìš©???œì ?¼ë¡œ ?„í™˜
                    st.toast(f"?”‘ {edit_id} ê³„ì •?¼ë¡œ ë¡œê·¸?¸í–ˆ?µë‹ˆ??")
                    st.rerun()
        
        with st.expander("?Œì› ?? œ"):
            del_id = st.selectbox("?? œ???Œì› ID ? íƒ", users_df['id'].unique(), key='del_user_select')
            if st.button("? íƒ???Œì› ?? œ"):
                if del_id == st.session_state.user_id:
                    st.error("ë³¸ì¸?€ ?? œ?????†ìŠµ?ˆë‹¤.")
                else:
                    delete_user(del_id)
                    st.success("?? œ ?„ë£Œ")
                    st.rerun()
        st.divider()
    
    # -------------------------------------------------------------------------
    # [?˜ì •] ê´€ë¦¬ì???ë‹¨ ???°ë™ (Tab 1: ë¶„ì„, Tab 2: ?¤ë¬¸ì§€ ?œì‘)
    # ?¼ë°˜ ?¬ìš©?ì—ê²ŒëŠ” Tab 1 ?”ë©´(ë¶„ì„)ë§?ì§ì ‘ ?¨ì¼ ?¸ì¶œ?œí‚µ?ˆë‹¤.
    # -------------------------------------------------------------------------
    if st.session_state.get('admin_mode', False) and st.session_state.get('user_role') == 'admin':
        st.stop()
        
    main_tab1, main_tab2, main_tab3 = st.tabs([
        _("AHP ë¶„ì„ ?„êµ¬", "AHP Analysis Tool"), 
        _("?¨ë¼??AHP ?¤ë¬¸ì§€ ?‘ì„± ë°?ë°°í¬(ë¬´ë£Œ)", "Create & Deploy Online AHP Survey (Free)"), 
        _("?¤ì‹œê°??‘ë‹µ ?„í™©", "Live Response Status")
    ])
        
    with main_tab1:
        # ë¹ ë¥¸ ?œì‘ ?¹ì…˜??AHP ë¶„ì„?„êµ¬ ???´ë? ìµœìƒ?¨ì— ë°°ì¹˜
        with st.container(border=True):
            st.markdown(_("#### ??ë¹ ë¥¸ ?œì‘ (?„ì‹œ?¬ìƒ ?¬ì—… ëª¨ë¸)", "#### ??Quick Start (Urban Regeneration Project Model)"))
            st.info(_("Saaty(1980)??Analytic Hierarchy Process (AHP) ë¶„ì„ ë°??¼ê????ë™ ë³´ì • ?„êµ¬?…ë‹ˆ??  \n?¼ë°˜ ë°?:blue[**?¼ì? AHP**] ë¶„ì„??ëª¨ë‘ ì§€?í•˜ë©? ?‘ì? ?…ë¡œ?œë§Œ?¼ë¡œ ê°œì¸ë³?ê°€ì¤‘ì¹˜ ?°ì¶œ, ?¼ê???CR) ?ë™ ë³´ì •, ê·¸ë£¹ ì§‘ê³„ ê²°ê³¼ë¥??œê³µ?©ë‹ˆ??",
                      "Saaty's (1980) Analytic Hierarchy Process (AHP) analysis and automatic consistency correction tool.  \nIt supports both traditional and :blue[**Fuzzy AHP**] analysis, providing individual weights, automatic consistency ratio (CR) correction, and group aggregation results upon Excel upload."))
            
            sample_excel = create_sample_excel()
            
            def load_example_file(path):
                try:
                    import os
                    base_dir = os.path.dirname(__file__)
                    full_path = os.path.join(base_dir, path)
                    with open(full_path, "rb") as f:
                        return f.read(), None
                except Exception as e:
                    return b"", str(e)
    
            is_en = st.session_state.get('lang', 'ko') == 'en'
            tahp_path = "sample_data/E_TAHP_Result.xlsx" if is_en else "sample_data/K_TAHP_Result.xlsx"
            fahp_path = "sample_data/E_FAHP_Result.xlsx" if is_en else "sample_data/K_FAHP_Result.xlsx"
            
            tahp_data, tahp_err = load_example_file(tahp_path)
            fahp_data, fahp_err = load_example_file(fahp_path)
            
            if tahp_err: st.error(f"TAHP Load Error: {tahp_err} | Path: {tahp_path}")
            if fahp_err: st.error(f"FAHP Load Error: {fahp_err} | Path: {fahp_path}")
    
            # 3ê³„ì¸µ ?˜í”Œ ?°ì´?? ê¶Œí•œ???°ë¼ ë¶„ê¸°
            # - ?•ì‹/ê´€ë¦¬ì: Mock_3Tier_Full.xlsx (100?? ?¤ì œ ë¶„ì„ ê°€??
            # - ë¬´ë£Œ/ë¹„ë¡œê·¸ì¸: create_sample_excel_v3() (5?? 5???œí•œ ?µê³¼)
            _role_now = st.session_state.get('user_role', None)
            _is_full_user = (_role_now in ('admin', 'official'))
            if _is_full_user:
                try:
                    with open("Mock_3Tier_Full.xlsx", "rb") as f:
                        sample_excel_v3 = f.read()
                    _v3_label = _("?“‚ 3ê³„ì¸µ ?˜í”Œ ?°ì´??, "?“‚ 3-Tier Sample Data")
                    _v3_filename = "Mock_3Tier_Full.xlsx"
                except Exception:
                    sample_excel_v3 = create_sample_excel_v3()
                    _v3_label = _("?“‚ 3ê³„ì¸µ ?˜í”Œ ?°ì´??, "?“‚ 3-Tier Sample Data")
                    _v3_filename = _("AHP_3Tier_Sample.xlsx", "AHP_3Tier_Sample.xlsx")
            else:
                sample_excel_v3 = create_sample_excel_v3()   # 5????ë¬´ë£Œ 5???œí•œ ?µê³¼
                _v3_label = _("?“‚ 3ê³„ì¸µ ?˜í”Œ ?°ì´??, "?“‚ 3-Tier Sample Data")
                _v3_filename = _("AHP_3Tier_Sample.xlsx", "AHP_3Tier_Sample.xlsx")
            
            # ëª¨ë“  ?¬ìš©?ì—ê²?2ê³„ì¸µÂ·3ê³„ì¸µ ?˜í”Œ ?°ì´??+ ê²°ê³¼ ?ˆì‹œ ë²„íŠ¼ 4ê°??œì‹œ
            col_btn1, col_btn2, col_btn3, col_btn4 = st.columns(4)
            with col_btn1:
                st.download_button(
                    label=_("?“‚ 2ê³„ì¸µ ?˜í”Œ ?°ì´??, "?“‚ 2-Tier Sample Data"),
                    data=sample_excel,
                    file_name=_("AHP_UrbanRegeneration_2Tier_Sample.xlsx", "AHP_UrbanRegeneration_2Tier_Sample.xlsx"),
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                    type="primary"
                )
            with col_btn2:
                st.download_button(
                    label=_v3_label,
                    data=sample_excel_v3,
                    file_name=_v3_filename,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                    type="primary"
                )
            with col_btn3:
                st.download_button(
                    label=_("?“„ ?¼ë°˜ AHP ë¶„ì„ ê²°ê³¼(?ˆì‹œ)", "?“„ Traditional AHP Report (Example)"),
                    data=tahp_data if tahp_data else b"",
                    file_name=_("E_TAHP_Result.xlsx", "E_TAHP_Result.xlsx") if is_en else _("K_TAHP_Result.xlsx", "K_TAHP_Result.xlsx"),
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                    disabled=(not tahp_data)
                )
            with col_btn4:
                st.download_button(
                    label=_("?“„ ?¼ì? AHP ë¶„ì„ ê²°ê³¼(?ˆì‹œ)", "?“„ Fuzzy AHP Report (Example)"),
                    data=fahp_data if fahp_data else b"",
                    file_name=_("E_FAHP_Result.xlsx", "E_FAHP_Result.xlsx") if is_en else _("K_FAHP_Result.xlsx", "K_FAHP_Result.xlsx"),
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                    disabled=(not fahp_data)
                )
        
        st.subheader(_("1. AHP ë¶„ì„ ëª¨ë¸ ?¤ì • ë°??…ë ¥ ?œí”Œë¦??¤ìš´ë¡œë“œ", "1. Setup AHP Decision Model & Download Template"))
        
        saved_model = None
        if st.session_state.user_id is None:
            st.info(_("?”’ **ë¡œê·¸????* '?˜ë§Œ??ë¶„ì„ ëª¨ë¸'??ë§Œë“¤ ???ˆìŠµ?ˆë‹¤. (ë¹„ë¡œê·¸ì¸ ?íƒœ?ì„œ???˜í”Œ ?°ì´?°ë¡œ ìµœì¢… ë¶„ì„ ê²°ê³¼ë¥?ë¯¸ë¦¬ë³????ˆìŠµ?ˆë‹¤)",
                      "?”’ **Log in** to create your own custom AHP models. (Even without logging in, you can preview results using sample data.)"))
        else:
            saved_model = load_user_model(st.session_state.user_id)
            is_en = st.session_state.get('lang', 'ko') == 'en'
        
        en_default_main = "Governance, Planning, Feasibility, Effectiveness"
        en_default_subs = {
            "Governance": "AdminSupport, Community, PM",
            "Planning": "IssueFit, AlternativeFit, GoalClarity",
            "Feasibility": "LandAcquisition, ProjectDetail, CostFit",
            "Effectiveness": "Economic, Social, Performance"
        }
        ko_default_main = "ê±°ë²„?ŒìŠ¤, ê³„íš?€?¹ì„±, ?¤í˜„ê°€?¥ì„±, ?¬ì—…?¨ê³¼"
        ko_default_subs = {
            "ê±°ë²„?ŒìŠ¤": "?‰ì •ì§€?? ì§€??³µ?™ì²´, ì´ê´„?¬ì—…ê´€ë¦¬ì",
            "ê³„íš?€?¹ì„±": "?„ì•ˆ?ì •?? ?€?ˆì ?•ì„±, ëª©í‘œêµ¬ì²´??,
            "?¤í˜„ê°€?¥ì„±": "ë¶€ì§€?•ë³´, ?¬ì—…êµ¬ì²´?? ?¬ì—…ë¹„ì ?•ì„±",
            "?¬ì—…?¨ê³¼": "ê²½ì œ?íš¨ê³? ?¬íšŒ?íš¨ê³? ?±ê³¼ê´€ë¦?
        }

        # [? ê·œ] 3ê³„ì¸µ(V3) ?˜í”Œ ?°ì´??(?¤ë§ˆ?¸í° êµ¬ë§¤ ê²°ì •)
        en_default_main_v3 = "Functionality, Design, Economy"
        en_default_subs_v3 = {
            "Functionality": "Hardware, Software",
            "Design": "Appearance, Usability",
            "Economy": "Device Price, Maintenance"
        }
        en_default_sub_subs_v3 = {
            "Hardware": "Camera, Battery, Processor",
            "Software": "OS, Default Apps",
            "Appearance": "Color, Material",
            "Usability": "", 
            "Device Price": "Lump Sum, Installment",
            "Maintenance": "Plan, Repair"
        }

        ko_default_main_v3 = "ê¸°ëŠ¥?? ?”ì?? ê²½ì œ??
        ko_default_subs_v3 = {
            "ê¸°ëŠ¥??: "?˜ë“œ?¨ì–´, ?Œí”„?¸ì›¨??,
            "?”ì??: "?¸ê?, ?¸ì˜??,
            "ê²½ì œ??: "?¨ë§ê¸°ê?ê²? ? ì?ë¹„ìš©"
        }
        ko_default_sub_subs_v3 = {
            "?˜ë“œ?¨ì–´": "ì¹´ë©”?? ë°°í„°ë¦? ?„ë¡œ?¸ì„œ",
            "?Œí”„?¸ì›¨??: "?´ì˜ì²´ì œ, ê¸°ë³¸??,
            "?¸ê?": "?‰ìƒ, ?¬ì§ˆ",
            "?¸ì˜??: "", 
            "?¨ë§ê¸°ê?ê²?: "?¼ì‹œë¶? ? ë?",
            "? ì?ë¹„ìš©": "?µì‹ ?”ê¸ˆ, ASë¹„ìš©"
        }
    
        # default assignments are moved inside expander to react to tier_level
    
        with st.expander(_("?“Œ ?˜ì˜ ë¶„ì„ ëª¨ë¸ ë§Œë“¤ê¸?, "?“Œ Create Custom AHP Model"), expanded=True):
            st.info(_("?€??ª©ê³??¸ë???ª©???…ë ¥?˜ì—¬ ?˜ë§Œ???…ë ¥ ?‘ì? ?œí”Œë¦¿ì„ ?ì„±?˜ì„¸?? ë³??œí”Œë¦¿ì? ?¼ë°˜ AHP ë°??¼ì? AHP(Fuzzy AHP) ë¶„ì„??ê³µí†µ?¼ë¡œ ?¬ìš©?©ë‹ˆ??\n\n?„ì¬ ?…ë ¥?˜ì–´ ?ˆëŠ” ?´ìš©?€ ?˜í”Œ ëª¨ë¸?…ë‹ˆ?? ?´ìš©?ë‹˜??AHP ëª¨ë¸ë¡??˜ì •?????ˆìŠµ?ˆë‹¤.",
                      "Enter main criteria and sub-criteria to generate your custom Excel template. This template is used for both traditional AHP and Fuzzy AHP analysis.\n\nThe content below is a sample model. You can modify it with your own AHP model."))
            
            # ê³„ì¸µ êµ¬ì¡° ?¤ì • (2ê³„ì¸µ ê¸°ì?ê³??™ì¼?˜ê²Œ ?„ì²´ ê³µê°œ)
            tier_level = 2
            st.markdown("##### ?™ï¸ ê³„ì¸µ êµ¬ì¡° ?¤ì •")
            tier_choice = st.radio(
                _("ê³„ì¸µ ?ˆë²¨??? íƒ?˜ì„¸??", "Select Hierarchy Level."),
                [_("2ê³„ì¸µ (?€ë¶„ë¥˜ - ì¤‘ë¶„ë¥?", "2-Tier (Main - Sub)"),
                 _("3ê³„ì¸µ (?€ë¶„ë¥˜ - ì¤‘ë¶„ë¥?- ?Œë¶„ë¥?", "3-Tier (Main - Sub - Sub-sub)")],
                index=0,
                horizontal=True,
                key="tab1_tier_choice"
            )
            if _("3ê³„ì¸µ", "3-Tier") in tier_choice:
                tier_level = 3
            st.markdown("---")
                
            # [? ê·œ] tier_level???°ë¼ ?˜í”Œ ?°ì´???¤ìœ„ì¹?
            if is_en:
                default_main = en_default_main_v3 if tier_level == 3 else en_default_main
                default_subs = en_default_subs_v3 if tier_level == 3 else en_default_subs
                default_sub_subs = en_default_sub_subs_v3 if tier_level == 3 else {}
            else:
                default_main = ko_default_main_v3 if tier_level == 3 else ko_default_main
                default_subs = ko_default_subs_v3 if tier_level == 3 else ko_default_subs
                default_sub_subs = ko_default_sub_subs_v3 if tier_level == 3 else {}
                
            if saved_model:
                saved_main = saved_model.get('main', '')
                if is_en and (saved_main == ko_default_main or saved_main == ko_default_main_v3 or not saved_main):
                    pass
                elif not is_en and (saved_main == en_default_main or saved_main == en_default_main_v3 or not saved_main):
                    pass
                else:
                    default_main = saved_main
                    default_subs = saved_model.get('subs', default_subs)
                    
            main_criteria_input = st.text_input(_("?€??ª© (Main Criteria, ì½¤ë§ˆ êµ¬ë¶„)", "Main Criteria (comma-separated)"), value=default_main)
            main_criteria_list = [x.strip() for x in main_criteria_input.split(',') if x.strip()]
            
            model_structure = {}
            sub_sub_structure = {}
            if main_criteria_list:
                for mc in main_criteria_list:
                    d_val = default_subs.get(mc, "")
                    if isinstance(d_val, list): d_val = ", ".join(d_val)
                    sub_input = st.text_input(_(f"'{mc}'???¸ë???ª©", f"Sub-criteria for '{mc}'"), value=d_val, key=f"tab1_sub_{mc}")
                    sub_list = [x.strip() for x in sub_input.split(',') if x.strip()]
                    model_structure[mc] = sub_list
                    
                    if tier_level == 3 and sub_list:
                        with st.expander(_(f"??'{mc}'???Œë¶„ë¥?(Sub-sub-criteria) ?…ë ¥", f"??Enter Sub-sub-criteria for '{mc}'"), expanded=True):
                            st.info(_("?’¡ **?¼í•© ê³„ì¸µ ?ˆë‚´**: ?Œë¶„ë¥?3ê³„ì¸µ)ê°€ ?†ëŠ” ??ª©?€ **ë¹„ì›Œ?ì‹œë©??ë™?¼ë¡œ 2ê³„ì¸µ ê°€ì¤‘ì¹˜ë¡?ê³„ì‚°**?©ë‹ˆ??", "?’¡ **Mixed-Tier Guide**: If a sub-criterion has no sub-sub-criteria, **leave it blank to automatically calculate as a 2-tier weight**."))
                            for sub_c in sub_list:
                                sub_sub_input = st.text_input(
                                    f"??'{sub_c}'???Œë¶„ë¥?(ì½¤ë§ˆ êµ¬ë¶„)", 
                                    value=default_sub_subs.get(sub_c, ""),
                                    placeholder="?? ??ª©1, ??ª©2 (???˜ìœ„ ?”ì¸???†ë‹¤ë©?ë¹„ì›Œ?ì„¸??",
                                    help="?…ë ¥ì¹¸ì„ ë¹„ì›Œ?ë©´ ????ª©?€ ?ë™?¼ë¡œ 2ê³„ì¸µ êµ¬ì¡°ë¡?ê°„ì£¼?˜ì–´ ë¶„ì„?©ë‹ˆ??",
                                    key=f"tab1_sub_sub_{sub_c}"
                                )
                                parsed_sub_subs = [x.strip().replace("_", " ") for x in sub_sub_input.split(",") if x.strip()]
                                if parsed_sub_subs:
                                    sub_sub_structure[sub_c] = parsed_sub_subs
            
            col1, col2 = st.columns(2)
            with col1:
                generate_clicked = st.button(_("1ï¸âƒ£ ?¤ì •??ëª¨ë¸ë¡??…ë ¥ ?‘ì? ?œí”Œë¦??ì„±", "1ï¸âƒ£ Generate Excel Template with this Model"), use_container_width=True)
            
            if generate_clicked:
                if not main_criteria_list:
                    st.error(_("?€??ª© ?…ë ¥ ?„ìš”", "Main criteria input is required"))
                else:
                    current_model = {'main': main_criteria_input, 'subs': model_structure, 'sub_subs': sub_sub_structure, 'Tier_Level': tier_level}
                    save_user_model(st.session_state.user_id, current_model)
                    st.toast(_("ëª¨ë¸ ?€???„ë£Œ", "Model successfully saved"))
                    
                    output_template = io.BytesIO()
                    with pd.ExcelWriter(output_template, engine='xlsxwriter') as writer:
                        main_pairs = list(itertools.combinations(main_criteria_list, 2))
                        main_cols_tpl = ["ID", "Type"] + [f"{a}_{b}" for a, b in main_pairs]
                        df_template_main = pd.DataFrame(columns=main_cols_tpl)
                        df_template_main.loc[0] = [1, ""] + [0]*len(main_pairs)
                        df_template_main.to_excel(writer, sheet_name="Main_Criteria", index=False)
                        
                        for mc, subs in model_structure.items():
                            if len(subs) < 2:
                                df_sub = pd.DataFrame(columns=["ID", "Type"])
                            else:
                                sub_pairs = list(itertools.combinations(subs, 2))
                                sub_cols = ["ID", "Type"] + [f"{a}_{b}" for a, b in sub_pairs]
                                df_sub = pd.DataFrame(columns=sub_cols)
                                df_sub.loc[0] = [1, ""] + [0]*len(sub_pairs)
                            safe_sheet_name = mc[:31]
                            df_sub.to_excel(writer, sheet_name=safe_sheet_name, index=False)
                            
                        # 3ê³„ì¸µ ?œíŠ¸ ?ì„±
                        if tier_level == 3:
                            for mc, subs in model_structure.items():
                                for sub_c in subs:
                                    ss_list = sub_sub_structure.get(sub_c, [])
                                    if len(ss_list) < 2:
                                        df_ss = pd.DataFrame(columns=["ID", "Type"])
                                    else:
                                        ss_pairs = list(itertools.combinations(ss_list, 2))
                                        ss_cols = ["ID", "Type"] + [f"{a}_{b}" for a, b in ss_pairs]
                                        df_ss = pd.DataFrame(columns=ss_cols)
                                        df_ss.loc[0] = [1, ""] + [0]*len(ss_pairs)
                                    safe_ss_name = sub_c[:31]
                                    df_ss.to_excel(writer, sheet_name=safe_ss_name, index=False)
                                    
                    output_template.seek(0)
                    
                    with col2:
                        st.download_button(
                            label=_("2ï¸âƒ£ ?“¥ ?‘ì? ?œí”Œë¦??¤ìš´ë¡œë“œ", "2ï¸âƒ£ ?“¥ Download Excel Template"),
                            data=output_template,
                            file_name="AHP_Master_Template.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True,
                            type="primary"
                        )
                    
                    st.info(_("?’¡ **?ˆë‚´:** 1ë²?ë²„íŠ¼???ŒëŸ¬ ëª¨ë¸???ì„± ë°??€?¥í–ˆ?µë‹ˆ?? ?°ì¸¡??2ë²?ë²„íŠ¼???´ë¦­?˜ì—¬ ì»´í“¨?°ì— ?‘ì? ?œí”Œë¦??Œì¼???€?¥í•˜?¸ìš”.", 
                              "?’¡ **Info:** The model has been generated and saved. Click the 2nd button on the right to download the Excel template file to your computer."))
    
                    st.markdown(_("""
                    ---
                    ### ?“ ?°ì´???…ë ¥ ê°€?´ë“œ
                    1. **?‘ì? ?Œì¼ ?´ê¸°**: ??ë²„íŠ¼???ŒëŸ¬ ?¤ìš´ë¡œë“œ???‘ì? ?Œì¼???¤í–‰?©ë‹ˆ??
                    2. **?ë?ë¹„êµ ?°ì´???…ë ¥**:
                        - **?¼ìª½** ??ª©????ì¤‘ìš”?˜ë©´: **?Œìˆ˜** ?…ë ¥ (?? -3)
                        - **?¤ë¥¸ìª?* ??ª©????ì¤‘ìš”?˜ë©´: **?‘ìˆ˜** ?…ë ¥ (?? 3)
                        - **?™ë“±**?˜ë©´: `1` ?…ë ¥
                    3. **?„ìˆ˜ ?•ë³´ ?…ë ¥**: A??ID), **B??Type)??ê·¸ë£¹ëª??…ë ¥ (?? ?„ë¬¸ê°€, ì£¼ë? ??**
                    """,
                    """
                    ---
                    ### ?“ Data Input Guide
                    1. **Open the Excel file**: Run the Excel template downloaded above.
                    2. **Enter pairwise comparisons**:
                        - If the **left** item is more important: enter a **negative** value (e.g., -3)
                        - If the **right** item is more important: enter a **positive** value (e.g., 3)
                        - If they are **equal**: enter `1`
                    3. **Required Information**: Column A (ID), **Column B (Type) for group names (e.g., Expert, Public, etc.)**
                    """))
                    img_file = _("ahp_input_guide.png", "ahp_input_guide_en.png")
                    caption_text = _("[ì°¸ê³ ] ?¤ë¬¸ ?‘ë‹µ???‘ì????…ë ¥?˜ëŠ” ë°©ë²•", "[Reference] How to enter survey responses into Excel")
                    if os.path.exists(img_file):
                        st.image(img_file, caption=caption_text)
    
        st.markdown("---")
    
        if st.session_state.user_role == 'official':
            with st.expander(_("?“‚ ?˜ì˜ ë¶„ì„ ë³´ê???(!ì¤‘ìš”) ë°˜ë“œ??ì»´í“¨?°ì— ë°±ì—…??ì£¼ì„¸??, "?“‚ My Analysis Storage (!Important: Please backup to your computer)")):
                my_analyses = get_user_analyses(st.session_state.user_id)
                if not my_analyses: st.info(_("?€?¥ëœ ë¶„ì„ ?†ìŒ", "No saved analyses found."))
                else:
                    for item in my_analyses:
                        a_id, filename, save_date = item
                        col_List1, col_List2, col_List3, col_List4 = st.columns([3, 2, 1, 1])
                        with col_List1: st.text(f"{filename}")
                        with col_List2: st.caption(f"{save_date}")
                        with col_List3:
                            file_info = get_analysis_file(analysis_id=a_id)
                            if file_info:
                                fname, fdata = file_info
                                st.download_button("â¬‡ï¸", fdata, fname, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key=f"dl_{a_id}", type="primary")
                        with col_List4:
                            if st.button("?—‘ï¸?, key=f"del_{a_id}"):
                                delete_analysis(a_id)
                                st.rerun()
    

    
        def write_custom_ahp_table(writer, sheet_name, df, title_text, start_row, formats, excluded_df=None):
            workbook = writer.book
            if sheet_name in writer.sheets: worksheet = writer.sheets[sheet_name]
            else:
                worksheet = workbook.add_worksheet(sheet_name)
                writer.sheets[sheet_name] = worksheet
        
            header_fmt = formats['header']
            merge_fmt = formats['merge']
            body_fmt = formats['body']
            num_fmt = formats['num']
            sum_row_fmt = formats['sum_row']
        
            # [? ê·œ ì¶”ê?] ?œì™¸ ?¬ë???ë°??œì™¸ ?‘ë‹µê°??°ì´??ì¶œë ¥
            if excluded_df is not None:
                worksheet.write(start_row, 0, _(f"??ë¶„ì„ ?œì™¸ ?¬ë??? {len(excluded_df)}ê±?, f"??Number of cases excluded: {len(excluded_df)}"), workbook.add_format({'bold': True, 'font_color': 'red'}))
                start_row += 1
                if not excluded_df.empty:
                    worksheet.write(start_row, 0, _("???œì™¸???‘ë‹µ ?°ì´??(ë³´ì • ?¤íŒ¨)", "??Excluded Response Data (Correction Failed)"), workbook.add_format({'bold': True}))
                    start_row += 1
                    excluded_df.to_excel(writer, sheet_name=sheet_name, startrow=start_row, index=False)
                    start_row += len(excluded_df) + 2
    
            worksheet.merge_range(start_row, 0, start_row, 6, title_text, workbook.add_format({'bold': True, 'font_size': 12}))
            start_row += 1
        
            headers = _(
                ["?€ë¶„ë¥˜", "ê°€ì¤‘ì¹˜(a)", "ì¤‘ë¶„ë¥?, "ê°€ì¤‘ì¹˜(b)", "ì¢…í•© ê°€ì¤‘ì¹˜(a x b)", "ì¢…í•© ?œìœ„", "ë¹„ê³ "],
                ["Main Criteria", "Weight(a)", "Sub-Criteria", "Weight(b)", "Global Weight(a x b)", "Global Rank", "Remarks"]
            )
            for col, h in enumerate(headers):
                worksheet.write(start_row, col, h, header_fmt)
            start_row += 1
        
            main_criteria = df['?€ë¶„ë¥˜'].unique()
            current_row = start_row
        
            for main_c in main_criteria:
                sub_df = df[df['?€ë¶„ë¥˜'] == main_c]
                n_subs = len(sub_df)
                main_w = sub_df.iloc[0]['?€ë¶„ë¥˜ ê°€ì¤‘ì¹˜']
                sub_cr = sub_df.iloc[0]['CR(ì¤‘ë¶„ë¥?']
                sub_ci = sub_df.iloc[0]['CI(ì¤‘ë¶„ë¥?'] if 'CI(ì¤‘ë¶„ë¥?' in sub_df.columns else 0.0
                sum_sub_w = sub_df['ì¤‘ë¶„ë¥?ê°€ì¤‘ì¹˜'].sum()
            
                merge_span = n_subs + 2 
                if merge_span > 1:
                    worksheet.merge_range(current_row, 0, current_row + merge_span - 1, 0, main_c, merge_fmt)
                    worksheet.merge_range(current_row, 1, current_row + merge_span - 1, 1, main_w, num_fmt)
                else:
                    worksheet.write(current_row, 0, main_c, merge_fmt)
                    worksheet.write(current_row, 1, main_w, num_fmt)
                
                for idx, row in sub_df.iterrows():
                    worksheet.write(current_row, 2, row['ì¤‘ë¶„ë¥?], body_fmt)
                    worksheet.write(current_row, 3, row['ì¤‘ë¶„ë¥?ê°€ì¤‘ì¹˜'], num_fmt)
                    worksheet.write(current_row, 4, row['Global Weight'], num_fmt)
                    worksheet.write(current_row, 5, row['Global Rank'], body_fmt)
                    worksheet.write(current_row, 6, "", body_fmt)
                    current_row += 1
            
                worksheet.write(current_row, 2, _("?©ê³„", "Total"), sum_row_fmt)
                worksheet.write(current_row, 3, sum_sub_w, formats['sum_val'])
                worksheet.write_blank(current_row, 4, "", sum_row_fmt)
                worksheet.write_blank(current_row, 5, "", sum_row_fmt)
                worksheet.write_blank(current_row, 6, "", sum_row_fmt)
                current_row += 1
            
                worksheet.write(current_row, 2, _("?¼ê???ë¹„ìœ¨(CR)", "Consistency Ratio (CR)"), sum_row_fmt)
                worksheet.write(current_row, 3, sub_cr, formats['num_sum'])
                worksheet.write(current_row, 4, _("?¼ê???ì§€??CI)", "Consistency Index (CI)"), sum_row_fmt)
                worksheet.write(current_row, 5, sub_ci, formats['num_sum'])
                worksheet.write_blank(current_row, 6, "", sum_row_fmt)
                current_row += 1
    
            worksheet.write(current_row, 0, _("?©ê³„", "Total"), sum_row_fmt)
            worksheet.write(current_row, 1, 1, formats['sum_val'])
            worksheet.write_blank(current_row, 2, "", sum_row_fmt)
            worksheet.write_blank(current_row, 3, "", sum_row_fmt)
            worksheet.write_blank(current_row, 4, "", sum_row_fmt)
            worksheet.write_blank(current_row, 5, "", sum_row_fmt)
            worksheet.write_blank(current_row, 6, "", sum_row_fmt)
        
            # [? ê·œ ì¶”ê?] ?€ë¶„ë¥˜???¼ê???ë¹„ìœ¨(CR) ë°??¼ê???ì§€??CI) ì¶œë ¥
            main_cr = df.iloc[0]['CR(?€ë¶„ë¥˜)'] if 'CR(?€ë¶„ë¥˜)' in df.columns else 0.0
            main_ci = df.iloc[0]['CI(?€ë¶„ë¥˜)'] if 'CI(?€ë¶„ë¥˜)' in df.columns else 0.0
        
            current_row += 1
            worksheet.write(current_row, 0, _("?¼ê???ë¹„ìœ¨(CR)", "Consistency Ratio (CR)"), sum_row_fmt)
            worksheet.write(current_row, 1, main_cr, formats['num_sum'])
            worksheet.write(current_row, 2, _("?¼ê???ì§€??CI)", "Consistency Index (CI)"), sum_row_fmt)
            worksheet.write(current_row, 3, main_ci, formats['num_sum'])
            worksheet.write_blank(current_row, 4, "", sum_row_fmt)
            worksheet.write_blank(current_row, 5, "", sum_row_fmt)
            worksheet.write_blank(current_row, 6, "", sum_row_fmt)
        
            worksheet.set_column('A:A', 15)
            worksheet.set_column('B:B', 12)
            worksheet.set_column('C:C', 25)
            worksheet.set_column('D:F', 12)
            return current_row + 2
    
        def add_borders_to_data(worksheet, start_row, start_col, df, border_fmt, has_header=True, has_index=False):
            rows = len(df) + (1 if has_header else 0)
            cols = len(df.columns) + (1 if has_index else 0)
            worksheet.conditional_format(start_row, start_col, start_row+rows-1, start_col+cols-1,
                                          {'type': 'formula', 'criteria': '=TRUE', 'format': border_fmt})
    
        st.subheader(_("2. ?°ì´???…ë¡œ??ë°?ë¶„ì„", "2. Data Upload & Analysis"))
        
        if st.session_state.get('user_role') == 'admin':
            st.info(_("?’¡ **?¼í•© ê³„ì¸µ(Mixed-Tier) ?‘ì? ë¶„ì„ ?ˆë‚´**: 3ê³„ì¸µ ?‘ì? ?œí”Œë¦¿ì„ ?…ë¡œ?œí•  ?? ?¹ì • ??ª©???€???Œë¶„ë¥??‰ê? ?œíŠ¸ê°€ ?†ê±°???‘ë‹µ??ë¹„ì›Œ???ˆë”?¼ë„ ?œìŠ¤?œì´ ?´ë‹¹ ??ª©???ë™?¼ë¡œ 2ê³„ì¸µ ê°€ì¤‘ì¹˜ë¡?ê°„ì£¼?˜ì—¬ ?ëŸ¬ ?†ì´ ë¶„ì„???˜í–‰?©ë‹ˆ??", "?’¡ **Mixed-Tier Excel Analysis Guide**: When uploading a 3-tier Excel template, if there are no sub-sub-criteria evaluation sheets for specific items or the responses are blank, the system automatically considers them as 2-tier weights and performs the analysis without errors."))

        # ?°ì´???ŒìŠ¤ ? íƒ ì¶”ê?
        data_source = st.radio(
            _("ë¶„ì„ ?°ì´???ŒìŠ¤ ? íƒ", "Select Analysis Data Source"),
            [_("?“‚ ?‘ì? ?Œì¼ ì§ì ‘ ?…ë¡œ??, "Upload Excel File"), _("?Œ ë°°í¬???¨ë¼???¤ë¬¸ ?°ì´???°ë™", "Link Online Survey Data")],
            horizontal=True
        )
    
        df_main = None
        sub_dfs = {}
        sheet_names = []
        filename_base = "AHP_Analysis"
    
        if data_source == _("?“‚ ?‘ì? ?Œì¼ ì§ì ‘ ?…ë¡œ??, "Upload Excel File"):
            uploaded_file = st.file_uploader(_("?‘ì„±???‘ì? ?Œì¼ ?…ë¡œ??(.xlsx)", "Upload completed Excel file (.xlsx)"), type=['xlsx', 'xls'])
            if uploaded_file:
                try:
                    excel_obj = pd.ExcelFile(uploaded_file)
                    sheet_names = excel_obj.sheet_names
                    df_main = pd.read_excel(uploaded_file, sheet_name=sheet_names[0])
                    
                    # 3ê³„ì¸µ ?ë³„ ë¡œì§ (df_main ì»¬ëŸ¼?ì„œ _ ?¬í•¨??ê²ƒìœ¼ë¡??€ë¶„ë¥˜ ?”ì¸ ?„ì¶œ)
                    main_criteria_infer = set()
                    for col in df_main.columns:
                        if '_' in col:
                            parts = col.split('_')
                            if len(parts) == 2:
                                main_criteria_infer.add(parts[0])
                                main_criteria_infer.add(parts[1])
                    
                    inferred_sub_sub_dfs = {}
                    for sn in sheet_names[1:]:
                        df_sheet = pd.read_excel(uploaded_file, sheet_name=sn)
                        # ?ˆì „???œíŠ¸ëª?safe_sheet_name)???„í•´ ?ë?ë¶„ì´ ?¼ì¹˜?˜ëŠ”ì§€ ?•ì¸
                        is_sub = any(sn == mc[:31] for mc in main_criteria_infer)
                        if is_sub:
                            sub_dfs[sn] = df_sheet
                        else:
                            inferred_sub_sub_dfs[sn] = df_sheet
                    
                    if len(inferred_sub_sub_dfs) > 0:
                        st.session_state["ahp_sub_sub_dfs"] = inferred_sub_sub_dfs
                        st.session_state["inferred_tier_level"] = 3
                    else:
                        st.session_state["inferred_tier_level"] = 2
                        
                    filename_base = uploaded_file.name.split('.')[0]
                except Exception as e:
                    st.error(f"?‘ì? ?Œì¼ ë¡œë“œ ?¤íŒ¨: {e}")
        else:
            # ë°°í¬???¨ë¼???¤ë¬¸ ?°ì´???°ë™
            if st.session_state.user_id is None:
                st.warning(_("?”’ ?¨ë¼???¤ë¬¸ ?°ì´???°ë™ ë¶„ì„?€ ?Œì› ?„ìš© ê¸°ëŠ¥?…ë‹ˆ?? ë¡œê·¸?¸í•´ ì£¼ì„¸??", "?”’ Online survey integration is available for members. Please log in."))
            else:
                import sqlite3
                try:
                    sync_short_codes_from_gs()
                except Exception:
                    pass
                conn = sqlite3.connect('users.db')
                cur = conn.cursor()
                cur.execute("SELECT survey_id, title, created_at FROM admin_surveys WHERE admin_id = ? ORDER BY created_at DESC", (st.session_state.user_id,))
                sqlite_surveys = cur.fetchall()
                conn.close()
                
                gs_surveys = []
                try:
                    from survey_manager import get_admin_surveys_from_gsheet
                    gs_surveys = get_admin_surveys_from_gsheet(st.session_state.user_id)
                except Exception:
                    pass
                
                merged_surveys = {}
                for s in gs_surveys + sqlite_surveys:
                    if s[0] not in merged_surveys:
                        merged_surveys[s[0]] = s
                admin_surveys = list(merged_surveys.values())
                admin_surveys.sort(key=lambda x: x[2], reverse=True)
            
                if not admin_surveys:
                    st.warning(_("ë°°í¬???¨ë¼???¤ë¬¸???†ìŠµ?ˆë‹¤.", "No deployed online surveys found."))
                else:
                    survey_options = {f"{row[1]} ({row[2]})": row[0] for row in admin_surveys}
                
                    default_idx = 0
                    if st.session_state.get("selected_survey_for_analysis") in survey_options.values():
                        default_idx = list(survey_options.values()).index(st.session_state.get("selected_survey_for_analysis"))
                
                    selected_survey_label = st.selectbox(
                        _("ë¶„ì„???¨ë¼???¤ë¬¸ ? íƒ", "Select Online Survey for Analysis"),
                        list(survey_options.keys()),
                        index=default_idx
                    )
                    selected_sheet_id = survey_options[selected_survey_label]
                    filename_base = f"Survey_{selected_sheet_id[:6]}"
                
                    if st.button(_("?”„ êµ¬ê? ?œíŠ¸?ì„œ ?¤ì‹œê°??‘ë‹µ ê°€?¸ì˜¤ê¸?, "?”„ Fetch Live Responses from Google Sheet"), type="primary", use_container_width=True):
                        from survey_manager import load_survey_metadata, get_survey_gspread_client
                        with st.spinner(_("êµ¬ê? ?œíŠ¸?ì„œ ?¤ë¬¸ ?°ì´??ë°?êµ¬ì¡°ë¥?ê°€?¸ì˜¤??ì¤?..", "Fetching survey structure and responses...")):
                            survey_meta = load_survey_metadata(selected_sheet_id)
                            g_client = get_survey_gspread_client()
                            if survey_meta and g_client:
                                try:
                                    spreadsheet = g_client.open_by_key(selected_sheet_id)
                                    raw_sheet = spreadsheet.worksheet("Raw_Data")
                                    all_rows = raw_sheet.get_all_values()
                                
                                    if len(all_rows) > 1:
                                        headers = all_rows[0]
                                        rows = all_rows[1:]
                                        raw_df = pd.DataFrame(rows, columns=headers)
                                        
                                        # [? ê·œ] ?¬ìš©???±ê¸‰???°ë¥¸ ?œë³¸ ???œí•œ (ë¬´ë£Œ ?¬ìš©?? ìµœë? 5?œë³¸)
                                        if st.session_state.get('user_role') == 'free' and len(raw_df) > 5:
                                            raw_df = raw_df.head(5)
                                            st.warning(_("? ï¸ ë¬´ë£Œ ?¬ìš©?ëŠ” ?¨ë¼???¤ë¬¸ ?°ë™ ??ìµœë? 5?œë³¸ê¹Œì?ë§?ë¶„ì„?????ˆìŠµ?ˆë‹¤. ì²˜ìŒ ?‘ìˆ˜??5ëª??????‘ë‹µë§?ë¶„ì„???¬ìš©?©ë‹ˆ??", "? ï¸ Free users can only analyze up to 5 samples. Only the first 5 responses will be analyzed."))
                                    
                                        for col in raw_df.columns:
                                            if col not in ["ID", "Type", "?œì¶œ?œê°„", "?µë????°ë½ì²?]:
                                                raw_df[col] = pd.to_numeric(raw_df[col], errors='coerce').fillna(1.0)
                                            
                                        ahp_model = survey_meta["AHP_Model_JSON"]
                                    
                                        base_cols = ["ID", "Type"]
                                        main_criteria = ahp_model.get("main", [])
                                        main_pairs = []
                                        for i in range(len(main_criteria)):
                                            for j in range(i + 1, len(main_criteria)):
                                                main_pairs.append(f"{main_criteria[i]}_{main_criteria[j]}")
                                        main_cols = [c for c in base_cols if c in raw_df.columns] + [p for p in main_pairs if p in raw_df.columns]
                                    
                                        st.session_state["ahp_df_main"] = raw_df[main_cols].copy()
                                    
                                        st.session_state["ahp_sub_dfs"] = {}
                                        sub_criteria_map = ahp_model.get("subs", {})
                                        for main_c, subs in sub_criteria_map.items():
                                            if len(subs) >= 2:
                                                sub_pairs = []
                                                for i in range(len(subs)):
                                                    for j in range(i + 1, len(subs)):
                                                        sub_pairs.append(f"{subs[i]}_{subs[j]}")
                                                sub_cols = [c for c in base_cols if c in raw_df.columns] + [p for p in sub_pairs if p in raw_df.columns]
                                                st.session_state["ahp_sub_dfs"][main_c] = raw_df[sub_cols].copy()
                                            
                                        # [? ê·œ] 3ê³„ì¸µ ëª¨ë¸??ê²½ìš° ?Œë¶„ë¥?sub_subs) ?°ì´?°í”„?ˆì„ ?Œì‹±
                                        tier_level = int(survey_meta.get("Tier_Level", 2))
                                        st.session_state["ahp_sub_sub_dfs"] = {}
                                        if tier_level == 3:
                                            sub_sub_map = ahp_model.get("sub_subs", {})
                                            for main_c, subs in sub_criteria_map.items():
                                                for sub_c in subs:
                                                    sub_subs = sub_sub_map.get(sub_c, [])
                                                    if len(sub_subs) >= 2:
                                                        sub_sub_pairs = []
                                                        for i in range(len(sub_subs)):
                                                            for j in range(i + 1, len(sub_subs)):
                                                                sub_sub_pairs.append(f"{sub_subs[i]}_{sub_subs[j]}")
                                                        ss_cols = [c for c in base_cols if c in raw_df.columns] + [p for p in sub_sub_pairs if p in raw_df.columns]
                                                        st.session_state["ahp_sub_sub_dfs"][sub_c] = raw_df[ss_cols].copy()

                                        sheet_names_list = ["Main_Criteria"] + list(st.session_state["ahp_sub_dfs"].keys())
                                        if tier_level == 3:
                                            sheet_names_list += list(st.session_state["ahp_sub_sub_dfs"].keys())
                                            
                                        st.session_state["ahp_sheet_names"] = sheet_names_list
                                        st.success(_(f"??êµ¬ê? ?œíŠ¸?ì„œ ì´?{len(raw_df)}ê±´ì˜ ?‘ë‹µ ?°ì´?°ë? ?±ê³µ?ìœ¼ë¡?ê°€?¸ì™”?µë‹ˆ??", f"??Successfully fetched {len(raw_df)} responses!"))
                                    else:
                                        st.warning(_("ê°€?¸ì˜¬ ?¤ë¬¸ ?‘ë‹µ ?°ì´?°ê? ?œíŠ¸??ì¡´ì¬?˜ì? ?ŠìŠµ?ˆë‹¤ (?¤ë”ë§?ì¡´ì¬).", "No survey responses found in the sheet."))
                                except Exception as g_err:
                                    st.error(f"êµ¬ê? ?œíŠ¸ ë¡œë“œ ?¤íŒ¨: {g_err}")
                            else:
                                st.error(_("?¤ë¬¸ ë©”í??°ì´???ëŠ” êµ¬ê? API ?´ë¼?´ì–¸?¸ë? ë¡œë“œ?????†ìŠµ?ˆë‹¤.", "Failed to load survey metadata or Google client."))
                
                    if "ahp_df_main" in st.session_state:
                        df_main = st.session_state["ahp_df_main"]
                        sub_dfs = st.session_state["ahp_sub_dfs"]
                        sheet_names = st.session_state["ahp_sheet_names"]
                        st.info(_("?’¡ êµ¬ê? ?œíŠ¸?ì„œ ë¡œë“œ???¤ì‹œê°??°ì´??ë¶„ì„ ëª¨ë“œ?…ë‹ˆ?? (???°ì´?°ë? ê°€?¸ì˜¤?¤ë©´ ??ë²„íŠ¼???´ë¦­??ì£¼ì„¸??", "?’¡ Live data analysis mode. Click the button above to refresh data."))

        if df_main is not None:
            try:
                main_cols_up = df_main.columns[2:]
                main_factors_up, n_main_up = infer_factors_from_columns(main_cols_up)
            
                permission_granted = False
                message = ""
                role_chk = st.session_state.user_role
                user_id_chk = st.session_state.user_id
            
                if role_chk == 'admin' or role_chk == 'official':
                    permission_granted = True
                    if role_chk == 'official':
                        today_chk = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).date()
                        expiry_chk = datetime.datetime.strptime(st.session_state.expiry_date, "%Y-%m-%d").date()
                        if today_chk > expiry_chk:
                            permission_granted = False
                            message = _("???´ìš© ê¸°ê°„??ë§Œë£Œ?˜ì—ˆ?µë‹ˆ??", "??Your subscription period has expired.")
                else: 
                    rows_ok = True
                    if data_source == _("?“‚ ?‘ì? ?Œì¼ ì§ì ‘ ?…ë¡œ??, "Upload Excel File"):
                        for sn in sheet_names:
                            if len(pd.read_excel(uploaded_file, sheet_name=sn)) > 5:
                                rows_ok = False
                                break
                    else:
                        if len(df_main) > 5:
                            rows_ok = False
                        for sn, sdf in sub_dfs.items():
                            if len(sdf) > 5:
                                rows_ok = False
                                break
                    if rows_ok: permission_granted = True
                    else: message = _(f"??**ë¬´ë£Œ?¬ìš©??*???œíŠ¸??ìµœë? 5ê°??œë³¸ê¹Œì?ë§?ë¶„ì„ ê°€?¥í•©?ˆë‹¤. (?„ì¬: {len(df_main)}ê°??œë³¸)",
                                     f"??**Free Users** can only analyze up to 5 samples per sheet. (Current: {len(df_main)} samples)")
            
                if permission_granted:
                    try:
                        if data_source == _("?“‚ ?‘ì? ?Œì¼ ì§ì ‘ ?…ë¡œ??, "Upload Excel File"):
                            tier_level = st.session_state.get("inferred_tier_level", 2)
                        else:
                            tier_level = int(survey_meta.get("Tier_Level", 2)) if 'survey_meta' in locals() else 2
                        
                        if tier_level == 3:
                            is_english = (st.session_state.get('lang', 'ko') == 'en')
                            success_v3 = False
                            msg_v3 = ""
                            final_df_v3 = None
                            output_res_v3 = None
                            ui_data_v3 = {}
                            with st.spinner(_("3ê³„ì¸µ(?Œë¶„ë¥??¬í•¨) AHP ì¢…í•© ë¶„ì„ ?˜í–‰ ì¤?..", "Performing 3-Tier AHP...")):
                                from ahp_utils_v3 import run_ahp_analysis_v3
                                sub_sub_dfs = st.session_state.get("ahp_sub_sub_dfs", {})
                                success_v3, msg_v3, final_df_v3, output_res_v3, ui_data_v3 = run_ahp_analysis_v3(
                                    df_main, sub_dfs, sub_sub_dfs, cr_threshold, max_iter_val, learning_rate, mean_method, ahp_method,
                                    process_single_sheet, fuzzy_ahp_analysis
                                )

                            if not success_v3:
                                st.error(msg_v3)
                                st.stop()
                            
                            if st.session_state.user_role == 'official':
                                if data_source == _("?“‚ ?‘ì? ?Œì¼ ì§ì ‘ ?…ë¡œ??, "Upload Excel File") and uploaded_file is not None:
                                    save_data = uploaded_file.getvalue()
                                    save_filename = f"{filename_base}_Raw.xlsx"
                                else:
                                    uploadable_io = io.BytesIO()
                                    with pd.ExcelWriter(uploadable_io, engine='openpyxl') as writer:
                                        if df_main is not None and not df_main.empty:
                                            df_main.to_excel(writer, index=False, sheet_name="Main_Criteria")
                                        for s_name, s_df in sub_dfs.items():
                                            s_df.to_excel(writer, index=False, sheet_name=s_name[:31])
                                        sub_sub_dfs_to_save = st.session_state.get("ahp_sub_sub_dfs", {})
                                        for s_name, s_df in sub_sub_dfs_to_save.items():
                                            s_df.to_excel(writer, index=False, sheet_name=s_name[:31])
                                    save_data = uploadable_io.getvalue()
                                    save_filename = f"{filename_base}_Raw.xlsx"
                                save_analysis_to_db(st.session_state.user_id, save_filename, save_data)

                            st.success(_("??3ê³„ì¸µ AHP ë¶„ì„???±ê³µ?ìœ¼ë¡??„ë£Œ?˜ì—ˆ?µë‹ˆ??", "??3-Tier AHP Analysis successfully completed!"))
                            st.markdown(_('<p style="color:red;font-weight:bold;font-size:0.95rem;margin:5px 0 10px;">? ï¸ ì£¼ì˜: ?ˆë¡œê³ ì¹¨?˜ê±°??ë¸Œë¼?°ì?ë¥??«ìœ¼ë©?ê²°ê³¼ê°€ ë¦¬ì…‹?©ë‹ˆ?? ?“‘ ê²°ê³¼ ?¤ìš´ë¡œë“œ ??—??ë°˜ë“œ???€?¥í•˜?¸ìš”.</p>',
                                          '<p style="color:red;font-weight:bold;font-size:0.95rem;margin:5px 0 10px;">? ï¸ Warning: Results reset on refresh. Download via ?“‘ Download Results tab.</p>'), unsafe_allow_html=True)

                            # --- 3ê³„ì¸µ ?„ìš© 5ê°???UI ---
                            v3_unique_groups = ui_data_v3.get("unique_groups", [])
                            v3_comparison_df  = ui_data_v3.get("comparison_df", pd.DataFrame())
                            v3_anova_df       = ui_data_v3.get("anova_df", pd.DataFrame())
                            v3_group_full_dfs = ui_data_v3.get("group_full_dfs", {})
                            v3_indiv_df       = ui_data_v3.get("indiv_df", pd.DataFrame())
                            v3_main_factors   = ui_data_v3.get("main_factors", [])

                            tab3v1, tab3v2, tab3v3, tab3v4, tab3v5 = st.tabs([
                                _("?Œ ì¢…í•© ë¶„ì„ (Global)", "?Œ Global Comprehensive Analysis"),
                                _("?‘¨\u200d?‘©\u200d?‘§\u200d?‘¦ ê·¸ë£¹ë³?ë¶„ì„", "?‘¨\u200d?‘©\u200d?‘§\u200d?‘¦ Group Analysis"),
                                _("?§ª ?µê³„ ê²€??(ANOVA)", "?§ª Statistical Test (ANOVA)"),
                                _("?“Š ?œê°???¼í„°", "?“Š Visualization Center"),
                                _("?“‘ ê²°ê³¼ ?¤ìš´ë¡œë“œ", "?“‘ Download Results")
                            ])

                            # ?€?€?€ Tab 1: ì¢…í•© ë¶„ì„ ?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€
                            with tab3v1:
                                st.subheader(_("?Œ 3ê³„ì¸µ ì¢…í•© ì¤‘ìš”??ë°??œìœ„", "?Œ 3-Tier Global Weights & Rankings"))
                                if is_english:
                                    _disp_v3 = final_df_v3.rename(columns={
                                        "?€ë¶„ë¥˜": "Main Criteria",    "?€ë¶„ë¥˜ ê°€ì¤‘ì¹˜": "Main Weight",
                                        "ì¤‘ë¶„ë¥?: "Sub-Criteria",     "ì¤‘ë¶„ë¥?ê°€ì¤‘ì¹˜": "Sub Weight",
                                        "?Œë¶„ë¥?: "Sub-sub-Criteria", "?Œë¶„ë¥?ê°€ì¤‘ì¹˜": "Sub-sub Weight",
                                        "CR(?€ë¶„ë¥˜)": "CR(Main)",     "CI(?€ë¶„ë¥˜)": "CI(Main)",
                                        "CR(ì¤‘ë¶„ë¥?": "CR(Sub)",      "CI(ì¤‘ë¶„ë¥?": "CI(Sub)",
                                        "CR(?Œë¶„ë¥?": "CR(Sub-sub)",  "CI(?Œë¶„ë¥?": "CI(Sub-sub)"
                                    })
                                else:
                                    _disp_v3 = final_df_v3
                                st.dataframe(_disp_v3.style.format(precision=4), use_container_width=True)

                                st.markdown(_("---\n#### ?“Š ?€ë¶„ë¥˜ë³??Œë¶„ë¥???ª© ê¸€ë¡œë²Œ ê°€ì¤‘ì¹˜",
                                              "---\n#### ?“Š Sub-sub-Criteria Global Weights by Main Criteria"))
                                _non_dummy_v3 = final_df_v3[~final_df_v3["?Œë¶„ë¥?].str.endswith("_?¨ì¼??ª©", na=False)].copy()
                                if _non_dummy_v3.empty:
                                    _non_dummy_v3 = final_df_v3.copy()
                                for _mf_v3 in v3_main_factors:
                                    _mf_subset = _non_dummy_v3[_non_dummy_v3["?€ë¶„ë¥˜"] == _mf_v3]
                                    if _mf_subset.empty:
                                        continue
                                    _mf_chart = _mf_subset.sort_values("Global Weight", ascending=True).copy()
                                    if is_english:
                                        _mf_chart = _mf_chart.rename(columns={"?Œë¶„ë¥?: "Sub-sub-Criteria"})
                                        _y_col_v3 = "Sub-sub-Criteria"
                                    else:
                                        _y_col_v3 = "?Œë¶„ë¥?
                                    _fig_v3_bar = px.bar(
                                        _mf_chart, y=_y_col_v3, x="Global Weight",
                                        orientation="h", text_auto=".4f",
                                        title=_(f"[{_mf_v3}] ?Œë¶„ë¥???ª©ë³?ê¸€ë¡œë²Œ ê°€ì¤‘ì¹˜", f"[{_mf_v3}] Sub-sub-Criteria Global Weights"),
                                        color_discrete_sequence=["#4F81BD"]
                                    )
                                    _fig_v3_bar.update_layout(height=max(300, len(_mf_chart)*40+80), margin=dict(l=0,r=10,t=40,b=20))
                                    st.plotly_chart(_fig_v3_bar, use_container_width=True)

                            # ?€?€?€ Tab 2: ê·¸ë£¹ë³?ë¶„ì„ ?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€
                            with tab3v2:
                                st.markdown(_("#### ê·¸ë£¹ë³??Œë¶„ë¥???ª© ê¸€ë¡œë²Œ ê°€ì¤‘ì¹˜ ë¹„êµ",
                                              "#### Sub-sub-Criteria Global Weight Comparison by Group"))
                                if not v3_comparison_df.empty:
                                    if is_english:
                                        _disp_comp_v3 = v3_comparison_df.copy()
                                        _disp_comp_v3.rename(columns={
                                            "?€ë¶„ë¥˜": "Main Criteria", "ì¤‘ë¶„ë¥?: "Sub-Criteria", "?Œë¶„ë¥?: "Sub-sub-Criteria",
                                            "ì¢…í•©?‰ê· (Overall)": "Overall Avg", "F-ê°?: "F-Value",
                                            "? ì˜??: "Significance", "?¬í›„ê²€??Tukey HSD)": "Post-Hoc (Tukey HSD)"
                                        }, inplace=True)
                                        if "Significance" in _disp_comp_v3.columns:
                                            _disp_comp_v3["Significance"] = _disp_comp_v3["Significance"].map(
                                                {"? ì˜??: "Significant", "? ì˜?˜ì? ?ŠìŒ": "Not Significant"}).fillna(_disp_comp_v3["Significance"])
                                    else:
                                        _disp_comp_v3 = v3_comparison_df
                                    st.dataframe(_disp_comp_v3.style.format(precision=4), use_container_width=True)
                                else:
                                    st.info(_("ê·¸ë£¹ë³?ë¹„êµ ?°ì´?°ê? ?†ìŠµ?ˆë‹¤.", "No group comparison data available."))

                                if len(v3_unique_groups) >= 2 and v3_group_full_dfs:
                                    st.markdown(_("---\n#### ê·¸ë£¹ë³??€ë¶„ë¥˜ ê°€ì¤‘ì¹˜ ë¹„êµ",
                                                  "---\n#### Main Criteria Weight Comparison by Group"))
                                    _grp_main_rows = []
                                    for _grp_v3 in v3_unique_groups:
                                        if _grp_v3 not in v3_group_full_dfs:
                                            continue
                                        _g_df_v3 = v3_group_full_dfs[_grp_v3]
                                        for _mf_v3b in v3_main_factors:
                                            _mf_sub_b = _g_df_v3[_g_df_v3["?€ë¶„ë¥˜"] == _mf_v3b]
                                            if not _mf_sub_b.empty:
                                                _grp_main_rows.append({
                                                    _("ê·¸ë£¹","Group"): _grp_v3,
                                                    _("?€ë¶„ë¥˜","Main Criteria"): _mf_v3b,
                                                    "Weight": float(_mf_sub_b.iloc[0]["?€ë¶„ë¥˜ ê°€ì¤‘ì¹˜"])
                                                })
                                    if _grp_main_rows:
                                        _grp_main_chart_df = pd.DataFrame(_grp_main_rows)
                                        _fig_grp_main = px.bar(
                                            _grp_main_chart_df,
                                            x=_("?€ë¶„ë¥˜","Main Criteria"), y="Weight",
                                            color=_("ê·¸ë£¹","Group"), barmode="group", text_auto=".4f",
                                            title=_("ê·¸ë£¹ë³??€ë¶„ë¥˜ ê°€ì¤‘ì¹˜ ë¹„êµ", "Main Criteria Weight Comparison by Group")
                                        )
                                        st.plotly_chart(_fig_grp_main, use_container_width=True)

                            # ?€?€?€ Tab 3: ANOVA ?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€
                            with tab3v3:
                                st.markdown(_("#### ì§‘ë‹¨ ê°?? ì˜??ë¶„ì„ (3ê³„ì¸µ ê¸°ì?)",
                                              "#### Significance Analysis Between Groups (3-Tier Level)"))
                                if not v3_anova_df.empty:
                                    if is_english:
                                        _disp_anova_v3 = v3_anova_df.copy()
                                        _disp_anova_v3.rename(columns={
                                            "?”ì¸": "Factor/Criteria", "F-ê°?: "F-Value",
                                            "? ì˜??: "Significance", "?¬í›„ê²€??Tukey HSD)": "Post-Hoc (Tukey HSD)"
                                        }, inplace=True)
                                        if "Significance" in _disp_anova_v3.columns:
                                            _disp_anova_v3["Significance"] = _disp_anova_v3["Significance"].map(
                                                {"? ì˜??: "Significant", "? ì˜?˜ì? ?ŠìŒ": "Not Significant"}).fillna(_disp_anova_v3["Significance"])
                                        def _translate_ph_v3(v):
                                            if not isinstance(v, str): return v
                                            v = v.replace("?„ë¬¸ê°€","Expert").replace("?¼ë°˜","General").replace("ê³µë¬´??,"Public Official")
                                            v = v.replace(" ì°¨ì´ ?ˆìŒ"," (Diff exists)")
                                            v = v.replace("ì§‘ë‹¨ ê°?êµ¬ì²´??ì°¨ì´ ë°œê²¬ ëª»í•¨","No significant pairwise difference found")
                                            v = v.replace("ê³„ì‚° ?¤ë¥˜","Calculation Error")
                                            return v
                                        if "Post-Hoc (Tukey HSD)" in _disp_anova_v3.columns:
                                            _disp_anova_v3["Post-Hoc (Tukey HSD)"] = _disp_anova_v3["Post-Hoc (Tukey HSD)"].apply(_translate_ph_v3)
                                    else:
                                        _disp_anova_v3 = v3_anova_df
                                    st.dataframe(_disp_anova_v3.style.format(precision=5), use_container_width=True)

                                    _sig_col_v3 = "Significance" if is_english else "? ì˜??
                                    _sig_val_v3 = "Significant" if is_english else "? ì˜??
                                    if _sig_col_v3 in _disp_anova_v3.columns:
                                        _sig_items_v3 = _disp_anova_v3[_disp_anova_v3[_sig_col_v3] == _sig_val_v3]
                                        if not _sig_items_v3.empty:
                                            _fcol_v3 = "Factor/Criteria" if is_english else "?”ì¸"
                                            _snames = ", ".join(_sig_items_v3[_fcol_v3].tolist())
                                            st.success(_(f"??? ì˜??ì°¨ì´ ë°œê²¬ ??ª©: {_snames}", f"??Statistically significant factors: {_snames}"))
                                        else:
                                            st.info(_("ëª¨ë“  ??ª©?ì„œ ê·¸ë£¹ ê°?? ì˜??ì°¨ì´ê°€ ?†ìŠµ?ˆë‹¤.", "No statistically significant group differences found."))
                                else:
                                    st.info(_("?µê³„ ê²€?•ì„ ?„í•´ 2ê°??´ìƒ??ê·¸ë£¹ ?°ì´?°ê? ?„ìš”?©ë‹ˆ??",
                                              "At least 2 group datasets are required for ANOVA."))

                            # ?€?€?€ Tab 4: ?œê°???¼í„° ?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€
                            with tab3v4:
                                st.markdown(_("#### ?“Š 3ê³„ì¸µ AHP ?œê°???¼í„°", "#### ?“Š 3-Tier AHP Visualization Center"))

                                st.markdown(_("**??ê¸€ë¡œë²Œ ê°€ì¤‘ì¹˜ ?œìœ„ ë²„ë¸” ì°¨íŠ¸ (ë²„ë¸” ?¬ê¸° = ì¤‘ë¶„ë¥?ê°€ì¤‘ì¹˜, ??= ?€ë¶„ë¥˜)**",
                                              "**??Global Weight Bubble Chart (bubble size = Sub weight, color = Main Criteria)**"))
                                _nd_v3 = final_df_v3[~final_df_v3["?Œë¶„ë¥?].str.endswith("_?¨ì¼??ª©", na=False)].copy()
                                if _nd_v3.empty:
                                    _nd_v3 = final_df_v3.copy()
                                    _item_col_bub = "ì¤‘ë¶„ë¥?
                                else:
                                    _item_col_bub = "?Œë¶„ë¥?
                                _bubble_df = _nd_v3.copy()
                                if "Global Rank" not in _bubble_df.columns:
                                    _bubble_df["Global Rank"] = _bubble_df["Global Weight"].rank(ascending=False, method="min").astype(int)
                                # ë²„ë¸” ?¬ê¸°: ì¤‘ë¶„ë¥?ê°€ì¤‘ì¹˜ ê¸°ë°˜ (ìµœì†Œ ?¬ê¸° ë³´ì¥)
                                _bubble_df["_bubble_size"] = (_bubble_df["ì¤‘ë¶„ë¥?ê°€ì¤‘ì¹˜"] * 100).clip(lower=3)
                                if is_english:
                                    _bubble_df_disp = _bubble_df.rename(columns={
                                        "?Œë¶„ë¥?: "Sub-sub-Criteria", "?€ë¶„ë¥˜": "Main Criteria",
                                        "ì¤‘ë¶„ë¥?: "Sub-Criteria", "ì¤‘ë¶„ë¥?ê°€ì¤‘ì¹˜": "Sub Weight"
                                    })
                                    _label_col_bub = "Sub-sub-Criteria" if _item_col_bub == "?Œë¶„ë¥? else "Sub-Criteria"
                                    _color_bub = "Main Criteria"
                                    _hover_sub_bub = "Sub-Criteria"
                                    _hover_subw_bub = "Sub Weight"
                                else:
                                    _bubble_df_disp = _bubble_df
                                    _label_col_bub = _item_col_bub
                                    _color_bub = "?€ë¶„ë¥˜"
                                    _hover_sub_bub = "ì¤‘ë¶„ë¥?
                                    _hover_subw_bub = "ì¤‘ë¶„ë¥?ê°€ì¤‘ì¹˜"
                                _fig_bub = px.scatter(
                                    _bubble_df_disp,
                                    x="Global Rank", y="Global Weight",
                                    size="_bubble_size", color=_color_bub,
                                    text=_label_col_bub,
                                    hover_data={
                                        _label_col_bub: True,
                                        _hover_sub_bub: True,
                                        _hover_subw_bub: ":.4f",
                                        "Global Weight": ":.4f",
                                        "Global Rank": True,
                                        "_bubble_size": False
                                    },
                                    title=_("?Œë¶„ë¥?ê¸€ë¡œë²Œ ê°€ì¤‘ì¹˜ ë²„ë¸” ì°¨íŠ¸ (ë²„ë¸”???´ìˆ˜ë¡?ì¤‘ë¶„ë¥?ë¹„ì¤‘ ?’ìŒ, ?„ë¡œ ê°ˆìˆ˜ë¡?ê¸€ë¡œë²Œ ê°€ì¤‘ì¹˜ ?’ìŒ)",
                                            "Sub-sub-Criteria Global Weight Bubble Chart (larger = higher sub weight, higher = higher global weight)"),
                                    color_discrete_sequence=px.colors.qualitative.Set2,
                                    size_max=55
                                )
                                _fig_bub.update_traces(textposition="top center", textfont_size=10)
                                _fig_bub.update_xaxes(
                                    title=_("ì¢…í•© ?œìœ„ (1??= ê°€??ì¤‘ìš”)", "Global Rank (1 = Most Important)"),
                                    dtick=1, autorange="reversed"
                                )
                                _fig_bub.update_yaxes(title=_("ê¸€ë¡œë²Œ ê°€ì¤‘ì¹˜", "Global Weight"))
                                _fig_bub.update_layout(height=560, legend_title_text=_color_bub)
                                st.plotly_chart(_fig_bub, use_container_width=True)

                                st.markdown(_("**??ê³„ì¸µë³??¼ê???ë¹„ìœ¨(CR) ë¶„í¬ ??ë°”ì´?¬ë¦° ?Œë¡¯**",
                                              "**??Consistency Ratio (CR) Distribution by Tier ??Violin Plot**"))
                                st.caption(_("ê³„ì¸µ??? íƒ?˜ë©´ ?´ë‹¹ ?˜ì? ?‘ë‹µ?ë“¤??CR ë¶„í¬ë¥??œì‹œ?©ë‹ˆ?? ë°”ì´?¬ë¦° ??= ë°€?? ?´ë? ë°•ìŠ¤ = ì¤‘ì•™ê°’Â·ì‚¬ë¶„ìœ„?? ??= ê°œë³„ ?‘ë‹µ??,
                                             "Select a tier to view respondent CR distribution. Width = density, box = median/IQR, dots = individual respondents"))

                                _vio_main_df   = ui_data_v3.get("main_results_df", pd.DataFrame())
                                _vio_sub_stor  = ui_data_v3.get("sub_results_storage", {})
                                _vio_ss_stor   = ui_data_v3.get("sub_sub_results_storage", {})
                                _vio_mf_list   = ui_data_v3.get("main_factors", [])

                                _tier_options_ko = ["?€ë¶„ë¥˜ (Main)", "ì¤‘ë¶„ë¥?(Sub)", "?Œë¶„ë¥?(Sub-sub)"]
                                _tier_options_en = ["Main Criteria", "Sub-Criteria", "Sub-sub-Criteria"]
                                _tier_opts = _tier_options_en if is_english else _tier_options_ko
                                _sel_tier = st.selectbox(
                                    _("?“‚ ?œì‹œ??ê³„ì¸µ ? íƒ", "?“‚ Select Tier to Display"),
                                    options=_tier_opts,
                                    key="vio_tier_select_v3"
                                )

                                try:
                                    import plotly.graph_objects as _go_vio
                                    _vio_palette = [
                                        "rgba(70,130,180,0.65)",
                                        "rgba(205,92,92,0.65)",
                                        "rgba(255,182,193,0.65)",
                                        "rgba(60,179,113,0.65)",
                                        "rgba(255,165,0,0.65)",
                                        "rgba(147,112,219,0.65)",
                                        "rgba(72,209,204,0.65)",
                                        "rgba(255,215,0,0.65)",
                                    ]
                                    _vio_line_pal = [
                                        "#4682B4","#CD5C5C","#FFB6C1","#3CB371",
                                        "#FFA500","#9370DB","#48D1CC","#FFD700"
                                    ]
                                    _fig_vio = _go_vio.Figure()
                                    _ci = 0

                                    # ?€?€ ? íƒ: ?€ë¶„ë¥˜ ?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€
                                    if _sel_tier in [_tier_opts[0]]:
                                        if not _vio_main_df.empty and "Final_CR" in _vio_main_df.columns:
                                            _main_cr = _vio_main_df["Final_CR"].dropna().tolist()
                                            _xlbl = _("?€ë¶„ë¥˜", "Main Criteria")
                                            _fig_vio.add_trace(_go_vio.Violin(
                                                y=_main_cr, x=[_xlbl]*len(_main_cr),
                                                name=_xlbl, box_visible=True, meanline_visible=True,
                                                points="all", jitter=0.35, pointpos=0,
                                                line_color=_vio_line_pal[0], fillcolor=_vio_palette[0],
                                                opacity=0.75,
                                                hovertemplate="<b>" + _xlbl + "</b><br>CR: %{y:.4f}<extra></extra>",
                                                showlegend=True
                                            ))
                                        _vio_xaxis_title = _("?€ë¶„ë¥˜", "Main Criteria")
                                        _vio_legend_title = _("?€ë¶„ë¥˜", "Main Criteria")

                                    # ?€?€ ? íƒ: ì¤‘ë¶„ë¥??€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€
                                    elif _sel_tier in [_tier_opts[1]]:
                                        # ?€ë¶„ë¥˜ë³„ë¡œ ?˜ë‚˜??ë°”ì´?¬ë¦° (?´ë‹¹ ?€ë¶„ë¥˜ ì¤‘ë¶„ë¥?ë¹„êµ ??CR)
                                        for _mf in _vio_mf_list:
                                            _sinfo = _vio_sub_stor.get(_mf, {})
                                            _sdf = _sinfo.get("df", None)
                                            if _sdf is None or _sdf.empty or "Final_CR" not in _sdf.columns:
                                                continue
                                            _cr_vals = _sdf["Final_CR"].dropna().tolist()
                                            if len(_cr_vals) < 2:
                                                continue
                                            _xlbl = _(f"ì¤‘ë¶„ë¥?{_mf})", f"Sub({_mf})")
                                            _fig_vio.add_trace(_go_vio.Violin(
                                                y=_cr_vals, x=[_xlbl]*len(_cr_vals),
                                                name=_xlbl, box_visible=True, meanline_visible=True,
                                                points="all", jitter=0.35, pointpos=0,
                                                line_color=_vio_line_pal[_ci % len(_vio_line_pal)],
                                                fillcolor=_vio_palette[_ci % len(_vio_palette)],
                                                opacity=0.75,
                                                hovertemplate="<b>" + _xlbl + "</b><br>CR: %{y:.4f}<extra></extra>",
                                                showlegend=True
                                            ))
                                            _ci += 1
                                        _vio_xaxis_title = _("?€ë¶„ë¥˜ (ì¤‘ë¶„ë¥?ë¹„êµ CR)", "Main Criteria (Sub-Criteria Comparison CR)")
                                        _vio_legend_title = _("ì¤‘ë¶„ë¥?, "Sub-Criteria")

                                    # ?€?€ ? íƒ: ?Œë¶„ë¥??€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€
                                    else:
                                        # ì¤‘ë¶„ë¥˜ë³„ë¡??˜ë‚˜??ë°”ì´?¬ë¦° (?´ë‹¹ ì¤‘ë¶„ë¥??Œë¶„ë¥?ë¹„êµ ??CR)
                                        for _mf in _vio_mf_list:
                                            _sinfo = _vio_sub_stor.get(_mf, {})
                                            _sub_factors = _sinfo.get("factors", [])
                                            for _sf in _sub_factors:
                                                _ssinfo = _vio_ss_stor.get(_sf, {})
                                                _ssdf = _ssinfo.get("df", None)
                                                if _ssdf is None or _ssdf.empty or "Final_CR" not in _ssdf.columns:
                                                    continue
                                                _cr_vals = _ssdf["Final_CR"].dropna().tolist()
                                                if len(_cr_vals) < 2:
                                                    continue
                                                _xlbl = _(f"?Œë¶„ë¥?{_sf})", f"Sub-sub({_sf})")
                                                _fig_vio.add_trace(_go_vio.Violin(
                                                    y=_cr_vals, x=[_xlbl]*len(_cr_vals),
                                                    name=_xlbl, box_visible=True, meanline_visible=True,
                                                    points="all", jitter=0.35, pointpos=0,
                                                    line_color=_vio_line_pal[_ci % len(_vio_line_pal)],
                                                    fillcolor=_vio_palette[_ci % len(_vio_palette)],
                                                    opacity=0.75,
                                                    hovertemplate="<b>" + _xlbl + "</b><br>CR: %{y:.4f}<extra></extra>",
                                                    showlegend=True
                                                ))
                                                _ci += 1
                                        _vio_xaxis_title = _("ì¤‘ë¶„ë¥?(?Œë¶„ë¥?ë¹„êµ CR)", "Sub-Criteria (Sub-sub Comparison CR)")
                                        _vio_legend_title = _("?Œë¶„ë¥?, "Sub-sub-Criteria")

                                    if len(_fig_vio.data) == 0:
                                        st.info(_("? íƒ??ê³„ì¸µ??CR ?°ì´?°ê? ?†ê±°???‘ë‹µ ?˜ê? ë¶€ì¡±í•©?ˆë‹¤.",
                                                  "No CR data available for the selected tier or insufficient responses."))
                                    else:
                                        _fig_vio.add_hline(
                                            y=0.1, line_dash="dash", line_color="red",
                                            annotation_text=_("CR ?„ê³„ê°?(0.1)", "CR Threshold (0.1)"),
                                            annotation_position="top right"
                                        )
                                        _fig_vio.update_layout(
                                            title=_(
                                                f"ë°”ì´?¬ë¦°?Œë¡¯ CR ??{_sel_tier}",
                                                f"Violin Plot CR ??{_sel_tier}"
                                            ),
                                            xaxis_title=_vio_xaxis_title,
                                            yaxis_title="Final_CR",
                                            violinmode="overlay",
                                            height=540,
                                            legend_title_text=_vio_legend_title,
                                            plot_bgcolor="white",
                                            paper_bgcolor="white",
                                            xaxis=dict(showgrid=False, tickangle=-20),
                                            yaxis=dict(showgrid=True, gridcolor="#eeeeee", zeroline=False)
                                        )
                                        st.plotly_chart(_fig_vio, use_container_width=True)
                                except Exception as _e_vio:
                                    st.warning(_(f"ë°”ì´?¬ë¦° ?Œë¡¯ ?ì„± ?¤íŒ¨: {_e_vio}", f"Violin plot generation failed: {_e_vio}"))

                                if len(v3_unique_groups) >= 2 and v3_group_full_dfs:
                                    st.markdown(_("**??ê·¸ë£¹ë³??€ë¶„ë¥˜ ì¤‘ìš”???ˆì´??ì°¨íŠ¸**",
                                                  "**??Main Criteria Importance Radar Chart by Group**"))
                                    _radar_rows = []
                                    for _grp_rd in v3_unique_groups:
                                        if _grp_rd not in v3_group_full_dfs: continue
                                        _gdf_rd = v3_group_full_dfs[_grp_rd]
                                        for _mf_rd in v3_main_factors:
                                            _mf_rd_sub = _gdf_rd[_gdf_rd["?€ë¶„ë¥˜"]==_mf_rd]
                                            _w_rd = float(_mf_rd_sub.iloc[0]["?€ë¶„ë¥˜ ê°€ì¤‘ì¹˜"]) if not _mf_rd_sub.empty else 0.0
                                            _lbl_rd = str(_grp_rd).replace("?„ë¬¸ê°€","Expert").replace("?¼ë°˜","General").replace("ê³µë¬´??,"Public Official") if is_english else _grp_rd
                                            _radar_rows.append({_("ê·¸ë£¹","Group"): _lbl_rd, _("??ª©","Factor"): _mf_rd, "Weight": _w_rd})
                                    if _radar_rows:
                                        _radar_df_v3 = pd.DataFrame(_radar_rows)
                                        _cats_rd = _radar_df_v3[_("??ª©","Factor")].unique().tolist()
                                        _fig_rd = go.Figure()
                                        _colors_rd = ["#4F81BD","#C0504D","#9BBB59","#8064A2","#F79646"]
                                        for _i_rd, _grp_rdn in enumerate(_radar_df_v3[_("ê·¸ë£¹","Group")].unique()):
                                            _g_rd = _radar_df_v3[_radar_df_v3[_("ê·¸ë£¹","Group")]==_grp_rdn]
                                            _vals_rd = [_g_rd[_g_rd[_("??ª©","Factor")]==c]["Weight"].values[0] if len(_g_rd[_g_rd[_("??ª©","Factor")]==c])>0 else 0 for c in _cats_rd]
                                            _vals_cl = _vals_rd + [_vals_rd[0]]
                                            _cats_cl = _cats_rd + [_cats_rd[0]]
                                            _fig_rd.add_trace(go.Scatterpolar(r=_vals_cl, theta=_cats_cl, fill="toself", name=_grp_rdn, line_color=_colors_rd[_i_rd % len(_colors_rd)], opacity=0.7))
                                        _fig_rd.update_layout(
                                            polar=dict(radialaxis=dict(visible=True, range=[0, max(0.01, _radar_df_v3["Weight"].max()*1.2)])),
                                            showlegend=True,
                                            title=_("ê·¸ë£¹ë³??€ë¶„ë¥˜ ì¤‘ìš”???¨í„´", "Main Criteria Importance Pattern by Group"),
                                            height=450
                                        )
                                        st.plotly_chart(_fig_rd, use_container_width=True)

                            # ?€?€?€ Tab 5: ê²°ê³¼ ?¤ìš´ë¡œë“œ ?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€
                            with tab3v5:
                                st.markdown(_("### ?“‘ 3ê³„ì¸µ AHP ì¢…í•©ë¶„ì„ ê²°ê³¼ ?¤ìš´ë¡œë“œ",
                                              "### ?“‘ Download 3-Tier AHP Comprehensive Analysis Results"))
                                st.download_button(
                                    label=_("?“¥ 3ê³„ì¸µ AHP ì¢…í•©ë¶„ì„ ê²°ê³¼ ?¤ìš´ë¡œë“œ (.xlsx)", "?“¥ Download 3-Tier AHP Results (.xlsx)"),
                                    data=output_res_v3,
                                    file_name="3Tier_AHP_Result.xlsx",
                                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                    type="primary",
                                    use_container_width=True
                                )
                                st.info(_("?“‹ ?‘ì? ?Œì¼?ëŠ” ì¢…í•©ë¶„ì„, ê·¸ë£¹ë¹„êµ, ê³„ì¸µë³??ì„¸?‰ë ¬, CR ë¶„í¬ ???„ì²´ ë¶„ì„ ê²°ê³¼ê°€ ?¬í•¨?©ë‹ˆ??",
                                          "?“‹ The Excel file contains all results: comprehensive summary, group comparison, detailed matrices per tier, and CR distribution."))

                            # 3ê³„ì¸µ ì²˜ë¦¬ ?„ë£Œ ??ê¸°ì¡´ 2ê³„ì¸µ UI ?¤í‚µ
                            st.stop()
                        
                        with st.spinner(_("ê³„ì¸µ ë¶„ì„ ?˜í–‰ ì¤?..", "Performing Analytic Hierarchy Process (AHP)...")):
                            # 1. ë©”ì¸ ?œíŠ¸ ë¶„ì„ ?œë„
                            try:
                                main_results_df, main_factors, main_excluded, main_excluded_df = process_single_sheet(
                                    df_main, cr_threshold, max_iter_val, learning_rate, mean_method, ahp_method
                                )
                            except Exception as e:
                                st.error(_("??[ë©”ì¸ ?œíŠ¸] ë¶„ì„ ì¤??¤ë¥˜ê°€ ë°œìƒ?ˆìŠµ?ˆë‹¤.", "??Error occurred during [Main Criteria] analysis."))
                                with st.expander(_("?’¡ ?´ìœ  ë°??´ê²° ë°©ë²• ë³´ê¸°", "?’¡ View Reason & Solution"), expanded=True):
                                    st.markdown(_(f"""
                                    **?ì¸:** ë©”ì¸ ?œíŠ¸???°ì´??êµ¬ì¡°ê°€ ?¬ë°”ë¥´ì? ?Šê±°???½ì„ ???ˆëŠ” ? íš¨ ?°ì´?°ê? ?†ìŠµ?ˆë‹¤. (Error: {e})
                                    **?´ê²° ë°©ë²•:**
                                    1. ?‘ì???ì²?ë²ˆì§¸ ?œíŠ¸ ?´ë¦„??`Main_Criteria`?¸ì? ?•ì¸?˜ì„¸??
                                    2. ID?€ Type ???¤ìŒ???ë?ë¹„êµ ?°ì´?°ê? ?¬ë°”ë¥´ê²Œ ?…ë ¥?˜ì—ˆ?”ì? ?•ì¸?˜ì„¸??
                                    3. ë¹??‰ì´ ?¬í•¨?˜ì–´ ?ˆë‹¤ë©??? œ ???¤ì‹œ ?œë„?˜ì„¸??
                                    """,
                                    f"""
                                    **Cause:** The structure of the main sheet is incorrect or contains no readable valid data. (Error: {e})
                                    **Solution:**
                                    1. Ensure that the first sheet name in Excel is `Main_Criteria`.
                                    2. Verify that pair-wise comparison data is correctly input after the 'ID' and 'Type' columns.
                                    3. If empty rows are included, delete them and try again.
                                    """))
                                st.stop()
    
                            # [ë°©ì–´ ì½”ë“œ] ë©”ì¸ ê²°ê³¼ ì¶©ë¶„??ì²´í¬
                            if main_results_df.empty or len(main_results_df) < 1:
                                st.error(_(f"? ï¸ ë¶„ì„ ë¶ˆê?: ë©”ì¸ ê¸°ì? ? íš¨ ?‘ë‹µ?ê? ë¶€ì¡±í•©?ˆë‹¤. (?„ì¬ {len(main_results_df)}ëª?",
                                           f"? ï¸ Cannot Analyze: Insufficient valid respondents for Main Criteria. (Current: {len(main_results_df)} respondents)"))
                                with st.expander(_("?’¡ ?´ìœ  ë°??´ê²° ë°©ë²• ë³´ê¸°", "?’¡ View Reason & Solution"), expanded=True):
                                    st.markdown(_(f"""
                                    **?ì¸:** ëª¨ë“  ?‘ë‹µ?ì˜ ?¼ê???ë¹„ìœ¨(CR)???„ê³„ì¹?{cr_threshold})ë¥?ì´ˆê³¼?˜ì—¬ ë³´ì • ?„ì—???˜ë ´?˜ì? ëª»í–ˆ?µë‹ˆ??
                                    **?´ê²° ë°©ë²•:**
                                    1. ?¼ìª½ ?¬ì´?œë°”?ì„œ **'?¼ê???ë¹„ìœ¨(CR) ?„ê³„ê°?**??0.15 ?ëŠ” 0.2ë¡??„í™”??ë³´ì„¸??
                                    2. **'ë³´ì • ê°•ë„(Learning Rate)'**ë¥?0.7 ?´ìƒ?¼ë¡œ ?’ì—¬ë³´ì„¸??
                                    3. **'ìµœë? ë³´ì • ë°˜ë³µ ?Ÿìˆ˜'**ë¥?500?Œë¡œ ?¤ì •?ˆëŠ”ì§€ ?•ì¸?˜ì„¸??
                                    """,
                                    f"""
                                    **Cause:** The Consistency Ratio (CR) of all respondents exceeded the threshold ({cr_threshold}) and could not converge even after correction.
                                    **Solution:**
                                    1. Loosen the **'Consistency Ratio (CR) Threshold'** to 0.15 or 0.2 in the left sidebar.
                                    2. Increase the **'Correction Intensity (Learning Rate)'** to 0.7 or higher.
                                    3. Ensure **'Max Correction Iterations'** is set to 500.
                                    """))
                                st.stop()
    
                            # --- Uploaded Data Matrix for CR Distortion Verification ---
                            if 'Orig_Matrix_Object' in main_results_df.columns:
                                orig_mats = np.stack(main_results_df['Orig_Matrix_Object'].values)
                                # Use geometric mean to aggregate the raw matrices of all respondents
                                agg_orig_matrix = np.exp(np.mean(np.log(orig_mats), axis=0))
                                st.session_state.uploaded_matrix = agg_orig_matrix
                            # -----------------------------------------------------------

                            # 2. ?˜ìœ„ ?œíŠ¸ ë¶„ì„ ë°??€??
                            sub_results_storage = {}
                            total_excl_df_list = [main_excluded_df]
                        
                            is_single_sheet = (len(sheet_names) == 1)
                        
                            if is_single_sheet:
                                for parent_factor in main_factors:
                                    # 1?¨ê³„ ë¶„ì„??ê²½ìš° (?˜ìœ„ ?œíŠ¸ê°€ ?†ìŒ), 
                                    # ?˜ìœ„ ê°€ì¤‘ì¹˜ 1.0??ê°€ì§€???”ë? ?°ì´?°ë? ?ë™?¼ë¡œ ?ì„±?˜ì—¬ ?°ì‚°??ë§ˆì¹©?ˆë‹¤.
                                    dummy_list = []
                                    for idx, row in main_results_df.iterrows():
                                        dummy_list.append({
                                            "ID": row['ID'],
                                            "Type": row['Type'],
                                            "Original_CI": 0.0,
                                            "Original_CR": 0.0,
                                            "Final_CI": 0.0,
                                            "Final_CR": 0.0,
                                            "Iterations": 0,
                                            "Corrected": False,
                                            "Matrix_Object": np.array([[1.0]]),
                                            f"Weight_{parent_factor}": 1.0
                                        })
                                    dummy_df = pd.DataFrame(dummy_list)
                                    sub_results_storage[parent_factor] = {
                                        'weights': np.array([1.0]),
                                        'factors': [parent_factor],
                                        'cr': 0.0,
                                        'ci': 0.0,
                                        'df': dummy_df,
                                        'group_matrix': np.array([[1.0]]),
                                        'group_cr': 0.0,
                                        'group_ci': 0.0
                                    }
                            else:
                                for parent_factor in main_factors:
                                    # ?€ë¶„ë¥˜ ??ª©ëª…ê³¼ ?¼ì¹˜?˜ëŠ” ?œíŠ¸ëª?ì°¾ê¸° (?€?Œë¬¸?? ê³µë°± ë¬´ì‹œ ë°?31???œí•œ ê³ ë ¤)
                                    target_name = parent_factor.strip().lower()
                                    target_name_31 = parent_factor[:31].strip().lower()
                                
                                    matched_sheet_name = None
                                    for sn in sheet_names[1:]:
                                        sn_clean = sn.strip().lower()
                                        if sn_clean == target_name or sn_clean == target_name_31:
                                            matched_sheet_name = sn
                                            break
                                
                                    if matched_sheet_name is None:
                                        st.error(_(f"??[?¸ë? ?œíŠ¸: {parent_factor}] ?œíŠ¸ë¥?ì°¾ì„ ???†ìŠµ?ˆë‹¤.", f"??[Detailed Sheet: {parent_factor}] Sheet not found."))
                                        with st.expander(_("?’¡ ?´ìœ  ë°??´ê²° ë°©ë²• ë³´ê¸°", "?’¡ View Reason & Solution"), expanded=True):
                                            st.markdown(_(f"""
                                            **?ì¸:** ë©”ì¸ ê¸°ì? ?œíŠ¸?ì„œ ?„ì¶œ???€ë¶„ë¥˜ ??ª© **'{parent_factor}'**???€?‘í•˜???¸ë? ?¤ë¬¸ ?‘ë‹µ ?œíŠ¸ê°€ ?‘ì? ?Œì¼ ?´ì— ì¡´ì¬?˜ì? ?Šê±°???œíŠ¸ ?´ë¦„???¤ë¦…?ˆë‹¤.
                                            **?´ê²° ë°©ë²•:**
                                            1. ?…ë¡œ?œí•œ ?‘ì? ?Œì¼ ?´ì— **'{parent_factor}'** (?ëŠ” 31???´ë‚´ë¡??ë?ë¶„ì´ ?¼ì¹˜?˜ëŠ” ëª…ì¹­)???œíŠ¸ê°€ ì¡´ì¬?˜ëŠ”ì§€ ?•ì¸?˜ì„¸??
                                            2. ?œíŠ¸ ?´ë¦„???ë’¤ ê³µë°±?´ë‚˜ ?¤íƒˆ???? 'ë¦¬ë“œ?€?„ë?ê°ë„'?€ 'ë¦¬ë“œ?€??ë¯¼ê°??)ê°€ ?†ëŠ”ì§€ ?•ì¸?˜ê³  ?œíŠ¸ëª…ì„ ë§ì¶°ì£¼ì„¸??
                                            """,
                                            f"""
                                            **Cause:** The detailed survey response sheet corresponding to the main criteria category **'{parent_factor}'** does not exist in the Excel file or has a different name.
                                            **Solution:**
                                            1. Check if a sheet named **'{parent_factor}'** (or a name matching the first 31 characters) exists in the uploaded Excel file.
                                            2. Ensure there are no leading/trailing spaces or spelling discrepancies (e.g., 'Lead Time Sensitivity' vs 'LeadTime Sensitivity') and align the sheet names.
                                            """))
                                        st.stop()
                                
                                    try:
                                        if data_source == _("?Œ ë°°í¬???¨ë¼???¤ë¬¸ ?°ì´???°ë™", "?Œ Connect Online Survey Data"):
                                            df_sub = st.session_state["ahp_sub_dfs"][matched_sheet_name]
                                        else:
                                            df_sub = pd.read_excel(uploaded_file, sheet_name=matched_sheet_name)
                                            
                                        sub_res_df, sub_facts, sub_excl, sub_excl_df = process_single_sheet(
                                            df_sub, cr_threshold, max_iter_val, learning_rate, mean_method, ahp_method
                                        )
                                    
                                        if sub_res_df.empty:
                                            raise ValueError(f"'{matched_sheet_name}' ?œíŠ¸??? íš¨??ë¶„ì„ ?°ì´?°ê? ?†ìŠµ?ˆë‹¤.")
                                        
                                        # ?µê³„ ê³„ì‚° ë¡œì§
                                        sub_w_cols = [f"Weight_{f}" for f in sub_facts]
                                        sub_matrices = np.stack(sub_res_df['Matrix_Object'].values)
                                        sub_group_matrix = np.mean(sub_matrices, axis=0) if mean_method == 'arithmetic' else gmean(sub_matrices, axis=0)
                                        sub_grp_cr, sub_grp_ci, _not_used_lambda = calculate_consistency(sub_group_matrix, method=mean_method)
                                    
                                        if ahp_method == 'fuzzy':
                                            sw_vals, sub_group_Si = fuzzy_ahp_analysis(sub_group_matrix)
                                            group_sub_w = pd.Series(sw_vals, index=sub_w_cols)
                                        else:
                                            sub_group_Si = None
                                            group_sub_w = sub_res_df[sub_w_cols].mean(axis=0) if mean_method == 'arithmetic' else gmean(sub_res_df[sub_w_cols].values, axis=0)
                                            group_sub_w = group_sub_w / group_sub_w.sum()
                                    
                                        sub_results_storage[parent_factor] = {
                                            'weights': group_sub_w, 'factors': sub_facts, 'cr': sub_res_df['Final_CR'].mean(),
                                            'ci': sub_res_df['Final_CI'].mean(),
                                            'df': sub_res_df, 'group_matrix': sub_group_matrix, 'group_cr': sub_grp_cr,
                                            'group_ci': sub_grp_ci, 'group_Si': sub_group_Si
                                        }
                                        if not sub_excl_df.empty:
                                            sub_excl_df['Sheet'] = parent_factor
                                            total_excl_df_list.append(sub_excl_df)
                                        
                                    except Exception as e:
                                        st.error(_(f"??[?¸ë? ?œíŠ¸: {matched_sheet_name}] ë¶„ì„ ì¤??¤ë¥˜ê°€ ë°œìƒ?ˆìŠµ?ˆë‹¤.", f"??Error occurred during [Detailed Sheet: {matched_sheet_name}] analysis."))
                                        with st.expander(_("?’¡ ?´ìœ  ë°??´ê²° ë°©ë²• ë³´ê¸°", "?’¡ View Reason & Solution"), expanded=True):
                                            st.markdown(_(f"""
                                            **?ì¸:** ?œíŠ¸ ?´ë????°ì´??êµ¬ì¡°ê°€ ?¬ë°”ë¥´ì? ?Šê±°?? ?´ë‹¹ ?œíŠ¸???‘ë‹µ?ë“¤??ëª¨ë‘ ?¼ê???ê¸°ì????µê³¼?˜ì? ëª»í–ˆ?µë‹ˆ?? (Error: {e})
                                            **?´ê²° ë°©ë²•:**
                                            1. ?´ë‹¹ ?¸ë? ?œíŠ¸???°ì´?°ì— ë¹?ì¹¸ì´??ë¬¸ìê°€ ?ì—¬ ?ˆëŠ”ì§€ ?•ì¸?˜ì„¸??
                                            2. CR ?„ê³„ê°’ì„ ?’ì—¬???¤ì‹œ ë¶„ì„??ë³´ì„¸??
                                            """,
                                            f"""
                                            **Cause:** The internal data structure of the sheet is incorrect, or all respondents for this sheet failed to pass the consistency ratio criteria. (Error: {e})
                                            **Solution:**
                                            1. Check if there are empty cells or text mixed in the data of the detailed sheet.
                                            2. Try analyzing again with a higher CR threshold.
                                            """))
                                        st.stop()
    
                            # ë¶„ì„ ?¤ë” ?—ìª½???œì™¸???¬ë????œì‹œ
                            total_excluded = main_excluded
                            st.markdown(f"**" + _(f"ë¶„ì„ ?œì™¸: {total_excluded}ê±?, f"Excluded from Analysis: {total_excluded} cases") + "**")
    
                            main_sig_df = calculate_pairwise_ttest(main_results_df, main_factors)
                            main_weight_cols = [f"Weight_{f}" for f in main_factors]
                        
                            main_matrices = np.stack(main_results_df['Matrix_Object'].values)
                            main_group_matrix = np.mean(main_matrices, axis=0) if mean_method == 'arithmetic' else gmean(main_matrices, axis=0)
                            main_grp_cr, main_grp_ci, _not_used_lambda = calculate_consistency(main_group_matrix, mean_method)
                        
                            if ahp_method == 'fuzzy':
                                mw_vals, main_group_Si = fuzzy_ahp_analysis(main_group_matrix)
                                group_main_weights = pd.Series(mw_vals, index=main_weight_cols)
                            else:
                                main_group_Si = None
                                if mean_method == 'arithmetic':
                                    group_main_weights = main_results_df[main_weight_cols].mean(axis=0)
                                else:
                                    group_main_weights = gmean(main_results_df[main_weight_cols].values, axis=0)
                                group_main_weights = group_main_weights / group_main_weights.sum()
                        
                            main_cr_final_avg = main_results_df['Final_CR'].mean()
                        
                            indiv_global_data = []
                            all_ids = main_results_df['ID'].unique()
                        
                            for uid in all_ids:
                                u_main = main_results_df[main_results_df['ID'] == uid]
                                if u_main.empty: continue
                                u_type = u_main['Type'].values[0]
                                for mf in main_factors:
                                    m_w = u_main[f"Weight_{mf}"].values[0]
                                    s_row_df = sub_results_storage[mf]['df']
                                    u_sub = s_row_df[s_row_df['ID'] == uid]
                                    if u_sub.empty: continue
                                    for sf in sub_results_storage[mf]['factors']:
                                        s_w = u_sub[f"Weight_{sf}"].values[0]
                                        indiv_global_data.append({
                                            "ID": uid, "Type": str(u_type), "Factor": sf, "Global_Weight": m_w * s_w,
                                            "Original_CR": u_main['Original_CR'].values[0],
                                            "Final_CR": u_main['Final_CR'].values[0]
                                        })
                            indiv_df = pd.DataFrame(indiv_global_data)
                        
                            anova_df = pd.DataFrame()
                            if not indiv_df.empty and len(indiv_df['Type'].unique()) >= 2:
                                anova_df = calculate_anova_and_posthoc(indiv_df)
    
                            summary_rows = []
                            for idx, main_f in enumerate(main_factors):
                                m_weight = group_main_weights.iloc[idx] if isinstance(group_main_weights, pd.Series) else group_main_weights[idx]
                                sub_info = sub_results_storage[main_f]
                                for s_idx, sub_f in enumerate(sub_info['factors']):
                                    s_weight = sub_info['weights'].iloc[s_idx] if isinstance(sub_info['weights'], pd.Series) else sub_info['weights'][s_idx]
                                    global_w = m_weight * s_weight
                                    summary_rows.append({
                                        "?€ë¶„ë¥˜": main_f, "?€ë¶„ë¥˜ ê°€ì¤‘ì¹˜": m_weight, "ì¤‘ë¶„ë¥?: sub_f, "ì¤‘ë¶„ë¥?ê°€ì¤‘ì¹˜": s_weight,
                                        "Global Weight": global_w, 
                                        "CR(?€ë¶„ë¥˜)": main_grp_cr, 
                                        "CI(?€ë¶„ë¥˜)": main_grp_ci,
                                        "CR(ì¤‘ë¶„ë¥?": sub_info['group_cr'],
                                        "CI(ì¤‘ë¶„ë¥?": sub_info['group_ci']
                                    })
                        
                            final_df = pd.DataFrame(summary_rows)
                            final_df['Global Rank'] = final_df['Global Weight'].round(3).rank(ascending=False, method='min').astype(int)
                            cols_order = ["?€ë¶„ë¥˜", "?€ë¶„ë¥˜ ê°€ì¤‘ì¹˜", "ì¤‘ë¶„ë¥?, "ì¤‘ë¶„ë¥?ê°€ì¤‘ì¹˜", "Global Weight", "Global Rank", "CR(?€ë¶„ë¥˜)", "CI(?€ë¶„ë¥˜)", "CR(ì¤‘ë¶„ë¥?", "CI(ì¤‘ë¶„ë¥?"]
                            final_df = final_df[cols_order]
    
                            unique_groups = sorted(main_results_df['Type'].astype(str).unique())
                            group_analysis_results = {}
                            group_full_dfs = {} 
                        
                            for grp in unique_groups:
                                grp_main_df = main_results_df[main_results_df['Type'].astype(str) == grp]
                                if grp_main_df.empty: continue
                                g_main_mats = np.stack(grp_main_df['Matrix_Object'].values)
                                g_main_mat_obj = np.mean(g_main_mats, axis=0) if mean_method == 'arithmetic' else gmean(g_main_mats, axis=0)
                                g_main_cr, g_main_ci, _not_used_lambda = calculate_consistency(g_main_mat_obj, method=mean_method)
                            
                                if ahp_method == 'fuzzy':
                                    mw_vals_grp, _unused_Si = fuzzy_ahp_analysis(g_main_mat_obj)
                                    g_main_w = pd.Series(mw_vals_grp, index=main_weight_cols)
                                else:
                                    g_main_w = grp_main_df[main_weight_cols].mean(axis=0) if mean_method == 'arithmetic' else gmean(grp_main_df[main_weight_cols].values, axis=0)
                                    g_main_w = g_main_w / g_main_w.sum()
                            
                                grp_rows = []
                                for idx, main_f in enumerate(main_factors):
                                    m_w = g_main_w.iloc[idx] if isinstance(g_main_w, pd.Series) else g_main_w[idx]
                                    full_sub_df = sub_results_storage[main_f]['df']
                                    grp_sub_df = full_sub_df[full_sub_df['Type'].astype(str) == grp]
                                    sub_facts = sub_results_storage[main_f]['factors']
                                    if grp_sub_df.empty: continue
                                    s_w_cols = [f"Weight_{f}" for f in sub_facts]
                                    g_sub_mats = np.stack(grp_sub_df['Matrix_Object'].values)
                                    g_sub_mat_obj = np.mean(g_sub_mats, axis=0) if mean_method == 'arithmetic' else gmean(g_sub_mats, axis=0)
                                    g_sub_cr, g_sub_ci, _not_used_lambda = calculate_consistency(g_sub_mat_obj, method=mean_method)
                                
                                    if ahp_method == 'fuzzy':
                                        sw_vals_grp, _unused_Si = fuzzy_ahp_analysis(g_sub_mat_obj)
                                        g_sub_w = pd.Series(sw_vals_grp, index=s_w_cols)
                                    else:
                                        g_sub_w = grp_sub_df[s_w_cols].mean(axis=0) if mean_method == 'arithmetic' else gmean(grp_sub_df[s_w_cols].values, axis=0)
                                        g_sub_w = g_sub_w / g_sub_w.sum()
                                    
                                    for s_idx, sf in enumerate(sub_facts):
                                        s_w_val = g_sub_w.iloc[s_idx] if isinstance(g_sub_w, pd.Series) else g_sub_w[s_idx]
                                        grp_rows.append({
                                            "?€ë¶„ë¥˜": main_f, "?€ë¶„ë¥˜ ê°€ì¤‘ì¹˜": m_w, "ì¤‘ë¶„ë¥?: sf, "ì¤‘ë¶„ë¥?ê°€ì¤‘ì¹˜": s_w_val,
                                            "Global Weight": m_w * s_w_val, 
                                            "CR(?€ë¶„ë¥˜)": g_main_cr, 
                                            "CI(?€ë¶„ë¥˜)": g_main_ci,
                                            "CR(ì¤‘ë¶„ë¥?": g_sub_cr, 
                                            "CI(ì¤‘ë¶„ë¥?": g_sub_ci
                                        })
                                g_df = pd.DataFrame(grp_rows)
                                if not g_df.empty:
                                    g_df['Global Rank'] = g_df['Global Weight'].round(3).rank(ascending=False, method='min').astype(int)
                                    group_full_dfs[grp] = g_df[cols_order]
                                    group_analysis_results[grp] = group_full_dfs[grp][['?€ë¶„ë¥˜', 'ì¤‘ë¶„ë¥?, 'Global Weight']]
    
                            comparison_df = final_df[['?€ë¶„ë¥˜', 'ì¤‘ë¶„ë¥?, 'Global Weight']].copy()
                            comparison_df.rename(columns={'Global Weight': 'ì¢…í•©?‰ê· (Overall)'}, inplace=True)
                            for grp, df_res in group_analysis_results.items():
                                temp_df = df_res.rename(columns={'Global Weight': grp})
                                comparison_df = comparison_df.merge(temp_df, on=['?€ë¶„ë¥˜', 'ì¤‘ë¶„ë¥?], how='left')
    
                            output_res = io.BytesIO()
                            with pd.ExcelWriter(output_res, engine='xlsxwriter') as writer:
                                workbook = writer.book
                                formats = {
                                    'header': workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'bg_color': '#000000', 'font_color': '#FFFFFF', 'border': 1}),
                                    'merge': workbook.add_format({'align': 'center', 'valign': 'vcenter', 'border': 1}),
                                    'body': workbook.add_format({'align': 'center', 'valign': 'vcenter', 'border': 1}),
                                    'num': workbook.add_format({'align': 'center', 'valign': 'vcenter', 'border': 1, 'num_format': '0.000'}),
                                    'sum_row': workbook.add_format({'bold': True, 'bg_color': '#D3D3D3', 'align': 'center', 'valign': 'vcenter', 'border': 1}),
                                    'sum_val': workbook.add_format({'num_format': '0', 'bg_color': '#D3D3D3', 'border': 1, 'align':'center'}),
                                    'num_sum': workbook.add_format({'num_format': '0.000', 'bg_color': '#D3D3D3', 'border': 1, 'align':'center'}),
                                    'yellow': workbook.add_format({'bg_color': 'yellow', 'border': 1, 'align': 'center', 'num_format': '0.000'})
                                }
                                border_fmt = workbook.add_format({'border': 1})
                                fmt_float_no_border = workbook.add_format({'num_format': '0.000', 'align': 'center', 'valign': 'vcenter', 'border': 1})
                                fmt_diagonal = workbook.add_format({'num_format': '0', 'align': 'center', 'valign': 'vcenter', 'bg_color': '#E7E6E6', 'border': 1})
    
                                total_excluded_df = pd.concat(total_excl_df_list, ignore_index=True)
                                sheet_name_comp = _('ì¢…í•©ë¶„ì„', 'Comprehensive Analysis')
                                current_row_ws = write_custom_ahp_table(writer, sheet_name_comp, final_df, _("1) ?„ì²´_ì¢…í•©ê²°ê³¼", "1) Overall Aggregated Results"), 1, formats, excluded_df=total_excluded_df)
                                for grp in unique_groups:
                                    if grp in group_full_dfs:
                                        current_row_ws = write_custom_ahp_table(writer, sheet_name_comp, group_full_dfs[grp], _(f"??[ê·¸ë£¹: {grp}] ë¶„ì„ ê²°ê³¼", f"??[Group: {grp}] Analysis Results"), current_row_ws, formats)
    
                                if len(unique_groups) >= 1:
                                    ws_comp = workbook.add_worksheet('Group_Comparison')
                                    writer.sheets['Group_Comparison'] = ws_comp
                                    s_row_cp = 1
                                    ws_comp.write_string(s_row_cp, 0, _("ê·¸ë£¹ ê°?ë¹„êµ(?¼ì›ë°°ì¹˜ ë¶„ì‚°ë¶„ì„: ANOVA)", "Group Comparison (One-way ANOVA)"), workbook.add_format({'bold': True, 'font_size': 12}))
                                    s_row_cp += 1
                                
                                    if not anova_df.empty:
                                        anova_for_merge = anova_df.rename(columns={'?”ì¸': 'ì¤‘ë¶„ë¥?})
                                        integrated_df = comparison_df.merge(anova_for_merge, on='ì¤‘ë¶„ë¥?, how='left')
                                    else:
                                        integrated_df = comparison_df
                                
                                    # English renaming logic for columns & significance
                                    if st.session_state.get('lang', 'ko') == 'en':
                                        rename_dict = {
                                            '?€ë¶„ë¥˜': 'Main Criteria',
                                            'ì¤‘ë¶„ë¥?: 'Sub-Criteria',
                                            'ì¢…í•©?‰ê· (Overall)': 'Overall',
                                            'F-ê°?: 'F-Value',
                                            'P-Value': 'P-Value',
                                            '? ì˜??: 'Significance',
                                            '?¬í›„ê²€??Tukey HSD)': 'Post-hoc (Tukey HSD)'
                                        }
                                        integrated_df_excel = integrated_df.copy()
                                        integrated_df_excel.rename(columns=rename_dict, inplace=True)
                                        if 'Significance' in integrated_df_excel.columns:
                                            integrated_df_excel['Significance'] = integrated_df_excel['Significance'].replace({
                                                '? ì˜??: 'Significant',
                                                '? ì˜?˜ì? ?ŠìŒ': 'Not Significant'
                                            })
                                        if 'Post-hoc (Tukey HSD)' in integrated_df_excel.columns:
                                            integrated_df_excel['Post-hoc (Tukey HSD)'] = integrated_df_excel['Post-hoc (Tukey HSD)'].replace({
                                                'ì§‘ë‹¨ ê°?êµ¬ì²´??ì°¨ì´ ë°œê²¬ ëª»í•¨': 'No specific difference found',
                                                'ê³„ì‚° ?¤ë¥˜': 'Calculation Error'
                                            })
                                            integrated_df_excel['Post-hoc (Tukey HSD)'] = integrated_df_excel['Post-hoc (Tukey HSD)'].apply(
                                                lambda x: x.replace(" ì°¨ì´ ?ˆìŒ", " Diff Exists") if isinstance(x, str) else x
                                            )
                                    else:
                                        integrated_df_excel = integrated_df
    
                                    integrated_df_excel.to_excel(writer, sheet_name='Group_Comparison', startrow=s_row_cp, index=False)
                                    add_borders_to_data(ws_comp, s_row_cp, 0, integrated_df_excel, border_fmt)
                                
                                    num_format_3 = workbook.add_format({'num_format': '0.000', 'border': 1, 'align': 'center'})
                                    for r in range(len(integrated_df_excel)):
                                        for c in range(1, len(integrated_df_excel.columns)):
                                            val = integrated_df_excel.iloc[r, c]
                                            if pd.notnull(val) and isinstance(val, (int, float)):
                                                ws_comp.write_number(s_row_cp + 1 + r, c, val, num_format_3)
                                            elif pd.notnull(val):
                                                ws_comp.write(s_row_cp + 1 + r, c, val, border_fmt)
    
                                    guide_start_row = s_row_cp + len(integrated_df_excel) + 3
                                    bold_fmt = workbook.add_format({'bold': True, 'font_size': 11, 'valign': 'vcenter', 'align': 'left', 'bg_color': '#F2F2F2', 'border': 1})
                                    text_fmt = workbook.add_format({'font_size': 10, 'text_wrap': True, 'valign': 'top', 'align': 'left', 'border': 1})
                                    ws_comp.set_column('A:G', 20) 
                                
                                    comp_title = _("??ê·¸ë£¹ ê°?ì¤‘ìš”?„ì˜ ì°¨ì´ê°€ ?ˆì?ë§??µê³„?ìœ¼ë¡?? ì˜?˜ì? ?Šê²Œ ?˜í??˜ëŠ” ?´ìœ ",
                                                   "??Reasons why group differences are not statistically significant despite variation in priorities")
                                    ws_comp.merge_range(guide_start_row, 0, guide_start_row, 6, comp_title, bold_fmt)
    
                                    guide_content_ko = [
                                        ("1. ê·¸ë£¹ ???¸ì°¨(ë¶„ì‚°)ê°€ ?ˆë¬´ ??ê²½ìš°", "ANOVA??'ê·¸ë£¹ ê°„ì˜ ì°¨ì´'?€ 'ê·¸ë£¹ ?´ì˜ ì°¨ì´'ë¥?ë¹„êµ?©ë‹ˆ??\n\n???ë¦¬: ê·¸ë£¹ ê°??‰ê·  ì°¨ì´ê°€ ?¬ë”?¼ë„, ê°?ê·¸ë£¹ ?´ë? ?°ì´?°ë“¤???œë¡œ ?¤ì­‰? ì­‰(ë¶„ì‚°?????˜ë‹¤ë©??µê³„?ìœ¼ë¡œëŠ” '??ì°¨ì´ê°€ ?°ì—°??ë°œìƒ?ˆì„ ê°€?¥ì„±???’ë‹¤'ê³??ë‹¨?©ë‹ˆ??"),
                                        ("2. ?œë³¸ ?¬ê¸°(Sample Size)??ë¶€ì¡?, "?µê³„??? ì˜?±ì? ?œë³¸???˜ì— ë§¤ìš° ë¯¼ê°?©ë‹ˆ??\n\n???„ìƒ: ê°?ê·¸ë£¹???°ì´??ê°œìˆ˜(?œë³¸??ê°€ ?ˆë¬´ ?ë‹¤ë©??µê³„????Power)??ë¶€ì¡±í•˜??? ì˜ë¯¸í•œ ì°¨ì´ë¥?ì°¾ì•„?´ì? ëª»í•©?ˆë‹¤."),
                                        ("3. ?°ì´?°ì˜ ?¨ìœ„(Scale)?€ ë³€?™ì„±", "?œì— ?˜í????˜ì¹˜?¤ì´ ?€ë¶€ë¶?ë§¤ìš° ?‘ì? ?Œìˆ˜???¨ìœ„?…ë‹ˆ?? ?¤ì œ ê³„ì‚° ê³¼ì •?ì„œ ?œì??¤ì°¨ ë²”ìœ„ ?´ì— ?ˆë‹¤ë©??µê³„?ìœ¼ë¡œëŠ” ì¸¡ì • ?¤ì°¨ ë²”ìœ„ ?´ì˜ ?”ë“¤ë¦¼ìœ¼ë¡?ê°„ì£¼?©ë‹ˆ??")
                                    ]
                                
                                    guide_content_en = [
                                        ("1. Within-Group Variance is Too Large", "ANOVA compares variance between groups against variance within groups.\n\n??Principle: Even if the mean difference between groups is large, if individual responses within each group are highly scattered (large variance), statistics will determine that the difference is likely due to chance."),
                                        ("2. Insufficient Sample Size", "Statistical significance is highly sensitive to the number of samples.\n\n??Phenomenon: If the number of data points (sample size) in each group is too small, statistical power is insufficient to detect significant differences."),
                                        ("3. Data Scale and Volatility", "The values in the table are mostly very small decimals. If they fall within the range of standard error, they are considered as minor fluctuations within the measurement error range.")
                                    ]
                                
                                    guide_content = guide_content_en if st.session_state.get('lang', 'ko') == 'en' else guide_content_ko
    
                                    current_row_comp = guide_start_row + 1
                                    for title, body in guide_content:
                                        ws_comp.set_row(current_row_comp, 25)
                                        ws_comp.merge_range(current_row_comp, 0, current_row_comp, 6, title, bold_fmt)
                                        ws_comp.set_row(current_row_comp + 1, 80)
                                        ws_comp.merge_range(current_row_comp + 1, 0, current_row_comp + 1, 6, body, text_fmt)
                                        current_row_comp += 2
    
                                def write_detailed_sheet_ws(sheet_name, matrix_df, detail_df, matrix_title, row_labels, group_matrices=None, sheet_excl_count=0):
                                    ws = workbook.add_worksheet(sheet_name)
                                    writer.sheets[sheet_name] = ws
                                    s_row_det = 0
                                
                                    excl_label = _(f"ë¶„ì„ ?œì™¸ ?¬ë??? {sheet_excl_count}ê±?, f"Excluded cases: {sheet_excl_count}")
                                    ws.write(s_row_det, 0, excl_label, workbook.add_format({'bold': True, 'font_color': 'red'}))
                                    s_row_det += 1
                                
                                    ws.write_string(s_row_det, 0, matrix_title)
                                    s_row_det += 1
                                    m_df_obj = pd.DataFrame(matrix_df, index=row_labels, columns=row_labels)
                                    m_df_obj.to_excel(writer, sheet_name=sheet_name, startrow=s_row_det)
                                    add_borders_to_data(ws, s_row_det, 0, m_df_obj, border_fmt, has_header=True, has_index=True)
                                    for r in range(len(matrix_df)):
                                        for c in range(len(matrix_df)):
                                            val = 1 if r==c else matrix_df[r][c]
                                            ws.write(s_row_det+r+1, c+1, val, border_fmt if r!=c else fmt_diagonal)
                                            if r!=c: ws.write(s_row_det+r+1, c+1, val, fmt_float_no_border)
                                
                                    # [? ê·œ ì¶”ê?] ?„ì²´ ì¢…í•© ?‰ë ¬ ?¤ë¥¸ìª½ì— ?„ì²´ CR, CI ê°??œì‹œ
                                    n_dim = len(matrix_df)
                                    cr_val, ci_val, _unused_lambda = calculate_consistency(matrix_df, mean_method)
                                
                                    ci_cr_header_fmt = workbook.add_format({
                                        'bold': True, 'align': 'center', 'valign': 'vcenter',
                                        'bg_color': '#4F81BD', 'font_color': '#FFFFFF', 'border': 1,
                                        'font_name': 'NanumGothic'
                                    })
                                    ci_cr_label_fmt = workbook.add_format({
                                        'bold': True, 'align': 'center', 'valign': 'vcenter',
                                        'bg_color': '#D9E1F2', 'border': 1,
                                        'font_name': 'NanumGothic'
                                    })
                                    ci_cr_val_fmt = workbook.add_format({
                                        'align': 'center', 'valign': 'vcenter', 'border': 1,
                                        'num_format': '0.000',
                                        'font_name': 'NanumGothic'
                                    })
                                    if cr_val > 0.1:
                                        ci_cr_val_fmt = workbook.add_format({
                                            'align': 'center', 'valign': 'vcenter', 'border': 1,
                                            'num_format': '0.000',
                                            'bg_color': '#FFC7CE', 'font_color': '#9C0006',
                                            'font_name': 'NanumGothic'
                                        })
                                
                                    ws.set_column(n_dim + 2, n_dim + 2, 12)
                                    ws.set_column(n_dim + 3, n_dim + 3, 12)
                                
                                    ws.merge_range(s_row_det, n_dim + 2, s_row_det, n_dim + 3, _("?„ì²´ ?¼ê???ì§€??, "Overall Consistency Indicators"), ci_cr_header_fmt)
                                    ws.write(s_row_det + 1, n_dim + 2, _("?„ì²´ CI", "Overall CI"), ci_cr_label_fmt)
                                    ws.write(s_row_det + 1, n_dim + 3, ci_val, ci_cr_val_fmt)
                                    ws.write(s_row_det + 2, n_dim + 2, _("?„ì²´ CR", "Overall CR"), ci_cr_label_fmt)
                                    ws.write(s_row_det + 2, n_dim + 3, cr_val, ci_cr_val_fmt)
                                
                                    s_row_det += len(matrix_df) + 3
                                
                                    if group_matrices:
                                        for g_name, g_mat in group_matrices.items():
                                            ws.write_string(s_row_det, 0, _(f"] ê·¸ë£¹ ì¢…í•© ?‰ë ¬: {g_name}", f"] Group Combined Matrix: {g_name}"))
                                            s_row_det += 1
                                            gm_df_obj = pd.DataFrame(g_mat, index=row_labels, columns=row_labels)
                                            gm_df_obj.to_excel(writer, sheet_name=sheet_name, startrow=s_row_det)
                                            add_borders_to_data(ws, s_row_det, 0, gm_df_obj, border_fmt, has_header=True, has_index=True)
                                            for r in range(len(g_mat)):
                                                for c in range(len(g_mat)):
                                                    val = 1 if r==c else g_mat[r][c]
                                                    ws.write(s_row_det+r+1, c+1, val, border_fmt if r!=c else fmt_diagonal)
                                                    if r!=c: ws.write(s_row_det+r+1, c+1, val, fmt_float_no_border)
                                        
                                            # [? ê·œ ì¶”ê?] ê·¸ë£¹ ì¢…í•© ?‰ë ¬ ?¤ë¥¸ìª½ì— ê·¸ë£¹ CR, CI ê°??œì‹œ
                                            g_cr_val, g_ci_val, _unused_lambda = calculate_consistency(g_mat, mean_method)
                                            g_ci_cr_val_fmt = workbook.add_format({
                                                'align': 'center', 'valign': 'vcenter', 'border': 1,
                                                'num_format': '0.000',
                                                'font_name': 'NanumGothic'
                                            })
                                            if g_cr_val > 0.1:
                                                g_ci_cr_val_fmt = workbook.add_format({
                                                    'align': 'center', 'valign': 'vcenter', 'border': 1,
                                                    'num_format': '0.000',
                                                    'bg_color': '#FFC7CE', 'font_color': '#9C0006',
                                                    'font_name': 'NanumGothic'
                                                })
                                        
                                            ws.merge_range(s_row_det, n_dim + 2, s_row_det, n_dim + 3, _("ê·¸ë£¹ ?¼ê???ì§€??, "Group Consistency Indicators"), ci_cr_header_fmt)
                                            ws.write(s_row_det + 1, n_dim + 2, _("ê·¸ë£¹ CI", "Group CI"), ci_cr_label_fmt)
                                            ws.write(s_row_det + 1, n_dim + 3, g_ci_val, g_ci_cr_val_fmt)
                                            ws.write(s_row_det + 2, n_dim + 2, _("ê·¸ë£¹ CR", "Group CR"), ci_cr_label_fmt)
                                            ws.write(s_row_det + 2, n_dim + 3, g_cr_val, g_ci_cr_val_fmt)
                                        
                                            s_row_det += len(g_mat) + 3
                                
                                    detail_df.to_excel(writer, sheet_name=sheet_name, startrow=s_row_det, index=False)
                                    for c_idx, col_val in enumerate(detail_df.columns):
                                        ws.write(s_row_det, c_idx, col_val, formats['header'])
                                
                                    for r_idx in range(len(detail_df)):
                                        row_pos = s_row_det + 1 + r_idx
                                        for c_idx, col_name in enumerate(detail_df.columns):
                                            val = detail_df.iloc[r_idx, c_idx]
                                            current_fmt = border_fmt
                                            if col_name in ['Original_CR', 'Final_CR'] and isinstance(val, (float, int)) and val > 0.1:
                                                current_fmt = formats['yellow']
                                            elif isinstance(val, (float, np.float64)):
                                                current_fmt = formats['num']
                                            else:
                                                current_fmt = formats['body']
                                        
                                            if pd.isnull(val):
                                                ws.write_blank(row_pos, c_idx, "", current_fmt)
                                            else:
                                                ws.write(row_pos, c_idx, val, current_fmt)
    
                                main_group_mats = {}
                                for grp in unique_groups:
                                    g_df_m = main_results_df[main_results_df['Type'].astype(str) == grp]
                                    if not g_df_m.empty:
                                        mats = np.stack(g_df_m['Matrix_Object'].values)
                                        main_group_mats[grp] = np.mean(mats, axis=0) if mean_method == 'arithmetic' else gmean(mats, axis=0)
    
                                out_main = main_results_df.drop(columns=['Matrix_Object', 'Orig_Matrix_Object'], errors='ignore')
                                write_detailed_sheet_ws('(?€ë¶„ë¥˜) Main', main_group_matrix, out_main, _("[?€ë¶„ë¥˜ ?‰ê? ì¢…í•© ?‰ë ¬]", "[Main Criteria Combined Matrix]"), main_factors, group_matrices=main_group_mats, sheet_excl_count=main_excluded)
                                for mf, info in sub_results_storage.items():
                                    safe_name = f"(ì¤‘ë¶„ë¥? {mf}"[:31]
                                    sub_grp_mats = {}
                                    for grp in unique_groups:
                                        g_sub_df = info['df'][info['df']['Type'].astype(str) == grp]
                                        if not g_sub_df.empty:
                                            mats = np.stack(g_sub_df['Matrix_Object'].values)
                                            sub_grp_mats[grp] = np.mean(mats, axis=0) if mean_method == 'arithmetic' else gmean(mats, axis=0)
                                    out_sub = info['df'].drop(columns=['Matrix_Object', 'Orig_Matrix_Object'], errors='ignore')
                                
                                    sub_excl_val = 0
                                    for df_ex in total_excl_df_list:
                                        if 'Sheet' in df_ex.columns and not df_ex.empty:
                                             if mf in df_ex['Sheet'].unique():
                                                 sub_excl_val = len(df_ex[df_ex['Sheet'] == mf])
                                             
                                    title_ko = f"[ì¤‘ë¶„ë¥??‰ê? ì¢…í•© ?‰ë ¬]  ???ìœ„ ê³„ì¸µ: ?€ë¶„ë¥˜ [{mf}]"
                                    title_en = f"[Sub-Criteria Combined Matrix]  ??Parent: Main [{mf}]"
                                    write_detailed_sheet_ws(safe_name, info['group_matrix'], out_sub, _(title_ko, title_en), info['factors'], group_matrices=sub_grp_mats, sheet_excl_count=sub_excl_val)
    
                                is_english = (st.session_state.get('lang', 'ko') == 'en')
                                theory_ws = workbook.add_worksheet("Consistency_Theory")
                                theory_title_fmt = workbook.add_format({'bold': True, 'font_size': 14, 'font_name': 'NanumGothic'})
                                theory_body_fmt = workbook.add_format({'text_wrap': True, 'valign': 'top', 'font_name': 'NanumGothic'})
                                if is_english:
                                    theory_text = [
                                        ["AHP Consistency Calibration Principle & Academic Foundation from a Decision-Making Perspective"],
                                        [""],
                                        ["1. Introduction: The Issue of Consistency in the Analytic Hierarchy Process (AHP)"],
                                        ["The Analytic Hierarchy Process, proposed by Saaty (1980), is a multi-criteria decision-making tool that quantifies human subjective judgment. When inconsistent judgments occur, they are mathematically corrected to ensure the reliability of the analysis."],
                                        [""],
                                        ["2. Calibration Algorithm: Iterative Convergence Adjusting Method"],
                                        [f"The original matrix A and the ideal matrix W are linearly combined according to the set learning rate (learning rate Î±={learning_rate}): A_new = (1-Î±)A + Î±W."],
                                        [""],
                                        ["3. Academic Foundation & Effects"],
                                        ["Adjustment using a weighted average of the original matrix and the consistent matrix preserves the decision maker's original preferences as much as possible while improving mathematical consistency."]
                                    ]
                                else:
                                    theory_text = [
                                        ["?˜ì‚¬ê²°ì •ë¡ ì  ê´€?ì—?œì˜ AHP ?¼ê???ë³´ì • ?ë¦¬ ë°??™ìˆ ??ê·¼ê±°"],
                                        [""],
                                        ["1. ?œë¡ : ê³„ì¸µë¶„ì„ê³¼ì •(AHP)???¼ê???ë¬¸ì œ"],
                                        ["Saaty(1980)???˜í•´ ?œì•ˆ??ê³„ì¸µë¶„ì„ê³¼ì •?€ ?¸ê°„??ì£¼ê????ë‹¨???•ëŸ‰?”í•˜???¤ê¸°ì¤€ ?˜ì‚¬ê²°ì • ?„êµ¬?´ë‹¤. ë¹„ì¼ê´€???ë‹¨??ë°œìƒ??ê²½ìš° ?˜í•™?ìœ¼ë¡?êµì •?˜ì—¬ ë¶„ì„??? ë¢°?±ì„ ?•ë³´?œë‹¤."],
                                        [""],
                                        ["2. ë³´ì • ?Œê³ ë¦¬ì¦˜: ë°˜ë³µ ?˜ë ´ ì¡°ì •ë²?],
                                        [f"?ë³¸ ?‰ë ¬ A?€ ?´ìƒ???‰ë ¬ Wë¥??¤ì •???™ìŠµë¥?Î±={learning_rate})???°ë¼ ? í˜• ê²°í•©?œë‹¤: A_new = (1-Î±)A + Î±W."],
                                        [""],
                                        ["3. ?™ìˆ ??ê·¼ê±° ë°??¨ê³¼"],
                                        ["?ë³¸ ?‰ë ¬ê³??¼ê? ?‰ë ¬??ê°€ì¤??‰ê· ???´ìš©??ì¡°ì •?€ ?˜ì‚¬ê²°ì •?ì˜ ?ë˜ ? í˜¸ ê²½í–¥?±ì„ ìµœë???ë³´ì¡´?˜ë©´???˜í•™???¼ê??±ì„ ?¥ìƒ?œí‚¨??"]
                                    ]
                                theory_ws.set_column('A:A', 100)
                                for r_idx, row_content in enumerate(theory_text):
                                    fmt = theory_title_fmt if r_idx == 0 else theory_body_fmt
                                    theory_ws.write(r_idx, 0, row_content[0], fmt)
    
                                if is_single_sheet:
                                    guide_ws = workbook.add_worksheet("Single_Sheet_Guide")
                                    guide_title_fmt = workbook.add_format({'bold': True, 'font_size': 14, 'font_name': 'NanumGothic', 'bg_color': '#D9E1F2', 'border': 1, 'align': 'center', 'valign': 'vcenter'})
                                    guide_section_fmt = workbook.add_format({'bold': True, 'font_size': 11, 'font_name': 'NanumGothic', 'bg_color': '#F2F2F2', 'border': 1, 'valign': 'vcenter', 'align': 'center'})
                                    guide_body_fmt = workbook.add_format({'text_wrap': True, 'valign': 'top', 'font_name': 'NanumGothic', 'border': 1})
                                
                                    guide_ws.set_column('A:A', 25)
                                    guide_ws.set_column('B:B', 75)
                                
                                    # Merge title row
                                    guide_title = _("1?¨ê³„ AHP ë¶„ì„ ê²°ê³¼ ?´ì„ ë°?ì£¼ì˜?¬í•­", "Step 1 AHP Analysis Result Interpretation and Guidelines")
                                    guide_ws.merge_range('A1:B1', guide_title, guide_title_fmt)
                                    guide_ws.set_row(0, 35)
                                
                                    if is_english:
                                        guide_data = [
                                            ("Classification", "Detailed Content"),
                                            ("1. Analysis Overview", "This report is a single-level AHP analysis result comparing only the main criteria (Step 1) evaluation criteria without sub-criteria."),
                                            ("2. Result Interpretation Method", "Since the sub-weights are fixed at 1.0, the 'Main Criteria Weight' and the 'Global Weight' are calculated with the same values. Therefore, you can interpret the 'Global Weight' as the final importance of each item."),
                                            ("3. Internal Virtual Operation Guide", "To maintain consistency of the 2-level operation of the AHP analysis system, the system internally auto-generated and computed dummy detailed items with a weight of 1.0 under the main criteria items. Due to this, the 'Result_[Main Criteria Name]' sheet exists in the results download file as a 1x1 matrix, which is a normal virtual operation result."),
                                            ("4. Consistency Ratio (CR) Warnings", "The provided consistency ratio represents only the CR of the pairwise comparison of the main criteria. Since there are no sub-criteria, the 'Sub-Criteria Consistency Ratio (CR)' is unconditionally marked as 0.000, which is not an error."),
                                            ("5. Academic/Report Writing Tip", "When utilizing this in academic research or reports, please explicitly state that 'pairwise comparison analysis was performed under a single-level (Step 1) hierarchical structure.'")
                                        ]
                                    else:
                                        guide_data = [
                                            ("ë¶„ë¥˜", "?ì„¸ ?´ìš©"),
                                            ("1. ë¶„ì„ ê°œìš”", "ë³?ë³´ê³ ?œëŠ” ?˜ìœ„ ?”ì†Œ ?†ì´ ?€ë¶„ë¥˜(1?¨ê³„) ?‰ê? ê¸°ì?ë§Œì„ ë¹„êµ???¨ì¼ ê³„ì¸µ AHP ë¶„ì„ ê²°ê³¼?…ë‹ˆ??"),
                                            ("2. ê²°ê³¼ ?´ì„ ë°©ë²•", "?˜ìœ„ ê°€ì¤‘ì¹˜ê°€ 1.0?¼ë¡œ ê³ ì •?˜ì–´ '?€ë¶„ë¥˜ ê°€ì¤‘ì¹˜'?€ 'Global Weight(ì¢…í•© ê°€ì¤‘ì¹˜)'ê°€ ?™ì¼???˜ì¹˜ë¡??°ì¶œ?˜ì—ˆ?µë‹ˆ?? ?°ë¼??'Global Weight'ë¥?ê°???ª©??ìµœì¢… ì¤‘ìš”?„ë¡œ ?´ì„?˜ì‹œë©??©ë‹ˆ??"),
                                            ("3. ?´ë? ê°€???°ì‚° ?ˆë‚´", "AHP ë¶„ì„ ?œìŠ¤?œì˜ 2?¨ê³„ ?°ì‚° ?¼ê???? ì?ë¥??„í•´, ?œìŠ¤???´ë??ìœ¼ë¡??€ë¶„ë¥˜ ??ª© ?˜ìœ„??ê°€ì¤‘ì¹˜ 1.0??ê°€ì§€???”ë? ?¸ë? ??ª©???ë™ ?ì„±?˜ì—¬ ?°ì‚°?˜ì??µë‹ˆ?? ?´ë¡œ ?¸í•´ ê²°ê³¼ ?¤ìš´ë¡œë“œ ?Œì¼??'Result_[?€ë¶„ë¥˜ëª?' ?œíŠ¸ê°€ 1x1 ?‰ë ¬ë¡?ì¡´ì¬?˜ì?ë§??´ëŠ” ?•ìƒ?ì¸ ê°€???°ì‚° ê²°ê³¼?…ë‹ˆ??"),
                                            ("4. ?¼ê???ë¹„ìœ¨(CR) ì£¼ì˜?¬í•­", "?œê³µ???¼ê???ë¹„ìœ¨?€ ?€ë¶„ë¥˜ ?ë?ë¹„êµ???¼ê???ë¹„ìœ¨(CR)ë§Œì„ ?˜í??…ë‹ˆ?? ?˜ìœ„ ?”ì†Œê°€ ì¡´ì¬?˜ì? ?Šìœ¼ë¯€ë¡?'ì¤‘ë¶„ë¥??¼ê???ë¹„ìœ¨(CR)'?€ ë¬´ì¡°ê±?0.000?¼ë¡œ ?œê¸°?˜ë©° ?´ëŠ” ?¤ë¥˜ê°€ ?„ë‹™?ˆë‹¤."),
                                            ("5. ?™ìˆ /ë³´ê³ ??ê¸°ì¬ ??, "?™ìˆ  ?°êµ¬??ë³´ê³ ?œì— ?œìš© ??'?¨ì¼ ê³„ì¸µ(1?¨ê³„) ê³„ì¸µ êµ¬ì¡° ?˜ì—???ë?ë¹„êµ ë¶„ì„???˜í–‰?˜ì???ê³?ëª…ì‹œ?ìœ¼ë¡?ê¸°ì¬?˜ì‹œê¸?ë°”ë?ˆë‹¤.")
                                        ]
                                
                                    for r_idx, (section, content) in enumerate(guide_data, start=1):
                                        if r_idx == 1:
                                            # Header row
                                            guide_ws.write(r_idx, 0, section, workbook.add_format({'bold': True, 'align': 'center', 'bg_color': '#A6A6A6', 'border': 1}))
                                            guide_ws.write(r_idx, 1, content, workbook.add_format({'bold': True, 'align': 'center', 'bg_color': '#A6A6A6', 'border': 1}))
                                        else:
                                            guide_ws.write(r_idx, 0, section, guide_section_fmt)
                                            guide_ws.write(r_idx, 1, content, guide_body_fmt)
                                        guide_ws.set_row(r_idx, 60 if r_idx > 1 else 20)
    
                                if ahp_method == 'fuzzy':
                                    # 1. Fuzzy AHP ê°€ì¤‘ì¹˜ ë¶„ì„ ê²°ê³¼ ?œíŠ¸ ì¶”ê?
                                    ws_fuzzy = workbook.add_worksheet('Fuzzy_AHP_Results')
                                    writer.sheets['Fuzzy_AHP_Results'] = ws_fuzzy
                                    ws_fuzzy.set_column('A:A', 25)
                                    ws_fuzzy.set_column('B:G', 20)
                                
                                    fuzzy_header_fmt = workbook.add_format({
                                        'bold': True, 'align': 'center', 'valign': 'vcenter',
                                        'bg_color': '#1F4E78', 'font_color': '#FFFFFF', 'border': 1,
                                        'font_name': 'NanumGothic'
                                    })
                                    title_fmt = workbook.add_format({
                                        'bold': True, 'font_size': 12, 'font_name': 'NanumGothic'
                                    })
                                
                                    row_idx = 1
                                
                                    ws_fuzzy.write_string(row_idx, 0, _("???€ë¶„ë¥˜ (Main Criteria) ?¼ì? AHP ë¶„ì„ ê²°ê³¼ (?¼ê°?¼ì????ìš©)", "??Main Criteria Fuzzy AHP Results (TFN Applied)"), title_fmt)
                                    row_idx += 1
                                
                                    headers = [
                                        _("êµ¬ë¶„", "Criteria"), 
                                        _("Fuzzy ê°€ì¤‘ì¹˜ (Lower)", "Fuzzy Weight (Lower)"), 
                                        _("Fuzzy ê°€ì¤‘ì¹˜ (Medium)", "Fuzzy Weight (Medium)"), 
                                        _("Fuzzy ê°€ì¤‘ì¹˜ (Upper)", "Fuzzy Weight (Upper)"), 
                                        _("ë¹„í¼ì§€??(Crisp)", "Defuzzified (Crisp)"), 
                                        _("ìµœì¢… ê°€ì¤‘ì¹˜ (Norm)", "Final Weight (Norm)"), 
                                        _("?œìœ„", "Rank")
                                    ]
                                
                                    for c_idx, h in enumerate(headers):
                                        ws_fuzzy.write(row_idx, c_idx, h, fuzzy_header_fmt)
                                    row_idx += 1
                                
                                    main_rows = []
                                    for i, (l, m, u) in enumerate(main_group_Si):
                                        crisp = (l * m * u) ** (1/3)
                                        norm_w = group_main_weights.iloc[i] if isinstance(group_main_weights, pd.Series) else group_main_weights[i]
                                        main_rows.append([main_factors[i], l, m, u, crisp, norm_w])
                                
                                    norm_w_list = [r[5] for r in main_rows]
                                    sorted_weights = sorted(list(set(norm_w_list)), reverse=True)
                                    ranks = [sorted_weights.index(w) + 1 for w in norm_w_list]
                                
                                    for i, r in enumerate(main_rows):
                                        r.append(ranks[i])
                                        ws_fuzzy.write(row_idx, 0, r[0], formats['body'])
                                        for c_idx in range(1, 6):
                                            ws_fuzzy.write_number(row_idx, c_idx, r[c_idx], formats['num'])
                                        ws_fuzzy.write_number(row_idx, 6, r[6], formats['body'])
                                        row_idx += 1
                                    
                                    row_idx += 2
                                
                                    for parent_f, sub_info in sub_results_storage.items():
                                        if sub_info.get('group_Si'):
                                            ws_fuzzy.write_string(row_idx, 0, _(f"???¸ë???ª© [{parent_f}] ?¼ì? AHP ë¶„ì„ ê²°ê³¼ (?¼ê°?¼ì????ìš©)", f"??Sub-Criteria [{parent_f}] Fuzzy AHP Results (TFN Applied)"), title_fmt)
                                            row_idx += 1
                                        
                                            for c_idx, h in enumerate(headers):
                                                ws_fuzzy.write(row_idx, c_idx, h, fuzzy_header_fmt)
                                            row_idx += 1
                                        
                                            sub_factors = sub_info['factors']
                                            sub_group_Si = sub_info['group_Si']
                                            group_sub_w = sub_info['weights']
                                        
                                            sub_rows = []
                                            for i, (l, m, u) in enumerate(sub_group_Si):
                                                crisp = (l * m * u) ** (1/3)
                                                norm_w = group_sub_w.iloc[i] if isinstance(group_sub_w, pd.Series) else group_sub_w[i]
                                                sub_rows.append([sub_factors[i], l, m, u, crisp, norm_w])
                                            
                                            norm_w_list = [r[5] for r in sub_rows]
                                            sorted_weights = sorted(list(set(norm_w_list)), reverse=True)
                                            ranks = [sorted_weights.index(w) + 1 for w in norm_w_list]
                                        
                                            for i, r in enumerate(sub_rows):
                                                r.append(ranks[i])
                                                ws_fuzzy.write(row_idx, 0, r[0], formats['body'])
                                                for c_idx in range(1, 6):
                                                    ws_fuzzy.write_number(row_idx, c_idx, r[c_idx], formats['num'])
                                                ws_fuzzy.write_number(row_idx, 6, r[6], formats['body'])
                                                row_idx += 1
                                        
                                            row_idx += 2
    
                                    # 2. ?¼ê???ë¹„ìœ¨(CR) ë¶„í¬ ë¶„ì„ ê²°ê³¼ ?œíŠ¸ ì¶”ê?
                                    ws_cr = workbook.add_worksheet('CR_Distribution')
                                    writer.sheets['CR_Distribution'] = ws_cr
                                    ws_cr.set_column('A:A', 25)
                                    ws_cr.set_column('B:H', 20)
                                
                                    cr_header_fmt = workbook.add_format({
                                        'bold': True, 'align': 'center', 'valign': 'vcenter',
                                        'bg_color': '#595959', 'font_color': '#FFFFFF', 'border': 1,
                                        'font_name': 'NanumGothic'
                                    })
                                
                                    ws_cr.write_string(1, 0, _("???¼ê???ë¹„ìœ¨(CR) ë¶„ì„ ?”ì•½", "??Consistency Ratio (CR) Analysis Summary"), title_fmt)
                                
                                    cr_headers = [
                                        _("?‰ê? ?œíŠ¸ëª?, "Sheet Name"),
                                        _("?‰ê·  CR", "Mean CR"),
                                        _("ì¤‘ì•™ê°?CR", "Median CR"),
                                        _("ìµœì†Œ CR", "Min CR"),
                                        _("ìµœë? CR", "Max CR"),
                                        _("?µê³¼ ?œë³¸ ??(CR <= 0.1)", "Passed Samples (CR <= 0.1)"),
                                        _("?„ì²´ ?œë³¸ ??, "Total Samples"),
                                        _("?µê³¼??(%)", "Pass Rate (%)")
                                    ]
                                
                                    for c_idx, h in enumerate(cr_headers):
                                        ws_cr.write(2, c_idx, h, cr_header_fmt)
                                    
                                    cr_row_idx = 3
                                
                                    sheets_to_process = [("Main_Criteria", main_results_df)]
                                    for mf, info in sub_results_storage.items():
                                        sheets_to_process.append((mf, info['df']))
                                    
                                    for sheet_name, df_s in sheets_to_process:
                                        if df_s.empty: continue
                                        cr_vals = df_s['Final_CR'].dropna().values
                                        if len(cr_vals) == 0: continue
                                    
                                        mean_cr = np.mean(cr_vals)
                                        median_cr = np.median(cr_vals)
                                        min_cr = np.min(cr_vals)
                                        max_cr = np.max(cr_vals)
                                        total_cnt = len(cr_vals)
                                        pass_cnt = np.sum(cr_vals <= 0.1)
                                        pass_rate = (pass_cnt / total_cnt) * 100
                                    
                                        ws_cr.write(cr_row_idx, 0, sheet_name, formats['body'])
                                        ws_cr.write_number(cr_row_idx, 1, mean_cr, formats['num'])
                                        ws_cr.write_number(cr_row_idx, 2, median_cr, formats['num'])
                                        ws_cr.write_number(cr_row_idx, 3, min_cr, formats['num'])
                                        ws_cr.write_number(cr_row_idx, 4, max_cr, formats['num'])
                                        ws_cr.write_number(cr_row_idx, 5, pass_cnt, formats['body'])
                                        ws_cr.write_number(cr_row_idx, 6, total_cnt, formats['body'])
                                        ws_cr.write_number(cr_row_idx, 7, pass_rate, formats['num'])
                                        cr_row_idx += 1
                                    
                                    cr_row_idx += 2
                                    ws_cr.write_string(cr_row_idx, 0, _("??ê°œë³„ ?‘ë‹µ?ë³„ ?¼ê???ë¹„ìœ¨(CR) ?ì„¸ ?´ì—­", "??Detailed Consistency Ratio (CR) by Respondent"), title_fmt)
                                    cr_row_idx += 1
                                
                                    indiv_headers = [
                                        _("ID (?¤ë¬¸??", "Respondent ID"),
                                        _("ê·¸ë£¹ (Type)", "Group Type"),
                                        _("?‰ê? ?œíŠ¸ëª?, "Sheet Name"),
                                        _("?¼ê???ë¹„ìœ¨ (CR)", "Consistency Ratio (CR)"),
                                        _("?ì • (CR <= 0.1)", "Status (CR <= 0.1)")
                                    ]
                                    for c_idx, h in enumerate(indiv_headers):
                                        ws_cr.write(cr_row_idx, c_idx, h, cr_header_fmt)
                                    cr_row_idx += 1
                                
                                    for idx_row, r in main_results_df.iterrows():
                                        cr_val = r['Final_CR']
                                        status = _("ë§Œì¡± (Pass)", "Pass") if cr_val <= 0.1 else _("ë¶ˆë§Œì¡?(Fail)", "Fail")
                                        ws_cr.write(cr_row_idx, 0, r['ID'], formats['body'])
                                        ws_cr.write(cr_row_idx, 1, r['Type'], formats['body'])
                                        ws_cr.write(cr_row_idx, 2, "Main_Criteria", formats['body'])
                                        ws_cr.write_number(cr_row_idx, 3, cr_val, formats['num'])
                                        ws_cr.write(cr_row_idx, 4, status, formats['body'])
                                        cr_row_idx += 1
                                    
                                    for mf, info in sub_results_storage.items():
                                        for idx_row, r in info['df'].iterrows():
                                            cr_val = r['Final_CR']
                                            status = _("ë§Œì¡± (Pass)", "Pass") if cr_val <= 0.1 else _("ë¶ˆë§Œì¡?(Fail)", "Fail")
                                            ws_cr.write(cr_row_idx, 0, r['ID'], formats['body'])
                                            ws_cr.write(cr_row_idx, 1, r['Type'], formats['body'])
                                            ws_cr.write(cr_row_idx, 2, mf, formats['body'])
                                            ws_cr.write_number(cr_row_idx, 3, cr_val, formats['num'])
                                            ws_cr.write(cr_row_idx, 4, status, formats['body'])
                                            cr_row_idx += 1
    
                        st.success(_("ë¶„ì„???„ë£Œ?˜ì—ˆ?µë‹ˆ??", "Analysis completed successfully."))
                        if st.session_state.user_role == 'official':
                            if data_source == _("?“‚ ?‘ì? ?Œì¼ ì§ì ‘ ?…ë¡œ??, "Upload Excel File") and uploaded_file is not None:
                                save_data = uploaded_file.getvalue()
                                save_filename = f"{filename_base}_Raw.xlsx"
                            else:
                                uploadable_io = io.BytesIO()
                                with pd.ExcelWriter(uploadable_io, engine='openpyxl') as writer:
                                    if df_main is not None and not df_main.empty:
                                        df_main.to_excel(writer, index=False, sheet_name="Main_Criteria")
                                    for s_name, s_df in sub_dfs.items():
                                        s_df.to_excel(writer, index=False, sheet_name=s_name[:31])
                                    sub_sub_dfs_to_save = st.session_state.get("ahp_sub_sub_dfs", {})
                                    for s_name, s_df in sub_sub_dfs_to_save.items():
                                        s_df.to_excel(writer, index=False, sheet_name=s_name[:31])
                                save_data = uploadable_io.getvalue()
                                save_filename = f"{filename_base}_Raw.xlsx"
                            save_analysis_to_db(st.session_state.user_id, save_filename, save_data)
    
                        # ê²°ê³¼ ?˜ë°œ??ì£¼ì˜ ?ˆë‚´
                        st.markdown(_('<p style="color: red; font-weight: bold; font-size: 0.95rem; margin-top: 5px; margin-bottom: 10px;">? ï¸ ì£¼ì˜: ?˜ì´ì§€ë¥??ˆë¡œê³ ì¹¨?˜ê±°??ë¸Œë¼?°ì?ë¥??«ìœ¼ë©?ë¶„ì„ ê²°ê³¼ê°€ ?€?¥ë˜ì§€ ?Šê³  ë¦¬ì…‹?˜ë?ë¡? ê²°ê³¼ë¬??‘ì? ?Œì¼(?“‘ ê²°ê³¼ ?¤ìš´ë¡œë“œ ????ë°˜ë“œ???¤ìš´ë¡œë“œ?˜ì—¬ ?€?¥í•´ ì£¼ì„¸??</p>',
                                      '<p style="color: red; font-weight: bold; font-size: 0.95rem; margin-top: 5px; margin-bottom: 10px;">? ï¸ Warning: Analysis results are not stored and will be reset if you refresh the page or close the browser. Please make sure to download and save the results Excel file (?“‘ Download Results tab).</p>'), unsafe_allow_html=True)
    
                        tab1, tab2, tab3, tab4, tab5 = st.tabs([
                            _("?Œ ì¢…í•© ë¶„ì„ (Global)", "?Œ Global Comprehensive Analysis"),
                            _("?‘¨?ğŸ‘©â€ğŸ‘§â€ğŸ‘?ê·¸ë£¹ë³?ë¶„ì„", "?‘¨?ğŸ‘©â€ğŸ‘§â€ğŸ‘?Group Analysis"),
                            _("?§ª ?µê³„ ê²€??(ANOVA)", "?§ª Statistical Test (ANOVA)"),
                            _("?“Š ?œê°???¼í„°", "?“Š Visualization Center"),
                            _("?“‘ ê²°ê³¼ ?¤ìš´ë¡œë“œ", "?“‘ Download Results")
                        ])
                        with tab1:
                            st.subheader(_("?Œ ì¢…í•© ì¤‘ìš”??ë°??œìœ„", "?Œ Global Weights & Rankings"))
                            if is_english:
                                disp_final_df = final_df.rename(columns={
                                    "?€ë¶„ë¥˜": "Main Criteria",
                                    "?€ë¶„ë¥˜ ê°€ì¤‘ì¹˜": "Main Criteria Weight",
                                    "ì¤‘ë¶„ë¥?: "Sub-Criteria",
                                    "ì¤‘ë¶„ë¥?ê°€ì¤‘ì¹˜": "Sub-Criteria Weight",
                                    "Global Weight": "Global Weight",
                                    "Global Rank": "Global Rank",
                                    "CR(?€ë¶„ë¥˜)": "CR (Main Criteria)",
                                    "CI(?€ë¶„ë¥˜)": "CI (Main Criteria)",
                                    "CR(ì¤‘ë¶„ë¥?": "CR (Sub-Criteria)",
                                    "CI(ì¤‘ë¶„ë¥?": "CI (Sub-Criteria)"
                                })
                            else:
                                disp_final_df = final_df
                            st.dataframe(disp_final_df.style.format(precision=3), use_container_width=True)
    

    
                        with tab2:
                            st.markdown(_("#### ê·¸ë£¹ë³?ê°€ì¤‘ì¹˜ ?ì„¸ ë¹„êµ", "#### Detailed Comparison of Weights by Group"))
                            disp_comparison_df = comparison_df.copy()
                            if is_english:
                                disp_comparison_df.rename(columns={
                                    "ì¤‘ë¶„ë¥?: "Sub-Criteria",
                                    "Overall": "Overall",
                                    "?„ë¬¸ê°€": "Expert",
                                    "?¼ë°˜": "General",
                                    "ê³µë¬´??: "Public Official"
                                }, inplace=True)
                            st.dataframe(disp_comparison_df.style.format(precision=4), use_container_width=True)
                        with tab3:
                            st.markdown(_("#### ì§‘ë‹¨ ê°?? ì˜??ë¶„ì„", "#### Analysis of Significance Between Groups"))
                            if not anova_df.empty:
                                if is_english:
                                    disp_anova = anova_df.copy()
                                    disp_anova.rename(columns={
                                        "?”ì¸": "Factor/Criteria",
                                        "F-ê°?: "F-Value",
                                        "P-Value": "P-Value",
                                        "? ì˜??: "Significance",
                                        "?¬í›„ê²€??Tukey HSD)": "Post-Hoc (Tukey HSD)"
                                    }, inplace=True)
                                
                                    # Map values in Significance
                                    disp_anova["Significance"] = disp_anova["Significance"].map({
                                        "? ì˜??: "Significant",
                                        "? ì˜?˜ì? ?ŠìŒ": "Not Significant"
                                    }).fillna(disp_anova["Significance"])
                                
                                    # Map values in Post-Hoc
                                    def translate_posthoc(val):
                                        if not isinstance(val, str):
                                            return val
                                        val = val.replace("?„ë¬¸ê°€", "Expert").replace("?¼ë°˜", "General").replace("ê³µë¬´??, "Public Official")
                                        val = val.replace(" ì°¨ì´ ?ˆìŒ", " (Diff exists)")
                                        val = val.replace("ì§‘ë‹¨ ê°?êµ¬ì²´??ì°¨ì´ ë°œê²¬ ëª»í•¨", "No significant pairwise difference found")
                                        val = val.replace("ê³„ì‚° ?¤ë¥˜", "Calculation Error")
                                        return val
                                    disp_anova["Post-Hoc (Tukey HSD)"] = disp_anova["Post-Hoc (Tukey HSD)"].apply(translate_posthoc)
                                else:
                                    disp_anova = anova_df
                                st.dataframe(disp_anova.style.format(precision=5), use_container_width=True)
                            else:
                                st.info(_("?µê³„ ê²€?•ì„ ?„í•´ 2ê°??´ìƒ??ê·¸ë£¹ ?°ì´?°ê? ?„ìš”?©ë‹ˆ??", "At least 2 group datasets are required for statistical testing (ANOVA)."))
                        with tab4:
                            st.markdown(_("#### ?“Š ?œê°???¼í„°", "#### ?“Š Visualization Center"))
                            col_chart1, col_chart2 = st.columns(2)
                            with col_chart1:
                                st.write(_("**ì¢…í•© ì¤‘ìš”??(Bar)**", "**Global Importance (Bar)**"))
                                chart_bar_df = final_df.sort_values('Global Weight').copy()
                                if is_english:
                                    chart_bar_df.rename(columns={"ì¤‘ë¶„ë¥?: "Sub-Criteria", "Global Weight": "Global Weight"}, inplace=True)
                                    y_col = "Sub-Criteria"
                                    x_col = "Global Weight"
                                else:
                                    y_col = "ì¤‘ë¶„ë¥?
                                    x_col = "Global Weight"
                                fig_bar = px.bar(chart_bar_df, y=y_col, x=x_col, orientation='h', text_auto='.3f')
                                st.plotly_chart(fig_bar, use_container_width=True)
                            with col_chart2:
                                st.write(_("**ê·¸ë£¹ë³?ì¤‘ìš”???¨í„´ (Radar)**", "**Importance Pattern by Group (Radar)**"))
                                indiv_global_radar = []
                                all_ids_r = main_results_df['ID'].unique()
                                for rid in all_ids_r:
                                    m_row_rd = main_results_df[main_results_df['ID'] == rid].iloc[0]
                                    rtype_rd = m_row_rd['Type']
                                    grp_name_en = rtype_rd
                                    if is_english:
                                        grp_name_en = str(rtype_rd).replace("?„ë¬¸ê°€", "Expert").replace("?¼ë°˜", "General").replace("ê³µë¬´??, "Public Official")
                                    for m_f_rd in main_factors:
                                        mw_indiv_rd = m_row_rd[f"Weight_{m_f_rd}"]
                                        s_row_df_rd = sub_results_storage[m_f_rd]['df']
                                        s_row_rd = s_row_df_rd[s_row_df_rd['ID'] == rid].iloc[0]
                                        for s_f_rd in sub_results_storage[m_f_rd]['factors']:
                                            indiv_global_radar.append({
                                                "Type": grp_name_en, 
                                                "Factor": s_f_rd, 
                                                "Global_Weight": mw_indiv_rd * s_row_rd[f"Weight_{s_f_rd}"]
                                            })
                                radar_indiv_df = pd.DataFrame(indiv_global_radar)
                                radar_plot_df = radar_indiv_df.groupby(['Type', 'Factor'])['Global_Weight'].mean().reset_index()
                                fig_radar = go.Figure()
                                for t in radar_plot_df['Type'].unique():
                                    t_data = radar_plot_df[radar_plot_df['Type'] == t]
                                    fig_radar.add_trace(go.Scatterpolar(r=t_data['Global_Weight'], theta=t_data['Factor'], fill='toself', name=t))
                                st.plotly_chart(fig_radar, use_container_width=True)
                        
                            # [ë°”ì´?¬ë¦° ?Œë¡¯] CR ë¶„í¬ ?œê°?????œë¡­?¤ìš´ ê³„ì¸µ ? íƒ
                            st.markdown("---")
                            st.write(_("**?¼ê???ë¹„ìœ¨(CR) ë¶„í¬ (Violin Plot)**", "**Consistency Ratio (CR) Distribution (Violin Plot)**"))
                            st.caption(_("ê³„ì¸µ??? íƒ?˜ë©´ ?´ë‹¹ ?˜ì? ?‘ë‹µ?ë“¤??CR ë¶„í¬ë¥??œì‹œ?©ë‹ˆ?? ë°”ì´?¬ë¦° ??= ë°€?? ?´ë? ë°•ìŠ¤ = ì¤‘ì•™ê°’Â·ì‚¬ë¶„ìœ„?? ??= ê°œë³„ ?‘ë‹µ??,
                                         "Select a tier to view respondent CR distribution. Width = density, box = median/IQR, dots = individual respondents"))

                            _t2_tier_opts_ko = ["?€ë¶„ë¥˜ (Main)", "ì¤‘ë¶„ë¥?(Sub)"]
                            _t2_tier_opts_en = ["Main Criteria", "Sub-Criteria"]
                            _t2_tier_opts = _t2_tier_opts_en if is_english else _t2_tier_opts_ko
                            _t2_sel_tier = st.selectbox(
                                _("?“‚ ?œì‹œ??ê³„ì¸µ ? íƒ", "?“‚ Select Tier to Display"),
                                options=_t2_tier_opts,
                                key="vio_tier_select_2tier"
                            )

                            _t2_vio_palette = [
                                "rgba(70,130,180,0.65)",
                                "rgba(205,92,92,0.65)",
                                "rgba(255,182,193,0.65)",
                                "rgba(60,179,113,0.65)",
                                "rgba(255,165,0,0.65)",
                                "rgba(147,112,219,0.65)",
                                "rgba(72,209,204,0.65)",
                                "rgba(255,215,0,0.65)",
                            ]
                            _t2_vio_line_pal = [
                                "#4682B4","#CD5C5C","#FFB6C1","#3CB371",
                                "#FFA500","#9370DB","#48D1CC","#FFD700"
                            ]

                            try:
                                _fig_t2_vio = go.Figure()
                                _t2_ci = 0

                                # ?€?€ ? íƒ: ?€ë¶„ë¥˜ ?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€
                                if _t2_sel_tier == _t2_tier_opts[0]:
                                    if not main_results_df.empty and "Final_CR" in main_results_df.columns:
                                        _t2_main_cr = main_results_df["Final_CR"].dropna().tolist()
                                        _t2_xlbl = _("?€ë¶„ë¥˜", "Main Criteria")
                                        _fig_t2_vio.add_trace(go.Violin(
                                            y=_t2_main_cr, x=[_t2_xlbl]*len(_t2_main_cr),
                                            name=_t2_xlbl, box_visible=True, meanline_visible=True,
                                            points="all", jitter=0.35, pointpos=0,
                                            line_color=_t2_vio_line_pal[0],
                                            fillcolor=_t2_vio_palette[0],
                                            opacity=0.75,
                                            hovertemplate="<b>" + _t2_xlbl + "</b><br>CR: %{y:.4f}<extra></extra>",
                                            showlegend=True
                                        ))
                                    _t2_xaxis_title = _("?€ë¶„ë¥˜", "Main Criteria")
                                    _t2_legend_title = _("?€ë¶„ë¥˜", "Main Criteria")

                                # ?€?€ ? íƒ: ì¤‘ë¶„ë¥??€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€
                                else:
                                    for _t2_mf, _t2_info in sub_results_storage.items():
                                        _t2_sdf = _t2_info.get("df", None)
                                        if _t2_sdf is None or _t2_sdf.empty or "Final_CR" not in _t2_sdf.columns:
                                            continue
                                        _t2_cr_vals = _t2_sdf["Final_CR"].dropna().tolist()
                                        if len(_t2_cr_vals) < 2:
                                            continue
                                        _t2_xlbl = _(f"ì¤‘ë¶„ë¥?{_t2_mf})", f"Sub({_t2_mf})")
                                        _fig_t2_vio.add_trace(go.Violin(
                                            y=_t2_cr_vals, x=[_t2_xlbl]*len(_t2_cr_vals),
                                            name=_t2_xlbl, box_visible=True, meanline_visible=True,
                                            points="all", jitter=0.35, pointpos=0,
                                            line_color=_t2_vio_line_pal[_t2_ci % len(_t2_vio_line_pal)],
                                            fillcolor=_t2_vio_palette[_t2_ci % len(_t2_vio_palette)],
                                            opacity=0.75,
                                            hovertemplate="<b>" + _t2_xlbl + "</b><br>CR: %{y:.4f}<extra></extra>",
                                            showlegend=True
                                        ))
                                        _t2_ci += 1
                                    _t2_xaxis_title = _("?€ë¶„ë¥˜ (ì¤‘ë¶„ë¥?ë¹„êµ CR)", "Main Criteria (Sub-Criteria Comparison CR)")
                                    _t2_legend_title = _("ì¤‘ë¶„ë¥?, "Sub-Criteria")

                                if len(_fig_t2_vio.data) == 0:
                                    st.info(_("? íƒ??ê³„ì¸µ??CR ?°ì´?°ê? ?†ê±°???‘ë‹µ ?˜ê? ë¶€ì¡±í•©?ˆë‹¤.",
                                              "No CR data available for the selected tier or insufficient responses."))
                                else:
                                    _fig_t2_vio.add_hline(
                                        y=0.1, line_dash="dash", line_color="red",
                                        annotation_text=_("CR ?„ê³„ê°?(0.1)", "CR Threshold (0.1)"),
                                        annotation_position="top right"
                                    )
                                    _fig_t2_vio.update_layout(
                                        title=_(
                                            f"ë°”ì´?¬ë¦°?Œë¡¯ CR ??{_t2_sel_tier}",
                                            f"Violin Plot CR ??{_t2_sel_tier}"
                                        ),
                                        xaxis_title=_t2_xaxis_title,
                                        yaxis_title="Final_CR",
                                        violinmode="overlay",
                                        height=540,
                                        legend_title_text=_t2_legend_title,
                                        plot_bgcolor="white",
                                        paper_bgcolor="white",
                                        xaxis=dict(showgrid=False, tickangle=-20),
                                        yaxis=dict(showgrid=True, gridcolor="#eeeeee", zeroline=False)
                                    )
                                    st.plotly_chart(_fig_t2_vio, use_container_width=True)
                            except Exception as _e_t2_vio:
                                st.warning(_(f"ë°”ì´?¬ë¦° ?Œë¡¯ ?ì„± ?¤íŒ¨: {_e_t2_vio}", f"Violin plot generation failed: {_e_t2_vio}"))
    
                            # ?€?€ Fuzzy AHP TFN ?¼ê°?¼ì? ê·¸ë˜??(Tab1 ê²°ê³¼ ?”ë©´ ì§í›„) ?€?€
                            if ahp_method == 'fuzzy':
                                st.markdown("---")
                                st.subheader(_("?“ ?¼ê°?¼ì???TFN) ê°€ì¤‘ì¹˜ ë¶„í¬", "?“ Triangular Fuzzy Number (TFN) Weight Distribution"))
                                st.caption(_("ê°??”ì¸???¼ê°?¼ì???L, M, U)?€ ë¹„í¼ì§€?”ëœ Crisp ê°€ì¤‘ì¹˜ë¥??œê°?”í•©?ˆë‹¤.",
                                             "Visualizes each factor's Triangular Fuzzy Numbers (L, M, U) and defuzzified Crisp weights."))
    
                                tfn_color_palette = [
                                    '#636EFA', '#EF553B', '#00CC96', '#AB63FA', '#FFA15A',
                                    '#19D3F3', '#FF6692', '#B6E880', '#FF97FF', '#FECB52'
                                ]
    
                                def render_tfn_chart(tfn_Si_data, tfn_factors_data, chart_title):
                                    fig = go.Figure()
                                    for i, (l, m, u) in enumerate(tfn_Si_data):
                                        color = tfn_color_palette[i % len(tfn_color_palette)]
                                        crisp = (l * m * u) ** (1/3)
                                        # ?¼ê°??ì±„ìš°ê¸?(ë°˜íˆ¬ëª?
                                        fig.add_trace(go.Scatter(
                                            x=[l, m, u, l],
                                            y=[0, 1, 0, 0],
                                            fill='toself',
                                            fillcolor=f"rgba({int(color[1:3],16)}, {int(color[3:5],16)}, {int(color[5:7],16)}, 0.15)" if color.startswith('#') and len(color) == 7 else (color.replace(')', ', 0.15)').replace('rgb', 'rgba') if 'rgb' in color else color),
                                            line=dict(color=color, width=2.5),
                                            mode='lines',
                                            name=f"{tfn_factors_data[i]}",
                                            hovertemplate=(
                                                f"<b>{tfn_factors_data[i]}</b><br>"
                                                f"L={l:.4f}, M={m:.4f}, U={u:.4f}<br>"
                                                f"Crisp={crisp:.4f}<extra></extra>"
                                            ),
                                            showlegend=True
                                        ))
                                        # Crisp ê°€ì¤‘ì¹˜ ?˜ì§ ?ì„ 
                                        fig.add_trace(go.Scatter(
                                            x=[crisp, crisp],
                                            y=[0, 0.85],
                                            mode='lines',
                                            line=dict(color=color, width=1.5, dash='dot'),
                                            showlegend=False,
                                            hoverinfo='skip'
                                        ))
                                        # Crisp ë§ˆì»¤
                                        fig.add_trace(go.Scatter(
                                            x=[crisp],
                                            y=[0.88],
                                            mode='markers+text',
                                            marker=dict(color=color, size=8, symbol='diamond'),
                                            text=[f"{crisp:.3f}"],
                                            textposition='top center',
                                            textfont=dict(size=10, color=color),
                                            showlegend=False,
                                            hovertemplate=f"<b>{tfn_factors_data[i]}</b> Crisp={crisp:.4f}<extra></extra>"
                                        ))
                                    fig.update_layout(
                                        title=dict(text=chart_title, font=dict(size=14)),
                                        xaxis_title=_("ê°€ì¤‘ì¹˜ ê°?(Weight Value)", "Weight Value"),
                                        yaxis_title=_("?Œì†??(Membership Degree)", "Membership Degree"),
                                        yaxis=dict(range=[-0.05, 1.25]),
                                        height=420,
                                        margin=dict(l=30, r=30, t=50, b=40),
                                        hovermode="closest",
                                        legend=dict(
                                            orientation="h",
                                            yanchor="bottom",
                                            y=-0.25,
                                            xanchor="center",
                                            x=0.5
                                        ),
                                        plot_bgcolor='rgba(248,249,250,1)',
                                        paper_bgcolor='rgba(255,255,255,1)'
                                    )
                                    fig.update_xaxes(gridcolor='rgba(200,200,200,0.3)', zeroline=True, zerolinecolor='rgba(150,150,150,0.5)')
                                    fig.update_yaxes(gridcolor='rgba(200,200,200,0.3)')
                                    return fig
    
                                # 1) ë©”ì¸ ê¸°ì? TFN ê·¸ë˜??
                                if main_group_Si:
                                    st.plotly_chart(
                                        render_tfn_chart(main_group_Si, main_factors,
                                            _("???€ë¶„ë¥˜ (Main Criteria) ?¼ê°?¼ì? ë¶„í¬", "??Main Criteria TFN Distribution")),
                                        use_container_width=True
                                    )
    
                                    # TFN ?˜ì¹˜ ?Œì´ë¸?
                                    tfn_table_rows = []
                                    for i, (l, m, u) in enumerate(main_group_Si):
                                        crisp = (l * m * u) ** (1/3)
                                        tfn_table_rows.append({
                                            _("?”ì¸", "Factor"): main_factors[i],
                                            "L (Lower)": l, "M (Most Likely)": m, "U (Upper)": u,
                                            "Crisp Weight": crisp,
                                            _("?•ê·œ??ê°€ì¤‘ì¹˜", "Normalized Weight"): group_main_weights.iloc[i] if isinstance(group_main_weights, pd.Series) else group_main_weights[i]
                                        })
                                    st.dataframe(pd.DataFrame(tfn_table_rows).style.format(precision=4), use_container_width=True)
    
                                # 2) ?¸ë? ê¸°ì?ë³?TFN ê·¸ë˜??
                                for parent_f, sub_info in sub_results_storage.items():
                                    if sub_info.get('group_Si'):
                                        st.markdown("---")
                                        st.plotly_chart(
                                            render_tfn_chart(sub_info['group_Si'], sub_info['factors'],
                                                _(f"??[{parent_f}] ?¸ë???ª© ?¼ê°?¼ì? ë¶„í¬", f"??[{parent_f}] Sub-Criteria TFN Distribution")),
                                            use_container_width=True
                                        )
                                        sub_tfn_rows = []
                                        for i, (l, m, u) in enumerate(sub_info['group_Si']):
                                            crisp = (l * m * u) ** (1/3)
                                            sub_tfn_rows.append({
                                                _("?”ì¸", "Factor"): sub_info['factors'][i],
                                                "L (Lower)": l, "M (Most Likely)": m, "U (Upper)": u,
                                                "Crisp Weight": crisp,
                                                _("?•ê·œ??ê°€ì¤‘ì¹˜", "Normalized Weight"): sub_info['weights'].iloc[i] if isinstance(sub_info['weights'], pd.Series) else sub_info['weights'][i]
                                            })
                                        st.dataframe(pd.DataFrame(sub_tfn_rows).style.format(precision=4), use_container_width=True)
    
                        with tab5:
                            st.markdown(_('<p style="color: red; font-weight: bold; font-size: 0.95rem; margin-bottom: 12px;">? ï¸ ì£¼ì˜: ë¶„ì„ ê²°ê³¼ê°€ ?¹ìƒ???êµ¬ ?€?¥ë˜ì§€ ?Šìœ¼ë¯€ë¡? ?„ë˜ ?¤ìš´ë¡œë“œ ë²„íŠ¼???ŒëŸ¬ ê²°ê³¼ë¬??‘ì? ?Œì¼??ì»´í“¨?°ì— ë°˜ë“œ???€?¥í•´ ì£¼ì„¸??</p>',
                                          '<p style="color: red; font-weight: bold; font-size: 0.95rem; margin-bottom: 12px;">? ï¸ Warning: Analysis results are not permanently stored on the web. Please make sure to click the download button below to save the Excel file to your computer.</p>'), unsafe_allow_html=True)
                            st.download_button(_("?“¥ ê²°ê³¼ ?Œì¼ ?¤ìš´ë¡œë“œ (Excel)", "?“¥ Download Results File (Excel)"), data=output_res.getvalue(), file_name="AHP_Result.xlsx", type="primary")
                            if 'radar_indiv_df' in locals() and not radar_indiv_df.empty:
                                disp_radar_df = radar_indiv_df.copy()
                                if is_english:
                                    disp_radar_df.rename(columns={
                                        "Type": "Group/Type",
                                        "Factor": "Factor/Criteria",
                                        "Global_Weight": "Global Weight"
                                    }, inplace=True)
                                st.dataframe(disp_radar_df.style.format(precision=4), use_container_width=True)
                            else:
                                st.dataframe(pd.DataFrame(), use_container_width=True)
    
                    except Exception as e:
                        import traceback
                        st.error(_("??ë¶„ì„ ?œìŠ¤???´ë? ?¤ë¥˜ê°€ ë°œìƒ?ˆìŠµ?ˆë‹¤.", "??An internal error occurred in the analysis system."))
                        st.info(_(f"?ì„¸ ?ëŸ¬ ?´ìš©: {e}", f"Detailed error: {e}"))
                        with st.expander(_("?” ?ì„¸ ?¤íƒ ?¸ë ˆ?´ìŠ¤", "?” Detailed Stack Trace")):
                            st.code(traceback.format_exc())
                        st.stop()
                else:
                    st.warning(message)
                    if role_chk == 'temp' and ("5ê°??œë³¸" in message or "5 samples" in message):
                        st.markdown("---")
                        with st.container(border=True):
                            if is_english:
                                st.markdown("### ?’³ Official User Upgrade & Unlimited Analysis")
                                st.markdown("Upgrading to an Official User **instantly removes the 5-sample limit** and allows unlimited access to all features.")
                                st.info("Upgrade to **Official User** to get unlimited access (3 months) for **$350.00 USD** via PayPal.")
                            
                                paypal_client_id = st.secrets.get("PAYPAL_CLIENT_ID", "sb")
                                user_id = st.session_state.user_id
                            
                                paypal_html = f"""
                                <div id="paypal-button-container-main" style="text-align: center; max-width: 100%;"></div>
                                <script src="https://www.paypal.com/sdk/js?client-id={paypal_client_id}&currency=USD&locale=en_US"></script>
                                <script>
                                  paypal.Buttons({{
                                    style: {{
                                      layout: 'vertical',
                                      color:  'gold',
                                      shape:  'rect',
                                      label:  'paypal',
                                      height: 40
                                    }},
                                    createOrder: function(data, actions) {{
                                      return actions.order.create({{
                                        purchase_units: [{{
                                          amount: {{
                                            value: '350.00'
                                          }},
                                          payee: {{
                                            email_address: 'jeon080423@gmail.com'
                                          }}
                                        }}]
                                      }});
                                    }},
                                    onApprove: function(data, actions) {{
                                      return actions.order.capture().then(function(details) {{
                                        window.top.location.href = window.top.location.origin + window.top.location.pathname + "?paypal_order_id=" + data.orderID + "&user_id=" + encodeURIComponent("{user_id}");
                                      }});
                                    }},
                                    onError: function(err) {{
                                      console.error(err);
                                      alert("Payment failed or was cancelled.");
                                    }}
                                  }}).render('#paypal-button-container-main');
                                </script>
                                """
                                st.components.v1.html(paypal_html, height=180)
                            else:
                                st.markdown(_("### ?’³ ?•ì‹ ?¬ìš©???¹ê²© ë°?ë¬´ì œ??ë¶„ì„", "### ?’³ Upgrade to Official User for Unlimited Analysis"))
                                st.markdown("?•ì‹ ?¬ìš©?ë¡œ ?¹ê²©?˜ì‹œë©?**?œë³¸ ???œí•œ(5ê°???ì¦‰ì‹œ ?´ì œ**?˜ë©° ëª¨ë“  ê¸°ëŠ¥??ë¬´ì œ?œìœ¼ë¡??¬ìš©?˜ì‹¤ ???ˆìŠµ?ˆë‹¤.")
                                st.info("ì¹´ì¹´?¤ë±…??3333-23-8667708 (?ˆê¸ˆì£? ?ˆã……?? ê³„ì¢Œë¡??¡ê¸ˆ?˜ì‹  ???„ë˜ ë²„íŠ¼???´ë¦­??ì£¼ì„¸??\n(?œë¹„???´ìš©?”ê¸ˆ: 50ë§Œì›)")
                                if st.button("?•ì‹ ?¬ìš©???„í™˜ ?”ì²­", use_container_width=True, key="main_upgrade_btn"):
                                    if send_conversion_request_email(st.session_state.user_id):
                                        st.success("?•ì‹ ?¬ìš©???„í™˜?”ì²­???„ë£Œ ?˜ì—ˆ?µë‹ˆ?? ?…ê¸ˆ ?•ì¸ ???•ì‹?¬ìš©?ë¡œ ?„í™˜???œë¦½?ˆë‹¤")
                                    else:
                                        st.error("?”ì²­ ?„ì†¡ ?¤íŒ¨. ê´€ë¦¬ì?ê²Œ ë¬¸ì˜ë°”ë?ˆë‹¤.")
            except Exception as e:
                st.error(f"?Œì¼ ì²˜ë¦¬ ?¤ë¥˜ ë°œìƒ: {e}")
            
        # -------------------------------------------------------------------------
        # [? ê·œ] ?¨ë¼???¤ë¬¸ì§€ ?œì‘ ??(Tab 2) ?ì„¸ êµ¬í˜„
        # -------------------------------------------------------------------------
    with main_tab2:
        # @st.fragment: ?„ì ¯ ë³€ê²??????ì—­ë§??¬ì‹¤??(?±ëŠ¥ ìµœì ??
        @st.fragment
        def _survey_setup_fragment():
            st.header(_("?“ AHP ?¨ë¼???¤ë¬¸ ?ë™ ?ì„± ë°?ë°°í¬", "?“ AHP Online Survey Auto-Generator & Deployer"))
            if st.session_state.user_id is None:
                st.warning(_("?”’ **ë¹„íšŒ?ë„ ?¨ë¼???¤ë¬¸ ?¼ì„ ë¯¸ë¦¬ ?‘ì„±??ë³????ˆìŠµ?ˆë‹¤.**", "?”’ **Non-members can also preview and fill out the online survey form.**"))
                st.info(_("?‘ì„±?˜ì‹  ?´ìš©?€ ì¢Œì¸¡ ?¬ì´?œë°”?ì„œ ?Œì›ê°€??ë°?ë¡œê·¸?¸ì„ ?˜ì‹œë©?ê·¸ë?ë¡?? ì??˜ì–´ ë°”ë¡œ ë°°í¬?˜ì‹¤ ???ˆìŠµ?ˆë‹¤. (ë¬´ë£Œ ?Œì›??ê¸°ëŠ¥ ?œí•œ ?†ì´ ëª¨ë“  ê¸°ëŠ¥ ?¬ìš© ê°€??", "Once you sign up and log in from the left sidebar, the contents you have written will be maintained and you can deploy immediately. (Free members can also use all features without restriction)"))

            st.info(_("?‘ë‹µ ?°ì´?°ëŠ” ?°ë™?˜ì‹  êµ¬ê? ?¤í”„?ˆë“œ?œíŠ¸???€?¥ë©?ˆë‹¤. ë°°í¬ ???°ì´?°ê? ?•ìƒ ê¸°ë¡?˜ëŠ”ì§€ ë°˜ë“œ???ŒìŠ¤?¸í•´ ì£¼ì„¸??\n\n? ï¸ **ì£¼ì˜:** ?°ë™ ?´ì œ???¤íŠ¸?Œí¬ ?¥ì•  ?±ìœ¼ë¡??¸í•œ ?°ì´??? ì‹¤???€?´ì„œ??ì±…ì„ì§€ì§€ ?Šìœ¼ë¯€ë¡? ì¤‘ìš” ?°ì´?°ëŠ” ì£¼ê¸°?ìœ¼ë¡?ë°±ì—… ë°?ë³´ê??˜ì‹œê¸?ë°”ë?ˆë‹¤.", "Response data is stored in your linked Google Spreadsheet. Please test data recording before deploying the survey.\n\n? ï¸ **Caution:** We are not responsible for data loss due to unlinking or network failures. Please backup your important data periodically."))

            # [ê°€?´ë“œ ?½ì…]
            with st.expander(_("?“– ?¨ë¼???¤ë¬¸ ?ë™ ?ì„± ë°?ë°°í¬ ?´ìš© ê°€?´ë“œ (?´ë¦­?˜ì—¬ ?¼ì¹˜ê¸?", "?“– Online Survey Auto-Generation & Deployment Guide (Click to expand)"), expanded=False):
                try:
                    import os
                    guide_file = "guide_en.html" if st.session_state.lang == "en" else "guide.html"
                    with open(os.path.join("static", guide_file), "r", encoding="utf-8") as f:
                        guide_html = f.read()
                    import streamlit.components.v1 as components
                    components.html(guide_html, height=720, scrolling=True)
                except Exception as e:
                    st.error("ê°€?´ë“œ ?Œì¼??ë¶ˆëŸ¬?????†ìŠµ?ˆë‹¤.")

            # (Dashboard moved to main_tab3 below)
            pass

            st.divider()
        
            # ------------------------------------------------------------
            # 0. ?¤ë¬¸ ê´€ë¦?(1??1?¤ë¬¸ ëª¨ë“œ)
            # ------------------------------------------------------------
            st.subheader(_("?¹ì…˜ 0: ???¤ë¬¸ ê´€ë¦?, "Section 0: My Survey Management"))

            # Initialize states
            if 'editing_survey_id' not in st.session_state:
                st.session_state.editing_survey_id = None
            if 'survey_auto_loaded' not in st.session_state:
                st.session_state.survey_auto_loaded = False

            # Check existing surveys (SQLite?€ êµ¬ê? ?œíŠ¸ ëª¨ë‘ ì¡°íšŒ?˜ì—¬ ë³‘í•©) ???¸ì…˜ ìºì‹±
            if '_cached_user_surveys' not in st.session_state or st.session_state.get('_survey_cache_dirty'):
                sqlite_surveys = []
                try:
                    import sqlite3
                    conn = sqlite3.connect('users.db')
                    cur = conn.cursor()
                    cur.execute("SELECT survey_id, title, created_at FROM admin_surveys WHERE admin_id = ? ORDER BY created_at DESC", (st.session_state.user_id,))
                    sqlite_surveys = cur.fetchall()
                    conn.close()
                except Exception:
                    pass

                gs_surveys = []
                try:
                    from survey_manager import get_admin_surveys_from_gsheet
                    gs_surveys = get_admin_surveys_from_gsheet(st.session_state.user_id)
                except Exception:
                    pass
                
                merged_surveys = {}
                for s in gs_surveys + sqlite_surveys:
                    if s[0] not in merged_surveys:
                        merged_surveys[s[0]] = s
                user_surveys = list(merged_surveys.values())
                user_surveys.sort(key=lambda x: x[2], reverse=True)
                st.session_state._cached_user_surveys = user_surveys
                st.session_state._survey_cache_dirty = False
            else:
                user_surveys = st.session_state._cached_user_surveys
            
            has_survey = len(user_surveys) > 0

            # Auto-load logic
            if has_survey and not st.session_state.survey_auto_loaded:
                sel_id = user_surveys[0][0] # Load the most recent one
                from survey_manager import load_survey_metadata
                meta = load_survey_metadata(sel_id)
                if meta:
                    st.session_state.editing_survey_id = sel_id
                    st.session_state.edit_title = meta.get("Title", "")
                    st.session_state.edit_desc = meta.get("Description", "")
                    st.session_state.edit_admin_email = meta.get("Admin_Email", "")

                    demo = meta.get("Demographics", {})
                    st.session_state.edit_type_question = demo.get("type_question", "")
                    st.session_state.edit_type_options = ", ".join(demo.get("type_options", []))
                    st.session_state.edit_demo_gender = demo.get("gender", False)
                    st.session_state.edit_demo_aff = demo.get("affiliation", False)
                    st.session_state.edit_demo_email = demo.get("email", False)
                    st.session_state.edit_demo_name = demo.get("name", False)
                    st.session_state.edit_demo_age = demo.get("age", False)
                    st.session_state.edit_demo_exp = demo.get("experience", False)
                    st.session_state.edit_age_type = demo.get("age_type", "ê°œë°©??(?«ì ì§ì ‘ ?…ë ¥)")
                    st.session_state.edit_exp_type = demo.get("experience_type", "ê°œë°©??(?«ì ì§ì ‘ ?…ë ¥)")
                
                    st.session_state.edit_scale_type = meta.get("Scale_Type", "1-9 Continuous")
                    cr_limit_raw = meta.get("CR_Limit", 0.1)
                    st.session_state.edit_cr_limit = float(cr_limit_raw) if cr_limit_raw is not None and str(cr_limit_raw).lower() != "none" else None
                    cr_guide_raw = meta.get("CR_Guide_Method", "realtime" if str(meta.get("CR_Guide_Enabled", "False")).lower() == "true" else "none")
                    st.session_state.edit_cr_guide_method = cr_guide_raw
                
                    ahp_model = meta.get("AHP_Model_JSON", {})
                    st.session_state.edit_main_input = ", ".join(ahp_model.get("main", []))
                    st.session_state.edit_sub_inputs = {}
                    for mc, subs in ahp_model.get("subs", {}).items():
                        st.session_state.edit_sub_inputs[mc] = ", ".join(subs)
                    
                    definitions = meta.get("Definitions", {})
                    st.session_state.edit_definitions = definitions
                st.session_state.survey_auto_loaded = True
                st.rerun()

            @st.dialog(_("?š¨ [ê²½ê³ ] ê¸°ì¡´ ?¤ë¬¸ ?êµ¬ ?? œ ?ˆë‚´", "?š¨ [Warning] Permanent Deletion of Existing Survey"))
            def confirm_new_survey():
                st.error(_("?ˆë¡œ???¤ë¬¸???‘ì„±?˜ì‹œë©?ê¸°ì¡´ ?°ë™??êµ¬ê? ?œíŠ¸???€?¥ëœ **ëª¨ë“  ?°ì´???¤ë¬¸ êµ¬ì¡°, ë¬¸í•­, ?˜ì§‘???„ì²´ ?‘ë‹µ ê²°ê³¼)ê°€ ì¦‰ì‹œ ?? œ?˜ë©° ?ˆë? ë³µêµ¬?????†ìŠµ?ˆë‹¤.**", "If you create a new survey, **ALL data saved in the linked Google Sheet (survey structure, questions, collected responses) will be immediately deleted and CANNOT be recovered.**"))
                st.info(_("?’¡ **?°ì´??ë³´ì¡´ ?ˆë‚´:** ê¸°ì¡´ ?¤ë¬¸???‘ë‹µ ê²°ê³¼ ë³´ì¡´???í•˜? ë‹¤ë©? ?? œ???™ì˜?˜ì‹œê¸??„ì— êµ¬ê? ?¤í”„?ˆë“œ?œíŠ¸???‘ì†?˜ì—¬ **[?Œì¼] -> [?¤ìš´ë¡œë“œ]** ë©”ë‰´ë¥??µí•´ ?‘ì?(.xlsx) ?Œì¼ ?±ìœ¼ë¡?ë°±ì—…ë³¸ì„ ?¬ìš©??ì»´í“¨?°ì— ë¯¸ë¦¬ ?¤ìš´ë¡œë“œ???ì‹œê¸?ë°”ë?ˆë‹¤.", "?’¡ **Data Preservation Guide:** If you wish to keep the existing responses, please go to the Google Spreadsheet and use the **[File] -> [Download]** menu to download a backup copy (e.g., .xlsx) to your computer before agreeing to delete."))
                agree = st.checkbox(_("?? ê¸°ì¡´ ?°ì´??ë°±ì—…???„ë£Œ?ˆê±°??ë¶ˆí•„?”í•˜ë©? ëª¨ë“  ?°ì´???? œ???™ì˜?©ë‹ˆ??", "Yes, I have backed up or do not need the existing data, and I agree to delete all data."))
                col1, col2 = st.columns(2)
                with col1:
                    if st.button(_("??ì·¨ì†Œ", "??Cancel"), use_container_width=True):
                        st.rerun()
                with col2:
                    if st.button(_("???™ì˜ ë°?ì´ˆê¸°??, "??Agree & Initialize"), type="primary", use_container_width=True, disabled=not agree):
                        with st.spinner(_("ê¸°ì¡´ ?°ì´?°ë? ?? œ?˜ëŠ” ì¤‘ì…?ˆë‹¤...", "Deleting existing data...")):
                            from survey_manager import delete_admin_survey
                            if user_surveys:
                                delete_admin_survey(user_surveys[0][0], st.session_state.user_id)
                            st.session_state.editing_survey_id = None
                            keys_to_clear = [k for k in st.session_state.keys() if k.startswith('edit_')]
                            for k in keys_to_clear:
                                del st.session_state[k]
                            st.session_state.survey_auto_loaded = True
                            st.session_state._survey_cache_dirty = True
                        st.success(_("?„ë£Œ?˜ì—ˆ?µë‹ˆ?? ?”ë©´???ˆë¡œê³ ì¹¨?©ë‹ˆ??", "Completed. The screen will be refreshed."))
                        import time
                        time.sleep(1.5)
                        st.rerun()

            linked_sheet_id = st.session_state.get("editing_survey_id")
            if linked_sheet_id:
                survey_title_display = st.session_state.get("edit_title", "")
                for s in user_surveys:
                    if s[0] == linked_sheet_id:
                        survey_title_display = s[1]
                        break
                st.success(_(f"?“Œ ?„ì¬ ë°°í¬???¤ë¬¸??ë¶ˆëŸ¬?”ìŠµ?ˆë‹¤: **{survey_title_display}**", f"?“Œ Loaded deployed survey: **{survey_title_display}**"))
                st.info(_("?„ë˜ ?¼ì—???´ìš©???˜ì •?˜ì‹  ???˜ë‹¨??**[ë°°í¬ ë°?DB ?°ë™ (?˜ì • ?´ìš© ?ìš©)]** ë²„íŠ¼???„ë¥´?œë©´ ê¸°ì¡´ ?œíŠ¸???´ìš©????–´?Œì›Œì§‘ë‹ˆ??", "If you modify the form below and click the **[Deploy & Link DB (Apply Modifications)]** button at the bottom, the existing sheet will be overwritten."))
                
                # [? ê·œ] ?°ë™??êµ¬ê? ?¤í”„?ˆë“œ?œíŠ¸ ë°”ë¡œê°€ê¸?ë²„íŠ¼ (?¨ìƒ‰ ë°°ê²½, ?°ìƒ‰ ?ìŠ¤?? ?„ì´ì½??†ìŒ)
                gs_link = f"https://docs.google.com/spreadsheets/d/{linked_sheet_id}"
                btn_label = _("?°ë™??êµ¬ê? ?¤í”„?ˆë“œ?œíŠ¸ ë°”ë¡œê°€ê¸?, "Open Linked Google Sheet")
                st.markdown(f'''
                <div style="background-color: #2349a2; border-radius: 6px; padding: 12px 16px; text-align: center; margin-bottom: 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.15);">
                    <a href="{gs_link}" target="_blank" style="color: #ffffff !important; text-decoration: none !important; font-weight: 600; font-size: 0.95rem; font-family: sans-serif; display: block; width: 100%;">
                        {btn_label}
                    </a>
                </div>
                ''', unsafe_allow_html=True)

                if st.button(_("??ì²˜ìŒë¶€?????¤ë¬¸ ?‘ì„±?˜ê¸° (ê¸°ì¡´ ?°ì´???? œ)", "??Start a new survey from scratch (Delete existing data)"), type="secondary", use_container_width=True):
                     confirm_new_survey()
            else:
                st.info(_("?“Œ ?‘ì„± ì¤‘ì¸ ???¤ë¬¸?…ë‹ˆ?? ?´ìš©???‘ì„±????ë°°í¬??ì£¼ì„¸??", "?“Œ This is a new survey in progress. Please fill out the contents and deploy."))
                if st.button(_("?????´ìš© ëª¨ë‘ ì§€?°ê¸° (ì´ˆê¸°??", "??Clear all form contents (Initialize)"), type="secondary"):
                    st.session_state.editing_survey_id = None
                    keys_to_clear = [k for k in st.session_state.keys() if k.startswith('edit_')]
                    for k in keys_to_clear:
                        del st.session_state[k]
                    st.rerun()

            st.divider()

            from survey_manager import create_survey_sheet, generate_pairwise_combinations

            # 7ê°??¹ì…˜ ?¤ë¬¸ì§€ ?ì„± ??êµ¬ì„±
            # ?¹ì…˜ 1: ê¸°ë³¸ ?•ë³´
            st.subheader(_("?¹ì…˜ 1: ?¤ë¬¸ ê¸°ë³¸ ?•ë³´ ?¤ì •", "Section 1: Survey Basic Info Setup"))
            default_survey_title = _("?œì¡°???‘ë™ë¡œë´‡ ?„ì… ?”ì¸ ì¤‘ìš”??ë¶„ì„???„í•œ ?„ë¬¸ê°€ AHP ?¤ë¬¸", "Expert AHP Survey on the Importance of Factors for Adopting Manufacturing Collaborative Robots")
            survey_title = st.text_input(_("?¤ë¬¸ì§€ ?œëª©", "Survey Title"), value=st.session_state.get("edit_title", default_survey_title))
        
            default_survey_desc_ko = """[ì¡°ì‚¬ ëª©ì  ë°??ˆë‚´ë¬?

    ?ˆë…•?˜ì‹­?ˆê¹Œ?
    ë³??¤ë¬¸ì¡°ì‚¬??[?°êµ¬/?„ë¡œ?íŠ¸ ì£¼ì œ]??ê´€??ì£¼ìš” ?”ì¸?¤ì˜ ?ë???ì¤‘ìš”?„ë? ?„ì¶œ?˜ê¸° ?„í•´ ?„ë¬¸ê°€(?ëŠ” ?¤ë¬´?? ?¬ëŸ¬ë¶„ì˜ ê³ ê²¬???˜ë ´?˜ê³ ??ë§ˆë ¨?˜ì—ˆ?µë‹ˆ?? 
    ë°”ì˜?œë”?¼ë„ ? ì‹œ ?œê°„???´ì–´ ê·€?˜ì˜ ê·€ì¤‘í•œ ?˜ê²¬???‘ë‹µ??ì£¼ì‹œë©??°êµ¬?????„ì?????ê²ƒì…?ˆë‹¤.

    ??ì¡°ì‚¬ ëª©ì  : [?°êµ¬/?„ë¡œ?íŠ¸ ëª©ì  ê¸°ì¬]
    ??ì¡°ì‚¬ ?´ìš© : [ì¡°ì‚¬ ?€???”ì¸] ê°„ì˜ AHP(?ë?ë¹„êµ) ?‰ê?
    ??ì¡°ì‚¬ ê¸°ê°„ : 202X??X??X??~ 202X??X??X??
    ??ê°œì¸?•ë³´ ë³´í˜¸ : 
    ë³?ì¡°ì‚¬ë¥??µí•´ ?˜ì§‘??ëª¨ë“  ?ë£Œ???µê³„ë²???3ì¡?ë¹„ë???ë³´í˜¸)???˜ê±°?˜ì—¬ ì² ì???ë³´í˜¸?˜ë©°, ?¤ì§ ?°êµ¬ ë°??µê³„ ë¶„ì„ ëª©ì ?¼ë¡œë§??œìš©?©ë‹ˆ?? ?‘ë‹µ?´ì£¼??ê°œì¸ ?•ë³´ ë°?ê°œë³„ ?‘ë‹µ ê²°ê³¼???ˆë? ?¸ë?ë¡?? ì¶œ?˜ì? ?ŠìŒ???½ì†?œë¦½?ˆë‹¤.

    ê·€?˜ì˜ ?Œì¤‘??ì°¸ì—¬??ê¹Šì? ê°ì‚¬ë¥??œë¦½?ˆë‹¤.

    - ?°êµ¬ ì±…ì„??: [?´ë¦„ ê¸°ì¬]
    - ë¬¸ì˜ì²?: [?°ë½ì²??ëŠ” ?´ë©”??ê¸°ì¬]"""

            default_survey_desc_en = """[Survey Purpose & Instructions]

    Greetings,
    This survey is designed to collect the valuable opinions of experts (or practitioners) to derive the relative importance of key factors regarding [Research/Project Topic].
    Your participation will be of great help to our research, and we would deeply appreciate it if you could take a moment out of your busy schedule to respond.

    ??Purpose : [Enter Research/Project Purpose]
    ??Content : AHP (Pairwise Comparison) evaluation among [Target Factors]
    ??Period : 202X-XX-XX ~ 202X-XX-XX
    ??Privacy Policy : 
    All data collected through this survey will be strictly protected in accordance with privacy laws and used solely for research and statistical analysis purposes. We promise that your personal information and individual responses will never be leaked externally.

    Thank you very much for your valuable participation.

    - Lead Researcher : [Enter Name]
    - Contact : [Enter Phone or Email]"""

            survey_desc = st.text_area(_("ì¡°ì‚¬ ëª©ì  ë°??ˆë‚´ë¬?, "Survey Purpose & Instructions"), value=st.session_state.get("edit_desc", _(default_survey_desc_ko, default_survey_desc_en)), height=350)
            if st.session_state.user_id:
                if "@" in st.session_state.user_id:
                    default_admin_email = st.session_state.user_id
                elif st.session_state.user_id == "shjeon":
                    default_admin_email = "jeon080423@gmail.com"
                else:
                    default_admin_email = f"{st.session_state.user_id}@ahpmaster.com"
            else:
                default_admin_email = "temp@ahpmaster.com"
            survey_admin_email = st.text_input(_("?¤ë¬¸ì¡°ì‚¬ ?´ë‹¹???´ë©”??ì£¼ì†Œ *", "Survey Admin Email *"), value=st.session_state.get("edit_admin_email", default_admin_email), placeholder="example@gmail.com")

            st.divider()

            # ?¹ì…˜ 1.5: ?‘ë‹µ???˜ì§‘ ?•ë³´ ë°?ê·¸ë£¹ ë¶„ë¥˜ ?¤ì •
            st.subheader(_("?¹ì…˜ 1.5: ?‘ë‹µ???˜ì§‘ ?•ë³´ ë°?ê·¸ë£¹ ë¶„ë¥˜", "Section 1.5: Respondent Info & Grouping"))

            # ê·¸ë£¹ ë¶„ë¥˜ ?¤ì •
            with st.container(border=True):
                st.markdown(_("**?‘¥ ê·¸ë£¹ ë¶„ë¥˜ ë¬¸í•­ ?¤ì •**", "**?‘¥ Group Classification Setup**"))
                type_q_val = st.session_state.get("edit_type_question")
                if type_q_val == "ê·€?˜ì˜ ?Œì†?€ ?´ë–»ê²??˜ì‹­?ˆê¹Œ?":
                    type_q_val = _("ê·€?˜ì˜ ?Œì†?€ ?´ë–»ê²??˜ì‹­?ˆê¹Œ?", "What is your affiliation?")
                elif not type_q_val:
                    type_q_val = _("ê·€?˜ì˜ ?Œì†?€ ?´ë–»ê²??˜ì‹­?ˆê¹Œ?", "What is your affiliation?")
                type_question = st.text_input(_("ê·¸ë£¹ ë¶„ë¥˜ ì§ˆë¬¸ ?œëª©", "Group Classification Question Title"), value=type_q_val)
            
                type_opts_val = st.session_state.get("edit_type_options")
                if type_opts_val == "?„ë¬¸ê°€, ?¼ë°˜, ê³µë¬´?? ê¸°í?":
                    type_opts_val = _("?„ë¬¸ê°€, ?¼ë°˜, ê³µë¬´?? ê¸°í?", "Expert, General, Public Official, Other")
                elif not type_opts_val:
                    type_opts_val = _("?„ë¬¸ê°€, ?¼ë°˜, ê³µë¬´?? ê¸°í?", "Expert, General, Public Official, Other")
                type_options = st.text_input(_("ê·¸ë£¹ ë¶„ë¥˜ ë³´ê¸° ?µì…˜ (ì½¤ë§ˆë¡?êµ¬ë¶„)", "Group Classification Options (comma-separated)"), value=type_opts_val)

            st.write("")

            # ?¸êµ¬?µê³„???•ë³´ ?¤ì •
            with st.container(border=True):
                st.markdown(_("**?“Š ?¸êµ¬?µê³„?™ì  ë¬¸í•­ ?˜ì§‘ ?¤ì •**", "**?“Š Demographic Questions Setup**"))
                demo_gender = st.checkbox(_("?±ë³„ ?˜ì§‘", "Collect Gender"), value=st.session_state.get("edit_demo_gender", True))
                demo_email = st.checkbox(_("?´ë©”???˜ì§‘", "Collect Email"), value=st.session_state.get("edit_demo_email", True))

                st.divider()

                demo_age = st.checkbox(_("?°ë ¹ ?˜ì§‘", "Collect Age"), value=st.session_state.get("edit_demo_age", True))
                age_type = "ê°œë°©??(?«ì ì§ì ‘ ?…ë ¥)"
                if demo_age:
                    age_type_options = [_("ê°œë°©??(?«ì ì§ì ‘ ?…ë ¥)", "Open-ended (Type Number)"), _("10???¨ìœ„ ? íƒ??, "Multiple Choice (10-year intervals)")]
                    age_type = st.radio(_("?°ë ¹ ?˜ì§‘ ë°©ì‹", "Age Collection Method"), age_type_options, index=0 if st.session_state.get("edit_age_type", "ê°œë°©??(?«ì ì§ì ‘ ?…ë ¥)") == "ê°œë°©??(?«ì ì§ì ‘ ?…ë ¥)" else 1, horizontal=True, key="survey_age_type_setup")

                st.divider()

                demo_exp = st.checkbox(_("ê²½ë ¥?„ìˆ˜ ?˜ì§‘", "Collect Years of Experience"), value=st.session_state.get("edit_demo_exp", True))
                exp_type = "ê°œë°©??(?«ì ì§ì ‘ ?…ë ¥)"
                if demo_exp:
                    exp_type_options = [_("ê°œë°©??(?«ì ì§ì ‘ ?…ë ¥)", "Open-ended (Type Number)"), _("5???¨ìœ„ ? íƒ??, "Multiple Choice (5-year intervals)")]
                    exp_type = st.radio(_("ê²½ë ¥?„ìˆ˜ ?˜ì§‘ ë°©ì‹", "Experience Collection Method"), exp_type_options, index=0 if st.session_state.get("edit_exp_type", "ê°œë°©??(?«ì ì§ì ‘ ?…ë ¥)") == "ê°œë°©??(?«ì ì§ì ‘ ?…ë ¥)" else 1, horizontal=True, key="survey_exp_type_setup")

            demographics_settings = {
                "name": False,  # ?±ëª… ?˜ì§‘ ?? œ
                "age": demo_age,
                "age_type": age_type,
                "gender": demo_gender,
                "experience": demo_exp,
                "experience_type": exp_type,
                "affiliation": False,  # ?Œì† ?˜ì§‘ ?? œ
                "email": demo_email,
                "type_question": type_question,
                "type_options": [x.strip() for x in type_options.split(",") if x.strip()]
            }

            st.divider()

            # ?¹ì…˜ 2: AHP ëª¨ë¸ ê³„ì¸µêµ¬ì¡° ?…ë ¥ ??
            st.subheader(_("?¹ì…˜ 2: AHP ?”ì¸ ê³„ì¸µêµ¬ì¡° ë°?ë¬¸í•­ ?¤ì •", "Section 2: AHP Criteria Hierarchy & Question Setup"))

            # ê³„ì¸µ êµ¬ì¡° ? íƒ (2ê³„ì¸µ ê¸°ì?ê³??™ì¼?˜ê²Œ ?„ì²´ ê³µê°œ)
            tier_level = 2
            st.markdown("---")
            st.markdown(_("##### ?™ï¸ ê³„ì¸µ êµ¬ì¡° ?ˆë²¨ ? íƒ", "##### ?™ï¸ Select Hierarchy Level"))
            tier_choice_tab2 = st.radio(
                _("?¤ë¬¸ ëª¨ë¸??ê³„ì¸µ ê¹Šì´ë¥?? íƒ?˜ì„¸??", "Select the hierarchy depth for your survey model."),
                [_("2ê³„ì¸µ (?€ë¶„ë¥˜ ??ì¤‘ë¶„ë¥?", "2-Tier (Main ??Sub)"),
                 _("3ê³„ì¸µ (?€ë¶„ë¥˜ ??ì¤‘ë¶„ë¥????Œë¶„ë¥?", "3-Tier (Main ??Sub ??Sub-sub)")],
                index=0,
                horizontal=True,
                key="tab2_tier_choice"
            )
            if _("3ê³„ì¸µ", "3-Tier") in tier_choice_tab2:
                tier_level = 3
            st.markdown("---")

            st.info(_(
                "?’¡ ?„ì¬ ?…ë ¥???”ì¸?€ **?ˆì‹œ**??ë¿ì´ë©? ?¬ìš©?ì˜ ?°êµ¬ ëª¨ë¸??ë§ì¶”???´ìš©??ëª¨ë‘ ?˜ì •?˜ì—¬ ?¬ìš©?????ˆìŠµ?ˆë‹¤.\n\n"
                "- ?€ë¶„ë¥˜ ë°??˜ìœ„ ?”ì¸?€ ë°˜ë“œ??**?¼í‘œ(,)** ë¡?êµ¬ë¶„?˜ì—¬ ?…ë ¥??ì£¼ì„¸??\n"
                "- ?”ì¸ëª…ì— ?¸ë”ë°?`_`) ê¸°í˜¸???œìŠ¤???´ë? ì²˜ë¦¬?€ ì¶©ëŒ?˜ë?ë¡??¬ìš©?????†ìŠµ?ˆë‹¤. (?…ë ¥ ???ë™?¼ë¡œ ê³µë°±?¼ë¡œ ë³€?˜ë©?ˆë‹¤.)",
                "?’¡ The current criteria are just **examples**. You can freely modify them to fit your research model.\n\n"
                "- Separate Main and Sub criteria using **commas(,)**.\n"
                "- Do not use underscores (`_`) in criteria names. (They will be automatically converted to spaces.)"
            ))

            default_tab2_main = _("ê¸°ëŠ¥?? ?”ì?? ê²½ì œ??, "Functionality, Design, Economy") if tier_level == 3 else _("ê¸°ìˆ  ?”ì¸, ì¡°ì§ ?”ì¸, ?˜ê²½ ?”ì¸, ?ì‹  ?”ì¸", "Technological, Organizational, Environmental, Innovational")
            main_input = st.text_input(_("?€??ª© (Main Criteria)", "Main Criteria"), value=st.session_state.get("edit_main_input", default_tab2_main))
            main_list = [x.strip().replace("_", " ") for x in main_input.split(",") if x.strip()]

            model_structure = {"main": main_list, "subs": {}}
            if tier_level == 3:
                model_structure["sub_subs"] = {}

            for mc in main_list:
                # ê¸°ë³¸ê°??œì•ˆ (ê¸°ì¡´ ?‘ìŠ¹???‘ë™ë¡œë´‡ ë°?3ê³„ì¸µ ?¤ë§ˆ?¸í° êµ¬ë§¤ ê²°ì •)
                default_sub_val = ""
                if mc in ["ê¸°ìˆ  ?”ì¸", "Technological"]: default_sub_val = _("?ë??ì´?? ?¸í™˜?? ?ˆì „?? ?œë¹„?¤ì???, "Relative Advantage, Compatibility, Security, Service Support")
                elif mc in ["ì¡°ì§ ?”ì¸", "Organizational"]: default_sub_val = _("ê²½ì˜ì§„ì??? ê¸°ìˆ ì¤€ë¹„ë„, ê¸ˆìœµ?ì›, êµìœ¡?ˆë ¨", "Top Management Support, Tech Readiness, Financial Resources, Training")
                elif mc in ["?˜ê²½ ?”ì¸", "Environmental"]: default_sub_val = _("?•ë?ì§€?? ê²½ìŸ?•ë ¥, ?¸ë ¥?? ?¸ë?ì§€??, "Gov Support, Competitive Pressure, Labor Shortage, External Support")
                elif mc in ["?ì‹  ?”ì¸", "Innovational"]: default_sub_val = _("ê²½ì˜ì§„ì˜ ?ì‹ ?? ë³€?”ìˆ˜?©íƒœ?? ?¤ë§ˆ?¸íŒ©? ë¦¬?˜ì?, ì§€?ì •??, "Management Innovativeness, Change Acceptance, Smart Factory Level, Knowledge Level")
                elif mc in ["ê¸°ëŠ¥??, "Functionality"]: default_sub_val = _("?˜ë“œ?¨ì–´, ?Œí”„?¸ì›¨??, "Hardware, Software")
                elif mc in ["?”ì??, "Design"]: default_sub_val = _("?¸ê?, ?¸ì˜??, "Appearance, Usability")
                elif mc in ["ê²½ì œ??, "Economy"]: default_sub_val = _("?¨ë§ê¸°ê?ê²? ? ì?ë¹„ìš©", "Device Price, Maintenance Cost")

                sub_input = st.text_input(_(f"'{mc}'???˜ìœ„ ?”ì¸ (Sub-criteria)", f"Sub-criteria for '{mc}'"), value=st.session_state.get("edit_sub_inputs", {}).get(mc, default_sub_val))
                subs_list = [x.strip().replace("_", " ") for x in sub_input.split(",") if x.strip()]
                model_structure["subs"][mc] = subs_list

                # [? ê·œ] 3ê³„ì¸µ ? íƒ ???Œë¶„ë¥??…ë ¥ ?„ë“œ ?™ì  ?ì„±
                if tier_level == 3 and subs_list:
                    with st.expander(_(f"??'{mc}' ?˜ìœ„???Œë¶„ë¥?(Sub-sub-criteria) ?…ë ¥", f"??Enter Sub-sub-criteria under '{mc}'"), expanded=True):
                        st.info(_("?’¡ **?¼í•© ê³„ì¸µ ?ˆë‚´**: ?Œë¶„ë¥?3ê³„ì¸µ)ê°€ ?†ëŠ” ??ª©?€ **ë¹„ì›Œ?ì‹œë©??ë™?¼ë¡œ 2ê³„ì¸µ ê°€ì¤‘ì¹˜ë¡?ê³„ì‚°**?©ë‹ˆ??", "?’¡ **Mixed-Tier Guide**: If a sub-criterion has no sub-sub-criteria, **leave it blank to automatically calculate as a 2-tier weight**."))
                        for sub_c in subs_list:
                            sub_sub_val = "" # 3ê³„ì¸µ ê¸°ë³¸ê°’ì? ë¹ˆì¹¸
                            if sub_c in ["?˜ë“œ?¨ì–´", "Hardware"]: sub_sub_val = _("ì¹´ë©”?? ë°°í„°ë¦? ?„ë¡œ?¸ì„œ", "Camera, Battery, Processor")
                            elif sub_c in ["?Œí”„?¸ì›¨??, "Software"]: sub_sub_val = _("?´ì˜ì²´ì œ, ê¸°ë³¸??, "OS, Default Apps")
                            elif sub_c in ["?¸ê?", "Appearance"]: sub_sub_val = _("?‰ìƒ, ?¬ì§ˆ", "Color, Material")
                            elif sub_c in ["?¨ë§ê¸°ê?ê²?, "Device Price"]: sub_sub_val = _("?¼ì‹œë¶? ? ë?", "Lump Sum, Installment")
                            elif sub_c in ["? ì?ë¹„ìš©", "Maintenance Cost"]: sub_sub_val = _("?µì‹ ?”ê¸ˆ, ASë¹„ìš©", "Telecom Fee, A/S Cost")
                        
                            sub_sub_input = st.text_input(
                                f"?‘‰ '{sub_c}'???˜ìœ„ ?”ì¸ (?¼í‘œ êµ¬ë¶„)", 
                                value=st.session_state.get("edit_sub_sub_inputs", {}).get(sub_c, sub_sub_val),
                                placeholder="?? ??ª©1, ??ª©2 (???˜ìœ„ ?”ì¸???†ë‹¤ë©?ë¹„ì›Œ?ì„¸??",
                                help="?…ë ¥ì¹¸ì„ ë¹„ì›Œ?ë©´ ????ª©?€ ?ë™?¼ë¡œ 2ê³„ì¸µ êµ¬ì¡°ë¡?ê°„ì£¼?˜ì–´ ë¶„ì„?©ë‹ˆ??",
                                key=f"sub_sub_{sub_c}"
                            )
                            # ?Œë¶„ë¥˜ê? ?…ë ¥??ê²½ìš°?ë§Œ ?€?? ?†ìœ¼ë©?ë¬´ì‹œ
                            parsed_sub_subs = [x.strip().replace("_", " ") for x in sub_sub_input.split(",") if x.strip()]
                            if parsed_sub_subs:
                                model_structure["sub_subs"][sub_c] = parsed_sub_subs

            st.caption(_("???ë?ë¹„êµ ?œì‘ ???‘ë‹µ?ê? ?„ë°˜???”ì¸ ?œìœ„ë¥?ë§¤ê¸°??'?¬ì „ ì¤‘ìš”???œìœ„ ì§€??ë¬¸í•­'?€ ?ë™?¼ë¡œ ?¤ë¬¸???¬í•¨?©ë‹ˆ??", "??A 'Prior Importance Ranking Question', where respondents rank the overall criteria before starting pairwise comparisons, is automatically included in the survey."))

            st.divider()

            # ?¹ì…˜ 3: ?”ì¸ ì¡°ì‘???•ì˜ ?¤ì •
            st.subheader(_("?¹ì…˜ 3: ?”ì¸ë³??ì„¸ ?¤ëª… (ì¡°ì‘???•ì˜)", "Section 3: Detailed Description per Criteria (Operational Definition)"))
            st.info(_("?‘ë‹µ?ê? ?”ì¸ ê°œë…??ì§ê??ìœ¼ë¡??Œì•…?????ˆë„ë¡??ì„¸ ?¤ëª…??ê¸°ìˆ ??ì£¼ì‹­?œì˜¤.", "Please provide detailed descriptions so respondents can intuitively understand each criteria concept."))
            definitions_map = {}
            for mc in main_list:
                # ?€ë¶„ë¥˜ëª??Œë???ë³¼ë“œ ë°??´ëª¨?°ì½˜???´ìš©???€ì¡??¤ì •
                st.markdown(_(f"#### ?Ÿ¦ :blue[**?€ë¶„ë¥˜: {mc}**]", f"#### ?Ÿ¦ :blue[**Main Criteria: {mc}**]"))
                default_main_def = ""
                if mc in ["ê¸°ìˆ  ?”ì¸", "Technological"]: default_main_def = _("?‘ë™ë¡œë´‡ ?„ì… ??ê¸°ìˆ ???±ëŠ¥, ?¸í™˜?? ?ˆì „??ë°?ê¸°ìˆ  ì§€????ê¸°ìˆ  ì¸¡ë©´???”ì¸", "Factors related to the technological aspect such as technical performance, compatibility, safety, and technical support.")
                elif mc in ["ì¡°ì§ ?”ì¸", "Organizational"]: default_main_def = _("?‘ë™ë¡œë´‡ ?„ì…ê³?ê´€?¨ëœ ì¡°ì§ ?´ë?????Ÿ‰, ê²½ì˜ì§?ì§€?? ?¬ë¬´ ë°?êµìœ¡ ?íƒœ ?”ì¸", "Factors related to the internal capabilities of the organization, top management support, financial and training status.")
                elif mc in ["?˜ê²½ ?”ì¸", "Environmental"]: default_main_def = _("?•ë? ì§€?? ?°ì—… ??ê²½ìŸ ?•ë ¥, êµ¬ì¸??ë°??¸ë? ?‘ë ¥ ???¸ë? ?˜ê²½???”ì¸", "External environmental factors such as government support, competitive pressure within the industry, labor shortage, and external cooperation.")
                elif mc in ["?ì‹  ?”ì¸", "Innovational"]: default_main_def = _("ê²½ì˜ì§„ì˜ ?ì‹  ì§€?¥ì„±, êµ¬ì„±?ì˜ ë³€???˜ìš©??ë°??¤ë§ˆ???©í† ë¦?ì§€??ê¸°ìˆ  ?˜ì? ?”ì¸", "Factors such as the management's innovation orientation, members' acceptance of change, and smart factory knowledge/skill levels.")

                edit_def_val = st.session_state.get("edit_definitions", {}).get(mc)
                val_to_use = edit_def_val if edit_def_val is not None else (default_main_def or _(f"{mc}???€???„ë°˜???”ì†Œë¥??¤ëª…?©ë‹ˆ??", f"Overall description for {mc}."))
                val_to_use = translate_definition_if_default(mc, val_to_use)

                definitions_map[mc] = st.text_input(
                    _(f"?‘‰ [{mc}] ?”ì¸???„ì²´?ì¸ ?¤ëª… ?…ë ¥", f"?‘‰ Enter overall description for [{mc}]"),
                    value=val_to_use,
                    key=f"def_main_{mc}"
                )

                # ì¤‘ë¶„ë¥˜ë“¤?€ ?°ê? ê´€ê³„ë? ë¬¶ì„ ???ˆë„ë¡??œê°?ìœ¼ë¡?êµ¬ë¶„???Œë‘ë¦?ì»¨í…Œ?´ë„ˆ ?ˆì— ë°°ì¹˜
                with st.container(border=True):
                    for sc in model_structure["subs"].get(mc, []):
                        # ê¸°ë³¸ ?‘ìŠ¹???¤ë¬¸ ?•ì˜ ?ìš©
                        default_def = ""
                        if sc in ["?ë??ì´??, "Relative Advantage"]: default_def = _("?„ì…?€???‘ë™ë¡œë´‡ê°„ì˜ ?ë????´ì ", "Relative advantage among the collaborative robots targeted for adoption.")
                        elif sc in ["?¸í™˜??, "Compatibility"]: default_def = _("ê¸°ì¡´ ?¤ë¹„???€???‘ë™ë¡œë´‡ê³¼ì˜ ?°ê²°??, "Connectivity with existing equipment or third-party collaborative robots.")
                        elif sc in ["?ˆì „??, "Security"]: default_def = _("?‘ì—…?ì? ê°™ì? ê³µê°„?ì„œ ?ˆì „ ?œìŠ¤ ?†ì´ ?‘ì—…???Œì˜ ?¸ì  ?¬ê³  ?ˆë°© ?˜ì?", "Level of human accident prevention when working in the same space as operators without safety fences.")
                        elif sc in ["?œë¹„?¤ì???, "Service Support"]: default_def = _("ê³µê¸‰?¬ì˜ ê¸°ìˆ  ë°?A/S ì§€???•ë„", "Degree of technical and A/S support from the supplier.")
                        elif sc in ["ê²½ì˜ì§„ì???, "Top Management Support"]: default_def = _("ê²½ì˜ì§„ì˜ ?„ì… ?˜ì? ë°?ê²½ì˜ì² í•™ ë°˜ì˜??, "The management's willingness to adopt and the degree to which management philosophy is reflected.")
                        elif sc in ["ê¸°ìˆ ì¤€ë¹„ë„", "Tech Readiness"]: default_def = _("ì¡°ì§?ì˜ ë¡œë´‡ ?œìš© ê¸°ìˆ  ì¤€ë¹??˜ì?", "The level of technical readiness of organizational members to utilize robots.")
                        elif sc in ["ê¸ˆìœµ?ì›", "Financial Resources"]: default_def = _("ë¡œë´‡ êµ¬ì…???„í•œ ?ë³¸ ?¬ë ¥ ë°??ê¸ˆ ì¡°ë‹¬ ?¸ì˜??, "Capital capacity and financing convenience for purchasing robots.")
                        elif sc in ["êµìœ¡?ˆë ¨", "Training"]: default_def = _("ê¸°ìˆ  ?¥ìƒ???„í•œ ?„íƒ/?¬ë‚´ êµìœ¡ ?„ë¡œê·¸ë¨ ? ë¬´", "Availability of external/internal training programs for skill improvement.")
                        elif sc in ["?•ë?ì§€??, "Gov Support"]: default_def = _("?‘ë™ë¡œë´‡ ?„ì…???œì„±?”í•˜ê¸??„í•œ ?•ë????¬ì • ì§€??ë°?ë³´ì¡°ê¸??œíƒ ?•ë„", "Degree of government financial support and subsidy benefits to promote the adoption of collaborative robots.")
                        elif sc in ["ê²½ìŸ?•ë ¥", "Competitive Pressure"]: default_def = _("?™ì¢… ?…ê³„ ?ëŠ” ê²½ìŸ?¬ì˜ ?‘ë™ë¡œë´‡ ?„ì…???°ë¥¸ ê²½ìŸ???•ë°• ?•ë„", "Degree of competitive pressure due to the adoption of collaborative robots by peers or competitors.")
                        elif sc in ["?¸ë ¥??, "Labor Shortage"]: default_def = _("?œì¡° ?„ì¥??êµ¬ì¸??ë°??ì‚° ?¸ë ¥ ?˜ê¸‰???´ë ¤?€ ?˜ì?", "Level of difficulty in finding labor and supplying production personnel at the manufacturing site.")
                        elif sc in ["?¸ë?ì§€??, "External Support"]: default_def = _("ë¡œë´‡ ê³µê¸‰???¸ì˜ ?¸ë? ì»¨ì„¤?? ?°êµ¬ê¸°ê? ?±ì˜ ê¸°ìˆ ??êµìœ¡??ì§€??, "Technical/educational support from external consulting, research institutes, etc., other than the robot supplier.")
                        elif sc in ["ê²½ì˜ì§„ì˜ ?ì‹ ??, "Management Innovativeness"]: default_def = _("?ˆë¡œ???œì¡° ê¸°ìˆ  ë°?ë¡œë´‡ ?„ì…???€??ìµœê³ ê²½ì˜?ì˜ ?ê·¹?ì¸ ?˜ì?", "The top management's active willingness to adopt new manufacturing technologies and robots.")
                        elif sc in ["ë³€?”ìˆ˜?©íƒœ??, "Change Acceptance"]: default_def = _("? ê·œ ?¥ë¹„ ë°??‘ì—… ?„ë¡œ?¸ìŠ¤ ë³€?”ì— ?€??êµ¬ì„±?ë“¤???˜ìš© ë°??‘ì¡° ?œë„", "Members' acceptance and cooperative attitude towards changes in new equipment and work processes.")
                        elif sc in ["?¤ë§ˆ?¸íŒ©? ë¦¬?˜ì?", "Smart Factory Level"]: default_def = _("ê³µì¥ ???”ì??¸í™”, ?•ë³´?œìŠ¤??MES ?? ë°??ë™??ê¸°ìˆ ???„ì¬ êµ¬ì¶• ?˜ì?", "Current level of implementation of digitalization, information systems (MES, etc.), and automation technology in the factory.")
                        elif sc in ["ì§€?ì •??, "Knowledge Level"]: default_def = _("?‘ë™ë¡œë´‡ ?œìš© ë°?? ì? ê´€ë¦¬ì— ?„ìš”??ì¡°ì§ ???„ë¬¸ ì§€???˜ì?", "Level of internal expertise required for the utilization and maintenance of collaborative robots.")

                        edit_sub_def_val = st.session_state.get("edit_definitions", {}).get(sc)
                        sub_val_to_use = edit_sub_def_val if edit_sub_def_val is not None else (default_def or _(f"{sc}???€???•ì˜?…ë‹ˆ??", f"Definition for {sc}."))
                        sub_val_to_use = translate_definition_if_default(sc, sub_val_to_use)

                        definitions_map[sc] = st.text_input(
                            _(f"??ì¤‘ë¶„ë¥?[{sc}] ?¤ëª… ?…ë ¥", f"?‘‰ Enter description for sub-criteria [{sc}]"),
                            value=sub_val_to_use,
                            key=f"def_sub_{sc}"
                        )
                st.write("") # ?¹ì…˜ ê°??œê°???¬ë°± ì¶”ê?

            st.divider()

            # ?¹ì…˜ 4: ì²™ë„ ?¸í„°?˜ì´???¤ì •
            st.subheader(_("?¹ì…˜ 4: ?ë?ë¹„êµ ?‘ë‹µ ì²™ë„ ?¤ì •", "Section 4: Pairwise Comparison Scale Setup"))
            scale_options = [
                _("1-9 Continuous (1ë¶€??9ê¹Œì? ?°ì†???¤ì???", "1-9 Continuous Scale"),
                _("1-3-7-9 Discrete (?´ì‚°??ì²™ë„)", "1-3-7-9 Discrete Scale"),
                _("1-3-5 Discrete (?´ì‚°??ì²™ë„)", "1-3-5 Discrete Scale")
            ]
            scale_option = st.radio(_("?‘ë‹µ ì²™ë„ ?€??, "Response Scale Type"), scale_options, index=0)

            st.divider()

            # ?¹ì…˜ 5: ?µë???ë°?ê°œì¸?•ë³´ ?˜ì§‘ ?™ì˜ ?¤ì •
            st.subheader(_("?¹ì…˜ 5: ?µë???ë°??™ì˜ ?‘ì‹ ?¤ì •", "Section 5: Reward & Consent Form Setup"))
            reward_enabled = st.toggle(_("?µë???ê¸°í”„?°ì½˜ ?? ?œê³µ ?œì„±??, "Enable Rewards (e.g., Gifticons)"))
            reward_desc = ""
            if reward_enabled:
                reward_desc = st.text_area(_("?µë????¤ëª…", "Reward Description"), value=st.session_state.get("edit_reward_desc", "ëª¨ë“  ?¤ë¬¸ ?‘ë‹µ??ë§ˆì¹œ ë¶„ë“¤?ê²Œ ?¤í?ë²…ìŠ¤ ?„ë©”ë¦¬ì¹´??ê¸°í”„?°ì½˜??ë°œì†¡???œë¦½?ˆë‹¤."))

            rewards_info = {
                "enabled": reward_enabled,
                "desc": reward_desc
            }

            st.divider()

            # ?¹ì…˜ 6: ?¤ì‹œê°?CR ê²€ì¦??ˆë²¨ ?¤ì •
            st.subheader(_("?¹ì…˜ 6: ?¼ê???ë¹„ìœ¨ (CR) ê²€ì¦??ˆë²¨", "Section 6: Consistency Ratio (CR) Validation Level"))
            # Get default index from edit state if editing, otherwise default to index 4 (0.3 ?´í•˜)
            default_cr_idx = 4
            if st.session_state.get("editing_survey_id") and st.session_state.get("edit_cr_limit") is not None:
                cr_val = float(st.session_state.get("edit_cr_limit"))
                if cr_val <= 0.1: default_cr_idx = 1
                elif cr_val <= 0.15: default_cr_idx = 2
                elif cr_val <= 0.2: default_cr_idx = 3
                elif cr_val <= 0.3: default_cr_idx = 4
            elif st.session_state.get("editing_survey_id") and st.session_state.get("edit_cr_limit") is None:
                default_cr_idx = 0
            
            cr_limit_opt = st.selectbox(_("?¼ê???ë¹„ìœ¨(CR) ?ˆìš© ê¸°ì?ì¹?, "Consistency Ratio (CR) Tolerance Limit"), [
                _("?œí•œ?˜ì? ?ŠìŒ (?´íƒˆë¥?ê°ì†Œ??", "No Limit (To reduce drop-out rate)"),
                _("0.1 ?´í•˜ (ë§¤ìš° ?„ê²©??", "0.1 or below (Very Strict)"),
                _("0.15 ?´í•˜ (?„ê²©??", "0.15 or below (Strict)"),
                _("0.2 ?´í•˜ (ë³´í†µ)", "0.2 or below (Normal)"),
                _("0.3 ?´í•˜ (?¼ë? ?ˆìš©)", "0.3 or below (Somewhat Lenient)")
            ], index=default_cr_idx)

            cr_limit = None
            if "0.15" in cr_limit_opt: cr_limit = 0.15
            elif "0.1" in cr_limit_opt: cr_limit = 0.1
            elif "0.2" in cr_limit_opt: cr_limit = 0.2
            elif "0.3" in cr_limit_opt: cr_limit = 0.3

            if cr_limit is not None:
                st.warning(_("? ï¸ ?¼ê???ë¹„ìœ¨(CR) ê¸°ì????ˆë¬´ ?„ê²©?˜ê²Œ(??²Œ) ?¤ì •??ê²½ìš°, ?¼ë¦¬??ëª¨ìˆœ???ˆëŠ” ?¤ë¬¸???€ê±?ë¬´íš¨ ì²˜ë¦¬?˜ì–´ ?‘ë‹µ?ì˜ ?¬ê????¼ë¡œ?„ê? ê·¹ë??”ë˜ê³??¤ë¬¸ ?´íƒˆë¥ ì´ ê¸‰ì¦?????ˆìœ¼??? ì˜?˜ì‹œê¸?ë°”ë?ˆë‹¤. ?‘ë‹µ???´íƒˆ????¶”ê¸??„í•´ ?¼ê???ë¹„ìœ¨ ?ˆìš© ê¸°ì?ì¹˜ë? 0.3 ?´í•˜ë¡??¬ìœ ë¡?²Œ ?¤ì •?˜ê³ , ?°ì´???˜ì§‘ ??AHPë§ˆìŠ¤?°ì˜ ?¼ê???ë³´ì • ê¸°ëŠ¥???µí•´ ?¬í›„ ë³´ì •?˜ì—¬ ë¶„ì„?˜ì‹œê¸°ë? ?ê·¹ ì¶”ì²œ?œë¦½?ˆë‹¤.", "? ï¸ Warning: If the CR limit is set too strict (low), many logically inconsistent surveys will be invalidated. This maximizes respondent fatigue and can cause the survey drop-out rate to spike. To reduce respondent dropout, we strongly recommend setting the consistency ratio tolerance to 0.3 or less and post-calibrating the collected data using the AHP Master consistency calibration feature."))
                # CR ê°€?´ë“œ ë°©ì‹ ? íƒ
                st.markdown(_("**?‘ë‹µ???¼ê???? ì?(CR) ê°€?´ë“œ ë°©ì‹ ? íƒ**", "**Select Consistency Ratio (CR) Guide Method for Respondents**"))
            
                default_guide = st.session_state.get("edit_cr_guide_method", "realtime")
            
                # Backward compatibility for old surveys that used toggle
                if "edit_cr_guide_enabled" in st.session_state:
                    if st.session_state["edit_cr_guide_enabled"] and default_guide not in ["realtime", "post_wizard", "none"]:
                        default_guide = "realtime"
                    elif not st.session_state["edit_cr_guide_enabled"] and default_guide not in ["realtime", "post_wizard", "none"]:
                        default_guide = "none"
            
                options_kr = {
                    "realtime": "?¤ì‹œê°?ê¶Œì¥ ë²”ìœ„ ?œê°???ˆë‚´ (?´íƒˆë¥?ìµœì†Œ?? ?¸ì˜???’ìŒ)",
                    "post_wizard": "?œì¶œ ??ì§€?¥í˜• ?˜ì • ?œì•ˆ ë§ˆë²•??(ê°€???™ìˆ ?ì¸ ë°©ì‹, ?¸í–¥???œê±°)",
                    "none": "?¼ê???ê°€?´ë“œ ?†ìŒ(?„ê²©??ê²€ì¦ë§Œ ?˜í–‰)"
                }
                options_en = {
                    "realtime": "Real-time Visual Range Guide (Minimizes dropout, high convenience)",
                    "post_wizard": "Post-Submission Smart Fix Wizard (Most academic, removes bias)",
                    "none": "No Guide (Strict validation only)"
                }
            
                def get_idx(val):
                    keys = list(options_kr.keys())
                    return keys.index(val) if val in keys else 0
                
                selected_idx = st.radio(
                    label=_("ê°€?´ë“œ ë°©ì‹??? íƒ?˜ì„¸??, "Choose guide method"),
                    options=[0, 1, 2],
                    format_func=lambda x: options_kr[list(options_kr.keys())[x]] if _("ko", "en") == "ko" else options_en[list(options_en.keys())[x]],
                    index=get_idx(default_guide),
                    label_visibility="collapsed"
                )
            
                cr_guide_method = list(options_kr.keys())[selected_idx]
            
                if cr_guide_method == "realtime":
                    st.info(_("?’¡ **?¤ì‹œê°??ˆë‚´**: ?‘ë‹µ?ê? ?¤ë¬¸ ì¤??¼ê??±ì„ ? ì??????ˆë„ë¡??Œë???ë°°ê²½?¼ë¡œ ê¶Œì¥?˜ëŠ” ?ˆìš© ë²”ìœ„ë¥??ˆë‚´?©ë‹ˆ?? ?¸ì˜?±ì´ ?’ê³  ?´íƒˆë¥ ì„ ?¬ê²Œ ??¶œ ???ˆìŠµ?ˆë‹¤.", "?’¡ **Real-time Guide**: Highlights the recommended range with a blue background to help respondents maintain consistency. Highly convenient and reduces dropouts."))
                elif cr_guide_method == "post_wizard":
                    st.success(_("?’¡ **ì§€?¥í˜• ?˜ì • ?œì•ˆ (ì¶”ì²œ)**: ?‘ë‹µ ì¤‘ì—???„ë¬´??ê°€?´ë“œë¥?ì£¼ì? ?Šì•„ ?‘ë‹µ?ì˜ ì§„ì§œ ?ê°???¸í–¥ ?†ì´ ?˜ì§‘?©ë‹ˆ?? ?œì¶œ ë²„íŠ¼???Œë?????CR??ì´ˆê³¼?˜ë©´, ê°€??ëª¨ìˆœ??????1ê°?ë¬¸í•­??ì°¾ì•„?´ì–´ ?˜ì •??ê¶Œê³ ?˜ëŠ” ë§ˆë²•?¬ë? ?„ì›?ˆë‹¤.", "?’¡ **Smart Fix Wizard (Recommended)**: Collects true thoughts without bias by providing no guide during response. If CR exceeds the limit upon submission, a wizard will appear to suggest fixing the single most contradictory question."))
                else:
                    st.warning(_("?’¡ **?ˆë‚´ ?†ìŒ**: ?‘ë‹µ?ì—ê²??´ë–¤ ?ŒíŠ¸??ì£¼ì? ?Šìœ¼ë©? ?œì¶œ ??CR??ì´ˆê³¼?˜ë©´ ?ëŸ¬ ë©”ì‹œì§€?€ ?¨ê»˜ ?„ì²´ ?¬ê?? ë? ?”êµ¬?©ë‹ˆ?? ?´íƒˆë¥ ì´ ?’ì•„ì§????ˆìŠµ?ˆë‹¤.", "?’¡ **No Guide**: Gives no hints. If CR is exceeded upon submission, an error message is shown requiring a full review. Dropouts may increase."))
            else:
                cr_guide_method = "none"

            st.divider()

            # ?¹ì…˜ 7: ìµœì¢… ë¯¸ë¦¬ë³´ê¸° ë°?ë°°í¬
            st.subheader(_("?¹ì…˜ 7: ?€????ìµœì¢… ë¯¸ë¦¬ë³´ê¸° ë°?ë°°í¬", "Section 7: Final Preview & Deployment Before Saving"))

            # [ì¶”ê?] êµ¬ê? ?¤í”„?ˆë“œ?œíŠ¸ ?°ë™ ?¤ì •
            if st.session_state.get('editing_survey_id'):
                st.markdown(_("##### ?™ï¸ ê¸°ì¡´ êµ¬ê? ?¤í”„?ˆë“œ?œíŠ¸ ?°ë™ (?˜ì • ëª¨ë“œ)", "##### ?™ï¸ Existing Google Spreadsheet Integration (Edit Mode)"))
                st.info(_("?„ì¬ **ê¸°ì¡´ ?¤ë¬¸ ?˜ì • ëª¨ë“œ**ë¡?ì§„ì…?ˆìŠµ?ˆë‹¤. ?˜ì •???¤ì • ?´ìš©?€ ê¸°ì¡´ ?°ë™??êµ¬ê? ?¤í”„?ˆë“œ?œíŠ¸???ˆì „?˜ê²Œ ??–´?Œì›Œì§‘ë‹ˆ??", "You have entered **Existing Survey Edit Mode**. The modified settings will be safely overwritten to the existing linked Google Spreadsheet."))
                existing_sheet_id_input = st.session_state.editing_survey_id
            else:
                st.markdown(_("##### ?™ï¸ ?°ë™??ë³¸ì¸??êµ¬ê? ?¤í”„?ˆë“œ?œíŠ¸ ?¤ì • *", "##### ?™ï¸ Setup Your Google Spreadsheet to Link *"))
                st.info(_("""
                **?’¡ ?°ë™ ë°©ë²•:**
                1. ë³¸ì¸??êµ¬ê? ?œë¼?´ë¸Œ?ì„œ **??êµ¬ê? ?¤í”„?ˆë“œ?œíŠ¸**ë¥??˜ë‚˜ ?ì„±?©ë‹ˆ?? (ë³¸ì¸ ê³„ì • ?©ëŸ‰ ?´ì—???ì„±?˜ë?ë¡??©ëŸ‰ ì´ˆê³¼ ?¤ë¥˜ê°€ ë°œìƒ?˜ì? ?ŠìŠµ?ˆë‹¤.)
                2. ?°ì¸¡ ?ë‹¨??'ê³µìœ ' ë²„íŠ¼???ŒëŸ¬ ?„ë˜???œë¹„??ê³„ì • ?´ë©”?¼ì„ **?¸ì§‘??* (Editor)ë¡?ì¶”ê??©ë‹ˆ??
                   * ?œë¹„??ê³„ì • ?´ë©”?? `ahp-master-v2@ahp-login.iam.gserviceaccount.com`
                3. ?ì„±???¤í”„?ˆë“œ?œíŠ¸??**URL ì£¼ì†Œ** ?ëŠ” **?œíŠ¸ ID**ë¥?ë³µì‚¬?˜ì—¬ ?„ë˜??ë¶™ì—¬?£ì–´ ì£¼ì„¸?? (?„ë˜ ?ˆì‹œ ?´ë?ì§€ ì°¸ê³ )
                """, """
                **?’¡ How to link:**
                1. Create a **New Google Spreadsheet** in your Google Drive. (This uses your account storage, so there will be no quota errors on our side.)
                2. Click the 'Share' button on the top right and add the following service account email as an **Editor**.
                   * Service Account Email: `ahp-master-v2@ahp-login.iam.gserviceaccount.com`
                3. Copy the **URL** or **Sheet ID** of the created spreadsheet and paste it below. (See the example image below)
                """))
                col1, col2 = st.columns([1, 2])
                with col1:
                    if os.path.exists("google_sheets_menu_guide.png"):
                        st.image("google_sheets_menu_guide.png", caption=_("êµ¬ê? ?¤í”„?ˆë“œ?œíŠ¸ ë©”ë‰´ ?‘ê·¼ ë°©ë²•", "How to access Google Sheets menu"), use_container_width=True)
                with col2:
                    st.image("manual_sheet_url_guide.png", caption=_("êµ¬ê? ?¤í”„?ˆë“œ?œíŠ¸ URL ì£¼ì†Œì°?ë³µì‚¬ ?ˆì‹œ", "Example of copying Google Spreadsheet URL"), use_container_width=True)
                existing_sheet_id_input = st.text_input(_("?°ë™??êµ¬ê? ?¤í”„?ˆë“œ?œíŠ¸ URL ?ëŠ” ID *", "Google Spreadsheet URL or ID to link *"), placeholder="https://docs.google.com/spreadsheets/d/...")
                st.warning(_(
                    "?“¢ **[RAW ?°ì´??ë³´ê? ë°?ë°±ì—… ?˜ë¬´ ?ˆë‚´]**\n\n"
                    "??êµ¬ê? ?¤í”„?ˆë“œ?œíŠ¸???€?¥ë˜??RAW ?°ì´?°ëŠ” **?ì„±?¼ë¡œë¶€??6ê°œì›”ê°?? ì??????ë™ ?? œ**?©ë‹ˆ??\n"
                    "??ì¡°ì‚¬ê°€ ?„ë£Œ?˜ë©´ ë°˜ë“œ??ë³¸ì¸??ì»´í“¨?°ì— ?‘ì?(.xlsx) ?ëŠ” CSV ?Œì¼ë¡??°ì´?°ë? ?¤ìš´ë¡œë“œ?˜ì—¬ **ë°±ì—…**??ì£¼ì‹œê¸?ë°”ë?ˆë‹¤.\n"
                    "???ì„± ??6ê°œì›”??ì§€???œì ??ê°€?…í•˜???´ë©”??ID)ë¡??¬ì „ ?? œ ë°?ë°±ì—… ?ˆë‚´ ë©”ì¼??ë°œì†¡?˜ë©°, ë©”ì¼ ë°œì†¡ 10????êµ¬ê? ?œíŠ¸ê°€ ?ë™ ?? œ?©ë‹ˆ??",
                    "?“¢ **[RAW Data Retention & Mandatory Backup Notice]**\n\n"
                    "??RAW data stored in Google Spreadsheets is **retained for 6 months from creation and then automatically deleted**.\n"
                    "??When your survey is completed, you MUST download and **backup** the data to your computer as an Excel (.xlsx) or CSV file.\n"
                    "??At 6 months post-creation, a deletion and backup notification email will be sent to your registered email (ID), and the Google Sheet will be deleted 10 days after the email notification."
                ))




            # Save current state for preview tab
            preview_id = f"preview_{st.session_state.user_id if st.session_state.user_id else 'guest'}"
            preview_data = {
                "Title": survey_title,
                "Description": survey_desc,
                "Admin_Email": survey_admin_email,
                "AHP_Model_JSON": model_structure,
                "Tier_Level": tier_level, # [? ê·œ] 3ê³„ì¸µ êµ¬ë¶„??
                "Scale_Type": scale_option,
                "Demographics": demographics_settings,
                "Definitions": definitions_map,
                "CR_Limit": cr_limit,
                "CR_Guide_Method": cr_guide_method,
                "Rewards_Info": rewards_info
            }

            st.session_state[f"_preview_data_{preview_id}"] = preview_data

            col_p1, col_p2 = st.columns(2)
            with col_p1:
                preview_link_html = f"""
                <a href="/?preview_id={preview_id}" target="_blank" style="text-decoration: none;">
                    <div style="
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        width: 100%;
                        padding: 0.375rem 0.75rem;
                        border: 1px solid rgba(49, 51, 63, 0.2);
                        border-radius: 4px;
                        background-color: #ffffff;
                        color: #31333f;
                        font-size: 14px;
                        font-weight: 400;
                        line-height: 1.6;
                        cursor: pointer;
                        text-align: center;
                        box-sizing: border-box;
                        transition: border-color 0.2s, color 0.2s, background-color 0.2s;
                    "
                    onmouseover="this.style.borderColor='#ff4b4b'; this.style.color='#ff4b4b';"
                    onmouseout="this.style.borderColor='rgba(49, 51, 63, 0.2)'; this.style.color='#31333f';"
                    >
                        {_("?‘ï¸??¤ë¬¸ì§€ ?‘ë‹µ ?”ë©´ ë¯¸ë¦¬ë³´ê¸°", "?‘ï¸?Preview Survey Form")}
                    </div>
                </a>
                """
                st.markdown(preview_link_html, unsafe_allow_html=True)

            with col_p2:
                if st.session_state.user_id is None:
                    btn_label = _("?”’ ë¬´ë£Œ ?Œì›ê°€????ë°°í¬?˜ê¸°", "?”’ Deploy after Free Sign Up")
                    if st.button(btn_label, type="primary", use_container_width=True):
                        st.warning(_("?”’ ë°°í¬ ë°?DB ?°ë™?€ ?Œì›ê°€????ê°€?¥í•©?ˆë‹¤. (ë¬´ë£Œ ?¬ìš©?ë„ ?œí•œ ?†ì´ ë°°í¬ ë°??°ë™ ê°€?¥í•¨)", "?”’ Deployment and DB integration are available after sign-up. (Free users can also deploy and link DB)"))
                        st.info(_("?’¡ ?ˆì‹¬?˜ì„¸?? ?„ì¬ ?‘ì„±?˜ì‹  ?´ìš©?€ ì°½ì„ ?«ì? ?Šê³  ?¼ìª½ ?¬ì´?œë°”?ì„œ ?Œì›ê°€??ë¡œê·¸?¸ì„ ?„ë£Œ?˜ì‹œë©?? ì•„ê°€ì§€ ?Šê³  ê·¸ë?ë¡?? ì??˜ì–´ ì¦‰ì‹œ ë°°í¬?˜ì‹¤ ???ˆìŠµ?ˆë‹¤.", "?’¡ Rest assured. The contents you have written will be maintained if you sign up and log in from the left sidebar without closing the window, allowing you to deploy immediately."))
                    
                        # ë¡œê·¸???¨ë„(?¬ì´?œë°”) ê°•ì¡° ? ë‹ˆë©”ì´??ì£¼ì…
                        highlight_html = """
                        <style>
                        @keyframes pulse-sidebar {
                            0% { box-shadow: inset -5px 0 15px rgba(255, 75, 75, 0.8); }
                            50% { box-shadow: inset -5px 0 30px rgba(255, 75, 75, 0.2); }
                            100% { box-shadow: inset -5px 0 15px rgba(255, 75, 75, 0.8); }
                        }
                        .floating-arrow {
                            position: fixed;
                            top: 20%;
                            left: 330px; /* ?¬ì´?œë°” ?ˆë¹„ ê³ ë ¤ */
                            font-size: 60px;
                            color: #ff4b4b;
                            z-index: 9999999;
                            pointer-events: none;
                            animation: bounce-left 0.8s infinite alternate;
                            text-shadow: 2px 2px 5px rgba(0,0,0,0.3);
                        }
                        @keyframes bounce-left {
                            from { transform: translateX(20px); }
                            to { transform: translateX(0px); }
                        }
                        </style>
                        <div class="floating-arrow">?‘ˆ</div>
                        <script>
                            const sidebar = window.parent.document.querySelector('[data-testid="stSidebar"]');
                            if (sidebar) {
                                sidebar.style.animation = 'pulse-sidebar 1.5s infinite';
                                sidebar.style.borderRight = '4px solid #ff4b4b';
                                setTimeout(() => {
                                    sidebar.style.animation = '';
                                    sidebar.style.borderRight = '';
                                }, 5000);
                            }
                        </script>
                        """
                        import streamlit.components.v1 as components
                        components.html(highlight_html, height=0, width=0)
                else:
                    btn_label = _("?? ë°°í¬ ë°?DB ?°ë™ (?˜ì • ?´ìš© ?ìš©)", "?? Deploy & Link DB (Apply Changes)") if st.session_state.get("editing_survey_id") else _("?? ë°°í¬ ë°?DB ?°ë™", "?? Deploy & Link DB")
                    if st.button(btn_label, type="primary", use_container_width=True):
                        if not existing_sheet_id_input.strip():
                            st.error(_("?°ë™??êµ¬ê? ?¤í”„?ˆë“œ?œíŠ¸ URL ?ëŠ” IDë¥?ë°˜ë“œ???…ë ¥?´ì•¼ ?©ë‹ˆ??", "You must enter the Google Spreadsheet URL or ID to link."))
                            import streamlit.components.v1 as components
                            alert_msg = _("?°ë™??êµ¬ê? ?¤í”„?ˆë“œ?œíŠ¸ URL???…ë ¥?˜ì? ?Šìœ¼ë©?ë°°í¬ ë°??°ë™???˜ì? ?ŠìŠµ?ˆë‹¤.\\në³¸ì¸??êµ¬ê? ?¤í”„?ˆë“œ?œíŠ¸ URL ?ëŠ” IDë¥?ë°˜ë“œ???…ë ¥??ì£¼ì„¸??", "Deployment and linking will fail without a Google Spreadsheet URL.\\nPlease make sure to enter your Google Spreadsheet URL or ID.")
                            components.html(f"<script>alert('{alert_msg}');</script>", height=0, width=0)
                        elif not survey_admin_email or "@" not in survey_admin_email:
                            st.error(_("êµ¬ê? ?œíŠ¸ ?Œìœ ê¶?ê³µìœ ë¥??„í•œ ?´ë©”??ì£¼ì†Œë¥??…ë ¥??ì£¼ì„¸??", "Please enter your email address to share Google Sheet ownership."))
                            import streamlit.components.v1 as components
                            alert_msg2 = _("êµ¬ê? ?œíŠ¸ ?Œìœ ê¶?ê³µìœ ë¥??„í•œ ?´ë©”??ì£¼ì†Œë¥??…ë ¥??ì£¼ì„¸??", "Please enter your email address to share Google Sheet ownership.")
                            components.html(f"<script>alert('{alert_msg2}');</script>", height=0, width=0)
                        else:
                            with st.spinner(_("êµ¬ê? ?¤í”„?ˆë“œ?œíŠ¸?€ ?¤ë¬¸ êµ¬ì¡°ë¥??°ë™?˜ëŠ” ì¤?..", "Linking survey structure with Google Spreadsheet...")):
                                try:
                                    target_sheet_id = existing_sheet_id_input.strip()
                                    if "docs.google.com/spreadsheets" in target_sheet_id:
                                        parts = target_sheet_id.split("/d/")
                                        if len(parts) > 1:
                                            target_sheet_id = parts[1].split("/")[0]

                                    if tier_level == 3:
                                        from survey_manager_v3 import create_survey_sheet_v3
                                        sheet_id = create_survey_sheet_v3(
                                            title=survey_title,
                                            admin_email=survey_admin_email,
                                            ahp_model=model_structure,
                                            scale_type=scale_option,
                                            demographics=demographics_settings,
                                            definition_map=definitions_map,
                                            cr_limit=cr_limit,
                                            cr_guide_method=cr_guide_method,
                                            rewards_info=rewards_info,
                                            description=survey_desc,
                                            existing_sheet_id=target_sheet_id,
                                            user_id=st.session_state.user_id
                                        )
                                    else:
                                        sheet_id = create_survey_sheet(
                                            title=survey_title,
                                            admin_email=survey_admin_email,
                                            ahp_model=model_structure,
                                            scale_type=scale_option,
                                            demographics=demographics_settings,
                                            definition_map=definitions_map,
                                            cr_limit=cr_limit,
                                            cr_guide_method=cr_guide_method,
                                            rewards_info=rewards_info,
                                            description=survey_desc,
                                            existing_sheet_id=target_sheet_id,
                                            user_id=st.session_state.user_id
                                        )



                                    # admin_surveys ?Œì´ë¸”ì— ? ê·œ ?¤ë¬¸ ?ë™ ?±ë¡ ë°?ë§ˆìŠ¤??êµ¬ê? ?œíŠ¸ ë°±ì—…
                                    try:
                                        from survey_manager import save_admin_survey_to_gsheet
                                        save_admin_survey_to_gsheet(sheet_id, survey_title, st.session_state.user_id)
                                
                                        conn = sqlite3.connect('users.db')
                                        cur = conn.cursor()
                                        cur.execute("INSERT INTO admin_surveys (survey_id, title, admin_id, created_at) VALUES (?, ?, ?, datetime('now'))",
                                                    (sheet_id, survey_title, st.session_state.user_id))
                                        conn.commit()
                                        conn.close()
                                    except Exception as dbe:
                                        pass

                                    # ë°°í¬ ì£¼ì†Œ ?ì„±
                                    base_url = st.query_params.get("base_url", ["https://ahpkrj.streamlit.app/"])[0] if isinstance(st.query_params.get("base_url"), list) else "https://ahpkrj.streamlit.app/"
                                    if "localhost" in base_url or "127.0.0.1" in base_url:
                                        short_url = f"{base_url}?survey_id={sheet_id}"
                                    else:
                                        short_url = f"https://ahpkrj.streamlit.app/?survey_id={sheet_id}"

                                    # ?¬ìš©??ë°°í¬ ?µê³„ ë°??¤ë¬¸ ë§í¬ ê¸°ë¡
                                    update_user_survey_distribution(st.session_state.user_id, short_url)
                                    st.session_state._survey_cache_dirty = True  # ?¤ë¬¸ ëª©ë¡ ìºì‹œ ë¬´íš¨??

                                    st.balloons()
                                    st.success(_("?‰ AHP ?¨ë¼???¤ë¬¸ì§€ê°€ ?±ê³µ?ìœ¼ë¡??…ë°?´íŠ¸(?˜ì •) ?˜ì—ˆ?µë‹ˆ??", "?‰ AHP online survey has been successfully updated!") if st.session_state.get("editing_survey_id") else _("?‰ AHP ?¨ë¼???¤ë¬¸ì§€ ë°??°ë™ êµ¬ê? ?œíŠ¸ ?ì„±???„ë£Œ?˜ì—ˆ?µë‹ˆ??", "?‰ AHP online survey and linked Google Sheet creation are complete!"))

                                    st.code(short_url, language="text")
                                    st.info(f"**??ë°°í¬ URL??ì¹´ì¹´?¤í†¡?´ë‚˜ ?´ë©”???±ìœ¼ë¡??‘ë‹µ ?€?ì?ê²Œ ë°œì†¡?˜ì‹­?œì˜¤.**  \nêµ¬ê? ?œíŠ¸ ë§í¬ ?ëŠ” êµ¬ê? ?œë¼?´ë¸Œ(ê³„ì •: {survey_admin_email})???‘ì†?˜ì‹œë©??¤ì‹œê°„ìœ¼ë¡??„ì ?˜ëŠ” ?‘ë‹µ???°ì´??Sheet 2: Raw_Data, Sheet 3: Demographic_Data)ë¥??•ì¸?˜ê³  ì¦‰ì‹œ ?¤ìš´ë¡œë“œ?˜ì—¬ ë¶„ì„?˜ì‹¤ ???ˆìŠµ?ˆë‹¤.")
                                    st.warning(_(
                                        "?“¢ **[RAW ?°ì´??ë³´ê? ë°?ë°±ì—… ?˜ë¬´ ?ˆë‚´]**\n\n"
                                        "??êµ¬ê? ?¤í”„?ˆë“œ?œíŠ¸???€?¥ë˜??RAW ?°ì´?°ëŠ” **?ì„±?¼ë¡œë¶€??6ê°œì›”ê°?? ì??????ë™ ?? œ**?©ë‹ˆ??\n"
                                        "??ì¡°ì‚¬ê°€ ?„ë£Œ?˜ë©´ ë°˜ë“œ??ë³¸ì¸??ì»´í“¨?°ì— ?‘ì?(.xlsx) ?ëŠ” CSV ?Œì¼ë¡??°ì´?°ë? ?¤ìš´ë¡œë“œ?˜ì—¬ **ë°±ì—…**??ì£¼ì‹œê¸?ë°”ë?ˆë‹¤.\n"
                                        "???ì„± ??6ê°œì›”??ì§€???œì ??ê°€?…í•˜???´ë©”??ID)ë¡??¬ì „ ?? œ ë°?ë°±ì—… ?ˆë‚´ ë©”ì¼??ë°œì†¡?˜ë©°, ë©”ì¼ ë°œì†¡ 10????êµ¬ê? ?œíŠ¸ê°€ ?ë™ ?? œ?©ë‹ˆ??",
                                        "?“¢ **[RAW Data Retention & Mandatory Backup Notice]**\n\n"
                                        "??RAW data stored in Google Spreadsheets is **retained for 6 months from creation and then automatically deleted**.\n"
                                        "??When your survey is completed, you MUST download and **backup** the data to your computer as an Excel (.xlsx) or CSV file.\n"
                                        "??At 6 months post-creation, a deletion and backup notification email will be sent to your registered email (ID), and the Google Sheet will be deleted 10 days after the email notification."
                                    ))
                                except Exception as ex:
                                    st.error(f"êµ¬ê? ?œíŠ¸ ?°ë™ ?¤íŒ¨: {ex}")
                                    import streamlit.components.v1 as components
                                    error_msg = str(ex).replace("'", "\\'").replace("\\n", " ")
                                    components.html(f"<script>alert('??êµ¬ê? ?¤í”„?ˆë“œ?œíŠ¸ ?°ë™???¤íŒ¨?ˆìŠµ?ˆë‹¤.\\n\\n?…ë ¥?˜ì‹  URL???¤í”„?ˆë“œ?œíŠ¸???‘ê·¼?????†ìŠµ?ˆë‹¤.\\n?ˆë‚´???œë¹„??ê³„ì • ?´ë©”??ahp-master-v2@ahp-login.iam.gserviceaccount.com)??ë°˜ë“œ??[?¸ì§‘??ë¡?ì¶”ê??˜ê³  ê³µìœ ??ì£¼ì…”???°ë™ ë°?ë°°í¬ê°€ ê°€?¥í•©?ˆë‹¤.\\n\\n?ì„¸ ?ëŸ¬: {error_msg}');</script>", height=0, width=0)


        _survey_setup_fragment()

    # -------------------------------------------------------------------------
    # [? ê·œ] ?‘ë‹µ?„í™© ?€?œë³´????(Tab 3) ?ì„¸ êµ¬í˜„
    # -------------------------------------------------------------------------
    with main_tab3:
        st.header(_("?¤ì‹œê°??‘ë‹µ ?„í™©", "Real-time Response Status"))
        selected_sheet_id = None
        
        if st.session_state.user_id is None:
            st.warning(_("?”’ **?¤ì‹œê°??‘ë‹µ ?„í™© ê¸°ëŠ¥?€ ?Œì› ?„ìš© ?œë¹„?¤ì…?ˆë‹¤.**", "?”’ **Real-time response status is a member-only service.**"))
            st.info("ë¬´ë£Œ ?Œì›ê°€??ë°?ë¡œê·¸?¸ì„ ?„ë£Œ?˜ì‹œë©?ë³¸ì¸??ë°°í¬???¤ë¬¸ì§€???¤ì‹œê°??‘ë‹µ ?íƒœ ë°??„ì  ?°ì´?°ë? ëª¨ë‹ˆ?°ë§?˜ê³  ?¤ìš´ë¡œë“œ?????ˆìŠµ?ˆë‹¤. (ë¬´ë£Œ ?Œì›??ê¸°ëŠ¥ ?œí•œ ?†ì´ ëª¨ë“  ê¸°ëŠ¥ ?¬ìš© ê°€??  \n**ì¢Œì¸¡ ?¬ì´?œë°”??ë¡œê·¸???Œì›ê°€???¨ë„**???´ìš©??ì£¼ì„¸??")
        else:
            # DB?ì„œ ?´ë‹¹ ê´€ë¦¬ìê°€ ?ì„±???¤ë¬¸ ëª©ë¡ ì¡°íšŒ
            import sqlite3
            import pandas as pd

            try:
                sync_short_codes_from_gs()
            except Exception:
                pass

            admin_surveys = []
            try:
                conn = sqlite3.connect('users.db')
                cur = conn.cursor()
                cur.execute("SELECT survey_id, title, created_at FROM admin_surveys WHERE admin_id = ? ORDER BY created_at DESC", (st.session_state.user_id,))
                sqlite_surveys = cur.fetchall()
                conn.close()
                
                gs_surveys = []
                try:
                    from survey_manager import get_admin_surveys_from_gsheet
                    gs_surveys = get_admin_surveys_from_gsheet(st.session_state.user_id)
                except Exception:
                    pass
                
                merged_surveys = {}
                for s in gs_surveys + sqlite_surveys:
                    if s[0] not in merged_surveys:
                        merged_surveys[s[0]] = s
                admin_surveys = list(merged_surveys.values())
                admin_surveys.sort(key=lambda x: x[2], reverse=True)
            except Exception as e:
                st.error(f"?¤ë¬¸ ëª©ë¡ ì¡°íšŒ ?¤íŒ¨: {e}")

            if not admin_surveys:
                st.warning("ë°°í¬???¤ë¬¸ì§€ê°€ ì¡´ì¬?˜ì? ?ŠìŠµ?ˆë‹¤. '?¨ë¼???¤ë¬¸ì§€ ?œì‘' ??—???¤ë¬¸??ë¨¼ì? ë°°í¬??ì£¼ì„¸??")
            else:
                # ë¡œê·¸?¸í•œ ?„ì´?”ì— ë§ì¶° ë³¸ì¸???¤ë¬¸?¤ë§Œ ?œë¡­?¤ìš´???¸ì¶œ?œí‚µ?ˆë‹¤.
                survey_options = {f"{row[1]} ({row[2]})": row[0] for row in admin_surveys}
                selected_label = st.selectbox(
                    "?¤ì‹œê°??„í™©???•ì¸???¤ë¬¸ ? íƒ",
                    list(survey_options.keys()),
                    key="tab3_survey_select"
                )
                selected_sheet_id = survey_options[selected_label]
                
                selected_survey_info = next(s for s in admin_surveys if s[0] == selected_sheet_id)
                survey_title = selected_survey_info[1]
                created_at = selected_survey_info[2]
                
                st.success(f"?“Œ ?„ì¬ ? íƒ???¤ë¬¸: **{survey_title}** (ë°°í¬?¼ì‹œ: {created_at})")
                st.divider()

        # ?€?œë³´???Œë”ë§?
        if selected_sheet_id:

            st.info("?’¡ êµ¬ê? API ?¼ì¼ ?¸ì¶œ ? ë‹¹??ì´ˆê³¼(Quota Exceeded 429 ?ëŸ¬)ë¥?ë°©ì??˜ê¸° ?„í•´, ?°ì´?°ëŠ” ?ë™?¼ë¡œ ë¶ˆëŸ¬?¤ì? ?ŠìŠµ?ˆë‹¤. ?„ë˜ ë²„íŠ¼???ŒëŸ¬ ìµœì‹  ?°ì´?°ë? ê°±ì‹ ?˜ì„¸??")
            if st.button("?”„ ?¤ì‹œê°??¤ë¬¸ ?€?œë³´??ë°??‘ë‹µ ?°ì´??ë¶ˆëŸ¬?¤ê¸° / ?ˆë¡œê³ ì¹¨", type="primary"):
                from survey_manager import get_survey_stats, get_survey_gspread_client
                with st.spinner("?¤ì‹œê°??¤ë¬¸ ?„í™© ë¡œë”© ì¤?.."):
                    # 1. Stats Loading
                    st.session_state["survey_stats"] = get_survey_stats(selected_sheet_id.strip())
                    
                    # 2. Raw Data Loading
                    g_client = get_survey_gspread_client()
                    if g_client:
                        try:
                            spreadsheet = g_client.open_by_key(selected_sheet_id.strip())
                            raw_sheet = spreadsheet.worksheet("Raw_Data")
                            all_rows = raw_sheet.get_all_values()

                            try:
                                demo_sheet = spreadsheet.worksheet("Demographic_Data")
                                demo_rows = demo_sheet.get_all_values()
                            except Exception:
                                demo_rows = []

                            if len(all_rows) > 0:
                                headers = all_rows[0]
                                rows = all_rows[1:]
                                st.session_state["live_df"] = pd.DataFrame(rows, columns=headers)

                                if len(demo_rows) > 0:
                                    demo_headers = demo_rows[0]
                                    demo_vals = demo_rows[1:]
                                    st.session_state["demo_df"] = pd.DataFrame(demo_vals, columns=demo_headers)
                                else:
                                    st.session_state["demo_df"] = None
                            else:
                                st.session_state["live_df"] = pd.DataFrame()
                                st.session_state["demo_df"] = None

                        except Exception as g_err:
                            st.error(f"êµ¬ê? ?œíŠ¸?ì„œ ?°ì´?°ë? ?½ì–´?¤ëŠ” ì¤??ëŸ¬ ë°œìƒ: {g_err}")
                            st.session_state["live_df"] = None
                    else:
                        st.warning("êµ¬ê? Sheets API ?´ë¼?´ì–¸???°ê²° ?¤íŒ¨ë¡??¸í•´ êµ¬ê? ?œíŠ¸ ???°ì´?°ë? ì§ì ‘ ?¤ìš´ë¡œë“œ?????†ìŠµ?ˆë‹¤.")
                        st.session_state["live_df"] = None

            if "survey_stats" in st.session_state:
                stats = st.session_state["survey_stats"]
                col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
                with col_stat1:
                    st.metric(_("ì´??‘ì†????(Visits)", "Total Visits"), f"{stats['visits']}" + _("ëª?, ""))
                with col_stat2:
                    st.metric(_("?„ë£Œ ?‘ë‹µ????(Completed)", "Completed Responses"), f"{stats['completed']}" + _("ëª?, ""))
                with col_stat3:
                    st.metric(_("?¼ê???ì´ˆê³¼ ì¤‘ë‹¨??(CR Fail)", "CR Fail Abandonments"), f"{stats['abandoned_cr']}" + _("??, " times"))
                with col_stat4:
                    st.metric(_("?¨ìˆœ ?´íƒˆ ì¤‘ë‹¨??(Bounce)", "Bounced Visitors"), f"{stats['abandoned_bounce']}" + _("ëª?, ""))

                # ?œê°??ì°¨íŠ¸ ì¶”ê?
                import plotly.express as px

                chart_data = pd.DataFrame({
                    "êµ¬ë¶„": ["?‘ë‹µ ?„ë£Œ", "?¼ê???ì´ˆê³¼ ì¤‘ë‹¨", "?¨ìˆœ ?˜ì´ì§€ ?´íƒˆ"],
                    "?¸ì›??: [stats['completed'], stats['abandoned_cr'], stats['abandoned_bounce']]
                })

                fig_stats = px.bar(
                    chart_data,
                    x="êµ¬ë¶„",
                    y="?¸ì›??,
                    text="?¸ì›??,
                    color="êµ¬ë¶„",
                    color_discrete_map={
                        "?‘ë‹µ ?„ë£Œ": "#2E7D32",
                        "?¼ê???ì´ˆê³¼ ì¤‘ë‹¨": "#C62828",
                        "?¨ìˆœ ?˜ì´ì§€ ?´íƒˆ": "#EF6C00"
                    },
                    title="?¤ë¬¸ ì°¸ì—¬ ?íƒœë³?ë¶„í¬"
                )
                fig_stats.update_layout(showlegend=False)
                st.plotly_chart(fig_stats, use_container_width=True)

            if "live_df" in st.session_state and st.session_state["live_df"] is not None:
                live_df = st.session_state["live_df"]
                demo_df = st.session_state.get("demo_df", None)

                # êµ¬ê? ?œíŠ¸?ì„œ ?¤ì‹œê°??‘ë‹µ ë¡œë°?´í„°(Raw_Data) ?¤ìš´ë¡œë“œ ê¸°ëŠ¥ ì¶”ê?
                with st.expander(_("?“¥ ?¤ì‹œê°?êµ¬ê? ?œíŠ¸ ?‘ë‹µ ?°ì´???¤ìš´ë¡œë“œ ?¼í„°", "?“¥ Real-time Google Sheet Response Data Download Center"), expanded=True):
                    if not live_df.empty:
                        st.success(f"êµ¬ê? ?¤í”„?ˆë“œ?œíŠ¸?ì„œ ?¤ì‹œê°??‘ë‹µ ?°ì´?°ë? ?±ê³µ?ìœ¼ë¡?ë¶ˆëŸ¬?”ìŠµ?ˆë‹¤. (Raw_Data: {len(live_df)}ê±? + (f", Demographic_Data: {len(demo_df)}ê±? if demo_df is not None else "") + ")")
                        
                        # ?“Š AHP ë¶„ì„ ?°ë™ ?¨ì¶• ë²„íŠ¼ ì¶”ê?
                        if st.button(_("?“Š ???¨ë¼???¤ë¬¸ ?°ì´?°ë¡œ ì¦‰ì‹œ AHP ë¶„ì„ ?˜í–‰?˜ê¸° (ë¶„ì„ ?„êµ¬ë¡??°ë™)", "?“Š Perform AHP Analysis Instantly with this Online Survey Data"), type="primary", use_container_width=True):
                            st.session_state["selected_survey_for_analysis"] = selected_sheet_id
                            from survey_manager import load_survey_metadata
                            survey_meta = load_survey_metadata(selected_sheet_id)
                            if survey_meta:
                                ahp_model = survey_meta["AHP_Model_JSON"]
                                base_cols = ["ID", "Type"]
                                main_criteria = ahp_model.get("main", [])
                                main_pairs = []
                                for i in range(len(main_criteria)):
                                    for j in range(i + 1, len(main_criteria)):
                                        main_pairs.append(f"{main_criteria[i]}_{main_criteria[j]}")
                                main_cols = [c for c in base_cols if c in live_df.columns] + [p for p in main_pairs if p in live_df.columns]
                                
                                st.session_state["ahp_df_main"] = live_df[main_cols].copy()
                                for col in st.session_state["ahp_df_main"].columns:
                                    if col not in ["ID", "Type"]:
                                        st.session_state["ahp_df_main"][col] = pd.to_numeric(st.session_state["ahp_df_main"][col], errors='coerce').fillna(1.0)
                                
                                 # ì¤‘ë¶„ë¥?ë³µì‚¬
                                st.session_state["ahp_sub_dfs"] = {}
                                sub_criteria_map = ahp_model.get("subs", {})
                                for main_c, subs in sub_criteria_map.items():
                                    if len(subs) >= 2:
                                        sub_pairs = []
                                        for i in range(len(subs)):
                                            for j in range(i + 1, len(subs)):
                                                sub_pairs.append(f"{subs[i]}_{subs[j]}")
                                        sub_cols = [c for c in base_cols if c in live_df.columns] + [p for p in sub_pairs if p in live_df.columns]
                                        st.session_state["ahp_sub_dfs"][main_c] = live_df[sub_cols].copy()
                                        for col in st.session_state["ahp_sub_dfs"][main_c].columns:
                                            if col not in ["ID", "Type"]:
                                                st.session_state["ahp_sub_dfs"][main_c][col] = pd.to_numeric(st.session_state["ahp_sub_dfs"][main_c][col], errors='coerce').fillna(1.0)
                                                
                                st.session_state["ahp_sheet_names"] = ["Main_Criteria"] + list(st.session_state["ahp_sub_dfs"].keys())
                                st.info(_("?“Š ?°ì´??ë¶„ì„ ì¤€ë¹„ê? ?„ë£Œ?˜ì—ˆ?µë‹ˆ?? **?ë‹¨??'?“Š AHP ë¶„ì„ ?„êµ¬' ??*??? íƒ?˜ê³  **'?Œ ë°°í¬???¨ë¼???¤ë¬¸ ?°ì´???°ë™'** ?¼ë””??ë²„íŠ¼??? íƒ?˜ì—¬ ë¶„ì„ ê²°ê³¼ë¥?ë°”ë¡œ ?•ì¸?˜ì‹­?œì˜¤.", "?“Š Data analysis preparation is complete! Select the **'?“Š AHP Analysis Tool' tab at the top** and choose the **'?Œ Link Distributed Online Survey Data'** radio button to view the results instantly."))

                        tab_raw, tab_demo = st.tabs(["?“Š Raw_Data (AHP ?ë?ë¹„êµ ?°ì´??", "?‘¤ Demographic_Data (?¸êµ¬?µê³„/?¬ì „?œìœ„)"])
                        with tab_raw:
                            st.dataframe(live_df, use_container_width=True)
                        with tab_demo:
                            if demo_df is not None:
                                st.dataframe(demo_df, use_container_width=True)
                            else:
                                st.info("?˜ì§‘???¸êµ¬?µê³„ ?°ì´?°ê? ?†ê±°??Demographic_Data ?œíŠ¸ê°€ ?ì„±?˜ì? ?Šì•˜?µë‹ˆ??")

                        # Excel ë°?CSV ?´ë³´?´ê¸° ë²„íŠ¼ ?œê³µ
                        import io

                        # 1. Excel ?´ë³´?´ê¸° (??ê°œì˜ ?œíŠ¸ë¥?ëª¨ë‘ ?¬í•¨)
                        excel_buffer = io.BytesIO()
                        with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                            from survey_manager import load_survey_metadata
                            survey_meta = load_survey_metadata(selected_sheet_id)
                            parsed_ok = False
                            
                            if survey_meta:
                                ahp_model = survey_meta.get("AHP_Model_JSON", {})
                                tier_level = int(survey_meta.get("Tier_Level", 2))
                                base_cols = ["ID", "Type"]
                                main_criteria = ahp_model.get("main", [])
                                main_pairs = []
                                for i in range(len(main_criteria)):
                                    for j in range(i + 1, len(main_criteria)):
                                        main_pairs.append(f"{main_criteria[i]}_{main_criteria[j]}")
                                main_cols = [c for c in base_cols if c in live_df.columns] + [p for p in main_pairs if p in live_df.columns]
                                
                                if len(main_cols) > 2:
                                    df_main_dl = live_df[main_cols].copy()
                                    df_main_dl.to_excel(writer, index=False, sheet_name="Main_Criteria")
                                    
                                    sub_criteria_map = ahp_model.get("subs", {})
                                    for main_c, subs in sub_criteria_map.items():
                                        if len(subs) >= 2:
                                            sub_pairs = []
                                            for i in range(len(subs)):
                                                for j in range(i + 1, len(subs)):
                                                    sub_pairs.append(f"{subs[i]}_{subs[j]}")
                                            sub_cols = [c for c in base_cols if c in live_df.columns] + [p for p in sub_pairs if p in live_df.columns]
                                            df_sub_dl = live_df[sub_cols].copy()
                                            df_sub_dl.to_excel(writer, index=False, sheet_name=main_c[:31])
                                            
                                    if tier_level == 3:
                                        sub_sub_map = ahp_model.get("sub_subs", {})
                                        for main_c, subs in sub_criteria_map.items():
                                            for sub_c in subs:
                                                sub_subs = sub_sub_map.get(sub_c, [])
                                                if len(sub_subs) >= 2:
                                                    sub_sub_pairs = []
                                                    for i in range(len(sub_subs)):
                                                        for j in range(i + 1, len(sub_subs)):
                                                            sub_sub_pairs.append(f"{sub_subs[i]}_{sub_subs[j]}")
                                                    ss_cols = [c for c in base_cols if c in live_df.columns] + [p for p in sub_sub_pairs if p in live_df.columns]
                                                    df_ss_dl = live_df[ss_cols].copy()
                                                    df_ss_dl.to_excel(writer, index=False, sheet_name=sub_c[:31])
                                    parsed_ok = True
                            
                            if not parsed_ok:
                                live_df.to_excel(writer, index=False, sheet_name='Raw_Data')
                            else:
                                live_df.to_excel(writer, index=False, sheet_name='Raw_Data_Dump')
                                
                            if demo_df is not None:
                                demo_df.to_excel(writer, index=False, sheet_name='Demographic_Data')

                        col_dl1, col_dl2 = st.columns(2)
                        with col_dl1:
                            st.download_button(
                                "?“¥ ?¤ì‹œê°??‘ë‹µ Excel ?¤ìš´ë¡œë“œ (.xlsx)",
                                data=excel_buffer.getvalue(),
                                file_name=f"Survey_Live_Data_{selected_sheet_id.strip()[:6]}.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                use_container_width=True,
                                type="primary"
                            )
                        # 2. CSV ?´ë³´?´ê¸° (Raw_Data ?°ì„  ?´ë³´?´ê¸°)
                        csv_buffer = io.StringIO()
                        live_df.to_csv(csv_buffer, index=False, header=True)
                        with col_dl2:
                            st.download_button(
                                "?“¥ ?¤ì‹œê°??‘ë‹µ CSV ?¤ìš´ë¡œë“œ (.csv)",
                                data=csv_buffer.getvalue().encode('utf-8-sig'),
                                file_name=f"Survey_Live_Data_{selected_sheet_id.strip()[:6]}.csv",
                                mime="text/csv",
                                use_container_width=True
                            )
                    else:
                        st.info("êµ¬ê? ?œíŠ¸???˜ì§‘???‘ë‹µ ë¡œë°?´í„°ê°€ ?„ì§ ë¹„ì–´ ?ˆìŠµ?ˆë‹¤.")

            # ë¡œì»¬ ?ˆì „ ë°±ì—… ?°ì´??ì¡°íšŒ ë°?ì¶”ì¶œ ? í‹¸ë¦¬í‹°
            try:
                conn = sqlite3.connect('users.db')
                backup_df = pd.read_sql_query(
                    "SELECT id, respondent_id, response_json, created_at FROM survey_backup_responses WHERE survey_id = ?",
                    conn, params=(selected_sheet_id.strip(),)
                )
                conn.close()

                if not backup_df.empty:
                    with st.expander("?›¡ï¸??œë²„ ë¡œì»¬ ?ˆì „ ë°±ì—… ê´€ë¦??¼í„°"):
                        st.success(f"êµ¬ê? ?œíŠ¸ ?°ë™ê³?ê´€ê³„ì—†???œë²„ ë¡œì»¬ ?°ì´?°ë² ?´ìŠ¤???€?¥ëœ ?ˆì „ ë°±ì—… ?°ì´?°ê? ì´?{len(backup_df)}ê±?ì¡´ì¬?©ë‹ˆ??")
                        st.dataframe(backup_df[["id", "respondent_id", "created_at"]], use_container_width=True)

                        # ?„ì²´ ë¡??°ì´??ë³µêµ¬ ?‘ì?/CSV ?°ì´??ë¹Œë“œ
                        recovered_raw_rows = []
                        recovered_demo_rows = []
                        for idx_b, r_b in backup_df.iterrows():
                            payload = json.loads(r_b["response_json"])
                            if "raw_row_data" in payload:
                                recovered_raw_rows.append(payload["raw_row_data"])
                            elif "row_data" in payload:
                                # ?˜ìœ„ ?¸í™˜??
                                recovered_raw_rows.append(payload["row_data"])

                            if "demo_row_data" in payload:
                                recovered_demo_rows.append(payload["demo_row_data"])

                        if recovered_raw_rows:
                            import io

                            # ?¤ë” ë³µêµ¬ ë¡œì§ ì¶”ê?
                            raw_headers = None
                            demo_headers = None
                            from survey_manager import load_survey_metadata
                            survey_meta = load_survey_metadata(selected_sheet_id.strip())
                            if survey_meta:
                                ahp_model = survey_meta.get("AHP_Model_JSON", {})
                                demographics = survey_meta.get("Demographics", {})
                                rewards_info = survey_meta.get("Rewards_Info", {})
                                tier_level = str(survey_meta.get("Tier_Level", "2"))
                                
                                raw_headers = ["ID", "Type"]
                                main_criteria = ahp_model.get("main", [])
                                for i in range(len(main_criteria)):
                                    for j in range(i + 1, len(main_criteria)):
                                        raw_headers.append(f"{main_criteria[i]}_{main_criteria[j]}")
                                sub_criteria_map = ahp_model.get("subs", {})
                                for main_c in main_criteria:
                                    subs = sub_criteria_map.get(main_c, [])
                                    if len(subs) >= 2:
                                        for i in range(len(subs)):
                                            for j in range(i + 1, len(subs)):
                                                raw_headers.append(f"{subs[i]}_{subs[j]}")
                                if tier_level == "3":
                                    sub_sub_map = ahp_model.get("sub_subs", {})
                                    for main_c in main_criteria:
                                        subs = sub_criteria_map.get(main_c, [])
                                        for sub_c in subs:
                                            sub_subs = sub_sub_map.get(sub_c, [])
                                            if len(sub_subs) >= 2:
                                                for i in range(len(sub_subs)):
                                                    for j in range(i + 1, len(sub_subs)):
                                                        raw_headers.append(f"{sub_subs[i]}_{sub_subs[j]}")
                                raw_headers.append("?œì¶œ?œê°„")
                                
                                demo_headers = ["ID", "Type"]
                                if demographics.get("name"): demo_headers.append("?±ëª…")
                                if demographics.get("age"): demo_headers.append("?°ë ¹")
                                if demographics.get("gender"): demo_headers.append("?±ë³„")
                                if demographics.get("experience"): demo_headers.append("ê²½ë ¥?„ìˆ˜")
                                # if demographics.get("affiliation"): demo_headers.append("?Œì†")
                                if demographics.get("email"): demo_headers.append("?´ë©”??)
                                demo_headers.append("?¬ì „?œìœ„ì§€??)
                                if rewards_info.get("enabled"):
                                    demo_headers.append("ê²½í’ˆ?°ë½ì²? if tier_level == "3" else "?µë????°ë½ì²?)
                                demo_headers.append("?œì¶œ?œê°„")

                            df_raw_backup = pd.DataFrame(recovered_raw_rows)
                            if raw_headers and len(raw_headers) == len(df_raw_backup.columns):
                                df_raw_backup.columns = raw_headers
                            elif raw_headers and len(raw_headers) > len(df_raw_backup.columns):
                                df_raw_backup.columns = raw_headers[:len(df_raw_backup.columns)]
                                
                            df_demo_backup = None
                            if recovered_demo_rows:
                                df_demo_backup = pd.DataFrame(recovered_demo_rows)
                                if demo_headers and len(demo_headers) == len(df_demo_backup.columns):
                                    df_demo_backup.columns = demo_headers
                                elif demo_headers and len(demo_headers) > len(df_demo_backup.columns):
                                    df_demo_backup.columns = demo_headers[:len(df_demo_backup.columns)]

                            # Excelë¡?ë°±ì—… ?°ì´?°ë? ?œí”Œë¦?êµ¬ì¡°??ë§ì¶° ë¶„í• ?˜ì—¬ ?¤ìš´ë¡œë“œ
                            if survey_meta and "AHP_Model_JSON" in survey_meta:
                                excel_backup_buffer = export_to_template_excel(df_raw_backup, df_demo_backup, survey_meta["AHP_Model_JSON"], survey_meta.get("Tier_Level", 2))
                            else:
                                excel_backup_buffer = io.BytesIO()
                                with pd.ExcelWriter(excel_backup_buffer, engine='openpyxl') as writer:
                                    df_raw_backup.to_excel(writer, index=False, header=bool(raw_headers), sheet_name='Raw_Data')
                                    if df_demo_backup is not None:
                                        df_demo_backup.to_excel(writer, index=False, header=bool(demo_headers), sheet_name='Demographic_Data')

                            col_b_dl1, col_b_dl2 = st.columns(2)
                            with col_b_dl1:
                                st.download_button(
                                    "?“¥ ë¡œì»¬ ë°±ì—… Excel ?¤ìš´ë¡œë“œ (.xlsx)",
                                    data=excel_backup_buffer.getvalue(),
                                    file_name=f"Backup_Recovery_{selected_sheet_id.strip()[:6]}.xlsx",
                                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                    use_container_width=True,
                                    type="primary"
                                )

                            with col_b_dl2:
                                # CSV ?Œì¼ ?•íƒœë¡?ë³µêµ¬ ?Œì¼ ?´ë³´?´ê¸° (Raw_Data ?°ì„ )
                                output_csv = io.StringIO()
                                df_raw_backup.to_csv(output_csv, index=False, header=bool(raw_headers))
                                st.download_button(
                                    "?“¥ ë¡œì»¬ ë°±ì—… Raw_Data CSV ?¤ìš´ë¡œë“œ (.csv)",
                                    data=output_csv.getvalue().encode('utf-8-sig'),
                                    file_name=f"Backup_Recovery_Raw_{selected_sheet_id.strip()[:6]}.csv",
                                    mime="text/csv",
                                    use_container_width=True
                                )
                else:
                    st.caption("???¤ë¬¸ì§€???±ë¡??ë¡œì»¬ ?œë²„ ë°±ì—… ?°ì´?°ê? ?†ìŠµ?ˆë‹¤. (ëª¨ë“  ?°ì´???•ìƒ ?ì¬)")
            except Exception as err:
                st.caption(f"ë¡œì»¬ ë°±ì—… ì¡°íšŒ ë¶ˆê?: {err}")


    st.markdown("---")
    st.caption("Â© 2026 AHP Master. All rights reserved.")


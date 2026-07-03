import streamlit as st


# Force rebuild 2026-01-24 v3 (Merged Sync & Restore)
# Force deploy 2026-02-07

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

from ahp_table_utils import write_custom_ahp_table, add_borders_to_data


# --- LAZY LOADER FOR HEAVY LIBRARIES (SPEED UP INITIAL LOAD) ---
class LazyLoader:
    def __init__(self, name):
        self.name = name
        self._module = None
    def _load(self):
        if self._module is None:
            import importlib
            self._module = importlib.import_module(self.name)
        return self._module
    def __getattr__(self, item):
        return getattr(self._load(), item)

pd = LazyLoader('pandas')
np = LazyLoader('numpy')
plt = LazyLoader('matplotlib.pyplot')
sns = LazyLoader('seaborn')
fm = LazyLoader('matplotlib.font_manager')
px = LazyLoader('plotly.express')
go = LazyLoader('plotly.graph_objects')
stats = LazyLoader('scipy.stats')

class LazyFunction:
    def __init__(self, module_name, func_name):
        self.module_name = module_name
        self.func_name = func_name
        self._func = None
    def __call__(self, *args, **kwargs):
        if self._func is None:
            import importlib
            module = importlib.import_module(self.module_name)
            self._func = getattr(module, self.func_name)
        return self._func(*args, **kwargs)

gmean = LazyFunction('scipy.stats', 'gmean')
ttest_rel = LazyFunction('scipy.stats', 'ttest_rel')
f_oneway = LazyFunction('scipy.stats', 'f_oneway')
# ---------------------------------------------------------------

def hash_password(password: str) -> str:
    """SHA-256 Hash a password with a fixed salt for security."""
    salt = "ahp_master_secure_salt_2026"
    return hashlib.sha256((password + salt).encode('utf-8')).hexdigest()

def generate_temp_password() -> str:
    """가입 시 비밀번호 유효성 검사를 통과하는 8자리 임시 비밀번호를 생성합니다."""
    chars = string.ascii_letters + string.digits
    specials = "!@#$%^&*"
    # 최소 1개 영문자, 1개 숫자, 1개 특수문자를 포함하도록 구성
    temp = [
        random.choice(string.ascii_lowercase),
        random.choice(string.uppercase) if hasattr(string, 'uppercase') else random.choice(string.ascii_uppercase),
        random.choice(string.digits),
        random.choice(specials)
    ]
    # 나머지 4자리는 영문/숫자 중 무작위 선택
    temp += [random.choice(chars) for _ in range(4)]
    random.shuffle(temp)
    return "".join(temp)

from matplotlib import rc
from email.mime.text import MIMEText
import itertools

from dateutil.relativedelta import relativedelta

from signup_agreement import show_agreement_ui

# --- LAZY LOAD HEAVY MODULES ---
gspread = LazyLoader('gspread')
requests = LazyLoader('requests')

# 1. 추가해야 할 라이브러리
from streamlit_javascript import st_javascript
import base64

# IP 위치 추적 및 공인 IP 추출을 위한 라이브러리 추가
# (requests는 LazyLoader로 처리)

# ANOVA 및 사후검정을 위한 라이브러리 (없을 경우 예외처리)
class LazyTukeyHSD:
    def __call__(self, *args, **kwargs):
        try:
            from statsmodels.stats.multicomp import pairwise_tukeyhsd
            return pairwise_tukeyhsd(*args, **kwargs)
        except ImportError:
            return None
pairwise_tukeyhsd = LazyTukeyHSD()
STATSMODELS_AVAILABLE = True


# -----------------------------------------------------------------------------
# 다국어(English/Korean) 번역 헬퍼 함수
# -----------------------------------------------------------------------------
if 'lang' not in st.session_state:
    try:
        _init_lang = st.query_params.get("lang", "ko")
        if isinstance(_init_lang, list): _init_lang = _init_lang[0]
        st.session_state.lang = _init_lang.lower()
    except:
        st.session_state.lang = 'ko'

        st.session_state.lang = 'ko'

def _(ko_text, en_text):
    if st.session_state.get('lang', 'ko') == 'en':
        return en_text
    return ko_text

DEFAULT_SURVEY_DESC_KO = """[조사 목적 및 안내문]

안녕하십니까?
본 설문조사는 [연구/프로젝트 주제]에 관한 주요 요인들의 상대적 중요도를 도출하기 위해 전문가(또는 실무자) 여러분의 고견을 수렴하고자 마련되었습니다. 
바쁘시더라도 잠시 시간을 내어 귀하의 귀중한 의견을 응답해 주시면 연구에 큰 도움이 될 것입니다.

■ 조사 목적 : [연구/프로젝트 목적 기재]
■ 조사 내용 : [조사 대상 요인] 간의 AHP(쌍대비교) 평가
■ 조사 기간 : 202X년 X월 X일 ~ 202X년 X월 X일
■ 개인정보 보호 : 
본 조사를 통해 수집된 모든 자료는 통계법 제33조(비밀의 보호)에 의거하여 철저히 보호되며, 오직 연구 및 통계 분석 목적으로만 활용됩니다.
응답해주신 개인 정보 및 개별 응답 결과는 절대 외부로 유출되지 않음을 약속드립니다.

귀하의 소중한 참여에 깊은 감사를 드립니다.

- 연구 책임자 : [이름 기재]
- 문의처 : [연락처 또는 이메일 기재]"""

DEFAULT_SURVEY_DESC_EN = """[Survey Purpose & Instructions]

Greetings,
This survey is designed to collect the valuable opinions of experts (or practitioners) to derive the relative importance of key factors regarding [Research/Project Topic].
Your participation will be of great help to our research, and we would deeply appreciate it if you could take a moment out of your busy schedule to respond.

■ Purpose : [Enter Research/Project Purpose]
■ Content : AHP (Pairwise Comparison) evaluation among [Target Factors]
■ Period : 202X-XX-XX ~ 202X-XX-XX
■ Privacy Policy : 
All data collected through this survey will be strictly protected in accordance with privacy laws and used solely for research and statistical analysis purposes. We promise that your personal information and individual responses will never be leaked externally.

Thank you very much for your valuable participation.

- Lead Researcher : [Enter Name]
- Contact : [Enter Phone or Email]"""

# Default definition mappings for auto-translation to English when survey is loaded in English mode
DEFAULT_TRANSLATED_DEFS = {
    DEFAULT_SURVEY_DESC_KO: DEFAULT_SURVEY_DESC_EN,
    "제조용 협동로봇 도입 요인 중요도 분석을 위한 전문가 AHP 설문": "Expert AHP Survey on the Importance of Factors for Adopting Manufacturing Collaborative Robots",
    "협동로봇 도입 시 기술적 성능, 호환성, 안전성 및 기술 지원 등 기술 측면의 요인": "Factors related to the technological aspect such as technical performance, compatibility, safety, and technical support.",
    "협동로봇 도입과 관련된 조직 내부의 역량, 경영진 지원, 재무 및 교육 상태 요인": "Factors related to the internal capabilities of the organization, top management support, financial and training status.",
    "정부 지원, 산업 내 경쟁 압력, 구인난 및 외부 협력 등 외부 환경적 요인": "External environmental factors such as government support, competitive pressure within the industry, labor shortage, and external cooperation.",
    "경영진의 혁신 지향성, 구성원의 변화 수용도 및 스마트 팩토리 지식/기술 수준 요인": "Factors such as the management's innovation orientation, members' acceptance of change, and smart factory knowledge/skill levels.",
    "도입대상 협동로봇간의 상대적 이점": "Relative advantage among the collaborative robots targeted for adoption.",
    "기존 설비나 타사 협동로봇과의 연결성": "Connectivity with existing equipment or third-party collaborative robots.",
    "작업자와 같은 공간에서 안전 펜스 없이 작업할 때의 인적 사고 예방 수준": "Level of human accident prevention when working in the same space as operators without safety fences.",
    "공급사의 기술 및 A/S 지원 정도": "Degree of technical and A/S support from the supplier.",
    "경영진의 도입 의지 및 경영철학 반영도": "The management's willingness to adopt and the degree to which management philosophy is reflected.",
    "조직원의 로봇 활용 기술 준비 수준": "The level of technical readiness of organizational members to utilize robots.",
    "로봇 구입을 위한 자본 여력 및 자금 조달 편의성": "Capital capacity and financing convenience for purchasing robots.",
    "기술 향상을 위한 위탁/사내 교육 프로그램 유무": "Availability of external/internal training programs for skill improvement.",
    "협동로봇 도입을 활성화하기 위한 정부의 재정 지원 및 보조금 혜택 정도": "Degree of government financial support and subsidy benefits to promote the adoption of collaborative robots.",
    "동종 업계 또는 경쟁사의 협동로봇 도입에 따른 경쟁적 압박 정도": "Degree of competitive pressure due to the adoption of collaborative robots by peers or competitors.",
    "제조 현장의 구인난 및 생산 인력 수급의 어려움 수준": "Level of difficulty in finding labor and supplying production personnel at the manufacturing site.",
    "로봇 공급사 외의 외부 컨설팅, 연구기관 등의 기술적/교육적 지원": "Technical/educational support from external consulting, research institutes, etc., other than the robot supplier.",
    "최고경영자의 적극적인 의지": "The top management's active willingness to adopt new manufacturing technologies and robots.",
    "새로운 제조 기술 및 로봇 도입에 대한 최고경영자의 적극적인 의지": "The top management's active willingness to adopt new manufacturing technologies and robots.",
    "신규 장비 및 작업 프로세스 변화에 대한 구성원들의 수용 및 협조 태도": "Members' acceptance and cooperative attitude towards changes in new equipment and work processes.",
    "공장 내 디지털화, 정보시스템(MES 등) 및 자동화 기술의 현재 구축 수준": "Current level of implementation of digitalization, information systems (MES, etc.), and automation technology in the factory.",
    "협동로봇 활용 및 유지 관리에 필요한 조직 내 전문 지식 수준": "Level of internal expertise required for the utilization and maintenance of collaborative robots.",
    "기능성": "Functionality",
    "디자인": "Design",
    "경제성": "Economy",
    "하드웨어": "Hardware",
    "소프트웨어": "Software",
    "외관": "Appearance",
    "편의성": "Usability",
    "단말기가격": "Device Price",
    "유지비용": "Maintenance Cost",
    "기술 요인": "Technological",
    "조직 요인": "Organizational",
    "환경 요인": "Environmental",
    "혁신 요인": "Innovational",
    "상대적이점": "Relative Advantage",
    "호환성": "Compatibility",
    "안전성": "Security",
    "서비스지원": "Service Support",
    "경영진지원": "Top Management Support",
    "기술준비도": "Tech Readiness",
    "금융자원": "Financial Resources",
    "교육훈련": "Training",
    "정부지원": "Gov Support",
    "경쟁압력": "Competitive Pressure",
    "인력난": "Labor Shortage",
    "외부지원": "External Support",
    "경영진의 혁신성": "Management Innovativeness",
    "변화수용태도": "Change Acceptance",
    "스마트팩토리수준": "Smart Factory Level",
    "지식정도": "Knowledge Level"
}

def translate_definition_if_default(factor_name, def_text):
    if st.session_state.get('lang', 'ko') != 'en' or not def_text:
        return def_text
        
    # [FIX] Handle multi-line survey description explicitly
    if def_text.strip() == DEFAULT_SURVEY_DESC_KO.strip():
        return DEFAULT_SURVEY_DESC_EN
    
    # Clean up whitespace for other definitions
    clean_def = re.sub(r'\s+', ' ', def_text).strip()
    
    # 1. Direct match in dictionary
    if clean_def in DEFAULT_TRANSLATED_DEFS:
        return DEFAULT_TRANSLATED_DEFS[clean_def]
        
    # Translate the factor_name in pattern matching to match Korean if it's saved in Korean
    trans_factor = DEFAULT_TRANSLATED_DEFS.get(factor_name, factor_name)
    
    # 2. Pattern matches for "{factor}에 대한 정의입니다." or "{factor}에 대한 정의 입니다."
    pattern1 = rf"^(?:{re.escape(factor_name)}|{re.escape(trans_factor)})\s*에\s*대한\s*정의\s*입니다\.?$"
    if re.match(pattern1, clean_def):
        return f"Definition for {trans_factor}."
        
    pattern2 = rf"^(?:{re.escape(factor_name)}|{re.escape(trans_factor)})\s*에\s*대한\s*전반적\s*요소를\s*설명합니다\.?$"
    if re.match(pattern2, clean_def):
        return f"Overall description for {trans_factor}."
        
    return def_text

def translate_factor_if_default(factor_name):
    if st.session_state.get('lang', 'ko') != 'en' or not factor_name:
        return factor_name
    return DEFAULT_TRANSLATED_DEFS.get(factor_name, factor_name)

# =============================================================================
# 0. 시스템 설정 및 유틸리티
# =============================================================================

# [수정] Base64 문자열의 패딩 및 정제를 위한 유틸리티 함수 강화
def fix_base64_padding(data):
    """
    Base64 문자열의 패딩(Incorrect padding) 오류를 수정하는 함수
    """
    if isinstance(data, str):
        # 1. 모든 공백 및 줄바꿈 문자 제거 (가장 중요한 수정)
        data = re.sub(r'\s+', '', data)
        
        # 2. 패딩(=) 계산 및 추가
        missing_padding = len(data) % 4
        if missing_padding:
            data += '=' * (4 - missing_padding)
    return data

# [수정 반영] 1) SEO 태그 삽입, 2) 서비스 명 변경(AHP 마스터), 4) 파비콘 설정
try:
    from PIL import Image
    favicon_path = "favicon.png"
    if os.path.exists(favicon_path):
        favicon_img = Image.open(favicon_path)
    else:
        favicon_img = "📊"
    
    st.set_page_config(
        page_title=_("AHP 마스터 | 일반 및 퍼지 AHP 의사결정 분석 시스템", "AHP Master | Traditional & Fuzzy AHP Decision Analysis System"), 
        layout="wide", 
        page_icon=favicon_img,
        menu_items={
            'Get Help': None,
            'Report a bug': None,
            'About': _("AHP 마스터 - 스마트 일반 및 퍼지 AHP 의사결정 분석 시스템", "AHP Master - Smart Traditional & Fuzzy AHP Decision Analysis System")
        }
    )
except Exception:
    st.set_page_config(page_title=_("AHP 마스터 | 퍼지 AHP 지원", "AHP Master | Fuzzy AHP Support"), layout="wide", page_icon="📊")

# [수정 반영] 메타 코드가 화면에 노출되지 않도록 display:none 스타일을 추가한 SEO 태그 (영한 통합 검색 최적화)
# [추가] 네이버 서치어드바이저 및 검색 엔진 크롤러 수집을 위해 메타 태그, canonical, JSON-LD 구조화 데이터를 실제 헤드(Parent Head)에 동적으로 삽입하는 1x1 이미지 로더 스크립트 탑재
seo_tags = """<div style="display:none;">
<title>AHP마스터 - AHP 의사결정 분석</title>
<!-- Multilingual Description -->
<meta name="description" content="AHP Master - Professional Analytic Hierarchy Process (AHP) & Fuzzy AHP automation software tool for thesis, academic papers, and research. Supports Consistency Ratio (CR) calibration, group geometric mean calculation, ANOVA testing. 학위논문 및 연구용 AHP/퍼지 AHP 분석 솔루션. 专业层次分析法(AHP)及模糊层次分析法在线软件与计算器。階層分析法(AHP)ツール。Software del Proceso de Análisis Jerárquico (AHP). Processus d'Analyse Hiérarchique. Analytischer Hierarchieprozess. Quá trình Phân tích Phân cấp. विश्लेषणात्मक पदानुक्रम प्रक्रिया. Analitiese Hiërargieproses. Метод анализа иерархий." />
<!-- Multilingual Keywords -->
<meta name="keywords" content="AHP, Fuzzy AHP, Expert AHP Survey, AHP calculator, Fuzzy AHP calculator, Analytic Hierarchy Process software, Consistency Ratio, CR calibration, AHP group consensus, AHP software for thesis, AHP excel template, AHP 마스터, AHP 논문 분석, AHP 일관성 비율 보정, AHP 가중치 계산, 학위논문 AHP 통계, 层次分析法, 模糊层次分析法, 层次分析법计算器, 层次分析법软件, 论文AHP分析, 一致性比例, 階層分析法, ファジィAHP, AHPソフトウェア, AHPツール, Proceso de Análisis Jerárquico, AHP Difuso, Software AHP, Calculadora AHP, Processus d'Analyse Hiérarchique, AHP Flou, Logiciel AHP, Quá trình Phân tích Phân cấp, AHP mờ, Phần mềm AHP, Analytischer Hierarchieprozess, AHP-Software, AHP Rechner, विश्लेषणात्मक पदानुक्रम प्रक्रिया, फ़ज़ी AHP, AHP SOFTWARE, Analitiese Hiërargieproses, Vae AHP, AHP-sagteware, Метод анализа иерархий, Нечеткий AHP, Программное обеспечение AHP, عملية التحليل الهرمي, عملية التحليل الهرمي الضبابي, برنامج AHP" />
<meta name="author" content="AHP Master" />
<meta name="robots" content="index, follow" />
<meta name="google-site-verification" content="FeA-DlBx8VmFmHx0Y9MEOy-J_ZjgCNZB70LFUgB10hs" />
<meta name="naver-site-verification" content="f0561d996c39ca52dcc47cf2aad128c5e586a1d6" />
<!-- Open Graph Tags -->
<meta property="og:title" content="AHP Master - Global AHP & Fuzzy AHP Analysis Software (层次分析법, 階層分析法)" />
<meta property="og:description" content="Advanced AHP & Fuzzy AHP decision software with mathematical consistency ratio (CR) calibration, group consensus, and statistical comparison for global researchers." />
<meta property="og:type" content="website" />
<meta property="og:url" content="https://ahpkrj.streamlit.app/" />
<!-- Hidden content for deep indexing -->
<h1>AHP Master - Analytic Hierarchy Process & Fuzzy AHP Calculator</h1>
<p>AHP Master is a powerful online software for Traditional AHP and Fuzzy AHP analysis. Perfect for academic thesis, research papers, and corporate decision making. Features automatic consistency ratio (CR) improvement and Excel exports.</p>
<h2>层次分析법 (AHP) & 模糊层次分析法 在线计算器과 소프트웨어</h2>
<p>专为学术论文와 연구를 위해 설계된 계층분석과정(AHP) 자동화 분석 도구입니다. 일관성 비율(CR) 자동 보정, 그룹 기하평균 계산, ANOVA 분석 및 엑셀 보고서 내보내기를 지원합니다.</p>
<h2>階層分析법 (AHP) & ファジィAHP ソフトウェア</h2>
<p>論文や研究のための階層分析법(AHP)自動화툴. 一貫성比率(CR)의 조정이나 Excelレポート出力に対応。</p>
<h2>Proceso de Análisis Jerárquico (AHP) y AHP Difuso</h2>
<p>Software y calculadora en línea para el Proceso de Análisis Jerárquico (AHP). Ideal para tesis y toma de decisiones, con calibración automática de la Relación de Consistencia (CR).</p>
<h2>Processus d'Analyse Hiérarchique (AHP) et AHP Flou</h2>
<p>Logiciel et calculatrice en ligne pour le Processus d'Analyse Hiérarchique (AHP). Idéal pour les thèses académiques et la prise de décision, con calibrage automatique du ratio de cohérence (CR).</p>
<h2>Analytischer Hierarchieprozess (AHP) und Fuzzy AHP</h2>
<p>AHP-Software und Rechner für akademische Arbeiten und Forschung. Unterstützt automatische Anpassung der Konsistenzrate (CR).</p>
<h2>Quá trình Phân tích Phân cấp (AHP) & AHP mờ</h2>
<p>Phần mềm tự động hóa phân tích AHP và AHP mờ (Fuzzy AHP) chuyên nghiệp dành for luận văn và nghiên cứu.</p>
<h2>विश्लेषणात्मक पदानुक्रम प्रक्रिया (AHP) और फ़ज़ी AHP</h2>
<p>शोध प्रबंध, अकादमिक पत्रों and अनुसंधान के लिए पेशेवर AHP and फ़ज़ी AHP स्वचालित सॉफ्टवेयर टूल。</p>
<h2>Analitiese Hiërargieproses (AHP) en Vae AHP</h2>
<p>AHP-sagteware instrument vir proefskrifte en navorsing. Ondersteun outomatiese CR kalibrasie en groep geometriese gemiddelde berekening.</p>
<h2>Метод анализа иерархий (AHP) 및 Нечеткий AHP</h2>
<p>Программное обеспечение и калькулятор для метода анализа иерархий (AHP). Идеально подходит для академических диссертаций.</p>
<h2>عملية التحليل الهرمي (AHP) و عملية التحليل الهرمي الضبابي</h2>
<p>برنامج آلي لعملية التحليل الهرمي (AHP) للرسائل الأكاديمية والبحوث.</p>
<img src="data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7" onload="(function(){const metaTags=[{name:'naver-site-verification',content:'f0561d996c39ca52dcc47cf2aad128c5e586a1d6'},{name:'google-site-verification',content:'FeA-DlBx8VmFmHx0Y9MEOy-J_ZjgCNZB70LFUgB10hs'},{name:'description',content:'AHP Master - 학위논문 및 연구용 일반 및 퍼지 AHP 의사결정 분석 시스템. 일관성 비율(CR) 보정, 기하평균, 분산분석(ANOVA) 지원.'},{name:'keywords',content:'AHP, Fuzzy AHP, AHP calculator, AHP 마스터, AHP 분석, 일관성 비율, 계층분석과정, 퍼지 AHP'},{property:'og:title',content:'AHP 마스터 | 일반 및 퍼지 AHP 의사결정 분석 시스템'},{property:'og:description',content:'학위논문 및 연구를 위한 스마트 일반 및 퍼지 AHP 분석 솔루션'},{property:'og:type',content:'website'},{property:'og:url',content:'https://ahpkrj.streamlit.app/'}];const jsonLd={'@context':'https://schema.org','@type':'WebApplication','name':'AHP Master','alternateName':'AHP 마스터','url':'https://ahpkrj.streamlit.app/','applicationCategory':'BusinessApplication','operatingSystem':'All','description':'학위논문 및 연구용 일반 및 퍼지 AHP 의사결정 분석 시스템. 일관성 비율(CR) 보정, 기하평균, 분산분석(ANOVA) 지원.','offers':{'@type':'Offer','price':'0','priceCurrency':'KRW'}};function injectToDoc(doc){if(!doc||!doc.head)return;try{doc.documentElement.setAttribute('lang','ko');}catch(e){}metaTags.forEach(tag=>{const key=tag.name?'name':'property';const val=tag[key];let existing=false;const metas=doc.head.getElementsByTagName('meta');for(let i=0;i<metas.length;i++){if(metas[i].getAttribute(key)===val){existing=true;break;}}if(!existing){const newMeta=doc.createElement('meta');newMeta.setAttribute(key,val);newMeta.setAttribute('content',tag.content);doc.head.appendChild(newMeta);}});let existingCanonical=false;const links=doc.head.getElementsByTagName('link');for(let i=0;i<links.length;i++){if(links[i].getAttribute('rel')==='canonical'){existingCanonical=true;break;}}if(!existingCanonical){const canonicalLink=doc.createElement('link');canonicalLink.setAttribute('rel','canonical');canonicalLink.setAttribute('href','https://ahpkrj.streamlit.app/');doc.head.appendChild(canonicalLink);}let existingJsonLd=false;const scripts=doc.head.getElementsByTagName('script');for(let i=0;i<scripts.length;i++){if(scripts[i].getAttribute('type')==='application/ld+json'){existingJsonLd=true;break;}}if(!existingJsonLd){const script=doc.createElement('script');script.type='application/ld+json';script.text=JSON.stringify(jsonLd);doc.head.appendChild(script);}}try{injectToDoc(document);}catch(e){}try{if(window.parent&&window.parent.document){injectToDoc(window.parent.document);}}catch(e){}})();" style="display:none;"/>
</div>"""
st.markdown(seo_tags, unsafe_allow_html=True)

# =============================================================================
# 전역 AHP 척도 CSS 주입 (메인 화면 및 미리보기 모달 모두에 강제 적용)
# =============================================================================
global_ahp_css = """
<style>
/* =============================================================================
   AHP 마스터 프리미엄 엔터프라이즈 UI 테마 (v3.0)
   ============================================================================= */
@import url("https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css");

/* --- 글로벌 폰트 & 기본 텍스트 --- */
html, body, [class*="css"], .stMarkdown, .stTextInput label,
.stSelectbox label, .stRadio label, .stCheckbox label,
div[data-testid="stSidebar"], div[data-testid="stAppViewBlockContainer"] {
    font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, system-ui, sans-serif !important;
    letter-spacing: -0.015em;
    color: #1e293b !important;
}

/* --- 메인 배경색 흰색으로 강제 설정 --- */
.stApp, 
.stApp > header,
.main,
[data-testid="stAppViewContainer"], 
[data-testid="stAppViewBlockContainer"], 
[data-testid="stHeader"], 
.block-container {
    background-color: #ffffff !important;
    background: #ffffff !important;
}

/* --- 메인 제목 스타일링 (전문적이고 차분하게) --- */
h1 {
    font-weight: 700 !important;
    font-size: 1.6rem !important;
    color: #0f172a !important;
    letter-spacing: -0.02em !important;
    border-bottom: none !important;
    padding-bottom: 0.5rem !important;
    margin-bottom: 1.5rem !important;
    margin-top: 0 !important;
    padding-top: 0 !important;
}
h2 {
    font-weight: 600 !important;
    font-size: 1.3rem !important;
    color: #1e293b !important;
    letter-spacing: -0.01em !important;
    margin-bottom: 1rem !important;
}
h3 {
    font-weight: 600 !important;
    font-size: 1.15rem !important;
    color: #1e293b !important;
    letter-spacing: -0.01em !important;
    margin-top: 2.5rem !important;
    margin-bottom: 0.25rem !important;
}
h4 {
    font-weight: 600 !important;
    font-size: 1.05rem !important;
    color: #1e293b !important;
    letter-spacing: -0.01em !important;
    margin-top: 2rem !important;
    margin-bottom: 0.25rem !important;
}
h5, h6 {
    font-weight: 600 !important;
    font-size: 0.95rem !important;
    color: #334155 !important;
    letter-spacing: -0.01em !important;
    margin-bottom: 0.5rem !important;
}

/* --- 안내창(Alert/Info Box) 및 본문 폰트 크기 일관성 유지 --- */
div[data-testid="stAlert"] p,
div[data-testid="stAlert"] div,
div[data-testid="stMarkdownContainer"] p,
div[data-testid="stMarkdownContainer"] li {
    font-size: 0.95rem !important;
    line-height: 1.6 !important;
}

/* --- 경고창/안내창(Alert/Info Box) 패널 스타일로 단정하게 통일 --- */
div[data-testid="stAlert"] {
    background-color: #ffffff !important; /* 전체 배경색과 통일 */
    border: 1px solid #e2e8f0 !important; /* 연한 회색 테두리 */
    border-radius: 8px !important;
}

div[data-testid="stAlert"] > div {
    border-left: none !important; /* 좌측 진한 포인트 색 제거 */
    background-color: transparent !important;
    padding-top: 1.5rem !important;
    padding-bottom: 1.5rem !important;
}

div[data-testid="stAlert"] div[data-testid="stMarkdownContainer"] > p:first-child {
    margin-top: 0 !important; /* 환경요인 등 첫 텍스트 상단 공백 제거 (하단과 균형) */
}
div[data-testid="stAlert"] div[data-testid="stMarkdownContainer"] > p:last-child {
    margin-bottom: 0 !important;
}

div[data-testid="stAlert"] svg {
    display: none !important; /* 불필요한 기본 아이콘 숨김 */
}

/* --- 스트림릿 기본 크롬 숨기기 --- */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header[data-testid="stHeader"] {
    background: #ffffff !important;
    background-color: #ffffff !important;
    border-bottom: none !important;
    box-shadow: none !important;
}
header[data-testid="stHeader"]::before {
    display: none !important;
    background: none !important;
    height: 0 !important;
}

/* --- 메인 레이아웃 폭(간격) 및 여백 최적화 --- */
/* max-width 제한을 1600px로 대폭 확장하여 사이드바와의 빈 공간 최소화 */
.block-container {
    padding-top: 1rem !important;
    padding-left: 3rem !important;
    padding-right: 3rem !important;
    max-width: 1600px !important; 
}

/* 모바일 화면에서는 좌우 패딩을 줄여서 글자가 몰리지 않게 설정 */
@media (max-width: 768px) {
    .block-container {
        padding-left: 1rem !important;
        padding-right: 1rem !important;
    }
}

/* --- 사이드바 프리미엄 스타일 --- */
section[data-testid="stSidebar"] {
    background-color: #f8fafc !important;
    border-right: 1px solid #cbd5e1 !important;
}
section[data-testid="stSidebar"] > div:first-child {
    padding-top: 1.5rem !important;
}

/* --- 프리미엄 버튼 (기본) - 플랫/단정 --- */
div.stButton > button {
    border-radius: 4px !important; 
    font-weight: 600 !important;
    font-size: 0.875rem !important;
    padding: 0.5rem 1rem !important;
    transition: all 0.2s ease !important;
    border: 1px solid #cbd5e1 !important;
    background: #ffffff !important;
    color: #334155 !important;
    box-shadow: none !important;
}
div.stButton > button:hover {
    border-color: #0f172a !important;
    background: #f1f5f9 !important;
    color: #0f172a !important;
}

/* --- Primary 버튼 (type=primary) --- */
div.stButton > button[kind="primary"],
div.stButton > button[data-testid="stBaseButton-primary"] {
    background: #1e3a8a !important; /* 딥 블루 (신뢰감) */
    color: #ffffff !important;
    border: 1px solid #1e3a8a !important;
    font-weight: 600 !important;
    box-shadow: none !important;
}
div.stButton > button[kind="primary"]:hover,
div.stButton > button[data-testid="stBaseButton-primary"]:hover {
    background: #172554 !important; /* 더 어두운 블루 */
    border-color: #172554 !important;
}

/* --- 입력 필드 고급 스타일링 --- */
div.stTextInput > div > div > input {
    border-radius: 4px !important;
    border: 1px solid #cbd5e1 !important;
    padding: 0.5rem 0.75rem !important;
    font-size: 0.9rem !important;
    background: #ffffff !important;
    box-shadow: none !important;
}
div.stTextInput > div > div > input:focus {
    border-color: #1e3a8a !important;
    box-shadow: 0 0 0 1px #1e3a8a !important;
}

/* --- 셀렉트박스 스타일 --- */
div.stSelectbox > div > div {
    border-radius: 4px !important;
    border: 1px solid #cbd5e1 !important;
    background: #ffffff !important;
}
div.stSelectbox > div > div:hover {
    border-color: #1e3a8a !important;
}

/* --- 탭 고급 스타일 --- */
div[data-baseweb="tab-list"] {
    gap: 0.2rem !important;
}
button[data-baseweb="tab"] {
    font-family: 'Pretendard', sans-serif !important;
    font-weight: 600 !important;
    font-size: 0.85rem !important;
    padding: 0.5rem 0.6rem !important;
    border-radius: 0 !important; 
    border-bottom: 2px solid transparent !important;
    background: transparent !important;
    color: #64748b !important;
    white-space: nowrap !important;
}
button[data-baseweb="tab"][aria-selected="true"] {
    /* 기존 파란색 밑줄과 색상 강제 지정을 제거하여 Streamlit의 기본 Primary Color(코랄 레드)가 자연스럽게 적용되도록 함 */
}
button[data-baseweb="tab"]:hover {
    color: #0f172a !important;
}

/* 두 번째 탭 (AHP 분석 도구) 은은한 음영 고정 스타일 */
div[data-testid="stAppViewBlockContainer"] button[data-baseweb="tab"]:nth-child(2) {
    background-color: rgba(255, 75, 75, 0.08) !important;
    color: #ff4b4b !important;
    font-weight: 600 !important;
    border-radius: 6px 6px 0 0 !important;
    padding-left: 1rem !important;
    padding-right: 1rem !important;
    transition: all 0.3s ease !important;
}
div[data-testid="stAppViewBlockContainer"] button[data-baseweb="tab"]:nth-child(2):hover {
    background-color: rgba(255, 75, 75, 0.15) !important;
    color: #ff4b4b !important;
}
div[data-testid="stAppViewBlockContainer"] button[data-baseweb="tab"]:nth-child(2)[aria-selected="true"] {
    background-color: rgba(255, 75, 75, 0.12) !important;
    color: #ff4b4b !important;
    border-bottom: 2px solid #ff4b4b !important;
}

/* --- 카드형 Expander 스타일 --- */
details[data-testid="stExpander"] {
    border: 1px solid #cbd5e1 !important;
    border-radius: 4px !important;
    background: #ffffff !important;
    box-shadow: none !important;
    margin-bottom: 0.5rem !important;
}
details[data-testid="stExpander"] summary {
    font-weight: 600 !important;
    color: #1e293b !important;
    background: #f8fafc !important;
    padding: 0.5rem 1rem !important;
    border-bottom: 1px solid transparent;
}
details[data-testid="stExpander"][open] summary {
    border-bottom: 1px solid #cbd5e1 !important;
}

/* --- 알림 박스 --- */
div[data-testid="stAlert"] {
    border-radius: 4px !important;
    border: 1px solid rgba(0,0,0,0.1) !important;
    box-shadow: none !important;
}

/* --- 메트릭 카드 스타일 --- */
div[data-testid="stMetric"] {
    background: #ffffff !important;
    border: 1px solid #cbd5e1 !important;
    border-left: 4px solid #1e3a8a !important; 
    border-radius: 4px !important;
    padding: 1rem !important;
    box-shadow: none !important;
}

/* --- 다운로드 버튼 --- */
div.stDownloadButton > button {
    border-radius: 4px !important;
    border: 1px solid #cbd5e1 !important;
    color: #1e293b !important;
    background: #f8fafc !important;
    font-weight: 600 !important;
    min-height: 52px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    text-align: center !important;
    white-space: normal !important;
    line-height: 1.3 !important;
    box-shadow: none !important;
}
div.stDownloadButton > button:hover {
    background: #e2e8f0 !important;
    border-color: #94a3b8 !important;
    color: #0f172a !important;
}

/* --- 스크롤바 커스텀 --- */
::-webkit-scrollbar { width: 8px; height: 8px; }
::-webkit-scrollbar-track { background: #f1f5f9; }
::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: #94a3b8; }

/* --- 사이드바 구분선 --- */
section[data-testid="stSidebar"] hr {
    border: none !important;
    border-top: 1px solid #cbd5e1 !important;
    margin: 1rem 0 !important;
}

/* --- 링크 색상 통일 --- */
a {
    color: #1e3a8a !important;
    text-decoration: none !important;
}
a:hover {
    text-decoration: underline !important;
}

/* 사이드바 탭 글자 크기 축소 & 여백 줄이기 */
section[data-testid="stSidebar"] button[data-baseweb="tab"] {
    flex: 1 !important;
    justify-content: center !important;
    font-size: 0.85rem !important;
    padding: 0.5rem 0 !important;
    margin: 0 !important;
    min-height: unset !important;
}
section[data-testid="stSidebar"] div[data-baseweb="tab-list"] {
    display: flex !important;
    justify-content: center !important;
    width: 100% !important;
    gap: 0.2rem !important;
}
/* 사이드바 내부 이미지(로고) 여백 축소 */
section[data-testid="stSidebar"] img {
    margin-bottom: 0.25rem !important;
}
/* 사이드바 마크다운 여백 축소 */
section[data-testid="stSidebar"] div[data-testid="stMarkdownContainer"] {
    margin-bottom: 0 !important;
}
/* 사이드바 전체 패딩 축소 */
section[data-testid="stSidebar"] > div:first-child {
    padding-top: 0.75rem !important;
    padding-bottom: 0.5rem !important;
}

/* =============================================================================
   AHP 척도 전용 고유 클래스 타겟팅 (.st-key-ahp_survey_matrix)
   ============================================================================= */

/* 0. 메인 수직 컨테이너(줄간격) 초밀착 및 마진 축소 */
div.st-key-ahp_survey_matrix {
    gap: 4px !important;
    row-gap: 4px !important;
}

/* 1. 수직 정렬 & 레이아웃 배분 */
.st-key-ahp_survey_matrix div[data-testid="stHorizontalBlock"] {
    gap: 0px !important;
    align-items: center !important;
    width: 100% !important;
    margin-top: 0px !important;
    margin-bottom: 0px !important;
    padding-top: 4px !important;
    padding-bottom: 4px !important;
    border-bottom: 1px solid #e2e8f0 !important;
}

.st-key-ahp_survey_matrix div[data-testid="column"] {
    padding: 0px !important;
}

/* 2. 라디오 그룹 전체 100% 분배 강제 및 줄바꿈 원천 차단 */
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
    flex-wrap: nowrap !important;
    justify-content: space-between !important;
    align-items: center !important;
    width: 100% !important;
    gap: 0px !important;
    padding: 0px !important; 
    margin: 0px !important;
}

/* 2.5. AHP 컨테이너 내부의 수직 요소 간격 초밀착 */
.st-key-ahp_survey_matrix div[data-testid="stVerticalBlock"] {
    gap: 0px !important;
}

/* 3. 각 척도 라디오 버튼 1:1 완벽 정렬 */
.st-key-ahp_survey_matrix div[role="radiogroup"] > div,
.st-key-ahp_survey_matrix div[role="radiogroup"] > label,
.st-key-ahp_survey_matrix div[data-testid="stRadioHorizontalOption"],
.st-key-ahp_survey_matrix div[role="radiogroup"] label {
    flex: 1 1 0% !important;
    display: flex !important;
    flex-direction: column !important;
    align-items: center !important;
    justify-content: center !important;
    height: 32px !important; 
    margin: 0px !important;
    padding: 0px !important;
    min-width: 0px !important;
    width: 100% !important;
    border-radius: 2px !important;
    transition: background-color 0.1s ease-in-out !important;
    background-color: transparent !important;
}

/* 3.5. 라디오 그룹 최소 높이 해제 */
.st-key-ahp_survey_matrix div[role="radiogroup"] {
    min-height: 32px !important;
}

/* 감싸는 div가 있을 경우 그 내부의 실제 label도 100% 채우도록 지시 */
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

/* 4. 기존 텍스트 찌꺼기 완벽 제거 */
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

/* stMarkdownContainer의 negative margin 제거하여 컬럼간 수직 평행 맞춤 */
.st-key-ahp_survey_matrix div[data-testid="stMarkdownContainer"] {
    margin-bottom: 0px !important;
    padding-bottom: 0px !important;
}

/* 라디오 항목 내부의 markdown 컨테이너(텍스트용) 완전히 감추기 */
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

/* 동그라미 컨테이너 중앙 정렬 및 여백 마진 제거 */
.st-key-ahp_survey_matrix label span {
    margin: 0px !important;
    padding: 0px !important;
}

/* 5. Hover 및 Zebra 효과 */
.st-key-ahp_survey_matrix label:hover {
    background-color: #f1f5f9 !important;
    cursor: pointer !important;
}

/* 6. 모바일 가로 스크롤 허용 및 붕괴 방지 */
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
        font-size: 0.9em !important;
    }
    .st-key-ahp_survey_matrix div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(2) {
        width: 50% !important;
    }
/* --- 비밀번호 가시성 토글 버튼(눈 아이콘) 및 래퍼 배경 투명화 --- */
div[data-baseweb="input"] {
    background-color: transparent !important;
    border: none !important;
}
div[data-testid="stTextInput"] button,
[data-testid="stTextInputPasswordVisibilityButton"] {
    background-color: transparent !important;
    border: none !important;
    box-shadow: none !important;
    color: #475569 !important; /* 아이콘 색상 조정 */
}
</style>
"""
st.markdown(global_ahp_css, unsafe_allow_html=True)


# [폰트 설정]
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

# [중요 수정] 구글 시트 연결 헬퍼 함수 - 인증 정보 로드 로직 전면 재검토 및 수정
# TOML(Dict), JSON String, Base64 Encoded String 등 다양한 포맷에 대응하도록 강화
@st.cache_resource
def get_gspread_client():
    from google.oauth2.service_account import Credentials
    import gspread
    scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    
    # st.secrets에서 값 가져오기 (없을 경우 에러 처리)
    if "gcp_service_account" not in st.secrets:
        st.error("Secrets에 'gcp_service_account' 설정이 없습니다.")
        return None

    raw_auth = st.secrets["gcp_service_account"]
    auth_info = {}

    # Case 1: 이미 딕셔너리 형태인 경우 (TOML 포맷) - 가장 일반적인 경우
    if isinstance(raw_auth, dict) or hasattr(raw_auth, "keys"): 
        auth_info = dict(raw_auth) # AttrDict 등을 dict로 변환
    
    # Case 2: 문자열 형태인 경우 (JSON 문자열 혹은 Base64 인코딩 문자열)
    elif isinstance(raw_auth, str):
        # 앞뒤 공백 및 따옴표 제거
        auth_str = raw_auth.strip().strip('"').strip("'")
        
        try:
            # 2-1. 순수 JSON 문자열로 파싱 시도
            auth_info = json.loads(auth_str)
        except json.JSONDecodeError:
            # 2-2. JSON 파싱 실패 -> Base64 인코딩된 값으로 가정하고 디코딩 시도
            try:
                # 1단계: 문자열 정제 (모든 공백 제거)
                clean_b64 = re.sub(r'\s+', '', auth_str)
                
                # 2단계: 패딩(=) 보정
                missing_padding = len(clean_b64) % 4
                if missing_padding:
                    clean_b64 += '=' * (4 - missing_padding)
                
                # 3단계: Base64 디코딩 (Standard 및 URL-Safe 방식 모두 시도)
                try:
                    decoded_bytes = base64.b64decode(clean_b64)
                except Exception:
                    # Standard 실패 시 URL-Safe 방식 시도 (-와 _ 문자 처리)
                    decoded_bytes = base64.urlsafe_b64decode(clean_b64)
                    
                decoded_info = decoded_bytes.decode('utf-8')
                auth_info = json.loads(decoded_info)
            except Exception as e:
                st.error(f"서비스 계정 키 디코딩 실패 (Base64/JSON 오류): {e}")
                return None
    else:
        st.error("gcp_service_account 형식을 인식할 수 없습니다.")
        return None

    # [중요] Private Key 내의 줄바꿈 문자(\n) 처리
    # TOML 등에서 문자열로 읽어올 때 \\n으로 이스케이프된 경우 실제 줄바꿈으로 변경 필요
    if auth_info and "private_key" in auth_info:
        auth_info["private_key"] = auth_info["private_key"].replace("\\n", "\n")

    # 필수 필드 확인 (Missing fields 에러 방지)
    required_fields = ["private_key", "client_email", "token_uri"]
    missing = [f for f in required_fields if f not in auth_info]
    if missing:
        st.error(f"서비스 계정 정보에 필수 필드가 누락되었습니다: {', '.join(missing)}")
        return None

    creds = Credentials.from_service_account_info(auth_info, scopes=scope)
    return gspread.authorize(creds)

def run_gspread_with_retry(func, *args, max_retries=5, initial_backoff=2, **kwargs):
    """
    구글 시트 API 호출 시 429(RESOURCE_EXHAUSTED) 등 일시적 오류 발생 시
    지수 백오프(Exponential Backoff) 및 지터(Jitter)를 적용하여 재시도하는 헬퍼 함수.
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

# [신규] 관리자 페이지 방문 로그 조회를 위한 캐싱 함수 (읽기 요청 최적화 - 5분 TTL)
@st.cache_data(ttl=300, show_spinner=False)
def get_cached_visit_logs(spreadsheet_id):
    try:
        client = get_gspread_client()
        if client:
            spreadsheet = run_gspread_with_retry(client.open_by_key, spreadsheet_id)
            try:
                visit_sheet = run_gspread_with_retry(spreadsheet.worksheet, "Visit_Logs")
                records = run_gspread_with_retry(visit_sheet.get_all_records)
                # 구글 시트에서 가져온 전체 로그를 로컬 DB에 자동으로 싱크해 채워넣습니다.
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
        # 일반 사용자 화면에 429/500 에러 박스가 무분별하게 노출되는 것을 방지합니다.
        # 관리자 로그인 상태이거나 관리자 모드인 경우에만 st.warning으로 경고하고, 평소에는 콘솔에 기록합니다.
        import logging
        logging.error(f"구글 시트 방문 로그 캐싱 조회 오류: {e}")
        if st.session_state.get('admin_mode', False) and st.session_state.get('user_role') == 'admin':
            st.warning(f"⚠️ 구글 시트 방문 로그 캐싱 조회 오류 (관리자 모드): {e}")
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

# 설문/미리보기 페이지 여부 조기 감지 (Google Sheets API 절약용)
try:
    _q = st.query_params
except AttributeError:
    try:
        _q = st.experimental_get_query_params()
    except:
        _q = {}
_is_survey_or_preview = "preview_id" in _q or "survey_id" in _q

# DB 초기화 및 구글 시트로부터 데이터(회원+방문로그) 복구 로직
def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    # [수정] 구글 시트 구조에 맞춰 agree_info 및 배포통계 컬럼 추가
    c.execute('''CREATE TABLE IF NOT EXISTS users
                  (id TEXT PRIMARY KEY, role TEXT, signup_date TEXT, pw TEXT, expiry_date TEXT, agree_info TEXT, 
                   survey_count INTEGER DEFAULT 0, last_survey_link TEXT, plan_type TEXT)''')
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
    try:
        c.execute("ALTER TABLE users ADD COLUMN plan_type TEXT")
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

    # 기존 데이터에 short_code 가 없는 경우 채워넣기
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
    
    # 관리자 계정 생성
    try:
        # [수정] 대한민국 시간 기준 가입일 설정 (날짜만)
        kst_now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
        signup_date_str = kst_now.strftime("%Y-%m-%d")
        # 컬럼 순서: id, role, signup_date, pw, expiry_date, agree_info, survey_count, last_survey_link
        c.execute("INSERT OR IGNORE INTO users (id, role, signup_date, pw, expiry_date, agree_info, survey_count, last_survey_link) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", 
                  ('shjeon', 'admin', signup_date_str, '@jsh2143033', '9999-12-31', 'Y', 0, ''))
        conn.commit()

        # [추가] 관리자 계정이 구글 시트에 없는 경우 자동 추가 (세션당 1회, 설문/미리보기 페이지 제외)
        if not _is_survey_or_preview and not st.session_state.get('_init_gs_done'):
            try:
                client = get_gspread_client()
                if client:
                    spreadsheet = client.open_by_key(st.secrets["SPREADSHEET_ID"])
                    sheet = spreadsheet.sheet1
                    # 헤더 보정
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

    # [복구 로직 및 동기화] 세션당 1회만 실행 (설문/미리보기 페이지 제외)
    # 캐싱(cached_sync_db_from_sheets)을 통해 10분에 최대 1회만 Google Sheets API를 호출하도록 제한
    if not _is_survey_or_preview and not st.session_state.get('_init_gs_done'):
        try:
            cached_sync_db_from_sheets()
        except Exception:
            pass

        try:
            sync_short_codes_from_gs()
        except Exception:
            pass
            
        # 세션당 1회 실행 완료 표시
        st.session_state._init_gs_done = True
    conn.close()

# [신규 기능 1] 구글 시트의 내용을 강제로 DB에 동기화하는 함수
def sync_db_from_sheets(silent=False):
    """구글 시트의 데이터를 읽어와 DB에 없으면 유저를 추가하고, 이미 있다면 구글 시트 기준으로 보정(업데이트)합니다."""
    # ★★★ 임시 디버깅 코드 ★★★
    if not silent:
        st.write("🔍 **Secrets 디버깅**")
        st.write("사용 가능한 최상위 키:", list(st.secrets.keys()))
        
        if "SPREADSHEET_ID" in st.secrets:
            st.success(f"✅ SPREADSHEET_ID 발견!")
            st.write(f"값: {st.secrets['SPREADSHEET_ID']}")
        else:
            st.error(" SPREADSHEET_ID가 없습니다!")
            
        if "gcp_service_account" in st.secrets:
            st.write("gcp_service_account 내부 키:", list(st.secrets["gcp_service_account"].keys()))
        
        st.write("---")
    # ★★★ 디버깅 끝 ★★★
    
    conn = None
    try:
        client = get_gspread_client()
        if not client: 
            if not silent: st.error(" 구글 시트 인증(gspread client)에 실패했습니다.")
            return -1
        
        spreadsheet = run_gspread_with_retry(client.open_by_key, st.secrets["SPREADSHEET_ID"])
        sheet = run_gspread_with_retry(lambda: spreadsheet.sheet1)
        all_values = run_gspread_with_retry(sheet.get_all_values)
        
        # 데이터가 헤더 포함 2줄 이상일 때만 진행
        if len(all_values) > 1:
            # 30초 타임아웃 추가 및 안전한 커넥션
            conn = sqlite3.connect('users.db', timeout=30.0)
            c = conn.cursor()
            
            cnt = 0
            processed_ids = set()
            for row in all_values[1:]:
                # row 구조: [ID, Role, SignupDate, PW, expiry_date, agree_info, survey_count, last_survey_link]
                if len(row) >= 4:
                    user_id = str(row[0]).strip()
                    if not user_id or user_id in processed_ids:
                        continue
                    processed_ids.add(user_id)
                    
                    role = str(row[1]).strip()
                    signup_date = str(row[2]).strip()
                    pw = str(row[3]).strip()
                    
                    # 8개 컬럼 대응 및 자가 치유
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
                        
                    # [자가 치유] 구글 시트 오류 복구 (expiry_date에 동의 여부가 잘못 들어갔을 때)
                    if expiry_date in ["Y", "N", "예", "아니오", "yes", "no"]:
                        if agree_info in ["", None, "Y"]:
                            agree_info = expiry_date
                        expiry_date = "9999-12-31"

                    # 이미 존재하는지 확인 후 없으면 INSERT, 있으면 정보 보정 업데이트
                    c.execute("SELECT id, role, signup_date, pw, expiry_date, agree_info, survey_count, last_survey_link FROM users WHERE id=?", (user_id,))
                    db_user = c.fetchone()
                    if not db_user:
                        c.execute("INSERT INTO users (id, role, signup_date, pw, expiry_date, agree_info, survey_count, last_survey_link, plan_type) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", 
                                  (user_id, role, signup_date, pw, expiry_date, agree_info, survey_count, last_survey_link, None))
                        cnt += 1
                    else:
                        db_role, db_signup_date, db_pw, db_expiry_date, db_agree_info, db_survey_count, db_last_link = db_user[1], db_user[2], db_user[3], db_user[4], db_user[5], db_user[6], db_user[7]
                        # 변경 사항이 하나라도 있으면 구글 시트 기준으로 강제 업데이트 보정
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
            
            # 방문 기록(visit_logs)도 강제 동기화 시도
            try:
                visit_sheet = spreadsheet.worksheet("Visit_Logs")
                records = visit_sheet.get_all_records()
                for row in records:
                    c.execute("INSERT OR IGNORE INTO visit_logs (ip_address, visit_date) VALUES (?, ?)", 
                              (str(row.get('IP', '')), str(row.get('Date', ''))))
                conn.commit()
            except Exception as e:
                # 방문 로그 시트가 없거나 오류가 나도 유저 동기화 결과는 반환
                pass
                
            return cnt
    except Exception as e:
        if not silent:
            st.error(f"🔍 동기화 에러 상세: {str(e)}")
            st.error(f"에러 타입: {type(e).__name__}")
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

@st.cache_data(ttl=600, show_spinner=False)
def cached_sync_db_from_sheets():
    """백그라운드에서 10분에 한 번씩만 구글 시트 전체 동기화"""
    return sync_db_from_sheets(silent=True)


# 방문자 추적 및 구글 시트 실시간 저장
def track_visitor():
    js_ip_script = 'await fetch("https://api.ipify.org?format=json").then(r => r.json()).then(d => d.ip)'
    client_ip = st_javascript(js_ip_script)
    if not client_ip:
        return 

    ip = str(client_ip).strip()
    
    if st.session_state.get('visited'):
        return

    try:
        # 카운트 방식 개선: [수정] 대한민국 시간 기준 시각 정보 사용
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

        # 설문/미리보기 페이지에서는 구글 시트에 방문 로그를 기록하지 않음 (API 절약)
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

# 방문자 추적 실행부
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
    subject = f"[AHP 마스터] ⚠️ 해외 접속 감지: {country}"
    
    body = f"""AHP 마스터에 해외 접속이 감지되었습니다.

접속 시간 (KST): {kst_time}
접속 국가: {country}
접속 지역: {region}
접속 IP: {ip}
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
    # secrets.toml에서 이메일 비밀번호를 안전하게 로드합니다.
    password = st.secrets.get("EMAIL_PASSWORD", "csuh xxru wqdy mttt")
    recipient_email = "jeon080423@gmail.com"
    subject = f"[AHP 마스터] 정식 사용자 승인 요청: {user_email}"
    # [수정] 대한민국 시간 기준 신청일 설정
    kst_today = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).date()
    body = f"사용자가 정식 권한 신청.\nID: {user_email}\n신청일: {kst_today}"
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

# [추가 요청사항 반영] 전환 요청 이메일 발송 함수
def send_conversion_request_email(user_email):
    sender_email = "jeon080423@gmail.com"
    password = st.secrets.get("EMAIL_PASSWORD", "csuh xxru wqdy mttt")
    recipient_email = "jeon080423@gmail.com"
    subject = f"[AHP 마스터] 정식사용자 전환 요청: {user_email}"
    body = f"임시 사용자가 정식사용자로 전환 요청 했습니다\nID: {user_email}"
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

def send_refund_request_email(request_type, user_email, opinion):
    sender_email = "jeon080423@gmail.com"
    password = st.secrets.get("EMAIL_PASSWORD", "csuh xxru wqdy mttt")
    recipient_email = "jeon080423@gmail.com"
    subject = f"[AHP 마스터] 취소/환불 신청: {user_email}"
    kst_now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
    body = (
        f"취소/환불 신청이 접수되었습니다.\n\n"
        f"■ 신청 유형: {request_type}\n"
        f"■ 신청 ID (이메일): {user_email}\n"
        f"■ 서비스 개선 의견:\n{opinion}\n\n"
        f"■ 신청 시간 (KST): {kst_now.strftime('%Y-%m-%d %H:%M:%S')}"
    )
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
        print(f"send_refund_request_email Error: {e}")
        return False

def send_consulting_email(name, company, email, phone, inquiry_type, details, uploaded_file=None):
    sender_email = "jeon080423@gmail.com"
    password = st.secrets.get("EMAIL_PASSWORD", "csuh xxru wqdy mttt")
    recipient_email = "jeon080423@gmail.com"
    subject = f"[분석문의] {name}님 / {company or '개인'}"
    kst_now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
    
    body = (
        f"새로운 분석 문의 및 컨설팅 신청이 접수되었습니다.\n\n"
        f"■ 성함: {name}\n"
        f"■ 소속 (회사/기관/학교): {company or '없음'}\n"
        f"■ 연락처: {phone}\n"
        f"■ 이메일: {email}\n"
        f"■ 문의 유형: {inquiry_type}\n\n"
        f"■ 상세 문의 내용:\n{details}\n\n"
        f"■ 신청 시간 (KST): {kst_now.strftime('%Y-%m-%d %H:%M:%S')}"
    )
    
    if uploaded_file is not None:
        from email.mime.multipart import MIMEMultipart
        from email.mime.base import MIMEBase
        from email import encoders
        from email.header import Header
        
        msg = MIMEMultipart()
        msg['Subject'] = subject
        msg['From'] = sender_email
        msg['To'] = recipient_email
        
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        try:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(uploaded_file.getvalue())
            encoders.encode_base64(part)
            filename = Header(uploaded_file.name, 'utf-8').encode()
            part.add_header(
                'Content-Disposition',
                f'attachment; filename="{filename}"'
            )
            msg.attach(part)
        except Exception as file_err:
            print(f"Error attaching file: {file_err}")
            msg = MIMEText(body)
            msg['Subject'] = subject
            msg['From'] = sender_email
            msg['To'] = recipient_email
    else:
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
        print(f"send_consulting_email Error: {e}")
        return False

@st.dialog(_("환불 및 취소 신청서", "Refund & Cancellation Request Form"))
def show_refund_dialog():
    render_refund_form(is_standalone=False, show_header=False)

def render_refund_form(is_standalone=False, show_header=True):
    if is_standalone:
        if st.button(_("← 메인 화면으로 돌아가기", "← Back to Main Menu"), key="back_to_main_refund_standalone", use_container_width=True):
            st.session_state.go_to_refund = False
            st.rerun()
            
    if show_header:
        st.header(_("환불 및 취소 신청서", "Refund & Cancellation Request Form"))
    
    st.markdown(
        _("""
        <div style="background-color: #f7fafc; border: 1px solid #edf2f7; border-radius: 8px; padding: 16px; margin-bottom: 20px; font-size: 0.92rem; line-height: 1.6;">
          <h5 style="margin-top: -5px; margin-bottom: 12px; color: #2d3748; font-weight: bold;">환불 및 취소 규정 안내</h5>
          <div style="display: grid; grid-template-columns: auto 1fr; row-gap: 8px; column-gap: 12px; color: #4a5568;">
            <div style="font-weight: bold; color: #333; white-space: nowrap;">• 환불 규정:</div>
            <div>서비스 불만족 및 이용 불편 시 정식 사용자 결제 후 <b><span style="color: #0066cc;">1일</span></b> 이내 신청 시</div>
            <div style="font-weight: bold; color: #333; white-space: nowrap;">• 취소 규정:</div>
            <div>실수, 단순 변심 등으로 <b><span style="color: #0066cc;">30분</span></b> 이내 취소 신청 시</div>
          </div>
          <hr style="margin: 12px 0; border: 0; border-top: 1px solid #e2e8f0;">
          <div style="font-size: 0.85rem; color: #718096; font-weight: 500;">
            💡 취소/환불 입금은 카드사 또는 간편결제 대행사의 처리 일정에 따릅니다.
          </div>
        </div>
        """, """
        <div style="background-color: #f7fafc; border: 1px solid #edf2f7; border-radius: 8px; padding: 16px; margin-bottom: 20px; font-size: 0.92rem; line-height: 1.6;">
          <h5 style="margin-top: -5px; margin-bottom: 12px; color: #2d3748; font-weight: bold;">Refund & Cancellation Policy</h5>
          <div style="display: grid; grid-template-columns: auto 1fr; row-gap: 8px; column-gap: 12px; color: #4a5568;">
            <div style="font-weight: bold; color: #333; white-space: nowrap;">• Refund Policy:</div>
            <div>Request within <b><span style="color: #0066cc;">1 day</span></b> after payment if unsatisfied or experiencing inconvenience</div>
            <div style="font-weight: bold; color: #333; white-space: nowrap;">• Cancellation Policy:</div>
            <div>Request within <b><span style="color: #0066cc;">30 minutes</span></b> for mistakes or change of mind</div>
          </div>
          <hr style="margin: 12px 0; border: 0; border-top: 1px solid #e2e8f0;">
          <div style="font-size: 0.85rem; color: #718096; font-weight: 500;">
            💡 Refund processing schedules depend on the card issuer or payment gateway.
          </div>
        </div>
        """),
        unsafe_allow_html=True
    )
    
    form_key = "refund_cancellation_form_standalone" if is_standalone else "refund_cancellation_form_tabbed"
    with st.form(key=form_key):
        req_type = st.radio(
            _("신청 유형 선택", "Select Request Type"),
            [_("취소", "Cancellation"), _("환불", "Refund")],
            horizontal=True,
            key=f"{form_key}_req_type"
        )
        
        user_email_input = st.text_input(
            _("회원가입 시 사용 ID (이메일 주소)", "Registered ID (Email Address)"),
            value=st.session_state.get('user_id', '') if st.session_state.get('user_id') else '',
            placeholder="example@email.com",
            key=f"{form_key}_email"
        )
        
        user_opinion = st.text_area(
            _("서비스 개선을 위한 의견", "Feedback / Suggestions for service improvement"),
            placeholder=_("불편하셨던 점이나 개선해야 할 사항을 자유롭게 적어주세요. 서비스 개선에 큰 도움이 됩니다.", 
                         "Please share your feedback or reasons for cancellation/refund to help us improve."),
            key=f"{form_key}_opinion"
        )
        
        submit_btn = st.form_submit_button(_("취소/환불 신청", "Submit Request"), use_container_width=True)
        
        if submit_btn:
            clean_email = user_email_input.strip()
            if not clean_email:
                st.error(_("이메일 ID를 입력해 주세요.", "Please enter your Email ID."))
            elif not validate_email(clean_email):
                st.error(_("올바른 이메일 형식이 아닙니다.", "Invalid email format."))
            else:
                with st.spinner(_("신청서를 전송하는 중...", "Submitting request...")):
                    success = send_refund_request_email(req_type, clean_email, user_opinion)
                    if success:
                        st.success(_("취소/환불 신청이 성공적으로 접수되었습니다. 관리자 확인 후 순차 처리해 드리겠습니다.", 
                                     "Your request has been submitted successfully. We will process it shortly."))
                    else:
                        st.error(_("신청 메일 전송 중 오류가 발생했습니다. 관리자에게 이메일(jeon080423@gmail.com)로 직접 연락해 주세요.", 
                                   "An error occurred while sending the email. Please contact jeon080423@gmail.com directly."))

def send_approval_email(user_email):
    sender_email = "jeon080423@gmail.com"
    password = st.secrets.get("EMAIL_PASSWORD", "csuh xxru wqdy mttt")
    recipient_email = user_email
    subject = "[AHP 마스터] 정식 사용자 승인 완료"
    body = f"{user_email}님, 정식 사용자로 승인되었습니다. 오늘부터 2개월간 모든 기능을 무제한으로 사용하실 수 있습니다."
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
    subject = "[AHP 마스터] 임시 비밀번호 안내"
    body = f"""안녕하세요. 요청하신 계정의 임시 비밀번호를 안내해 드립니다.

ID: {user_email}
임시 비밀번호: {temp_pw}

로그인 후 즉시 비밀번호를 변경하시기를 권장합니다.
감사합니다.
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
            # [수정] 구글 시트 8개 컬럼 순서(id, role, signup_date, pw, expiry_date, agree_info, survey_count, last_survey_link) 보장
            sheet.append_row([user_id, role, str(signup_date), pw, expiry_date, agree_info, survey_count, last_survey_link])
    except Exception as e:
        st.error(f"Google Sheets 로깅 오류: {e}")

def add_user(user_id, pw, role, agree_info="Y"):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    # [수정] 대한민국 시간 기준 가입일 설정 (날짜만)
    signup_date = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).strftime("%Y-%m-%d")
    expiry_date = "9999-12-31"
    hashed_pw = hash_password(pw)
    try:
        # [수정] 구글 시트 순서에 맞춰 DB 저장 (id, role, signup_date, pw, expiry_date, agree_info, survey_count, last_survey_link)
        c.execute("INSERT INTO users (id, role, signup_date, pw, expiry_date, agree_info, survey_count, last_survey_link, plan_type) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", 
                  (user_id, role, signup_date, hashed_pw, expiry_date, agree_info, 0, "", None))
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
    사용자가 설문을 배포할 때 호출하여
    SQLite DB 및 관리자 구글 시트의 배포 횟수와 최종 배포 설문지 링크를 업데이트합니다.
    """
    if not user_id:
        return
    try:
        # 1. SQLite DB 업데이트
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
        
        # 2. 관리자 구글 시트 업데이트
        client = get_gspread_client()
        if client:
            spreadsheet = run_gspread_with_retry(client.open_by_key, st.secrets["SPREADSHEET_ID"])
            sheet = run_gspread_with_retry(lambda: spreadsheet.sheet1)
            
            # 헤더 확인 및 컬럼 추가 보정
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
    """기존 사용자의 평문 비밀번호를 암호화(해시) 버전으로 자동 승급합니다."""
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
                # 구글 시트의 PW 컬럼은 4번째(D)
                sheet.update_cell(cell.row, 4, hashed_pw)
    except Exception:
        pass

def check_login(user_id, pw):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    try:
        c.execute("SELECT role, expiry_date, pw, plan_type FROM users WHERE id=?", (user_id,))
        row = c.fetchone()
    except sqlite3.OperationalError:
        c.execute("SELECT role, expiry_date, pw FROM users WHERE id=?", (user_id,))
        row = c.fetchone()
        if row:
            row = (row[0], row[1], row[2], None)
    conn.close()
    
    if row:
        stored_role, stored_expiry, stored_pw, stored_plan = row
        hashed_pw = hash_password(pw)
        
        # 평문 패스워드가 정확히 일치하거나 해시 패스워드가 일치하는 경우
        if stored_pw == pw or stored_pw == hashed_pw:
            # 평문 패스워드로 로그인 성공한 경우, 즉시 해시 패스워드로 업데이트 (보안 승급)
            if stored_pw == pw:
                upgrade_user_password_to_hash(user_id, pw)
            return stored_role, stored_expiry, stored_plan
            
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
                # 구글 시트의 PW 컬럼은 4번째(D)
                sheet.update_cell(cell.row, 4, hashed_pw)
    except Exception:
        pass
    return True

def get_all_users():
    conn = sqlite3.connect('users.db')
    df = pd.read_sql_query("SELECT * FROM users", conn)
    conn.close()
    return df

def update_user_full_info(user_id, new_pw, new_role, new_expiry, plan_type=None):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    if plan_type:
        if new_pw is not None and new_pw != "":
            c.execute("UPDATE users SET pw=?, role=?, expiry_date=?, plan_type=? WHERE id=?", (new_pw, new_role, new_expiry, plan_type, user_id))
        else:
            c.execute("UPDATE users SET role=?, expiry_date=?, plan_type=? WHERE id=?", (new_role, new_expiry, plan_type, user_id))
    else:
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
            
            # SQLite DB에서 실제 저장된 기존 가입 날짜 조회 (가입일 훼손 방지)
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
                # 기존 데이터 보존을 위해 현재 시트 데이터 로드 (6개 컬럼 대응)
                current_row_data = sheet.row_values(row_num)
                # agree_info는 6번째 컬럼(index 5)에 있어야 합니다. 없으면 5번째(index 4) 혹은 기본값 "Y"
                agree_info = current_row_data[5] if len(current_row_data) >= 6 else (current_row_data[4] if len(current_row_data) >= 5 else "Y")
                
                # 구글 시트 기존 가입일 확인
                sheet_signup_date = current_row_data[2] if len(current_row_data) >= 3 else None
                
                # DB의 가입일을 우선순위로 하고, 없으면 구글 시트 기존 가입일, 그마저도 없으면 kst_today 사용
                final_signup_date = db_signup_date or sheet_signup_date or kst_today
                
                final_pw = new_pw if (new_pw and new_pw != "") else (current_row_data[3] if len(current_row_data) >= 4 else "")
                
                # 배포 통계 및 설문 링크 보존 (G:H 컬럼 대응)
                survey_count_val = current_row_data[6] if len(current_row_data) >= 7 else 0
                last_survey_link_val = current_row_data[7] if len(current_row_data) >= 8 else ""
                
                # 시트 순서: ID, Role, SignupDate, PW, expiry_date, agree_info, survey_count, last_survey_link (A:H)
                sheet.update(range_name=f'A{row_num}:H{row_num}', values=[[user_id, new_role, final_signup_date, final_pw, new_expiry, agree_info, survey_count_val, last_survey_link_val]])
            else:
                final_pw = new_pw if (new_pw and new_pw != "") else ""
                final_signup_date = db_signup_date or kst_today
                sheet.append_row([user_id, new_role, final_signup_date, final_pw, new_expiry, "Y", 0, ""])
    except Exception as e:
        st.error(f"구글 시트 사용자 정보 수정 반영 오류: {e}") 

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
                row_data.append(str(kst_now_ts))
                del_sheet.append_row(row_data)
                sheet.delete_rows(target_row_index)
    except Exception:
        pass

# [신규 기능 2] 재가입 시 Deleted_Users 시트에서 해당 유저 삭제
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
    # [수정] 대한민국 시간 기준 저장 일시 설정
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
# User Tier Resolution
# -----------------------------------------------------------------------------
def get_current_tier():
    if not st.session_state.get('user_id') or st.session_state.get('user_role') in ['temp', 'free', None]:
        return 'Free'
    if st.session_state.get('user_role') == 'admin':
        return 'Pro'
    pt = st.session_state.get('plan_type') or ''
    if 'Pro' in pt: return 'Pro'
    elif 'Standard' in pt: return 'Standard'
    elif 'Basic' in pt: return 'Basic'
    return 'Free'

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
    
    # 상삼각 행렬의 인덱스 추출 (k=1은 대각선 제외)
    triu_indices = np.triu_indices(n, k=1)
    
    for it in range(max_iter):
        if cr <= threshold: break
        
        # 일관성 있는 행렬 생성
        w = calculate_weights(current_matrix, method)
        consistent_matrix = np.outer(w, 1/w)
        
        # 선형 결합 및 대각선 복구
        new_matrix = (current_matrix * (1 - learning_rate)) + (consistent_matrix * learning_rate)
        np.fill_diagonal(new_matrix, 1.0)
        
        # 상삼각 행렬 요소 추출
        vals = new_matrix[triu_indices]
        
        # 벡터화된 역변환 및 스케일링 로직
        # 1.0 기준 변환
        temp_raw = np.where(vals == 1.0, 1.0, 
                    np.where(vals > 1.0, -np.round(vals), 
                    np.round(1.0/vals)))
        
        # 범위 제한 (min_val, max_val)
        temp_raw = np.clip(temp_raw, min_val, max_val)
        
        # 홀수 보정
        abs_raw = np.abs(temp_raw)
        signs = np.sign(temp_raw)
        # 짝수인 경우 -1 (최소 1 유지)
        abs_raw = np.where((abs_raw % 2 == 0) & (abs_raw != 0), np.maximum(1, abs_raw - 1), abs_raw)
        # 0인 경우 1로 처리
        temp_raw = np.where(temp_raw == 0, 1, (signs * abs_raw)).astype(int)
        
        # 정수화된 값을 다시 AHP 스케일로 변환하여 행렬에 일괄 반영
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

    # ID와 인구통계(Type) 관련 컬럼을 제외한 나머지를 쌍대비교 컬럼으로 간주
    comp_cols = [c for c in df.columns if str(c).strip().lower() != 'id' and not str(c).strip().lower().startswith('type')]
    meta_cols = [c for c in df.columns if c not in comp_cols]
    factors, n = infer_factors_from_columns(comp_cols)
    
    # 시트 전체 데이터의 로우데이터 최대값/최솟값 계산
    all_comp_values = df[comp_cols].values.flatten()
    sheet_min = int(np.min(all_comp_values))
    sheet_max = int(np.max(all_comp_values))
    
    results_list = []
    excluded_list = []
    excluded_count = 0
    for idx, row in df.iterrows():
        meta_data = {c: row[c] for c in meta_cols}
        respondent_id = meta_data.get('ID', row.iloc[0]) if 'ID' in meta_data else row.iloc[0]
        matrix = np.eye(n)
        
        # 원본 Rawdata를 정수 형태(-9 ~ 9)로 추출
        raw_values = []
        col_idx = 0
        has_format_error = False
        for i in range(n):
            for j in range(i + 1, n):
                if col_idx < len(comp_cols):
                    raw_val = row[comp_cols[col_idx]]
                    raw_values.append(raw_val)
                    
                    if pd.isna(raw_val) or type(raw_val) == str or not (-9 <= float(raw_val) <= 9):
                        has_format_error = True
                    
                    if not has_format_error:
                        ahp_val = parse_input_value(float(raw_val))
                        matrix[i, j] = ahp_val
                        matrix[j, i] = 1.0 / ahp_val
                    col_idx += 1
                    
        if has_format_error:
            excluded_count += 1
            ex_res = meta_data.copy()
            for k, col_name in enumerate(comp_cols):
                ex_res[col_name] = raw_values[k] if k < len(raw_values) else np.nan
            ex_res["CR"] = "데이터 오류(Format Error)"
            excluded_list.append(ex_res)
            continue
            
        orig_cr, orig_ci, _unused_lambda = calculate_consistency(matrix, method)
        final_matrix = matrix.copy()
        final_cr = orig_cr
        iterations = 0
        corrected_flag = False
        if orig_cr > cr_threshold:
            final_matrix, final_cr, iterations, corrected_flag = improve_consistency(
                matrix, cr_threshold, sheet_min, sheet_max, max_iter=max_iter, learning_rate=learning_rate, method=method
            )
        
        # 만약 최대 반복을 수행했음에도 CR이 임계값을 초과할 경우 해당 응답자 제외
        if final_cr > cr_threshold:
            excluded_count += 1
            ex_res = meta_data.copy()
            for k, col_name in enumerate(comp_cols):
                ex_res[col_name] = raw_values[k]
            ex_res["CR"] = final_cr
            excluded_list.append(ex_res)
            continue

        # 보정 후 Rawdata (역변환: 상삼각 행렬 값을 정수 펀칭 스케일로 변환)
        final_raw_values = []
        for i in range(n):
            for j in range(i + 1, n):
                val = final_matrix[i, j]
                if val == 1.0: final_raw_val = 1
                elif val > 1.0: final_raw_val = -int(round(val)) # 왼쪽 우선 (음수)
                else: final_raw_val = int(round(1.0/val)) # 오른쪽 우선 (양수)
                final_raw_values.append(final_raw_val)

        _unused_cr, final_ci, _unused_lambda = calculate_consistency(final_matrix, method)
        if ahp_method == 'fuzzy':
            final_weights, final_Si = fuzzy_ahp_analysis(final_matrix)
        else:
            final_weights = calculate_weights(final_matrix, method)
        
        # 결과 딕셔너리 구성 (요청사항 5 재배치 반영)
        res = meta_data.copy()
        
        # [수정] 1. 보정 전 Rawdata 삽입
        for k, col_name in enumerate(comp_cols):
            res[f"Raw_Orig_{col_name}"] = raw_values[k]
        
        # [수정] 2. Original_CI, Original_CR 순서 배치
        res["Original_CI"] = orig_ci
        res["Original_CR"] = orig_cr
        
        # [수정] 3. 보정 후 Rawdata 삽입
        for k, col_name in enumerate(comp_cols):
            res[f"Raw_Final_{col_name}"] = final_raw_values[k]
            
        # [수정] 4. Final_CI, Final_CR 순서 배치
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
            main_list = ["기능성", "디자인", "경제성"]
            subs = {"기능성": ["하드웨어", "소프트웨어"], "디자인": ["외관", "편의성"], "경제성": ["단말기가격", "유지비용"]}
            sub_subs = {"하드웨어": ["카메라", "배터리", "프로세서"], "소프트웨어": ["운영체제", "기본앱"], "외관": ["색상", "재질"], "편의성": [], "단말기가격": ["일시불", "할부"], "유지비용": ["통신요금", "AS비용"]}
            
        def _get_dummy_data(cols, num_respondents=5):
            # cols contains ["ID", "Type", pair1, pair2...]
            data = []
            for i in range(num_respondents):
                row = [i+1, "전문가" if not is_en else "Expert"]
                for _ in range(len(cols)-2):
                    row.append(int(np.random.choice([1, 3, 5, -3, -5])))
                data.append(row)
            return data
            
        main_pairs = list(itertools.combinations(main_list, 2))
        main_cols = ["ID", "Type"] + [f"{a}_{b}" for a, b in main_pairs]
        df_main = pd.DataFrame(_get_dummy_data(main_cols), columns=main_cols)
        df_main.to_excel(writer, sheet_name="Main_Criteria", index=False)
        
        for i, mc in enumerate(main_list):
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
            main_cols = ["ID", "Type", "거버넌스_계획타당성", "거버넌스_실현가능성", "거버넌스_사업효과", 
                          "계획타당성_실현가능성", "계획타당성_사업효과", "실현가능성_사업효과"]
            main_data = [
                [1, "전문가",-3,	-3, 3, 1, 1, 1],                
                [2, "전문가", -5, 3, 3, 3, 3, 3],        
                [3, "일반", 5, 1, 3, -5, -5, -3],
                [4, "일반", -3,-3, 3, -3, 3, -3],
                [5, "공무원", -5, 5, -5, -5, 5, -5]
            ]
            df_main = pd.DataFrame(main_data, columns=main_cols)
            df_main.to_excel(writer, sheet_name="Main_Criteria", index=False)
            
            inconsistent_pattern = [
                [1, "전문가", 1, -3, 1],
                [2, "전문가", -3, -3, -3],
                [3, "일반", 3, -3, 1],
                [4, "일반", -3, 5, 3],
                [5, "공무원", -3, 5, 3]
            ]
            sub1_cols = ["ID", "Type", "행정지원_지역공동체", "행정지원_총괄사업관리자", "지역공동체_총괄사업관리자"]
            pd.DataFrame(inconsistent_pattern, columns=sub1_cols).to_excel(writer, sheet_name="거버넌스", index=False)
            sub2_cols = ["ID", "Type", "현안적정성_대안적정성", "현안적정성_목표구체성", "대안적정성_목표구체성"]
            pd.DataFrame(inconsistent_pattern, columns=sub2_cols).to_excel(writer, sheet_name="계획타당성", index=False)
            sub3_cols = ["ID", "Type", "부지확보_사업구체화", "부지확보_사업비적정성", "사업구체화_사업비적정성"]
            pd.DataFrame(inconsistent_pattern, columns=sub3_cols).to_excel(writer, sheet_name="실현가능성", index=False)
            sub4_cols = ["ID", "Type", "경제적효과_사회적효과", "경제적효과_성과관리", "사회적효과_성과관리"]
            pd.DataFrame(inconsistent_pattern, columns=sub4_cols).to_excel(writer, sheet_name="사업효과", index=False)
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
            "요인": factor,
            "F-값": f_stat,
            "P-Value": p_val,
            "유의성": "유의함" if p_val < 0.05 else "유의하지 않음",
            "사후검정(Tukey HSD)": ""
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
                    row["사후검정(Tukey HSD)"] = ", ".join(pairs_str) + " 차이 있음"
                else:
                    row["사후검정(Tukey HSD)"] = "집단 간 구체적 차이 발견 못함"
            except Exception as e:
                row["사후검정(Tukey HSD)"] = "계산 오류"
        
        results.append(row)
        
    return pd.DataFrame(results)

# -----------------------------------------------------------------------------
# [삭제] 좋아요 기능 제거됨
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# 2. Setup & Layout
# -----------------------------------------------------------------------------

if not st.session_state.get('_db_initialized'):
    init_db()
    st.session_state._db_initialized = True

# CSS 최적화


if 'user_id' not in st.session_state: st.session_state.user_id = None
if 'user_role' not in st.session_state: st.session_state.user_role = None
if 'expiry_date' not in st.session_state: st.session_state.expiry_date = None
if 'admin_mode' not in st.session_state: st.session_state.admin_mode = False
if 'model_structure' not in st.session_state: st.session_state.model_structure = {}
if 'page' not in st.session_state: st.session_state.page = "main"
if 'signup_paypal_user' not in st.session_state: st.session_state.signup_paypal_user = None
if 'signup_portone_user' not in st.session_state: st.session_state.signup_portone_user = None

# 로그인 상태일 경우 가입 결제 대기 상태 초기화
if st.session_state.user_id is not None:
    st.session_state.signup_paypal_user = None
    st.session_state.signup_portone_user = None

# Check for foreign access once per session
check_foreign_access()

# -----------------------------------------------------------------------------
# 쿼리 매개변수 확인 (다국어 선택 및 결제 완료 처리)
# -----------------------------------------------------------------------------
try:
    q_params = st.query_params
except AttributeError:
    try:
        q_params = st.experimental_get_query_params()
    except:
        q_params = {}

# -----------------------------------------------------------------------------
# 구글 OAuth 2.0 콜백 처리
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
            
            st.success("🎉 구글 계정 연동이 완료되었습니다!")
            st.query_params.clear()
            st.rerun()
        except Exception as oauth_err:
            st.error(f"구글 계정 연동 실패: {oauth_err}")
            st.query_params.clear()


# -----------------------------------------------------------------------------
# [신규] 동적 라우팅 - 응답자 설문 참여 SPA (Single Page Application)
# -----------------------------------------------------------------------------


if "preview_id" in q_params or "survey_id" in q_params:
    is_preview_mode = "preview_id" in q_params
    
    from survey_manager import load_survey_metadata, save_response_to_sheet, generate_pairwise_combinations, calculate_matrix_cr
    
    if is_preview_mode:
        preview_id_param = q_params["preview_id"]
        if isinstance(preview_id_param, list):
            preview_id_param = preview_id_param[0]
            
        st.info("⚠️ [미리보기 모드] 이 화면은 응답자가 보게 될 화면의 실시간 미리보기입니다. 입력된 데이터는 제출되지 않습니다.")
        
        preview_file_path = f"temp_previews/{preview_id_param}.json"
        if os.path.exists(preview_file_path):
            with open(preview_file_path, "r", encoding="utf-8") as f:
                survey_meta = json.load(f)
        else:
            st.warning(_("미리보기 데이터를 불러올 수 없습니다.", "Failed to load preview data."))
            st.markdown(_("""
#### 📋 미리보기 전에 아래 사항을 먼저 완료해 주세요.

1. **설문지 설정 완료** — 메인 페이지에서 AHP 모델 구조, 요인, 척도 등 설문 설정을 모두 입력합니다.
2. **구글 스프레드시트 연동** — 섹션 7에서 본인의 구글 스프레드시트 URL 또는 ID를 입력하고, 서비스 계정 이메일을 편집자로 공유합니다.
3. **미리보기 버튼 클릭** — 설정이 완료된 후 "👁️ 설문지 응답 화면 미리보기" 버튼을 다시 눌러 주세요.

> 💡 설문 설정 페이지에서 내용을 입력한 뒤 미리보기를 눌러야 정상적으로 표시됩니다.
            """, """
#### 📋 Please complete the following steps before previewing.

1. **Complete Survey Settings** — Enter all survey settings, including AHP model structure, factors, and scales on the main page.
2. **Google Spreadsheet Integration** — In Section 7, enter your Google Spreadsheet URL or ID and share it with the service account email as an editor.
3. **Click Preview Button** — After the setup is complete, click the "👁️ Preview Survey Screen" button again.

> 💡 The preview will display correctly only after entering content on the survey settings page.
            """))
            st.stop()
            
        survey_id_param = f"preview_{preview_id_param}"
    else:
        survey_id_param = q_params["survey_id"]
        if isinstance(survey_id_param, list):
            survey_id_param = survey_id_param[0]

    submitted_key = f"survey_submitted_{survey_id_param}"
    if st.session_state.get(submitted_key):
        # 1. HTML/CSS를 이용한 모던하고 수려한 감사 카드 UI 렌더링
        thank_you_title = _("설문 제출이 성공적으로 완료되었습니다!", "Survey Submitted Successfully!")
        thank_you_body = _(
            "의사결정 우선순위 분석을 위해 소중한 시간 내어 응답해 주셔서 대단히 감사합니다. <br>보내주신 답변은 안전하게 기록되었으며 연구 분석에 귀중한 자료로 활용됩니다.",
            "Thank you very much for taking your valuable time to respond for decision-making priority analysis. <br>Your responses have been safely recorded and will be used as valuable data for research analysis."
        )
        thank_you_note = _(
            "※ 브라우저 보안 규정에 따라 '창 닫기' 버튼이 동작하지 않을 수 있습니다. <br>동작하지 않을 경우 현재 열려있는 <strong>브라우저 탭의 X 버튼</strong>을 직접 눌러 종료해 주세요.",
            "※ Depending on browser security policies, the 'Close Window' button may not work. <br>If it does not work, please close the current <strong>browser tab</strong> manually."
        )
        st.markdown(f"""
        <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 60px 20px; text-align: center; font-family: 'Inter', sans-serif; background-color: #ffffff; border-radius: 12px; box-shadow: 0 4px 24px rgba(0,0,0,0.06); margin-top: 40px; border: 1px solid #e2e8f0;">
            <div style="background-color: #ecfdf5; border: 1px solid #a7f3d0; border-radius: 50%; width: 90px; height: 90px; display: flex; align-items: center; justify-content: center; margin-bottom: 24px; box-shadow: 0 4px 10px rgba(16, 185, 129, 0.1);">
                <span style="font-size: 45px; color: #10b981;">🎉</span>
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
        
        # 2. 창 닫기 버튼 렌더링 및 자바스크립트 실행 트리거
        import streamlit.components.v1 as components
        close_clicked = st.button(_("🚪 창 닫기", "🚪 Close Window"), use_container_width=True)
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
            
    st.info(_("⚠️ 페이지를 새로고침하거나 이탈 시 입력된 정보가 모두 초기화되니 주의 바랍니다.", "⚠️ Please note that all entered information will be initialized if you refresh or leave the page."))
    
    # 미리보기 모드가 아닌 경우에만 구글 시트에서 메타데이터를 로드
    if not is_preview_mode:
        survey_meta = load_survey_metadata(survey_id_param)
        if not survey_meta:
            st.error(_("설문지를 불러올 수 없습니다. 올바른 링크인지 확인해 주세요.", "Failed to load the survey. Please check if the link is correct."))
            st.stop()
        
        # 세션 상태 기반 1회성 방문 카운트 증가 처리 (새로고침 방지용 세션변수 활용)
        if f"visited_survey_{survey_id_param}" not in st.session_state:
            from survey_manager import increment_survey_visit
            increment_survey_visit(survey_id_param)
            st.session_state[f"visited_survey_{survey_id_param}"] = True
        
    survey_title = survey_meta.get('Title', 'AHP 온라인 설문조사')
    if survey_title in ['AHP 온라인 설문조사', '제조용 협동로봇 도입 요인 중요도 분석을 위한 전문가 AHP 설문']:
        survey_title = _(survey_title, 'Expert AHP Survey on the Importance of Factors for Adopting Manufacturing Collaborative Robots')
        
    # --- Survey Language Switcher ---
    lang_col1, lang_col2 = st.columns([8, 2])
    with lang_col1:
        st.title(survey_title)
    with lang_col2:
        st.write("") # Add some vertical padding
        lang_options = {"한국어 (Korean)": "ko", "English (영어)": "en"}
        current_survey_lang = "en" if st.session_state.get('lang', 'ko') == 'en' else "ko"
        selected_lang_label = st.selectbox(
            "Language / 언어", 
            options=list(lang_options.keys()), 
            index=0 if current_survey_lang == 'ko' else 1,
            key=f"survey_lang_selector_{survey_id_param}",
            label_visibility="collapsed"
        )
        new_lang = lang_options[selected_lang_label]
        if new_lang != current_survey_lang:
            st.session_state.lang = new_lang
            st.rerun()
    # --------------------------------
    
    # 조사 목적 및 안내문, 설문 담당자 이메일 표시 (깔끔한 디자인 적용)
    survey_desc = survey_meta.get("Description", "")
    survey_desc = translate_definition_if_default("Description", survey_desc)
    
    # 마침표(.)를 기준으로 강제 줄내림 적용하여 긴 문장 가독성 향상 (사용자 입력 레이아웃 유지를 위해 비활성화)
    # if survey_desc:
    #     survey_desc = survey_desc.replace(". ", ".\n\n")
    
    survey_email = survey_meta.get("Admin_Email", "temp@ahpmaster.com")
    if not survey_email or str(survey_email).strip() == "":
        survey_email = "temp@ahpmaster.com"
    
    if survey_desc or survey_email:
        email_html = (
            f"<div style='margin-top: 16px; padding-top: 16px; border-top: 1px solid #e2e8f0; font-weight: bold;'>"
            f"📧 " + _("설문 담당자 문의:", "Contact Survey Administrator:") + " "
            f"<a href='mailto:{survey_email}' style='color: #2563eb; text-decoration: none;'>{survey_email}</a>"
            f"</div>"
        ) if survey_email else ""
        
        # 사용자 입력 레이아웃(줄바꿈 및 띄어쓰기)을 그대로 유지하기 위해 white-space: pre-wrap 적용
        box_html = f"""
        <div style="border: 1px solid #cbd5e1; border-radius: 8px; padding: 24px; background-color: #ffffff; color: #1e293b; font-size: 0.95rem; line-height: 1.6; margin-bottom: 24px; white-space: pre-wrap;">{survey_desc}
            {email_html}
        </div>
        """
        st.markdown(box_html, unsafe_allow_html=True)

    
    # 모델 정보와 인구통계 추출
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
    
    # AHP 쌍대비교 기본 선택값을 1(동등)로 설정하기 위해 session_state 사전 초기화 (버전 v3 적용으로 세션 캐시 갱신)
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
    
    # 단일 스크롤 폼 생성
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

    # 1. 응답자 기본 정보
    st.subheader(f"{section_num}. " + _("응답자 기본 정보", "Respondent Demographic Information"))
    section_num += 1
    resp_data = {}
    
    # 아이디는 응답자에게 제시하지 말고 임의로 무작위 자동 부여
    if "survey_resp_uuid" not in st.session_state:
        import uuid
        st.session_state.survey_resp_uuid = str(uuid.uuid4())[:8]
    resp_data["id"] = st.session_state.survey_resp_uuid
    
    sq_idx = 1
    
    # 성명
    if demographics.get("name"):
        name_label = f"SQ{sq_idx}. " + _("성명 *", "Name *")
        sq_idx += 1
        col1, col2 = st.columns([1, 3])
        with col1:
            resp_data["name"] = st.text_input(name_label, key="survey_resp_name")
        st.caption(_("💡 수집된 성명은 중복 응답 검토 용도로만 사용됩니다. 성명 전체 입력을 원치 않으실 경우, 이름의 일부만 입력하셔도 무방합니다. (예: 홍@동, 홍길@ 등)", "💡 The collected name is used only for duplicate response checking. If you do not wish to provide your full name, you may enter a partial name. (e.g., J@hn, Joh@ Doe)"))
    
    # 그룹 분류는 설계자가 설정한 문항과 보기를 적용
    type_questions_data = demographics.get("type_questions")
    resp_data["types"] = []
    
    if type_questions_data and isinstance(type_questions_data, list):
        for i, tq in enumerate(type_questions_data):
            tq_q = tq.get("q", tq.get("question", ""))
            tq_opts = tq.get("opts", [])
            if not tq_q or tq_q == "귀하의 소속은 어떻게 되십니까?":
                tq_q = _("귀하의 소속은 어떻게 되십니까?", "What is your affiliation?")
            
            if not isinstance(tq_opts, list) or not tq_opts or tq_opts == ["전문가", "일반", "공무원", "기타"]:
                if "opts" not in tq: # it was added via UI as short answer text
                    tq_opts = []
                else:
                    tq_opts = [_("전문가", "Expert"), _("일반", "General"), _("공무원", "Public Official"), _("기타", "Other")]
            
            if tq_opts:
                tq_opts = [translate_factor_if_default(opt) for opt in tq_opts]
                ans = st.radio(f"SQ{sq_idx}. {tq_q}", tq_opts, index=0, key=f"survey_resp_type_{i}", horizontal=True)
            else:
                ans = st.text_input(f"SQ{sq_idx}. {tq_q}", key=f"survey_resp_type_{i}")
            resp_data["types"].append(ans)
            sq_idx += 1
    else:
        # 역방향 호환성
        type_q = demographics.get("type_question", "")
        if not type_q or type_q == "귀하의 소속은 어떻게 되십니까?":
            type_q = _("귀하의 소속은 어떻게 되십니까?", "What is your affiliation?")
        
        type_opts = demographics.get("type_options", [])
        if not isinstance(type_opts, list) or not type_opts or type_opts == ["전문가", "일반", "공무원", "기타"]:
            type_opts = [_("전문가", "Expert"), _("일반", "General"), _("공무원", "Public Official"), _("기타", "Other")]
        else:
            type_opts = [translate_factor_if_default(opt) for opt in type_opts]
            
        ans = st.radio(f"SQ{sq_idx}. {type_q}", type_opts, index=0, key="survey_resp_type", horizontal=True)
        resp_data["types"].append(ans)
        sq_idx += 1
        
    # 기존 코드와의 호환성을 위해 type 속성도 유지
    if resp_data["types"]:
        resp_data["type"] = resp_data["types"][0]
    

    
    # 연령: 개방형 vs 10세 단위 선택형
    if demographics.get("age"):
        age_label = f"SQ{sq_idx}. " + _("연령 *", "Age *")
        sq_idx += 1
        age_type = demographics.get("age_type", "개방형 (숫자 직접 입력)")
        if age_type == "10세 단위 선택형":
            age_options = [_("20대 미만", "Under 20s"), _("20대 (20~29세)", "20s (20-29)"), _("30대 (30~39세)", "30s (30-39)"), _("40대 (40~49세)", "40s (40-49)"), _("50대 (50~59세)", "50s (50-59)"), _("60대 이상", "60s or older")]
            resp_data["age"] = st.radio(age_label, age_options, index=0, key="survey_resp_age", horizontal=True)
        else:
            col1, col2 = st.columns([1, 3])
            with col1:
                resp_data["age"] = st.text_input(f"{age_label} " + _("(세)", "(Years)"), value="", placeholder=_("예: 30", "e.g. 30"), key="survey_resp_age_text")
            
    if demographics.get("gender"):
        resp_data["gender"] = st.radio(f"SQ{sq_idx}. " + _("성별 *", "Gender *"), [_("남자", "Male"), _("여자", "Female")], key="survey_resp_gender", horizontal=True)
        sq_idx += 1
    
    # 경력년수: 개방형 vs 5년 단위 선택형
    if demographics.get("experience"):
        exp_label = f"SQ{sq_idx}. " + _("경력년수 *", "Years of Experience *")
        sq_idx += 1
        exp_type = demographics.get("experience_type", "개방형 (숫자 직접 입력)")
        if exp_type == "5년 단위 선택형":
            exp_options = [_("5년 미만", "Less than 5 years"), _("5년 이상 ~ 10년 미만", "5 to 10 years"), _("10년 이상 ~ 15년 미만", "10 to 15 years"), _("15년 이상 ~ 20년 미만", "15 to 20 years"), _("20년 이상", "20 years or more")]
            resp_data["experience"] = st.radio(exp_label, exp_options, index=0, key="survey_resp_experience", horizontal=True)
        else:
            col1, col2 = st.columns([1, 3])
            with col1:
                resp_data["experience"] = st.text_input(f"{exp_label} " + _("(년)", "(Years)"), value="", placeholder=_("예: 5", "e.g. 5"), key="survey_resp_experience_text")
            
    # 소속 문항 삭제됨
    # if demographics.get("affiliation"):
    #     resp_data["affiliation"] = st.text_input(f"SQ{sq_idx}. " + _("소속 *", "Affiliation *"), key="survey_resp_affiliation")
    #     sq_idx += 1
        
    if demographics.get("email"):
        col1, col2 = st.columns([1, 3])
        with col1:
            resp_data["email"] = st.text_input(f"SQ{sq_idx}. " + _("이메일 *", "Email *"), key="survey_resp_email", value="", placeholder=_("예: user@example.com", "e.g. user@example.com"))
        sq_idx += 1
    
    st.divider()
    
    main_criteria = ahp_model.get("main", [])
    
    with st.container():
        # 4. AHP 쌍대비교 문항 생성
        st.subheader(f"{section_num}. " + _("요인 간 상대적 중요도 평가 (쌍대비교)", "Evaluation of Relative Importance between Factors (Pairwise Comparison)"))
        ahp_section_prefix = f"{section_num}"
        section_num += 1
        
        st.info(_("""
        **응답 방법**: 왼쪽 요인과 오른쪽 요인 중 **더 중요하다고 생각하는 방향**으로 숫자를 선택해 주세요. 숫자가 클수록 해당 요인이 더 중요함을 의미합니다.

        - **동등(1)**: 양쪽 요인이 똑같이 중요할 때 가운데 **1**을 선택하세요.
        - **왼쪽 요인이 더 중요할 때**: 왼쪽 방향(← )의 숫자를 선택하세요. 숫자가 클수록 왼쪽 요인이 훨씬 중요함을 나타냅니다.
        - **오른쪽 요인이 더 중요할 때**: 오른쪽 방향( →)의 숫자를 선택하세요. 숫자가 클수록 오른쪽 요인이 훨씬 중요함을 나타냅니다.
        """ + ("""\n        💡 :blue[**파란색 배경 가이드: 앞선 응답들과의 논리적 일관성(CR)을 최적으로 유지할 수 있는**] :red[**권장 선택 구간**]:blue[**입니다.**]""" if cr_guide_method == "realtime" else ""), """
        **Response Method**: Please select the number in the direction of **the factor you think is more important** between the left factor and the right factor. A larger number means that factor is more important.

        - **Equal (1)**: Choose the middle **1** when both factors are equally important.
        - **When the left factor is more important**: Choose a number on the left side (←). A larger number indicates the left factor is much more important.
        - **When the right factor is more important**: Choose a number on the right side (→). A larger number indicates the right factor is much more important.
        """ + ("""\n        💡 :blue[**Blue Background Guide: Indicates the**] :red[**recommended selection range**] :blue[**to optimally maintain logical consistency (CR) with your previous answers.**]""" if cr_guide_method == "realtime" else "")))
        
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
                    _((f"[{parent_trans}] 하위 요인 비교"), f"Sub-criteria Comparison under [{parent_trans}]")
                    if comb['type'] == 'sub'
                    else _("대분류(핵심) 요인 비교", "Main Criteria (Core) Comparison")
                )
                st.markdown(f"#### {parent_lbl}")
                
                # [수정] 평가 요인 정의 및 설명을 각 척도 평가 바로 위쪽으로 이동
                if comb['type'] == 'sub':
                    # 해당 대분류(parent) 카드 출력
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
                    main_rows_html = ""
                    if definitions:
                        for i, mc in enumerate(ahp_model.get("main", [])):
                            text_color = "#334155"
                            border = "#cbd5e1"
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
                        <div style="background-color: #f8fafc; border: 1px solid #e2e8f0; padding: 16px; border-radius: 8px; margin-top: 0px; margin-bottom: 15px;">
                            <h5 style="margin: 0 0 12px 0; color: #1e293b; font-size: 1.0rem; font-weight: bold;">{_("대분류 요인 정의", "Main Criteria Definitions")}</h5>
                            <div style="display: flex; flex-direction: column; gap: 2px; background-color: #ffffff; padding: 12px; border-radius: 6px; border: 1px solid #e2e8f0;">
                                {main_rows_html}
                            </div>
                        </div>
                        """
                        st.markdown(card_html.replace("\n", " "), unsafe_allow_html=True)
                
                comp_idx += 1
            
                # 척도 인터페이스 설정에 따른 선택 라디오 버튼 옵션 매핑
                if scale_type == "1-3-5 Discrete":
                    options = [-5, -3, 1, 3, 5]
                    format_func = lambda x: _("왼쪽 요인이 훨씬 중요 (-5)", "Left factor is much more important (-5)") if x == -5 else (_("왼쪽 요인이 약간 중요 (-3)", "Left factor is slightly more important (-3)") if x == -3 else (_("양측이 동등함 (1)", "Equal importance (1)") if x == 1 else (_("오른쪽 요인이 약간 중요 (3)", "Right factor is slightly more important (3)") if x == 3 else _("오른쪽 요인이 훨씬 중요 (5)", "Right factor is much more important (5)"))))
                elif scale_type == "1-3-7-9 Discrete":
                    options = [-9, -7, -3, 1, 3, 7, 9]
                    format_func = lambda x: _("왼쪽 절대적 중요 (-9)", "Left is absolutely more important (-9)") if x == -9 else (_("왼쪽 대단히 중요 (-7)", "Left is strongly more important (-7)") if x == -7 else (_("왼쪽 약간 중요 (-3)", "Left is slightly more important (-3)") if x == -3 else (_("동등함 (1)", "Equal (1)") if x == 1 else (_("오른쪽 약간 중요 (3)", "Right is slightly more important (3)") if x == 3 else (_("오른쪽 대단히 중요 (7)", "Right is strongly more important (7)") if x == 7 else _("오른쪽 절대적 중요 (9)", "Right is absolutely more important (9)"))))))
                else: # 1-9 Continuous (Default)
                    options = list(range(-9, -1)) + list(range(1, 10))
                    options = sorted(list(set(options))) # -9 ~ -2, 1, 2 ~ 9
                    format_func = lambda x: _(f"왼쪽 중요도 {abs(x)}", f"Left importance {abs(x)}") if x < 0 else (_("동등 (1)", "Equal (1)") if x == 1 else _(f"오른쪽 중요도 {x}", f"Right importance {x}"))
                
                # PDF 설문지와 유사한 헤더 스타일 표 생성
                # 척도 옵션에 맞추어 표 상단에 표시될 헤더 및 척도 값 구성
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
            
                # 척도 수에 맞추어 비율 동적 계산 (left_cols + 동일(1) + right_cols)
                header_cells = left_cols + ["1"] + right_cols
                total_scale_count = len(header_cells)
                scale_width = 70.0 / total_scale_count
                left_width = scale_width * len(left_cols)
                right_width = scale_width * len(right_cols)

                # CSS 주입: 컬럼 간의 gap을 0으로 차단하고 라디오 그룹을 100% 분배
            

                # HTML 표 헤더 구조
                # fixed table layout에서 colspan 사용 시 각 컬럼 너비를 동일 배분하도록 colgroup 정의
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
                        <th style="border: 1px solid #334155; padding: 6px; font-size: 12px;" rowspan="2">{_("비교 요인", "Comparison Criteria")}</th>
                        <th style="border: 1px solid #334155; padding: 4px; color: #93c5fd; font-size: 12px;" colspan="{len(left_cols)}">{_("← 좌측 요인 중요도", "← Left Criteria Importance")}</th>
                        <th style="border: 1px solid #334155; padding: 4px; background-color: #3b82f6; color: #ffffff; font-size: 12px;" rowspan="2">{_("동등<br>(1)", "Equal<br>(1)")}</th>
                        <th style="border: 1px solid #334155; padding: 4px; color: #93c5fd; font-size: 12px;" colspan="{len(right_cols)}">{_("우측 요인 중요도 →", "Right Criteria Importance →")}</th>
                        <th style="border: 1px solid #334155; padding: 6px; font-size: 12px;" rowspan="2">{_("비교 요인", "Comparison Criteria")}</th>
                    </tr>
                    <tr style="background-color: #334155; color: #cbd5e1; font-weight: bold; border-bottom: 1px solid #cbd5e1;">
                        {"".join([f"<td style='border: 1px solid #475569; padding: 4px 0; font-size: 12px;'>{val}</td>" for val in left_cols])}
                        {"".join([f"<td style='border: 1px solid #475569; padding: 4px 0; font-size: 12px;'>{val}</td>" for val in right_cols])}
                    </tr>
                </table>
                """
                st.markdown(header_html, unsafe_allow_html=True)

                # 3단 컬럼 배치: [왼쪽 요인명 컬럼 (15%)] - [척도 라디오 버튼 영역 컬럼 (70%)] - [오른쪽 요인명 컬럼 (15%)]
                for left_f, right_f in comb["pairs"]:
                    pair_key = f"{left_f}_{right_f}"
                    clean_id = pair_key.replace(" ", "_")
                    st.markdown(f"<div id='anchor_{clean_id}'></div>", unsafe_allow_html=True)
                
                    row_cols = st.columns([15, 70, 15])
                
                    # 왼쪽 요인명 출력
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
                
                    # 라디오 버튼들을 가로로 완전 정렬하여 1열로 배치
                    with row_cols[1]:
                        # 안전을 위해 options에서 중복 및 -1 값 명시적 제외
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
                                
                                # 비교 요인이 2개 초과이고, 그룹 내의 다른 문항들이 모두 응답된 경우에만 권장 범위를 산출합니다.
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
                            # Streamlit st.radio 라벨 중복(튕김 현상) 방지를 위해 음수 쪽에 보이지 않는 공백(Zero-width space) 추가
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
                
                    # 오른쪽 요인명 출력
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
            
        if demographics.get("name"):
            st.subheader(_("응답자 성명 확인", "Respondent Name Verification"))
            col1, col2 = st.columns([1, 3])
            with col1:
                resp_data["name"] = st.text_input(_("성명 *", "Name *"), key="survey_resp_name", value="", placeholder=_("예: 홍길동 (또는 홍*동)", "e.g. John Doe (or J. Doe)"))
                st.caption(_("중복 응답 확인을 위해 입력을 요청드립니다. 전체 이름 공개가 불편하신 경우 성씨 또는 성씨와 이름 끝자만 입력하셔도 됩니다.", "Requested to check for duplicate responses. If uncomfortable disclosing your full name, you may enter just your last name or initials."))
            st.divider()

        # 5. 개인정보 수집 및 답례품 동적 노출 및 문구 설정
        has_demographics = any(demographics.values()) if demographics else False
        has_rewards = rewards_info.get("enabled", False) if rewards_info else False
        
        agree_check = _("동의", "Agree")
        if has_demographics or has_rewards:
            if has_rewards:
                subheader_text = f"{section_num}. " + _("개인정보 수집 및 답례품", "Personal Information Collection & Reward")
                radio_label = _("개인정보 수집 및 답례품 지급을 위한 이용 동의에 동의하십니까? *", "Do you agree to the collection of personal information and use for reward distribution? *")
            else:
                subheader_text = f"{section_num}. " + _("개인정보 수집 동의", "Consent to Personal Information Collection")
                radio_label = _("개인정보 수집 및 이용에 동의하십니까? *", "Do you agree to the collection and use of personal information? *")
                
            st.subheader(subheader_text)
            section_num += 1
            
            if has_rewards:
                st.info(f"**" + _("답례품 안내", "Reward Info") + f"**: {rewards_info.get('desc', _('설문 완료 시 답례품을 제공합니다.', 'A reward will be provided upon survey completion.'))}")
                reward_contact = st.text_input(_("답례품 지급용 연락처(휴대폰 번호 또는 이메일) *", "Contact for Reward (Mobile number or Email) *"), key="survey_reward_contact")
                resp_data["reward_contact"] = reward_contact
                
            agree_check = st.radio(radio_label, [_("동의", "Agree"), _("비동의", "Disagree")], index=1, key="survey_agree_check")
        
        # 마법사 상태 확인
        wizard_state_key = f"cr_wizard_state_{survey_id_param}"
        wizard_state = st.session_state.get(wizard_state_key, {"active": False})
        
        if wizard_state.get("active"):
            st.warning(_("⚠️ 제출 전 일관성 비율(CR) 점검", "⚠️ Pre-submission Consistency Ratio (CR) Check"))
            st.error(_(f"분석 결과, **[{wizard_state['failed_group']}]** 문항들의 응답 일관성이 부족합니다. (현재 CR: {wizard_state['cr']:.3f} > 기준치: {cr_limit})", f"Analysis shows inconsistent responses for **[{wizard_state['failed_group']}]**. (Current CR: {wizard_state['cr']:.3f} > Limit: {cr_limit})"))
            
            w_pair = wizard_state['worst_pair']
            cur_v = wizard_state['current_val']
            sug_v = wizard_state['suggested_val']
            
            def val_to_text(v, p1, p2):
                if v == 1: return _("동등함 (1)", "Equal (1)")
                if v < 0: return f"{p1} 방향으로 {abs(v)}"
                return f"{p2} 방향으로 {v}"
                
            cur_txt = val_to_text(cur_v, w_pair[0], w_pair[1])
            sug_txt = val_to_text(sug_v, w_pair[0], w_pair[1])
            
            st.info(_(f"""
            💡 **지능형 수정 제안**: 
            현재 [{w_pair[0]}]와 [{w_pair[1]}]의 비교 응답이 다른 응답들과 수학적 모순이 가장 큽니다.
            * 현재 선택하신 값: **{cur_txt}**
            * 논리적 일관성을 위한 추천 값: **{sug_txt}**
            """, f"""
            💡 **Smart Fix Suggestion**: 
            Your comparison between [{w_pair[0]}] and [{w_pair[1]}] has the highest mathematical contradiction with your other answers.
            * Your current selection: **{cur_txt}**
            * Suggested value for logical consistency: **{sug_txt}**
            """))
            
            if st.button(_("다시 검토", "Review again"), use_container_width=True):
                st.session_state[wizard_state_key]["active"] = False
                target_key = f"{w_pair[0]}_{w_pair[1]}"
                st.session_state["scroll_target"] = target_key
                st.session_state["highlight_target"] = target_key
                st.rerun()
                    
            submit_btn = False # 마법사 표시 중에는 일반 제출 안함
        else:
            # 제출 버튼
            submit_btn = st.button(_("설문지 제출하기", "Submit Survey"), type="primary")
        if submit_btn:
            # 필수값 유효성 검증
            missing = False
            
            # AHP 응답 누락 검증
            missing_ahp = [k for k, v in ahp_answers.items() if v is None]
            
            # 인구통계 필수값
            if demographics.get("name") and not resp_data.get("name"): missing = True
            if demographics.get("age") and resp_data.get("age") is None: missing = True
            if demographics.get("experience") and resp_data.get("experience") is None: missing = True
            if demographics.get("email") and not resp_data.get("email"): missing = True
            if rewards_info.get("enabled") and not resp_data.get("reward_contact"): missing = True
            
            if agree_check not in ["동의", "Agree"]:
                st.error(_("설문제출을 위해 개인정보 수집 동의에 체크해 주세요.", "Please agree to the personal information collection to submit the survey."))
                st.stop()
                
            if missing_ahp:
                st.error(_("답변하지 않은 AHP 쌍대비교 문항이 있습니다. 모든 문항에 응답해 주십시오.", "There are unanswered AHP pairwise comparison questions. Please answer all questions."))
                st.stop()

            if missing:
                st.error(_("입력되지 않은 필수 문항(*)이 있습니다. 폼을 다시 한 번 확인해 주세요.", "There are missing required fields (*). Please check the form again."))
                st.stop()
                
            # CR 계산 및 마법사 로직
            if cr_limit is not None:
                cr_failed = False
                failed_factors = []
                failed_group_name = ""
                failed_cr = 0.0
                
                # 대분류 CR 체크
                main_cr = calculate_matrix_cr(main_criteria, ahp_answers)
                if main_cr > cr_limit:
                    cr_failed = True
                    failed_factors = main_criteria
                    failed_group_name = _("대분류", "Main Criteria")
                    failed_cr = main_cr
                
                # 하위분류 CR 체크
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
                    
                    # 마법사가 없거나 마법사 제안을 계산할 수 없는 경우 (기존 로직)
                    if not is_preview_mode:
                        from survey_manager import increment_abandoned_cr
                        increment_abandoned_cr(survey_id_param)
                    st.error(_(f"[{failed_group_name}] 항목의 응답 일관성이 부족합니다. (일관성 비율: {failed_cr:.3f} > 설정 임계값: {cr_limit}) 일부 문항을 다시 검토해 주십시오.", f"The consistency of your responses for [{failed_group_name}] is insufficient. (CR: {failed_cr:.3f} > threshold: {cr_limit}) Please review some questions again."))
                    st.stop()
            
            # 저장 진행
            with st.spinner(_("응답을 안전하게 전송 중입니다...", "Submitting your response safely...")):
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
                        st.error(_("데이터 저장 중 서버 에러가 발생했습니다. 잠시 후 다시 시도해 주세요.", "A server error occurred while saving data. Please try again later."))
                    
    st.stop()

# 자동 로그인 및 권한 갱신 처리 (쿼리 파라미터 기반)
if "login_user" in q_params and "login_token" in q_params:
    login_user_val = q_params["login_user"]
    if isinstance(login_user_val, list): login_user_val = login_user_val[0]
    login_token_val = q_params["login_token"]
    if isinstance(login_token_val, list): login_token_val = login_token_val[0]
    
    # 토큰 검증
    expected_token = hashlib.sha256(f"{login_user_val}:AHP_MASTER_SECURE_SALT_2026_!@#".encode()).hexdigest()
    if login_token_val == expected_token:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("SELECT role, expiry_date FROM users WHERE id=?", (login_user_val,))
        db_user = c.fetchone()
        conn.close()
        if db_user:
            role_changed = (st.session_state.user_id != login_user_val) or (st.session_state.user_role != db_user[0])
            st.session_state.user_id = login_user_val
            st.session_state.user_role = db_user[0]
            st.session_state.expiry_date = db_user[1]
            
            # URL 파라미터를 정리하여 불필요한 반복 쿼리 및 노출 방지
            st.query_params.pop("login_user", None)
            st.query_params.pop("login_token", None)
            
            if role_changed:
                st.toast("🎉 Account status updated!")
                st.rerun()


# 자동 로그아웃 처리 (30분 미활동 시)
import time
TIMEOUT_LIMIT = 1800 # 30분 (초 단위)
current_time = int(time.time())

if st.session_state.user_id is not None:
    last_act = q_params.get("last_activity")
    if isinstance(last_act, list): last_act = last_act[0]
    
    if last_act:
        try:
            elapsed = current_time - int(last_act)
            if elapsed > TIMEOUT_LIMIT:
                # 세션 및 쿼리 파라미터 초기화
                st.session_state.user_id = None
                st.session_state.user_role = None
                st.session_state.expiry_date = None
                st.session_state.admin_mode = False
                st.query_params.clear()
                st.toast(_(" 30분간 활동이 없어 보안을 위해 자동 로그아웃되었습니다.", " Logged out automatically due to 30 minutes of inactivity."))
                st.rerun()
            else:
                st.query_params["last_activity"] = str(current_time)
        except ValueError:
            st.query_params["last_activity"] = str(current_time)
    else:
        st.query_params["last_activity"] = str(current_time)

# 다국어 처리
if "lang" in q_params:
    lang_val = q_params["lang"]
    if isinstance(lang_val, list): lang_val = lang_val[0]
    if str(lang_val).lower() in ["en", "english"]:
        st.session_state.lang = "en"
    elif str(lang_val).lower() in ["ko", "korean"]:
        st.session_state.lang = "ko"

# PortOne 자동 결제 승격 처리
if "portone_paid" in q_params and "user_id" in q_params:
    user_id_param = q_params.get("user_id", [""])[0] if isinstance(q_params.get("user_id"), list) else q_params.get("user_id", "")
    months_param = int(q_params.get("months", ["2"])[0] if isinstance(q_params.get("months"), list) else q_params.get("months", 2))
    plan_name_param = q_params.get("plan_name", ["정식 사용자"])[0] if isinstance(q_params.get("plan_name"), list) else q_params.get("plan_name", "정식 사용자")
    if user_id_param:
        kst_now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
        
        # 기존 사용자 정보 조회
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("SELECT role, expiry_date FROM users WHERE id=?", (user_id_param,))
        res = c.fetchone()
        conn.close()
        
        current_role = "temp"
        current_expiry = kst_now.strftime("%Y-%m-%d")
        if res:
            current_role, current_expiry = res[0], res[1]
            
        if months_param > 0:
            new_expiry_date = (kst_now + relativedelta(months=months_param)).strftime("%Y-%m-%d")
            target_role = "official"
        else:
            new_expiry_date = current_expiry
            target_role = current_role
            
        update_user_full_info(user_id_param, None, target_role, new_expiry_date, plan_type=plan_name_param)
        
        import hashlib
        login_token = hashlib.sha256(f"{user_id_param}:AHP_MASTER_SECURE_SALT_2026_!@#".encode()).hexdigest()
        html_code = f"""
        <!DOCTYPE html>
        <html>
        <head><meta charset="utf-8"></head>
        <body style="font-family: sans-serif; text-align: center; padding: 50px;">
          <h3 style="color: green;">🎉 결제가 완료되어 정식 사용자로 승급되었습니다!</h3>
          <p>아래 버튼을 클릭하여 로그인을 진행해 주세요.</p>
          <button onclick="handleLogin()" style="padding: 12px 24px; background-color: #4CAF50; color: white; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; margin-top: 20px; font-weight: bold;">로그인하기</button>
          <script>
            // 원래 창(opener)이 있다면 로그인 처리 URL로 이동시킵니다.
            var loginUrl = "https://ahpkrj.streamlit.app/?login_user=" + encodeURIComponent("{user_id_param}") + "&login_token=" + encodeURIComponent("{login_token}");
            try {{
                var mainWin = null;
                if (window.top && window.top.opener) {{
                    mainWin = window.top.opener;
                }} else if (window.opener) {{
                    mainWin = window.opener;
                }}
                
                if (mainWin) {{
                    mainWin.location.href = loginUrl;
                }}
            }} catch(e) {{
                console.error("Failed to redirect main window:", e);
            }}

            function handleLogin() {{
                // 새 브라우저 창 띄우기 (자동 로그인 URL 포함)
                window.open(loginUrl, "_blank");
                // 결제완료창 닫기
                try {{
                    if (window.top) {{
                        window.top.close();
                    }} else {{
                        window.close();
                    }}
                }} catch(e) {{
                    window.close();
                }}
            }}
          </script>
        </body>
        </html>
        """
        st.components.v1.html(html_code, height=400)
    st.stop()

# 페이팔 자동 결제 승격 처리 (서버 검증 포함)
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
            months_param = int(q_params.get("months", ["2"])[0] if isinstance(q_params.get("months"), list) else q_params.get("months", 2))
            plan_name_param = q_params.get("plan_name", ["정식 사용자"])[0] if isinstance(q_params.get("plan_name"), list) else q_params.get("plan_name", "정식 사용자")
            
            kst_now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
            
            # 기존 사용자 정보 조회
            conn = sqlite3.connect('users.db')
            c = conn.cursor()
            c.execute("SELECT role, expiry_date FROM users WHERE id=?", (target_user,))
            res = c.fetchone()
            conn.close()
            
            current_role = "temp"
            current_expiry = kst_now.strftime("%Y-%m-%d")
            if res:
                current_role, current_expiry = res[0], res[1]
                
            if months_param > 0:
                new_expiry_date = (kst_now + relativedelta(months=months_param)).strftime("%Y-%m-%d")
                target_role = "official"
            else:
                new_expiry_date = current_expiry
                target_role = current_role
                
            update_user_full_info(target_user, None, target_role, new_expiry_date, plan_type=plan_name_param)
            
            if st.session_state.get("user_id") == target_user:
                st.session_state.user_role = target_role
                st.session_state.expiry_date = new_expiry_date
            st.toast("🎉 PayPal Payment successful! Account upgraded/updated.")
    else:
        st.error(f"Payment verification failed: {msg}")
        
    st.query_params.clear()
    st.rerun()

# 정식 회원 자동 만료 체크 (로그인 상태)
if st.session_state.user_id is not None and st.session_state.user_role == 'official':
    today = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).date()
    try:
        expiry_date_val_temp = datetime.datetime.strptime(st.session_state.expiry_date, "%Y-%m-%d").date()
        if today > expiry_date_val_temp:
            update_user_full_info(st.session_state.user_id, None, "temp", "9999-12-31")
            st.session_state.user_role = "temp"
            st.session_state.expiry_date = "9999-12-31"
            st.toast("📅 Subscription expired. Automatically downgraded to Free User.")
            st.rerun()
    except Exception:
        pass

# =============================================================================
# 3. Sidebar (Auth & Settings) - 항상 표시되도록 위치 조정
# =============================================================================

def get_login_redirect_html(plan_name="정식 사용자", inner_html="", is_best=False, lang="ko"):
    border_css = "border: 2px solid #ff4b4b;" if is_best else "border: 1px solid #ddd;"
    best_badge = "<div style='position: absolute; top: -12px; right: 15px; background-color: #ff4b4b; color: white; padding: 3px 12px; border-radius: 12px; font-size: 0.8rem; font-weight: bold;'>BEST</div>" if is_best else ""
    
    btn_label = f"Pay {plan_name.split(' (')[0]}" if lang == "en" else f"결제 {plan_name.split(' (')[0]}"
    alert_msg = "Login or Sign-up is required. Please proceed in the main tab or sidebar." if lang == "en" else "로그인 또는 회원가입이 필요합니다. 메인 탭이나 사이드바를 통해 로그인/가입을 진행해주세요."
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <style>
        @import url("https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css");
        body {{ font-family: 'Pretendard', sans-serif; margin:0; padding: 15px 5px 5px 5px; box-sizing: border-box; }}
        .pricing-box {{
            padding: 15px; 
            border-radius: 10px; 
            {border_css}
            height: 500px; 
            position: relative;
            display: flex;
            flex-direction: column;
            box-sizing: border-box;
            background: white;
        }}
        .btn {{
            margin-top: auto;
            width: 100%;
            padding: 12px;
            background-color: #333333;
            color: white;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 15px;
            font-weight: bold;
            font-family: inherit;
        }}
        .btn:hover {{ background-color: #555555; }}
      </style>
    </head>
    <body>
      <div class="pricing-box">
          {best_badge}
          <div>{inner_html}</div>
          <button class="btn" onclick="redirectSignup()">{btn_label}</button>
      </div>
      <script>
        function redirectSignup() {{
            const tabs = window.parent.document.querySelectorAll('button[data-baseweb="tab"]');
            for (let i = 0; i < tabs.length; i++) {{
                if (tabs[i].innerText.includes('회원가입') || tabs[i].innerText.includes('Sign Up')) {{
                    tabs[i].click();
                    window.parent.scrollTo(0, 0);
                    return;
                }}
            }}
            // Fallback
            alert('{alert_msg}');
            window.parent.scrollTo(0, 0);
        }}
      </script>
    </body>
    </html>
    """

def get_portone_payment_html(user_id, plan_name="정식 사용자", amount=500000, months=2, inner_html="", is_best=False):
    import hashlib
    login_token = hashlib.sha256(f"{user_id}:AHP_MASTER_SECURE_SALT_2026_!@#".encode()).hexdigest()
    # 이메일 형식 검증 (간단히 @ 포함 여부로 확인) 및 공백 제거
    safe_email = user_id.strip() if user_id and "@" in user_id else "test@ahp.kr"
    
    border_css = "border: 2px solid #ff4b4b;" if is_best else "border: 1px solid #ddd;"
    best_badge = "<div style='position: absolute; top: -12px; right: 15px; background-color: #ff4b4b; color: white; padding: 3px 12px; border-radius: 12px; font-size: 0.8rem; font-weight: bold;'>BEST</div>" if is_best else ""
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <style>
        @import url("https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css");
        body {{ font-family: 'Pretendard', sans-serif; margin:0; padding: 15px 5px 5px 5px; box-sizing: border-box; }}
        .pricing-box {{
            padding: 15px; 
            border-radius: 10px; 
            {border_css}
            height: 500px; 
            position: relative;
            display: flex;
            flex-direction: column;
            box-sizing: border-box;
            background: white;
        }}
        .btn {{
            margin-top: auto;
            width: 100%;
            padding: 12px;
            background-color: #333333;
            color: white;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 15px;
            font-weight: bold;
            font-family: inherit;
        }}
        .btn:hover {{ background-color: #555555; }}
      </style>
    </head>
    <body>
      <div class="pricing-box">
          {best_badge}
          <div>{inner_html}</div>
          <button class="btn" onclick="openPaymentWindow()">결제 {plan_name.split(" (")[0]}</button>
      </div>
      <script>
        function openPaymentWindow() {{
          const win = window.open("", "_blank", "width=850,height=700");
          if (!win) {{
             alert("팝업 차단이 설정되어 있습니다. 팝업 차단을 해제해주세요.");
             return;
          }}
          win.document.write(`
            <!DOCTYPE html>
            <html>
            <head>
              <meta charset="utf-8">
              <title>안전 결제 진행</title>
            </head>
            <body style="margin:0; padding:20px; font-family: sans-serif; text-align: center;">
              <h3 id="statusMsg">결제 모듈을 안전하게 불러오는 중입니다...</h3>
              <p>이 창을 닫지 마세요.</p>
            </body>
            </html>
          `);
          win.document.close();

          let baseOrigin = "https://ahpkrj.streamlit.app";
          try {{
             if (window.top && window.top.location && window.top.location.origin && window.top.location.origin !== "null") {{
                 baseOrigin = window.top.location.origin + window.top.location.pathname;
             }}
          }} catch(e) {{}}
          if (baseOrigin.endsWith("/")) {{ baseOrigin = baseOrigin.slice(0, -1); }}
          const returnUrl = baseOrigin + "/?portone_paid=true&user_id=" + encodeURIComponent("{user_id}") + "&login_user=" + encodeURIComponent("{user_id}") + "&login_token=" + encodeURIComponent("{login_token}") + "&months={months}&plan_name=" + encodeURIComponent("{plan_name}");
          const script = win.document.createElement("script");
          script.src = "https://cdn.portone.io/v2/browser-sdk.js";
          script.onload = function() {{
            win.document.getElementById("statusMsg").innerText = "결제창을 띄우는 중입니다...";
            const r = Math.random().toString(36).substring(2, 15);
            win.PortOne.requestPayment({{
              storeId: "store-e653cab4-7da6-4bcb-9968-63f77d048c5d",
              channelKey: "channel-key-4279e2d9-c986-47cb-b190-ab1f9bb71215",
              paymentId: "pay-" + r,
              orderName: "{plan_name} - {safe_email}",
              totalAmount: {amount},
              currency: "CURRENCY_KRW",
              payMethod: "CARD",
              redirectUrl: returnUrl,
              customer: {{
                email: "{safe_email}",
                fullName: "사용자",
                phoneNumber: "010-0000-0000"
              }}
            }}).then(function(response) {{
              if (response.code != null) {{
                alert("결제 실패: " + response.message);
                win.close();
              }} else {{
                win.location.href = returnUrl;
              }}
            }}).catch(function(error) {{
              alert("결제 창 호출 중 오류가 발생했습니다: " + error.message);
              win.close();
            }});
          }};
          script.onerror = function() {{
            win.document.getElementById("statusMsg").innerText = "결제 모듈 로드 실패! 인터넷 연결을 확인하세요.";
          }};
          win.document.head.appendChild(script);
        }}
      </script>
    </body>
    </html>
    """

def get_portone_custom_services_html(user_id=None):
    import hashlib
    login_token = ""
    safe_email = "test@ahp.kr"
    if user_id:
        login_token = hashlib.sha256(f"{user_id}:AHP_MASTER_SECURE_SALT_2026_!@#".encode()).hexdigest()
        safe_email = user_id.strip() if "@" in user_id else "test@ahp.kr"

    is_logged_in = "true" if user_id else "false"

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <style>
        @import url("https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css");
        body {{ font-family: 'Pretendard', sans-serif; margin:0; padding: 15px 5px 5px 5px; box-sizing: border-box; }}
        .pricing-box {{
            padding: 15px; 
            border-radius: 10px; 
            border: 1px solid #ddd;
            height: 500px; 
            position: relative;
            display: flex;
            flex-direction: column;
            box-sizing: border-box;
            background: white;
        }}
        .title {{ margin-top: 0 !important; margin-bottom: 0; font-size: 1.3rem; font-weight: bold; color: #333; }}
        .subtitle {{ color: #888; font-size: 1.1rem; }}
        .price-container {{ margin-top: 15px; margin-bottom: 5px; }}
        .price {{ color: #ff4b4b; font-size: 2rem; font-weight: bold; margin: 0; }}
        .period {{ color: #555; margin-top:0; font-size: 1rem; }}
        .desc {{ font-size: 0.85rem; color: #666; min-height: 40px; margin: 0; }}
        .divider {{ margin: 10px 0; border: 0; border-top: 1px solid #eee; }}
        
        .svc-list {{
            list-style: none;
            padding-left: 0;
            margin: 0;
            font-size: 0.9rem;
            color: #333;
            line-height: 1.8;
            flex-grow: 1;
        }}
        .svc-item {{
            display: flex;
            align-items: flex-start;
            margin-bottom: 8px;
            cursor: pointer;
        }}
        .svc-item input[type="checkbox"] {{
            margin-right: 8px;
            margin-top: 4px;
            cursor: pointer;
            accent-color: #ff4b4b;
        }}
        .svc-item span {{
            font-size: 0.85rem;
            line-height: 1.4;
        }}
        
        .btn {{
            margin-top: auto;
            width: 100%;
            padding: 12px;
            background-color: #333333;
            color: white;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 15px;
            font-weight: bold;
            font-family: inherit;
        }}
        .btn:hover {{ background-color: #555555; }}
      </style>
    </head>
    <body>
      <div class="pricing-box">
          <h3 class="title">부가 서비스 대행</h3>
          <span class="subtitle">Custom Services</span>
          <div class="price-container">
              <h2 class="price" id="totalPriceDisplay">0원</h2>
          </div>
          <p class="period">선택된 서비스 합계 금액</p>
          <p class="desc" id="statusDesc">필요한 서비스를 선택해 주세요.</p>
          <hr class="divider">
          
          <ul class="svc-list">
              <li class="svc-item">
                  <label style="display: flex; align-items: flex-start;">
                      <input type="checkbox" id="svc_opt_1" value="50000" data-name="온라인 설문 셋팅" onchange="updatePrice()">
                      <span>AHP 온라인 설문 셋팅 <span style="color: #666; font-size: 0.75rem;">(50,000원)</span></span>
                  </label>
              </li>
              <li class="svc-item">
                  <label style="display: flex; align-items: flex-start;">
                      <input type="checkbox" id="svc_opt_2" value="50000" data-name="결과 분석 대행" onchange="updatePrice()">
                      <span>AHP 결과 분석 대행 <span style="color: #666; font-size: 0.75rem;">(50,000원)</span></span>
                  </label>
              </li>
              <li class="svc-item">
                  <label style="display: flex; align-items: flex-start;">
                      <input type="checkbox" id="svc_opt_3" value="30000" data-name="코딩 엑셀 양식 설정 대행" onchange="updatePrice()">
                      <span>AHP 코딩 엑셀 설정 대행 <span style="color: #666; font-size: 0.75rem;">(30,000원)</span></span>
                  </label>
              </li>
          
              <li class="svc-item">
                  <label style="display: flex; align-items: flex-start;">
                      <input type="checkbox" id="svc_opt_ext" value="100000" data-name="1개월 이용 연장" onchange="updatePrice()">
                      <span>1개월 이용 연장 <span style="color: #666; font-size: 0.75rem;">(100,000원)</span></span>
                  </label>
              </li>
          </ul>
          
          <div style="font-size: 0.72rem; color: #555; text-align: center; margin-bottom: 12px; background: #fafafa; padding: 6px; border-radius: 5px; border: 1px dashed #ccc; line-height: 1.4;">
              연구비용 견적서 발급 및 부가서비스 문의: <br>카톡아이디: <b>AHPkr</b>
          </div>
          
          <button class="btn" id="payBtn" onclick="handlePayAction()">결제하기</button>
      </div>
      
      <script>
        function updatePrice() {{
            const opt1 = document.getElementById("svc_opt_1");
            const opt2 = document.getElementById("svc_opt_2");
            const opt3 = document.getElementById("svc_opt_3");
            
            let total = 0;
            let count = 0;
            if (opt1.checked) {{ total += parseInt(opt1.value); count++; }}
            if (opt2.checked) {{ total += parseInt(opt2.value); count++; }}
            if (opt3.checked) {{ total += parseInt(opt3.value); count++; }}
            
            document.getElementById("totalPriceDisplay").innerText = total.toLocaleString() + "원";
            if (count > 0) {{
                document.getElementById("statusDesc").innerText = "선택된 대행 서비스 총 " + count + "건";
                document.getElementById("payBtn").innerText = "결제하기";
                document.getElementById("payBtn").style.backgroundColor = "#ff4b4b";
            }} else {{
                document.getElementById("statusDesc").innerText = "필요한 서비스를 선택해 주세요.";
                document.getElementById("payBtn").innerText = "옵션을 선택해주세요";
                document.getElementById("payBtn").style.backgroundColor = "#333333";
            }}
        }}
        
        updatePrice();
        
        function handlePayAction() {{
            const opt1 = document.getElementById("svc_opt_1");
            const opt2 = document.getElementById("svc_opt_2");
            const opt3 = document.getElementById("svc_opt_3");
            
            let total = 0;
            let items = [];
            if (opt1.checked) {{ total += parseInt(opt1.value); items.push(opt1.getAttribute("data-name")); }}
            if (opt2.checked) {{ total += parseInt(opt2.value); items.push(opt2.getAttribute("data-name")); }}
            if (opt3.checked) {{ total += parseInt(opt3.value); items.push(opt3.getAttribute("data-name")); }}
            
            if (total === 0) {{
                alert("결제하실 부가 서비스 대행 옵션을 하나 이상 선택해주세요.");
                return;
            }}
            
            if ({is_logged_in}) {{
                openPaymentWindow(total, items.join(", "), addMonths);
            }} else {{
                redirectSignup();
            }}
        }}
        
        function redirectSignup() {{
            const tabs = window.parent.document.querySelectorAll('button[data-baseweb="tab"]');
            for (let i = 0; i < tabs.length; i++) {{
                if (tabs[i].innerText.includes('회원가입') || tabs[i].innerText.includes('Sign Up')) {{
                    tabs[i].click();
                    window.parent.scrollTo(0, 0);
                    return;
                }}
            }}
            alert('로그인 또는 회원가입이 필요합니다. 메인 탭이나 사이드바를 통해 로그인/가입을 진행해주세요.');
            window.parent.scrollTo(0, 0);
        }}
        
        function openPaymentWindow(amount, planName, addMonths) {{
          const win = window.open("", "_blank", "width=850,height=700");
          if (!win) {{
             alert("팝업 차단이 설정되어 있습니다. 팝업 차단을 해제해주세요.");
             return;
          }}
          win.document.write(`
            <!DOCTYPE html>
            <html>
            <head>
              <meta charset="utf-8">
              <title>안전 결제 진행</title>
            </head>
            <body style="margin:0; padding:20px; font-family: sans-serif; text-align: center;">
              <h3 id="statusMsg">결제 모듈을 안전하게 불러오는 중입니다...</h3>
              <p>이 창을 닫지 마세요.</p>
            </body>
            </html>
          `);
          win.document.close();
          
          let baseOrigin = "https://ahpkrj.streamlit.app";
          try {{
             if (window.top && window.top.location && window.top.location.origin && window.top.location.origin !== "null") {{
                 baseOrigin = window.top.location.origin + window.top.location.pathname;
             }}
          }} catch(e) {{}}
          if (baseOrigin.endsWith("/")) {{ baseOrigin = baseOrigin.slice(0, -1); }}
          
          const returnUrl = baseOrigin + "/?portone_paid=true&user_id=" + encodeURIComponent("{user_id}") + "&login_user=" + encodeURIComponent("{user_id}") + "&login_token=" + encodeURIComponent("{login_token}") + "&months=" + addMonths + "&plan_name=" + encodeURIComponent("부가 서비스: " + planName);
          
          const script = win.document.createElement("script");
          script.src = "https://cdn.portone.io/v2/browser-sdk.js";
          script.onload = function() {{
            win.document.getElementById("statusMsg").innerText = "결제창을 띄우는 중입니다...";
            const r = Math.random().toString(36).substring(2, 15);
            win.PortOne.requestPayment({{
              storeId: "store-e653cab4-7da6-4bcb-9968-63f77d048c5d",
              channelKey: "channel-key-4279e2d9-c986-47cb-b190-ab1f9bb71215",
              paymentId: "pay-" + r,
              orderName: "부가 서비스: " + planName + " - {safe_email}",
              totalAmount: amount,
              currency: "CURRENCY_KRW",
              payMethod: "CARD",
              redirectUrl: returnUrl,
              customer: {{
                email: "{safe_email}",
                fullName: "사용자",
                phoneNumber: "010-0000-0000"
              }}
            }}).then(function(response) {{
              if (response.code != null) {{
                alert("결제 실패: " + response.message);
                win.close();
              }} else {{
                win.location.href = returnUrl;
              }}
            }}).catch(function(error) {{
              alert("결제 창 호출 중 오류가 발생했습니다: " + error.message);
              win.close();
            }});
          }};
          script.onerror = function() {{
            win.document.getElementById("statusMsg").innerText = "결제 모듈 로드 실패! 인터넷 연결을 확인하세요.";
          }};
          win.document.head.appendChild(script);
        }}
      </script>
    </body>
    </html>
    """

def get_paypal_payment_html(user_id, plan_name="Official User", amount_usd=162.00, months=1, inner_html="", is_best=False):


    border_css = "border: 2px solid #ff4b4b;" if is_best else "border: 1px solid #ddd;"
    best_badge = "<div style='position: absolute; top: -12px; right: 15px; background-color: #ff4b4b; color: white; padding: 3px 12px; border-radius: 12px; font-size: 0.8rem; font-weight: bold;'>BEST</div>" if is_best else ""
    paypal_client_id = st.secrets.get("PAYPAL_CLIENT_ID", "sb")
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <style>
        @import url("https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css");
        body {{ font-family: 'Pretendard', sans-serif; margin:0; padding: 15px 5px 5px 5px; box-sizing: border-box; }}
        .pricing-box {{
            padding: 15px; 
            border-radius: 10px; 
            {border_css}
            height: 500px; 
            position: relative;
            display: flex;
            flex-direction: column;
            box-sizing: border-box;
            background: white;
        }}
        .paypal-btn-container {{
            margin-top: auto;
            width: 100%;
        }}
      </style>
    </head>
    <body>
      <div class="pricing-box">
          {best_badge}
          <div>{inner_html}</div>
          <div class="paypal-btn-container" id="paypal-button-container"></div>
      </div>
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
                  value: '{amount_usd:.2f}'
                }},
                description: '{plan_name}'
              }}]
            }});
          }},
          onApprove: function(data, actions) {{
            return actions.order.capture().then(function(details) {{
              window.top.location.href = window.top.location.origin + window.top.location.pathname + "?paypal_order_id=" + data.orderID + "&user_id=" + encodeURIComponent("{user_id}") + "&months={months}&plan_name=" + encodeURIComponent("{plan_name}");
            }});
          }},
          onError: function(err) {{
            alert('PayPal payment failed or was cancelled.');
          }}
        }}).render('#paypal-button-container');
      </script>
    </body>
    </html>
    """


def get_paypal_custom_services_html(user_id=None):







    is_logged_in = "true" if user_id else "false"
    paypal_client_id = st.secrets.get("PAYPAL_CLIENT_ID", "sb")

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <style>
        @import url("https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css");
        body {{ font-family: 'Pretendard', sans-serif; margin:0; padding: 15px 5px 5px 5px; box-sizing: border-box; }}
        .pricing-box {{
            padding: 15px; 
            border-radius: 10px; 
            border: 1px solid #ddd;
            height: 500px; 
            position: relative;
            display: flex;
            flex-direction: column;
            box-sizing: border-box;
            background: white;
        }}
        .title {{ margin-top: 0 !important; margin-bottom: 0; font-size: 1.3rem; font-weight: bold; color: #333; }}
        .subtitle {{ color: #888; font-size: 1.1rem; }}
        .price-container {{ margin-top: 15px; margin-bottom: 5px; }}
        .price {{ color: #ff4b4b; font-size: 2rem; font-weight: bold; margin: 0; }}
        .period {{ color: #555; margin-top:0; font-size: 1rem; }}
        .desc {{ font-size: 0.85rem; color: #666; min-height: 40px; margin: 0; }}
        .divider {{ margin: 10px 0; border: 0; border-top: 1px solid #eee; }}
        
        .svc-list {{
            list-style: none;
            padding-left: 0;
            margin: 0;
            font-size: 0.9rem;
            color: #333;
            line-height: 1.8;
            flex-grow: 1;
        }}
        .svc-item {{
            display: flex;
            align-items: flex-start;
            margin-bottom: 8px;
            cursor: pointer;
        }}
        .svc-item input[type="checkbox"] {{
            margin-right: 8px;
            margin-top: 4px;
            cursor: pointer;
            accent-color: #ff4b4b;
        }}
        .svc-item span {{
            font-size: 0.85rem;
            line-height: 1.4;
        }}
        .paypal-btn-container {{
            margin-top: auto;
            width: 100%;
            min-height: 40px;
        }}
      </style>
    </head>
    <body>
      <div class="pricing-box">
          <h3 class="title">Proxy Services</h3>
          <span class="subtitle">Custom Services</span>
          <div class="price-container">
              <h2 class="price" id="totalPriceDisplay">$0 USD</h2>
          </div>
          <p class="period">Total Selected Amount</p>
          <p class="desc" id="statusDesc">Please select the proxy services you need.</p>
          <hr class="divider">
          
          <ul class="svc-list">
              <li class="svc-item">
                  <label style="display: flex; align-items: flex-start;">
                      <input type="checkbox" id="svc_opt_1" value="33" data-name="Online Survey Setup" onchange="updatePrice()">
                      <span>AHP Online Survey Setup<br><span style="color: #666; font-size: 0.75rem;">($33 USD)</span></span>
                  </label>
              </li>
              <li class="svc-item">
                  <label style="display: flex; align-items: flex-start;">
                      <input type="checkbox" id="svc_opt_2" value="33" data-name="Result Analysis Proxy" onchange="updatePrice()">
                      <span>AHP Result Analysis Proxy <span style="color: #666; font-size: 0.75rem;">($33 USD)</span></span>
                  </label>
              </li>
              <li class="svc-item">
                  <label style="display: flex; align-items: flex-start;">
                      <input type="checkbox" id="svc_opt_3" value="20" data-name="Coding Excel Sheet Setup" onchange="updatePrice()">
                      <span>AHP Coding Excel Sheet Setup<br><span style="color: #666; font-size: 0.75rem;">($20 USD)</span></span>
                  </label>
              </li>
          
              <li class="svc-item">
                  <label style="display: flex; align-items: flex-start;">
                      <input type="checkbox" id="svc_opt_ext" value="74" data-name="1 Month Extension" onchange="updatePrice()">
                      <span>1 Month Extension <span style="color: #666; font-size: 0.75rem;">($74 USD)</span></span>
                  </label>
              </li>
          </ul>
          
          <div style="font-size: 0.72rem; color: #555; text-align: center; margin-bottom: 12px; background: #fafafa; padding: 6px; border-radius: 5px; border: 1px dashed #ccc; line-height: 1.4;">
              Proxy Request/Inquiry : <br>Email: <b>jeon080423@gmail.com</b>
          </div>
          
          <div class="paypal-btn-container" id="paypal-button-container"></div>
      </div>
      
      <script src="https://www.paypal.com/sdk/js?client-id={paypal_client_id}&currency=USD&locale=en_US"></script>
      <script>
        function updatePrice() {{
            const opt1 = document.getElementById("svc_opt_1");
            const opt2 = document.getElementById("svc_opt_2");
            const opt3 = document.getElementById("svc_opt_3");
            
            let total = 0;
            let count = 0;
            let items = [];
            if (opt1.checked) {{ total += parseInt(opt1.value); count++; items.push(opt1.getAttribute("data-name")); }}
            if (opt2.checked) {{ total += parseInt(opt2.value); count++; items.push(opt2.getAttribute("data-name")); }}
            if (opt3.checked) {{ total += parseInt(opt3.value); count++; items.push(opt3.getAttribute("data-name")); }}
            
            document.getElementById("totalPriceDisplay").innerText = "$" + total.toLocaleString() + " USD";
            
            if (count > 0) {{
                document.getElementById("statusDesc").innerText = "Selected services: " + count + " item(s)";
            }} else {{
                document.getElementById("statusDesc").innerText = "Please select the proxy services you need.";
            }}
            
            renderPaypalButton(total, items.join(", "));
        }}
        
        function renderPaypalButton(amount, planName) {{
            const container = document.getElementById("paypal-button-container");
            container.innerHTML = "";
            
            if (amount === 0) {{
                container.innerHTML = '<div style="text-align: center; padding: 10px; background: #eee; font-size: 0.85rem; border-radius: 5px; color: #777; font-weight: bold;">Select an option above</div>';
                return;
            }}
            
            paypal.Buttons({{
              style: {{
                layout: 'vertical',
                color:  'gold',
                shape:  'rect',
                label:  'paypal',
                height: 35
              }},
              createOrder: function(data, actions) {{
                if (!{is_logged_in}) {{
                    redirectSignup();
                    return Promise.reject("Sign in required");
                }}
                return actions.order.create({{
                  purchase_units: [{{
                    amount: {{
                      value: amount.toFixed(2)
                    }},
                    description: "Proxy Services: " + planName
                  }}]
                }});
              }},
              onApprove: function(data, actions) {{
                return actions.order.capture().then(function(details) {{
                  window.top.location.href = window.top.location.origin + window.top.location.pathname + "?paypal_order_id=" + data.orderID + "&user_id=" + encodeURIComponent("{user_id}") + "&months=" + addMonths + "&plan_name=" + encodeURIComponent("부가 서비스: " + planName);
                }});
              }},
              onError: function(err) {{
                alert('PayPal payment failed or was cancelled.');
              }}
            }}).render('#paypal-button-container');
        }}
        
        updatePrice();
        
        function redirectSignup() {{
            const tabs = window.parent.document.querySelectorAll('button[data-baseweb="tab"]');
            for (let i = 0; i < tabs.length; i++) {{
                if (tabs[i].innerText.includes('회원가입') || tabs[i].innerText.includes('Sign Up')) {{
                    tabs[i].click();
                    window.parent.scrollTo(0, 0);
                    return;
                }}
            }}
            alert('Login or Sign-up is required. Please proceed in the main tab or sidebar.');
            window.parent.scrollTo(0, 0);
        }}
      </script>
    </body>
    </html>
    """


def get_fee_info_text():
    return _(
        """<div style="line-height: 1.4; font-size: 0.95rem;">
  <hr style="margin-top: 15px; margin-bottom: 15px; border: 0; border-top: 1px solid #ddd;">
  <div style="background-color: #e6f7ff; border-left: 4px solid #1890ff; padding: 10px; margin-bottom: 12px; border-radius: 4px;">
    <span style="font-size: 0.9rem; color: #0050b3; font-weight: bold;">💡 계산서 발급 가능</span>
  </div>
  <h3 style="margin-top: -5px; margin-bottom: 8px;">환불 및 취소 규정</h3>
  <div style="margin-top: 10px; font-size: 0.85rem; color: #444; background-color: #f9f9f9; padding: 12px; border-radius: 5px; border: 1px solid #eee;">
    <div style="display: grid; grid-template-columns: auto 1fr; row-gap: 6px; column-gap: 8px; line-height: 1.45;">
      <div style="font-weight: bold; color: #333; white-space: nowrap;">• 환불정책:</div>
      <div>불만족 100% 환불</div>
      <div style="font-weight: bold; color: #333; white-space: nowrap;">• 취소규정:</div>
      <div>30분 이내 취소 신청</div>
    </div>
  </div>
</div>""",
        """<div style="line-height: 1.4; font-size: 0.95rem;">
  <hr style="margin-top: 15px; margin-bottom: 15px; border: 0; border-top: 1px solid #ddd;">
  <div style="background-color: #e6f7ff; border-left: 4px solid #1890ff; padding: 10px; margin-bottom: 12px; border-radius: 4px;">
    <span style="font-size: 0.9rem; color: #0050b3; font-weight: bold;">💡 Tax Invoice Available</span>
  </div>
  <h3 style="margin-top: -5px; margin-bottom: 8px;">Refund & Cancellation Policy</h3>
  <div style="margin-top: 10px; font-size: 0.85rem; color: #444; background-color: #f9f9f9; padding: 12px; border-radius: 5px; border: 1px solid #eee;">
    <div style="display: grid; grid-template-columns: auto 1fr; row-gap: 6px; column-gap: 8px; line-height: 1.45;">
      <div style="font-weight: bold; color: #333; white-space: nowrap;">• Refund Policy:</div>
      <div>100% Refund if unsatisfied</div>
      <div style="font-weight: bold; color: #333; white-space: nowrap;">• Cancellation Policy:</div>
      <div>Cancellation within 30 minutes</div>
    </div>
  </div>
</div>"""
    )

with st.sidebar:


    try:
        import base64
        with open("ahp_master_logo.png", "rb") as f:
            encoded_logo = base64.b64encode(f.read()).decode()
        st.markdown(
            f'<a href="https://jeon080423.github.io/AHPkr" target="_blank">'
            f'<img src="data:image/png;base64,{encoded_logo}" style="width:100%; border-radius: 4px; display: block; margin-bottom: 10px;">'
            f'</a>',
            unsafe_allow_html=True
        )
    except:
        st.markdown(
            f'<a href="https://jeon080423.github.io/AHPkr" target="_blank" style="text-decoration: none; color: inherit;">'
            f'<h3 style="margin-top: -5px; margin-bottom: 10px;">{_(" AHP 마스터", " AHP Master")}</h3>'
            f'</a>',
            unsafe_allow_html=True
        )


    if st.session_state.user_id is None:
        tab_login, tab_find_pw = st.tabs([_("로그인", "Login"), _("비밀번호 찾기", "Find Password")])
        
        with tab_login:
            l_id = st.text_input(_("아이디 (이메일 주소)", "Username (Email Address)"), key="l_id")
            l_pw = st.text_input(_("비밀번호 (PW)", "Password (PW)"), type="password", key="l_pw")
            if st.button(_("로그인 실행", "Login")):
                result = check_login(l_id.strip(), l_pw)
                if result:
                    # [수정] 대한민국 시간 기준 오늘 날짜 가져오기
                    today = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).date()
                    expiry_date_val = datetime.datetime.strptime(result[1], "%Y-%m-%d").date()
                    if today > expiry_date_val:
                        if result[0] == 'official':
                            # 정식 사용자가 만료된 경우 -> 자동으로 무료사용자(temp)로 즉시 안전 승격 해제 및 전환
                            try:
                                update_user_full_info(l_id.strip(), None, "temp", "9999-12-31")
                                st.session_state.user_id = l_id.strip()
                                st.session_state.user_role = "temp"
                                st.session_state.expiry_date = "9999-12-31"
                                st.query_params["login_user"] = l_id.strip()
                                st.query_params["login_token"] = hashlib.sha256(f"{l_id.strip()}:AHP_MASTER_SECURE_SALT_2026_!@#".encode()).hexdigest()
                                st.query_params["last_activity"] = str(int(time.time()))
                                st.toast(_("📅 정식 이용 기간이 만료되어 무료사용자 권한으로 자동 전환되었습니다.", "📅 Subscription expired. Automatically downgraded to Free User."))
                                st.success(_(f"환영합니다, {l_id}님! 정식 이용 기간이 만료되어 무료사용자(5표본 분석 가능) 권한으로 자동 전환되었습니다. 사이드바에서 언제든 연장 결제하실 수 있습니다!",
                                             f"Welcome, {l_id}! Your subscription expired and you were automatically downgraded to a Free User (5-sample analysis possible). You can extend your subscription anytime in the sidebar!"))
                                st.rerun()
                            except Exception as e:
                                st.error(_(f"만료 회원 자동 전환 처리 중 오류가 발생했습니다: {e}", f"Error during automatic expiry downgrade: {e}"))
                        else:
                            st.error(_(f"❌ 이용 기간이 만료되었습니다. (만료일: {result[1]})", f"❌ Subscription expired. (Expiry date: {result[1]})"))
                    else:
                        st.session_state.user_id = l_id.strip()
                        st.session_state.user_role = result[0]
                        st.session_state.expiry_date = result[1]
                        st.session_state.plan_type = result[2] if len(result) > 2 else None
                        st.query_params["login_user"] = l_id.strip()
                        st.query_params["login_token"] = hashlib.sha256(f"{l_id.strip()}:AHP_MASTER_SECURE_SALT_2026_!@#".encode()).hexdigest()
                        st.query_params["last_activity"] = str(int(time.time()))
                        if 'signup_paypal_user' in st.session_state:
                            del st.session_state.signup_paypal_user
                        if 'signup_portone_user' in st.session_state:
                            del st.session_state.signup_portone_user
                        st.success(_(f"환영합니다, {l_id}님!", f"Welcome, {l_id}!"))
                        st.rerun()
                else:
                    st.error(_("아이디 또는 비밀번호가 일치하지 않습니다.", "Incorrect username or password."))
            
            
        with tab_find_pw:
            st.write(_("가입 시 사용한 이메일 주소를 입력해주세요. 이메일로 새로운 임시 비밀번호가 발송됩니다.",
                       "Please enter the email address used at registration. A new temporary password will be sent to your email."))
            f_id = st.text_input(_("가입한 아이디 (이메일)", "Registered ID (Email)"), key="f_id")
            if st.button(_("임시 비밀번호 전송", "Send Temporary Password")):
                if not f_id:
                    st.warning(_("이메일 주소를 입력해주세요.", "Please enter your email address."))
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
                            st.success(_(f"'{f_id}'로 임시 비밀번호를 전송했습니다.\n이메일을 확인해주세요.", f"Temporary password sent to '{f_id}'.\nPlease check your email."))
                        else:
                            st.error(_("이메일 전송 중 오류가 발생했습니다.", "Error sending email."))
                    else:
                        st.error(_("등록되지 않은 아이디입니다.", "ID is not registered."))

    else:
        if st.session_state.user_role == 'admin':
            role_disp = _("관리자", "Admin")
        elif st.session_state.user_role == 'official':
            pt = st.session_state.get('plan_type')
            role_disp = f"{_('정식 사용자', 'Official User')} ({pt})" if pt else _("정식 사용자", "Official User")
        else:
            role_disp = _("무료사용자", "Free User")
        
        expiry_info = ""
        if st.session_state.expiry_date:
            expiry_label = _("만료일: ", "Expiry: ")
            expiry_info = f' | {expiry_label}{st.session_state.expiry_date}'
            
        info_html = f"""<div style="background-color: #e8f5e9; border: 1px solid #c8e6c9; border-radius: 6px; color: #2e7d32; font-weight: bold; font-size: 0.85rem; padding: 8px 10px; text-align: center; margin-bottom: 8px;">
👤 {st.session_state.user_id} ({role_disp}{expiry_info})
</div>"""
        st.markdown(info_html, unsafe_allow_html=True)
        
        if st.session_state.user_role == 'temp':
            with st.expander(_("💳 정식 사용자 승격/결제", "💳 Upgrade to Official User"), expanded=False):
                if st.session_state.lang == 'en':
                    st.markdown("#####  PayPal Membership Upgrade")
                    st.info("Upgrade to **Official User** to get unlimited access (2 months) for **$350.00 USD**.")
                    
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
                    st.markdown("##### 💳 정식 사용자 승격 결제")
                    st.info("메인 페이지의 **서비스 요금** 탭에서 결제를 진행해 주세요.")
        
    if st.session_state.user_id is not None:
        if st.session_state.user_role == 'admin':
            btn_label = _("🔧 관리자 화면 닫기", "🔧 Exit Admin Panel") if st.session_state.get('admin_mode', False) else _("🔧 관리자 화면 접속", "🔧 Connect to Admin Panel")
            if st.button(btn_label):
                st.session_state.admin_mode = not st.session_state.admin_mode
                st.rerun()

        with st.expander(_("🔐 비밀번호 변경", "🔐 Change Password")):
            cur_pw = st.text_input(_("현재 비밀번호", "Current Password"), type="password", key="chg_cur_new")
            new_pw_val = st.text_input(_("새 비밀번호", "New Password"), type="password", key="chg_new_new")
            confirm_pw = st.text_input(_("새 비밀번호 확인", "Confirm New Password"), type="password", key="chg_conf_new")
            
            if st.button(_("비밀번호 변경", "Change Password"), key="btn_chg_pw_new"):
                if new_pw_val != confirm_pw:
                    st.error(_("새 비밀번호가 일치하지 않습니다.", "New passwords do not match."))
                elif not validate_password(new_pw_val):
                    st.error(_("비밀번호는 4자 이상, 영문+특수문자를 포함해야 합니다.", "Password must be at least 4 characters and contain letters and special characters."))
                else:
                    chk_res = check_login(st.session_state.user_id, cur_pw)
                    if chk_res:
                        change_user_password(st.session_state.user_id, new_pw_val)
                        st.success(_("비밀번호가 변경되었습니다.", "Password successfully changed."))
                    else:
                        st.error(_("현재 비밀번호가 올바르지 않습니다.", "Incorrect current password."))


        if st.button(_("로그아웃", "Log Out"), key="btn_logout_new"):
            st.session_state.user_id = None
            st.session_state.user_role = None
            st.session_state.expiry_date = None
            st.session_state.plan_type = None
            st.session_state.admin_mode = False
            st.session_state.signup_paypal_user = None
            st.session_state.signup_portone_user = None
            st.query_params.pop("login_user", None)
            st.query_params.pop("login_token", None)
            st.rerun()



    st.markdown(get_fee_info_text(), unsafe_allow_html=True)
    if st.button(_("환불 및 취소 신청", "Request Refund & Cancellation"), key="sidebar_refund_btn", use_container_width=True):
        show_refund_dialog()

    if st.session_state.user_id is not None and st.session_state.user_role == 'temp':
        import streamlit.components.v1 as components
        components.html(get_portone_payment_html(st.session_state.user_id), height=60)
    st.markdown("""
    <div style="line-height: 1.4; font-size: 0.95rem;">
      <hr style="margin-top: 15px; margin-bottom: 15px; border: 0; border-top: 1px solid #ddd;">
      <h3 style="margin-top: -5px; margin-bottom: 8px;">사업자정보</h3>
      <div style="font-size: 0.85rem; color: #555;">
        상호: 프레쉬인사이트<br>
        대표자: 전상현<br>
        사업자등록번호: 683-27-00122<br>
        사업장 주소: 인천시 부평구 원길로 12, 가동 203호<br>
        전화번호: 0507-1347-2610<br>
        이메일: jeon080423@gmail.com<br>
        개인정보관리책임자: 전상현<br>
        통신판매업 신고번호: 간이과세자<br>
      </div>
    </div>
    """, unsafe_allow_html=True)



# =============================================================================
# 4. Main Content Logic
# =============================================================================

if st.session_state.get('page', 'main') == 'guide':
    if st.button("← Back to AHP Analysis Tool", use_container_width=True, key="btn_back_to_main"):
        st.session_state.page = "main"
        st.rerun()
    
    st.title(" AHP Master - English User Guide")
    st.markdown("""
    🚀 **Welcome!** **AHP Master** is a smart web service that automatically processes the entire Analytic Hierarchy Process (AHP) workflow in 1 second, without requiring complex equations or statistical software.
    This guide is designed to walk first-time users through the step-by-step process of completing their academic thesis statistics and decision analysis smoothly.
    
    ---
    
    ###  Step 1: Prepare the Excel Template (Write & Customize)
    AHP Master uses a specifically formatted Excel file to read your survey data.
    
    1. **Download Template**: Go to the AHP Master website (https://ahpkrj.streamlit.app/) and click the **[Download Excel Template]** button on the home screen.
    2. **🔥 Customize to Fit Your Model (Important)**:
       * The default template items (evaluation criteria, alternatives, etc.) and hierarchical structure can be freely edited to match your specific research model.
       * You can add or delete criteria to construct your own custom AHP model.
    3. **Enter Survey Data**: Open the customized Excel template and enter your pairwise comparison survey responses.
       * **Evaluation Scale**: Uses Saaty's 1-9 fundamental scale (e.g., enter 7 if item A is much more important than B, enter 1 if they are equally important).
       * **Note**: Be careful not to break the core structure (sheet configuration, etc.) of the template.
    
    ### 📥 Step 2: Upload File & Run Basic Analysis
    Once your data entry is complete, it's time to run the analysis.
    
    1. **File Upload**: Drag and drop your Excel file into the **[Drag and drop file here]** zone in the center of the screen, or click **[Browse files]** to select your file.
    2. **Automatic Execution**: The system will instantly run the complex matrix calculations in the background. Basic analysis typically completes in 1 to 3 seconds.
    
    ### ⚙️ Step 3: Utilize [Analysis Settings] in the Sidebar
    After uploading, you can fine-tune the analysis details through the "Analysis Settings" in the left sidebar to suit your research methodology.
    
    1. **Select Aggregation Method**:
       * You can set specific parameters like the weight integration method (Geometric Mean vs. Arithmetic Mean) or the decimal precision required for your research.
    2. **CR Calibration Settings (Optional)**:
       * You can set boundaries such as how much you allow the original response to change (Correction Intensity/Learning Rate) when performing Consistency Ratio (CR) calibration.
       * *(If accessing on a mobile device, tap the `>` icon in the top left to reveal the sidebar menu.)*
    
    ### 📊 Step 4: Consistency Validation & Automatic Calibration (CR)
    This is the step to validate the logical consistency of responses, which is critical in AHP academic studies.
    
    1. **Check Initial CR Value**: Check the **Consistency Ratio (CR)** displayed in the results panel.
       * `CR < 0.1` (Green): Indicates highly consistent and logical responses (Passed).
       * `CR > 0.1` (Red): Indicates logical contradictions exceed the standard limit (Needs Calibration).
    2. **🔥 One-Click Auto Calibration**: If the initial CR value exceeds 0.1, do not worry. Simply click the **[CR Auto Calibration]** button. AHP Master's optimization algorithm will adjust the CR value to under 0.1 automatically, preserving the original response preferences as much as possible.
    
    ### 🏆 Step 5: Check Weights & Save Results
    Once all validations and settings are complete, use the final results in your report or paper.
    
    1. **Check Weights & Rankings**:
       * **Main/Sub-Criteria Weights**: View the weight percentages and decimals representing the importance of each item.
       * **Global Rank**: View the overall 1st-to-last rankings of the items in an intuitive table and visual Plotly charts.
    2. **Download Results (Excel/Image)**:
       * Click the **[Download Results (Excel)]** button at the bottom of the screen to save the results in a clean table format ready to copy-paste.
       * Click the camera icon in the top right of the Plotly charts to save the charts as high-resolution images (PNG).
    
    ---
    
    ### 💡 Frequently Asked Questions (FAQ)
    
    * **Q1. Can I change the template items to fit my specific paper?**
      * **Yes, absolutely!** The default template is only an example. You can add or delete rows and columns, rename text, and modify items to build **your own custom hierarchical model (Custom Model)** to fit your evaluation criteria and alternative count.
    * **Q2. Can I analyze data from multiple survey respondents (group analysis) at once?**
      * Yes! If you have multiple respondents, you can calculate the geometric mean of individual pairwise comparisons in Excel, enter the aggregated figures into the template, and upload it to calculate the group weights at once.
    * **Q3. I see an "Error" message during upload. Why?**
      * In the customization process, the required sheets' layout may have been broken, or some number input cells might have empty (Null) values or text instead of numbers. Please review your Excel template to ensure all numeric inputs are complete.
    
    ---
    
    ### 💬 Contact & Support
    If you have any questions during analysis, or need custom AHP consulting (expert survey execution, thesis statistical consulting, etc.), please contact us:
    * **Email**: jeon080423@gmail.com
    * **KakaoTalk ID**: AHPkr
    * **Mobile**: +82-10-2142-2610
    """)
    
    if st.button("← Back to AHP Analysis Tool", use_container_width=True, key="btn_back_to_main_bottom"):
        st.session_state.page = "main"
        st.rerun()
    st.stop()

# 메인 헤더 영역
try:
    # 성능 최적화를 위해 메인 화면에서는 구글 시트 대신 로컬 DB의 방문 로그 수만 즉시 집계합니다.
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM visit_logs")
    total_visits = c.fetchone()[0]
    conn.close()
except Exception:
    total_visits = 0

col_main_title, col_settings_title = st.columns([3.0, 1.1], gap="large")
with col_main_title:
    st.title(_("AHP 의사결정 분석 솔루션", "AHP Decision Analysis Solution"))

with col_settings_title:
    visitor_label = _("누적 방문자", "Total Visitors")
    visitor_unit = _("명", " visitors")
    
    import urllib.parse
    current_params = dict(st.query_params)
    ko_params = current_params.copy()
    ko_params['lang'] = 'ko'
    ko_url = "?" + urllib.parse.urlencode(ko_params, doseq=True)
    
    en_params = current_params.copy()
    en_params['lang'] = 'en'
    en_url = "?" + urllib.parse.urlencode(en_params, doseq=True)
    
    cur_lang = st.session_state.get('lang', 'ko')
    lang_ko_color = "#0369a1" if cur_lang == 'ko' else "#9cb4cc"
    lang_ko_weight = "bold" if cur_lang == 'ko' else "normal"
    lang_en_color = "#0369a1" if cur_lang == 'en' else "#9cb4cc"
    lang_en_weight = "bold" if cur_lang == 'en' else "normal"
    
    counter_html = f"""
    <div style="text-align: right; margin-top: 32px; display: flex; justify-content: flex-end; align-items: center; gap: 15px;">
        <span style="font-size: 0.85rem;">
            <a href="{ko_url}" target="_self" style="text-decoration: none; color: {lang_ko_color}; font-weight: {lang_ko_weight};">한국어</a>
            <span style="color: #ccc; margin: 0 4px;">|</span>
            <a href="{en_url}" target="_self" style="text-decoration: none; color: {lang_en_color}; font-weight: {lang_en_weight};">English</a>
        </span>
        <span style="font-size: 0.85rem; color: #0369a1; font-weight: bold;">
            {visitor_label} : {total_visits:,}{visitor_unit}
        </span>
    </div>
    """
    st.markdown(counter_html, unsafe_allow_html=True)

col_main, col_settings = st.columns([3.0, 1.1], gap="large")
@st.dialog(_("알림", "Notice"))
def show_warning_dialog():
    st.warning(_("⚠️ 분석 후 확인 가능합니다. (데이터를 먼저 업로드하세요)", "⚠️ Available after analysis. (Please upload data first)"))

# ---------- CR Distortion Verification Dialog ----------
@st.dialog(_("🔍 CR 보정 결과 왜곡 검증", "🔍 CR Consistency Distortion Verification"), width="large")
def show_cr_distortion_dialog():

    from cr_analysis import run_analysis, matrix_to_heatmap_img
        
    st.info(_("📊 업로드된 메인 기준 데이터(응답자 전체 기하평균 행렬)를 바탕으로 검증을 수행합니다.", "📊 Performing verification based on the uploaded Main Criteria data (geometric mean matrix of all respondents)."))
    original_matrix = st.session_state.uploaded_matrix

    # Determine selected CR option
    option = st.session_state.get('cr_threshold_label', '0.1')
    if option in ["보정 하지 않음", "Do Not Correct"]:
        corrected_matrix = original_matrix.copy()
        option_name = _("보정 안 함", "Do Not Correct")
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
        st.subheader(_(" 검증 결과", " Verification Results"))
        st.dataframe(pd.DataFrame([metrics]), use_container_width=True)

        # Heatmaps side by side
        orig_img = matrix_to_heatmap_img(original_matrix, _("원본 행렬", "Original Matrix"))
        corr_img = matrix_to_heatmap_img(corrected_matrix, option_name)
        hm1, hm2 = st.columns(2)
        with hm1:
            st.image(f"data:image/png;base64,{orig_img}", caption=_("원본 행렬", "Original Matrix"), use_container_width=True)
        with hm2:
            st.image(f"data:image/png;base64,{corr_img}", caption=_("보정 행렬", "Corrected Matrix"), use_container_width=True)

    with left_col:
        st.subheader(_(" 검증 방법", " Verification Method"))
        st.markdown(_(
            f"""
본 검증은 CR(일관성 비율) 보정 과정에서 **원본 응답 데이터가 얼마나 변형되었는지**를 정량적으로 측정합니다.

**검증 절차:**
1. **원본 행렬 확보** — 설문 응답자의 쌍대비교 판단 행렬을 그대로 사용합니다.
2. **보정 행렬 생성** — 선택된 CR 임계값(`{option_name}`)에 따라 반복 수렴 조정법(Iterative Adjustment)으로 보정된 행렬을 생성합니다.
3. **차이 분석** — 원본과 보정 행렬 간 4가지 수리적 지표를 계산합니다:
   - **유클리드 거리**: 행렬 원소 간 직선 거리
   - **맨해튼 거리**: 행렬 원소 간 절대 차이의 합
   - **코사인 유사도**: 두 행렬 벡터의 방향 일치도
   - **왜곡 점수**: 위 지표들을 종합한 왜곡 수준 지수
4. **종합 판정** — 왜곡 점수를 기준으로 보정의 신뢰성을 평가합니다.

> 💡 왜곡 점수가 낮을수록 보정이 원본 응답의 경향성을 잘 보존했음을 의미합니다.

---
""",
            f"""
This verification quantitatively measures **how much the original response data was altered** during the CR (Consistency Ratio) correction process.

**Verification Procedure:**
1. **Obtain Original Matrix** — Use the respondent's raw pairwise comparison judgment matrix as-is.
2. **Generate Corrected Matrix** — Apply the Iterative Adjustment method based on the selected CR threshold (`{option_name}`) to produce a corrected matrix.
3. **Difference Analysis** — Calculate 4 mathematical metrics between the original and corrected matrices:
   - **Euclidean Distance**: Straight-line distance between matrix elements
   - **Manhattan Distance**: Sum of absolute element-wise differences
   - **Cosine Similarity**: Directional alignment of the two matrix vectors
   - **Distortion Score**: Composite index summarizing overall distortion
4. **Overall Verdict** — Evaluate the reliability of the correction based on the Distortion Score.

> 💡 A lower Distortion Score means the correction better preserved the original response patterns.

---
"""))

        st.subheader(_(" 결과 해석", " Interpretation"))

        # Extract metric values
        euc = metrics.get("euclidean", 0)
        man = metrics.get("manhattan", 0)
        cos = metrics.get("cosine_similarity", 1)
        dist = metrics.get("distortion_score", 0)

        st.markdown(_( 
            f"""
**1. 유클리드 거리 (Euclidean Distance): `{euc:.6f}`**  
원본 행렬과 보정 행렬 사이의 직선 거리입니다.  
값이 **0에 가까울수록** 보정이 원본을 거의 변형하지 않았음을 의미합니다.

**2. 맨해튼 거리 (Manhattan Distance): `{man:.6f}`**  
각 원소별 차이의 절대값 합입니다.  
유클리드 거리와 함께 보정의 **전체적인 변동 크기**를 나타냅니다.

**3. 코사인 유사도 (Cosine Similarity): `{cos:.6f}`**  
두 행렬 벡터 간의 방향 유사도입니다.  
**1.0에 가까울수록** 보정 전후 응답 패턴이 동일한 방향을 유지하고 있습니다.

**4. 왜곡 점수 (Distortion Score): `{dist:.6f}`**  
종합적인 왜곡 수준을 나타내는 지표입니다.

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
            verdict_icon = "✅"
            verdict = _("왜곡 수준: **매우 낮음** — 보정이 원본 응답을 거의 변형하지 않았습니다. 신뢰할 수 있는 결과입니다.",
                        "Distortion Level: **Very Low** — The correction barely altered the original responses. The result is reliable.")
        elif dist < 0.05:
            verdict_icon = "🟡"
            verdict = _("왜곡 수준: **낮음** — 경미한 조정이 있었으나 원본 경향성이 잘 보존되었습니다.",
                        "Distortion Level: **Low** — Minor adjustments were made, but the original trends are well preserved.")
        elif dist < 0.15:
            verdict_icon = "🟠"
            verdict = _("왜곡 수준: **보통** — 일부 변형이 발생했습니다. 결과 해석에 주의가 필요합니다.",
                        "Distortion Level: **Moderate** — Some distortion occurred. Interpret results with caution.")
        else:
            verdict_icon = "🔴"
            verdict = _("왜곡 수준: **높음** — 보정 과정에서 상당한 변형이 발생했습니다. CR 임계값을 조정하거나 원본 데이터를 재검토하세요.",
                        "Distortion Level: **High** — Significant distortion occurred during correction. Consider adjusting the CR threshold or reviewing the original data.")

        st.markdown(f"### {verdict_icon} {_('종합 판정', 'Overall Verdict')}")
        st.info(verdict)


with col_settings:
    if st.session_state.get('admin_mode', False) and st.session_state.get('user_role') == 'admin':
        pass
    else:
        with st.container(border=True):
            st.markdown(f'<h4 style="color:black; font-family:Arial, sans-serif; font-weight:bold; margin-top:0; margin-bottom:15px; font-size:1.1rem;">{_("AHP 분석 설정", "Analysis Settings")}</h4>', unsafe_allow_html=True)
            ahp_method_label = st.radio(_("분석 기법", "Analysis Method"), (_('일반 AHP (Traditional AHP)', 'Traditional AHP'), _('퍼지 AHP (Fuzzy AHP)', 'Fuzzy AHP')), index=0)
            ahp_method = 'traditional' if '일반' in ahp_method_label or 'Traditional' in ahp_method_label else 'fuzzy'
            if ahp_method == 'fuzzy':
                tier = get_current_tier()
                if tier != 'Pro':
                    st.error(_("🔒 퍼지 AHP는 Pro 요금제 전용 기능입니다.", "🔒 Fuzzy AHP is exclusive to Pro Tier."))
                    st.warning(_("현재 무료 및 일반 회원 등급에서는 일반 AHP 결과만 분석 및 제공됩니다. 퍼지 AHP 분석을 이용하시려면 Pro 등급으로 업그레이드해주시기 바랍니다.", 
                                 "In your current tier, only Traditional AHP results are analyzed and provided. To use Fuzzy AHP, please upgrade to the Pro Tier."))
                    ahp_method = 'traditional'
            mean_method_label = st.radio(_("평균 산출 방식", "Aggregation Method"), (_('기하평균 (Geometric)', 'Geometric Mean'), _('산술평균 (Arithmetic)', 'Arithmetic Mean')), index=0)
            mean_method = 'geometric' if '기하' in mean_method_label or 'Geometric' in mean_method_label else 'arithmetic'
            cr_threshold_label = st.selectbox(
                _("일관성 비율(CR) 임계값", "Consistency Ratio (CR) Threshold"), 
                [_("0.1", "0.1"), _("0.15", "0.15"), _("0.2", "0.2"), _("보정 하지 않음", "Do Not Correct")], 
                index=0,
                key="cr_threshold_label",
                help=_(
                    "임계값 설정(0.1, 0.15 또는 0.2)은 일관성 비율(CR)을 해당 수치로 정확하게 일치시키는 것이 아니라, 해당 임계값 이하로 만드는 것을 의미합니다. 이미 임계값 이하인 데이터는 보정하지 않으며, 이를 통해 원본 응답이 과도하게 왜곡되는 것을 방지합니다.",
                    "The threshold setting (0.1, 0.15 or 0.2) does not force the consistency ratio (CR) to equal that value. Instead, it adjusts the CR to be less than or equal to the threshold. If a matrix is already within the threshold, no correction is applied, preventing excessive distortion of the original responses."
                )
            )
            if "보정 하지 않음" in cr_threshold_label or "Do Not Correct" in cr_threshold_label:
                cr_threshold = 999.0
                learning_rate = 0.0
            else:
                cr_threshold = float(cr_threshold_label)
            if "보정 하지 않음" in cr_threshold_label or "Do Not Correct" in cr_threshold_label:
                max_iter_val = 0
                st.number_input(_("최대 보정 반복 횟수", "Max Correction Iterations"), min_value=0, max_value=500, value=0, step=50, disabled=True, key="max_iter_disabled")
            else:
                max_iter_val = st.number_input(_("최대 보정 반복 횟수", "Max Correction Iterations"), min_value=10, max_value=500, value=500, step=50, key="max_iter_enabled")
        
            if "보정 하지 않음" in cr_threshold_label or "Do Not Correct" in cr_threshold_label:
                st.slider(_("보정 강도 (Learning Rate)", "Correction Intensity (Learning Rate)"), min_value=0.0, max_value=0.9, value=0.0, step=0.1, disabled=True, key="learning_rate_disabled")
            else:
                learning_rate = st.slider(_("보정 강도 (Learning Rate)", "Correction Intensity (Learning Rate)"), min_value=0.1, max_value=0.9, value=0.6, step=0.1, key="learning_rate_enabled")


        # 1. CR 보정 결과 왜곡 검증
        with st.expander(_("🔍 CR 보정 결과 왜곡 검증", "🔍 CR Consistency Distortion Verification"), expanded=False):
            if st.button(_("▶ 검증 실행", "▶ Run Verification"), use_container_width=True, key="btn_cr_verify"):
                if "uploaded_matrix" not in st.session_state:
                    show_warning_dialog()
                else:
                    show_cr_distortion_dialog()

        # 2. 일관성 보정 기준
        with st.expander(_("ℹ️ 일관성 보정 기준", "ℹ️ Consistency Correction Standard"), expanded=False):
            st.markdown(_(r"""
            **보정 방법: 반복 수렴 조정법(Iterative Adjustment)**
            가중치 산출 알고리즘(Saaty)에 의해 판단 행렬이 비일관적(CR > 임계값)인 경우, 수학적으로 일관된 행렬과 원본 행렬을 일정 비율로 혼합하여 반복적으로 가중치를 미세 조정한 결과를 제시합니다.
        
            **현재 방법의 특징:**
            1. **최소 판단 왜곡**: 원본 설문 응답의 경향성을 보존하면서 수학적 일관성만을 확보합니다.
            2. **자동 수렴**: 설정된 반복 횟수 내에서 CR 값을 임계값 이하로 자동 개선합니다. ($New = (1-\alpha) \times Old + \alpha \times Ideal$)
            3. **과도한 보정 방지**: 임계값 설정(0.1, 0.15 또는 0.2)은 CR 값을 정확히 맞추는 것이 아니라 임계값 '이하'로 만드는 것을 목표로 합니다. 이미 임계값 이하인 응답은 보정을 수행하지 않아 원본 판단을 최대한 보존합니다.
        
            """, r"""
            **Correction Method: Iterative Adjustment**
            If the judgment matrix is inconsistent (CR > threshold) based on Saaty's weight algorithm, it repeatedly adjusts the weights by mixing the original matrix with a mathematically consistent matrix.
        
            **Key Features:**
            1. **Minimal Distortion of Judgments**: Preserves the trends of the original survey responses while securing mathematical consistency.
            2. **Automatic Convergence**: Automatically improves the CR value to be below the threshold within the maximum number of iterations. ($New = (1-\alpha) \times Old + \alpha \times Ideal$)
            3. **Prevention of Excessive Correction**: The threshold setting (0.1, 0.15 or 0.2) targets bringing the CR 'below or equal to' the threshold, rather than matching it exactly. Responses already below the threshold are left uncorrected to preserve the original judgments as much as possible.
        
            """))

        # 3. 이용자 가이드
        with st.expander(_("📖 이용자 가이드", "📖 User Guide"), expanded=False):
            st.markdown(_("AHP 마스터 서비스 사용 설명서 및 가이드 링크입니다.", "Link to the AHP Master user manual and guide."))
            if st.session_state.get('lang', 'ko') == 'en':
                if st.button("Read English User Guide", use_container_width=True, key="btn_read_guide"):
                    st.session_state.page = "guide"
                    st.rerun()
            else:
                st.link_button("이용자 가이드 바로가기", "https://morison.tistory.com/103", use_container_width=True)

        with st.expander(_("🎓 학술 논문 및 연구 보고서 기재 방법 예시", "🎓 Example of citation in academic papers/reports"), expanded=False):
            st.info(_("AHP 분석 결과를 학위 논문이나 연구 보고서에 기술할 때 아래 예시문을 참고하여 인용 및 서술하실 수 있습니다.",
                      "When describing AHP analysis results in your thesis or research report, you can refer to and cite the example below."))
            st.markdown(_("""
            > **[논문 기재 예시문]**
            > 
            > "본 연구에서 수집된 설문 데이터는 웹 기반 AHP 전용 분석 솔루션인 'AHP 마스터'를 활용하여 분석을 수행하였다. Saaty(1980)의 계층분석과정에 따라 쌍대비교 행렬을 구성하여 국지적 가중치와 종합 가중치(Global Weight)를 산출하였으며, 일관성 비율(CR)이 0.1 미만이 되도록 시스템의 보정 기능을 거쳐 결과의 타당성을 확보하였다."
            """,
            """
            > **[Example of Paper Citation]**
            > 
            > "The survey data collected in this study was analyzed using 'AHP Master', a web-based dedicated AHP analysis solution. Pairwise comparison matrices were constructed in accordance with Saaty's (1980) Analytic Hierarchy Process to calculate local and global weights, and the validity of the results was secured through the system's consistency ratio (CR) adjustment function to ensure CR was below 0.1."
            """))



with col_main:
                
    
    if st.session_state.get('admin_mode', False) and st.session_state.user_role == 'admin':
        # 세션 스테이트 기반 성공 메시지 잔존 출력
        if "sync_success_msg" in st.session_state:
            st.success(st.session_state["sync_success_msg"])
            del st.session_state["sync_success_msg"]
    
        st.subheader(_(" 가입자 현황 및 관리", " Registered Users & Admin Control"))
        
        col_sync1, col_sync2 = st.columns([2, 8])
        with col_sync1:
            if st.button("🔄 구글 시트와 동기화"):
                with st.spinner("구글 시트 데이터 불러오는 중..."):
                    # 캐시 수동 비우기
                    get_cached_visit_logs.clear()
                    added_count = sync_db_from_sheets()
                if added_count >= 0:
                    st.session_state["sync_success_msg"] = f"🎉 동기화 완료! (보정 및 복구된 데이터: {added_count}건)"
                    st.rerun()
                else:
                    st.error("동기화 중 오류가 발생했습니다. 화면상의 에러 메시지를 확인해 주세요.")
        
        try:
            # [최적화] 구글 시트 API 분당 호출 제한(429)을 피하기 위해 5분 캐시 처리된 함수를 사용합니다.
            visit_data_gs = get_cached_visit_logs(st.secrets["SPREADSHEET_ID"])
            if not visit_data_gs:
                try:
                    conn = sqlite3.connect('users.db')
                    df_local = pd.read_sql_query("SELECT ip_address as IP, visit_date as Date FROM visit_logs", conn)
                    conn.close()
                    if not df_local.empty:
                        # 지도 시각화 등에 필요한 컬럼 빈값 보정
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
    
                st.write("#### 🗺️ 접속자 실시간 위치 분포")
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
                            st.info("유효한 좌표 데이터가 없습니다.")
                    else:
                        st.info("지도에 표시할 위치 정보 데이터가 아직 수집되지 않았습니다.")
                else:
                    st.info("위치 정보 컬럼이 존재하지 않습니다.")
            else:
                total_visits = 0
                daily_df_counts = pd.DataFrame()
    
            st.write(f"**누적 방문자:** {total_visits:,}명")
            st.write("#### 📅 일별 방문자 현황 (날짜별 합산)")
            if not daily_df_counts.empty:
                fig_visit = px.bar(daily_df_counts, x='Date_Only', y='count', text='count',
                                    labels={'Date_Only': '날짜', 'count': '방문자 수'})
                fig_visit.update_traces(textposition='outside')
                fig_visit.update_layout(xaxis_title="날짜", yaxis_title="방문자 수", showlegend=False, xaxis={'type': 'category'})
                st.plotly_chart(fig_visit, use_container_width=True)
            else:
                st.info("방문 기록이 없습니다.")
        except Exception as e:
            st.error(f"통계 오류: {e}")
        st.divider()
        
        # 배포 통계 집계 및 시각화
        st.write("---")
        st.write(_("### 📊 설문지 배포 통계", "### 📊 Survey Distribution Statistics"))
        users_df = get_all_users()
        
        # 컬럼 존재 확인 및 결측치 보정
        if 'survey_count' not in users_df.columns:
            users_df['survey_count'] = 0
        if 'last_survey_link' not in users_df.columns:
            users_df['last_survey_link'] = ""
            
        users_df['survey_count'] = pd.to_numeric(users_df['survey_count'].fillna(0)).astype(int)
        
        # 1. 요약 통계
        total_dist_surveys = users_df['survey_count'].sum()
        active_users_count = (users_df['survey_count'] > 0).sum()
        total_registered_users = len(users_df)
        
        col_stat1, col_stat2, col_stat3 = st.columns(3)
        with col_stat1:
            st.metric(_("총 설문 배포 건수", "Total Distributed Surveys"), f"{total_dist_surveys}" + _("건", ""))
        with col_stat2:
            st.metric(_("설문 배포 경험 회원 수", "Members with Distribution Experience"), f"{active_users_count}" + _("명", ""))
        with col_stat3:
            st.metric(_("총 가입 회원 수", "Total Registered Members"), f"{total_registered_users}" + _("명", ""))
            
        # 2. 사용자별 배포 횟수 차트
        active_users_df = users_df[users_df['survey_count'] > 0].copy()
        if not active_users_df.empty:
            active_users_df = active_users_df.sort_values(by='survey_count', ascending=False)
            fig_dist = px.bar(active_users_df, x='id', y='survey_count', text='survey_count',
                              labels={'id': '회원 ID', 'survey_count': '배포 건수'},
                              title="회원별 설문지 배포 현황 (1건 이상 배포 회원)")
            fig_dist.update_traces(textposition='outside')
            fig_dist.update_layout(xaxis_title="회원 ID", yaxis_title="배포 건수")
            st.plotly_chart(fig_dist, use_container_width=True)
        else:
            st.info(_("아직 설문을 배포한 사용자가 없습니다.", "No users have distributed a survey yet."))
            
        st.write("---")
        st.write(_("### 👥 가입자 현황 및 최종 배포 링크", "### 👥 Subscriber Status and Latest Distribution Links"))
        
        # 컬럼 순서 및 구성 재조정하여 데이터프레임으로 출력
        display_df = users_df[['id', 'role', 'signup_date', 'pw', 'survey_count', 'last_survey_link', 'expiry_date', 'agree_info']].copy()
        st.dataframe(
            display_df,
            column_config={
                "id": "회원 ID",
                "role": "권한",
                "signup_date": "가입일",
                "pw": "비밀번호",
                "survey_count": "배포 횟수",
                "last_survey_link": st.column_config.LinkColumn("최종 배포 설문지 링크", display_text="설문지 바로가기"),
                "expiry_date": "만료일",
                "agree_info": "동의여부"
            },
            hide_index=True,
            use_container_width=True
        )
    
        with st.expander("회원 정보 수정 (비밀번호 초기화 포함)"):
            edit_id = st.selectbox("수정할 회원 ID", users_df['id'].unique())
            selected_user = users_df[users_df['id'] == edit_id].iloc[0]
            new_role_val = st.selectbox("권한 변경", ['temp', 'official', 'admin'], 
                                    index=['temp', 'official', 'admin'].index(selected_user['role']))
            
            if new_role_val == 'official' and selected_user['role'] != 'official':
                suggested_date = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).date() + relativedelta(months=2)
                new_expiry_val = st.text_input("만료일 설정 (YYYY-MM-DD) - 2개월 기한 자동 제안됨", value=str(suggested_date))
            else:
                new_expiry_val = st.text_input("만료일 변경 (YYYY-MM-DD)", value=selected_user['expiry_date'])
                
            new_pw_edit = st.text_input("새 비밀번호 (입력 시 변경됨)", type="password", placeholder="변경하지 않으려면 비워두세요")
            
            col_admin_act1, col_admin_act2 = st.columns(2)
            with col_admin_act1:
                if st.button("정보 수정 적용", use_container_width=True):
                    update_user_full_info(edit_id, new_pw_edit, new_role_val, new_expiry_val)
                    if new_role_val == 'official' and selected_user['role'] != 'official':
                        send_approval_email(edit_id)
                    st.success(f"{edit_id} 회원의 정보가 수정되었습니다.")
                    st.rerun()
            with col_admin_act2:
                if st.button("🔑 이 계정으로 로그인", use_container_width=True, type="secondary", help="비밀번호 없이 이 사용자의 계정으로 세션을 즉시 전환합니다."):
                    st.session_state.user_id = edit_id
                    st.session_state.user_role = selected_user['role']
                    st.session_state.expiry_date = selected_user['expiry_date']
                    st.session_state.admin_mode = False  # 일반 사용자 시점으로 전환
                    st.toast(f"🔑 {edit_id} 계정으로 로그인했습니다.")
                    st.rerun()
        
        with st.expander("회원 삭제"):
            del_id = st.selectbox("삭제할 회원 ID 선택", users_df['id'].unique(), key='del_user_select')
            if st.button("선택한 회원 삭제"):
                if del_id == st.session_state.user_id:
                    st.error("본인은 삭제할 수 없습니다.")
                else:
                    delete_user(del_id)
                    st.success("삭제 완료")
                    st.rerun()
        st.divider()
    
    # -------------------------------------------------------------------------
    # [수정] 관리자용 상단 탭 연동 (Tab 1: 분석, Tab 2: 설문지 제작)
    # 일반 사용자에게는 Tab 1 화면(분석)만 직접 단일 노출시킵니다.
    # -------------------------------------------------------------------------
    if st.session_state.get('admin_mode', False) and st.session_state.get('user_role') == 'admin':
        st.stop()
    main_tab_consulting, main_tab1, main_tab_coding, main_tab2, main_tab3, main_tab_pricing, main_tab_signup = st.tabs([
        _("분석 문의 및 컨설팅", "Analysis Inquiry & Consulting"),
        _("AHP 분석 도구", "AHP Analysis Tool"), 
        _("AHP 코딩 엑셀 양식", "AHP Coding Excel Form"), 
        _("온라인 AHP 설문/배포(:red[**무료**])", "Online AHP Survey/Deployment (:red[**Free**])"), 
        _("실시간 응답 현황", "Live Response Status"),
        _("서비스 요금", "Service Pricing"),
        _("회원가입", "Sign Up")
    ], default=_("AHP 분석 도구", "AHP Analysis Tool"))
        
    with main_tab1:
        # 빠른 시작 섹션을 AHP 분석도구 탭 내부 최상단에 배치

        st.header(_("빠른 시작 (도시재생 사업 모델)", "Quick Start (Urban Regeneration Project Model)"))
        st.info(_("Saaty(1980)의 Analytic Hierarchy Process (AHP) 분석 및 일관성 자동 보정 도구입니다.  \n일반 및 :blue[**퍼지 AHP**] 분석을 모두 지원하며, 엑셀 업로드만으로 개인별 가중치 산출, 일관성(CR) 자동 보정, 그룹 집계 결과를 제공합니다.",
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
    
        # 3계층 샘플 데이터: 권한에 따라 분기
        # - 정식/관리자: Mock_3Tier_Full.xlsx (100행, 실제 분석 가능)
        # - 무료/비로그인: create_sample_excel_v3() (5행, 5행 제한 통과)
        _role_now = st.session_state.get('user_role', None)
        _is_full_user = (_role_now in ('admin', 'official'))
        if _is_full_user:
            try:
                with open("Mock_3Tier_Full.xlsx", "rb") as f:
                    sample_excel_v3 = f.read()
                _v3_label = _("📂 3계층 샘플 데이터", "📂 3-Tier Sample Data")
                _v3_filename = "Mock_3Tier_Full.xlsx"
            except Exception:
                sample_excel_v3 = create_sample_excel_v3()
                _v3_label = _("📂 3계층 샘플 데이터", "📂 3-Tier Sample Data")
                _v3_filename = _("AHP_3Tier_Sample.xlsx", "AHP_3Tier_Sample.xlsx")
        else:
            sample_excel_v3 = create_sample_excel_v3()   # 5행 — 무료 5행 제한 통과
            _v3_label = _("📂 3계층 샘플 데이터", "📂 3-Tier Sample Data")
            _v3_filename = _("AHP_3Tier_Sample.xlsx", "AHP_3Tier_Sample.xlsx")
            
        # 모든 사용자에게 2계층·3계층 샘플 데이터 + 결과 예시 버튼 4개 표시
        col_btn1, col_btn2, col_btn3, col_btn4 = st.columns(4)
        with col_btn1:
            st.download_button(
                label=_("📂 2계층 샘플 데이터", "📂 2-Tier Sample Data"),
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
                label=_("📄 일반 AHP 분석 결과(예시)", "📄 Traditional AHP Report (Example)"),
                data=tahp_data if tahp_data else b"",
                file_name=_("E_TAHP_Result.xlsx", "E_TAHP_Result.xlsx") if is_en else _("K_TAHP_Result.xlsx", "K_TAHP_Result.xlsx"),
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                disabled=(not tahp_data)
            )
        with col_btn4:
            st.download_button(
                label=_("📄 퍼지 AHP 분석 결과(예시)", "📄 Fuzzy AHP Report (Example)"),
                data=fahp_data if fahp_data else b"",
                file_name=_("E_FAHP_Result.xlsx", "E_FAHP_Result.xlsx") if is_en else _("K_FAHP_Result.xlsx", "K_FAHP_Result.xlsx"),
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                disabled=(not fahp_data)
            )
        
        st.subheader(_("1. 데이터 업로드 및 분석", "1. Data Upload & Analysis"))
        
        if st.session_state.get('user_role') == 'admin':
            st.info(_("💡 **혼합 계층(Mixed-Tier) 엑셀 분석 안내**: 3계층 코딩 엑셀 양식을 업로드할 때, 특정 항목에 대한 소분류 평가 시트가 없거나 응답이 비워져 있더라도 시스템이 해당 항목을 자동으로 2계층 가중치로 간주하여 에러 없이 분석을 수행합니다.", "💡 **Mixed-Tier Excel Analysis Guide**: When uploading a 3-tier Excel template, if there are no sub-sub-criteria evaluation sheets for specific items or the responses are blank, the system automatically considers them as 2-tier weights and performs the analysis without errors."))

        # 데이터 소스 선택 추가
        data_source = st.radio(
            _("분석 데이터 소스 선택", "Select Analysis Data Source"),
            [_("📂 엑셀 파일 직접 업로드", "Upload Excel File"), _("🌐 배포된 온라인 설문 데이터 연동", "Link Online Survey Data")],
            horizontal=True
        )
    
        # [신규 추가] 인구통계 빈도/비율 분석용 헬퍼 함수
        def generate_demographics_summary(demo_df):
            if demo_df is None or demo_df.empty:
                return None
            
            # 불필요한 시스템용 컬럼 제외
            exclude_keywords = ["id", "type", "사전순위", "답례품", "연락처", "제출시간"]
            target_cols = []
            for col in demo_df.columns:
                col_lower = str(col).lower()
                if not any(ex in col_lower for ex in exclude_keywords):
                    target_cols.append(col)
            
            if not target_cols:
                return None
                
            summary_rows = []
            for col in target_cols:
                counts = demo_df[col].value_counts(dropna=False)
                total = len(demo_df)
                for val, count in counts.items():
                    pct = (count / total) * 100 if total > 0 else 0
                    summary_rows.append({
                        "인구통계 항목 (Demographic Field)": col,
                        "응답 보기 (Value)": str(val) if pd.notna(val) else "미응답(N/A)",
                        "빈도수 (Frequency)": count,
                        "비율 (Percentage, %)": round(pct, 1)
                    })
                    
            if summary_rows:
                return pd.DataFrame(summary_rows)
            return None

        def preprocess_uploaded_df(df):
            # 1. 제출시간/타임스탬프 제거
            drop_cols = [c for c in df.columns if str(c).strip().lower() in ["타임스탬프", "제출시간", "timestamp"]]
            if drop_cols:
                df = df.drop(columns=drop_cols)
            # 다중 인구통계(Type 1, Type 2...)는 유지하여 향후 선택적 분석이 가능하도록 함
            return df
            
        df_main = None
        sub_dfs = {}
        sheet_names = []
        filename_base = "AHP_Analysis"
    
        if data_source == _("📂 엑셀 파일 직접 업로드", "Upload Excel File"):
            uploaded_file = st.file_uploader(_("작성된 엑셀 파일 업로드 (.xlsx)", "Upload completed Excel file (.xlsx)"), type=['xlsx', 'xls'])
            if uploaded_file:
                try:
                    excel_obj = pd.ExcelFile(uploaded_file)
                    sheet_names = excel_obj.sheet_names
                    df_main = pd.read_excel(uploaded_file, sheet_name=sheet_names[0])
                    df_main = preprocess_uploaded_df(df_main)
                    
                    if "Type" not in df_main.columns and len(df_main.columns) > 1:
                        col1 = df_main.columns[1]
                        if "_" not in col1 and col1 not in ["ID", "제출시간"]:
                            df_main.rename(columns={col1: "Type"}, inplace=True)
                            
                    # 3계층 식별 로직 (df_main 컬럼에서 _ 포함된 것으로 대분류 요인 도출)
                    main_criteria_infer = set()
                    for col in df_main.columns:
                        if '_' in col:
                            parts = col.split('_')
                            if len(parts) == 2:
                                main_criteria_infer.add(parts[0])
                                main_criteria_infer.add(parts[1])
                    
                    inferred_sub_sub_dfs = {}
                    ignore_sheets = ["raw_data", "raw_data_dump", "demographic_data", "raw data"]
                    for sn in sheet_names[1:]:
                        # [추가] 온라인 설문 배포 형식 엑셀의 원본/인구통계 데이터 시트 자동 무시 (단, 인구통계는 별도 저장)
                        sn_lower = sn.lower().strip()
                        if sn_lower in ignore_sheets:
                            if "demographic" in sn_lower:
                                st.session_state["demo_df"] = pd.read_excel(uploaded_file, sheet_name=sn)
                                st.session_state["demo_df"] = preprocess_uploaded_df(st.session_state["demo_df"])
                            continue
                            
                        df_sheet = pd.read_excel(uploaded_file, sheet_name=sn)
                        df_sheet = preprocess_uploaded_df(df_sheet)
                        if "Type" not in df_sheet.columns and len(df_sheet.columns) > 1:
                            col1 = df_sheet.columns[1]
                            if "_" not in col1 and col1 not in ["ID", "제출시간"]:
                                df_sheet.rename(columns={col1: "Type"}, inplace=True)
                                
                        # 안전한 시트명(safe_sheet_name)을 위해 앞부분이 일치하는지 확인
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
                    st.error(f"엑셀 파일 로드 실패: {e}")
        else:
            # 배포된 온라인 설문 데이터 연동
            if st.session_state.user_id is None:
                st.warning(_(" 온라인 설문 데이터 연동 분석은 회원 전용 기능입니다. 로그인해 주세요.", " Online survey integration is available for members. Please log in."))
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
                    st.warning(_("배포된 온라인 설문이 없습니다.", "No deployed online surveys found."))
                else:
                    survey_options = {f"{row[1]} ({row[2]})": row[0] for row in admin_surveys}
                
                    default_idx = 0
                    if st.session_state.get("selected_survey_for_analysis") in survey_options.values():
                        default_idx = list(survey_options.values()).index(st.session_state.get("selected_survey_for_analysis"))
                
                    selected_survey_label = st.selectbox(
                        _("분석할 온라인 설문 선택", "Select Online Survey for Analysis"),
                        list(survey_options.keys()),
                        index=default_idx
                    )
                    selected_sheet_id = survey_options[selected_survey_label]
                    filename_base = f"Survey_{selected_sheet_id[:6]}"
                
                    if st.button(_("🔄 구글 시트에서 실시간 응답 가져오기", "🔄 Fetch Live Responses from Google Sheet"), type="primary", use_container_width=True):
                        st.session_state["selected_survey_for_analysis"] = selected_sheet_id
                        from survey_manager import load_survey_metadata, get_survey_gspread_client
                        with st.spinner(_("구글 시트에서 설문 데이터 및 구조를 가져오는 중...", "Fetching survey structure and responses...")):
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
                                        
                                        if "Type" not in raw_df.columns and len(raw_df.columns) > 1:
                                            col1 = raw_df.columns[1]
                                            if "_" not in col1 and col1 not in ["ID", "제출시간"]:
                                                raw_df.rename(columns={col1: "Type"}, inplace=True)
                                                
                                        # [신규] 사용자 등급에 따른 표본 수 제한 (무료 사용자: 최대 5표본)
                                        if st.session_state.get('user_role') == 'free' and len(raw_df) > 5:
                                            raw_df = raw_df.head(5)
                                            st.warning(_("⚠️ 무료 사용자는 온라인 설문 연동 시 최대 5표본까지만 분석할 수 있습니다. 처음 접수된 5명(행)의 응답만 분석에 사용됩니다.", "⚠️ Free users can only analyze up to 5 samples. Only the first 5 responses will be analyzed."))
                                    
                                        for col in raw_df.columns:
                                            if col not in ["ID", "Type", "제출시간", "답례품_연락처"]:
                                                raw_df[col] = pd.to_numeric(raw_df[col], errors='coerce')
                                            
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
                                            
                                        # [신규] 3계층 모델인 경우 소분류(sub_subs) 데이터프레임 파싱
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
                                        st.success(_(f"✅ 구글 시트에서 총 {len(raw_df)}건의 응답 데이터를 성공적으로 가져왔습니다!", f"✅ Successfully fetched {len(raw_df)} responses!"))
                                    else:
                                        st.warning(_("가져올 설문 응답 데이터가 시트에 존재하지 않습니다 (헤더만 존재).", "No survey responses found in the sheet."))
                                except Exception as g_err:
                                    st.error(f"구글 시트 로드 실패: {g_err}")
                            else:
                                st.error(_("설문 메타데이터 또는 구글 API 클라이언트를 로드할 수 없습니다.", "Failed to load survey metadata or Google client."))
                
                    if "ahp_df_main" in st.session_state:
                        df_main = st.session_state["ahp_df_main"]
                        sub_dfs = st.session_state["ahp_sub_dfs"]
                        sheet_names = st.session_state["ahp_sheet_names"]
                        st.info(_("💡 구글 시트에서 로드된 실시간 데이터 분석 모드입니다. (새 데이터를 가져오려면 위 버튼을 클릭해 주세요)", "💡 Live data analysis mode. Click the button above to refresh data."))

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
                            message = _("⛔ 이용 기간이 만료되었습니다.", "⛔ Your subscription period has expired.")
                else: 
                    rows_ok = True
                    if data_source == _("📂 엑셀 파일 직접 업로드", "Upload Excel File"):
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
                    else: message = _(f"⛔ **무료사용자**는 시트당 최대 5개 표본까지만 분석 가능합니다. (현재: {len(df_main)}개 표본)",
                                     f"⛔ **Free Users** can only analyze up to 5 samples per sheet. (Current: {len(df_main)} samples)")
            
                if permission_granted:
                    tier = get_current_tier()
                    try:
                        if data_source == _("📂 엑셀 파일 직접 업로드", "Upload Excel File"):
                            tier_level = st.session_state.get("inferred_tier_level", 2)
                        else:
                            if 'survey_meta' not in locals():
                                from survey_manager import load_survey_metadata
                                sheet_id_for_meta = st.session_state.get("selected_survey_for_analysis")
                                survey_meta = load_survey_metadata(sheet_id_for_meta) if sheet_id_for_meta else {}
                            tier_level = int(survey_meta.get("Tier_Level", 2)) if survey_meta else 2
                        
                        if tier_level == 3:
                            is_english = (st.session_state.get('lang', 'ko') == 'en')
                            success_v3 = False
                            msg_v3 = ""
                            final_df_v3 = None
                            output_res_v3 = None
                            ui_data_v3 = {}
                            with st.spinner(_("3계층(소분류 포함) AHP 종합 분석 수행 중...", "Performing 3-Tier AHP...")):
                                from ahp_utils_v3 import run_ahp_analysis_v3
                                sub_sub_dfs = st.session_state.get("ahp_sub_sub_dfs", {})
                                
                                # 인구통계 요약본 생성하여 전달
                                demo_summary_df_v3 = None
                                if "demo_df" in st.session_state and st.session_state["demo_df"] is not None:
                                    demo_summary_df_v3 = generate_demographics_summary(st.session_state["demo_df"])
                                    
                                success_v3, msg_v3, final_df_v3, output_res_v3, ui_data_v3 = run_ahp_analysis_v3(
                                    df_main, sub_dfs, sub_sub_dfs, cr_threshold, max_iter_val, learning_rate, mean_method, ahp_method,
                                    process_single_sheet, fuzzy_ahp_analysis, demo_summary_df=demo_summary_df_v3
                                )

                            if not success_v3:
                                st.error(msg_v3)
                                st.stop()
                            
                            if st.session_state.user_role == 'official':
                                if data_source == _("📂 엑셀 파일 직접 업로드", "Upload Excel File") and uploaded_file is not None:
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

                            st.success(_("✅ 3계층 AHP 분석이 성공적으로 완료되었습니다!", "✅ 3-Tier AHP Analysis successfully completed!"))
                            st.markdown(_('<p style="color:red;font-weight:bold;font-size:0.95rem;margin:5px 0 10px;"> 주의: 새로고침하거나 브라우저를 닫으면 결과가 리셋됩니다.  결과 다운로드 탭에서 반드시 저장하세요.</p>',
                                          '<p style="color:red;font-weight:bold;font-size:0.95rem;margin:5px 0 10px;">⚠️ Warning: Results reset on refresh. Download via 📑 Download Results tab.</p>'), unsafe_allow_html=True)

                            # --- 3계층 전용 5개 탭 UI ---
                            v3_unique_groups = ui_data_v3.get("unique_groups", [])
                            v3_comparison_df  = ui_data_v3.get("comparison_df", pd.DataFrame())
                            v3_anova_df       = ui_data_v3.get("anova_df", pd.DataFrame())
                            v3_group_full_dfs = ui_data_v3.get("group_full_dfs", {})
                            v3_indiv_df       = ui_data_v3.get("indiv_df", pd.DataFrame())
                            v3_main_factors   = ui_data_v3.get("main_factors", [])

                            tab3v1, tab3v2, tab3v3, tab3v4, tab3v5 = st.tabs([
                                _("🌐 종합 분석 (Global)", "🌐 Global Comprehensive Analysis"),
                                _("👨\u200d👩\u200d👧\u200d👦 그룹별 분석", "👨\u200d👩\u200d👧\u200d👦 Group Analysis"),
                                _("🧪 통계 검정 (ANOVA)", "🧪 Statistical Test (ANOVA)"),
                                _("📊 시각화 센터", "📊 Visualization Center"),
                                _("📑 결과 다운로드", "📑 Download Results")
                            ])

                            # ─── Tab 1: 종합 분석 ────────────────────────────────────────────
                            with tab3v1:
                                st.subheader(_(" 3계층 종합 중요도 및 순위", " 3-Tier Global Weights & Rankings"))
                                if is_english:
                                    _disp_v3 = final_df_v3.rename(columns={
                                        "대분류": "Main Criteria",    "대분류 가중치": "Main Weight",
                                        "중분류": "Sub-Criteria",     "중분류 가중치": "Sub Weight",
                                        "소분류": "Sub-sub-Criteria", "소분류 가중치": "Sub-sub Weight",
                                        "CR(대분류)": "CR(Main)",     "CI(대분류)": "CI(Main)",
                                        "CR(중분류)": "CR(Sub)",      "CI(중분류)": "CI(Sub)",
                                        "CR(소분류)": "CR(Sub-sub)",  "CI(소분류)": "CI(Sub-sub)"
                                    })
                                else:
                                    _disp_v3 = final_df_v3
                                st.dataframe(_disp_v3.style.format(precision=4), use_container_width=True)

                                st.markdown(_("---\n####  대분류별 소분류 항목 글로벌 가중치",
                                              "---\n#### 📊 Sub-sub-Criteria Global Weights by Main Criteria"))
                                _non_dummy_v3 = final_df_v3[~final_df_v3["소분류"].str.endswith("_단일항목", na=False)].copy()
                                if _non_dummy_v3.empty:
                                    _non_dummy_v3 = final_df_v3.copy()
                                for _mf_v3 in v3_main_factors:
                                    _mf_subset = _non_dummy_v3[_non_dummy_v3["대분류"] == _mf_v3]
                                    if _mf_subset.empty:
                                        continue
                                    _mf_chart = _mf_subset.sort_values("Global Weight", ascending=True).copy()
                                    if is_english:
                                        _mf_chart = _mf_chart.rename(columns={"소분류": "Sub-sub-Criteria"})
                                        _y_col_v3 = "Sub-sub-Criteria"
                                    else:
                                        _y_col_v3 = "소분류"
                                    _fig_v3_bar = px.bar(
                                        _mf_chart, y=_y_col_v3, x="Global Weight",
                                        orientation="h", text_auto=".4f",
                                        title=_(f"[{_mf_v3}] 소분류 항목별 글로벌 가중치", f"[{_mf_v3}] Sub-sub-Criteria Global Weights"),
                                        color_discrete_sequence=["#4F81BD"]
                                    )
                                    _fig_v3_bar.update_layout(height=max(300, len(_mf_chart)*40+80), margin=dict(l=0,r=10,t=40,b=20))
                                    st.plotly_chart(_fig_v3_bar, use_container_width=True)

                            # ─── Tab 2: 그룹별 분석 ──────────────────────────────────────────
                            with tab3v2:
                                st.markdown(_("#### 그룹별 소분류 항목 글로벌 가중치 비교",
                                              "#### Sub-sub-Criteria Global Weight Comparison by Group"))
                                if not v3_comparison_df.empty:
                                    if is_english:
                                        _disp_comp_v3 = v3_comparison_df.copy()
                                        _disp_comp_v3.rename(columns={
                                            "대분류": "Main Criteria", "중분류": "Sub-Criteria", "소분류": "Sub-sub-Criteria",
                                            "종합평균(Overall)": "Overall Avg", "F-값": "F-Value",
                                            "유의성": "Significance", "사후검정(Tukey HSD)": "Post-Hoc (Tukey HSD)"
                                        }, inplace=True)
                                        if "Significance" in _disp_comp_v3.columns:
                                            _disp_comp_v3["Significance"] = _disp_comp_v3["Significance"].map(
                                                {"유의함": "Significant", "유의하지 않음": "Not Significant"}).fillna(_disp_comp_v3["Significance"])
                                    else:
                                        _disp_comp_v3 = v3_comparison_df
                                    st.dataframe(_disp_comp_v3.style.format(precision=4), use_container_width=True)
                                else:
                                    st.info(_("그룹별 비교 데이터가 없습니다.", "No group comparison data available."))

                                if len(v3_unique_groups) >= 2 and v3_group_full_dfs:
                                    st.markdown(_("---\n#### 그룹별 대분류 가중치 비교",
                                                  "---\n#### Main Criteria Weight Comparison by Group"))
                                    _grp_main_rows = []
                                    for _grp_v3 in v3_unique_groups:
                                        if _grp_v3 not in v3_group_full_dfs:
                                            continue
                                        _g_df_v3 = v3_group_full_dfs[_grp_v3]
                                        for _mf_v3b in v3_main_factors:
                                            _mf_sub_b = _g_df_v3[_g_df_v3["대분류"] == _mf_v3b]
                                            if not _mf_sub_b.empty:
                                                _grp_main_rows.append({
                                                    _("그룹","Group"): _grp_v3,
                                                    _("대분류","Main Criteria"): _mf_v3b,
                                                    "Weight": float(_mf_sub_b.iloc[0]["대분류 가중치"])
                                                })
                                    if _grp_main_rows:
                                        _grp_main_chart_df = pd.DataFrame(_grp_main_rows)
                                        _fig_grp_main = px.bar(
                                            _grp_main_chart_df,
                                            x=_("대분류","Main Criteria"), y="Weight",
                                            color=_("그룹","Group"), barmode="group", text_auto=".4f",
                                            title=_("그룹별 대분류 가중치 비교", "Main Criteria Weight Comparison by Group")
                                        )
                                        st.plotly_chart(_fig_grp_main, use_container_width=True)

                            # ─── Tab 3: ANOVA ─────────────────────────────────────────────────
                            with tab3v3:
                                st.markdown(_("#### 집단 간 유의성 분석 (3계층 기준)",
                                              "#### Significance Analysis Between Groups (3-Tier Level)"))
                                if not v3_anova_df.empty:
                                    if is_english:
                                        _disp_anova_v3 = v3_anova_df.copy()
                                        _disp_anova_v3.rename(columns={
                                            "요인": "Factor/Criteria", "F-값": "F-Value",
                                            "유의성": "Significance", "사후검정(Tukey HSD)": "Post-Hoc (Tukey HSD)"
                                        }, inplace=True)
                                        if "Significance" in _disp_anova_v3.columns:
                                            _disp_anova_v3["Significance"] = _disp_anova_v3["Significance"].map(
                                                {"유의함": "Significant", "유의하지 않음": "Not Significant"}).fillna(_disp_anova_v3["Significance"])
                                        def _translate_ph_v3(v):
                                            if not isinstance(v, str): return v
                                            v = v.replace("전문가","Expert").replace("일반","General").replace("공무원","Public Official")
                                            v = v.replace(" 차이 있음"," (Diff exists)")
                                            v = v.replace("집단 간 구체적 차이 발견 못함","No significant pairwise difference found")
                                            v = v.replace("계산 오류","Calculation Error")
                                            return v
                                        if "Post-Hoc (Tukey HSD)" in _disp_anova_v3.columns:
                                            _disp_anova_v3["Post-Hoc (Tukey HSD)"] = _disp_anova_v3["Post-Hoc (Tukey HSD)"].apply(_translate_ph_v3)
                                    else:
                                        _disp_anova_v3 = v3_anova_df
                                    st.dataframe(_disp_anova_v3.style.format(precision=5), use_container_width=True)

                                    _sig_col_v3 = "Significance" if is_english else "유의성"
                                    _sig_val_v3 = "Significant" if is_english else "유의함"
                                    if _sig_col_v3 in _disp_anova_v3.columns:
                                        _sig_items_v3 = _disp_anova_v3[_disp_anova_v3[_sig_col_v3] == _sig_val_v3]
                                        if not _sig_items_v3.empty:
                                            _fcol_v3 = "Factor/Criteria" if is_english else "요인"
                                            _snames = ", ".join(_sig_items_v3[_fcol_v3].tolist())
                                            st.success(_(f"✅ 유의한 차이 발견 항목: {_snames}", f"✅ Statistically significant factors: {_snames}"))
                                        else:
                                            st.info(_("모든 항목에서 그룹 간 유의한 차이가 없습니다.", "No statistically significant group differences found."))
                                else:
                                    st.info(_("통계 검정을 위해 2개 이상의 그룹 데이터가 필요합니다.",
                                              "At least 2 group datasets are required for ANOVA."))

                            # ─── Tab 4: 시각화 센터 ──────────────────────────────────────────
                            with tab3v4:
                                st.markdown(_("####  3계층 AHP 시각화 센터", "####  3-Tier AHP Visualization Center"))

                                st.markdown(_("**① 글로벌 가중치 순위 버블 차트 (버블 크기 = 중분류 가중치, 색 = 대분류)**",
                                              "**① Global Weight Bubble Chart (bubble size = Sub weight, color = Main Criteria)**"))
                                _nd_v3 = final_df_v3[~final_df_v3["소분류"].str.endswith("_단일항목", na=False)].copy()
                                if _nd_v3.empty:
                                    _nd_v3 = final_df_v3.copy()
                                    _item_col_bub = "중분류"
                                else:
                                    _item_col_bub = "소분류"
                                _bubble_df = _nd_v3.copy()
                                if "Global Rank" not in _bubble_df.columns:
                                    _bubble_df["Global Rank"] = _bubble_df["Global Weight"].rank(ascending=False, method="min").astype(int)
                                # 버블 크기: 중분류 가중치 기반 (최소 크기 보장)
                                _bubble_df["_bubble_size"] = (_bubble_df["중분류 가중치"] * 100).clip(lower=3)
                                if is_english:
                                    _bubble_df_disp = _bubble_df.rename(columns={
                                        "소분류": "Sub-sub-Criteria", "대분류": "Main Criteria",
                                        "중분류": "Sub-Criteria", "중분류 가중치": "Sub Weight"
                                    })
                                    _label_col_bub = "Sub-sub-Criteria" if _item_col_bub == "소분류" else "Sub-Criteria"
                                    _color_bub = "Main Criteria"
                                    _hover_sub_bub = "Sub-Criteria"
                                    _hover_subw_bub = "Sub Weight"
                                else:
                                    _bubble_df_disp = _bubble_df
                                    _label_col_bub = _item_col_bub
                                    _color_bub = "대분류"
                                    _hover_sub_bub = "중분류"
                                    _hover_subw_bub = "중분류 가중치"
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
                                    title=_("소분류 글로벌 가중치 버블 차트 (버블이 클수록 중분류 비중 높음, 위로 갈수록 글로벌 가중치 높음)",
                                            "Sub-sub-Criteria Global Weight Bubble Chart (larger = higher sub weight, higher = higher global weight)"),
                                    color_discrete_sequence=px.colors.qualitative.Set2,
                                    size_max=55
                                )
                                _fig_bub.update_traces(textposition="top center", textfont_size=10)
                                _fig_bub.update_xaxes(
                                    title=_("종합 순위 (1위 = 가장 중요)", "Global Rank (1 = Most Important)"),
                                    dtick=1, autorange="reversed"
                                )
                                _fig_bub.update_yaxes(title=_("글로벌 가중치", "Global Weight"))
                                _fig_bub.update_layout(height=560, legend_title_text=_color_bub)
                                st.plotly_chart(_fig_bub, use_container_width=True)

                                st.markdown(_("**② 계층별 일관성 비율(CR) 분포 — 바이올린 플롯**",
                                              "**② Consistency Ratio (CR) Distribution by Tier — Violin Plot**"))
                                st.caption(_("계층을 선택하면 해당 수준 응답자들의 CR 분포를 표시합니다. 바이올린 폭 = 밀도, 내부 박스 = 중앙값·사분위수, 점 = 개별 응답자",
                                             "Select a tier to view respondent CR distribution. Width = density, box = median/IQR, dots = individual respondents"))

                                _vio_main_df   = ui_data_v3.get("main_results_df", pd.DataFrame())
                                _vio_sub_stor  = ui_data_v3.get("sub_results_storage", {})
                                _vio_ss_stor   = ui_data_v3.get("sub_sub_results_storage", {})
                                _vio_mf_list   = ui_data_v3.get("main_factors", [])

                                _tier_options_ko = ["대분류 (Main)", "중분류 (Sub)", "소분류 (Sub-sub)"]
                                _tier_options_en = ["Main Criteria", "Sub-Criteria", "Sub-sub-Criteria"]
                                _tier_opts = _tier_options_en if is_english else _tier_options_ko
                                _sel_tier = st.selectbox(
                                    _("📂 표시할 계층 선택", "📂 Select Tier to Display"),
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

                                    # ── 선택: 대분류 ─────────────────────────────────
                                    if _sel_tier in [_tier_opts[0]]:
                                        if not _vio_main_df.empty and "Final_CR" in _vio_main_df.columns:
                                            _main_cr = _vio_main_df["Final_CR"].dropna().tolist()
                                            _xlbl = _("대분류", "Main Criteria")
                                            _fig_vio.add_trace(_go_vio.Violin(
                                                y=_main_cr, x=[_xlbl]*len(_main_cr),
                                                name=_xlbl, box_visible=True, meanline_visible=True,
                                                points="all", jitter=0.35, pointpos=0,
                                                line_color=_vio_line_pal[0], fillcolor=_vio_palette[0],
                                                opacity=0.75,
                                                hovertemplate="<b>" + _xlbl + "</b><br>CR: %{y:.4f}<extra></extra>",
                                                showlegend=True
                                            ))
                                        _vio_xaxis_title = _("대분류", "Main Criteria")
                                        _vio_legend_title = _("대분류", "Main Criteria")

                                    # ── 선택: 중분류 ─────────────────────────────────
                                    elif _sel_tier in [_tier_opts[1]]:
                                        # 대분류별로 하나의 바이올린 (해당 대분류 중분류 비교 시 CR)
                                        for _mf in _vio_mf_list:
                                            _sinfo = _vio_sub_stor.get(_mf, {})
                                            _sdf = _sinfo.get("df", None)
                                            if _sdf is None or _sdf.empty or "Final_CR" not in _sdf.columns:
                                                continue
                                            _cr_vals = _sdf["Final_CR"].dropna().tolist()
                                            if len(_cr_vals) < 2:
                                                continue
                                            _xlbl = _(f"중분류({_mf})", f"Sub({_mf})")
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
                                        _vio_xaxis_title = _("대분류 (중분류 비교 CR)", "Main Criteria (Sub-Criteria Comparison CR)")
                                        _vio_legend_title = _("중분류", "Sub-Criteria")

                                    # ── 선택: 소분류 ─────────────────────────────────
                                    else:
                                        # 중분류별로 하나의 바이올린 (해당 중분류 소분류 비교 시 CR)
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
                                                _xlbl = _(f"소분류({_sf})", f"Sub-sub({_sf})")
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
                                        _vio_xaxis_title = _("중분류 (소분류 비교 CR)", "Sub-Criteria (Sub-sub Comparison CR)")
                                        _vio_legend_title = _("소분류", "Sub-sub-Criteria")

                                    if len(_fig_vio.data) == 0:
                                        st.info(_("선택한 계층의 CR 데이터가 없거나 응답 수가 부족합니다.",
                                                  "No CR data available for the selected tier or insufficient responses."))
                                    else:
                                        _fig_vio.add_hline(
                                            y=0.1, line_dash="dash", line_color="red",
                                            annotation_text=_("CR 임계값 (0.1)", "CR Threshold (0.1)"),
                                            annotation_position="top right"
                                        )
                                        _fig_vio.update_layout(
                                            title=_(
                                                f"바이올린플롯 CR — {_sel_tier}",
                                                f"Violin Plot CR — {_sel_tier}"
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
                                    st.warning(_(f"바이올린 플롯 생성 실패: {_e_vio}", f"Violin plot generation failed: {_e_vio}"))

                                if len(v3_unique_groups) >= 2 and v3_group_full_dfs:
                                    st.markdown(_("**③ 그룹별 대분류 중요도 레이더 차트**",
                                                  "**③ Main Criteria Importance Radar Chart by Group**"))
                                    _radar_rows = []
                                    for _grp_rd in v3_unique_groups:
                                        if _grp_rd not in v3_group_full_dfs: continue
                                        _gdf_rd = v3_group_full_dfs[_grp_rd]
                                        for _mf_rd in v3_main_factors:
                                            _mf_rd_sub = _gdf_rd[_gdf_rd["대분류"]==_mf_rd]
                                            _w_rd = float(_mf_rd_sub.iloc[0]["대분류 가중치"]) if not _mf_rd_sub.empty else 0.0
                                            _lbl_rd = str(_grp_rd).replace("전문가","Expert").replace("일반","General").replace("공무원","Public Official") if is_english else _grp_rd
                                            _radar_rows.append({_("그룹","Group"): _lbl_rd, _("항목","Factor"): _mf_rd, "Weight": _w_rd})
                                    if _radar_rows:
                                        _radar_df_v3 = pd.DataFrame(_radar_rows)
                                        _cats_rd = _radar_df_v3[_("항목","Factor")].unique().tolist()
                                        _fig_rd = go.Figure()
                                        _colors_rd = ["#4F81BD","#C0504D","#9BBB59","#8064A2","#F79646"]
                                        for _i_rd, _grp_rdn in enumerate(_radar_df_v3[_("그룹","Group")].unique()):
                                            _g_rd = _radar_df_v3[_radar_df_v3[_("그룹","Group")]==_grp_rdn]
                                            _vals_rd = [_g_rd[_g_rd[_("항목","Factor")]==c]["Weight"].values[0] if len(_g_rd[_g_rd[_("항목","Factor")]==c])>0 else 0 for c in _cats_rd]
                                            _vals_cl = _vals_rd + [_vals_rd[0]]
                                            _cats_cl = _cats_rd + [_cats_rd[0]]
                                            _fig_rd.add_trace(go.Scatterpolar(r=_vals_cl, theta=_cats_cl, fill="toself", name=_grp_rdn, line_color=_colors_rd[_i_rd % len(_colors_rd)], opacity=0.7))
                                        _fig_rd.update_layout(
                                            polar=dict(radialaxis=dict(visible=True, range=[0, max(0.01, _radar_df_v3["Weight"].max()*1.2)])),
                                            showlegend=True,
                                            title=_("그룹별 대분류 중요도 패턴", "Main Criteria Importance Pattern by Group"),
                                            height=450
                                        )
                                        st.plotly_chart(_fig_rd, use_container_width=True)

                            # ─── Tab 5: 결과 다운로드 ────────────────────────────────────────
                            with tab3v5:
                                st.markdown(_("###  3계층 AHP 종합분석 결과 다운로드",
                                              "### 📑 Download 3-Tier AHP Comprehensive Analysis Results"))
                                st.download_button(
                                    label=_("📥 3계층 AHP 종합분석 결과 다운로드 (.xlsx)", "📥 Download 3-Tier AHP Results (.xlsx)"),
                                    data=output_res_v3,
                                    file_name="3Tier_AHP_Result.xlsx",
                                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                    type="primary",
                                    use_container_width=True
                                )
                                st.info(_("📋 엑셀 파일에는 종합분석, 그룹비교, 계층별 상세행렬, CR 분포 등 전체 분석 결과가 포함됩니다.",
                                          "📋 The Excel file contains all results: comprehensive summary, group comparison, detailed matrices per tier, and CR distribution."))

                            # 3계층 처리 완료 – 기존 2계층 UI 스킵
                            st.stop()
                        
                        with st.spinner(_("계층 분석 수행 중...", "Performing Analytic Hierarchy Process (AHP)...")):
                            # 1. 메인 시트 분석 시도
                            try:
                                main_results_df, main_factors, main_excluded, main_excluded_df = process_single_sheet(
                                    df_main, cr_threshold, max_iter_val, learning_rate, mean_method, ahp_method
                                )
                            except Exception as e:
                                st.error(_("❌ [메인 시트] 분석 중 오류가 발생했습니다.", "❌ Error occurred during [Main Criteria] analysis."))
                                with st.expander(_("💡 이유 및 해결 방법 보기", "💡 View Reason & Solution"), expanded=True):
                                    st.markdown(_(f"""
                                    **원인:** 메인 시트의 데이터 구조가 올바르지 않거나 읽을 수 있는 유효 데이터가 없습니다. (Error: {e})
                                    **해결 방법:**
                                    1. 엑셀의 첫 번째 시트 이름이 `Main_Criteria`인지 확인하세요.
                                    2. ID와 Type 열 다음에 쌍대비교 데이터가 올바르게 입력되었는지 확인하세요.
                                    3. 빈 행이 포함되어 있다면 삭제 후 다시 시도하세요.
                                    """,
                                    f"""
                                    **Cause:** The structure of the main sheet is incorrect or contains no readable valid data. (Error: {e})
                                    **Solution:**
                                    1. Ensure that the first sheet name in Excel is `Main_Criteria`.
                                    2. Verify that pair-wise comparison data is correctly input after the 'ID' and 'Type' columns.
                                    3. If empty rows are included, delete them and try again.
                                    """))
                                st.stop()
    
                            # [방어 코드] 메인 결과 충분성 체크
                            if main_results_df.empty or len(main_results_df) < 1:
                                st.error(_(f"⚠️ 분석 불가: 메인 기준 유효 응답자가 부족합니다. (현재 {len(main_results_df)}명)",
                                           f"⚠️ Cannot Analyze: Insufficient valid respondents for Main Criteria. (Current: {len(main_results_df)} respondents)"))
                                with st.expander(_("💡 이유 및 해결 방법 보기", "💡 View Reason & Solution"), expanded=True):
                                    st.markdown(_(f"""
                                    **원인:** 모든 응답자의 일관성 비율(CR)이 임계치({cr_threshold})를 초과하여 보정 후에도 수렴하지 못했습니다.
                                    **해결 방법:**
                                    1. 왼쪽 사이드바에서 **'일관성 비율(CR) 임계값'**을 0.15 또는 0.2로 완화해 보세요.
                                    2. **'보정 강도(Learning Rate)'**를 0.7 이상으로 높여보세요.
                                    3. **'최대 보정 반복 횟수'**를 500회로 설정했는지 확인하세요.
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

                            # 2. 하위 시트 분석 및 저장
                            sub_results_storage = {}
                            total_excl_df_list = [main_excluded_df]
                        
                            is_single_sheet = (len(sheet_names) == 1)
                        
                            if is_single_sheet:
                                for parent_factor in main_factors:
                                    # 1단계 분석인 경우 (하위 시트가 없음), 
                                    # 하위 가중치 1.0을 가지는 더미 데이터를 자동으로 생성하여 연산을 마칩니다.
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
                                    # 대분류 항목명과 일치하는 시트명 찾기 (대소문자, 공백 무시 및 31자 제한 고려)
                                    target_name = parent_factor.strip().lower()
                                    target_name_31 = parent_factor[:31].strip().lower()
                                
                                    matched_sheet_name = None
                                    for sn in sheet_names[1:]:
                                        sn_clean = sn.strip().lower()
                                        if sn_clean == target_name or sn_clean == target_name_31:
                                            matched_sheet_name = sn
                                            break
                                
                                    if matched_sheet_name is None:
                                        st.error(_(f"❌ [세부 시트: {parent_factor}] 시트를 찾을 수 없습니다.", f"❌ [Detailed Sheet: {parent_factor}] Sheet not found."))
                                        with st.expander(_("💡 이유 및 해결 방법 보기", "💡 View Reason & Solution"), expanded=True):
                                            st.markdown(_(f"""
                                            **원인:** 메인 기준 시트에서 도출된 대분류 항목 **'{parent_factor}'**에 대응하는 세부 설문 응답 시트가 엑셀 파일 내에 존재하지 않거나 시트 이름이 다릅니다.
                                            **해결 방법:**
                                            1. 업로드한 엑셀 파일 내에 **'{parent_factor}'** (또는 31자 이내로 앞부분이 일치하는 명칭)의 시트가 존재하는지 확인하세요.
                                            2. 시트 이름의 앞뒤 공백이나 오탈자(예: '리드타임민감도'와 '리드타임 민감도')가 없는지 확인하고 시트명을 맞춰주세요.
                                            """,
                                            f"""
                                            **Cause:** The detailed survey response sheet corresponding to the main criteria category **'{parent_factor}'** does not exist in the Excel file or has a different name.
                                            **Solution:**
                                            1. Check if a sheet named **'{parent_factor}'** (or a name matching the first 31 characters) exists in the uploaded Excel file.
                                            2. Ensure there are no leading/trailing spaces or spelling discrepancies (e.g., 'Lead Time Sensitivity' vs 'LeadTime Sensitivity') and align the sheet names.
                                            """))
                                        st.stop()
                                
                                    try:
                                        if data_source == _("🌐 배포된 온라인 설문 데이터 연동", "🌐 Connect Online Survey Data"):
                                            df_sub = st.session_state["ahp_sub_dfs"][matched_sheet_name]
                                        else:
                                            df_sub = pd.read_excel(uploaded_file, sheet_name=matched_sheet_name)
                                            df_sub = preprocess_uploaded_df(df_sub)
                                            
                                        sub_res_df, sub_facts, sub_excl, sub_excl_df = process_single_sheet(
                                            df_sub, cr_threshold, max_iter_val, learning_rate, mean_method, ahp_method
                                        )
                                    
                                        if sub_res_df.empty:
                                            raise ValueError(f"'{matched_sheet_name}' 시트에 유효한 분석 데이터가 없습니다.")
                                        
                                        # 통계 계산 로직
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
                                        st.error(_(f"❌ [세부 시트: {matched_sheet_name}] 분석 중 오류가 발생했습니다.", f"❌ Error occurred during [Detailed Sheet: {matched_sheet_name}] analysis."))
                                        with st.expander(_("💡 이유 및 해결 방법 보기", "💡 View Reason & Solution"), expanded=True):
                                            st.markdown(_(f"""
                                            **원인:** 시트 내부의 데이터 구조가 올바르지 않거나, 해당 시트의 응답자들이 모두 일관성 기준을 통과하지 못했습니다. (Error: {e})
                                            **해결 방법:**
                                            1. 해당 세부 시트의 데이터에 빈 칸이나 문자가 섞여 있는지 확인하세요.
                                            2. CR 임계값을 높여서 다시 분석해 보세요.
                                            """,
                                            f"""
                                            **Cause:** The internal data structure of the sheet is incorrect, or all respondents for this sheet failed to pass the consistency ratio criteria. (Error: {e})
                                            **Solution:**
                                            1. Check if there are empty cells or text mixed in the data of the detailed sheet.
                                            2. Try analyzing again with a higher CR threshold.
                                            """))
                                        st.stop()
    
                            # 분석 헤더 윗쪽에 제외된 사례수 표시
                            total_excluded = main_excluded
                            st.markdown(f"**" + _(f"분석 제외: {total_excluded}건", f"Excluded from Analysis: {total_excluded} cases") + "**")
    
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
                        
                            # --- 다중 인구통계 변수 처리 UI ---
                            demo_cols = [c for c in main_results_df.columns if str(c).strip().lower() == 'type' or str(c).strip().lower().startswith('type ')]
                            if len(demo_cols) > 1 and tier in ['Standard', 'Pro']:
                                selected_demo = st.selectbox(_("📊 교차분석 그룹 기준 변수 선택", "📊 Select Grouping Variable for Analysis"), demo_cols)
                                main_results_df['Type'] = main_results_df[selected_demo]
                                for mf in main_factors:
                                    sub_results_storage[mf]['df']['Type'] = sub_results_storage[mf]['df'][selected_demo]
                            elif len(demo_cols) > 0:
                                main_results_df['Type'] = main_results_df[demo_cols[0]]
                                for mf in main_factors:
                                    sub_results_storage[mf]['df']['Type'] = sub_results_storage[mf]['df'][demo_cols[0]]
                            else:
                                main_results_df['Type'] = 'All'
                                for mf in main_factors:
                                    sub_results_storage[mf]['df']['Type'] = 'All'

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
                                        "대분류": main_f, "대분류 가중치": m_weight, "중분류": sub_f, "중분류 가중치": s_weight,
                                        "Global Weight": global_w, 
                                        "CR(대분류)": main_grp_cr, 
                                        "CI(대분류)": main_grp_ci,
                                        "CR(중분류)": sub_info['group_cr'],
                                        "CI(중분류)": sub_info['group_ci']
                                    })
                        
                            final_df = pd.DataFrame(summary_rows)
                            final_df['Global Rank'] = final_df['Global Weight'].round(3).rank(ascending=False, method='min').astype(int)
                            cols_order = ["대분류", "대분류 가중치", "중분류", "중분류 가중치", "Global Weight", "Global Rank", "CR(대분류)", "CI(대분류)", "CR(중분류)", "CI(중분류)"]
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
                                            "대분류": main_f, "대분류 가중치": m_w, "중분류": sf, "중분류 가중치": s_w_val,
                                            "Global Weight": m_w * s_w_val, 
                                            "CR(대분류)": g_main_cr, 
                                            "CI(대분류)": g_main_ci,
                                            "CR(중분류)": g_sub_cr, 
                                            "CI(중분류)": g_sub_ci
                                        })
                                g_df = pd.DataFrame(grp_rows)
                                if not g_df.empty:
                                    g_df['Global Rank'] = g_df['Global Weight'].round(3).rank(ascending=False, method='min').astype(int)
                                    group_full_dfs[grp] = g_df[cols_order]
                                    group_analysis_results[grp] = group_full_dfs[grp][['대분류', '중분류', 'Global Weight']]
    
                            comparison_df = final_df[['대분류', '중분류', 'Global Weight']].copy()
                            comparison_df.rename(columns={'Global Weight': '종합평균(Overall)'}, inplace=True)
                            for grp, df_res in group_analysis_results.items():
                                temp_df = df_res.rename(columns={'Global Weight': grp})
                                comparison_df = comparison_df.merge(temp_df, on=['대분류', '중분류'], how='left')
    
                            output_res = io.BytesIO()
                            with pd.ExcelWriter(output_res, engine='xlsxwriter') as writer:
                                workbook = writer.book
                                
                                # [신규 추가] 인구통계 결과 엑셀 시트 출력
                                if "demo_df" in st.session_state and st.session_state["demo_df"] is not None:
                                    demo_summary_df = generate_demographics_summary(st.session_state["demo_df"])
                                    if demo_summary_df is not None:
                                        demo_summary_df.to_excel(writer, sheet_name='Result_Demographics', index=False)
                                        # Result_Demographics 엑셀 서식 적용
                                        ws_demo = writer.sheets['Result_Demographics']
                                        header_format_demo = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'bg_color': '#4F81BD', 'font_color': '#FFFFFF', 'border': 1})
                                        body_format_demo = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'border': 1})
                                        for col_num, value in enumerate(demo_summary_df.columns.values):
                                            ws_demo.write(0, col_num, value, header_format_demo)
                                        for row in range(len(demo_summary_df)):
                                            for col in range(len(demo_summary_df.columns)):
                                                ws_demo.write(row+1, col, demo_summary_df.iloc[row, col], body_format_demo)
                                        ws_demo.set_column('A:A', 30)
                                        ws_demo.set_column('B:D', 20)
                                
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
                                sheet_name_comp = _('종합분석', 'Comprehensive Analysis')
                                current_row_ws = write_custom_ahp_table(writer, sheet_name_comp, final_df, _("1) 전체_종합결과", "1) Overall Aggregated Results"), 1, formats, excluded_df=total_excluded_df)
                                for grp in unique_groups:
                                    if grp in group_full_dfs:
                                        current_row_ws = write_custom_ahp_table(writer, sheet_name_comp, group_full_dfs[grp], _(f"▶ [그룹: {grp}] 분석 결과", f"▶ [Group: {grp}] Analysis Results"), current_row_ws, formats)
    
                                if len(unique_groups) >= 1:
                                    ws_comp = workbook.add_worksheet('Group_Comparison')
                                    writer.sheets['Group_Comparison'] = ws_comp
                                    s_row_cp = 1
                                    ws_comp.write_string(s_row_cp, 0, _("그룹 간 비교(일원배치 분산분석: ANOVA)", "Group Comparison (One-way ANOVA)"), workbook.add_format({'bold': True, 'font_size': 12}))
                                    s_row_cp += 1
                                
                                    tier = get_current_tier()
                                    if tier not in ['Standard', 'Pro']:
                                        ws_comp.write_string(s_row_cp, 0, _("🔒 통계 검정 결과(ANOVA/사후검정)는 Standard 등급 이상 정식 사용자에게만 제공됩니다.", "🔒 Statistical test results (ANOVA/Post-hoc) are exclusive to Standard and Pro Tier users."), workbook.add_format({'italic': True, 'font_color': '#FF0000', 'font_name': 'NanumGothic'}))
                                        s_row_cp += 1
                                
                                    if tier in ['Standard', 'Pro'] and not anova_df.empty:
                                        anova_for_merge = anova_df.rename(columns={'요인': '중분류'})
                                        integrated_df = comparison_df.merge(anova_for_merge, on='중분류', how='left')
                                    else:
                                        integrated_df = comparison_df
                                
                                    # English renaming logic for columns & significance
                                    if st.session_state.get('lang', 'ko') == 'en':
                                        rename_dict = {
                                            '대분류': 'Main Criteria',
                                            '중분류': 'Sub-Criteria',
                                            '종합평균(Overall)': 'Overall',
                                            'F-값': 'F-Value',
                                            'P-Value': 'P-Value',
                                            '유의성': 'Significance',
                                            '사후검정(Tukey HSD)': 'Post-hoc (Tukey HSD)'
                                        }
                                        integrated_df_excel = integrated_df.copy()
                                        integrated_df_excel.rename(columns=rename_dict, inplace=True)
                                        if 'Significance' in integrated_df_excel.columns:
                                            integrated_df_excel['Significance'] = integrated_df_excel['Significance'].replace({
                                                '유의함': 'Significant',
                                                '유의하지 않음': 'Not Significant'
                                            })
                                        if 'Post-hoc (Tukey HSD)' in integrated_df_excel.columns:
                                            integrated_df_excel['Post-hoc (Tukey HSD)'] = integrated_df_excel['Post-hoc (Tukey HSD)'].replace({
                                                '집단 간 구체적 차이 발견 못함': 'No specific difference found',
                                                '계산 오류': 'Calculation Error'
                                            })
                                            integrated_df_excel['Post-hoc (Tukey HSD)'] = integrated_df_excel['Post-hoc (Tukey HSD)'].apply(
                                                lambda x: x.replace(" 차이 있음", " Diff Exists") if isinstance(x, str) else x
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
                                
                                    if tier in ['Standard', 'Pro']:
                                        comp_title = _("※ 그룹 간 중요도의 차이가 있지만 통계적으로 유의하지 않게 나타나는 이유",
                                                       "※ Reasons why group differences are not statistically significant despite variation in priorities")
                                        ws_comp.merge_range(guide_start_row, 0, guide_start_row, 6, comp_title, bold_fmt)
    
                                    guide_content_ko = [
                                        ("1. 그룹 내 편차(분산)가 너무 큰 경우", "ANOVA는 '그룹 간의 차이'와 '그룹 내의 차이'를 비교합니다.\n\n■ 원리: 그룹 간 평균 차이가 크더라도, 각 그룹 내부 데이터들이 서로 들쭉날쭉(분산이 큼)하다면 통계적으로는 '이 차이가 우연히 발생했을 가능성이 높다'고 판단합니다."),
                                        ("2. 표본 크기(Sample Size)의 부족", "통계적 유의성은 표본의 수에 매우 민감합니다.\n\n■ 현상: 각 그룹의 데이터 개수(표본수)가 너무 적다면 통계적 힘(Power)이 부족하여 유의미한 차이를 찾아내지 못합니다."),
                                        ("3. 데이터의 단위(Scale)와 변동성", "표에 나타난 수치들이 대부분 매우 작은 소수점 단위입니다. 실제 계산 과정에서 표준오차 범위 내에 있다면 통계적으로는 측정 오차 범위 내의 흔들림으로 간주됩니다.")
                                    ]
                                
                                    guide_content_en = [
                                        ("1. Within-Group Variance is Too Large", "ANOVA compares variance between groups against variance within groups.\n\n■ Principle: Even if the mean difference between groups is large, if individual responses within each group are highly scattered (large variance), statistics will determine that the difference is likely due to chance."),
                                        ("2. Insufficient Sample Size", "Statistical significance is highly sensitive to the number of samples.\n\n■ Phenomenon: If the number of data points (sample size) in each group is too small, statistical power is insufficient to detect significant differences."),
                                        ("3. Data Scale and Volatility", "The values in the table are mostly very small decimals. If they fall within the range of standard error, they are considered as minor fluctuations within the measurement error range.")
                                    ]
                                
                                    guide_content = (guide_content_en if st.session_state.get('lang', 'ko') == 'en' else guide_content_ko) if tier in ['Standard', 'Pro'] else []
    
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
                                
                                    excl_label = _(f"분석 제외 사례수: {sheet_excl_count}건", f"Excluded cases: {sheet_excl_count}")
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
                                
                                    # [신규 추가] 전체 종합 행렬 오른쪽에 전체 CR, CI 값 표시
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
                                
                                    ws.merge_range(s_row_det, n_dim + 2, s_row_det, n_dim + 3, _("전체 일관성 지표", "Overall Consistency Indicators"), ci_cr_header_fmt)
                                    ws.write(s_row_det + 1, n_dim + 2, _("전체 CI", "Overall CI"), ci_cr_label_fmt)
                                    ws.write(s_row_det + 1, n_dim + 3, ci_val, ci_cr_val_fmt)
                                    ws.write(s_row_det + 2, n_dim + 2, _("전체 CR", "Overall CR"), ci_cr_label_fmt)
                                    ws.write(s_row_det + 2, n_dim + 3, cr_val, ci_cr_val_fmt)
                                
                                    s_row_det += len(matrix_df) + 3
                                
                                    if group_matrices:
                                        for g_name, g_mat in group_matrices.items():
                                            ws.write_string(s_row_det, 0, _(f"] 그룹 종합 행렬: {g_name}", f"] Group Combined Matrix: {g_name}"))
                                            s_row_det += 1
                                            gm_df_obj = pd.DataFrame(g_mat, index=row_labels, columns=row_labels)
                                            gm_df_obj.to_excel(writer, sheet_name=sheet_name, startrow=s_row_det)
                                            add_borders_to_data(ws, s_row_det, 0, gm_df_obj, border_fmt, has_header=True, has_index=True)
                                            for r in range(len(g_mat)):
                                                for c in range(len(g_mat)):
                                                    val = 1 if r==c else g_mat[r][c]
                                                    ws.write(s_row_det+r+1, c+1, val, border_fmt if r!=c else fmt_diagonal)
                                                    if r!=c: ws.write(s_row_det+r+1, c+1, val, fmt_float_no_border)
                                        
                                            # [신규 추가] 그룹 종합 행렬 오른쪽에 그룹 CR, CI 값 표시
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
                                        
                                            ws.merge_range(s_row_det, n_dim + 2, s_row_det, n_dim + 3, _("그룹 일관성 지표", "Group Consistency Indicators"), ci_cr_header_fmt)
                                            ws.write(s_row_det + 1, n_dim + 2, _("그룹 CI", "Group CI"), ci_cr_label_fmt)
                                            ws.write(s_row_det + 1, n_dim + 3, g_ci_val, g_ci_cr_val_fmt)
                                            ws.write(s_row_det + 2, n_dim + 2, _("그룹 CR", "Group CR"), ci_cr_label_fmt)
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
                                write_detailed_sheet_ws('(대분류) Main', main_group_matrix, out_main, _("[대분류 평가 종합 행렬]", "[Main Criteria Combined Matrix]"), main_factors, group_matrices=main_group_mats, sheet_excl_count=main_excluded)
                                for mf, info in sub_results_storage.items():
                                    safe_name = f"(중분류) {mf}"[:31]
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
                                             
                                    title_ko = f"[중분류 평가 종합 행렬]  ▶ 상위 계층: 대분류 [{mf}]"
                                    title_en = f"[Sub-Criteria Combined Matrix]  ▶ Parent: Main [{mf}]"
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
                                        [f"The original matrix A and the ideal matrix W are linearly combined according to the set learning rate (learning rate α={learning_rate}): A_new = (1-α)A + αW."],
                                        [""],
                                        ["3. Academic Foundation & Effects"],
                                        ["Adjustment using a weighted average of the original matrix and the consistent matrix preserves the decision maker's original preferences as much as possible while improving mathematical consistency."]
                                    ]
                                else:
                                    theory_text = [
                                        ["의사결정론적 관점에서의 AHP 일관성 보정 원리 및 학술적 근거"],
                                        [""],
                                        ["1. 서론: 계층분석과정(AHP)의 일관성 문제"],
                                        ["Saaty(1980)에 의해 제안된 계층분석과정은 인간의 주관적 판단을 정량화하는 다기준 의사결정 도구이다. 비일관적 판단이 발생할 경우 수학적으로 교정하여 분석의 신뢰성을 확보한다."],
                                        [""],
                                        ["2. 보정 알고리즘: 반복 수렴 조정법"],
                                        [f"원본 행렬 A와 이상적 행렬 W를 설정된 학습률(α={learning_rate})에 따라 선형 결합한다: A_new = (1-α)A + αW."],
                                        [""],
                                        ["3. 학술적 근거 및 효과"],
                                        ["원본 행렬과 일관 행렬의 가중 평균을 이용한 조정은 의사결정자의 원래 선호 경향성을 최대한 보존하면서 수학적 일관성을 향상시킨다."]
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
                                    guide_title = _("1단계 AHP 분석 결과 해석 및 주의사항", "Step 1 AHP Analysis Result Interpretation and Guidelines")
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
                                            ("분류", "상세 내용"),
                                            ("1. 분석 개요", "본 보고서는 하위 요소 없이 대분류(1단계) 평가 기준만을 비교한 단일 계층 AHP 분석 결과입니다."),
                                            ("2. 결과 해석 방법", "하위 가중치가 1.0으로 고정되어 '대분류 가중치'와 'Global Weight(종합 가중치)'가 동일한 수치로 산출되었습니다. 따라서 'Global Weight'를 각 항목의 최종 중요도로 해석하시면 됩니다."),
                                            ("3. 내부 가상 연산 안내", "AHP 분석 시스템의 2단계 연산 일관성 유지를 위해, 시스템 내부적으로 대분류 항목 하위에 가중치 1.0을 가지는 더미 세부 항목을 자동 생성하여 연산하였습니다. 이로 인해 결과 다운로드 파일에 'Result_[대분류명]' 시트가 1x1 행렬로 존재하지만 이는 정상적인 가상 연산 결과입니다."),
                                            ("4. 일관성 비율(CR) 주의사항", "제공된 일관성 비율은 대분류 쌍대비교의 일관성 비율(CR)만을 나타냅니다. 하위 요소가 존재하지 않으므로 '중분류 일관성 비율(CR)'은 무조건 0.000으로 표기되며 이는 오류가 아닙니다."),
                                            ("5. 학술/보고서 기재 팁", "학술 연구나 보고서에 활용 시 '단일 계층(1단계) 계층 구조 하에서 쌍대비교 분석을 수행하였다'고 명시적으로 기재하시기 바랍니다.")
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
                                    # 1. Fuzzy AHP 가중치 분석 결과 시트 추가
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
                                
                                    ws_fuzzy.write_string(row_idx, 0, _("■ 대분류 (Main Criteria) 퍼지 AHP 분석 결과 (삼각피지수 적용)", "■ Main Criteria Fuzzy AHP Results (TFN Applied)"), title_fmt)
                                    row_idx += 1
                                
                                    headers = [
                                        _("구분", "Criteria"), 
                                        _("Fuzzy 가중치 (Lower)", "Fuzzy Weight (Lower)"), 
                                        _("Fuzzy 가중치 (Medium)", "Fuzzy Weight (Medium)"), 
                                        _("Fuzzy 가중치 (Upper)", "Fuzzy Weight (Upper)"), 
                                        _("비퍼지화 (Crisp)", "Defuzzified (Crisp)"), 
                                        _("최종 가중치 (Norm)", "Final Weight (Norm)"), 
                                        _("순위", "Rank")
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
                                            ws_fuzzy.write_string(row_idx, 0, _(f"■ 세부항목 [{parent_f}] 퍼지 AHP 분석 결과 (삼각피지수 적용)", f"■ Sub-Criteria [{parent_f}] Fuzzy AHP Results (TFN Applied)"), title_fmt)
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
    
                                    # 2. 일관성 비율(CR) 분포 분석 결과 시트 추가
                                    ws_cr = workbook.add_worksheet('CR_Distribution')
                                    writer.sheets['CR_Distribution'] = ws_cr
                                    ws_cr.set_column('A:A', 25)
                                    ws_cr.set_column('B:H', 20)
                                
                                    cr_header_fmt = workbook.add_format({
                                        'bold': True, 'align': 'center', 'valign': 'vcenter',
                                        'bg_color': '#595959', 'font_color': '#FFFFFF', 'border': 1,
                                        'font_name': 'NanumGothic'
                                    })
                                
                                    ws_cr.write_string(1, 0, _("■ 일관성 비율(CR) 분석 요약", "■ Consistency Ratio (CR) Analysis Summary"), title_fmt)
                                
                                    cr_headers = [
                                        _("평가 시트명", "Sheet Name"),
                                        _("평균 CR", "Mean CR"),
                                        _("중앙값 CR", "Median CR"),
                                        _("최소 CR", "Min CR"),
                                        _("최대 CR", "Max CR"),
                                        _("통과 표본 수 (CR <= 0.1)", "Passed Samples (CR <= 0.1)"),
                                        _("전체 표본 수", "Total Samples"),
                                        _("통과율 (%)", "Pass Rate (%)")
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
                                    ws_cr.write_string(cr_row_idx, 0, _("■ 개별 응답자별 일관성 비율(CR) 상세 내역", "■ Detailed Consistency Ratio (CR) by Respondent"), title_fmt)
                                    cr_row_idx += 1
                                
                                    indiv_headers = [
                                        _("ID (설문자)", "Respondent ID"),
                                        _("그룹 (Type)", "Group Type"),
                                        _("평가 시트명", "Sheet Name"),
                                        _("일관성 비율 (CR)", "Consistency Ratio (CR)"),
                                        _("판정 (CR <= 0.1)", "Status (CR <= 0.1)")
                                    ]
                                    for c_idx, h in enumerate(indiv_headers):
                                        ws_cr.write(cr_row_idx, c_idx, h, cr_header_fmt)
                                    cr_row_idx += 1
                                
                                    for idx_row, r in main_results_df.iterrows():
                                        cr_val = r['Final_CR']
                                        status = _("만족 (Pass)", "Pass") if cr_val <= 0.1 else _("불만족 (Fail)", "Fail")
                                        ws_cr.write(cr_row_idx, 0, r['ID'], formats['body'])
                                        ws_cr.write(cr_row_idx, 1, r['Type'], formats['body'])
                                        ws_cr.write(cr_row_idx, 2, "Main_Criteria", formats['body'])
                                        ws_cr.write_number(cr_row_idx, 3, cr_val, formats['num'])
                                        ws_cr.write(cr_row_idx, 4, status, formats['body'])
                                        cr_row_idx += 1
                                    
                                    for mf, info in sub_results_storage.items():
                                        for idx_row, r in info['df'].iterrows():
                                            cr_val = r['Final_CR']
                                            status = _("만족 (Pass)", "Pass") if cr_val <= 0.1 else _("불만족 (Fail)", "Fail")
                                            ws_cr.write(cr_row_idx, 0, r['ID'], formats['body'])
                                            ws_cr.write(cr_row_idx, 1, r['Type'], formats['body'])
                                            ws_cr.write(cr_row_idx, 2, mf, formats['body'])
                                            ws_cr.write_number(cr_row_idx, 3, cr_val, formats['num'])
                                            ws_cr.write(cr_row_idx, 4, status, formats['body'])
                                            cr_row_idx += 1
    
                        st.success(_("분석이 완료되었습니다.", "Analysis completed successfully."))
                        if st.session_state.user_role == 'official':
                            if data_source == _("📂 엑셀 파일 직접 업로드", "Upload Excel File") and uploaded_file is not None:
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
    
                        # 결과 휘발성 주의 안내
                        st.markdown(_('<p style="color: red; font-weight: bold; font-size: 0.95rem; margin-top: 5px; margin-bottom: 10px;"> 주의: 페이지를 새로고침하거나 브라우저를 닫으면 분석 결과가 저장되지 않고 리셋되므로, 결과물 엑셀 파일( 결과 다운로드 탭)을 반드시 다운로드하여 저장해 주세요.</p>',
                                      '<p style="color: red; font-weight: bold; font-size: 0.95rem; margin-top: 5px; margin-bottom: 10px;">⚠️ Warning: Analysis results are not stored and will be reset if you refresh the page or close the browser. Please make sure to download and save the results Excel file (📑 Download Results tab).</p>'), unsafe_allow_html=True)
    
                        tab1, tab2, tab3, tab4, tab5 = st.tabs([
                            _("🌐 종합 분석 (Global)", "🌐 Global Comprehensive Analysis"),
                            _("👨‍👩‍👧‍👦 그룹별 분석", "👨‍👩‍👧‍👦 Group Analysis"),
                            _("🧪 통계 검정 (ANOVA)", "🧪 Statistical Test (ANOVA)"),
                            _("📊 시각화 센터", "📊 Visualization Center"),
                            _("📑 결과 다운로드", "📑 Download Results")
                        ])
                        with tab1:
                            st.subheader(_(" 종합 중요도 및 순위", " Global Weights & Rankings"))
                            if is_english:
                                disp_final_df = final_df.rename(columns={
                                    "대분류": "Main Criteria",
                                    "대분류 가중치": "Main Criteria Weight",
                                    "중분류": "Sub-Criteria",
                                    "중분류 가중치": "Sub-Criteria Weight",
                                    "Global Weight": "Global Weight",
                                    "Global Rank": "Global Rank",
                                    "CR(대분류)": "CR (Main Criteria)",
                                    "CI(대분류)": "CI (Main Criteria)",
                                    "CR(중분류)": "CR (Sub-Criteria)",
                                    "CI(중분류)": "CI (Sub-Criteria)"
                                })
                            else:
                                disp_final_df = final_df
                            st.dataframe(disp_final_df.style.format(precision=3), use_container_width=True)
    

    
                        with tab2:
                            st.markdown(_("#### 그룹별 가중치 상세 비교", "#### Detailed Comparison of Weights by Group"))
                            disp_comparison_df = comparison_df.copy()
                            if is_english:
                                disp_comparison_df.rename(columns={
                                    "중분류": "Sub-Criteria",
                                    "Overall": "Overall",
                                    "전문가": "Expert",
                                    "일반": "General",
                                    "공무원": "Public Official"
                                }, inplace=True)
                            st.dataframe(disp_comparison_df.style.format(precision=4), use_container_width=True)
                        with tab3:
                            st.markdown(_("#### 집단 간 유의성 분석", "#### Analysis of Significance Between Groups"))
                            if not anova_df.empty:
                                if is_english:
                                    disp_anova = anova_df.copy()
                                    disp_anova.rename(columns={
                                        "요인": "Factor/Criteria",
                                        "F-값": "F-Value",
                                        "P-Value": "P-Value",
                                        "유의성": "Significance",
                                        "사후검정(Tukey HSD)": "Post-Hoc (Tukey HSD)"
                                    }, inplace=True)
                                
                                    # Map values in Significance
                                    disp_anova["Significance"] = disp_anova["Significance"].map({
                                        "유의함": "Significant",
                                        "유의하지 않음": "Not Significant"
                                    }).fillna(disp_anova["Significance"])
                                
                                    # Map values in Post-Hoc
                                    def translate_posthoc(val):
                                        if not isinstance(val, str):
                                            return val
                                        val = val.replace("전문가", "Expert").replace("일반", "General").replace("공무원", "Public Official")
                                        val = val.replace(" 차이 있음", " (Diff exists)")
                                        val = val.replace("집단 간 구체적 차이 발견 못함", "No significant pairwise difference found")
                                        val = val.replace("계산 오류", "Calculation Error")
                                        return val
                                    disp_anova["Post-Hoc (Tukey HSD)"] = disp_anova["Post-Hoc (Tukey HSD)"].apply(translate_posthoc)
                                else:
                                    disp_anova = anova_df
                                st.dataframe(disp_anova.style.format(precision=5), use_container_width=True)
                            else:
                                st.info(_("통계 검정을 위해 2개 이상의 그룹 데이터가 필요합니다.", "At least 2 group datasets are required for statistical testing (ANOVA)."))
                        with tab4:
                            st.markdown(_("####  시각화 센터", "####  Visualization Center"))
                            col_chart1, col_chart2 = st.columns(2)
                            with col_chart1:
                                st.write(_("**종합 중요도 (Bar)**", "**Global Importance (Bar)**"))
                                chart_bar_df = final_df.sort_values('Global Weight').copy()
                                if is_english:
                                    chart_bar_df.rename(columns={"중분류": "Sub-Criteria", "Global Weight": "Global Weight"}, inplace=True)
                                    y_col = "Sub-Criteria"
                                    x_col = "Global Weight"
                                else:
                                    y_col = "중분류"
                                    x_col = "Global Weight"
                                fig_bar = px.bar(chart_bar_df, y=y_col, x=x_col, orientation='h', text_auto='.3f')
                                st.plotly_chart(fig_bar, use_container_width=True)
                            with col_chart2:
                                st.write(_("**그룹별 중요도 패턴 (Radar)**", "**Importance Pattern by Group (Radar)**"))
                                indiv_global_radar = []
                                all_ids_r = main_results_df['ID'].unique()
                                for rid in all_ids_r:
                                    m_row_rd = main_results_df[main_results_df['ID'] == rid].iloc[0]
                                    rtype_rd = m_row_rd['Type']
                                    grp_name_en = rtype_rd
                                    if is_english:
                                        grp_name_en = str(rtype_rd).replace("전문가", "Expert").replace("일반", "General").replace("공무원", "Public Official")
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
                        
                            # [바이올린 플롯] CR 분포 시각화 — 드롭다운 계층 선택
                            st.markdown("---")
                            st.write(_("**일관성 비율(CR) 분포 (Violin Plot)**", "**Consistency Ratio (CR) Distribution (Violin Plot)**"))
                            st.caption(_("계층을 선택하면 해당 수준 응답자들의 CR 분포를 표시합니다. 바이올린 폭 = 밀도, 내부 박스 = 중앙값·사분위수, 점 = 개별 응답자",
                                         "Select a tier to view respondent CR distribution. Width = density, box = median/IQR, dots = individual respondents"))

                            _t2_tier_opts_ko = ["대분류 (Main)", "중분류 (Sub)"]
                            _t2_tier_opts_en = ["Main Criteria", "Sub-Criteria"]
                            _t2_tier_opts = _t2_tier_opts_en if is_english else _t2_tier_opts_ko
                            _t2_sel_tier = st.selectbox(
                                _("📂 표시할 계층 선택", "📂 Select Tier to Display"),
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

                                # ── 선택: 대분류 ─────────────────────────────────
                                if _t2_sel_tier == _t2_tier_opts[0]:
                                    if not main_results_df.empty and "Final_CR" in main_results_df.columns:
                                        _t2_main_cr = main_results_df["Final_CR"].dropna().tolist()
                                        _t2_xlbl = _("대분류", "Main Criteria")
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
                                    _t2_xaxis_title = _("대분류", "Main Criteria")
                                    _t2_legend_title = _("대분류", "Main Criteria")

                                # ── 선택: 중분류 ─────────────────────────────────
                                else:
                                    for _t2_mf, _t2_info in sub_results_storage.items():
                                        _t2_sdf = _t2_info.get("df", None)
                                        if _t2_sdf is None or _t2_sdf.empty or "Final_CR" not in _t2_sdf.columns:
                                            continue
                                        _t2_cr_vals = _t2_sdf["Final_CR"].dropna().tolist()
                                        if len(_t2_cr_vals) < 2:
                                            continue
                                        _t2_xlbl = _(f"중분류({_t2_mf})", f"Sub({_t2_mf})")
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
                                    _t2_xaxis_title = _("대분류 (중분류 비교 CR)", "Main Criteria (Sub-Criteria Comparison CR)")
                                    _t2_legend_title = _("중분류", "Sub-Criteria")

                                if len(_fig_t2_vio.data) == 0:
                                    st.info(_("선택한 계층의 CR 데이터가 없거나 응답 수가 부족합니다.",
                                              "No CR data available for the selected tier or insufficient responses."))
                                else:
                                    _fig_t2_vio.add_hline(
                                        y=0.1, line_dash="dash", line_color="red",
                                        annotation_text=_("CR 임계값 (0.1)", "CR Threshold (0.1)"),
                                        annotation_position="top right"
                                    )
                                    _fig_t2_vio.update_layout(
                                        title=_(
                                            f"바이올린플롯 CR — {_t2_sel_tier}",
                                            f"Violin Plot CR — {_t2_sel_tier}"
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
                                st.warning(_(f"바이올린 플롯 생성 실패: {_e_t2_vio}", f"Violin plot generation failed: {_e_t2_vio}"))
    
                            # ── Fuzzy AHP TFN 삼각퍼지 그래프 (Tab1 결과 화면 직후) ──
                            if ahp_method == 'fuzzy':
                                st.markdown("---")
                                st.subheader(_(" 삼각퍼지수(TFN) 가중치 분포", " Triangular Fuzzy Number (TFN) Weight Distribution"))
                                st.caption(_("각 요인의 삼각퍼지수(L, M, U)와 비퍼지화된 Crisp 가중치를 시각화합니다.",
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
                                        # 삼각형 채우기 (반투명)
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
                                        # Crisp 가중치 수직 점선
                                        fig.add_trace(go.Scatter(
                                            x=[crisp, crisp],
                                            y=[0, 0.85],
                                            mode='lines',
                                            line=dict(color=color, width=1.5, dash='dot'),
                                            showlegend=False,
                                            hoverinfo='skip'
                                        ))
                                        # Crisp 마커
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
                                        xaxis_title=_("가중치 값 (Weight Value)", "Weight Value"),
                                        yaxis_title=_("소속도 (Membership Degree)", "Membership Degree"),
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
    
                                # 1) 메인 기준 TFN 그래프
                                if main_group_Si:
                                    st.plotly_chart(
                                        render_tfn_chart(main_group_Si, main_factors,
                                            _("▶ 대분류 (Main Criteria) 삼각퍼지 분포", "▶ Main Criteria TFN Distribution")),
                                        use_container_width=True
                                    )
    
                                    # TFN 수치 테이블
                                    tfn_table_rows = []
                                    for i, (l, m, u) in enumerate(main_group_Si):
                                        crisp = (l * m * u) ** (1/3)
                                        tfn_table_rows.append({
                                            _("요인", "Factor"): main_factors[i],
                                            "L (Lower)": l, "M (Most Likely)": m, "U (Upper)": u,
                                            "Crisp Weight": crisp,
                                            _("정규화 가중치", "Normalized Weight"): group_main_weights.iloc[i] if isinstance(group_main_weights, pd.Series) else group_main_weights[i]
                                        })
                                    st.dataframe(pd.DataFrame(tfn_table_rows).style.format(precision=4), use_container_width=True)
    
                                # 2) 세부 기준별 TFN 그래프
                                for parent_f, sub_info in sub_results_storage.items():
                                    if sub_info.get('group_Si'):
                                        st.markdown("---")
                                        st.plotly_chart(
                                            render_tfn_chart(sub_info['group_Si'], sub_info['factors'],
                                                _(f"▶ [{parent_f}] 세부항목 삼각퍼지 분포", f"▶ [{parent_f}] Sub-Criteria TFN Distribution")),
                                            use_container_width=True
                                        )
                                        sub_tfn_rows = []
                                        for i, (l, m, u) in enumerate(sub_info['group_Si']):
                                            crisp = (l * m * u) ** (1/3)
                                            sub_tfn_rows.append({
                                                _("요인", "Factor"): sub_info['factors'][i],
                                                "L (Lower)": l, "M (Most Likely)": m, "U (Upper)": u,
                                                "Crisp Weight": crisp,
                                                _("정규화 가중치", "Normalized Weight"): sub_info['weights'].iloc[i] if isinstance(sub_info['weights'], pd.Series) else sub_info['weights'][i]
                                            })
                                        st.dataframe(pd.DataFrame(sub_tfn_rows).style.format(precision=4), use_container_width=True)
    
                        with tab5:
                            st.markdown(_('<p style="color: red; font-weight: bold; font-size: 0.95rem; margin-bottom: 12px;"> 주의: 분석 결과가 웹상에 영구 저장되지 않으므로, 아래 다운로드 버튼을 눌러 결과물 엑셀 파일을 컴퓨터에 반드시 저장해 주세요.</p>',
                                          '<p style="color: red; font-weight: bold; font-size: 0.95rem; margin-bottom: 12px;">⚠️ Warning: Analysis results are not permanently stored on the web. Please make sure to click the download button below to save the Excel file to your computer.</p>'), unsafe_allow_html=True)
                            st.download_button(_("📥 결과 파일 다운로드 (Excel)", "📥 Download Results File (Excel)"), data=output_res.getvalue(), file_name="AHP_Result.xlsx", type="primary")
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
                        st.error(_("❌ 분석 시스템 내부 오류가 발생했습니다.", "❌ An internal error occurred in the analysis system."))
                        st.info(_(f"상세 에러 내용: {e}", f"Detailed error: {e}"))
                        with st.expander(_("🔍 상세 스택 트레이스", "🔍 Detailed Stack Trace")):
                            st.code(traceback.format_exc())
                        st.stop()
                else:
                    st.warning(message)
                    if role_chk == 'temp' and ("5개 표본" in message or "5 samples" in message):
                        st.markdown("---")
                        with st.container(border=True):
                            is_english = (st.session_state.get('lang', 'ko') == 'en')
                            if is_english:
                                st.markdown("###  Official User Upgrade & Unlimited Analysis")
                                st.markdown("Upgrading to an Official User **instantly removes the 5-sample limit** and allows unlimited access to all features.")
                                st.info("Upgrade to **Official User** to get unlimited access (2 months) for **$350.00 USD** via PayPal.")
                            
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
                                st.markdown(_("### 💳 정식 사용자 승격 및 무제한 분석", "### 💳 Upgrade to Official User for Unlimited Analysis"))
                                st.markdown("정식 사용자로 승격하시면 **표본 수 제한(5개)이 즉시 해제**되며 모든 기능을 무제한으로 사용하실 수 있습니다.")
                                st.info("정식 사용자로 즉시 승격하시려면 상단의 **서비스 요금** 탭을 클릭하여 결제를 진행해 주세요.")
            except Exception as e:
                st.error(f"파일 처리 오류 발생: {e}")
            
        st.markdown("---")
    
        if st.session_state.user_role == 'official':
            with st.expander(_("📂 나의 분석 보관함 (!중요) 반드시 컴퓨터에 백업해 주세요", "📂 My Analysis Storage (!Important: Please backup to your computer)")):
                my_analyses = get_user_analyses(st.session_state.user_id)
                if not my_analyses: st.info(_("저장된 분석 없음", "No saved analyses found."))
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
                                st.download_button("⬇️", fdata, fname, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key=f"dl_{a_id}", type="primary")
                        with col_List4:
                            if st.button("🗑", key=f"del_{a_id}"):
                                delete_analysis(a_id)
                                st.rerun()
    

    
    # -------------------------------------------------------------------------
    # [신규] 코딩 엑셀 양식 탭
    # -------------------------------------------------------------------------
    with main_tab_coding:
        # -------------------------------------------------------------------------
        # [신규] 온라인 설문지 제작 탭 (Tab 2) 상세 구현
        # -------------------------------------------------------------------------
        st.header(_("AHP 분석 모델 설정 및 코딩 양식 다운로드", "Setup AHP Decision Model & Download Coding Form"))
        
        saved_model = None
        if st.session_state.user_id is None:
            st.info(_(" **로그인 후** '나만의 분석 모델'을 만들 수 있습니다. (비로그인 상태에서도 샘플 데이터로 최종 분석 결과를 미리볼 수 있습니다)",
                      " **Log in** to create your own custom AHP models. (Even without logging in, you can preview results using sample data.)"))
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
        ko_default_main = "거버넌스, 계획타당성, 실현가능성, 사업효과"
        ko_default_subs = {
            "거버넌스": "행정지원, 지역공동체, 총괄사업관리자",
            "계획타당성": "현안적정성, 대안적정성, 목표구체성",
            "실현가능성": "부지확보, 사업구체화, 사업비적정성",
            "사업효과": "경제적효과, 사회적효과, 성과관리"
        }

        # [신규] 3계층(V3) 샘플 데이터 (스마트폰 구매 결정)
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

        ko_default_main_v3 = "기능성, 디자인, 경제성"
        ko_default_subs_v3 = {
            "기능성": "하드웨어, 소프트웨어",
            "디자인": "외관, 편의성",
            "경제성": "단말기가격, 유지비용"
        }
        ko_default_sub_subs_v3 = {
            "하드웨어": "카메라, 배터리, 프로세서",
            "소프트웨어": "운영체제, 기본앱",
            "외관": "색상, 재질",
            "편의성": "", 
            "단말기가격": "일시불, 할부",
            "유지비용": "통신요금, AS비용"
        }
    
    
        with st.expander(_(" 나의 분석 모델 만들기", " Create Custom AHP Model"), expanded=True):
            st.info(_("대항목과 세부항목을 입력하여 나만의 코딩 엑셀 양식을 생성하세요. 본 템플릿은 일반 AHP 및 퍼지 AHP(Fuzzy AHP) 분석에 공통으로 사용됩니다.\n\n현재 입력되어 있는 내용은 샘플 모델입니다. 이용자님의 AHP 모델로 수정할 수 있습니다.",
                      "Enter main criteria and sub-criteria to generate your custom Excel template. This template is used for both traditional AHP and Fuzzy AHP analysis.\n\nThe content below is a sample model. You can modify it with your own AHP model."))
            
            # 계층 구조 설정 (2계층 기준과 동일하게 전체 공개)
            tier_level = 2
            st.markdown("#####  계층 구조 설정")
            tier_choice = st.radio(
                _("계층 레벨을 선택하세요.", "Select Hierarchy Level."),
                [_("2계층 (대분류 - 중분류)", "2-Tier (Main - Sub)"),
                 _("3계층 (대분류 - 중분류 - 소분류)", "3-Tier (Main - Sub - Sub-sub)")],
                index=0,
                horizontal=True,
                key="tab1_tier_choice"
            )
            if _("3계층", "3-Tier") in tier_choice:
                tier_level = 3
            st.markdown("---")
                
            # [신규] tier_level에 따라 샘플 데이터 스위칭
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
                    
            main_criteria_input = st.text_input(_("대항목 (Main Criteria, 콤마 구분)", "Main Criteria (comma-separated)"), value=default_main)
            main_criteria_list = [x.strip() for x in main_criteria_input.split(',') if x.strip()]
            
            model_structure = {}
            sub_sub_structure = {}
            if main_criteria_list:
                for mc in main_criteria_list:
                    d_val = default_subs.get(mc, "")
                    if isinstance(d_val, list): d_val = ", ".join(d_val)
                    sub_input = st.text_input(_(f"'{mc}'의 세부항목", f"Sub-criteria for '{mc}'"), value=d_val, key=f"tab1_sub_{mc}")
                    sub_list = [x.strip() for x in sub_input.split(',') if x.strip()]
                    model_structure[mc] = sub_list
                    
                    if tier_level == 3 and sub_list:
                        with st.expander(_(f"▶ '{mc}'의 소분류 (Sub-sub-criteria) 입력", f"▶ Enter Sub-sub-criteria for '{mc}'"), expanded=True):
                            st.info(_("💡 **혼합 계층 안내**: 소분류(3계층)가 없는 항목은 **비워두시면 자동으로 2계층 가중치로 계산**됩니다.", "💡 **Mixed-Tier Guide**: If a sub-criterion has no sub-sub-criteria, **leave it blank to automatically calculate as a 2-tier weight**."))
                            for sub_c in sub_list:
                                sub_sub_input = st.text_input(
                                    f"▶ '{sub_c}'의 소분류 (콤마 구분)", 
                                    value=default_sub_subs.get(sub_c, ""),
                                    placeholder="예: 항목1, 항목2 (※ 하위 요인이 없다면 비워두세요)",
                                    help="입력칸을 비워두면 이 항목은 자동으로 2계층 구조로 간주되어 분석됩니다.",
                                    key=f"tab1_sub_sub_{sub_c}"
                                )
                                parsed_sub_subs = [x.strip().replace("_", " ") for x in sub_sub_input.split(",") if x.strip()]
                                if parsed_sub_subs:
                                    sub_sub_structure[sub_c] = parsed_sub_subs
            
            col1, col2 = st.columns(2)
            with col1:
                generate_clicked = st.button(_("1️⃣ 설정한 모델로 AHP 코딩 엑셀 양식 생성", "1️⃣ Generate Excel Template with this Model"), use_container_width=True)
            
            if generate_clicked:
                if st.session_state.user_id is None:
                    st.warning(_("코딩 엑셀 양식 생성 및 다운로드는 로그인한 사용자(무료 회원 포함)만 이용 가능합니다. 왼쪽 메뉴에서 로그인하거나 회원가입을 해주세요.", "Generating and downloading Excel templates is only available to logged-in users (including free members). Please log in or sign up from the left menu."))
                elif not main_criteria_list:
                    st.error(_("대항목 입력 필요", "Main criteria input is required"))
                else:
                    current_model = {'main': main_criteria_input, 'subs': model_structure, 'sub_subs': sub_sub_structure, 'Tier_Level': tier_level}
                    save_user_model(st.session_state.user_id, current_model)
                    st.toast(_("모델 저장 완료", "Model successfully saved"))
                    
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
                            
                        # 3계층 시트 생성
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
                            label=_("2️⃣ 📥 코딩 엑셀 양식 다운로드", "2️⃣ 📥 Download Excel Template"),
                            data=output_template,
                            file_name="AHP_Master_Template.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True,
                            type="primary"
                        )
                    
                    st.info(_("💡 **안내:** 1번 버튼을 눌러 모델을 생성 및 저장했습니다. 우측의 2번 버튼을 클릭하여 컴퓨터에 코딩 엑셀 양식 파일을 저장하세요.", 
                              "💡 **Info:** The model has been generated and saved. Click the 2nd button on the right to download the Excel template file to your computer."))
    
                    st.markdown(_("""
                    ---
                    ### 📝 데이터 입력 가이드
                    1. **엑셀 파일 열기**: 위 버튼을 눌러 다운로드한 엑셀 파일을 실행합니다.
                    2. **쌍대비교 데이터 입력**:
                        - **왼쪽** 항목이 더 중요하면: **음수** 입력 (예: -3)
                        - **오른쪽** 항목이 더 중요하면: **양수** 입력 (예: 3)
                        - **동등**하면: `1` 입력
                    3. **필수 정보 입력**: A열(ID), **B열(Type)에 그룹명 입력 (예: 전문가, 주민 등)**
                    """,
                    """
                    ---
                    ### 📝 Data Input Guide
                    1. **Open the Excel file**: Run the Excel template downloaded above.
                    2. **Enter pairwise comparisons**:
                        - If the **left** item is more important: enter a **negative** value (e.g., -3)
                        - If the **right** item is more important: enter a **positive** value (e.g., 3)
                        - If they are **equal**: enter `1`
                    3. **Required Information**: Column A (ID), **Column B (Type) for group names (e.g., Expert, Public, etc.)**
                    """))
                    img_file = _("ahp_input_guide.png", "ahp_input_guide_en.png")
                    caption_text = _("[참고] 설문 응답을 엑셀에 입력하는 방법", "[Reference] How to enter survey responses into Excel")
                    if os.path.exists(img_file):
                        st.image(img_file, caption=caption_text)
    

    with main_tab2:
        # @st.fragment: 위젯 변경 시 이 영역만 재실행 (성능 최적화)
        @st.fragment
        def _survey_setup_fragment():
            st.header(_("AHP 온라인 설문 자동 생성 및 배포", "AHP Online Survey Auto-Generator & Deployer"))
            box_style = """
            <div style="background-color: #f8f9fc; border: none; border-radius: 8px; padding: 16px 20px; margin-bottom: 20px; color: #1e293b; font-size: 0.95em; line-height: 1.6; box-shadow: 0 2px 8px rgba(0,0,0,0.04);">
            """
            if st.session_state.user_id is None:
                msg = _(
                    "<strong>비회원도 온라인 설문 폼을 미리 작성해 볼 수 있습니다.</strong><br>"
                    "작성하신 내용은 좌측 사이드바에서 회원가입 및 로그인을 하시면 그대로 유지되어 바로 배포하실 수 있습니다. (무료 회원도 기능 제한 없이 모든 기능 사용 가능)<br><br>"
                    "응답 데이터는 연동하신 구글 스프레드시트에 저장됩니다. 배포 전 데이터가 정상 기록되는지 반드시 테스트해 주세요.<br>"
                    "⚠️ <strong>주의:</strong> 연동 해제나 네트워크 장애 등으로 인한 데이터 유실에 대해서는 책임지지 않으므로, 중요 데이터는 주기적으로 백업 및 보관하시기 바랍니다.",
                    
                    "<strong>Non-members can also preview and fill out the online survey form.</strong><br>"
                    "Once you sign up and log in from the left sidebar, the contents you have written will be maintained and you can deploy immediately. (Free members can also use all features without restriction)<br><br>"
                    "Response data is stored in your linked Google Spreadsheet. Please test data recording before deploying the survey.<br>"
                    "⚠️ <strong>Caution:</strong> We are not responsible for data loss due to unlinking or network failures. Please backup your important data periodically."
                )
            else:
                msg = _(
                    "응답 데이터는 연동하신 구글 스프레드시트에 저장됩니다. 배포 전 데이터가 정상 기록되는지 반드시 테스트해 주세요.<br>"
                    "⚠️ <strong>주의:</strong> 연동 해제나 네트워크 장애 등으로 인한 데이터 유실에 대해서는 책임지지 않으므로, 중요 데이터는 주기적으로 백업 및 보관하시기 바랍니다.",
                    
                    "Response data is stored in your linked Google Spreadsheet. Please test data recording before deploying the survey.<br>"
                    "⚠️ <strong>Caution:</strong> We are not responsible for data loss due to unlinking or network failures. Please backup your important data periodically."
                )
            st.markdown(f"{box_style}{msg}</div>", unsafe_allow_html=True)

            # [가이드 삽입]
            with st.expander(_("📖 온라인 설문 자동 생성 및 배포 이용 가이드 (클릭하여 펼치기)", "📖 Online Survey Auto-Generation & Deployment Guide (Click to expand)"), expanded=False):
                try:
                    import os
                    guide_file = "guide_en.html" if st.session_state.lang == "en" else "guide.html"
                    with open(os.path.join("static", guide_file), "r", encoding="utf-8") as f:
                        guide_html = f.read()
                    import streamlit.components.v1 as components
                    components.html(guide_html, height=720, scrolling=True)
                except Exception as e:
                    st.error("가이드 파일을 불러올 수 없습니다.")

            # (Dashboard moved to main_tab3 below)
            pass

            st.divider()
        
            # ------------------------------------------------------------
            # 0. 설문 관리 (1인 1설문 모드)
            # ------------------------------------------------------------
            st.subheader(_("섹션 0: 내 설문 관리", "Section 0: My Survey Management"))

            # Initialize states
            if 'editing_survey_id' not in st.session_state:
                st.session_state.editing_survey_id = None
            if 'survey_auto_loaded' not in st.session_state:
                st.session_state.survey_auto_loaded = False

            # Check existing surveys (SQLite와 구글 시트 모두 조회하여 병합) — 세션 캐싱
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
                    if "type_questions" in demo:
                        tqs = []
                        for tq in demo["type_questions"]:
                            tqs.append({"q": tq["q"], "opts": ", ".join(tq["opts"])})
                        st.session_state.edit_type_questions = tqs
                    st.session_state.edit_demo_gender = demo.get("gender", False)
                    st.session_state.edit_demo_aff = demo.get("affiliation", False)
                    st.session_state.edit_demo_email = demo.get("email", False)
                    st.session_state.edit_demo_name = demo.get("name", False)
                    st.session_state.edit_demo_age = demo.get("age", False)
                    st.session_state.edit_demo_exp = demo.get("experience", False)
                    st.session_state.edit_age_type = demo.get("age_type", "개방형 (숫자 직접 입력)")
                    st.session_state.edit_exp_type = demo.get("experience_type", "개방형 (숫자 직접 입력)")
                
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

            @st.dialog(_("🚨 [경고] 기존 설문 영구 삭제 안내", "🚨 [Warning] Permanent Deletion of Existing Survey"))
            def confirm_new_survey():
                st.error(_("새로운 설문을 작성하시면 기존 연동된 구글 시트에 저장된 **모든 데이터(설문 구조, 문항, 수집된 전체 응답 결과)가 즉시 삭제되며 절대 복구할 수 없습니다.**", "If you create a new survey, **ALL data saved in the linked Google Sheet (survey structure, questions, collected responses) will be immediately deleted and CANNOT be recovered.**"))
                st.info(_("💡 **데이터 보존 안내:** 기존 설문의 응답 결과 보존을 원하신다면, 삭제에 동의하시기 전에 구글 스프레드시트에 접속하여 **[파일] -> [다운로드]** 메뉴를 통해 엑셀(.xlsx) 파일 등으로 백업본을 사용자 컴퓨터에 미리 다운로드해 두시기 바랍니다.", "💡 **Data Preservation Guide:** If you wish to keep the existing responses, please go to the Google Spreadsheet and use the **[File] -> [Download]** menu to download a backup copy (e.g., .xlsx) to your computer before agreeing to delete."))
                agree = st.checkbox(_("네, 기존 데이터 백업을 완료했거나 불필요하며, 모든 데이터 삭제에 동의합니다.", "Yes, I have backed up or do not need the existing data, and I agree to delete all data."))
                col1, col2 = st.columns(2)
                with col1:
                    if st.button(_("❌ 취소", "❌ Cancel"), use_container_width=True):
                        st.rerun()
                with col2:
                    if st.button(_("✅ 동의 및 초기화", "✅ Agree & Initialize"), type="primary", use_container_width=True, disabled=not agree):
                        with st.spinner(_("기존 데이터를 삭제하는 중입니다...", "Deleting existing data...")):
                            from survey_manager import delete_admin_survey
                            if user_surveys:
                                delete_admin_survey(user_surveys[0][0], st.session_state.user_id)
                            st.session_state.editing_survey_id = None
                            keys_to_clear = [k for k in st.session_state.keys() if k.startswith('edit_')]
                            for k in keys_to_clear:
                                del st.session_state[k]
                            st.session_state.survey_auto_loaded = False
                        st.success(_("완료되었습니다. 화면이 새로고침됩니다.", "Completed. The screen will be refreshed."))
                        import time
                        time.sleep(1.5)
                        st.rerun()

            if has_survey:
                st.success(_(f" 현재 배포된 설문이 있습니다. 자동으로 불러왔습니다: **{user_surveys[0][1]}**", f" A deployed survey exists. Automatically loaded: **{user_surveys[0][1]}**"))
                st.info(_("아래 폼에서 내용을 수정하신 뒤 하단의 **[배포 및 DB 연동 (수정 내용 적용)]** 버튼을 누르시면 기존 시트에 내용이 덮어씌워집니다.", "If you modify the form below and click the **[Deploy & Link DB (Apply Modifications)]** button at the bottom, the existing sheet will be overwritten."))
                if st.button(_("✨ 처음부터 새 설문 작성하기 (기존 데이터 삭제)", "✨ Start a new survey from scratch (Delete existing data)"), type="secondary"):
                     confirm_new_survey()
            else:
                st.info(_(" 작성 중인 새 설문입니다. 내용을 작성한 뒤 배포해 주세요.", " This is a new survey in progress. Please fill out the contents and deploy."))
                if st.button(_("✨ 폼 내용 모두 지우기 (초기화)", "✨ Clear all form contents (Initialize)"), type="secondary"):
                    st.session_state.editing_survey_id = None
                    keys_to_clear = [k for k in st.session_state.keys() if k.startswith('edit_')]
                    for k in keys_to_clear:
                        del st.session_state[k]
                    st.rerun()

            st.divider()

            from survey_manager import create_survey_sheet

            # 7개 섹션 설문지 생성 폼 구성
            # 섹션 1: 기본 정보
            st.subheader(_("섹션 1: 설문 기본 정보 설정", "Section 1: Survey Basic Info Setup"))
            default_survey_title = _("제조용 협동로봇 도입 요인 중요도 분석을 위한 전문가 AHP 설문", "Expert AHP Survey on the Importance of Factors for Adopting Manufacturing Collaborative Robots")
            survey_title = st.text_input(_("설문지 제목", "Survey Title"), value=st.session_state.get("edit_title", default_survey_title))
        
            default_survey_desc_ko = """[조사 목적 및 안내문]

    안녕하십니까?
    본 설문조사는 [연구/프로젝트 주제]에 관한 주요 요인들의 상대적 중요도를 도출하기 위해 전문가(또는 실무자) 여러분의 고견을 수렴하고자 마련되었습니다. 
    바쁘시더라도 잠시 시간을 내어 귀하의 귀중한 의견을 응답해 주시면 연구에 큰 도움이 될 것입니다.

    ■ 조사 목적 : [연구/프로젝트 목적 기재]
    ■ 조사 내용 : [조사 대상 요인] 간의 AHP(쌍대비교) 평가
    ■ 조사 기간 : 202X년 X월 X일 ~ 202X년 X월 X일
    ■ 개인정보 보호 : 
    본 조사를 통해 수집된 모든 자료는 통계법 제33조(비밀의 보호)에 의거하여 철저히 보호되며, 오직 연구 및 통계 분석 목적으로만 활용됩니다.
응답해주신 개인 정보 및 개별 응답 결과는 절대 외부로 유출되지 않음을 약속드립니다.

    귀하의 소중한 참여에 깊은 감사를 드립니다.

    - 연구 책임자 : [이름 기재]
    - 문의처 : [연락처 또는 이메일 기재]"""

            default_survey_desc_en = """[Survey Purpose & Instructions]

    Greetings,
    This survey is designed to collect the valuable opinions of experts (or practitioners) to derive the relative importance of key factors regarding [Research/Project Topic].
    Your participation will be of great help to our research, and we would deeply appreciate it if you could take a moment out of your busy schedule to respond.

    ■ Purpose : [Enter Research/Project Purpose]
    ■ Content : AHP (Pairwise Comparison) evaluation among [Target Factors]
    ■ Period : 202X-XX-XX ~ 202X-XX-XX
    ■ Privacy Policy : 
    All data collected through this survey will be strictly protected in accordance with privacy laws and used solely for research and statistical analysis purposes. We promise that your personal information and individual responses will never be leaked externally.

    Thank you very much for your valuable participation.

    - Lead Researcher : [Enter Name]
    - Contact : [Enter Phone or Email]"""

            survey_desc = st.text_area(_("조사 목적 및 안내문", "Survey Purpose & Instructions"), value=st.session_state.get("edit_desc", _(default_survey_desc_ko, default_survey_desc_en)), height=350)
            if st.session_state.user_id:
                if "@" in st.session_state.user_id:
                    default_admin_email = st.session_state.user_id
                elif st.session_state.user_id == "shjeon":
                    default_admin_email = "jeon080423@gmail.com"
                else:
                    default_admin_email = f"{st.session_state.user_id}@ahpmaster.com"
            else:
                default_admin_email = "temp@ahpmaster.com"
            survey_admin_email = default_admin_email

            st.divider()

            # 섹션 1.5: 응답자 수집 정보 및 그룹 분류 설정
            st.subheader(_("섹션 1.5: 응답자 수집 정보 및 그룹 분류", "Section 1.5: Respondent Info & Grouping"))

            # 그룹 분류 문항 설정
            with st.container(border=True):
                st.markdown(_("** 그룹 분류 문항 설정**", "** Group Classification Setup**"))
                
                default_type_q = _("귀하의 소속은 어떻게 되십니까?", "What is your affiliation?")
                default_type_opts = _("전문가, 일반, 공무원, 기타", "Expert, General, Public Official, Other")
                
                if "edit_type_questions" not in st.session_state:
                    legacy_q = st.session_state.get("edit_type_question")
                    legacy_opts = st.session_state.get("edit_type_options")
                    
                    init_q = legacy_q if legacy_q and legacy_q != "귀하의 소속은 어떻게 되십니까?" else default_type_q
                    init_opts = legacy_opts if legacy_opts and legacy_opts != "전문가, 일반, 공무원, 기타" else default_type_opts
                    st.session_state["edit_type_questions"] = [{"q": init_q, "opts": init_opts}]

                type_questions_state = st.session_state["edit_type_questions"]
                num_types = len(type_questions_state)
                
                col1, col2, col3 = st.columns([6, 2, 2])
                with col2:
                    if st.button(_("➕ 문항 추가", "➕ Add Question"), use_container_width=True, disabled=num_types >= 3):
                        st.session_state["edit_type_questions"].append({"q": "", "opts": ""})
                        st.rerun()
                with col3:
                    if st.button(_("➖ 문항 삭제", "➖ Remove"), use_container_width=True, disabled=num_types <= 1):
                        st.session_state["edit_type_questions"].pop()
                        st.rerun()
                
                
                type_questions = []
                for i in range(num_types):
                    st.markdown(f"**{i+1}.**")
                    if i == 0:
                        q_label = _("그룹 분류 질문 제목", "Group Classification Question Title")
                        opts_label = _("그룹 분류 보기 옵션 (콤마로 구분)", "Group Classification Options (comma-separated)")
                    else:
                        q_label = _("추가 설문 문항", "Additional Survey Question")
                        opts_label = _("추가 문항 보기 옵션 (콤마로 구분)", "Additional Question Options (comma-separated)")
                        
                    q_val = st.text_input(q_label + f" ({i+1})", value=type_questions_state[i]["q"], key=f"tq_q_{i}")
                    opts_val = st.text_input(opts_label + f" ({i+1})", value=type_questions_state[i]["opts"], key=f"tq_opts_{i}")
                    
                    type_questions_state[i]["q"] = q_val
                    type_questions_state[i]["opts"] = opts_val
                    
                    type_questions.append({
                        "q": q_val,
                        "opts": [x.strip() for x in opts_val.split(",") if x.strip()]
                    })
                
                type_question = type_questions[0]["q"] if type_questions else ""
                type_options = ", ".join(type_questions[0]["opts"]) if type_questions else ""


            # 인구통계학 정보 설정
            with st.container(border=True):
                st.markdown(_("** 인구통계학적 문항 수집 설정**", "** Demographic Questions Setup**"))
                demo_name = st.checkbox(_("이름 수집", "Collect Name"), value=st.session_state.get("edit_demo_name", False))
                demo_gender = st.checkbox(_("성별 수집", "Collect Gender"), value=st.session_state.get("edit_demo_gender", True))
                demo_email = st.checkbox(_("이메일 수집", "Collect Email"), value=st.session_state.get("edit_demo_email", True))

                st.markdown("<hr style='margin: 0.5rem 0; border: none; border-top: 1px solid #e2e8f0;'>", unsafe_allow_html=True)

                demo_age = st.checkbox(_("연령 수집", "Collect Age"), value=st.session_state.get("edit_demo_age", True))
                age_type = "개방형 (숫자 직접 입력)"
                if demo_age:
                    age_type_options = [_("개방형 (숫자 직접 입력)", "Open-ended (Type Number)"), _("10세 단위 선택형", "Multiple Choice (10-year intervals)")]
                    age_type = st.radio(_("연령 수집 방식", "Age Collection Method"), age_type_options, index=0 if st.session_state.get("edit_age_type", "개방형 (숫자 직접 입력)") == "개방형 (숫자 직접 입력)" else 1, horizontal=True, key="survey_age_type_setup")

                st.markdown("<hr style='margin: 0.5rem 0; border: none; border-top: 1px solid #e2e8f0;'>", unsafe_allow_html=True)

                demo_exp = st.checkbox(_("경력년수 수집", "Collect Years of Experience"), value=st.session_state.get("edit_demo_exp", True))
                exp_type = "개방형 (숫자 직접 입력)"
                if demo_exp:
                    exp_type_options = [_("개방형 (숫자 직접 입력)", "Open-ended (Type Number)"), _("5년 단위 선택형", "Multiple Choice (5-year intervals)")]
                    exp_type = st.radio(_("경력년수 수집 방식", "Experience Collection Method"), exp_type_options, index=0 if st.session_state.get("edit_exp_type", "개방형 (숫자 직접 입력)") == "개방형 (숫자 직접 입력)" else 1, horizontal=True, key="survey_exp_type_setup")

            demographics_settings = {
                "name": demo_name,
                "age": demo_age,
                "age_type": age_type,
                "gender": demo_gender,
                "experience": demo_exp,
                "experience_type": exp_type,
                "affiliation": False,  # 소속 수집 삭제
                "email": demo_email,
                "type_question": type_question,
                "type_options": [x.strip() for x in type_options.split(",") if x.strip()],
                "type_questions": type_questions
            }

            st.markdown("<hr style='margin: 0.5rem 0; border: none; border-top: 1px solid #e2e8f0;'>", unsafe_allow_html=True)

            # 섹션 2: AHP 모델 계층구조 입력 폼
            st.subheader(_("섹션 2: AHP 요인 계층구조 및 문항 설정", "Section 2: AHP Criteria Hierarchy & Question Setup"))

            # 계층 구조 선택 (2계층 기준과 동일하게 전체 공개)
            tier_level = 2
            st.markdown("---")
            st.markdown(_("#####  계층 구조 레벨 선택", "#####  Select Hierarchy Level"))
            tier_choice_tab2 = st.radio(
                _("설문 모델의 계층 깊이를 선택하세요.", "Select the hierarchy depth for your survey model."),
                [_("2계층 (대분류 ➔ 중분류)", "2-Tier (Main ➔ Sub)"),
                 _("3계층 (대분류 ➔ 중분류 ➔ 소분류)", "3-Tier (Main ➔ Sub ➔ Sub-sub)")],
                index=0,
                horizontal=True,
                key="tab2_tier_choice"
            )
            if _("3계층", "3-Tier") in tier_choice_tab2:
                tier_level = 3
            st.markdown("---")

            st.info(_(
                "💡 현재 입력된 요인은 **예시**일 뿐이며, 사용자의 연구 모델에 맞추어 내용을 모두 수정하여 사용할 수 있습니다.\n\n"
                "- 대분류 및 하위 요인은 반드시 **쉼표(,)** 로 구분하여 입력해 주세요.\n"
                "- 요인명에 언더바(`_`) 기호는 시스템 내부 처리와 충돌하므로 사용할 수 없습니다. (입력 시 자동으로 공백으로 변환됩니다.)",
                "💡 The current criteria are just **examples**. You can freely modify them to fit your research model.\n\n"
                "- Separate Main and Sub criteria using **commas(,)**.\n"
                "- Do not use underscores (`_`) in criteria names. (They will be automatically converted to spaces.)"
            ))

            default_tab2_main = _("기능성, 디자인, 경제성", "Functionality, Design, Economy") if tier_level == 3 else _("기술 요인, 조직 요인, 환경 요인, 혁신 요인", "Technological, Organizational, Environmental, Innovational")
            main_input = st.text_input(_("대항목 (Main Criteria)", "Main Criteria"), value=st.session_state.get("edit_main_input", default_tab2_main))
            main_list = [x.strip().replace("_", " ") for x in main_input.split(",") if x.strip()]

            model_structure = {"main": main_list, "subs": {}}
            if tier_level == 3:
                model_structure["sub_subs"] = {}

            for i, mc in enumerate(main_list):
                # 기본값 제안 (기존 양승훈 협동로봇 및 3계층 스마트폰 구매 결정)
                default_sub_val = ""
                if mc in ["기술 요인", "Technological"]: default_sub_val = _("상대적이점, 호환성, 안전성, 서비스지원", "Relative Advantage, Compatibility, Security, Service Support")
                elif mc in ["조직 요인", "Organizational"]: default_sub_val = _("경영진지원, 기술준비도, 금융자원, 교육훈련", "Top Management Support, Tech Readiness, Financial Resources, Training")
                elif mc in ["환경 요인", "Environmental"]: default_sub_val = _("정부지원, 경쟁압력, 인력난, 외부지원", "Gov Support, Competitive Pressure, Labor Shortage, External Support")
                elif mc in ["혁신 요인", "Innovational"]: default_sub_val = _("경영진의 혁신성, 변화수용태도, 스마트팩토리수준, 지식정도", "Management Innovativeness, Change Acceptance, Smart Factory Level, Knowledge Level")
                elif mc in ["기능성", "Functionality"]: default_sub_val = _("하드웨어, 소프트웨어", "Hardware, Software")
                elif mc in ["디자인", "Design"]: default_sub_val = _("외관, 편의성", "Appearance, Usability")
                elif mc in ["경제성", "Economy"]: default_sub_val = _("단말기가격, 유지비용", "Device Price, Maintenance Cost")

                sub_input = st.text_input(_(f"'{mc}'의 하위 요인 (Sub-criteria)", f"Sub-criteria for '{mc}'"), value=st.session_state.get("edit_sub_inputs", {}).get(mc, default_sub_val))
                subs_list = [x.strip().replace("_", " ") for x in sub_input.split(",") if x.strip()]
                model_structure["subs"][mc] = subs_list

                # [신규] 3계층 선택 시 소분류 입력 필드 동적 생성
                if tier_level == 3 and subs_list:
                    with st.expander(_(f"↳ '{mc}' 하위의 소분류 (Sub-sub-criteria) 입력", f"↳ Enter Sub-sub-criteria under '{mc}'"), expanded=True):
                        st.info(_("💡 **혼합 계층 안내**: 소분류(3계층)가 없는 항목은 **비워두시면 자동으로 2계층 가중치로 계산**됩니다.", "💡 **Mixed-Tier Guide**: If a sub-criterion has no sub-sub-criteria, **leave it blank to automatically calculate as a 2-tier weight**."))
                        for sub_c in subs_list:
                            sub_sub_val = "" # 3계층 기본값은 빈칸
                            if sub_c in ["하드웨어", "Hardware"]: sub_sub_val = _("카메라, 배터리, 프로세서", "Camera, Battery, Processor")
                            elif sub_c in ["소프트웨어", "Software"]: sub_sub_val = _("운영체제, 기본앱", "OS, Default Apps")
                            elif sub_c in ["외관", "Appearance"]: sub_sub_val = _("색상, 재질", "Color, Material")
                            elif sub_c in ["단말기가격", "Device Price"]: sub_sub_val = _("일시불, 할부", "Lump Sum, Installment")
                            elif sub_c in ["유지비용", "Maintenance Cost"]: sub_sub_val = _("통신요금, AS비용", "Telecom Fee, A/S Cost")
                        
                            sub_sub_input = st.text_input(
                                f"👉 '{sub_c}'의 하위 요인 (쉼표 구분)", 
                                value=st.session_state.get("edit_sub_sub_inputs", {}).get(sub_c, sub_sub_val),
                                placeholder="예: 항목1, 항목2 (※ 하위 요인이 없다면 비워두세요)",
                                help="입력칸을 비워두면 이 항목은 자동으로 2계층 구조로 간주되어 분석됩니다.",
                                key=f"sub_sub_{sub_c}"
                            )
                            # 소분류가 입력된 경우에만 저장, 없으면 무시
                            parsed_sub_subs = [x.strip().replace("_", " ") for x in sub_sub_input.split(",") if x.strip()]
                            if parsed_sub_subs:
                                model_structure["sub_subs"][sub_c] = parsed_sub_subs

            st.caption(_("※ 쌍대비교 시작 전 응답자가 전반적 요인 순위를 매기는 '사전 중요도 순위 지정 문항'은 자동으로 설문에 포함됩니다.", "※ A 'Prior Importance Ranking Question', where respondents rank the overall criteria before starting pairwise comparisons, is automatically included in the survey."))

            st.divider()

            # 섹션 3: 요인 조작적 정의 설정
            st.subheader(_("섹션 3: 요인별 상세 설명 (조작적 정의)", "Section 3: Detailed Description per Criteria (Operational Definition)"))
            st.info(_("응답자가 요인 개념을 직관적으로 파악할 수 있도록 상세 설명을 기술해 주십시오.", "Please provide detailed descriptions so respondents can intuitively understand each criteria concept."))
            definitions_map = {}
            for i, mc in enumerate(main_list):
                # 대분류명 파란색 볼드 및 이모티콘을 이용해 대조 설정
                st.markdown(_(f"####  :blue[**대분류: {mc}**]", f"####  :blue[**Main Criteria: {mc}**]"))
                default_main_def = ""
                if mc in ["기술 요인", "Technological"]: default_main_def = _("협동로봇 도입 시 기술적 성능, 호환성, 안전성 및 기술 지원 등 기술 측면의 요인", "Factors related to the technological aspect such as technical performance, compatibility, safety, and technical support.")
                elif mc in ["조직 요인", "Organizational"]: default_main_def = _("협동로봇 도입과 관련된 조직 내부의 역량, 경영진 지원, 재무 및 교육 상태 요인", "Factors related to the internal capabilities of the organization, top management support, financial and training status.")
                elif mc in ["환경 요인", "Environmental"]: default_main_def = _("정부 지원, 산업 내 경쟁 압력, 구인난 및 외부 협력 등 외부 환경적 요인", "External environmental factors such as government support, competitive pressure within the industry, labor shortage, and external cooperation.")
                elif mc in ["혁신 요인", "Innovational"]: default_main_def = _("경영진의 혁신 지향성, 구성원의 변화 수용도 및 스마트 팩토리 지식/기술 수준 요인", "Factors such as the management's innovation orientation, members' acceptance of change, and smart factory knowledge/skill levels.")

                edit_def_val = st.session_state.get("edit_definitions", {}).get(mc)
                val_to_use = edit_def_val if edit_def_val is not None else (default_main_def or _(f"{mc}에 대한 전반적 요소를 설명합니다.", f"Overall description for {mc}."))
                val_to_use = translate_definition_if_default(mc, val_to_use)

                definitions_map[mc] = st.text_input(
                    _(f"👉 [{mc}] 요인의 전체적인 설명 입력", f"👉 Enter overall description for [{mc}]"),
                    value=val_to_use,
                    key=f"def_main_{mc}_{i}"
                )

                # 중분류들은 연관 관계를 묶을 수 있도록 시각적으로 구분된 테두리 컨테이너 안에 배치
                with st.container(border=True):
                    for j, sc in enumerate(model_structure["subs"].get(mc, [])):
                        # 기본 양승훈 설문 정의 적용
                        default_def = ""
                        if sc in ["상대적이점", "Relative Advantage"]: default_def = _("도입대상 협동로봇간의 상대적 이점", "Relative advantage among the collaborative robots targeted for adoption.")
                        elif sc in ["호환성", "Compatibility"]: default_def = _("기존 설비나 타사 협동로봇과의 연결성", "Connectivity with existing equipment or third-party collaborative robots.")
                        elif sc in ["안전성", "Security"]: default_def = _("작업자와 같은 공간에서 안전 펜스 없이 작업할 때의 인적 사고 예방 수준", "Level of human accident prevention when working in the same space as operators without safety fences.")
                        elif sc in ["서비스지원", "Service Support"]: default_def = _("공급사의 기술 및 A/S 지원 정도", "Degree of technical and A/S support from the supplier.")
                        elif sc in ["경영진지원", "Top Management Support"]: default_def = _("경영진의 도입 의지 및 경영철학 반영도", "The management's willingness to adopt and the degree to which management philosophy is reflected.")
                        elif sc in ["기술준비도", "Tech Readiness"]: default_def = _("조직원의 로봇 활용 기술 준비 수준", "The level of technical readiness of organizational members to utilize robots.")
                        elif sc in ["금융자원", "Financial Resources"]: default_def = _("로봇 구입을 위한 자본 여력 및 자금 조달 편의성", "Capital capacity and financing convenience for purchasing robots.")
                        elif sc in ["교육훈련", "Training"]: default_def = _("기술 향상을 위한 위탁/사내 교육 프로그램 유무", "Availability of external/internal training programs for skill improvement.")
                        elif sc in ["정부지원", "Gov Support"]: default_def = _("협동로봇 도입을 활성화하기 위한 정부의 재정 지원 및 보조금 혜택 정도", "Degree of government financial support and subsidy benefits to promote the adoption of collaborative robots.")
                        elif sc in ["경쟁압력", "Competitive Pressure"]: default_def = _("동종 업계 또는 경쟁사의 협동로봇 도입에 따른 경쟁적 압박 정도", "Degree of competitive pressure due to the adoption of collaborative robots by peers or competitors.")
                        elif sc in ["인력난", "Labor Shortage"]: default_def = _("제조 현장의 구인난 및 생산 인력 수급의 어려움 수준", "Level of difficulty in finding labor and supplying production personnel at the manufacturing site.")
                        elif sc in ["외부지원", "External Support"]: default_def = _("로봇 공급사 외의 외부 컨설팅, 연구기관 등의 기술적/교육적 지원", "Technical/educational support from external consulting, research institutes, etc., other than the robot supplier.")
                        elif sc in ["경영진의 혁신성", "Management Innovativeness"]: default_def = _("새로운 제조 기술 및 로봇 도입에 대한 최고경영자의 적극적인 의지", "The top management's active willingness to adopt new manufacturing technologies and robots.")
                        elif sc in ["변화수용태도", "Change Acceptance"]: default_def = _("신규 장비 및 작업 프로세스 변화에 대한 구성원들의 수용 및 협조 태도", "Members' acceptance and cooperative attitude towards changes in new equipment and work processes.")
                        elif sc in ["스마트팩토리수준", "Smart Factory Level"]: default_def = _("공장 내 디지털화, 정보시스템(MES 등) 및 자동화 기술의 현재 구축 수준", "Current level of implementation of digitalization, information systems (MES, etc.), and automation technology in the factory.")
                        elif sc in ["지식정도", "Knowledge Level"]: default_def = _("협동로봇 활용 및 유지 관리에 필요한 조직 내 전문 지식 수준", "Level of internal expertise required for the utilization and maintenance of collaborative robots.")

                        edit_sub_def_val = st.session_state.get("edit_definitions", {}).get(sc)
                        sub_val_to_use = edit_sub_def_val if edit_sub_def_val is not None else (default_def or _(f"{sc}에 대한 정의입니다.", f"Definition for {sc}."))
                        sub_val_to_use = translate_definition_if_default(sc, sub_val_to_use)

                        definitions_map[sc] = st.text_input(
                            _(f"ㄴ 중분류 [{sc}] 설명 입력", f"👉 Enter description for sub-criteria [{sc}]"),
                            value=sub_val_to_use,
                            key=f"def_sub_{mc}_{sc}_{j}"
                        )
                st.write("") # 섹션 간 시각적 여백 추가

            st.divider()

            # 섹션 4: 척도 인터페이스 설정
            st.subheader(_("섹션 4: 쌍대비교 응답 척도 설정", "Section 4: Pairwise Comparison Scale Setup"))
            scale_options = [
                _("1-9 Continuous (1부터 9까지 연속형 스케일)", "1-9 Continuous Scale"),
                _("1-3-7-9 Discrete (이산형 척도)", "1-3-7-9 Discrete Scale"),
                _("1-3-5 Discrete (이산형 척도)", "1-3-5 Discrete Scale")
            ]
            scale_option = st.radio(_("응답 척도 타입", "Response Scale Type"), scale_options, index=0)

            st.divider()

            # 섹션 5: 답례품 및 개인정보 수집 동의 설정
            st.subheader(_("섹션 5: 답례품 및 동의 양식 설정", "Section 5: Reward & Consent Form Setup"))
            reward_enabled = st.toggle(_("답례품(기프티콘 등) 제공 활성화", "Enable Rewards (e.g., Gifticons)"))
            reward_desc = ""
            if reward_enabled:
                reward_desc = st.text_area(_("답례품 설명", "Reward Description"), value=st.session_state.get("edit_reward_desc", "모든 설문 응답을 마친 분들에게 스타벅스 아메리카노 기프티콘을 발송해 드립니다."))

            rewards_info = {
                "enabled": reward_enabled,
                "desc": reward_desc
            }

            st.divider()

            # 섹션 6: 실시간 CR 검증 레벨 설정
            st.subheader(_("섹션 6: 제출 전 일관성 비율 (CR) 검증 레벨", "Section 6: Pre-submission Consistency Ratio (CR) Validation Level"))
            # Get default index from edit state if editing, otherwise default to index 4 (0.3 이하)
            default_cr_idx = 4
            if st.session_state.get("editing_survey_id") and st.session_state.get("edit_cr_limit") is not None:
                cr_val = float(st.session_state.get("edit_cr_limit"))
                if cr_val <= 0.1: default_cr_idx = 1
                elif cr_val <= 0.15: default_cr_idx = 2
                elif cr_val <= 0.2: default_cr_idx = 3
                elif cr_val <= 0.3: default_cr_idx = 4
            elif st.session_state.get("editing_survey_id") and st.session_state.get("edit_cr_limit") is None:
                default_cr_idx = 0
            
            cr_limit_opt = st.selectbox(_("일관성 비율(CR) 허용 기준치", "Consistency Ratio (CR) Tolerance Limit"), [
                _("제한하지 않음 (이탈률 감소용)", "No Limit (To reduce drop-out rate)"),
                _("0.1 이하 (매우 엄격함)", "0.1 or below (Very Strict)"),
                _("0.15 이하 (엄격함)", "0.15 or below (Strict)"),
                _("0.2 이하 (보통)", "0.2 or below (Normal)"),
                _("0.3 이하 (일부 허용)", "0.3 or below (Somewhat Lenient)")
            ], index=default_cr_idx)

            cr_limit = None
            if "0.15" in cr_limit_opt: cr_limit = 0.15
            elif "0.1" in cr_limit_opt: cr_limit = 0.1
            elif "0.2" in cr_limit_opt: cr_limit = 0.2
            elif "0.3" in cr_limit_opt: cr_limit = 0.3

            if cr_limit is not None:
                st.warning(_("⚠️ 일관성 비율(CR) 기준을 너무 엄격하게(낮게) 설정할 경우, 논리적 모순이 있는 설문이 대거 무효 처리되어 응답자의 재검토 피로도가 극대화되고 설문 이탈률이 급증할 수 있으니 유의하시기 바랍니다. 응답자 이탈을 낮추기 위해 일관성 비율 허용 기준치를 0.3 이하로 여유롭게 설정하고, 데이터 수집 후 AHP마스터의 일관성 보정 기능을 통해 사후 보정하여 분석하시기를 적극 추천드립니다.", "⚠️ Warning: If the CR limit is set too strict (low), many logically inconsistent surveys will be invalidated. This maximizes respondent fatigue and can cause the survey drop-out rate to spike. To reduce respondent dropout, we strongly recommend setting the consistency ratio tolerance to 0.3 or less and post-calibrating the collected data using the AHP Master consistency calibration feature."))
                # CR 가이드 방식 선택
                st.markdown(_("**응답자 일관성 유지(CR) 가이드 방식 선택**", "**Select Consistency Ratio (CR) Guide Method for Respondents**"))
            
                default_guide = st.session_state.get("edit_cr_guide_method", "realtime")
            
                # Backward compatibility for old surveys that used toggle
                if "edit_cr_guide_enabled" in st.session_state:
                    if st.session_state["edit_cr_guide_enabled"] and default_guide not in ["realtime", "post_wizard", "none"]:
                        default_guide = "realtime"
                    elif not st.session_state["edit_cr_guide_enabled"] and default_guide not in ["realtime", "post_wizard", "none"]:
                        default_guide = "none"
            
                options_kr = {
                    "realtime": "실시간 권장 범위 시각화 안내 (이탈률 최소화, 편의성 높음)",
                    "post_wizard": "제출 후 지능형 수정 제안 마법사 (가장 학술적인 방식, 편향성 제거)",
                    "none": "일관성 가이드 없음(엄격한 검증만 수행)"
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
                    label=_("가이드 방식을 선택하세요", "Choose guide method"),
                    options=[0, 1, 2],
                    format_func=lambda x: options_kr[list(options_kr.keys())[x]] if _("ko", "en") == "ko" else options_en[list(options_en.keys())[x]],
                    index=get_idx(default_guide),
                    label_visibility="collapsed"
                )
            
                cr_guide_method = list(options_kr.keys())[selected_idx]
            
                if cr_guide_method == "realtime":
                    st.info(_("💡 **실시간 안내**: 응답자가 설문 중 일관성을 유지할 수 있도록 파란색 배경으로 권장되는 허용 범위를 안내합니다. 편의성이 높고 이탈률을 크게 낮출 수 있습니다.", "💡 **Real-time Guide**: Highlights the recommended range with a blue background to help respondents maintain consistency. Highly convenient and reduces dropouts."))
                elif cr_guide_method == "post_wizard":
                    st.success(_("💡 **지능형 수정 제안 (추천)**: 응답 중에는 아무런 가이드를 주지 않아 응답자의 진짜 생각을 편향 없이 수집합니다. 제출 버튼을 눌렀을 때 CR이 초과하면, 가장 모순이 큰 딱 1개 문항을 찾아내어 수정을 권고하는 마법사를 띄웁니다.", "💡 **Smart Fix Wizard (Recommended)**: Collects true thoughts without bias by providing no guide during response. If CR exceeds the limit upon submission, a wizard will appear to suggest fixing the single most contradictory question."))
                else:
                    st.warning(_("💡 **안내 없음**: 응답자에게 어떤 힌트도 주지 않으며, 제출 시 CR을 초과하면 에러 메시지와 함께 전체 재검토를 요구합니다. 이탈률이 높아질 수 있습니다.", "💡 **No Guide**: Gives no hints. If CR is exceeded upon submission, an error message is shown requiring a full review. Dropouts may increase."))
            else:
                cr_guide_method = "none"

            st.divider()

            # 섹션 7: 최종 미리보기 및 배포
            st.subheader(_("섹션 7: 저장 전 최종 미리보기 및 배포", "Section 7: Final Preview & Deployment Before Saving"))

            # [추가] 구글 스프레드시트 연동 설정
            if st.session_state.get('editing_survey_id'):
                st.markdown(_("#####  기존 구글 스프레드시트 연동 (수정 모드)", "#####  Existing Google Spreadsheet Integration (Edit Mode)"))
                st.info(_("현재 **기존 설문 수정 모드**로 진입했습니다. 수정한 설정 내용은 기존 연동된 구글 스프레드시트에 안전하게 덮어씌워집니다.\n\n**연동된 시트 ID:** ", "You have entered **Existing Survey Edit Mode**. The modified settings will be safely overwritten to the existing linked Google Spreadsheet.\n\n**Linked Sheet ID:** ") + st.session_state.editing_survey_id)
                existing_sheet_id_input = st.session_state.editing_survey_id
            else:
                past_surveys = []
                if survey_admin_email and "@" in survey_admin_email:
                    import sqlite3
                    try:
                        conn = sqlite3.connect('users.db')
                        c = conn.cursor()
                        c.execute("SELECT title, survey_id, created_at FROM admin_surveys WHERE admin_id=? ORDER BY created_at DESC", (survey_admin_email,))
                        past_surveys = c.fetchall()
                        conn.close()
                    except Exception:
                        pass
                        
                existing_sheet_id_input = ""
                show_manual_input = True
                
                if len(past_surveys) > 0:
                    st.markdown("##### 🔗 배포 방식 선택 (Deployment Method)")
                    deploy_option = st.radio(
                        _("배포 방식을 선택해 주세요.", "Please select a deployment method."),
                        options=[
                            _("새로운 구글 시트 URL 연동 (신규 발급)", "Link New Google Sheet URL (Issue New)"),
                            _("기존 배포했던 설문 URL 재사용 (덮어쓰기)", "Reuse Existing Deployed Survey URL (Overwrite)")
                        ],
                        index=0,
                        key="deploy_option_radio",
                        label_visibility="collapsed"
                    )
                    st.write("")
                    
                    if "재사용" in deploy_option or "Reuse" in deploy_option:
                        show_manual_input = False
                        st.markdown(_("##### ⚙️ 재사용할 기존 설문 선택", "##### ⚙️ Select Existing Survey to Reuse"))
                        survey_options = {f"{row[0]} ({row[2][:16]})" : row[1] for row in past_surveys}
                        selected_survey_label = st.selectbox(
                            _("과거에 배포했던 설문 목록", "List of previously deployed surveys"),
                            options=list(survey_options.keys())
                        )
                        existing_sheet_id_input = survey_options[selected_survey_label]
                        st.info(_("선택한 설문의 구글 스프레드시트에 새로운 내용을 덮어씌웁니다. 기존 응답 URL은 그대로 유지됩니다.", "The new content will be overwritten on the Google Spreadsheet of the selected survey. The existing response URL will be maintained."))
                
                if show_manual_input:
                    st.markdown(_("##### ⚙️ 연동할 본인의 구글 스프레드시트 설정 *", "##### ⚙️ Setup Your Google Spreadsheet to Link *"))
                    st.info(_("""
                    **💡 연동 방법:**
                    1. 본인의 구글 드라이브에서 **새 구글 스프레드시트**를 하나 생성합니다. (본인 계정 용량 내에서 생성되므로 용량 초과 오류가 시 발생하지 않습니다.)
                    2. 우측 상단의 '공유' 버튼을 눌러 아래의 서비스 계정 이메일을 **편집자** (Editor)로 추가합니다.
                       * 서비스 계정 이메일: `ahp2-75@ahp2-486703.iam.gserviceaccount.com`
                    3. 생성한 스프레드시트의 **URL 주소** 또는 **시트 ID**를 복사하여 아래에 붙여넣어 주세요. (아래 예시 이미지 참고)
                    """, """
                    **💡 How to link:**
                    1. Create a **New Google Spreadsheet** in your Google Drive. (This uses your account storage, so there will be no quota errors on our side.)
                    2. Click the 'Share' button on the top right and add the following service account email as an **Editor**.
                       * Service Account Email: `ahp2-75@ahp2-486703.iam.gserviceaccount.com`
                    3. Copy the **URL** or **Sheet ID** of the created spreadsheet and paste it below. (See the example image below)
                    """))
                    st.image("manual_sheet_url_guide.png", caption=_("구글 스프레드시트 URL 주소창 복사 예시", "Example of copying Google Spreadsheet URL"), width=650)
                    existing_sheet_id_input = st.text_input(_("연동할 구글 스프레드시트 URL 또는 ID *", "Google Spreadsheet URL or ID to link *"), placeholder="https://docs.google.com/spreadsheets/d/...")




            # Save current state for preview tab
            preview_id = f"preview_{st.session_state.user_id if st.session_state.user_id else 'guest'}"
            preview_data = {
                "Title": survey_title,
                "Description": survey_desc,
                "Admin_Email": survey_admin_email,
                "AHP_Model_JSON": model_structure,
                "Tier_Level": tier_level, # [신규] 3계층 구분용
                "Scale_Type": scale_option,
                "Demographics": demographics_settings,
                "Definitions": definitions_map,
                "CR_Limit": cr_limit,
                "CR_Guide_Method": cr_guide_method,
                "Rewards_Info": rewards_info
            }

            st.session_state[f"_preview_data_{preview_id}"] = preview_data

            import json, os
            os.makedirs("temp_previews", exist_ok=True)
            with open(f"temp_previews/{preview_id}.json", "w", encoding="utf-8") as f:
                json.dump(preview_data, f, ensure_ascii=False)

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
                        {_("👁️ 설문지 응답 화면 미리보기", "👁️ Preview Survey Form")}
                    </div>
                </a>
                """
                st.markdown(preview_link_html, unsafe_allow_html=True)

            with col_p2:
                if st.session_state.user_id is None:
                    btn_label = _(" 무료 회원가입 후 배포하기", " Deploy after Free Sign Up")
                    if st.button(btn_label, type="primary", use_container_width=True):
                        st.warning(_(" 배포 및 DB 연동은 회원가입 후 가능합니다. (무료 사용자도 제한 없이 배포 및 연동 가능함)", " Deployment and DB integration are available after sign-up. (Free users can also deploy and link DB)"))
                        st.info(_("💡 안심하세요. 현재 작성하신 내용은 창을 닫지 않고 왼쪽 사이드바에서 회원가입/로그인을 완료하시면 날아가지 않고 그대로 유지되어 즉시 배포하실 수 있습니다.", "💡 Rest assured. The contents you have written will be maintained if you sign up and log in from the left sidebar without closing the window, allowing you to deploy immediately."))
                    
                        pass
                else:
                    btn_label = _("🚀 배포 및 DB 연동 (수정 내용 적용)", "🚀 Deploy & Link DB (Apply Changes)") if st.session_state.get("editing_survey_id") else _("🚀 배포 및 DB 연동", "🚀 Deploy & Link DB")
                    if st.button(btn_label, type="primary", use_container_width=True):
                        if not existing_sheet_id_input.strip():
                            st.error(_("연동할 구글 스프레드시트 URL 또는 ID를 반드시 입력해야 합니다.", "You must enter the Google Spreadsheet URL or ID to link."))
                            import streamlit.components.v1 as components
                            alert_msg = _("연동할 구글 스프레드시트 URL을 입력하지 않으면 배포 및 연동이 되지 않습니다.\\n본인의 구글 스프레드시트 URL 또는 ID를 반드시 입력해 주세요.", "Deployment and linking will fail without a Google Spreadsheet URL.\\nPlease make sure to enter your Google Spreadsheet URL or ID.")
                            components.html(f"<script>alert('{alert_msg}');</script>", height=0, width=0)
                        else:
                            with st.spinner(_("구글 스프레드시트와 설문 구조를 연동하는 중...", "Linking survey structure with Google Spreadsheet...")):
                                try:
                                    target_sheet_id = existing_sheet_id_input.strip()
                                    if "docs.google.com/spreadsheets" in target_sheet_id:
                                        parts = target_sheet_id.split("/d/")
                                        if len(parts) > 1:
                                            target_sheet_id = parts[1].split("/")[0]

                                    import os
                                    override_flag = 'sonwook_override.flag'
                                    if survey_admin_email == 'sonwook@gmail.com' and not target_sheet_id and os.path.exists(override_flag):
                                        target_sheet_id = '1Ux7_iZ4TCMIQPfnl4hfdkA8fUlpJcCM8OLp7xQD-wl4'
                                        os.remove(override_flag)

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



                                    # admin_surveys 테이블에 신규 설문 자동 등록 및 마스터 구글 시트 백업
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

                                    # 배포 주소 생성
                                    base_url = st.query_params.get("base_url", ["https://ahpkrj.streamlit.app/"])[0] if isinstance(st.query_params.get("base_url"), list) else "https://ahpkrj.streamlit.app/"
                                    if "localhost" in base_url or "127.0.0.1" in base_url:
                                        short_url = f"{base_url}?survey_id={sheet_id}"
                                    else:
                                        short_url = f"https://ahpkrj.streamlit.app/?survey_id={sheet_id}"

                                    # 사용자 배포 통계 및 설문 링크 기록
                                    update_user_survey_distribution(st.session_state.user_id, short_url)
                                    st.session_state._survey_cache_dirty = True  # 설문 목록 캐시 무효화

                                    st.balloons()
                                    st.success(_("🎉 AHP 온라인 설문지가 성공적으로 업데이트(수정) 되었습니다!", "🎉 AHP online survey has been successfully updated!") if st.session_state.get("editing_survey_id") else _("🎉 AHP 온라인 설문지 및 연동 구글 시트 생성이 완료되었습니다!", "🎉 AHP online survey and linked Google Sheet creation are complete!"))

                                    st.code(short_url, language="text")
                                    st.info(f"**위 배포 URL을 카카오톡이나 이메일 등으로 응답 대상자에게 발송하십시오.**  \n구글 시트 링크 또는 구글 드라이브(계정: {survey_admin_email})에 접속하시면 실시간으로 누적되는 응답자 데이터(Sheet 2: Raw_Data, Sheet 3: Demographic_Data)를 확인하고 즉시 다운로드하여 분석하실 수 있습니다.")
                                except Exception as ex:
                                    st.error(f"구글 시트 연동 실패: {ex}")
                                    import streamlit.components.v1 as components
                                    error_msg = str(ex).replace("'", "\\'").replace("\\n", " ")
                                    components.html(f"<script>alert('❌ 구글 스프레드시트 연동에 실패했습니다.\\n\\n입력하신 URL의 스프레드시트에 접근할 수 없습니다.\\n안내된 서비스 계정 이메일(ahp2-75@ahp2-486703.iam.gserviceaccount.com)을 반드시 [편집자]로 추가하고 공유해 주셔야 연동 및 배포가 가능합니다.\\n\\n상세 에러: {error_msg}');</script>", height=0, width=0)


        _survey_setup_fragment()

    # -------------------------------------------------------------------------
    # [신규] 응답현황 대시보드 탭 (Tab 3) 상세 구현
    # -------------------------------------------------------------------------
    with main_tab3:
        st.header(_("실시간 응답 현황", "Real-time Response Status"))
        selected_sheet_id = None
        
        if st.session_state.user_id is None:
            st.warning(_(" **실시간 응답 현황 기능은 회원 전용 서비스입니다.**", " **Real-time response status is a member-only service.**"))
            st.info("무료 회원가입 및 로그인을 완료하시면 본인이 배포한 설문지의 실시간 응답 상태 및 누적 데이터를 모니터링하고 다운로드할 수 있습니다. (무료 회원도 기능 제한 없이 모든 기능 사용 가능)  \n**좌측 사이드바의 로그인/회원가입 패널**을 이용해 주세요.")
        else:
            # DB에서 해당 관리자가 생성한 설문 목록 조회
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
                st.error(f"설문 목록 조회 실패: {e}")

            if not admin_surveys:
                st.warning("배포된 설문지가 존재하지 않습니다. '온라인 설문지 제작' 탭에서 설문을 먼저 배포해 주세요.")
            else:
                # 로그인한 아이디에 맞춰 본인의 설문들만 드롭다운에 노출시킵니다.
                survey_options = {f"{row[1]} ({row[2]})": row[0] for row in admin_surveys}
                selected_label = st.selectbox(
                    "실시간 현황을 확인할 설문 선택",
                    list(survey_options.keys()),
                    key="tab3_survey_select"
                )
                selected_sheet_id = survey_options[selected_label]
                
                selected_survey_info = next(s for s in admin_surveys if s[0] == selected_sheet_id)
                survey_title = selected_survey_info[1]
                created_at = selected_survey_info[2]
                
                st.success(f" 현재 선택된 설문: **{survey_title}** (배포일시: {created_at})")
                st.divider()

        # 대시보드 렌더링
        if selected_sheet_id:

            st.info(" 구글 API 일일 호출 할당량 초과(Quota Exceeded 429 에러)를 방지하기 위해, 데이터는 자동으로 불러오지 않습니다. 아래 버튼을 눌러 최신 데이터를 갱신하세요.")
            if st.button("🔄 실시간 설문 대시보드 및 응답 데이터 불러오기 / 새로고침", type="primary"):
                from survey_manager import get_survey_stats, get_survey_gspread_client
                with st.spinner("실시간 설문 현황 로딩 중..."):
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
                            st.error(f"구글 시트에서 데이터를 읽어오는 중 에러 발생: {g_err}")
                            st.session_state["live_df"] = None
                    else:
                        st.warning("구글 Sheets API 클라이언트 연결 실패로 인해 구글 시트 내 데이터를 직접 다운로드할 수 없습니다.")
                        st.session_state["live_df"] = None

            if "survey_stats" in st.session_state:
                stats = st.session_state["survey_stats"]
                col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
                with col_stat1:
                    st.metric(_("총 접속자 수 (Visits)", "Total Visits"), f"{stats['visits']}" + _("명", ""))
                with col_stat2:
                    st.metric(_("완료 응답자 수 (Completed)", "Completed Responses"), f"{stats['completed']}" + _("명", ""))
                with col_stat3:
                    st.metric(_("일관성 초과 중단자 (CR Fail)", "CR Fail Abandonments"), f"{stats['abandoned_cr']}" + _("회", " times"))
                with col_stat4:
                    st.metric(_("단순 이탈 중단자 (Bounce)", "Bounced Visitors"), f"{stats['abandoned_bounce']}" + _("명", ""))

                # 시각화 차트 추가
                import plotly.express as px

                chart_data = pd.DataFrame({
                    "구분": ["응답 완료", "일관성 초과 중단", "단순 페이지 이탈"],
                    "인원수": [stats['completed'], stats['abandoned_cr'], stats['abandoned_bounce']]
                })

                fig_stats = px.bar(
                    chart_data,
                    x="구분",
                    y="인원수",
                    text="인원수",
                    color="구분",
                    color_discrete_map={
                        "응답 완료": "#2E7D32",
                        "일관성 초과 중단": "#C62828",
                        "단순 페이지 이탈": "#EF6C00"
                    },
                    title="설문 참여 상태별 분포"
                )
                fig_stats.update_layout(showlegend=False)
                st.plotly_chart(fig_stats, use_container_width=True)

            if "live_df" in st.session_state and st.session_state["live_df"] is not None:
                live_df = st.session_state["live_df"]
                demo_df = st.session_state.get("demo_df", None)

                # 구글 시트에서 실시간 응답 로데이터(Raw_Data) 다운로드 기능 추가
                with st.expander(_("📥 실시간 구글 시트 응답 데이터 다운로드 센터", "📥 Real-time Google Sheet Response Data Download Center"), expanded=True):
                    if not live_df.empty:
                        st.success(f"구글 스프레드시트에서 실시간 응답 데이터를 성공적으로 불러왔습니다. (Raw_Data: {len(live_df)}건" + (f", Demographic_Data: {len(demo_df)}건" if demo_df is not None else "") + ")")
                        
                        # 📊 AHP 분석 연동 단축 버튼 추가
                        if st.button(_("📊 이 온라인 설문 데이터로 즉시 AHP 분석 수행하기 (분석 도구로 연동)", "📊 Perform AHP Analysis Instantly with this Online Survey Data"), type="primary", use_container_width=True):
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
                                        st.session_state["ahp_df_main"][col] = pd.to_numeric(st.session_state["ahp_df_main"][col], errors='coerce')
                                
                                 # 중분류 복사
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
                                                st.session_state["ahp_sub_dfs"][main_c][col] = pd.to_numeric(st.session_state["ahp_sub_dfs"][main_c][col], errors='coerce')
                                                
                                st.session_state["ahp_sheet_names"] = ["Main_Criteria"] + list(st.session_state["ahp_sub_dfs"].keys())
                                st.info(_("📊 데이터 분석 준비가 완료되었습니다! **상단의 '📊 AHP 분석 도구' 탭**을 선택하고 **'🌐 배포된 온라인 설문 데이터 연동'** 라디오 버튼을 선택하여 분석 결과를 바로 확인하십시오.", "📊 Data analysis preparation is complete! Select the **'📊 AHP Analysis Tool' tab at the top** and choose the **'🌐 Link Distributed Online Survey Data'** radio button to view the results instantly."))

                        tab_raw, tab_demo = st.tabs(["📊 Raw_Data (AHP 쌍대비교 데이터)", "👤 Demographic_Data (인구통계/사전순위)"])
                        with tab_raw:
                            st.dataframe(live_df, use_container_width=True)
                        with tab_demo:
                            if demo_df is not None:
                                st.dataframe(demo_df, use_container_width=True)
                            else:
                                st.info("수집된 인구통계 데이터가 없거나 Demographic_Data 시트가 생성되지 않았습니다.")

                        # Excel 및 CSV 내보내기 버튼 제공
                        import io

                        # 1. Excel 내보내기 (두 개의 시트를 모두 포함)
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
                                "📥 실시간 응답 Excel 다운로드 (.xlsx)",
                                data=excel_buffer.getvalue(),
                                file_name=f"Survey_Live_Data_{selected_sheet_id.strip()[:6]}.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                use_container_width=True,
                                type="primary"
                            )
                        # 2. CSV 내보내기 (Raw_Data 우선 내보내기)
                        csv_buffer = io.StringIO()
                        live_df.to_csv(csv_buffer, index=False, header=True)
                        with col_dl2:
                            st.download_button(
                                "📥 실시간 응답 CSV 다운로드 (.csv)",
                                data=csv_buffer.getvalue().encode('utf-8-sig'),
                                file_name=f"Survey_Live_Data_{selected_sheet_id.strip()[:6]}.csv",
                                mime="text/csv",
                                use_container_width=True
                            )
                    else:
                        st.info("구글 시트에 수집된 응답 로데이터가 아직 비어 있습니다.")

            # 로컬 안전 백업 데이터 조회 및 추출 유틸리티
            try:
                conn = sqlite3.connect('users.db')
                backup_df = pd.read_sql_query(
                    "SELECT id, respondent_id, response_json, created_at FROM survey_backup_responses WHERE survey_id = ?",
                    conn, params=(selected_sheet_id.strip(),)
                )
                conn.close()

                if not backup_df.empty:
                    with st.expander("🛡️ 서버 로컬 안전 백업 관리 센터"):
                        st.success(f"구글 시트 연동과 관계없이 서버 로컬 데이터베이스에 저장된 안전 백업 데이터가 총 {len(backup_df)}건 존재합니다.")
                        st.dataframe(backup_df[["id", "respondent_id", "created_at"]], use_container_width=True)

                        # 전체 로 데이터 복구 엑셀/CSV 데이터 빌드
                        recovered_raw_rows = []
                        recovered_demo_rows = []
                        for idx_b, r_b in backup_df.iterrows():
                            payload = json.loads(r_b["response_json"])
                            if "raw_row_data" in payload:
                                recovered_raw_rows.append(payload["raw_row_data"])
                            elif "row_data" in payload:
                                # 하위 호환성
                                recovered_raw_rows.append(payload["row_data"])

                            if "demo_row_data" in payload:
                                recovered_demo_rows.append(payload["demo_row_data"])

                        if recovered_raw_rows:
                            import io

                            # 헤더 복구 로직 추가
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
                                raw_headers.append("제출시간")
                                
                                demo_headers = ["ID", "Type"]
                                if demographics.get("name"): demo_headers.append("성명")
                                if demographics.get("age"): demo_headers.append("연령")
                                if demographics.get("gender"): demo_headers.append("성별")
                                if demographics.get("experience"): demo_headers.append("경력년수")
                                # if demographics.get("affiliation"): demo_headers.append("소속")
                                if demographics.get("email"): demo_headers.append("이메일")
                                demo_headers.append("사전순위지정")
                                if rewards_info.get("enabled"):
                                    demo_headers.append("경품연락처" if tier_level == "3" else "답례품_연락처")
                                demo_headers.append("제출시간")

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

                            # Excel로 백업 데이터를 템플릿 구조에 맞춰 분할하여 다운로드
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
                                    "📥 로컬 백업 Excel 다운로드 (.xlsx)",
                                    data=excel_backup_buffer.getvalue(),
                                    file_name=f"Backup_Recovery_{selected_sheet_id.strip()[:6]}.xlsx",
                                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                    use_container_width=True,
                                    type="primary"
                                )

                            with col_b_dl2:
                                # CSV 파일 형태로 복구 파일 내보내기 (Raw_Data 우선)
                                output_csv = io.StringIO()
                                df_raw_backup.to_csv(output_csv, index=False, header=bool(raw_headers))
                                st.download_button(
                                    "📥 로컬 백업 Raw_Data CSV 다운로드 (.csv)",
                                    data=output_csv.getvalue().encode('utf-8-sig'),
                                    file_name=f"Backup_Recovery_Raw_{selected_sheet_id.strip()[:6]}.csv",
                                    mime="text/csv",
                                    use_container_width=True
                                )
                else:
                    st.caption("이 설문지에 등록된 로컬 서버 백업 데이터가 없습니다. (모든 데이터 정상 적재)")
            except Exception as err:
                st.caption(f"로컬 백업 조회 불가: {err}")

    with main_tab_pricing:
        st.markdown(_("## 서비스 요금 안내 <span style='font-size: 0.95rem; font-weight: 500; color: #0284c7; margin-left: 16px; background: #e0f2fe; padding: 6px 14px; border-radius: 20px; vertical-align: middle; box-shadow: 0 1px 2px rgba(0,0,0,0.05);'>💳 연구비/법인카드 및 세금계산서 100% 지원</span>", "## Service Pricing <span style='font-size: 0.95rem; font-weight: 500; color: #0284c7; margin-left: 16px; background: #e0f2fe; padding: 6px 14px; border-radius: 20px; vertical-align: middle; box-shadow: 0 1px 2px rgba(0,0,0,0.05);'>💳 Research Cards & Tax Invoices 100% Supported</span>"), unsafe_allow_html=True)

        col_p1, col_p2, col_p3, col_p4 = st.columns(4)
        
        if st.session_state.lang == 'en':
            # 1 Month
            with col_p1:
                inner_1 = """
                    <h3 style='margin-top: 0 !important; margin-bottom: 0;'>Basic</h3>
                    <span style='color: #888; font-size: 1.1rem;'>2 Months</span>
                    <h2 style='margin-top: 15px; margin-bottom: 5px; color: #ff4b4b;'>$185 USD</h2>
                    <p style='font-size: 0.85rem; color: #666; min-height: 40px;'>Suitable for small-scale projects aiming for reliable results using standard AHP methodology.</p>
                    <hr style='margin: 10px 0;'>
                    <ul style='font-size: 0.9rem; padding-left: 20px; color: #333; line-height: 1.6;'>
                        <li><b>Standard AHP features</b></li>
                        <li><b>Unlimited sample size</b></li>
                        <li>Unlimited project creation</li>
                        <li>Standard email support</li>
                    </ul>
                """
                if st.session_state.user_id:
                    st.components.v1.html(get_paypal_payment_html(st.session_state.user_id, "Basic (2 Months)", 185.0, 2, inner_html=inner_1, is_best=False), height=520)
                else:
                    st.components.v1.html(get_login_redirect_html("Basic (2 Months)", inner_html=inner_1, is_best=False, lang="en"), height=520)

            # 3 Months
            with col_p2:
                inner_3 = """
                    <h3 style='margin-top: 0 !important; margin-bottom: 0;'>Standard</h3>
                    <span style='color: #888; font-size: 1.1rem;'>2 Months</span>
                    <h2 style='margin-top: 15px; margin-bottom: 5px; color: #ff4b4b;'>$330 USD</h2>
                    <p style='font-size: 0.85rem; color: #666; min-height: 40px;'>Suitable for professional research requiring precise conclusions through demographic group-difference analysis.</p>
                    <hr style='margin: 10px 0;'>
                    <ul style='font-size: 0.9rem; padding-left: 20px; color: #333; line-height: 1.6;'>
                        <li><b>Includes Advanced Cross-Statistical Analysis (T-Test, ANOVA)</b></li>
                        <li><b>Unlimited sample size</b></li>
                        <li>Unlimited project creation</li>
                        <li>Standard email support</li>
                    </ul>
                """
                if st.session_state.user_id:
                    st.components.v1.html(get_paypal_payment_html(st.session_state.user_id, "Standard (2 Months)", 330.0, 2, inner_html=inner_3, is_best=True), height=520)
                else:
                    st.components.v1.html(get_login_redirect_html("Standard (2 Months)", inner_html=inner_3, is_best=True, lang="en"), height=520)

            # 6 Months
            with col_p3:
                inner_6 = """
                    <h3 style='margin-top: 0 !important; margin-bottom: 0;'>Pro</h3>
                    <span style='color: #888; font-size: 1.1rem;'>2 Months</span>
                    <h2 style='margin-top: 15px; margin-bottom: 5px; color: #ff4b4b;'>$700 USD</h2>
                    <p style='font-size: 0.85rem; color: #666; min-height: 40px;'>Suitable for research institutions and top-tier academic journals requiring advanced Fuzzy AHP analysis and priority support.</p>
                    <hr style='margin: 10px 0;'>
                    <ul style='font-size: 0.9rem; padding-left: 20px; color: #333; line-height: 1.6;'>
                        <li><b>Includes Fuzzy AHP</b></li>
                        <li>Advanced cross-statistical analysis (T-Test, ANOVA)</li>
                        <li>Unlimited sample size & projects</li>
                        <li>Priority tech/bug support</li>
                        <li><b>1 Free survey setup proxy</b></li>
                    </ul>
                """
                if st.session_state.user_id:
                    st.components.v1.html(get_paypal_payment_html(st.session_state.user_id, "Pro (2 Months)", 700.0, 2, inner_html=inner_6, is_best=False), height=520)
                else:
                    st.components.v1.html(get_login_redirect_html("Pro (2 Months)", inner_html=inner_6, is_best=False, lang="en"), height=520)

            # Proxy Services (PayPal)
            with col_p4:
                st.components.v1.html(get_paypal_custom_services_html(st.session_state.user_id), height=520)
        else:
            # 1개월
            with col_p1:
                inner_1 = """
                    <h3 style='margin-top: 0 !important; margin-bottom: 0;'>Basic</h3>
                    <span style='color: #888; font-size: 1.1rem;'>2개월</span>
                    <h2 style='margin-top: 15px; margin-bottom: 5px; color: #ff4b4b;'>350,000원</h2>
                    <p style='font-size: 0.85rem; color: #666; min-height: 40px;'>표준 AHP 방법론을 활용하여 신뢰성 있는 결과를 도출하는 소규모 프로젝트에 적합합니다.</p>
                    <hr style='margin: 10px 0;'>
                    <ul style='font-size: 0.9rem; padding-left: 20px; color: #333; line-height: 1.6;'>
                        <li><b>일반 AHP 기능 제공</b></li>
                        <li><b>표본수 무제한</b></li>
                        <li>프로젝트 생성 무제한</li>
                        <li>일반 이메일 지원</li>
                    </ul>
                """
                if st.session_state.user_id:
                    st.components.v1.html(get_portone_payment_html(st.session_state.user_id, "Basic (2개월)", 350000, 2, inner_html=inner_1, is_best=False), height=520)
                else:
                    st.components.v1.html(get_login_redirect_html("Basic (2개월)", inner_html=inner_1, is_best=False), height=520)

            # 3개월
            with col_p2:
                inner_3 = """
                    <h3 style='margin-top: 0 !important; margin-bottom: 0;'>Standard</h3>
                    <span style='color: #888; font-size: 1.1rem;'>2개월</span>
                    <h2 style='margin-top: 15px; margin-bottom: 5px; color: #ff4b4b;'>500,000원</h2>
                    <p style='font-size: 0.85rem; color: #666; min-height: 40px;'>응답자 그룹별 차이 분석을 통해 보다 정교한 결론을 도출하는 전문 리서치에 적합합니다.</p>
                    <hr style='margin: 10px 0;'>
                    <ul style='font-size: 0.9rem; padding-left: 20px; color: #333; line-height: 1.6;'>
                        <li><b>집단간 차이 분석 (T-Test, ANOVA) 제공</b></li>
                        <li><b>표본수 무제한</b></li>
                        <li>프로젝트 생성 무제한</li>
                        <li>일반 이메일 지원</li>
                    </ul>
                """
                if st.session_state.user_id:
                    st.components.v1.html(get_portone_payment_html(st.session_state.user_id, "Standard (2개월)", 500000, 2, inner_html=inner_3, is_best=True), height=520)
                else:
                    st.components.v1.html(get_login_redirect_html("Standard (2개월)", inner_html=inner_3, is_best=True), height=520)

            # 6개월
            with col_p3:
                inner_6 = """
                    <h3 style='margin-top: 0 !important; margin-bottom: 0;'>Pro</h3>
                    <span style='color: #888; font-size: 1.1rem;'>2개월</span>
                    <h2 style='margin-top: 15px; margin-bottom: 5px; color: #ff4b4b;'>950,000원</h2>
                    <p style='font-size: 0.85rem; color: #666; min-height: 40px;'>고도화된 퍼지 AHP 분석과 최우선 기술 지원이 필요한 전문 학술지 투고 및 연구 기관에 적합합니다.</p>
                    <hr style='margin: 10px 0;'>
                    <ul style='font-size: 0.9rem; padding-left: 20px; color: #333; line-height: 1.6;'>
                        <li><b>퍼지 AHP (Fuzzy AHP) 분석 기능 포함</b></li>
                        <li>집단간 차이 분석 (T-Test, ANOVA) 제공</li>
                        <li>표본수 무제한 및 프로젝트 무제한</li>
                        <li>최우선 기술/오류 지원</li>
                        <li><b>설문 셋팅 1회 무료 대행</b></li>
                    </ul>
                """
                if st.session_state.user_id:
                    st.components.v1.html(get_portone_payment_html(st.session_state.user_id, "Pro (2개월)", 950000, 2, inner_html=inner_6, is_best=False), height=520)
                else:
                    st.components.v1.html(get_login_redirect_html("Pro (2개월)", inner_html=inner_6, is_best=False), height=520)

            # 부가 서비스 대행
            with col_p4:
                st.components.v1.html(get_portone_custom_services_html(st.session_state.user_id), height=520)
            
        st.markdown("<br><br>", unsafe_allow_html=True)

    with main_tab_consulting:
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
                        success = send_consulting_email(
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
                            st.error(_("문의 메일 전송 중 오류가 발생했습니다. 관리자에게 이메일(jeon080423@gmail.com)로 직접 연락해 주세요.", 
                                       "An error occurred while sending the email. Please contact jeon080423@gmail.com directly."))

    with main_tab_signup:
        if st.session_state.user_id:
            st.info(_("이미 로그인되어 있습니다.", "You are already logged in."))
        else:
            agreements = show_agreement_ui()
            s_id = st.text_input(_("아이디 (이메일 주소)", "Username (Email Address)"), key="main_s_id")
            s_pw = st.text_input(_("비밀번호", "Password"), type="password", key="main_s_pw")
            
            if st.button(_("가입신청", "Register"), key="main_btn_signup"):
                if not agreements.get("agree_personal_info"):
                    st.error(_("개인정보 수집·이용에 동의해야 가입신청할 수 있습니다.", "You must agree to the privacy policy to register."))
                elif not validate_email(s_id):
                    st.error(_("올바른 이메일 형식이 아닙니다.", "Invalid email format."))
                elif not validate_password(s_pw):
                    st.error(_("비밀번호는 문자+특수문자여야 합니다.", "Password must contain both letters and special characters."))
                else:
                    restore_from_deleted_sheet(s_id.strip())
                    # 가입 시 무조건 'temp' 권한으로 배정
                    if add_user(s_id.strip(), s_pw, 'temp', agree_info="Y"):
                        st.success(_("회원가입이 완료되었습니다! 사이드바의 '로그인' 탭에서 로그인해 주시기 바랍니다.", "Registration successful! Please log in using the 'Login' tab in the sidebar."))
                        import time
                        time.sleep(2)
                        st.rerun()
                    else:
                        st.error(_("이미 존재하는 아이디입니다.", "ID already exists."))

    st.markdown("---")
    st.caption("© 2026 AHP Master. All rights reserved.")


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

# ahp_table_utils will be lazy loaded below


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
    """가????비?번호 ?효??검?? ?과?는 8?리 ?시 비?번호??성?니??"""
    chars = string.ascii_letters + string.digits
    specials = "!@#$%^&*"
    # 최소 1??문?? 1??자, 1??수문자??함?도?구성
    temp = [
        random.choice(string.ascii_lowercase),
        random.choice(string.uppercase) if hasattr(string, 'uppercase') else random.choice(string.ascii_uppercase),
        random.choice(string.digits),
        random.choice(specials)
    ]
    # ?머지 4?리???문/?자 ?무작???택
    temp += [random.choice(chars) for _ in range(4)]
    random.shuffle(temp)
    return "".join(temp)

# --- LAZY LOAD HEAVY MODULES ---
gspread = LazyLoader('gspread')
requests = LazyLoader('requests')
itertools = LazyLoader('itertools')

write_custom_ahp_table = LazyFunction('ahp_table_utils', 'write_custom_ahp_table')
add_borders_to_data = LazyFunction('ahp_table_utils', 'add_borders_to_data')
rc = LazyFunction('matplotlib', 'rc')
MIMEText = LazyFunction('email.mime.text', 'MIMEText')
relativedelta = LazyFunction('dateutil.relativedelta', 'relativedelta')
show_agreement_ui = LazyFunction('signup_agreement', 'show_agreement_ui')
st_javascript = LazyFunction('streamlit_javascript', 'st_javascript')

import base64

# IP ?치 추적 ?공인 IP 추출???한 ?이브러?추?
# (requests??LazyLoader?처리)

# ANOVA ??후검?을 ?한 ?이브러?(?을 경우 ?외처리)
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
# ?국??English/Korean) 번역 ?퍼 ?수
# -----------------------------------------------------------------------------
try:
    if 'lang' not in st.session_state:
        try:
            _init_lang = st.query_params.get("lang", "ko")
            if isinstance(_init_lang, list): _init_lang = _init_lang[0]
            st.session_state.lang = _init_lang.lower()
        except:
            st.session_state.lang = 'ko'
except:
    pass

def _(ko_text, en_text):
    try:
        if st.session_state.get('lang', 'ko') == 'en':
            return en_text
    except:
        pass
    return ko_text

@st.cache_data(show_spinner=False)
def translate_dynamic_text(text, target_lang='en'):
    if not text or not str(text).strip():
        return text
    try:
        from deep_translator import GoogleTranslator
        translator = GoogleTranslator(source='ko', target=target_lang)
        return translator.translate(str(text))
    except Exception:
        return text

def _t(text):
    """Dynamically translates user-provided text if the current language is English."""
    try:
        if st.session_state.get('lang', 'ko') == 'en':
            return translate_dynamic_text(text, 'en')
    except:
        pass
    return text
DEFAULT_SURVEY_DESC_KO = """[조사 목적 ??내?

?녕?십?까?
??문조사??[?구/?로?트 주제]??관??주요 ?인?의 ????중요?? ?출?기 ?해 ?문가(?는 ?무?? ?러분의 고견???렴?고??마련?었?니?? 
바쁘?더?도 ?시 ?간???어 귀?의 귀중한 ?견???답??주시??구??????????것입?다.

??조사 목적 : [?구/?로?트 목적 기재]
??조사 ?용 : [조사 ????인] 간의 AHP(??비교) ??
??조사 기간 : 202X??X??X??~ 202X??X??X??
??개인?보 보호 : 
?조사??해 ?집??모든 ?료???계???3?비???보호)???거?여 철???보호?며, ?직 ?구 ??계 분석 목적?로??용?니??
?답?주??개인 ?보 ?개별 ?답 결과???? ????출?? ?음???속?립?다.

귀?의 ?중??참여??깊? 감사??립?다.

- ?구 책임??: [?름 기재]
- 문의?: [?락??는 ?메??기재]"""

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
    "?조???동로봇 ?입 ?인 중요??분석???한 ?문가 AHP ?문": "Expert AHP Survey on the Importance of Factors for Adopting Manufacturing Collaborative Robots",
    "?동로봇 ?입 ??기술???능, ?환?? ?전???기술 지????기술 측면???인": "Factors related to the technological aspect such as technical performance, compatibility, safety, and technical support.",
    "?동로봇 ?입?관?된 조직 ??????, 경영?지?? ?무 ?교육 ?태 ?인": "Factors related to the internal capabilities of the organization, top management support, financial and training status.",
    "?? 지?? ?업 ??경쟁 ?력, 구인????? ?력 ???? ?경???인": "External environmental factors such as government support, competitive pressure within the industry, labor shortage, and external cooperation.",
    "경영진의 ?신 지?성, 구성?의 변???용????마???토?지??기술 ?? ?인": "Factors such as the management's innovation orientation, members' acceptance of change, and smart factory knowledge/skill levels.",
    "?입????동로봇간의 ?????점": "Relative advantage among the collaborative robots targeted for adoption.",
    "기존 ?비??????동로봇과의 ?결??: "Connectivity with existing equipment or third-party collaborative robots.",
    "?업?? 같? 공간?서 ?전 ?스 ?이 ?업???의 ?적 ?고 ?방 ??": "Level of human accident prevention when working in the same space as operators without safety fences.",
    "공급?의 기술 ?A/S 지???도": "Degree of technical and A/S support from the supplier.",
    "경영진의 ?입 ?? ?경영철학 반영??: "The management's willingness to adopt and the degree to which management philosophy is reflected.",
    "조직?의 로봇 ?용 기술 준???": "The level of technical readiness of organizational members to utilize robots.",
    "로봇 구입???한 ?본 ?력 ??금 조달 ?의??: "Capital capacity and financing convenience for purchasing robots.",
    "기술 ?상???한 ?탁/?내 교육 ?로그램 ?무": "Availability of external/internal training programs for skill improvement.",
    "?동로봇 ?입???성?하??한 ?????정 지???보조??택 ?도": "Degree of government financial support and subsidy benefits to promote the adoption of collaborative robots.",
    "?종 ?계 ?는 경쟁?의 ?동로봇 ?입???른 경쟁???박 ?도": "Degree of competitive pressure due to the adoption of collaborative robots by peers or competitors.",
    "?조 ?장??구인????산 ?력 ?급???려? ??": "Level of difficulty in finding labor and supplying production personnel at the manufacturing site.",
    "로봇 공급???의 ?? 컨설?? ?구기? ?의 기술??교육??지??: "Technical/educational support from external consulting, research institutes, etc., other than the robot supplier.",
    "최고경영?의 ?극?인 ??": "The top management's active willingness to adopt new manufacturing technologies and robots.",
    "?로???조 기술 ?로봇 ?입?????최고경영?의 ?극?인 ??": "The top management's active willingness to adopt new manufacturing technologies and robots.",
    "?규 ?비 ??업 ?로?스 변?에 ???구성?들???용 ??조 ?도": "Members' acceptance and cooperative attitude towards changes in new equipment and work processes.",
    "공장 ?????화, ?보?스??MES ?? ??동??기술???재 구축 ??": "Current level of implementation of digitalization, information systems (MES, etc.), and automation technology in the factory.",
    "?동로봇 ?용 ??? 관리에 ?요??조직 ???문 지????": "Level of internal expertise required for the utilization and maintenance of collaborative robots.",
    "기능??: "Functionality",
    "?자??: "Design",
    "경제??: "Economy",
    "?드?어": "Hardware",
    "?프?웨??: "Software",
    "??": "Appearance",
    "?의??: "Usability",
    "?말기??: "Device Price",
    "??비용": "Maintenance Cost",
    "기술 ?인": "Technological",
    "조직 ?인": "Organizational",
    "?경 ?인": "Environmental",
    "?신 ?인": "Innovational",
    "???이??: "Relative Advantage",
    "?환??: "Compatibility",
    "?전??: "Security",
    "?비????: "Service Support",
    "경영진???: "Top Management Support",
    "기술준비도": "Tech Readiness",
    "금융?원": "Financial Resources",
    "교육?련": "Training",
    "??지??: "Gov Support",
    "경쟁?력": "Competitive Pressure",
    "?력??: "Labor Shortage",
    "??지??: "External Support",
    "경영진의 ?신??: "Management Innovativeness",
    "변?수?태??: "Change Acceptance",
    "?마?팩?리??": "Smart Factory Level",
    "지?정??: "Knowledge Level"
}

def translate_definition_if_default(factor_name, def_text):
    if st.session_state.get('lang', 'ko') != 'en' or not def_text:
        return def_text
        
    # Strip HTML tags for checking (in case of Quill editor)
    import re
    plain_text = re.sub(r'<[^>]+>', '', def_text).strip()
    
    # [FIX] Handle multi-line survey description explicitly
    if plain_text == re.sub(r'<[^>]+>', '', DEFAULT_SURVEY_DESC_KO).strip():
        # If the original text is the default, return the English default (wrapped in HTML paragraph if needed, but st.markdown handles raw text fine)
        return DEFAULT_SURVEY_DESC_EN
    
    # Clean up whitespace for other definitions
    clean_def = re.sub(r'\s+', ' ', plain_text).strip()
    
    # 1. Direct match in dictionary
    if clean_def in DEFAULT_TRANSLATED_DEFS:
        return DEFAULT_TRANSLATED_DEFS[clean_def]
        
    # Translate the factor_name in pattern matching to match Korean if it's saved in Korean
    trans_factor = DEFAULT_TRANSLATED_DEFS.get(factor_name, _t(factor_name))
    
    # 2. Pattern matches for "{factor}??????의?니??" or "{factor}??????의 ?니??"
    pattern1 = rf"^(?:{re.escape(factor_name)}|{re.escape(trans_factor)})\s*??s*???s*?의\s*?니??.?$"
    if re.match(pattern1, clean_def):
        return f"Definition for {trans_factor}."
        
    pattern2 = rf"^(?:{re.escape(factor_name)}|{re.escape(trans_factor)})\s*??s*???s*?반??s*?소?s*?명?니??.?$"
    if re.match(pattern2, clean_def):
        return f"Overall description for {trans_factor}."
        
    return _t(def_text)

def translate_factor_if_default(factor_name):
    if st.session_state.get('lang', 'ko') != 'en' or not factor_name:
        return factor_name
    return DEFAULT_TRANSLATED_DEFS.get(factor_name, _t(factor_name))

# =============================================================================
# 0. ?스???정 ??틸리티
# =============================================================================

# [?정] Base64 문자?의 ?딩 ??제??한 ?틸리티 ?수 강화
def fix_base64_padding(data):
    """
    Base64 문자?의 ?딩(Incorrect padding) ?류??정?는 ?수
    """
    if isinstance(data, str):
        # 1. 모든 공백 ?줄바?문자 ?거 (가??중요???정)
        data = re.sub(r'\s+', '', data)
        
        # 2. ?딩(=) 계산 ?추?
        missing_padding = len(data) % 4
        if missing_padding:
            data += '=' * (4 - missing_padding)
    return data

# [?정 반영] 1) SEO ?그 ?입, 2) ?비???변?AHP 마스??, 4) ?비??정
try:
    from PIL import Image
    favicon_path = "favicon.png"
    if os.path.exists(favicon_path):
        favicon_img = Image.open(favicon_path)
    else:
        favicon_img = "?"
    
    st.set_page_config(
        page_title=_("AHP 분석 ?로그램 | ?라??AHP ?문·?? AHP ?계 ?루????AHP Master", "AHP Master | Traditional & Fuzzy AHP Decision Analysis System"),
        layout="wide", 
        page_icon=favicon_img,
        menu_items={
            'Get Help': None,
            'Report a bug': None,
            'About': _("AHP 마스??- ?마???반 ??? AHP ?사결정 분석 ?스??, "AHP Master - Smart Traditional & Fuzzy AHP Decision Analysis System")
        }
    )
except Exception:
    try:
        st.set_page_config(page_title=_("AHP 마스??| ?? AHP 지??, "AHP Master | Fuzzy AHP Support"), layout="wide", page_icon="?")
    except Exception:
        pass

# [?정 반영] 메? 코드가 ?면???출?? ?도?display:none ???을 추???SEO ?그 (?한 ?합 검??최적??
# [추?] ?이??치?드바이? ?검???진 ?롤???집???해 메? ?그, canonical, JSON-LD 구조???이?? ?제 ?드(Parent Head)???적?로 ?입?는 1x1 ??지 로더 ?크립트 ?재
seo_tags = """<div style="display:none;">
<title>AHP마스??- AHP ?사결정 분석</title>
<!-- Multilingual Description -->
<meta name="description" content="AHP Master - Professional Analytic Hierarchy Process (AHP) & Fuzzy AHP automation software tool for thesis, academic papers, and research. Supports Consistency Ratio (CR) calibration, group geometric mean calculation, ANOVA testing. ?위?문 ??구??AHP/?? AHP 분석 ?루??(AHP 분석 ??? ?? ?플??동?? 3계층 모델 ??비교 ?문지 ?동 ?성, ?답??CR ?0.1 ?하 관? ?설?방?, ?인?종합 가중치 계산 ?그래???각??지??. 专业层次?析?AHP)?模糊层次分?法?线?与?算器?階層分?法(AHP)?ー?。Software del Proceso de Análisis Jerárquico (AHP). Processus d'Analyse Hiérarchique. Analytischer Hierarchieprozess. Quá trình Phân tích Phân cấp. विश्लेषणात्म?पदानुक्र?प्रक्रिय? Analitiese Hiërargieproses. ?е?од анализа ие?а??ий." />
<!-- Multilingual Keywords -->
<meta name="keywords" content="AHP, Fuzzy AHP, Expert AHP Survey, AHP calculator, Fuzzy AHP calculator, Analytic Hierarchy Process software, Consistency Ratio, CR calibration, AHP group consensus, AHP software for thesis, AHP excel template, AHP 마스?? AHP ?로그램, AHP ??, AHP 분석 ??? AHP 분석 ?플? AHP ?문 분석, AHP ????비율 보정, AHP 가중치 계산, ?위?문 AHP ?계, 层次?析? 模糊层次?析? 层次?析법?算器, 层次?析법软? 论文AHP?析, 一?性比? ?層?析? ?ァ?ィAHP, AHP?フ?ウ?ア, AHP?ー?? Proceso de Análisis Jerárquico, AHP Difuso, Software AHP, Calculadora AHP, Processus d'Analyse Hiérarchique, AHP Flou, Logiciel AHP, Quá trình Phân tích Phân cấp, AHP m? Phần mềm AHP, Analytischer Hierarchieprozess, AHP-Software, AHP Rechner, विश्लेषणात्म?पदानुक्र?प्रक्रिय? फ़ज़ी AHP, AHP SOFTWARE, Analitiese Hiërargieproses, Vae AHP, AHP-sagteware, ?е?од анализа ие?а??ий, ?е?е?кий AHP, ??ог?аммное обе?пе?ение AHP, ع???ة ا?تح??? ا??ر??, ع???ة ا?تح??? ا??ر?? ا?ضباب?, بر?ا?ج AHP" />
<meta name="author" content="AHP Master" />
<meta name="robots" content="index, follow" />
<meta name="google-site-verification" content="FeA-DlBx8VmFmHx0Y9MEOy-J_ZjgCNZB70LFUgB10hs" />
<meta name="naver-site-verification" content="f0561d996c39ca52dcc47cf2aad128c5e586a1d6" />
<!-- Open Graph Tags -->
<meta property="og:title" content="AHP Master - Global AHP & Fuzzy AHP Analysis Software (层次?析? ?層?析?" />
<meta property="og:description" content="Advanced AHP & Fuzzy AHP decision software with mathematical consistency ratio (CR) calibration, group consensus, and statistical comparison for global researchers." />
<meta property="og:type" content="website" />
<meta property="og:url" content="https://ahpkrj.streamlit.app/" />
<!-- Hidden content for deep indexing -->
<h1>AHP Master - Analytic Hierarchy Process & Fuzzy AHP Calculator</h1>
<p>AHP Master is a powerful online software for Traditional AHP and Fuzzy AHP analysis. Perfect for academic thesis, research papers, and corporate decision making. Features automatic consistency ratio (CR) improvement and Excel exports.</p>
<h2>层次?析?(AHP) & 模糊层次?析??线计算?과 ?프?웨??/h2>
<p>专为?论文? ?구??해 ?계??계층분석과정(AHP) ?동??분석 ?구?니?? ????비율(CR) ?동 보정, 그룹 기하?균 계산, ANOVA 분석 ??? 보고???보?기?지?합?다.</p>
<h2>?層?析?(AHP) & ?ァ?ィAHP ?フ?ウ?ア</h2>
<p>論文?研究の?め??層分?법(AHP)?動?툴. 一貫성比率(CR)??조정?나 Excel?ポ?ト?力??応?/p>
<h2>Proceso de Análisis Jerárquico (AHP) y AHP Difuso</h2>
<p>Software y calculadora en línea para el Proceso de Análisis Jerárquico (AHP). Ideal para tesis y toma de decisiones, con calibración automática de la Relación de Consistencia (CR).</p>
<h2>Processus d'Analyse Hiérarchique (AHP) et AHP Flou</h2>
<p>Logiciel et calculatrice en ligne pour le Processus d'Analyse Hiérarchique (AHP). Idéal pour les thèses académiques et la prise de décision, con calibrage automatique du ratio de cohérence (CR).</p>
<h2>Analytischer Hierarchieprozess (AHP) und Fuzzy AHP</h2>
<p>AHP-Software und Rechner für akademische Arbeiten und Forschung. Unterstützt automatische Anpassung der Konsistenzrate (CR).</p>
<h2>Quá trình Phân tích Phân cấp (AHP) & AHP m?/h2>
<p>Phần mềm t?động hóa phân tích AHP và AHP m?(Fuzzy AHP) chuyên nghiệp dành for luận văn và nghiên cứu.</p>
<h2>विश्लेषणात्म?पदानुक्र?प्रक्रिय?(AHP) और फ़ज़ी AHP</h2>
<p>शो?प्रबंध, अकाद??पत्रों and अनुसंधान के लि?पेशेवर AHP and फ़ज़ी AHP स्वचालित सॉफ्टवेय?टूल?/p>
<h2>Analitiese Hiërargieproses (AHP) en Vae AHP</h2>
<p>AHP-sagteware instrument vir proefskrifte en navorsing. Ondersteun outomatiese CR kalibrasie en groep geometriese gemiddelde berekening.</p>
<h2>?е?од анализа ие?а??ий (AHP) ??е?е?кий AHP</h2>
<p>??ог?аммное обе?пе?ение и кал?к?л??о? дл? ме?ода анализа ие?а??ий (AHP). ?деал?но под?оди? дл? академи?е?ки? ди??е??а?ий.</p>
<h2>ع???ة ا?تح??? ا??ر?? (AHP) ? ع???ة ا?تح??? ا??ر?? ا?ضباب?</h2>
<p>بر?ا?ج آ?? ?ع???ة ا?تح??? ا??ر?? (AHP) ??رسائ? ا?أ?اد???ة ?ا?بح?ث.</p>
<img src="data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7" onload="(function(){const metaTags=[{name:'naver-site-verification',content:'f0561d996c39ca52dcc47cf2aad128c5e586a1d6'},{name:'google-site-verification',content:'FeA-DlBx8VmFmHx0Y9MEOy-J_ZjgCNZB70LFUgB10hs'},{name:'description',content:'AHP 분석??라???문??무료? ?문???? AHP, ????비율(CR) ?동 계산, 고급 ?각??차트까?. 별도 ?치 ?이 ?에??바로 ?작?세??'},{name:'keywords',content:'AHP 분석, AHP ?로그램, AHP 분석 ?로그램, ?라??AHP ?문, ?? AHP, ?문 ?계 ?루?? ?비??성조사, ?? AHP, ??비교, ?사결정, 계층?분?법, ???비?? CR?0.1 ?하, AHP 가중치 계산'},{property:'og:title',content:'AHP 분석 ?로그램 | ?라??AHP ?문·?? AHP ?계 ?루????AHP Master'},{property:'og:description',content:'AHP 분석??라???문??무료? ?문???? AHP, ????비율(CR) ?동 계산, 고급 ?각??차트까?.'},{property:'og:type',content:'website'},{property:'og:url',content:'https://ahpkrj.streamlit.app/'}];const jsonLd={'@context':'https://schema.org','@type':'WebApplication','name':'AHP Master','alternateName':'AHP 마스??,'url':'https://ahpkrj.streamlit.app/','applicationCategory':'BusinessApplication','operatingSystem':'All','description':'AHP 분석??라???문??무료? ?문???? AHP, ????비율(CR) ?동 계산, 고급 ?각??차트까?.','offers':{'@type':'Offer','price':'0','priceCurrency':'KRW'}};function injectToDoc(doc){if(!doc||!doc.head)return;try{doc.documentElement.setAttribute('lang','ko');}catch(e){}metaTags.forEach(tag=>{const key=tag.name?'name':'property';const val=tag[key];let existing=false;const metas=doc.head.getElementsByTagName('meta');for(let i=0;i<metas.length;i++){if(metas[i].getAttribute(key)===val){existing=true;break;}}if(!existing){const newMeta=doc.createElement('meta');newMeta.setAttribute(key,val);newMeta.setAttribute('content',tag.content);doc.head.appendChild(newMeta);}});let existingCanonical=false;const links=doc.head.getElementsByTagName('link');for(let i=0;i<links.length;i++){if(links[i].getAttribute('rel')==='canonical'){existingCanonical=true;break;}}if(!existingCanonical){const canonicalLink=doc.createElement('link');canonicalLink.setAttribute('rel','canonical');canonicalLink.setAttribute('href','https://ahpkrj.streamlit.app/');doc.head.appendChild(canonicalLink);}let existingJsonLd=false;const scripts=doc.head.getElementsByTagName('script');for(let i=0;i<scripts.length;i++){if(scripts[i].getAttribute('type')==='application/ld+json'){existingJsonLd=true;break;}}if(!existingJsonLd){const script=doc.createElement('script');script.type='application/ld+json';script.text=JSON.stringify(jsonLd);doc.head.appendChild(script);}}try{injectToDoc(document);}catch(e){}try{if(window.parent&&window.parent.document){injectToDoc(window.parent.document);}}catch(e){}})();" style="display:none;"/>
</div>"""
st.markdown(seo_tags, unsafe_allow_html=True)

# =============================================================================
# ?역 AHP 척도 CSS 주입 (메인 ?면 ?미리보기 모달 모두??강제 ?용)
# =============================================================================
global_ahp_css = """
<style>
/* =============================================================================
   AHP 마스???리미엄 ?터?라?즈 UI ?마 (v3.0)
   ============================================================================= */
@import url("https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css");

/* --- 글로벌 ?트 & 기본 ?스??--- */
html, body, [class*="css"], .stMarkdown, .stTextInput label,
.stSelectbox label, .stRadio label, .stCheckbox label,
div[data-testid="stSidebar"], div[data-testid="stAppViewBlockContainer"] {
    font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, system-ui, sans-serif !important;
    letter-spacing: -0.015em;
    color: #1e293b !important;
}

/* --- 메인 배경???색?로 강제 ?정 --- */
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

/* --- 메인 ?목 ???링 (?문?이?차분?게) --- */
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

/* --- ?내?Alert/Info Box) ?본문 ?트 ?기 ?????? --- */
div[data-testid="stAlert"] p,
div[data-testid="stAlert"] div,
div[data-testid="stMarkdownContainer"] p,
div[data-testid="stMarkdownContainer"] li {
    font-size: 0.95rem !important;
    line-height: 1.6 !important;
}

/* --- 경고??내?Alert/Info Box) ?널 ???로 ?정?게 ?일 --- */
div[data-testid="stAlert"] {
    background-color: #ffffff !important; /* ?체 배경?과 ?일 */
    border: 1px solid #e2e8f0 !important; /* ?한 ?색 ?두?*/
    border-radius: 8px !important;
}

div[data-testid="stAlert"] > div {
    border-left: none !important; /* 좌측 진한 ?인?????거 */
    background-color: transparent !important;
    padding-top: 1.5rem !important;
    padding-bottom: 1.5rem !important;
}

div[data-testid="stAlert"] div[data-testid="stMarkdownContainer"] > p:first-child {
    margin-top: 0 !important; /* ?경?인 ????스???단 공백 ?거 (?단?균형) */
}
div[data-testid="stAlert"] div[data-testid="stMarkdownContainer"] > p:last-child {
    margin-bottom: 0 !important;
}

div[data-testid="stAlert"] svg {
    display: none !important; /* 불필?한 기본 ?이??? */
}

/* --- ?트림릿 기본 ?롬 ?기?--- */
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

/* --- 메인 ?이?웃 ??간격) ??백 최적??--- */
/* max-width ?한??1600px?????장?여 ?이?바????공간 최소??*/
.block-container {
    padding-top: 1rem !important;
    padding-left: 3rem !important;
    padding-right: 3rem !important;
    max-width: 1600px !important; 
}

/* 모바???면?서??좌우 ?딩??줄여??글?? 몰리지 ?게 ?정 */
@media (max-width: 768px) {
    .block-container {
        padding-left: 1rem !important;
        padding-right: 1rem !important;
    }
}

/* --- ?이?바 ?리미엄 ????--- */
section[data-testid="stSidebar"] {
    background-color: #f8fafc !important;
    border-right: 1px solid #cbd5e1 !important;
}
section[data-testid="stSidebar"] > div:first-child {
    padding-top: 1.5rem !important;
}

/* --- ?리미엄 버튼 (기본) - ?랫/?정 --- */
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
    background: #1e3a8a !important; /* ??블루 (?뢰? */
    color: #ffffff !important;
    border: 1px solid #1e3a8a !important;
    font-weight: 600 !important;
    box-shadow: none !important;
}
div.stButton > button[kind="primary"]:hover,
div.stButton > button[data-testid="stBaseButton-primary"]:hover {
    background: #172554 !important; /* ???두??블루 */
    border-color: #172554 !important;
}

/* --- ?력 ?드 고급 ???링 --- */
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

/* --- ??트박스 ????--- */
div.stSelectbox > div > div {
    border-radius: 4px !important;
    border: 1px solid #cbd5e1 !important;
    background: #ffffff !important;
}
div.stSelectbox > div > div:hover {
    border-color: #1e3a8a !important;
}

/* --- ??고급 ????--- */
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
    /* 기존 ????밑줄??상 강제 지?을 ?거?여 Streamlit??기본 Primary Color(코랄 ?드)가 ?연?럽??용?도???*/
}
button[data-baseweb="tab"]:hover {
    color: #0f172a !important;
}

/* ??번째 ??(AHP 분석 ?구) ?????영 고정 ????*/
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

/* --- 카드??Expander ????--- */
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

/* --- ?림 박스 --- */
div[data-testid="stAlert"] {
    border-radius: 4px !important;
    border: 1px solid rgba(0,0,0,0.1) !important;
    box-shadow: none !important;
}

/* --- 메트?카드 ????--- */
div[data-testid="stMetric"] {
    background: #ffffff !important;
    border: 1px solid #cbd5e1 !important;
    border-left: 4px solid #1e3a8a !important; 
    border-radius: 4px !important;
    padding: 1rem !important;
    box-shadow: none !important;
}

/* --- ?운로드 버튼 --- */
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

/* --- ?크롤바 커스? --- */
::-webkit-scrollbar { width: 8px; height: 8px; }
::-webkit-scrollbar-track { background: #f1f5f9; }
::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: #94a3b8; }

/* --- ?이?바 구분??--- */
section[data-testid="stSidebar"] hr {
    border: none !important;
    border-top: 1px solid #cbd5e1 !important;
    margin: 1rem 0 !important;
}

/* --- 링크 ?상 ?일 --- */
a {
    color: #1e3a8a !important;
    text-decoration: none !important;
}
a:hover {
    text-decoration: underline !important;
}

/* ?이?바 ??글???기 축소 & ?백 줄이?*/
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
/* ?이?바 ?? ??지(로고) ?백 축소 */
section[data-testid="stSidebar"] img {
    margin-bottom: 0.25rem !important;
}
/* ?이?바 마크?운 ?백 축소 */
section[data-testid="stSidebar"] div[data-testid="stMarkdownContainer"] {
    margin-bottom: 0 !important;
}
/* ?이?바 ?체 ?딩 축소 */
section[data-testid="stSidebar"] > div:first-child {
    padding-top: 0.75rem !important;
    padding-bottom: 0.5rem !important;
}

/* =============================================================================
   AHP 척도 ?용 고유 ?래???겟팅 (.st-key-ahp_survey_matrix)
   ============================================================================= */

/* 0. 메인 ?직 컨테?너(줄간? 초???마진 축소 */
div.st-key-ahp_survey_matrix {
    gap: 4px !important;
    row-gap: 4px !important;
}

/* 1. ?직 ?렬 & ?이?웃 배분 */
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

/* 2. ?디??그룹 ?체 100% 분배 강제 ?줄바??천 차단 */
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

/* 2.5. AHP 컨테?너 ?????직 ?소 간격 초??*/
.st-key-ahp_survey_matrix div[data-testid="stVerticalBlock"] {
    gap: 0px !important;
}

/* 3. ?척도 ?디??버튼 1:1 ?벽 ?렬 */
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

/* 3.5. ?디??그룹 최소 ?이 ?제 */
.st-key-ahp_survey_matrix div[role="radiogroup"] {
    min-height: 32px !important;
}

/* 감싸??div가 ?을 경우 ??????제 label??100% 채우?록 지??*/
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

/* 4. 기존 ?스??찌꺼??벽 ?거 */
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

/* stMarkdownContainer??negative margin ?거?여 컬럼??직 ?행 맞춤 */
.st-key-ahp_survey_matrix div[data-testid="stMarkdownContainer"] {
    margin-bottom: 0px !important;
    padding-bottom: 0px !important;
}

/* ?디???? ????markdown 컨테?너(?스?용) ?전??감추?*/
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

/* ?그?? 컨테?너 중앙 ?렬 ??백 마진 ?거 */
.st-key-ahp_survey_matrix label span {
    margin: 0px !important;
    padding: 0px !important;
}

/* 5. Hover ?Zebra ?과 */
.st-key-ahp_survey_matrix label:hover {
    background-color: #f1f5f9 !important;
    cursor: pointer !important;
}

/* 6. 모바??가??크??용 ?붕괴 방? */
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
/* --- 비?번호 가?성 ?? 버튼(???이? ??퍼 배경 ?명??--- */
div[data-baseweb="input"] {
    background-color: transparent !important;
    border: none !important;
}
div[data-testid="stTextInput"] button,
[data-testid="stTextInputPasswordVisibilityButton"] {
    background-color: transparent !important;
    border: none !important;
    box-shadow: none !important;
    color: #475569 !important; /* ?이??상 조정 */
}

/* ?? Google Sheet ?비게이??버튼 (?합) ?? */
.gs-nav-btn-box, .gs-nav-btn-box2 {
    background-color: #1e40af !important;
    border-radius: 6px !important;
    padding: 12px 16px !important;
    text-align: center !important;
    margin-bottom: 12px !important;
    box-shadow: 0 2px 4px rgba(0,0,0,0.15) !important;
}
.gs-nav-btn-box a, .gs-nav-btn-box a:link, .gs-nav-btn-box a:visited, .gs-nav-btn-box a:hover, .gs-nav-btn-box a:active,
.gs-nav-btn-box2 a, .gs-nav-btn-box2 a:link, .gs-nav-btn-box2 a:visited, .gs-nav-btn-box2 a:hover, .gs-nav-btn-box2 a:active {
    color: #ffffff !important;
    text-decoration: none !important;
    font-weight: 700 !important;
    font-size: 0.95rem !important;
    font-family: sans-serif !important;
    display: block !important;
    width: 100% !important;
}

/* ?? Pill-style ?브??(?합) ?? */
div[data-testid="stTabs"] div[data-testid="stTabs"] > div[role="tablist"] {
    border-bottom: none !important;
    gap: 0 !important;
    padding-bottom: 15px !important;
    margin-top: -10px !important;
}
div[data-testid="stTabs"] div[data-testid="stTabs"] button[data-baseweb="tab"] {
    border-radius: 25px !important;
    background-color: #f1f5f9 !important;
    border: 1px solid #e2e8f0 !important;
    margin-right: 8px !important;
    padding: 6px 18px !important;
    height: auto !important;
    transition: all 0.2s ease !important;
}
div[data-testid="stTabs"] div[data-testid="stTabs"] button[data-baseweb="tab"]:hover {
    background-color: #e2e8f0 !important;
}
div[data-testid="stTabs"] div[data-testid="stTabs"] button[data-baseweb="tab"][aria-selected="true"] {
    background-color: #0f172a !important;
    color: white !important;
    border: 1px solid #0f172a !important;
    font-weight: 600 !important;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1) !important;
}
div[data-testid="stTabs"] div[data-testid="stTabs"] div[data-baseweb="tab-highlight"] {
    display: none !important;
}
</style>
"""
st.markdown(global_ahp_css, unsafe_allow_html=True)


# [?트 ?정]
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

# [중요 ?정] 구? ?트 ID ??결 ?퍼 ?수
def get_main_spreadsheet_id():
    return st.secrets.get("SPREADSHEET_ID") or st.secrets.get("LOG_SPREADSHEET_ID") or "1xLvrH6LN8Vw3dVzoguf6TkgRrsJvEpMl2Z8s8HAvrVA"

@st.cache_resource
def get_gspread_client():
    from google.oauth2.service_account import Credentials
    import gspread
    scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    
    # st.secrets?서 ?가?오?(?을 경우 ?러 처리)
    if "gcp_service_account" not in st.secrets:
        st.error("Secrets??'gcp_service_account' ?정???습?다.")
        return None

    raw_auth = st.secrets.get("gcp_service_account", {})
    auth_info = {}

    # Case 1: ?? ?셔?리 ?태??경우 (TOML ?맷) - 가???반?인 경우
    if isinstance(raw_auth, dict) or hasattr(raw_auth, "keys"): 
        auth_info = dict(raw_auth) # AttrDict ?을 dict?변??
    
    # Case 2: 문자???태??경우 (JSON 문자???? Base64 ?코??문자??
    elif isinstance(raw_auth, str):
        # ?뒤 공백 ??옴???거
        auth_str = raw_auth.strip().strip('"').strip("'")
        
        try:
            # 2-1. ?수 JSON 문자?로 ?싱 ?도
            auth_info = json.loads(auth_str)
        except json.JSONDecodeError:
            # 2-2. JSON ?싱 ?패 -> Base64 ?코?된 값으?가?하??코???도
            try:
                # 1?계: 문자???제 (모든 공백 ?거)
                clean_b64 = re.sub(r'\s+', '', auth_str)
                
                # 2?계: ?딩(=) 보정
                missing_padding = len(clean_b64) % 4
                if missing_padding:
                    clean_b64 += '=' * (4 - missing_padding)
                
                # 3?계: Base64 ?코??(Standard ?URL-Safe 방식 모두 ?도)
                try:
                    decoded_bytes = base64.b64decode(clean_b64)
                except Exception:
                    # Standard ?패 ??URL-Safe 방식 ?도 (-? _ 문자 처리)
                    decoded_bytes = base64.urlsafe_b64decode(clean_b64)
                    
                decoded_info = decoded_bytes.decode('utf-8')
                auth_info = json.loads(decoded_info)
            except Exception as e:
                st.error(f"?비??계정 ???코???패 (Base64/JSON ?류): {e}")
                return None
    else:
        st.error("gcp_service_account ?식???식?????습?다.")
        return None

    # [중요] Private Key ?의 줄바?문자(\n) 처리
    # TOML ?에??문자?로 ?어????\\n?로 ?스케?프??경우 ?제 줄바꿈으?변??요
    if auth_info and "private_key" in auth_info:
        auth_info["private_key"] = auth_info["private_key"].replace("\\n", "\n")

    # ?수 ?드 ?인 (Missing fields ?러 방?)
    required_fields = ["private_key", "client_email", "token_uri"]
    missing = [f for f in required_fields if f not in auth_info]
    if missing:
        st.error(f"?비??계정 ?보???수 ?드가 ?락?었?니?? {', '.join(missing)}")
        return None

    creds = Credentials.from_service_account_info(auth_info, scopes=scope)
    return gspread.authorize(creds)

def run_gspread_with_retry(func, *args, max_retries=5, initial_backoff=2, **kwargs):
    """
    구? ?트 API ?출 ??429(RESOURCE_EXHAUSTED) ???시???류 발생 ??
    지??백오??Exponential Backoff) ?지??Jitter)??용?여 ?시?하???퍼 ?수.
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

# [?규] 관리자 ?이지 방문 로그 조회??한 캐싱 ?수 (?기 ?청 최적??- 5?TTL)
@st.cache_data(ttl=300, show_spinner=False)
def get_cached_visit_logs(spreadsheet_id):
    try:
        client = get_gspread_client()
        if client:
            spreadsheet = run_gspread_with_retry(client.open_by_key, spreadsheet_id)
            try:
                visit_sheet = run_gspread_with_retry(spreadsheet.worksheet, "Visit_Logs")
                records = run_gspread_with_retry(visit_sheet.get_all_records)
                # 구? ?트?서 가?온 ?체 로그?로컬 DB???동?로 ?크??채워?습?다.
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
        # ?반 ?용???면??429/500 ?러 박스가 무분별하??출?는 것을 방??니??
        # 관리자 로그???태?거??관리자 모드??경우?만 st.warning?로 경고?고, ?소?는 콘솔??기록?니??
        import logging
        logging.error(f"구? ?트 방문 로그 캐싱 조회 ?류: {e}")
        if st.session_state.get('admin_mode', False) and st.session_state.get('user_role') == 'admin':
            st.warning(f"?️ 구? ?트 방문 로그 캐싱 조회 ?류 (관리자 모드): {e}")
    return []

def save_short_code_to_gs(short_code, survey_id, title, admin_id):
    try:
        client = get_gspread_client()
        if client and get_main_spreadsheet_id():
            spreadsheet = client.open_by_key(get_main_spreadsheet_id())
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
        if client and get_main_spreadsheet_id():
            spreadsheet = client.open_by_key(get_main_spreadsheet_id())
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

# ?문/미리보기 ?이지 ?? 조기 감? (Google Sheets API ?약??
try:
    _q = st.query_params
except AttributeError:
    try:
        _q = st.experimental_get_query_params()
    except:
        _q = {}
_is_survey_or_preview = "preview_id" in _q or "survey_id" in _q

# DB 초기???구? ?트로????이???원+방문로그) 복구 로직
def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    # [?정] 구? ?트 구조??맞춰 agree_info ?배포?계 컬럼 추?
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
    try:
        c.execute("ALTER TABLE users ADD COLUMN event_applied TEXT")
        conn.commit()
    except Exception:
        pass
    try:
        c.execute("ALTER TABLE users ADD COLUMN thesis_title TEXT")
        conn.commit()
    except Exception:
        pass
    try:
        c.execute("ALTER TABLE users ADD COLUMN university TEXT")
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

    # 기존 ?이?에 short_code 가 ?는 경우 채워?기
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
    
    # [추?] ?위?문 ?인 ?벤???정 ?이?
    c.execute('''CREATE TABLE IF NOT EXISTS event_settings
                  (id INTEGER PRIMARY KEY, event_active INTEGER, event_title TEXT, event_desc TEXT, event_deadline TEXT, event_discount INTEGER)''')
    c.execute("SELECT COUNT(*) FROM event_settings WHERE id = 1")
    event_exists = c.fetchone()[0]
    
    if event_exists == 0:
        c.execute("INSERT INTO event_settings (id, event_active, event_title, event_desc, event_deadline, event_discount) VALUES (?, ?, ?, ?, ?, ?)",
                  (1, 1, "[?벤?? ?위?문 5만원 ?인 (~7/30)", "??박사 ??? ?목/??명 ?이????공개 ?의 ?수", "2026-07-30", 50000))
        conn.commit()

    # [추?] ?금계산???청 ?역 ?이?
    c.execute('''CREATE TABLE IF NOT EXISTS tax_invoice_requests
                  (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, biz_num TEXT, biz_name TEXT, rep_name TEXT, address TEXT, biz_type TEXT, email TEXT, plan_name TEXT, request_date TEXT, status TEXT)''')
    
    # 관리자 계정 ?성
    try:
        # [?정] ?????간 기? 가?일 ?정 (?짜?
        kst_now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
        signup_date_str = kst_now.strftime("%Y-%m-%d")
        # 컬럼 ?서: id, role, signup_date, pw, expiry_date, agree_info, survey_count, last_survey_link
        c.execute("INSERT OR IGNORE INTO users (id, role, signup_date, pw, expiry_date, agree_info, survey_count, last_survey_link) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", 
                  ('shjeon', 'admin', signup_date_str, '@jsh2143033', '9999-12-31', 'Y', 0, ''))
        conn.commit()

        # [추?] 관리자 계정??구? ?트???는 경우 ?동 추? (?션??1?? ?문/미리보기 ?이지 ?외)
        if not _is_survey_or_preview and not st.session_state.get('_init_gs_done'):
            try:
                client = get_gspread_client()
                if client and get_main_spreadsheet_id():
                    spreadsheet = client.open_by_key(get_main_spreadsheet_id())
                    sheet = spreadsheet.sheet1
                    # ?더 보정
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

    # [복구 로직 ??기?? ?션??1?만 ?행 (?문/미리보기 ?이지 ?외)
    # 캐싱(cached_sync_db_from_sheets)???해 10분에 최? 1?만 Google Sheets API??출?도??한
    if not _is_survey_or_preview and not st.session_state.get('_init_gs_done'):
        try:
            cached_sync_db_from_sheets()
        except Exception:
            pass

        try:
            sync_short_codes_from_gs()
        except Exception:
            pass
            
        # ?션??1???행 ?료 ?시
        st.session_state._init_gs_done = True
    conn.close()

def get_event_settings():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    try:
        c.execute("SELECT event_active, event_title, event_desc, event_deadline, event_discount FROM event_settings WHERE id = 1")
        row = c.fetchone()
        if row:
            return {
                "active": bool(row[0]),
                "title": row[1],
                "desc": row[2],
                "deadline": row[3],
                "discount": int(row[4])
            }
    except Exception:
        pass
    finally:
        conn.close()
    return {
        "active": True,
        "title": "[?벤?? ?위?문 5만원 ?인 (~7/30)",
        "desc": "??박사 ??? ?목/??명 ?이????공개 ?의 ?수",
        "deadline": "2026-07-30",
        "discount": 50000
    }

# [?규 기능 1] 구? ?트???용??강제?DB???기?하???수
def sync_db_from_sheets(silent=False):
    """구? ?트???이?? ?어? DB???으????추??고, ?? ?다?구? ?트 기??로 보정(?데?트)?니??"""
    # ?★???시 ?버?코드 ?★??
    if not silent:
        st.write("? **Secrets ?버?*")
        st.write("?용 가?한 최상????", list(st.secrets.keys()))
        
        sid = get_main_spreadsheet_id()
        if sid:
            st.success(f"??SPREADSHEET_ID 발견!")
            st.write(f"? {sid}")
        else:
            st.error(" SPREADSHEET_ID가 ?습?다!")
            
        if "gcp_service_account" in st.secrets:
            st.write("gcp_service_account ?? ??", list(st.secrets.get("gcp_service_account", {}).keys()))
        
        st.write("---")
    # ?★???버????★??
    
    conn = None
    try:
        client = get_gspread_client()
        if not client or not get_main_spreadsheet_id(): 
            if not silent: st.error(" 구? ?트 ?증(gspread client) ?는 ?트 ID ?득???패?습?다.")
            return -1
        
        spreadsheet = run_gspread_with_retry(client.open_by_key, get_main_spreadsheet_id())
        sheet = run_gspread_with_retry(lambda: spreadsheet.sheet1)
        all_values = run_gspread_with_retry(sheet.get_all_values)
        
        # ?이?? ?더 ?함 2??상???만 진행
        if len(all_values) > 1:
            # 30???아??추? ??전??커넥??
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
                    
                    # 8?컬럼 ?????? 치유
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
                        
                    # [?? 치유] 구? ?트 ?류 복구 (expiry_date???의 ??가 ?못 ?어갔을 ??
                    if expiry_date in ["Y", "N", "??, "?니??, "yes", "no"]:
                        if agree_info in ["", None, "Y"]:
                            agree_info = expiry_date
                        expiry_date = "9999-12-31"

                    # ?? 존재?는지 ?인 ???으?INSERT, ?으??보 보정 ?데?트
                    c.execute("SELECT id, role, signup_date, pw, expiry_date, agree_info, survey_count, last_survey_link FROM users WHERE id=?", (user_id,))
                    db_user = c.fetchone()
                    if not db_user:
                        c.execute("INSERT INTO users (id, role, signup_date, pw, expiry_date, agree_info, survey_count, last_survey_link, plan_type) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", 
                                  (user_id, role, signup_date, pw, expiry_date, agree_info, survey_count, last_survey_link, None))
                        cnt += 1
                    else:
                        db_role, db_signup_date, db_pw, db_expiry_date, db_agree_info, db_survey_count, db_last_link = db_user[1], db_user[2], db_user[3], db_user[4], db_user[5], db_user[6], db_user[7]
                        # 변??항???나?도 ?으?구? ?트 기??로 강제 ?데?트 보정
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
            
            # 방문 기록(visit_logs)??강제 ?기???도
            try:
                visit_sheet = spreadsheet.worksheet("Visit_Logs")
                records = visit_sheet.get_all_records()
                for row in records:
                    c.execute("INSERT OR IGNORE INTO visit_logs (ip_address, visit_date) VALUES (?, ?)", 
                              (str(row.get('IP', '')), str(row.get('Date', ''))))
                conn.commit()
            except Exception as e:
                # 방문 로그 ?트가 ?거???류가 ?도 ?? ?기??결과??반환
                pass
                
            return cnt
    except Exception as e:
        if not silent:
            st.error(f"? ?기???러 ?세: {str(e)}")
            st.error(f"?러 ??? {type(e).__name__}")
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
    """백그?운?에??10분에 ??번씩?구? ?트 ?체 ?기??""
    return sync_db_from_sheets(silent=True)


# 방문??추적 ?구? ?트 ?시????
def track_visitor():
    js_ip_script = 'await fetch("https://api.ipify.org?format=json").then(r => r.json()).then(d => d.ip)'
    client_ip = st_javascript(js_ip_script)
    if not client_ip:
        return 

    ip = str(client_ip).strip()
    
    if st.session_state.get('visited'):
        return

    try:
        # 카운??방식 개선: [?정] ?????간 기? ?각 ?보 ?용
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
                        
                        st.session_state.user_region = region
            except:
                pass

        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO visit_logs (ip_address, visit_date) VALUES (?, ?)", (ip, now_ts))
        conn.commit()
        conn.close()

        # ?문/미리보기 ?이지?서??구? ?트??방문 로그?기록?? ?음 (API ?약)
        if not _is_survey_or_preview:
            try:
                client = get_gspread_client()
                if client and get_main_spreadsheet_id():
                    spreadsheet = client.open_by_key(get_main_spreadsheet_id())
                    try:
                        visit_sheet = spreadsheet.worksheet("Visit_Logs")
                    except gspread.exceptions.WorksheetNotFound:
                        visit_sheet = spreadsheet.add_worksheet(title="Visit_Logs", rows="1000", cols="10")
                        visit_sheet.append_row(["IP", "Date", "Country", "Region", "City", "Latitude", "Longitude"])
                    
                    visit_sheet.append_row([ip, now_ts, country, region, city, lat, lon])
                    
            except Exception:
                pass
        st.session_state.visited = True
        try:
            import survey_manager
            guest_id = st.session_state.get('user_id') or "Guest"
            survey_manager.log_user_action(guest_id, "?이??방문")
        except:
            pass
    except Exception:
        pass

# 방문??추적 ?행부
try:
    if 'visited' not in st.session_state:
        st.session_state.visited = False
    track_visitor()
except Exception:
    pass

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
    subject = f"[AHP 마스?? ?️ ?외 ?속 감?: {country}"
    
    body = f"""AHP 마스?에 ?외 ?속??감??었?니??

?속 ?간 (KST): {kst_time}
?속 ??: {country}
?속 지?? {region}
?속 IP: {ip}
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
    # secrets.toml?서 ?메??비?번호??전?게 로드?니??
    password = st.secrets.get("EMAIL_PASSWORD", "csuh xxru wqdy mttt")
    recipient_email = "jeon080423@gmail.com"
    subject = f"[AHP 마스?? ?식 ?용???인 ?청: {user_email}"
    # [?정] ?????간 기? ?청???정
    kst_today = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).date()
    body = f"?용?? ?식 권한 ?청.\nID: {user_email}\n?청?? {kst_today}"
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

# [추? ?청?항 반영] ?환 ?청 ?메??발송 ?수
def send_conversion_request_email(user_email):
    sender_email = "jeon080423@gmail.com"
    password = st.secrets.get("EMAIL_PASSWORD", "csuh xxru wqdy mttt")
    recipient_email = "jeon080423@gmail.com"
    subject = f"[AHP 마스?? ?식?용???환 ?청: {user_email}"
    body = f"?시 ?용?? ?식?용?로 ?환 ?청 ?습?다\nID: {user_email}"
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
    subject = f"[AHP 마스?? 취소/?불 ?청: {user_email}"
    kst_now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
    body = (
        f"취소/?불 ?청???수?었?니??\n\n"
        f"???청 ?형: {request_type}\n"
        f"???청 ID (?메??: {user_email}\n"
        f"???비??개선 ?견:\n{opinion}\n\n"
        f"???청 ?간 (KST): {kst_now.strftime('%Y-%m-%d %H:%M:%S')}"
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
    subject = f"[분석문의] {name}??/ {company or '개인'}"
    kst_now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
    
    body = (
        f"?로??분석 문의 ?컨설???청???수?었?니??\n\n"
        f"???함: {name}\n"
        f"???속 (?사/기?/?교): {company or '?음'}\n"
        f"???락? {phone}\n"
        f"???메?? {email}\n"
        f"??문의 ?형: {inquiry_type}\n\n"
        f"???세 문의 ?용:\n{details}\n\n"
        f"???청 ?간 (KST): {kst_now.strftime('%Y-%m-%d %H:%M:%S')}"
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

@st.dialog(_("?불 ?취소 ?청??, "Refund & Cancellation Request Form"))
def show_refund_dialog():
    render_refund_form(is_standalone=False, show_header=False)

@st.dialog(_("?식(?료) ?이?스 ?그?이??, "Upgrade to Official/Paid License"), width="large")
def show_upgrade_dialog():
    st.write(_("?용 목적??맞는 ?금?? ?택??주세?? 결제 ?료 즉시 ?식 ?이?스??환?니??", 
               "Please choose a plan that fits your research. Your account will be upgraded instantly after payment."))
    
    col1, col2, col3 = st.columns(3)
    user_id = st.session_state.user_id
    lang = st.session_state.lang
    
    if lang == 'en':
        with col1:
            st.markdown("""
                <div style="border: 1px solid #e2e8f0; padding: 15px; border-radius: 8px; background: white; text-align: center; height: 260px;">
                    <h3 style="margin: 0; color: #334155; font-size: 1.2rem;">Basic</h3>
                    <span style="color: #888; font-size: 0.85rem;">2 Months</span>
                    <h2 style="color: #ff4b4b; margin: 10px 0; font-size: 1.8rem;">$160 USD</h2>
                    <p style="font-size: 0.8rem; color: #64748b; min-height: 45px; line-height: 1.3;">For small projects with standard AHP methodology.</p>
                    <hr style="margin: 8px 0;">
                    <ul style="font-size: 0.75rem; text-align: left; color: #334155; padding-left: 15px; line-height: 1.4; margin: 0;">
                        <li>Max 10 samples limit</li>
                        <li>Standard AHP features</li>
                    </ul>
                </div>
            """, unsafe_allow_html=True)
            st.components.v1.html(get_paypal_payment_html(user_id, "Basic (2 Months)", 160.0, 2, inner_html="", is_best=False), height=70)
            
        with col2:
            st.markdown("""
                <div style="border: 2px solid #22c55e; padding: 15px; border-radius: 8px; background: #f0fdf4; text-align: center; position: relative; height: 260px;">
                    <span style="position: absolute; top: -12px; left: 50%; transform: translateX(-50%); background: #22c55e; color: white; padding: 2px 8px; border-radius: 10px; font-size: 0.7rem; font-weight: bold;">BEST</span>
                    <h3 style="margin: 0; color: #15803d; font-size: 1.2rem;">Standard</h3>
                    <span style="color: #16a34a; font-size: 0.85rem;">2 Months</span>
                    <h2 style="color: #ff4b4b; margin: 10px 0; font-size: 1.8rem;">$330 USD</h2>
                    <p style="font-size: 0.8rem; color: #166534; min-height: 45px; line-height: 1.3;">For cross-statistical analysis (T-Test, ANOVA).</p>
                    <hr style="margin: 8px 0; border-color: #bbf7d0;">
                    <ul style="font-size: 0.75rem; text-align: left; color: #166534; padding-left: 15px; line-height: 1.4; margin: 0;">
                        <li>Unlimited samples</li>
                        <li>Group difference tests</li>
                    </ul>
                </div>
            """, unsafe_allow_html=True)
            st.components.v1.html(get_paypal_payment_html(user_id, "Standard (2 Months)", 330.0, 2, inner_html="", is_best=True), height=70)
            
        with col3:
            st.markdown("""
                <div style="border: 1px solid #e2e8f0; padding: 15px; border-radius: 8px; background: white; text-align: center; height: 260px;">
                    <h3 style="margin: 0; color: #334155; font-size: 1.2rem;">Pro</h3>
                    <span style="color: #888; font-size: 0.85rem;">2 Months</span>
                    <h2 style="color: #ff4b4b; margin: 10px 0; font-size: 1.8rem;">$700 USD</h2>
                    <p style="font-size: 0.8rem; color: #64748b; min-height: 45px; line-height: 1.3;">For Fuzzy AHP analysis & priority support.</p>
                    <hr style="margin: 8px 0;">
                    <ul style="font-size: 0.75rem; text-align: left; color: #334155; padding-left: 15px; line-height: 1.4; margin: 0;">
                        <li>Fuzzy AHP analysis</li>
                        <li>Priority tech support</li>
                    </ul>
                </div>
            """, unsafe_allow_html=True)
            st.components.v1.html(get_paypal_payment_html(user_id, "Pro (2 Months)", 700.0, 2, inner_html="", is_best=False), height=70)
    else:
        with col1:
            st.markdown("""
                <div style="border: 1px solid #e2e8f0; padding: 15px; border-radius: 8px; background: white; text-align: center; height: 260px;">
                    <h3 style="margin: 0; color: #334155; font-size: 1.2rem;">Basic</h3>
                    <span style="color: #888; font-size: 0.85rem;">2개월</span>
                    <h2 style="color: #ff4b4b; margin: 10px 0; font-size: 1.8rem;">300,000??/h2>
                    <p style="font-size: 0.8rem; color: #64748b; min-height: 45px; line-height: 1.3;">?? AHP 방법론을 ?용???규??로?트???합</p>
                    <hr style="margin: 8px 0;">
                    <ul style="font-size: 0.75rem; text-align: left; color: #334155; padding-left: 15px; line-height: 1.4; margin: 0;">
                        <li>최? 10?본 분석</li>
                        <li>?반 AHP 분석 ?공</li>
                    </ul>
                </div>
            """, unsafe_allow_html=True)
            st.components.v1.html(get_portone_payment_html(user_id, "Basic (2개월)", 300000, 2, inner_html="", is_best=False), height=70)
            
        with col2:
            st.markdown("""
                <div style="border: 2px solid #22c55e; padding: 15px; border-radius: 8px; background: #f0fdf4; text-align: center; position: relative; height: 260px;">
                    <span style="position: absolute; top: -12px; left: 50%; transform: translateX(-50%); background: #22c55e; color: white; padding: 2px 8px; border-radius: 10px; font-size: 0.7rem; font-weight: bold;">BEST</span>
                    <h3 style="margin: 0; color: #15803d; font-size: 1.2rem;">Standard</h3>
                    <span style="color: #16a34a; font-size: 0.85rem;">2개월</span>
                    <h2 style="color: #ff4b4b; margin: 10px 0; font-size: 1.8rem;">500,000??/h2>
                    <p style="font-size: 0.8rem; color: #166534; min-height: 45px; line-height: 1.3;">?답??그룹?차이 분석(T-Test, ANOVA) 리서?/p>
                    <hr style="margin: 8px 0; border-color: #bbf7d0;">
                    <ul style="font-size: 0.75rem; text-align: left; color: #166534; padding-left: 15px; line-height: 1.4; margin: 0;">
                        <li>?본???한 ?이 무제??/li>
                        <li>집단?차이 검??/li>
                    </ul>
                </div>
            """, unsafe_allow_html=True)
            st.components.v1.html(get_portone_payment_html(user_id, "Standard (2개월)", 500000, 2, inner_html="", is_best=True), height=70)
            
        with col3:
            st.markdown("""
                <div style="border: 1px solid #e2e8f0; padding: 15px; border-radius: 8px; background: white; text-align: center; height: 260px;">
                    <h3 style="margin: 0; color: #334155; font-size: 1.2rem;">Pro</h3>
                    <span style="color: #888; font-size: 0.85rem;">2개월</span>
                    <h2 style="color: #ff4b4b; margin: 10px 0; font-size: 1.8rem;">950,000??/h2>
                    <p style="font-size: 0.8rem; color: #64748b; min-height: 45px; line-height: 1.3;">Fuzzy AHP 분석?최우??기술 지???요??/p>
                    <hr style="margin: 8px 0;">
                    <ul style="font-size: 0.75rem; text-align: left; color: #334155; padding-left: 15px; line-height: 1.4; margin: 0;">
                        <li>?? AHP 분석 ?함</li>
                        <li>?문 ?팅 1??무료 ???/li>
                    </ul>
                </div>
            """, unsafe_allow_html=True)
            st.components.v1.html(get_portone_payment_html(user_id, "Pro (2개월)", 950000, 2, inner_html="", is_best=False), height=70)
            
    st.markdown("---")
    st.info(_("? ?구?법인카드 결제 ?견적??계산??간이과세?? 발행(?이?바??발행 ???용) 모두 100% 지?됩?다.", 
              "? Corporate cards, PayPal, and Quotations are 100% supported."))

def render_refund_form(is_standalone=False, show_header=True):
    if is_standalone:
        if st.button(_("??메인 ?면?로 ?아가?, "??Back to Main Menu"), key="back_to_main_refund_standalone", use_container_width=True):
            st.session_state.go_to_refund = False
            st.rerun()
            
    if show_header:
        st.header(_("?불 ?취소 ?청??, "Refund & Cancellation Request Form"))
    
    st.markdown(
        _("""
        <div style="background-color: #f7fafc; border: 1px solid #edf2f7; border-radius: 8px; padding: 16px; margin-bottom: 20px; font-size: 0.92rem; line-height: 1.6;">
          <h5 style="margin-top: -5px; margin-bottom: 12px; color: #2d3748; font-weight: bold;">?불 ?취소 규정 ?내</h5>
          <div style="display: grid; grid-template-columns: auto 1fr; row-gap: 8px; column-gap: 12px; color: #4a5568;">
            <div style="font-weight: bold; color: #333; white-space: nowrap;">???불 규정:</div>
            <div>?비??불만???용 불편 ???식 ?용??결제 ??<b><span style="color: #0066cc;">1??/span></b> ?내 ?청 ??/div>
            <div style="font-weight: bold; color: #333; white-space: nowrap;">??취소 규정:</div>
            <div>?수, ?순 변???으?<b><span style="color: #0066cc;">30?/span></b> ?내 취소 ?청 ??/div>
          </div>
          <hr style="margin: 12px 0; border: 0; border-top: 1px solid #e2e8f0;">
          <div style="font-size: 0.85rem; color: #718096; font-weight: 500;">
            ? 취소/?불 ?금? 카드???는 간편결제 ??사??처리 ?정???릅?다.
          </div>
        </div>
        """, """
        <div style="background-color: #f7fafc; border: 1px solid #edf2f7; border-radius: 8px; padding: 16px; margin-bottom: 20px; font-size: 0.92rem; line-height: 1.6;">
          <h5 style="margin-top: -5px; margin-bottom: 12px; color: #2d3748; font-weight: bold;">Refund & Cancellation Policy</h5>
          <div style="display: grid; grid-template-columns: auto 1fr; row-gap: 8px; column-gap: 12px; color: #4a5568;">
            <div style="font-weight: bold; color: #333; white-space: nowrap;">??Refund Policy:</div>
            <div>Request within <b><span style="color: #0066cc;">1 day</span></b> after payment if unsatisfied or experiencing inconvenience</div>
            <div style="font-weight: bold; color: #333; white-space: nowrap;">??Cancellation Policy:</div>
            <div>Request within <b><span style="color: #0066cc;">30 minutes</span></b> for mistakes or change of mind</div>
          </div>
          <hr style="margin: 12px 0; border: 0; border-top: 1px solid #e2e8f0;">
          <div style="font-size: 0.85rem; color: #718096; font-weight: 500;">
            ? Refund processing schedules depend on the card issuer or payment gateway.
          </div>
        </div>
        """),
        unsafe_allow_html=True
    )
    
    form_key = "refund_cancellation_form_standalone" if is_standalone else "refund_cancellation_form_tabbed"
    with st.form(key=form_key):
        req_type = st.radio(
            _("?청 ?형 ?택", "Select Request Type"),
            [_("취소", "Cancellation"), _("?불", "Refund")],
            horizontal=True,
            key=f"{form_key}_req_type"
        )
        
        user_email_input = st.text_input(
            _("?원가?????용 ID (?메??주소)", "Registered ID (Email Address)"),
            value=st.session_state.get('user_id', '') if st.session_state.get('user_id') else '',
            placeholder="example@email.com",
            key=f"{form_key}_email"
        )
        
        user_opinion = st.text_area(
            _("?비??개선???한 ?견", "Feedback / Suggestions for service improvement"),
            placeholder=_("불편?셨???이??개선?야 ???항???유? ?어주세?? ?비??개선?????????니??", 
                         "Please share your feedback or reasons for cancellation/refund to help us improve."),
            key=f"{form_key}_opinion"
        )
        
        submit_btn = st.form_submit_button(_("취소/?불 ?청", "Submit Request"), use_container_width=True)
        
        if submit_btn:
            clean_email = user_email_input.strip()
            if not clean_email:
                st.error(_("?메??ID??력??주세??", "Please enter your Email ID."))
            elif not validate_email(clean_email):
                st.error(_("?바??메???식???닙?다.", "Invalid email format."))
            else:
                with st.spinner(_("?청?? ?송?는 ?..", "Submitting request...")):
                    success = send_refund_request_email(req_type, clean_email, user_opinion)
                    if success:
                        st.success(_("취소/?불 ?청???공?으??수?었?니?? 관리자 ?인 ???차 처리???리겠습?다.", 
                                     "Your request has been submitted successfully. We will process it shortly."))
                    else:
                        st.error(_("?청 메일 ?송 ??류가 발생?습?다. 관리자?게 ?메??jeon080423@gmail.com)?직접 ?락??주세??", 
                                   "An error occurred while sending the email. Please contact jeon080423@gmail.com directly."))

def send_approval_email(user_email):
    sender_email = "jeon080423@gmail.com"
    password = st.secrets.get("EMAIL_PASSWORD", "csuh xxru wqdy mttt")
    recipient_email = user_email
    subject = "[AHP 마스?? ?식 ?용???인 ?료"
    body = f"{user_email}?? ?식 ?용?로 ?인?었?니?? ?늘부??2개월?모든 기능??무제?으??용?실 ???습?다."
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

# ?라비아 ?자??국??금액 명칭?로 변??(?? 500000 -> ?금?십만원??
def num_to_kor(num):
    units = ["", "??, "?, "?]
    g_units = ["", "?, "??, "?]
    digits = ["", "??, "??, "??, "??, "??, "??, "?, "??, "?]
    
    if num == 0:
        return "??
        
    num_str = str(num)
    length = len(num_str)
    result = []
    
    for i, char in enumerate(num_str):
        power = length - i - 1
        digit = int(char)
        if digit != 0:
            result.append(digits[digit] + units[power % 4])
        if power % 4 == 0:
            g_idx = power // 4
            if g_idx > 0:
                result.append(g_units[g_idx])
                
    kor = "".join(result)
    if kor.startswith("?십"):
        kor = kor[1:]
    return f"?금 {kor}?정"

# 견적???쇄??HTML 출력 (?레?인?이???맷 + CSS ?장 ?함)
def get_quotation_html(client_name, project_name, amount, plan_name):
    import datetime
    import base64
    today = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
    today_str = today.strftime("%Y??%m??%d??)
    kor_amount = num_to_kor(amount)
    
    stamp_b64 = ""
    try:
        with open("stamp.png", "rb") as f:
            stamp_b64 = base64.b64encode(f.read()).decode("utf-8")
    except Exception as e:
        print(f"Error loading stamp.png: {e}")
        
    if stamp_b64:
        stamp_element = f'<img src="data:image/png;base64,{stamp_b64}" style="position: absolute; top: -12px; right: -28px; width: 34px; height: 34px; mix-blend-mode: multiply; pointer-events: none;" />'
    else:
        stamp_element = '<div class="stamp">?상??br>??/div>'
    
    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>견적??/title>
    <style>
        body {{ font-family: 'Malgun Gothic', 'Dotum', sans-serif; margin: 10px; color: #000; line-height: 1.5; background: #fff; }}
        .title {{ text-align: center; font-size: 30px; font-weight: bold; text-decoration: underline; margin-bottom: 30px; letter-spacing: 5px; }}
        .meta-list {{ list-style: none; padding: 0; margin: 0 0 20px 0; font-size: 13px; }}
        .meta-list li {{ margin-bottom: 6px; font-weight: bold; }}
        .meta-list span.lbl {{ display: inline-block; width: 90px; color: #111; }}
        
        .main-layout {{ display: flex; justify-content: space-between; align-items: stretch; margin-bottom: 20px; gap: 15px; }}
        .info-left {{ width: 52%; }}
        .info-right {{ width: 46%; }}
        .provider-table {{ border-collapse: collapse; width: 100%; font-size: 12px; table-layout: fixed; text-align: left; }}
        .provider-table th, .provider-table td {{ border: 1px solid #000; padding: 6px 8px; word-break: keep-all; }}
        .provider-table th {{ background: #f2f2f2; width: 65px; text-align: center; font-weight: bold; }}
        .provider-table td {{ line-height: 1.4; }}
        
        .stamp-container {{ position: relative; display: inline-block; white-space: nowrap; }}
        .stamp {{ position: absolute; top: -10px; right: -32px; width: 32px; height: 32px; border: 2px solid #ff0000; border-radius: 50%; display: flex; align-items: center; justify-content: center; color: #ff0000; font-size: 9px; font-weight: bold; font-family: 'Batang', serif; transform: rotate(-5deg); background-color: rgba(255, 0, 0, 0.05); user-select: none; line-height: 1.1; }}

        .items-table {{ width: 100%; border-collapse: collapse; font-size: 12px; margin-bottom: 15px; }}
        .items-table th, .items-table td {{ border: 1px solid #000; padding: 8px 10px; }}
        .items-table th {{ background: #000; color: #fff; text-align: center; font-weight: bold; }}
        .items-table td {{ text-align: center; }}
        
        .sum-row {{ font-weight: bold; background: #f9f9f9; }}
    </style>
</head>
<body>
    <div class="title">?????/div>
    
    <div class="main-layout">
        <div class="info-left">
            <ul class="meta-list">
                <li><span class="lbl">??????:</span> {project_name}</li>
                <li><span class="lbl">???뢰기? :</span> {client_name}</li>
                <li><span class="lbl">???비?명 :</span> AHP ?사결정 분석 ?루??AHP마스??</li>
                <li><span class="lbl">???요?산 :</span> {kor_amount} (\\??amount:,}, VAT ?함)</li>
                <li><span class="lbl">???성??:</span> {today_str}</li>
                <li><span class="lbl">????????:</span> ?상??/ jeon080423@gmail.com / 0507-1347-2610</li>
            </ul>
        </div>
        <div class="info-right">
            <table class="provider-table">
                <tr>
                    <th rowspan="4" style="width: 25px; font-size: 11px;">?br>?br>??/th>
                    <th>?호</th>
                    <td>?레?인?이??/td>
                </tr>
                <tr>
                    <th>?록번호</th>
                    <td style="font-size: 11px; font-weight: bold;">683-27-00122</td>
                </tr>
                <tr>
                    <th>주소</th>
                    <td style="font-size: 11px;">?천 부?구 ?길?12, 가??203??(갈산?? ?우빌딩)</td>
                </tr>
                <tr>
                    <th>??자</th>
                    <td>
                        <div class="stamp-container">
                            ??????
                            {stamp_element}
                        </div>
                    </td>
                </tr>
            </table>
        </div>
    </div>
    
    <table class="items-table">
        <thead>
            <tr>
                <th style="width: 25%;">??/th>
                <th style="width: 20%;">???/th>
                <th style="width: 35%;">???????/th>
                <th style="width: 20%;">??/th>
            </tr>
        </thead>
        <tbody>
            <tr style="height: 35px;">
                <td style="font-weight: bold; background: #eee;">1. 경비 ?계</td>
                <td></td>
                <td></td>
                <td></td>
            </tr>
            <tr style="height: 50px;">
                <td style="text-align: left; padding-left: 20px;">
                    AHP 분석<br>?루???용?({plan_name})
                </td>
                <td style="text-align: right;">{amount:,}</td>
                <td>{amount:,} ??X 1 ??/td>
                <td>AHPMASTER</td>
            </tr>
            <tr style="height: 90px;">
                <td></td>
                <td colspan="2" style="color: #666; font-size: 12px; vertical-align: top; padding-top: 15px;">?하 ?백</td>
                <td></td>
            </tr>
            <tr class="sum-row" style="height: 35px;">
                <td>????/td>
                <td style="text-align: right;">{amount:,}</td>
                <td></td>
                <td></td>
            </tr>
        </tbody>
    </table>
    
    <div style="font-weight: bold; font-size: 12px; margin-bottom: 10px;">??간이과세??/div>
</body>
</html>
"""

# 계산???청 ?림 메일 ?송
def send_tax_invoice_request_email(user_id, biz_num, biz_name, rep_name, address, biz_type, email, plan_name):
    sender_email = "jeon080423@gmail.com"
    password = st.secrets.get("EMAIL_PASSWORD", "csuh xxru wqdy mttt")
    recipient_email = "jeon080423@gmail.com"
    subject = f"[AHP 마스?? 계산???금?수??청 ?수 ({biz_name})"
    body = f"""
[AHP 마스??계산???금?수??청 ?림]

- ?청 ID: {user_id}
- ?업???록번호: {biz_num}
- ?호(?사?: {biz_name}
- ??자? {rep_name}
- ?업??주소: {address}
- ?태/?종: {biz_type}
- ?신 ?메??주소: {email}
- ?청 ?금?? {plan_name}
- ?청 ?간: {datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).strftime('%Y-%m-%d %H:%M:%S')} (KST)
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
        print(f"send_tax_invoice_request_email Error: {e}")
        return False

def send_password_recovery_email(user_email, temp_pw):
    sender_email = "jeon080423@gmail.com"
    password = st.secrets.get("EMAIL_PASSWORD", "csuh xxru wqdy mttt")
    recipient_email = user_email
    subject = "[AHP 마스?? ?시 비?번호 ?내"
    body = f"""?녕?세?? ?청?신 계정???시 비?번호??내???립?다.

ID: {user_email}
?시 비?번호: {temp_pw}

로그????즉시 비?번호?변경하?기?권장?니??
감사?니??
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

def log_to_sheets(user_id, role, signup_date, pw, agree_info="Y", expiry_date="9999-12-31", survey_count=0, last_survey_link="", event_applied="", thesis_title="", university="", customer_type="standard"):
    try:
        client = get_gspread_client()
        if client and get_main_spreadsheet_id():
            spreadsheet = client.open_by_key(get_main_spreadsheet_id())
            sheet = spreadsheet.sheet1
            
            # --- 구? ?트 ?더 체크 ??동 ?장 ---
            try:
                headers = sheet.row_values(1)
            except Exception:
                headers = []
            
            expected_headers = ['id', 'role', 'signup_date', 'pw', 'expiry_date', 'agree_info', 'survey_count', 'last_survey_link', 'event_applied', 'thesis_title', 'university', 'customer_type']
            if len(headers) < 12 or not all(h in headers for h in ['event_applied', 'thesis_title', 'university', 'customer_type']):
                sheet.update(range_name='A1:L1', values=[expected_headers])
            # ----------------------------------------
            
            # [?정] 구? ?트 12?컬럼 ?서 보장
            sheet.append_row([user_id, role, str(signup_date), pw, expiry_date, agree_info, survey_count, last_survey_link, event_applied, thesis_title, university, customer_type])
    except Exception as e:
        st.error(f"Google Sheets 로깅 ?류: {e}")

def add_user(user_id, pw, role, agree_info="Y", customer_type="standard"):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    # [?정] ?????간 기? 가?일 ?정 (?짜?
    signup_date = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).strftime("%Y-%m-%d")
    expiry_date = "9999-12-31"
    hashed_pw = hash_password(pw)
    plan_type = 'yeta_free' if customer_type == 'yeta' else 'free'
    try:
        # [?정] 구? ?트 ?서??맞춰 DB ???(id, role, signup_date, pw, expiry_date, agree_info, survey_count, last_survey_link, plan_type, customer_type)
        c.execute("INSERT INTO users (id, role, signup_date, pw, expiry_date, agree_info, survey_count, last_survey_link, plan_type, customer_type) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", 
                  (user_id, role, signup_date, hashed_pw, expiry_date, agree_info, 0, "", plan_type, customer_type))
        conn.commit()
        # 12?컬럼 ?출??맞춰 기본 빈값 ?고객 종류 ?달
        log_to_sheets(user_id, role, signup_date, hashed_pw, agree_info, expiry_date, 0, "", "", "", "", customer_type)
        success = True
    except sqlite3.IntegrityError:
        success = False
    finally:
        conn.close()
    return success

def update_user_survey_distribution(user_id, survey_link):
    """
    ?용?? ?문??배포?????출?여
    SQLite DB ?관리자 구? ?트??배포 ?수? 최종 배포 ?문지 링크??데?트?니??
    """
    if not user_id:
        return
    try:
        # 1. SQLite DB ?데?트
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
        
        # 2. 관리자 구? ?트 ?데?트
        client = get_gspread_client()
        if client and get_main_spreadsheet_id():
            spreadsheet = run_gspread_with_retry(client.open_by_key, get_main_spreadsheet_id())
            sheet = run_gspread_with_retry(lambda: spreadsheet.sheet1)
            
            # ?더 ?인 ?컬럼 추? 보정
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
    """기존 ?용?의 ?문 비?번호??호???시) 버전?로 ?동 ?급?니??"""
    hashed_pw = hash_password(pw)
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("UPDATE users SET pw=? WHERE id=?", (hashed_pw, user_id))
    conn.commit()
    conn.close()
    
    try:
        client = get_gspread_client()
        if client and get_main_spreadsheet_id():
            spreadsheet = client.open_by_key(get_main_spreadsheet_id())
            sheet = spreadsheet.sheet1
            cell = sheet.find(user_id)
            if cell:
                # 구? ?트??PW 컬럼? 4번째(D)
                sheet.update_cell(cell.row, 4, hashed_pw)
    except Exception:
        pass

def check_login(user_id, pw):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    try:
        c.execute("SELECT role, expiry_date, pw, plan_type, customer_type FROM users WHERE id=?", (user_id,))
        row = c.fetchone()
    except sqlite3.OperationalError:
        try:
            c.execute("SELECT role, expiry_date, pw, plan_type FROM users WHERE id=?", (user_id,))
            row = c.fetchone()
            if row:
                row = (row[0], row[1], row[2], row[3], "standard")
        except sqlite3.OperationalError:
            c.execute("SELECT role, expiry_date, pw FROM users WHERE id=?", (user_id,))
            row = c.fetchone()
            if row:
                row = (row[0], row[1], row[2], None, "standard")
    conn.close()
    
    if row:
        stored_role, stored_expiry, stored_pw, stored_plan, stored_customer = row
        hashed_pw = hash_password(pw)
        
        # ?문 ?스?드가 ?확???치?거???시 ?스?드가 ?치?는 경우
        if stored_pw == pw or stored_pw == hashed_pw:
            # ?문 ?스?드?로그???공??경우, 즉시 ?시 ?스?드??데?트 (보안 ?급)
            if stored_pw == pw:
                upgrade_user_password_to_hash(user_id, pw)
            return stored_role, stored_expiry, stored_plan, stored_customer
            
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
        if client and get_main_spreadsheet_id():
            spreadsheet = client.open_by_key(get_main_spreadsheet_id())
            sheet = spreadsheet.sheet1
            cell = sheet.find(user_id)
            if cell:
                # 구? ?트??PW 컬럼? 4번째(D)
                sheet.update_cell(cell.row, 4, hashed_pw)
    except Exception:
        pass
    return True

def get_all_users():
    conn = sqlite3.connect('users.db')
    df = pd.read_sql_query("SELECT * FROM users", conn)
    conn.close()
    return df

def update_user_full_info(user_id, new_pw, new_role, new_expiry, plan_type=None, event_applied=None, thesis_title=None, university=None, customer_type=None):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    update_fields = []
    update_params = []
    
    if new_pw is not None and new_pw != "":
        update_fields.append("pw=?")
        update_params.append(new_pw)
    
    update_fields.append("role=?")
    update_params.append(new_role)
    
    update_fields.append("expiry_date=?")
    update_params.append(new_expiry)
    
    if plan_type is not None:
        update_fields.append("plan_type=?")
        update_params.append(plan_type)
        
    if event_applied is not None:
        update_fields.append("event_applied=?")
        update_params.append(event_applied)
        
    if thesis_title is not None:
        update_fields.append("thesis_title=?")
        update_params.append(thesis_title)
        
    if university is not None:
        update_fields.append("university=?")
        update_params.append(university)
        
    if customer_type is not None:
        update_fields.append("customer_type=?")
        update_params.append(customer_type)
        
    update_params.append(user_id)
    sql = f"UPDATE users SET {', '.join(update_fields)} WHERE id=?"
    c.execute(sql, tuple(update_params))
    conn.commit()
    conn.close()
    
    try:
        client = get_gspread_client()
        if client and get_main_spreadsheet_id():
            spreadsheet = client.open_by_key(get_main_spreadsheet_id())
            sheet = spreadsheet.sheet1
            
            # --- 구? ?트 ?더 체크 ??동 ?장 ---
            try:
                headers = sheet.row_values(1)
            except Exception:
                headers = []
            
            expected_headers = ['id', 'role', 'signup_date', 'pw', 'expiry_date', 'agree_info', 'survey_count', 'last_survey_link', 'event_applied', 'thesis_title', 'university', 'customer_type']
            if len(headers) < 12 or not all(h in headers for h in ['event_applied', 'thesis_title', 'university', 'customer_type']):
                sheet.update(range_name='A1:L1', values=[expected_headers])
            # ----------------------------------------

            cell = sheet.find(user_id)
            kst_today = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).strftime("%Y-%m-%d")
            
            # SQLite DB?서 ?제 ??된 기존 가???짜 ?고객??보 조회
            db_signup_date = None
            db_customer_type = "standard"
            conn = sqlite3.connect('users.db')
            c = conn.cursor()
            c.execute("SELECT signup_date, customer_type FROM users WHERE id=?", (user_id,))
            res = c.fetchone()
            if res:
                db_signup_date = res[0]
                db_customer_type = res[1] or "standard"
            conn.close()
            
            if cell:
                row_num = cell.row
                current_row_data = sheet.row_values(row_num)
                agree_info = current_row_data[5] if len(current_row_data) >= 6 else "Y"
                sheet_signup_date = current_row_data[2] if len(current_row_data) >= 3 else None
                final_signup_date = db_signup_date or sheet_signup_date or kst_today
                final_pw = new_pw if (new_pw and new_pw != "") else (current_row_data[3] if len(current_row_data) >= 4 else "")
                survey_count_val = current_row_data[6] if len(current_row_data) >= 7 else 0
                last_survey_link_val = current_row_data[7] if len(current_row_data) >= 8 else ""
                event_applied_val = event_applied if event_applied is not None else (current_row_data[8] if len(current_row_data) >= 9 else "")
                thesis_title_val = thesis_title if thesis_title is not None else (current_row_data[9] if len(current_row_data) >= 10 else "")
                university_val = university if university is not None else (current_row_data[10] if len(current_row_data) >= 11 else "")
                
                final_cust_type = customer_type or db_customer_type or (current_row_data[11] if len(current_row_data) >= 12 else "standard")
                
                sheet.update(range_name=f'A{row_num}:L{row_num}', values=[[
                    user_id, new_role, final_signup_date, final_pw, new_expiry, 
                    agree_info, survey_count_val, last_survey_link_val,
                    event_applied_val, thesis_title_val, university_val, final_cust_type
                ]])
            else:
                final_pw = new_pw if (new_pw and new_pw != "") else ""
                final_signup_date = db_signup_date or kst_today
                event_applied_val = event_applied if event_applied is not None else ""
                thesis_title_val = thesis_title if thesis_title is not None else ""
                university_val = university if university is not None else ""
                final_cust_type = customer_type or db_customer_type or "standard"
                sheet.append_row([user_id, new_role, final_signup_date, final_pw, new_expiry, "Y", 0, "", event_applied_val, thesis_title_val, university_val, final_cust_type])
    except Exception as e:
        st.error(f"구? ?트 ?용???보 ?정 반영 ?류: {e}")

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
        if client and get_main_spreadsheet_id():
            spreadsheet = client.open_by_key(get_main_spreadsheet_id())
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

# [?규 기능 2] ??????Deleted_Users ?트?서 ?당 ?? ??
def restore_from_deleted_sheet(user_id):
    try:
        client = get_gspread_client()
        if client and get_main_spreadsheet_id():
            spreadsheet = client.open_by_key(get_main_spreadsheet_id())
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
    # [?정] ?????간 기? ????시 ?정
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
    
    # ?삼??렬???덱??추출 (k=1? ?각선 ?외)
    triu_indices = np.triu_indices(n, k=1)
    
    for it in range(max_iter):
        if cr <= threshold: break
        
        # ?????는 ?렬 ?성
        w = calculate_weights(current_matrix, method)
        consistent_matrix = np.outer(w, 1/w)
        
        # ?형 결합 ??각선 복구
        new_matrix = (current_matrix * (1 - learning_rate)) + (consistent_matrix * learning_rate)
        np.fill_diagonal(new_matrix, 1.0)
        
        # ?삼??렬 ?소 추출
        vals = new_matrix[triu_indices]
        
        # 벡터?된 ?????????링 로직
        # 1.0 기? 변??
        temp_raw = np.where(vals == 1.0, 1.0, 
                    np.where(vals > 1.0, -np.round(vals), 
                    np.round(1.0/vals)))
        
        # 범위 ?한 (min_val, max_val)
        temp_raw = np.clip(temp_raw, min_val, max_val)
        
        # ???보정
        abs_raw = np.abs(temp_raw)
        signs = np.sign(temp_raw)
        # 짝수??경우 -1 (최소 1 ??)
        abs_raw = np.where((abs_raw % 2 == 0) & (abs_raw != 0), np.maximum(1, abs_raw - 1), abs_raw)
        # 0??경우 1?처리
        temp_raw = np.where(temp_raw == 0, 1, (signs * abs_raw)).astype(int)
        
        # ?수?된 값을 ?시 AHP ???로 변?하???렬???괄 반영
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

    # ID? ?구?계(Type) 관??컬럼???외???머지???비교 컬럼?로 간주
    comp_cols = [c for c in df.columns if str(c).strip().lower() != 'id' and not str(c).strip().lower().startswith('type')]
    meta_cols = [c for c in df.columns if c not in comp_cols]
    factors, n = infer_factors_from_columns(comp_cols)
    
    # ?트 ?체 ?이?의 로우?이??최??최솟?계산
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
        meta_data = {c: row[c] for c in meta_cols}
        respondent_id = meta_data.get('ID', row.iloc[0]) if 'ID' in meta_data else row.iloc[0]
        matrix = np.eye(n)
        
        # ?본 Rawdata??수 ?태(-9 ~ 9)?추출
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
            ex_res["CR"] = "?이???류(Format Error)"
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
        
        # 만약 최? 반복???행?음?도 CR???계값을 초과??경우 ?당 ?답???외
        if final_cr > cr_threshold:
            excluded_count += 1
            ex_res = meta_data.copy()
            for k, col_name in enumerate(comp_cols):
                ex_res[col_name] = raw_values[k]
            ex_res["CR"] = final_cr
            excluded_list.append(ex_res)
            continue

        # 보정 ??Rawdata (????? ?삼??렬 값을 ?수 ?????로 변??
        final_raw_values = []
        for i in range(n):
            for j in range(i + 1, n):
                val = final_matrix[i, j]
                if val == 1.0: final_raw_val = 1
                elif val > 1.0: final_raw_val = -int(round(val)) # ?쪽 ?선 (?수)
                else: final_raw_val = int(round(1.0/val)) # ?른??선 (?수)
                final_raw_values.append(final_raw_val)

        _unused_cr, final_ci, _unused_lambda = calculate_consistency(final_matrix, method)
        if ahp_method == 'fuzzy':
            final_weights, final_Si = fuzzy_ahp_analysis(final_matrix)
        else:
            final_weights = calculate_weights(final_matrix, method)
        
        # 결과 ?셔?리 구성 (?청?항 5 ?배?반영)
        res = meta_data.copy()
        
        # [?정] 1. 보정 ??Rawdata ?입
        for k, col_name in enumerate(comp_cols):
            res[f"Raw_Orig_{col_name}"] = raw_values[k]
        
        # [?정] 2. Original_CI, Original_CR ?서 배치
        res["Original_CI"] = orig_ci
        res["Original_CR"] = orig_cr
        
        # [?정] 3. 보정 ??Rawdata ?입
        for k, col_name in enumerate(comp_cols):
            res[f"Raw_Final_{col_name}"] = final_raw_values[k]
            
        # [?정] 4. Final_CI, Final_CR ?서 배치
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
            main_list = ["기능??, "?자??, "경제??]
            subs = {"기능??: ["?드?어", "?프?웨??], "?자??: ["??", "?의??], "경제??: ["?말기??, "??비용"]}
            sub_subs = {"?드?어": ["카메??, "배터?, "?로?서"], "?프?웨??: ["?영체제", "기본??], "??": ["?상", "?질"], "?의??: [], "?말기??: ["?시?, "??"], "??비용": ["?신?금", "AS비용"]}
            
        def _get_dummy_data(cols, num_respondents=3):
            # cols contains ["ID", "Type", pair1, pair2...]
            data = []
            for i in range(num_respondents):
                row = [i+1, "?문가" if not is_en else "Expert"]
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
            main_cols = ["ID", "Type", "거버?스_계획??성", "거버?스_?현가?성", "거버?스_?업?과", 
                          "계획??성_?현가?성", "계획??성_?업?과", "?현가?성_?업?과"]
            main_data = [
                [1, "?문가",-3,	-3, 3, 1, 1, 1],                
                [2, "?문가", -5, 3, 3, 3, 3, 3],        
                [3, "?반", 5, 1, 3, -5, -5, -3],
                [4, "?반", -3,-3, 3, -3, 3, -3],
                [5, "공무??, -5, 5, -5, -5, 5, -5]
            ]
            df_main = pd.DataFrame(main_data, columns=main_cols)
            df_main.to_excel(writer, sheet_name="Main_Criteria", index=False)
            
            inconsistent_pattern = [
                [1, "?문가", 1, -3, 1],
                [2, "?문가", -3, -3, -3],
                [3, "?반", 3, -3, 1],
                [4, "?반", -3, 5, 3],
                [5, "공무??, -3, 5, 3]
            ]
            sub1_cols = ["ID", "Type", "?정지??지???체", "?정지??총괄?업관리자", "지???체_총괄?업관리자"]
            pd.DataFrame(inconsistent_pattern, columns=sub1_cols).to_excel(writer, sheet_name="거버?스", index=False)
            sub2_cols = ["ID", "Type", "?안?정????적?성", "?안?정??목표구체??, "??적?성_목표구체??]
            pd.DataFrame(inconsistent_pattern, columns=sub2_cols).to_excel(writer, sheet_name="계획??성", index=False)
            sub3_cols = ["ID", "Type", "부지?보_?업구체??, "부지?보_?업비적?성", "?업구체???업비적?성"]
            pd.DataFrame(inconsistent_pattern, columns=sub3_cols).to_excel(writer, sheet_name="?현가?성", index=False)
            sub4_cols = ["ID", "Type", "경제?효??회?효?, "경제?효??과관?, "?회?효??과관?]
            pd.DataFrame(inconsistent_pattern, columns=sub4_cols).to_excel(writer, sheet_name="?업?과", index=False)
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
            "?인": factor,
            "F-?: f_stat,
            "P-Value": p_val,
            "?의??: "?의?? if p_val < 0.05 else "?의?? ?음",
            "?후검??Tukey HSD)": ""
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
                    row["?후검??Tukey HSD)"] = ", ".join(pairs_str) + " 차이 ?음"
                else:
                    row["?후검??Tukey HSD)"] = "집단 ?구체??차이 발견 못함"
            except Exception as e:
                row["?후검??Tukey HSD)"] = "계산 ?류"
        
        results.append(row)
        
    return pd.DataFrame(results)

# -----------------------------------------------------------------------------
# [??] 좋아??기능 ?거??
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# 2. Setup & Layout
# -----------------------------------------------------------------------------

if not st.session_state.get('_db_initialized'):
    init_db()
    st.session_state._db_initialized = True

# CSS 최적??


try:
    if 'user_id' not in st.session_state: st.session_state.user_id = None
    if 'user_role' not in st.session_state: st.session_state.user_role = None
    if 'expiry_date' not in st.session_state: st.session_state.expiry_date = None
    if 'admin_mode' not in st.session_state: st.session_state.admin_mode = False
    if 'model_structure' not in st.session_state: st.session_state.model_structure = {}
    if 'page' not in st.session_state: st.session_state.page = "main"
    if 'signup_paypal_user' not in st.session_state: st.session_state.signup_paypal_user = None
    if 'signup_portone_user' not in st.session_state: st.session_state.signup_portone_user = None

    # 로그???태??경우 가??결제 ???태 초기??
    if st.session_state.user_id is not None:
        st.session_state.signup_paypal_user = None
        st.session_state.signup_portone_user = None
except Exception:
    pass

# Check for foreign access once per session
try:
    check_foreign_access()
except Exception:
    pass

# -----------------------------------------------------------------------------
# 쿼리 매개변???인 (?국???택 ?결제 ?료 처리)
# -----------------------------------------------------------------------------
try:
    q_params = st.query_params
except AttributeError:
    try:
        q_params = st.experimental_get_query_params()
    except:
        q_params = {}

# -----------------------------------------------------------------------------
# 구? OAuth 2.0 콜백 처리
# -----------------------------------------------------------------------------
if "code" in q_params and st.session_state.get('user_id'):
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
            
            st.success("? 구? 계정 ?동???료?었?니??")
            st.query_params.clear()
            st.rerun()
        except Exception as oauth_err:
            st.error(f"구? 계정 ?동 ?패: {oauth_err}")
            st.query_params.clear()


# -----------------------------------------------------------------------------
# [?규] ?적 ?우??- ?답???문 참여 SPA (Single Page Application)
# -----------------------------------------------------------------------------


if "preview_id" in q_params or "survey_id" in q_params:
    is_preview_mode = "preview_id" in q_params
    
    from survey_manager import load_survey_metadata, save_response_to_sheet, generate_pairwise_combinations, calculate_matrix_cr
    
    if is_preview_mode:
        preview_id_param = q_params["preview_id"]
        if isinstance(preview_id_param, list):
            preview_id_param = preview_id_param[0]
            
        st.info("?️ [미리보기 모드] ???면? ?답?? 보게 ???면???시?미리보기?니?? ?력???이?는 ?출?? ?습?다.")
        
        preview_file_path = f"temp_previews/{preview_id_param}.json"
        if os.path.exists(preview_file_path):
            with open(preview_file_path, "r", encoding="utf-8") as f:
                survey_meta = json.load(f)
        else:
            st.warning(_("미리보기 ?이?? 불러?????습?다.", "Failed to load preview data."))
            st.markdown(_("""
#### ? 미리보기 ?에 ?래 ?항??먼? ?료??주세??

1. **?문지 ?정 ?료** ??메인 ?이지?서 AHP 모델 구조, ?인, 척도 ???문 ?정??모두 ?력?니??
2. **구? ?프?드?트 ?동** ???션 5?서 본인??구? ?프?드?트 URL ?는 ID??력?고, ?비??계정 ?메?을 ?집?로 공유?니??
3. **미리보기 버튼 ?릭** ???정???료????"???문지 ?답 ?면 미리보기" 버튼???시 ?러 주세??

> ? ?문 ?정 ?이지?서 ?용???력????미리보기??러???상?으??시?니??
            """, """
#### ? Please complete the following steps before previewing.

1. **Complete Survey Settings** ??Enter all survey settings, including AHP model structure, factors, and scales on the main page.
2. **Google Spreadsheet Integration** ??In Section 5, enter your Google Spreadsheet URL or ID and share it with the service account email as an editor.
3. **Click Preview Button** ??After the setup is complete, click the "??Preview Survey Screen" button again.

> ? The preview will display correctly only after entering content on the survey settings page.
            """))
            st.stop()
            
        survey_id_param = f"preview_{preview_id_param}"
    else:
        survey_id_param = q_params["survey_id"]
        if isinstance(survey_id_param, list):
            survey_id_param = survey_id_param[0]

    submitted_key = f"survey_submitted_{survey_id_param}"
    if st.session_state.get(submitted_key):
        # 1. HTML/CSS??용??모던?고 ?려??감사 카드 UI ?더?
        thank_you_title = _("?문 ?출???공?으??료?었?니??", "Survey Submitted Successfully!")
        thank_you_body = _(
            "?사결정 ?선?위 분석???해 ?중???간 ?어 ?답??주셔????히 감사?니?? <br>보내주신 ??? ?전?게 기록?었?며 ?구 분석??귀중한 ?료??용?니??",
            "Thank you very much for taking your valuable time to respond for decision-making priority analysis. <br>Your responses have been safely recorded and will be used as valuable data for research analysis."
        )
        thank_you_note = _(
            "??브라?? 보안 규정???라 '??기' 버튼???작?? ?을 ???습?다. <br>?작?? ?을 경우 ?재 ?려?는 <strong>브라?? ?? X 버튼</strong>??직접 ?러 종료??주세??",
            "??Depending on browser security policies, the 'Close Window' button may not work. <br>If it does not work, please close the current <strong>browser tab</strong> manually."
        )
        st.markdown(f"""
        <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 60px 20px; text-align: center; font-family: 'Inter', sans-serif; background-color: #ffffff; border-radius: 12px; box-shadow: 0 4px 24px rgba(0,0,0,0.06); margin-top: 40px; border: 1px solid #e2e8f0;">
            <div style="background-color: #ecfdf5; border: 1px solid #a7f3d0; border-radius: 50%; width: 90px; height: 90px; display: flex; align-items: center; justify-content: center; margin-bottom: 24px; box-shadow: 0 4px 10px rgba(16, 185, 129, 0.1);">
                <span style="font-size: 45px; color: #10b981;">?</span>
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
        
        import streamlit.components.v1 as components
        
        # 1.5. 모바??가?모드 ?체?면 ?동 ?제 ?방향 ?금 ?제 ?크립트 주입
        components.html("""
        <script>
        try {
            const parent = window.parent.document;
            if (parent.fullscreenElement || parent.webkitFullscreenElement) {
                if (parent.exitFullscreen) {
                    parent.exitFullscreen().catch(e => console.log(e));
                } else if (parent.webkitExitFullscreen) {
                    parent.webkitExitFullscreen();
                }
            }
            
            // ?면 방향 ?금 ?제 (?로 모드?복원 가?하?
            if (window.screen.orientation && window.screen.orientation.unlock) {
                window.screen.orientation.unlock();
            } else if (parent.screen.orientation && parent.screen.orientation.unlock) {
                parent.screen.orientation.unlock();
            }
        } catch(e) {
            console.log("Error exiting fullscreen:", e);
        }
        </script>
        """, height=0)
        
        # 2. ??기 버튼 ?더???바?크립트 ?행 ?리?
        close_clicked = st.button(_("? ??기", "? Close Window"), use_container_width=True)
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
            
    st.info(_("?️ ?이지??로고침?거???탈 ???력???보가 모두 초기?되??주의 바랍?다.", "?️ Please note that all entered information will be initialized if you refresh or leave the page."))
    
    # 미리보기 모드가 ?닌 경우?만 구? ?트?서 메??이?? 로드
    if not is_preview_mode:
        survey_meta = load_survey_metadata(survey_id_param)
        if not survey_meta:
            st.error(_("?문지?불러?????습?다. ?바?링크?? ?인??주세??", "Failed to load the survey. Please check if the link is correct."))
            st.stop()
        
        # ?션 ?태 기반 1?성 방문 카운??증? 처리 (?로고침 방????션변???용)
        if f"visited_survey_{survey_id_param}" not in st.session_state:
            from survey_manager import increment_survey_visit
            increment_survey_visit(survey_id_param)
            st.session_state[f"visited_survey_{survey_id_param}"] = True
            
    # [YETA ?용 ?우?? ?? 모드??경우 ?? ?용 ?더???출
    if survey_meta.get("Is_Yeta") == "True" or survey_meta.get("Is_Yeta") is True:
        import yeta_survey_renderer
        yeta_survey_renderer.render_yeta_survey(survey_meta, is_preview_mode=is_preview_mode, survey_id_param=survey_id_param)
        st.stop()
        
    survey_title = survey_meta.get('Title', 'AHP ?라???문조사')
    if survey_title in ['AHP ?라???문조사', '?조???동로봇 ?입 ?인 중요??분석???한 ?문가 AHP ?문']:
        survey_title = _(survey_title, 'Expert AHP Survey on the Importance of Factors for Adopting Manufacturing Collaborative Robots')
    else:
        survey_title = _t(survey_title)
        
    # --- Survey Language Switcher ---
    lang_col1, lang_col2 = st.columns([8, 2])
    with lang_col1:
        st.title(survey_title)
    with lang_col2:
        st.write("") # Add some vertical padding
        lang_options = {"?국??(Korean)": "ko", "English (?어)": "en"}
        current_survey_lang = "en" if st.session_state.get('lang', 'ko') == 'en' else "ko"
        selected_lang_label = st.selectbox(
            "Language / ?어", 
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
    
    # 조사 목적 ??내? ?문 ?당???메???시 (깔끔???자???용)
    survey_desc = survey_meta.get("Description", "")
    survey_desc = translate_definition_if_default("Description", survey_desc)
    
    # ?스???의 ?정 ?어 볼드(**?어**) ?밑줄(__?어__) 처리 지??
    import re
    survey_desc = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', survey_desc)
    survey_desc = re.sub(r'__(.*?)__', r'<u>\1</u>', survey_desc)
    
    survey_email = survey_meta.get("Admin_Email", "temp@ahpmaster.com")
    if not survey_email or str(survey_email).strip() == "":
        survey_email = "temp@ahpmaster.com"
    
    if survey_desc or survey_email:
        email_html = (
            f"<div style='margin-top: 16px; padding-top: 16px; border-top: 1px solid #e2e8f0; font-weight: bold;'>"
            f"? " + _("?문 ?당??문의:", "Contact Survey Administrator:") + " "
            f"<a href='mailto:{survey_email}' style='color: #2563eb; text-decoration: none;'>{survey_email}</a>"
            f"</div>"
        ) if survey_email else ""
        
        mobile_hint_html = (
            f"<div style='margin-top: 16px; padding: 12px; background-color: #f1f5f9; border-radius: 6px; font-size: 0.9rem; color: #334155; display: flex; gap: 8px; align-items: center;'>"
            f"<span style='font-size: 1.2rem;'>?</span> <span>" + _("?마?폰?로 ?속?신 경우, <b>기기?가로로 ?전</b>?시??욱 ?리?게 ?문???답?실 ???습?다.", "If you are using a smartphone, you can respond to the survey more conveniently by <b>rotating the screen horizontally</b>.") + "</span>"
            f"</div>"
        )
        
        # ?용???력 ?이?웃(줄바???어?기)??그?????기 ?해 white-space: pre-wrap ?용
        box_html = f'<div style="border: 1px solid #cbd5e1; border-radius: 8px; padding: 24px; background-color: #ffffff; color: #1e293b; font-size: 0.95rem; line-height: 1.6; margin-bottom: 24px; white-space: pre-wrap;">{survey_desc}\n{email_html}\n{mobile_hint_html}</div>'
        st.markdown(box_html, unsafe_allow_html=True)

    
    # 모델 ?보? ?구?계 추출
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
    
    # AHP ??비교 기본 ?택값을 1(?등)??정?기 ?해 session_state ?전 초기??(버전 v3 ?용?로 ?션 캐시 갱신)
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
    
    # ?일 ?크????성
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

    # 1. ?답??기본 ?보
    st.subheader(f"{section_num}. " + _("?답??기본 ?보", "Respondent Demographic Information"))
    section_num += 1
    resp_data = {}
    
    # ?이?는 ?답?에??시?? 말고 ?의?무작???동 부??
    if "survey_resp_uuid" not in st.session_state:
        import uuid
        st.session_state.survey_resp_uuid = str(uuid.uuid4())[:8]
    resp_data["id"] = st.session_state.survey_resp_uuid
    
    sq_idx = 1
    
    # ?명
    if demographics.get("name"):
        name_label = f"SQ{sq_idx}. " + _("?명 *", "Name *")
        sq_idx += 1
        col1, col2 = st.columns([1, 3])
        with col1:
            resp_data["name"] = st.text_input(name_label, key="survey_resp_name")
        st.caption(_("? ?집???명? 중복 ?답 검???도로만 ?용?니?? ?명 ?체 ?력???치 ?으??경우, ?름??????력?셔??무방?니?? (?? ???? ?길@ ??", "? The collected name is used only for duplicate response checking. If you do not wish to provide your full name, you may enter a partial name. (e.g., J@hn, Joh@ Doe)"))
    
    # 그룹 분류???계?? ?정??문항?보기??용
    type_questions_data = demographics.get("type_questions")
    resp_data["types"] = []
    
    if type_questions_data and isinstance(type_questions_data, list):
        for i, tq in enumerate(type_questions_data):
            tq_q = tq.get("q", tq.get("question", ""))
            tq_opts = tq.get("opts", [])
            if not tq_q or tq_q == "귀?의 ?속? ?떻??십?까?":
                tq_q = _("귀?의 ?속? ?떻??십?까?", "What is your affiliation?")
            else:
                tq_q = _t(tq_q)
            
            if not isinstance(tq_opts, list) or not tq_opts or tq_opts == ["?문가", "?반", "공무??, "기?"]:
                if "opts" not in tq: # it was added via UI as short answer text
                    tq_opts = []
                else:
                    tq_opts = [_("?문가", "Expert"), _("?반", "General"), _("공무??, "Public Official"), _("기?", "Other")]
            
            if tq_opts:
                tq_opts = [translate_factor_if_default(opt) for opt in tq_opts]
                ans = st.radio(f"SQ{sq_idx}. {tq_q}", tq_opts, index=0, key=f"survey_resp_type_{i}", horizontal=True)
            else:
                ans = st.text_input(f"SQ{sq_idx}. {tq_q}", key=f"survey_resp_type_{i}")
            resp_data["types"].append(ans)
            sq_idx += 1
    else:
        # ?????환??
        type_q = demographics.get("type_question", "")
        if not type_q or type_q == "귀?의 ?속? ?떻??십?까?":
            type_q = _("귀?의 ?속? ?떻??십?까?", "What is your affiliation?")
        else:
            type_q = _t(type_q)
        
        type_opts = demographics.get("type_options", [])
        if not isinstance(type_opts, list) or not type_opts or type_opts == ["?문가", "?반", "공무??, "기?"]:
            type_opts = [_("?문가", "Expert"), _("?반", "General"), _("공무??, "Public Official"), _("기?", "Other")]
        else:
            type_opts = [translate_factor_if_default(opt) for opt in type_opts]
            
        ans = st.radio(f"SQ{sq_idx}. {type_q}", type_opts, index=0, key="survey_resp_type", horizontal=True)
        resp_data["types"].append(ans)
        sq_idx += 1
        
    # 기존 코드????환?을 ?해 type ?성????
    if resp_data["types"]:
        resp_data["type"] = resp_data["types"][0]
    

    
    # ?령: 개방??vs 10???위 ?택??
    if demographics.get("age"):
        age_label = f"SQ{sq_idx}. " + _("?령 *", "Age *")
        sq_idx += 1
        age_type = demographics.get("age_type", "개방??(?자 직접 ?력)")
        if age_type == "10???위 ?택??:
            age_options = [_("20? 미만", "Under 20s"), _("20? (20~29??", "20s (20-29)"), _("30? (30~39??", "30s (30-39)"), _("40? (40~49??", "40s (40-49)"), _("50? (50~59??", "50s (50-59)"), _("60? ?상", "60s or older")]
            resp_data["age"] = st.radio(age_label, age_options, index=0, key="survey_resp_age", horizontal=True)
        else:
            col1, col2 = st.columns([1, 3])
            with col1:
                resp_data["age"] = st.text_input(f"{age_label} " + _("(??", "(Years)"), value="", placeholder=_("?? 30", "e.g. 30"), key="survey_resp_age_text")
            
    if demographics.get("gender"):
        resp_data["gender"] = st.radio(f"SQ{sq_idx}. " + _("?별 *", "Gender *"), [_("?자", "Male"), _("?자", "Female")], key="survey_resp_gender", horizontal=True)
        sq_idx += 1
    
    # 경력?수: 개방??vs 5???위 ?택??
    if demographics.get("experience"):
        exp_label = f"SQ{sq_idx}. " + _("경력?수 *", "Years of Experience *")
        sq_idx += 1
        exp_type = demographics.get("experience_type", "개방??(?자 직접 ?력)")
        if exp_type == "5???위 ?택??:
            exp_options = [_("5??미만", "Less than 5 years"), _("5???상 ~ 10??미만", "5 to 10 years"), _("10???상 ~ 15??미만", "10 to 15 years"), _("15???상 ~ 20??미만", "15 to 20 years"), _("20???상", "20 years or more")]
            resp_data["experience"] = st.radio(exp_label, exp_options, index=0, key="survey_resp_experience", horizontal=True)
        else:
            col1, col2 = st.columns([1, 3])
            with col1:
                resp_data["experience"] = st.text_input(f"{exp_label} " + _("(??", "(Years)"), value="", placeholder=_("?? 5", "e.g. 5"), key="survey_resp_experience_text")
            
    # ?속 문항 ????
    # if demographics.get("affiliation"):
    #     resp_data["affiliation"] = st.text_input(f"SQ{sq_idx}. " + _("?속 *", "Affiliation *"), key="survey_resp_affiliation")
    #     sq_idx += 1
        
    if demographics.get("email"):
        col1, col2 = st.columns([1, 3])
        with col1:
            resp_data["email"] = st.text_input(f"SQ{sq_idx}. " + _("?메??*", "Email *"), key="survey_resp_email", value="", placeholder=_("?? user@example.com", "e.g. user@example.com"))
        sq_idx += 1
    
    st.divider()
    
    main_criteria = ahp_model.get("main", [])
    
    with st.container():
        # 4. AHP ??비교 문항 ?성
        st.subheader(f"{section_num}. " + _("?인 ?????중요???? (??비교)", "Evaluation of Relative Importance between Factors (Pairwise Comparison)"))
        ahp_section_prefix = f"{section_num}"
        section_num += 1
        
        st.info(_("??중요??방향?로 ?자??택?세?? **1**=?등, ?자가 ?수??당 방향???인????중요?니??",
                  "Select the number toward the more important factor. **1**=Equal, larger number = more important."))
        if cr_guide_method == "realtime":
            st.markdown(_(":blue[**????배경**]: ????CR)??최적?로 ???는 :red[**권장 ?택 구간**]?니??",
                          ":blue[**Blue background**]: :red[**recommended range**] to maintain optimal consistency (CR)."))
        with st.expander(_("?세 ?답 가?드", "Detailed Response Guide"), expanded=False):
            st.markdown(_("""
- **?등(1)**: ?쪽 ?인???같??중요????가?데 **1**???택?세??
- **?쪽 ?인????중요????*: ?쪽 방향(??)???자??택?세?? ?자가 ?수??쪽 ?인???씬 중요?을 ???니??
- **?른??인????중요????*: ?른?방향( ?????자??택?세?? ?자가 ?수??른??인???씬 중요?을 ???니??
            """, """
- **Equal (1)**: Choose the middle **1** when both factors are equally important.
- **Left factor more important**: Choose a number on the left (??. Larger = much more important.
- **Right factor more important**: Choose a number on the right (??. Larger = much more important.
            """))
        
        # 모바??가?모드 강제 ?환 ?버?이
        import streamlit.components.v1 as components
        mobile_landscape_overlay_html = """
        <script>
        try {
            const parent = window.parent.document;
            if (!parent.getElementById('mobile-landscape-overlay')) {
                const overlay = parent.createElement('div');
                overlay.id = 'mobile-landscape-overlay';
                
                const style = parent.createElement('style');
                style.innerHTML = `
                    #mobile-landscape-overlay {
                        display: none;
                        position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
                        background-color: rgba(255,255,255,0.98);
                        z-index: 999999; flex-direction: column;
                        justify-content: center; align-items: center; text-align: center;
                        padding: 20px; box-sizing: border-box;
                    }
                    @media (orientation: portrait) and (max-width: 768px) {
                        #mobile-landscape-overlay { display: flex; }
                    }
                    .landscape-btn {
                        background-color: #ff4b4b; color: white; border: none; border-radius: 8px;
                        padding: 15px 25px; font-size: 18px; font-weight: bold; margin-top: 20px;
                        cursor: pointer; box-shadow: 0 4px 6px rgba(0,0,0,0.1); width: 100%; max-width: 320px;
                    }
                    .landscape-note {
                        font-size: 13.5px; color: #555; margin-top: 20px; line-height: 1.5; word-break: keep-all; background: #f8f9fa; padding: 15px; border-radius: 8px; max-width: 320px; text-align: left;
                    }
                `;
                parent.head.appendChild(style);

                overlay.innerHTML = `
                    <div style="font-size: 50px; margin-bottom: 15px;">??</div>
                    <h2 style="color: #333; margin-bottom: 10px; font-size: 22px;">가?모드 최적??/h2>
                    <p style="color: #444; font-size: 15px; margin-bottom: 5px;">???문(AHP ??비교)? 가??면?서<br>가???하??답?실 ???습?다.</p>
                    <button class="landscape-btn" id="btn-force-landscape">? ?면??가로로 ?리??문 계속?기</button>
                    <div class="landscape-note">
                        ??<b>?이??iOS) ?용???내</b><br>
                        ??버튼???동?? ?을 ???습?다.<br>
                        기기??<b>'?동 ?전'??켜고</b> ?마?폰????주시??내창이 ?라집니??
                    </div>
                `;
                parent.body.appendChild(overlay);

                parent.getElementById('btn-force-landscape').addEventListener('click', function() {
                    const docElm = parent.documentElement;
                    if (docElm.requestFullscreen) {
                        docElm.requestFullscreen().then(() => {
                            if (window.screen.orientation && window.screen.orientation.lock) {
                                window.screen.orientation.lock('landscape').catch(e => console.log(e));
                            } else if (parent.screen.orientation && parent.screen.orientation.lock) {
                                parent.screen.orientation.lock('landscape').catch(e => console.log(e));
                            }
                        }).catch(e => console.log(e));
                    } else if (docElm.webkitRequestFullscreen) {
                        docElm.webkitRequestFullscreen();
                        if (parent.screen.orientation && parent.screen.orientation.lock) {
                            parent.screen.orientation.lock('landscape').catch(e => console.log(e));
                        }
                    }
                });
            }
        } catch(e) {
            console.log("Error injecting overlay:", e);
        }
        </script>
        """
        components.html(mobile_landscape_overlay_html, height=0)
        
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
                    _((f"[{parent_trans}] ?위 ?인 비교"), f"Sub-criteria Comparison under [{parent_trans}]")
                    if comb['type'] == 'sub'
                    else _("?분류(?심) ?인 비교", "Main Criteria (Core) Comparison")
                )
                st.markdown(f"#### {parent_lbl}")
                
                # [?정] ?? ?인 ?의 ??명???척도 ?? 바로 ?쪽?로 ?동
                if comb['type'] == 'sub':
                    # ?당 ?분류(parent) 카드 출력
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
                            <h5 style="margin: 0 0 12px 0; color: #1e293b; font-size: 1.0rem; font-weight: bold;">{_("?분류 ?인 ?의", "Main Criteria Definitions")}</h5>
                            <div style="display: flex; flex-direction: column; gap: 2px; background-color: #ffffff; padding: 12px; border-radius: 6px; border: 1px solid #e2e8f0;">
                                {main_rows_html}
                            </div>
                        </div>
                        """
                        st.markdown(card_html.replace("\n", " "), unsafe_allow_html=True)
                
                comp_idx += 1
            
                # 척도 ?터?이???정???른 ?택 ?디??버튼 ?션 매핑
                if "1-3-5 Discrete" in scale_type:
                    options = [-5, -3, 1, 3, 5]
                    format_func = lambda x: _("?쪽 ?인???씬 중요 (-5)", "Left factor is much more important (-5)") if x == -5 else (_("?쪽 ?인???간 중요 (-3)", "Left factor is slightly more important (-3)") if x == -3 else (_("?측???등??(1)", "Equal importance (1)") if x == 1 else (_("?른??인???간 중요 (3)", "Right factor is slightly more important (3)") if x == 3 else _("?른??인???씬 중요 (5)", "Right factor is much more important (5)"))))
                elif "1-5 Continuous" in scale_type or ("1-5" in scale_type and "Discrete" not in scale_type):
                    options = [-5, -4, -3, -2, 1, 2, 3, 4, 5]
                    format_func = lambda x: _(f"?쪽 중요??{abs(x)}", f"Left importance {abs(x)}") if x < 0 else (_("?등 (1)", "Equal (1)") if x == 1 else _(f"?른?중요??{x}", f"Right importance {x}"))
                elif "1-3-7-9 Discrete" in scale_type:
                    options = [-9, -7, -3, 1, 3, 7, 9]
                    format_func = lambda x: _("?쪽 ????중요 (-9)", "Left is absolutely more important (-9)") if x == -9 else (_("?쪽 ??히 중요 (-7)", "Left is strongly more important (-7)") if x == -7 else (_("?쪽 ?간 중요 (-3)", "Left is slightly more important (-3)") if x == -3 else (_("?등??(1)", "Equal (1)") if x == 1 else (_("?른??간 중요 (3)", "Right is slightly more important (3)") if x == 3 else (_("?른???히 중요 (7)", "Right is strongly more important (7)") if x == 7 else _("?른?????중요 (9)", "Right is absolutely more important (9)"))))))
                else: # 1-9 Continuous (Default)
                    options = list(range(-9, -1)) + list(range(1, 10))
                    options = sorted(list(set(options))) # -9 ~ -2, 1, 2 ~ 9
                    format_func = lambda x: _(f"?쪽 중요??{abs(x)}", f"Left importance {abs(x)}") if x < 0 else (_("?등 (1)", "Equal (1)") if x == 1 else _(f"?른?중요??{x}", f"Right importance {x}"))
                
                # 모바??최적?? 가??크??역 지?을 ?한 컨테?너 ?성
                survey_container = st.container()
                survey_container.markdown("<div class='ahp_scrollable_area'></div>", unsafe_allow_html=True)
                
                # CSS 주입: 컬럼 간의 gap??0?로 차단?고 모바??가??크?지??
                mobile_css = """
                <style>
                /* 모바??(768px ?하) ?경?서 가??크??용 ??로 ?임 방? */
                @media (max-width: 768px) {
                    /* 직계 ?식?로 마커?가?stVerticalBlock ??택?여 부?컨테?너 ?이?웃 ?괴 방? */
                    div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .ahp_scrollable_area) {
                        overflow-x: auto !important;
                        padding-bottom: 15px;
                    }
                    div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .ahp_scrollable_area) > div {
                        min-width: 700px !important;
                    }
                    div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .ahp_scrollable_area) div[data-testid="stHorizontalBlock"] {
                        flex-wrap: nowrap !important;
                        flex-direction: row !important;
                    }
                    div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .ahp_scrollable_area) div[data-testid="stHorizontalBlock"] > div:nth-child(1) {
                        width: 15% !important; min-width: 15% !important; flex: 1 1 15% !important;
                    }
                    div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .ahp_scrollable_area) div[data-testid="stHorizontalBlock"] > div:nth-child(2) {
                        width: 70% !important; min-width: 70% !important; flex: 1 1 70% !important;
                    }
                    div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .ahp_scrollable_area) div[data-testid="stHorizontalBlock"] > div:nth-child(3) {
                        width: 15% !important; min-width: 15% !important; flex: 1 1 15% !important;
                    }
                }
                </style>
                """
                survey_container.markdown(mobile_css, unsafe_allow_html=True)
                
                # PDF ?문지? ?사???더 ???????성
                # 척도 ?션??맞추?????단???시???더 ?척도 ?구성
                if "1-3-5 Discrete" in scale_type:
                    left_cols = ["5", "3"]
                    right_cols = ["3", "5"]
                    options = [-5, -3, 1, 3, 5]
                    col_headers = ["5", "3", "1", "3", "5"]
                elif "1-5 Continuous" in scale_type or ("1-5" in scale_type and "Discrete" not in scale_type):
                    left_cols = ["5", "4", "3", "2"]
                    right_cols = ["2", "3", "4", "5"]
                    options = [-5, -4, -3, -2, 1, 2, 3, 4, 5]
                    col_headers = ["5", "4", "3", "2", "1", "2", "3", "4", "5"]
                elif "1-3-7-9 Discrete" in scale_type:
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
            
                # 척도 ?에 맞추??비율 ?적 계산 (left_cols + ?일(1) + right_cols)
                header_cells = left_cols + ["1"] + right_cols
                total_scale_count = len(header_cells)
                scale_width = 70.0 / total_scale_count
                left_width = scale_width * len(left_cols)
                right_width = scale_width * len(right_cols)

                # CSS 주입: 컬럼 간의 gap??0?로 차단?고 ?디??그룹??100% 분배
            

                # HTML ???더 구조
                # fixed table layout?서 colspan ?용 ???컬럼 ?비??일 배분?도?colgroup ?의
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
                        <th style="border: 1px solid #334155; padding: 6px; font-size: 12px;" rowspan="2">{_("비교 ?인", "Comparison Criteria")}</th>
                        <th style="border: 1px solid #334155; padding: 4px; color: #93c5fd; font-size: 12px;" colspan="{len(left_cols)}">{_("??좌측 ?인 중요??, "??Left Criteria Importance")}</th>
                        <th style="border: 1px solid #334155; padding: 4px; background-color: #3b82f6; color: #ffffff; font-size: 12px;" rowspan="2">{_("?등<br>(1)", "Equal<br>(1)")}</th>
                        <th style="border: 1px solid #334155; padding: 4px; color: #93c5fd; font-size: 12px;" colspan="{len(right_cols)}">{_("?측 ?인 중요????, "Right Criteria Importance ??)}</th>
                        <th style="border: 1px solid #334155; padding: 6px; font-size: 12px;" rowspan="2">{_("비교 ?인", "Comparison Criteria")}</th>
                    </tr>
                    <tr style="background-color: #334155; color: #cbd5e1; font-weight: bold; border-bottom: 1px solid #cbd5e1;">
                        {"".join([f"<td style='border: 1px solid #475569; padding: 4px 0; font-size: 12px;'>{val}</td>" for val in left_cols])}
                        {"".join([f"<td style='border: 1px solid #475569; padding: 4px 0; font-size: 12px;'>{val}</td>" for val in right_cols])}
                    </tr>
                </table>
                """
                survey_container.markdown(header_html, unsafe_allow_html=True)

                # 3??컬럼 배치: [?쪽 ?인?컬럼 (15%)] - [척도 ?디??버튼 ?역 컬럼 (70%)] - [?른??인?컬럼 (15%)]
                for left_f, right_f in comb["pairs"]:
                    pair_key = f"{left_f}_{right_f}"
                    clean_id = pair_key.replace(" ", "_")
                    survey_container.markdown(f"<div id='anchor_{clean_id}'></div>", unsafe_allow_html=True)
                
                    row_cols = survey_container.columns([15, 70, 15])
                
                    # ?쪽 ?인?출력
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
                
                    # ?디??버튼?을 가로로 ?전 ?렬?여 1?로 배치
                    with row_cols[1]:
                        # ?전???해 options?서 중복 ?-1 ?명시???외
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
                                
                                # 비교 ?인??2?초과?고, 그룹 ?의 ?른 문항?이 모두 ?답??경우?만 권장 범위??출?니??
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
                            # Streamlit st.radio ?벨 중복(?? ?상) 방???해 ?수 쪽에 보이지 ?는 공백(Zero-width space) 추?
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
                
                    # ?른??인?출력
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
            st.subheader(_("?답???명 ?인", "Respondent Name Verification"))
            col1, col2 = st.columns([1, 3])
            with col1:
                name_verify = st.text_input(_("?명 *", "Name *"), key="survey_resp_name_verify", value="", placeholder=_("?? ?길??(?는 ????", "e.g. John Doe (or J. Doe)"))
                if name_verify:
                    resp_data["name"] = name_verify
                st.caption(_("중복 ?답 ?인???해 ?력???청?립?다. ?체 ?름 공개가 불편?신 경우 ?씨 ?는 ?씨? ?름 ?자??력?셔???니??", "Requested to check for duplicate responses. If uncomfortable disclosing your full name, you may enter just your last name or initials."))
            st.divider()

        # 5. 개인?보 ?집 ??????적 ?출 ?문구 ?정
        has_demographics = any(demographics.values()) if demographics else False
        has_rewards = rewards_info.get("enabled", False) if rewards_info else False
        
        agree_check = _("?의", "Agree")
        if has_demographics or has_rewards:
            if has_rewards:
                subheader_text = f"{section_num}. " + _("개인?보 ?집 ?????, "Personal Information Collection & Reward")
                radio_label = _("개인?보 ?집 ?????지급을 ?한 ?용 ?의???의?십?까? *", "Do you agree to the collection of personal information and use for reward distribution? *")
            else:
                subheader_text = f"{section_num}. " + _("개인?보 ?집 ?의", "Consent to Personal Information Collection")
                radio_label = _("개인?보 ?집 ??용???의?십?까? *", "Do you agree to the collection and use of personal information? *")
                
            st.subheader(subheader_text)
            section_num += 1
            
            if has_rewards:
                st.info(f"**" + _("?????내", "Reward Info") + f"**: {rewards_info.get('desc', _('?문 ?료 ?????을 ?공?니??', 'A reward will be provided upon survey completion.'))}")
                reward_contact = st.text_input(_("????지급용 ?락?????번호 ?는 ?메?? *", "Contact for Reward (Mobile number or Email) *"), key="survey_reward_contact")
                resp_data["reward_contact"] = reward_contact
                
            agree_check = st.radio(radio_label, [_("?의", "Agree"), _("비동??, "Disagree")], index=1, key="survey_agree_check")
        
        # 마법???태 ?인
        wizard_state_key = f"cr_wizard_state_{survey_id_param}"
        wizard_state = st.session_state.get(wizard_state_key, {"active": False})
        
        if wizard_state.get("active"):
            st.warning(_("?️ ????비율(CR) ??", "?️ Consistency Ratio (CR) Check"))
            st.error(_(f"분석 결과, **[{wizard_state['failed_group']}]** 문항?의 ?답 ???이 부족합?다. (?재 CR: {wizard_state['cr']:.3f} > 기?? {cr_limit})", f"Analysis shows inconsistent responses for **[{wizard_state['failed_group']}]**. (Current CR: {wizard_state['cr']:.3f} > Limit: {cr_limit})"))
            
            w_pair = wizard_state['worst_pair']
            cur_v = wizard_state['current_val']
            sug_v = wizard_state['suggested_val']
            
            def val_to_text(v, p1, p2):
                if v == 1: return _("?등??(1)", "Equal (1)")
                if v < 0: return f"{p1} 방향?로 {abs(v)}"
                return f"{p2} 방향?로 {v}"
                
            cur_txt = val_to_text(cur_v, w_pair[0], w_pair[1])
            sug_txt = val_to_text(sug_v, w_pair[0], w_pair[1])
            
            st.info(_(f"""
            ? **지?형 ?정 ?안**: 
            ?재 [{w_pair[0]}]? [{w_pair[1]}]??비교 ?답???른 ?답?과 ?학??모순??가???니??
            * ?재 ?택?신 ? **{cur_txt}**
            * ?리?????을 ?한 추천 ? **{sug_txt}**
            """, f"""
            ? **Smart Fix Suggestion**: 
            Your comparison between [{w_pair[0]}] and [{w_pair[1]}] has the highest mathematical contradiction with your other answers.
            * Your current selection: **{cur_txt}**
            * Suggested value for logical consistency: **{sug_txt}**
            """))
            
            if st.button(_("?시 검??, "Review again"), use_container_width=True):
                st.session_state[wizard_state_key]["active"] = False
                target_key = f"{w_pair[0]}_{w_pair[1]}"
                st.session_state["scroll_target"] = target_key
                st.session_state["highlight_target"] = target_key
                st.rerun()
                    
            submit_btn = False # 마법???시 중에???반 ?출 ?함
        else:
            # ?출 버튼
            submit_btn = st.button(_("?문지 ?출?기", "Submit Survey"), type="primary")
        if submit_btn:
            # ?수??효??검?
            missing = False
            
            # AHP ?답 ?락 검?
            missing_ahp = [k for k, v in ahp_answers.items() if v is None]
            
            # ?구?계 ?수?
            if demographics.get("name") and not resp_data.get("name"): missing = True
            if demographics.get("age") and resp_data.get("age") is None: missing = True
            if demographics.get("experience") and resp_data.get("experience") is None: missing = True
            if demographics.get("email") and not resp_data.get("email"): missing = True
            if rewards_info.get("enabled") and not resp_data.get("reward_contact"): missing = True
            
            if agree_check not in ["?의", "Agree"]:
                st.error(_("?문?출???해 개인?보 ?집 ?의??체크??주세??", "Please agree to the personal information collection to submit the survey."))
                st.stop()
                
            if missing_ahp:
                st.error(_("???? ?? AHP ??비교 문항???습?다. 모든 문항???답??주십?오.", "There are unanswered AHP pairwise comparison questions. Please answer all questions."))
                st.stop()

            if missing:
                st.error(_("?력?? ?? ?수 문항(*)???습?다. ?을 ?시 ????인??주세??", "There are missing required fields (*). Please check the form again."))
                st.stop()
                
            # CR 계산 ?마법??로직
            if cr_limit is not None:
                cr_failed = False
                failed_factors = []
                failed_group_name = ""
                failed_cr = 0.0
                
                # ?분류 CR 체크
                main_cr = calculate_matrix_cr(main_criteria, ahp_answers)
                if main_cr > cr_limit:
                    cr_failed = True
                    failed_factors = main_criteria
                    failed_group_name = _("?분류", "Main Criteria")
                    failed_cr = main_cr
                
                # ?위분류 CR 체크
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
                    
                    # 마법?? ?거??마법???안??계산?????는 경우 (기존 로직)
                    if not is_preview_mode:
                        from survey_manager import increment_abandoned_cr
                        increment_abandoned_cr(survey_id_param)
                    st.error(_(f"[{failed_group_name}] ?????답 ???이 부족합?다. (????비율: {failed_cr:.3f} > ?정 ?계? {cr_limit}) ?? 문항???시 검?해 주십?오.", f"The consistency of your responses for [{failed_group_name}] is insufficient. (CR: {failed_cr:.3f} > threshold: {cr_limit}) Please review some questions again."))
                    st.stop()
            
            # ???진행
            with st.spinner(_("?답???전?게 ?송 중입?다...", "Submitting your response safely...")):
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
                        st.error(_("?이???????버 ?러가 발생?습?다. ?시 ???시 ?도??주세??", "A server error occurred while saving data. Please try again later."))
                    
    st.stop()

# ?동 로그???권한 갱신 처리 (쿼리 ?라미터 기반)
if "login_user" in q_params and "login_token" in q_params:
    login_user_val = q_params["login_user"]
    if isinstance(login_user_val, list): login_user_val = login_user_val[0]
    login_token_val = q_params["login_token"]
    if isinstance(login_token_val, list): login_token_val = login_token_val[0]
    
    # ?큰 검?
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
            try:
                import survey_manager
                survey_manager.log_user_action(login_user_val, "로그??(URL ?라미터)")
            except:
                pass
            
            # URL ?라미터??리?여 불필?한 반복 쿼리 ??출 방?
            if "login_user" in st.query_params:
                try:
                    del st.query_params["login_user"]
                except Exception:
                    pass
            if "login_token" in st.query_params:
                try:
                    del st.query_params["login_token"]
                except Exception:
                    pass
            
            if role_changed:
                st.toast("? Account status updated!")
                st.rerun()


# ?동 로그?웃 처리 (30?미활????
import time
TIMEOUT_LIMIT = 1800 # 30?(??위)
current_time = int(time.time())

if st.session_state.get('user_id') is not None:
    last_act = q_params.get("last_activity")
    if isinstance(last_act, list): last_act = last_act[0]
    
    if last_act:
        try:
            elapsed = current_time - int(last_act)
            if elapsed > TIMEOUT_LIMIT:
                # ?션 ?쿼리 ?라미터 초기??
                st.session_state.user_id = None
                st.session_state.user_role = None
                st.session_state.expiry_date = None
                st.session_state.admin_mode = False
                st.query_params.clear()
                st.toast(_(" 30분간 ?동???어 보안???해 ?동 로그?웃?었?니??", " Logged out automatically due to 30 minutes of inactivity."))
                st.rerun()
            else:
                st.query_params["last_activity"] = str(current_time)
        except ValueError:
            st.query_params["last_activity"] = str(current_time)
    else:
        st.query_params["last_activity"] = str(current_time)

# ?국??처리
if "lang" in q_params:
    lang_val = q_params["lang"]
    if isinstance(lang_val, list): lang_val = lang_val[0]
    if str(lang_val).lower() in ["en", "english"]:
        st.session_state.lang = "en"
    elif str(lang_val).lower() in ["ko", "korean"]:
        st.session_state.lang = "ko"

# PortOne ?동 결제 ?격 처리
if "portone_paid" in q_params and "user_id" in q_params:
    user_id_param = q_params.get("user_id", [""])[0] if isinstance(q_params.get("user_id"), list) else q_params.get("user_id", "")
    months_param = int(q_params.get("months", ["2"])[0] if isinstance(q_params.get("months"), list) else q_params.get("months", 2))
    plan_name_param = q_params.get("plan_name", ["?식 ?용??])[0] if isinstance(q_params.get("plan_name"), list) else q_params.get("plan_name", "?식 ?용??)
    
    # ?벤??관???라미터 ?싱 (추?)
    event_applied_param = q_params.get("event_applied", ["N"])[0] if isinstance(q_params.get("event_applied"), list) else q_params.get("event_applied", "N")
    university_param = q_params.get("university", [""])[0] if isinstance(q_params.get("university"), list) else q_params.get("university", "")
    thesis_title_param = q_params.get("thesis_title", [""])[0] if isinstance(q_params.get("thesis_title"), list) else q_params.get("thesis_title", "")
    
    if user_id_param:
        kst_now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
        
        # 기존 ?용???보 조회
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
            
        # update_user_full_info ?자???벤???이??추? ?달
        update_user_full_info(
            user_id_param, None, target_role, new_expiry_date, 
            plan_type=plan_name_param, 
            event_applied=event_applied_param, 
            thesis_title=thesis_title_param, 
            university=university_param
        )
        
        import hashlib
        login_token = hashlib.sha256(f"{user_id_param}:AHP_MASTER_SECURE_SALT_2026_!@#".encode()).hexdigest()
        html_code = f"""
        <!DOCTYPE html>
        <html>
        <head><meta charset="utf-8"></head>
        <body style="font-family: sans-serif; text-align: center; padding: 50px;">
          <h3 style="color: green;">? 결제가 ?료?어 ?식 ?용?로 ?급?었?니??</h3>
          <p>?래 버튼???릭?여 로그?을 진행??주세??</p>
          <button onclick="handleLogin()" style="padding: 12px 24px; background-color: #4CAF50; color: white; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; margin-top: 20px; font-weight: bold;">로그?하?/button>
          <script>
            // ?래 ?opener)???다?로그??처리 URL??동?킵?다.
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
                // ??브라?? ??우?(?동 로그??URL ?함)
                window.open(loginUrl, "_blank");
                // 결제?료??기
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

# ?이???동 결제 ?격 처리 (?버 검??함)
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
            plan_name_param = q_params.get("plan_name", ["?식 ?용??])[0] if isinstance(q_params.get("plan_name"), list) else q_params.get("plan_name", "?식 ?용??)
            
            kst_now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
            
            # 기존 ?용???보 조회
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
            st.toast("? PayPal Payment successful! Account upgraded/updated.")
    else:
        st.error(f"Payment verification failed: {msg}")
        
    st.query_params.clear()
    st.rerun()

# ?식 ?원 ?동 만료 체크 (로그???태)
if st.session_state.get('user_id') is not None and st.session_state.get('user_role') == 'official':
    today = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).date()
    try:
        expiry_date_val_temp = datetime.datetime.strptime(st.session_state.expiry_date, "%Y-%m-%d").date()
        if today > expiry_date_val_temp:
            update_user_full_info(st.session_state.user_id, None, "temp", "9999-12-31")
            st.session_state.user_role = "temp"
            st.session_state.expiry_date = "9999-12-31"
            st.toast("? Subscription expired. Automatically downgraded to Free User.")
            st.rerun()
    except Exception:
        pass

# =============================================================================
# 3. Sidebar (Auth & Settings) - ?? ?시?도??치 조정
# =============================================================================

def get_login_redirect_html(plan_name="?식 ?용??, inner_html="", is_best=False, lang="ko"):
    import datetime
    event_cfg = get_event_settings()
    is_cfg_active = event_cfg["active"]
    event_title = event_cfg["title"]
    event_desc = event_cfg["desc"]
    event_deadline_str = event_cfg["deadline"]
    
    kst_now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
    try:
        event_deadline = datetime.datetime.strptime(event_deadline_str, "%Y-%m-%d")
        event_deadline = event_deadline.replace(hour=23, minute=59, second=59, tzinfo=datetime.timezone(datetime.timedelta(hours=9)))
    except Exception:
        event_deadline = datetime.datetime(2026, 7, 30, 23, 59, 59, tzinfo=datetime.timezone(datetime.timedelta(hours=9)))
        
    is_event_active = is_cfg_active and kst_now <= event_deadline and (plan_name.startswith("Basic") or plan_name.startswith("Standard")) and lang == "ko"
    
    border_css = "border: 2px solid #ff4b4b;" if is_best else "border: 1px solid #ddd;"
    best_badge = "<div style='position: absolute; top: -12px; right: 15px; background-color: #ff4b4b; color: white; padding: 3px 12px; border-radius: 12px; font-size: 0.8rem; font-weight: bold;'>BEST</div>" if is_best else ""
    
    event_ui_html = ""
    if is_event_active:
        event_ui_html = f"""
        <div id="event-container" style="margin-top: auto; margin-bottom: 6px; padding: 6px 8px; background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%); border: 1px dashed #0284c7; border-radius: 6px; font-size: 0.72rem; text-align: left; line-height: 1.2; height: auto; overflow: hidden;">
            <div style="font-weight: bold; color: #0284c7; margin-bottom: 2px;">
                <b>{event_title}</b>
            </div>
            <div style="font-size: 0.65rem; color: #475569;">
                {event_desc}
            </div>
        </div>
        """
        
    btn_label = f"Pay {plan_name.split(' (')[0]}" if lang == "en" else f"결제 {plan_name.split(' (')[0]}"
    alert_msg = "Login or Sign-up is required. Please proceed in the main tab or sidebar." if lang == "en" else "로그???는 ?원가?이 ?요?니?? 메인 ?????이?바??해 로그??가?을 진행?주?요."
    
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
          <div style="height: 260px; box-sizing: border-box;">{inner_html}</div>
          {event_ui_html}
          <button class="btn" onclick="redirectSignup()">{btn_label}</button>
      </div>
      <script>
        function redirectSignup() {{
            const tabs = window.parent.document.querySelectorAll('button[data-baseweb="tab"]');
            for (let i = 0; i < tabs.length; i++) {{
                if (tabs[i].innerText.includes('?원가??) || tabs[i].innerText.includes('Sign Up')) {{
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

def get_portone_payment_html(user_id, plan_name="?식 ?용??, amount=500000, months=2, inner_html="", is_best=False):
    import hashlib
    import datetime
    login_token = hashlib.sha256(f"{user_id}:AHP_MASTER_SECURE_SALT_2026_!@#".encode()).hexdigest()
    is_logged_in_js = "true" if user_id and str(user_id).strip() else "false"
    if user_id and str(user_id).strip():
        u_str = str(user_id).strip()
        safe_email = u_str if "@" in u_str else f"{u_str}@ahp.kr"
        order_name = f"{plan_name} ({u_str})"
    else:
        safe_email = "customer@ahp.kr"
        order_name = f"{plan_name}"
    
    event_cfg = get_event_settings()
    is_cfg_active = event_cfg["active"]
    event_title = event_cfg["title"]
    event_desc = event_cfg["desc"]
    event_deadline_str = event_cfg["deadline"]
    event_discount = event_cfg["discount"]
    
    # ?벤???성???? 기한 검??
    kst_now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
    try:
        event_deadline = datetime.datetime.strptime(event_deadline_str, "%Y-%m-%d")
        event_deadline = event_deadline.replace(hour=23, minute=59, second=59, tzinfo=datetime.timezone(datetime.timedelta(hours=9)))
    except Exception:
        event_deadline = datetime.datetime(2026, 7, 30, 23, 59, 59, tzinfo=datetime.timezone(datetime.timedelta(hours=9)))
        
    is_event_active = is_cfg_active and kst_now <= event_deadline and (plan_name.startswith("Basic") or plan_name.startswith("Standard"))
    
    border_css = "border: 2px solid #ff4b4b;" if is_best else "border: 1px solid #ddd;"
    best_badge = "<div style='position: absolute; top: -12px; right: 15px; background-color: #ff4b4b; color: white; padding: 3px 12px; border-radius: 12px; font-size: 0.8rem; font-weight: bold;'>BEST</div>" if is_best else ""
    
    event_ui_html = ""
    if is_event_active:
        event_ui_html = f"""
        <div id="event-container" style="margin-top: auto; margin-bottom: 6px; padding: 6px 8px; background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%); border: 1px dashed #0284c7; border-radius: 6px; font-size: 0.72rem; text-align: left; line-height: 1.2; height: auto; overflow: hidden;">
            <div style="font-weight: bold; color: #0284c7; margin-bottom: 2px;">
                <b>{event_title}</b>
            </div>
            <div style="font-size: 0.65rem; color: #475569; margin-bottom: 4px;">
                {event_desc}
            </div>
            <label style="display: flex; align-items: center; gap: 4px; font-weight: bold; color: #1e293b; cursor: pointer; user-select: none; font-size: 0.7rem; margin: 0;">
                <input type="checkbox" id="event-agree" onchange="toggleEvent()" style="accent-color: #0284c7; cursor: pointer; width: 13px; height: 13px; margin: 0;">
                ?인 ?청 ({event_discount:,}??즉시 ?인)
            </label>
            <div id="event-inputs" style="display: none; flex-direction: column; gap: 4px; background: white; padding: 6px 24px 6px 10px; border-radius: 4px; border: 1px solid #e2e8f0; margin-top: 4px;">
                <div style="display: flex; align-items: center; gap: 4px;">
                    <span style="color: #334155; font-weight: 600; font-size: 0.68rem; min-width: 36px;">??명:</span>
                    <input type="text" id="univ-name" placeholder="?? ?국? ??원" style="flex-grow: 1; padding: 3px 5px; border: 1px solid #cbd5e1; border-radius: 3px; font-size: 0.68rem; outline: none; font-family: inherit; height: 22px; box-sizing: border-box;">
                </div>
                <div style="display: flex; align-items: center; gap: 4px;">
                    <span style="color: #334155; font-weight: 600; font-size: 0.68rem; min-width: 36px;">?문?</span>
                    <input type="text" id="thesis-title" placeholder="?? AHP ?사결정 ?구" style="flex-grow: 1; padding: 3px 5px; border: 1px solid #cbd5e1; border-radius: 3px; font-size: 0.68rem; outline: none; font-family: inherit; height: 22px; box-sizing: border-box;">
                </div>
            </div>
        </div>
        """

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
          <div style="height: 260px; box-sizing: border-box;">{inner_html}</div>
          {event_ui_html}
          <button class="btn" onclick="openPaymentWindow()">결제 {plan_name.split(" (")[0]}</button>
      </div>
      <script>
        let isEventApplied = false;
        const originalAmount = {amount};
        let finalAmount = originalAmount;

        function toggleEvent() {{
            const agreeCheckbox = document.getElementById("event-agree");
            const inputDiv = document.getElementById("event-inputs");
            const priceSpan = window.parent.document.getElementById("price-display-span");
            
            if (agreeCheckbox && agreeCheckbox.checked) {{
                if (inputDiv) inputDiv.style.display = "flex";
                finalAmount = originalAmount - {event_discount};
                isEventApplied = true;
            }} else {{
                if (inputDiv) inputDiv.style.display = "none";
                finalAmount = originalAmount;
                isEventApplied = false;
                if (document.getElementById("univ-name")) document.getElementById("univ-name").value = "";
                if (document.getElementById("thesis-title")) document.getElementById("thesis-title").value = "";
            }}
            
            // iframe 밖의 메인 문서???의??가??스?도 변경을 ?도?니??
            // basic-price-display-span, standard-price-display-span ?으?찾아봅니??
            let priceSpanOuter = null;
            if (originalAmount === 350000) {{
                priceSpanOuter = window.parent.document.getElementById("basic-price-display-span");
            }} else if (originalAmount === 500000) {{
                priceSpanOuter = window.parent.document.getElementById("standard-price-display-span");
            }}
            
            if (priceSpanOuter) {{
                priceSpanOuter.innerText = finalAmount.toLocaleString();
            }}
        }}

        function openPaymentWindow() {{
          if (!{is_logged_in_js}) {{
              alert("?원 ?용 결제 ?비?입?다. ?원가???는 로그?????용??주세??");
              redirectSignup();
              return;
          }}
          let univ = "";
          let thesis = "";
          
          if (isEventApplied) {{
              const uInput = document.getElementById("univ-name");
              const tInput = document.getElementById("thesis-title");
              univ = uInput ? uInput.value.trim() : "";
              thesis = tInput ? tInput.value.trim() : "";
              
              if (!univ) {{
                  alert("?벤???택 ?용???해 ??명???력??주세??");
                  if (uInput) uInput.focus();
                  return;
              }}
              if (!thesis) {{
                  alert("?벤???택 ?용???해 ?문명을 ?력??주세??");
                  if (tInput) tInput.focus();
                  return;
              }}
          }}

          const win = window.open("", "_blank", "width=850,height=700");
          if (!win) {{
             alert("?업 차단???정?어 ?습?다. ?업 차단???제?주?요.");
             return;
          }}
          win.document.write(`
            <!DOCTYPE html>
            <html>
            <head>
              <meta charset="utf-8">
              <title>?전 결제 진행</title>
            </head>
            <body style="margin:0; padding:20px; font-family: sans-serif; text-align: center;">
              <h3 id="statusMsg">결제 모듈???전?게 불러?는 중입?다...</h3>
              <p>??창을 ?? 마세??</p>
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
          
          let eventParams = "&event_applied=" + (isEventApplied ? "Y" : "N") + 
                            "&university=" + encodeURIComponent(univ) + 
                            "&thesis_title=" + encodeURIComponent(thesis);
                            
          const returnUrl = baseOrigin + "/?portone_paid=true&user_id=" + encodeURIComponent("{user_id}") + "&login_user=" + encodeURIComponent("{user_id}") + "&login_token=" + encodeURIComponent("{login_token}") + "&months={months}&plan_name=" + encodeURIComponent("{plan_name}") + eventParams;
          
          const script = win.document.createElement("script");
          script.src = "https://cdn.portone.io/v2/browser-sdk.js";
          script.onload = function() {{
            win.document.getElementById("statusMsg").innerText = "결제창을 ?우??중입?다...";
            const r = Math.random().toString(36).substring(2, 15);
            win.PortOne.requestPayment({{
              storeId: "store-e653cab4-7da6-4bcb-9968-63f77d048c5d",
              channelKey: "channel-key-4279e2d9-c986-47cb-b190-ab1f9bb71215",
              paymentId: "pay-" + r,
              orderName: "{order_name}",
              totalAmount: finalAmount,
              currency: "CURRENCY_KRW",
              payMethod: "CARD",
              redirectUrl: returnUrl,
              customer: {{
                email: "{safe_email}",
                fullName: "?용??,
                phoneNumber: "010-0000-0000"
              }}
            }}).then(function(response) {{
              if (response.code != null) {{
                alert("결제 ?패: " + response.message);
                win.close();
              }} else {{
                win.location.href = returnUrl;
              }}
            }}).catch(function(error) {{
              alert("결제 ??출 ??류가 발생?습?다: " + error.message);
              win.close();
            }});
          }};
          script.onerror = function() {{
            win.document.getElementById("statusMsg").innerText = "결제 모듈 로드 ?패! ?터???결???인?세??";
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
    safe_email = "customer@ahp.kr"
    if user_id and str(user_id).strip():
        u_str = str(user_id).strip()
        login_token = hashlib.sha256(f"{u_str}:AHP_MASTER_SECURE_SALT_2026_!@#".encode()).hexdigest()
        safe_email = u_str if "@" in u_str else f"{u_str}@ahp.kr"

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
          <h3 class="title">부가 ?비?????/h3>
          <span class="subtitle">Custom Services</span>
          <div class="price-container">
              <h2 class="price" id="totalPriceDisplay">0??/h2>
          </div>
          <p class="period">?택???비???계 금액</p>
          <p class="desc" id="statusDesc">?요???비?? ?택??주세??</p>
          <hr class="divider">
          
          <ul class="svc-list">
              <li class="svc-item">
                  <label style="display: flex; align-items: flex-start;">
                      <input type="checkbox" id="svc_opt_1" value="50000" data-name="?라???문 ?팅" onchange="updatePrice()">
                      <span>AHP ?라???문 ?팅 <span style="color: #666; font-size: 0.75rem;">(50,000??</span></span>
                  </label>
              </li>
              <li class="svc-item">
                  <label style="display: flex; align-items: flex-start;">
                      <input type="checkbox" id="svc_opt_2" value="50000" data-name="결과 분석 ??? onchange="updatePrice()">
                      <span>AHP 결과 분석 ???<span style="color: #666; font-size: 0.75rem;">(50,000??</span></span>
                  </label>
              </li>
              <li class="svc-item">
                  <label style="display: flex; align-items: flex-start;">
                      <input type="checkbox" id="svc_opt_3" value="30000" data-name="코딩 ?? ?식 ?정 ??? onchange="updatePrice()">
                      <span>AHP 코딩 ?? ?정 ???<span style="color: #666; font-size: 0.75rem;">(30,000??</span></span>
                  </label>
              </li>
          
              <li class="svc-item">
                  <label style="display: flex; align-items: flex-start;">
                      <input type="checkbox" id="svc_opt_ext" value="100000" data-name="1개월 ?용 ?장" onchange="updatePrice()">
                      <span>1개월 ?용 ?장 <span style="color: #666; font-size: 0.75rem;">(100,000??</span></span>
                  </label>
              </li>
          </ul>
          
          <div style="font-size: 0.72rem; color: #555; text-align: center; margin-bottom: 12px; background: #fafafa; padding: 6px; border-radius: 5px; border: 1px dashed #ccc; line-height: 1.4;">
              견적??발급 ?부가?비??문의: <br>카톡?이?? <b>AHPkr</b>
          </div>
          
          <button class="btn" id="payBtn" onclick="handlePayAction()">결제?기</button>
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
            
            document.getElementById("totalPriceDisplay").innerText = total.toLocaleString() + "??;
            if (count > 0) {{
                document.getElementById("statusDesc").innerText = "?택??????비???" + count + "?;
                document.getElementById("payBtn").innerText = "결제?기";
                document.getElementById("payBtn").style.backgroundColor = "#ff4b4b";
            }} else {{
                document.getElementById("statusDesc").innerText = "?요???비?? ?택??주세??";
                document.getElementById("payBtn").innerText = "?션???택?주?요";
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
                alert("결제?실 부가 ?비??????션???나 ?상 ?택?주?요.");
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
                if (tabs[i].innerText.includes('?원가??) || tabs[i].innerText.includes('Sign Up')) {{
                    tabs[i].click();
                    window.parent.scrollTo(0, 0);
                    return;
                }}
            }}
            alert('로그???는 ?원가?이 ?요?니?? 메인 ?????이?바??해 로그??가?을 진행?주?요.');
            window.parent.scrollTo(0, 0);
        }}
        
        function openPaymentWindow(amount, planName, addMonths) {{
          if (!{is_logged_in}) {{
              alert("?원 ?용 결제 ?비?입?다. ?원가???는 로그?????용??주세??");
              redirectSignup();
              return;
          }}
          const win = window.open("", "_blank", "width=850,height=700");
          if (!win) {{
             alert("?업 차단???정?어 ?습?다. ?업 차단???제?주?요.");
             return;
          }}
          win.document.write(`
            <!DOCTYPE html>
            <html>
            <head>
              <meta charset="utf-8">
              <title>?전 결제 진행</title>
            </head>
            <body style="margin:0; padding:20px; font-family: sans-serif; text-align: center;">
              <h3 id="statusMsg">결제 모듈???전?게 불러?는 중입?다...</h3>
              <p>??창을 ?? 마세??</p>
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
          
          const returnUrl = baseOrigin + "/?portone_paid=true&user_id=" + encodeURIComponent("{user_id}") + "&login_user=" + encodeURIComponent("{user_id}") + "&login_token=" + encodeURIComponent("{login_token}") + "&months=" + addMonths + "&plan_name=" + encodeURIComponent("부가 ?비?? " + planName);
          
          const script = win.document.createElement("script");
          script.src = "https://cdn.portone.io/v2/browser-sdk.js";
          script.onload = function() {{
            win.document.getElementById("statusMsg").innerText = "결제창을 ?우??중입?다...";
            const r = Math.random().toString(36).substring(2, 15);
            win.PortOne.requestPayment({{
              storeId: "store-e653cab4-7da6-4bcb-9968-63f77d048c5d",
              channelKey: "channel-key-4279e2d9-c986-47cb-b190-ab1f9bb71215",
              paymentId: "pay-" + r,
              orderName: "부가 ?비?? " + planName + " - {safe_email}",
              totalAmount: amount,
              currency: "CURRENCY_KRW",
              payMethod: "CARD",
              redirectUrl: returnUrl,
              customer: {{
                email: "{safe_email}",
                fullName: "?용??,
                phoneNumber: "010-0000-0000"
              }}
            }}).then(function(response) {{
              if (response.code != null) {{
                alert("결제 ?패: " + response.message);
                win.close();
              }} else {{
                win.location.href = returnUrl;
              }}
            }}).catch(function(error) {{
              alert("결제 ??출 ??류가 발생?습?다: " + error.message);
              win.close();
            }});
          }};
          script.onerror = function() {{
            win.document.getElementById("statusMsg").innerText = "결제 모듈 로드 ?패! ?터???결???인?세??";
          }};
          win.document.head.appendChild(script);
        }}
      </script>
    </body>
    </html>
    """


def get_unified_english_pricing_html(user_id):
    is_logged_in = "true" if user_id else "false"
    paypal_client_id = st.secrets.get("PAYPAL_CLIENT_ID", "sb")
    
    # We will pass the user_id via query params exactly as done in get_paypal_payment_html
    # window.top.location.href = window.top.location.origin + window.top.location.pathname + "?paypal_order_id=" + data.orderID + "&user_id=" + encodeURIComponent("{user_id}") + "&months={months}&plan_name=" + encodeURIComponent("{plan_name}");
    
    return f'''
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <style>
        @import url("https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css");
        body {{ font-family: 'Pretendard', sans-serif; margin:0; padding: 15px; box-sizing: border-box; background: transparent; }}
        
        .pricing-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 15px;
            width: 100%;
        }}
        
        @media (max-width: 900px) {{
            .pricing-grid {{
                grid-template-columns: repeat(2, 1fr);
            }}
        }}
        @media (max-width: 600px) {{
            .pricing-grid {{
                grid-template-columns: 1fr;
            }}
        }}

        .pricing-box {{
            padding: 15px; 
            border-radius: 10px; 
            height: 520px; 
            position: relative;
            display: flex;
            flex-direction: column;
            box-sizing: border-box;
            background: white;
            border: 1px solid #ddd;
        }}
        .pricing-box.best {{
            border: 2px solid #ff4b4b;
        }}
        
        .best-badge {{
            position: absolute; top: -12px; right: 15px; background-color: #ff4b4b; color: white; padding: 3px 12px; border-radius: 12px; font-size: 0.8rem; font-weight: bold;
        }}

        h3 {{ margin-top: 0 !important; margin-bottom: 0; }}
        .subtitle {{ color: #888; font-size: 1.1rem; }}
        h2.price {{ margin-top: 15px; margin-bottom: 5px; color: #ff4b4b; font-size: 2rem; font-weight: bold; }}
        p.desc {{ font-size: 0.85rem; color: #666; min-height: 40px; margin-top:0; }}
        hr {{ margin: 10px 0; border: 0; border-top: 1px solid #eee; }}
        
        ul.features {{ font-size: 0.9rem; padding-left: 20px; color: #333; line-height: 1.6; margin-top: 0; flex-grow: 1; }}
        
        .svc-list {{ list-style: none; padding-left: 0; margin: 0; font-size: 0.9rem; color: #333; line-height: 1.8; flex-grow: 1; }}
        .svc-item {{ display: flex; align-items: flex-start; margin-bottom: 8px; cursor: pointer; }}
        .svc-item input[type="checkbox"] {{ margin-right: 8px; margin-top: 4px; cursor: pointer; accent-color: #ff4b4b; }}
        .svc-item span {{ font-size: 0.85rem; line-height: 1.4; }}

        .btn-container {{ margin-top: auto; width: 100%; min-height: 40px; }}
        
        .login-btn {{
            width: 100%; padding: 12px; font-weight: bold; font-size: 1rem; border-radius: 5px; cursor: pointer; border: none; transition: 0.3s;
            background-color: #f1f5f9; color: #475569;
        }}
        .login-btn:hover {{ background-color: #e2e8f0; }}
        .login-btn.primary {{ background-color: #ff4b4b; color: white; }}
        .login-btn.primary:hover {{ background-color: #e63946; }}
      </style>
    </head>
    <body>
      <div class="pricing-grid">
          <!-- Basic Plan -->
          <div class="pricing-box">
              <h3>Basic</h3>
              <span class="subtitle">2 Months</span>
              <h2 class="price">$160 USD</h2>
              <p class="desc">Suitable for small-scale projects aiming for reliable results using standard AHP methodology.</p>
              <hr>
              <ul class="features">
                  <li><b>Standard AHP features</b></li>
                  <li><b>Max 10 samples limit</b></li>
                  <li>Unlimited project creation</li>
                  <li>Standard email support</li>
              </ul>
              <div class="btn-container" id="paypal-btn-basic"></div>
          </div>

          <!-- Standard Plan -->
          <div class="pricing-box best">
              <div class="best-badge">BEST</div>
              <h3>Standard</h3>
              <span class="subtitle">2 Months</span>
              <h2 class="price">$330 USD</h2>
              <p class="desc">Suitable for professional research requiring precise conclusions through demographic group-difference analysis.</p>
              <hr>
              <ul class="features">
                  <li><b>Includes Advanced Cross-Statistical Analysis (T-Test, ANOVA)</b></li>
                  <li><b>Unlimited sample size</b></li>
                  <li>Unlimited project creation</li>
                  <li>Standard email support</li>
              </ul>
              <div class="btn-container" id="paypal-btn-standard"></div>
          </div>

          <!-- Pro Plan -->
          <div class="pricing-box">
              <h3>Pro</h3>
              <span class="subtitle">2 Months</span>
              <h2 class="price">$700 USD</h2>
              <p class="desc">Suitable for research institutions and top-tier academic journals requiring advanced Fuzzy AHP analysis and priority support.</p>
              <hr>
              <ul class="features">
                  <li><b>Includes Fuzzy AHP</b></li>
                  <li>Advanced cross-statistical analysis (T-Test, ANOVA)</li>
                  <li>Unlimited sample size & projects</li>
                  <li>Priority tech/bug support</li>
                  <li><b>1 Free survey setup proxy</b></li>
              </ul>
              <div class="btn-container" id="paypal-btn-pro"></div>
          </div>

          <!-- Custom Services -->
          <div class="pricing-box">
              <h3>Proxy Services</h3>
              <span class="subtitle">Custom Services</span>
              <h2 class="price" id="totalPriceDisplay">$0 USD</h2>
              <p class="desc" id="statusDesc" style="margin-bottom:0;">Please select the proxy services you need.</p>
              <hr>
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
              <div class="btn-container" id="paypal-btn-custom"></div>
          </div>
      </div>
      
      <script>
        const isLoggedIn = {is_logged_in};
        let paypalLoaded = false;
        
        function redirectLogin() {{
            window.top.location.hash = "";
            const formContainer = window.top.document.querySelector('[data-testid="stSidebar"]');
            if(formContainer) {{
                const inputs = formContainer.querySelectorAll('input');
                if(inputs.length > 0) inputs[0].focus();
            }}
            alert("Please log in from the left sidebar to purchase.");
        }}

        function setupLoginButtons() {{
            document.getElementById('paypal-btn-basic').innerHTML = '<button class="login-btn" onclick="redirectLogin()">Log in to Purchase</button>';
            document.getElementById('paypal-btn-standard').innerHTML = '<button class="login-btn primary" onclick="redirectLogin()">Log in to Purchase</button>';
            document.getElementById('paypal-btn-pro').innerHTML = '<button class="login-btn" onclick="redirectLogin()">Log in to Purchase</button>';
            document.getElementById('paypal-btn-custom').innerHTML = '<button class="login-btn" onclick="redirectLogin()">Log in to Purchase</button>';
        }}

        function createOrderData(amountStr, planNameStr) {{
            return function(data, actions) {{
                return actions.order.create({{
                    purchase_units: [{{ amount: {{ value: amountStr }}, description: planNameStr }}]
                }});
            }};
        }}

        function createOnApprove(months, planNameStr) {{
            return function(data, actions) {{
                return actions.order.capture().then(function(details) {{
                    window.top.location.href = window.top.location.origin + window.top.location.pathname + "?paypal_order_id=" + data.orderID + "&user_id=" + encodeURIComponent("{user_id}") + "&months=" + months + "&plan_name=" + encodeURIComponent(planNameStr);
                }});
            }};
        }}
        
        function onError(err) {{ alert('PayPal payment failed or was cancelled.'); }}

        function renderPaypalButton(containerId, amount, planName, months) {{
            paypal.Buttons({{
                style: {{ layout: 'vertical', color: 'gold', shape: 'rect', label: 'paypal', height: 40 }},
                createOrder: createOrderData(amount.toString(), planName),
                onApprove: createOnApprove(months, planName),
                onError: onError
            }}).render('#' + containerId);
        }}

        // Global variables for custom button
        let customButtonsInstance = null;

        window.addEventListener('load', function() {{
            if (!isLoggedIn) {{
                setupLoginButtons();
                updatePrice();
                return;
            }}
            
            var script = document.createElement('script');
            script.src = "https://www.paypal.com/sdk/js?client-id={paypal_client_id}&currency=USD&locale=en_US";
            script.onload = function() {{
                paypalLoaded = true;
                
                // Render static buttons
                renderPaypalButton('paypal-btn-basic', 160.0, "Basic (2 Months)", 2);
                renderPaypalButton('paypal-btn-standard', 330.0, "Standard (2 Months)", 2);
                renderPaypalButton('paypal-btn-pro', 700.0, "Pro (2 Months)", 2);
                
                // Initial custom button render
                updatePrice();
            }};
            document.head.appendChild(script);
        }});

        function updatePrice() {{
            const opt1 = document.getElementById("svc_opt_1");
            const opt2 = document.getElementById("svc_opt_2");
            const opt3 = document.getElementById("svc_opt_3");
            const optExt = document.getElementById("svc_opt_ext");
            
            let total = 0;
            let count = 0;
            let items = [];
            if (opt1 && opt1.checked) {{ total += parseInt(opt1.value); count++; items.push(opt1.getAttribute("data-name")); }}
            if (opt2 && opt2.checked) {{ total += parseInt(opt2.value); count++; items.push(opt2.getAttribute("data-name")); }}
            if (opt3 && opt3.checked) {{ total += parseInt(opt3.value); count++; items.push(opt3.getAttribute("data-name")); }}
            if (optExt && optExt.checked) {{ total += parseInt(optExt.value); count++; items.push(optExt.getAttribute("data-name")); }}
            
            document.getElementById("totalPriceDisplay").innerText = "$" + total.toLocaleString() + " USD";
            
            if (count > 0) {{
                document.getElementById("statusDesc").innerText = "Selected services: " + count + " item(s)";
            }} else {{
                document.getElementById("statusDesc").innerText = "Please select the proxy services you need.";
            }}
            
            if (isLoggedIn) {{
                renderCustomPaypalButton(total, items.join(", "));
            }}
        }}

        function renderCustomPaypalButton(amount, planName) {{
            const container = document.getElementById("paypal-btn-custom");
            
            if (amount === 0) {{
                if (customButtonsInstance) {{
                    customButtonsInstance.close();
                    customButtonsInstance = null;
                }}
                container.innerHTML = '<div style="text-align: center; padding: 10px; background: #eee; font-size: 0.85rem; border-radius: 5px; color: #777; font-weight: bold;">Select an option above</div>';
                return;
            }}
            
            if (!paypalLoaded) return;
            
            if (customButtonsInstance) {{
                customButtonsInstance.close();
                customButtonsInstance = null;
            }}
            container.innerHTML = "";
            
            customButtonsInstance = paypal.Buttons({{
                style: {{ layout: 'vertical', color: 'gold', shape: 'rect', label: 'paypal', height: 40 }},
                createOrder: createOrderData(amount.toString(), planName),
                onApprove: createOnApprove(0, planName), // months 0 for custom
                onError: onError
            }});
            
            customButtonsInstance.render('#paypal-btn-custom');
        }}
      </script>
    </body>
    </html>
    '''


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
      <script>
        window.addEventListener('load', function() {{
            var script = document.createElement('script');
            script.src = "https://www.paypal.com/sdk/js?client-id={paypal_client_id}&currency=USD&locale=en_US";
            script.onload = function() {{
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
            }};
            document.head.appendChild(script);
        }});
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
      
      <script>
        let paypalLoaded = false;
        window.addEventListener('load', function() {{
            var script = document.createElement('script');
            script.src = "https://www.paypal.com/sdk/js?client-id={paypal_client_id}&currency=USD&locale=en_US";
            script.onload = function() {{
                paypalLoaded = true;
                updatePrice();
            }};
            document.head.appendChild(script);
        }});

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
            
            if (!paypalLoaded) return;
            
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
                  window.top.location.href = window.top.location.origin + window.top.location.pathname + "?paypal_order_id=" + data.orderID + "&user_id=" + encodeURIComponent("{user_id}") + "&months=" + addMonths + "&plan_name=" + encodeURIComponent("부가 ?비?? " + planName);
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
                if (tabs[i].innerText.includes('?원가??) || tabs[i].innerText.includes('Sign Up')) {{
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
    is_free_user = False
    try:
        is_free_user = (st.session_state.get('user_id') is not None and st.session_state.get('user_role') == 'temp')
    except:
        pass

    if is_free_user:
        return _(
            """<div style="line-height: 1.4; font-size: 0.95rem;">
  <hr style="margin-top: 15px; margin-bottom: 15px; border: 0; border-top: 1px solid #ddd;">
  <div style="background-color: #fffbeb; padding: 12px; margin-bottom: 15px; border-radius: 6px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
    <span style="font-size: 0.95rem; color: #b45309; font-weight: bold; display: block; margin-bottom: 6px;">? ?식(?료) ?원 ?환 ?택</span>
    <span style="font-size: 0.85rem; color: #1e293b; line-height: 1.5; display: block;">
      ?식 ?원?로 ?환?시?모든 분석 ?도가 즉시 ?제?며 ?래 ?택???공?니??
    </span>
    <ul style="color: #334155; margin: 6px 0 0 0; padding-left: 9px; line-height: 1.45;">
      <li><span style="font-size: 0.85rem;">분석 ?본???한 ?전 ?제 (무제??분석)</span></li>
      <li><span style="font-size: 0.85rem;">집단?차이 분석 (T-Test, ANOVA) ?공</span></li>
      <li><span style="font-size: 0.85rem;">??(Fuzzy) AHP 분석 기능 지??(Pro)</span></li>
      <li><span style="font-size: 0.85rem;">?문??고해?도 ?각??보고???운로드</span></li>
    </ul>
  </div>
  <div style="background-color: #e6f7ff; border-left: 4px solid #1890ff; padding: 10px; margin-bottom: 12px; border-radius: 4px;">
    <span style="font-size: 0.9rem; color: #0050b3; font-weight: bold;">? 계산???금?수?발급</span>
  </div>
  <h3 style="margin-top: -5px; margin-bottom: 8px;">?불 ?취소 규정</h3>
  <div style="margin-top: 10px; font-size: 0.85rem; color: #444; background-color: #f9f9f9; padding: 12px; border-radius: 5px; border: 1px solid #eee;">
    <div style="display: grid; grid-template-columns: auto 1fr; row-gap: 6px; column-gap: 8px; line-height: 1.45;">
      <div style="font-weight: bold; color: #333; white-space: nowrap;">???불?책:</div>
      <div>불만?100% ?불</div>
      <div style="font-weight: bold; color: #333; white-space: nowrap;">??취소규정:</div>
      <div>30??내 취소 ?청</div>
    </div>
  </div>
</div>""",
            """<div style="line-height: 1.4; font-size: 0.95rem;">
  <hr style="margin-top: 15px; margin-bottom: 15px; border: 0; border-top: 1px solid #ddd;">
  <div style="background-color: #fffbeb; padding: 12px; margin-bottom: 15px; border-radius: 6px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
    <span style="font-size: 0.95rem; color: #b45309; font-weight: bold; display: block; margin-bottom: 6px;">? Upgrade to Paid License</span>
    <span style="font-size: 0.85rem; color: #1e293b; line-height: 1.5; display: block;">
      Upgrade to a paid license to unlock all limits and enjoy the following benefits:
    </span>
    <ul style="color: #334155; margin: 6px 0 0 0; padding-left: 9px; line-height: 1.45;">
      <li><span style="font-size: 0.85rem;">Unlimited sample analysis (no limit)</span></li>
      <li><span style="font-size: 0.85rem;">Cross-statistical analysis (T-Test, ANOVA)</span></li>
      <li><span style="font-size: 0.85rem;">Fuzzy AHP analysis support (Pro plan)</span></li>
      <li><span style="font-size: 0.85rem;">Download advanced charts & thesis reports</span></li>
    </ul>
  </div>
  <div style="background-color: #e6f7ff; border-left: 4px solid #1890ff; padding: 10px; margin-bottom: 12px; border-radius: 4px;">
    <span style="font-size: 0.9rem; color: #0050b3; font-weight: bold;">? Tax Invoice & Cash Receipt Available</span>
  </div>
  <h3 style="margin-top: -5px; margin-bottom: 8px;">Refund & Cancellation Policy</h3>
  <div style="margin-top: 10px; font-size: 0.85rem; color: #444; background-color: #f9f9f9; padding: 12px; border-radius: 5px; border: 1px solid #eee;">
    <div style="display: grid; grid-template-columns: auto 1fr; row-gap: 6px; column-gap: 8px; line-height: 1.45;">
      <div style="font-weight: bold; color: #333; white-space: nowrap;">??Refund Policy:</div>
      <div>100% Refund if unsatisfied</div>
      <div style="font-weight: bold; color: #333; white-space: nowrap;">??Cancellation Policy:</div>
      <div>Cancellation within 30 minutes</div>
    </div>
  </div>
</div>"""
        )
    else:
        return _(
            """<div style="line-height: 1.4; font-size: 0.95rem;">
  <hr style="margin-top: 15px; margin-bottom: 15px; border: 0; border-top: 1px solid #ddd;">
  <div style="background-color: #f0fdf4; padding: 12px; margin-bottom: 15px; border-radius: 6px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
    <span style="font-size: 0.95rem; color: #15803d; font-weight: bold; display: block; margin-bottom: 6px;">? 무료 ?원가???내</span>
    <span style="font-size: 0.85rem; color: #1e293b; line-height: 1.5; display: block;">
      ?단??<strong>'?원가??</strong> ????<strong>무료 ?원가??/strong>??가?합?다. 무료 ?원?게???래 ?택???공?니??
    </span>
    <ul style="color: #334155; margin: 6px 0 0 0; padding-left: 9px; line-height: 1.45;">
      <li><span style="font-size: 0.85rem;">AHP 코딩 ?? ?식 ?운로드</span></li>
      <li><span style="font-size: 0.85rem;">?라??AHP ?문지 ?작/배포 (무료)</span></li>
      <li><span style="font-size: 0.85rem;">?시??문 ?이??구? ?트 ?동</span></li>
      <li><span style="font-size: 0.85rem;">?문 ?답 모니?링 & 결과 ?운로드</span></li>
      <li><span style="font-size: 0.85rem;">AHP 분석 ?구 무료 체험 (최? 3?본)</span></li>
    </ul>
  </div>
  <div style="background-color: #e6f7ff; border-left: 4px solid #1890ff; padding: 10px; margin-bottom: 12px; border-radius: 4px;">
    <span style="font-size: 0.9rem; color: #0050b3; font-weight: bold;">? 계산???금?수?발급</span>
  </div>
  <h3 style="margin-top: -5px; margin-bottom: 8px;">?불 ?취소 규정</h3>
  <div style="margin-top: 10px; font-size: 0.85rem; color: #444; background-color: #f9f9f9; padding: 12px; border-radius: 5px; border: 1px solid #eee;">
    <div style="display: grid; grid-template-columns: auto 1fr; row-gap: 6px; column-gap: 8px; line-height: 1.45;">
      <div style="font-weight: bold; color: #333; white-space: nowrap;">???불?책:</div>
      <div>불만?100% ?불</div>
      <div style="font-weight: bold; color: #333; white-space: nowrap;">??취소규정:</div>
      <div>30??내 취소 ?청</div>
    </div>
  </div>
</div>""",
            """<div style="line-height: 1.4; font-size: 0.95rem;">
  <hr style="margin-top: 15px; margin-bottom: 15px; border: 0; border-top: 1px solid #ddd;">
  <div style="background-color: #f0fdf4; padding: 12px; margin-bottom: 15px; border-radius: 6px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
    <span style="font-size: 0.95rem; color: #15803d; font-weight: bold; display: block; margin-bottom: 6px;">? Free Account Benefits</span>
    <span style="font-size: 0.85rem; color: #1e293b; line-height: 1.5; display: block;">
      You can sign up for a <strong>free account</strong> via the <strong>'Sign Up'</strong> tab at the top. Free members enjoy:
    </span>
    <ul style="color: #334155; margin: 6px 0 0 0; padding-left: 9px; line-height: 1.45;">
      <li><span style="font-size: 0.85rem;">Download AHP coding Excel templates</span></li>
      <li><span style="font-size: 0.85rem;">Create and deploy online AHP surveys (Free)</span></li>
      <li><span style="font-size: 0.85rem;">Real-time data integration with Google Sheets</span></li>
      <li><span style="font-size: 0.85rem;">Monitor responses & download raw data</span></li>
      <li><span style="font-size: 0.85rem;">Free trial of AHP analysis tools (up to 3 samples)</span></li>
    </ul>
  </div>
  <div style="background-color: #e6f7ff; border-left: 4px solid #1890ff; padding: 10px; margin-bottom: 12px; border-radius: 4px;">
    <span style="font-size: 0.9rem; color: #0050b3; font-weight: bold;">? Tax Invoice Available</span>
  </div>
  <h3 style="margin-top: -5px; margin-bottom: 8px;">Refund & Cancellation Policy</h3>
  <div style="margin-top: 10px; font-size: 0.85rem; color: #444; background-color: #f9f9f9; padding: 12px; border-radius: 5px; border: 1px solid #eee;">
    <div style="display: grid; grid-template-columns: auto 1fr; row-gap: 6px; column-gap: 8px; line-height: 1.45;">
      <div style="font-weight: bold; color: #333; white-space: nowrap;">??Refund Policy:</div>
      <div>100% Refund if unsatisfied</div>
      <div style="font-weight: bold; color: #333; white-space: nowrap;">??Cancellation Policy:</div>
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
            f'<a href="https://www.ahpmaster.com" target="_blank">'
            f'<img src="data:image/png;base64,{encoded_logo}" style="width:100%; border-radius: 4px; display: block; margin-bottom: 10px;">'
            f'</a>',
            unsafe_allow_html=True
        )
    except:
        st.markdown(
            f'<a href="https://www.ahpmaster.com" target="_blank" style="text-decoration: none; color: inherit;">'
            f'<h3 style="margin-top: -5px; margin-bottom: 10px;">{_(" AHP 마스??, " AHP Master")}</h3>'
            f'</a>',
            unsafe_allow_html=True
        )


    if st.session_state.user_id is None:
        tab_login, tab_find_pw = st.tabs([_("로그??, "Login"), _("비?번호 찾기", "Find Password")])
        
        with tab_login:
            l_id = st.text_input(_("?이??(?메??주소)", "Username (Email Address)"), key="l_id")
            l_pw = st.text_input(_("비?번호 (PW)", "Password (PW)"), type="password", key="l_pw")
            if st.button(_("로그???행", "Login")):
                result = check_login(l_id.strip(), l_pw)
                if result:
                    # [?정] ?????간 기? ?늘 ?짜 가?오?
                    today = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).date()
                    expiry_date_val = datetime.datetime.strptime(result[1], "%Y-%m-%d").date()
                    if today > expiry_date_val:
                        if result[0] == 'official':
                            # ?식 ?용?? 만료??경우 -> ?동?로 무료?용??temp)?즉시 ?전 ?격 ?제 ??환
                            try:
                                update_user_full_info(l_id.strip(), None, "temp", "9999-12-31")
                                st.session_state.user_id = l_id.strip()
                                st.session_state.user_role = "temp"
                                st.session_state.expiry_date = "9999-12-31"
                                try:
                                    import survey_manager
                                    survey_manager.log_user_action(l_id.strip(), "로그??(?시 발급)")
                                except:
                                    pass
                                st.query_params["login_user"] = l_id.strip()
                                st.query_params["login_token"] = hashlib.sha256(f"{l_id.strip()}:AHP_MASTER_SECURE_SALT_2026_!@#".encode()).hexdigest()
                                st.query_params["last_activity"] = str(int(time.time()))
                                st.toast(_("? ?식 ?용 기간??만료?어 무료?용??권한?로 ?동 ?환?었?니??", "? Subscription expired. Automatically downgraded to Free User."))
                                st.success(_(f"?영?니?? {l_id}?? ?식 ?용 기간??만료?어 무료?용??3?본 분석 가?? 권한?로 ?동 ?환?었?니?? ?이?바?서 ?제???장 결제?실 ???습?다!",
                                             f"Welcome, {l_id}! Your subscription expired and you were automatically downgraded to a Free User (5-sample analysis possible). You can extend your subscription anytime in the sidebar!"))
                                st.rerun()
                            except Exception as e:
                                st.error(_(f"만료 ?원 ?동 ?환 처리 ??류가 발생?습?다: {e}", f"Error during automatic expiry downgrade: {e}"))
                        else:
                            st.error(_(f"???용 기간??만료?었?니?? (만료?? {result[1]})", f"??Subscription expired. (Expiry date: {result[1]})"))
                    else:
                        st.session_state.user_id = l_id.strip()
                        st.session_state.user_role = result[0]
                        st.session_state.expiry_date = result[1]
                        st.session_state.logout_requested = False
                        st.session_state._survey_cache_dirty = True
                        st.session_state.pop('_cached_user_surveys', None)
                        st.session_state.survey_auto_loaded = False
                        try:
                            import survey_manager
                            survey_manager.log_user_action(l_id.strip(), "로그??)
                        except:
                            pass
                        st.session_state.plan_type = result[2] if len(result) > 2 else None
                        st.query_params["login_user"] = l_id.strip()
                        st.query_params["login_token"] = hashlib.sha256(f"{l_id.strip()}:AHP_MASTER_SECURE_SALT_2026_!@#".encode()).hexdigest()
                        st.query_params["last_activity"] = str(int(time.time()))
                        if 'signup_paypal_user' in st.session_state:
                            del st.session_state.signup_paypal_user
                        if 'signup_portone_user' in st.session_state:
                            del st.session_state.signup_portone_user
                        st.success(_(f"?영?니?? {l_id}??", f"Welcome, {l_id}!"))
                        st.rerun()
                else:
                    st.error(_("?이???는 비?번호가 ?치?? ?습?다.", "Incorrect username or password."))
            
            
        with tab_find_pw:
            st.write(_("가?????용???메??주소??력?주?요. ?메?로 ?로???시 비?번호가 발송?니??",
                       "Please enter the email address used at registration. A new temporary password will be sent to your email."))
            f_id = st.text_input(_("가?한 ?이??(?메??", "Registered ID (Email)"), key="f_id")
            if st.button(_("?시 비?번호 ?송", "Send Temporary Password")):
                if not f_id:
                    st.warning(_("?메??주소??력?주?요.", "Please enter your email address."))
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
                            st.success(_(f"'{f_id}'??시 비?번호??송?습?다.\n?메?을 ?인?주?요.", f"Temporary password sent to '{f_id}'.\nPlease check your email."))
                        else:
                            st.error(_("?메???송 ??류가 발생?습?다.", "Error sending email."))
                    else:
                        st.error(_("?록?? ?? ?이?입?다.", "ID is not registered."))

    else:
        if st.session_state.user_role == 'admin':
            role_disp = _("관리자", "Admin")
        elif st.session_state.user_role == 'official':
            pt = st.session_state.get('plan_type')
            role_disp = f"{_('?식 ?용??, 'Official User')} ({pt})" if pt else _("?식 ?용??, "Official User")
        else:
            role_disp = _("무료?용??, "Free User")
        
        expiry_info = ""
        if st.session_state.expiry_date:
            expiry_label = _("만료?? ", "Expiry: ")
            expiry_info = f' | {expiry_label}{st.session_state.expiry_date}'
            
        info_html = f"""<div style="background-color: #e8f5e9; border: 1px solid #c8e6c9; border-radius: 6px; color: #2e7d32; font-weight: bold; font-size: 0.85rem; padding: 8px 10px; text-align: center; margin-bottom: 8px;">
? {st.session_state.user_id} ({role_disp}{expiry_info})
</div>"""
        st.markdown(info_html, unsafe_allow_html=True)
        
        if st.session_state.user_role == 'admin':
            btn_label = _("? 관리자 ?면 ?기", "? Exit Admin Panel") if st.session_state.get('admin_mode', False) else _("? 관리자 ?면 ?속", "? Connect to Admin Panel")
            if st.button(btn_label):
                st.session_state.admin_mode = not st.session_state.admin_mode
                st.rerun()

        # [?치 ?동] 2. 로그?웃 버튼
        if st.button(_("로그?웃", "Log Out"), key="btn_logout_new"):
            st.session_state.user_id = None
            st.session_state.user_role = None
            st.session_state.expiry_date = None
            st.session_state.plan_type = None
            st.session_state.admin_mode = False
            st.session_state.signup_paypal_user = None
            st.session_state.signup_portone_user = None
            st.session_state.logout_requested = True
            st.session_state._survey_cache_dirty = True
            st.session_state.pop('_cached_user_surveys', None)
            st.session_state.survey_auto_loaded = False
            if 'cookie_manager' in st.session_state and st.session_state.cookie_manager:
                try:
                    st.session_state.cookie_manager.delete("ahp_user_id", key="del_ahp_user_cookie_manual")
                except Exception:
                    pass
            if "login_user" in st.query_params:
                try:
                    del st.query_params["login_user"]
                except Exception:
                    pass
            if "login_token" in st.query_params:
                try:
                    del st.query_params["login_token"]
                except Exception:
                    pass
            st.rerun()


        # [?치 ?동] 1. 비?번호 변?expander
        with st.expander(_("비?번호 변?, "Change Password")):
            cur_pw = st.text_input(_("?재 비?번호", "Current Password"), type="password", key="chg_cur_new")
            new_pw_val = st.text_input(_("??비?번호", "New Password"), type="password", key="chg_new_new")
            confirm_pw = st.text_input(_("??비?번호 ?인", "Confirm New Password"), type="password", key="chg_conf_new")
            
            if st.button(_("비?번호 변?, "Change Password"), key="btn_chg_pw_new"):
                if new_pw_val != confirm_pw:
                    st.error(_("??비?번호가 ?치?? ?습?다.", "New passwords do not match."))
                elif not validate_password(new_pw_val):
                    st.error(_("비?번호??4???상, ?문+?수문자??함?야 ?니??", "Password must be at least 4 characters and contain letters and special characters."))
                else:
                    chk_res = check_login(st.session_state.user_id, cur_pw)
                    if chk_res:
                        change_user_password(st.session_state.user_id, new_pw_val)
                        st.success(_("비?번호가 변경되?습?다.", "Password successfully changed."))
                    else:
                        st.error(_("?재 비?번호가 ?바르? ?습?다.", "Incorrect current password."))

    st.markdown(get_fee_info_text(), unsafe_allow_html=True)
    if st.button(_("?불 ?취소 ?청", "Request Refund & Cancellation"), key="sidebar_refund_btn", use_container_width=True):
        show_refund_dialog()

    if st.session_state.user_id is not None and st.session_state.user_role == 'temp':
        if st.button(_("??식 ?용?로 ?환?기", "?Upgrade to Paid License Now"), key="sidebar_upgrade_btn", use_container_width=True):
            st.components.v1.html("""
                <script>
                    const tabs = window.parent.document.querySelectorAll('button[data-baseweb="tab"]');
                    for (let i = 0; i < tabs.length; i++) {
                        if (tabs[i].innerText.includes('?비???내') || tabs[i].innerText.includes('Service Info')) {
                            tabs[i].click();
                            window.parent.scrollTo(0, 0);
                            break;
                        }
                    }
                </script>
            """, height=0, width=0)
    st.markdown("""
    <div style="line-height: 1.4; font-size: 0.95rem;">
      <hr style="margin-top: 15px; margin-bottom: 15px; border: 0; border-top: 1px solid #ddd;">
      <h3 style="margin-top: -5px; margin-bottom: 8px;">?업?정?/h3>
      <div style="font-size: 0.85rem; color: #555;">
        ?호: ?레?인?이??br>
        ??자: ?상??br>
        ?업?등록번?? 683-27-00122<br>
        ?업??주소: ?천??부?구 ?길?12, 가??203??br>
        ?화번호: 0507-1347-2610<br>
        ?메?? jeon080423@gmail.com<br>
        개인?보관리책?자: ?상??br>
        ?신?매???고번호: 간이과세??br>
      </div>
    </div>
    """, unsafe_allow_html=True)



# =============================================================================
# 4. Main Content Logic
# =============================================================================

if st.session_state.get('page', 'main') == 'guide':
    if st.button("??Back to AHP Analysis Tool", use_container_width=True, key="btn_back_to_main"):
        st.session_state.page = "main"
        st.rerun()
    
    st.title(" AHP Master - English User Guide")
    st.markdown("""
    ?? **Welcome!** **AHP Master** is a smart web service that automatically processes the entire Analytic Hierarchy Process (AHP) workflow in 1 second, without requiring complex equations or statistical software.
    This guide is designed to walk first-time users through the step-by-step process of completing their academic thesis statistics and decision analysis smoothly.
    
    ---
    
    ###  Step 1: Prepare the Excel Template (Write & Customize)
    AHP Master uses a specifically formatted Excel file to read your survey data.
    
    1. **Download Template**: Go to the AHP Master website (https://ahpkrj.streamlit.app/) and click the **[Download Excel Template]** button on the home screen.
    2. **? Customize to Fit Your Model (Important)**:
       * The default template items (evaluation criteria, alternatives, etc.) and hierarchical structure can be freely edited to match your specific research model.
       * You can add or delete criteria to construct your own custom AHP model.
    3. **Enter Survey Data**: Open the customized Excel template and enter your pairwise comparison survey responses.
       * **Evaluation Scale**: Uses Saaty's 1-9 fundamental scale (e.g., enter 7 if item A is much more important than B, enter 1 if they are equally important).
       * **Note**: Be careful not to break the core structure (sheet configuration, etc.) of the template.
    
    ### ? Step 2: Upload File & Run Basic Analysis
    Once your data entry is complete, it's time to run the analysis.
    
    1. **File Upload**: Drag and drop your Excel file into the **[Drag and drop file here]** zone in the center of the screen, or click **[Browse files]** to select your file.
    2. **Automatic Execution**: The system will instantly run the complex matrix calculations in the background. Basic analysis typically completes in 1 to 3 seconds.
    
    ### ?️ Step 3: Utilize [Analysis Settings] in the Sidebar
    After uploading, you can fine-tune the analysis details through the "Analysis Settings" in the left sidebar to suit your research methodology.
    
    1. **Select Aggregation Method**:
       * You can set specific parameters like the weight integration method (Geometric Mean vs. Arithmetic Mean) or the decimal precision required for your research.
    2. **CR Calibration Settings (Optional)**:
       * You can set boundaries such as how much you allow the original response to change (Correction Intensity/Learning Rate) when performing Consistency Ratio (CR) calibration.
       * *(If accessing on a mobile device, tap the `>` icon in the top left to reveal the sidebar menu.)*
    
    ### ? Step 4: Consistency Validation & Automatic Calibration (CR)
    This is the step to validate the logical consistency of responses, which is critical in AHP academic studies.
    
    1. **Check Initial CR Value**: Check the **Consistency Ratio (CR)** displayed in the results panel.
       * `CR < 0.1` (Green): Indicates highly consistent and logical responses (Passed).
       * `CR > 0.1` (Red): Indicates logical contradictions exceed the standard limit (Needs Calibration).
    2. **? One-Click Auto Calibration**: If the initial CR value exceeds 0.1, do not worry. Simply click the **[CR Auto Calibration]** button. AHP Master's optimization algorithm will adjust the CR value to under 0.1 automatically, preserving the original response preferences as much as possible.
    
    ### ? Step 5: Check Weights & Save Results
    Once all validations and settings are complete, use the final results in your report or paper.
    
    1. **Check Weights & Rankings**:
       * **Main/Sub-Criteria Weights**: View the weight percentages and decimals representing the importance of each item.
       * **Global Rank**: View the overall 1st-to-last rankings of the items in an intuitive table and visual Plotly charts.
    2. **Download Results (Excel/Image)**:
       * Click the **[Download Results (Excel)]** button at the bottom of the screen to save the results in a clean table format ready to copy-paste.
       * Click the camera icon in the top right of the Plotly charts to save the charts as high-resolution images (PNG).
    
    ---
    
    ### ? Frequently Asked Questions (FAQ)
    
    * **Q1. Can I change the template items to fit my specific paper?**
      * **Yes, absolutely!** The default template is only an example. You can add or delete rows and columns, rename text, and modify items to build **your own custom hierarchical model (Custom Model)** to fit your evaluation criteria and alternative count.
    * **Q2. Can I analyze data from multiple survey respondents (group analysis) at once?**
      * Yes! If you have multiple respondents, you can calculate the geometric mean of individual pairwise comparisons in Excel, enter the aggregated figures into the template, and upload it to calculate the group weights at once.
    * **Q3. I see an "Error" message during upload. Why?**
      * In the customization process, the required sheets' layout may have been broken, or some number input cells might have empty (Null) values or text instead of numbers. Please review your Excel template to ensure all numeric inputs are complete.
    
    ---
    
    ### ? Contact & Support
    If you have any questions during analysis, or need custom AHP consulting (expert survey execution, thesis statistical consulting, etc.), please contact us:
    * **Email**: jeon080423@gmail.com
    * **KakaoTalk ID**: AHPkr
    * **Mobile**: 0507-1347-2610
    """)
    
    if st.button("??Back to AHP Analysis Tool", use_container_width=True, key="btn_back_to_main_bottom"):
        st.session_state.page = "main"
        st.rerun()
    st.stop()

# 메인 ?더 ?역
try:
    # ?능 최적?? ?해 메인 ?면?서??구? ?트 ???로컬 DB??방문 로그 ?만 즉시 집계?니??
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM visit_logs")
    total_visits = c.fetchone()[0]
    conn.close()
except Exception:
    total_visits = 0

col_main_title, col_settings_title = st.columns([3.0, 1.1], gap="large")
with col_main_title:
    st.title(_("AHP ?사결정 분석 ?루??, "AHP Decision Analysis Solution"))

with col_settings_title:
    visitor_label = _("?적 방문??, "Total Visitors")
    visitor_unit = _("?, " visitors")
    
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
            <a href="{ko_url}" target="_self" style="text-decoration: none; color: {lang_ko_color}; font-weight: {lang_ko_weight};">?국??/a>
            <span style="color: #ccc; margin: 0 4px;">|</span>
            <a href="{en_url}" target="_self" style="text-decoration: none; color: {lang_en_color}; font-weight: {lang_en_weight};">English</a>
        </span>
        <span style="font-size: 0.85rem; color: #0369a1; font-weight: bold;">
            {visitor_label} : {total_visits:,}{visitor_unit}
        </span>
    </div>
    """
    st.markdown(counter_html, unsafe_allow_html=True)

import contextlib
col_main = contextlib.nullcontext()
col_settings = contextlib.nullcontext()
@st.dialog(_("?림", "Notice"))
def show_warning_dialog():
    st.warning(_("?️ 분석 ???인 가?합?다. (?이?? 먼? ?로?하?요)", "?️ Available after analysis. (Please upload data first)"))

# ---------- CR Distortion Verification Dialog ----------
@st.dialog(_("? CR 보정 결과 ?곡 검?, "? CR Consistency Distortion Verification"), width="large")
def show_cr_distortion_dialog():

    from cr_analysis import run_analysis, matrix_to_heatmap_img
        
    st.info(_("? ?로?된 메인 기? ?이???답???체 기하?균 ?렬)?바탕?로 검증을 ?행?니??", "? Performing verification based on the uploaded Main Criteria data (geometric mean matrix of all respondents)."))
    original_matrix = st.session_state.uploaded_matrix

    # Determine selected CR option
    option = st.session_state.get('cr_threshold_label', '0.1')
    if option in ["보정 ?? ?음", "Do Not Correct"]:
        corrected_matrix = original_matrix.copy()
        option_name = _("보정 ????, "Do Not Correct")
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
        st.subheader(_(" 검?결과", " Verification Results"))
        st.dataframe(pd.DataFrame([metrics]), use_container_width=True)

        # Heatmaps side by side
        orig_img = matrix_to_heatmap_img(original_matrix, _("?본 ?렬", "Original Matrix"))
        corr_img = matrix_to_heatmap_img(corrected_matrix, option_name)
        hm1, hm2 = st.columns(2)
        with hm1:
            st.image(f"data:image/png;base64,{orig_img}", caption=_("?본 ?렬", "Original Matrix"), use_container_width=True)
        with hm2:
            st.image(f"data:image/png;base64,{corr_img}", caption=_("보정 ?렬", "Corrected Matrix"), use_container_width=True)

    with left_col:
        st.subheader(_(" 검?방법", " Verification Method"))
        st.markdown(_(
            f"""
?검증? CR(????비율) 보정 과정?서 **?본 ?답 ?이?? ?마??변?되?는지**??량?으?측정?니??

**검??차:**
1. **?본 ?렬 ?보** ???문 ?답?의 ??비교 ?단 ?렬??그???용?니??
2. **보정 ?렬 ?성** ???택??CR ?계?`{option_name}`)???라 반복 ?렴 조정?Iterative Adjustment)?로 보정???렬???성?니??
3. **차이 분석** ???본?보정 ?렬 ?4가지 ?리??지?? 계산?니??
   - **?클리드 거리**: ?렬 ?소 ?직선 거리
   - **맨해??거리**: ?렬 ?소 ??? 차이????
   - **코사???사??*: ???렬 벡터??방향 ?치??
   - **?곡 ?수**: ??지?들??종합???곡 ?? 지??
4. **종합 ?정** ???곡 ?수?기??로 보정???뢰?을 ???니??

> ? ?곡 ?수가 ???록 보정???본 ?답??경향?을 ??보존?음?????니??

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

> ? A lower Distortion Score means the correction better preserved the original response patterns.

---
"""))

        st.subheader(_(" 결과 ?석", " Interpretation"))

        # Extract metric values
        euc = metrics.get("euclidean", 0)
        man = metrics.get("manhattan", 0)
        cos = metrics.get("cosine_similarity", 1)
        dist = metrics.get("distortion_score", 0)

        st.markdown(_( 
            f"""
**1. ?클리드 거리 (Euclidean Distance): `{euc:.6f}`**  
?본 ?렬?보정 ?렬 ?이??직선 거리?니??  
값이 **0??가까울?록** 보정???본??거의 변?하지 ?았?을 ???니??

**2. 맨해??거리 (Manhattan Distance): `{man:.6f}`**  
??소?차이??????입?다.  
?클리드 거리? ?께 보정??**?체?인 변???기**????니??

**3. 코사???사??(Cosine Similarity): `{cos:.6f}`**  
???렬 벡터 간의 방향 ?사?입?다.  
**1.0??가까울?록** 보정 ?후 ?답 ?턴???일??방향?????고 ?습?다.

**4. ?곡 ?수 (Distortion Score): `{dist:.6f}`**  
종합?인 ?곡 ???????는 지?입?다.

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
            verdict = _("?곡 ??: **매우 ??** ??보정???본 ?답??거의 변?하지 ?았?니?? ?뢰?????는 결과?니??",
                        "Distortion Level: **Very Low** ??The correction barely altered the original responses. The result is reliable.")
        elif dist < 0.05:
            verdict_icon = "?"
            verdict = _("?곡 ??: **??** ??경???조정???었?나 ?본 경향?이 ??보존?었?니??",
                        "Distortion Level: **Low** ??Minor adjustments were made, but the original trends are well preserved.")
        elif dist < 0.15:
            verdict_icon = "?"
            verdict = _("?곡 ??: **보통** ???? 변?이 발생?습?다. 결과 ?석??주의가 ?요?니??",
                        "Distortion Level: **Moderate** ??Some distortion occurred. Interpret results with caution.")
        else:
            verdict_icon = "?"
            verdict = _("?곡 ??: **?음** ??보정 과정?서 ?당??변?이 발생?습?다. CR ?계값을 조정?거???본 ?이?? ???하?요.",
                        "Distortion Level: **High** ??Significant distortion occurred during correction. Consider adjusting the CR threshold or reviewing the original data.")

        st.markdown(f"### {verdict_icon} {_('종합 ?정', 'Overall Verdict')}")
        st.info(verdict)


def render_ahp_analysis_settings():
    ahp_method = 'traditional'
    mean_method = 'geometric'
    cr_threshold = 0.1
    max_iter_val = 500
    learning_rate = 0.6
    if st.session_state.get('admin_mode', False) and st.session_state.get('user_role') == 'admin':
        pass
    else:
        with st.container(border=True):
            st.markdown(f'<h4 style="color:black; font-family:Arial, sans-serif; font-weight:bold; margin-top:0; margin-bottom:15px; font-size:1.1rem;">{_("AHP 분석 ?정", "Analysis Settings")}</h4>', unsafe_allow_html=True)
            ahp_method_label = st.radio(_("분석 기법", "Analysis Method"), (_('?반 AHP (Traditional AHP)', 'Traditional AHP'), _('?? AHP (Fuzzy AHP)', 'Fuzzy AHP')), index=0)
            ahp_method = 'traditional' if '?반' in ahp_method_label or 'Traditional' in ahp_method_label else 'fuzzy'
            if ahp_method == 'fuzzy':
                tier = get_current_tier()
                if tier != 'Pro':
                    st.error(_("? ?? AHP??Pro ?금???용 기능?니??", "? Fuzzy AHP is exclusive to Pro Tier."))
                    st.warning(_("?재 무료 ??반 ?원 ?급?서???반 AHP 결과?분석 ??공?니?? ?? AHP 분석???용?시?면 Pro ?급?로 ?그?이?해주시?바랍?다.", 
                                 "In your current tier, only Traditional AHP results are analyzed and provided. To use Fuzzy AHP, please upgrade to the Pro Tier."))
                    ahp_method = 'traditional'
            mean_method_label = st.radio(_("?균 ?출 방식", "Aggregation Method"), (_('기하?균 (Geometric)', 'Geometric Mean'), _('?술?균 (Arithmetic)', 'Arithmetic Mean')), index=0)
            mean_method = 'geometric' if '기하' in mean_method_label or 'Geometric' in mean_method_label else 'arithmetic'
            cr_threshold_label = st.selectbox(
                _("????비율(CR) ?계?, "Consistency Ratio (CR) Threshold"), 
                [_("0.1", "0.1"), _("0.15", "0.15"), _("0.2", "0.2"), _("보정 ?? ?음", "Do Not Correct")], 
                index=0,
                key="cr_threshold_label",
                help=_(
                    "?계??정(0.1, 0.15 ?는 0.2)? ????비율(CR)???당 ?치??확?게 ?치?키??것이 ?니?? ?당 ?계??하?만드??것을 ???니?? ?? ?계??하???이?는 보정?? ?으? ?? ?해 ?본 ?답??과도?게 ?곡?는 것을 방??니??",
                    "The threshold setting (0.1, 0.15 or 0.2) does not force the consistency ratio (CR) to equal that value. Instead, it adjusts the CR to be less than or equal to the threshold. If a matrix is already within the threshold, no correction is applied, preventing excessive distortion of the original responses."
                )
            )
            if "보정 ?? ?음" in cr_threshold_label or "Do Not Correct" in cr_threshold_label:
                cr_threshold = 999.0
                learning_rate = 0.0
            else:
                try:
                    cr_threshold = float(cr_threshold_label)
                except ValueError:
                    cr_threshold = 0.1
            if "보정 ?? ?음" in cr_threshold_label or "Do Not Correct" in cr_threshold_label:
                max_iter_val = 0
                st.number_input(_("최? 보정 반복 ?수", "Max Correction Iterations"), min_value=0, max_value=500, value=0, step=50, disabled=True, key="max_iter_disabled")
            else:
                max_iter_val = st.number_input(_("최? 보정 반복 ?수", "Max Correction Iterations"), min_value=10, max_value=500, value=500, step=50, key="max_iter_enabled")
        
            if "보정 ?? ?음" in cr_threshold_label or "Do Not Correct" in cr_threshold_label:
                st.slider(_("보정 강도 (Learning Rate)", "Correction Intensity (Learning Rate)"), min_value=0.0, max_value=0.9, value=0.0, step=0.1, disabled=True, key="learning_rate_disabled")
            else:
                learning_rate = st.slider(_("보정 강도 (Learning Rate)", "Correction Intensity (Learning Rate)"), min_value=0.1, max_value=0.9, value=0.6, step=0.1, key="learning_rate_enabled")
        # 1. CR 보정 결과 ?곡 검?
        with st.expander(_("CR 보정 결과 ?곡 검?, "CR Consistency Distortion Verification"), expanded=False):
            if st.button(_("??검??행", "??Run Verification"), use_container_width=True, key="btn_cr_verify"):
                if "uploaded_matrix" not in st.session_state:
                    show_warning_dialog()
                else:
                    show_cr_distortion_dialog()

        # 2. ????보정 기?
        with st.expander(_("????보정 기?", "Consistency Correction Standard"), expanded=False):
            st.markdown(_(r"""
            **보정 방법: 반복 ?렴 조정?Iterative Adjustment)**
            가중치 ?출 ?고리즘(Saaty)???해 ?단 ?렬??비일관??CR > ?계???경우, ?학?으??????렬??본 ?렬???정 비율??합?여 반복?으?가중치?미세 조정??결과??시?니??
        
            **?재 방법???징:**
            1. **최소 ?단 ?곡**: ?본 ?문 ?답??경향?을 보존?면???학?????만???보?니??
            2. **?동 ?렴**: ?정??반복 ?수 ?에??CR 값을 ?계??하??동 개선?니?? ($New = (1-\alpha) \times Old + \alpha \times Ideal$)
            3. **과도??보정 방?**: ?계??정(0.1, 0.15 ?는 0.2)? CR 값을 ?확??맞추??것이 ?니???계?'?하'?만드??것을 목표??니?? ?? ?계??하???답? 보정???행?? ?아 ?본 ?단??최???보존?니??
        
            """, r"""
            **Correction Method: Iterative Adjustment**
            If the judgment matrix is inconsistent (CR > threshold) based on Saaty's weight algorithm, it repeatedly adjusts the weights by mixing the original matrix with a mathematically consistent matrix.
        
            **Key Features:**
            1. **Minimal Distortion of Judgments**: Preserves the trends of the original survey responses while securing mathematical consistency.
            2. **Automatic Convergence**: Automatically improves the CR value to be below the threshold within the maximum number of iterations. ($New = (1-\alpha) \times Old + \alpha \times Ideal$)
            3. **Prevention of Excessive Correction**: The threshold setting (0.1, 0.15 or 0.2) targets bringing the CR 'below or equal to' the threshold, rather than matching it exactly. Responses already below the threshold are left uncorrected to preserve the original judgments as much as possible.
        
            """))

        # 3. ?용??가?드
        with st.expander(_("?용??가?드", "User Guide"), expanded=False):
            st.markdown(_("AHP 마스???비???용 ?명???가?드 링크?니??", "Link to the AHP Master user manual and guide."))
            if st.session_state.get('lang', 'ko') == 'en':
                if st.button("Read English User Guide", use_container_width=True, key="btn_read_guide"):
                    st.session_state.page = "guide"
                    st.rerun()
            else:
                st.link_button("?용??가?드 바로가?, "https://morison.tistory.com/103", use_container_width=True)

        with st.expander(_("?술 ?문 ??구 보고??기재 방법 ?시", "Example of citation in academic papers/reports"), expanded=False):
            st.info(_("AHP 분석 결과??위 ?문?나 ?구 보고?에 기술?????래 ?시문을 참고?여 ?용 ??술?실 ???습?다.",
                      "When describing AHP analysis results in your thesis or research report, you can refer to and cite the example below."))
            st.markdown(_("""
            > **[?문 기재 ?시?**
            > 
            > "??구?서 ?집???문 ?이?는 ??기반 AHP ?용 분석 ?루?인 'AHP 마스????용?여 분석???행???? Saaty(1980)??계층분석과정???라 ??비교 ?렬??구성?여 ????가중치? 종합 가중치(Global Weight)??출???며, ????비율(CR)??0.1 미만???도??스?의 보정 기능??거쳐 결과????성???보????"
            """,
            """
            > **[Example of Paper Citation]**
            > 
            > "The survey data collected in this study was analyzed using 'AHP Master', a web-based dedicated AHP analysis solution. Pairwise comparison matrices were constructed in accordance with Saaty's (1980) Analytic Hierarchy Process to calculate local and global weights, and the validity of the results was secured through the system's consistency ratio (CR) adjustment function to ensure CR was below 0.1."
            """))

        if st.session_state.get('lang', 'ko') == 'ko':
            pdf_path = "AHP_Master_Accuracy_Paper.pdf"
            if os.path.exists(pdf_path):
                import base64
                with open(pdf_path, "rb") as f:
                    base64_pdf = base64.b64encode(f.read()).decode('utf-8')
                pdf_html = f'<a href="data:application/pdf;base64,{base64_pdf}" download="AHP_Master_Accuracy_Paper.pdf" style="text-decoration: underline; font-weight: bold; font-size: 14px; color: #1B2A4A;">? AHP ?확??검??문 (PDF) ?운로드</a>'
                st.markdown("<br/>", unsafe_allow_html=True)
                st.markdown(pdf_html, unsafe_allow_html=True)

    return ahp_method, mean_method, cr_threshold, max_iter_val, learning_rate



with contextlib.nullcontext():
                
    
    if st.session_state.get('admin_mode', False) and st.session_state.user_role == 'admin':
        # ?션 ?테?트 기반 ?공 메시지 ?존 출력
        if "sync_success_msg" in st.session_state:
            st.success(st.session_state["sync_success_msg"])
            del st.session_state["sync_success_msg"]
    
        st.subheader(_(" 가?자 ?황 ?관?, " Registered Users & Admin Control"))
        
        col_sync1, col_sync2 = st.columns([2, 8])
        with col_sync1:
            if st.button("? 구? ?트? ?기??):
                with st.spinner("구? ?트 ?이??불러?는 ?.."):
                    # 캐시 ?동 비우?
                    get_cached_visit_logs.clear()
                    added_count = sync_db_from_sheets()
                if added_count >= 0:
                    st.session_state["sync_success_msg"] = f"? ?기???료! (보정 ?복구???이?? {added_count}?"
                    st.rerun()
                else:
                    st.error("?기????류가 발생?습?다. ?면?의 ?러 메시지??인??주세??")
        
        try:
            # [최적?? 구? ?트 API 분당 ?출 ?한(429)???하??해 5?캐시 처리???수??용?니??
            visit_data_gs = get_cached_visit_logs(get_main_spreadsheet_id()) if get_main_spreadsheet_id() else []
            if not visit_data_gs:
                try:
                    conn = sqlite3.connect('users.db')
                    df_local = pd.read_sql_query("SELECT ip_address as IP, visit_date as Date FROM visit_logs", conn)
                    conn.close()
                    if not df_local.empty:
                        # 지???각???에 ?요??컬럼 빈값 보정
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
    
                st.write("#### ???속???시??치 분포")
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
                            st.info("?효??좌표 ?이?? ?습?다.")
                    else:
                        st.info("지?에 ?시???치 ?보 ?이?? ?직 ?집?? ?았?니??")
                else:
                    st.info("?치 ?보 컬럼??존재?? ?습?다.")
            else:
                total_visits = 0
                daily_df_counts = pd.DataFrame()
    
            st.write(f"**?적 방문??** {total_visits:,}?)
            st.write("#### ? ?별 방문???황 (?짜??산)")
            if not daily_df_counts.empty:
                fig_visit = px.bar(daily_df_counts, x='Date_Only', y='count', text='count',
                                    labels={'Date_Only': '?짜', 'count': '방문????})
                fig_visit.update_traces(textposition='outside')
                fig_visit.update_layout(xaxis_title="?짜", yaxis_title="방문????, showlegend=False, xaxis={'type': 'category'})
                st.plotly_chart(fig_visit, use_container_width=True)
            else:
                st.info("방문 기록???습?다.")
        except Exception as e:
            st.error(f"?계 ?류: {e}")
        st.divider()
        
        # 배포 ?계 집계 ??각??
        st.write("---")
        st.write(_("### ? ?문지 배포 ?계", "### ? Survey Distribution Statistics"))
        users_df = get_all_users()
        
        # 컬럼 존재 ?인 ?결측?보정
        if 'survey_count' not in users_df.columns:
            users_df['survey_count'] = 0
        if 'last_survey_link' not in users_df.columns:
            users_df['last_survey_link'] = ""
            
        users_df['survey_count'] = pd.to_numeric(users_df['survey_count'].fillna(0)).astype(int)
        
        # 1. ?약 ?계
        total_dist_surveys = users_df['survey_count'].sum()
        active_users_count = (users_df['survey_count'] > 0).sum()
        total_registered_users = len(users_df)
        
        col_stat1, col_stat2, col_stat3 = st.columns(3)
        with col_stat1:
            st.metric(_("??문 배포 건수", "Total Distributed Surveys"), f"{total_dist_surveys}" + _("?, ""))
        with col_stat2:
            st.metric(_("?문 배포 경험 ?원 ??, "Members with Distribution Experience"), f"{active_users_count}" + _("?, ""))
        with col_stat3:
            st.metric(_("?가???원 ??, "Total Registered Members"), f"{total_registered_users}" + _("?, ""))
            
        # 2. ?용?별 배포 ?수 차트
        active_users_df = users_df[users_df['survey_count'] > 0].copy()
        if not active_users_df.empty:
            active_users_df = active_users_df.sort_values(by='survey_count', ascending=False)
            fig_dist = px.bar(active_users_df, x='id', y='survey_count', text='survey_count',
                              labels={'id': '?원 ID', 'survey_count': '배포 건수'},
                              title="?원??문지 배포 ?황 (1??상 배포 ?원)")
            fig_dist.update_traces(textposition='outside')
            fig_dist.update_layout(xaxis_title="?원 ID", yaxis_title="배포 건수")
            st.plotly_chart(fig_dist, use_container_width=True)
        else:
            st.info(_("?직 ?문??배포???용?? ?습?다.", "No users have distributed a survey yet."))
            
        st.write("---")
        st.write(_("### ? 가?자 ?황 ?최종 배포 링크", "### ? Subscriber Status and Latest Distribution Links"))
        
        # 컬럼 ?서 ?구성 ?조?하???이?프?임?로 출력
        display_df = users_df[['id', 'role', 'signup_date', 'pw', 'survey_count', 'last_survey_link', 'expiry_date', 'agree_info']].copy()
        st.dataframe(
            display_df,
            column_config={
                "id": "?원 ID",
                "role": "권한",
                "signup_date": "가?일",
                "pw": "비?번호",
                "survey_count": "배포 ?수",
                "last_survey_link": st.column_config.LinkColumn("최종 배포 ?문지 링크", display_text="?문지 바로가?),
                "expiry_date": "만료??,
                "agree_info": "?의??"
            },
            hide_index=True,
            use_container_width=True
        )
    
        with st.expander("?원 ?보 ?정 (비?번호 초기???함)"):
            edit_id = st.selectbox("?정???원 ID", users_df['id'].unique())
            selected_user = users_df[users_df['id'] == edit_id].iloc[0]
            new_role_val = st.selectbox("권한 변?, ['temp', 'official', 'admin'], 
                                    index=['temp', 'official', 'admin'].index(selected_user['role']))
            
            if new_role_val == 'official' and selected_user['role'] != 'official':
                suggested_date = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).date() + relativedelta(months=2)
                new_expiry_val = st.text_input("만료???정 (YYYY-MM-DD) - 2개월 기한 ?동 ?안??, value=str(suggested_date))
            else:
                new_expiry_val = st.text_input("만료??변?(YYYY-MM-DD)", value=selected_user['expiry_date'])
                
            new_pw_edit = st.text_input("??비?번호 (?력 ??변경됨)", type="password", placeholder="변경하지 ?으?면 비워?세??)
            
            col_admin_act1, col_admin_act2 = st.columns(2)
            with col_admin_act1:
                if st.button("?보 ?정 ?용", use_container_width=True):
                    update_user_full_info(edit_id, new_pw_edit, new_role_val, new_expiry_val)
                    if new_role_val == 'official' and selected_user['role'] != 'official':
                        send_approval_email(edit_id)
                    st.success(f"{edit_id} ?원???보가 ?정?었?니??")
                    st.rerun()
            with col_admin_act2:
                if st.button("? ??계정?로 로그??, use_container_width=True, type="secondary", help="비?번호 ?이 ???용?의 계정?로 ?션??즉시 ?환?니??"):
                    st.session_state.user_id = edit_id
                    st.session_state.user_role = selected_user['role']
                    st.session_state.expiry_date = selected_user['expiry_date']
                    st.session_state.admin_mode = False  # ?반 ?용???점?로 ?환
                    st.toast(f"? {edit_id} 계정?로 로그?했?니??")
                    st.rerun()
        
        with st.expander("?원 ??"):
            del_id = st.selectbox("?????원 ID ?택", users_df['id'].unique(), key='del_user_select')
            if st.button("?택???원 ??"):
                if del_id == st.session_state.user_id:
                    st.error("본인? ???????습?다.")
                else:
                    delete_user(del_id)
                    st.success("?? ?료")
                    st.rerun()

        with st.expander("? ?위?문 ?인 ?벤???정 ??어"):
            event_cfg = get_event_settings()
            
            new_active = st.checkbox("?벤???성????", value=event_cfg["active"], key="admin_event_active")
            new_title = st.text_input("?벤???목", value=event_cfg["title"], key="admin_event_title")
            new_desc = st.text_area("?벤???용/?명", value=event_cfg["desc"], key="admin_event_desc")
            
            try:
                default_deadline_date = datetime.datetime.strptime(event_cfg["deadline"], "%Y-%m-%d").date()
            except Exception:
                default_deadline_date = datetime.date(2026, 7, 30)
            new_deadline_date = st.date_input("?벤??종료??, value=default_deadline_date, key="admin_event_deadline")
            new_deadline_str = str(new_deadline_date)
            
            new_discount = st.number_input("?인 금액 (??", min_value=0, max_value=500000, value=event_cfg["discount"], step=5000, key="admin_event_discount")
            
            if st.button("?벤???정 ???, use_container_width=True):
                conn = sqlite3.connect('users.db')
                c = conn.cursor()
                try:
                    c.execute("UPDATE event_settings SET event_active=?, event_title=?, event_desc=?, event_deadline=?, event_discount=? WHERE id=1",
                              (1 if new_active else 0, new_title, new_desc, new_deadline_str, int(new_discount)))
                    conn.commit()
                    st.success("? ?벤???정???공?으???되?습?다!")
                    st.rerun()
                except Exception as e:
                    st.error(f"?정 ????패: {e}")
                finally:
                    conn.close()

        st.divider()
    
    # -------------------------------------------------------------------------
    # [?정] 관리자???단 ???동 (Tab 1: 분석, Tab 2: ?문지 ?작)
    # ?반 ?용?에게는 Tab 1 ?면(분석)?직접 ?일 ?출?킵?다.
    # -------------------------------------------------------------------------
    if st.session_state.get('admin_mode', False) and st.session_state.get('user_role') == 'admin':
        st.stop()
    main_tab1, main_tab_coding, main_tab2, main_tab3, main_tab_service = st.tabs([
        _("?? ?로??분석", "Upload & Analyze"), 
        _("?이???력 ?식 만들?, "Create Data Entry Template"), 
        _("?문 배포", "Deploy Survey"), 
        _("?답 ?황", "Responses"),
        _("?비???내", "Service Info")
    ], default=_("?? ?로??분석", "Upload & Analyze"))
        
    with main_tab1:
        tab1_main_col, tab1_settings_col = st.columns([3.0, 1.1], gap="large")
        with tab1_settings_col:
            ahp_method, mean_method, cr_threshold, max_iter_val, learning_rate = render_ahp_analysis_settings()
        tab1_main_col.__enter__()
        # 빠른 ?작 ?션??AHP 분석?구 ???? 최상?에 배치

        st.header(_("빠른 ?작", "Quick Start"))
        st.info(_("?반 AHP ?:blue[**?? AHP**] 분석??지?합?다. ?? ?로????가중치 ?출, ????CR) ?동 보정, 그룹 집계까? ??번에 ?료?니??",
                  "Supports both Traditional and :blue[**Fuzzy AHP**] analysis. Upload Excel ??individual weights, automatic CR correction, and group aggregation in one step."))
            
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
    
        # 3계층 ?플 ?이?? 권한???라 분기
        # - ?식/관리자: Mock_3Tier_Full.xlsx (100?? ?제 분석 가??
        # - 무료/비로그인: create_sample_excel_v3() (3?? 3???한 ?과)
        _role_now = st.session_state.get('user_role', None)
        _is_full_user = (_role_now in ('admin', 'official'))
        if _is_full_user:
            try:
                with open("Mock_3Tier_Full.xlsx", "rb") as f:
                    sample_excel_v3 = f.read()
                _v3_label = _("? 3계층 ?플 ?이??, "? 3-Tier Sample Data")
                _v3_filename = "Mock_3Tier_Full.xlsx"
            except Exception:
                sample_excel_v3 = create_sample_excel_v3()
                _v3_label = _("? 3계층 ?플 ?이??, "? 3-Tier Sample Data")
                _v3_filename = _("AHP_3Tier_Sample.xlsx", "AHP_3Tier_Sample.xlsx")
        else:
            sample_excel_v3 = create_sample_excel_v3()   # 3????무료 3???한 ?과
            _v3_label = _("? 3계층 ?플 ?이??, "? 3-Tier Sample Data")
            _v3_filename = _("AHP_3Tier_Sample.xlsx", "AHP_3Tier_Sample.xlsx")
            
        # 모든 ?용?에?2계층·3계층 ?플 ?이??+ 결과 ?시 버튼 4??시
        col_btn1, col_btn2, col_btn3, col_btn4 = st.columns(4)
        with col_btn1:
            st.download_button(
                label=_("? 2계층 ?플 ?이??, "? 2-Tier Sample Data"),
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
                label=_("? ?반 AHP 분석 결과(?시)", "? Traditional AHP Report (Example)"),
                data=tahp_data if tahp_data else b"",
                file_name=_("E_TAHP_Result.xlsx", "E_TAHP_Result.xlsx") if is_en else _("K_TAHP_Result.xlsx", "K_TAHP_Result.xlsx"),
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                disabled=(not tahp_data)
            )
        with col_btn4:
            st.download_button(
                label=_("? ?? AHP 분석 결과(?시)", "? Fuzzy AHP Report (Example)"),
                data=fahp_data if fahp_data else b"",
                file_name=_("E_FAHP_Result.xlsx", "E_FAHP_Result.xlsx") if is_en else _("K_FAHP_Result.xlsx", "K_FAHP_Result.xlsx"),
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                disabled=(not fahp_data)
            )
        
        st.subheader(_("1. ?이???로???분석", "1. Data Upload & Analysis"))
        
        if st.session_state.get('user_role') == 'admin':
            st.info(_("**?합 계층(Mixed-Tier) ?? 분석 ?내**: 3계층 코딩 ?? ?식???로?할 ?? ?정 ????????분??? ?트가 ?거???답??비워???더?도 ?스?이 ?당 ?????동?로 2계층 가중치?간주?여 ?러 ?이 분석???행?니??", "**Mixed-Tier Excel Analysis Guide**: When uploading a 3-tier Excel template, if there are no sub-sub-criteria evaluation sheets for specific items or the responses are blank, the system automatically considers them as 2-tier weights and performs the analysis without errors."))

        # ?이???스 ?택 추?
        data_source = st.radio(
            _("분석 ?이???스 ?택", "Select Analysis Data Source"),
            [_("? ?? ?일 직접 ?로??, "Upload Excel File"), _("? 배포???라???문 ?이???동", "Link Online Survey Data")],
            horizontal=True
        )
    
        # [?규 추?] ?구?계 빈도/비율 분석???퍼 ?수
        def generate_demographics_summary(demo_df):
            if demo_df is None or demo_df.empty:
                return None
            
            working_df = demo_df.copy()
            
            def _clean_id(x):
                s = str(x).strip()
                if s.endswith(".0"):
                    s = s[:-2]
                return s
            
            # 1. 최종 ?료 ?답??ID)??터?(미완??탈???외)
            completed_ids = set()
            if "ahp_df_main" in st.session_state and st.session_state["ahp_df_main"] is not None:
                if "ID" in st.session_state["ahp_df_main"].columns:
                    completed_ids = set(st.session_state["ahp_df_main"]["ID"].apply(_clean_id))
            elif "live_df" in st.session_state and st.session_state["live_df"] is not None:
                if "ID" in st.session_state["live_df"].columns:
                    completed_ids = set(st.session_state["live_df"]["ID"].apply(_clean_id))
            
            id_col = None
            for c in working_df.columns:
                if str(c).strip().lower() == "id":
                    id_col = c
                    break

            if completed_ids and id_col:
                working_df = working_df[working_df[id_col].apply(_clean_id).isin(completed_ids)].copy()

            if working_df.empty:
                return None

            # 불필?한 ?스?용 컬럼 ?외
            exclude_keywords = ["id", "type", "?전?위", "????, "?락?, "?출?간"]
            target_cols = []
            for col in working_df.columns:
                col_lower = str(col).lower()
                if not any(ex in col_lower for ex in exclude_keywords):
                    target_cols.append(col)
            
            if not target_cols:
                return None
                
            summary_rows = []
            for col in target_cols:
                col_str = str(col).strip()
                col_data = working_df[col]
                
                # 2. 질문 문구가 ?답 보기??어가거나 ?값인 ?? ?거 (?효 ?답??터?
                valid_items = []
                for val in col_data:
                    if pd.isna(val):
                        continue
                    val_str = str(val).strip()
                    if not val_str or val_str == "미응??N/A)":
                        continue
                    # 질문 ?더 ?스?? ?일?거???? ?함??기본??스???외
                    if val_str == col_str or (len(val_str) >= 8 and (val_str in col_str or col_str in val_str)):
                        continue
                    valid_items.append(val_str)
                
                if not valid_items:
                    continue
                
                series_valid = pd.Series(valid_items)
                counts = series_valid.value_counts()
                total = len(valid_items)
                for val, count in counts.items():
                    pct = (count / total) * 100 if total > 0 else 0
                    summary_rows.append({
                        "?구?계 ?? (Demographic Field)": col,
                        "?답 보기 (Value)": val,
                        "빈도??(Frequency)": count,
                        "비율 (Percentage, %)": round(pct, 1)
                    })
                    
            if summary_rows:
                return pd.DataFrame(summary_rows)
            return None

        def preprocess_uploaded_df(df):
            # 1. ?출?간/??스?프 ?거
            drop_cols = [c for c in df.columns if str(c).strip().lower() in ["??스?프", "?출?간", "timestamp"]]
            if drop_cols:
                df = df.drop(columns=drop_cols)
            # ?중 ?구?계(Type 1, Type 2...)?????여 ?후 ?택??분석??가?하?록 ??
            return df
            
        df_main = None
        sub_dfs = {}
        sheet_names = []
        filename_base = "AHP_Analysis"
    
        if data_source == _("? ?? ?일 직접 ?로??, "Upload Excel File"):
            uploaded_file = st.file_uploader(_("?성???? ?일 ?로??(.xlsx)", "Upload completed Excel file (.xlsx)"), type=['xlsx', 'xls'])
            if uploaded_file:
                try:
                    excel_obj = pd.ExcelFile(uploaded_file)
                    sheet_names = excel_obj.sheet_names
                    df_main = pd.read_excel(uploaded_file, sheet_name=sheet_names[0])
                    df_main = preprocess_uploaded_df(df_main)
                    
                    # [?규] Basic ?금???본???한 (최? 10?본?로 ?라?싱?여 분석 ?용)
                    if st.session_state.get('plan_type') == 'Basic' and len(df_main) > 10:
                        df_main = df_main.head(10)
                        st.warning(_("?️ 베이??금?는 ?? ?로????최? 10?본까??분석?????습?다. 처음 10??본?분석???용?니??",
                                     "?️ Basic users can only analyze up to 10 samples. Only the first 10 samples will be analyzed."))
                    
                    if "Type" not in df_main.columns and len(df_main.columns) > 1:
                        col1 = df_main.columns[1]
                        if "_" not in col1 and col1 not in ["ID", "?출?간"]:
                            df_main.rename(columns={col1: "Type"}, inplace=True)
                            
                    # 3계층 ?별 로직 (df_main 컬럼?서 _ ?함??것으??분류 ?인 ?출)
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
                        # [추?] ?라???문 배포 ?식 ?????본/?구?계 ?이???트 ?동 무시 (?? ?구?계??별도 ???
                        sn_lower = sn.lower().strip()
                        if sn_lower in ignore_sheets:
                            if "demographic" in sn_lower:
                                demo_df = pd.read_excel(uploaded_file, sheet_name=sn)
                                demo_df = preprocess_uploaded_df(demo_df)
                                if st.session_state.get('plan_type') == 'Basic' and len(demo_df) > 10:
                                    demo_df = demo_df.head(10)
                                st.session_state["demo_df"] = demo_df
                            continue
                            
                        df_sheet = pd.read_excel(uploaded_file, sheet_name=sn)
                        df_sheet = preprocess_uploaded_df(df_sheet)
                        if st.session_state.get('plan_type') == 'Basic' and len(df_sheet) > 10:
                            df_sheet = df_sheet.head(10)
                            
                        if "Type" not in df_sheet.columns and len(df_sheet.columns) > 1:
                            col1 = df_sheet.columns[1]
                            if "_" not in col1 and col1 not in ["ID", "?출?간"]:
                                df_sheet.rename(columns={col1: "Type"}, inplace=True)
                                
                        # ?전???트?safe_sheet_name)???해 ??분이 ?치?는지 ?인
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
                    st.error(f"?? ?일 로드 ?패: {e}")
        else:
            # 배포???라???문 ?이???동
            if st.session_state.user_id is None:
                st.warning(_(" ?라???문 ?이???동 분석? ?원 ?용 기능?니?? 로그?해 주세??", " Online survey integration is available for members. Please log in."))
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
                    st.warning(_("배포???라???문???습?다.", "No deployed online surveys found."))
                else:
                    survey_options = {f"{row[1]} ({row[2]})": row[0] for row in admin_surveys}
                
                    default_idx = 0
                    if st.session_state.get("selected_survey_for_analysis") in survey_options.values():
                        default_idx = list(survey_options.values()).index(st.session_state.get("selected_survey_for_analysis"))
                
                    selected_survey_label = st.selectbox(
                        _("분석???라???문 ?택", "Select Online Survey for Analysis"),
                        list(survey_options.keys()),
                        index=default_idx
                    )
                    selected_sheet_id = survey_options[selected_survey_label]
                    filename_base = f"Survey_{selected_sheet_id[:6]}"
                
                    if st.button(_("? 구? ?트?서 ?시??답 가?오?, "? Fetch Live Responses from Google Sheet"), type="primary", use_container_width=True):
                        import survey_manager; survey_manager.log_user_action(st.session_state.get("user_id") or "Guest", "?시??답 가?오?)
                        st.session_state["selected_survey_for_analysis"] = selected_sheet_id
                        from survey_manager import load_survey_metadata, get_survey_gspread_client
                        with st.spinner(_("구? ?트?서 ?문 ?이???구조?가?오???..", "Fetching survey structure and responses...")):
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
                                            if "_" not in col1 and col1 not in ["ID", "?출?간"]:
                                                raw_df.rename(columns={col1: "Type"}, inplace=True)
                                                
                                        # [?규] ?용???급???른 ?본 ???한 (무료 ?용?? 최? 3?본)
                                        if st.session_state.get('user_role') == 'free' and len(raw_df) > 3:
                                            raw_df = raw_df.head(5)
                                            st.warning(_("?️ 무료 ?용?는 ?라???문 ?동 ??최? 3?본까??분석?????습?다. 처음 ?수??3??????답?분석???용?니??", "?️ Free users can only analyze up to 3 samples. Only the first 3 responses will be analyzed."))
                                    
                                        # [?규] Basic ?금???본 ???한 (최? 10?본?로 ?라?싱?여 분석 ?용)
                                        if st.session_state.get('plan_type') == 'Basic' and len(raw_df) > 10:
                                            raw_df = raw_df.head(10)
                                            st.warning(_("?️ 베이??금?는 ?라???문 ?동 ??최? 10?본까??분석?????습?다. 처음 ?수??10??????답?분석???용?니??",
                                                         "?️ Basic users can only analyze up to 10 samples. Only the first 10 responses will be analyzed."))
                                    
                                        for col in raw_df.columns:
                                            if col not in ["ID", "Type", "?출?간", "?????락?]:
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
                                            
                                        # [?규] 3계층 모델??경우 ?분?sub_subs) ?이?프?임 ?싱
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
                                        st.success(_(f"??구? ?트?서 ?{len(raw_df)}건의 ?답 ?이?? ?공?으?가?왔?니??", f"??Successfully fetched {len(raw_df)} responses!"))
                                    else:
                                        st.warning(_("가?올 ?문 ?답 ?이?? ?트??존재?? ?습?다 (?더?존재).", "No survey responses found in the sheet."))
                                except Exception as g_err:
                                    st.error(f"구? ?트 로드 ?패: {g_err}")
                            else:
                                st.error(_("?문 메??이???는 구? API ?라?언?? 로드?????습?다.", "Failed to load survey metadata or Google client."))
                
                    if "ahp_df_main" in st.session_state:
                        df_main = st.session_state["ahp_df_main"]
                        sub_dfs = st.session_state["ahp_sub_dfs"]
                        sheet_names = st.session_state["ahp_sheet_names"]
                        st.info(_("구? ?트?서 로드???시??이??분석 모드?니?? (???이?? 가?오?면 ??버튼???릭??주세??", "Live data analysis mode. Click the button above to refresh data."))

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
                            message = _("???용 기간??만료?었?니??", "??Your subscription period has expired.")
                        

                else: 
                    rows_ok = True
                    if data_source == _("? ?? ?일 직접 ?로??, "Upload Excel File"):
                        for sn in sheet_names:
                            if len(pd.read_excel(uploaded_file, sheet_name=sn)) > 3:
                                rows_ok = False
                                break
                    else:
                        if len(df_main) > 3:
                            rows_ok = False
                        for sn, sdf in sub_dfs.items():
                            if len(sdf) > 3:
                                rows_ok = False
                                break
                    if rows_ok: permission_granted = True
                    else: message = _(f"??**무료?용??*???트??최? 3??본까??분석 가?합?다. (?재: {len(df_main)}??본)",
                                     f"??**Free Users** can only analyze up to 3 samples per sheet. (Current: {len(df_main)} samples)")
            
                if permission_granted:
                    tier = get_current_tier()
                    try:
                        if data_source == _("? ?? ?일 직접 ?로??, "Upload Excel File"):
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
                            with st.spinner(_("3계층(?분??함) AHP 종합 분석 ?행 ?..", "Performing 3-Tier AHP...")):
                                from ahp_utils_v3 import run_ahp_analysis_v3
                                sub_sub_dfs = st.session_state.get("ahp_sub_sub_dfs", {})
                                
                                # ?구?계 ?약??성?여 ?달
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
                                if data_source == _("? ?? ?일 직접 ?로??, "Upload Excel File") and uploaded_file is not None:
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

                            st.success(_("??3계층 AHP 분석???공?으??료?었?니??", "??3-Tier AHP Analysis successfully completed!"))
                            if st.session_state.get('plan_type') == 'Basic':
                                st.info(_("**Basic ?한**: ?본 10개로 ?한?니?? Standard ?상?로 ?그?이?하?요.",
                                          "? **Basic Limit**: Limited to 10 samples. Please upgrade to Standard or higher."))
                            st.caption(_("?️ ?로고침 ??결과가 리셋?니?? 결과 ?운로드 ????반드????하?요.",
                                         "?️ Results reset on refresh. Download via the Results tab."))

                            # --- 3계층 ?용 5???UI ---
                            v3_unique_groups = ui_data_v3.get("unique_groups", [])
                            v3_comparison_df  = ui_data_v3.get("comparison_df", pd.DataFrame())
                            v3_anova_df       = ui_data_v3.get("anova_df", pd.DataFrame())
                            v3_group_full_dfs = ui_data_v3.get("group_full_dfs", {})
                            v3_indiv_df       = ui_data_v3.get("indiv_df", pd.DataFrame())
                            v3_main_factors   = ui_data_v3.get("main_factors", [])

                            tab3v1, tab3v2, tab3v3, tab3v4, tab3v5 = st.tabs([
                                _("종합 분석 (Global)", "Global Comprehensive Analysis"),
                                _("그룹?분석", "Group Analysis"),
                                _("?계 검??(ANOVA)", "Statistical Test (ANOVA)"),
                                _("?각???터", "Visualization Center"),
                                _("결과 ?운로드", "Download Results")
                            ])

                            # ??? Tab 1: 종합 분석 ????????????????????????????????????????????
                            with tab3v1:
                                st.subheader(_(" 3계층 종합 중요????위", " 3-Tier Global Weights & Rankings"))
                                if is_english:
                                    _disp_v3 = final_df_v3.rename(columns={
                                        "?분류": "Main Criteria",    "?분류 가중치": "Main Weight",
                                        "중분?: "Sub-Criteria",     "중분?가중치": "Sub Weight",
                                        "?분?: "Sub-sub-Criteria", "?분?가중치": "Sub-sub Weight",
                                        "CR(?분류)": "CR(Main)",     "CI(?분류)": "CI(Main)",
                                        "CR(중분?": "CR(Sub)",      "CI(중분?": "CI(Sub)",
                                        "CR(?분?": "CR(Sub-sub)",  "CI(?분?": "CI(Sub-sub)"
                                    })
                                else:
                                    _disp_v3 = final_df_v3
                                st.dataframe(_disp_v3.style.format(precision=4), use_container_width=True)

                                st.markdown(_("---\n####  ?분류??분??? 글로벌 가중치",
                                              "---\n#### ? Sub-sub-Criteria Global Weights by Main Criteria"))
                                _non_dummy_v3 = final_df_v3[~final_df_v3["?분?].str.endswith("_?일??", na=False)].copy()
                                if _non_dummy_v3.empty:
                                    _non_dummy_v3 = final_df_v3.copy()
                                for _mf_v3 in v3_main_factors:
                                    _mf_subset = _non_dummy_v3[_non_dummy_v3["?분류"] == _mf_v3]
                                    if _mf_subset.empty:
                                        continue
                                    _mf_chart = _mf_subset.sort_values("Global Weight", ascending=True).copy()
                                    if is_english:
                                        _mf_chart = _mf_chart.rename(columns={"?분?: "Sub-sub-Criteria"})
                                        _y_col_v3 = "Sub-sub-Criteria"
                                    else:
                                        _y_col_v3 = "?분?
                                    _fig_v3_bar = px.bar(
                                        _mf_chart, y=_y_col_v3, x="Global Weight",
                                        orientation="h", text_auto=".4f",
                                        title=_(f"[{_mf_v3}] ?분????글로벌 가중치", f"[{_mf_v3}] Sub-sub-Criteria Global Weights"),
                                        color_discrete_sequence=["#4F81BD"]
                                    )
                                    _fig_v3_bar.update_layout(height=max(300, len(_mf_chart)*40+80), margin=dict(l=0,r=10,t=40,b=20))
                                    st.plotly_chart(_fig_v3_bar, use_container_width=True)

                            # ??? Tab 2: 그룹?분석 ??????????????????????????????????????????
                            with tab3v2:
                                st.markdown(_("#### 그룹??분??? 글로벌 가중치 비교",
                                              "#### Sub-sub-Criteria Global Weight Comparison by Group"))
                                if not v3_comparison_df.empty:
                                    if is_english:
                                        _disp_comp_v3 = v3_comparison_df.copy()
                                        _disp_comp_v3.rename(columns={
                                            "?분류": "Main Criteria", "중분?: "Sub-Criteria", "?분?: "Sub-sub-Criteria",
                                            "종합?균(Overall)": "Overall Avg", "F-?: "F-Value",
                                            "?의??: "Significance", "?후검??Tukey HSD)": "Post-Hoc (Tukey HSD)"
                                        }, inplace=True)
                                        if "Significance" in _disp_comp_v3.columns:
                                            _disp_comp_v3["Significance"] = _disp_comp_v3["Significance"].map(
                                                {"?의??: "Significant", "?의?? ?음": "Not Significant"}).fillna(_disp_comp_v3["Significance"])
                                    else:
                                        _disp_comp_v3 = v3_comparison_df
                                    st.dataframe(_disp_comp_v3.style.format(precision=4), use_container_width=True)
                                else:
                                    st.info(_("그룹?비교 ?이?? ?습?다.", "No group comparison data available."))

                                if len(v3_unique_groups) >= 2 and v3_group_full_dfs:
                                    st.markdown(_("---\n#### 그룹??분류 가중치 비교",
                                                  "---\n#### Main Criteria Weight Comparison by Group"))
                                    _grp_main_rows = []
                                    for _grp_v3 in v3_unique_groups:
                                        if _grp_v3 not in v3_group_full_dfs:
                                            continue
                                        _g_df_v3 = v3_group_full_dfs[_grp_v3]
                                        for _mf_v3b in v3_main_factors:
                                            _mf_sub_b = _g_df_v3[_g_df_v3["?분류"] == _mf_v3b]
                                            if not _mf_sub_b.empty:
                                                _grp_main_rows.append({
                                                    _("그룹","Group"): _grp_v3,
                                                    _("?분류","Main Criteria"): _mf_v3b,
                                                    "Weight": float(_mf_sub_b.iloc[0]["?분류 가중치"])
                                                })
                                    if _grp_main_rows:
                                        _grp_main_chart_df = pd.DataFrame(_grp_main_rows)
                                        _fig_grp_main = px.bar(
                                            _grp_main_chart_df,
                                            x=_("?분류","Main Criteria"), y="Weight",
                                            color=_("그룹","Group"), barmode="group", text_auto=".4f",
                                            title=_("그룹??분류 가중치 비교", "Main Criteria Weight Comparison by Group")
                                        )
                                        st.plotly_chart(_fig_grp_main, use_container_width=True)

                            # ??? Tab 3: ANOVA ?????????????????????????????????????????????????
                            with tab3v3:
                                st.markdown(_("#### 집단 ??의??분석 (3계층 기?)",
                                              "#### Significance Analysis Between Groups (3-Tier Level)"))
                                if not v3_anova_df.empty:
                                    if is_english:
                                        _disp_anova_v3 = v3_anova_df.copy()
                                        _disp_anova_v3.rename(columns={
                                            "?인": "Factor/Criteria", "F-?: "F-Value",
                                            "?의??: "Significance", "?후검??Tukey HSD)": "Post-Hoc (Tukey HSD)"
                                        }, inplace=True)
                                        if "Significance" in _disp_anova_v3.columns:
                                            _disp_anova_v3["Significance"] = _disp_anova_v3["Significance"].map(
                                                {"?의??: "Significant", "?의?? ?음": "Not Significant"}).fillna(_disp_anova_v3["Significance"])
                                        def _translate_ph_v3(v):
                                            if not isinstance(v, str): return v
                                            v = v.replace("?문가","Expert").replace("?반","General").replace("공무??,"Public Official")
                                            v = v.replace(" 차이 ?음"," (Diff exists)")
                                            v = v.replace("집단 ?구체??차이 발견 못함","No significant pairwise difference found")
                                            v = v.replace("계산 ?류","Calculation Error")
                                            return v
                                        if "Post-Hoc (Tukey HSD)" in _disp_anova_v3.columns:
                                            _disp_anova_v3["Post-Hoc (Tukey HSD)"] = _disp_anova_v3["Post-Hoc (Tukey HSD)"].apply(_translate_ph_v3)
                                    else:
                                        _disp_anova_v3 = v3_anova_df
                                    st.dataframe(_disp_anova_v3.style.format(precision=5), use_container_width=True)

                                    _sig_col_v3 = "Significance" if is_english else "?의??
                                    _sig_val_v3 = "Significant" if is_english else "?의??
                                    if _sig_col_v3 in _disp_anova_v3.columns:
                                        _sig_items_v3 = _disp_anova_v3[_disp_anova_v3[_sig_col_v3] == _sig_val_v3]
                                        if not _sig_items_v3.empty:
                                            _fcol_v3 = "Factor/Criteria" if is_english else "?인"
                                            _snames = ", ".join(_sig_items_v3[_fcol_v3].tolist())
                                            st.success(_(f"???의??차이 발견 ??: {_snames}", f"??Statistically significant factors: {_snames}"))
                                        else:
                                            st.info(_("모든 ???서 그룹 ??의??차이가 ?습?다.", "No statistically significant group differences found."))
                                else:
                                    st.info(_("?계 검?을 ?해 2??상??그룹 ?이?? ?요?니??",
                                              "At least 2 group datasets are required for ANOVA."))

                            # ??? Tab 4: ?각???터 ??????????????????????????????????????????
                            with tab3v4:
                                st.markdown(_("####  3계층 AHP ?각???터", "####  3-Tier AHP Visualization Center"))

                                st.markdown(_("**??글로벌 가중치 ?위 버블 차트 (버블 ?기 = 중분?가중치, ??= ?분류)**",
                                              "**??Global Weight Bubble Chart (bubble size = Sub weight, color = Main Criteria)**"))
                                _nd_v3 = final_df_v3[~final_df_v3["?분?].str.endswith("_?일??", na=False)].copy()
                                if _nd_v3.empty:
                                    _nd_v3 = final_df_v3.copy()
                                    _item_col_bub = "중분?
                                else:
                                    _item_col_bub = "?분?
                                _bubble_df = _nd_v3.copy()
                                if "Global Rank" not in _bubble_df.columns:
                                    _bubble_df["Global Rank"] = _bubble_df["Global Weight"].rank(ascending=False, method="min").astype(int)
                                # 버블 ?기: 중분?가중치 기반 (최소 ?기 보장)
                                _bubble_df["_bubble_size"] = (_bubble_df["중분?가중치"] * 100).clip(lower=3)
                                if is_english:
                                    _bubble_df_disp = _bubble_df.rename(columns={
                                        "?분?: "Sub-sub-Criteria", "?분류": "Main Criteria",
                                        "중분?: "Sub-Criteria", "중분?가중치": "Sub Weight"
                                    })
                                    _label_col_bub = "Sub-sub-Criteria" if _item_col_bub == "?분? else "Sub-Criteria"
                                    _color_bub = "Main Criteria"
                                    _hover_sub_bub = "Sub-Criteria"
                                    _hover_subw_bub = "Sub Weight"
                                else:
                                    _bubble_df_disp = _bubble_df
                                    _label_col_bub = _item_col_bub
                                    _color_bub = "?분류"
                                    _hover_sub_bub = "중분?
                                    _hover_subw_bub = "중분?가중치"
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
                                    title=_("?분?글로벌 가중치 버블 차트 (버블???수?중분?비중 ?음, ?로 갈수?글로벌 가중치 ?음)",
                                            "Sub-sub-Criteria Global Weight Bubble Chart (larger = higher sub weight, higher = higher global weight)"),
                                    color_discrete_sequence=px.colors.qualitative.Set2,
                                    size_max=55
                                )
                                _fig_bub.update_traces(textposition="top center", textfont_size=10)
                                _fig_bub.update_xaxes(
                                    title=_("종합 ?위 (1??= 가??중요)", "Global Rank (1 = Most Important)"),
                                    dtick=1, autorange="reversed"
                                )
                                _fig_bub.update_yaxes(title=_("글로벌 가중치", "Global Weight"))
                                _fig_bub.update_layout(height=560, legend_title_text=_color_bub)
                                st.plotly_chart(_fig_bub, use_container_width=True)

                                st.markdown(_("**??계층?????비율(CR) 분포 ??바이?린 ?롯**",
                                              "**??Consistency Ratio (CR) Distribution by Tier ??Violin Plot**"))
                                st.caption(_("계층???택?면 ?당 ?? ?답?들??CR 분포??시?니?? 바이?린 ??= 밀?? ?? 박스 = 중앙값·사분위?? ??= 개별 ?답??,
                                             "Select a tier to view respondent CR distribution. Width = density, box = median/IQR, dots = individual respondents"))

                                _vio_main_df   = ui_data_v3.get("main_results_df", pd.DataFrame())
                                _vio_sub_stor  = ui_data_v3.get("sub_results_storage", {})
                                _vio_ss_stor   = ui_data_v3.get("sub_sub_results_storage", {})
                                _vio_mf_list   = ui_data_v3.get("main_factors", [])

                                _tier_options_ko = ["?분류 (Main)", "중분?(Sub)", "?분?(Sub-sub)"]
                                _tier_options_en = ["Main Criteria", "Sub-Criteria", "Sub-sub-Criteria"]
                                _tier_opts = _tier_options_en if is_english else _tier_options_ko
                                _sel_tier = st.selectbox(
                                    _("? ?시??계층 ?택", "? Select Tier to Display"),
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

                                    # ?? ?택: ?분류 ?????????????????????????????????
                                    if _sel_tier in [_tier_opts[0]]:
                                        if not _vio_main_df.empty and "Final_CR" in _vio_main_df.columns:
                                            _main_cr = _vio_main_df["Final_CR"].dropna().tolist()
                                            _xlbl = _("?분류", "Main Criteria")
                                            _fig_vio.add_trace(_go_vio.Violin(
                                                y=_main_cr, x=[_xlbl]*len(_main_cr),
                                                name=_xlbl, box_visible=True, meanline_visible=True,
                                                points="all", jitter=0.35, pointpos=0,
                                                line_color=_vio_line_pal[0], fillcolor=_vio_palette[0],
                                                opacity=0.75,
                                                hovertemplate="<b>" + _xlbl + "</b><br>CR: %{y:.4f}<extra></extra>",
                                                showlegend=True
                                            ))
                                        _vio_xaxis_title = _("?분류", "Main Criteria")
                                        _vio_legend_title = _("?분류", "Main Criteria")

                                    # ?? ?택: 중분??????????????????????????????????
                                    elif _sel_tier in [_tier_opts[1]]:
                                        # ?분류별로 ?나??바이?린 (?당 ?분류 중분?비교 ??CR)
                                        for _mf in _vio_mf_list:
                                            _sinfo = _vio_sub_stor.get(_mf, {})
                                            _sdf = _sinfo.get("df", None)
                                            if _sdf is None or _sdf.empty or "Final_CR" not in _sdf.columns:
                                                continue
                                            _cr_vals = _sdf["Final_CR"].dropna().tolist()
                                            if len(_cr_vals) < 2:
                                                continue
                                            _xlbl = _(f"중분?{_mf})", f"Sub({_mf})")
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
                                        _vio_xaxis_title = _("?분류 (중분?비교 CR)", "Main Criteria (Sub-Criteria Comparison CR)")
                                        _vio_legend_title = _("중분?, "Sub-Criteria")

                                    # ?? ?택: ?분??????????????????????????????????
                                    else:
                                        # 중분류별??나??바이?린 (?당 중분??분?비교 ??CR)
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
                                                _xlbl = _(f"?분?{_sf})", f"Sub-sub({_sf})")
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
                                        _vio_xaxis_title = _("중분?(?분?비교 CR)", "Sub-Criteria (Sub-sub Comparison CR)")
                                        _vio_legend_title = _("?분?, "Sub-sub-Criteria")

                                    if len(_fig_vio.data) == 0:
                                        st.info(_("?택??계층??CR ?이?? ?거???답 ?? 부족합?다.",
                                                  "No CR data available for the selected tier or insufficient responses."))
                                    else:
                                        _fig_vio.add_hline(
                                            y=0.1, line_dash="dash", line_color="red",
                                            annotation_text=_("CR ?계?(0.1)", "CR Threshold (0.1)"),
                                            annotation_position="top right"
                                        )
                                        _fig_vio.update_layout(
                                            title=_(
                                                f"바이?린?롯 CR ??{_sel_tier}",
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
                                    st.warning(_(f"바이?린 ?롯 ?성 ?패: {_e_vio}", f"Violin plot generation failed: {_e_vio}"))

                                if len(v3_unique_groups) >= 2 and v3_group_full_dfs:
                                    st.markdown(_("**??그룹??분류 중요???이??차트**",
                                                  "**??Main Criteria Importance Radar Chart by Group**"))
                                    _radar_rows = []
                                    for _grp_rd in v3_unique_groups:
                                        if _grp_rd not in v3_group_full_dfs: continue
                                        _gdf_rd = v3_group_full_dfs[_grp_rd]
                                        for _mf_rd in v3_main_factors:
                                            _mf_rd_sub = _gdf_rd[_gdf_rd["?분류"]==_mf_rd]
                                            _w_rd = float(_mf_rd_sub.iloc[0]["?분류 가중치"]) if not _mf_rd_sub.empty else 0.0
                                            _lbl_rd = str(_grp_rd).replace("?문가","Expert").replace("?반","General").replace("공무??,"Public Official") if is_english else _grp_rd
                                            _radar_rows.append({_("그룹","Group"): _lbl_rd, _("??","Factor"): _mf_rd, "Weight": _w_rd})
                                    if _radar_rows:
                                        _radar_df_v3 = pd.DataFrame(_radar_rows)
                                        _cats_rd = _radar_df_v3[_("??","Factor")].unique().tolist()
                                        _fig_rd = go.Figure()
                                        _colors_rd = ["#4F81BD","#C0504D","#9BBB59","#8064A2","#F79646"]
                                        for _i_rd, _grp_rdn in enumerate(_radar_df_v3[_("그룹","Group")].unique()):
                                            _g_rd = _radar_df_v3[_radar_df_v3[_("그룹","Group")]==_grp_rdn]
                                            _vals_rd = [_g_rd[_g_rd[_("??","Factor")]==c]["Weight"].values[0] if len(_g_rd[_g_rd[_("??","Factor")]==c])>0 else 0 for c in _cats_rd]
                                            _vals_cl = _vals_rd + [_vals_rd[0]]
                                            _cats_cl = _cats_rd + [_cats_rd[0]]
                                            _fig_rd.add_trace(go.Scatterpolar(r=_vals_cl, theta=_cats_cl, fill="toself", name=_grp_rdn, line_color=_colors_rd[_i_rd % len(_colors_rd)], opacity=0.7))
                                        _fig_rd.update_layout(
                                            polar=dict(radialaxis=dict(visible=True, range=[0, max(0.01, _radar_df_v3["Weight"].max()*1.2)])),
                                            showlegend=True,
                                            title=_("그룹??분류 중요???턴", "Main Criteria Importance Pattern by Group"),
                                            height=450
                                        )
                                        st.plotly_chart(_fig_rd, use_container_width=True)

                            # ??? Tab 5: 결과 ?운로드 ????????????????????????????????????????
                            with tab3v5:
                                st.markdown(_("###  3계층 AHP 종합분석 결과 ?운로드",
                                              "### ? Download 3-Tier AHP Comprehensive Analysis Results"))
                                st.download_button(
                                    label=_("? 3계층 AHP 종합분석 결과 ?운로드 (.xlsx)", "? Download 3-Tier AHP Results (.xlsx)"),
                                    data=output_res_v3,
                                    file_name="3Tier_AHP_Result.xlsx",
                                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                    type="primary",
                                    use_container_width=True
                                )
                                st.info(_("? ?? ?일?는 종합분석, 그룹비교, 계층??세?렬, CR 분포 ???체 분석 결과가 ?함?니??",
                                          "? The Excel file contains all results: comprehensive summary, group comparison, detailed matrices per tier, and CR distribution."))

                            # 3계층 처리 ?료 ??기존 2계층 UI ?킵
                            st.stop()
                        
                        with st.spinner(_("계층 분석 ?행 ?..", "Performing Analytic Hierarchy Process (AHP)...")):
                            # 1. 메인 ?트 분석 ?도
                            try:
                                main_results_df, main_factors, main_excluded, main_excluded_df = process_single_sheet(
                                    df_main, cr_threshold, max_iter_val, learning_rate, mean_method, ahp_method
                                )
                            except Exception as e:
                                st.error(_("??[메인 ?트] 분석 ??류가 발생?습?다.", "??Error occurred during [Main Criteria] analysis."))
                                with st.expander(_("? ?유 ??결 방법 보기", "? View Reason & Solution"), expanded=True):
                                    st.markdown(_(f"""
                                    **?인:** 메인 ?트???이??구조가 ?바르? ?거???을 ???는 ?효 ?이?? ?습?다. (Error: {e})
                                    **?결 방법:**
                                    1. ?????번째 ?트 ?름??`Main_Criteria`?? ?인?세??
                                    2. ID? Type ???음????비교 ?이?? ?바르게 ?력?었?? ?인?세??
                                    3. ??이 ?함?어 ?다??? ???시 ?도?세??
                                    """,
                                    f"""
                                    **Cause:** The structure of the main sheet is incorrect or contains no readable valid data. (Error: {e})
                                    **Solution:**
                                    1. Ensure that the first sheet name in Excel is `Main_Criteria`.
                                    2. Verify that pair-wise comparison data is correctly input after the 'ID' and 'Type' columns.
                                    3. If empty rows are included, delete them and try again.
                                    """))
                                st.stop()
    
                            # [방어 코드] 메인 결과 충분??체크
                            if main_results_df.empty or len(main_results_df) < 1:
                                st.error(_(f"?️ 분석 불?: 메인 기? ?효 ?답?? 부족합?다. (?재 {len(main_results_df)}?",
                                           f"?️ Cannot Analyze: Insufficient valid respondents for Main Criteria. (Current: {len(main_results_df)} respondents)"))
                                with st.expander(_("? ?유 ??결 방법 보기", "? View Reason & Solution"), expanded=True):
                                    st.markdown(_(f"""
                                    **?인:** 모든 ?답?의 ????비율(CR)???계?{cr_threshold})?초과?여 보정 ?에???렴?? 못했?니??
                                    **?결 방법:**
                                    1. ?쪽 ?이?바?서 **'????비율(CR) ?계?**??0.15 ?는 0.2??화??보세??
                                    2. **'보정 강도(Learning Rate)'**?0.7 ?상?로 ?여보세??
                                    3. **'최? 보정 반복 ?수'**?500?로 ?정?는지 ?인?세??
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

                            # 2. ?위 ?트 분석 ????
                            sub_results_storage = {}
                            total_excl_df_list = [main_excluded_df]
                        
                            is_single_sheet = (len(sheet_names) == 1)
                        
                            if is_single_sheet:
                                for parent_factor in main_factors:
                                    # 1?계 분석??경우 (?위 ?트가 ?음), 
                                    # ?위 가중치 1.0??가지???? ?이?? ?동?로 ?성?여 ?산??마칩?다.
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
                                    # ?분류 ??명과 ?치?는 ?트?찾기 (??문?? 공백 무시 ?31???한 고려)
                                    target_name = parent_factor.strip().lower()
                                    target_name_31 = parent_factor[:31].strip().lower()
                                
                                    matched_sheet_name = None
                                    for sn in sheet_names[1:]:
                                        sn_clean = sn.strip().lower()
                                        if sn_clean == target_name or sn_clean == target_name_31:
                                            matched_sheet_name = sn
                                            break
                                
                                    if matched_sheet_name is None:
                                        st.error(_(f"??[?? ?트: {parent_factor}] ?트?찾을 ???습?다.", f"??[Detailed Sheet: {parent_factor}] Sheet not found."))
                                        with st.expander(_("? ?유 ??결 방법 보기", "? View Reason & Solution"), expanded=True):
                                            st.markdown(_(f"""
                                            **?인:** 메인 기? ?트?서 ?출???분류 ?? **'{parent_factor}'**????하???? ?문 ?답 ?트가 ?? ?일 ?에 존재?? ?거???트 ?름???릅?다.
                                            **?결 방법:**
                                            1. ?로?한 ?? ?일 ?에 **'{parent_factor}'** (?는 31???내???분이 ?치?는 명칭)???트가 존재?는지 ?인?세??
                                            2. ?트 ?름???뒤 공백?나 ?탈???? '리드???감도'? '리드???민감??)가 ?는지 ?인?고 ?트명을 맞춰주세??
                                            """,
                                            f"""
                                            **Cause:** The detailed survey response sheet corresponding to the main criteria category **'{parent_factor}'** does not exist in the Excel file or has a different name.
                                            **Solution:**
                                            1. Check if a sheet named **'{parent_factor}'** (or a name matching the first 31 characters) exists in the uploaded Excel file.
                                            2. Ensure there are no leading/trailing spaces or spelling discrepancies (e.g., 'Lead Time Sensitivity' vs 'LeadTime Sensitivity') and align the sheet names.
                                            """))
                                        st.stop()
                                
                                    try:
                                        if data_source == _("? 배포???라???문 ?이???동", "? Connect Online Survey Data"):
                                            df_sub = st.session_state["ahp_sub_dfs"][matched_sheet_name]
                                        else:
                                            df_sub = pd.read_excel(uploaded_file, sheet_name=matched_sheet_name)
                                            df_sub = preprocess_uploaded_df(df_sub)
                                            
                                        sub_res_df, sub_facts, sub_excl, sub_excl_df = process_single_sheet(
                                            df_sub, cr_threshold, max_iter_val, learning_rate, mean_method, ahp_method
                                        )
                                    
                                        if sub_res_df.empty:
                                            raise ValueError(f"'{matched_sheet_name}' ?트???효??분석 ?이?? ?습?다.")
                                        
                                        # ?계 계산 로직
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
                                        st.error(_(f"??[?? ?트: {matched_sheet_name}] 분석 ??류가 발생?습?다.", f"??Error occurred during [Detailed Sheet: {matched_sheet_name}] analysis."))
                                        with st.expander(_("? ?유 ??결 방법 보기", "? View Reason & Solution"), expanded=True):
                                            st.markdown(_(f"""
                                            **?인:** ?트 ?????이??구조가 ?바르? ?거?? ?당 ?트???답?들??모두 ????기????과?? 못했?니?? (Error: {e})
                                            **?결 방법:**
                                            1. ?당 ?? ?트???이?에 ?칸이??문자가 ?여 ?는지 ?인?세??
                                            2. CR ?계값을 ?여???시 분석??보세??
                                            """,
                                            f"""
                                            **Cause:** The internal data structure of the sheet is incorrect, or all respondents for this sheet failed to pass the consistency ratio criteria. (Error: {e})
                                            **Solution:**
                                            1. Check if there are empty cells or text mixed in the data of the detailed sheet.
                                            2. Try analyzing again with a higher CR threshold.
                                            """))
                                        st.stop()
    
                            # 분석 ?더 ?쪽???외???????시
                            total_excluded = main_excluded
                            st.markdown(f"**" + _(f"분석 ?외: {total_excluded}?, f"Excluded from Analysis: {total_excluded} cases") + "**")
    
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
                        
                            # --- ?중 ?구?계 변??처리 UI ---
                            demo_cols = [c for c in main_results_df.columns if str(c).strip().lower() == 'type' or str(c).strip().lower().startswith('type ')]
                            if len(demo_cols) > 1 and tier in ['Standard', 'Pro']:
                                selected_demo = st.selectbox(_("? 교차분석 그룹 기? 변???택", "? Select Grouping Variable for Analysis"), demo_cols)
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
                                        "?분류": main_f, "?분류 가중치": m_weight, "중분?: sub_f, "중분?가중치": s_weight,
                                        "Global Weight": global_w, 
                                        "CR(?분류)": main_grp_cr, 
                                        "CI(?분류)": main_grp_ci,
                                        "CR(중분?": sub_info['group_cr'],
                                        "CI(중분?": sub_info['group_ci']
                                    })
                        
                            final_df = pd.DataFrame(summary_rows)
                            final_df['Global Rank'] = final_df['Global Weight'].round(3).rank(ascending=False, method='min').astype(int)
                            cols_order = ["?분류", "?분류 가중치", "중분?, "중분?가중치", "Global Weight", "Global Rank", "CR(?분류)", "CI(?분류)", "CR(중분?", "CI(중분?"]
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
                                            "?분류": main_f, "?분류 가중치": m_w, "중분?: sf, "중분?가중치": s_w_val,
                                            "Global Weight": m_w * s_w_val, 
                                            "CR(?분류)": g_main_cr, 
                                            "CI(?분류)": g_main_ci,
                                            "CR(중분?": g_sub_cr, 
                                            "CI(중분?": g_sub_ci
                                        })
                                g_df = pd.DataFrame(grp_rows)
                                if not g_df.empty:
                                    g_df['Global Rank'] = g_df['Global Weight'].round(3).rank(ascending=False, method='min').astype(int)
                                    group_full_dfs[grp] = g_df[cols_order]
                                    group_analysis_results[grp] = group_full_dfs[grp][['?분류', '중분?, 'Global Weight']]
    
                            comparison_df = final_df[['?분류', '중분?, 'Global Weight']].copy()
                            comparison_df.rename(columns={'Global Weight': '종합?균(Overall)'}, inplace=True)
                            for grp, df_res in group_analysis_results.items():
                                temp_df = df_res.rename(columns={'Global Weight': grp})
                                comparison_df = comparison_df.merge(temp_df, on=['?분류', '중분?], how='left')
    
                            output_res = io.BytesIO()
                            with pd.ExcelWriter(output_res, engine='xlsxwriter') as writer:
                                workbook = writer.book
                                
                                # [?규 추?] ?구?계 결과 ?? ?트 출력
                                if "demo_df" in st.session_state and st.session_state["demo_df"] is not None:
                                    demo_summary_df = generate_demographics_summary(st.session_state["demo_df"])
                                    if demo_summary_df is not None:
                                        demo_summary_df.to_excel(writer, sheet_name='Result_Demographics', index=False)
                                        # Result_Demographics ?? ?식 ?용
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
                                current_row_ws = write_custom_ahp_table(writer, sheet_name_comp, final_df, _("1) ?체_종합결과", "1) Overall Aggregated Results"), 1, formats, excluded_df=total_excluded_df)
                                for grp in unique_groups:
                                    if grp in group_full_dfs:
                                        current_row_ws = write_custom_ahp_table(writer, sheet_name_comp, group_full_dfs[grp], _(f"??[그룹: {grp}] 분석 결과", f"??[Group: {grp}] Analysis Results"), current_row_ws, formats)
    
                                if len(unique_groups) >= 1:
                                    ws_comp = workbook.add_worksheet('Group_Comparison')
                                    writer.sheets['Group_Comparison'] = ws_comp
                                    s_row_cp = 1
                                    ws_comp.write_string(s_row_cp, 0, _("그룹 ?비교(?원배치 분산분석: ANOVA)", "Group Comparison (One-way ANOVA)"), workbook.add_format({'bold': True, 'font_size': 12}))
                                    s_row_cp += 1
                                
                                    tier = get_current_tier()
                                    if tier not in ['Standard', 'Pro']:
                                        ws_comp.write_string(s_row_cp, 0, _("? ?계 검??결과(ANOVA/?후검????Standard ?급 ?상 ?식 ?용?에게만 ?공?니??", "? Statistical test results (ANOVA/Post-hoc) are exclusive to Standard and Pro Tier users."), workbook.add_format({'italic': True, 'font_color': '#FF0000', 'font_name': 'NanumGothic'}))
                                        s_row_cp += 1
                                
                                    if tier in ['Standard', 'Pro'] and not anova_df.empty:
                                        anova_for_merge = anova_df.rename(columns={'?인': '중분?})
                                        integrated_df = comparison_df.merge(anova_for_merge, on='중분?, how='left')
                                    else:
                                        integrated_df = comparison_df
                                
                                    # English renaming logic for columns & significance
                                    if st.session_state.get('lang', 'ko') == 'en':
                                        rename_dict = {
                                            '?분류': 'Main Criteria',
                                            '중분?: 'Sub-Criteria',
                                            '종합?균(Overall)': 'Overall',
                                            'F-?: 'F-Value',
                                            'P-Value': 'P-Value',
                                            '?의??: 'Significance',
                                            '?후검??Tukey HSD)': 'Post-hoc (Tukey HSD)'
                                        }
                                        integrated_df_excel = integrated_df.copy()
                                        integrated_df_excel.rename(columns=rename_dict, inplace=True)
                                        if 'Significance' in integrated_df_excel.columns:
                                            integrated_df_excel['Significance'] = integrated_df_excel['Significance'].replace({
                                                '?의??: 'Significant',
                                                '?의?? ?음': 'Not Significant'
                                            })
                                        if 'Post-hoc (Tukey HSD)' in integrated_df_excel.columns:
                                            integrated_df_excel['Post-hoc (Tukey HSD)'] = integrated_df_excel['Post-hoc (Tukey HSD)'].replace({
                                                '집단 ?구체??차이 발견 못함': 'No specific difference found',
                                                '계산 ?류': 'Calculation Error'
                                            })
                                            integrated_df_excel['Post-hoc (Tukey HSD)'] = integrated_df_excel['Post-hoc (Tukey HSD)'].apply(
                                                lambda x: x.replace(" 차이 ?음", " Diff Exists") if isinstance(x, str) else x
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
                                        comp_title = _("??그룹 ?중요?의 차이가 ????계?으??의?? ?게 ???는 ?유",
                                                       "??Reasons why group differences are not statistically significant despite variation in priorities")
                                        ws_comp.merge_range(guide_start_row, 0, guide_start_row, 6, comp_title, bold_fmt)
    
                                    guide_content_ko = [
                                        ("1. 그룹 ???차(분산)가 ?무 ??경우", "ANOVA??'그룹 간의 차이'? '그룹 ?의 차이'?비교?니??\n\n???리: 그룹 ??균 차이가 ?더?도, ?그룹 ?? ?이?들???로 ?쭉?쭉(분산?????다??계?으로는 '??차이가 ?연??발생?을 가?성???다'??단?니??"),
                                        ("2. ?본 ?기(Sample Size)??부?, "?계???의?? ?본???에 매우 민감?니??\n\n???상: ?그룹???이??개수(?본??가 ?무 ?다??계????Power)??부족하???의미한 차이?찾아?? 못합?다."),
                                        ("3. ?이?의 ?위(Scale)? 변?성", "?에 ?????치?이 ?부?매우 ?? ?수???위?니?? ?제 계산 과정?서 ???차 범위 ?에 ?다??계?으로는 측정 ?차 범위 ?의 ?들림으?간주?니??")
                                    ]
                                
                                    guide_content_en = [
                                        ("1. Within-Group Variance is Too Large", "ANOVA compares variance between groups against variance within groups.\n\n??Principle: Even if the mean difference between groups is large, if individual responses within each group are highly scattered (large variance), statistics will determine that the difference is likely due to chance."),
                                        ("2. Insufficient Sample Size", "Statistical significance is highly sensitive to the number of samples.\n\n??Phenomenon: If the number of data points (sample size) in each group is too small, statistical power is insufficient to detect significant differences."),
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
                                
                                    excl_label = _(f"분석 ?외 ???? {sheet_excl_count}?, f"Excluded cases: {sheet_excl_count}")
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
                                
                                    # [?규 추?] ?체 종합 ?렬 ?른쪽에 ?체 CR, CI ??시
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
                                
                                    ws.merge_range(s_row_det, n_dim + 2, s_row_det, n_dim + 3, _("?체 ????지??, "Overall Consistency Indicators"), ci_cr_header_fmt)
                                    ws.write(s_row_det + 1, n_dim + 2, _("?체 CI", "Overall CI"), ci_cr_label_fmt)
                                    ws.write(s_row_det + 1, n_dim + 3, ci_val, ci_cr_val_fmt)
                                    ws.write(s_row_det + 2, n_dim + 2, _("?체 CR", "Overall CR"), ci_cr_label_fmt)
                                    ws.write(s_row_det + 2, n_dim + 3, cr_val, ci_cr_val_fmt)
                                
                                    s_row_det += len(matrix_df) + 3
                                
                                    if group_matrices:
                                        for g_name, g_mat in group_matrices.items():
                                            ws.write_string(s_row_det, 0, _(f"] 그룹 종합 ?렬: {g_name}", f"] Group Combined Matrix: {g_name}"))
                                            s_row_det += 1
                                            gm_df_obj = pd.DataFrame(g_mat, index=row_labels, columns=row_labels)
                                            gm_df_obj.to_excel(writer, sheet_name=sheet_name, startrow=s_row_det)
                                            add_borders_to_data(ws, s_row_det, 0, gm_df_obj, border_fmt, has_header=True, has_index=True)
                                            for r in range(len(g_mat)):
                                                for c in range(len(g_mat)):
                                                    val = 1 if r==c else g_mat[r][c]
                                                    ws.write(s_row_det+r+1, c+1, val, border_fmt if r!=c else fmt_diagonal)
                                                    if r!=c: ws.write(s_row_det+r+1, c+1, val, fmt_float_no_border)
                                        
                                            # [?규 추?] 그룹 종합 ?렬 ?른쪽에 그룹 CR, CI ??시
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
                                        
                                            ws.merge_range(s_row_det, n_dim + 2, s_row_det, n_dim + 3, _("그룹 ????지??, "Group Consistency Indicators"), ci_cr_header_fmt)
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
                                write_detailed_sheet_ws('(?분류) Main', main_group_matrix, out_main, _("[?분류 ?? 종합 ?렬]", "[Main Criteria Combined Matrix]"), main_factors, group_matrices=main_group_mats, sheet_excl_count=main_excluded)
                                for mf, info in sub_results_storage.items():
                                    safe_name = f"(중분? {mf}"[:31]
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
                                             
                                    title_ko = f"[중분??? 종합 ?렬]  ???위 계층: ?분류 [{mf}]"
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
                                        [f"The original matrix A and the ideal matrix W are linearly combined according to the set learning rate (learning rate α={learning_rate}): A_new = (1-α)A + αW."],
                                        [""],
                                        ["3. Academic Foundation & Effects"],
                                        ["Adjustment using a weighted average of the original matrix and the consistent matrix preserves the decision maker's original preferences as much as possible while improving mathematical consistency."]
                                    ]
                                else:
                                    theory_text = [
                                        ["?사결정론적 관?에?의 AHP ????보정 ?리 ??술??근거"],
                                        [""],
                                        ["1. ?론: 계층분석과정(AHP)??????문제"],
                                        ["Saaty(1980)???해 ?안??계층분석과정? ?간??주????단???량?하???기준 ?사결정 ?구?다. 비일관???단??발생??경우 ?학?으?교정?여 분석???뢰?을 ?보?다."],
                                        [""],
                                        ["2. 보정 ?고리즘: 반복 ?렴 조정?],
                                        [f"?본 ?렬 A? ?상???렬 W??정???습?α={learning_rate})???라 ?형 결합?다: A_new = (1-α)A + αW."],
                                        [""],
                                        ["3. ?술??근거 ??과"],
                                        ["?본 ?렬??? ?렬??가??균???용??조정? ?사결정?의 ?래 ?호 경향?을 최???보존?면???학?????을 ?상?킨??"]
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
                                    guide_title = _("1?계 AHP 분석 결과 ?석 ?주의?항", "Step 1 AHP Analysis Result Interpretation and Guidelines")
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
                                            ("분류", "?세 ?용"),
                                            ("1. 분석 개요", "?보고?는 ?위 ?소 ?이 ?분류(1?계) ?? 기?만을 비교???일 계층 AHP 분석 결과?니??"),
                                            ("2. 결과 ?석 방법", "?위 가중치가 1.0?로 고정?어 '?분류 가중치'? 'Global Weight(종합 가중치)'가 ?일???치??출?었?니?? ?라??'Global Weight'??????최종 중요?로 ?석?시??니??"),
                                            ("3. ?? 가???산 ?내", "AHP 분석 ?스?의 2?계 ?산 ????????해, ?스?????으??분류 ?? ?위??가중치 1.0??가지???? ?? ?????동 ?성?여 ?산???니?? ?로 ?해 결과 ?운로드 ?일??'Result_[?분류?' ?트가 1x1 ?렬?존재????는 ?상?인 가???산 결과?니??"),
                                            ("4. ????비율(CR) 주의?항", "?공??????비율? ?분류 ??비교??????비율(CR)만을 ???니?? ?위 ?소가 존재?? ?으므?'중분?????비율(CR)'? 무조?0.000?로 ?기?며 ?는 ?류가 ?닙?다."),
                                            ("5. ?술/보고??기재 ??, "?술 ?구??보고?에 ?용 ??'?일 계층(1?계) 계층 구조 ?에????비교 분석???행?????명시?으?기재?시?바랍?다.")
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
                                    # 1. Fuzzy AHP 가중치 분석 결과 ?트 추?
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
                                
                                    ws_fuzzy.write_string(row_idx, 0, _("???분류 (Main Criteria) ?? AHP 분석 결과 (?각?????용)", "??Main Criteria Fuzzy AHP Results (TFN Applied)"), title_fmt)
                                    row_idx += 1
                                
                                    headers = [
                                        _("구분", "Criteria"), 
                                        _("Fuzzy 가중치 (Lower)", "Fuzzy Weight (Lower)"), 
                                        _("Fuzzy 가중치 (Medium)", "Fuzzy Weight (Medium)"), 
                                        _("Fuzzy 가중치 (Upper)", "Fuzzy Weight (Upper)"), 
                                        _("비퍼지??(Crisp)", "Defuzzified (Crisp)"), 
                                        _("최종 가중치 (Norm)", "Final Weight (Norm)"), 
                                        _("?위", "Rank")
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
                                            ws_fuzzy.write_string(row_idx, 0, _(f"?????? [{parent_f}] ?? AHP 분석 결과 (?각?????용)", f"??Sub-Criteria [{parent_f}] Fuzzy AHP Results (TFN Applied)"), title_fmt)
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
    
                                    # 2. ????비율(CR) 분포 분석 결과 ?트 추?
                                    ws_cr = workbook.add_worksheet('CR_Distribution')
                                    writer.sheets['CR_Distribution'] = ws_cr
                                    ws_cr.set_column('A:A', 25)
                                    ws_cr.set_column('B:H', 20)
                                
                                    cr_header_fmt = workbook.add_format({
                                        'bold': True, 'align': 'center', 'valign': 'vcenter',
                                        'bg_color': '#595959', 'font_color': '#FFFFFF', 'border': 1,
                                        'font_name': 'NanumGothic'
                                    })
                                
                                    ws_cr.write_string(1, 0, _("??????비율(CR) 분석 ?약", "??Consistency Ratio (CR) Analysis Summary"), title_fmt)
                                
                                    cr_headers = [
                                        _("?? ?트?, "Sheet Name"),
                                        _("?균 CR", "Mean CR"),
                                        _("중앙?CR", "Median CR"),
                                        _("최소 CR", "Min CR"),
                                        _("최? CR", "Max CR"),
                                        _("?과 ?본 ??(CR <= 0.1)", "Passed Samples (CR <= 0.1)"),
                                        _("?체 ?본 ??, "Total Samples"),
                                        _("?과??(%)", "Pass Rate (%)")
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
                                    ws_cr.write_string(cr_row_idx, 0, _("??개별 ?답?별 ????비율(CR) ?세 ?역", "??Detailed Consistency Ratio (CR) by Respondent"), title_fmt)
                                    cr_row_idx += 1
                                
                                    indiv_headers = [
                                        _("ID (?문??", "Respondent ID"),
                                        _("그룹 (Type)", "Group Type"),
                                        _("?? ?트?, "Sheet Name"),
                                        _("????비율 (CR)", "Consistency Ratio (CR)"),
                                        _("?정 (CR <= 0.1)", "Status (CR <= 0.1)")
                                    ]
                                    for c_idx, h in enumerate(indiv_headers):
                                        ws_cr.write(cr_row_idx, c_idx, h, cr_header_fmt)
                                    cr_row_idx += 1
                                
                                    for idx_row, r in main_results_df.iterrows():
                                        cr_val = r['Final_CR']
                                        status = _("만족 (Pass)", "Pass") if cr_val <= 0.1 else _("불만?(Fail)", "Fail")
                                        ws_cr.write(cr_row_idx, 0, r['ID'], formats['body'])
                                        ws_cr.write(cr_row_idx, 1, r['Type'], formats['body'])
                                        ws_cr.write(cr_row_idx, 2, "Main_Criteria", formats['body'])
                                        ws_cr.write_number(cr_row_idx, 3, cr_val, formats['num'])
                                        ws_cr.write(cr_row_idx, 4, status, formats['body'])
                                        cr_row_idx += 1
                                    
                                    for mf, info in sub_results_storage.items():
                                        for idx_row, r in info['df'].iterrows():
                                            cr_val = r['Final_CR']
                                            status = _("만족 (Pass)", "Pass") if cr_val <= 0.1 else _("불만?(Fail)", "Fail")
                                            ws_cr.write(cr_row_idx, 0, r['ID'], formats['body'])
                                            ws_cr.write(cr_row_idx, 1, r['Type'], formats['body'])
                                            ws_cr.write(cr_row_idx, 2, mf, formats['body'])
                                            ws_cr.write_number(cr_row_idx, 3, cr_val, formats['num'])
                                            ws_cr.write(cr_row_idx, 4, status, formats['body'])
                                            cr_row_idx += 1
    
                        st.success(_("분석???료?었?니??", "Analysis completed successfully."))
                        if st.session_state.get('plan_type') == 'Basic':
                            st.info(_("**Basic ?한**: ?본 10개로 ?한?니?? Standard ?상?로 ?그?이?하?요.",
                                      "? **Basic Limit**: Limited to 10 samples. Please upgrade to Standard or higher."))
                        if st.session_state.user_role == 'official':
                            if data_source == _("? ?? ?일 직접 ?로??, "Upload Excel File") and uploaded_file is not None:
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
    
                        st.caption(_("?️ ?로고침 ??결과가 리셋?니?? 결과 ?운로드 ????반드????하?요.",
                                     "?️ Results reset on refresh. Download via the Results tab."))
    
                        tab1, tab2, tab3, tab4, tab5 = st.tabs([
                            _("종합 분석 (Global)", "Global Comprehensive Analysis"),
                            _("그룹?분석", "Group Analysis"),
                            _("?계 검??(ANOVA)", "Statistical Test (ANOVA)"),
                            _("?각???터", "Visualization Center"),
                            _("결과 ?운로드", "Download Results")
                        ])
                        with tab1:
                            st.subheader(_(" 종합 중요????위", " Global Weights & Rankings"))
                            if is_english:
                                disp_final_df = final_df.rename(columns={
                                    "?분류": "Main Criteria",
                                    "?분류 가중치": "Main Criteria Weight",
                                    "중분?: "Sub-Criteria",
                                    "중분?가중치": "Sub-Criteria Weight",
                                    "Global Weight": "Global Weight",
                                    "Global Rank": "Global Rank",
                                    "CR(?분류)": "CR (Main Criteria)",
                                    "CI(?분류)": "CI (Main Criteria)",
                                    "CR(중분?": "CR (Sub-Criteria)",
                                    "CI(중분?": "CI (Sub-Criteria)"
                                })
                            else:
                                disp_final_df = final_df
                            st.dataframe(disp_final_df.style.format(precision=3), use_container_width=True)
    

    
                        with tab2:
                            st.markdown(_("#### 그룹?가중치 ?세 비교", "#### Detailed Comparison of Weights by Group"))
                            disp_comparison_df = comparison_df.copy()
                            if is_english:
                                disp_comparison_df.rename(columns={
                                    "중분?: "Sub-Criteria",
                                    "Overall": "Overall",
                                    "?문가": "Expert",
                                    "?반": "General",
                                    "공무??: "Public Official"
                                }, inplace=True)
                            st.dataframe(disp_comparison_df.style.format(precision=4), use_container_width=True)
                        with tab3:
                            st.markdown(_("#### 집단 ??의??분석", "#### Analysis of Significance Between Groups"))
                            if not anova_df.empty:
                                if is_english:
                                    disp_anova = anova_df.copy()
                                    disp_anova.rename(columns={
                                        "?인": "Factor/Criteria",
                                        "F-?: "F-Value",
                                        "P-Value": "P-Value",
                                        "?의??: "Significance",
                                        "?후검??Tukey HSD)": "Post-Hoc (Tukey HSD)"
                                    }, inplace=True)
                                
                                    # Map values in Significance
                                    disp_anova["Significance"] = disp_anova["Significance"].map({
                                        "?의??: "Significant",
                                        "?의?? ?음": "Not Significant"
                                    }).fillna(disp_anova["Significance"])
                                
                                    # Map values in Post-Hoc
                                    def translate_posthoc(val):
                                        if not isinstance(val, str):
                                            return val
                                        val = val.replace("?문가", "Expert").replace("?반", "General").replace("공무??, "Public Official")
                                        val = val.replace(" 차이 ?음", " (Diff exists)")
                                        val = val.replace("집단 ?구체??차이 발견 못함", "No significant pairwise difference found")
                                        val = val.replace("계산 ?류", "Calculation Error")
                                        return val
                                    disp_anova["Post-Hoc (Tukey HSD)"] = disp_anova["Post-Hoc (Tukey HSD)"].apply(translate_posthoc)
                                else:
                                    disp_anova = anova_df
                                st.dataframe(disp_anova.style.format(precision=5), use_container_width=True)
                            else:
                                st.info(_("?계 검?을 ?해 2??상??그룹 ?이?? ?요?니??", "At least 2 group datasets are required for statistical testing (ANOVA)."))
                        with tab4:
                            st.markdown(_("####  ?각???터", "####  Visualization Center"))
                            col_chart1, col_chart2 = st.columns(2)
                            with col_chart1:
                                st.write(_("**종합 중요??(Bar)**", "**Global Importance (Bar)**"))
                                chart_bar_df = final_df.sort_values('Global Weight').copy()
                                if is_english:
                                    chart_bar_df.rename(columns={"중분?: "Sub-Criteria", "Global Weight": "Global Weight"}, inplace=True)
                                    y_col = "Sub-Criteria"
                                    x_col = "Global Weight"
                                else:
                                    y_col = "중분?
                                    x_col = "Global Weight"
                                fig_bar = px.bar(chart_bar_df, y=y_col, x=x_col, orientation='h', text_auto='.3f')
                                st.plotly_chart(fig_bar, use_container_width=True)
                            with col_chart2:
                                st.write(_("**그룹?중요???턴 (Radar)**", "**Importance Pattern by Group (Radar)**"))
                                indiv_global_radar = []
                                all_ids_r = main_results_df['ID'].unique()
                                for rid in all_ids_r:
                                    m_row_rd = main_results_df[main_results_df['ID'] == rid].iloc[0]
                                    rtype_rd = m_row_rd['Type']
                                    grp_name_en = rtype_rd
                                    if is_english:
                                        grp_name_en = str(rtype_rd).replace("?문가", "Expert").replace("?반", "General").replace("공무??, "Public Official")
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
                        
                            # [바이?린 ?롯] CR 분포 ?각?????롭?운 계층 ?택
        with tab_signup_side:
            if st.session_state.user_id:
                st.info(_("?? 로그?되???습?다.", "You are already logged in."))
            else:
                signup_type = st.radio(
                    _("가??구분 ?택", "Select Registration Type"),
                    options=[
                        _("무료 ?원가??, "Free Registration"),
                        _("?식(?료) ?원가??, "Official (Paid) Registration")
                    ],
                    horizontal=True,
                    key="main_signup_type"
                )

                if signup_type == _("?식(?료) ?원가??, "Official (Paid) Registration"):
                    st.info(_(
                        "? **?식(?료) ?이?스 ?용 ?내**\n\n"
                        "1. 먼? **'무료 ?원가??**???택?여 계정???성??주세??\n"
                        "2. ?성??계정?로 로그?한 ?? ?쪽 ?이?바??**결제 ?동** ?는 ?단??**'?비???금'** ?? ?해 결제??료?시?즉시 ?식 ?이?스??그?이?됩?다.\n\n"
                        "? *?구?법인카드 결제 ?견적??계산??간이과세?? 발행??100% 지?됩?다.*",
                        "? **Official (Paid) License Info**\n\n"
                        "1. Please first select **'Free Registration'** to create your account.\n"
                        "2. Log in with your new account and complete the payment through the **Payment System** in the left sidebar or the **'Service Pricing'** tab to instantly upgrade to an official license.\n\n"
                        "? *Supports Research/Corporate Cards, and Quotations (100% supported).*"
                    ))
                else:
                    agreements = show_agreement_ui()
                    s_id = st.text_input(_("?이??(?메??주소)", "Username (Email Address)"), key="main_s_id")
                    s_pw = st.text_input(_("비?번호", "Password"), type="password", key="main_s_pw")

                    s_cust_type = "standard"

                    if st.button(_("가?신?, "Register"), key="main_btn_signup"):
                        if not agreements.get("agree_personal_info"):
                            st.error(_("개인?보 ?집·?용???의?야 가?신? ???습?다.", "You must agree to the privacy policy to register."))
                        elif not validate_email(s_id):
                            st.error(_("?바??메???식???닙?다.", "Invalid email format."))
                        elif not validate_password(s_pw):
                            st.error(_("비?번호??문자+?수문자?야 ?니??", "Password must contain both letters and special characters."))
                        else:
                            restore_from_deleted_sheet(s_id.strip())
                            # 가????무조?'temp' 권한?로 배정
                            if add_user(s_id.strip(), s_pw, 'temp', agree_info="Y", customer_type=s_cust_type):
                                st.success(_("?원가?이 ?료?었?니?? ?이?바??'로그?? ????로그?해 주시?바랍?다.", "Registration successful! Please log in using the 'Login' tab in the sidebar."))
                                import time
                                time.sleep(2)
                                st.rerun()
                            else:
                                st.error(_("?? 존재?는 ?이?입?다.", "ID already exists."))

                    st.info(_("? **개인?보 보호 ?내**\n\nAHP 마스?는 ?용?의 ?름, ?화번호 ??불필?한 개인?보??집?? ?습?다. ?한 ?력?신 비?번호??강력?게 ?호?되????되므?관리자???????습?다. ?심?고 ?용??주세??", "? **Privacy Protection Notice**\n\nAHP Master does not collect unnecessary personal information such as names or phone numbers. Furthermore, your password is strongly encrypted and stored securely, so even the administrator cannot access it. Please use our service with peace of mind."))


                            st.markdown("---")
                            st.write(_("**????비율(CR) 분포 (Violin Plot)**", "**Consistency Ratio (CR) Distribution (Violin Plot)**"))
                            st.caption(_("계층???택?면 ?당 ?? ?답?들??CR 분포??시?니?? 바이?린 ??= 밀?? ?? 박스 = 중앙값·사분위?? ??= 개별 ?답??,
                                         "Select a tier to view respondent CR distribution. Width = density, box = median/IQR, dots = individual respondents"))

                            _t2_tier_opts_ko = ["?분류 (Main)", "중분?(Sub)"]
                            _t2_tier_opts_en = ["Main Criteria", "Sub-Criteria"]
                            _t2_tier_opts = _t2_tier_opts_en if is_english else _t2_tier_opts_ko
                            _t2_sel_tier = st.selectbox(
                                _("? ?시??계층 ?택", "? Select Tier to Display"),
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

                                # ?? ?택: ?분류 ?????????????????????????????????
                                if _t2_sel_tier == _t2_tier_opts[0]:
                                    if not main_results_df.empty and "Final_CR" in main_results_df.columns:
                                        _t2_main_cr = main_results_df["Final_CR"].dropna().tolist()
                                        _t2_xlbl = _("?분류", "Main Criteria")
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
                                    _t2_xaxis_title = _("?분류", "Main Criteria")
                                    _t2_legend_title = _("?분류", "Main Criteria")

                                # ?? ?택: 중분??????????????????????????????????
                                else:
                                    for _t2_mf, _t2_info in sub_results_storage.items():
                                        _t2_sdf = _t2_info.get("df", None)
                                        if _t2_sdf is None or _t2_sdf.empty or "Final_CR" not in _t2_sdf.columns:
                                            continue
                                        _t2_cr_vals = _t2_sdf["Final_CR"].dropna().tolist()
                                        if len(_t2_cr_vals) < 2:
                                            continue
                                        _t2_xlbl = _(f"중분?{_t2_mf})", f"Sub({_t2_mf})")
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
                                    _t2_xaxis_title = _("?분류 (중분?비교 CR)", "Main Criteria (Sub-Criteria Comparison CR)")
                                    _t2_legend_title = _("중분?, "Sub-Criteria")

                                if len(_fig_t2_vio.data) == 0:
                                    st.info(_("?택??계층??CR ?이?? ?거???답 ?? 부족합?다.",
                                              "No CR data available for the selected tier or insufficient responses."))
                                else:
                                    _fig_t2_vio.add_hline(
                                        y=0.1, line_dash="dash", line_color="red",
                                        annotation_text=_("CR ?계?(0.1)", "CR Threshold (0.1)"),
                                        annotation_position="top right"
                                    )
                                    _fig_t2_vio.update_layout(
                                        title=_(
                                            f"바이?린?롯 CR ??{_t2_sel_tier}",
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
                                st.warning(_(f"바이?린 ?롯 ?성 ?패: {_e_t2_vio}", f"Violin plot generation failed: {_e_t2_vio}"))
    
                            # ?? Fuzzy AHP TFN ?각?? 그래??(Tab1 결과 ?면 직후) ??
                            if ahp_method == 'fuzzy':
                                st.markdown("---")
                                st.subheader(_(" ?각????TFN) 가중치 분포", " Triangular Fuzzy Number (TFN) Weight Distribution"))
                                st.caption(_("??인???각????L, M, U)? 비퍼지?된 Crisp 가중치??각?합?다.",
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
                                        # ?각??채우?(반투?
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
                                        # Crisp 가중치 ?직 ?선
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
                                        xaxis_title=_("가중치 ?(Weight Value)", "Weight Value"),
                                        yaxis_title=_("?속??(Membership Degree)", "Membership Degree"),
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
    
                                # 1) 메인 기? TFN 그래??
                                if main_group_Si:
                                    st.plotly_chart(
                                        render_tfn_chart(main_group_Si, main_factors,
                                            _("???분류 (Main Criteria) ?각?? 분포", "??Main Criteria TFN Distribution")),
                                        use_container_width=True
                                    )
    
                                    # TFN ?치 ?이?
                                    tfn_table_rows = []
                                    for i, (l, m, u) in enumerate(main_group_Si):
                                        crisp = (l * m * u) ** (1/3)
                                        tfn_table_rows.append({
                                            _("?인", "Factor"): main_factors[i],
                                            "L (Lower)": l, "M (Most Likely)": m, "U (Upper)": u,
                                            "Crisp Weight": crisp,
                                            _("?규??가중치", "Normalized Weight"): group_main_weights.iloc[i] if isinstance(group_main_weights, pd.Series) else group_main_weights[i]
                                        })
                                    st.dataframe(pd.DataFrame(tfn_table_rows).style.format(precision=4), use_container_width=True)
    
                                # 2) ?? 기??TFN 그래??
                                for parent_f, sub_info in sub_results_storage.items():
                                    if sub_info.get('group_Si'):
                                        st.markdown("---")
                                        st.plotly_chart(
                                            render_tfn_chart(sub_info['group_Si'], sub_info['factors'],
                                                _(f"??[{parent_f}] ???? ?각?? 분포", f"??[{parent_f}] Sub-Criteria TFN Distribution")),
                                            use_container_width=True
                                        )
                                        sub_tfn_rows = []
                                        for i, (l, m, u) in enumerate(sub_info['group_Si']):
                                            crisp = (l * m * u) ** (1/3)
                                            sub_tfn_rows.append({
                                                _("?인", "Factor"): sub_info['factors'][i],
                                                "L (Lower)": l, "M (Most Likely)": m, "U (Upper)": u,
                                                "Crisp Weight": crisp,
                                                _("?규??가중치", "Normalized Weight"): sub_info['weights'].iloc[i] if isinstance(sub_info['weights'], pd.Series) else sub_info['weights'][i]
                                            })
                                        st.dataframe(pd.DataFrame(sub_tfn_rows).style.format(precision=4), use_container_width=True)
    
                        with tab5:
                            st.markdown(_('<p style="color: red; font-weight: bold; font-size: 0.95rem; margin-bottom: 12px;"> 주의: 분석 결과가 ?상???구 ??되지 ?으므? ?래 ?운로드 버튼???러 결과??? ?일??컴퓨?에 반드????해 주세??</p>',
                                          '<p style="color: red; font-weight: bold; font-size: 0.95rem; margin-bottom: 12px;">?️ Warning: Analysis results are not permanently stored on the web. Please make sure to click the download button below to save the Excel file to your computer.</p>'), unsafe_allow_html=True)
                            st.download_button(_("? 결과 ?일 ?운로드 (Excel)", "? Download Results File (Excel)"), data=output_res.getvalue(), file_name="AHP_Result.xlsx", type="primary", on_click=lambda: __import__("survey_manager").log_user_action(st.session_state.get("user_id") or "Guest", "결과 ?? ?운로드"))
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
                        st.error(_("??분석 ?스???? ?류가 발생?습?다.", "??An internal error occurred in the analysis system."))
                        st.info(_(f"?세 ?러 ?용: {e}", f"Detailed error: {e}"))
                        with st.expander(_("? ?세 ?택 ?레?스", "? Detailed Stack Trace")):
                            st.code(traceback.format_exc())
                        st.stop()
                else:
                    st.warning(message)
                    if role_chk == 'temp' and ("3??본" in message or "3 samples" in message):
                        st.markdown("---")
                        with st.container(border=True):
                            is_english = (st.session_state.get('lang', 'ko') == 'en')
                            if is_english:
                                st.markdown("###  Official User Upgrade & Unlimited Analysis")
                                st.markdown("Upgrading to an Official User **instantly removes the 3-sample limit** and allows unlimited access to all features.")
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
                                st.markdown(_("### ? 무제??분석 ?즉시 ?제", "### ? Upgrade to Official User for Unlimited Analysis"))
                                st.markdown("?식 ?용?로 ?격?시?**?본 ???한(3???즉시 ?제**?며 모든 분석 기능??무제?으??용?실 ???습?다.")
                                st.error("??**?재 ?이?는 3?본??초과?여 분석??차단?었?니??**\n\n지?바로 ?그?이?하??? ?이 분석???어가?요!")
                                if st.button("?? 지??그?이?하?무제??분석?기", type="primary", use_container_width=True):
                                    st.components.v1.html("""
                                        <script>
                                            const tabs = window.parent.document.querySelectorAll('button[data-baseweb="tab"]');
                                            for (let i = 0; i < tabs.length; i++) {
                                                if (tabs[i].innerText.includes('?비???내') || tabs[i].innerText.includes('Service Info')) {
                                                    tabs[i].click();
                                                    window.parent.scrollTo(0, 0);
                                                    break;
                                                }
                                            }
                                        </script>
                                    """, height=0, width=0)
            except Exception as e:
                st.error(f"?일 처리 ?류 발생: {e}")
            
        st.markdown("---")
    
        if st.session_state.user_role == 'official':
            with st.expander(_("?의 분석 보???(중요: 반드??컴퓨?에 백업??주세??", "My Analysis Storage (Important: Please backup to your computer)")):
                my_analyses = get_user_analyses(st.session_state.user_id)
                if not my_analyses: st.info(_("??된 분석 ?음", "No saved analyses found."))
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
                            if st.button("?", key=f"del_{a_id}"):
                                delete_analysis(a_id)
                                st.rerun()
    

    
    # -------------------------------------------------------------------------
    # [?규] 코딩 ?? ?식 ??
    # -------------------------------------------------------------------------
    with main_tab_coding:
        # -------------------------------------------------------------------------
        # [?규] ?라???문지 ?작 ??(Tab 2) ?세 구현
        # -------------------------------------------------------------------------
        st.header(_("AHP 분석 모델 ?정 ?코딩 ?식 ?운로드", "Setup AHP Decision Model & Download Coding Form"))
        
        saved_model = None
        if st.session_state.user_id is None:
            st.info(_("로그?????만??분석 모델????할 ???습?다. (비로그인?서???플 ?이?로 미리보기 가??",
                      "Log in to save your custom models. (Preview with sample data available without login)"))
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
        ko_default_main = "거버?스, 계획??성, ?현가?성, ?업?과"
        ko_default_subs = {
            "거버?스": "?정지?? 지???체, 총괄?업관리자",
            "계획??성": "?안?정?? ??적?성, 목표구체??,
            "?현가?성": "부지?보, ?업구체?? ?업비적?성",
            "?업?과": "경제?효? ?회?효? ?과관?
        }

        # [?규] 3계층(V3) ?플 ?이??(?마?폰 구매 결정)
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

        ko_default_main_v3 = "기능?? ?자?? 경제??
        ko_default_subs_v3 = {
            "기능??: "?드?어, ?프?웨??,
            "?자??: "??, ?의??,
            "경제??: "?말기?? ??비용"
        }
        ko_default_sub_subs_v3 = {
            "?드?어": "카메?? 배터? ?로?서",
            "?프?웨??: "?영체제, 기본??,
            "??": "?상, ?질",
            "?의??: "", 
            "?말기??: "?시? ??",
            "??비용": "?신?금, AS비용"
        }
    
    
        with st.expander(_("?의 분석 모델 만들?, "Create Custom AHP Model"), expanded=True):
            st.info(_("???????????력?여 코딩 ?? ?식???성?세?? (?반 AHP / ?? AHP 공용)",
                      "Enter criteria to generate your coding Excel template. (For both Traditional and Fuzzy AHP)"))
            
            # 계층 구조 ?정 (2계층 기???일?게 ?체 공개)
            tier_level = 2
            st.markdown("#####  계층 구조 ?정")
            tier_choice = st.radio(
                _("계층 ?벨???택?세??", "Select Hierarchy Level."),
                [_("2계층 (?분류 - 중분?", "2-Tier (Main - Sub)"),
                 _("3계층 (?분류 - 중분?- ?분?", "3-Tier (Main - Sub - Sub-sub)")],
                index=0,
                horizontal=True,
                key="tab1_tier_choice"
            )
            if _("3계층", "3-Tier") in tier_choice:
                tier_level = 3
            st.markdown("---")
                
            # [?규] tier_level???라 ?플 ?이???위?
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
                    
            main_criteria_input = st.text_input(_("??? (Main Criteria, ?표 구분)", "Main Criteria (comma-separated)"), value=default_main)
            main_criteria_list = [x.strip() for x in main_criteria_input.split(',') if x.strip()]
            
            model_structure = {}
            sub_sub_structure = {}
            if main_criteria_list:
                for mc in main_criteria_list:
                    d_val = default_subs.get(mc, "")
                    if isinstance(d_val, list): d_val = ", ".join(d_val)
                    sub_input = st.text_input(_(f"'{mc}'??????", f"Sub-criteria for '{mc}'"), value=d_val, key=f"tab1_sub_{mc}")
                    sub_list = [x.strip() for x in sub_input.split(',') if x.strip()]
                    model_structure[mc] = sub_list
                    
                    if tier_level == 3 and sub_list:
                        with st.expander(_(f"??'{mc}'???분?(Sub-sub-criteria) ?력", f"??Enter Sub-sub-criteria for '{mc}'"), expanded=True):

                            for sub_c in sub_list:
                                sub_sub_input = st.text_input(
                                    f"??'{sub_c}'???분?(?표 구분)", 
                                    value=default_sub_subs.get(sub_c, ""),
                                    placeholder="?? ??1, ??2 (???위 ?인???다?비워?세??",
                                    help="?력칸을 비워?면 ????? ?동?로 2계층 구조?간주?어 분석?니??",
                                    key=f"tab1_sub_sub_{sub_c}"
                                )
                                parsed_sub_subs = [x.strip().replace("_", " ") for x in sub_sub_input.split(",") if x.strip()]
                                if parsed_sub_subs:
                                    sub_sub_structure[sub_c] = parsed_sub_subs
            
            # ?? 계층 구조 ?리 ?각????????????????????????????????????????
            if main_criteria_list:
                st.markdown("---")
                st.markdown(_("##### ? 계층 구조 미리보기", "##### ? Hierarchy Preview"))
                tree_lines = []
                for mi, mc in enumerate(main_criteria_list):
                    is_last_main = (mi == len(main_criteria_list) - 1)
                    prefix_main = "??? " if is_last_main else "??? "
                    tree_lines.append(f"{prefix_main}[{mc}]")
                    
                    subs = model_structure.get(mc, [])
                    for si, sc in enumerate(subs):
                        is_last_sub = (si == len(subs) - 1)
                        branch_main = "    " if is_last_main else "??  "
                        prefix_sub = "??? " if is_last_sub else "??? "
                        
                        sub_subs = sub_sub_structure.get(sc, []) if tier_level == 3 else []
                        if sub_subs:
                            tree_lines.append(f"{branch_main}{prefix_sub}{sc}")
                            for ssi, ssc in enumerate(sub_subs):
                                is_last_ss = (ssi == len(sub_subs) - 1)
                                branch_sub = "    " if is_last_sub else "??  "
                                prefix_ss = "??? " if is_last_ss else "??? "
                                tree_lines.append(f"{branch_main}{branch_sub}{prefix_ss}{ssc}")
                        else:
                            tree_lines.append(f"{branch_main}{prefix_sub}{sc}")
                
                tree_text = "\n".join(tree_lines)
                st.code(tree_text, language=None)
            # ?????????????????????????????????????????????????????????????

            # ?? ?이???력 가?드 (?? ?출) ????????????????????????????
            with st.expander(_("? ?운로드???????이?? ?력?는 방법", "? How to enter data in the downloaded Excel"), expanded=False):
                st.markdown(_("""
**???? ?일 ?기**: ?래 버튼?로 ?운로드???? ?일???행?니??

**????비교 ?이???력**:
- **?쪽(?행)** ??????중요?면: **?수** ?력 (?? `-3`)
- **?른?미시??** ??????중요?면: **?수** ?력 (?? `3`)
- ??????**?등**?면: `1` ?력

**???수 ?보 ?력**:
- A??`ID`): ?답??번호 (1, 2, 3, ...)
- B??`Type`): 그룹?(?? ?문가, 주?, 공무????
                """, """
**??Open the Excel file**: Run the template downloaded via the button below.

**??Enter pairwise comparison data**:
- If the **left** item is more important: enter a **negative** value (e.g., `-3`)
- If the **right** item is more important: enter a **positive** value (e.g., `3`)
- If they are **equal**: enter `1`

**??Required information**:
- Column A (`ID`): Respondent number (1, 2, 3, ...)
- Column B (`Type`): Group name (e.g., Expert, Public, Official)
                """))
                img_file = _("ahp_input_guide.png", "ahp_input_guide_en.png")
                if os.path.exists(img_file):
                    st.image(img_file, caption=_("[참고] ?문 ?답???????력?는 방법", "[Reference] How to enter survey responses into Excel"))
            # ?????????????????????????????????????????????????????????????

            col1, col2 = st.columns(2)
            with col1:
                generate_clicked = st.button(_("1️⃣ ?정??모델?AHP 코딩 ?? ?식 ?성", "1️⃣ Generate Excel Template with this Model"), use_container_width=True)
                if generate_clicked:
                    import survey_manager; survey_manager.log_user_action(st.session_state.get("user_id") or "Guest", "AHP ?? ?식 ?성")
            
            if generate_clicked:
                if st.session_state.user_id is None:
                    st.warning(_("코딩 ?? ?식 ?성 ??운로드??로그?한 ?용??무료 ?원 ?함)??용 가?합?다. ?쪽 메뉴?서 로그?하거나 ?원가?을 ?주?요.", "Generating and downloading Excel templates is only available to logged-in users (including free members). Please log in or sign up from the left menu."))
                elif not main_criteria_list:
                    st.error(_("??? ?력 ?요", "Main criteria input is required"))
                else:
                    current_model = {'main': main_criteria_input, 'subs': model_structure, 'sub_subs': sub_sub_structure, 'Tier_Level': tier_level}
                    save_user_model(st.session_state.user_id, current_model)
                    st.toast(_("모델 ????료", "Model successfully saved"))
                    
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
                            
                        # 3계층 ?트 ?성
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
                            label=_("2️⃣ ? 코딩 ?? ?식 ?운로드", "2️⃣ ? Download Excel Template"),
                            data=output_template,
                            file_name="AHP_Master_Template.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True,
                            type="primary"
                        )
                    
                    st.info(_("**?내:** 1?버튼???러 모델???성 ???했?니?? ?측??2?버튼???릭?여 컴퓨?에 코딩 ?? ?식 ?일????하?요.", 
                              "? **Info:** The model has been generated and saved. Click the 2nd button on the right to download the Excel template file to your computer."))
    
                    st.markdown(_("""
                    ---
                    ### ? ?이???력 가?드
                    1. **?? ?일 ?기**: ??버튼???러 ?운로드???? ?일???행?니??
                    2. **??비교 ?이???력**:
                        - **?쪽** ??????중요?면: **?수** ?력 (?? -3)
                        - **?른?* ??????중요?면: **?수** ?력 (?? 3)
                        - **?등**?면: `1` ?력
                    3. **?수 ?보 ?력**: A??ID), **B??Type)??그룹??력 (?? ?문가, 주? ??**
                    """,
                    """
                    ---
                    ### ? Data Input Guide
                    1. **Open the Excel file**: Run the Excel template downloaded above.
                    2. **Enter pairwise comparisons**:
                        - If the **left** item is more important: enter a **negative** value (e.g., -3)
                        - If the **right** item is more important: enter a **positive** value (e.g., 3)
                        - If they are **equal**: enter `1`
                    3. **Required Information**: Column A (ID), **Column B (Type) for group names (e.g., Expert, Public, etc.)**
                    """))
                    img_file = _("ahp_input_guide.png", "ahp_input_guide_en.png")
                    caption_text = _("[참고] ?문 ?답???????력?는 방법", "[Reference] How to enter survey responses into Excel")
                    if os.path.exists(img_file):
                        st.image(img_file, caption=caption_text)
        tab1_main_col.__exit__(None, None, None)
    

    with main_tab2:
        @st.fragment
        def _survey_setup_fragment():
            try:
                import retention_manager
                retention_manager.run_retention_check_silent()
            except Exception:
                pass
            st.header(_("AHP ?라???문 ?동 ?성 ?배포", "AHP Online Survey Auto-Generator & Deployer"))
            box_style = """
            <div style="background-color: #f8f9fc; border: none; border-radius: 8px; padding: 16px 20px; margin-bottom: 20px; color: #1e293b; font-size: 0.95em; line-height: 1.6; box-shadow: 0 2px 8px rgba(0,0,0,0.04);">
            """
            if st.session_state.user_id is None:
                msg = _(
                    "<strong>비회?도 ?라???문 ?을 미리 ?성??????습?다.</strong><br>"
                    "?성?신 ?용? 좌측 ?이?바?서 ?원가???로그?을 ?시?그?????어 바로 배포?실 ???습?다. (무료 ?원??기능 ?한 ?이 모든 기능 ?용 가??<br><br>"
                    "?답 ?이?는 ?동?신 구? ?프?드?트????됩?다. 배포 ???이?? ?상 기록?는지 반드???스?해 주세??<br>"
                    "?️ <strong>주의:</strong> ?동 ?제???트?크 ?애 ?으??한 ?이???실????서??책임지지 ?으므? 중요 ?이?는 주기?으?백업 ?보??시?바랍?다.",
                    
                    "<strong>Non-members can also preview and fill out the online survey form.</strong><br>"
                    "Once you sign up and log in from the left sidebar, the contents you have written will be maintained and you can deploy immediately. (Free members can also use all features without restriction)<br><br>"
                    "Response data is stored in your linked Google Spreadsheet. Please test data recording before deploying the survey.<br>"
                    "?️ <strong>Caution:</strong> We are not responsible for data loss due to unlinking or network failures. Please backup your important data periodically."
                )
            else:
                msg = _(
                    "?답 ?이?는 ?동?신 구? ?프?드?트????됩?다. 배포 ???이?? ?상 기록?는지 반드???스?해 주세??<br>"
                    "?️ <strong>주의:</strong> ?동 ?제???트?크 ?애 ?으??한 ?이???실????서??책임지지 ?으므? 중요 ?이?는 주기?으?백업 ?보??시?바랍?다.",
                    
                    "Response data is stored in your linked Google Spreadsheet. Please test data recording before deploying the survey.<br>"
                    "?️ <strong>Caution:</strong> We are not responsible for data loss due to unlinking or network failures. Please backup your important data periodically."
                )
            st.markdown(f"{box_style}{msg}</div>", unsafe_allow_html=True)
            def render_section_header(title):
                style = (
                    'background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);'
                    'color: #ffffff;'
                    'padding: 12px 20px;'
                    'border-radius: 6px;'
                    'font-weight: bold;'
                    'font-size: 1.1rem;'
                    'text-align: center;'
                    'letter-spacing: 0.5px;'
                    'margin-top: 25px;'
                    'margin-bottom: 15px;'
                    'box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);'
                    'border: 1px solid #334155;'
                )
                st.markdown(f'<div style="{style}">{title}</div>', unsafe_allow_html=True)

            col_survey_main, col_survey_settings = st.columns([3.0, 1.1], gap="large")
            with col_survey_settings:
                with st.container(border=True):
                    st.markdown(f'<h4 style="color:black; font-family:Arial, sans-serif; font-weight:bold; margin-top:0; margin-bottom:15px; font-size:1.1rem;">{_("???문 관?, "My Survey Management")}</h4>', unsafe_allow_html=True)

                    # Initialize states
                    if 'editing_survey_id' not in st.session_state:
                        st.session_state.editing_survey_id = None
                    if 'survey_auto_loaded' not in st.session_state:
                        st.session_state.survey_auto_loaded = False

                    # Check existing surveys (SQLite? 구? ?트 모두 조회?여 병합) ???션 캐싱
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
                            st.session_state.edit_age_type = demo.get("age_type", "개방??(?자 직접 ?력)")
                            st.session_state.edit_exp_type = demo.get("experience_type", "개방??(?자 직접 ?력)")

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

                    @st.dialog(_("? [경고] 기존 ?문 ?구 ?? ?내", "? [Warning] Permanent Deletion of Existing Survey"))
                    def confirm_new_survey():
                        st.error(_("?로???문???성?시?기존 ?동??구? ?트????된 **모든 ?이???문 구조, 문항, ?집???체 ?답 결과)가 즉시 ???며 ?? 복구?????습?다.**", "If you create a new survey, **ALL data saved in the linked Google Sheet (survey structure, questions, collected responses) will be immediately deleted and CANNOT be recovered.**"))
                        st.info(_("**?이??보존 ?내:** 기존 ?문???답 결과 보존???하?다? ?????의?시??에 구? ?프?드?트???속?여 **[?일] -> [?운로드]** 메뉴??해 ??(.xlsx) ?일 ?으?백업본을 ?용??컴퓨?에 미리 ?운로드???시?바랍?다.", "**Data Preservation Guide:** If you wish to keep the existing responses, please go to the Google Spreadsheet and use the **[File] -> [Download]** menu to download a backup copy (e.g., .xlsx) to your computer before agreeing to delete."))
                        agree = st.checkbox(_("?? 기존 ?이??백업???료?거??불필?하? 모든 ?이???????의?니??", "Yes, I have backed up or do not need the existing data, and I agree to delete all data."))
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button(_("??취소", "??Cancel"), use_container_width=True):
                                st.rerun()
                        with col2:
                            if st.button(_("???의 ?초기??, "??Agree & Initialize"), type="primary", use_container_width=True, disabled=not agree):
                                with st.spinner(_("기존 ?이?? ???는 중입?다...", "Deleting existing data...")):
                                    from survey_manager import delete_admin_survey
                                    if user_surveys:
                                        delete_admin_survey(user_surveys[0][0], st.session_state.user_id)
                                    st.session_state.editing_survey_id = None
                                    keys_to_clear = [k for k in st.session_state.keys() if k.startswith('edit_')]
                                    for k in keys_to_clear:
                                        del st.session_state[k]
                                    st.session_state.survey_auto_loaded = True
                                    st.session_state._survey_cache_dirty = True
                                st.success(_("?료?었?니?? ?면???로고침?니??", "Completed. The screen will be refreshed."))
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
                        st.success(_(f" ?재 배포???문??불러?습?다: **{survey_title_display}**", f" Loaded deployed survey: **{survey_title_display}**"))
                        st.info(_("?래 ?에???용???정?신 ???단??**[배포 ?DB ?동 (?정 ?용 ?용)]** 버튼???르?면 기존 ?트???용?????워집니??", "If you modify the form below and click the **[Deploy & Link DB (Apply Modifications)]** button at the bottom, the existing sheet will be overwritten."))
                        
                        # [?규] ?동??구? ?프?드?트 바로가???라???문 링크 ?시
                        base_url = st.query_params.get("base_url", ["https://ahpkrj.streamlit.app/"])[0] if isinstance(st.query_params.get("base_url"), list) else "https://ahpkrj.streamlit.app/"
                        if "localhost" in base_url or "127.0.0.1" in base_url:
                            active_survey_url = f"{base_url}?survey_id={linked_sheet_id}"
                        else:
                            active_survey_url = f"https://ahpkrj.streamlit.app/?survey_id={linked_sheet_id}"

                        st.markdown(_("##### ? ?라???문지 링크 (?답??배포??", "##### ? Online Survey Link (For Distribution)"))
                        st.code(active_survey_url, language="text")
                        st.caption(_("? ???문 링크?복사?여 ?메?이??메신???답 ??자?게 ?달?세??", "? Copy the survey link above and send it to respondents via email or messenger."))

                        gs_link = f"https://docs.google.com/spreadsheets/d/{linked_sheet_id}"
                        btn_label = _("?동??구? ?프?드?트 바로가?, "Open Linked Google Sheet")
                        st.markdown(f'''

                        <div class="gs-nav-btn-box">
                            <a href="{gs_link}" target="_blank">
                                ? {btn_label}
                            </a>
                        </div>
                        ''', unsafe_allow_html=True)

                    if st.button(_("??처음부?????문 ?성?기 (기존 ?이????)", "??Start a new survey from scratch (Delete existing data)"), type="secondary", use_container_width=True):
                         confirm_new_survey()
                    else:
                        if st.button(_("?????용 모두 지?기 (초기??", "??Clear all form contents (Initialize)"), type="secondary"):
                            st.session_state.editing_survey_id = None
                            keys_to_clear = [k for k in st.session_state.keys() if k.startswith('edit_')]
                            for k in keys_to_clear:
                                del st.session_state[k]
                            st.rerun()

                    st.divider()

                    # [?규] URL ?축 ?QR코드 ?성 지???비??링크 (가로줄 ??시 배치)
                    st.markdown(_("###### ? ?문 배포 ?용???구", "###### ? Useful Distribution Tools"))
                    st.markdown(_(
                        "??**?URL ?축**: [buly.kr 바로가??️](https://buly.kr/)\n\n"
                        "??**QR코드 ?성**: [qr.naver.com 바로가??️](https://qr.naver.com/)",
                        "??**Shorten Long URL**: [buly.kr ?️](https://buly.kr/)\n\n"
                        "??**Generate QR Code**: [qr.naver.com ?️](https://qr.naver.com/)"
                    ))

                    from survey_manager import create_survey_sheet

                    # ?위 ?? ?누지 ?고 ?나???결???이지?구성

            with col_survey_main:
                # 5??션 ?문지 ?성 ??구성
                # ?션 1: 기본 ?보
                render_section_header(_("?션 1: ?문 기본 ?보 ?정", "Section 1: Survey Basic Info Setup"))
                default_survey_title = _("?조???동로봇 ?입 ?인 중요??분석???한 ?문가 AHP ?문", "Expert AHP Survey on the Importance of Factors for Adopting Manufacturing Collaborative Robots")
                st.markdown(f"**{_('?문지 ?목', 'Survey Title')}**")
                survey_title = st.text_input(_('?문지 ?목', 'Survey Title'), value=st.session_state.get("edit_title", default_survey_title), label_visibility="collapsed")
            
                default_survey_desc_ko = """[조사 목적 ??내?

?녕?십?까?
??문조사??[?구/?로?트 주제]??관??주요 ?인?의 ????중요?? ?출?기 ?해 
?문가(?는 ?무?? ?러분의 고견???렴?고??마련?었?니??

바쁘?더?도 ?시 ?간???어 귀?의 귀중한 ?견???답??주시??구??????????것입?다.

??조사 목적 : [?구/?로?트 목적 기재]
??조사 ?용 : [조사 ????인] 간의 AHP(??비교) ??
??조사 기간 : 202X??X??X??~ 202X??X??X??
??개인?보 보호 :
  - ?조사??해 ?집??모든 ?료???계???3?비???보호)???거?여 철???보호?며, 
    ?직 ?구 ??계 분석 목적?로??용?니??
  - ?답?주??개인 ?보 ?개별 ?답 결과???? ????출?? ?음???속?립?다.

귀?의 ?중??참여??깊? 감사??립?다.

- ?구 책임??: [?름 기재]
- 문의?: [?락??는 ?메??기재]"""
    
                default_survey_desc_en = """[Survey Purpose & Instructions]

Greetings,
This survey is designed to gather the opinions of experts (or practitioners) to derive the relative importance 
of major factors regarding [Research/Project Topic].

Even if you are busy, taking a moment to provide your valuable input will be of great help to our research.

??Purpose : [Enter Research/Project Purpose]
??Content : AHP (Pairwise Comparison) evaluation among [Factors to be Surveyed]
??Period : [Start Date] ~ [End Date]
??Privacy :
  - All data collected through this survey is strictly protected under Article 33 (Protection of Secrets) 
    of the Statistics Act and will be used solely for research and statistical analysis purposes.
  - We promise that your personal information and individual responses will never be leaked externally.

Thank you deeply for your valuable participation.

- Lead Researcher : [Enter Name]
- Contact : [Enter Phone or Email]"""
    
                st.markdown(f"**{_('조사 목적 ??내?, 'Survey Purpose & Instructions')}**")
                
                from quill_editor import st_quill
                survey_desc = st_quill(
                    value=st.session_state.get("edit_desc", _(default_survey_desc_ko, default_survey_desc_en)),
                    key="quill_standard_desc_editor"
                )
                if survey_desc is None:
                    survey_desc = st.session_state.get("edit_desc", _(default_survey_desc_ko, default_survey_desc_en))
                st.session_state["edit_desc"] = survey_desc
                
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

                st.write("")
                # ?답???집 ?보 ?그룹 분류 ?정 (?션 1??합)

                # 그룹 분류 문항 ?정
                st.markdown(f"**{_('그룹 분류 문항 ?정', 'Group Classification Setup')}**")
                
                default_type_q = _("귀?의 ?속? ?떻??십?까?", "What is your affiliation?")
                default_type_opts = _("?문가, ?반, 공무?? 기?", "Expert, General, Public Official, Other")
                
                if "edit_type_questions" not in st.session_state:
                    legacy_q = st.session_state.get("edit_type_question")
                    legacy_opts = st.session_state.get("edit_type_options")
                
                    init_q = legacy_q if legacy_q and legacy_q != "귀?의 ?속? ?떻??십?까?" else default_type_q
                    init_opts = legacy_opts if legacy_opts and legacy_opts != "?문가, ?반, 공무?? 기?" else default_type_opts
                    st.session_state["edit_type_questions"] = [{"q": init_q, "opts": init_opts}]

                type_questions_state = st.session_state["edit_type_questions"]
                num_types = len(type_questions_state)
                
                col1, col2, col3 = st.columns([6, 2, 2])
                with col2:
                    if st.button(_("??문항 추?", "??Add Question"), use_container_width=True, disabled=num_types >= 3):
                        st.session_state["edit_type_questions"].append({"q": "", "opts": ""})
                        st.rerun()
                with col3:
                    if st.button(_("??문항 ??", "??Remove"), use_container_width=True, disabled=num_types <= 1):
                        st.session_state["edit_type_questions"].pop()
                        st.rerun()
                
                
                type_questions = []
                for i in range(num_types):
                    st.markdown(f"**{i+1}.**")
                    if i == 0:
                        q_label = _("그룹 분류 질문 ?목", "Group Classification Question Title")
                        opts_label = _("그룹 분류 보기 ?션 (?표?구분)", "Group Classification Options (comma-separated)")
                    else:
                        q_label = _("추? ?문 문항", "Additional Survey Question")
                        opts_label = _("추? 문항 보기 ?션 (?표?구분)", "Additional Question Options (comma-separated)")
                    
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


                # ?구?계???보 ?정
                st.markdown(f"**{_('?구?계?적 문항 ?집 ?정', 'Demographic Questions Setup')}**")
                demo_name = st.checkbox(_("?름 ?집", "Collect Name"), value=st.session_state.get("edit_demo_name", False))
                demo_gender = st.checkbox(_("?별 ?집", "Collect Gender"), value=st.session_state.get("edit_demo_gender", True))
                demo_email = st.checkbox(_("?메???집", "Collect Email"), value=st.session_state.get("edit_demo_email", True))




                demo_age = st.checkbox(_("?령 ?집", "Collect Age"), value=st.session_state.get("edit_demo_age", False))
                age_type = "개방??(?자 직접 ?력)"
                if demo_age:
                    age_type_options = [_("개방??(?자 직접 ?력)", "Open-ended (Type Number)"), _("10???위 ?택??, "Multiple Choice (10-year intervals)")]
                    age_type = st.radio(_("?령 ?집 방식", "Age Collection Method"), age_type_options, index=0 if st.session_state.get("edit_age_type", "개방??(?자 직접 ?력)") == "개방??(?자 직접 ?력)" else 1, horizontal=True, key="survey_age_type_setup")




                demo_exp = st.checkbox(_("경력?수 ?집", "Collect Years of Experience"), value=st.session_state.get("edit_demo_exp", False))
                exp_type = "개방??(?자 직접 ?력)"
                if demo_exp:
                    exp_type_options = [_("개방??(?자 직접 ?력)", "Open-ended (Type Number)"), _("5???위 ?택??, "Multiple Choice (5-year intervals)")]
                    exp_type = st.radio(_("경력?수 ?집 방식", "Experience Collection Method"), exp_type_options, index=0 if st.session_state.get("edit_exp_type", "개방??(?자 직접 ?력)") == "개방??(?자 직접 ?력)" else 1, horizontal=True, key="survey_exp_type_setup")

                demographics_settings = {
                    "name": demo_name,
                    "age": demo_age,
                    "age_type": age_type,
                    "gender": demo_gender,
                    "experience": demo_exp,
                    "experience_type": exp_type,
                    "affiliation": False,  # ?속 ?집 ??
                    "email": demo_email,
                    "type_question": type_question,
                    "type_options": [x.strip() for x in type_options.split(",") if x.strip()],
                    "type_questions": type_questions
                }






                with st.container():
                    # ?션 2: AHP 모델 계층구조 ?력 ??
                    render_section_header(_("?션 2: AHP ?인 계층구조 ?문항 ?정", "Section 2: AHP Criteria Hierarchy & Question Setup"))

                    # 계층 구조 ?택 (2계층 기???일?게 ?체 공개)
                    tier_level = 2


                    st.markdown(_("#####  계층 구조 ?벨 ?택", "#####  Select Hierarchy Level"))
                    tier_choice_tab2 = st.radio(
                        _("?문 모델??계층 깊이??택?세??", "Select the hierarchy depth for your survey model."),
                        [_("2계층 (?분류 ??중분?", "2-Tier (Main ??Sub)"),
                         _("3계층 (?분류 ??중분????분?", "3-Tier (Main ??Sub ??Sub-sub)")],
                        index=0,
                        horizontal=True,
                        key="tab2_tier_choice"
                    )
                    if _("3계층", "3-Tier") in tier_choice_tab2:
                        tier_level = 3



                    st.info(_(
                        "? ?재 ?력???인? **?시**??뿐이? ?용?의 ?구 모델??맞추???용??모두 ?정?여 ?용?????습?다.\n\n"
                        "- ?분류 ??위 ?인? 반드??**?표(,)** ?구분?여 ?력??주세??\n"
                        "- ?인명에 ?더?`_`) 기호???스???? 처리? 충돌????용?????습?다. (?력 ???동?로 공백?로 변?됩?다.)",
                        "? The current criteria are just **examples**. You can freely modify them to fit your research model.\n\n"
                        "- Separate Main and Sub criteria using **commas(,)**.\n"
                        "- Do not use underscores (`_`) in criteria names. (They will be automatically converted to spaces.)"
                    ))

                    default_tab2_main = _("기능?? ?자?? 경제??, "Functionality, Design, Economy") if tier_level == 3 else _("기술 ?인, 조직 ?인, ?경 ?인, ?신 ?인", "Technological, Organizational, Environmental, Innovational")
                    main_input = st.text_input(_("??? (Main Criteria)", "Main Criteria"), value=st.session_state.get("edit_main_input", default_tab2_main))
                    main_list = [x.strip().replace("_", " ") for x in main_input.split(",") if x.strip()]

                    model_structure = {"main": main_list, "subs": {}}
                    if tier_level == 3:
                        model_structure["sub_subs"] = {}

                    for i, mc in enumerate(main_list):
                        # 기본??안 (기존 ?승???동로봇 ?3계층 ?마?폰 구매 결정)
                        default_sub_val = ""
                        if mc in ["기술 ?인", "Technological"]: default_sub_val = _("???이?? ?환?? ?전?? ?비????, "Relative Advantage, Compatibility, Security, Service Support")
                        elif mc in ["조직 ?인", "Organizational"]: default_sub_val = _("경영진??? 기술준비도, 금융?원, 교육?련", "Top Management Support, Tech Readiness, Financial Resources, Training")
                        elif mc in ["?경 ?인", "Environmental"]: default_sub_val = _("??지?? 경쟁?력, ?력?? ??지??, "Gov Support, Competitive Pressure, Labor Shortage, External Support")
                        elif mc in ["?신 ?인", "Innovational"]: default_sub_val = _("경영진의 ?신?? 변?수?태?? ?마?팩?리??, 지?정??, "Management Innovativeness, Change Acceptance, Smart Factory Level, Knowledge Level")
                        elif mc in ["기능??, "Functionality"]: default_sub_val = _("?드?어, ?프?웨??, "Hardware, Software")
                        elif mc in ["?자??, "Design"]: default_sub_val = _("??, ?의??, "Appearance, Usability")
                        elif mc in ["경제??, "Economy"]: default_sub_val = _("?말기?? ??비용", "Device Price, Maintenance Cost")

                        sub_input = st.text_input(_(f"'{mc}'???위 ?인 (Sub-criteria)", f"Sub-criteria for '{mc}'"), value=st.session_state.get("edit_sub_inputs", {}).get(mc, default_sub_val))
                        subs_list = [x.strip().replace("_", " ") for x in sub_input.split(",") if x.strip()]
                        model_structure["subs"][mc] = subs_list

                        # [?규] 3계층 ?택 ???분??력 ?드 ?적 ?성
                        if tier_level == 3 and subs_list:
                            with st.expander(_(f"??'{mc}' ?위???분?(Sub-sub-criteria) ?력", f"??Enter Sub-sub-criteria under '{mc}'"), expanded=True):

                                for sub_c in subs_list:
                                    sub_sub_val = "" # 3계층 기본값? 빈칸
                                    if sub_c in ["?드?어", "Hardware"]: sub_sub_val = _("카메?? 배터? ?로?서", "Camera, Battery, Processor")
                                    elif sub_c in ["?프?웨??, "Software"]: sub_sub_val = _("?영체제, 기본??, "OS, Default Apps")
                                    elif sub_c in ["??", "Appearance"]: sub_sub_val = _("?상, ?질", "Color, Material")
                                    elif sub_c in ["?말기??, "Device Price"]: sub_sub_val = _("?시? ??", "Lump Sum, Installment")
                                    elif sub_c in ["??비용", "Maintenance Cost"]: sub_sub_val = _("?신?금, AS비용", "Telecom Fee, A/S Cost")
                        
                                    sub_sub_input = st.text_input(
                                        f"? '{sub_c}'???위 ?인 (?표 구분)", 
                                        value=st.session_state.get("edit_sub_sub_inputs", {}).get(sub_c, sub_sub_val),
                                        placeholder="?? ??1, ??2 (???위 ?인???다?비워?세??",
                                        help="?력칸을 비워?면 ????? ?동?로 2계층 구조?간주?어 분석?니??",
                                        key=f"sub_sub_{sub_c}"
                                    )
                                    # ?분류? ?력??경우?만 ??? ?으?무시
                                    parsed_sub_subs = [x.strip().replace("_", " ") for x in sub_sub_input.split(",") if x.strip()]
                                    if parsed_sub_subs:
                                        model_structure["sub_subs"][sub_c] = parsed_sub_subs

                    # ?? 계층 구조 ?리 ?각????????????????????????????????
                    if main_list:
                        st.markdown("---")
                        st.markdown(_("##### ? 계층 구조 미리보기", "##### ? Hierarchy Preview"))
                        tree_lines = []
                        for mi, mc in enumerate(main_list):
                            is_last_main = (mi == len(main_list) - 1)
                            prefix_main = "??? " if is_last_main else "??? "
                            tree_lines.append(f"{prefix_main}[{mc}]")
                            
                            subs = model_structure.get("subs", {}).get(mc, [])
                            sub_subs_map = model_structure.get("sub_subs", {})
                            for si, sc in enumerate(subs):
                                is_last_sub = (si == len(subs) - 1)
                                branch_main = "    " if is_last_main else "??  "
                                prefix_sub = "??? " if is_last_sub else "??? "
                                
                                sub_subs = sub_subs_map.get(sc, []) if tier_level == 3 else []
                                if sub_subs:
                                    tree_lines.append(f"{branch_main}{prefix_sub}{sc}")
                                    for ssi, ssc in enumerate(sub_subs):
                                        is_last_ss = (ssi == len(sub_subs) - 1)
                                        branch_sub = "    " if is_last_sub else "??  "
                                        prefix_ss = "??? " if is_last_ss else "??? "
                                        tree_lines.append(f"{branch_main}{branch_sub}{prefix_ss}{ssc}")
                                else:
                                    tree_lines.append(f"{branch_main}{prefix_sub}{sc}")
                        
                        tree_text = "\n".join(tree_lines)
                        st.code(tree_text, language=None)
                    # ??????????????????????????????????????????????????????

                    st.caption(_("????비교 ?작 ???답?? ?반???인 ?위?매기??'?전 중요???위 지??문항'? ?동?로 ?문???함?니??", "??A 'Prior Importance Ranking Question', where respondents rank the overall criteria before starting pairwise comparisons, is automatically included in the survey."))




                with st.container():
                    # ?션 3: ?인 조작???의 ?정
                    render_section_header(_("?션 3: ?인??세 ?명 (조작???의)", "Section 3: Detailed Description per Criteria (Operational Definition)"))
                    st.info(_("?답?? ?인 개념??직??으??악?????도??세 ?명??기술??주십?오.", "Please provide detailed descriptions so respondents can intuitively understand each criteria concept."))
                    definitions_map = {}
                    for i, mc in enumerate(main_list):
                        # ?분류?????볼드 ??모?콘???용?????정
                        st.markdown(_(f"####  :blue[**?분류: {mc}**]", f"####  :blue[**Main Criteria: {mc}**]"))
                        default_main_def = ""
                        if mc in ["기술 ?인", "Technological"]: default_main_def = _("?동로봇 ?입 ??기술???능, ?환?? ?전???기술 지????기술 측면???인", "Factors related to the technological aspect such as technical performance, compatibility, safety, and technical support.")
                        elif mc in ["조직 ?인", "Organizational"]: default_main_def = _("?동로봇 ?입?관?된 조직 ??????, 경영?지?? ?무 ?교육 ?태 ?인", "Factors related to the internal capabilities of the organization, top management support, financial and training status.")
                        elif mc in ["?경 ?인", "Environmental"]: default_main_def = _("?? 지?? ?업 ??경쟁 ?력, 구인????? ?력 ???? ?경???인", "External environmental factors such as government support, competitive pressure within the industry, labor shortage, and external cooperation.")
                        elif mc in ["?신 ?인", "Innovational"]: default_main_def = _("경영진의 ?신 지?성, 구성?의 변???용????마???토?지??기술 ?? ?인", "Factors such as the management's innovation orientation, members' acceptance of change, and smart factory knowledge/skill levels.")

                        edit_def_val = st.session_state.get("edit_definitions", {}).get(mc)
                        val_to_use = edit_def_val if edit_def_val is not None else (default_main_def or _(f"{mc}??????반???소??명?니??", f"Overall description for {mc}."))
                        val_to_use = translate_definition_if_default(mc, val_to_use)

                        definitions_map[mc] = st.text_input(
                            _(f"? [{mc}] ?인???체?인 ?명 ?력", f"? Enter overall description for [{mc}]"),
                            value=val_to_use,
                            key=f"def_main_{mc}_{i}"
                        )

                        # 중분류들? ?? 관계? 묶을 ???도??각?으?구분???두?컨테?너 ?에 배치
                        with st.container(border=True):
                            for j, sc in enumerate(model_structure["subs"].get(mc, [])):
                                # 기본 ?승???문 ?의 ?용
                                default_def = ""
                                if sc in ["???이??, "Relative Advantage"]: default_def = _("?입????동로봇간의 ?????점", "Relative advantage among the collaborative robots targeted for adoption.")
                                elif sc in ["?환??, "Compatibility"]: default_def = _("기존 ?비??????동로봇과의 ?결??, "Connectivity with existing equipment or third-party collaborative robots.")
                                elif sc in ["?전??, "Security"]: default_def = _("?업?? 같? 공간?서 ?전 ?스 ?이 ?업???의 ?적 ?고 ?방 ??", "Level of human accident prevention when working in the same space as operators without safety fences.")
                                elif sc in ["?비????, "Service Support"]: default_def = _("공급?의 기술 ?A/S 지???도", "Degree of technical and A/S support from the supplier.")
                                elif sc in ["경영진???, "Top Management Support"]: default_def = _("경영진의 ?입 ?? ?경영철학 반영??, "The management's willingness to adopt and the degree to which management philosophy is reflected.")
                                elif sc in ["기술준비도", "Tech Readiness"]: default_def = _("조직?의 로봇 ?용 기술 준???", "The level of technical readiness of organizational members to utilize robots.")
                                elif sc in ["금융?원", "Financial Resources"]: default_def = _("로봇 구입???한 ?본 ?력 ??금 조달 ?의??, "Capital capacity and financing convenience for purchasing robots.")
                                elif sc in ["교육?련", "Training"]: default_def = _("기술 ?상???한 ?탁/?내 교육 ?로그램 ?무", "Availability of external/internal training programs for skill improvement.")
                                elif sc in ["??지??, "Gov Support"]: default_def = _("?동로봇 ?입???성?하??한 ?????정 지???보조??택 ?도", "Degree of government financial support and subsidy benefits to promote the adoption of collaborative robots.")
                                elif sc in ["경쟁?력", "Competitive Pressure"]: default_def = _("?종 ?계 ?는 경쟁?의 ?동로봇 ?입???른 경쟁???박 ?도", "Degree of competitive pressure due to the adoption of collaborative robots by peers or competitors.")
                                elif sc in ["?력??, "Labor Shortage"]: default_def = _("?조 ?장??구인????산 ?력 ?급???려? ??", "Level of difficulty in finding labor and supplying production personnel at the manufacturing site.")
                                elif sc in ["??지??, "External Support"]: default_def = _("로봇 공급???의 ?? 컨설?? ?구기? ?의 기술??교육??지??, "Technical/educational support from external consulting, research institutes, etc., other than the robot supplier.")
                                elif sc in ["경영진의 ?신??, "Management Innovativeness"]: default_def = _("?로???조 기술 ?로봇 ?입?????최고경영?의 ?극?인 ??", "The top management's active willingness to adopt new manufacturing technologies and robots.")
                                elif sc in ["변?수?태??, "Change Acceptance"]: default_def = _("?규 ?비 ??업 ?로?스 변?에 ???구성?들???용 ??조 ?도", "Members' acceptance and cooperative attitude towards changes in new equipment and work processes.")
                                elif sc in ["?마?팩?리??", "Smart Factory Level"]: default_def = _("공장 ?????화, ?보?스??MES ?? ??동??기술???재 구축 ??", "Current level of implementation of digitalization, information systems (MES, etc.), and automation technology in the factory.")
                                elif sc in ["지?정??, "Knowledge Level"]: default_def = _("?동로봇 ?용 ??? 관리에 ?요??조직 ???문 지????", "Level of internal expertise required for the utilization and maintenance of collaborative robots.")

                                edit_sub_def_val = st.session_state.get("edit_definitions", {}).get(sc)
                                sub_val_to_use = edit_sub_def_val if edit_sub_def_val is not None else (default_def or _(f"{sc}??????의?니??", f"Definition for {sc}."))
                                sub_val_to_use = translate_definition_if_default(sc, sub_val_to_use)

                                definitions_map[sc] = st.text_input(
                                    _(f"??중분?[{sc}] ?명 ?력", f"? Enter description for sub-criteria [{sc}]"),
                                    value=sub_val_to_use,
                                    key=f"def_sub_{mc}_{sc}_{j}"
                                )
                        st.write("") # ?션 ??각???백 추?




                with st.container():
                    # ?션 4: 척도 ?터?이???정
                    render_section_header(_("?션 4: ??비교 ?답 척도 ?????CR) 검??벨 ?정", "Section 4: Scale Type & CR Validation Level Setup"))
                    scale_options = [
                        _("1-9 Continuous (1부??9까? ?속??????", "1-9 Continuous Scale"),
                        _("1-5 Continuous (1부??5까? ?속??????", "1-5 Continuous Scale"),
                        _("1-3-7-9 Discrete (?산??척도)", "1-3-7-9 Discrete Scale"),
                        _("1-3-5 Discrete (?산??척도)", "1-3-5 Discrete Scale")
                    ]
                    st.markdown(f"**{_('?답 척도 ???, 'Response Scale Type')}**")
                    default_scale = st.session_state.get("edit_scale_type", "1-9 Continuous")
                    scale_idx = 0
                    if "1-5" in default_scale and "Discrete" not in default_scale:
                        scale_idx = 1
                    elif "1-3-7-9" in default_scale:
                        scale_idx = 2
                    elif "1-3-5" in default_scale:
                        scale_idx = 3

                    scale_option = st.radio(_("?답 척도 ???, "Response Scale Type"), scale_options, index=scale_idx, label_visibility="collapsed")




                    # ?션 5: ?????개인?보 ?집 ?의 ?정
                    if st.session_state.get("user_id") == "shjeon":
                        st.markdown(_("#### ? [?택] ??????의 ?식 ?정 (shjeon ?용)", "#### ? [Optional] Reward & Consent Form Setup (shjeon only)"))
                        reward_enabled = st.toggle(_("????기프?콘 ?? ?공 ?성??, "Enable Rewards (e.g., Gifticons)"))
                        reward_desc = ""
                        if reward_enabled:
                            reward_desc = st.text_area(_("?????명", "Reward Description"), value=st.session_state.get("edit_reward_desc", "모든 ?문 ?답??마친 분들?게 ??벅스 ?메리카??기프?콘??발송???립?다."))
                
                        rewards_info = {
                            "enabled": reward_enabled,
                            "desc": reward_desc
                        }


                    else:
                        rewards_info = {"enabled": False}

                    # ????비율 (CR) 검??벨 ?정
                    st.markdown(_("**????비율 (CR) 검??벨 ?정**", "**Consistency Ratio (CR) Validation Level Setup**"))
                    # Get default index from edit state if editing, otherwise default to index 3 (0.2 ?하)
                    default_cr_idx = 3
                    if st.session_state.get("editing_survey_id") and st.session_state.get("edit_cr_limit") is not None:
                        cr_val = float(st.session_state.get("edit_cr_limit"))
                        if cr_val <= 0.1: default_cr_idx = 1
                        elif cr_val <= 0.15: default_cr_idx = 2
                        elif cr_val <= 0.2: default_cr_idx = 3
                        elif cr_val <= 0.3: default_cr_idx = 4
                    elif st.session_state.get("editing_survey_id") and st.session_state.get("edit_cr_limit") is None:
                        default_cr_idx = 0
            
                    cr_limit_opt = st.selectbox(_("????비율(CR) ?용 기??, "Consistency Ratio (CR) Tolerance Limit"), [
                        _("?한?? ?음 (?탈?감소??", "No Limit (To reduce drop-out rate)"),
                        _("0.1 ?하 (매우 ?격??", "0.1 or below (Very Strict)"),
                        _("0.15 ?하 (?격??", "0.15 or below (Strict)"),
                        _("0.2 ?하 (보통)", "0.2 or below (Normal)"),
                        _("0.3 ?하 (?? ?용)", "0.3 or below (Somewhat Lenient)")
                    ], index=default_cr_idx)

                    cr_limit = None
                    if "0.15" in cr_limit_opt: cr_limit = 0.15
                    elif "0.1" in cr_limit_opt: cr_limit = 0.1
                    elif "0.2" in cr_limit_opt: cr_limit = 0.2
                    elif "0.3" in cr_limit_opt: cr_limit = 0.3

                    if cr_limit is not None:
                        st.warning(_("?️ ????비율(CR) 기????무 ?격?게(??) ?정??경우, ?리??모순???는 ?문????무효 처리?어 ?답?의 ?????로?? 극??되??문 ?탈률이 급증?????으???의?시?바랍?다. ?답???탈??????해 ????비율 ?용 기?치? 0.3 ?하??유? ?정?고, ?이???집 ??AHP마스?의 ????보정 기능???해 ?후 보정?여 분석?시기? ?극 추천?립?다.", "?️ Warning: If the CR limit is set too strict (low), many logically inconsistent surveys will be invalidated. This maximizes respondent fatigue and can cause the survey drop-out rate to spike. To reduce respondent dropout, we strongly recommend setting the consistency ratio tolerance to 0.3 or less and post-calibrating the collected data using the AHP Master consistency calibration feature."))
                        # CR 가?드 방식 ?택
                        st.markdown(_("**?답????????(CR) 가?드 방식 ?택**", "**Select Consistency Ratio (CR) Guide Method for Respondents**"))
            
                        default_guide = st.session_state.get("edit_cr_guide_method", "realtime")
            
                        # Backward compatibility for old surveys that used toggle
                        if "edit_cr_guide_enabled" in st.session_state:
                            if st.session_state["edit_cr_guide_enabled"] and default_guide not in ["realtime", "post_wizard", "none"]:
                                default_guide = "realtime"
                            elif not st.session_state["edit_cr_guide_enabled"] and default_guide not in ["realtime", "post_wizard", "none"]:
                                default_guide = "none"
            
                        options_kr = {
                            "realtime": "?시?권장 범위 ?각???내 (?탈?최소?? ?의???음)",
                            "post_wizard": "?출 ??지?형 ?정 ?안 마법??(가???술?인 방식, ?향???거)",
                            "none": "????가?드 ?음(?격??검증만 ?행)"
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
                            label=_("가?드 방식???택?세??, "Choose guide method"),
                            options=[0, 1, 2],
                            format_func=lambda x: options_kr[list(options_kr.keys())[x]] if _("ko", "en") == "ko" else options_en[list(options_en.keys())[x]],
                            index=get_idx(default_guide),
                            label_visibility="collapsed"
                        )
            
                        cr_guide_method = list(options_kr.keys())[selected_idx]
            
                        if cr_guide_method == "realtime":
                            st.info(_("**?시??내**: ?답?? ?문 ????을 ???????도?????배경?로 권장?는 ?용 범위??내?니?? ?의?이 ?고 ?탈률을 ?게 ?? ???습?다.", "**Real-time Guide**: Highlights the recommended range with a blue background to help respondents maintain consistency. Highly convenient and reduces dropouts."))
                        elif cr_guide_method == "post_wizard":
                            st.success(_("? **지?형 ?정 ?안 (추천)**: ?답 중에???무??가?드?주? ?아 ?답?의 진짜 ?각???향 ?이 ?집?니?? ?출 버튼????????CR??초과?면, 가??모순??????1?문항??찾아?어 ?정??권고?는 마법?? ?웁?다.", "? **Smart Fix Wizard (Recommended)**: Collects true thoughts without bias by providing no guide during response. If CR exceeds the limit upon submission, a wizard will appear to suggest fixing the single most contradictory question."))
                        else:
                            st.warning(_("**?내 ?음**: ?답?에??떤 ?트??주? ?으? ?출 ??CR??초과?면 ?러 메시지? ?께 ?체 ???? ?구?니?? ?탈률이 ?아????습?다.", "**No Guide**: Gives no hints. If CR is exceeded upon submission, an error message is shown requiring a full review. Dropouts may increase."))
                    else:
                        cr_guide_method = "none"




                    # ?션 7: 최종 미리보기 ?배포
                    render_section_header(_("?션 5: ?????최종 미리보기 ?배포", "Section 5: Final Preview & Deployment Before Saving"))

                    # [추?] 구? ?프?드?트 ?동 ?정
                    if st.session_state.get('editing_survey_id'):
                        st.markdown(_("#####  기존 구? ?프?드?트 ?동 (?정 모드)", "#####  Existing Google Spreadsheet Integration (Edit Mode)"))
                        st.info(_("?재 **기존 ?문 ?정 모드**?진입?습?다. ?정???정 ?용? 기존 ?동??구? ?프?드?트???전?게 ???워집니??", "You have entered **Existing Survey Edit Mode**. The modified settings will be safely overwritten to the existing linked Google Spreadsheet."))
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
                        deploy_opts = [
                            _("??구? ?프?드?트 ?동 (직접 URL ?력)", "Link New Google Spreadsheet (Manual URL Input)")
                        ]
                        if len(past_surveys) > 0:
                            deploy_opts.append(_("기존 배포?던 ?문 URL ?사??(???기)", "Reuse Existing Deployed Survey URL (Overwrite)"))
                        
                        if len(deploy_opts) > 1:
                            st.markdown("##### ? 배포 방식 ?택 (Deployment Method)")
                            deploy_option = st.radio(
                                _("배포 방식???택??주세??", "Please select a deployment method."),
                                options=deploy_opts,
                                index=0,
                                key="deploy_option_radio",
                                label_visibility="collapsed"
                            )
                            st.write("")
                        else:
                            deploy_option = deploy_opts[0]
                
                        if "?사?? in deploy_option or "Reuse" in deploy_option:
                            st.markdown(_("##### ?️ ?사?할 기존 ?문 ?택", "##### ?️ Select Existing Survey to Reuse"))
                            survey_options = {f"{row[0]} ({row[2][:16]})" : row[1] for row in past_surveys}
                            selected_survey_label = st.selectbox(
                                _("과거??배포?던 ?문 목록", "List of previously deployed surveys"),
                                options=list(survey_options.keys())
                            )
                            existing_sheet_id_input = survey_options[selected_survey_label]
                            st.info(_("?택???문??구? ?프?드?트???로???용?????웁?다. 기존 ?답 URL? 그?????니??", "The new content will be overwritten on the Google Spreadsheet of the selected survey. The existing response URL will be maintained."))
                            
                        else:
                            st.markdown(_("##### ? 구? ?프?드?트 직접 ?동", "##### ? Link Google Spreadsheet Manually"))
                            st.warning(_(
                                "1. 본인 구? ?라?브?서 '??프?드?트'??로 만듭?다.\n"
                                f"2. ?측 ?단 [공유] 버튼???러 `{st.secrets.get('gcp_service_account', {}).get('client_email', '?비?계??)}` 계정??**?집??*?추??니??\n"
                                "3. ?당 ?프?드?트??주소(URL)?복사?여 ?래??붙여?습?다.",
                                "1. Create a 'Blank Spreadsheet' in your Google Drive.\n"
                                f"2. Click [Share] and add `{st.secrets.get('gcp_service_account', {}).get('client_email', 'service_account')}` as an **Editor**.\n"
                                "3. Copy and paste the spreadsheet URL below."
                            ))
                            import os
                            col1, col2 = st.columns([1, 2])
                            with col1:
                                if os.path.exists("google_sheets_menu_guide.png"):
                                    st.image("google_sheets_menu_guide.png", caption=_("구? ?프?드?트 메뉴 ?근 방법", "How to access Google Sheets menu"), use_container_width=True)
                            with col2:
                                if os.path.exists("manual_sheet_url_guide.png"):
                                    st.image("manual_sheet_url_guide.png", caption=_("구? ?프?드?트 URL 주소?복사 ?시", "Google Spreadsheet URL Copy Example"), use_container_width=True)
                            manual_url = st.text_input(_("?프?드?트 URL ?력", "Input Spreadsheet URL"), placeholder="https://docs.google.com/spreadsheets/d/...")
                            if manual_url:
                                existing_sheet_id_input = manual_url.strip()
                            else:
                                existing_sheet_id_input = ""




                    # Save current state for preview tab
                    preview_id = f"preview_{st.session_state.user_id if st.session_state.user_id else 'guest'}"
                    preview_data = {
                        "Title": survey_title,
                        "Description": survey_desc,
                        "Admin_Email": survey_admin_email,
                        "AHP_Model_JSON": model_structure,
                        "Tier_Level": tier_level, # [?규] 3계층 구분??
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
                                {_("???문지 ?답 ?면 미리보기", "??Preview Survey Form")}
                            </div>
                        </a>
                        """
                        st.markdown(preview_link_html, unsafe_allow_html=True)

                    with col_p2:
                        if st.session_state.user_id is None:
                            btn_label = _(" 무료 ?원가????배포?기", " Deploy after Free Sign Up")
                            if st.button(btn_label, type="primary", use_container_width=True):
                                import survey_manager; survey_manager.log_user_action(st.session_state.get("user_id") or "Guest", "?문 배포 ?행")
                                st.warning(_(" 배포 ?DB ?동? ?원가????가?합?다. (무료 ?용?도 ?한 ?이 배포 ??동 가?함)", " Deployment and DB integration are available after sign-up. (Free users can also deploy and link DB)"))
                                st.info(_("?심?세?? ?재 ?성?신 ?용? 창을 ?? ?고 ?쪽 ?이?바?서 ?원가??로그?을 ?료?시??아가지 ?고 그?????어 즉시 배포?실 ???습?다.", "Rest assured. The contents you have written will be maintained if you sign up and log in from the left sidebar without closing the window, allowing you to deploy immediately."))
                    
                                pass
                        else:
                            btn_label = _("?? 배포 ?DB ?동 (?정 ?용 ?용)", "?? Deploy & Link DB (Apply Changes)") if st.session_state.get("editing_survey_id") else _("?? 배포 ?DB ?동", "?? Deploy & Link DB")
                            if st.button(btn_label, type="primary", use_container_width=True):
                                import survey_manager; survey_manager.log_user_action(st.session_state.get("user_id") or "Guest", "?문 배포 ?행")
                                if not existing_sheet_id_input.strip():
                                    st.error(_("?동??구? ?프?드?트 URL 주소??력?거?? ?사?할 기존 ?문???택??주세??", "Please enter a valid Spreadsheet URL or select an existing survey to reuse."))
                                else:
                                    with st.spinner(_("구? ?프?드?트? ?문 구조??동?는 ?..", "Linking survey structure with Google Spreadsheet...")):
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



                                            # admin_surveys ?이블에 ?규 ?문 ?동 ?록 ?마스??구? ?트 백업
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

                                            # 배포 주소 ?성
                                            base_url = st.query_params.get("base_url", ["https://ahpkrj.streamlit.app/"])[0] if isinstance(st.query_params.get("base_url"), list) else "https://ahpkrj.streamlit.app/"
                                            if "localhost" in base_url or "127.0.0.1" in base_url:
                                                short_url = f"{base_url}?survey_id={sheet_id}"
                                            else:
                                                short_url = f"https://ahpkrj.streamlit.app/?survey_id={sheet_id}"

                                            # ?용??배포 ?계 ??문 링크 기록
                                            update_user_survey_distribution(st.session_state.user_id, short_url)
                                            st.session_state._survey_cache_dirty = True  # ?문 목록 캐시 무효??

                                            st.balloons()
                                            st.success(_("? AHP ?라???문지가 ?공?으??데?트(?정) ?었?니??", "? AHP online survey has been successfully updated!") if st.session_state.get("editing_survey_id") else _("? AHP ?라???문지 ??동 구? ?트 ?성???료?었?니??", "? AHP online survey and linked Google Sheet creation are complete!"))

                                            st.code(short_url, language="text")
                                            st.info(_("**?문 ?달 ?내:** ?성???문조사 링크?복사?여 ?메?이??메신?(카카?톡 ????답 ??자?게 ?달??주세??", "**Survey Sharing Guide:** Please copy the generated survey link and send it to respondents via email or messenger."))
                                            
                                            sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}"
                                            st.write("")
                                            st.markdown(f'''

                                            <div class="gs-nav-btn-box2">
                                                <a href="{sheet_url}" target="_blank">
                                                    ? ?동??구? ?프?드?트 바로가?(?답 ?이???시??인)
                                                </a>
                                            </div>
                                            ''', unsafe_allow_html=True)
                                            
                                            st.info(f"""**구? ?트 ??이???인 ?내:**
1. **즉시 ?인:** ?의 **[? ?동??구? ?프?드?트 바로가?** 버튼???릭?면 ?성???트?바로 ?동?니??
2. **?메???림:** 귀?의 구? 계정({survey_admin_email})?로 '?집??권한 공유' 초? 메일??발송?었?니?? 메일??링크??해?도 ?제???속?????습?다.
3. **구? ?라?브:** 본인??구? ?라?브 좌측 메뉴 ?**[공유 문서??(Shared with me)]**?서 ?제???당 ?문 ?트?찾고 ?이??Sheet 2: Raw_Data, Sheet 3: Demographic_Data)??인?거???운로드?????습?다.""")
                                        except Exception as ex:
                                            st.error(f"구? ?트 ?동 ?패: {ex}")
                                            import streamlit.components.v1 as components
                                            error_msg = str(ex).replace("'", "\\'").replace("\\n", " ")
                                            components.html(f"<script>alert('??구? ?프?드?트 ?동???패?습?다.\\n\\n?력?신 URL???프?드?트???근?????습?다.\\n?내???비??계정 ?메??ahp-master-v2@ahp-login.iam.gserviceaccount.com)??반드??[?집???추??고 공유??주셔???동 ?배포가 가?합?다.\\n\\n?세 ?러: {error_msg}');</script>", height=0, width=0)


        _survey_setup_fragment()

    # -------------------------------------------------------------------------
    # [?규] ?답?황 ??보????(Tab 3) ?세 구현
    # -------------------------------------------------------------------------
    with main_tab3:
        if st.session_state.get('user_id') == 'shjeon':
            # Sub-tabs UI: pill CSS??글로벌 ?마(global_ahp_css)???합??
            
            sub_tabs = st.tabs(["진행 ?황", "????발송 관?, "?????정(Admin)"])
            tab_live_content = sub_tabs[0]
            with sub_tabs[1]:
                import coupon_manager
                coupon_manager.render_dispatch_tab()
            with sub_tabs[2]:
                import coupon_manager
                coupon_manager.render_admin_tab()
        else:
            tab_live_content = st.container()

        with tab_live_content:
            st.header(_("?시??답 ?황", "Real-time Response Status"))
            selected_sheet_id = None
        
            if st.session_state.user_id is None:
                st.warning(_("로그?????용 가?한 ?원 ?용 ?비?입?다. (무료 ?원??모든 기능 ?용 가??",
                             "Member-only service. Log in to monitor responses. (Free members can use all features)"))
            else:
                # DB?서 ?당 관리자가 ?성???문 목록 조회
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
                    st.error(f"?문 목록 조회 ?패: {e}")

                if not admin_surveys:
                    st.warning("배포???문지가 존재?? ?습?다. '?라???문지 ?작' ?????문??먼? 배포??주세??")
                else:
                    # 로그?한 ?이?에 맞춰 본인???문?만 ?롭?운???출?킵?다.
                    survey_options = {f"{row[1]} ({row[2]})": row[0] for row in admin_surveys}
                    selected_label = st.selectbox(
                        "?시??황???인???문 ?택",
                        list(survey_options.keys()),
                        key="tab3_survey_select"
                    )
                    selected_sheet_id = survey_options[selected_label]
                
                    selected_survey_info = next(s for s in admin_surveys if s[0] == selected_sheet_id)
                    survey_title = selected_survey_info[1]
                    created_at = selected_survey_info[2]
                
                    st.success(f" ?재 ?택???문: **{survey_title}** (배포?시: {created_at})")
                    st.divider()

            # ??보???더?
            if selected_sheet_id:

                if st.button("? ?시??문 ??보????답 ?이??불러?기 / ?로고침", type="primary"):
                    from survey_manager import get_survey_stats, get_survey_gspread_client
                    with st.spinner("?시??문 ?황 로딩 ?.."):
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
                                st.error(f"구? ?트?서 ?이?? ?어?는 ??러 발생: {g_err}")
                                st.session_state["live_df"] = None
                        else:
                            st.warning("구? Sheets API ?라?언???결 ?패??해 구? ?트 ???이?? 직접 ?운로드?????습?다.")
                            st.session_state["live_df"] = None

                if "survey_stats" in st.session_state:
                    stats = st.session_state["survey_stats"]
                    col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
                    with col_stat1:
                        st.metric(_("??속????(Visits)", "Total Visits"), f"{stats['visits']}" + _("?, ""))
                    with col_stat2:
                        st.metric(_("?료 ?답????(Completed)", "Completed Responses"), f"{stats['completed']}" + _("?, ""))
                    with col_stat3:
                        st.metric(_("????초과 중단??(CR Fail)", "CR Fail Abandonments"), f"{stats['abandoned_cr']}" + _("??, " times"))
                    with col_stat4:
                        st.metric(_("?순 ?탈 중단??(Bounce)", "Bounced Visitors"), f"{stats['abandoned_bounce']}" + _("?, ""))

                    # ?각??차트 추?
                    import plotly.express as px

                    chart_data = pd.DataFrame({
                        "구분": ["?답 ?료", "????초과 중단", "?순 ?이지 ?탈"],
                        "?원??: [stats['completed'], stats['abandoned_cr'], stats['abandoned_bounce']]
                    })

                    fig_stats = px.bar(
                        chart_data,
                        x="구분",
                        y="?원??,
                        text="?원??,
                        color="구분",
                        color_discrete_map={
                            "?답 ?료": "#2E7D32",
                            "????초과 중단": "#C62828",
                            "?순 ?이지 ?탈": "#EF6C00"
                        },
                        title="?문 참여 ?태?분포"
                    )
                    fig_stats.update_layout(showlegend=False)
                    st.plotly_chart(fig_stats, use_container_width=True)

                if "live_df" in st.session_state and st.session_state["live_df"] is not None:
                    live_df = st.session_state["live_df"]
                    demo_df = st.session_state.get("demo_df", None)

                    # 구? ?트?서 ?시??답 로데?터(Raw_Data) ?운로드 기능 추?
                    with st.expander(_("? ?시?구? ?트 ?답 ?이???운로드 ?터", "? Real-time Google Sheet Response Data Download Center"), expanded=True):
                        if not live_df.empty:
                            st.success(f"구? ?프?드?트?서 ?시??답 ?이?? ?공?으?불러?습?다. (Raw_Data: {len(live_df)}? + (f", Demographic_Data: {len(demo_df)}? if demo_df is not None else "") + ")")
                        
                            # ? AHP 분석 ?동 ?축 버튼 추?
                            if st.button(_("? ???라???문 ?이?로 즉시 AHP 분석 ?행?기 (분석 ?구??동)", "? Perform AHP Analysis Instantly with this Online Survey Data"), type="primary", use_container_width=True):
                                import survey_manager; survey_manager.log_user_action(st.session_state.get("user_id") or "Guest", "?라???문 ?이???동")
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
                                
                                     # 중분?복사
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
                                    st.info(_("? ?이??분석 준비? ?료?었?니?? **?단??'? AHP 분석 ?구' ??*???택?고 **'? 배포???라???문 ?이???동'** ?디??버튼???택?여 분석 결과?바로 ?인?십?오.", "? Data analysis preparation is complete! Select the **'? AHP Analysis Tool' tab at the top** and choose the **'? Link Distributed Online Survey Data'** radio button to view the results instantly."))

                            tab_raw, tab_demo = st.tabs(["? Raw_Data (AHP ??비교 ?이??", "? Demographic_Data (?구?계/?전?위)"])
                            with tab_raw:
                                st.dataframe(live_df, use_container_width=True)
                            with tab_demo:
                                if demo_df is not None:
                                    st.dataframe(demo_df, use_container_width=True)
                                else:
                                    st.info("?집???구?계 ?이?? ?거??Demographic_Data ?트가 ?성?? ?았?니??")

                            # Excel ?CSV ?보?기 버튼 ?공
                            import io

                            # 1. Excel ?보?기 (??개의 ?트?모두 ?함)
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
                                    "? ?시??답 Excel ?운로드 (.xlsx)",
                                    data=excel_buffer.getvalue(),
                                    file_name=f"Survey_Live_Data_{selected_sheet_id.strip()[:6]}.xlsx",
                                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                    use_container_width=True,
                                    type="primary"
                                )
                            # 2. CSV ?보?기 (Raw_Data ?선 ?보?기)
                            csv_buffer = io.StringIO()
                            live_df.to_csv(csv_buffer, index=False, header=True)
                            with col_dl2:
                                st.download_button(
                                    "? ?시??답 CSV ?운로드 (.csv)",
                                    data=csv_buffer.getvalue().encode('utf-8-sig'),
                                    file_name=f"Survey_Live_Data_{selected_sheet_id.strip()[:6]}.csv",
                                    mime="text/csv",
                                    use_container_width=True
                                )
                        else:
                            st.info("구? ?트???집???답 로데?터가 ?직 비어 ?습?다.")

                # 로컬 ?전 백업 ?이??조회 ?추출 ?틸리티
                try:
                    conn = sqlite3.connect('users.db')
                    backup_df = pd.read_sql_query(
                        "SELECT id, respondent_id, response_json, created_at FROM survey_backup_responses WHERE survey_id = ?",
                        conn, params=(selected_sheet_id.strip(),)
                    )
                    conn.close()

                    if not backup_df.empty:
                        with st.expander("???버 로컬 ?전 백업 관??터"):
                            st.success(f"구? ?트 ?동?관계없???버 로컬 ?이?베?스????된 ?전 백업 ?이?? ?{len(backup_df)}?존재?니??")
                            st.dataframe(backup_df[["id", "respondent_id", "created_at"]], use_container_width=True)

                            # ?체 ??이??복구 ??/CSV ?이??빌드
                            recovered_raw_rows = []
                            recovered_demo_rows = []
                            for idx_b, r_b in backup_df.iterrows():
                                payload = json.loads(r_b["response_json"])
                                if "raw_row_data" in payload:
                                    recovered_raw_rows.append(payload["raw_row_data"])
                                elif "row_data" in payload:
                                    # ?위 ?환??
                                    recovered_raw_rows.append(payload["row_data"])

                                if "demo_row_data" in payload:
                                    recovered_demo_rows.append(payload["demo_row_data"])

                            if recovered_raw_rows:
                                import io

                                # ?더 복구 로직 추?
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
                                    raw_headers.append("?출?간")
                                
                                    demo_headers = ["ID", "Type"]
                                    if demographics.get("name"): demo_headers.append("?명")
                                    if demographics.get("age"): demo_headers.append("?령")
                                    if demographics.get("gender"): demo_headers.append("?별")
                                    if demographics.get("experience"): demo_headers.append("경력?수")
                                    # if demographics.get("affiliation"): demo_headers.append("?속")
                                    if demographics.get("email"): demo_headers.append("?메??)
                                    demo_headers.append("?전?위지??)
                                    if rewards_info.get("enabled"):
                                        demo_headers.append("경품?락? if tier_level == "3" else "?????락?)
                                    demo_headers.append("?출?간")

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

                                # Excel?백업 ?이?? ?플?구조??맞춰 분할?여 ?운로드
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
                                        "? 로컬 백업 Excel ?운로드 (.xlsx)",
                                        data=excel_backup_buffer.getvalue(),
                                        file_name=f"Backup_Recovery_{selected_sheet_id.strip()[:6]}.xlsx",
                                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                        use_container_width=True,
                                        type="primary"
                                    )

                                with col_b_dl2:
                                    # CSV ?일 ?태?복구 ?일 ?보?기 (Raw_Data ?선)
                                    output_csv = io.StringIO()
                                    df_raw_backup.to_csv(output_csv, index=False, header=bool(raw_headers))
                                    st.download_button(
                                        "? 로컬 백업 Raw_Data CSV ?운로드 (.csv)",
                                        data=output_csv.getvalue().encode('utf-8-sig'),
                                        file_name=f"Backup_Recovery_Raw_{selected_sheet_id.strip()[:6]}.csv",
                                        mime="text/csv",
                                        use_container_width=True
                                    )
                    else:
                        st.caption("???문지???록??로컬 ?버 백업 ?이?? ?습?다. (모든 ?이???상 ?재)")
                except Exception as err:
                    st.caption(f"로컬 백업 조회 불?: {err}")



    with main_tab_service:
        svc_tab_pricing, svc_tab_consulting, svc_tab_signup, svc_tab_quote, svc_tab_invoice = st.tabs([
            _("?비???금", "Pricing"),
            _("컨설??문의", "Consulting"),
            _("?원가??, "Sign Up"),
            _("견적??출력", "Estimate"),
            _("계산???수?, "Invoice")
        ])

        with svc_tab_pricing:
            st.markdown(_("## ?비???금 ?내 <span style='font-size: 0.95rem; font-weight: 500; color: #0284c7; margin-left: 16px; background: #e0f2fe; padding: 6px 14px; border-radius: 20px; vertical-align: middle; box-shadow: 0 1px 2px rgba(0,0,0,0.05);'>? ?구?법인카드 ?계산??지??/span>", "## Service Pricing <span style='font-size: 0.95rem; font-weight: 500; color: #0284c7; margin-left: 16px; background: #e0f2fe; padding: 6px 14px; border-radius: 20px; vertical-align: middle; box-shadow: 0 1px 2px rgba(0,0,0,0.05);'>? Research Cards & Invoices Supported</span>"), unsafe_allow_html=True)

            if st.session_state.lang == 'en':
                st.components.v1.html(get_unified_english_pricing_html(st.session_state.user_id), height=560)
            else:
                col_p1, col_p2, col_p3, col_p4 = st.columns(4)
                # 1개월
                with col_p1:
                    inner_1 = """
                        <h3 style='margin-top: 0 !important; margin-bottom: 0;'>Basic</h3>
                        <span style='color: #888; font-size: 1.1rem;'>2개월</span>
                        <h2 style='margin-top: 15px; margin-bottom: 5px; color: #ff4b4b;'><span id='basic-price-display-span'>300,000</span>??/h2>
                        <p style='font-size: 0.85rem; color: #666; min-height: 40px;'>?? AHP 방법론을 ?용?여 ?뢰???는 결과??출?는 ?규??로?트???합?니??</p>
                        <hr style='margin: 10px 0;'>
                        <ul style='font-size: 0.9rem; padding-left: 20px; color: #333; line-height: 1.6;'>
                            <li><b>?반 AHP 기능 ?공</b></li>
                            <li><b>?본 ?? 10?본 ?하</b></li>
                            <li>?로?트 ?성 무제??/li>
                            <li>?반 ?메??지??/li>
                        </ul>
                    """
                    if st.session_state.user_id:
                        st.components.v1.html(get_portone_payment_html(st.session_state.user_id, "Basic (2개월)", 300000, 2, inner_html=inner_1, is_best=False), height=520)
                    else:
                        st.components.v1.html(get_login_redirect_html("Basic (2개월)", inner_html=inner_1, is_best=False), height=520)

                # 3개월
                with col_p2:
                    inner_3 = """
                        <h3 style='margin-top: 0 !important; margin-bottom: 0;'>Standard</h3>
                        <span style='color: #888; font-size: 1.1rem;'>2개월</span>
                        <h2 style='margin-top: 15px; margin-bottom: 5px; color: #ff4b4b;'><span id='standard-price-display-span'>500,000</span>??/h2>
                        <p style='font-size: 0.85rem; color: #666; min-height: 40px;'>?답??그룹?차이 분석???해 보다 ?교??결론???출?는 ?문 리서치에 ?합?니??</p>
                        <hr style='margin: 10px 0;'>
                        <ul style='font-size: 0.9rem; padding-left: 20px; color: #333; line-height: 1.6;'>
                            <li><b>집단?차이 분석 (T-Test, ANOVA) ?공</b></li>
                            <li><b>?본??무제??/b></li>
                            <li>?로?트 ?성 무제??/li>
                            <li>?반 ?메??지??/li>
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
                        <h2 style='margin-top: 15px; margin-bottom: 5px; color: #ff4b4b;'>950,000??/h2>
                        <p style='font-size: 0.85rem; color: #666; min-height: 40px;'>고도?된 ?? AHP 분석?최우??기술 지?이 ?요???문 ?술지 ?고 ??구 기????합?니??</p>
                        <hr style='margin: 10px 0;'>
                        <ul style='font-size: 0.9rem; padding-left: 20px; color: #333; line-height: 1.6;'>
                            <li><b>?? AHP (Fuzzy AHP) 분석 기능 ?함</b></li>
                            <li>집단?차이 분석 (T-Test, ANOVA) ?공</li>
                            <li>?본??무제????로?트 무제??/li>
                            <li>최우??기술/?류 지??/li>
                            <li><b>?문 ?팅 1??무료 ???/b></li>
                        </ul>
                    """
                    if st.session_state.user_id:
                        st.components.v1.html(get_portone_payment_html(st.session_state.user_id, "Pro (2개월)", 950000, 2, inner_html=inner_6, is_best=False), height=520)
                    else:
                        st.components.v1.html(get_login_redirect_html("Pro (2개월)", inner_html=inner_6, is_best=False), height=520)

                # 부가 ?비?????
                with col_p4:
                    st.components.v1.html(get_portone_custom_services_html(st.session_state.user_id), height=520)

            st.markdown("<br><br>", unsafe_allow_html=True)


        with svc_tab_consulting:
            st.header(_("분석 문의 ?컨설???청", "Analysis Inquiry & Consulting Application"))

            # ?내 문구 ??화번호
            st.markdown(
                _("""
                <div style="background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%); border-left: 5px solid #475569; padding: 20px; margin-bottom: 24px; border-radius: 8px; box-shadow: 0 4px 12px rgba(15, 23, 42, 0.05); font-size: 0.95rem; line-height: 1.6;">
                  <h4 style="margin-top: -5px; margin-bottom: 12px; color: #1e293b; font-weight: bold; font-size: 1.1rem; display: flex; align-items: center; gap: 8px;">
                    <span>??/span> ?문 분석 ?AHP/?계 컨설??문의
                  </h4>
                  <p style="color: #475569; margin-bottom: 16px; font-size: 0.9rem;">
                    ?위?문, ?구보고?? 리서??로?트 ??AHP ??계 분석??????문?인 컨설?을 ?공???립?다.
                  </p>
                  <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px; background: white; padding: 12px 16px; border-radius: 6px; border: 1px solid #e2e8f0;">
                    <div style="font-weight: 600; color: #1e293b;">? ?화번호: <span style="color: #1e3a8a; font-weight: bold;">0507-1347-2610</span></div>
                    <div style="font-weight: 600; color: #1e293b;">? 카카?톡 ID: <span style="color: #1e3a8a; font-weight: bold;">AHPkr</span></div>
                  </div>
                  <div style="font-size: 0.85rem; color: #64748b; margin-top: 12px; font-weight: 500;">
                    ? 궁금?신 ?항? ?화, 카카?톡 ?는 ?래 문의 ?을 ?해 ?하??락주시??속?게 ?내???리겠습?다.
                  </div>
                </div>
                """, """
                <div style="background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%); border-left: 5px solid #475569; padding: 20px; margin-bottom: 24px; border-radius: 8px; box-shadow: 0 4px 12px rgba(15, 23, 42, 0.05); font-size: 0.95rem; line-height: 1.6;">
                  <h4 style="margin-top: -5px; margin-bottom: 12px; color: #1e293b; font-weight: bold; font-size: 1.1rem; display: flex; align-items: center; gap: 8px;">
                    <span>??/span> Professional AHP & Statistical Consulting
                  </h4>
                  <p style="color: #475569; margin-bottom: 16px; font-size: 0.9rem;">
                    We provide professional consultation on AHP and statistical analysis for academic theses, research reports, and market research.
                  </p>
                  <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px; background: white; padding: 12px 16px; border-radius: 6px; border: 1px solid #e2e8f0;">
                    <div style="font-weight: 600; color: #1e293b;">? Phone: <span style="color: #1e3a8a; font-weight: bold;">0507-1347-2610</span></div>
                    <div style="font-weight: 600; color: #1e293b;">? KakaoTalk ID: <span style="color: #1e3a8a; font-weight: bold;">AHPkr</span></div>
                  </div>
                  <div style="font-size: 0.85rem; color: #64748b; margin-top: 12px; font-weight: 500;">
                    ? Please feel free to call us, find KakaoTalk ID, or submit the form below. We will get back to you shortly.
                  </div>
                </div>
                """),
                unsafe_allow_html=True
            )

            with st.form(key="consulting_inquiry_form"):
                c_name = st.text_input(_("?함 (?수)", "Name (Required)"), key="c_name")
                c_company = st.text_input(_("?속 기?/?사/?교 (?택)", "Organization/Company/School (Optional)"), key="c_company")
                c_phone = st.text_input(_("?락?(?택)", "Contact Number (Optional)"), key="c_phone", placeholder="010-1234-5678")
                c_email = st.text_input(
                    _("?? 받으???메??(?수)", "Email to Receive Answer (Required)"),
                    value=st.session_state.get('user_id', '') if st.session_state.get('user_id') else '',
                    key="c_email"
                )

                c_type = st.selectbox(
                    _("문의 ?형 ?택 (?수)", "Select Inquiry Type (Required)"),
                    [
                        _("AHP 분석 ?컨설??, "AHP Analysis & Consulting"),
                        _("Fuzzy AHP 분석 ?컨설??, "Fuzzy AHP Analysis & Consulting"),
                        _("AHP ?라???문 ?팅 ???, "AHP Online Survey Setup Agency"),
                        _("????CR) ?류 보정 ?조정", "Consistency Ratio (CR) Error Correction"),
                        _("기? 분석 ??계 관??문의", "Other Statistical / Analysis Inquiries")
                    ],
                    key="c_type"
                )

                c_details = st.text_area(
                    _("?세 문의 ?용 (?수)", "Detailed Inquiry (Required)"),
                    placeholder=_("분석 목적, ?본 ?? 모형??계층 구조 ??구체?인 ?용??기재??주시????확?고 빠른 ?담??가?합?다.",
                                 "Please describe your project details, sample size, or structure for a faster response."),
                    key="c_details"
                )

                c_file = st.file_uploader(
                    _("관??참고 ?일 첨? (?택, 최? 10MB)", "Attach Reference File (Optional, Max 10MB)"),
                    type=["xlsx", "xls", "pdf", "docx", "zip", "png", "jpg"],
                    key="c_file"
                )

                c_submit = st.form_submit_button(_("문의?기", "Submit Inquiry"), use_container_width=True)

                if c_submit:
                    if not c_name.strip():
                        st.error(_("?함???력??주세??", "Please enter your name."))
                    elif not c_email.strip():
                        st.error(_("?메??주소??력??주세??", "Please enter your email address."))
                    elif not validate_email(c_email.strip()):
                        st.error(_("?바??메???식???닙?다.", "Invalid email format."))
                    elif not c_details.strip():
                        st.error(_("?세 문의 ?용???력??주세??", "Please enter the detailed inquiry."))
                    else:
                        with st.spinner(_("문의 ?용???송?는 ?..", "Submitting inquiry...")):
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
                                st.success(_("문의 ?청???공?으??수?었?니?? ?당?? ?인 ???속?게 ?락???리겠습?다.",
                                             "Your inquiry has been submitted successfully. We will get back to you shortly."))
                            else:
                                st.error(_("문의 메일 ?송 ??류가 발생?습?다. 관리자?게 ?메??jeon080423@gmail.com)?직접 ?락??주세??",
                                           "An error occurred while sending the email. Please contact jeon080423@gmail.com directly."))



        with svc_tab_quote:
            with st.expander(_("? 견적??출력", "? Print Estimate")):
                q_client = st.text_input(_("?뢰기??(?신)", "Client Institution"), placeholder=_("?? (??이치피?크", "e.g., HP Tech Co., Ltd."), key="q_client_input")
                q_project = st.text_input(_("과제?(?로?트?", "Project / Task Name"), placeholder=_("?? AHP 가중치 ?? 분석", "e.g., AHP Weight Assessment Analysis"), key="q_project_input")

                q_tier = st.selectbox(
                    _("?비??구분 (?금??", "Pricing Plan Tier"),
                    options=[
                        (_("Basic ?금??(300,000??", "Basic Plan (300,000 KRW)"), 300000, "Basic"),
                        (_("Standard ?금??(500,000??", "Standard Plan (500,000 KRW)"), 500000, "Standard"),
                        (_("Pro ?금??(950,000??", "Pro Plan (950,000 KRW)"), 950000, "Pro")
                    ],
                    format_func=lambda x: x[0],
                    key="q_tier_select"
                )

                clean_client = q_client.strip()
                clean_project = q_project.strip()

                if clean_client and clean_project:
                    plan_label, amount, plan_name = q_tier
                    q_html = get_quotation_html(clean_client, clean_project, amount, plan_name)

                    import json
                    escaped_html = json.dumps(q_html)

                    button_iframe = f"""
                    <script src="https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.10.1/html2pdf.bundle.min.js"></script>
                    <style>
                        .btn {{
                            width: 100%;
                            height: 38px;
                            background-color: #000000;
                            color: white;
                            border: 1px solid #000000;
                            border-radius: 4px;
                            font-weight: bold;
                            cursor: pointer;
                            font-size: 14px;
                            display: flex;
                            align-items: center;
                            justify-content: center;
                            font-family: sans-serif;
                        }}
                    </style>
                    <button class="btn" id="dl-pdf-btn">? 견적???운로드 (PDF)</button>
                    <div id="hidden-q-container" style="display: none; width: 720px; background: white; padding: 10px;"></div>

                    <script>
                        document.getElementById('dl-pdf-btn').onclick = function() {{
                            var container = document.getElementById('hidden-q-container');
                            container.innerHTML = {escaped_html};
                            container.style.display = 'block';

                            var opt = {{
                                margin:       [10, 10, 10, 10],
                                filename:     '견적??{clean_client}.pdf',
                                image:        {{ type: 'jpeg', quality: 0.98 }},
                                html2canvas:  {{ scale: 2.2, useCORS: true, logging: false }},
                                jsPDF:        {{ unit: 'mm', format: 'a4', orientation: 'portrait' }}
                            }};

                            html2pdf().from(container).set(opt).save().then(function() {{
                                container.style.display = 'none';
                            }});
                        }};
                    </script>
                    """
                    st.components.v1.html(button_iframe, height=45)
                else:
                    st.warning(_("견적???운로드??해 ?뢰기?명과 과제명을 먼? ?력??주세??",
                                 "Please enter the Client Institution and Project Name to enable download."))


        with svc_tab_invoice:
            with st.expander(_("? 계산???금?수??청", "? Request Invoice/Cash Receipt")):
                t_biz_num = st.text_input(_("?업???록번호", "Business Registration Number"), placeholder="000-00-00000", key="t_biz_num_input")
                t_biz_name = st.text_input(_("?호 (?사?", "Company Name"), key="t_biz_name_input")
                t_rep_name = st.text_input(_("??자?, "CEO Name"), key="t_rep_name_input")
                t_address = st.text_input(_("?업??주소", "Business Address"), key="t_address_input")
                t_biz_type = st.text_input(_("?태 / ?종", "Business Category / Type"), key="t_biz_type_input")
                t_email = st.text_input(_("계산???금?수??신 ?메??, "Invoice/Cash Receipt Email"), key="t_email_input")

                t_tier = st.selectbox(
                    _("?청 ?비??(?금??", "Pricing Plan for Invoice"),
                    options=[
                        (_("Basic ?금??(300,000??", "Basic Plan (300,000 KRW)"), "Basic"),
                        (_("Standard ?금??(500,000??", "Standard Plan (500,000 KRW)"), "Standard"),
                        (_("Pro ?금??(950,000??", "Pro Plan (950,000 KRW)"), "Pro")
                    ],
                    format_func=lambda x: x[0],
                    key="t_tier_select"
                )

                if st.button(_("계산???금?수??청?기", "Submit Invoice/Cash Receipt Request"), use_container_width=True, key="btn_request_tax"):
                    if not t_biz_num.strip():
                        st.error(_("?업???록번호??력??주세??", "Please enter the Business Registration Number."))
                    elif not t_biz_name.strip():
                        st.error(_("?호??력??주세??", "Please enter the Company Name."))
                    elif not t_rep_name.strip():
                        st.error(_("??자명을 ?력??주세??", "Please enter the CEO Name."))
                    elif not t_email.strip():
                        st.error(_("?메?을 ?력??주세??", "Please enter the Email."))
                    elif not validate_email(t_email.strip()):
                        st.error(_("?바??메???식???닙?다.", "Invalid email format."))
                    else:
                        with st.spinner(_("?청?? ?출?는 ?..", "Submitting request...")):
                            import sqlite3
                            conn = sqlite3.connect('users.db')
                            c = conn.cursor()
                            try:
                                import datetime
                                now_str = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).strftime("%Y-%m-%d %H:%M:%S")
                                c.execute("""
                                    INSERT INTO tax_invoice_requests
                                    (user_id, biz_num, biz_name, rep_name, address, biz_type, email, plan_name, request_date, status)
                                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                """, (st.session_state.user_id, t_biz_num.strip(), t_biz_name.strip(), t_rep_name.strip(), t_address.strip(), t_biz_type.strip(), t_email.strip(), t_tier[1], now_str, 'pending'))
                                conn.commit()

                                mail_success = send_tax_invoice_request_email(
                                    st.session_state.user_id, t_biz_num.strip(), t_biz_name.strip(), t_rep_name.strip(),
                                    t_address.strip(), t_biz_type.strip(), t_email.strip(), t_tier[0]
                                )

                                if mail_success:
                                    st.success(_("계산???금?수??청???수?었?니?? 관리자 ?인 ??발행?니??",
                                                 "Request submitted! The invoice will be issued after review."))
                                else:
                                    st.warning(_("DB ??? ?공?으???림 메일 발송???패?습?다. 관리자가 ?인 ???차 처리???리겠습?다.",
                                                 "Saved to DB, but email alert failed. The admin will review it soon."))
                            except Exception as e:
                                st.error(_(f"?청 ??류가 발생?습?다: {e}", f"Error during submission: {e}"))
                            finally:
                                conn.close()



    st.markdown("---")
    st.caption("© 2026 AHP Master. All rights reserved.")

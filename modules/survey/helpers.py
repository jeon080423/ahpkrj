"""
Survey 모듈 헬퍼 함수
- standard_app.py에서 추출 (Phase 2 NameError 수정, 2026-11-01)
- 팀 2 리뷰에서 발견된 NameError 11건 + 의존성 클로저 전체 포함
- 총 25개 함수/상수

주의: 이 모듈은 st.session_state를 직접 사용합니다.
원본 standard_app.py의 모듈 스코프와 동일한 동작을 보장하기 위해
의존성 클로저 전체를 함께 이전했습니다.
"""
import streamlit as st

# 명시적 import (LazyLoader 대체 — 모듈 독립성 확보)
import numpy as np
import pandas as pd
from scipy.stats import gmean
import json
import os
import re
import io
import time
import sqlite3
import base64
import logging
import random
import concurrent.futures
import gspread


# ============================================================
# i18n
# ============================================================

# 원본: standard_app.py L155-L161
def _(ko_text, en_text):
    try:
        if st.session_state.get('lang', 'ko') == 'en':
            return en_text
    except:
        pass
    return ko_text


# 원본: standard_app.py L164-L182
def _translate_single_chunk(text, target_lang='en', _retry=0):
    """단일 청크 번역 (내부용). 실패 시 원문 반환. 429 rate limit 시 재시도. 네트워크 타임아웃 10초 (2026-10-31 버그 수정)."""
    import concurrent.futures
    def _do_translate():
        from deep_translator import GoogleTranslator
        translator = GoogleTranslator(source='ko', target=target_lang)
        return translator.translate(str(text))
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
            fut = ex.submit(_do_translate)
            return fut.result(timeout=10)
    except Exception as e:
        err = str(e).lower()
        # Rate limit(429/TooManyRequests)이면 잠시 대기 후 재시도 (최대 3회)
        if ('toomanyrequests' in err or '429' in err or 'too many requests' in err) and _retry < 3:
            import time
            time.sleep(2 * (_retry + 1))
            return _translate_single_chunk(text, target_lang, _retry + 1)
        return text


# 원본: standard_app.py L185-L212
def translate_dynamic_text(text, target_lang='en'):
    if not text or not str(text).strip():
        return text
    text = str(text)
    # 긴 텍스트는 문단 단위로 나눠서 번역 (구글 번역 1회 요청 길이 제한 회피)
    # 1500자 이하이면 그대로 번역
    if len(text) <= 1500:
        return _translate_single_chunk(text, target_lang)
    chunks = []
    current = []
    current_len = 0
    for para in text.split('\n'):
        # 문단이 너무 길면 문장 단위로 추가 분할
        sub_paras = [para]
        if len(para) > 1500:
            import re as _re
            sub_paras = _re.split(r'(?<=[.!?。！？])\s+', para)
        for sp in sub_paras:
            if current_len + len(sp) + 1 > 1500 and current:
                chunks.append('\n'.join(current))
                current = []
                current_len = 0
            current.append(sp)
            current_len += len(sp) + 1
    if current:
        chunks.append('\n'.join(current))
    translated = [_translate_single_chunk(c, target_lang) for c in chunks if c.strip()]
    return '\n'.join(translated) if translated else text


# 원본: standard_app.py L226-L233
def _t(text):
    """Dynamically translates user-provided text if the current language is English."""
    try:
        if st.session_state.get('lang', 'ko') == 'en':
            return translate_dynamic_text(text, 'en')
    except:
        pass
    return text



# ============================================================
# constants
# ============================================================

# 원본: standard_app.py L234-L250
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


# 원본: standard_app.py L252-L267
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


# 원본: standard_app.py L270-L323
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


# 원본: standard_app.py L3103-L3106
FUZZY_SCALE = {
    1: (1.0, 1.0, 1.0), 2: (1.0, 2.0, 3.0), 3: (2.0, 3.0, 4.0), 4: (3.0, 4.0, 5.0), 5: (4.0, 5.0, 6.0),
    6: (5.0, 6.0, 7.0), 7: (6.0, 7.0, 8.0), 8: (7.0, 8.0, 9.0), 9: (9.0, 9.0, 9.0)
}



# ============================================================
# gspread
# ============================================================

# 원본: standard_app.py L1115-L1116
def get_main_spreadsheet_id():
    return st.secrets.get("SPREADSHEET_ID") or st.secrets.get("LOG_SPREADSHEET_ID") or "1xLvrH6LN8Vw3dVzoguf6TkgRrsJvEpMl2Z8s8HAvrVA"


# 원본: standard_app.py L1119-L1184
def get_gspread_client():
    from google.oauth2.service_account import Credentials
    import gspread
    scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    
    # st.secrets에서 값 가져오기 (없을 경우 에러 처리)
    if "gcp_service_account" not in st.secrets:
        st.error("Secrets에 'gcp_service_account' 설정이 없습니다.")
        return None

    raw_auth = st.secrets.get("gcp_service_account", {})
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


# 원본: standard_app.py L1186-L1209
def run_gspread_with_retry(func, *args, max_retries=6, initial_backoff=2, **kwargs):
    # [2026-10-24] max_retries 5→6: 백오프 합계(2+4+8+16+32≈62초+지터)가 분당 쿼터 윈도우(60초)를
    # 넘겨야 쿼터 소진 상황에서도 재시도가 성공할 수 있음 (5회·약 31초로는 윈도우 리셋 전에 포기했음)
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


# 원본: standard_app.py L1265-L1291
def _sync_short_codes_from_gs_impl():
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


# 원본: standard_app.py L1297-L1298
def _sync_short_codes_from_gs_cached():
    _sync_short_codes_from_gs_impl()


# 원본: standard_app.py L1301-L1305
def sync_short_codes_from_gs():
    try:
        _sync_short_codes_from_gs_cached()
    except Exception:
        pass



# ============================================================
# ahp_math
# ============================================================

# 원본: standard_app.py L3074-L3076
def get_ri(n):
    ri_dict = {1: 0.00, 2: 0.00, 3: 0.58, 4: 0.90, 5: 1.12, 6: 1.24, 7: 1.32, 8: 1.41, 9: 1.45, 10: 1.49}
    return ri_dict.get(n, 1.49)


# 원본: standard_app.py L3078-L3087
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


# 원본: standard_app.py L3089-L3101
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


# 원본: standard_app.py L3108-L3114
def saaty_to_fuzzy(v):
    try:
        val = max(1, min(9, int(round(v)))) if v >= 1 else max(1, min(9, int(round(1/v))))
        tfn = FUZZY_SCALE[val]
        if v < 1: return (1.0/tfn[2], 1.0/tfn[1], 1.0/tfn[0])
        return tfn
    except: return (1.0, 1.0, 1.0)


# 원본: standard_app.py L3116-L3133
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


# 원본: standard_app.py L3135-L3184
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
        
        # 0인 경우 1(동등)로 처리
        temp_raw = np.where(temp_raw == 0, 1, temp_raw).astype(int)
        
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


# 원본: standard_app.py L3186-L3197
def parse_input_value(val):
    """펀칭값(-9~-2, 1, 2~9)을 AHP 분석값으로 변환
    - 음수(-9~-2): 왼쪽 선호 → 절댓값 (9~2)
    - 1: 동등 → 1.0
    - 양수(2~9): 오른쪽 선호 → 역수 (1/2~1/9)
    """
    if val < 0:
        return abs(val)
    elif val == 1:
        return 1.0
    else:  # val >= 2
        return 1.0 / val


# 원본: standard_app.py L3199-L3231
def convert_df_punching_to_ahp(df, comp_col_names=None):
    """데이터프레임의 펀칭값을 AHP 분석값으로 변환한 복사본 반환
    - comp_col_names가 None이면 ID, Type, 제출시간 등을 제외한 모든 컬럼을 변환 대상으로 간주
    - 변환 불가 값(NaN, 문자 등)은 그대로 유지
    """
    import pandas as pd
    import numpy as np
    result = df.copy()
    # 변환 제외 컬럼
    exclude = {'id', 'type', '제출시간', 'timestamp', '타임스탬프', '기타', 'other', '보상'}
    for col in result.columns:
        c_str = str(col).strip()
        c_lower = c_str.lower()
        if c_lower in exclude or c_str.endswith('_기타') or c_str.endswith('(기타)'):
            continue
        if comp_col_names is not None and col not in comp_col_names:
            continue
        def _conv(v):
            try:
                if pd.isna(v):
                    return v
                num = float(v)
                if int(num) != num:
                    return v
                iv = int(num)
                valid = set(list(range(-9, -1)) + [1] + list(range(2, 10)))
                if iv not in valid:
                    return v
                return parse_input_value(iv)
            except (ValueError, TypeError):
                return v
        result[col] = result[col].apply(_conv)
    return result


# 원본: standard_app.py L3233-L3250
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


# 원본: standard_app.py L3273-L3439
def process_single_sheet(df, cr_threshold, max_iter, learning_rate, method='geometric', ahp_method='traditional'):

    # ID와 인구통계(Type), 기타 직접입력 컬럼을 제외한 나머지를 쌍대비교 컬럼으로 간주
    def _is_comp_col(col_name):
        c_str = str(col_name).strip()
        c_lower = c_str.lower()
        if c_lower == 'id' or c_lower.startswith('type') or c_lower in ['제출시간', 'timestamp', '타임스탬프', '기타', 'other', '보상']:
            return False
        if c_str.endswith('_기타') or c_str.endswith('(기타)'):
            return False
        return True

    comp_cols = [c for c in df.columns if _is_comp_col(c)]
    meta_cols = [c for c in df.columns if c not in comp_cols]
    factors, n = infer_factors_from_columns(comp_cols)
    
    # 시트 전체 데이터의 로우데이터 최대값/최솟값 계산
    all_comp_values = pd.to_numeric(df[comp_cols].values.flatten(), errors='coerce')
    valid_comp_values = all_comp_values[~np.isnan(all_comp_values)]
    sheet_min = -9
    sheet_max = 9
    if len(valid_comp_values) > 0:
        sheet_min = min(-9, int(np.min(valid_comp_values)))
        sheet_max = max(9, int(np.max(valid_comp_values)))
    
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
        format_error_detail = ""
        for i in range(n):
            for j in range(i + 1, n):
                if col_idx < len(comp_cols):
                    raw_val = row[comp_cols[col_idx]]
                    raw_values.append(raw_val)
                    
                    try:
                        num_val = float(raw_val)
                        # 유효값: -9~-2, 1, 2~9 (정수)
                        # -1, 0은 입력 불가 / 범위를 벗어난 값도 오류
                        valid_values = set(list(range(-9, -1)) + [1] + list(range(2, 10)))
                        if pd.isna(num_val) or int(num_val) != num_val or int(num_val) not in valid_values:
                            has_format_error = True
                            # 오류 상세 기록 (사용자 안내용)
                            if not pd.isna(num_val):
                                try:
                                    iv = int(num_val)
                                    if iv == 0 or iv == -1:
                                        format_error_detail = f"'{comp_cols[col_idx]}' 컬럼에 허용되지 않은 값 '{raw_val}'이(가) 있습니다. 동등은 1로 입력하세요."
                                    elif not (-9 <= iv <= 9):
                                        format_error_detail = f"'{comp_cols[col_idx]}' 컬럼의 값 '{raw_val}'이(가) 허용 범위(-9~9)를 벗어났습니다."
                                    else:
                                        format_error_detail = f"'{comp_cols[col_idx]}' 컬럼의 값 '{raw_val}'이(가) 올바르지 않습니다."
                                except:
                                    format_error_detail = f"'{comp_cols[col_idx]}' 컬럼에 숫자가 아닌 값 '{raw_val}'이(가) 있습니다."
                    except (ValueError, TypeError):
                        has_format_error = True
                        format_error_detail = f"'{comp_cols[col_idx]}' 컬럼에 숫자가 아닌 값 '{raw_val}'이(가) 있습니다."
                    
                    if not has_format_error:
                        ahp_val = parse_input_value(num_val)
                        matrix[i, j] = ahp_val
                        matrix[j, i] = 1.0 / ahp_val
                    col_idx += 1
                    
        if has_format_error:
            excluded_count += 1
            ex_res = meta_data.copy()
            for k, col_name in enumerate(comp_cols):
                _rv = raw_values[k] if k < len(raw_values) else np.nan
                try:
                    _rv = parse_input_value(float(_rv))
                except (ValueError, TypeError):
                    pass
                ex_res[col_name] = _rv
            ex_res["CR"] = f"데이터 오류(Format Error): {format_error_detail}" if format_error_detail else "데이터 오류(Format Error)"
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
                _rv = raw_values[k]
                try:
                    _rv = parse_input_value(float(_rv))
                except (ValueError, TypeError):
                    pass
                ex_res[col_name] = _rv
            ex_res["CR"] = final_cr
            excluded_list.append(ex_res)
            continue

        # 보정 후 데이터 (AHP 값 그대로 저장, 2026-10-18 변경: 펀칭값으로 역변환하지 않음)
        final_raw_values = []
        for i in range(n):
            for j in range(i + 1, n):
                val = final_matrix[i, j]
                final_raw_values.append(round(float(val), 4))

        _unused_cr, final_ci, _unused_lambda = calculate_consistency(final_matrix, method)
        if ahp_method == 'fuzzy':
            final_weights, final_Si = fuzzy_ahp_analysis(final_matrix)
        else:
            final_weights = calculate_weights(final_matrix, method)
        
        # 결과 딕셔너리 구성 (요청사항 5 재배치 반영)
        res = meta_data.copy()
        
        # [수정] 1. 보정 전 데이터 삽입 (AHP 변환값으로 저장, 2026-10-18)
        for k, col_name in enumerate(comp_cols):
            try:
                _ov = parse_input_value(float(raw_values[k]))
            except (ValueError, TypeError):
                _ov = raw_values[k]
            res[f"Raw_Orig_{col_name}"] = _ov
        
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


# 원본: standard_app.py L4102-L4113
def _ss_blocks_in_order(ahp_model):
    """[2026-10-21 버그수정] 소분류 블록을 모델 순서(대분류→중분류)대로 반환: [(중분류, [쌍 이름...]), ...]"""
    blocks = []
    sub_map = ahp_model.get("subs", {}) or {}
    ss_map = ahp_model.get("sub_subs", {}) or {}
    for main_c in ahp_model.get("main", []) or []:
        for sub_c in sub_map.get(main_c, []) or []:
            sss = ss_map.get(sub_c, []) or []
            if len(sss) >= 2:
                pairs = [f"{sss[i]}_{sss[j]}" for i in range(len(sss)) for j in range(i + 1, len(sss))]
                blocks.append((sub_c, pairs))
    return blocks


# 원본: standard_app.py L4116-L4154
def _extract_ss_block_df(df, base_cols, blocks, sub_c, pairs):
    """[2026-10-21 버그수정] 소분류(잎)별 쌍대비교 블록을 df에서 분리해 평문 쌍 이름 컬럼으로 반환.
    - 접두(SS::{중분류}::) 컬럼이 있으면 선택 후 접두사를 벗긴다.
    - 평문 컬럼이 중복 등장하면(구 Raw_Data 형식) 모델 순서 기준 해당 블록을 위치로 선택한다.
    - 어느 쪽도 아니면 기존 동작처럼 존재하는 평문 컬럼만 선택한다.
    """
    base_sel = [c for c in base_cols if c in df.columns]
    prefixed = [f"SS::{sub_c}::{p}" for p in pairs]
    if all(p in df.columns for p in prefixed):
        out = df[base_sel + prefixed].copy()
        out.columns = base_sel + list(pairs)
        return out
    col_list = list(df.columns)
    if all(p in col_list for p in pairs) and any(col_list.count(p) > 1 for p in pairs):
        occ_map = {}
        for b_sub, b_pairs in blocks:
            if b_sub == sub_c and list(b_pairs) == list(pairs):
                break
            for p in b_pairs:
                occ_map[p] = occ_map.get(p, 0) + 1
        base_idx = [i for i, c in enumerate(col_list) if c in base_cols]
        pick = []
        ok = True
        for p in pairs:
            occ = [i for i, c in enumerate(col_list) if c == p]
            want = occ_map.get(p, 0)
            if len(occ) == 1:
                pick.append(occ[0])
            elif want < len(occ):
                pick.append(occ[want])
            else:
                ok = False
                break
        if ok:
            out = df.iloc[:, base_idx + pick].copy()
            out.columns = base_sel + list(pairs)
            return out
    plain_sel = [p for p in pairs if p in df.columns]
    return df[base_sel + plain_sel].copy()


# 원본: standard_app.py L4157-L4217
def export_to_template_excel(raw_df, demo_df, ahp_model, tier_level=2, to_ahp_values=False):
    """템플릿 구조 엑셀 생성
    - to_ahp_values=True이면 쌍대비교 펀칭값을 AHP 분석값으로 변환하여 저장
    """
    import io
    import pandas as pd

    # AHP 변환값으로 저장 옵션
    if to_ahp_values and raw_df is not None and not raw_df.empty:
        raw_df = convert_df_punching_to_ahp(raw_df)

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
            _ss_blocks = _ss_blocks_in_order(ahp_model)
            for main_c, subs in sub_criteria_map.items():
                for sub_c in subs:
                    sub_subs = sub_sub_map.get(sub_c, [])
                    if len(sub_subs) >= 2:
                        sub_sub_pairs = []
                        for i in range(len(sub_subs)):
                            for j in range(i + 1, len(sub_subs)):
                                sub_sub_pairs.append(f"{sub_subs[i]}_{sub_subs[j]}")
                        df_sub_sub = _extract_ss_block_df(raw_df, base_cols, _ss_blocks, sub_c, sub_sub_pairs)
                        safe_sheet_name = str(sub_c)[:31]
                        df_sub_sub.to_excel(writer, index=False, sheet_name=safe_sheet_name)
                        
        # 4. Demographic Data
        if demo_df is not None and not demo_df.empty:
            demo_df.to_excel(writer, index=False, sheet_name="Demographic_Data")
            
    return excel_buffer



# ============================================================
# survey_ops
# ============================================================

# 원본: standard_app.py L325-L357
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
    
    # 2. Pattern matches for "{factor}에 대한 정의입니다." or "{factor}에 대한 정의 입니다."
    pattern1 = rf"^(?:{re.escape(factor_name)}|{re.escape(trans_factor)})\s*에\s*대한\s*정의\s*입니다\.?$"
    if re.match(pattern1, clean_def):
        return f"Definition for {trans_factor}."
        
    pattern2 = rf"^(?:{re.escape(factor_name)}|{re.escape(trans_factor)})\s*에\s*대한\s*전반적\s*요소를\s*설명합니다\.?$"
    if re.match(pattern2, clean_def):
        return f"Overall description for {trans_factor}."
        
    return _t(def_text)


# 원본: standard_app.py L2585-L2636
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
        if client and get_main_spreadsheet_id():
            spreadsheet = run_gspread_with_retry(client.open_by_key, get_main_spreadsheet_id())
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


# 원본: standard_app.py L9281-L9352
def show_reset_survey_dialog(sheet_id, survey_title):
    from survey_manager import reset_survey_responses
    
    st.markdown(_(
        f"선택된 설문: **{survey_title}**\n\n"
        "이 작업은 설문 문항 및 설정(Survey_Metadata)은 그대로 보존하고, **수집된 모든 응답 데이터(Raw_Data, Demographic_Data, Main_Criteria 및 기준별 시트의 2행 이하)만 완전히 삭제**합니다.\n\n"
        "💡 **언제 사용하나요?** 테스트 목적으로 입력한 가짜/테스트 응답을 깨끗이 비우고, 실제 대상자 모집을 시작하기 직전에 유용합니다.",
        f"Selected Survey: **{survey_title}**\n\n"
        "This will preserve survey structure and settings, but **permanently delete all collected response rows**.\n\n"
        "💡 **When to use?** Useful for clearing test responses before officially launching the survey."
    ))
    
    st.warning(_(
        "⚠️ **주의**: 삭제된 데이터는 복구할 수 없습니다. 안전을 위해 '자동 백업 시트 생성' 옵션을 켜두시기를 강력히 권장합니다.",
        "⚠️ **Warning**: Deleted data cannot be recovered. Enabling the 'Auto-backup Sheet' option is strongly recommended."
    ))
    
    do_backup = st.checkbox(
        _("🛡️ 초기화 전 구글 시트 내에 백업 시트('Raw_Backup_날짜시간') 자동 생성 (권장)",
          "🛡️ Automatically create a backup sheet in Google Sheets before reset (Recommended)"),
        value=True,
        key="chk_reset_backup"
    )
    
    agree = st.checkbox(
        _("위 내용을 충분히 확인하였으며, 응답 데이터를 삭제하고 초기화하는 데 동의합니다.",
          "I have read and understood the warning, and I agree to delete response data."),
        value=False,
        key="chk_reset_agree"
    )
    
    confirm_text = st.text_input(
        _("확인을 위해 아래에 **초기화** 또는 **RESET**을 직접 입력하세요:",
          "Type **RESET** below to confirm:"),
        key="txt_reset_confirm"
    )
    
    is_confirmed = agree and (confirm_text.strip() in ["초기화", "RESET", "reset"])
    
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        if st.button(_("❌ 취소", "❌ Cancel"), use_container_width=True, key="btn_cancel_reset"):
            st.rerun()
    with col_c2:
        if st.button(
            _("🗑️ 영구 초기화 실행", "🗑️ Execute Permanent Reset"),
            type="primary",
            use_container_width=True,
            disabled=not is_confirmed,
            key="btn_exec_reset"
        ):
            with st.spinner(_("구글 시트 응답 데이터를 안전하게 초기화 중입니다...", "Resetting survey response data safely...")):
                res = reset_survey_responses(sheet_id, create_backup=do_backup, user_id=st.session_state.get("user_id"))
                if res.get("success"):
                    deleted_cnt = res.get("deleted_count", 0)
                    backup_name = res.get("backup_sheet_name")
                    msg_ko = f"✅ 총 {deleted_cnt}건의 응답 데이터가 성공적으로 초기화되었습니다!"
                    if backup_name:
                        msg_ko += f"\n(구글 시트에 백업 시트 '{backup_name}' 생성 완료)"
                    msg_en = f"✅ Successfully cleared {deleted_cnt} responses!"
                    if backup_name:
                        msg_en += f"\n(Backup sheet '{backup_name}' created in Google Sheet)"
                    st.success(_(msg_ko, msg_en))
                    
                    # 로컬 세션 상태 초기화
                    for k in ["ahp_df_main", "ahp_sub_dfs", "ahp_sub_sub_dfs", "live_df", "demo_df", "survey_stats"]:
                        st.session_state.pop(k, None)
                    import time
                    time.sleep(2.0)
                    st.rerun()
                else:
                    st.error(_(f"초기화 실패: {res.get('error')}", f"Reset failed: {res.get('error')}"))



import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import yeta_utils
import math
import os
import sqlite3
import datetime
import hashlib
import string
import random
import re
import smtplib
import time
import base64
import json
import gspread
from google.oauth2.service_account import Credentials
from email.mime.text import MIMEText
import signup_agreement

# Helper function for Korean translation fallback
def _(ko_text, en_text):
    if st.session_state.get('lang', 'ko') == 'en':
        return en_text
    return ko_text

# --- AUTH & DB UTILITIES ---
def hash_password(password: str) -> str:
    """SHA-256 Hash a password with a fixed salt for security."""
    salt = "ahp_master_secure_salt_2026"
    return hashlib.sha256((password + salt).encode('utf-8')).hexdigest()

def generate_temp_password() -> str:
    """가입 시 비밀번호 유효성 검사를 통과하는 8자리 임시 비밀번호를 생성합니다."""
    chars = string.ascii_letters + string.digits
    specials = "!@#$%^&*"
    temp = [
        random.choice(string.ascii_lowercase),
        random.choice(string.ascii_uppercase),
        random.choice(string.digits),
        random.choice(specials)
    ]
    temp += [random.choice(chars) for _ in range(4)]
    random.shuffle(temp)
    return "".join(temp)

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
        
        # 평문 패스워드가 정확히 일치하거나 해시 패스워드가 일치하는 경우
        if stored_pw == pw or stored_pw == hashed_pw:
            # 평문 패스워드로 로그인 성공한 경우, 즉시 해시 패스워드로 업데이트 (보안 승급)
            if stored_pw == pw:
                upgrade_user_password_to_hash(user_id, pw)
            return stored_role, stored_expiry, stored_plan, stored_customer
            
    return None

def change_user_password(user_id, new_pw):
    hashed_pw = hash_password(new_pw)
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("UPDATE users SET pw=? WHERE id=?", (hashed_pw, user_id))
    conn.commit()
    conn.close()
    
    try:
        client = get_gspread_client()
        spreadsheet_id = st.secrets.get("SPREADSHEET_ID")
        if client and spreadsheet_id:
            spreadsheet = client.open_by_key(spreadsheet_id)
            sheet = spreadsheet.sheet1
            cell = sheet.find(user_id)
            if cell:
                sheet.update_cell(cell.row, 4, hashed_pw)
    except Exception:
        pass
    return True

# --- MISSING HELPERS ADDED ---
def num_to_kor(num):
    units = ["", "십", "백", "천"]
    g_units = ["", "만", "억", "조"]
    digits = ["", "일", "이", "삼", "사", "오", "육", "칠", "팔", "구"]
    
    if num == 0:
        return "영"
        
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
    if kor.startswith("일십"):
        kor = kor[1:]
    return f"일금 {kor}원정"

def get_quotation_html(client_name, project_name, amount, plan_name):
    today = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
    today_str = today.strftime("%Y년 %m월 %d일")
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
        stamp_element = '<div class="stamp">전상현<br>인</div>'
    
    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>견적서</title>
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
    <div class="title">견 적 서</div>
    
    <div class="main-layout">
        <div class="info-left">
            <ul class="meta-list">
                <li><span class="lbl">■ 과 제 명 :</span> {project_name}</li>
                <li><span class="lbl">■ 의뢰기관 :</span> {client_name}</li>
                <li><span class="lbl">■ 서비스명 :</span> AHP 의사결정 분석 솔루션(AHP마스터)</li>
                <li><span class="lbl">■ 소요예산 :</span> {kor_amount} (\\₩{amount:,}, VAT 포함)</li>
                <li><span class="lbl">■ 작성일 :</span> {today_str}</li>
                <li><span class="lbl">■ 담 당 자 :</span> 전상현 / jeon080423@gmail.com / 0507-1347-2610</li>
            </ul>
        </div>
        <div class="info-right">
            <table class="provider-table">
                <tr>
                    <th rowspan="4" style="width: 25px; font-size: 11px;">공<br>급<br>자</th>
                    <th>상호</th>
                    <td>프레쉬인사이트</td>
                </tr>
                <tr>
                    <th>등록번호</th>
                    <td style="font-size: 11px; font-weight: bold;">683-27-00122</td>
                </tr>
                <tr>
                    <th>주소</th>
                    <td style="font-size: 11px;">인천 부평구 원길로 12, 가동 203호 (갈산동, 선우빌딩)</td>
                </tr>
                <tr>
                    <th>대표자</th>
                    <td>
                        <div class="stamp-container">
                            전 상 현
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
                <th style="width: 25%;">비 목</th>
                <th style="width: 20%;">금 액</th>
                <th style="width: 35%;">산 출 내 역</th>
                <th style="width: 20%;">비 고</th>
            </tr>
        </thead>
        <tbody>
            <tr style="height: 35px;">
                <td style="font-weight: bold; background: #eee;">1. 경비 소계</td>
                <td></td>
                <td></td>
                <td></td>
            </tr>
            <tr style="height: 50px;">
                <td style="text-align: left; padding-left: 20px;">
                    AHP 분석<br>솔루션 이용료 ({plan_name})
                </td>
                <td style="text-align: right;">{amount:,}</td>
                <td>{amount:,} 원 X 1 식</td>
                <td>AHPMASTER</td>
            </tr>
            <tr style="height: 90px;">
                <td></td>
                <td colspan="2" style="color: #666; font-size: 12px; vertical-align: top; padding-top: 15px;">이하 여백</td>
                <td></td>
            </tr>
            <tr class="sum-row" style="height: 35px;">
                <td>총 합 계</td>
                <td style="text-align: right;">{amount:,}</td>
                <td></td>
                <td></td>
            </tr>
        </tbody>
    </table>
    
    <div style="font-weight: bold; font-size: 12px; margin-bottom: 10px;">※ 간이과세자</div>
</body>
</html>
"""

def send_tax_invoice_request_email(user_id, biz_num, biz_name, rep_name, address, biz_type, email, plan_name):
    sender_email = "jeon080423@gmail.com"
    password = st.secrets.get("EMAIL_PASSWORD", "csuh xxru wqdy mttt")
    recipient_email = "jeon080423@gmail.com"
    subject = f"[AHP 마스터] 계산서 발행 신청 접수 ({biz_name})"
    body = f"""
[AHP 마스터 계산서 신청 알림]

- 신청 ID: {user_id}
- 사업자 등록번호: {biz_num}
- 상호(회사명): {biz_name}
- 대표자명: {rep_name}
- 사업장 주소: {address}
- 업태/업종: {biz_type}
- 수신 이메일 주소: {email}
- 신청 요금제: {plan_name}
- 신청 시간: {datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).strftime('%Y-%m-%d %H:%M:%S')} (KST)
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
# -----------------------------
def get_yeta_login_redirect_html(plan_name="무료 체험판", inner_html="", is_best=False):
    border_css = "border: 2px solid #ff4b4b;" if is_best else "border: 1px solid #ddd;"
    best_badge = "<div style='position: absolute; top: -12px; right: 15px; background-color: #ff4b4b; color: white; padding: 3px 12px; border-radius: 12px; font-size: 0.8rem; font-weight: bold;'>BEST</div>" if is_best else ""
    
    if "무료" in plan_name or "0" in plan_name:
        btn_label = "분석기로 이동"
    elif "기관" in plan_name:
        btn_label = "로그인 후 B2B 신청"
    else:
        btn_label = "로그인 후 결제"
        
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
          <button class="btn" onclick="redirectAction()">{btn_label}</button>
      </div>
      <script>
        function redirectAction() {{
            if ("{plan_name}".includes("무료 체험판")) {{
                const tabs = window.parent.document.querySelectorAll('button[data-baseweb="tab"]');
                for (let i = 0; i < tabs.length; i++) {{
                    if (tabs[i].innerText.includes('예타 종합평가(AHP) 분석') || tabs[i].innerText.includes('Preliminary Feasibility')) {{
                        tabs[i].click();
                        window.parent.scrollTo(0, 0);
                        return;
                    }}
                }}
            }}
            
            const tabs = window.parent.document.querySelectorAll('button[data-baseweb="tab"]');
            for (let i = 0; i < tabs.length; i++) {{
                if (tabs[i].innerText.includes('회원가입') || tabs[i].innerText.includes('Sign Up')) {{
                    tabs[i].click();
                    window.parent.scrollTo(0, 0);
                    return;
                }}
            }}
            alert('로그인 또는 회원가입이 필요합니다. 메인 화면 또는 사이드바에서 로그인을 해주세요.');
            window.parent.scrollTo(0, 0);
        }}
      </script>
    </body>
    </html>
    """

def get_yeta_portone_payment_html(user_id, plan_name="단건 분석권", amount=300000, months=2, inner_html="", is_best=False):
    import hashlib
    login_token = hashlib.sha256(f"{user_id}:AHP_MASTER_SECURE_SALT_2026_!@#".encode()).hexdigest()
    safe_email = user_id.strip() if user_id and "@" in user_id else "test@ahp.kr"
    
    event_cfg = get_event_settings()
    is_cfg_active = event_cfg["active"]
    event_title = event_cfg["title"]
    event_desc = event_cfg["desc"]
    event_deadline_str = event_cfg["deadline"]
    event_discount = event_cfg["discount"]
    
    kst_now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
    try:
        event_deadline = datetime.datetime.strptime(event_deadline_str, "%Y-%m-%d")
        event_deadline = event_deadline.replace(hour=23, minute=59, second=59, tzinfo=datetime.timezone(datetime.timedelta(hours=9)))
    except Exception:
        event_deadline = datetime.datetime(2026, 7, 30, 23, 59, 59, tzinfo=datetime.timezone(datetime.timedelta(hours=9)))
        
    is_event_active = is_cfg_active and kst_now <= event_deadline and plan_name == "단건 분석권"
    
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
                할인 신청 ({event_discount:,}원 즉시 할인)
            </label>
            <div id="event-inputs" style="display: none; flex-direction: column; gap: 4px; background: white; padding: 6px 24px 6px 10px; border-radius: 4px; border: 1px solid #e2e8f0; margin-top: 4px;">
                <div style="display: flex; align-items: center; gap: 4px;">
                    <span style="color: #334155; font-weight: 600; font-size: 0.68rem; min-width: 36px;">대학명:</span>
                    <input type="text" id="univ-name" placeholder="예: 한국대 대학원" style="flex-grow: 1; padding: 3px 5px; border: 1px solid #cbd5e1; border-radius: 3px; font-size: 0.68rem; outline: none; font-family: inherit; height: 22px; box-sizing: border-box;">
                </div>
                <div style="display: flex; align-items: center; gap: 4px;">
                    <span style="color: #334155; font-weight: 600; font-size: 0.68rem; min-width: 36px;">논문명:</span>
                    <input type="text" id="thesis-title" placeholder="예: AHP 의사결정 연구" style="flex-grow: 1; padding: 3px 5px; border: 1px solid #cbd5e1; border-radius: 3px; font-size: 0.68rem; outline: none; font-family: inherit; height: 22px; box-sizing: border-box;">
                </div>
            </div>
        </div>
        """

    if plan_name == "무료 체험판 (영구)":
        btn_onclick = "redirectAnalysis()"
        btn_label = "체험하기"
    elif plan_name == "연간 라이선스":
        btn_onclick = "scrollToB2B()"
        btn_label = "세금계산서/인보이스 신청"
    else:
        btn_onclick = "openPaymentWindow()"
        btn_label = f"결제 {plan_name}"

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
          <button class="btn" onclick="{btn_onclick}">{btn_label}</button>
      </div>
      <script>
        let isEventApplied = false;
        const originalAmount = {amount};
        let finalAmount = originalAmount;

        function toggleEvent() {{
            const agreeCheckbox = document.getElementById("event-agree");
            const inputDiv = document.getElementById("event-inputs");
            const priceSpanOuter = window.parent.document.getElementById("yeta-single-price-display-span");
            
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
            
            if (priceSpanOuter) {{
                priceSpanOuter.innerText = finalAmount.toLocaleString();
            }}
        }}

        function redirectAnalysis() {{
            const tabs = window.parent.document.querySelectorAll('button[data-baseweb="tab"]');
            for (let i = 0; i < tabs.length; i++) {{
                if (tabs[i].innerText.includes('예타 종합평가(AHP) 분석') || tabs[i].innerText.includes('Preliminary Feasibility')) {{
                    tabs[i].click();
                    window.parent.scrollTo(0, 0);
                    return;
                }}
            }}
        }}

        function scrollToB2B() {{
            const b2bEl = window.parent.document.getElementById("b2b-payment-section");
            if (b2bEl) {{
                b2bEl.scrollIntoView({{ behavior: 'smooth' }});
            }} else {{
                alert('하단의 B2B 세금계산서/인보이스 발행 요청 서식을 작성해 주세요.');
            }}
        }}

        function openPaymentWindow() {{
          let univ = "";
          let thesis = "";
          
          if (isEventApplied) {{
              const uInput = document.getElementById("univ-name");
              const tInput = document.getElementById("thesis-title");
              univ = uInput ? uInput.value.trim() : "";
              thesis = tInput ? tInput.value.trim() : "";
              
              if (!univ) {{
                  alert("이벤트 혜택 적용을 위해 대학명을 입력해 주세요.");
                  if (uInput) uInput.focus();
                  return;
              }}
              if (!thesis) {{
                  alert("이벤트 혜택 적용을 위해 논문명을 입력해 주세요.");
                  if (tInput) tInput.focus();
                  return;
              }}
          }}

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

          let baseOrigin = window.location.origin;
          try {{
             if (window.top && window.top.location && window.top.location.origin && window.top.location.origin !== "null") {{
                 baseOrigin = window.top.location.origin + window.top.location.pathname;
             }}
          }} catch(e) {{}}
          if (baseOrigin.endsWith("/")) {{ baseOrigin = baseOrigin.slice(0, -1); }}
          
          let eventParams = "&event_applied=" + (isEventApplied ? "Y" : "N") + 
                            "&university=" + encodeURIComponent(univ) + 
                            "&thesis_title=" + encodeURIComponent(thesis);
                            
          const returnUrl = baseOrigin + "/?portone_paid=true&mode=yeta&user_id=" + encodeURIComponent("{user_id}") + "&login_user=" + encodeURIComponent("{user_id}") + "&login_token=" + encodeURIComponent("{login_token}") + "&months={months}&plan_name=" + encodeURIComponent("{plan_name}") + eventParams;
          
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
              totalAmount: finalAmount,
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

def get_yeta_portone_custom_services_html(user_id=None):
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
              견적서 발급 및 부가서비스 문의: <br>카톡아이디: <b>AHPkr</b>
          </div>
          
          <button class="btn" id="payBtn" onclick="handlePayAction()">결제하기</button>
      </div>
      
      <script>
        function updatePrice() {{
            const opt1 = document.getElementById("svc_opt_1");
            const opt2 = document.getElementById("svc_opt_2");
            const opt3 = document.getElementById("svc_opt_3");
            const optExt = document.getElementById("svc_opt_ext");
            
            let total = 0;
            let count = 0;
            if (opt1.checked) {{ total += parseInt(opt1.value); count++; }}
            if (opt2.checked) {{ total += parseInt(opt2.value); count++; }}
            if (opt3.checked) {{ total += parseInt(opt3.value); count++; }}
            if (optExt && optExt.checked) {{ total += parseInt(optExt.value); count++; }}
            
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
            const optExt = document.getElementById("svc_opt_ext");
            
            let total = 0;
            let items = [];
            let addMonths = 0;
            if (opt1.checked) {{ total += parseInt(opt1.value); items.push(opt1.getAttribute("data-name")); }}
            if (opt2.checked) {{ total += parseInt(opt2.value); items.push(opt2.getAttribute("data-name")); }}
            if (opt3.checked) {{ total += parseInt(opt3.value); items.push(opt3.getAttribute("data-name")); }}
            if (optExt && optExt.checked) {{ total += parseInt(optExt.value); items.push(optExt.getAttribute("data-name")); addMonths = 1; }}
            
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
          
          let baseOrigin = window.location.origin;
          try {{
             if (window.top && window.top.location && window.top.location.origin && window.top.location.origin !== "null") {{
                 baseOrigin = window.top.location.origin + window.top.location.pathname;
             }}
          }} catch(e) {{}}
          if (baseOrigin.endsWith("/")) {{ baseOrigin = baseOrigin.slice(0, -1); }}
          
          const returnUrl = baseOrigin + "/?portone_paid=true&mode=yeta&user_id=" + encodeURIComponent("{user_id}") + "&login_user=" + encodeURIComponent("{user_id}") + "&login_token=" + encodeURIComponent("{login_token}") + "&months=" + addMonths + "&plan_name=" + encodeURIComponent("부가 서비스: " + planName);
          
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

# -----------------------------
def validate_email(email):
    return re.match(r"[^@]+@[^@]+\.[^@]+", email)

def validate_password(password):
    if len(password) < 4: return False
    has_char = re.search(r'[a-zA-Z]', password)
    has_special = re.search(r'[!@#$%^&*(),.?":{}|<>]', password)
    return has_char and has_special

def upgrade_user_password_to_hash(user_id, pw):
    hashed_pw = hash_password(pw)
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("UPDATE users SET pw=? WHERE id=?", (hashed_pw, user_id))
    conn.commit()
    conn.close()
    
    try:
        client = get_gspread_client()
        spreadsheet_id = st.secrets.get("SPREADSHEET_ID")
        if client and spreadsheet_id:
            spreadsheet = client.open_by_key(spreadsheet_id)
            sheet = spreadsheet.sheet1
            cell = sheet.find(user_id)
            if cell:
                sheet.update_cell(cell.row, 4, hashed_pw)
    except Exception:
        pass

# --- GOOGLE SHEETS & MEMBER MANAGEMENT ---
@st.cache_resource
def get_gspread_client():
    scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    raw_auth = st.secrets.get("gcp_service_account")
    if not raw_auth:
        return None
    auth_info = {}
    if isinstance(raw_auth, dict) or hasattr(raw_auth, "keys"):
        auth_info = dict(raw_auth)
    elif isinstance(raw_auth, str):
        auth_str = raw_auth.strip().strip('"').strip("'")
        try:
            auth_info = json.loads(auth_str)
        except json.JSONDecodeError:
            try:
                clean_b64 = re.sub(r'\s+', '', auth_str)
                missing_padding = len(clean_b64) % 4
                if missing_padding:
                    clean_b64 += '=' * (4 - missing_padding)
                try:
                    decoded_bytes = base64.b64decode(clean_b64)
                except Exception:
                    decoded_bytes = base64.urlsafe_b64decode(clean_b64)
                decoded_info = decoded_bytes.decode('utf-8')
                auth_info = json.loads(decoded_info)
            except Exception:
                return None
    else:
        return None

    if auth_info and "private_key" in auth_info:
        auth_info["private_key"] = auth_info["private_key"].replace("\\n", "\n")
    required_fields = ["private_key", "client_email", "token_uri"]
    missing = [f for f in required_fields if f not in auth_info]
    if missing:
        return None

    creds = Credentials.from_service_account_info(auth_info, scopes=scope)
    return gspread.authorize(creds)

def run_gspread_with_retry(func, *args, max_retries=5, initial_backoff=2, **kwargs):
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

@st.cache_data(ttl=300, show_spinner=False)
def get_cached_visit_logs(spreadsheet_id):
    try:
        client = get_gspread_client()
        if client:
            spreadsheet = run_gspread_with_retry(client.open_by_key, spreadsheet_id)
            try:
                visit_sheet = run_gspread_with_retry(spreadsheet.worksheet, "Visit_Logs")
                records = run_gspread_with_retry(visit_sheet.get_all_records)
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
    except Exception:
        return []

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
        "title": "[이벤트] 학위논문 5만원 할인 (~7/30)",
        "desc": "석/박사 대상. 제목/대학명 사이트 내 공개 동의 필수",
        "deadline": "2026-07-30",
        "discount": 50000
    }

def sync_db_from_sheets(silent=False):
    conn = None
    try:
        client = get_gspread_client()
        spreadsheet_id = st.secrets.get("SPREADSHEET_ID")
        if not client or not spreadsheet_id: 
            return -1
        spreadsheet = run_gspread_with_retry(client.open_by_key, spreadsheet_id)
        sheet = run_gspread_with_retry(lambda: spreadsheet.sheet1)
        all_values = run_gspread_with_retry(sheet.get_all_values)
        
        if len(all_values) > 1:
            conn = sqlite3.connect('users.db', timeout=30.0)
            c = conn.cursor()
            cnt = 0
            processed_ids = set()
            for row in all_values[1:]:
                if len(row) >= 4:
                    user_id = str(row[0]).strip()
                    if not user_id or user_id in processed_ids:
                        continue
                    processed_ids.add(user_id)
                    
                    role = str(row[1]).strip()
                    signup_date = str(row[2]).strip()
                    pw = str(row[3]).strip()
                    
                    survey_count = 0
                    last_survey_link = ""
                    customer_type = "standard"
                    if len(row) >= 12:
                        expiry_date = str(row[4]).strip()
                        agree_info = str(row[5]).strip()
                        try:
                            survey_count = int(row[6])
                        except:
                            survey_count = 0
                        last_survey_link = str(row[7]).strip()
                        customer_type = str(row[11]).strip() or "standard"
                    elif len(row) >= 8:
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
                        
                    if expiry_date in ["Y", "N", "예", "아니오", "yes", "no"]:
                        if agree_info in ["", None, "Y"]:
                            agree_info = expiry_date
                        expiry_date = "9999-12-31"

                    c.execute("SELECT id, role, signup_date, pw, expiry_date, agree_info, survey_count, last_survey_link, customer_type FROM users WHERE id=?", (user_id,))
                    db_user = c.fetchone()
                    if not db_user:
                        plan_type = 'yeta_free' if customer_type == 'yeta' else 'free'
                        c.execute("INSERT INTO users (id, role, signup_date, pw, expiry_date, agree_info, survey_count, last_survey_link, plan_type, customer_type) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", 
                                  (user_id, role, signup_date, pw, expiry_date, agree_info, survey_count, last_survey_link, plan_type, customer_type))
                        cnt += 1
                    else:
                        db_role, db_signup_date, db_pw, db_expiry_date, db_agree_info, db_survey_count, db_last_link, db_cust = db_user[1], db_user[2], db_user[3], db_user[4], db_user[5], db_user[6], db_user[7], db_user[8]
                        if (db_role != role or db_signup_date != signup_date or 
                            db_pw != pw or db_expiry_date != expiry_date or db_agree_info != agree_info or
                            db_survey_count != survey_count or db_last_link != last_survey_link or db_cust != customer_type):
                            c.execute("""
                                UPDATE users 
                                SET role=?, signup_date=?, pw=?, expiry_date=?, agree_info=?, survey_count=?, last_survey_link=?, customer_type=?
                                WHERE id=?
                            """, (role, signup_date, pw, expiry_date, agree_info, survey_count, last_survey_link, customer_type, user_id))
                            cnt += 1
            
            conn.commit()
            
            try:
                visit_sheet = spreadsheet.worksheet("Visit_Logs")
                records = visit_sheet.get_all_records()
                for row in records:
                    c.execute("INSERT OR IGNORE INTO visit_logs (ip_address, visit_date) VALUES (?, ?)", 
                              (str(row.get('IP', '')), str(row.get('Date', ''))))
                conn.commit()
            except Exception:
                pass
                
            return cnt
    except Exception:
        if conn:
            try: conn.rollback()
            except Exception: pass
        return -1
    finally:
        if conn:
            try: conn.close()
            except Exception: pass
    return 0

def get_all_users():
    conn = sqlite3.connect('users.db')
    df = pd.read_sql_query("SELECT * FROM users", conn)
    conn.close()
    return df

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
        spreadsheet_id = st.secrets.get("SPREADSHEET_ID")
        if client and spreadsheet_id:
            spreadsheet = client.open_by_key(spreadsheet_id)
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

def add_user(user_id, pw, role, agree_info="Y", customer_type="standard"):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    signup_date = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).strftime("%Y-%m-%d")
    expiry_date = "9999-12-31"
    hashed_pw = hash_password(pw)
    plan_type = 'yeta_free' if customer_type == 'yeta' else 'free'
    try:
        c.execute("INSERT INTO users (id, role, signup_date, pw, expiry_date, agree_info, survey_count, last_survey_link, plan_type, customer_type) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", 
                  (user_id, role, signup_date, hashed_pw, expiry_date, agree_info, 0, "", plan_type, customer_type))
        conn.commit()
        log_to_sheets(user_id, role, signup_date, hashed_pw, agree_info, expiry_date, 0, "", "", "", "", customer_type)
        success = True
    except sqlite3.IntegrityError:
        success = False
    finally:
        conn.close()
    return success

def log_to_sheets(user_id, role, signup_date, pw, agree_info="Y", expiry_date="9999-12-31", survey_count=0, last_survey_link="", event_applied="", thesis_title="", university="", customer_type="standard"):
    try:
        client = get_gspread_client()
        spreadsheet_id = st.secrets.get("SPREADSHEET_ID")
        if client and spreadsheet_id:
            spreadsheet = client.open_by_key(spreadsheet_id)
            sheet = spreadsheet.sheet1
            
            try:
                headers = sheet.row_values(1)
            except Exception:
                headers = []
            
            expected_headers = ['id', 'role', 'signup_date', 'pw', 'expiry_date', 'agree_info', 'survey_count', 'last_survey_link', 'event_applied', 'thesis_title', 'university', 'customer_type']
            if len(headers) < 12 or not all(h in headers for h in ['event_applied', 'thesis_title', 'university', 'customer_type']):
                sheet.update(range_name='A1:L1', values=[expected_headers])
            
            sheet.append_row([user_id, role, str(signup_date), pw, expiry_date, agree_info, survey_count, last_survey_link, event_applied, thesis_title, university, customer_type])
    except Exception:
        pass

def restore_from_deleted_sheet(user_id):
    try:
        client = get_gspread_client()
        spreadsheet_id = st.secrets.get("SPREADSHEET_ID")
        if client and spreadsheet_id:
            spreadsheet = client.open_by_key(spreadsheet_id)
            try:
                del_sheet = spreadsheet.worksheet("Deleted_Users")
                cell = del_sheet.find(user_id)
                if cell:
                    del_sheet.delete_rows(cell.row)
            except (gspread.exceptions.WorksheetNotFound, gspread.exceptions.CellNotFound):
                pass
    except Exception:
        pass

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
        spreadsheet_id = st.secrets.get("SPREADSHEET_ID")
        if client and spreadsheet_id:
            spreadsheet = client.open_by_key(spreadsheet_id)
            sheet = spreadsheet.sheet1
            
            try:
                headers = sheet.row_values(1)
            except Exception:
                headers = []
            
            expected_headers = ['id', 'role', 'signup_date', 'pw', 'expiry_date', 'agree_info', 'survey_count', 'last_survey_link', 'event_applied', 'thesis_title', 'university', 'customer_type']
            if len(headers) < 12 or not all(h in headers for h in ['event_applied', 'thesis_title', 'university', 'customer_type']):
                sheet.update(range_name='A1:L1', values=[expected_headers])

            cell = sheet.find(user_id)
            kst_today = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).strftime("%Y-%m-%d")
            
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
                final_pw = new_pw if (new_pw and new_pw != "") else cell.value
                final_signup_date = db_signup_date or kst_today
                event_applied_val = event_applied if event_applied is not None else ""
                thesis_title_val = thesis_title if thesis_title is not None else ""
                university_val = university if university is not None else ""
                final_cust_type = customer_type or db_customer_type or "standard"
                
                sheet.update(
                    range_name=f'A{cell.row}:L{cell.row}',
                    values=[[
                        user_id, new_role, final_signup_date, final_pw, new_expiry, "Y", 0, "", 
                        event_applied_val, thesis_title_val, university_val, final_cust_type
                    ]]
                )
            else:
                final_pw = new_pw if (new_pw and new_pw != "") else ""
                final_signup_date = db_signup_date or kst_today
                event_applied_val = event_applied if event_applied is not None else ""
                thesis_title_val = thesis_title if thesis_title is not None else ""
                university_val = university if university is not None else ""
                final_cust_type = customer_type or db_customer_type or "standard"
                sheet.append_row([user_id, new_role, final_signup_date, final_pw, new_expiry, "Y", 0, "", event_applied_val, thesis_title_val, university_val, final_cust_type])
    except Exception:
        pass

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
    except Exception:
        return False

# --- CORE ROUTING ACTION ---
def run():
    # Initialize session state variables
    if 'user_id' not in st.session_state:
        st.session_state.user_id = None
    if 'user_role' not in st.session_state:
        st.session_state.user_role = None
    if 'expiry_date' not in st.session_state:
        st.session_state.expiry_date = None
    if 'plan_type' not in st.session_state:
        st.session_state.plan_type = None
    if 'admin_mode' not in st.session_state:
        st.session_state.admin_mode = False

    # Get query parameters
    q_params = st.query_params

    # 1. Automatic Login and Token Verification (Query Param-based)
    if "login_user" in q_params and "login_token" in q_params:
        login_user_val = q_params["login_user"]
        if isinstance(login_user_val, list): login_user_val = login_user_val[0]
        login_token_val = q_params["login_token"]
        if isinstance(login_token_val, list): login_token_val = login_token_val[0]
        
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
                
                st.query_params.pop("login_user", None)
                st.query_params.pop("login_token", None)
                
                if role_changed:
                    st.toast("🎉 Account status updated!")
                    st.rerun()

    # 2. Inactivity Timeout Check (30 minutes)
    TIMEOUT_LIMIT = 1800
    current_time = int(time.time())
    if st.session_state.user_id is not None:
        last_act = q_params.get("last_activity")
        if isinstance(last_act, list): last_act = last_act[0]
        
        if last_act:
            try:
                elapsed = current_time - int(last_act)
                if elapsed > TIMEOUT_LIMIT:
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

    # 3. Custom CSS Styling (Premium Corporate Theme)
    st.markdown("""
    <style>
    /* =============================================================================
       AHP 마스터 프리미엄 엔터프라이즈 UI 테마 (v3.0) - 예타 모듈용
       ============================================================================= */
    @import url("https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css");
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap');

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
        background-color: #ffffff !important; 
        border: 1px solid #e2e8f0 !important; 
        border-radius: 8px !important;
    }

    div[data-testid="stAlert"] > div {
        border-left: none !important; 
        background-color: transparent !important;
        padding-top: 1.5rem !important;
        padding-bottom: 1.5rem !important;
    }

    div[data-testid="stAlert"] div[data-testid="stMarkdownContainer"] > p:first-child {
        margin-top: 0 !important; 
    }
    div[data-testid="stAlert"] div[data-testid="stMarkdownContainer"] > p:last-child {
        margin-bottom: 0 !important;
    }

    div[data-testid="stAlert"] svg {
        display: none !important; 
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
    .block-container {
        padding-top: 1rem !important;
        padding-left: 3rem !important;
        padding-right: 3rem !important;
        max-width: 1600px !important; 
    }

    @media (max-width: 768px) {
        .block-container {
            padding-left: 1rem !important;
            padding-right: 1rem !important;
        }
    }

    /* --- 사이드바 프리미엄 스타일 --- */
    section[data-testid="stSidebar"] {
        background-color: #1a365d !important;
        border-right: 1px solid #102a43 !important;
    }
    section[data-testid="stSidebar"] > div:first-child {
        padding-top: 1.5rem !important;
    }
    section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
    section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] span,
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] h3,
    section[data-testid="stSidebar"] h4,
    section[data-testid="stSidebar"] h5 {
        color: #f8fafc !important;
    }
    section[data-testid="stSidebar"] input {
        color: #0f172a !important;
    }
    /* 사이드바 내의 일반 버튼 */
    section[data-testid="stSidebar"] div.stButton > button {
        background-color: #2c5282 !important;
        color: #ffffff !important;
        border: 1px solid #2c5282 !important;
    }
    section[data-testid="stSidebar"] div.stButton > button:hover {
        background-color: #3182ce !important;
        border-color: #3182ce !important;
        color: #ffffff !important;
    }
    /* 사이드바 내의 Expander */
    section[data-testid="stSidebar"] [data-testid="stExpander"] {
        background-color: rgba(255, 255, 255, 0.05) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
    }
    section[data-testid="stSidebar"] [data-testid="stExpander"] details summary p,
    section[data-testid="stSidebar"] [data-testid="stExpander"] details summary span {
        color: #ffffff !important;
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
        background: #1e3a8a !important; 
        color: #ffffff !important;
        border: 1px solid #1e3a8a !important;
        font-weight: 600 !important;
        box-shadow: none !important;
    }
    div.stButton > button[kind="primary"]:hover,
    div.stButton > button[data-testid="stBaseButton-primary"]:hover {
        background: #172554 !important; 
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
    button[data-baseweb="tab"]:hover {
        color: #0f172a !important;
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

    /* 사이드바 탭 글자 크기 축소 & 여백 줄이기 & 색상 통일 */
    section[data-testid="stSidebar"] button[data-baseweb="tab"] {
        flex: 1 !important;
        justify-content: center !important;
        font-size: 0.85rem !important;
        padding: 0.5rem 0 !important;
        margin: 0 !important;
        min-height: unset !important;
        color: #cbd5e1 !important;
        background-color: transparent !important;
        border-bottom: 2px solid transparent !important;
    }
    section[data-testid="stSidebar"] button[data-baseweb="tab"][aria-selected="true"] {
        color: #ffffff !important;
        border-bottom: 2px solid #ffffff !important;
    }
    section[data-testid="stSidebar"] button[data-baseweb="tab"]:hover {
        color: #ffffff !important;
    }
    section[data-testid="stSidebar"] div[data-baseweb="tab-list"] {
        display: flex !important;
        justify-content: center !important;
        width: 100% !important;
        gap: 0.2rem !important;
    }
    section[data-testid="stSidebar"] img {
        margin-bottom: 0.25rem !important;
    }
    section[data-testid="stSidebar"] div[data-testid="stMarkdownContainer"] {
        margin-bottom: 0 !important;
    }
    section[data-testid="stSidebar"] > div:first-child {
        padding-top: 0.75rem !important;
        padding-bottom: 0.5rem !important;
    }

    /* --- 비밀번호 가시성 토글 버튼 --- */
    div[data-baseweb="input"] {
        background-color: transparent !important;
        border: none !important;
    }
    div[data-testid="stTextInput"] button,
    [data-testid="stTextInputPasswordVisibilityButton"] {
        background-color: transparent !important;
        border: none !important;
        box-shadow: none !important;
        color: #475569 !important;
    }

    /* =============================================================================
       예타 전용 커스텀 클래스
       ============================================================================= */
    .yeta-body {
        font-family: 'Pretendard', 'Outfit', sans-serif;
    }
    .yeta-header {
        background-color: #1A365D;
        color: white;
        padding: 30px;
        border-radius: 12px;
        margin-bottom: 30px;
        border-left: 6px solid #3182CE;
    }
    .yeta-header h1 {
        color: white !important;
        margin: 0 !important;
        font-size: 2.2rem !important;
        font-weight: 700 !important;
    }
    .yeta-header p {
        margin: 10px 0 0 0 !important;
        font-size: 1.1rem !important;
        color: #E2E8F0 !important;
    }
    .verdict-card {
        padding: 25px;
        border-radius: 12px;
        text-align: center;
        margin-bottom: 25px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
    }
    .verdict-pass {
        background-color: #EBF8FF;
        border: 2px solid #3182CE;
        color: #2B6CB0;
    }
    .verdict-fail {
        background-color: #FFF5F5;
        border: 2px solid #E53E3E;
        color: #C53030;
    }
    .verdict-title {
        font-size: 1.5rem;
        font-weight: 700;
        margin-bottom: 10px;
    }
    .verdict-score {
        font-size: 3rem;
        font-weight: 800;
        margin-bottom: 10px;
    }

    /* B2B Pricing Cards */
    .pricing-grid {
        display: flex;
        gap: 20px;
        flex-wrap: wrap;
        margin-bottom: 30px;
    }
    .price-card {
        flex: 1;
        min-width: 280px;
        background: white;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 25px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.02);
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }
    .price-card-tier {
        font-size: 1.2rem;
        font-weight: 700;
        color: #4A5568;
        margin-bottom: 10px;
    }
    .price-card-amount {
        font-size: 2.2rem;
        font-weight: 800;
        color: #1A202C;
        margin-bottom: 15px;
    }
    .price-card-features {
        list-style: none;
        padding-left: 0;
        margin-bottom: 25px;
    }
    .price-card-features li {
        margin-bottom: 8px;
        font-size: 0.9rem;
        color: #4A5568;
        display: flex;
        align-items: center;
    }
    .price-card-features li::before {
        content: "✓";
        color: #3182CE;
        margin-right: 8px;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

    # 4. Handle PortOne Payment Callback inside Yeta
    if "portone_paid" in q_params and "user_id" in q_params:
        user_id_param = q_params.get("user_id")
        plan_name_param = q_params.get("plan_name", "단건 분석권")
        kst_now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
        new_expiry_date = (kst_now + datetime.timedelta(days=365)).strftime("%Y-%m-%d")
        
        try:
            conn = sqlite3.connect('users.db')
            c = conn.cursor()
            c.execute("UPDATE users SET role='official', expiry_date=?, plan_type=? WHERE id=?", 
                      (new_expiry_date, plan_name_param, user_id_param))
            conn.commit()
            conn.close()
            
            st.success(f"🎉 {plan_name_param} 결제가 완료되어 정식 회원(예타 기능 잠금해제)으로 승급되었습니다!")
            if st.button("예타 분석 홈으로 가기"):
                st.query_params.pop("portone_paid", None)
                st.query_params.pop("user_id", None)
                st.query_params.pop("plan_name", None)
                st.rerun()
            st.stop()
        except Exception as e:
            st.error(f"결제 데이터 데이터베이스 저장 실패: {str(e)}")

    # 5. Page Header Section
    st.markdown(f"""
    <div style='margin-top: 55px;'>
        <h1>{_('국가 예비타당성조사 종합평가(AHP) 시스템', 'Preliminary Feasibility Study AHP System')}</h1>
        <p style='color: #666; font-size: 1.05rem; margin-bottom: 30px;'>{_('기획재정부 및 KDI 표준 지침을 준수하는 공공투자사업 AHP 종합 평가 모듈입니다.', 'AHP comprehensive evaluation module for public investment projects in compliance with MoEF & KDI standard guidelines.')}</p>
    </div>
    """, unsafe_allow_html=True)

    # --- ADMIN MODE INTERCEPTOR ---
    if st.session_state.get('admin_mode', False) and st.session_state.user_role == 'admin':
        st.subheader(_("👥 가입자 현황 및 관리 (예타 전용 뷰)", "Registered Users & Admin Control (YETA View)"))
        
        col_sync1, col_sync2 = st.columns([2, 8])
        with col_sync1:
            if st.button("🔄 구글 시트와 동기화"):
                with st.spinner("구글 시트 데이터 불러오는 중..."):
                    sync_count = sync_db_from_sheets()
                if sync_count >= 0:
                    st.success(f"🎉 동기화 완료! (보정 및 복구된 데이터: {sync_count}건)")
                    st.rerun()
                else:
                    st.error("동기화 중 오류가 발생했습니다. 화면상의 에러 메시지를 확인해 주세요.")

        try:
            spreadsheet_id = st.secrets.get("SPREADSHEET_ID")
            visit_data_gs = get_cached_visit_logs(spreadsheet_id) if spreadsheet_id else []
            if not visit_data_gs:
                try:
                    conn = sqlite3.connect('users.db')
                    df_local = pd.read_sql_query("SELECT ip_address as IP, visit_date as Date FROM visit_logs", conn)
                    conn.close()
                    if not df_local.empty:
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
                total_visits = len(daily_df_logs)
                
                st.write(f"**누적 방문자:** {total_visits:,}명")
                st.write("#### 📅 일별 방문자 현황")
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
        st.write("### 👥 가입자 현황 및 최종 배포 링크")
        
        users_df = get_all_users()
        if 'survey_count' not in users_df.columns:
            users_df['survey_count'] = 0
        if 'last_survey_link' not in users_df.columns:
            users_df['last_survey_link'] = ""
        users_df['survey_count'] = pd.to_numeric(users_df['survey_count'].fillna(0)).astype(int)
        
        display_df = users_df[['id', 'role', 'signup_date', 'pw', 'survey_count', 'last_survey_link', 'expiry_date', 'agree_info', 'customer_type']].copy()
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
                "agree_info": "동의여부",
                "customer_type": "고객군"
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
                new_expiry_val_default = str(datetime.date.today() + datetime.timedelta(days=60))
            else:
                new_expiry_val_default = selected_user['expiry_date']
                
            new_expiry_val = st.text_input("만료일 설정/변경 (YYYY-MM-DD)", value=new_expiry_val_default)
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
                if st.button("🔑 이 계정으로 로그인", use_container_width=True, type="secondary"):
                    st.session_state.user_id = edit_id
                    st.session_state.user_role = selected_user['role']
                    st.session_state.expiry_date = selected_user['expiry_date']
                    st.session_state.admin_mode = False
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

        with st.expander("🎁 학위논문 할인 이벤트 설정 및 제어"):
            event_cfg = get_event_settings()
            new_active = st.checkbox("이벤트 활성화 여부", value=event_cfg["active"], key="admin_event_active")
            new_title = st.text_input("이벤트 제목", value=event_cfg["title"], key="admin_event_title")
            new_desc = st.text_area("이벤트 내용/설명", value=event_cfg["desc"], key="admin_event_desc")
            
            try:
                default_deadline_date = datetime.datetime.strptime(event_cfg["deadline"], "%Y-%m-%d").date()
            except Exception:
                default_deadline_date = datetime.date(2026, 7, 30)
            new_deadline_date = st.date_input("이벤트 종료일", value=default_deadline_date, key="admin_event_deadline")
            new_deadline_str = str(new_deadline_date)
            new_discount = st.number_input("할인 금액 (원)", min_value=0, max_value=500000, value=event_cfg["discount"], step=5000, key="admin_event_discount")
            
            if st.button("이벤트 설정 저장", use_container_width=True):
                conn = sqlite3.connect('users.db')
                c = conn.cursor()
                try:
                    c.execute("UPDATE event_settings SET event_active=?, event_title=?, event_desc=?, event_deadline=?, event_discount=? WHERE id=1",
                              (1 if new_active else 0, new_title, new_desc, new_deadline_str, int(new_discount)))
                    conn.commit()
                    st.success("🎉 이벤트 설정이 성공적으로 저장되었습니다!")
                    st.rerun()
                except Exception as e:
                    st.error(f"설정 저장 실패: {e}")
                finally:
                    conn.close()

        st.stop()

    # 6. Sidebar Configuration (Authentication & Yeta Settings)
    with st.sidebar:
        # AHP Master Logo
        try:
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

        # Login / Session panel
        if st.session_state.user_id is None:
            tab_login, tab_find_pw = st.tabs([_("로그인", "Login"), _("비밀번호 찾기", "Find Password")])
            
            with tab_login:
                l_id = st.text_input(_("아이디 (이메일 주소)", "Username (Email Address)"), key="l_id")
                l_pw = st.text_input(_("비밀번호 (PW)", "Password (PW)"), type="password", key="l_pw")
                if st.button(_("로그인 실행", "Login"), key="btn_login_yeta"):
                    result = check_login(l_id.strip(), l_pw)
                    if result:
                        today = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).date()
                        expiry_date_val = datetime.datetime.strptime(result[1], "%Y-%m-%d").date()
                        if today > expiry_date_val:
                            if result[0] == 'official':
                                try:
                                    update_user_full_info(l_id.strip(), None, "temp", "9999-12-31")
                                    st.session_state.user_id = l_id.strip()
                                    st.session_state.user_role = "temp"
                                    st.session_state.expiry_date = "9999-12-31"
                                    st.query_params["login_user"] = l_id.strip()
                                    st.query_params["login_token"] = hashlib.sha256(f"{l_id.strip()}:AHP_MASTER_SECURE_SALT_2026_!@#".encode()).hexdigest()
                                    st.query_params["last_activity"] = str(int(time.time()))
                                    st.toast(_("📅 정식 이용 기간이 만료되어 무료사용자 권한으로 자동 전환되었습니다.", "📅 Subscription expired. Downgraded to Free User."))
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
                            st.success(_(f"환영합니다, {l_id}님!", f"Welcome, {l_id}!"))
                            st.rerun()
                    else:
                        st.error(_("아이디 또는 비밀번호가 일치하지 않습니다.", "Incorrect username or password."))
            
            with tab_find_pw:
                st.write(_("가입 시 사용한 이메일 주소를 입력해주세요. 이메일로 새로운 임시 비밀번호가 발송됩니다.",
                           "Please enter the email address used at registration. A new temporary password will be sent to your email."))
                f_id = st.text_input(_("가입한 아이디 (이메일)", "Registered ID (Email)"), key="f_id")
                if st.button(_("임시 비밀번호 전송", "Send Temporary Password"), key="btn_find_pw_yeta"):
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
            
            if st.session_state.user_role == 'admin':
                btn_label = _("🔧 관리자 화면 닫기", "🔧 Exit Admin Panel") if st.session_state.get('admin_mode', False) else _("🔧 관리자 화면 접속", "🔧 Connect to Admin Panel")
                if st.button(btn_label):
                    st.session_state.admin_mode = not st.session_state.admin_mode
                    st.rerun()

            with st.expander(_("🔐 비밀번호 변경", "🔐 Change Password")):
                cur_pw = st.text_input(_("현재 비밀번호", "Current Password"), type="password", key="chg_cur_yeta")
                new_pw_val = st.text_input(_("새 비밀번호", "New Password"), type="password", key="chg_new_yeta")
                confirm_pw = st.text_input(_("새 비밀번호 확인", "Confirm New Password"), type="password", key="chg_conf_yeta")
                
                if st.button(_("비밀번호 변경", "Change Password"), key="btn_chg_pw_yeta"):
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

            if st.button(_("로그아웃", "Log Out"), key="btn_logout_yeta"):
                st.session_state.user_id = None
                st.session_state.user_role = None
                st.session_state.expiry_date = None
                st.session_state.plan_type = None
                st.session_state.admin_mode = False
                st.query_params.pop("login_user", None)
                st.query_params.pop("login_token", None)
                st.rerun()

            with st.expander(_("📄 견적서 출력", "📄 Print Estimate")):
                q_client = st.text_input(_("의뢰기관명 (수신)", "Client Institution"), placeholder=_("예: (주)에이치피테크", "e.g., HP Tech Co., Ltd."), key="q_client_yeta")
                q_project = st.text_input(_("과제명 (프로젝트명)", "Project / Task Name"), placeholder=_("예: 예타 가중치 평가 분석", "e.g., Yeta Weight Assessment Analysis"), key="q_project_yeta")
                
                q_tier = st.selectbox(
                    _("서비스 구분 (요금제)", "Pricing Plan Tier"),
                    options=[
                        (_("단건 분석권 (300,000원)", "Single Plan (300,000 KRW)"), 300000, "단건 분석권"),
                        (_("연간 라이선스 (3,000,000원)", "Annual License (3,000,000 KRW)"), 3000000, "연간 라이선스")
                    ],
                    format_func=lambda x: x[0],
                    key="q_tier_select_yeta"
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
                    <button class="btn" id="dl-pdf-btn">📄 견적서 다운로드 (PDF)</button>
                    <div id="hidden-q-container" style="display: none; width: 720px; background: white; padding: 10px;"></div>
                    
                    <script>
                        document.getElementById('dl-pdf-btn').onclick = function() {{
                            var container = document.getElementById('hidden-q-container');
                            container.innerHTML = {escaped_html};
                            container.style.display = 'block';
                            
                            var opt = {{
                                margin:       [10, 10, 10, 10],
                                filename:     '견적서_{clean_client}.pdf',
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
                    st.warning(_("견적서 다운로드를 위해 의뢰기관명과 과제명을 먼저 입력해 주세요.", 
                                 "Please enter the Client Institution and Project Name to enable download."))

            with st.expander(_("📄 계산서 발행 신청", "📄 Request Invoice")):
                t_biz_num = st.text_input(_("사업자 등록번호", "Business Registration Number"), placeholder="000-00-00000", key="t_biz_num_yeta")
                t_biz_name = st.text_input(_("상호 (회사명)", "Company Name"), key="t_biz_name_yeta")
                t_rep_name = st.text_input(_("대표자명", "CEO Name"), key="t_rep_name_yeta")
                t_address = st.text_input(_("사업장 주소", "Business Address"), key="t_address_yeta")
                t_biz_type = st.text_input(_("업태 / 업종", "Business Category / Type"), key="t_biz_type_yeta")
                t_email = st.text_input(_("계산서 수신 이메일", "Invoice Email"), key="t_email_yeta")
                
                t_tier = st.selectbox(
                    _("신청 서비스 (요금제)", "Pricing Plan for Invoice"),
                    options=[
                        (_("단건 분석권 (300,000원)", "Single Plan (300,000 KRW)"), "단건 분석권"),
                        (_("연간 라이선스 (3,000,000원)", "Annual License (3,000,000 KRW)"), "연간 라이선스")
                    ],
                    format_func=lambda x: x[0],
                    key="t_tier_select_yeta"
                )
                
                if st.button(_("계산서 발행 신청하기", "Submit Invoice Request"), use_container_width=True, key="btn_request_tax_yeta"):
                    if not t_biz_num.strip():
                        st.error(_("사업자 등록번호를 입력해 주세요.", "Please enter the Business Registration Number."))
                    elif not t_biz_name.strip():
                        st.error(_("상호를 입력해 주세요.", "Please enter the Company Name."))
                    elif not t_rep_name.strip():
                        st.error(_("대표자명을 입력해 주세요.", "Please enter the CEO Name."))
                    elif not t_email.strip():
                        st.error(_("이메일을 입력해 주세요.", "Please enter the Email."))
                    elif not validate_email(t_email.strip()):
                        st.error(_("올바른 이메일 형식이 아닙니다.", "Invalid email format."))
                    else:
                        with st.spinner(_("신청서를 제출하는 중...", "Submitting request...")):
                            conn = sqlite3.connect('users.db')
                            c = conn.cursor()
                            try:
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
                                    st.success(_("계산서 신청이 접수되었습니다! 관리자 확인 후 계산서가 발행됩니다.", 
                                                 "Request submitted! The invoice will be issued after review."))
                                else:
                                    st.warning(_("DB 저장은 성공했으나 알림 메일 발송에 실패했습니다. 관리자가 확인 후 순차 처리해 드리겠습니다.", 
                                                 "Saved to DB, but email alert failed. The admin will review it soon."))
                            except Exception as e:
                                st.error(_(f"신청 중 오류가 발생했습니다: {e}", f"Error during submission: {e}"))
                            finally:
                                conn.close()
                                
    # 7. Navigation Tabs
    if st.session_state.user_id:
        tab_guide, tab_analysis, tab_excel, tab_survey_create, tab_live_response, tab_pricing = st.tabs([
            _("예타 AHP 지침 안내", "AHP Guidelines Guide"),
            _("예타 종합평가(AHP) 분석", "Preliminary Feasibility Analysis"),
            _("예타 코딩 엑셀 양식", "Yeta Coding Excel Form"),
            _("예타 전용 AHP 설문 작성 및 배포", "Create Yeta Survey"),
            _("실시간 응답 현황", "Live Response Status"),
            _("서비스 요금", "Pricing & License")
        ])
    else:
        tab_guide, tab_analysis, tab_excel, tab_survey_create, tab_live_response, tab_pricing, tab_signup = st.tabs([
            _("예타 AHP 지침 안내", "AHP Guidelines Guide"),
            _("예타 종합평가(AHP) 분석", "Preliminary Feasibility Analysis"),
            _("예타 코딩 엑셀 양식", "Yeta Coding Excel Form"),
            _("예타 전용 AHP 설문 작성 및 배포", "Create Yeta Survey"),
            _("실시간 응답 현황", "Live Response Status"),
            _("서비스 요금", "Pricing & License"),
            _("회원가입", "Sign Up")
        ])

    # =========================================================================
    # TAB 1: Analysis Tool
    # =========================================================================
    with tab_analysis:
        st.write("### " + _("예비타당성 종합평가(AHP)", "Preliminary Feasibility AHP Synthesis"))
        st.markdown("<br>", unsafe_allow_html=True)
        
        main_col, settings_col = st.columns([3.0, 1.2], gap="large")
        
        with settings_col:
            # ==========================================
            # SECTION 1: 분석 환경 설정 (Settings)
            # ==========================================
            with st.container(border=True):
                st.markdown(f"<div style='font-size: 1.1rem; font-weight: bold; color: #1e3a8a; margin-bottom: 15px;'><i class='fas fa-cogs'></i> {_('예타 종합평가(AHP) 가중치 설정', 'Yeta AHP Weights Settings')}</div>", unsafe_allow_html=True)
                
                project_type = st.selectbox(
                    _("사업 유형(모델) 선택", "Select Project Type (Model)"),
                    options=[
                        ("construction_non_capital", _("건설사업 (비수도권)", "Construction (Non-capital)")),
                        ("construction_capital", _("건설사업 (수도권)", "Construction (Capital)")),
                        ("rnd_bc", _("R&D사업 (B/C)", "R&D (B/C)")),
                        ("rnd_ec", _("R&D사업 (E/C)", "R&D (E/C)")),
                        ("other_bc", _("기타 재정사업 (B/C)", "Other Fiscal (B/C)")),
                        ("other_ec", _("기타 재정사업 (E/C)", "Other Fiscal (E/C)"))
                    ],
                    format_func=lambda x: x[1],
                    key="yeta_project_type_select"
                )
                p_type = project_type[0]
                
                st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)
                
                st.markdown(f"<div style='font-size: 0.95rem; font-weight: 600; margin-bottom: 8px;'>{_('A. 정량 데이터 (B/C, 지역낙후도)', 'A. Quantitative Data')}</div>", unsafe_allow_html=True)
                bc_ratio = st.number_input(_("경제성 분석 결과 (B/C 비율)", "B/C Ratio"), min_value=0.0, max_value=10.0, value=1.05, step=0.05)
                
                has_regional = "non_capital" in p_type or p_type == "other_bc" or p_type == "other_ec"
                if has_regional:
                    lir_value = st.number_input(_("지역낙후도 지수 (LIR/MIR)", "Regional Backwardness (LIR)"), min_value=-3.0, max_value=3.0, value=0.0, step=0.1)
                else:
                    lir_value = 0.0
                    st.text_input(_("지역낙후도 지수 (LIR/MIR)", "Regional Backwardness (LIR)"), value="수도권/해당없음", disabled=True)
                
                st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)
                
                st.markdown(f"<div style='font-size: 0.95rem; font-weight: 600; margin-bottom: 8px;'>{_('B. 1계층 상수합 가중치 (%)', 'B. Level 1 Weights (%)')}</div>", unsafe_allow_html=True)
                if p_type == "rnd_bc":
                    econ_w = st.slider(_("경제성 가중치", "Economics Weight"), 0, 100, 45) / 100.0
                    tech_w = st.slider(_("과학기술적 타당성", "Science/Tech Weight"), 0, 100, 35) / 100.0
                    policy_w = st.slider(_("정책적 타당성", "Policy Weight"), 0, 100, 20) / 100.0
                    regional_w = 0.0
                elif p_type == "rnd_ec":
                    econ_w = st.slider(_("경제성 가중치", "Economics Weight"), 0, 100, 35) / 100.0
                    tech_w = st.slider(_("과학기술적 타당성", "Science/Tech Weight"), 0, 100, 45) / 100.0
                    policy_w = st.slider(_("정책적 타당성", "Policy Weight"), 0, 100, 20) / 100.0
                    regional_w = 0.0
                elif p_type == "construction_capital":
                    tech_w = 0.0
                    econ_w = st.slider(_("경제성 가중치", "Economics Weight"), 0, 100, 65) / 100.0
                    policy_w = st.slider(_("정책적 가중치", "Policy Weight"), 0, 100, 35) / 100.0
                    regional_w = 0.0
                    st.slider(_("지역균형발전 가중치", "Regional Balance Weight"), 0, 100, 0, disabled=True)
                elif p_type == "other_bc":
                    tech_w = 0.0
                    econ_w = st.slider(_("경제성 가중치", "Economics Weight"), 0, 100, 40) / 100.0
                    policy_w = st.slider(_("정책적 가중치", "Policy Weight"), 0, 100, 60) / 100.0
                    regional_w = 0.0
                elif p_type == "other_ec":
                    tech_w = 0.0
                    econ_w = st.slider(_("경제성 가중치", "Economics Weight"), 0, 100, 30) / 100.0
                    policy_w = st.slider(_("정책적 가중치", "Policy Weight"), 0, 100, 70) / 100.0
                    regional_w = 0.0
                else: # construction_non_capital
                    tech_w = 0.0
                    econ_w = st.slider(_("경제성 가중치", "Economics Weight"), 0, 100, 40) / 100.0
                    policy_w = st.slider(_("정책적 가중치", "Policy Weight"), 0, 100, 30) / 100.0
                    regional_w = st.slider(_("지역균형발전 가중치", "Regional Balance Weight"), 0, 100, 30) / 100.0

                valid_w, w_msg = yeta_utils.validate_yeta_level1_weights(p_type, econ_w, policy_w, regional_w, tech_w)
                if valid_w:
                    st.markdown(f"<div style='color: green; font-size: 0.8rem; margin-top: -10px;'>✔️ {_('KDI 지침 가중치 범위 부합', 'Weights OK')}</div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div style='color: red; font-size: 0.8rem; margin-top: -10px;'>⚠️ {w_msg}</div>", unsafe_allow_html=True)


        with main_col:
            # ==========================================
            # SECTION 3: 엑셀 데이터 업로드 및 분석 (Upload & Analyze)
            # ==========================================
            with st.container(border=True):
                st.markdown(f"<h3 style='color: #b91c1c; margin-bottom: 10px; font-size: 1.3rem;'><i class='fas fa-chart-line'></i> {_('2. 데이터 업로드 및 종합평가 분석', '2. Upload Data & Run AHP Analysis')}</h3>", unsafe_allow_html=True)
                st.markdown(_("<span style='font-size: 0.95rem; color: #4b5563;'>템플릿에 작성이 완료된 AHP 엑셀 데이터를 업로드하면 즉시 예비타당성조사 종합평가 결과가 산출됩니다.</span>", "Upload the completed AHP Excel data to instantly calculate the preliminary feasibility study comprehensive evaluation result."), unsafe_allow_html=True)
                
                st.markdown("<br>", unsafe_allow_html=True)
                
                # User Tier Check
                is_official = False
                if st.session_state.get("user_id"):
                    if st.session_state.get("user_role") in ["official", "admin"]:
                        is_official = True
                    else:
                        try:
                            conn = sqlite3.connect('users.db')
                            c = conn.cursor()
                            c.execute("SELECT role FROM users WHERE id=?", (st.session_state.user_id,))
                            res = c.fetchone()
                            if res and res[0] in ["official", "admin"]:
                                is_official = True
                            conn.close()
                        except:
                            pass

                uploaded_file = st.file_uploader(_("응답이 완료된 AHP 엑셀 파일 첨부", "Upload the completed AHP Excel file"), type=["xlsx"])
                
                if uploaded_file is not None:
                    try:
                        import pandas as pd
                        df = pd.read_excel(uploaded_file)
                        st.success(_("데이터 로드 성공! 연산을 시작합니다.", "Data loaded successfully! Starting computation."))
                        
                        max_free_evals = 3
                        if not is_official and len(df) > max_free_evals:
                            st.warning(f"⚠️ 무료 사용자는 최대 {max_free_evals}명의 설문 데이터만 분석 가능합니다. (정식 결제 시 무제한 분석 가능)")
                            df = df.head(max_free_evals)
                            
                        res_df, final_yeta_score = yeta_utils.process_yeta_ahp_data(df, p_type, bc_ratio, lir_value)
                        
                        st.markdown("---")
                        st.markdown("### " + _("📊 종합평가(AHP) 최종 결과", "📊 Final AHP Evaluation Results"))
                        
                        is_pass = final_yeta_score >= 0.5
                        card_class = "verdict-pass" if is_pass else "verdict-fail"
                        verdict_text = _("사업 타당성 확보 (시행)", "Project Feasible (Go)") if is_pass else _("사업 타당성 미흡 (미시행)", "Project Not Feasible (Stop)")
                        
                        st.markdown(f"""
                        <div class="verdict-card {card_class}">
                            <div class="verdict-title">{_("최종 종합 평가 판정", "Final Comprehensive Evaluation Verdict")}</div>
                            <div class="verdict-score">{final_yeta_score:.3f}</div>
                            <div style="font-size: 1.3rem; font-weight: bold;">{verdict_text}</div>
                            <div style="font-size: 0.9rem; margin-top: 10px; opacity: 0.85;">
                                {_("KDI 지침 기준: AHP 종합점수 0.5 이상일 때 타당성 확보", "MoEF & KDI standard: Feasible when AHP score >= 0.5")}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        st.markdown("<br>", unsafe_allow_html=True)
                        st.write("#### " + _("👨‍🔬 평가자별 점수 분포 및 극단값 배제 현황", "👨‍🔬 Evaluator Distribution & Outlier Exclusion"))
                        st.dataframe(res_df, use_container_width=True)
                        
                    except Exception as e:
                        st.error(f"엑셀 분석 중 오류가 발생했습니다: {str(e)}")




    # =========================================================================
    # =========================================================================
    # TAB 1.5: Yeta Excel Template Generator
    # =========================================================================
    with tab_excel:
        st.write("### " + _("예비타당성조사 AHP 코딩 엑셀 양식 설정 및 다운로드", "Setup & Download Yeta AHP Coding Excel Form"))
        st.markdown("<br>", unsafe_allow_html=True)
        
        st.markdown(f"<h4 style='color: #1e3a8a; margin-top: 10px;'><i class='fas fa-check-circle'></i> 1단계: 분석 모델(사업 유형) 선택</h4>", unsafe_allow_html=True)
        with st.container(border=True):
            excel_project_type = st.selectbox(
                _("대상 사업 유형", "Select Project Type"),
                options=[
                    ("construction_non_capital", _("건설사업 (비수도권)", "Construction (Non-capital)")),
                    ("construction_capital", _("건설사업 (수도권)", "Construction (Capital)")),
                    ("rnd_bc", _("R&D사업 (B/C)", "R&D (B/C)")),
                    ("rnd_ec", _("R&D사업 (E/C)", "R&D (E/C)")),
                    ("other_bc", _("기타 재정사업 (B/C)", "Other Fiscal (B/C)")),
                    ("other_ec", _("기타 재정사업 (E/C)", "Other Fiscal (E/C)"))
                ],
                format_func=lambda x: x[1],
                key="yeta_excel_project_type_select"
            )
            ex_p_type = excel_project_type[0]
            
            if "rnd" in ex_p_type:
                st.info(_("📊 1계층 고정 항목: 경제성, 정책성, 과학기술성", "📊 Fixed Level 1: Economics, Policy, Science/Tech"))
            elif "capital" in ex_p_type and "non" not in ex_p_type:
                st.info(_("📊 1계층 고정 항목: 경제성, 정책성", "📊 Fixed Level 1: Economics, Policy"))
            else:
                st.info(_("📊 1계층 고정 항목: 경제성, 정책성, 지역균형발전", "📊 Fixed Level 1: Economics, Policy, Regional Balance"))
        
        st.markdown(f"<h4 style='color: #1e3a8a; margin-top: 25px;'><i class='fas fa-list'></i> 2단계: 2계층 평가 요인 커스터마이징</h4>", unsafe_allow_html=True)
        with st.container(border=True):
            st.caption(_("대상 사업 특성에 맞춰 세부 평가 항목을 쉼표(,)로 구분하여 입력하세요. 입력한 요인 개수에 맞춰 쌍대비교 폼이 자동 계산됩니다.", "Enter sub-factors separated by commas according to the project characteristics. Pairwise forms are auto-calculated."))
            
            policy_input = st.text_input(_("정책성 하위 요인", "Policy Factors"), value="정책의 일관성, 사업추진상의 위험요인")
            policy_factors = [x.strip() for x in policy_input.split(",") if x.strip()]
            
            regional_factors = []
            if "non_capital" in ex_p_type or "other" in ex_p_type:
                reg_input = st.text_input(_("지역균형발전 하위 요인", "Regional Factors"), value="지역경제 파급효과, 지역개발계획과의 부합성")
                regional_factors = [x.strip() for x in reg_input.split(",") if x.strip()]
                
            tech_factors = []
            if "rnd" in ex_p_type:
                tech_input = st.text_input(_("과학기술성 하위 요인", "Tech Factors"), value="기술개발계획의 적절성, 기술개발 성공가능성, 기존 사업과의 중복성")
                tech_factors = [x.strip() for x in tech_input.split(",") if x.strip()]

        st.markdown(f"<h4 style='color: #047857; margin-top: 25px;'><i class='fas fa-file-excel'></i> 3단계: 맞춤형 엑셀 폼 생성 및 다운로드</h4>", unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown(_("<span style='font-size: 0.95rem; color: #4b5563;'>위 1단계와 2단계에서 설정한 <b>예비타당성조사 분석 모델 및 요인</b>에 맞춰진 전용 엑셀 펀칭 폼입니다.</span>", "This is a dedicated Excel punching form tailored to the Yeta analysis model and factors set above."), unsafe_allow_html=True)
            
            st.markdown("""
            <div style='background-color: #f9fafb; padding: 15px; border-radius: 5px; margin-top: 15px; border-left: 4px solid #3b82f6; margin-bottom: 20px;'>
                <strong>[양식 구조 안내]</strong><br>
                ✔️ <b>동일한 부분</b>: 2계층 이후 항목들 간의 쌍대비교 입력 방식 및 CR 검증 로직은 일반 AHP와 동일합니다.<br>
                ✔️ <b>달라지는 부분</b>: 예타 지침에 따라 1계층(경제/정책/지역) 가중치는 쌍대비교가 아닌 <b>100점 상수합법</b> 비율로 기입합니다.<br><br>
                <strong>[📝 데이터 입력 가이드]</strong><br>
                다운로드하시는 엑셀 폼에 데이터를 기입하실 때 아래 규칙을 따르세요.<br>
                ✔️ 왼쪽(시행) 항목이 더 중요하면: <b>음수</b> 입력 (예: -3)<br>
                ✔️ 오른쪽(미시행) 항목이 더 중요하면: <b>양수</b> 입력 (예: 3)<br>
                ✔️ 두 항목이 동등하게 중요하면: <b>1</b> 입력
            </div>
            """, unsafe_allow_html=True)
            
            img_file = _("ahp_input_guide.png", "ahp_input_guide_en.png")
            caption_text = _("[참고] 설문 응답을 엑셀에 입력하는 방법", "[Reference] How to enter survey responses into Excel")
            if os.path.exists(img_file):
                st.image(img_file, caption=caption_text)
            
            template_bytes = yeta_utils.generate_yeta_excel_template(ex_p_type, policy_factors, regional_factors, tech_factors)
            st.download_button(
                label=_("👉 맞춤형 예타 AHP 엑셀 템플릿 다운로드 (.xlsx)", "👉 Download Custom Yeta AHP Excel Template (.xlsx)"),
                data=template_bytes,
                file_name=f"yeta_ahp_template_{ex_p_type}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary",
                use_container_width=True
            )

    # =========================================================================
    # TAB 2: Yeta Survey Creator
    # =========================================================================
    with tab_survey_create:
        st.write("### " + _("예비타당성조사 AHP 전문가 설문지 제작 및 배포", "Create and Distribute YETA AHP Survey"))
        st.info(_("KDI 지침에 명시된 요인을 바탕으로 예타 전용 설문지를 쉽게 구성하고 구글 시트와 연동하여 배포할 수 있습니다.", "Easily configure the YETA-specific survey based on KDI guidelines, link it with Google Sheets, and distribute it."))
        
        st.markdown("#### 1. 사업 기본 정보 및 자료 첨부")
        survey_title = st.text_input(_("설문지 제목", "Survey Title"), value=_("재정투자사업 종합평가(AHP) 전문가 설문", "Expert AHP Survey for Preliminary Feasibility Study"))
        default_survey_desc = _(
            "안녕하십니까, 전문가님.\n"
            "본 설문은 KDI 예비타당성조사 수행 지침에 의거하여, 해당 재정투자사업의 타당성 및 추진 여부를 최종 판단하기 위한 '종합평가(AHP)' 용도로 기획되었습니다.\n\n"
            "전문가님께서는 제공된 'AHP 자료집' 및 사업 개요를 충분히 숙지하신 후, 각 평가항목(경제성, 정책성, 지역균형발전, 기술성 등) 간의 상대적 중요도를 평가해주시기 바랍니다.\n\n"
            "■ 주요 평가 유의사항\n"
            "1. (제1계층 평가) 대분류 항목 간의 상대적 중요도를 '총합이 100'이 되도록 배분해 주십시오. (상수합법)\n"
            "   ※ 단, KDI 예비타당성조사 종합평가 지침에 명시된 사업 유형별 가이드라인에 따라 부문별 입력 가능한 점수 범위(상하한선)가 시스템적으로 제한되어 있으니 이 점 널리 양해 부탁드립니다.\n"
            "2. (제2계층 평가) 세부 항목 간 쌍대비교 시, 두 항목 중 더 중요하다고 판단되는 쪽으로 9점 척도 기준 가중치를 부여해 주십시오.\n"
            "3. 설문 응답의 일관성 비율(CR)이 권고 수준(0.15 미만)을 유지할 수 있도록 논리적인 평가를 당부드립니다.\n\n"
            "주관기관: OOOO\n"
            "문의처: OOO, sample@test.co.kr, 00)000-0000\n\n"
            "바쁘신 일정 중에도 국가 공공투자사업의 합리적 의사결정을 위해 귀중한 시간을 내어 주셔서 진심으로 감사드립니다.",
            "Hello, Expert.\nThis survey is designed to comprehensively evaluate the feasibility of the proposed public investment project using the AHP method based on KDI guidelines..."
        )
        survey_desc = st.text_area(_("설문 안내문", "Instructions"), value=default_survey_desc, height=250)
        
        project_desc = st.text_area(_("사업 개요 설명", "Project Overview Description"), placeholder="응답자가 사업 내용을 파악할 수 있도록 주요 사업 개요를 입력하세요.")
        project_url = st.text_input(_("사업 설명 자료 첨부 (URL 링크)", "Project Material Link (URL)"), placeholder="예: 구글 드라이브, 노션 링크 등 (응답자가 다운로드/열람할 수 있는 외부 링크)")

        st.markdown("#### 2. 예타 사업 유형 및 평가항목 세부 설정")
        yeta_p_type = st.selectbox(
            _("평가 대상 사업 유형", "Target Project Type"),
            options=["건설사업 (비수도권)", "건설사업 (수도권)", "R&D사업 (B/C)", "R&D사업 (E/C)", "정보화사업", "기타사업 (B/C)", "기타사업 (E/C)"]
        )
        
        # Depending on project type, show expanders for factor descriptions.
        with st.expander("📝 1계층 및 2계층 평가항목 상세 설명 설정", expanded=True):
            st.caption("응답자가 각 항목의 의미를 명확히 이해할 수 있도록 항목별 상세 설명을 입력할 수 있습니다.")
            st.markdown("<div style='margin-top: 10px; margin-bottom: 5px; font-weight: bold; color: #1e293b; font-size: 15px;'>📌 1계층 평가항목</div>", unsafe_allow_html=True)
            st.text_input("경제성(Economic Feasibility) 설명", placeholder="예: 사업의 B/C 비율 등 경제적 타당성을 평가합니다.")
            st.text_input("정책성(Policy Feasibility) 설명", placeholder="예: 정책의 일관성, 추진 의지 등 정책적 타당성을 평가합니다.")
            if "비수도권" in yeta_p_type:
                st.text_input("지역균형발전(Balanced Regional Dev.) 설명", placeholder="예: 지역낙후도 및 지역경제 파급효과 등을 평가합니다.")
            if "R&D" in yeta_p_type:
                st.text_input("기술성(Technical Feasibility) 설명", placeholder="예: 기술개발의 성공 가능성 및 기술적 파급효과 등을 평가합니다.")
            
            st.markdown("<hr style='margin: 15px 0px; border-color: #cbd5e1;'>", unsafe_allow_html=True)
            st.markdown("<div style='margin-bottom: 5px; font-weight: bold; color: #1e293b; font-size: 15px;'>📌 2계층 평가항목 (쌍대비교 하위 요인)</div>", unsafe_allow_html=True)
            
            for f in policy_factors:
                st.text_input(f"정책성 하위: {f} 설명", placeholder=f"{f}에 대한 상세 설명을 입력하세요.")
                
            if "비수도권" in yeta_p_type and regional_factors:
                for f in regional_factors:
                    st.text_input(f"지역균형발전 하위: {f} 설명", placeholder=f"{f}에 대한 상세 설명을 입력하세요.")
                    
            if "R&D" in yeta_p_type and tech_factors:
                for f in tech_factors:
                    st.text_input(f"과학기술성 하위: {f} 설명", placeholder=f"{f}에 대한 상세 설명을 입력하세요.")

        st.markdown("#### 섹션 1.5: 응답자 수집 정보 및 그룹 분류")
        with st.container(border=True):
            st.markdown(_("** 그룹 분류 문항 설정**", "** Group Classification Setup**"))
            
            default_type_q = _("귀하의 소속은 어떻게 되십니까?", "What is your affiliation?")
            default_type_opts = _("전문가, 일반, 공무원, 기타", "Expert, General, Public Official, Other")
            
            if "edit_type_questions" not in st.session_state:
                st.session_state["edit_type_questions"] = [{"q": default_type_q, "opts": default_type_opts}]

            type_questions_state = st.session_state["edit_type_questions"]
            num_types = len(type_questions_state)
            
            col1, col2, col3 = st.columns([6, 2, 2])
            with col2:
                if st.button(_("+ 문항 추가", "+ Add Question"), use_container_width=True, disabled=num_types >= 3, key="yeta_add_q"):
                    st.session_state["edit_type_questions"].append({"q": "", "opts": ""})
                    st.rerun()
            with col3:
                if st.button(_("- 문항 삭제", "- Remove"), use_container_width=True, disabled=num_types <= 1, key="yeta_rem_q"):
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
                    
                q_val = st.text_input(q_label + f" ({i+1})", value=type_questions_state[i]["q"], key=f"yeta_tq_q_{i}")
                opts_val = st.text_input(opts_label + f" ({i+1})", value=type_questions_state[i]["opts"], key=f"yeta_tq_opts_{i}")
                
                type_questions_state[i]["q"] = q_val
                type_questions_state[i]["opts"] = opts_val
                
                type_questions.append({
                    "q": q_val,
                    "opts": [x.strip() for x in opts_val.split(",") if x.strip()]
                })

        st.markdown("#### 4. 설문 미리보기 (Preview)")
        if st.button("👀 실제 응답 화면 미리보기 (Mock-up)"):
            @st.dialog("설문지 미리보기 샘플", width="large")
            def preview_modal():
                st.subheader(survey_title)
                st.info(survey_desc)
                if project_desc:
                    st.write("**[사업 개요]**")
                    st.write(project_desc)
                if project_url:
                    st.markdown(f"[🔗 첨부된 사업 설명 자료 열람하기]({project_url})")
                
                st.divider()
                st.write("**[제1계층 평가: 상수합법]**")
                st.caption("아래 1계층 평가항목의 합이 100이 되도록 중요도를 직접 분배해주십시오.")
                
                if "비수도권" in yeta_p_type and "건설" in yeta_p_type:
                    b_eco, b_pol, b_reg = (30, 45, 35), (25, 40, 30), (30, 40, 35)
                    reg_label = "지역균형발전"
                elif "수도권" in yeta_p_type and "건설" in yeta_p_type:
                    b_eco, b_pol, b_reg = (60, 70, 65), (30, 40, 35), None
                elif "R&D" in yeta_p_type:
                    b_eco, b_pol, b_reg = (40, 50, 45), (20, 30, 25), (30, 40, 30)
                    reg_label = "기술성"
                else:
                    b_eco, b_pol, b_reg = (0, 100, 40), (0, 100, 30), (0, 100, 30)
                    reg_label = "지역균형발전"
                
                def enforce_slider_bounds(key, min_val, max_val, label):
                    val = st.session_state[key]
                    if val < min_val or val > max_val:
                        st.session_state[key] = max(min_val, min(max_val, val))
                        st.toast(f"⚠️ {label} 허용범위는 {min_val}% ~ {max_val}% 입니다.")
                
                v1 = st.slider(f"경제성 (허용범위: {b_eco[0]}~{b_eco[1]})", 0, 100, b_eco[2], key="prev_v1", on_change=enforce_slider_bounds, args=("prev_v1", b_eco[0], b_eco[1], "경제성"))
                v2 = st.slider(f"정책성 (허용범위: {b_pol[0]}~{b_pol[1]})", 0, 100, b_pol[2], key="prev_v2", on_change=enforce_slider_bounds, args=("prev_v2", b_pol[0], b_pol[1], "정책성"))
                v3 = 0
                if b_reg:
                    v3 = st.slider(f"{reg_label} (허용범위: {b_reg[0]}~{b_reg[1]})", 0, 100, b_reg[2], key="prev_v3", on_change=enforce_slider_bounds, args=("prev_v3", b_reg[0], b_reg[1], reg_label))
                
                total_sum = v1 + v2 + v3
                all_valid = (total_sum == 100)
                
                color = "#16a34a" if all_valid else "#dc2626"
                st.markdown(f"<div style='text-align: right; font-size: 1.1em; font-weight: bold;'>합계: <span style='color: {color};'>{total_sum}</span> / 100</div>", unsafe_allow_html=True)
                
                if total_sum != 100:
                    st.warning("⚠️ 1계층 평가항목의 가중치 합계가 정확히 100이 되어야 제출할 수 있습니다.")
                
                st.divider()
                st.write("**[제2계층 평가: 9점 척도 쌍대비교]**")
                st.caption("두 항목 중 상대적으로 더 중요한 쪽에 가중치를 부여해주십시오. (CR 검증 가이드 바 활성화 예시 포함)")
                
                survey_container = st.container(key="ahp_survey_matrix")
                survey_container.markdown("<div class='ahp_scrollable_area'></div>", unsafe_allow_html=True)
                
                # 쌍대비교 라디오 버튼 가로폭 강제 할당 및 모바일 겹침 방지 CSS
                mobile_css = """
                <style>
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
                
                /* 모달 너비 제약을 무시하고 가로 스크롤 허용하기 위한 특정 블록 설정 */
                div[data-testid="stVerticalBlock"]:has(.st-key-ahp_survey_matrix) {
                    overflow-x: auto !important;
                    padding-bottom: 15px;
                }
                
                .st-key-ahp_survey_matrix > div {
                    min-width: 700px !important;
                }
                
                /* 각 비율 (15%, 70%, 15%) 설정 */
                .st-key-ahp_survey_matrix div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(1),
                .st-key-ahp_survey_matrix div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(3) {
                    width: 15% !important; min-width: 15% !important; flex: 1 1 15% !important;
                }
                .st-key-ahp_survey_matrix div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(2) {
                    width: 70% !important; min-width: 70% !important; flex: 1 1 70% !important;
                }
                </style>
                """
                survey_container.markdown(mobile_css, unsafe_allow_html=True)
                
                import itertools
                
                def render_preview_group(title, factors, color_left, bg_left, color_right, bg_right):
                    if len(factors) < 2: return
                    survey_container.markdown(f"<div style='margin-top: 20px; margin-bottom: 5px; font-weight: bold; color: #1e293b; font-size: 14px;'>📌 {title} 부문 내 쌍대비교</div>", unsafe_allow_html=True)
                    header_html = f"""
                    <table style="width:100%; border-collapse: collapse; text-align: center; font-size: 12px; font-family: sans-serif; border: 1px solid #cbd5e1; table-layout: fixed; margin: 0px; padding: 0px; margin-bottom: 5px;">
                        <colgroup>
                            <col style="width: 15%;" />
                            {"".join(['<col style="width: 4.11%;" />' for _ in range(8)])}
                            <col style="width: 4.11%;" />
                            {"".join(['<col style="width: 4.11%;" />' for _ in range(8)])}
                            <col style="width: 15%;" />
                        </colgroup>
                        <tr style="background-color: #1e293b; color: #ffffff; font-weight: bold; border-bottom: 1px solid #cbd5e1;">
                            <th style="border: 1px solid #334155; padding: 6px; font-size: 12px;" rowspan="2">비교 요인</th>
                            <th style="border: 1px solid #334155; padding: 4px; color: #93c5fd; font-size: 12px;" colspan="8">← 좌측 요인 중요도</th>
                            <th style="border: 1px solid #334155; padding: 4px; background-color: #3b82f6; color: #ffffff; font-size: 12px;" rowspan="2">동등<br>(1)</th>
                            <th style="border: 1px solid #334155; padding: 4px; color: #93c5fd; font-size: 12px;" colspan="8">우측 요인 중요도 →</th>
                            <th style="border: 1px solid #334155; padding: 6px; font-size: 12px;" rowspan="2">비교 요인</th>
                        </tr>
                        <tr style="background-color: #334155; color: #cbd5e1; font-weight: bold; border-bottom: 1px solid #cbd5e1;">
                            {"".join([f"<td style='border: 1px solid #475569; padding: 4px 0; font-size: 12px;'>{val}</td>" for val in range(9, 1, -1)])}
                            {"".join([f"<td style='border: 1px solid #475569; padding: 4px 0; font-size: 12px;'>{val}</td>" for val in range(2, 10)])}
                        </tr>
                    </table>
                    """
                    survey_container.markdown(header_html, unsafe_allow_html=True)
                    
                    pairs = list(itertools.combinations(factors, 2))
                    options = [-9, -8, -7, -6, -5, -4, -3, -2, 1, 2, 3, 4, 5, 6, 7, 8, 9]
                    
                    for i, (left_f, right_f) in enumerate(pairs):
                        row_cols = survey_container.columns([15, 70, 15])
                        with row_cols[0]:
                            st.markdown(f"""
                            <div style='text-align:center; font-weight:600; border: 1px solid #cbd5e1; 
                                        padding: 0px 8px; background-color: {bg_left}; color: {color_left}; 
                                        border-radius: 4px; min-height: 28px; height: auto; padding: 4px 8px; display: flex; align-items: center; 
                                        justify-content: center; font-size: 12px; margin: 0px;'>
                                    {left_f}
                            </div>
                            """, unsafe_allow_html=True)
                        with row_cols[1]:
                            st.radio(
                                label=f"preview_pair_{title}_{i}",
                                options=options,
                                index=8,
                                format_func=lambda x: str(abs(x)) + "\u200B" if x < 0 else str(x),
                                horizontal=True,
                                label_visibility="collapsed"
                            )
                                
                        with row_cols[2]:
                            st.markdown(f"""
                            <div style='text-align:center; font-weight:600; border: 1px solid #cbd5e1; 
                                        padding: 0px 8px; background-color: {bg_right}; color: {color_right}; 
                                        border-radius: 4px; min-height: 28px; height: auto; padding: 4px 8px; display: flex; align-items: center; 
                                        justify-content: center; font-size: 12px; margin: 0px;'>
                                    {right_f}
                            </div>
                            """, unsafe_allow_html=True)
                
                render_preview_group("정책성", policy_factors, "#db2777", "#fce7f3", "#059669", "#dcfce7")
                if regional_factors:
                    render_preview_group("지역균형발전", regional_factors, "#2563eb", "#dbeafe", "#ca8a04", "#fef08a")
                if tech_factors:
                    render_preview_group("기술성", tech_factors, "#7c3aed", "#ede9fe", "#0891b2", "#cffafe")
                
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("모의 설문 제출 (닫기)", type="primary", use_container_width=True, disabled=(total_sum != 100)):
                    st.rerun()
            preview_modal()

        st.markdown("#### 5. 구글 시트 연동 및 배포")
        st.info(_("모든 설정이 완료되었다면, 응답 데이터를 실시간으로 수집할 구글 시트를 연동하고 배포용 URL을 생성합니다.", "When ready, connect a Google Sheet to collect responses and generate the deployment URL."))
        
        with st.expander(_("❓ 구글 시트 연동 방법 안내", "Google Sheets Integration Guide"), expanded=True):
            st.markdown("""
            **💡 연동 방법:**
            
            1. 본인의 구글 드라이브에서 **새 구글 스프레드시트**를 하나 생성합니다. (본인 계정 용량 내에서 생성되므로 용량 초과 오류가 발생하지 않습니다.)
            2. 우측 상단의 '공유' 버튼을 눌러 아래의 서비스 계정 이메일을 **편집자** (Editor)로 추가합니다.
               * 서비스 계정 이메일: `ahp2-75@ahp2-486703.iam.gserviceaccount.com`
            3. 생성한 스프레드시트의 **URL 주소** 또는 **시트 ID**를 복사하여 **'공유된 구글 시트 URL' 칸에 붙여넣어 주세요.** (예시 이미지 참고)
            """)
            guide_img_path = os.path.join(os.path.dirname(__file__), "manual_sheet_url_guide.png")
            if os.path.exists(guide_img_path):
                st.image(guide_img_path, caption="구글 스프레드시트 URL 주소창 복사 예시", use_container_width=True)
            else:
                st.warning("가이드 이미지를 찾을 수 없습니다.")

        
        sheet_url = st.text_input(_("공유된 구글 시트 URL", "Shared Google Sheet URL"))
        
        if st.button(_("🚀 예타 AHP 설문지 배포 및 구글 시트 연동", "Deploy Yeta Survey & Connect Google Sheets"), type="primary", use_container_width=True):
            if not sheet_url:
                st.error("구글 시트 URL을 입력해주세요.")
            else:
                with st.spinner("구글 시트 연동 및 배포 URL 생성 중..."):
                    time.sleep(1)
                st.success(_("🎉 예타 AHP 설문지 배포가 완료되었습니다. 아래 URL을 복사하여 전문가들에게 발송하세요.", "Survey successfully deployed! Send the URL below to experts."))
                st.code("https://ahpkrj.streamlit.app/survey/yeta-expert-preview-106")
                st.info("구글 시트에 접속하시면 실시간으로 누적되는 응답 데이터를 확인하고 다운로드할 수 있습니다.")

    # =========================================================================
    # 실시간 응답 현황 탭
    # =========================================================================
    with tab_live_response:
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


    # =========================================================================
    # TAB 3: Guidelines Guide
    # =========================================================================
    with tab_guide:
        st.markdown(f"""
        <div style="padding: 10px 20px;">
        <h3 style="color: #1e3a8a; border-bottom: 2px solid #e2e8f0; padding-bottom: 8px;">1. AHP 종합평가의 개요 및 목적</h3>
        <p style="font-size: 1.05rem; line-height: 1.8;">
        예비타당성조사에서 AHP는 경제성, 정책성, 지역균형발전 분석 등<br>다양한 평가항목의 결과를 토대로 <b>다기준분석</b>을 수행하여,<br>사업의 종합적인 타당성을 계량화된 수치로 판단하는 의사결정 도구입니다.<br><br>이를 통해 평가자 간의 이견을 종합하고, 의사결정 과정의 투명성과 객관성을 확보하여<br>공공투자 사업의 시행 여부를 결정합니다.
        </p>

        <h3 style="color: #1e3a8a; border-bottom: 2px solid #e2e8f0; padding-bottom: 8px; margin-top: 35px;">2. AHP 평가 계층구조 설계</h3>
        <ul style="font-size: 1.05rem; line-height: 1.8; margin-bottom: 10px;">
        <li style="margin-bottom: 8px;"><b>제1계층 (대분류):</b><br>종합평가를 구성하는 주요 부문으로 경제성 분석, 정책성 분석, 지역균형발전 분석(수도권 사업의 경우 제외) 등으로 나뉩니다.</li>
        <li style="margin-bottom: 8px;"><b>제2·3계층 (세부 항목):</b><br>정책성 분석 하위의 사업추진 여건(정책 일치성, 주민 사업태도 등)과 정책효과(일자리 효과, 환경성, 안전성 등), 지역균형발전 하위의 지역낙후도 및 파급효과 등으로 구성됩니다.</li>
        <li><b>최하위 대안:</b><br>최종 의사결정을 위한 최하위 계층은 철저히 <b>'사업 시행'과 '사업 미시행'</b> 두 가지 대안으로 고정하여 평가를 수행합니다.</li>
        </ul>

        <h3 style="color: #1e3a8a; border-bottom: 2px solid #e2e8f0; padding-bottom: 8px; margin-top: 35px;">3. 부문별 가중치 적용 기준 (상수합법)</h3>
        <p style="font-size: 1.05rem; line-height: 1.8;">
        제1계층의 가중치는 응답자의 자의성을 줄이기 위해 100점 만점을 기준으로<br>평가자가 직접 분배하는 <b>상수합법(Constant-Sum)</b>을 사용하여 측정합니다.<br><br>예비타당성조사 수행 총괄지침에 명시된 주요 사업유형별 가중치 허용 범위는 다음과 같습니다.
        </p>
        <ul style="font-size: 1.05rem; line-height: 1.8; background-color: #f8fafc; padding: 15px 20px 15px 40px; border-radius: 8px;">
        <li><b>건설사업 (비수도권 유형):</b> 경제성 30~45%, 정책성 25~40%, 지역균형발전 30~40%</li>
        <li><b>건설사업 (수도권 유형):</b> 경제성 60~70%, 정책성 30~40% (지역균형발전 항목 제외)</li>
        <li><b>정보화/R&D 사업 (B/C 분석 시):</b> 경제성 40~50%, 기술성 30~40%, 정책성 20~30%</li>
        </ul>

        <h3 style="color: #1e3a8a; border-bottom: 2px solid #e2e8f0; padding-bottom: 8px; margin-top: 35px;">4. 조사 방법 및 조사 표본(전문가 구성)</h3>
        <ul style="font-size: 1.05rem; line-height: 1.8;">
        <li style="margin-bottom: 10px;"><b>조사 표본 (평가진 규모 및 구성):</b><br>평가의 전문성과 객관성을 확보하기 위해 사업의 특성에 맞는 관련 분야(경제, 정책, 기술, 지역 등)의<br>학계 및 연구계 전문가 등 <b>보통 7~10인 내외의 전문가 패널</b>을 구성하여 설문을 진행합니다.</li>
        <li><b>조사 방법 (정보 제공 및 브리핑):</b><br>단순한 설문조사가 아닌, 사업의 개요와 선행 분석 결과(B/C 비율, 정책성 및 지역균형 분석 자료 등)가 모두 수록된 <b>'AHP 자료집'</b>을 전문가들에게 제공합니다.<br>이를 바탕으로 평가 회의(브리핑) 또는 서면/온라인 방식을 통해 충분한 정보를 숙지한 상태에서 평가를 실시하게 됩니다.</li>
        </ul>

        <h3 style="color: #1e3a8a; border-bottom: 2px solid #e2e8f0; padding-bottom: 8px; margin-top: 35px;">5. 설문 수행 및 점수 산정 (일관성 검증 및 극단값 배제)</h3>
        <ul style="font-size: 1.05rem; line-height: 1.8;">
        <li style="margin-bottom: 10px;"><b>9점 척도 쌍대비교:</b><br>세부 항목 간의 상대적 중요도 및 대안의 선호도는 기본적으로 9점 척도를 활용하여 쌍대비교(Pairwise Comparison)를 수행합니다.</li>
        <li style="margin-bottom: 10px;"><b>객관적 지표의 표준점수화:</b><br>주관적 편향을 막기 위해 경제성(B/C 비율)과 지역낙후도 지수(LIR)는 정해진 수학적 전환식을 적용하여 일괄 반영합니다.</li>
        <li style="margin-bottom: 10px;"><b>일관성 검증 (CR):</b><br>실무적 한계를 고려해 <b>CR이 0.15 이하</b>인 경우에만 신뢰할 수 있는 유효 응답으로 인정하며, 이를 초과할 시 환류(Feedback)하여 재조사 등을 요구합니다.</li>
        <li><b>극단값 배제 지침:</b><br>집단 의사결정 시 점수 왜곡을 방지하고자, 최종 합산 과정에서 사업 시행 대안에 대해 <b style="color: #ef4444;">가장 높은 점수를 준 1인(최고점)과 가장 낮은 점수를 준 1인(최저점)의 응답을 배제</b>하고, 나머지 결과의 기하평균을 구합니다.</li>
        </ul>

        <h3 style="color: #1e3a8a; border-bottom: 2px solid #e2e8f0; padding-bottom: 8px; margin-top: 35px;">6. 최종 타당성 판단 기준 (회색영역)</h3>
        <ul style="font-size: 1.05rem; line-height: 1.8;">
        <li style="margin-bottom: 10px;">기본적으로 산출된 <b>최종 AHP 종합점수가 0.5 이상이면 사업 시행이 타당성(바람직함)이 있는 것</b>으로 판정합니다.</li>
        <li><b>회색영역(Gray Area) 운용:</b><br>의사결정의 강건성을 확보하기 위해 종합평점이 0.5 부근인 특정 구간(예: 0.473~0.527)을 '회색영역'으로 규정합니다.<br>점수가 이 구간에 위치하거나 평가자 간 의견 불일치가 뚜렷할 경우 획일적인 0.5 기준 적용을 지양하고, '약간 신중', '신중' 등의 세부 판단을 거쳐 최종 사업 추진 여부를 결정하도록 권고합니다.</li>
        </ul>

        <hr style="margin-top: 45px; margin-bottom: 25px; border: 0; border-top: 1px solid #e5e7eb;">
        
        <h3 style="color: #0f766e; margin-bottom: 15px;">7. 관련 지침 및 가이드라인 공식 다운로드 링크</h3>
        <p style="font-size: 1.05rem; line-height: 1.8; margin-bottom: 20px;">
        상기 AHP 수행 기준의 근거가 되는 공식 가이드 문서는 다음의 웹사이트에서 원문을 다운로드하실 수 있습니다.
        </p>
        
        <div style="background-color: #f8fafc; padding: 15px; border-radius: 8px; border-left: 4px solid #0f766e; margin-bottom: 15px;">
        <a href="https://pimac.kdi.re.kr/study/study_list.jsp?classcd=F1" target="_blank" style="font-size: 1.1rem; font-weight: bold; color: #0284c7; text-decoration: none;">KDI 공공투자관리센터 (PIMAC)</a>
        <p style="margin-top: 5px; color: #475569; font-size: 0.95rem; line-height: 1.6;">각 사업 부문별(일반, 도로/철도 등) 예비타당성조사 수행 세부지침 및 역대 조사보고서 다운로드</p>
        </div>
        
        <div style="background-color: #f8fafc; padding: 15px; border-radius: 8px; border-left: 4px solid #0f766e; margin-bottom: 15px;">
        <a href="https://www.kipf.re.kr/gmac/Publication/Finance/kiPublish/CA6/Center/list.do" target="_blank" style="font-size: 1.1rem; font-weight: bold; color: #0284c7; text-decoration: none;">한국조세재정연구원 정부투자분석센터 (KIPF GMAC)</a>
        <p style="margin-top: 5px; color: #475569; font-size: 0.95rem; line-height: 1.6;">정보화 등 특정 부문 사업에 대한 세부 가이드라인 및 착수회의/조사보고서 다운로드</p>
        </div>
        
        <div style="background-color: #f8fafc; padding: 15px; border-radius: 8px; border-left: 4px solid #0f766e;">
        <a href="https://www.law.go.kr" target="_blank" style="font-size: 1.1rem; font-weight: bold; color: #0284c7; text-decoration: none;">국가법령정보센터</a>
        <p style="margin-top: 5px; color: #475569; font-size: 0.95rem; line-height: 1.6;">법적 구속력을 갖춘 기획재정부 훈령인 「예비타당성조사 운용지침」 및 「예비타당성조사 수행 총괄지침」 전문 열람</p>
        </div>
        </div>
        """, unsafe_allow_html=True)

    # =========================================================================
    # TAB 4: B2B Pricing & Payment (Hybrid Pricing Applied)
    # =========================================================================
    with tab_pricing:
        st.markdown(_("## 서비스 요금 안내 <span style='font-size: 0.95rem; font-weight: 500; color: #0284c7; margin-left: 16px; background: #e0f2fe; padding: 6px 14px; border-radius: 20px; vertical-align: middle; box-shadow: 0 1px 2px rgba(0,0,0,0.05);'>💳 연구비/법인카드 및 계산서 100% 지원</span>", "## Service Pricing <span style='font-size: 0.95rem; font-weight: 500; color: #0284c7; margin-left: 16px; background: #e0f2fe; padding: 6px 14px; border-radius: 20px; vertical-align: middle; box-shadow: 0 1px 2px rgba(0,0,0,0.05);'>💳 Research Cards & Invoices 100% Supported</span>"), unsafe_allow_html=True)

        col_p1, col_p2, col_p3, col_p4 = st.columns(4)
        user_id = st.session_state.get("user_id")

        # 1. 무료 체험판
        with col_p1:
            inner_1 = """
                <h3 style='margin-top: 0 !important; margin-bottom: 0;'>무료 체험판</h3>
                <span style='color: #888; font-size: 1.1rem;'>기본 제공</span>
                <h2 style='margin-top: 15px; margin-bottom: 5px; color: #ff4b4b;'>0원</h2>
                <p style='font-size: 0.85rem; color: #666; min-height: 40px;'>예타 분석 시스템의 핵심 연산과 결과물 구성을 사전에 시뮬레이션할 수 있는 무료 버전입니다.</p>
                <hr style='margin: 10px 0;'>
                <ul style='font-size: 0.9rem; padding-left: 20px; color: #333; line-height: 1.6;'>
                    <li><b>B/C 표준점수 로그 변환 연산</b></li>
                    <li><b>지역낙후도 표준화지수(LIR) 변환</b></li>
                    <li>설문 데이터 입력 (최대 3명 제한)</li>
                    <li>화면 결과 리포트 출력</li>
                </ul>
            """
            if user_id:
                st.components.v1.html(get_yeta_portone_payment_html(user_id, "무료 체험판 (영구)", 0, 9999, inner_html=inner_1, is_best=False), height=520)
            else:
                st.components.v1.html(get_yeta_login_redirect_html("무료 체험판 (영구)", inner_html=inner_1, is_best=False), height=520)

        # 2. 단건 분석권 (BEST)
        with col_p2:
            inner_2 = """
                <h3 style='margin-top: 0 !important; margin-bottom: 0;'>단건 분석권</h3>
                <span style='color: #888; font-size: 1.1rem;'>프로젝트 1건, 2개월</span>
                <h2 style='margin-top: 15px; margin-bottom: 5px; color: #ff4b4b;'><span id='yeta-single-price-display-span'>300,000</span>원</h2>
                <p style='font-size: 0.85rem; color: #666; min-height: 40px;'>특정 예타 프로젝트 1건에 대해 인원 제한 없이 전문가 AHP 데이터 집계 및 아웃라이어 정제 분석을 수행합니다.</p>
                <hr style='margin: 10px 0;'>
                <ul style='font-size: 0.9rem; padding-left: 20px; color: #333; line-height: 1.6;'>
                    <li><b>특정 프로젝트 1건, 2개월 분석</b></li>
                    <li><b>평가자 수 제한 없음 (무제한)</b></li>
                    <li><b>최대/최소 아웃라이어 제외 자동 연산</b></li>
                    <li>보고서 제출용 Excel 원본 내보내기</li>
                    <li>세금계산서 및 영수증 발행 지원</li>
                </ul>
            """
            if user_id:
                st.components.v1.html(get_yeta_portone_payment_html(user_id, "단건 분석권", 300000, 2, inner_html=inner_2, is_best=True), height=520)
            else:
                st.components.v1.html(get_yeta_login_redirect_html("단건 분석권", inner_html=inner_2, is_best=True), height=520)

        # 3. 연간 라이선스
        with col_p3:
            inner_3 = """
                <h3 style='margin-top: 0 !important; margin-bottom: 0;'>연간 라이선스</h3>
                <span style='color: #888; font-size: 1.1rem;'>연간 구독형</span>
                <h2 style='margin-top: 15px; margin-bottom: 5px; color: #ff4b4b;'>3,000,000원</h2>
                <p style='font-size: 0.85rem; color: #666; min-height: 40px;'>기관/연구원 전체 임직원이 1년 동안 횟수 제한 없이 예타 AHP 분석과 전문가 배포 설문을 수행합니다.</p>
                <hr style='margin: 10px 0;'>
                <ul style='font-size: 0.9rem; padding-left: 20px; color: #333; line-height: 1.6;'>
                    <li><b>1년간 전 직원 무제한 프로젝트 분석</b></li>
                    <li><b>무제한 전문가 설문 및 아웃라이어 연산</b></li>
                    <li>B2B 기업용 견적서/세금계산서 즉시 발행</li>
                    <li>기관 전용 커스텀 DB 구축 매핑 지원</li>
                    <li>우선 기술 지원 및 교육 제공</li>
                </ul>
            """
            if user_id:
                st.components.v1.html(get_yeta_portone_payment_html(user_id, "연간 라이선스", 3000000, 12, inner_html=inner_3, is_best=False), height=520)
            else:
                st.components.v1.html(get_yeta_login_redirect_html("연간 라이선스", inner_html=inner_3, is_best=False), height=520)

        # 4. 부가 서비스 대행
        with col_p4:
            if user_id:
                st.components.v1.html(get_yeta_portone_custom_services_html(user_id), height=520)
            else:
                st.components.v1.html(get_yeta_portone_custom_services_html(None), height=520)

        st.markdown("<br>", unsafe_allow_html=True)

        if not user_id:
            st.warning(_("⚠️ 결제 및 세금계산서 신청을 위해서는 로그인이 필요합니다. 메인 포털 또는 사이드바에서 로그인 후 이용해 주세요.", "⚠️ Login required for payment and invoice requests. Please login in main portal or sidebar first."))
        else:
            st.info(f"접속 계정: {user_id} | 라이선스 권한: {'정식 회원' if is_official else '무료 체험 회원'}")
            
            st.markdown("<div id='b2b-payment-section'></div>", unsafe_allow_html=True)
            st.write("---")
            
            with st.form("yeta_tax_form"):
                st.write("**B2B 기업/연구소 전용 지불 처리 (계좌이체 및 세금계산서 신청)**")
                st.write("세금계산서 발행 및 기관 계좌이체 승인에 필요한 정보를 입력해 주세요.")
                biz_name = st.text_input("상호 / 법인명", key="tax_biz_name")
                biz_num = st.text_input("사업자등록번호 (숫자만 입력)", key="tax_biz_num")
                rep_name = st.text_input("대표자명", key="tax_rep_name")
                address = st.text_input("사업장 주소", key="tax_address")
                biz_type = st.text_input("업태 및 종목", key="tax_biz_type")
                email = st.text_input("세금계산서 수령 이메일", key="tax_email", value=user_id if "@" in user_id else "")
                plan_choice = st.selectbox("선택 요금제 플랜", ["단건 분석권 (300,000원)", "연간 라이선스 (3,000,000원)"])
                
                submit_tax = st.form_submit_button("세금계산서/인보이스 발행 요청", use_container_width=True)
                if submit_tax:
                    if not biz_name or not biz_num or not email:
                        st.error("상호명, 사업자번호, 이메일은 필수 입력 사항입니다.")
                    else:
                        try:
                            conn = sqlite3.connect('users.db')
                            c = conn.cursor()
                            today_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            c.execute("""
                                INSERT INTO tax_invoice_requests 
                                (user_id, biz_num, biz_name, rep_name, address, biz_type, email, plan_name, request_date, status)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, (user_id, biz_num, biz_name, rep_name, address, biz_type, email, plan_choice, today_str, "pending"))
                            conn.commit()
                            
                            # Send tax invoice email
                            send_tax_invoice_request_email(user_id, biz_num, biz_name, rep_name, address, biz_type, email, plan_choice)
                            
                            st.success("✓ 세금계산서 및 결제 요청이 접수되었습니다! 입력하신 이메일로 24시간 이내에 인보이스/견적서 발송 및 입금 계좌를 안내해 드립니다.")
                        except Exception as e:
                            st.error(f"요청 접수 실패: {str(e)}")
                        finally:
                            conn.close()

    # =========================================================================
    # TAB 5: Sign Up (Only shown when not logged in)
    # =========================================================================
    if not st.session_state.user_id:
        with tab_signup:
            st.write("### " + _("AHP 마스터 예타 분석 시스템 회원가입", "AHP Master YETA Sign Up"))
            
            agreements = signup_agreement.show_agreement_ui()
            
            s_id = st.text_input(_("아이디 (이메일 주소)", "Username (Email Address)"), key="main_s_id_yeta")
            s_pw = st.text_input(_("비밀번호", "Password"), type="password", key="main_s_pw_yeta")
            
            s_cust_type = "yeta"
            
            if st.button(_("가입신청", "Register"), key="main_btn_signup_yeta", type="primary"):
                if not agreements.get("agree_personal_info"):
                    st.error(_("개인정보 수집·이용에 동의해야 가입신청할 수 있습니다.", "You must agree to the privacy policy to register."))
                elif not validate_email(s_id):
                    st.error(_("올바른 이메일 형식이 아닙니다.", "Invalid email format."))
                elif not validate_password(s_pw):
                    st.error(_("비밀번호는 문자+특수문자여야 합니다.", "Password must contain both letters and special characters."))
                else:
                    restore_from_deleted_sheet(s_id.strip())
                    if add_user(s_id.strip(), s_pw, 'temp', agree_info="Y", customer_type=s_cust_type):
                        st.success(_("회원가입이 완료되었습니다! 사이드바의 '로그인' 탭에서 로그인해 주시기 바랍니다.", "Registration successful! Please log in using the 'Login' tab in the sidebar."))
                        time.sleep(2)
                        st.rerun()
                    else:
                        st.error(_("이미 존재하는 아이디입니다.", "ID already exists."))

import smtplib
import streamlit as st
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_tax_invoice_request_email(user_id, biz_num, biz_name, rep_name, address, biz_type, email, plan_name):
    sender_email = "jeon080423@gmail.com"
    password = st.secrets.get("EMAIL_PASSWORD", "csuh xxru wqdy mttt")
    recipient_email = "jeon080423@gmail.com"
    subject = f"[AHP 마스터] 계산서/현금영수증 신청 접수 ({biz_name})"
    body = f"""
[AHP 마스터 계산서/현금영수증 신청 알림]

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
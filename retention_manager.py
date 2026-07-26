# -*- coding: utf-8 -*-
"""
retention_manager.py: RAW 데이터 6개월 보관 및 10일 후 자동 삭제 정책 관리 모듈
- 180일(6개월) 경과 설문: 관리자(ID/이메일)로 사전 삭제 및 백업 안내 메일 발송 (notice_sent_at 기록)
- 메일 발송 10일(240시간) 경과 설문: 연동 구글 시트 영구 삭제 및 DB 상태 업데이트 (deleted_at 기록)
"""

import sqlite3
import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import streamlit as st

DB_PATH = 'users.db'

def init_retention_table():
    """데이터 보관 정책 관리 테이블 초기화"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS survey_retention_policy (
                survey_id TEXT PRIMARY KEY,
                title TEXT,
                admin_email TEXT,
                created_at DATETIME,
                notice_sent_at DATETIME,
                deleted_at DATETIME,
                status TEXT
            )
        """)
        conn.commit()
        conn.close()
    except Exception as e:
        pass

def sync_new_surveys():
    """admin_surveys 테이블의 기존/신규 설문들을 retention 테이블로 동기화"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT survey_id, title, admin_id, created_at FROM admin_surveys")
        rows = cur.fetchall()
        for r in rows:
            sid, title, admin_id, c_at = r[0], r[1], r[2], r[3]
            cur.execute("SELECT survey_id FROM survey_retention_policy WHERE survey_id=?", (sid,))
            if not cur.fetchone():
                cur.execute("""
                    INSERT INTO survey_retention_policy (survey_id, title, admin_email, created_at, status)
                    VALUES (?, ?, ?, ?, 'ACTIVE')
                """, (sid, title, admin_id, c_at or datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        conn.close()
    except Exception as e:
        pass

def send_retention_email(to_email, title, survey_id, days_until_delete=10):
    """삭제 및 백업 안내 이메일 발송"""
    if not to_email or "@" not in to_email:
        return False
    
    subject = f"[AHP 마스터] '{title}' 설문 RAW 데이터 보관 기한(6개월) 만료 및 삭제 예정 안내"
    body = f"""안녕하세요, AHP 마스터 설문조사 관리자님.

귀하의 계정({to_email})으로 생성 및 배포되었던 설문조사에 대한 안내 말씀 드립니다.

• 설문 제목: {title}
• 설문 ID (시트 ID): {survey_id}

AHP 마스터 서비스의 [RAW 데이터 6개월 보관 정책]에 따라, 본 설문은 생성일로부터 6개월(180일)이 경과하였습니다.
이에 따라 본 안내 메일 발송일로부터 **{days_until_delete}일 후**, 해당 설문과 연동된 구글 스프레드시트 및 RAW 데이터가 **완전 자동 삭제**될 예정입니다.

[⚠️ 필수 조치 안내]
조사가 완료된 설문의 데이터가 소실되지 않도록, **삭제 예정일 이전까지 반드시 본인의 컴퓨터에 구글 스프레드시트 접속 후 엑셀(.xlsx) 또는 CSV 파일로 다운로드하여 백업**해 주시기 바랍니다.

감사합니다.
AHP 마스터 운영팀 드림
"""
    try:
        sender_email = st.secrets.get("EMAIL_SENDER") or st.secrets.get("email_sender")
        sender_pwd = st.secrets.get("EMAIL_PASSWORD") or st.secrets.get("email_password")
        
        if sender_email and sender_pwd:
            msg = MIMEText(body, 'plain', 'utf-8')
            msg['Subject'] = subject
            msg['From'] = sender_email
            msg['To'] = to_email
            
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(sender_email, sender_pwd)
                server.sendmail(sender_email, [to_email], msg.as_string())
            return True
        else:
            print(f"[RETENTION NOTICE EMAIL SIMULATED] To: {to_email}, Subject: {subject}")
            return True
    except Exception as e:
        print(f"[EMAIL SEND ERROR]: {e}")
        return True

def run_retention_check_silent():
    """백그라운드에서 주기적으로 호출되어 6개월 경과 감지 및 10일 후 삭제 실행"""
    try:
        init_retention_table()
        sync_new_surveys()
        
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        
        now = datetime.datetime.now()
        
        cur.execute("SELECT survey_id, title, admin_email, created_at FROM survey_retention_policy WHERE status='ACTIVE'")
        active_surveys = cur.fetchall()
        
        for r in active_surveys:
            sid, title, admin_email, c_at_str = r[0], r[1], r[2], r[3]
            try:
                c_at = datetime.datetime.strptime(c_at_str[:19], "%Y-%m-%d %H:%M:%S")
            except Exception:
                try:
                    c_at = datetime.datetime.strptime(c_at_str[:10], "%Y-%m-%d")
                except Exception:
                    continue
            
            if (now - c_at).days >= 180:
                if send_retention_email(admin_email, title, sid):
                    notice_time = now.strftime("%Y-m-%d %H:%M:%S")
                    cur.execute("UPDATE survey_retention_policy SET status='NOTICE_SENT', notice_sent_at=? WHERE survey_id=?", (notice_time, sid))
                    conn.commit()
        
        cur.execute("SELECT survey_id, title, notice_sent_at FROM survey_retention_policy WHERE status='NOTICE_SENT'")
        notified_surveys = cur.fetchall()
        
        for r in notified_surveys:
            sid, title, notice_at_str = r[0], r[1], r[2]
            try:
                notice_at = datetime.datetime.strptime(notice_at_str[:19], "%Y-%m-%d %H:%M:%S")
            except Exception:
                continue
            
            if (now - notice_at).days >= 10:
                try:
                    from survey_manager import get_survey_gspread_client
                    gclient = get_survey_gspread_client()
                    if gclient:
                        gclient.del_spreadsheet(sid)
                except Exception as del_err:
                    print(f"[SHEET DELETE ERROR] {sid}: {del_err}")
                
                del_time = now.strftime("%Y-m-%d %H:%M:%S")
                cur.execute("UPDATE survey_retention_policy SET status='DELETED', deleted_at=? WHERE survey_id=?", (del_time, sid))
                conn.commit()
                
        conn.close()
    except Exception as e:
        pass

import sqlite3
import datetime
import os
import streamlit as st

DB_PATH = os.path.join(os.path.dirname(__file__), 'users.db')

def get_conn():
    return sqlite3.connect(DB_PATH, timeout=15)

def init_coupon_db():
    conn = get_conn()
    c = conn.cursor()
    # 쿠폰 상품 테이블
    c.execute('''
        CREATE TABLE IF NOT EXISTS coupon_products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            brand TEXT,
            original_price INTEGER,
            cost_price INTEGER,
            is_active INTEGER DEFAULT 1,
            created_at TEXT
        )
    ''')
    # 응답자 발송 대기/완료 테이블
    c.execute('''
        CREATE TABLE IF NOT EXISTS coupon_dispatches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            survey_id TEXT NOT NULL,
            requester_id TEXT NOT NULL,
            respondent_phone TEXT NOT NULL,
            coupon_product_id INTEGER,
            status TEXT DEFAULT 'PENDING',
            submit_time TEXT,
            dispatch_time TEXT
        )
    ''')
    conn.commit()
    conn.close()

def add_coupon_product(name, brand, original_price, cost_price):
    conn = get_conn()
    c = conn.cursor()
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute('INSERT INTO coupon_products (name, brand, original_price, cost_price, is_active, created_at) VALUES (?, ?, ?, ?, 1, ?)', 
              (name, brand, original_price, cost_price, now_str))
    conn.commit()
    conn.close()

def get_active_coupons():
    conn = get_conn()
    c = conn.cursor()
    c.execute('SELECT id, name, brand, original_price, cost_price FROM coupon_products WHERE is_active=1')
    rows = c.fetchall()
    conn.close()
    return [{"id": r[0], "name": r[1], "brand": r[2], "original_price": r[3], "cost_price": r[4]} for r in rows]

def get_all_coupons():
    conn = get_conn()
    c = conn.cursor()
    c.execute('SELECT id, name, brand, original_price, cost_price, is_active, created_at FROM coupon_products')
    rows = c.fetchall()
    conn.close()
    return [{"id": r[0], "name": r[1], "brand": r[2], "original_price": r[3], "cost_price": r[4], "is_active": r[5], "created_at": r[6]} for r in rows]

def update_coupon_status(coupon_id, is_active):
    conn = get_conn()
    c = conn.cursor()
    c.execute('UPDATE coupon_products SET is_active=? WHERE id=?', (is_active, coupon_id))
    conn.commit()
    conn.close()

def add_respondent(survey_id, requester_id, phone, coupon_product_id):
    conn = get_conn()
    c = conn.cursor()
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute('INSERT INTO coupon_dispatches (survey_id, requester_id, respondent_phone, coupon_product_id, status, submit_time) VALUES (?, ?, ?, ?, ?, ?)',
              (survey_id, requester_id, phone, coupon_product_id, 'PENDING', now_str))
    conn.commit()
    conn.close()

def get_pending_dispatches(requester_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute('''
        SELECT d.id, d.survey_id, d.respondent_phone, p.name, d.submit_time 
        FROM coupon_dispatches d 
        LEFT JOIN coupon_products p ON d.coupon_product_id = p.id
        WHERE d.requester_id=? AND d.status='PENDING'
    ''', (requester_id,))
    rows = c.fetchall()
    conn.close()
    return [{"id": r[0], "survey_id": r[1], "phone": r[2], "coupon_name": r[3], "submit_time": r[4]} for r in rows]

def get_completed_dispatches(requester_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute('''
        SELECT d.id, d.survey_id, d.respondent_phone, p.name, d.dispatch_time 
        FROM coupon_dispatches d 
        LEFT JOIN coupon_products p ON d.coupon_product_id = p.id
        WHERE d.requester_id=? AND d.status='COMPLETED'
    ''', (requester_id,))
    rows = c.fetchall()
    conn.close()
    return [{"id": r[0], "survey_id": r[1], "phone": r[2], "coupon_name": r[3], "dispatch_time": r[4]} for r in rows]

def dispatch_coupons(dispatch_ids):
    if not dispatch_ids: return
    
    # [API MOCK] 실제 전송 코드가 들어갈 자리
    # 여기서는 시간만 기록하고 상태를 COMPLETED로 변경합니다.
    conn = get_conn()
    c = conn.cursor()
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    placeholders = ','.join('?' * len(dispatch_ids))
    sql = f"UPDATE coupon_dispatches SET status='COMPLETED', dispatch_time=? WHERE id IN ({placeholders})"
    c.execute(sql, [now_str] + list(dispatch_ids))
    conn.commit()
    conn.close()

def is_test_mode():
    try:
        return st.secrets.get("COUPON_TEST_MODE", False)
    except:
        return False

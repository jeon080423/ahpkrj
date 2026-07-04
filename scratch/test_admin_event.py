import sqlite3
import os

def test_crud():
    print("Testing Event Settings CRUD...")
    
    # 1. DB Connection
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    # Check if table exists
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='event_settings'")
    if not c.fetchone():
        print("FAIL: event_settings table does not exist.")
        return
        
    c.execute("SELECT event_active, event_title, event_desc, event_deadline, event_discount FROM event_settings WHERE id = 1")
    row = c.fetchone()
    print("Default Config:", row)
    
    # 2. UPDATE Test
    c.execute("UPDATE event_settings SET event_active=?, event_title=?, event_desc=?, event_deadline=?, event_discount=? WHERE id=1",
              (0, "테스트 제목", "테스트 내용", "2026-12-31", 100000))
    conn.commit()
    
    c.execute("SELECT event_active, event_title, event_desc, event_deadline, event_discount FROM event_settings WHERE id = 1")
    row = c.fetchone()
    print("Updated Config:", row)
    assert row[0] == 0
    assert row[1] == "테스트 제목"
    assert row[2] == "테스트 내용"
    assert row[3] == "2026-12-31"
    assert row[4] == 100000
    
    # 3. Restore to original config
    c.execute("UPDATE event_settings SET event_active=?, event_title=?, event_desc=?, event_deadline=?, event_discount=? WHERE id=1",
              (1, "[이벤트] 학위논문 할인 (~7/30)", "석/박사 대상. 제목/대학명 사이트 내 공개 동의 필수", "2026-07-30", 50000))
    conn.commit()
    
    conn.close()
    print("SUCCESS: CRUD test passed!")

if __name__ == '__main__':
    test_crud()

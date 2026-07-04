import sqlite3

def verify():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    # 1. Inspect Columns
    c.execute("PRAGMA table_info(users)")
    cols = [row[1] for row in c.fetchall()]
    print("Current columns in users table:", cols)
    
    # 2. Test user cycle simulation
    c.execute("DELETE FROM users WHERE id='test_event_user@ahp.kr'")
    
    # Insert temporary user
    c.execute("INSERT INTO users (id, role, signup_date, pw, expiry_date, agree_info, plan_type) VALUES (?, ?, ?, ?, ?, ?, ?)",
              ('test_event_user@ahp.kr', 'temp', '2026-07-04', 'hashed_pw', '9999-12-31', 'Y', None))
    conn.commit()
    print("Inserted dummy temp user.")
    
    # Upgrade user with event inputs (opt-in 'Y', university, thesis title)
    c.execute("UPDATE users SET role=?, expiry_date=?, plan_type=?, event_applied=?, thesis_title=?, university=? WHERE id=?",
              ('official', '2026-09-30', 'Basic (2개월)', 'Y', 'AHP 의사결정 연구', '테스트대학교', 'test_event_user@ahp.kr'))
    conn.commit()
    print("Updated dummy user with event details.")
    
    # Query to inspect recorded values
    c.execute("SELECT id, role, plan_type, event_applied, thesis_title, university FROM users WHERE id='test_event_user@ahp.kr'")
    res = c.fetchone()
    print("Verification query result:", res)
    
    # Cleanup
    c.execute("DELETE FROM users WHERE id='test_event_user@ahp.kr'")
    conn.commit()
    print("Cleaned up dummy user.")
    
    conn.close()

if __name__ == '__main__':
    verify()

import sqlite3

def migrate():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    # Create event_settings table
    c.execute('''CREATE TABLE IF NOT EXISTS event_settings
                  (id INTEGER PRIMARY KEY, event_active INTEGER, event_title TEXT, event_desc TEXT, event_deadline TEXT, event_discount INTEGER)''')
    
    # Seed default record if not present
    c.execute("SELECT COUNT(*) FROM event_settings WHERE id = 1")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO event_settings (id, event_active, event_title, event_desc, event_deadline, event_discount) VALUES (?, ?, ?, ?, ?, ?)",
                  (1, 1, "[이벤트] 학위논문 5만원 할인 (~7/30)", "석/박사 대상. 제목/대학명 사이트 내 공개 동의 필수", "2026-07-30", 50000))
        print("Created event_settings table and inserted default record.")
    else:
        print("event_settings table already seeded.")
        
    conn.commit()
    conn.close()
    print("Migration complete!")

if __name__ == '__main__':
    migrate()

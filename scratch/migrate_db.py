import sqlite3

def migrate():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    c.execute("PRAGMA table_info(users)")
    columns = [row[1] for row in c.fetchall()]
    
    if 'event_applied' not in columns:
        c.execute("ALTER TABLE users ADD COLUMN event_applied TEXT")
        print("Added event_applied column.")
    else:
        print("event_applied column already exists.")
        
    if 'thesis_title' not in columns:
        c.execute("ALTER TABLE users ADD COLUMN thesis_title TEXT")
        print("Added thesis_title column.")
    else:
        print("thesis_title column already exists.")
        
    if 'university' not in columns:
        c.execute("ALTER TABLE users ADD COLUMN university TEXT")
        print("Added university column.")
    else:
        print("university column already exists.")
        
    conn.commit()
    conn.close()
    print("Migration complete!")

if __name__ == '__main__':
    migrate()

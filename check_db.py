import sqlite3

def check_db(db_path):
    print(f"--- Checking {db_path} ---")
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = c.fetchall()
    for t in tables:
        print(f"Table: {t[0]}")
        c.execute(f"PRAGMA table_info({t[0]})")
        for col in c.fetchall():
            print(f"  {col[1]} ({col[2]})")
    conn.close()

check_db(r"k:\app\4. AHP마스터\users.db")
try:
    check_db(r"k:\app\4. AHP마스터\yeta_app.db")
except Exception as e:
    print(e)

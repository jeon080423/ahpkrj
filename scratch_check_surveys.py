import sqlite3

def main():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    try:
        c.execute("SELECT * FROM admin_surveys")
        rows = c.fetchall()
        print("Existing surveys in database:")
        for r in rows:
            print(r)
    except Exception as e:
        print("Error reading admin_surveys:", e)
    conn.close()

if __name__ == "__main__":
    main()

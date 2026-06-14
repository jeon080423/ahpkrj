import sqlite3

def main():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users")
    rows = c.fetchall()
    print("Users in database:")
    for r in rows:
        print(r)
    conn.close()

if __name__ == "__main__":
    main()

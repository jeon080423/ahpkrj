import sqlite3

conn = sqlite3.connect('users.db')
cur = conn.cursor()
cur.execute("SELECT * FROM admin_surveys")
rows = cur.fetchall()
print("All rows in admin_surveys:")
for row in rows:
    print(row)
conn.close()

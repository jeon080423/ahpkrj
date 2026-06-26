import sqlite3
conn = sqlite3.connect('ahp_admin.db')
cur = conn.cursor()
cur.execute('SELECT survey_id, title FROM admin_surveys')
print(cur.fetchall())

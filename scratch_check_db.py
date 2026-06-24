import sqlite3
import json
conn = sqlite3.connect('users.db')
c = conn.cursor()
c.execute("SELECT metadata_json FROM survey_metadata_cache WHERE survey_id='1paouJoWGxkrmlfhE4S1iB7n9xvlzQb6lMLsl45DbVPY'")
res = c.fetchone()
if res:
    print(json.dumps(json.loads(res[0]), indent=2, ensure_ascii=False))
else:
    print("NOT FOUND")

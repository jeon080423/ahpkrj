import sqlite3
import json

conn = sqlite3.connect('users.db')
c = conn.cursor()
c.execute("SELECT survey_id, metadata_json FROM survey_metadata_cache")
rows = c.fetchall()
for row in rows:
    survey_id = row[0]
    if survey_id.startswith('1SN'):
        print(f"Found survey: {survey_id}")
        meta = json.loads(row[1])
        ahp = meta.get("AHP_Model_JSON", {})
        main_criteria = ahp.get("main", [])
        print("Main criteria:", main_criteria)

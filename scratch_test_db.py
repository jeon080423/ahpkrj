import sqlite3
conn = sqlite3.connect('users.db')
c = conn.cursor()
c.execute("SELECT survey_id FROM admin_surveys WHERE survey_id LIKE '1SN-tm%'")
rows = c.fetchall()
print(rows)
if rows:
    survey_id = rows[0][0]
    import json
    c.execute("SELECT metadata_json FROM survey_metadata_cache WHERE survey_id = ?", (survey_id,))
    meta_row = c.fetchone()
    if meta_row:
        meta = json.loads(meta_row[0])
        ahp_model = meta.get("AHP_Model_JSON", {})
        print("Model main:", ahp_model.get("main", []))
        print("Model subs:", list(ahp_model.get("subs", {}).keys()))
    else:
        print("No metadata in cache.")

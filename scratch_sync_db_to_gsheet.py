import sys
import sqlite3
import gspread

sys.path.append('f:/app/4. AHP마스터')
from survey_manager import get_survey_gspread_client, save_admin_survey_to_gsheet

try:
    conn = sqlite3.connect('f:/app/4. AHP마스터/users.db')
    cur = conn.cursor()
    cur.execute('SELECT survey_id, title, admin_id FROM admin_surveys')
    rows = cur.fetchall()
    
    print(f"Found {len(rows)} surveys in local DB.")
    
    for row in rows:
        survey_id, title, admin_id = row
        print(f"Syncing {survey_id}...")
        save_admin_survey_to_gsheet(survey_id, title, admin_id)
        
    print("Sync complete.")
except Exception as e:
    print("Error:", e)
finally:
    if 'conn' in locals():
        conn.close()

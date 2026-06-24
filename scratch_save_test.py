import sqlite3
import json
from survey_manager_v3 import save_response_to_sheet_v3

# Create dummy inputs
survey_id = 'test_survey_123'
resp_data = {
    'name': 'Test User',
    'affiliation': 'Test Corp',
    'email': 'test@test.com',
    'pre_ranking': 'FactorA-FactorB'
}
ahp_answers = {
    'FactorA_FactorB': 5,
    'FactorA_FactorC': 3,
    'FactorB_FactorC': -2
}
demographics = {
    'name': True,
    'affiliation': True,
    'email': True
}
ahp_model = {
    'main': ['FactorA', 'FactorB', 'FactorC'],
    'subs': {}
}
rewards_info = {'enabled': False}

# Attempt save
try:
    # First, let's inject a fake test_survey_123 into surveys table so it has a sheet URL
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS surveys
                 (id TEXT PRIMARY KEY, user_id TEXT, title TEXT, spreadsheet_url TEXT, sheet_id TEXT, tier_level INTEGER, ahp_model TEXT, demographics TEXT, status TEXT)''')
    c.execute('''INSERT OR IGNORE INTO surveys (id, user_id, title, spreadsheet_url, sheet_id, tier_level, ahp_model, demographics, status)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
              (survey_id, 'testuser', 'Test Survey', 'https://docs.google.com/spreadsheets/d/1Xy_...', '1Xy_...', 3, json.dumps(ahp_model), json.dumps(demographics), 'active'))
    conn.commit()
    conn.close()

    result = save_response_to_sheet_v3(survey_id, resp_data, ahp_answers, demographics, ahp_model, rewards_info)
    print('Save result:', result)
    
    # Check DB backup
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('SELECT * FROM survey_backup_responses ORDER BY id DESC LIMIT 1')
    row = c.fetchone()
    print('DB Backup Row id:', row[0])
    print('DB Backup Row payload:', row[3])
    conn.close()
except Exception as e:
    import traceback
    traceback.print_exc()

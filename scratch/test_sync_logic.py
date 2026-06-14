import toml
import gspread
from google.oauth2.service_account import Credentials
import json
import sqlite3

def get_gspread_client(secrets):
    scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    raw_auth = secrets["gcp_service_account"]
    auth_info = dict(raw_auth)
    auth_info["private_key"] = auth_info["private_key"].replace("\\n", "\n")
    creds = Credentials.from_service_account_info(auth_info, scopes=scope)
    return gspread.authorize(creds)

def main():
    secrets = toml.load(".streamlit/secrets.toml")
    spreadsheet_id = secrets["SPREADSHEET_ID"]
    
    print("Getting gspread client...")
    client = get_gspread_client(secrets)
    print("Client initialized.")
    
    print("Opening spreadsheet by key:", spreadsheet_id)
    spreadsheet = client.open_by_key(spreadsheet_id)
    
    print("Opening worksheet Short_Urls...")
    sheet = spreadsheet.worksheet("Short_Urls")
    
    print("Fetching records...")
    records = sheet.get_all_records()
    print(f"Found {len(records)} records.")
    
    conn = sqlite3.connect('users.db')
    cur = conn.cursor()
    for r in records:
        print("Record:", r)
        short_code = str(r.get("short_code", "")).strip()
        survey_id = str(r.get("survey_id", "")).strip()
        title = str(r.get("title", "")).strip()
        admin_id = str(r.get("admin_id", "")).strip()
        created_at = str(r.get("created_at", "")).strip()
        if short_code and survey_id:
            cur.execute("INSERT OR IGNORE INTO admin_surveys (survey_id, title, admin_id, created_at, short_code) VALUES (?, ?, ?, ?, ?)",
                        (survey_id, title, admin_id, created_at, short_code))
            cur.execute("UPDATE admin_surveys SET short_code = ? WHERE survey_id = ? AND (short_code IS NULL OR short_code = '')", (short_code, survey_id))
    conn.commit()
    
    cur.execute("SELECT * FROM admin_surveys")
    print("Database contents:")
    for row in cur.fetchall():
        print(row)
        
    conn.close()

if __name__ == "__main__":
    main()

import toml
import os
from google.oauth2.service_account import Credentials
import gspread

def main():
    secrets_path = ".streamlit/secrets.toml"
    if not os.path.exists(secrets_path):
        print("secrets.toml not found")
        return
        
    secrets = toml.load(secrets_path)
    auth_info = secrets["gcp_service_account"]
    if "private_key" in auth_info:
        auth_info["private_key"] = auth_info["private_key"].replace("\\n", "\n")
        
    scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    creds = Credentials.from_service_account_info(auth_info, scopes=scope)
    client = gspread.authorize(creds)
    
    try:
        spreadsheet = client.open_by_key(secrets["SPREADSHEET_ID"])
        sheet = spreadsheet.sheet1
        records = sheet.get_all_records()
        
        # print recent 10 records
        print(f"Total records: {len(records)}")
        print("Recent 10 records:")
        for r in records[-10:]:
            print(r)
            
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    main()

import toml
import gspread
from google.oauth2.service_account import Credentials
import json

def main():
    secrets = toml.load(".streamlit/secrets.toml")
    spreadsheet_id = secrets["SPREADSHEET_ID"]
    auth_info = dict(secrets["gcp_service_account"])
    auth_info["private_key"] = auth_info["private_key"].replace("\\n", "\n")
    
    scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    creds = Credentials.from_service_account_info(auth_info, scopes=scope)
    client = gspread.authorize(creds)
    
    try:
        spreadsheet = client.open_by_key(spreadsheet_id)
        sheet = spreadsheet.worksheet("Short_Urls")
        records = sheet.get_all_records()
        print("Records in Short_Urls worksheet:")
        for r in records:
            print(r)
    except Exception as e:
        print("Error accessing Short_Urls worksheet:", e)

if __name__ == "__main__":
    main()

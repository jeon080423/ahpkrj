import toml
import os
from google.oauth2.service_account import Credentials
import gspread

def main():
    secrets_path = ".streamlit/secrets.toml"
    if not os.path.exists(secrets_path):
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
        for i, ws in enumerate(spreadsheet.worksheets()):
            print(f"Worksheet {i}: {ws.title}")
            try:
                # print first few rows
                vals = ws.get_all_values()
                print(f"Rows: {len(vals)}")
                if len(vals) > 0:
                    print("Headers:", vals[0])
                if len(vals) > 1:
                    print("Last row:", vals[-1])
            except Exception as ex:
                print("Error reading worksheet:", ex)
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    main()

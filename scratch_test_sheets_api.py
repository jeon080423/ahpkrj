import toml
import os
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

def main():
    secrets_path = ".streamlit/secrets.toml"
    if not os.path.exists(secrets_path):
        print("secrets.toml not found")
        return
        
    secrets = toml.load(secrets_path)
    auth_info = secrets["gcp_service_account"]
    if "private_key" in auth_info:
        auth_info["private_key"] = auth_info["private_key"].replace("\\n", "\n")
        
    scope = ['https://www.googleapis.com/auth/spreadsheets']
    creds = Credentials.from_service_account_info(auth_info, scopes=scope)
    
    try:
        print("Attempting to create spreadsheet via Sheets API v4...")
        sheets_service = build('sheets', 'v4', credentials=creds)
        spreadsheet_body = {
            'properties': {
                'title': "[AHP 테스트] Sheets API v4 Creation"
            }
        }
        request = sheets_service.spreadsheets().create(body=spreadsheet_body)
        response = request.execute()
        spreadsheet_id = response.get('spreadsheetId')
        print("Success! Created sheet ID:", spreadsheet_id)
        
        # Clean up using drive API (requires drive scope, let's just see if creation works first)
    except Exception as e:
        print("Error during Sheets API creation:", e)

if __name__ == "__main__":
    main()

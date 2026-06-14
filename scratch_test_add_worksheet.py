import toml
import os
import gspread
from google.oauth2.service_account import Credentials

def main():
    secrets_path = ".streamlit/secrets.toml"
    if not os.path.exists(secrets_path):
        print("secrets.toml not found")
        return
        
    secrets = toml.load(secrets_path)
    auth_info = secrets["gcp_service_account"]
    if "private_key" in auth_info:
        auth_info["private_key"] = auth_info["private_key"].replace("\\n", "\n")
        
    spreadsheet_id = secrets["SPREADSHEET_ID"]
    print("Master Spreadsheet ID:", spreadsheet_id)
    
    scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    creds = Credentials.from_service_account_info(auth_info, scopes=scope)
    client = gspread.authorize(creds)
    
    try:
        print("Opening master spreadsheet...")
        spreadsheet = client.open_by_key(spreadsheet_id)
        print("Adding a test worksheet...")
        worksheet = spreadsheet.add_worksheet(title="TEST_WORKSHEET_CREATION", rows="100", cols="10")
        print("Success! Created worksheet:", worksheet.title)
        
        # Clean up
        print("Deleting test worksheet...")
        spreadsheet.del_worksheet(worksheet)
        print("Cleaned up successfully.")
    except Exception as e:
        print("Error during worksheet creation:", e)

if __name__ == "__main__":
    main()

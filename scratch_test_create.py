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
        
    scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    creds = Credentials.from_service_account_info(auth_info, scopes=scope)
    client = gspread.authorize(creds)
    
    try:
        print("Attempting to create spreadsheet...")
        sheet = client.create("[AHP 테스트] Test Creation")
        print("Success! Created sheet ID:", sheet.id)
        # Clean up
        from googleapiclient.discovery import build
        drive_service = build('drive', 'v3', credentials=creds)
        drive_service.files().delete(fileId=sheet.id).execute()
        print("Cleaned up successfully.")
    except Exception as e:
        print("Error during creation:", e)

if __name__ == "__main__":
    main()

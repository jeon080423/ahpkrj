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
    print("Service Account Email:", auth_info.get("client_email"))
    
    scope = ['https://www.googleapis.com/auth/drive']
    creds = Credentials.from_service_account_info(auth_info, scopes=scope)
    drive_service = build('drive', 'v3', credentials=creds)
    
    about = drive_service.about().get(fields="storageQuota, user").execute()
    print("User info:", about.get("user"))
    print("Storage Quota detail:", about.get("storageQuota"))

if __name__ == "__main__":
    main()

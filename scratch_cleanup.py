import os
import json
import toml
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

def clean_drive():
    secrets_path = ".streamlit/secrets.toml"
    if not os.path.exists(secrets_path):
        print("secrets.toml not found")
        return
        
    secrets = toml.load(secrets_path)
    if "gcp_service_account" not in secrets:
        print("gcp_service_account not in secrets")
        return
        
    auth_info = dict(secrets["gcp_service_account"])
    if "private_key" in auth_info:
        auth_info["private_key"] = auth_info["private_key"].replace("\\n", "\n")
        
    scope = ['https://www.googleapis.com/auth/drive']
    creds = Credentials.from_service_account_info(auth_info, scopes=scope)
    drive_service = build('drive', 'v3', credentials=creds)
    
    # Check quota
    about = drive_service.about().get(fields="storageQuota").execute()
    print("Storage Quota:", about.get("storageQuota"))
    
    # List files
    files_list = []
    page_token = None
    while True:
        response = drive_service.files().list(
            q="trashed = false",
            spaces='drive',
            fields='nextPageToken, files(id, name, size, mimeType, createdTime, owners)',
            pageToken=page_token
        ).execute()
        files_list.extend(response.get('files', []))
        page_token = response.get('nextPageToken', None)
        if not page_token:
            break
            
    print(f"Total non-trashed files found: {len(files_list)}")
    
    # Empty trash first
    print("Emptying trash...")
    try:
        drive_service.files().emptyTrash().execute()
        print("Trash emptied successfully.")
    except Exception as e:
        print("Failed to empty trash:", e)
        
    # Print details of top 20 files
    print("\nTop 20 Files:")
    for f in files_list[:20]:
        owners = [o.get("displayName") or o.get("emailAddress") for o in f.get("owners", [])]
        print(f"- {f.get('name')} ({f.get('id')}) | Size: {f.get('size')} | Type: {f.get('mimeType')} | Created: {f.get('createdTime')} | Owners: {owners}")
        
    # Count of files owned by service account
    service_email = auth_info.get("client_email")
    owned_files = [f for f in files_list if any(o.get("emailAddress") == service_email for o in f.get("owners", []))]
    print(f"\nFiles owned by service account: {len(owned_files)}")
    
if __name__ == "__main__":
    clean_drive()

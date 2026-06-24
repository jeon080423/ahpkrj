import toml
import os
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials

spreadsheet_id = "1paouJoWGxkrmlfhE4S1iB7n9xvlzQb6lMLsl45DbVPY"

secrets_path = os.path.expanduser("~/.streamlit/secrets.toml")
if not os.path.exists(secrets_path):
    secrets_path = "g:/AHPkr/.streamlit/secrets.toml"

with open(secrets_path, "r", encoding="utf-8") as f:
    secrets = toml.load(f)

creds_dict = dict(secrets["gcp_service_account"])
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

try:
    spreadsheet = client.open_by_key(spreadsheet_id)
    worksheets = spreadsheet.worksheets()
    print("Sheet Titles:")
    for ws in worksheets:
        print(f"- {ws.title}")
except Exception as e:
    print(f"Error: {e}")

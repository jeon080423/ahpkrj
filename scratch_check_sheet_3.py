import toml
import os
import streamlit as st

secrets_path = r"C:\Users\shjeon.HRI9623C\.streamlit\secrets.toml"
with open(secrets_path, "r", encoding="utf-8") as f:
    secrets = toml.load(f)

# Mock st.secrets
st.secrets = secrets

from survey_manager import get_survey_gspread_client
client = get_survey_gspread_client()

spreadsheet_id = "1paouJoWGxkrmlfhE4S1iB7n9xvlzQb6lMLsl45DbVPY"
spreadsheet = client.open_by_key(spreadsheet_id)
worksheets = spreadsheet.worksheets()
print("Sheet Titles:")
for ws in worksheets:
    print(f"- {ws.title}")

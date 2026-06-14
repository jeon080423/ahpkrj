import sys
import os
sys.path.append(os.path.abspath("."))
import streamlit as st

# We need to mock st.secrets or set it up if it's not run under streamlit
# Since we are running as a standard script, st.secrets might be empty or load from .streamlit/secrets.toml
# Let's check if we can run it.
import toml
secrets = toml.load(".streamlit/secrets.toml")
for k, v in secrets.items():
    st.secrets[k] = v

from app import sync_short_codes_from_gs
import sqlite3

print("Running sync_short_codes_from_gs...")
try:
    sync_short_codes_from_gs()
    print("Sync finished.")
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT * FROM admin_surveys")
    print("Surveys after sync:", c.fetchall())
    conn.close()
except Exception as e:
    print("Exception during sync:", e)

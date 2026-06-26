import sqlite3
import streamlit as st
import gspread
import datetime
import os
import sys

# Adding the current directory to sys.path to import local modules if needed
sys.path.append(os.getcwd())
from app import get_gspread_client

def sync_visit_logs():
    print("Connecting to local DB...")
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS visit_logs (ip_address TEXT, visit_date TEXT, UNIQUE(ip_address, visit_date))")
    
    print("Connecting to Google Sheets...")
    client = get_gspread_client()
    if not client:
        print("Failed to get gspread client.")
        return
        
    spreadsheet = client.open_by_key(st.secrets["SPREADSHEET_ID"])
    try:
        visit_sheet = spreadsheet.worksheet("Visit_Logs")
        records = visit_sheet.get_all_records()
        print(f"Found {len(records)} records in Google Sheets.")
        
        inserted = 0
        for row in records:
            try:
                c.execute("INSERT OR IGNORE INTO visit_logs (ip_address, visit_date) VALUES (?, ?)", 
                          (str(row.get('IP', '')), str(row.get('Date', ''))))
                if c.rowcount > 0:
                    inserted += 1
            except Exception as e:
                pass
        conn.commit()
        print(f"Successfully inserted {inserted} new records into local DB.")
        
        c.execute("SELECT COUNT(*) FROM visit_logs")
        total = c.fetchone()[0]
        print(f"Total records in local DB now: {total}")
        
    except Exception as e:
        print(f"Error accessing Google Sheets: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    sync_visit_logs()

import sys
import os
import random
import datetime
import time

sys.path.append('f:\\app\\4. AHP마스터')
from survey_manager import get_survey_gspread_client

def insert_bad_row():
    client = get_survey_gspread_client()
    sheet_id = '1paouJoWGxkrmlfhE4S1iB7n9xvlzQb6lMLsl45DbVPY'
    spreadsheet = client.open_by_key(sheet_id)
    worksheets = spreadsheet.worksheets()
    
    for ws in worksheets:
        title = ws.title
        if title in ["Survey_Metadata", "Short_Urls"]:
            continue
            
        headers = ws.row_values(1)
        if not headers:
            continue
            
        row = []
        for h in headers:
            if h == "ID": row.append("bad_user_1")
            elif h == "제출시간": row.append(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            elif "_" in h:
                # Add bad data to trigger Format Error
                row.append(random.choice(["1/5", "10", "-15", "A", ""]))
            else: row.append("Test")
                
        ws.append_row(row)
        print(f"Appended bad row to {title}")
        time.sleep(1)

if __name__ == "__main__":
    insert_bad_row()

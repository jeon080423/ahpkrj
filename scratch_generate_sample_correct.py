import sys
import os
import random
import datetime
import time

sys.path.append('f:\\app\\4. AHP마스터')
from survey_manager import get_survey_gspread_client

def fix_sample_data():
    client = get_survey_gspread_client()
    sheet_id = '1paouJoWGxkrmlfhE4S1iB7n9xvlzQb6lMLsl45DbVPY'
    try:
        spreadsheet = client.open_by_key(sheet_id)
    except Exception as e:
        print(f"Error opening spreadsheet: {e}")
        return

    worksheets = spreadsheet.worksheets()
    
    # We will generate 2 rows of CORRECT data
    for idx in range(1, 3):
        user_id = f"test_user_v2_{idx}"
        timestamp = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).strftime("%Y-%m-%d %H:%M:%S")
        
        for ws in worksheets:
            title = ws.title
            if title in ["Survey_Metadata", "Short_Urls"]:
                continue
                
            headers = ws.row_values(1)
            if not headers:
                continue
            
            # Find rows from previous run and delete them? 
            # Or just append the new rows. Let's just append new rows.
            
            row = []
            for h in headers:
                if h == "ID":
                    row.append(user_id)
                elif h == "제출시간":
                    row.append(timestamp)
                elif h in ["Type", "Type 1", "그룹 분류"]:
                    row.append("전문가" if idx == 1 else "일반")
                elif h in ["Type 2", "추가 문항 1"]:
                    row.append("A" if idx == 1 else "B")
                elif h in ["성명"]:
                    row.append(f"테스터{idx}")
                elif h in ["연령"]:
                    row.append("30대")
                elif h in ["성별"]:
                    row.append("남성" if idx == 1 else "여성")
                elif h in ["경력년수"]:
                    row.append("5년")
                elif h in ["소속"]:
                    row.append("소속 A")
                elif h in ["이메일"]:
                    row.append(f"test{idx}@example.com")
                elif "_" in h: # AHP pair
                    # Correct AHP format used by app.py: -5, -3, 1, 3, 5
                    # Negative means left is important, positive means right is important.
                    vals = ["-5", "-3", "1", "3", "5"]
                    row.append(random.choice(vals))
                else:
                    row.append("")
                    
            ws.append_row(row)
            print(f"Appended correct row {idx} to {title}")
            time.sleep(1) # prevent rate limit

if __name__ == "__main__":
    fix_sample_data()

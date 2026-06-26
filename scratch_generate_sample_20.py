import sys
import os
import random
import datetime
import time

sys.path.append('f:\\app\\4. AHP마스터')
from survey_manager import get_survey_gspread_client

def generate_20_samples():
    client = get_survey_gspread_client()
    sheet_id = '1paouJoWGxkrmlfhE4S1iB7n9xvlzQb6lMLsl45DbVPY'
    try:
        spreadsheet = client.open_by_key(sheet_id)
    except Exception as e:
        print(f"Error opening spreadsheet: {e}")
        return

    worksheets = spreadsheet.worksheets()
    
    # We will generate 20 rows of CORRECT data
    for ws in worksheets:
        title = ws.title
        if title in ["Survey_Metadata", "Short_Urls"]:
            continue
            
        headers = ws.row_values(1)
        if not headers:
            continue
            
        new_rows = []
        for idx in range(1, 21):
            user_id = f"test_20_user_{idx}"
            timestamp = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).strftime("%Y-%m-%d %H:%M:%S")
            
            row = []
            for h in headers:
                if h == "ID":
                    row.append(user_id)
                elif h == "제출시간":
                    row.append(timestamp)
                elif h in ["Type", "Type 1", "그룹 분류"]:
                    row.append(random.choice(["전문가", "일반", "공무원", "기타"]))
                elif h in ["Type 2", "추가 문항 1"]:
                    row.append(random.choice(["A", "B", "C", "D"]))
                elif h in ["성명"]:
                    row.append(f"대량테스터{idx}")
                elif h in ["연령"]:
                    row.append(random.choice(["20대 미만", "20대 (20~29세)", "30대 (30~39세)", "40대 (40~49세)", "50대 (50~59세)", "60대 이상"]))
                elif h in ["성별"]:
                    row.append(random.choice(["남성", "여성"]))
                elif h in ["경력년수"]:
                    row.append(f"{random.randint(1, 20)}년")
                elif h in ["소속"]:
                    row.append(f"소속 {random.choice(['A', 'B', 'C'])}")
                elif h in ["이메일"]:
                    row.append(f"mass_test{idx}@example.com")
                elif "_" in h: # AHP pair
                    # Correct AHP format used by app.py: -5, -3, 1, 3, 5
                    # Negative means left is important, positive means right is important.
                    # We will use the 9-point scale to have more variance: -9, -7, -5, -3, 1, 3, 5, 7, 9
                    vals = ["-9", "-7", "-5", "-3", "1", "3", "5", "7", "9"]
                    row.append(random.choice(vals))
                else:
                    row.append("")
            new_rows.append(row)
            
        try:
            ws.append_rows(new_rows)
            print(f"Successfully appended 20 rows to {title}")
        except Exception as e:
            print(f"Failed to append to {title}: {e}")
            
        time.sleep(2) # prevent rate limit between sheets

if __name__ == "__main__":
    generate_20_samples()

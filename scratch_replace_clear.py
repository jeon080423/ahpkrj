import sys

with open('f:/app/4. AHP마스터/survey_manager.py', 'r', encoding='utf-8') as f:
    content = f.read()

target = """        # Raw_Data 워크시트 설정
        try:
            raw_sheet = spreadsheet.worksheet("Raw_Data")
            raw_sheet.clear()
        except gspread.WorksheetNotFound:
            raw_sheet = spreadsheet.add_worksheet(title="Raw_Data", rows="1000", cols="50")

        # Demographic_Data 워크시트 설정
        try:
            demo_sheet = spreadsheet.worksheet("Demographic_Data")
            demo_sheet.clear()
        except gspread.WorksheetNotFound:
            demo_sheet = spreadsheet.add_worksheet(title="Demographic_Data", rows="1000", cols="20")"""

replacement = """        # Raw_Data 워크시트 설정
        try:
            raw_sheet = spreadsheet.worksheet("Raw_Data")
            # 수정 시 기존 데이터 보존
        except gspread.WorksheetNotFound:
            raw_sheet = spreadsheet.add_worksheet(title="Raw_Data", rows="1000", cols="50")

        # Demographic_Data 워크시트 설정
        try:
            demo_sheet = spreadsheet.worksheet("Demographic_Data")
            # 수정 시 기존 데이터 보존
        except gspread.WorksheetNotFound:
            demo_sheet = spreadsheet.add_worksheet(title="Demographic_Data", rows="1000", cols="20")"""

if target in content:
    content = content.replace(target, replacement)
    with open('f:/app/4. AHP마스터/survey_manager.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Replaced clear logic successfully")
else:
    print("Target clear logic not found")

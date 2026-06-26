import sys

with open('f:/app/4. AHP마스터/survey_manager.py', 'r', encoding='utf-8') as f:
    content = f.read()

new_function = """def delete_admin_survey(survey_id, admin_id):
    import sqlite3
    import gspread
    client = get_survey_gspread_client()
    if not client: return False
    
    # 1. Clear data in the user's survey sheet
    try:
        spreadsheet = client.open_by_key(survey_id)
        for sheet_name in ["Raw_Data", "Demographic_Data", "Survey_Metadata", "AHP_Model", "Pairwise_Data"]:
            try:
                ws = spreadsheet.worksheet(sheet_name)
                ws.clear()
            except gspread.exceptions.WorksheetNotFound:
                pass
    except Exception as e:
        print(f"Failed to clear survey sheet {survey_id}:", e)
        
    # 2. Remove from Admin_Surveys Master Sheet
    try:
        master_sheet = client.open_by_key('1xLvrH6LN8Vw3dVzoguf6TkgRrsJvEpMl2Z8s8HAvrVA')
        ws = master_sheet.worksheet('Admin_Surveys')
        all_records = ws.get_all_records()
        
        # Find the row to delete. Note: get_all_records() returns a list of dicts.
        # Gspread row index for deletion is 1-based, and row 1 is header. So data starts at row 2.
        for i, r in enumerate(all_records):
            if str(r.get('survey_id')) == str(survey_id) and str(r.get('admin_id')) == str(admin_id):
                row_index_to_delete = i + 2  # +2 because header is row 1, and enumerate is 0-based
                ws.delete_rows(row_index_to_delete)
                break
    except Exception as e:
        print("Failed to remove from Master GSheet:", e)

    # 3. Remove from Local DB
    try:
        conn = sqlite3.connect('users.db')
        cur = conn.cursor()
        cur.execute("DELETE FROM admin_surveys WHERE survey_id = ? AND admin_id = ?", (survey_id, admin_id))
        conn.commit()
        conn.close()
    except Exception as e:
        print("Failed to remove from local SQLite:", e)
        
    return True

"""

# Insert it before get_admin_surveys_from_gsheet
target = "def get_admin_surveys_from_gsheet(admin_id):"

if target in content:
    content = content.replace(target, new_function + target)
    with open('f:/app/4. AHP마스터/survey_manager.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Added delete_admin_survey to survey_manager.py successfully.")
else:
    print("Target get_admin_surveys_from_gsheet not found")

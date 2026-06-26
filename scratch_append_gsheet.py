code = '''
def save_admin_survey_to_gsheet(survey_id, title, admin_id):
    import datetime
    import gspread
    client = get_survey_gspread_client()
    if not client: return False
    try:
        master_sheet = client.open_by_key('1xLvrH6LN8Vw3dVzoguf6TkgRrsJvEpMl2Z8s8HAvrVA')
        try:
            ws = master_sheet.worksheet('Admin_Surveys')
        except gspread.exceptions.WorksheetNotFound:
            ws = master_sheet.add_worksheet(title='Admin_Surveys', rows=1000, cols=5)
            ws.append_row(['survey_id', 'title', 'admin_id', 'created_at'])
            
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ws.append_row([survey_id, title, admin_id, now_str])
        return True
    except Exception as e:
        print("save_admin_survey_to_gsheet error:", e)
        return False

def get_admin_surveys_from_gsheet(admin_id):
    import gspread
    client = get_survey_gspread_client()
    if not client: return []
    try:
        master_sheet = client.open_by_key('1xLvrH6LN8Vw3dVzoguf6TkgRrsJvEpMl2Z8s8HAvrVA')
        try:
            ws = master_sheet.worksheet('Admin_Surveys')
        except gspread.exceptions.WorksheetNotFound:
            return []
            
        all_records = ws.get_all_records()
        surveys = []
        for r in all_records:
            if str(r.get('admin_id')) == str(admin_id):
                surveys.append((str(r.get('survey_id')), str(r.get('title')), str(r.get('created_at'))))
        surveys.sort(key=lambda x: x[2], reverse=True)
        return surveys
    except Exception as e:
        print("get_admin_surveys_from_gsheet error:", e)
        return []
'''
with open('f:/app/4. AHP마스터/survey_manager.py', 'a', encoding='utf-8') as f:
    f.write(code)

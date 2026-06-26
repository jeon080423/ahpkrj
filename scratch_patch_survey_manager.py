import sys

with open('f:/app/4. AHP마스터/survey_manager.py', 'r', encoding='utf-8') as f:
    content = f.read()

target1 = """    # 3. Remove from Local DB
    try:
        conn = sqlite3.connect('users.db')
        cur = conn.cursor()
        cur.execute("DELETE FROM admin_surveys WHERE survey_id = ? AND admin_id = ?", (survey_id, admin_id))"""

replacement1 = """    # 3. Remove from Local DB
    try:
        conn = sqlite3.connect('users.db')
        cur = conn.cursor()
        # Delete ALL surveys for this admin since it's a 1-survey system
        cur.execute("DELETE FROM admin_surveys WHERE admin_id = ?", (admin_id,))"""

target2 = """        for i, r in enumerate(all_records):
            if str(r.get('survey_id')) == str(survey_id) and str(r.get('admin_id')) == str(admin_id):
                row_index_to_delete = i + 2  # +2 because header is row 1, and enumerate is 0-based
                ws.delete_rows(row_index_to_delete)
                break"""

replacement2 = """        # Find all rows for this admin and delete them from bottom to top to avoid index shifting
        rows_to_delete = []
        for i, r in enumerate(all_records):
            if str(r.get('admin_id')) == str(admin_id):
                rows_to_delete.append(i + 2)
        
        for r_idx in sorted(rows_to_delete, reverse=True):
            ws.delete_rows(r_idx)"""

target3 = """def get_admin_surveys_from_gsheet(admin_id):
    import gspread
    client = get_survey_gspread_client()
    if not client: return []
    try:
        master_sheet = client.open_by_key('1xLvrH6LN8Vw3dVzoguf6TkgRrsJvEpMl2Z8s8HAvrVA')
        ws = master_sheet.worksheet('Admin_Surveys')
        all_records = ws.get_all_records()"""

replacement3 = """def get_admin_surveys_from_gsheet(admin_id):
    import gspread
    client = get_survey_gspread_client()
    if not client: return []
    try:
        master_sheet = client.open_by_key('1xLvrH6LN8Vw3dVzoguf6TkgRrsJvEpMl2Z8s8HAvrVA')
        ws = master_sheet.worksheet('Admin_Surveys')
        try:
            all_records = ws.get_all_records()
        except Exception:
            all_records = []"""

if target1 in content and target2 in content and target3 in content:
    content = content.replace(target1, replacement1)
    content = content.replace(target2, replacement2)
    content = content.replace(target3, replacement3)
    with open('f:/app/4. AHP마스터/survey_manager.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Patched survey_manager.py successfully.")
else:
    print("Could not find targets in survey_manager.py")

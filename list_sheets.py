import sys
sys.path.append(r'k:\app\4. AHP마스터')
from survey_manager import get_survey_gspread_client
client = get_survey_gspread_client()
if client:
    print('Client obtained. Listing files...')
    try:
        # get all spreadsheets the service account can see
        for sh in client.openall():
            print(f"Title: {sh.title}, ID: {sh.id}")
    except Exception as e:
        print(f'Error listing files: {e}')

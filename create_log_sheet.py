import sys
sys.path.append(r'k:\app\4. AHP마스터')
from survey_manager import get_survey_gspread_client

def create_and_share_log_sheet():
    client = get_survey_gspread_client()
    if not client:
        print("Failed to get gspread client.")
        return

    # Create new spreadsheet
    try:
        sh = client.create('AHP_Activity_Logs')
        print(f"Created new spreadsheet '{sh.title}' with ID: {sh.id}")
        
        # Share with user
        sh.share('jeon080423@gmail.com', perm_type='user', role='writer')
        print("Shared with jeon080423@gmail.com")
        
        # Initialize worksheets
        ws_user = sh.sheet1
        ws_user.update_title('User_Activity_Logs')
        ws_user.append_row(["Timestamp", "User ID", "Region", "Action Sequence"])
        
        ws_guest = sh.add_worksheet(title='Guest_Activity_Logs', rows=1000, cols=10)
        ws_guest.append_row(["Timestamp", "User ID", "Region", "Action Sequence"])
        
        print("Initialized User_Activity_Logs and Guest_Activity_Logs")
        print(f"URL: {sh.url}")
        
        # Save ID to a temporary file so the agent can read it
        with open('new_sheet_id.txt', 'w', encoding='utf-8') as f:
            f.write(sh.id)
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    create_and_share_log_sheet()

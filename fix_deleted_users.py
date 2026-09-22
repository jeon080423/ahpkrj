import sys
import os
sys.path.append(r'k:\app\4. AHP마스터')
from survey_manager import get_survey_gspread_client

def fix_deleted_users():
    client = get_survey_gspread_client()
    if not client:
        print("Failed to get client")
        return
        
    sh = client.open_by_key('1xLvrH6LN8Vw3dVzoguf6TkgRrsJvEpMl2Z8s8HAvrVA')
    ws = sh.worksheet('Deleted_Users')
    
    all_rows = ws.get_all_values()
    
    new_rows = []
    # Force header
    new_rows.append(['ID', 'Role', 'SignupDate', 'PW', 'agree_info', 'DeletedDate'])
    
    for row in all_rows[1:]:
        non_empty = [x for x in row if x.strip()]
        if not non_empty:
            continue
            
        # The first non-empty should be ID
        # Wait, the structure of non_empty depends on what was in Registered_Users.
        # Let's map it: 
        # non_empty[0] is usually ID.
        # non_empty[1] is Role.
        # non_empty[2] is SignupDate.
        # non_empty[3] is PW.
        # non_empty[4] is expire_date.
        # non_empty[5] is agree_info.
        # non_empty[-1] is DeletedDate (timestamp).
        
        if len(non_empty) >= 6:
            c_id = non_empty[0]
            c_role = non_empty[1]
            c_signup = non_empty[2]
            c_pw = non_empty[3]
            # some rows might not have expire_date or agree_info in the exact same spot if empty strings were stripped from the middle
            # But earlier we saw:
            # ['jjjjj@mo.com', 'official', '2026-06-27', '253c4fcc41fd1d562049f92e2134fa438ad30aea039d6d0d90f1baef63841826', '2026-08-27', 'Y', '0', '2026-07-01 10:15:50']
            # So index 4 is expire_date, 5 is agree_info, 6 is login_fail_count, 7 is DeletedDate
            # Wait, if they are exactly as non_empty:
            # Let's just grab the first 4, then look for 'Y' or 'N' for agree_info.
            
            c_agree = 'Y' if 'Y' in non_empty else ('N' if 'N' in non_empty else '')
            c_del_date = non_empty[-1]
            
            new_rows.append([c_id, c_role, c_signup, c_pw, c_agree, c_del_date])
    
    # Now we clear the worksheet and write the new_rows
    ws.clear()
    ws.update('A1', new_rows)
    print(f"Fixed {len(new_rows)} rows in Deleted_Users")

if __name__ == '__main__':
    fix_deleted_users()

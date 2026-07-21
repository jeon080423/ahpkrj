# -*- coding: utf-8 -*-
import sqlite3
import re
from datetime import datetime

def update_landing_page():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    # Get top 5 formal users
    c.execute('''
        SELECT id, plan_type, signup_date, expiry_date 
        FROM users 
        WHERE plan_type IN ('Premium', 'Standard', 'Basic') OR plan_type LIKE '%개월%'
        ORDER BY signup_date DESC LIMIT 5
    ''')
    rows = c.fetchall()
    conn.close()
    
    real_users_js = []
    for r in rows:
        uid, plan, signup_date_str, expiry_date_str = r
        if not uid or len(uid) < 3: continue
        
        uid_prefix = uid.split('@')[0]
        if len(uid_prefix) >= 5:
            surname = uid_prefix[:5] + "***"
        else:
            surname = uid_prefix + "***"
            
        plan_str = plan if plan in ["Premium", "Standard", "Basic"] else "Standard"
        
        period = 2
        try:
            signup_date = datetime.strptime(signup_date_str, "%Y-%m-%d")
            expiry_date = datetime.strptime(expiry_date_str, "%Y-%m-%d")
            months = (expiry_date.year - signup_date.year) * 12 + expiry_date.month - signup_date.month
            if 0 < months < 120:
                period = months
        except:
            pass
            
        js_obj = f"{{ surname: '{surname}', plan: '{plan_str}', period: {period}, regDate: new Date('{signup_date_str}') }}"
        real_users_js.append(js_obj)
        
    with open('docs/index.html', 'r', encoding='utf-8') as f:
        content = f.read()
        
    injection_code = "\n          // --- REAL USERS FROM DB ---\n"
    for js_obj in real_users_js:
        injection_code += f"          mockData.push({js_obj});\n"
    injection_code += "          // ---------------------------\n"
    
    if "// --- REAL USERS FROM DB ---" in content:
        content = re.sub(r'// --- REAL USERS FROM DB ---.*?// ---------------------------', injection_code.strip(), content, flags=re.DOTALL)
    else:
        content = content.replace("const mockData = [];", "const mockData = [];\n" + injection_code)
        
    with open('docs/index.html', 'w', encoding='utf-8') as f:
        f.write(content)
        
    print(f"Successfully injected {len(real_users_js)} real users into docs/index.html")

if __name__ == '__main__':
    update_landing_page()

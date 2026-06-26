import re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Fix admin mode button text
old_btn = '''        if st.session_state.user_role == 'admin':
            if st.button(_("🔧 관리자 화면 접속", "🔧 Connect to Admin Panel")):'''
new_btn = '''        if st.session_state.user_role == 'admin':
            btn_label = _("🔧 관리자 화면 닫기", "🔧 Exit Admin Panel") if st.session_state.get('admin_mode', False) else _("🔧 관리자 화면 접속", "🔧 Connect to Admin Panel")
            if st.button(btn_label):'''
content = content.replace(old_btn, new_btn)

# 2. Fix admin mode visitor count to use the global total_visits
old_admin_visits = '''                daily_df_counts = daily_df_logs.groupby('Date_Only').size().reset_index(name='count')
                total_visits = len(daily_df_logs)'''
new_admin_visits = '''                daily_df_counts = daily_df_logs.groupby('Date_Only').size().reset_index(name='count')
                # total_visits remains as calculated from local db above'''
content = content.replace(old_admin_visits, new_admin_visits)

old_visit_write = '''            st.write(f"**총 누적 방문자 수 (시간 기반):** {total_visits:,}회")'''
new_visit_write = '''            st.write(f"**총 누적 방문자 수:** {total_visits:,}명")'''
content = content.replace(old_visit_write, new_visit_write)

# 3. Indent col_settings block if not in admin mode
col_settings_idx = content.find('with col_settings:')
col_main_idx = content.find('with col_main:', col_settings_idx)

if col_settings_idx != -1 and col_main_idx != -1:
    col_settings_block = content[col_settings_idx:col_main_idx]
    
    lines = col_settings_block.split('\n')
    new_lines = []
    for i, line in enumerate(lines):
        if i == 0:
            new_lines.append(line)
            new_lines.append("    if st.session_state.get('admin_mode', False) and st.session_state.get('user_role') == 'admin':")
            new_lines.append("        pass")
            new_lines.append("    else:")
        elif i == 1 and 'with st.container(border=True):' in line:
            new_lines.append("    " + line)
        elif i > 1:
            if line.strip() == '':
                new_lines.append(line)
            else:
                new_lines.append("    " + line)
                
    new_col_settings_block = '\n'.join(new_lines)
    content = content[:col_settings_idx] + new_col_settings_block + content[col_main_idx:]

# 4. Hide main tabs if in admin mode
old_tabs = '''    main_tab1, main_tab2, main_tab3 = st.tabs(['''
new_tabs = '''    if st.session_state.get('admin_mode', False) and st.session_state.get('user_role') == 'admin':
        st.stop()
        
    main_tab1, main_tab2, main_tab3 = st.tabs(['''
content = content.replace(old_tabs, new_tabs)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Modifications applied successfully.")

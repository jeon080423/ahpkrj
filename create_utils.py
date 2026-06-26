import re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

pattern = re.compile(r'        def write_custom_ahp_table\(.*?        def add_borders_to_data\(.*?    with main_tab2:', re.DOTALL)
match = pattern.search(content)

if match:
    text = match.group(0)
    func_text = text[:-19] # remove \n    with main_tab2:
    lines = func_text.splitlines()
    dedented = []
    for line in lines:
        if line.startswith('        '): dedented.append(line[8:])
        else: dedented.append(line)
        
    with open('ahp_table_utils.py', 'w', encoding='utf-8') as f:
        f.write('import streamlit as st\n')
        f.write('def _(ko_text, en_text):\n')
        f.write('    if st.session_state.get("lang", "ko") == "en": return en_text\n')
        f.write('    return ko_text\n\n')
        f.write('\n'.join(dedented))
        
    # remove from app.py
    new_content = content.replace(text, '    with main_tab2:')
    
    # inject import at the top of app.py
    import_statement = 'from ahp_table_utils import write_custom_ahp_table, add_borders_to_data\n'
    if import_statement not in new_content:
        new_content = new_content.replace('import sys\n', f'import sys\n{import_statement}')
        
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(new_content)
        
    print('Success')
else:
    print('Not found')

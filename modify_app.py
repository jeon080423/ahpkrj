with open('app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()
with open('temp_table.py', 'r', encoding='utf-8') as f:
    table_lines = f.readlines()

new_lines = lines[:25] + ['\n'] + table_lines + ['\n'] + lines[25:6637] + lines[6746:]
with open('app.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

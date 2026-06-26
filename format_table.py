with open('temp_table.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()
with open('temp_table.py', 'w', encoding='utf-8') as f:
    for line in lines:
        f.write(line[8:] if line.startswith('        ') else line)

with open('temp_table.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()
dedented = []
for i, line in enumerate(lines):
    if i == 0:
        dedented.append(line.replace('\ufeff', '').lstrip())
    else:
        if line.startswith('    '):
            dedented.append(line[4:])
        else:
            dedented.append(line)
with open('ahp_utils_v3.py', 'a', encoding='utf-8') as f:
    f.write('\n')
    f.writelines(dedented)

import sys

with open('f:/app/4. AHP마스터/app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i in range(3460, 3568):
    if lines[i].strip():
        lines[i] = "    " + lines[i]

with open('f:/app/4. AHP마스터/app.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("Fixed indentation for write_custom_ahp_table and add_borders_to_data")

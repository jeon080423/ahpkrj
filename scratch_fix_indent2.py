import sys

with open('f:/app/4. AHP마스터/app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i in range(3437, 3458):
    if lines[i].strip():
        lines[i] = "    " + lines[i]

with open('f:/app/4. AHP마스터/app.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("Fixed indentation for '나의 분석 보관함' block")

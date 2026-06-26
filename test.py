import re

with open('app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if '** 그룹 분류 문항 설정**' in line:
        print(f'Found old block at line {i+1}')
    if 'default_type_q = _("귀하의 소속은' in line:
        print(f'Found new block at line {i+1}')
    if 'type_questions = []' in line:
        print(f'Found type_questions init at line {i+1}')

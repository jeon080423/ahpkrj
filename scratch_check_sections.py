import sys
content = open('app.py', 'r', encoding='utf-8').read()
lines = content.split('\n')
for i, line in enumerate(lines):
    if 'st.subheader(' in line and '섹션' in line:
        print(f'{i}: {line.strip()}')
    if 'st.stop()' in line:
        print(f'{i}: {line.strip()}')

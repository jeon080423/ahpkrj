with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()
content = content.replace('엑셀 템플릿', '코딩 엑셀 양식')
content = content.replace('입력 코딩 엑셀 양식', '코딩 엑셀 양식')
with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('Replaced!')

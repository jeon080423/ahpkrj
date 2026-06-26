import re
with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()
# find the function
pattern = re.compile(r'        def write_custom_ahp_table\(.*?with main_tab2:', re.DOTALL)
match = pattern.search(content)
if match:
    func_text = match.group(0)[:-15] # remove 'with main_tab2:'
    content = content.replace(func_text, '')
    dedented = '\n'.join([line[8:] if line.startswith('        ') else line for line in func_text.splitlines()])
    # insert before 'def _(ko_text, en_text):'
    content = content.replace('def _(ko_text, en_text):', dedented + '\n\ndef _(ko_text, en_text):')
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('Replaced')
else:
    print('Not found')

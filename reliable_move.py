import sys

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Remove BOM if exists
if content.startswith('\ufeff'):
    content = content[1:]

lines = content.splitlines()

start_idx = -1
end_idx = -1
for i, line in enumerate(lines):
    if "def write_custom_ahp_table(" in line and "v3" not in line:
        start_idx = i
        break

if start_idx != -1:
    for i in range(start_idx, len(lines)):
        if "def add_borders_to_data" in lines[i]:
            pass
        if "with main_tab2:" in lines[i]:
            end_idx = i
            break

if start_idx != -1 and end_idx != -1:
    extracted = lines[start_idx:end_idx]
    # dedent by finding the leading spaces of the first line
    first_line = extracted[0]
    leading_spaces = len(first_line) - len(first_line.lstrip())
    dedented = [line[leading_spaces:] if line.startswith(' ' * leading_spaces) else line for line in extracted]
    
    # put the dedented at line 25
    new_lines = lines[:25] + dedented + lines[25:start_idx] + lines[end_idx:]
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write('\n'.join(new_lines))
    print("Success")
else:
    print("Could not find functions")

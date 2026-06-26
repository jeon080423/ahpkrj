import sys
content = open("app.py", "r", encoding="utf-8").read()
lines = content.split('\n')
for i, line in enumerate(lines):
    if "preview_file_path" in line:
        print(f"{i+1}: {line}")

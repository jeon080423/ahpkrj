import sys
content = open("app.py", "r", encoding="utf-8").read()
idx = content.find("if demographics.get(\"age\"):")
if idx != -1:
    sys.stdout.buffer.write(content[idx:idx+1500].encode("utf-8"))
else:
    print("Not found")

import sys
content = open("app.py", "r", encoding="utf-8").read()
idx = content.find("resp_data = {}")
if idx != -1:
    sys.stdout.buffer.write(content[max(0,idx-200):idx+800].encode("utf-8"))
else:
    print("Not found")

import sys
content = open("app.py", "r", encoding="utf-8").read()
idx = content.find("survey_id_param = f\"preview_")
if idx != -1:
    sys.stdout.buffer.write(content[max(0,idx-200):idx+1500].encode("utf-8", errors="replace"))
else:
    print("Not found")

import sys
content = open("app.py", "r", encoding="utf-8").read()
idx = content.find("resp_data = {}")
if idx != -1:
    end_idx = content.find("if demographics.get(\"gender\"):", idx)
    sys.stdout.buffer.write(content[idx:end_idx].encode("utf-8"))
else:
    print("Not found")

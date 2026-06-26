import sys
content = open("app.py", "r", encoding="utf-8").read()
idx = content.find("df_main = get_sheet_data(sh, \"Raw_Data\")")
if idx != -1:
    sys.stdout.buffer.write(content[max(0,idx-200):idx+1500].encode("utf-8"))
else:
    print("Not found")

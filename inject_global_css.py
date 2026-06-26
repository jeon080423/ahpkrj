import pandas as pd
import json

file_path = r"F:\SD카드 백업\Ahp\19. AHP마스터 셈플데이터\AHP_Master_Template.xlsx"
xls = pd.ExcelFile(file_path)

data = {}
for sheet_name in xls.sheet_names:
    df = pd.read_excel(file_path, sheet_name=sheet_name)
    
    sheet_data = {
        "columns": df.columns.tolist(),
        "first_5_rows": df.head(5).to_dict(orient="records")
    }
    data[sheet_name] = sheet_data

with open("temp_excel_info.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("Excel info saved to temp_excel_info.json")

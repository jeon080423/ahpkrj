import pandas as pd
import openpyxl

def inspect_excel(path):
    print(f"=== Inspecting {path} ===")
    try:
        xls = pd.ExcelFile(path)
        print("Sheets:", xls.sheet_names)
        for sheet in xls.sheet_names:
            df = pd.read_excel(path, sheet_name=sheet)
            print(f"Sheet: {sheet}, Shape: {df.shape}")
            print("Columns:", df.columns.tolist()[:10])
            print("First 2 rows:")
            print(df.head(2))
            print("-" * 40)
    except Exception as e:
        print(f"Error reading {path}: {e}")

inspect_excel("G:\\K_TAHP_Result.xlsx")
inspect_excel("G:\\K_FAHP_Result.xlsx")

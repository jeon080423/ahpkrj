import pandas as pd
import sys

def inspect_excel(path, output_txt):
    sys.stdout = open(output_txt, 'w', encoding='utf-8')
    try:
        xls = pd.ExcelFile(path)
        print(f"=== File: {path} ===")
        print("Sheets in file:", xls.sheet_names)
        print("="*60)
        for sheet in xls.sheet_names:
            df = pd.read_excel(path, sheet_name=sheet)
            print(f"Sheet: {sheet}, Shape: {df.shape}")
            # Print non-empty rows or a nice preview
            print("Preview of columns & first 10 rows:")
            pd.set_option('display.max_columns', 15)
            pd.set_option('display.width', 1000)
            print(df.head(15))
            print("*"*60)
    except Exception as e:
        print(f"Error: {e}")
    finally:
        sys.stdout.close()
        sys.stdout = sys.__stdout__

inspect_excel("G:\\K_TAHP_Result.xlsx", "G:\\scratch\\k_tahp_structure.txt")
inspect_excel("G:\\K_FAHP_Result.xlsx", "G:\\scratch\\k_fahp_structure.txt")
print("Done writing structures to G:\\scratch\\k_tahp_structure.txt and k_fahp_structure.txt")

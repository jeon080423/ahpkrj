import pandas as pd

def inspect_xlsx(path):
    print(f"=== Inspecting {path} ===")
    try:
        xls = pd.ExcelFile(path)
        print("Sheet names:", xls.sheet_names)
        for s in xls.sheet_names[:3]:
            df = xls.parse(s)
            print(f"  Sheet: {s}, Shape: {df.shape}")
            print("    Columns:", list(df.columns[:10]))
            print("    Sample Row:")
            if len(df) > 0:
                print(f"      {df.iloc[0].to_dict()}")
    except Exception as e:
        print(f"Error inspecting {path}: {e}")

inspect_xlsx("Mock_3Tier_Full.xlsx")
inspect_xlsx("Mock_3Tier_Partial.xlsx")

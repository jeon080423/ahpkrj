import pandas as pd

def verify_file(path):
    xls = pd.ExcelFile(path)
    print("Sheets in generated file:", xls.sheet_names)
    print("=" * 60)
    for sheet in xls.sheet_names:
        df = pd.read_excel(path, sheet_name=sheet)
        print(f"Sheet: {sheet}, Shape: {df.shape}")
        # Show first 5 rows and non-null values
        print(df.head(5))
        print("-" * 50)

if __name__ == "__main__":
    verify_file("G:\\scratch\\test_output_v3.xlsx")

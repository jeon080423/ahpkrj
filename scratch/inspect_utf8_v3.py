import openpyxl
import sys

wb = openpyxl.load_workbook("G:\\scratch\\test_output_v3.xlsx")
ws = wb["종합분석"]

sys.stdout.reconfigure(encoding='utf-8')
print("Rows in UTF-8:")
for r in range(4, 26):
    row_vals = [ws.cell(row=r, column=c).value for c in range(1, 10)]
    print(f"Row {r:2d}: {row_vals}")

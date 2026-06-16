import openpyxl
import sys

wb = openpyxl.load_workbook("G:\\K_TAHP_Result.xlsx")
ws = wb["종합분석"]

row_vals = [ws.cell(row=4, column=c).value for c in range(1, 10)]
sys.stdout.reconfigure(encoding='utf-8')
print("Headers in UTF-8:")
for idx, val in enumerate(row_vals):
    print(f"Col {idx+1}: {val}")

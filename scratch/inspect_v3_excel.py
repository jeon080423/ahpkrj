import openpyxl

wb = openpyxl.load_workbook("G:\\scratch\\test_output_v3.xlsx")
ws = wb["종합분석"]

print("Rows in '종합분석':")
for r in range(1, 30):
    row_vals = [ws.cell(row=r, column=c).value for c in range(1, 10)]
    print(f"Row {r:2d}: {row_vals}")

print("\nMerged Cells in '종합분석':")
for merged in sorted(ws.merged_cells.ranges, key=lambda r: (r.min_row, r.min_col)):
    print(f"Range: {merged.coord}")

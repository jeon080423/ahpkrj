import sys

file_path = r'f:\app\4. AHP마스터\app.py'

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i in range(4650, 4670):
    if 'from ahp_utils_v3 import run_ahp_analysis_v3' in lines[i] and 'write_custom_ahp_table_v3' not in lines[i]:
        lines[i] = lines[i].replace('from ahp_utils_v3 import run_ahp_analysis_v3', 'from ahp_utils_v3 import run_ahp_analysis_v3, write_custom_ahp_table_v3')
        print(f"Patched line {i}")

for i in range(5400, 5420):
    if 'current_row_ws = write_custom_ahp_table(' in lines[i]:
        lines[i] = lines[i].replace('write_custom_ahp_table(', 'write_custom_ahp_table_v3(')
        print(f"Patched line {i}")

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("Patching complete.")

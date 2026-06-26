import sys

file_path = r'f:\app\4. AHP마스터\app.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

old_block = """
        #  Rawdata  (-9 ~ 9) 
        raw_values = []
        col_idx = 0
        for i in range(n):
            for j in range(i + 1, n):
                if col_idx < len(comp_cols):
                    raw_val = row[comp_cols[col_idx]]
                    raw_values.append(raw_val)
                    ahp_val = parse_input_value(raw_val)
                    matrix[i, j] = ahp_val
                    matrix[j, i] = 1.0 / ahp_val
                    col_idx += 1
        
        orig_cr, orig_ci, _unused_lambda = calculate_consistency(matrix, method)
"""

new_block = """
        raw_values = []
        col_idx = 0
        has_format_error = False
        for i in range(n):
            for j in range(i + 1, n):
                if col_idx < len(comp_cols):
                    raw_val = row[comp_cols[col_idx]]
                    raw_values.append(raw_val)
                    
                    if pd.isna(raw_val) or type(raw_val) == str or not (-9 <= float(raw_val) <= 9):
                        has_format_error = True
                    
                    if not has_format_error:
                        ahp_val = parse_input_value(float(raw_val))
                        matrix[i, j] = ahp_val
                        matrix[j, i] = 1.0 / ahp_val
                    col_idx += 1
                    
        if has_format_error:
            excluded_count += 1
            ex_res = {"ID": respondent_id, "Type": respondent_type}
            for k, col_name in enumerate(comp_cols):
                ex_res[col_name] = raw_values[k] if k < len(raw_values) else np.nan
            ex_res["CR"] = "데이터 오류(Format Error)"
            excluded_list.append(ex_res)
            continue
            
        orig_cr, orig_ci, _unused_lambda = calculate_consistency(matrix, method)
"""

# Since old_block might have encoding/comment differences, let's use regex or string methods carefully.
# Wait, let's just find the start of 'raw_values = []' and end of 'orig_cr, orig_ci'

start_idx = content.find('raw_values = []\n        col_idx = 0')
end_idx = content.find('orig_cr, orig_ci, _unused_lambda = calculate_consistency(matrix, method)')
if start_idx != -1 and end_idx != -1:
    end_idx += len('orig_cr, orig_ci, _unused_lambda = calculate_consistency(matrix, method)')
    
    # Check if we are inside process_single_sheet
    if content.rfind('def process_single_sheet', 0, start_idx) != -1:
        new_content = content[:start_idx] + new_block.strip() + content[end_idx:]
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print("Patched process_single_sheet successfully.")
    else:
        print("Found but not inside process_single_sheet")
else:
    print("Could not find the block to replace.")

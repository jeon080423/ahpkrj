import sys

def update_app_py(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # The exact block we want to replace
    target_call = """                                success_v3, msg_v3, final_df_v3, output_res_v3 = run_ahp_analysis_v3(
                                    df_main, sub_dfs, sub_sub_dfs, cr_threshold, max_iter_val, learning_rate, mean_method, ahp_method
                                )"""

    replacement_call = """                                success_v3, msg_v3, final_df_v3, output_res_v3 = run_ahp_analysis_v3(
                                    df_main, sub_dfs, sub_sub_dfs, cr_threshold, max_iter_val, learning_rate, mean_method, ahp_method,
                                    process_single_sheet, fuzzy_ahp_analysis
                                )"""

    if target_call in content:
        content = content.replace(target_call, replacement_call)
        print("Updated run_ahp_analysis_v3 call successfully.")
    else:
        print("Failed to find target_call in app.py")
        sys.exit(1)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)

if __name__ == "__main__":
    update_app_py("f:/app/4. AHP마스터/app.py")

import sys

def replace_lines(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    start_idx = -1
    end_idx = -1
    
    # We want to replace from "col_btn1, col_btn2 = st.columns(2)"
    # to the end of "with col_btn3:" block.
    for i, line in enumerate(lines):
        if "col_btn1, col_btn2 = st.columns(2)" in line and start_idx == -1:
            start_idx = i
        if start_idx != -1 and i > start_idx:
            if "st.subheader(_(\"1. AHP 분석 모델 설정 및 입력 템플릿 다운로드\"" in line:
                end_idx = i - 1 # The empty line before the subheader
                break
                
    if start_idx == -1 or end_idx == -1:
        print("Could not find start or end index")
        return
        
    print(f"Replacing lines {start_idx} to {end_idx}")
    
    new_code = """            is_admin = st.session_state.get('user_role') == 'admin'
            
            if is_admin:
                col_btn1, col_btn2, col_btn3, col_btn4 = st.columns(4)
                with col_btn1:
                    st.download_button(
                        label=_("📂 2계층 샘플 데이터", "📂 Download 2-Tier Sample Data"),
                        data=sample_excel,
                        file_name=_("AHP_UrbanRegeneration_2Tier_Sample.xlsx", "AHP_UrbanRegeneration_2Tier_Sample.xlsx"),
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                        type="primary"
                    )
                with col_btn2:
                    st.download_button(
                        label=_("📂 3계층 샘플 데이터", "📂 Download 3-Tier Sample Data"),
                        data=sample_excel_v3,
                        file_name=_("AHP_Smartphone_3Tier_Sample.xlsx", "AHP_Smartphone_3Tier_Sample.xlsx"),
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                        type="primary"
                    )
                with col_btn3:
                    st.download_button(
                        label=_("📄 일반 AHP 보고서", "📄 Traditional AHP Report (Example)"),
                        data=tahp_data if tahp_data else b"",
                        file_name=_("E_TAHP_Result.xlsx", "E_TAHP_Result.xlsx") if is_en else _("K_TAHP_Result.xlsx", "K_TAHP_Result.xlsx"),
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                        disabled=(not tahp_data)
                    )
                with col_btn4:
                    st.download_button(
                        label=_("📄 퍼지 AHP 보고서", "📄 Fuzzy AHP Report (Example)"),
                        data=fahp_data if fahp_data else b"",
                        file_name=_("E_FAHP_Result.xlsx", "E_FAHP_Result.xlsx") if is_en else _("K_FAHP_Result.xlsx", "K_FAHP_Result.xlsx"),
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                        disabled=(not fahp_data)
                    )
            else:
                col_btn1, col_btn2, col_btn3 = st.columns(3)
                with col_btn1:
                    st.download_button(
                        label=_("📂 샘플 데이터 다운로드", "📂 Download Test Sample Data"),
                        data=sample_excel,
                        file_name=_("AHP_UrbanRegeneration_Sample.xlsx", "AHP_DecisionModel_Sample.xlsx"),
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                        type="primary"
                    )
                with col_btn2:
                    st.download_button(
                        label=_("📄 일반 AHP 보고서", "📄 Traditional AHP Report (Example)"),
                        data=tahp_data if tahp_data else b"",
                        file_name=_("E_TAHP_Result.xlsx", "E_TAHP_Result.xlsx") if is_en else _("K_TAHP_Result.xlsx", "K_TAHP_Result.xlsx"),
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                        disabled=(not tahp_data)
                    )
                with col_btn3:
                    st.download_button(
                        label=_("📄 퍼지 AHP 보고서", "📄 Fuzzy AHP Report (Example)"),
                        data=fahp_data if fahp_data else b"",
                        file_name=_("E_FAHP_Result.xlsx", "E_FAHP_Result.xlsx") if is_en else _("K_FAHP_Result.xlsx", "K_FAHP_Result.xlsx"),
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                        disabled=(not fahp_data)
                    )
"""
    
    # End idx points to the empty line, so we keep lines up to start_idx, then new_code, then lines from end_idx
    lines = lines[:start_idx] + [new_code] + lines[end_idx:]
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)
        
    print("Done replacing.")

if __name__ == "__main__":
    replace_lines("f:/app/4. AHP마스터/app.py")

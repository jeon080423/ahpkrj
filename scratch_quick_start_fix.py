import sys

def update_app_py(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # The exact block we want to replace
    target_btn = """            sample_excel_v3 = create_sample_excel_v3()
            
            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                st.download_button(
                    label=_("📂 2계층 테스트 데이터 다운로드", "📂 Download 2-Tier Sample Data"),
                    data=sample_excel,
                    file_name=_("AHP_UrbanRegeneration_2Tier_Sample.xlsx", "AHP_UrbanRegeneration_2Tier_Sample.xlsx"),
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                    type="primary"
                )
            with col_btn2:
                if st.session_state.get('user_role') == 'admin':
                    st.download_button(
                        label=_("📂 3계층 테스트 데이터 다운로드 (관리자용)", "📂 Download 3-Tier Sample Data"),
                        data=sample_excel_v3,
                        file_name=_("AHP_Smartphone_3Tier_Sample.xlsx", "AHP_Smartphone_3Tier_Sample.xlsx"),
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                        type="primary"
                    )
                else:
                    st.write("") # 빈 공간
            with col_btn2:
                st.download_button(
                    label=_("📄 일반 AHP 분석 보고서(예시)", "📄 Traditional AHP Analysis Report (Example)"),
                    data=tahp_data if tahp_data else b"",
                    file_name=_("E_TAHP_Result.xlsx", "E_TAHP_Result.xlsx") if is_en else _("K_TAHP_Result.xlsx", "K_TAHP_Result.xlsx"),
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                    disabled=(not tahp_data)
                )
            with col_btn3:
                st.download_button(
                    label=_("📄 퍼지 AHP 분석 보고서(예시)", "📄 Fuzzy AHP Analysis Report (Example)"),
                    data=fahp_data if fahp_data else b"",
                    file_name=_("E_FAHP_Result.xlsx", "E_FAHP_Result.xlsx") if is_en else _("K_FAHP_Result.xlsx", "K_FAHP_Result.xlsx"),
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                    disabled=(not fahp_data)
                )"""

    replacement_btn = """            sample_excel_v3 = create_sample_excel_v3()
            
            is_admin = st.session_state.get('user_role') == 'admin'
            
            if is_admin:
                cols = st.columns(4)
                with cols[0]:
                    st.download_button(
                        label=_("📂 2계층 샘플 데이터", "📂 Download 2-Tier Sample Data"),
                        data=sample_excel,
                        file_name=_("AHP_UrbanRegeneration_2Tier_Sample.xlsx", "AHP_UrbanRegeneration_2Tier_Sample.xlsx"),
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                        type="primary"
                    )
                with cols[1]:
                    st.download_button(
                        label=_("📂 3계층 샘플 데이터", "📂 Download 3-Tier Sample Data"),
                        data=sample_excel_v3,
                        file_name=_("AHP_Smartphone_3Tier_Sample.xlsx", "AHP_Smartphone_3Tier_Sample.xlsx"),
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                        type="primary"
                    )
                with cols[2]:
                    st.download_button(
                        label=_("📄 일반 AHP 보고서", "📄 Traditional AHP Report (Example)"),
                        data=tahp_data if tahp_data else b"",
                        file_name=_("E_TAHP_Result.xlsx", "E_TAHP_Result.xlsx") if is_en else _("K_TAHP_Result.xlsx", "K_TAHP_Result.xlsx"),
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                        disabled=(not tahp_data)
                    )
                with cols[3]:
                    st.download_button(
                        label=_("📄 퍼지 AHP 보고서", "📄 Fuzzy AHP Report (Example)"),
                        data=fahp_data if fahp_data else b"",
                        file_name=_("E_FAHP_Result.xlsx", "E_FAHP_Result.xlsx") if is_en else _("K_FAHP_Result.xlsx", "K_FAHP_Result.xlsx"),
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                        disabled=(not fahp_data)
                    )
            else:
                cols = st.columns(3)
                with cols[0]:
                    st.download_button(
                        label=_("📂 샘플 데이터 다운로드", "📂 Download Test Sample Data"),
                        data=sample_excel,
                        file_name=_("AHP_UrbanRegeneration_Sample.xlsx", "AHP_DecisionModel_Sample.xlsx"),
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                        type="primary"
                    )
                with cols[1]:
                    st.download_button(
                        label=_("📄 일반 AHP 보고서", "📄 Traditional AHP Report (Example)"),
                        data=tahp_data if tahp_data else b"",
                        file_name=_("E_TAHP_Result.xlsx", "E_TAHP_Result.xlsx") if is_en else _("K_TAHP_Result.xlsx", "K_TAHP_Result.xlsx"),
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                        disabled=(not tahp_data)
                    )
                with cols[2]:
                    st.download_button(
                        label=_("📄 퍼지 AHP 보고서", "📄 Fuzzy AHP Report (Example)"),
                        data=fahp_data if fahp_data else b"",
                        file_name=_("E_FAHP_Result.xlsx", "E_FAHP_Result.xlsx") if is_en else _("K_FAHP_Result.xlsx", "K_FAHP_Result.xlsx"),
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                        disabled=(not fahp_data)
                    )"""

    if target_btn in content:
        content = content.replace(target_btn, replacement_btn)
    else:
        print("Failed to find target_btn in app.py")
        sys.exit(1)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
        
    print("Updated button columns successfully.")

if __name__ == "__main__":
    update_app_py("f:/app/4. AHP마스터/app.py")

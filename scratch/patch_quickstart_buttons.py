"""
빠른 시작 섹션에서 is_admin 분기를 제거하고
모든 사용자에게 4개 버튼(2계층 샘플, 3계층 샘플, 일반AHP, 퍼지AHP)을 표시하는 패치.
"""

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_block = '''            is_admin = st.session_state.get('user_role') == 'admin'
            
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
                        file_name=_("Mock_3Tier_Full.xlsx", "Mock_3Tier_Full.xlsx"),
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                        type="primary"
                    )
                with col_btn3:
                    st.download_button(
                        label=_("📄 일반 AHP 분석 결과(예시)", "📄 Traditional AHP Report (Example)"),
                        data=tahp_data if tahp_data else b"",
                        file_name=_("E_TAHP_Result.xlsx", "E_TAHP_Result.xlsx") if is_en else _("K_TAHP_Result.xlsx", "K_TAHP_Result.xlsx"),
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                        disabled=(not tahp_data)
                    )
                with col_btn4:
                    st.download_button(
                        label=_("📄 퍼지 AHP 분석 결과(예시)", "📄 Fuzzy AHP Report (Example)"),
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
                        label=_("📄 일반 AHP 분석 결과(예시)", "📄 Traditional AHP Report (Example)"),
                        data=tahp_data if tahp_data else b"",
                        file_name=_("E_TAHP_Result.xlsx", "E_TAHP_Result.xlsx") if is_en else _("K_TAHP_Result.xlsx", "K_TAHP_Result.xlsx"),
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                        disabled=(not tahp_data)
                    )
                with col_btn3:
                    st.download_button(
                        label=_("📄 퍼지 AHP 분석 결과(예시)", "📄 Fuzzy AHP Report (Example)"),
                        data=fahp_data if fahp_data else b"",
                        file_name=_("E_FAHP_Result.xlsx", "E_FAHP_Result.xlsx") if is_en else _("K_FAHP_Result.xlsx", "K_FAHP_Result.xlsx"),
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                        disabled=(not fahp_data)
                    )'''

new_block = '''            # 모든 사용자에게 2계층·3계층 샘플 데이터 + 결과 예시 버튼 4개 표시
            col_btn1, col_btn2, col_btn3, col_btn4 = st.columns(4)
            with col_btn1:
                st.download_button(
                    label=_("📂 2계층 샘플 데이터", "📂 2-Tier Sample Data"),
                    data=sample_excel,
                    file_name=_("AHP_UrbanRegeneration_2Tier_Sample.xlsx", "AHP_UrbanRegeneration_2Tier_Sample.xlsx"),
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                    type="primary"
                )
            with col_btn2:
                st.download_button(
                    label=_("📂 3계층 샘플 데이터", "📂 3-Tier Sample Data"),
                    data=sample_excel_v3,
                    file_name=_("Mock_3Tier_Full.xlsx", "Mock_3Tier_Full.xlsx"),
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                    type="primary"
                )
            with col_btn3:
                st.download_button(
                    label=_("📄 일반 AHP 분석 결과(예시)", "📄 Traditional AHP Report (Example)"),
                    data=tahp_data if tahp_data else b"",
                    file_name=_("E_TAHP_Result.xlsx", "E_TAHP_Result.xlsx") if is_en else _("K_TAHP_Result.xlsx", "K_TAHP_Result.xlsx"),
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                    disabled=(not tahp_data)
                )
            with col_btn4:
                st.download_button(
                    label=_("📄 퍼지 AHP 분석 결과(예시)", "📄 Fuzzy AHP Report (Example)"),
                    data=fahp_data if fahp_data else b"",
                    file_name=_("E_FAHP_Result.xlsx", "E_FAHP_Result.xlsx") if is_en else _("K_FAHP_Result.xlsx", "K_FAHP_Result.xlsx"),
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                    disabled=(not fahp_data)
                )'''

if old_block in content:
    new_content = content.replace(old_block, new_block, 1)
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("SUCCESS: Quick start 4-button patch applied.")
else:
    print("ERROR: Old block not found.")
    import re
    m = re.search(r'is_admin = st\.session_state\.get\(\'user_role\'\) == \'admin\'', content)
    if m:
        print("Partial match found at:", m.start())
    else:
        print("No match.")

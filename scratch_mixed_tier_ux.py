import sys

def modify_mixed_tier_ux(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Target 1: Tab 1 UI
    target1 = """                    if tier_level == 3 and sub_list:
                        with st.expander(f"▶ '{mc}'의 소분류 (Sub-sub-criteria) 입력", expanded=True):
                            for sub_c in sub_list:
                                sub_sub_input = st.text_input(
                                    f"▶ '{sub_c}'의 소분류 (콤마 구분)", 
                                    value="",
                                    key=f"tab1_sub_sub_{sub_c}"
                                )"""

    replacement1 = """                    if tier_level == 3 and sub_list:
                        with st.expander(f"▶ '{mc}'의 소분류 (Sub-sub-criteria) 입력", expanded=True):
                            st.info("💡 **혼합 계층 안내**: 소분류(3계층)가 없는 항목은 **비워두시면 자동으로 2계층 가중치로 계산**됩니다.")
                            for sub_c in sub_list:
                                sub_sub_input = st.text_input(
                                    f"▶ '{sub_c}'의 소분류 (콤마 구분)", 
                                    value="",
                                    placeholder="예: 항목1, 항목2 (※ 하위 요인이 없다면 비워두세요)",
                                    help="입력칸을 비워두면 이 항목은 2계층 구조로 간주되어 분석됩니다.",
                                    key=f"tab1_sub_sub_{sub_c}"
                                )"""

    if target1 in content:
        content = content.replace(target1, replacement1)
    else:
        print("Target 1 not found")
        sys.exit(1)

    # Target 2: Tab 2 UI
    target2 = """                # [신규] 3계층 선택 시 소분류 입력 필드 동적 생성
                if tier_level == 3 and subs_list:
                    with st.expander(f"▶ '{mc}'의 소분류 (Sub-sub-criteria) 입력", expanded=True):
                        for sub_c in subs_list:
                            sub_sub_val = "" # 3계층 기본은 빈칸
                            sub_sub_input = st.text_input(
                                f"▶ '{sub_c}'의 소분류 (쉼표 구분)", 
                                value=st.session_state.get("edit_sub_sub_inputs", {}).get(sub_c, sub_sub_val),
                                key=f"sub_sub_{sub_c}"
                            )"""

    replacement2 = """                # [신규] 3계층 선택 시 소분류 입력 필드 동적 생성
                if tier_level == 3 and subs_list:
                    with st.expander(f"▶ '{mc}'의 소분류 (Sub-sub-criteria) 입력", expanded=True):
                        st.info("💡 **혼합 계층 안내**: 소분류(3계층)가 없는 항목은 **비워두시면 자동으로 2계층 가중치로 계산**됩니다.")
                        for sub_c in subs_list:
                            sub_sub_val = "" # 3계층 기본은 빈칸
                            sub_sub_input = st.text_input(
                                f"▶ '{sub_c}'의 소분류 (쉼표 구분)", 
                                value=st.session_state.get("edit_sub_sub_inputs", {}).get(sub_c, sub_sub_val),
                                placeholder="예: 항목1, 항목2 (※ 하위 요인이 없다면 비워두세요)",
                                help="입력칸을 비워두면 이 항목은 2계층 구조로 간주되어 분석됩니다.",
                                key=f"sub_sub_{sub_c}"
                            )"""

    if target2 in content:
        content = content.replace(target2, replacement2)
    else:
        print("Target 2 not found")
        sys.exit(1)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
        
    print("Mixed-Tier UX logic updated.")

if __name__ == "__main__":
    modify_mixed_tier_ux("f:/app/4. AHP마스터/app.py")

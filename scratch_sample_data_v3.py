import sys

def update_sample_data(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Define the new sample block to insert after ko_default_subs
    new_defaults = """
        # [신규] 3계층(V3) 샘플 데이터 (스마트폰 구매 결정)
        en_default_main_v3 = "Functionality, Design, Economy"
        en_default_subs_v3 = {
            "Functionality": "Hardware, Software",
            "Design": "Appearance, Usability",
            "Economy": "Device Price, Maintenance"
        }
        en_default_sub_subs_v3 = {
            "Hardware": "Camera, Battery, Processor",
            "Software": "OS, Default Apps",
            "Appearance": "Color, Material",
            "Usability": "", 
            "Device Price": "Lump Sum, Installment",
            "Maintenance": "Plan, Repair"
        }

        ko_default_main_v3 = "기능성, 디자인, 경제성"
        ko_default_subs_v3 = {
            "기능성": "하드웨어, 소프트웨어",
            "디자인": "외관, 편의성",
            "경제성": "단말기가격, 유지비용"
        }
        ko_default_sub_subs_v3 = {
            "하드웨어": "카메라, 배터리, 프로세서",
            "소프트웨어": "운영체제, 기본앱",
            "외관": "색상, 재질",
            "편의성": "", 
            "단말기가격": "일시불, 할부",
            "유지비용": "통신요금, AS비용"
        }
"""
    # Target 1: Insert new defaults in Tab 1
    target_defaults = """        ko_default_subs = {
            "거버넌스": "행정지원, 지역공동체, 총괄사업관리자",
            "계획타당성": "현안적정성, 대안적정성, 목표구체성",
            "실현가능성": "재원확보, 부지확보, 주민동의",
            "사업효과": "주거환경개선, 경제활성화, 공동체회복"
        }"""
        
    replacement_defaults = target_defaults + "\n" + new_defaults

    if target_defaults in content:
        content = content.replace(target_defaults, replacement_defaults)
    else:
        print("Failed to find target_defaults")
        sys.exit(1)

    # Target 2: Change Tab 1 default assignment to use tier_level.
    # Wait, tier_level is defined inside expander. We need to move the default assignment inside the expander, AFTER tier_level is set.
    # Let's remove the old assignment block first.
    target_old_assign = """        if is_en:
            default_main = en_default_main
            default_subs = en_default_subs
        else:
            default_main = ko_default_main
            default_subs = ko_default_subs

        if saved_model:
            saved_main = saved_model.get('main', '')
            # 만약 저장된 모델이 반대 언어의 기본 예시와 동일하거나 비어 있다면, 현재 언어의 기본 예시를 표시
            if is_en and (saved_main == ko_default_main or not saved_main):
                pass
            elif not is_en and (saved_main == en_default_main or not saved_main):
                pass
            else:
                default_main = saved_main
                default_subs = saved_model.get('subs', default_subs)"""

    replacement_old_assign = """        # default assignments are moved inside expander to react to tier_level"""

    if target_old_assign in content:
        content = content.replace(target_old_assign, replacement_old_assign)
    else:
        print("Failed to find target_old_assign")
        sys.exit(1)

    # Target 3: Insert the new assignment block inside expander, right before main_criteria_input
    target_inside_expander = """            tier_level = 3 if "3계층" in tier_choice else 2
                st.markdown("---")
            main_criteria_input = st.text_input(_("대항목 (Main Criteria, 콤마 구분)", "Main Criteria (comma-separated)"), value=default_main)"""
    
    # Actually, the code is:
    #                 if "3계층" in tier_choice:
    #                     tier_level = 3
    #                 st.markdown("---")
    #             main_criteria_input = st.text_input(_("대항목 (Main Criteria, 콤마 구분)", "Main Criteria (comma-separated)"), value=default_main)

    target_inside_expander_real = """                if "3계층" in tier_choice:
                    tier_level = 3
                st.markdown("---")
            main_criteria_input = st.text_input(_("대항목 (Main Criteria, 콤마 구분)", "Main Criteria (comma-separated)"), value=default_main)"""

    replacement_inside_expander = """                if "3계층" in tier_choice:
                    tier_level = 3
                st.markdown("---")
                
            # [신규] tier_level에 따라 샘플 데이터 스위칭
            if is_en:
                default_main = en_default_main_v3 if tier_level == 3 else en_default_main
                default_subs = en_default_subs_v3 if tier_level == 3 else en_default_subs
                default_sub_subs = en_default_sub_subs_v3 if tier_level == 3 else {}
            else:
                default_main = ko_default_main_v3 if tier_level == 3 else ko_default_main
                default_subs = ko_default_subs_v3 if tier_level == 3 else ko_default_subs
                default_sub_subs = ko_default_sub_subs_v3 if tier_level == 3 else {}
                
            if saved_model:
                saved_main = saved_model.get('main', '')
                if is_en and (saved_main == ko_default_main or saved_main == ko_default_main_v3 or not saved_main):
                    pass
                elif not is_en and (saved_main == en_default_main or saved_main == en_default_main_v3 or not saved_main):
                    pass
                else:
                    default_main = saved_main
                    default_subs = saved_model.get('subs', default_subs)
                    
            main_criteria_input = st.text_input(_("대항목 (Main Criteria, 콤마 구분)", "Main Criteria (comma-separated)"), value=default_main)"""

    if target_inside_expander_real in content:
        content = content.replace(target_inside_expander_real, replacement_inside_expander)
    else:
        print("Failed to find target_inside_expander_real")
        sys.exit(1)

    # Target 4: Pre-fill sub_subs based on default_sub_subs
    target_sub_sub = """                                sub_sub_input = st.text_input(
                                    f"▶ '{sub_c}'의 소분류 (콤마 구분)", 
                                    value="",
                                    placeholder="예: 항목1, 항목2 (※ 하위 요인이 없다면 비워두세요)","""
                                    
    replacement_sub_sub = """                                sub_sub_input = st.text_input(
                                    f"▶ '{sub_c}'의 소분류 (콤마 구분)", 
                                    value=default_sub_subs.get(sub_c, ""),
                                    placeholder="예: 항목1, 항목2 (※ 하위 요인이 없다면 비워두세요)","""

    if target_sub_sub in content:
        content = content.replace(target_sub_sub, replacement_sub_sub)
    else:
        print("Failed to find target_sub_sub")
        sys.exit(1)


    # --- TAB 2 LOGIC ---
    # Target 5: In Tab 2, change the main criteria default value based on tier_level
    target_tab2_main = """            main_input = st.text_input(_("대항목 (Main Criteria)", "Main Criteria"), value=st.session_state.get("edit_main_input", "기술 요인, 조직 요인, 환경 요인, 혁신 요인"))"""
    
    replacement_tab2_main = """            default_tab2_main = "기능성, 디자인, 경제성" if tier_level == 3 else "기술 요인, 조직 요인, 환경 요인, 혁신 요인"
            main_input = st.text_input(_("대항목 (Main Criteria)", "Main Criteria"), value=st.session_state.get("edit_main_input", default_tab2_main))"""

    if target_tab2_main in content:
        content = content.replace(target_tab2_main, replacement_tab2_main)
    else:
        print("Failed to find target_tab2_main")
        sys.exit(1)

    # Target 6: In Tab 2, change the sub default values
    target_tab2_sub = """            for mc in main_list:
                # 기본값 제안 (기존 양승훈 협동로봇 설문지 구조 자동 매핑)
                default_sub_val = ""
                if mc == "기술 요인": default_sub_val = "상대적이점, 호환성, 안전성, 서비스지원"
                elif mc == "조직 요인": default_sub_val = "경영진지원, 기술준비도, 금융자원, 교육훈련"
                elif mc == "환경 요인": default_sub_val = "정부지원, 경쟁압력, 인력난, 외부지원"
                elif mc == "혁신 요인": default_sub_val = "경영진의 혁신성, 변화수용태도, 스마트팩토리수준, 지식정도"

                sub_input = st.text_input(_(f"'{mc}'의 하위 요인 (Sub-criteria)", f"Sub-criteria for '{mc}'"), value=st.session_state.get("edit_sub_inputs", {}).get(mc, default_sub_val))"""

    replacement_tab2_sub = """            for mc in main_list:
                # 기본값 제안 (기존 양승훈 협동로봇 및 3계층 스마트폰 구매 결정)
                default_sub_val = ""
                if mc == "기술 요인": default_sub_val = "상대적이점, 호환성, 안전성, 서비스지원"
                elif mc == "조직 요인": default_sub_val = "경영진지원, 기술준비도, 금융자원, 교육훈련"
                elif mc == "환경 요인": default_sub_val = "정부지원, 경쟁압력, 인력난, 외부지원"
                elif mc == "혁신 요인": default_sub_val = "경영진의 혁신성, 변화수용태도, 스마트팩토리수준, 지식정도"
                elif mc == "기능성": default_sub_val = "하드웨어, 소프트웨어"
                elif mc == "디자인": default_sub_val = "외관, 편의성"
                elif mc == "경제성": default_sub_val = "단말기가격, 유지비용"

                sub_input = st.text_input(_(f"'{mc}'의 하위 요인 (Sub-criteria)", f"Sub-criteria for '{mc}'"), value=st.session_state.get("edit_sub_inputs", {}).get(mc, default_sub_val))"""

    if target_tab2_sub in content:
        content = content.replace(target_tab2_sub, replacement_tab2_sub)
    else:
        print("Failed to find target_tab2_sub")
        sys.exit(1)

    # Target 7: In Tab 2, pre-fill sub_subs
    target_tab2_sub_sub = """                        for sub_c in subs_list:
                            sub_sub_val = "" # 3계층 기본값은 빈칸
                            sub_sub_input = st.text_input("""
                            
    replacement_tab2_sub_sub = """                        for sub_c in subs_list:
                            sub_sub_val = "" # 3계층 기본값은 빈칸
                            if sub_c == "하드웨어": sub_sub_val = "카메라, 배터리, 프로세서"
                            elif sub_c == "소프트웨어": sub_sub_val = "운영체제, 기본앱"
                            elif sub_c == "외관": sub_sub_val = "색상, 재질"
                            elif sub_c == "단말기가격": sub_sub_val = "일시불, 할부"
                            elif sub_c == "유지비용": sub_sub_val = "통신요금, AS비용"
                            
                            sub_sub_input = st.text_input("""

    if target_tab2_sub_sub in content:
        content = content.replace(target_tab2_sub_sub, replacement_tab2_sub_sub)
    else:
        print("Failed to find target_tab2_sub_sub")
        sys.exit(1)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
        
    print("Sample data updated!")

if __name__ == "__main__":
    update_sample_data("f:/app/4. AHP마스터/app.py")

import sys

def update_app_py(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Target 1: Add create_sample_excel_v3() right before create_sample_excel()
    # Or right after it. Let's find def create_sample_excel() and add it before.
    target_create_sample = "def create_sample_excel():"
    
    new_func = """import itertools
import numpy as np

def create_sample_excel_v3():
    output = io.BytesIO()
    is_en = (st.session_state.get('lang', 'ko') == 'en')
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        if is_en:
            main_list = ["Functionality", "Design", "Economy"]
            subs = {"Functionality": ["Hardware", "Software"], "Design": ["Appearance", "Usability"], "Economy": ["Device Price", "Maintenance"]}
            sub_subs = {"Hardware": ["Camera", "Battery", "Processor"], "Software": ["OS", "Default Apps"], "Appearance": ["Color", "Material"], "Usability": [], "Device Price": ["Lump Sum", "Installment"], "Maintenance": ["Plan", "Repair"]}
        else:
            main_list = ["기능성", "디자인", "경제성"]
            subs = {"기능성": ["하드웨어", "소프트웨어"], "디자인": ["외관", "편의성"], "경제성": ["단말기가격", "유지비용"]}
            sub_subs = {"하드웨어": ["카메라", "배터리", "프로세서"], "소프트웨어": ["운영체제", "기본앱"], "외관": ["색상", "재질"], "편의성": [], "단말기가격": ["일시불", "할부"], "유지비용": ["통신요금", "AS비용"]}
            
        def _get_dummy_data(cols, num_respondents=3):
            # cols contains ["ID", "Type", pair1, pair2...]
            data = []
            for i in range(num_respondents):
                row = [i+1, "전문가" if not is_en else "Expert"]
                for _ in range(len(cols)-2):
                    row.append(int(np.random.choice([1, 3, 5, -3, -5])))
                data.append(row)
            return data
            
        main_pairs = list(itertools.combinations(main_list, 2))
        main_cols = ["ID", "Type"] + [f"{a}_{b}" for a, b in main_pairs]
        df_main = pd.DataFrame(_get_dummy_data(main_cols), columns=main_cols)
        df_main.to_excel(writer, sheet_name="Main_Criteria", index=False)
        
        for mc in main_list:
            sub_list = subs.get(mc, [])
            if len(sub_list) < 2:
                df_sub = pd.DataFrame(columns=["ID", "Type"])
            else:
                sub_pairs = list(itertools.combinations(sub_list, 2))
                sub_cols = ["ID", "Type"] + [f"{a}_{b}" for a, b in sub_pairs]
                df_sub = pd.DataFrame(_get_dummy_data(sub_cols), columns=sub_cols)
            df_sub.to_excel(writer, sheet_name=mc[:31], index=False)
            
            for sub_c in sub_list:
                ss_list = sub_subs.get(sub_c, [])
                if len(ss_list) < 2:
                    df_ss = pd.DataFrame(columns=["ID", "Type"])
                else:
                    ss_pairs = list(itertools.combinations(ss_list, 2))
                    ss_cols = ["ID", "Type"] + [f"{a}_{b}" for a, b in ss_pairs]
                    df_ss = pd.DataFrame(_get_dummy_data(ss_cols), columns=ss_cols)
                df_ss.to_excel(writer, sheet_name=f"{mc[:15]}_{sub_c[:15]}", index=False)
                
    output.seek(0)
    return output.getvalue()

def create_sample_excel():"""

    if target_create_sample in content:
        content = content.replace(target_create_sample, new_func)
    else:
        print("Failed to find create_sample_excel")
        sys.exit(1)

    # Target 2: Modify the buttons in Quick Start section
    target_btn = """            col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 1])
            with col_btn1:
                st.download_button(
                    label=_("📂 테스트용 샘플 데이터 다운로드", "📂 Download Test Sample Data"),
                    data=sample_excel,
                    file_name=_("AHP_UrbanRegeneration_Sample.xlsx", "AHP_DecisionModel_Sample.xlsx"),
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                    type="primary"
                )"""
                
    replacement_btn = """            sample_excel_v3 = create_sample_excel_v3()
            
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
                    st.write("") # 빈 공간"""

    if target_btn in content:
        content = content.replace(target_btn, replacement_btn)
    else:
        print("Failed to find target_btn")
        sys.exit(1)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
        
    print("Updated Quick Start buttons")

if __name__ == "__main__":
    update_app_py("f:/app/4. AHP마스터/app.py")

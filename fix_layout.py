import sys

file_path = "f:/app/4. AHP마스터/app.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

block1_old = """            # 척도 수에 맞추어 비율 동적 계산 (left_cols + 동일(1) + right_cols)
            total_scale_count = len(left_cols) + 1 + len(right_cols)
            
            # 1-3-5, 1-3-7-9, 1-9 연속형 척도별 헤더 대비 라디오의 정렬을 1px 오차 없이 일치시키기 위한 최적의 좌우 백분율 패딩 적용
            # 각 척도 종류별 브라우저 렌더링 비율을 극도로 계산한 결과값 반영
            if scale_type == "1-3-5 Discrete":
                padding_val = "10.0%"
            elif scale_type == "1-3-7-9 Discrete":
                padding_val = "6.5%"
            else: # 1-9 Continuous (17개 옵션)
                padding_val = "2.1%"

            # CSS 주입: 컬럼 간의 gap을 0으로 차단하고 라디오 그룹의 패딩을 동적 비율로 일치시킴
            st.markdown(
                f\"\"\"
                <style>
                div[data-testid="stHorizontalBlock"] {{
                    gap: 0px !important;
                }}
                div[data-testid="column"] {{
                    padding: 0px !important;
                }}
                /* streamlit radio horizontal flex layout override to distribute items evenly */
                div[role="radiogroup"] {{
                    display: flex !important;
                    flex-direction: row !important;
                    justify-content: space-between !important;
                    width: 100% !important;
                    gap: 0px !important;
                    padding: 0px {padding_val} !important; /* 각 척도별 정밀 매핑 여백 반영 */
                }}
                div[role="radiogroup"] > label {{
                    flex: 1 !important;
                    text-align: center !important;
                    display: flex !important;
                    flex-direction: column !important;
                    align-items: center !important;
                    justify-content: center !important;
                    margin: 0px !important;
                    padding: 0px !important;
                    min-width: 0px !important;
                }}
                /* 라디오 버튼의 숫자 텍스트 숨기기 */
                div[role="radiogroup"] label div[data-testid="stWidgetLabel"],
                div[role="radiogroup"] label p {{
                    display: none !important;
                    height: 0px !important;
                    margin: 0px !important;
                    padding: 0px !important;
                }}
                /* 동그라미 라디오 버튼 정중앙 배치 */
                div[role="radiogroup"] label span {{
                    margin: 0px auto !important;
                    padding: 0px !important;
                }}
                </style>
                \"\"\",
                unsafe_allow_html=True
            )

            # HTML 구조를 사용해 깔끔한 메트릭스 표 상단부(헤더) 정의
            # 구글 폼/네이버 폼 스타일처럼 100% 꽉 찬 고정 테이블을 사용하여 라인 일치 보장
            header_cells = left_cols + ["1"] + right_cols
            td_width = 100.0 / len(header_cells)
            
            # HTML 표 헤더 구조
            header_html = f\"\"\"
            <table style="width:100%; border-collapse: collapse; text-align: center; font-size: 13px; font-family: sans-serif; border: 1px solid #444444; table-layout: fixed; margin: 0px; padding: 0px;">
                <tr style="background-color: #d1d5db; font-weight: bold; border-bottom: 1px solid #444444;">
                    <th style="width: 16%; border: 1px solid #444444; padding: 8px;" rowspan="2">항목</th>
                    <th style="width: 34%; border: 1px solid #444444; padding: 4px;" colspan="{len(left_cols)}">◀ 좌측 항목이 더 중요</th>
                    <th style="width: 10%; border: 1px solid #444444; padding: 4px; background-color: #cbd5e1;" rowspan="2">동일<br>(1)</th>
                    <th style="width: 34%; border: 1px solid #444444; padding: 4px;" colspan="{len(right_cols)}">우측 항목이 더 중요 ▶</th>
                    <th style="width: 16%; border: 1px solid #444444; padding: 8px;" rowspan="2">항목</th>
                </tr>
                <tr style="background-color: #e5e7eb; font-weight: bold; border-bottom: 2px solid #444444;">
                    {"".join([f"<td style='border: 1px solid #444444; padding: 6px 0; width: {td_width}%;'>{val}</td>" for val in left_cols])}
                    {"".join([f"<td style='border: 1px solid #444444; padding: 6px 0; width: {td_width}%;'>{val}</td>" for val in right_cols])}
                </tr>
            </table>
            \"\"\"
            st.markdown(header_html, unsafe_allow_html=True)
            st.write("") # 미세 세로 간격 확보

            # 3단 컬럼 배치: [왼쪽 요인명 컬럼 (1.6 / 16%)] - [척도 라디오 버튼 영역 컬럼 (6.8 / 68%)] - [오른쪽 요인명 컬럼 (1.6 / 16%)]
            # 상단 헤더 테이블의 width 비율인 16%, 68%(34+10+34), 16% 와 정확히 매핑되도록 분할
            for left_f, right_f in comb["pairs"]:
                pair_key = f"{left_f}_{right_f}"
                
                row_cols = st.columns([1.6, 6.8, 1.6])"""

block1_new = """            # 척도 수에 맞추어 비율 동적 계산 (left_cols + 동일(1) + right_cols)
            header_cells = left_cols + ["1"] + right_cols
            total_scale_count = len(header_cells)
            scale_width = 70.0 / total_scale_count
            left_width = scale_width * len(left_cols)
            right_width = scale_width * len(right_cols)

            # CSS 주입: 컬럼 간의 gap을 0으로 차단하고 라디오 그룹을 100% 분배
            st.markdown(
                f\"\"\"
                <style>
                div[data-testid="stHorizontalBlock"] {{
                    gap: 0px !important;
                }}
                div[data-testid="column"] {{
                    padding: 0px !important;
                }}
                /* streamlit radio horizontal flex layout override to distribute items evenly */
                div[data-testid="stRadio"] {{
                    width: 100% !important;
                }}
                div[role="radiogroup"] {{
                    display: flex !important;
                    flex-direction: row !important;
                    justify-content: space-between !important;
                    width: 100% !important;
                    gap: 0px !important;
                    padding: 0px !important; 
                }}
                div[role="radiogroup"] > label {{
                    flex: 1 1 0% !important;
                    text-align: center !important;
                    display: flex !important;
                    flex-direction: column !important;
                    align-items: center !important;
                    justify-content: center !important;
                    margin: 0px !important;
                    padding: 0px !important;
                    min-width: 0px !important;
                }}
                /* 라디오 버튼의 숫자 텍스트 숨기기 */
                div[role="radiogroup"] label div[data-testid="stWidgetLabel"],
                div[role="radiogroup"] label p {{
                    display: none !important;
                    height: 0px !important;
                    margin: 0px !important;
                    padding: 0px !important;
                }}
                /* 동그라미 라디오 버튼 정중앙 배치 */
                div[role="radiogroup"] label span {{
                    margin: 0px auto !important;
                    padding: 0px !important;
                }}
                </style>
                \"\"\",
                unsafe_allow_html=True
            )

            # HTML 표 헤더 구조
            header_html = f\"\"\"
            <table style="width:100%; border-collapse: collapse; text-align: center; font-size: 13px; font-family: sans-serif; border: 1px solid #444444; table-layout: fixed; margin: 0px; padding: 0px;">
                <tr style="background-color: #d1d5db; font-weight: bold; border-bottom: 1px solid #444444;">
                    <th style="width: 15%; border: 1px solid #444444; padding: 8px;" rowspan="2">항목</th>
                    <th style="width: {left_width}%; border: 1px solid #444444; padding: 4px;" colspan="{len(left_cols)}">◀ 좌측 항목이 더 중요</th>
                    <th style="width: {scale_width}%; border: 1px solid #444444; padding: 4px; background-color: #cbd5e1;" rowspan="2">동일<br>(1)</th>
                    <th style="width: {right_width}%; border: 1px solid #444444; padding: 4px;" colspan="{len(right_cols)}">우측 항목이 더 중요 ▶</th>
                    <th style="width: 15%; border: 1px solid #444444; padding: 8px;" rowspan="2">항목</th>
                </tr>
                <tr style="background-color: #e5e7eb; font-weight: bold; border-bottom: 2px solid #444444;">
                    {"".join([f"<td style='border: 1px solid #444444; padding: 6px 0;'>{val}</td>" for val in left_cols])}
                    {"".join([f"<td style='border: 1px solid #444444; padding: 6px 0;'>{val}</td>" for val in right_cols])}
                </tr>
            </table>
            \"\"\"
            st.markdown(header_html, unsafe_allow_html=True)
            st.write("") # 미세 세로 간격 확보

            # 3단 컬럼 배치: [왼쪽 요인명 컬럼 (15%)] - [척도 라디오 버튼 영역 컬럼 (70%)] - [오른쪽 요인명 컬럼 (15%)]
            for left_f, right_f in comb["pairs"]:
                pair_key = f"{left_f}_{right_f}"
                
                row_cols = st.columns([15, 70, 15])"""

block2_old = """                if scale_option == "1-3-5 Discrete":
                    left_cols = ["5", "3"]
                    right_cols = ["3", "5"]
                    options = [-5, -3, 1, 3, 5]
                    padding_val = "10.0%"
                elif scale_option == "1-3-7-9 Discrete":
                    left_cols = ["9", "7", "3"]
                    right_cols = ["3", "7", "9"]
                    options = [-9, -7, -3, 1, 3, 7, 9]
                    padding_val = "6.5%"
                else: # 1-9 Continuous (Default)
                    left_cols = ["9", "8", "7", "6", "5", "4", "3", "2"]
                    right_cols = ["2", "3", "4", "5", "6", "7", "8", "9"]
                    options = list(range(-9, -1)) + list(range(1, 10))
                    options = sorted(list(set(options))) # -9 ~ -2, 1, 2 ~ 9
                    padding_val = "2.1%"

                # 미리보기 화면에도 수직 정렬 CSS 주입 (gap 0px 제거 및 척도별 동적 padding 적용)
                st.markdown(
                    f\"\"\"
                    <style>
                    div[data-testid="stHorizontalBlock"] {{
                        gap: 0px !important;
                    }}
                    div[data-testid="column"] {{
                        padding: 0px !important;
                    }}
                    div[role="radiogroup"] {{
                        display: flex !important;
                        flex-direction: row !important;
                        justify-content: space-between !important;
                        width: 100% !important;
                        gap: 0px !important;
                        padding: 0px {padding_val} !important; /* 각 척도별 정밀 매핑 여백 반영 */
                    }}
                    div[role="radiogroup"] > label {{
                        flex: 1 !important;
                        text-align: center !important;
                        display: flex !important;
                        flex-direction: column !important;
                        align-items: center !important;
                        justify-content: center !important;
                        margin: 0px !important;
                        padding: 0px !important;
                        min-width: 0px !important;
                    }}
                    div[role="radiogroup"] label div[data-testid="stWidgetLabel"],
                    div[role="radiogroup"] label p {{
                        display: none !important;
                        height: 0px !important;
                        margin: 0px !important;
                        padding: 0px !important;
                    }}
                    div[role="radiogroup"] label span {{
                        margin: 0px auto !important;
                        padding: 0px !important;
                    }}
                    </style>
                    \"\"\",
                    unsafe_allow_html=True
                )

                # 헤더 렌더링용 td 너비
                header_cells = left_cols + ["1"] + right_cols
                td_width = 100.0 / len(header_cells)

                for comb in combinations:
                    parent_lbl = f"[{comb['parent']}] 하위 요인 비교" if comb['type'] == 'sub' else "대분류(핵심) 요인 비교"
                    st.markdown(f"##### 🔍 {parent_lbl}")
                    
                    # HTML 구조를 사용해 깔끔한 메트릭스 표 상단부(헤더) 정의 (미리보기)
                    header_html = f\"\"\"
                    <table style="width:100%; border-collapse: collapse; text-align: center; font-size: 13px; font-family: sans-serif; border: 1px solid #444444; margin-bottom: 10px; table-layout: fixed;">
                        <tr style="background-color: #d1d5db; font-weight: bold; border-bottom: 1px solid #444444;">
                            <th style="width: 16%; border: 1px solid #444444; padding: 8px;" rowspan="2">항목</th>
                            <th style="width: 34%; border: 1px solid #444444; padding: 4px;" colspan="{len(left_cols)}">◀ 좌측 항목이 더 중요</th>
                            <th style="width: 10%; border: 1px solid #444444; padding: 4px; background-color: #cbd5e1;" rowspan="2">동일<br>(1)</th>
                            <th style="width: 34%; border: 1px solid #444444; padding: 4px;" colspan="{len(right_cols)}">우측 항목이 더 중요 ▶</th>
                            <th style="width: 16%; border: 1px solid #444444; padding: 8px;" rowspan="2">항목</th>
                        </tr>
                        <tr style="background-color: #e5e7eb; font-weight: bold; border-bottom: 2px solid #444444;">
                            {"".join([f"<td style='border: 1px solid #444444; padding: 6px 0; width: {td_width}%;'>{val}</td>" for val in left_cols])}
                            {"".join([f"<td style='border: 1px solid #444444; padding: 6px 0; width: {td_width}%;'>{val}</td>" for val in right_cols])}
                        </tr>
                    </table>
                    \"\"\"
                    st.markdown(header_html, unsafe_allow_html=True)
                    st.write("")
                    
                    for left_f, right_f in comb["pairs"]:
                        pair_key = f"{left_f}_{right_f}"
                        row_cols = st.columns([1.6, 6.8, 1.6])"""

block2_new = """                if scale_option == "1-3-5 Discrete":
                    left_cols = ["5", "3"]
                    right_cols = ["3", "5"]
                    options = [-5, -3, 1, 3, 5]
                elif scale_option == "1-3-7-9 Discrete":
                    left_cols = ["9", "7", "3"]
                    right_cols = ["3", "7", "9"]
                    options = [-9, -7, -3, 1, 3, 7, 9]
                else: # 1-9 Continuous (Default)
                    left_cols = ["9", "8", "7", "6", "5", "4", "3", "2"]
                    right_cols = ["2", "3", "4", "5", "6", "7", "8", "9"]
                    options = list(range(-9, -1)) + list(range(1, 10))
                    options = sorted(list(set(options))) # -9 ~ -2, 1, 2 ~ 9

                # 헤더 및 척도 너비 동적 계산
                header_cells = left_cols + ["1"] + right_cols
                total_scale_count = len(header_cells)
                scale_width = 70.0 / total_scale_count
                left_width = scale_width * len(left_cols)
                right_width = scale_width * len(right_cols)

                # 미리보기 화면에도 수직 정렬 CSS 주입
                st.markdown(
                    f\"\"\"
                    <style>
                    div[data-testid="stHorizontalBlock"] {{
                        gap: 0px !important;
                    }}
                    div[data-testid="column"] {{
                        padding: 0px !important;
                    }}
                    div[data-testid="stRadio"] {{
                        width: 100% !important;
                    }}
                    div[role="radiogroup"] {{
                        display: flex !important;
                        flex-direction: row !important;
                        justify-content: space-between !important;
                        width: 100% !important;
                        gap: 0px !important;
                        padding: 0px !important;
                    }}
                    div[role="radiogroup"] > label {{
                        flex: 1 1 0% !important;
                        text-align: center !important;
                        display: flex !important;
                        flex-direction: column !important;
                        align-items: center !important;
                        justify-content: center !important;
                        margin: 0px !important;
                        padding: 0px !important;
                        min-width: 0px !important;
                    }}
                    div[role="radiogroup"] label div[data-testid="stWidgetLabel"],
                    div[role="radiogroup"] label p {{
                        display: none !important;
                        height: 0px !important;
                        margin: 0px !important;
                        padding: 0px !important;
                    }}
                    div[role="radiogroup"] label span {{
                        margin: 0px auto !important;
                        padding: 0px !important;
                    }}
                    </style>
                    \"\"\",
                    unsafe_allow_html=True
                )

                for comb in combinations:
                    parent_lbl = f"[{comb['parent']}] 하위 요인 비교" if comb['type'] == 'sub' else "대분류(핵심) 요인 비교"
                    st.markdown(f"##### 🔍 {parent_lbl}")
                    
                    # HTML 구조를 사용해 깔끔한 메트릭스 표 상단부(헤더) 정의 (미리보기)
                    header_html = f\"\"\"
                    <table style="width:100%; border-collapse: collapse; text-align: center; font-size: 13px; font-family: sans-serif; border: 1px solid #444444; margin-bottom: 10px; table-layout: fixed;">
                        <tr style="background-color: #d1d5db; font-weight: bold; border-bottom: 1px solid #444444;">
                            <th style="width: 15%; border: 1px solid #444444; padding: 8px;" rowspan="2">항목</th>
                            <th style="width: {left_width}%; border: 1px solid #444444; padding: 4px;" colspan="{len(left_cols)}">◀ 좌측 항목이 더 중요</th>
                            <th style="width: {scale_width}%; border: 1px solid #444444; padding: 4px; background-color: #cbd5e1;" rowspan="2">동일<br>(1)</th>
                            <th style="width: {right_width}%; border: 1px solid #444444; padding: 4px;" colspan="{len(right_cols)}">우측 항목이 더 중요 ▶</th>
                            <th style="width: 15%; border: 1px solid #444444; padding: 8px;" rowspan="2">항목</th>
                        </tr>
                        <tr style="background-color: #e5e7eb; font-weight: bold; border-bottom: 2px solid #444444;">
                            {"".join([f"<td style='border: 1px solid #444444; padding: 6px 0;'>{val}</td>" for val in left_cols])}
                            {"".join([f"<td style='border: 1px solid #444444; padding: 6px 0;'>{val}</td>" for val in right_cols])}
                        </tr>
                    </table>
                    \"\"\"
                    st.markdown(header_html, unsafe_allow_html=True)
                    st.write("")
                    
                    for left_f, right_f in comb["pairs"]:
                        pair_key = f"{left_f}_{right_f}"
                        row_cols = st.columns([15, 70, 15])"""

if block1_old in content:
    content = content.replace(block1_old, block1_new)
    print("Block 1 replaced successfully.")
else:
    print("Block 1 old text not found.")

if block2_old in content:
    content = content.replace(block2_old, block2_new)
    print("Block 2 replaced successfully.")
else:
    print("Block 2 old text not found.")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

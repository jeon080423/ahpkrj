import sys
import re

file_path = "f:/app/4. AHP마스터/app.py"
with open(file_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

# 1. Update Global CSS
new_css = """global_ahp_css = \"\"\"
<style>
/* =============================================================================
   AHP 척도 전용 고유 클래스 타겟팅 (.st-key-ahp_survey_matrix)
   ============================================================================= */

/* 1. 수직 정렬 & 레이아웃 배분 */
.st-key-ahp_survey_matrix div[data-testid="stHorizontalBlock"] {
    gap: 0px !important;
    align-items: center !important;
    width: 100% !important;
}

.st-key-ahp_survey_matrix div[data-testid="column"] {
    padding: 0px !important;
}

/* 2. 라디오 그룹 전체 100% 분배 강제 및 줄바꿈 원천 차단 */
.st-key-ahp_survey_matrix div[data-testid="stRadio"],
.st-key-ahp_survey_matrix .stRadio {
    width: 100% !important;
}

.st-key-ahp_survey_matrix div[data-testid="stRadio"] > div,
.st-key-ahp_survey_matrix div[role="radiogroup"] {
    display: flex !important;
    flex-direction: row !important;
    flex-wrap: nowrap !important; /* 핵심: 모달에서도 절대 줄바꿈 되지 않음 */
    justify-content: space-between !important;
    align-items: center !important;
    width: 100% !important;
    gap: 0px !important;
    padding: 0px !important; 
    margin: 0px !important;
}

/* 3. 각 척도 라디오 버튼 1:1 완벽 정렬 */
.st-key-ahp_survey_matrix label {
    flex: 1 1 0% !important;
    display: flex !important;
    flex-direction: column !important;
    align-items: center !important;
    justify-content: center !important;
    height: 44px !important;
    margin: 0px !important;
    padding: 0px !important;
    min-width: 0px !important;
    border-radius: 4px !important;
    transition: background-color 0.2s ease-in-out !important;
    background-color: transparent !important;
}

/* 4. 기존 텍스트 찌꺼기 완벽 제거 */
.st-key-ahp_survey_matrix label div[data-testid="stWidgetLabel"],
.st-key-ahp_survey_matrix label p {
    display: none !important;
    height: 0px !important;
    width: 0px !important;
    margin: 0px !important;
    padding: 0px !important;
    opacity: 0 !important;
    overflow: hidden !important;
    position: absolute !important;
}

/* 동그라미 컨테이너 중앙 정렬 */
.st-key-ahp_survey_matrix label span {
    margin: 0px auto !important;
    padding: 0px !important;
}

/* 5. Hover 및 Zebra 효과 */
.st-key-ahp_survey_matrix label:hover {
    background-color: #e2e8f0 !important;
    cursor: pointer !important;
}

.st-key-ahp_survey_matrix div[data-testid="stHorizontalBlock"]:hover {
    background-color: #fafafa !important; 
}

/* 6. 모바일 가로 스크롤 허용 및 붕괴 방지 */
@media (max-width: 768px) {
    .stApp > header + div, 
    .block-container,
    div[data-testid="stDialog"] {
        overflow-x: auto !important;
        -webkit-overflow-scrolling: touch;
    }
    .st-key-ahp_survey_matrix div[data-testid="stHorizontalBlock"] {
        flex-wrap: nowrap !important;
        min-width: 750px !important;
    }
    .st-key-ahp_survey_matrix div[data-testid="column"] {
        flex: 0 0 auto !important;
    }
    .st-key-ahp_survey_matrix div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(1),
    .st-key-ahp_survey_matrix div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(3) {
        width: 15% !important; 
    }
    .st-key-ahp_survey_matrix div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(2) {
        width: 70% !important;
    }
}
</style>
\"\"\""""

content = "".join(lines)
# Replace CSS
content = re.sub(r'global_ahp_css = """\n<style>.*?</style>\n"""', new_css, content, flags=re.DOTALL)

# 2. Add st.container and indent Main Survey loop
main_loop_start = """        for comb in combinations:
            parent_lbl = f"[{comb['parent']}] 하위 요인 비교" if comb['type'] == 'sub' else "대분류(핵심) 요인 비교"
            st.markdown(f"#### 🔍 {parent_lbl}")"""
            
main_loop_replacement = """        with st.container(key="ahp_survey_matrix"):
            for comb in combinations:
                parent_lbl = f"[{comb['parent']}] 하위 요인 비교" if comb['type'] == 'sub' else "대분류(핵심) 요인 비교"
                st.markdown(f"#### 🔍 {parent_lbl}")"""

# 3. Add st.container and indent Preview Survey loop
preview_loop_start = """                for comb in combinations:
                    parent_lbl = f"[{comb['parent']}] 하위 요인 비교" if comb['type'] == 'sub' else "대분류(핵심) 요인 비교"
                    st.markdown(f"##### 🔍 {parent_lbl}")"""

preview_loop_replacement = """                with st.container(key="ahp_survey_matrix"):
                    for comb in combinations:
                        parent_lbl = f"[{comb['parent']}] 하위 요인 비교" if comb['type'] == 'sub' else "대분류(핵심) 요인 비교"
                        st.markdown(f"##### 🔍 {parent_lbl}")"""

# Indent blocks carefully using string replace for known blocks
# Actually, since the block sizes are significant, let's use a function to indent the blocks until st.divider()
def wrap_with_container(content_str, marker_str, indent_level):
    idx = content_str.find(marker_str)
    if idx == -1: return content_str
    
    # Find the end of the block, which is the next st.divider() at the same indent_level
    end_marker = " " * indent_level + "st.divider()\n"
    end_idx = content_str.find(end_marker, idx)
    
    if end_idx == -1: return content_str
    
    # Extract the block
    pre = content_str[:idx]
    block = content_str[idx:end_idx]
    post = content_str[end_idx:]
    
    # Add container start
    container_str = " " * indent_level + 'with st.container(key="ahp_survey_matrix"):\n'
    
    # Indent block
    indented_block = ""
    for line in block.splitlines(True):
        if line.strip() == "":
            indented_block += line
        else:
            indented_block += "    " + line
            
    return pre + container_str + indented_block + post

# Main block wrap
content = wrap_with_container(content, '        for comb in combinations:\n            parent_lbl = f"[{comb[\'parent\']}]', 8)

# Preview block wrap
content = wrap_with_container(content, '                for comb in combinations:\n                    parent_lbl = f"[{comb[\'parent\']}]', 16)


with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("CSS updated and st.container wrappers added.")

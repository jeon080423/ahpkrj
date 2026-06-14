import sys

file_path = "f:/app/4. AHP마스터/app.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

target = "st.markdown(seo_tags, unsafe_allow_html=True)"

global_css = """st.markdown(seo_tags, unsafe_allow_html=True)

# =============================================================================
# 전역 AHP 척도 CSS 주입 (메인 화면 및 미리보기 모달 모두에 강제 적용)
# =============================================================================
global_ahp_css = \"\"\"
<style>
/* 1. 수직 정렬 & 레이아웃 배분 */
div[data-testid="stHorizontalBlock"] {
    gap: 0px !important;
    align-items: center !important;
}
div[data-testid="column"] {
    padding: 0px !important;
}

/* 2. 라디오 그룹 전체 100% 분배 강제 */
div[data-testid="stRadio"],
.stRadio {
    width: 100% !important;
}
div[role="radiogroup"] {
    display: flex !important;
    flex-direction: row !important;
    justify-content: space-between !important;
    width: 100% !important;
    gap: 0px !important;
    padding: 0px !important; 
}

/* 3. 각 척도 라디오 버튼 1:1 완벽 정렬 */
div[role="radiogroup"] > label {
    flex: 1 1 0% !important;
    display: flex !important;
    flex-direction: column !important;
    align-items: center !important;
    justify-content: center !important;
    height: 44px !important;
    margin: 0px !important;
    padding: 0px !important;
    min-width: 0px !important;
    border-radius: 4px;
    transition: background-color 0.2s ease-in-out;
}

/* 4. 기존 텍스트 찌꺼기 제거 */
div[role="radiogroup"] label div[data-testid="stWidgetLabel"],
div[role="radiogroup"] label p {
    display: none !important;
    height: 0px !important;
    margin: 0px !important;
    padding: 0px !important;
}
div[role="radiogroup"] label span {
    margin: 0px auto !important;
    padding: 0px !important;
}

/* 5. Hover 및 Zebra 효과 */
div[role="radiogroup"] > label:hover {
    background-color: #e2e8f0 !important;
    cursor: pointer !important;
}
div[data-testid="stHorizontalBlock"]:hover {
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
    div[data-testid="stHorizontalBlock"] {
        flex-wrap: nowrap !important;
        min-width: 750px !important;
    }
    div[data-testid="column"] {
        flex: 0 0 auto !important;
    }
    div[data-testid="column"]:nth-child(1),
    div[data-testid="column"]:nth-child(3) {
        width: 15% !important; 
    }
    div[data-testid="column"]:nth-child(2) {
        width: 70% !important;
    }
}
</style>
\"\"\"
st.markdown(global_ahp_css, unsafe_allow_html=True)
"""

if target in content and "전역 AHP 척도 CSS 주입" not in content:
    content = content.replace(target, global_css, 1)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    print("Global CSS injected successfully.")
else:
    print("Target not found or CSS already injected.")

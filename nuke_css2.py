import sys
import re

file_path = "f:/app/4. AHP마스터/app.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

robust_css = """global_ahp_css = \"\"\"
<style>
/* 1. 수직 정렬 & 레이아웃 배분 (AHP 척도가 포함된 stHorizontalBlock 대상) */
div[data-testid="stHorizontalBlock"]:has(div[data-testid="stRadio"] label:nth-child(5)) {
    gap: 0px !important;
    align-items: center !important;
    width: 100% !important;
}

div[data-testid="stHorizontalBlock"]:has(div[data-testid="stRadio"] label:nth-child(5)) > div[data-testid="column"] {
    padding: 0px !important;
}

/* 2. 라디오 그룹 전체 100% 분배 강제 (옵션이 5개 이상인 라디오 버튼만 타겟) */
div[data-testid="stRadio"]:has(label:nth-child(5)),
div[data-testid="stRadio"]:has(label:nth-child(5)) .stRadio {
    width: 100% !important;
}

div[data-testid="stRadio"]:has(label:nth-child(5)) > div,
div[role="radiogroup"]:has(label:nth-child(5)) {
    display: flex !important;
    flex-direction: row !important;
    justify-content: space-between !important;
    align-items: center !important;
    width: 100% !important;
    gap: 0px !important;
    padding: 0px !important; 
    margin: 0px !important;
}

/* 3. 각 척도 라디오 버튼 1:1 완벽 정렬 */
div[data-testid="stRadio"]:has(label:nth-child(5)) label,
div[role="radiogroup"]:has(label:nth-child(5)) label {
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

/* 4. 기존 텍스트 찌꺼기 완벽 제거 (AHP 척도의 경우 텍스트를 숨김) */
div[data-testid="stRadio"]:has(label:nth-child(5)) label div[data-testid="stWidgetLabel"],
div[data-testid="stRadio"]:has(label:nth-child(5)) label p,
div[role="radiogroup"]:has(label:nth-child(5)) label p {
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
div[data-testid="stRadio"]:has(label:nth-child(5)) label span,
div[role="radiogroup"]:has(label:nth-child(5)) label span {
    margin: 0px auto !important;
    padding: 0px !important;
}

/* 5. Hover 및 Zebra 효과 */
div[data-testid="stRadio"]:has(label:nth-child(5)) label:hover,
div[role="radiogroup"]:has(label:nth-child(5)) label:hover {
    background-color: #e2e8f0 !important;
    cursor: pointer !important;
}

div[data-testid="stHorizontalBlock"]:has(div[data-testid="stRadio"] label:nth-child(5)):hover {
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
    div[data-testid="stHorizontalBlock"]:has(div[data-testid="stRadio"] label:nth-child(5)) {
        flex-wrap: nowrap !important;
        min-width: 750px !important;
    }
    div[data-testid="column"] {
        flex: 0 0 auto !important;
    }
    div[data-testid="stHorizontalBlock"]:has(div[data-testid="stRadio"] label:nth-child(5)) > div[data-testid="column"]:nth-child(1),
    div[data-testid="stHorizontalBlock"]:has(div[data-testid="stRadio"] label:nth-child(5)) > div[data-testid="column"]:nth-child(3) {
        width: 15% !important; 
    }
    div[data-testid="stHorizontalBlock"]:has(div[data-testid="stRadio"] label:nth-child(5)) > div[data-testid="column"]:nth-child(2) {
        width: 70% !important;
    }
}
</style>
\"\"\""""

# Update global css block
content = re.sub(r'global_ahp_css = """\n<style>.*?</style>\n"""', robust_css, content, flags=re.DOTALL)

# Update personal info radio text
content = content.replace('["동의함", "동의하지 않음"]', '["동의", "비동의"]')

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Robust global CSS injected and personal info labels updated.")

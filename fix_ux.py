import sys

file_path = "f:/app/4. AHP마스터/app.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

target = """                /* 동그라미 라디오 버튼 정중앙 배치 */
                div[role="radiogroup"] label span {{
                    margin: 0px auto !important;
                    padding: 0px !important;
                }}
                </style>"""

replacement = """                /* 동그라미 라디오 버튼 정중앙 배치 */
                div[role="radiogroup"] label span {{
                    margin: 0px auto !important;
                    padding: 0px !important;
                }}

                /* =========================================================
                   2. 응답 편의성 및 가독성 강화 (Hover & Zebra Striping)
                   ========================================================= */
                div[role="radiogroup"] > label:hover {{
                    background-color: #e2e8f0 !important;
                    cursor: pointer !important;
                }}
                div[data-testid="stHorizontalBlock"]:hover {{
                    background-color: #fafafa !important; 
                }}

                /* =========================================================
                   3. 모바일 반응형 웹 대응 (세로 붕괴 방지 및 가로 스크롤)
                   ========================================================= */
                @media (max-width: 768px) {{
                    .stApp > header + div, 
                    .block-container {{
                        overflow-x: auto !important;
                        -webkit-overflow-scrolling: touch;
                    }}
                    div[data-testid="stHorizontalBlock"] {{
                        flex-wrap: nowrap !important;
                        min-width: 750px !important;
                    }}
                    div[data-testid="column"] {{
                        flex: 0 0 auto !important;
                    }}
                    div[data-testid="column"]:nth-child(1),
                    div[data-testid="column"]:nth-child(3) {{
                        width: 15% !important; 
                    }}
                    div[data-testid="column"]:nth-child(2) {{
                        width: 70% !important;
                    }}
                }}
                </style>"""

if target in content:
    content = content.replace(target, replacement)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    print("UX CSS injected successfully.")
else:
    print("Target CSS not found.")

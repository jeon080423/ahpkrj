import re

with open('survey_manager.py', 'r', encoding='utf-8') as f:
    content = f.read()

target = """    type_headers = ["Type"]
    if demographics and demographics.get("type_questions"):
        tq_count = len(demographics["type_questions"])
        if tq_count > 0:
            type_headers = [f"Type {i+1}" for i in range(tq_count)]"""

replacement = """    type_headers = ["그룹 분류"]
    if demographics and demographics.get("type_questions"):
        tq_list = demographics["type_questions"]
        if len(tq_list) > 0:
            type_headers = [tq.get("q", f"추가 문항 {i}") if i > 0 else tq.get("q", "그룹 분류") for i, tq in enumerate(tq_list)]"""

if target in content:
    content = content.replace(target, replacement)
    with open('survey_manager.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Successfully replaced type_headers in survey_manager.py")
else:
    print("Target not found in survey_manager.py")

import sys
import importlib

with open('g:/AHPkr/app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

insert_idx = 0
for i, line in enumerate(lines):
    if line.startswith('import streamlit as st'):
        insert_idx = i + 1
        break

lines.insert(insert_idx, "import importlib\nimport survey_manager\nimportlib.reload(survey_manager)\ntry:\n    import survey_manager_v3\n    importlib.reload(survey_manager_v3)\nexcept:\n    pass\n")

with open('g:/AHPkr/app.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

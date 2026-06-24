import sqlite3
import json
from survey_manager import load_survey_metadata, create_survey_sheet

ahp_model = {
    "main": ["A", "B", "C"],
    "subs": {
        "A": ["A1", "A2", "A3"],
        "B": ["B1", "B2"],
        "C": ["C1", "C2", "C3"]
    },
    "sub_subs": {
        "A1": ["A1a", "A1b"]
    }
}

# Just print out the logic that creates the sheets to verify it looks correct
main_criteria = ahp_model.get("main", [])
main_pairs = []
for i in range(len(main_criteria)):
    for j in range(i + 1, len(main_criteria)):
        main_pairs.append(f"{main_criteria[i]}_{main_criteria[j]}")
print("Main_Criteria headers:", ["ID", "Type"] + main_pairs + ["제출시간"])

sub_criteria_map = ahp_model.get("subs", {})
for main_c in main_criteria:
    subs = sub_criteria_map.get(main_c, [])
    if len(subs) >= 2:
        sub_pairs = []
        for i in range(len(subs)):
            for j in range(i + 1, len(subs)):
                sub_pairs.append(f"{subs[i]}_{subs[j]}")
        print(f"Sheet '{str(main_c)[:31]}' headers:", ["ID", "Type"] + sub_pairs + ["제출시간"])

sub_sub_map = ahp_model.get("sub_subs", {})
for main_c, subs in sub_criteria_map.items():
    for sub_c in subs:
        sub_subs = sub_sub_map.get(sub_c, [])
        if len(sub_subs) >= 2:
            ss_pairs = []
            for i in range(len(sub_subs)):
                for j in range(i + 1, len(sub_subs)):
                    ss_pairs.append(f"{sub_subs[i]}_{sub_subs[j]}")
            print(f"Sheet '{str(sub_c)[:31]}' headers:", ["ID", "Type"] + ss_pairs + ["제출시간"])

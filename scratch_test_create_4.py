import sys
import importlib
import survey_manager
importlib.reload(survey_manager)
from survey_manager import create_survey_sheet

ahp_model = {
    "main": ["A", "B", "C"],
    "subs": {"A": ["A1", "A2"], "B": ["B1", "B2"], "C": ["C1", "C2"]}
}

try:
    sheet_id = create_survey_sheet(
        title="Test Auto Creation",
        description="test",
        admin_email="test@example.com",
        ahp_model=ahp_model,
        scale_type=9,
        demographics={"name": True},
        definition_map={},
        cr_limit=0.1,
        rewards_info={"enabled": False}
    )
    print(f"Created successfully. Sheet ID: {sheet_id}")
    
    from survey_manager import get_survey_gspread_client
    client = get_survey_gspread_client()
    sh = client.open_by_key(sheet_id)
    print("Worksheets:")
    for ws in sh.worksheets():
        print(ws.title)
        
except Exception as e:
    import traceback
    traceback.print_exc()

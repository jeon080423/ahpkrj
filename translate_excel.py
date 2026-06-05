import pandas as pd

file_path = r"F:\SD카드 백업\Ahp\19. AHP마스터 셈플데이터\AHP_Master_Template.xlsx"
out_path = r"F:\SD카드 백업\Ahp\19. AHP마스터 셈플데이터\AHP_Master_Template_EN.xlsx"

translation_dict = {
    # Main Criteria
    "재생 에너지": "Renewable Energy",
    "에너지 효율화": "Energy Efficiency",
    "온실가스 흡수": "GHG Absorption",
    
    # Sub Criteria
    "태양광 발전": "Solar Power",
    "풍력 발전": "Wind Power",
    "지열 발전": "Geothermal Power",
    "바이오메스": "Biomass",
    
    "산업/건물에너지 효율화": "Industry_Building Energy Efficiency",
    "스마트 시티 건설": "Smart City Construction",
    "친환경 차량 확대": "Eco-friendly Vehicle Expansion",
    "폐기물 자원순환": "Waste Resource Circulation",
    
    "조림 및 재조림": "Afforestation and Reforestation",
    "바이오차(CAR) 생산": "Biochar Production",
    "산림 파괴 방지": "Deforestation Prevention",
    "해양및연안 온실가스 흡수": "Marine and Coastal GHG Absorption",
    
    # Values
    "한국": "Korea"
}

def translate_text(text):
    if not isinstance(text, str):
        return text
    
    # Exact match
    if text in translation_dict:
        return translation_dict[text]
    
    # Underscore separated columns (e.g., A_B)
    if '_' in text:
        parts = text.split('_')
        translated_parts = [translation_dict.get(p.strip(), p.strip()) for p in parts]
        return '_'.join(translated_parts)
        
    return text

xls = pd.ExcelFile(file_path)

with pd.ExcelWriter(out_path, engine='openpyxl') as writer:
    for sheet_name in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=sheet_name)
        
        # Translate column names
        df.columns = [translate_text(col) for col in df.columns]
        
        # Translate 'Type' column values if exists
        if 'Type' in df.columns:
            df['Type'] = df['Type'].apply(lambda x: translate_text(x))
            
        # Translate sheet name
        new_sheet_name = translate_text(sheet_name)
        # Sheet names must be <= 31 chars in Excel
        new_sheet_name = new_sheet_name[:31]
        
        df.to_excel(writer, sheet_name=new_sheet_name, index=False)

print(f"Successfully translated and saved to: {out_path}")

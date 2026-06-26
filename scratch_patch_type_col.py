import re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Excel upload df_main fix
target1 = """                    df_main = pd.read_excel(uploaded_file, sheet_name=sheet_names[0])
                    
                    # 3계층 식별 로직"""

replacement1 = """                    df_main = pd.read_excel(uploaded_file, sheet_name=sheet_names[0])
                    
                    if "Type" not in df_main.columns and len(df_main.columns) > 1:
                        col1 = df_main.columns[1]
                        if "_" not in col1 and col1 not in ["ID", "제출시간"]:
                            df_main.rename(columns={col1: "Type"}, inplace=True)
                            
                    # 3계층 식별 로직"""

# 2. Excel upload df_sheet fix
target2 = """                    for sn in sheet_names[1:]:
                        df_sheet = pd.read_excel(uploaded_file, sheet_name=sn)
                        # 안전한 시트명(safe_sheet_name)을 위해 앞부분이 일치하는지 확인"""

replacement2 = """                    for sn in sheet_names[1:]:
                        df_sheet = pd.read_excel(uploaded_file, sheet_name=sn)
                        if "Type" not in df_sheet.columns and len(df_sheet.columns) > 1:
                            col1 = df_sheet.columns[1]
                            if "_" not in col1 and col1 not in ["ID", "제출시간"]:
                                df_sheet.rename(columns={col1: "Type"}, inplace=True)
                                
                        # 안전한 시트명(safe_sheet_name)을 위해 앞부분이 일치하는지 확인"""

# 3. Online survey raw_df fix
target3 = """                                        raw_df = pd.DataFrame(rows, columns=headers)
                                        
                                        # [신규] 사용자 등급에 따른 표본 수 제한"""

replacement3 = """                                        raw_df = pd.DataFrame(rows, columns=headers)
                                        
                                        if "Type" not in raw_df.columns and len(raw_df.columns) > 1:
                                            col1 = raw_df.columns[1]
                                            if "_" not in col1 and col1 not in ["ID", "제출시간"]:
                                                raw_df.rename(columns={col1: "Type"}, inplace=True)
                                                
                                        # [신규] 사용자 등급에 따른 표본 수 제한"""

if target1 in content and target2 in content and target3 in content:
    content = content.replace(target1, replacement1)
    content = content.replace(target2, replacement2)
    content = content.replace(target3, replacement3)
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Successfully replaced all targets in app.py")
else:
    if target1 not in content: print("Target 1 not found")
    if target2 not in content: print("Target 2 not found")
    if target3 not in content: print("Target 3 not found")

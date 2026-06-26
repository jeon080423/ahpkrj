import sys

target_file = "app.py"
content = open(target_file, "r", encoding="utf-8").read()

start_idx = content.find('    resp_data = {}')
end_idx = content.find('    # 연령: 개방형 vs 10세 단위 선택형')

if start_idx == -1 or end_idx == -1:
    print("Could not find start or end block")
    sys.exit(1)

old_block = content[start_idx:end_idx]

new_block = """    resp_data = {}
    
    # 아이디는 응답자에게 제시하지 말고 임의로 무작위 자동 부여
    if "survey_resp_uuid" not in st.session_state:
        import uuid
        st.session_state.survey_resp_uuid = str(uuid.uuid4())[:8]
    resp_data["id"] = st.session_state.survey_resp_uuid
    
    sq_idx = 1
    
    # 성명
    if demographics.get("name"):
        name_label = f"SQ{sq_idx}. " + _("성명 *", "Name *")
        sq_idx += 1
        resp_data["name"] = st.text_input(name_label, key="survey_resp_name")
    
    # 그룹 분류는 설계자가 설정한 문항과 보기를 적용
    type_questions_data = demographics.get("type_questions")
    resp_data["types"] = []
    
    if type_questions_data and isinstance(type_questions_data, list):
        for i, tq in enumerate(type_questions_data):
            tq_q = tq.get("q", tq.get("question", ""))
            tq_opts = tq.get("opts", [])
            if not tq_q or tq_q == "귀하의 소속은 어떻게 되십니까?":
                tq_q = _("귀하의 소속은 어떻게 되십니까?", "What is your affiliation?")
            
            if not isinstance(tq_opts, list) or not tq_opts or tq_opts == ["전문가", "일반", "공무원", "기타"]:
                if "opts" not in tq: # it was added via UI as short answer text
                    tq_opts = []
                else:
                    tq_opts = [_("전문가", "Expert"), _("일반", "General"), _("공무원", "Public Official"), _("기타", "Other")]
            
            if tq_opts:
                tq_opts = [translate_factor_if_default(opt) for opt in tq_opts]
                ans = st.radio(f"SQ{sq_idx}. {tq_q}", tq_opts, index=0, key=f"survey_resp_type_{i}", horizontal=True)
            else:
                ans = st.text_input(f"SQ{sq_idx}. {tq_q}", key=f"survey_resp_type_{i}")
            resp_data["types"].append(ans)
            sq_idx += 1
    else:
        # 역방향 호환성
        type_q = demographics.get("type_question", "")
        if not type_q or type_q == "귀하의 소속은 어떻게 되십니까?":
            type_q = _("귀하의 소속은 어떻게 되십니까?", "What is your affiliation?")
        
        type_opts = demographics.get("type_options", [])
        if not isinstance(type_opts, list) or not type_opts or type_opts == ["전문가", "일반", "공무원", "기타"]:
            type_opts = [_("전문가", "Expert"), _("일반", "General"), _("공무원", "Public Official"), _("기타", "Other")]
        else:
            type_opts = [translate_factor_if_default(opt) for opt in type_opts]
            
        ans = st.radio(f"SQ{sq_idx}. {type_q}", type_opts, index=0, key="survey_resp_type", horizontal=True)
        resp_data["types"].append(ans)
        sq_idx += 1
        
    # 기존 코드와의 호환성을 위해 type 속성도 유지
    if resp_data["types"]:
        resp_data["type"] = resp_data["types"][0]
    

    
"""

content = content.replace(old_block, new_block)
with open(target_file, "w", encoding="utf-8") as f:
    f.write(content)
print("Successfully patched app.py")

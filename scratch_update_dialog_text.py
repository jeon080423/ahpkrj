import re

with open('f:/app/4. AHP마스터/app.py', 'r', encoding='utf-8') as f:
    content = f.read()

target = """            @st.dialog("⚠️ 기존 설문 삭제 및 새 설문 작성 안내")
            def confirm_new_survey():
                st.warning("새로운 설문을 작성하시면 기존 구글 시트에 저장된 **설문 구조 및 수집된 응답자 데이터 전체**가 영구적으로 삭제됩니다.\\n\\n이 작업은 취소할 수 없습니다.")
                agree = st.checkbox("네, 모든 기존 데이터가 삭제된다는 것을 이해하며 새 설문 작성에 동의합니다.")"""

replacement = """            @st.dialog("🚨 [경고] 기존 설문 영구 삭제 안내")
            def confirm_new_survey():
                st.error("새로운 설문을 작성하시면 기존 연동된 구글 시트에 저장된 **모든 데이터(설문 구조, 문항, 수집된 전체 응답 결과)가 즉시 삭제되며 절대 복구할 수 없습니다.**")
                st.info("💡 **데이터 보존 안내:** 기존 설문의 응답 결과 보존을 원하신다면, 삭제에 동의하시기 전에 구글 스프레드시트에 접속하여 **[파일] -> [다운로드]** 메뉴를 통해 엑셀(.xlsx) 파일 등으로 백업본을 사용자 컴퓨터에 미리 다운로드해 두시기 바랍니다.")
                agree = st.checkbox("네, 기존 데이터 백업을 완료했거나 불필요하며, 모든 데이터 삭제에 동의합니다.")"""

if target in content:
    new_content = content.replace(target, replacement)
    with open('f:/app/4. AHP마스터/app.py', 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("Replaced dialog text successfully.")
else:
    print("Target dialog text not found.")

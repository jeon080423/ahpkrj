import io
content = io.open('app.py', 'r', encoding='utf-8').read()
content = content.replace('with st.form("respondent_survey_form"):', 'with st.container():')
content = content.replace('submit_btn = st.form_submit_button(_("답변 제출하기", "Submit Survey"), type="primary")', 'submit_btn = st.button(_("답변 제출하기", "Submit Survey"), type="primary")')
io.open('app.py', 'w', encoding='utf-8').write(content)

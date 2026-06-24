import io
content = io.open('app.py', 'r', encoding='utf-8').read()
content = content.replace("st.caption(f\"<div style='color: red; font-size: 10px;'>{debug_text}</div>\", unsafe_allow_html=True)", "")
io.open('app.py', 'w', encoding='utf-8').write(content)

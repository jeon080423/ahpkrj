import streamlit as st
import importlib
import sys

# 1. Page Config (Must be called as the very first Streamlit command)
try:
    from PIL import Image
    import os
    if os.path.exists("favicon.png"):
        favicon = Image.open("favicon.png")
    else:
        favicon = "📊"
    st.set_page_config(
        page_title="AHP Master Portal",
        layout="wide",
        page_icon=favicon
    )
except Exception:
    pass

# 2. Re-resolve language settings
if 'lang' not in st.session_state:
    try:
        _init_lang = st.query_params.get("lang", "ko")
        if isinstance(_init_lang, list): _init_lang = _init_lang[0]
        st.session_state.lang = _init_lang.lower()
    except:
        st.session_state.lang = 'ko'

def _(ko_text, en_text):
    if st.session_state.get('lang', 'ko') == 'en':
        return en_text
    return ko_text

# 3. Handle query parameters and session state for routing
if "mode" in st.query_params:
    st.session_state.mode = st.query_params.get("mode")

# If the mode is set in session state but not in query params, update query params
if st.session_state.get("mode") and "mode" not in st.query_params:
    st.query_params["mode"] = st.session_state.mode

mode = st.session_state.get("mode")

# 4. Route to standard_app or yeta_app
if mode == "yeta":
    import yeta_app
    importlib.reload(yeta_app)
else:
    import standard_app
    importlib.reload(standard_app)

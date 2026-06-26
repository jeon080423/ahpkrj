import streamlit as st

@st.dialog("Test Dialog")
def show_dialog():
    st.write("This is a dialog")
    if st.button("Close"):
        st.rerun()
        
print("Streamlit has dialog:", hasattr(st, 'dialog'))
print("Streamlit has experimental_dialog:", hasattr(st, 'experimental_dialog'))

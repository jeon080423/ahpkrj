import os
import streamlit.components.v1 as components

_RELEASE = True

if not _RELEASE:
    _component_func = components.declare_component(
        "custom_quill",
        url="http://localhost:3001",
    )
else:
    parent_dir = os.path.dirname(os.path.abspath(__file__))
    _component_func = components.declare_component("custom_quill", path=parent_dir)

def st_quill(value="", key=None, html=False):
    component_value = _component_func(value=value, key=key, default=value)
    return component_value

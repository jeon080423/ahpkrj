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
    """
    Quill WYSIWYG 리치 텍스트 편집기 Custom Component
    """
    if value is None:
        value = ""
        
    component_value = _component_func(value=value, key=key, default=value)
    if component_value is None:
        return value
    return component_value

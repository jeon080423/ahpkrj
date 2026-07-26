import streamlit as st
import re

def st_quill(value="", key=None, html=False):
    """
    Streamlit Cloud 환경에서 iframe 기반 Custom Component(Quill 등)가
    CORS/CSP 차단 및 0px 높이 렌더링 문제로 백지로 표시되는 현상을 완전히 해결하기 위해,
    100% 네이티브 Streamlit 위젯 기반의 마크다운/텍스트 편집기(Live Preview 지원)로 동작합니다.
    """
    if key is None:
        key = "default_native_quill_editor"
        
    textarea_key = f"{key}_input_textarea"
    last_val_key = f"{key}_last_param_val"
    
    # 외부에서 value가 강제로 변경된 경우(예: 저장된 설문 불러오기, 초기화 등), 세션 상태 동기화
    if last_val_key not in st.session_state or st.session_state[last_val_key] != value:
        st.session_state[last_val_key] = value
        st.session_state[textarea_key] = value if value is not None else ""
    
    # 편집기 컨테이너 스타일링
    st.markdown("""
    <style>
    .editor-tip-box {
        background-color: #f8fafc;
        border: 1px solid #cbd5e1;
        border-left: 4px solid #3b82f6;
        border-radius: 6px;
        padding: 10px 14px;
        font-size: 0.88rem;
        color: #334155;
        margin-bottom: 12px;
        line-height: 1.5;
    }
    .preview-card {
        background-color: #ffffff;
        border: 1px solid #cbd5e1;
        border-radius: 8px;
        padding: 24px;
        font-size: 0.95rem;
        line-height: 1.6;
        color: #1e293b;
        white-space: pre-wrap;
        min-height: 180px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    </style>
    """, unsafe_allow_html=True)
    
    tab_edit, tab_preview = st.tabs(["✏️ 안내문 편집기 (Editor)", "👁️ 실시간 미리보기 (Live Preview)"])
    
    with tab_edit:
        st.markdown(
            '<div class="editor-tip-box">'
            '💡 <b>서식 안내:</b> 텍스트 내에 <code>**굵게**</code> (Bold), <code>__밑줄__</code> (Underline), '
            '<code>- 목록</code> 등을 입력하시면 응답자 화면 및 실시간 미리보기에서 서식으로 아름답게 렌더링됩니다.'
            '</div>', 
            unsafe_allow_html=True
        )
        
        current_text = st.text_area(
            label="안내문 내용 입력",
            value=st.session_state[textarea_key],
            height=260,
            key=textarea_key,
            label_visibility="collapsed",
            placeholder="여기에 설문 조사 목적 및 안내문을 작성하세요..."
        )
        # 사용자가 수정한 값을 tracking key에도 동기화
        st.session_state[last_val_key] = current_text
        
    with tab_preview:
        preview_text = current_text if current_text else ""
        preview_text_formatted = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', preview_text)
        preview_text_formatted = re.sub(r'__(.*?)__', r'<u>\1</u>', preview_text_formatted)
        
        if not preview_text_formatted.strip():
            st.info("✏️ 편집기 탭에서 안내문 내용을 작성하시면 여기에 실시간으로 미리보기가 표시됩니다.")
        else:
            st.markdown(f'<div class="preview-card">{preview_text_formatted}</div>', unsafe_allow_html=True)
            
    return current_text

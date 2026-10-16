"""
project_manager.py — 프로젝트(설문) 생성·목록·전환·삭제 관리 모듈

기존 "새 설문 작성하기"는 연동된 시트를 덮어쓰는 방식이라
기존 프로젝트가 삭제되는 문제가 있었다.
이 모듈은 새 Google Sheet를 별도로 생성하여
기존 프로젝트를 유지한 채 추가 프로젝트를 만드는 흐름을 제공한다.

standard_app.py에서 가볍게 import하여 사용한다.
"""
import streamlit as st
from ui_style import section_title, hint


def get_my_projects(admin_id):
    """현재 관리자의 프로젝트 목록을 반환한다. [(survey_id, title, created_at), ...]
    survey_id 기준 중복 제거."""
    try:
        from survey_manager import get_admin_surveys_from_gsheet
        raw = get_admin_surveys_from_gsheet(admin_id) or []
        seen = set()
        unique = []
        for sid, title, created_at in raw:
            if sid not in seen:
                seen.add(sid)
                unique.append((sid, title, created_at))
        return unique
    except Exception:
        return []


def render_project_manager():
    """프로젝트 관리 영역 UI를 렌더링한다."""
    user_id = st.session_state.get("user_id")
    if not user_id:
        st.warning("로그인이 필요합니다.")
        return

    section_title("프로젝트 관리", "📁")

    projects = get_my_projects(user_id)

    # ---- 프로젝트 목록 ----
    with st.container(border=True):
        section_title(f"내 프로젝트 ({len(projects)}개)")
        if not projects:
            hint("생성된 프로젝트가 없습니다. 아래에서 새 프로젝트를 만드세요.")
        else:
            for sid, title, created_at in projects:
                c1, c2, c3 = st.columns([3, 2, 1])
                with c1:
                    st.write(f"📋 {title}")
                with c2:
                    st.caption(created_at)
                with c3:
                    if st.button("🗑️", key=f"pm_del_{sid}", help="이 프로젝트 삭제"):
                        st.session_state[f"pm_confirm_del_{sid}"] = True
                # 삭제 확인
                if st.session_state.get(f"pm_confirm_del_{sid}"):
                    st.warning(f"'{title}' 프로젝트를 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다.")
                    dc1, dc2 = st.columns(2)
                    with dc1:
                        if st.button("삭제 확정", key=f"pm_del_yes_{sid}", type="primary"):
                            _delete_project(sid, user_id)
                            st.session_state.pop(f"pm_confirm_del_{sid}", None)
                            st.rerun()
                    with dc2:
                        if st.button("취소", key=f"pm_del_no_{sid}"):
                            st.session_state.pop(f"pm_confirm_del_{sid}", None)
                            st.rerun()

    st.divider()

    # ---- 새 프로젝트 생성 ----
    with st.container(border=True):
        section_title("새 프로젝트 만들기", "➕")
        hint("기존 프로젝트는 그대로 유지됩니다.")
        new_title = st.text_input("프로젝트 이름", key="pm_new_title",
                                  placeholder="예: 2026년 고객만족도 조사")
        if st.button("새 프로젝트 생성", key="pm_create",
                     type="primary", use_container_width=True):
            if not new_title or not new_title.strip():
                st.error("프로젝트 이름을 입력하세요.")
            else:
                _create_new_project(new_title.strip(), user_id)


def _create_new_project(title, admin_id):
    """기존 프로젝트를 건드리지 않고 새 Google Sheet로 프로젝트를 생성한다."""
    try:
        from survey_manager import (
            create_survey_sheet, save_admin_survey_to_gsheet,
        )
        with st.spinner("새 프로젝트를 생성하는 중..."):
            # 최소 기본값으로 빈 설문 시트 생성 (상세 설정은 설문 작성 탭에서)
            result = create_survey_sheet(
                title=title,
                admin_email=admin_id,
                ahp_model={"name": title, "factors": [], "sub_factors": {}},
                scale_type="9점",
                demographics=[],
                definition_map={},
                cr_limit=0.1,
                cr_guide_method="auto",
                rewards_info={},
                description="",
                existing_sheet_id=None,  # 새 시트 생성
                user_id=admin_id,
            )
            new_sheet_id = result.get("spreadsheet_id") if isinstance(result, dict) else None
            if not new_sheet_id and isinstance(result, str):
                new_sheet_id = result

            if new_sheet_id:
                save_admin_survey_to_gsheet(new_sheet_id, title, admin_id)
                st.success(f"✅ '{title}' 프로젝트가 생성되었습니다.")
                st.info("설문 문항 설정은 '설문 작성 및 배포' 탭에서 진행하세요.")
            else:
                st.error("프로젝트 생성에 실패했습니다. (시트 ID를 받지 못함)")
    except Exception as e:
        st.error(f"프로젝트 생성 실패: {e}")


def _delete_project(survey_id, admin_id):
    """프로젝트를 관리자 목록에서 제거한다. (시트 자체는 Google Drive에 남음)"""
    try:
        from survey_manager import delete_admin_survey
        ok = delete_admin_survey(survey_id, admin_id)
        if ok:
            st.success("프로젝트가 삭제되었습니다.")
        else:
            st.error("프로젝트 삭제에 실패했습니다.")
    except Exception as e:
        st.error(f"프로젝트 삭제 실패: {e}")

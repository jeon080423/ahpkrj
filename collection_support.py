# -*- coding: utf-8 -*-
"""응답 수집 지원 UI (1단계)
- 배포 완료 화면: 목표/마감일 설정, QR 코드, 초대·리마인드 문구
- 현황판: 진행률, 남은 일수, 상태별 다음 행동 카드
- 분석 준비 리포트 진입
"""
import datetime
import io

import streamlit as st


# ----------------------------------------------------------------------------
# 문구 템플릿
# ----------------------------------------------------------------------------
def _invite_templates(survey_title, survey_url):
    return {
        "이메일": (
            f"[설문 참여 요청] {survey_title}\n\n"
            f"안녕하십니까.\n"
            f"아래 설문에 참여해 주시면 연구에 큰 도움이 됩니다. "
            f"소요 시간은 약 5~10분이며, 응답 내용은 통계 분석 목적으로만 사용됩니다.\n\n"
            f"▶ 설문 링크: {survey_url}\n\n"
            f"바쁘신 와중에도 참여해 주셔서 감사합니다."
        ),
        "카카오톡": (
            f"[설문 참여 부탁드려요!]\n"
            f"{survey_title}\n\n"
            f"5~10분이면 끝나는 간단한 설문입니다. "
            f"아래 링크를 눌러 참여해 주세요!\n"
            f"▶ {survey_url}"
        ),
        "문자/메신저": (
            f"[AHP 설문] {survey_title} 참여 요청드립니다. "
            f"약 5~10분 소요됩니다. {survey_url}"
        ),
    }


def _reminder_templates(survey_title, survey_url, deadline_str=""):
    deadline_txt = f" (마감: {deadline_str})" if deadline_str else ""
    return {
        "1차 리마인드": (
            f"[설문 참여 독려] {survey_title}{deadline_txt}\n\n"
            f"안녕하십니까. 지난번 안내드린 설문에 아직 참여하지 않으셨다면 "
            f"아래 링크를 통해 응답해 주시길 부탁드립니다.\n"
            f"▶ 설문 링크: {survey_url}\n\n"
            f"이미 참여해 주신 분들께는 감사드립니다."
        ),
        "2차 리마인드 (마감 임박)": (
            f"[마감 임박] {survey_title}{deadline_txt}\n\n"
            f"설문 응답 마감이 얼마 남지 않았습니다. "
            f"아직 참여하지 않으신 분들의 소중한 의견을 기다립니다.\n"
            f"▶ 설문 링크: {survey_url}"
        ),
    }


def _log_share(sheet_id, channel, action_type):
    """공유 활동 기록 (실패해도 UI를 막지 않음)."""
    try:
        from survey_manager import (
            log_structured_event, get_anonymous_user_id,
            get_anonymous_survey_id, EVENT_SHARE_ACTION,
        )
        raw_uid = st.session_state.get("user_id") or "guest"
        log_structured_event(
            EVENT_SHARE_ACTION,
            anonymous_user_id=get_anonymous_user_id(raw_uid),
            anonymous_survey_id=get_anonymous_survey_id(sheet_id),
            properties={"channel": channel, "action_type": action_type},
        )
    except Exception:
        pass


# ----------------------------------------------------------------------------
# 배포 완료 화면: 응답 수집 시작하기
# ----------------------------------------------------------------------------
def render_collection_kickoff(sheet_id, short_url, survey_title=""):
    """배포 성공 직후 표시되는 '응답 수집 시작하기' 섹션."""
    from survey_manager import (
        log_structured_event, get_anonymous_user_id, get_anonymous_survey_id,
        update_survey_collection_goals, EVENT_SURVEY_DEPLOYED,
    )

    # 배포 이벤트 1회 기록
    deploy_flag = f"_deployed_logged_{sheet_id}"
    if not st.session_state.get(deploy_flag):
        try:
            raw_uid = st.session_state.get("user_id") or "guest"
            log_structured_event(
                EVENT_SURVEY_DEPLOYED,
                anonymous_user_id=get_anonymous_user_id(raw_uid),
                anonymous_survey_id=get_anonymous_survey_id(sheet_id),
                properties={"title": (survey_title or "")[:80]},
            )
        except Exception:
            pass
        st.session_state[deploy_flag] = True

    st.divider()
    st.markdown("### 📢 응답 수집 시작하기")
    st.caption("목표를 설정하고, 아래 도구를 복사해 응답자에게 전달하세요. "
               "복사·다운로드 활동은 익명으로 기록되어 수집 현황 분석에 사용됩니다.")

    # ---- 목표/마감일 설정 ----
    with st.container(border=True):
        st.markdown("**🎯 수집 목표 설정**")
        c1, c2, c3 = st.columns([1, 1, 1])
        with c1:
            target_n = st.number_input("목표 응답 수", min_value=0, max_value=100000,
                                       value=0, step=1,
                                       key=f"cs_target_{sheet_id}",
                                       help="0이면 목표 미설정 상태로 유지됩니다.")
        with c2:
            deadline = st.date_input("응답 마감일", value=None,
                                     key=f"cs_deadline_{sheet_id}")
        with c3:
            st.write("")
            st.write("")
            if st.button("💾 목표 저장", key=f"cs_save_{sheet_id}",
                         use_container_width=True):
                res = update_survey_collection_goals(
                    sheet_id,
                    target_count=int(target_n) if target_n else None,
                    deadline=deadline,
                    user_id=st.session_state.get("user_id"),
                )
                if res.get("success"):
                    st.success("수집 목표가 저장되었습니다.")
                    st.session_state.pop(f"_cs_meta_{sheet_id}", None)
                else:
                    st.error(f"저장 실패: {res.get('error')}")

    # ---- QR 코드 ----
    with st.container(border=True):
        st.markdown("**📷 설문 QR 코드**")
        qr_ok = False
        try:
            import qrcode
            qr = qrcode.QRCode(box_size=8, border=2)
            qr.add_data(short_url)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            buf.seek(0)
            qc1, qc2 = st.columns([1, 2])
            with qc1:
                st.image(buf, width=180)
            with qc2:
                st.download_button("⬇️ QR 코드 다운로드 (PNG)",
                                   data=buf.getvalue(),
                                   file_name=f"survey_qr_{sheet_id[:8]}.png",
                                   mime="image/png",
                                   key=f"cs_qr_dl_{sheet_id}")
                if st.button("📋 QR 다운로드 기록하기", key=f"cs_qr_log_{sheet_id}"):
                    _log_share(sheet_id, "qr", "qr_download")
                    st.toast("기록되었습니다.")
            qr_ok = True
        except Exception:
            qr_ok = False
        if not qr_ok:
            st.link_button("↗️ QR 코드 만들기 (qr.naver.com)",
                           "https://qr.naver.com/", use_container_width=False)
            st.caption("QR 라이브러리를 불러오지 못해 외부 생성기로 연결합니다.")

    # ---- 초대 문구 ----
    with st.container(border=True):
        st.markdown("**💬 채널별 초대 문구**")
        tabs = st.tabs(list(_invite_templates(survey_title, short_url).keys()))
        for tab, (ch, text) in zip(tabs, _invite_templates(survey_title, short_url).items()):
            with tab:
                st.code(text, language="text")
                if st.button(f"📋 '{ch}' 문구 사용 기록하기",
                             key=f"cs_invite_{ch}_{sheet_id}"):
                    _log_share(sheet_id, ch, "invite_copy")
                    st.toast("기록되었습니다.")

    # ---- 리마인드 문구 ----
    with st.expander("🔔 리마인드 문구 (1차·2차)", expanded=False):
        deadline_str = ""
        try:
            dl = st.session_state.get(f"cs_deadline_{sheet_id}")
            if dl:
                deadline_str = dl.strftime("%Y-%m-%d")
        except Exception:
            pass
        rtabs = st.tabs(list(_reminder_templates(survey_title, short_url, deadline_str).keys()))
        for tab, (name, text) in zip(rtabs, _reminder_templates(survey_title, short_url, deadline_str).items()):
            with tab:
                st.code(text, language="text")
                if st.button(f"📋 '{name}' 사용 기록하기",
                             key=f"cs_remind_{name}_{sheet_id}"):
                    _log_share(sheet_id, "reminder", name)
                    st.toast("기록되었습니다.")
        st.caption("💡 자동 발송은 개인정보 처리 설계 이후 단계에서 제공될 예정입니다. "
                   "우선 문구를 복사해 직접 발송해 주세요.")


# ----------------------------------------------------------------------------
# 현황판: 진행률·남은 일수·상태별 다음 행동 카드
# ----------------------------------------------------------------------------
def _days_remaining(deadline_str):
    if not deadline_str:
        return None
    try:
        d = datetime.datetime.strptime(deadline_str.strip(), "%Y-%m-%d").date()
        return (d - datetime.date.today()).days
    except Exception:
        return None


def render_collection_progress(sheet_id, survey_meta, completed_count, visit_count=0):
    """대시보드에 진행률/마감일/다음 행동 카드를 표시한다."""
    meta = survey_meta or {}
    try:
        target = int(meta.get("Target_Response_Count") or 0)
    except (ValueError, TypeError):
        target = 0
    deadline_str = str(meta.get("Collection_Deadline") or "").strip()

    st.markdown("### 🎯 수집 진행 현황")
    p1, p2, p3 = st.columns(3)
    with p1:
        if target > 0:
            pct = min(completed_count / target, 1.0)
            st.metric("진행률", f"{completed_count} / {target}명", f"{pct*100:.0f}%")
            st.progress(pct)
        else:
            st.metric("완료 응답", f"{completed_count}명")
            st.caption("목표 응답 수가 설정되지 않았습니다. 배포 화면에서 설정할 수 있습니다.")
    with p2:
        days = _days_remaining(deadline_str)
        if days is None:
            st.metric("마감일", "미설정")
        elif days < 0:
            st.metric("마감일", deadline_str, f"{abs(days)}일 지남", delta_color="inverse")
        elif days == 0:
            st.metric("마감일", deadline_str, "오늘 마감!")
        else:
            st.metric("마감일", deadline_str, f"{days}일 남음")
    with p3:
        rate = (completed_count / visit_count * 100) if visit_count else 0
        st.metric("방문 대비 완료율", f"{rate:.1f}%", f"방문 {visit_count}명")

    # ---- 상태별 다음 행동 카드 ----
    st.markdown("**📌 다음 행동**")
    action_title, action_desc, action_hint = _next_action_card(
        completed_count, visit_count, target, _days_remaining(deadline_str))
    with st.container(border=True):
        st.markdown(f"**{action_title}**")
        st.write(action_desc)
        st.caption(action_hint)


def _next_action_card(completed, visits, target, days_left):
    """계획서의 상태표에 따른 다음 행동 카드 내용."""
    if visits == 0:
        return ("📣 아직 링크 유입이 없습니다",
                "설문 링크가 응답자에게 전달되지 않은 상태입니다. 초대 문구를 복사해 배포 채널에 공유하세요.",
                "배포 화면의 '채널별 초대 문구'를 이용하세요.")
    if completed == 0:
        return ("🔍 시작 장벽을 점검하세요",
                "방문자는 있지만 완료 응답이 없습니다. 설문 첫 화면의 안내 문구와 모바일 가독성을 확인해 보세요.",
                "설문 미리보기로 응답자 화면을 직접 확인해 보세요.")
    if target > 0 and completed < target * 0.5:
        return ("📣 추가 배포가 필요합니다",
                "목표의 50%에 못 미치고 있습니다. 리마인드 문구를 복사해 미응답자에게 독려 메시지를 보내세요.",
                "'리마인드 문구' 탭에서 1차 리마인드를 복사할 수 있습니다.")
    if target > 0 and completed < target * 0.8:
        return ("🚀 목표 달성이 눈앞입니다",
                "조금만 더 모으면 목표에 도달합니다. 마감 전 리마인드를 보내세요.",
                "2차 리마인드(마감 임박) 문구를 활용해 보세요.")
    if target > 0 and completed >= target:
        return ("🎉 목표 달성! 분석을 시작하세요",
                "수집 목표를 달성했습니다. 아래 '분석 준비 리포트'에서 데이터를 확인하고 전체 분석을 시작하세요.",
                "분석 준비 리포트 버튼을 눌러 데이터 품질을 먼저 확인하세요.")
    if days_left is not None and days_left <= 3 and days_left >= 0:
        return ("⏰ 마감이 임박했습니다",
                "마감까지 3일 이하 남았습니다. 리마인드 발송으로 마지막 응답을 모으세요.",
                "2차 리마인드(마감 임박) 문구를 활용해 보세요.")
    return ("📊 순조롭게 수집 중입니다",
            "응답이 꾸준히 모이고 있습니다. 현황을 주기적으로 확인하세요.",
            "실시간 현황 링크를 공동연구자와 공유할 수 있습니다.")


# ----------------------------------------------------------------------------
# 분석 준비 리포트 (1단계: 진입 버튼 + 기본 요약)
# ----------------------------------------------------------------------------
def render_analysis_readiness_entry(sheet_id, completed_count):
    """완료 응답 1건 이상일 때 분석 준비 리포트 진입 버튼을 표시한다."""
    if completed_count < 1:
        return
    from survey_manager import (
        log_structured_event, get_anonymous_user_id, get_anonymous_survey_id,
        EVENT_ANALYSIS_READINESS_VIEWED,
    )
    if st.button("📊 분석 준비 리포트 보기", key=f"cs_readiness_{sheet_id}",
                 type="primary", use_container_width=False):
        st.session_state[f"_readiness_open_{sheet_id}"] = True
        try:
            raw_uid = st.session_state.get("user_id") or "guest"
            log_structured_event(
                EVENT_ANALYSIS_READINESS_VIEWED,
                anonymous_user_id=get_anonymous_user_id(raw_uid),
                anonymous_survey_id=get_anonymous_survey_id(sheet_id),
                properties={"completed": completed_count},
            )
        except Exception:
            pass

    if st.session_state.get(f"_readiness_open_{sheet_id}"):
        with st.container(border=True):
            st.markdown("**📊 분석 준비 리포트 (미리보기)**")
            st.write(f"- 완료 응답 수: **{completed_count}건**")
            st.write("- 무료 분석 범위: 3표본 (온라인 설문 기준)")
            st.info("전체 응답을 반영한 가중치 결과와 보고서 파일은 유료 플랜에서 생성할 수 있습니다. "
                    "아래 '전체 분석 시작' 흐름에서 데이터를 불러오세요.")
            st.caption("※ 2단계에서 CR 충족 현황·유효 응답 수·상위 기준 미리보기가 추가됩니다.")

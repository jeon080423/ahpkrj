"""서비스 계정 Google Drive 정리용 임시 관리자 도구.

주의: 이 모듈은 드라이브 용량 부족 문제를 해결하기 위한 임시 도구이다.
- 등록된 설문(AHPkr_Users)과 연결된 시트는 절대 삭제하지 않는다.
- 삭제는 사용자가 명시적으로 선택한 파일에 한해 2단계 확인 후 수행한다.
"""
import streamlit as st


def _get_drive_service():
    """서비스 계정으로 Google Drive API 서비스를 반환한다."""
    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build

    if "gcp_service_account" not in st.secrets:
        return None, "Secrets에 'gcp_service_account' 설정이 없습니다."

    raw_auth = st.secrets.get("gcp_service_account", {})
    auth_info = dict(raw_auth) if isinstance(raw_auth, dict) or hasattr(raw_auth, "keys") else None
    if not auth_info and isinstance(raw_auth, str):
        import json, base64
        auth_str = raw_auth.strip().strip('"').strip("'")
        try:
            auth_info = json.loads(auth_str)
        except Exception:
            try:
                auth_info = json.loads(base64.b64decode(auth_str).decode("utf-8"))
            except Exception as e:
                return None, f"서비스 계정 키 파싱 실패: {e}"
    if not auth_info:
        return None, "서비스 계정 키 형식을 인식할 수 없습니다."

    try:
        scopes = ["https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(auth_info, scopes=scopes)
        service = build("drive", "v3", credentials=creds, cache_discovery=False)
        return service, None
    except Exception as e:
        return None, f"Drive API 연결 실패: {e}"


def _get_registered_sheet_ids():
    """AHPkr_Users에 등록된 모든 스프레드시트 ID를 반환한다."""
    try:
        from survey_manager import get_survey_gspread_client, run_gspread_with_retry
        client = get_survey_gspread_client()
        if not client:
            return set()
        master = run_gspread_with_retry(client.open_by_key, "1xLvrH6LN8Vw3dVzoguf6TkgRrsJvEpMl2Z8s8HAvrVA")
        # Admin_Surveys 시트에서 ID 수집
        try:
            ws = master.worksheet("Admin_Surveys")
        except Exception:
            return set()
        records = run_gspread_with_retry(ws.get_all_records)
        ids = set()
        for r in records:
            sid = str(r.get("Survey_ID") or r.get("survey_id") or "").strip()
            if sid:
                ids.add(sid)
        return ids
    except Exception:
        return set()


def render_drive_cleanup():
    """드라이브 정리 UI를 렌더링한다."""
    from ui_style import section_title, hint

    section_title("드라이브 정리 (관리자)")
    hint("서비스 계정 드라이브의 스프레드시트 목록이다. 등록된 설문과 연결된 시트는 삭제할 수 없다.")

    service, err = _get_drive_service()
    if err:
        st.error(err)
        return

    # 파일 목록 조회 (서비스 계정이 소유한 파일만)
    with st.spinner("드라이브 파일 목록을 조회하는 중..."):
        try:
            files = []
            page_token = None
            while True:
                resp = service.files().list(
                    q="mimeType='application/vnd.google-apps.spreadsheet' and trashed=false and 'me' in owners",
                    fields="files(id, name, createdTime, modifiedTime, size, quotaBytesUsed, owners), nextPageToken",
                    pageSize=100,
                    pageToken=page_token,
                ).execute()
                files.extend(resp.get("files", []))
                page_token = resp.get("nextPageToken")
                if not page_token:
                    break
        except Exception as e:
            st.error(f"파일 목록 조회 실패: {e}")
            return

    if not files:
        st.info("서비스 계정이 소유한 스프레드시트가 없습니다. 용량 부족의 원인이 다른 곳에 있을 수 있습니다.")
        st.caption("참고: 서비스 계정과 공유된 파일(소유자 아님)은 목록에 표시되지 않습니다.")
        return

    registered = _get_registered_sheet_ids()

    # 용량 계산
    total_bytes = sum(int(f.get("quotaBytesUsed") or 0) for f in files)
    st.metric("스프레드시트 수", f"{len(files)}개")
    st.metric("사용 용량", f"{total_bytes / (1024**2):.1f} MB")

    # 테이블 구성
    import pandas as pd
    rows = []
    for f in files:
        fid = f["id"]
        is_registered = fid in registered
        rows.append({
            "선택": False,
            "파일명": f.get("name", "(제목 없음)"),
            "생성일": (f.get("createdTime") or "")[:10],
            "용량(KB)": round(int(f.get("quotaBytesUsed") or 0) / 1024, 1),
            "등록됨": "예" if is_registered else "아니오",
            "_id": fid,
            "_safe": not is_registered,
        })
    df = pd.DataFrame(rows)

    # 등록된 시트는 선택 불가 표시
    st.caption("등록됨='예'인 시트는 사용자 프로젝트와 연결되어 있어 삭제할 수 없습니다.")

    # 삭제 대상 선택 (등록되지 않은 것만)
    deletable = df[df["_safe"]].copy()
    if deletable.empty:
        st.info("삭제 가능한 시트가 없습니다. (모두 등록된 설문과 연결되어 있음)")
        return

    st.subheader(f"삭제 후보 ({len(deletable)}개)")
    for idx, row in deletable.iterrows():
        c1, c2, c3, c4 = st.columns([1, 4, 2, 2])
        with c1:
            checked = st.checkbox("", key=f"dc_sel_{row['_id']}", label_visibility="collapsed")
        with c2:
            st.write(row["파일명"])
        with c3:
            st.caption(row["생성일"])
        with c4:
            st.caption(f"{row['용량(KB)']} KB")
        if checked:
            st.session_state[f"dc_checked_{row['_id']}"] = True
        else:
            st.session_state.pop(f"dc_checked_{row['_id']}", None)

    selected_ids = [k.replace("dc_checked_", "") for k in st.session_state if k.startswith("dc_checked_")]
    if selected_ids:
        st.warning(f"{len(selected_ids)}개 파일을 삭제합니다. 이 작업은 되돌릴 수 없습니다.")
        if st.button("선택한 파일 삭제 확정", type="primary", key="dc_delete_confirm"):
            deleted = []
            failed = []
            for fid in selected_ids:
                # 안전장치: 등록된 시트는 건너뛴다
                if fid in registered:
                    failed.append((fid, "등록된 설문과 연결되어 있어 건너뜀"))
                    continue
                try:
                    service.files().delete(fileId=fid).execute()
                    deleted.append(fid)
                except Exception as e:
                    failed.append((fid, str(e)))
            for fid in deleted:
                st.session_state.pop(f"dc_checked_{fid}", None)
                st.session_state.pop(f"dc_sel_{fid}", None)
            if deleted:
                st.success(f"{len(deleted)}개 파일 삭제 완료.")
            if failed:
                for fid, reason in failed:
                    st.error(f"삭제 실패 ({fid[:8]}...): {reason}")
            st.rerun()

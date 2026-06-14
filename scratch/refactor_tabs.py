import re

with open("app.py", "r", encoding="utf-8") as f:
    content = f.read()

# Tab 2 & 3 markers
tab2_start_marker = '    # [신규] 관리자용 온라인 설문지 제작 탭 (Tab 2) 상세 구현\n    # -------------------------------------------------------------------------\n    if has_admin_tab:\n        with main_tab2:'
tab3_start_marker = '    # -------------------------------------------------------------------------\n    # [신규] 관리자용 응답현황 대시보드 탭 (Tab 3) 상세 구현\n    # -------------------------------------------------------------------------\n    if has_admin_tab:\n        with main_tab3:'

parts = content.split(tab2_start_marker)
if len(parts) == 2:
    left, right = parts
    subparts = right.split(tab3_start_marker)
    if len(subparts) == 2:
        tab2_body, rest = subparts
        
        # Process Tab 2
        tab2_lines = tab2_body.split("\n")
        new_tab2_lines = []
        new_tab2_lines.append('    with main_tab2:')
        new_tab2_lines.append('        st.header("📝 AHP 온라인 설문 자동 생성 및 배포기")')
        new_tab2_lines.append('        if st.session_state.user_id is None:')
        new_tab2_lines.append('            st.warning("🔒 **온라인 설문지 제작 기능은 회원 전용 서비스입니다.**")')
        new_tab2_lines.append('            st.info("회원가입 및 로그인을 완료하시면 제한 없이 AHP 온라인 설문지를 자동 생성하고 본인의 구글 스프레드시트와 연동할 수 있습니다.  \\n**좌측 사이드바의 로그인/회원가입 패널**을 이용해 주세요.")')
        new_tab2_lines.append('        else:')
        
        for line in tab2_lines:
            stripped = line.strip()
            if not stripped:
                new_tab2_lines.append("")
                continue
            
            # Skip the original headers/warnings as we customized them above
            if 'st.header("📝 AHP 온라인 설문 자동 생성 및 배포기")' in line:
                continue
            if 'st.info("모든 응답 데이터는 이용자 본인의 구글 계정' in line:
                new_tab2_lines.append('            st.info("모든 응답 데이터는 이용자 본인의 구글 계정(연동한 구글 스프레드시트)을 통해 저장되므로, 설문 배포 전에 테스트 응답을 제출하여 실제 시트에 정상적으로 데이터가 기록되는지 반드시 직접 미리 확인해야 합니다.")')
                continue
            if 'st.warning("⚠️ **주의 및 경고:** 본 플랫폼은 데이터 저장 오류' in line:
                new_tab2_lines.append('            st.warning("⚠️ **주의 및 경고:** 본 플랫폼은 데이터 저장 오류, 구글 API 연동 해제, 네트워크 장애 또는 관리 미흡 등으로 인한 데이터의 유실이나 소실에 대해 어떠한 법적/기술적 책임도 지지 않습니다. 중요 데이터는 실시간 구글 시트 확인 및 서버 로컬 안전 백업을 통해 주기적으로 다운로드하여 보관해 주시기 바랍니다.")')
                continue
                
            # Keep original line (which is already indented by 12 spaces, matching the "else:" block)
            new_tab2_lines.append(line)
            
        # Process Tab 3
        tab3_parts = rest.split("    st.markdown(\"---\")\n    st.caption(\"© 2026 AHP Master. All rights reserved.\")")
        if len(tab3_parts) == 2:
            tab3_body, footer = tab3_parts
            tab3_lines = tab3_body.split("\n")
            new_tab3_lines = []
            new_tab3_lines.append('    with main_tab3:')
            new_tab3_lines.append('        st.header("📊 배포 설문 실시간 응답 현황 대시보드")')
            new_tab3_lines.append('        if st.session_state.user_id is None:')
            new_tab3_lines.append('            st.warning("🔒 **응답현황 대시보드 기능은 회원 전용 서비스입니다.**")')
            new_tab3_lines.append('            st.info("회원가입 및 로그인을 완료하시면 본인이 배포한 설문지의 실시간 응답 상태 및 누적 데이터를 모니터링하고 다운로드할 수 있습니다.  \\n**좌측 사이드바의 로그인/회원가입 패널**을 이용해 주세요.")')
            new_tab3_lines.append('        else:')
            
            for line in tab3_lines:
                stripped = line.strip()
                if not stripped:
                    new_tab3_lines.append("")
                    continue
                if 'st.header("📊 배포 설문 실시간 응답 현황 대시보드")' in line:
                    continue
                if 'st.info("로그인한 관리자 계정으로 배포한 설문 목록을 자동으로 조회' in line:
                    new_tab3_lines.append('            st.info("본인이 배포한 설문 목록을 자동으로 조회하여 실시간 응답 현황을 대시보드로 구성합니다. (별도의 구글 스프레드시트 ID 입력 불필요)")')
                    continue
                
                # Keep original line (which is already indented by 12 spaces, matching the "else:" block)
                new_tab3_lines.append(line)
                
            # Reconstruct content
            new_content = left + "    # [신규] 온라인 설문지 제작 탭 (Tab 2) 상세 구현\n    # -------------------------------------------------------------------------\n" + "\n".join(new_tab2_lines) + "\n\n    # -------------------------------------------------------------------------\n    # [신규] 응답현황 대시보드 탭 (Tab 3) 상세 구현\n    # -------------------------------------------------------------------------\n" + "\n".join(new_tab3_lines) + "\n    st.markdown(\"---\")\n    st.caption(\"© 2026 AHP Master. All rights reserved.\")" + footer
            
            # Apply unconditional tabs at line 3237
            new_content = new_content.replace(
                '    has_admin_tab = (st.session_state.user_role == \'admin\')\n    \n    if has_admin_tab:\n        main_tab1, main_tab2, main_tab3 = st.tabs(["📊 AHP 분석 도구", "📝 온라인 설문지 제작", "📊 응답현황 대시보드"])\n    else:\n        main_tab1 = st.container() # 일반 사용자는 컨테이너로 직접 단독 노출',
                '    main_tab1, main_tab2, main_tab3 = st.tabs(["📊 AHP 분석 도구", "📝 온라인 설문지 제작", "📊 응답현황 대시보드"])'
            )
            
            with open("app.py", "w", encoding="utf-8") as f:
                f.write(new_content)
            print("Refactoring succeeded!")
        else:
            print("Footer not found")
    else:
        print("Tab 3 split failed")
else:
    print("Tab 2 split failed")

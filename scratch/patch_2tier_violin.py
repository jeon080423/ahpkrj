"""
2계층 바이올린 플롯을 3계층과 동일한 드롭다운 + go.Violin 스타일로 교체.
드롭다운: 대분류(Main) / 중분류(Sub)
- 대분류 선택: Main_Criteria CR 분포 1개 바이올린
- 중분류 선택: 각 중분류 시트별 CR 분포 바이올린 (중분류 수만큼)
색상은 Type(그룹)별로 구분하지 않고 Sheet별로 구분.
"""

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_block = '''                            # [추가 수정 부분] 바이올린 플롯 (CR 분포 시각화)
                            st.markdown("---")
                            st.write(_("**일관성 비율(CR) 분포 (Violin Plot)**", "**Consistency Ratio (CR) Distribution (Violin Plot)**"))
                        
                            # CR 값 추출을 위한 데이터 정제
                            cr_dist_data = []
                            # 메인 시트 CR
                            for idx_row, r in main_results_df.iterrows():
                                g_type_val = str(r['Type'])
                                if is_english:
                                    g_type_val = g_type_val.replace("전문가", "Expert").replace("일반", "General").replace("공무원", "Public Official")
                                cr_dist_data.append({"Type": g_type_val, "Sheet": "Main_Criteria", "CR": r['Final_CR']})
                            # 하위 시트 CR
                            for mf, info in sub_results_storage.items():
                                for idx_row, r in info['df'].iterrows():
                                    g_type_val = str(r['Type'])
                                    if is_english:
                                        g_type_val = g_type_val.replace("전문가", "Expert").replace("일반", "General").replace("공무원", "Public Official")
                                    cr_dist_data.append({"Type": g_type_val, "Sheet": mf, "CR": r['Final_CR']})
                        
                            if cr_dist_data:
                                cr_df = pd.DataFrame(cr_dist_data)
                                color_map = {
                                    "전문가": "#1f77b4", "일반": "#d62728", "공무원": "#2ca02c",
                                    "Expert": "#1f77b4", "General": "#d62728", "Public Official": "#2ca02c"
                                }
                                unique_types = cr_df['Type'].unique()
                            
                                # [1. 전체 표본 그래프 선행 출력]
                                if len(unique_types) > 1:
                                    fig_all = px.violin(cr_df, y="CR", x="Sheet", box=True, points="all",
                                                       hover_data=cr_df.columns, title=_("[전체 표본] 일관성 비율(CR) 분포", "[Overall Samples] Consistency Ratio (CR) Distribution"),
                                                       color_discrete_sequence=["#7f7f7f"]) # 전체는 회색 계열
                                    fig_all.update_traces(spanmode='soft', pointpos=0, jitter=0.5, marker=dict(opacity=0.6, size=5))
                                
                                    # 학술 논문용(Publication-ready) 스타일 적용
                                    fig_all.update_layout(
                                        template="simple_white",
                                        font=dict(family="Arial, sans-serif", size=14, color="black"),
                                        title_font=dict(size=16, family="Arial, sans-serif", color="black"),
                                        xaxis=dict(title=None, showline=True, linewidth=1.5, linecolor='black', mirror=True, tickfont=dict(color="black")),
                                        yaxis=dict(showline=True, linewidth=1.5, linecolor='black', mirror=True, tickfont=dict(color="black")),
                                        plot_bgcolor="white",
                                        paper_bgcolor="white",
                                        margin=dict(l=60, r=40, t=60, b=40)
                                    )
                                    # Y축 범위를 자동(Auto)으로 맡겨 꼬리(하단/상단)가 잘리지 않고 뾰족하게 보이도록 수정
                                    st.plotly_chart(fig_all, use_container_width=True)
                                    st.markdown("---")
     
                                # [2. 그룹별 별도 객체로 분리하여 출력]
                                for g_type in unique_types:
                                    g_df = cr_df[cr_df['Type'] == g_type]
                                    fig_violin = px.violin(g_df, y="CR", x="Sheet", box=True, points="all",
                                                           hover_data=g_df.columns, title=_(f"[{g_type}] 일관성 비율(CR) 분포", f"[{g_type}] Consistency Ratio (CR) Distribution"),
                                                           color_discrete_sequence=[color_map.get(g_type, "#1f77b4")])
                                    fig_violin.update_traces(spanmode='soft', pointpos=0, jitter=0.5, marker=dict(opacity=0.6, size=5))
                                
                                    # 학술 논문용(Publication-ready) 스타일 적용
                                    fig_violin.update_layout(
                                        template="simple_white",
                                        font=dict(family="Arial, sans-serif", size=14, color="black"),
                                        title_font=dict(size=16, family="Arial, sans-serif", color="black"),
                                        xaxis=dict(title=None, showline=True, linewidth=1.5, linecolor='black', mirror=True, tickfont=dict(color="black")),
                                        yaxis=dict(showline=True, linewidth=1.5, linecolor='black', mirror=True, tickfont=dict(color="black")),
                                        plot_bgcolor="white",
                                        paper_bgcolor="white",
                                        margin=dict(l=60, r=40, t=60, b=40)
                                    )
                                    # Y축 범위를 자동(Auto)으로 맡겨 꼬리가 잘리지 않도록 수정
                                    st.plotly_chart(fig_violin, use_container_width=True)'''

new_block = '''                            # [바이올린 플롯] CR 분포 시각화 — 드롭다운 계층 선택
                            st.markdown("---")
                            st.write(_("**일관성 비율(CR) 분포 (Violin Plot)**", "**Consistency Ratio (CR) Distribution (Violin Plot)**"))
                            st.caption(_("계층을 선택하면 해당 수준 응답자들의 CR 분포를 표시합니다. 바이올린 폭 = 밀도, 내부 박스 = 중앙값·사분위수, 점 = 개별 응답자",
                                         "Select a tier to view respondent CR distribution. Width = density, box = median/IQR, dots = individual respondents"))

                            _t2_tier_opts_ko = ["대분류 (Main)", "중분류 (Sub)"]
                            _t2_tier_opts_en = ["Main Criteria", "Sub-Criteria"]
                            _t2_tier_opts = _t2_tier_opts_en if is_english else _t2_tier_opts_ko
                            _t2_sel_tier = st.selectbox(
                                _("📂 표시할 계층 선택", "📂 Select Tier to Display"),
                                options=_t2_tier_opts,
                                key="vio_tier_select_2tier"
                            )

                            _t2_vio_palette = [
                                "rgba(70,130,180,0.65)",
                                "rgba(205,92,92,0.65)",
                                "rgba(255,182,193,0.65)",
                                "rgba(60,179,113,0.65)",
                                "rgba(255,165,0,0.65)",
                                "rgba(147,112,219,0.65)",
                                "rgba(72,209,204,0.65)",
                                "rgba(255,215,0,0.65)",
                            ]
                            _t2_vio_line_pal = [
                                "#4682B4","#CD5C5C","#FFB6C1","#3CB371",
                                "#FFA500","#9370DB","#48D1CC","#FFD700"
                            ]

                            try:
                                _fig_t2_vio = go.Figure()
                                _t2_ci = 0

                                # ── 선택: 대분류 ─────────────────────────────────
                                if _t2_sel_tier == _t2_tier_opts[0]:
                                    if not main_results_df.empty and "Final_CR" in main_results_df.columns:
                                        _t2_main_cr = main_results_df["Final_CR"].dropna().tolist()
                                        _t2_xlbl = _("대분류", "Main Criteria")
                                        _fig_t2_vio.add_trace(go.Violin(
                                            y=_t2_main_cr, x=[_t2_xlbl]*len(_t2_main_cr),
                                            name=_t2_xlbl, box_visible=True, meanline_visible=True,
                                            points="all", jitter=0.35, pointpos=0,
                                            line_color=_t2_vio_line_pal[0],
                                            fillcolor=_t2_vio_palette[0],
                                            opacity=0.75,
                                            hovertemplate="<b>" + _t2_xlbl + "</b><br>CR: %{y:.4f}<extra></extra>",
                                            showlegend=True
                                        ))
                                    _t2_xaxis_title = _("대분류", "Main Criteria")
                                    _t2_legend_title = _("대분류", "Main Criteria")

                                # ── 선택: 중분류 ─────────────────────────────────
                                else:
                                    for _t2_mf, _t2_info in sub_results_storage.items():
                                        _t2_sdf = _t2_info.get("df", None)
                                        if _t2_sdf is None or _t2_sdf.empty or "Final_CR" not in _t2_sdf.columns:
                                            continue
                                        _t2_cr_vals = _t2_sdf["Final_CR"].dropna().tolist()
                                        if len(_t2_cr_vals) < 2:
                                            continue
                                        _t2_xlbl = _(f"중분류({_t2_mf})", f"Sub({_t2_mf})")
                                        _fig_t2_vio.add_trace(go.Violin(
                                            y=_t2_cr_vals, x=[_t2_xlbl]*len(_t2_cr_vals),
                                            name=_t2_xlbl, box_visible=True, meanline_visible=True,
                                            points="all", jitter=0.35, pointpos=0,
                                            line_color=_t2_vio_line_pal[_t2_ci % len(_t2_vio_line_pal)],
                                            fillcolor=_t2_vio_palette[_t2_ci % len(_t2_vio_palette)],
                                            opacity=0.75,
                                            hovertemplate="<b>" + _t2_xlbl + "</b><br>CR: %{y:.4f}<extra></extra>",
                                            showlegend=True
                                        ))
                                        _t2_ci += 1
                                    _t2_xaxis_title = _("대분류 (중분류 비교 CR)", "Main Criteria (Sub-Criteria Comparison CR)")
                                    _t2_legend_title = _("중분류", "Sub-Criteria")

                                if len(_fig_t2_vio.data) == 0:
                                    st.info(_("선택한 계층의 CR 데이터가 없거나 응답 수가 부족합니다.",
                                              "No CR data available for the selected tier or insufficient responses."))
                                else:
                                    _fig_t2_vio.add_hline(
                                        y=0.1, line_dash="dash", line_color="red",
                                        annotation_text=_("CR 임계값 (0.1)", "CR Threshold (0.1)"),
                                        annotation_position="top right"
                                    )
                                    _fig_t2_vio.update_layout(
                                        title=_(
                                            f"바이올린플롯 CR — {_t2_sel_tier}",
                                            f"Violin Plot CR — {_t2_sel_tier}"
                                        ),
                                        xaxis_title=_t2_xaxis_title,
                                        yaxis_title="Final_CR",
                                        violinmode="overlay",
                                        height=540,
                                        legend_title_text=_t2_legend_title,
                                        plot_bgcolor="white",
                                        paper_bgcolor="white",
                                        xaxis=dict(showgrid=False, tickangle=-20),
                                        yaxis=dict(showgrid=True, gridcolor="#eeeeee", zeroline=False)
                                    )
                                    st.plotly_chart(_fig_t2_vio, use_container_width=True)
                            except Exception as _e_t2_vio:
                                st.warning(_(f"바이올린 플롯 생성 실패: {_e_t2_vio}", f"Violin plot generation failed: {_e_t2_vio}"))'''

if old_block in content:
    new_content = content.replace(old_block, new_block, 1)
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("SUCCESS: 2-tier violin plot patch applied.")
else:
    print("ERROR: Old block not found.")
    import re
    m = re.search(r'\[추가 수정 부분\] 바이올린 플롯', content)
    if m:
        print("Partial match at:", m.start())
        print("Context:", repr(content[m.start():m.start()+300]))
    else:
        print("No partial match found.")

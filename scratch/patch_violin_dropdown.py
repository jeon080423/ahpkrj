"""
app.py 바이올린 플롯을 드롭다운(대분류/중분류/소분류) 방식으로 교체하는 패치.
각 계층을 선택하면 해당 계층의 Final_CR 분포를 보여준다.
- 대분류: main_results_df 의 Final_CR (1개 바이올린)
- 중분류: 대분류별 sub_results_storage[mf]['df']['Final_CR'] (대분류 수만큼 바이올린)
- 소분류: 중분류별 sub_sub_results_storage[sf]['df']['Final_CR'] (소분류 있는 중분류 수만큼 바이올린)
"""

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_block = '''                                st.markdown(_("**② 계층별 일관성 비율(CR) 분포 — 바이올린 플롯**",
                                              "**② Consistency Ratio (CR) Distribution by Tier — Violin Plot**"))
                                st.caption(_("대분류 + 각 중분류별 응답자 CR 분포. 바이올린 폭 = 밀도, 내부 박스 = 중앙값·사분위수, 점 = 개별 응답자",
                                             "CR distribution by Main + Sub criteria. Violin width = density, box = median/IQR, dots = individual respondents"))
                                _vio_main_df = ui_data_v3.get("main_results_df", pd.DataFrame())
                                _vio_sub_stor = ui_data_v3.get("sub_results_storage", {})
                                _vio_mf_list  = ui_data_v3.get("main_factors", [])
                                try:
                                    import plotly.graph_objects as _go_vio
                                    # 팔레트: 중분류 수만큼 (Set1 계열 선명한 색)
                                    _vio_palette = [
                                        "rgba(70,130,180,0.65)",   # steel blue
                                        "rgba(205,92,92,0.65)",    # indian red
                                        "rgba(255,182,193,0.65)",  # light pink
                                        "rgba(60,179,113,0.65)",   # medium sea green
                                        "rgba(255,165,0,0.65)",    # orange
                                        "rgba(147,112,219,0.65)",  # medium purple
                                        "rgba(72,209,204,0.65)",   # medium turquoise
                                        "rgba(255,215,0,0.65)",    # gold
                                    ]
                                    _vio_line_palette = [
                                        "#4682B4","#CD5C5C","#FFB6C1","#3CB371",
                                        "#FFA500","#9370DB","#48D1CC","#FFD700"
                                    ]
                                    _fig_vio = _go_vio.Figure()
                                    _col_idx = 0

                                    # ── 대분류 바이올린 ──────────────────────────────
                                    if not _vio_main_df.empty and "Final_CR" in _vio_main_df.columns:
                                        _main_cr = _vio_main_df["Final_CR"].dropna().tolist()
                                        _main_id  = _vio_main_df.get("ID", pd.Series([""] * len(_vio_main_df))).tolist()
                                        _x_label_main = _("대분류", "Main Criteria")
                                        _fig_vio.add_trace(_go_vio.Violin(
                                            y=_main_cr,
                                            x=[_x_label_main] * len(_main_cr),
                                            name=_x_label_main,
                                            box_visible=True,
                                            meanline_visible=True,
                                            points="all",
                                            jitter=0.35,
                                            pointpos=0,
                                            line_color=_vio_line_palette[_col_idx % len(_vio_line_palette)],
                                            fillcolor=_vio_palette[_col_idx % len(_vio_palette)],
                                            opacity=0.75,
                                            hovertemplate="<b>" + _x_label_main + "</b><br>CR: %{y:.4f}<extra></extra>",
                                            showlegend=True
                                        ))
                                        _col_idx += 1

                                    # ── 중분류 바이올린 (중분류별 각 1개) ────────────
                                    for _mf in _vio_mf_list:
                                        _sinfo = _vio_sub_stor.get(_mf, {})
                                        _sdf = _sinfo.get("df", None)
                                        if _sdf is None or _sdf.empty or "Final_CR" not in _sdf.columns:
                                            continue
                                        _sub_factors = _sinfo.get("factors", [])
                                        for _sf in _sub_factors:
                                            # 각 중분류 항목 단위로 하나의 바이올린
                                            _sf_cr = _sdf["Final_CR"].dropna().tolist()
                                            if len(_sf_cr) < 2:
                                                continue
                                            _x_label_sf = _(f"중분류({_sf})", f"Sub({_sf})")
                                            _c_fill = _vio_palette[_col_idx % len(_vio_palette)]
                                            _c_line = _vio_line_palette[_col_idx % len(_vio_line_palette)]
                                            _fig_vio.add_trace(_go_vio.Violin(
                                                y=_sf_cr,
                                                x=[_x_label_sf] * len(_sf_cr),
                                                name=_x_label_sf,
                                                box_visible=True,
                                                meanline_visible=True,
                                                points="all",
                                                jitter=0.35,
                                                pointpos=0,
                                                line_color=_c_line,
                                                fillcolor=_c_fill,
                                                opacity=0.75,
                                                hovertemplate="<b>" + _x_label_sf + "</b><br>CR: %{y:.4f}<extra></extra>",
                                                showlegend=True
                                            ))
                                            _col_idx += 1

                                    if len(_fig_vio.data) == 0:
                                        st.info(_("바이올린 플롯을 그릴 CR 데이터가 없습니다.", "No CR data available for violin plot."))
                                    else:
                                        _cr_threshold_line = 0.1
                                        _fig_vio.add_hline(
                                            y=_cr_threshold_line,
                                            line_dash="dash",
                                            line_color="red",
                                            annotation_text=_("CR 임계값 (0.1)", "CR Threshold (0.1)"),
                                            annotation_position="top right"
                                        )
                                        _fig_vio.update_layout(
                                            title=_(
                                                "바이올린플롯 CR",
                                                "Violin Plot — Consistency Ratio (CR)"
                                            ),
                                            xaxis_title=_("계층 (대분류 / 중분류)", "Tier (Main / Sub-Criteria)"),
                                            yaxis_title="Final_CR",
                                            violinmode="overlay",
                                            height=540,
                                            legend_title_text=_("중분류", "Sub-Criteria"),
                                            plot_bgcolor="white",
                                            paper_bgcolor="white",
                                            xaxis=dict(showgrid=False),
                                            yaxis=dict(showgrid=True, gridcolor="#eeeeee", zeroline=False)
                                        )
                                        st.plotly_chart(_fig_vio, use_container_width=True)
                                except Exception as _e_vio:
                                    st.warning(_(f"바이올린 플롯 생성 실패: {_e_vio}", f"Violin plot generation failed: {_e_vio}"))'''

new_block = '''                                st.markdown(_("**② 계층별 일관성 비율(CR) 분포 — 바이올린 플롯**",
                                              "**② Consistency Ratio (CR) Distribution by Tier — Violin Plot**"))
                                st.caption(_("계층을 선택하면 해당 수준 응답자들의 CR 분포를 표시합니다. 바이올린 폭 = 밀도, 내부 박스 = 중앙값·사분위수, 점 = 개별 응답자",
                                             "Select a tier to view respondent CR distribution. Width = density, box = median/IQR, dots = individual respondents"))

                                _vio_main_df   = ui_data_v3.get("main_results_df", pd.DataFrame())
                                _vio_sub_stor  = ui_data_v3.get("sub_results_storage", {})
                                _vio_ss_stor   = ui_data_v3.get("sub_sub_results_storage", {})
                                _vio_mf_list   = ui_data_v3.get("main_factors", [])

                                _tier_options_ko = ["대분류 (Main)", "중분류 (Sub)", "소분류 (Sub-sub)"]
                                _tier_options_en = ["Main Criteria", "Sub-Criteria", "Sub-sub-Criteria"]
                                _tier_opts = _tier_options_en if is_english else _tier_options_ko
                                _sel_tier = st.selectbox(
                                    _("📂 표시할 계층 선택", "📂 Select Tier to Display"),
                                    options=_tier_opts,
                                    key="vio_tier_select_v3"
                                )

                                try:
                                    import plotly.graph_objects as _go_vio
                                    _vio_palette = [
                                        "rgba(70,130,180,0.65)",
                                        "rgba(205,92,92,0.65)",
                                        "rgba(255,182,193,0.65)",
                                        "rgba(60,179,113,0.65)",
                                        "rgba(255,165,0,0.65)",
                                        "rgba(147,112,219,0.65)",
                                        "rgba(72,209,204,0.65)",
                                        "rgba(255,215,0,0.65)",
                                    ]
                                    _vio_line_pal = [
                                        "#4682B4","#CD5C5C","#FFB6C1","#3CB371",
                                        "#FFA500","#9370DB","#48D1CC","#FFD700"
                                    ]
                                    _fig_vio = _go_vio.Figure()
                                    _ci = 0

                                    # ── 선택: 대분류 ─────────────────────────────────
                                    if _sel_tier in [_tier_opts[0]]:
                                        if not _vio_main_df.empty and "Final_CR" in _vio_main_df.columns:
                                            _main_cr = _vio_main_df["Final_CR"].dropna().tolist()
                                            _xlbl = _("대분류", "Main Criteria")
                                            _fig_vio.add_trace(_go_vio.Violin(
                                                y=_main_cr, x=[_xlbl]*len(_main_cr),
                                                name=_xlbl, box_visible=True, meanline_visible=True,
                                                points="all", jitter=0.35, pointpos=0,
                                                line_color=_vio_line_pal[0], fillcolor=_vio_palette[0],
                                                opacity=0.75,
                                                hovertemplate="<b>" + _xlbl + "</b><br>CR: %{y:.4f}<extra></extra>",
                                                showlegend=True
                                            ))
                                        _vio_xaxis_title = _("대분류", "Main Criteria")
                                        _vio_legend_title = _("대분류", "Main Criteria")

                                    # ── 선택: 중분류 ─────────────────────────────────
                                    elif _sel_tier in [_tier_opts[1]]:
                                        # 대분류별로 하나의 바이올린 (해당 대분류 중분류 비교 시 CR)
                                        for _mf in _vio_mf_list:
                                            _sinfo = _vio_sub_stor.get(_mf, {})
                                            _sdf = _sinfo.get("df", None)
                                            if _sdf is None or _sdf.empty or "Final_CR" not in _sdf.columns:
                                                continue
                                            _cr_vals = _sdf["Final_CR"].dropna().tolist()
                                            if len(_cr_vals) < 2:
                                                continue
                                            _xlbl = _(f"중분류({_mf})", f"Sub({_mf})")
                                            _fig_vio.add_trace(_go_vio.Violin(
                                                y=_cr_vals, x=[_xlbl]*len(_cr_vals),
                                                name=_xlbl, box_visible=True, meanline_visible=True,
                                                points="all", jitter=0.35, pointpos=0,
                                                line_color=_vio_line_pal[_ci % len(_vio_line_pal)],
                                                fillcolor=_vio_palette[_ci % len(_vio_palette)],
                                                opacity=0.75,
                                                hovertemplate="<b>" + _xlbl + "</b><br>CR: %{y:.4f}<extra></extra>",
                                                showlegend=True
                                            ))
                                            _ci += 1
                                        _vio_xaxis_title = _("대분류 (중분류 비교 CR)", "Main Criteria (Sub-Criteria Comparison CR)")
                                        _vio_legend_title = _("중분류", "Sub-Criteria")

                                    # ── 선택: 소분류 ─────────────────────────────────
                                    else:
                                        # 중분류별로 하나의 바이올린 (해당 중분류 소분류 비교 시 CR)
                                        for _mf in _vio_mf_list:
                                            _sinfo = _vio_sub_stor.get(_mf, {})
                                            _sub_factors = _sinfo.get("factors", [])
                                            for _sf in _sub_factors:
                                                _ssinfo = _vio_ss_stor.get(_sf, {})
                                                _ssdf = _ssinfo.get("df", None)
                                                if _ssdf is None or _ssdf.empty or "Final_CR" not in _ssdf.columns:
                                                    continue
                                                _cr_vals = _ssdf["Final_CR"].dropna().tolist()
                                                if len(_cr_vals) < 2:
                                                    continue
                                                _xlbl = _(f"소분류({_sf})", f"Sub-sub({_sf})")
                                                _fig_vio.add_trace(_go_vio.Violin(
                                                    y=_cr_vals, x=[_xlbl]*len(_cr_vals),
                                                    name=_xlbl, box_visible=True, meanline_visible=True,
                                                    points="all", jitter=0.35, pointpos=0,
                                                    line_color=_vio_line_pal[_ci % len(_vio_line_pal)],
                                                    fillcolor=_vio_palette[_ci % len(_vio_palette)],
                                                    opacity=0.75,
                                                    hovertemplate="<b>" + _xlbl + "</b><br>CR: %{y:.4f}<extra></extra>",
                                                    showlegend=True
                                                ))
                                                _ci += 1
                                        _vio_xaxis_title = _("중분류 (소분류 비교 CR)", "Sub-Criteria (Sub-sub Comparison CR)")
                                        _vio_legend_title = _("소분류", "Sub-sub-Criteria")

                                    if len(_fig_vio.data) == 0:
                                        st.info(_("선택한 계층의 CR 데이터가 없거나 응답 수가 부족합니다.",
                                                  "No CR data available for the selected tier or insufficient responses."))
                                    else:
                                        _fig_vio.add_hline(
                                            y=0.1, line_dash="dash", line_color="red",
                                            annotation_text=_("CR 임계값 (0.1)", "CR Threshold (0.1)"),
                                            annotation_position="top right"
                                        )
                                        _fig_vio.update_layout(
                                            title=_(
                                                f"바이올린플롯 CR — {_sel_tier}",
                                                f"Violin Plot CR — {_sel_tier}"
                                            ),
                                            xaxis_title=_vio_xaxis_title,
                                            yaxis_title="Final_CR",
                                            violinmode="overlay",
                                            height=540,
                                            legend_title_text=_vio_legend_title,
                                            plot_bgcolor="white",
                                            paper_bgcolor="white",
                                            xaxis=dict(showgrid=False, tickangle=-20),
                                            yaxis=dict(showgrid=True, gridcolor="#eeeeee", zeroline=False)
                                        )
                                        st.plotly_chart(_fig_vio, use_container_width=True)
                                except Exception as _e_vio:
                                    st.warning(_(f"바이올린 플롯 생성 실패: {_e_vio}", f"Violin plot generation failed: {_e_vio}"))'''

if old_block in content:
    new_content = content.replace(old_block, new_block, 1)
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("SUCCESS: Dropdown violin plot patch applied.")
else:
    print("ERROR: Old block not found.")
    import re
    m = re.search(r'계층별 일관성 비율', content)
    if m:
        print("Partial match at:", m.start())
        print("Context:", repr(content[m.start():m.start()+200]))
    else:
        print("No partial match found.")

"""
app.py의 바이올린 플롯 코드를 이미지와 동일한 스타일로 교체하는 패치 스크립트.
- X축: 대분류, 중분류(이름) 각각
- Y축: Final_CR (일관성 비율)
- 색상: 중분류별 구분, 범례 표시
- 내부: 박스플롯 + 개별 점(jitter)
"""

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 기존 바이올린 플롯 블록 찾기 (st.caption 포함)
old_block = '''                                st.markdown(_("**② 대분류별 글로벌 가중치 분포 — 바이올린 플롯**",
                                              "**② Global Weight Distribution by Main Criteria — Violin Plot**"))
                                st.caption(_("바이올린 형태의 폭 = 해당 가중치 값의 밀도(응답자 분포), 내부 박스 = 중앙값·사분위수, 점 = 개별 소분류 항목",
                                             "Violin width = density of weight values (respondent distribution), inner box = median/IQR, dots = individual sub-sub items"))
                                _vio_df = final_df_v3[~final_df_v3["소분류"].str.endswith("_단일항목", na=False)].copy()
                                if _vio_df.empty:
                                    _vio_df = final_df_v3.copy()
                                    _vio_item_col = "중분류"
                                else:
                                    _vio_item_col = "소분류"
                                if not _vio_df.empty and len(_vio_df) >= 2:
                                    try:
                                        import plotly.graph_objects as _go_vio
                                        _vio_colors = px.colors.qualitative.Set2
                                        _vio_main_list = _vio_df["대분류"].unique().tolist()
                                        _fig_vio = _go_vio.Figure()
                                        for _vi, _mf in enumerate(_vio_main_list):
                                            _sub_v = _vio_df[_vio_df["대분류"] == _mf]
                                            _col_v = _vio_colors[_vi % len(_vio_colors)]
                                            _x_label = _mf if not is_english else _mf
                                            # 바이올린
                                            _fig_vio.add_trace(_go_vio.Violin(
                                                y=_sub_v["Global Weight"],
                                                x=[_x_label] * len(_sub_v),
                                                name=_x_label,
                                                box_visible=True,
                                                meanline_visible=True,
                                                points="all",
                                                jitter=0.3,
                                                pointpos=0,
                                                line_color=_col_v,
                                                fillcolor=_col_v,
                                                opacity=0.7,
                                                hovertemplate=(
                                                    "<b>%{text}</b><br>"
                                                    + _("글로벌 가중치", "Global Weight") + ": %{y:.4f}<extra></extra>"
                                                ),
                                                text=_sub_v[_vio_item_col].tolist(),
                                                showlegend=True
                                            ))
                                        _fig_vio.update_layout(
                                            title=_(
                                                "대분류별 소분류 글로벌 가중치 분포 (바이올린 플롯)",
                                                "Global Weight Distribution per Main Criteria (Violin Plot)"
                                            ),
                                            xaxis_title=_("대분류", "Main Criteria"),
                                            yaxis_title=_("글로벌 가중치", "Global Weight"),
                                            violinmode="group",
                                            height=520,
                                            legend_title_text=_("대분류", "Main Criteria")
                                        )
                                        st.plotly_chart(_fig_vio, use_container_width=True)
                                    except Exception as _e_vio:
                                        st.warning(_(f"바이올린 플롯 생성 실패: {_e_vio}", f"Violin plot generation failed: {_e_vio}"))
                                else:
                                    st.info(_("바이올린 플롯을 위한 데이터가 부족합니다 (항목 수 2개 이상 필요).",
                                              "Insufficient data for violin plot (at least 2 items required)."))'''

new_block = '''                                st.markdown(_("**② 계층별 일관성 비율(CR) 분포 — 바이올린 플롯**",
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

if old_block in content:
    new_content = content.replace(old_block, new_block, 1)
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("SUCCESS: Violin plot patch (image style) applied.")
else:
    print("ERROR: Old block not found.")
    import re
    m = re.search(r'대분류별 글로벌 가중치 분포', content)
    if m:
        print("Partial match at:", m.start())
    else:
        print("No partial match.")

"""
app.py 트리맵 섹션을 바이올린 플롯으로 교체하는 패치 스크립트
"""

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_block = '''                                st.markdown(_("**② 계층 구조 트리맵 (대분류 > 중분류 > 소분류)**",
                                              "**② Hierarchical Treemap (Main > Sub > Sub-sub)**"))
                                _tm_df = final_df_v3.copy()
                                _is_dummy = _tm_df["소분류"].str.endswith("_단일항목", na=False).all()
                                if _is_dummy:
                                    _tm_df["소분류"] = _tm_df["중분류"]
                                _tm_df = _tm_df[_tm_df["Global Weight"] > 0].copy()
                                if not _tm_df.empty:
                                    try:
                                        if is_english:
                                            _tm_disp = _tm_df.rename(columns={"대분류":"Main","중분류":"Sub","소분류":"Sub-sub"})
                                            _path_cols = ["Main","Sub","Sub-sub"]
                                        else:
                                            _tm_disp = _tm_df
                                            _path_cols = ["대분류","중분류","소분류"]
                                        _fig_tree_v3 = px.treemap(
                                            _tm_disp, path=_path_cols, values="Global Weight",
                                            color="Global Weight", color_continuous_scale="Blues",
                                            title=_("3계층 AHP 가중치 계층 트리맵", "3-Tier AHP Weight Hierarchical Treemap")
                                        )
                                        _fig_tree_v3.update_traces(textinfo="label+percent parent")
                                        _fig_tree_v3.update_layout(height=550)
                                        st.plotly_chart(_fig_tree_v3, use_container_width=True)
                                    except Exception as _e_tree:
                                        st.warning(_(f"트리맵 생성 실패: {_e_tree}", f"Treemap generation failed: {_e_tree}"))'''

new_block = '''                                st.markdown(_("**② 대분류별 글로벌 가중치 분포 — 바이올린 플롯**",
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

if old_block in content:
    new_content = content.replace(old_block, new_block, 1)
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("SUCCESS: Violin plot patch applied.")
else:
    print("ERROR: Old treemap block not found.")
    import re
    m = re.search(r'계층 구조 트리맵', content)
    if m:
        print("Partial match found at:", m.start())
        print("Context:", repr(content[m.start()-50:m.start()+100]))
    else:
        print("No partial match found either.")

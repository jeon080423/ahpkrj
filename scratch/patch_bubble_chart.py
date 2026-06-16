"""
app.py의 3계층 시각화 센터 ① 막대 차트를 버블 차트로 교체하는 패치 스크립트
"""

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_block = '''                                st.markdown(_("**① 전체 소분류 글로벌 가중치 (대분류별 색 구분)**",
                                              "**① All Sub-sub-Criteria Global Weights (colored by Main Criteria)**"))
                                _nd_v3 = final_df_v3[~final_df_v3["소분류"].str.endswith("_단일항목", na=False)].copy()
                                if _nd_v3.empty:
                                    _nd_v3 = final_df_v3.copy()
                                    _y_viz = "중분류"
                                else:
                                    _y_viz = "소분류"
                                _chart_all_v3 = _nd_v3.sort_values("Global Weight", ascending=True).copy()
                                if is_english:
                                    _chart_all_v3 = _chart_all_v3.rename(columns={"소분류":"Sub-sub-Criteria","대분류":"Main Criteria","중분류":"Sub-Criteria"})
                                    _y_viz = "Sub-sub-Criteria" if _y_viz=="소분류" else "Sub-Criteria"
                                    _color_viz = "Main Criteria"
                                else:
                                    _color_viz = "대분류"
                                _fig_all_v3 = px.bar(
                                    _chart_all_v3, y=_y_viz, x="Global Weight",
                                    orientation="h", text_auto=".4f", color=_color_viz,
                                    title=_("소분류 전체 글로벌 가중치", "All Sub-sub-Criteria Global Weights"),
                                    color_discrete_sequence=px.colors.qualitative.Set2
                                )
                                _fig_all_v3.update_layout(height=max(400, len(_chart_all_v3)*30+100))
                                st.plotly_chart(_fig_all_v3, use_container_width=True)'''

new_block = '''                                st.markdown(_("**① 글로벌 가중치 순위 버블 차트 (버블 크기 = 중분류 가중치, 색 = 대분류)**",
                                              "**① Global Weight Bubble Chart (bubble size = Sub weight, color = Main Criteria)**"))
                                _nd_v3 = final_df_v3[~final_df_v3["소분류"].str.endswith("_단일항목", na=False)].copy()
                                if _nd_v3.empty:
                                    _nd_v3 = final_df_v3.copy()
                                    _item_col_bub = "중분류"
                                else:
                                    _item_col_bub = "소분류"
                                _bubble_df = _nd_v3.copy()
                                if "Global Rank" not in _bubble_df.columns:
                                    _bubble_df["Global Rank"] = _bubble_df["Global Weight"].rank(ascending=False, method="min").astype(int)
                                # 버블 크기: 중분류 가중치 기반 (최소 크기 보장)
                                _bubble_df["_bubble_size"] = (_bubble_df["중분류 가중치"] * 100).clip(lower=3)
                                if is_english:
                                    _bubble_df_disp = _bubble_df.rename(columns={
                                        "소분류": "Sub-sub-Criteria", "대분류": "Main Criteria",
                                        "중분류": "Sub-Criteria", "중분류 가중치": "Sub Weight"
                                    })
                                    _label_col_bub = "Sub-sub-Criteria" if _item_col_bub == "소분류" else "Sub-Criteria"
                                    _color_bub = "Main Criteria"
                                    _hover_sub_bub = "Sub-Criteria"
                                    _hover_subw_bub = "Sub Weight"
                                else:
                                    _bubble_df_disp = _bubble_df
                                    _label_col_bub = _item_col_bub
                                    _color_bub = "대분류"
                                    _hover_sub_bub = "중분류"
                                    _hover_subw_bub = "중분류 가중치"
                                _fig_bub = px.scatter(
                                    _bubble_df_disp,
                                    x="Global Rank", y="Global Weight",
                                    size="_bubble_size", color=_color_bub,
                                    text=_label_col_bub,
                                    hover_data={
                                        _label_col_bub: True,
                                        _hover_sub_bub: True,
                                        _hover_subw_bub: ":.4f",
                                        "Global Weight": ":.4f",
                                        "Global Rank": True,
                                        "_bubble_size": False
                                    },
                                    title=_("소분류 글로벌 가중치 버블 차트 (버블이 클수록 중분류 비중 높음, 위로 갈수록 글로벌 가중치 높음)",
                                            "Sub-sub-Criteria Global Weight Bubble Chart (larger = higher sub weight, higher = higher global weight)"),
                                    color_discrete_sequence=px.colors.qualitative.Set2,
                                    size_max=55
                                )
                                _fig_bub.update_traces(textposition="top center", textfont_size=10)
                                _fig_bub.update_xaxes(
                                    title=_("종합 순위 (1위 = 가장 중요)", "Global Rank (1 = Most Important)"),
                                    dtick=1, autorange="reversed"
                                )
                                _fig_bub.update_yaxes(title=_("글로벌 가중치", "Global Weight"))
                                _fig_bub.update_layout(height=560, legend_title_text=_color_bub)
                                st.plotly_chart(_fig_bub, use_container_width=True)'''

if old_block in content:
    new_content = content.replace(old_block, new_block, 1)
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("SUCCESS: Bubble chart patch applied.")
else:
    print("ERROR: Old block not found.")
    # Debug: check for partial match
    import re
    m = re.search(r'전체 소분류 글로벌 가중치.*?plotly_chart.*?use_container_width=True\)', content, re.DOTALL)
    if m:
        print("Found partial match at:", m.start(), "-", m.end())
        print("Sample:", repr(content[m.start():m.start()+100]))

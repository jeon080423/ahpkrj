"""
app.py의 3계층 분석 결과 출력 블록을 5개 탭 UI로 교체하는 패치 스크립트.
4251~4281번 라인을 새 코드로 교체한다.
"""
import re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 교체 대상: run_ahp_analysis_v3 호출부터 st.stop() 까지
# 정규식으로 정확한 블록을 찾는다
old_block = '''                        if tier_level == 3:
                            success_v3 = False
                            msg_v3 = ""
                            final_df_v3 = None
                            output_res_v3 = None
                            with st.spinner(_(\"3계층(소분류 포함) AHP 종합 분석 수행 중...\", \"Performing 3-Tier AHP...\")):
                                from ahp_utils_v3 import run_ahp_analysis_v3
                                sub_sub_dfs = st.session_state.get(\"ahp_sub_sub_dfs\", {})
                                success_v3, msg_v3, final_df_v3, output_res_v3 = run_ahp_analysis_v3(
                                    df_main, sub_dfs, sub_sub_dfs, cr_threshold, max_iter_val, learning_rate, mean_method, ahp_method,
                                    process_single_sheet, fuzzy_ahp_analysis
                                )
                            
                            # Display results outside the spinner block so it terminates properly
                            if not success_v3:
                                st.error(msg_v3)
                                st.stop()
                            
                            st.success(_(\"✅ 3계층 AHP 분석이 성공적으로 완료되었습니다!\", \"✅ 3-Tier AHP Analysis successfully completed!\"))
                            st.dataframe(final_df_v3, use_container_width=True)
                            
                            st.download_button(
                                label=_(\"📥 3계층 AHP 종합분석 결과 다운로드 (.xlsx)\", \"📥 Download 3-Tier AHP Results (.xlsx)\"),
                                data=output_res_v3,
                                file_name=\"3Tier_AHP_Result.xlsx\",
                                mime=\"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet\",
                                type=\"primary\",
                                use_container_width=True
                            )
                            # 3계층은 3계층 전용 결과만 출력하고, 기존 2계층 차트 UI는 스킵
                            st.stop()'''

new_block = '''                        if tier_level == 3:
                            success_v3 = False
                            msg_v3 = ""
                            final_df_v3 = None
                            output_res_v3 = None
                            ui_data_v3 = {}
                            with st.spinner(_(\"3계층(소분류 포함) AHP 종합 분석 수행 중...\", \"Performing 3-Tier AHP...\")):
                                from ahp_utils_v3 import run_ahp_analysis_v3
                                sub_sub_dfs = st.session_state.get(\"ahp_sub_sub_dfs\", {})
                                success_v3, msg_v3, final_df_v3, output_res_v3, ui_data_v3 = run_ahp_analysis_v3(
                                    df_main, sub_dfs, sub_sub_dfs, cr_threshold, max_iter_val, learning_rate, mean_method, ahp_method,
                                    process_single_sheet, fuzzy_ahp_analysis
                                )

                            if not success_v3:
                                st.error(msg_v3)
                                st.stop()

                            st.success(_(\"✅ 3계층 AHP 분석이 성공적으로 완료되었습니다!\", \"✅ 3-Tier AHP Analysis successfully completed!\"))
                            st.markdown(_('<p style=\"color:red;font-weight:bold;font-size:0.95rem;margin:5px 0 10px;\">⚠️ 주의: 새로고침하거나 브라우저를 닫으면 결과가 리셋됩니다. 📑 결과 다운로드 탭에서 반드시 저장하세요.</p>',
                                          '<p style=\"color:red;font-weight:bold;font-size:0.95rem;margin:5px 0 10px;\">⚠️ Warning: Results reset on refresh. Download via 📑 Download Results tab.</p>'), unsafe_allow_html=True)

                            # --- 3계층 전용 5개 탭 UI ---
                            v3_unique_groups = ui_data_v3.get(\"unique_groups\", [])
                            v3_comparison_df  = ui_data_v3.get(\"comparison_df\", pd.DataFrame())
                            v3_anova_df       = ui_data_v3.get(\"anova_df\", pd.DataFrame())
                            v3_group_full_dfs = ui_data_v3.get(\"group_full_dfs\", {})
                            v3_indiv_df       = ui_data_v3.get(\"indiv_df\", pd.DataFrame())
                            v3_main_factors   = ui_data_v3.get(\"main_factors\", [])

                            tab3v1, tab3v2, tab3v3, tab3v4, tab3v5 = st.tabs([
                                _(\"🌐 종합 분석 (Global)\", \"🌐 Global Comprehensive Analysis\"),
                                _(\"👨\\u200d👩\\u200d👧\\u200d👦 그룹별 분석\", \"👨\\u200d👩\\u200d👧\\u200d👦 Group Analysis\"),
                                _(\"🧪 통계 검정 (ANOVA)\", \"🧪 Statistical Test (ANOVA)\"),
                                _(\"📊 시각화 센터\", \"📊 Visualization Center\"),
                                _(\"📑 결과 다운로드\", \"📑 Download Results\")
                            ])

                            # ─── Tab 1: 종합 분석 ────────────────────────────────────────────
                            with tab3v1:
                                st.subheader(_(\"🌐 3계층 종합 중요도 및 순위\", \"🌐 3-Tier Global Weights & Rankings\"))
                                if is_english:
                                    _disp_v3 = final_df_v3.rename(columns={
                                        \"대분류\": \"Main Criteria\",    \"대분류 가중치\": \"Main Weight\",
                                        \"중분류\": \"Sub-Criteria\",     \"중분류 가중치\": \"Sub Weight\",
                                        \"소분류\": \"Sub-sub-Criteria\", \"소분류 가중치\": \"Sub-sub Weight\",
                                        \"CR(대분류)\": \"CR(Main)\",     \"CI(대분류)\": \"CI(Main)\",
                                        \"CR(중분류)\": \"CR(Sub)\",      \"CI(중분류)\": \"CI(Sub)\",
                                        \"CR(소분류)\": \"CR(Sub-sub)\",  \"CI(소분류)\": \"CI(Sub-sub)\"
                                    })
                                else:
                                    _disp_v3 = final_df_v3
                                st.dataframe(_disp_v3.style.format(precision=4), use_container_width=True)

                                st.markdown(_(\"---\\n#### 📊 대분류별 소분류 항목 글로벌 가중치\",
                                              \"---\\n#### 📊 Sub-sub-Criteria Global Weights by Main Criteria\"))
                                _non_dummy_v3 = final_df_v3[~final_df_v3[\"소분류\"].str.endswith(\"_단일항목\", na=False)].copy()
                                if _non_dummy_v3.empty:
                                    _non_dummy_v3 = final_df_v3.copy()
                                for _mf_v3 in v3_main_factors:
                                    _mf_subset = _non_dummy_v3[_non_dummy_v3[\"대분류\"] == _mf_v3]
                                    if _mf_subset.empty:
                                        continue
                                    _mf_chart = _mf_subset.sort_values(\"Global Weight\", ascending=True).copy()
                                    if is_english:
                                        _mf_chart = _mf_chart.rename(columns={\"소분류\": \"Sub-sub-Criteria\"})
                                        _y_col_v3 = \"Sub-sub-Criteria\"
                                    else:
                                        _y_col_v3 = \"소분류\"
                                    _fig_v3_bar = px.bar(
                                        _mf_chart, y=_y_col_v3, x=\"Global Weight\",
                                        orientation=\"h\", text_auto=\".4f\",
                                        title=_(f\"[{_mf_v3}] 소분류 항목별 글로벌 가중치\", f\"[{_mf_v3}] Sub-sub-Criteria Global Weights\"),
                                        color_discrete_sequence=[\"#4F81BD\"]
                                    )
                                    _fig_v3_bar.update_layout(height=max(300, len(_mf_chart)*40+80), margin=dict(l=0,r=10,t=40,b=20))
                                    st.plotly_chart(_fig_v3_bar, use_container_width=True)

                            # ─── Tab 2: 그룹별 분석 ──────────────────────────────────────────
                            with tab3v2:
                                st.markdown(_(\"#### 그룹별 소분류 항목 글로벌 가중치 비교\",
                                              \"#### Sub-sub-Criteria Global Weight Comparison by Group\"))
                                if not v3_comparison_df.empty:
                                    if is_english:
                                        _disp_comp_v3 = v3_comparison_df.copy()
                                        _disp_comp_v3.rename(columns={
                                            \"대분류\": \"Main Criteria\", \"중분류\": \"Sub-Criteria\", \"소분류\": \"Sub-sub-Criteria\",
                                            \"종합평균(Overall)\": \"Overall Avg\", \"F-값\": \"F-Value\",
                                            \"유의성\": \"Significance\", \"사후검정(Tukey HSD)\": \"Post-Hoc (Tukey HSD)\"
                                        }, inplace=True)
                                        if \"Significance\" in _disp_comp_v3.columns:
                                            _disp_comp_v3[\"Significance\"] = _disp_comp_v3[\"Significance\"].map(
                                                {\"유의함\": \"Significant\", \"유의하지 않음\": \"Not Significant\"}).fillna(_disp_comp_v3[\"Significance\"])
                                    else:
                                        _disp_comp_v3 = v3_comparison_df
                                    st.dataframe(_disp_comp_v3.style.format(precision=4), use_container_width=True)
                                else:
                                    st.info(_(\"그룹별 비교 데이터가 없습니다.\", \"No group comparison data available.\"))

                                if len(v3_unique_groups) >= 2 and v3_group_full_dfs:
                                    st.markdown(_(\"---\\n#### 그룹별 대분류 가중치 비교\",
                                                  \"---\\n#### Main Criteria Weight Comparison by Group\"))
                                    _grp_main_rows = []
                                    for _grp_v3 in v3_unique_groups:
                                        if _grp_v3 not in v3_group_full_dfs:
                                            continue
                                        _g_df_v3 = v3_group_full_dfs[_grp_v3]
                                        for _mf_v3b in v3_main_factors:
                                            _mf_sub_b = _g_df_v3[_g_df_v3[\"대분류\"] == _mf_v3b]
                                            if not _mf_sub_b.empty:
                                                _grp_main_rows.append({
                                                    _(\"그룹\",\"Group\"): _grp_v3,
                                                    _(\"대분류\",\"Main Criteria\"): _mf_v3b,
                                                    \"Weight\": float(_mf_sub_b.iloc[0][\"대분류 가중치\"])
                                                })
                                    if _grp_main_rows:
                                        _grp_main_chart_df = pd.DataFrame(_grp_main_rows)
                                        _fig_grp_main = px.bar(
                                            _grp_main_chart_df,
                                            x=_(\"대분류\",\"Main Criteria\"), y=\"Weight\",
                                            color=_(\"그룹\",\"Group\"), barmode=\"group\", text_auto=\".4f\",
                                            title=_(\"그룹별 대분류 가중치 비교\", \"Main Criteria Weight Comparison by Group\")
                                        )
                                        st.plotly_chart(_fig_grp_main, use_container_width=True)

                            # ─── Tab 3: ANOVA ─────────────────────────────────────────────────
                            with tab3v3:
                                st.markdown(_(\"#### 집단 간 유의성 분석 (3계층 기준)\",
                                              \"#### Significance Analysis Between Groups (3-Tier Level)\"))
                                if not v3_anova_df.empty:
                                    if is_english:
                                        _disp_anova_v3 = v3_anova_df.copy()
                                        _disp_anova_v3.rename(columns={
                                            \"요인\": \"Factor/Criteria\", \"F-값\": \"F-Value\",
                                            \"유의성\": \"Significance\", \"사후검정(Tukey HSD)\": \"Post-Hoc (Tukey HSD)\"
                                        }, inplace=True)
                                        if \"Significance\" in _disp_anova_v3.columns:
                                            _disp_anova_v3[\"Significance\"] = _disp_anova_v3[\"Significance\"].map(
                                                {\"유의함\": \"Significant\", \"유의하지 않음\": \"Not Significant\"}).fillna(_disp_anova_v3[\"Significance\"])
                                        def _translate_ph_v3(v):
                                            if not isinstance(v, str): return v
                                            v = v.replace(\"전문가\",\"Expert\").replace(\"일반\",\"General\").replace(\"공무원\",\"Public Official\")
                                            v = v.replace(\" 차이 있음\",\" (Diff exists)\")
                                            v = v.replace(\"집단 간 구체적 차이 발견 못함\",\"No significant pairwise difference found\")
                                            v = v.replace(\"계산 오류\",\"Calculation Error\")
                                            return v
                                        if \"Post-Hoc (Tukey HSD)\" in _disp_anova_v3.columns:
                                            _disp_anova_v3[\"Post-Hoc (Tukey HSD)\"] = _disp_anova_v3[\"Post-Hoc (Tukey HSD)\"].apply(_translate_ph_v3)
                                    else:
                                        _disp_anova_v3 = v3_anova_df
                                    st.dataframe(_disp_anova_v3.style.format(precision=5), use_container_width=True)

                                    _sig_col_v3 = \"Significance\" if is_english else \"유의성\"
                                    _sig_val_v3 = \"Significant\" if is_english else \"유의함\"
                                    if _sig_col_v3 in _disp_anova_v3.columns:
                                        _sig_items_v3 = _disp_anova_v3[_disp_anova_v3[_sig_col_v3] == _sig_val_v3]
                                        if not _sig_items_v3.empty:
                                            _fcol_v3 = \"Factor/Criteria\" if is_english else \"요인\"
                                            _snames = \", \".join(_sig_items_v3[_fcol_v3].tolist())
                                            st.success(_(f\"✅ 유의한 차이 발견 항목: {_snames}\", f\"✅ Statistically significant factors: {_snames}\"))
                                        else:
                                            st.info(_(\"모든 항목에서 그룹 간 유의한 차이가 없습니다.\", \"No statistically significant group differences found.\"))
                                else:
                                    st.info(_(\"통계 검정을 위해 2개 이상의 그룹 데이터가 필요합니다.\",
                                              \"At least 2 group datasets are required for ANOVA.\"))

                            # ─── Tab 4: 시각화 센터 ──────────────────────────────────────────
                            with tab3v4:
                                st.markdown(_(\"#### 📊 3계층 AHP 시각화 센터\", \"#### 📊 3-Tier AHP Visualization Center\"))

                                st.markdown(_(\"**① 전체 소분류 글로벌 가중치 (대분류별 색 구분)**\",
                                              \"**① All Sub-sub-Criteria Global Weights (colored by Main Criteria)**\"))
                                _nd_v3 = final_df_v3[~final_df_v3[\"소분류\"].str.endswith(\"_단일항목\", na=False)].copy()
                                if _nd_v3.empty:
                                    _nd_v3 = final_df_v3.copy()
                                    _y_viz = \"중분류\"
                                else:
                                    _y_viz = \"소분류\"
                                _chart_all_v3 = _nd_v3.sort_values(\"Global Weight\", ascending=True).copy()
                                if is_english:
                                    _chart_all_v3 = _chart_all_v3.rename(columns={\"소분류\":\"Sub-sub-Criteria\",\"대분류\":\"Main Criteria\",\"중분류\":\"Sub-Criteria\"})
                                    _y_viz = \"Sub-sub-Criteria\" if _y_viz==\"소분류\" else \"Sub-Criteria\"
                                    _color_viz = \"Main Criteria\"
                                else:
                                    _color_viz = \"대분류\"
                                _fig_all_v3 = px.bar(
                                    _chart_all_v3, y=_y_viz, x=\"Global Weight\",
                                    orientation=\"h\", text_auto=\".4f\", color=_color_viz,
                                    title=_(\"소분류 전체 글로벌 가중치\", \"All Sub-sub-Criteria Global Weights\"),
                                    color_discrete_sequence=px.colors.qualitative.Set2
                                )
                                _fig_all_v3.update_layout(height=max(400, len(_chart_all_v3)*30+100))
                                st.plotly_chart(_fig_all_v3, use_container_width=True)

                                st.markdown(_(\"**② 계층 구조 트리맵 (대분류 > 중분류 > 소분류)**\",
                                              \"**② Hierarchical Treemap (Main > Sub > Sub-sub)**\"))
                                _tm_df = final_df_v3.copy()
                                _is_dummy = _tm_df[\"소분류\"].str.endswith(\"_단일항목\", na=False).all()
                                if _is_dummy:
                                    _tm_df[\"소분류\"] = _tm_df[\"중분류\"]
                                _tm_df = _tm_df[_tm_df[\"Global Weight\"] > 0].copy()
                                if not _tm_df.empty:
                                    try:
                                        if is_english:
                                            _tm_disp = _tm_df.rename(columns={\"대분류\":\"Main\",\"중분류\":\"Sub\",\"소분류\":\"Sub-sub\"})
                                            _path_cols = [\"Main\",\"Sub\",\"Sub-sub\"]
                                        else:
                                            _tm_disp = _tm_df
                                            _path_cols = [\"대분류\",\"중분류\",\"소분류\"]
                                        _fig_tree_v3 = px.treemap(
                                            _tm_disp, path=_path_cols, values=\"Global Weight\",
                                            color=\"Global Weight\", color_continuous_scale=\"Blues\",
                                            title=_(\"3계층 AHP 가중치 계층 트리맵\", \"3-Tier AHP Weight Hierarchical Treemap\")
                                        )
                                        _fig_tree_v3.update_traces(textinfo=\"label+percent parent\")
                                        _fig_tree_v3.update_layout(height=550)
                                        st.plotly_chart(_fig_tree_v3, use_container_width=True)
                                    except Exception as _e_tree:
                                        st.warning(_(f\"트리맵 생성 실패: {_e_tree}\", f\"Treemap generation failed: {_e_tree}\"))

                                if len(v3_unique_groups) >= 2 and v3_group_full_dfs:
                                    st.markdown(_(\"**③ 그룹별 대분류 중요도 레이더 차트**\",
                                                  \"**③ Main Criteria Importance Radar Chart by Group**\"))
                                    _radar_rows = []
                                    for _grp_rd in v3_unique_groups:
                                        if _grp_rd not in v3_group_full_dfs: continue
                                        _gdf_rd = v3_group_full_dfs[_grp_rd]
                                        for _mf_rd in v3_main_factors:
                                            _mf_rd_sub = _gdf_rd[_gdf_rd[\"대분류\"]==_mf_rd]
                                            _w_rd = float(_mf_rd_sub.iloc[0][\"대분류 가중치\"]) if not _mf_rd_sub.empty else 0.0
                                            _lbl_rd = str(_grp_rd).replace(\"전문가\",\"Expert\").replace(\"일반\",\"General\").replace(\"공무원\",\"Public Official\") if is_english else _grp_rd
                                            _radar_rows.append({_(\"그룹\",\"Group\"): _lbl_rd, _(\"항목\",\"Factor\"): _mf_rd, \"Weight\": _w_rd})
                                    if _radar_rows:
                                        _radar_df_v3 = pd.DataFrame(_radar_rows)
                                        _cats_rd = _radar_df_v3[_(\"항목\",\"Factor\")].unique().tolist()
                                        _fig_rd = go.Figure()
                                        _colors_rd = [\"#4F81BD\",\"#C0504D\",\"#9BBB59\",\"#8064A2\",\"#F79646\"]
                                        for _i_rd, _grp_rdn in enumerate(_radar_df_v3[_(\"그룹\",\"Group\")].unique()):
                                            _g_rd = _radar_df_v3[_radar_df_v3[_(\"그룹\",\"Group\")]==_grp_rdn]
                                            _vals_rd = [_g_rd[_g_rd[_(\"항목\",\"Factor\")]==c][\"Weight\"].values[0] if len(_g_rd[_g_rd[_(\"항목\",\"Factor\")]==c])>0 else 0 for c in _cats_rd]
                                            _vals_cl = _vals_rd + [_vals_rd[0]]
                                            _cats_cl = _cats_rd + [_cats_rd[0]]
                                            _fig_rd.add_trace(go.Scatterpolar(r=_vals_cl, theta=_cats_cl, fill=\"toself\", name=_grp_rdn, line_color=_colors_rd[_i_rd % len(_colors_rd)], opacity=0.7))
                                        _fig_rd.update_layout(
                                            polar=dict(radialaxis=dict(visible=True, range=[0, max(0.01, _radar_df_v3[\"Weight\"].max()*1.2)])),
                                            showlegend=True,
                                            title=_(\"그룹별 대분류 중요도 패턴\", \"Main Criteria Importance Pattern by Group\"),
                                            height=450
                                        )
                                        st.plotly_chart(_fig_rd, use_container_width=True)

                            # ─── Tab 5: 결과 다운로드 ────────────────────────────────────────
                            with tab3v5:
                                st.markdown(_(\"### 📑 3계층 AHP 종합분석 결과 다운로드\",
                                              \"### 📑 Download 3-Tier AHP Comprehensive Analysis Results\"))
                                st.download_button(
                                    label=_(\"📥 3계층 AHP 종합분석 결과 다운로드 (.xlsx)\", \"📥 Download 3-Tier AHP Results (.xlsx)\"),
                                    data=output_res_v3,
                                    file_name=\"3Tier_AHP_Result.xlsx\",
                                    mime=\"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet\",
                                    type=\"primary\",
                                    use_container_width=True
                                )
                                st.info(_(\"📋 엑셀 파일에는 종합분석, 그룹비교, 계층별 상세행렬, CR 분포 등 전체 분석 결과가 포함됩니다.\",
                                          \"📋 The Excel file contains all results: comprehensive summary, group comparison, detailed matrices per tier, and CR distribution.\"))

                            # 3계층 처리 완료 – 기존 2계층 UI 스킵
                            st.stop()'''

if old_block in content:
    new_content = content.replace(old_block, new_block, 1)
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("SUCCESS: Patch applied.")
else:
    # Try to find it more leniently
    # Count occurrence
    import re
    matches = [(m.start(), m.end()) for m in re.finditer(r'if tier_level == 3:\s*\n\s*success_v3 = False', content)]
    print(f"Pattern not found. Found tier_level==3 blocks at positions: {matches}")
    print("First 200 chars of old_block:", repr(old_block[:200]))
    
    # Also check if ahp_utils_v3 call pattern exists
    pattern = r'success_v3, msg_v3, final_df_v3, output_res_v3 = run_ahp_analysis_v3'
    if re.search(pattern, content):
        print("Found old 4-tuple return call")
    else:
        print("Old 4-tuple call NOT found")

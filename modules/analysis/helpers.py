"""Analysis module helpers - extracted from standard_app.py"""
# Auto-generated 2026-11-01

import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import io
import sqlite3
import datetime
import base64
import itertools
import random
import traceback
import re
import os, sys, time, json, hashlib
try:
    import xlsxwriter
except ImportError:
    xlsxwriter = None

class LazyFunction:
    def __init__(self, module_name, func_name):
        self.module_name = module_name
        self.func_name = func_name
        self._func = None
    def __call__(self, *args, **kwargs):
        if self._func is None:
            import importlib
            module = importlib.import_module(self.module_name)
            self._func = getattr(module, self.func_name)
        return self._func(*args, **kwargs)

# Lazy-loaded heavy dependencies
gmean = LazyFunction('scipy.stats', 'gmean')
ttest_rel = LazyFunction('scipy.stats', 'ttest_rel')
f_oneway = LazyFunction('scipy.stats', 'f_oneway')
write_custom_ahp_table = LazyFunction('ahp_table_utils', 'write_custom_ahp_table')
add_borders_to_data = LazyFunction('ahp_table_utils', 'add_borders_to_data')

STATSMODELS_AVAILABLE = True

def _(ko, en, ja=None):
    import streamlit as st
    lang = st.session_state.get('lang', 'ko')
    if lang == 'ja' and ja is not None:
        return ja
    return en if lang == 'en' else ko

def _load_example_file(path):
    """Load sample/example Excel files with caching to prevent rerun issues."""
    try:
        import os
        base_dir = os.path.dirname(__file__)
        full_path = os.path.join(base_dir, path)
        with open(full_path, "rb") as f:
            return f.read(), None
    except Exception as e:
        return b"", str(e)

def apply_sample_limit(df, source_label=""):
    """[2026-10-19] 등급별 분석 표본 수 제한 헬퍼 (방어 다층화용).

    - Free: 최대 3표본 (처음 접수된 3행만 분석)
    - Basic: 최대 10표본 (처음 접수된 10행만 분석)
    - Standard/Pro: 무제한
    유료 전환 시 user_role/plan_type이 바뀌면 자동으로 제한 해제됨 (별도 해제 로직 불필요).
    source_label: 경고 메시지에 표시할 데이터 출처 (예: "온라인 설문 연동", "엑셀 업로드").
    """
    if df is None or getattr(df, 'empty', True):
        return df
    tier = get_current_tier()
    limit = 3 if tier == 'Free' else (10 if tier == 'Basic' else None)
    if limit is not None and len(df) > limit:
        df = df.head(limit).copy()
        src = f" ({source_label})" if source_label else ""
        if tier == 'Free':
            st.warning(_(f"⚠️ 무료 사용자는{src} 최대 3표본까지만 분석할 수 있습니다. 처음 접수된 3명(행)의 응답만 분석에 사용됩니다.",
                         f"⚠️ Free users can only analyze up to 3 samples{src}. Only the first 3 responses will be analyzed."))
        else:
            st.warning(_(f"⚠️ 베이직 요금제는{src} 최대 10표본까지만 분석할 수 있습니다. 처음 접수된 10명(행)의 응답만 분석에 사용됩니다.",
                         f"⚠️ Basic users can only analyze up to 10 samples{src}. Only the first 10 responses will be analyzed."))
    return df

def build_alternative_excel(alt_result):
    """대안 평가 전용 엑셀 생성 (단독 다운로드용).

    시트 구성은 write_alternative_sheets를 사용하므로 본 결과 파일(AHP_Result.xlsx)에
    통합되는 대안 시트와 동일하다.
    """
    import io as _io
    buf = _io.BytesIO()
    import xlsxwriter
    wb = xlsxwriter.Workbook(buf, {"in_memory": True})
    write_alternative_sheets(wb, alt_result)
    wb.close()
    buf.seek(0)
    return buf.getvalue()

def calculate_anova_and_posthoc(full_data):
    results = []
    unique_factors = full_data['Factor'].unique()
    
    for factor in unique_factors:
        subset = full_data[full_data['Factor'] == factor]
        groups = [group['Global_Weight'].values for name, group in subset.groupby('Type')]
        
        if len(groups) < 2:
            continue
            
        f_stat, p_val = f_oneway(*groups)
        
        row = {
            "요인": factor,
            "F-값": f_stat,
            "P-Value": p_val,
            "유의성": "유의함" if p_val < 0.05 else "유의하지 않음",
            "사후검정(Tukey HSD)": ""
        }
        
        if p_val < 0.05 and STATSMODELS_AVAILABLE:
            try:
                tukey = pairwise_tukeyhsd(endog=subset['Global_Weight'], groups=subset['Type'], alpha=0.05)
                tukey_df = pd.DataFrame(data=tukey.summary().data[1:], columns=tukey.summary().data[0])
                sig_pairs = tukey_df[tukey_df['reject'] == True]
                if not sig_pairs.empty:
                    pairs_str = []
                    for idx_row, r in sig_pairs.iterrows():
                        pairs_str.append(f"{r['group1']} vs {r['group2']}")
                    row["사후검정(Tukey HSD)"] = ", ".join(pairs_str) + " 차이 있음"
                else:
                    row["사후검정(Tukey HSD)"] = "집단 간 구체적 차이 발견 못함"
            except Exception as e:
                row["사후검정(Tukey HSD)"] = "계산 오류"
        
        results.append(row)
        
    return pd.DataFrame(results)

def calculate_consistency(matrix, method='geometric'):
    n = matrix.shape[0]
    if n <= 2: return 0.0, 0.0, n
    weights = calculate_weights(matrix, method)
    weighted_sum = matrix.dot(weights)
    weights_safe = weights.copy()
    weights_safe[weights_safe == 0] = 1e-10
    lambda_values = weighted_sum / weights_safe
    lambda_max = lambda_values.mean()
    ci = (lambda_max - n) / (n - 1)
    ri = get_ri(n)
    cr = ci / ri if ri > 0 else 0.0
    return cr, ci, lambda_max

def calculate_expert_consensus(results_df, factors):
    """
    results_df: Weight_{factor} 컬럼을 포함한 응답자별 가중치 DataFrame
    factors: 평가기준명 리스트
    반환: dict with summary, top_votes, kendall_w, kendall_p, sentences
    """
    import numpy as _np

    weight_cols = [f"Weight_{f}" for f in factors]
    # Weight 컬럼이 없는 요인 제외
    avail = [(f, c) for f, c in zip(factors, weight_cols) if c in results_df.columns]
    if not avail or len(results_df) < 2:
        return None

    factors_a, cols_a = zip(*avail)
    w = results_df[list(cols_a)].to_numpy(dtype=float)
    n_resp = w.shape[0]

    # --- 섹션 1: 항목별 기술통계 ---
    means = _np.nanmean(w, axis=0)
    sds = _np.nanstd(w, axis=0, ddof=1) if n_resp > 1 else _np.zeros_like(means)
    cvs = _np.divide(sds, means, out=_np.zeros_like(sds), where=means != 0)
    maxs = _np.nanmax(w, axis=0)
    mins = _np.nanmin(w, axis=0)
    ranges = maxs - mins

    def _judge(cv):
        if cv < 0.15:
            return "높음"
        elif cv < 0.30:
            return "보통"
        return "낮음"

    summary_rows = []
    for i, f in enumerate(factors_a):
        summary_rows.append({
            "평가기준": f,
            "평균 가중치": round(float(means[i]), 3),
            "표준편차": round(float(sds[i]), 3),
            "변이계수(CV)": round(float(cvs[i]), 3),
            "최고값": round(float(maxs[i]), 3),
            "최저값": round(float(mins[i]), 3),
            "범위": round(float(ranges[i]), 3),
            "일치도 판정": _judge(float(cvs[i])),
        })

    # --- 섹션 2: 1위 득표율 ---
    top_idx = _np.nanargmax(w, axis=1)
    vote_counts = _np.bincount(top_idx, minlength=len(factors_a))
    order = _np.argsort(-vote_counts)
    top_rows = []
    for rank, oi in enumerate(order, start=1):
        cnt = int(vote_counts[oi])
        top_rows.append({
            "순위": rank,
            "평가기준": factors_a[oi],
            "1위 선택 인원": cnt,
            "득표율": round(cnt / n_resp, 3),
        })

    # --- 섹션 3: Kendall's W ---
    # 가중치를 순위(1위=1)로 변환 (동점 평균 순위)
    ranks = _np.empty_like(w)
    for r in range(n_resp):
        row = w[r]
        # 내림차순 순위 (가중치가 클수록 1위)
        order_r = _np.argsort(-row)
        rank_vals = _np.empty_like(order_r, dtype=float)
        # 동점 처리
        sorted_row = row[order_r]
        i = 0
        while i < len(sorted_row):
            j = i
            while j + 1 < len(sorted_row) and sorted_row[j + 1] == sorted_row[i]:
                j += 1
            avg_rank = (i + j) / 2 + 1
            rank_vals[order_r[i:j + 1]] = avg_rank
            i = j + 1
        ranks[r] = rank_vals

    k = len(factors_a)
    R_j = _np.nansum(ranks, axis=0)
    R_bar = _np.nanmean(R_j)
    S = _np.nansum((R_j - R_bar) ** 2)
    # 동점 보정
    T = 0.0
    for r in range(n_resp):
        vals, counts = _np.unique(ranks[r], return_counts=True)
        T += _np.sum(counts ** 3 - counts)
    denom = n_resp ** 2 * (k ** 3 - k) - n_resp * T
    kendall_w = (12 * S / denom) if denom != 0 else 0.0
    # 카이제곱 근사로 p-value
    try:
        from scipy.stats import chi2 as _chi2
        chi_stat = n_resp * (k - 1) * kendall_w
        kendall_p = float(_chi2.sf(chi_stat, k - 1))
    except Exception:
        kendall_p = None

    def _w_judge(v):
        if v >= 0.7:
            return "상당한 합의"
        elif v >= 0.5:
            return "중간 수준 합의"
        elif v >= 0.3:
            return "약한 합의"
        return "합의 부족"

    # --- 자동 해석 문장 ---
    cv_max_i = int(_np.nanargmax(cvs))
    cv_min_i = int(_np.nanargmin(cvs))
    s1 = (f"{factors_a[cv_min_i]}(CV={cvs[cv_min_i]:.3f})은 전문가 의견이 잘 모인 항목이며, "
          f"{factors_a[cv_max_i]}(CV={cvs[cv_max_i]:.3f})은 의견이 분산되어 해석에 유의가 필요합니다.")
    top1 = top_rows[0]
    s2 = (f"전문가 {n_resp}명 중 {top1['1위 선택 인원']}명({top1['득표율']*100:.1f}%)이 "
          f"'{top1['평가기준']}'을 최우선 기준으로 선택했습니다.")
    p_str = f"(p={kendall_p:.3f})" if kendall_p is not None else ""
    s3 = (f"Kendall's W = {kendall_w:.3f}로 전문가 간 {_w_judge(kendall_w)}이 확인되었습니다{p_str}.")

    return {
        "n_resp": n_resp,
        "summary": summary_rows,
        "top_votes": top_rows,
        "kendall_w": round(float(kendall_w), 3),
        "kendall_p": round(float(kendall_p), 3) if kendall_p is not None else None,
        "w_judge": _w_judge(float(kendall_w)),
        "s1": s1, "s2": s2, "s3": s3,
    }

def calculate_pairwise_ttest(df, factors):
    n = len(factors)
    p_values = pd.DataFrame(index=factors, columns=factors)
    weight_cols = [f"Weight_{f}" for f in factors]
    for i in range(n):
        for j in range(n):
            if i == j:
                p_values.iloc[i, j] = 1.0
            else:
                col1 = weight_cols[i]
                col2 = weight_cols[j]
                if col1 in df.columns and col2 in df.columns and len(df) > 1:
                    try:
                        _unused_t, p = ttest_rel(df[col1], df[col2], nan_policy='omit')
                        p_values.iloc[i, j] = p
                    except:
                        p_values.iloc[i, j] = np.nan
                else:
                    p_values.iloc[i, j] = np.nan
    return p_values

def calculate_weights(matrix, method='geometric'):
    if method == 'arithmetic':
        col_sum = matrix.sum(axis=0)
        col_sum[col_sum == 0] = 1
        normalized_matrix = matrix / col_sum
        weights = normalized_matrix.mean(axis=1)
    else:
        geom_means = gmean(matrix, axis=1)
        weights = geom_means / geom_means.sum()
    return weights

def compute_alternative_analysis(df_main, sub_dfs, sub_sub_dfs, alt_dfs, model,
                                 cr_threshold, max_iter, learning_rate,
                                 method='geometric', ahp_method='traditional'):
    """[2026-10-20] 대안 평가 종합 분석.

    개인별 최하위(leaf) 요인의 글로벌 가중치 × 잎별 대안 국지 가중치를 합산해
    응답자별 대안 종합점수를 구하고, 그룹 종합점수는 개인 점수의 평균(산술/기하)으로 집계한다.
    모든 잎의 대안 응답과 기준 가중치가 모두 있는 응답자만 포함한다.
    반환: dict 또는 None(분석 불가 시)
    """
    try:
        from survey_manager_v3 import get_leaf_criteria_v3
    except Exception:
        return None
    alternatives = model.get("alternatives", []) or []
    if len(alternatives) < 2 or not alt_dfs:
        return None
    leaves = get_leaf_criteria_v3(model)
    if not leaves:
        return None

    def _run(df):
        if df is None or len(df) == 0:
            return None, []
        res, facs, _exc, _edf = process_single_sheet(df, cr_threshold, max_iter, learning_rate, method, ahp_method)
        return res, facs

    def _run_full(df):
        """대안 잎 전용: 제외 건수·제외 df·집단 종합 행렬까지 함께 반환 (엑셀 상세 표용)."""
        if df is None or len(df) == 0:
            return None, [], 0, None, None, None, None
        res, facs, exc_cnt, exc_df = process_single_sheet(df, cr_threshold, max_iter, learning_rate, method, ahp_method)
        gmat, gcr, gci = None, None, None
        if res is not None and not res.empty and "Matrix_Object" in res.columns:
            try:
                _mats = np.stack(res["Matrix_Object"].values)
                gmat = np.mean(_mats, axis=0) if method == 'arithmetic' else gmean(_mats, axis=0)
                gcr, gci, _lam = calculate_consistency(gmat, method)
            except Exception:
                gmat, gcr, gci = None, None, None
        return res, facs, exc_cnt, exc_df, gmat, gcr, gci

    def _indiv_weights(res):
        out = {}
        if res is None or res.empty:
            return out
        for _, r in res.iterrows():
            rid = str(r.get("ID", ""))
            out[rid] = {c[7:]: float(r[c]) for c in res.columns if c.startswith("Weight_")}
        return out

    def _group_weights(res, facs):
        if res is None or res.empty or not facs:
            return {}
        wcols = [f"Weight_{f}" for f in facs]
        if method == 'arithmetic':
            s = res[wcols].mean(axis=0)
        else:
            s = pd.Series(gmean(res[wcols].values, axis=0), index=wcols)
        tot = float(s.sum())
        if tot <= 0:
            return {}
        return {f: float(s[f"Weight_{f}"]) / tot for f in facs}

    def _group_cr(res):
        """집단 종합 행렬(개인 행렬 집계)의 CR — 보고서 표1·검증 요약용."""
        try:
            mats = np.stack(res["Matrix_Object"].values)
            gm = np.mean(mats, axis=0) if method == 'arithmetic' else gmean(mats, axis=0)
            cr, _ci, _lam = calculate_consistency(gm, method)
            return float(cr)
        except Exception:
            return None

    # 1) 기준 가중치 (개인별·그룹)
    main_res, main_facs = _run(df_main)
    if main_res is None or main_res.empty:
        return None
    main_indiv = _indiv_weights(main_res)
    main_group = _group_weights(main_res, main_facs)
    main_cr = _group_cr(main_res)

    sub_indiv, sub_group, sub_cr = {}, {}, {}
    for parent, sdf in (sub_dfs or {}).items():
        res, facs = _run(sdf)
        if res is not None and not res.empty:
            sub_indiv[parent] = _indiv_weights(res)
            sub_group[parent] = _group_weights(res, facs)
            sub_cr[parent] = _group_cr(res)
    ss_indiv, ss_group, ss_cr = {}, {}, {}
    for parent, sdf in (sub_sub_dfs or {}).items():
        res, facs = _run(sdf)
        if res is not None and not res.empty:
            ss_indiv[parent] = _indiv_weights(res)
            ss_group[parent] = _group_weights(res, facs)
            ss_cr[parent] = _group_cr(res)

    subs_map = model.get("subs", {}) or {}
    ss_map = model.get("sub_subs", {}) or {}

    def _leaf_chain(leaf):
        for mc in model.get("main", []):
            subs = subs_map.get(mc, []) or []
            if not subs:
                if leaf == mc:
                    return (mc, None, False)
                continue
            for sc in subs:
                ss = ss_map.get(sc, []) or []
                if len(ss) >= 2:
                    if leaf in ss:
                        return (mc, sc, True)
                elif leaf == sc:
                    return (mc, sc, False)
        return None

    # 2) 잎 글로벌 가중치 (개인별·그룹)
    indiv_leaf_w = {}
    for rid, mw in main_indiv.items():
        indiv_leaf_w[rid] = {}
        for leaf in leaves:
            chain = _leaf_chain(leaf)
            if not chain:
                continue
            mc, sc, is_ss = chain
            w = mw.get(mc, 0.0)
            if sc is not None:
                w *= sub_indiv.get(mc, {}).get(rid, {}).get(sc, 0.0)
                if is_ss:
                    w *= ss_indiv.get(sc, {}).get(rid, {}).get(leaf, 0.0)
            indiv_leaf_w[rid][leaf] = w
    group_leaf_w = {}
    for leaf in leaves:
        chain = _leaf_chain(leaf)
        if not chain:
            continue
        mc, sc, is_ss = chain
        w = main_group.get(mc, 0.0)
        if sc is not None:
            w *= sub_group.get(mc, {}).get(sc, 0.0)
            if is_ss:
                w *= ss_group.get(sc, {}).get(leaf, 0.0)
        group_leaf_w[leaf] = w

    # 3) 대안 가중치 (개인별·잎별, 그룹·잎별)
    alt_indiv, alt_group = {}, {}
    leaf_detail = {}
    for leaf in leaves:
        adf = alt_dfs.get(leaf)
        if adf is None:
            return None
        res, facs, exc_cnt, exc_df, gmat, gcr, gci = _run_full(adf)
        if res is None or res.empty:
            return None
        alt_indiv[leaf] = _indiv_weights(res)
        alt_group[leaf] = _group_weights(res, facs)
        leaf_detail[leaf] = {"res": res, "factors": facs, "excluded_count": exc_cnt,
                             "excluded_df": exc_df, "group_matrix": gmat,
                             "group_cr": gcr, "group_ci": gci}

    # 4) 개인별 종합점수 (모든 잎 완비 응답자만)
    type_map = {}
    if main_res is not None and "Type" in main_res.columns:
        for _, r in main_res.iterrows():
            type_map[str(r.get("ID", ""))] = r.get("Type", "")
    indiv_rows = []
    for rid, leaf_ws in indiv_leaf_w.items():
        if any(leaf not in alt_indiv or rid not in alt_indiv[leaf] for leaf in leaves):
            continue
        scores = {a: 0.0 for a in alternatives}
        for leaf in leaves:
            gw = leaf_ws.get(leaf, 0.0)
            for a in alternatives:
                scores[a] += gw * alt_indiv[leaf][rid].get(a, 0.0)
        tot = sum(scores.values())
        if tot > 0:
            scores = {a: v / tot for a, v in scores.items()}
        top_alt = max(scores, key=scores.get) if scores else ""
        indiv_rows.append({"ID": rid, "Type": type_map.get(rid, ""),
                           **{f"Score_{a}": scores[a] for a in alternatives},
                           "1위 대안": top_alt})
    indiv_df = pd.DataFrame(indiv_rows)
    if indiv_df.empty:
        return None

    # 5) 그룹 종합점수 (개인 점수 평균 후 정규화)
    score_cols = [f"Score_{a}" for a in alternatives]
    if method == 'arithmetic':
        grp_s = indiv_df[score_cols].mean(axis=0)
    else:
        grp_s = pd.Series(gmean(indiv_df[score_cols].values, axis=0), index=score_cols)
    tot = float(grp_s.sum())
    group_scores = {a: (float(grp_s[f"Score_{a}"]) / tot if tot > 0 else 0.0) for a in alternatives}

    # 잎별 직속 상위 내 부분가중치와 계층 경로 (보고서 표1용)
    leaf_local, leaf_chain_map = {}, {}
    for leaf in leaves:
        _ch = _leaf_chain(leaf)
        leaf_chain_map[leaf] = list(_ch) if _ch else []
        if not _ch:
            leaf_local[leaf] = None
            continue
        _mc, _sc, _is_ss = _ch
        if _is_ss:
            leaf_local[leaf] = (ss_group.get(_sc, {}) or {}).get(leaf)
        elif _sc:
            leaf_local[leaf] = (sub_group.get(_mc, {}) or {}).get(leaf)
        else:
            leaf_local[leaf] = 1.0

    return {
        "alternatives": alternatives,
        "leaves": leaves,
        "group_scores": group_scores,
        "indiv_df": indiv_df,
        "leaf_alt_group": alt_group,
        "leaf_group_global": group_leaf_w,
        "n_used": len(indiv_df),
        # [2026-10-21] 엑셀 상세화용 추가 정보 (구 결과 dict와 하위 호환: 빌더에서 .get 사용)
        "leaf_alt_indiv": alt_indiv,
        "leaf_detail": leaf_detail,
        "settings": {"cr_threshold": cr_threshold, "method": method, "ahp_method": ahp_method},
        # [2026-10-21 통합 보고서용] 요인 그룹 가중치·CR·잎 경로 (표1/계층구조/민감도 분석용)
        "factor_group": {
            "main_weights": main_group, "main_cr": main_cr,
            "sub_weights": sub_group, "sub_cr": sub_cr,
            "ss_weights": ss_group, "ss_cr": ss_cr,
            "leaf_local": leaf_local, "leaf_chain": leaf_chain_map,
        },
        "model": {"main": model.get("main", []), "subs": model.get("subs", {}), "sub_subs": model.get("sub_subs", {})},
    }

def create_sample_excel():
    output = io.BytesIO()
    is_en = (st.session_state.get('lang', 'ko') == 'en')
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        if is_en:
            main_cols = ["ID", "Type", "Governance_Planning", "Governance_Feasibility", "Governance_Effectiveness", 
                          "Planning_Feasibility", "Planning_Effectiveness", "Feasibility_Effectiveness"]
            main_data = [
                [1, "Expert", -3, -3, 3, 1, 1, 1],                
                [2, "Expert", -5, 3, 3, 3, 3, 3],        
                [3, "General", 5, 1, 3, -5, -5, -3]
            ]
            df_main = pd.DataFrame(main_data, columns=main_cols)
            df_main.to_excel(writer, sheet_name="Main_Criteria", index=False)
            
            inconsistent_pattern = [
                [1, "Expert", 1, -3, 1],
                [2, "Expert", -3, -3, -3],
                [3, "General", 3, -3, 1]
            ]
            sub1_cols = ["ID", "Type", "AdminSupport_Community", "AdminSupport_PM", "Community_PM"]
            pd.DataFrame(inconsistent_pattern, columns=sub1_cols).to_excel(writer, sheet_name="Governance", index=False)
            sub2_cols = ["ID", "Type", "IssueFit_AlternativeFit", "IssueFit_GoalClarity", "AlternativeFit_GoalClarity"]
            pd.DataFrame(inconsistent_pattern, columns=sub2_cols).to_excel(writer, sheet_name="Planning", index=False)
            sub3_cols = ["ID", "Type", "LandAcquisition_ProjectDetail", "LandAcquisition_CostFit", "ProjectDetail_CostFit"]
            pd.DataFrame(inconsistent_pattern, columns=sub3_cols).to_excel(writer, sheet_name="Feasibility", index=False)
            sub4_cols = ["ID", "Type", "Economic_Social", "Economic_Performance", "Social_Performance"]
            pd.DataFrame(inconsistent_pattern, columns=sub4_cols).to_excel(writer, sheet_name="Effectiveness", index=False)
        else:
            main_cols = ["ID", "Type", "거버넌스_계획타당성", "거버넌스_실현가능성", "거버넌스_사업효과", 
                          "계획타당성_실현가능성", "계획타당성_사업효과", "실현가능성_사업효과"]
            main_data = [
                [1, "전문가",-3,	-3, 3, 1, 1, 1],                
                [2, "전문가", -5, 3, 3, 3, 3, 3],        
                [3, "일반", 5, 1, 3, -5, -5, -3]
            ]
            df_main = pd.DataFrame(main_data, columns=main_cols)
            df_main.to_excel(writer, sheet_name="Main_Criteria", index=False)
            
            inconsistent_pattern = [
                [1, "전문가", 1, -3, 1],
                [2, "전문가", -3, -3, -3],
                [3, "일반", 3, -3, 1]
            ]
            sub1_cols = ["ID", "Type", "행정지원_지역공동체", "행정지원_총괄사업관리자", "지역공동체_총괄사업관리자"]
            pd.DataFrame(inconsistent_pattern, columns=sub1_cols).to_excel(writer, sheet_name="거버넌스", index=False)
            sub2_cols = ["ID", "Type", "현안적정성_대안적정성", "현안적정성_목표구체성", "대안적정성_목표구체성"]
            pd.DataFrame(inconsistent_pattern, columns=sub2_cols).to_excel(writer, sheet_name="계획타당성", index=False)
            sub3_cols = ["ID", "Type", "부지확보_사업구체화", "부지확보_사업비적정성", "사업구체화_사업비적정성"]
            pd.DataFrame(inconsistent_pattern, columns=sub3_cols).to_excel(writer, sheet_name="실현가능성", index=False)
            sub4_cols = ["ID", "Type", "경제적효과_사회적효과", "경제적효과_성과관리", "사회적효과_성과관리"]
            pd.DataFrame(inconsistent_pattern, columns=sub4_cols).to_excel(writer, sheet_name="사업효과", index=False)
    output.seek(0)
    return output

def create_sample_excel_v3():
    output = io.BytesIO()
    is_en = (st.session_state.get('lang', 'ko') == 'en')
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        if is_en:
            main_list = ["Functionality", "Design", "Economy"]
            subs = {"Functionality": ["Hardware", "Software"], "Design": ["Appearance", "Usability"], "Economy": ["Device Price", "Maintenance"]}
            sub_subs = {"Hardware": ["Camera", "Battery", "Processor"], "Software": ["OS", "Default Apps"], "Appearance": ["Color", "Material"], "Usability": [], "Device Price": ["Lump Sum", "Installment"], "Maintenance": ["Plan", "Repair"]}
        else:
            main_list = ["기능성", "디자인", "경제성"]
            subs = {"기능성": ["하드웨어", "소프트웨어"], "디자인": ["외관", "편의성"], "경제성": ["단말기가격", "유지비용"]}
            sub_subs = {"하드웨어": ["카메라", "배터리", "프로세서"], "소프트웨어": ["운영체제", "기본앱"], "외관": ["색상", "재질"], "편의성": [], "단말기가격": ["일시불", "할부"], "유지비용": ["통신요금", "AS비용"]}
            
        def _get_dummy_data(cols, num_respondents=3):
            # cols contains ["ID", "Type", pair1, pair2...]
            data = []
            for i in range(num_respondents):
                row = [i+1, "전문가" if not is_en else "Expert"]
                for _ in range(len(cols)-2):
                    row.append(int(np.random.choice([1, 3, 5, -3, -5])))
                data.append(row)
            return data
            
        main_pairs = list(itertools.combinations(main_list, 2))
        main_cols = ["ID", "Type"] + [f"{a}_{b}" for a, b in main_pairs]
        df_main = pd.DataFrame(_get_dummy_data(main_cols), columns=main_cols)
        df_main.to_excel(writer, sheet_name="Main_Criteria", index=False)
        
        for i, mc in enumerate(main_list):
            sub_list = subs.get(mc, [])
            if len(sub_list) < 2:
                df_sub = pd.DataFrame(columns=["ID", "Type"])
            else:
                sub_pairs = list(itertools.combinations(sub_list, 2))
                sub_cols = ["ID", "Type"] + [f"{a}_{b}" for a, b in sub_pairs]
                df_sub = pd.DataFrame(_get_dummy_data(sub_cols), columns=sub_cols)
            df_sub.to_excel(writer, sheet_name=mc[:31], index=False)
            
            for sub_c in sub_list:
                ss_list = sub_subs.get(sub_c, [])
                if len(ss_list) < 2:
                    df_ss = pd.DataFrame(columns=["ID", "Type"])
                else:
                    ss_pairs = list(itertools.combinations(ss_list, 2))
                    ss_cols = ["ID", "Type"] + [f"{a}_{b}" for a, b in ss_pairs]
                    df_ss = pd.DataFrame(_get_dummy_data(ss_cols), columns=ss_cols)
                df_ss.to_excel(writer, sheet_name=f"{mc[:15]}_{sub_c[:15]}", index=False)
                
    output.seek(0)
    return output.getvalue()

def delete_analysis(analysis_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("DELETE FROM saved_analyses WHERE id=?", (analysis_id,))
    conn.commit()
    conn.close()

def fuzzy_ahp_analysis(matrix):
    n = matrix.shape[0]
    fuzzy_mat = np.zeros((n, n, 3))
    for i in range(n):
        for j in range(n):
            if i == j: fuzzy_mat[i,j] = (1.0, 1.0, 1.0)
            else: fuzzy_mat[i,j] = saaty_to_fuzzy(matrix[i,j])
    row_sums = []
    for i in range(n): 
        row_sums.append((sum(fuzzy_mat[i,:,0]), sum(fuzzy_mat[i,:,1]), sum(fuzzy_mat[i,:,2])))
    t_l, t_m, t_u = sum(x[0] for x in row_sums), sum(x[1] for x in row_sums), sum(x[2] for x in row_sums)
    if t_l == 0: return np.ones(n)/n, row_sums
    Si = []
    for (l, m, u) in row_sums: 
        Si.append((l/t_u if t_u!=0 else 0.0, m/t_m if t_m!=0 else 0.0, u/t_l if t_l!=0 else 0.0))
    crisp_w = np.array([(l*m*u)**(1/3) for (l,m,u) in Si])
    norm_w = crisp_w / crisp_w.sum() if crisp_w.sum() != 0 else np.ones(n)/n
    return norm_w, Si

def get_analysis_file(analysis_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT filename, file_data FROM saved_analyses WHERE id=?", (analysis_id,))
    result = c.fetchone()
    conn.close()
    return result

def get_current_tier():
    if not st.session_state.get('user_id') or st.session_state.get('user_role') in ['temp', 'free', None]:
        return 'Free'
    if st.session_state.get('user_role') == 'admin':
        return 'Pro'
    pt = st.session_state.get('plan_type') or ''
    if 'Pro' in pt: return 'Pro'
    elif 'Standard' in pt: return 'Standard'
    elif 'Basic' in pt: return 'Basic'
    return 'Free'

def get_ri(n):
    ri_dict = {1: 0.00, 2: 0.00, 3: 0.58, 4: 0.90, 5: 1.12, 6: 1.24, 7: 1.32, 8: 1.41, 9: 1.45, 10: 1.49}
    return ri_dict.get(n, 1.49)

def get_user_analyses(user_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT id, filename, save_date FROM saved_analyses WHERE user_id=? ORDER BY save_date DESC", (user_id,))
    rows = c.fetchall()
    conn.close()
    return rows

def improve_consistency(matrix, threshold, min_val, max_val, max_iter=500, learning_rate=0.6, method='geometric'):
    current_matrix = matrix.copy()
    n = current_matrix.shape[0]
    cr, ci, _unused_lambda = calculate_consistency(current_matrix, method)
    iterations = 0
    if cr <= threshold: return current_matrix, cr, iterations, False
    
    # 상삼각 행렬의 인덱스 추출 (k=1은 대각선 제외)
    triu_indices = np.triu_indices(n, k=1)
    
    for it in range(max_iter):
        if cr <= threshold: break
        
        # 일관성 있는 행렬 생성
        w = calculate_weights(current_matrix, method)
        consistent_matrix = np.outer(w, 1/w)
        
        # 선형 결합 및 대각선 복구
        new_matrix = (current_matrix * (1 - learning_rate)) + (consistent_matrix * learning_rate)
        np.fill_diagonal(new_matrix, 1.0)
        
        # 상삼각 행렬 요소 추출
        vals = new_matrix[triu_indices]
        
        # 벡터화된 역변환 및 스케일링 로직
        # 1.0 기준 변환
        temp_raw = np.where(vals == 1.0, 1.0, 
                    np.where(vals > 1.0, -np.round(vals), 
                    np.round(1.0/vals)))
        
        # 범위 제한 (min_val, max_val)
        temp_raw = np.clip(temp_raw, min_val, max_val)
        
        # 0인 경우 1(동등)로 처리
        temp_raw = np.where(temp_raw == 0, 1, temp_raw).astype(int)
        
        # 정수화된 값을 다시 AHP 스케일로 변환하여 행렬에 일괄 반영
        final_vals = np.where(temp_raw == 0, 1.0,
                      np.where(temp_raw < 0, np.abs(temp_raw).astype(float),
                      np.where(temp_raw == 1, 1.0, 1.0 / temp_raw)))
        
        new_matrix[triu_indices] = final_vals
        new_matrix.T[triu_indices] = 1.0 / final_vals
        
        current_matrix = new_matrix
        cr, ci, _unused_lambda = calculate_consistency(current_matrix, method)
        iterations += 1
        
    was_corrected = iterations > 0
    return current_matrix, cr, iterations, was_corrected

def infer_factors_from_columns(cols):
    m = len(cols)
    delta = 1 + 8 * m
    n = int((1 + np.sqrt(delta)) / 2)
    extracted_factors = []
    seen = set()
    for c in cols:
        parts = str(c).split('_')
        for p in parts:
            p_str = p.strip()
            if p_str not in seen:
                seen.add(p_str)
                extracted_factors.append(p_str)
    if len(extracted_factors) == n:
        factors = extracted_factors 
    else:
        factors = [f"F{i+1}" for i in range(n)]
    return factors, n

def parse_input_value(val):
    """펀칭값(-9~-2, 1, 2~9)을 AHP 분석값으로 변환
    - 음수(-9~-2): 왼쪽 선호 → 절댓값 (9~2)
    - 1: 동등 → 1.0
    - 양수(2~9): 오른쪽 선호 → 역수 (1/2~1/9)
    """
    if val < 0:
        return abs(val)
    elif val == 1:
        return 1.0
    else:  # val >= 2
        return 1.0 / val

def process_single_sheet(df, cr_threshold, max_iter, learning_rate, method='geometric', ahp_method='traditional'):

    # ID와 인구통계(Type), 기타 직접입력 컬럼을 제외한 나머지를 쌍대비교 컬럼으로 간주
    def _is_comp_col(col_name):
        c_str = str(col_name).strip()
        c_lower = c_str.lower()
        if c_lower == 'id' or c_lower.startswith('type') or c_lower in ['제출시간', 'timestamp', '타임스탬프', '기타', 'other', '보상']:
            return False
        if c_str.endswith('_기타') or c_str.endswith('(기타)'):
            return False
        return True

    comp_cols = [c for c in df.columns if _is_comp_col(c)]
    meta_cols = [c for c in df.columns if c not in comp_cols]
    factors, n = infer_factors_from_columns(comp_cols)
    
    # 시트 전체 데이터의 로우데이터 최대값/최솟값 계산
    all_comp_values = pd.to_numeric(df[comp_cols].values.flatten(), errors='coerce')
    valid_comp_values = all_comp_values[~np.isnan(all_comp_values)]
    sheet_min = -9
    sheet_max = 9
    if len(valid_comp_values) > 0:
        sheet_min = min(-9, int(np.min(valid_comp_values)))
        sheet_max = max(9, int(np.max(valid_comp_values)))
    
    results_list = []
    excluded_list = []
    excluded_count = 0
    for idx, row in df.iterrows():
        meta_data = {c: row[c] for c in meta_cols}
        respondent_id = meta_data.get('ID', row.iloc[0]) if 'ID' in meta_data else row.iloc[0]
        matrix = np.eye(n)
        
        # 원본 Rawdata를 정수 형태(-9 ~ 9)로 추출
        raw_values = []
        col_idx = 0
        has_format_error = False
        format_error_detail = ""
        for i in range(n):
            for j in range(i + 1, n):
                if col_idx < len(comp_cols):
                    raw_val = row[comp_cols[col_idx]]
                    raw_values.append(raw_val)
                    
                    try:
                        num_val = float(raw_val)
                        # 유효값: -9~-2, 1, 2~9 (정수)
                        # -1, 0은 입력 불가 / 범위를 벗어난 값도 오류
                        valid_values = set(list(range(-9, -1)) + [1] + list(range(2, 10)))
                        if pd.isna(num_val) or int(num_val) != num_val or int(num_val) not in valid_values:
                            has_format_error = True
                            # 오류 상세 기록 (사용자 안내용)
                            if not pd.isna(num_val):
                                try:
                                    iv = int(num_val)
                                    if iv == 0 or iv == -1:
                                        format_error_detail = f"'{comp_cols[col_idx]}' 컬럼에 허용되지 않은 값 '{raw_val}'이(가) 있습니다. 동등은 1로 입력하세요."
                                    elif not (-9 <= iv <= 9):
                                        format_error_detail = f"'{comp_cols[col_idx]}' 컬럼의 값 '{raw_val}'이(가) 허용 범위(-9~9)를 벗어났습니다."
                                    else:
                                        format_error_detail = f"'{comp_cols[col_idx]}' 컬럼의 값 '{raw_val}'이(가) 올바르지 않습니다."
                                except:
                                    format_error_detail = f"'{comp_cols[col_idx]}' 컬럼에 숫자가 아닌 값 '{raw_val}'이(가) 있습니다."
                    except (ValueError, TypeError):
                        has_format_error = True
                        format_error_detail = f"'{comp_cols[col_idx]}' 컬럼에 숫자가 아닌 값 '{raw_val}'이(가) 있습니다."
                    
                    if not has_format_error:
                        ahp_val = parse_input_value(num_val)
                        matrix[i, j] = ahp_val
                        matrix[j, i] = 1.0 / ahp_val
                    col_idx += 1
                    
        if has_format_error:
            excluded_count += 1
            ex_res = meta_data.copy()
            for k, col_name in enumerate(comp_cols):
                _rv = raw_values[k] if k < len(raw_values) else np.nan
                try:
                    _rv = parse_input_value(float(_rv))
                except (ValueError, TypeError):
                    pass
                ex_res[col_name] = _rv
            ex_res["CR"] = f"데이터 오류(Format Error): {format_error_detail}" if format_error_detail else "데이터 오류(Format Error)"
            excluded_list.append(ex_res)
            continue
            
        orig_cr, orig_ci, _unused_lambda = calculate_consistency(matrix, method)
        final_matrix = matrix.copy()
        final_cr = orig_cr
        iterations = 0
        corrected_flag = False
        if orig_cr > cr_threshold:
            final_matrix, final_cr, iterations, corrected_flag = improve_consistency(
                matrix, cr_threshold, sheet_min, sheet_max, max_iter=max_iter, learning_rate=learning_rate, method=method
            )
        
        # 만약 최대 반복을 수행했음에도 CR이 임계값을 초과할 경우 해당 응답자 제외
        if final_cr > cr_threshold:
            excluded_count += 1
            ex_res = meta_data.copy()
            for k, col_name in enumerate(comp_cols):
                _rv = raw_values[k]
                try:
                    _rv = parse_input_value(float(_rv))
                except (ValueError, TypeError):
                    pass
                ex_res[col_name] = _rv
            ex_res["CR"] = final_cr
            excluded_list.append(ex_res)
            continue

        # 보정 후 데이터 (AHP 값 그대로 저장, 2026-10-18 변경: 펀칭값으로 역변환하지 않음)
        final_raw_values = []
        for i in range(n):
            for j in range(i + 1, n):
                val = final_matrix[i, j]
                final_raw_values.append(round(float(val), 4))

        _unused_cr, final_ci, _unused_lambda = calculate_consistency(final_matrix, method)
        if ahp_method == 'fuzzy':
            final_weights, final_Si = fuzzy_ahp_analysis(final_matrix)
        else:
            final_weights = calculate_weights(final_matrix, method)
        
        # 결과 딕셔너리 구성 (요청사항 5 재배치 반영)
        res = meta_data.copy()
        
        # [수정] 1. 보정 전 데이터 삽입 (AHP 변환값으로 저장, 2026-10-18)
        for k, col_name in enumerate(comp_cols):
            try:
                _ov = parse_input_value(float(raw_values[k]))
            except (ValueError, TypeError):
                _ov = raw_values[k]
            res[f"Raw_Orig_{col_name}"] = _ov
        
        # [수정] 2. Original_CI, Original_CR 순서 배치
        res["Original_CI"] = orig_ci
        res["Original_CR"] = orig_cr
        
        # [수정] 3. 보정 후 Rawdata 삽입
        for k, col_name in enumerate(comp_cols):
            res[f"Raw_Final_{col_name}"] = final_raw_values[k]
            
        # [수정] 4. Final_CI, Final_CR 순서 배치
        res["Final_CI"] = final_ci
        res["Final_CR"] = final_cr
        
        res["Iterations"] = iterations
        res["Corrected"] = corrected_flag
        res["Matrix_Object"] = final_matrix 
        res["Orig_Matrix_Object"] = matrix.copy()
        
        for f_idx, f_name in enumerate(factors):
            res[f"Weight_{f_name}"] = final_weights[f_idx]
            if ahp_method == 'fuzzy':
                l, m, u = final_Si[f_idx]
                res[f"L_{f_name}"] = l
                res[f"M_{f_name}"] = m
                res[f"U_{f_name}"] = u
                res[f"Crisp_{f_name}"] = (l*m*u)**(1/3)
            
        results_list.append(res)
        
    results_df = pd.DataFrame(results_list)
    excluded_df = pd.DataFrame(excluded_list)
    return results_df, factors, excluded_count, excluded_df

def render_ahp_analysis_settings():
    ahp_method = 'traditional'
    mean_method = 'geometric'
    cr_threshold = 0.1
    max_iter_val = 500
    learning_rate = 0.6
    if st.session_state.get('admin_mode', False) and st.session_state.get('user_role') == 'admin':
        pass
    else:
        with st.container(border=True):
            st.markdown(f'<h4 style="color:black; font-family:Arial, sans-serif; font-weight:bold; margin-top:0; margin-bottom:15px; font-size:1.1rem;">{_("AHP 분석 설정", "Analysis Settings")}</h4>', unsafe_allow_html=True)
            ahp_method_label = st.radio(_("분석 기법", "Analysis Method"), (_('일반 AHP (Traditional AHP)', 'Traditional AHP'), _('퍼지 AHP (Fuzzy AHP)', 'Fuzzy AHP')), index=0)
            ahp_method = 'traditional' if '일반' in ahp_method_label or 'Traditional' in ahp_method_label else 'fuzzy'
            if ahp_method == 'fuzzy':
                tier = get_current_tier()
                if tier != 'Pro':
                    st.error(_("🔒 퍼지 AHP는 Pro 요금제 전용 기능입니다.", "🔒 Fuzzy AHP is exclusive to Pro Tier."))
                    st.warning(_("현재 무료 및 일반 회원 등급에서는 일반 AHP 결과만 분석 및 제공됩니다. 퍼지 AHP 분석을 이용하시려면 Pro 등급으로 업그레이드해주시기 바랍니다.", 
                                 "In your current tier, only Traditional AHP results are analyzed and provided. To use Fuzzy AHP, please upgrade to the Pro Tier."))
                    ahp_method = 'traditional'
            mean_method_label = st.radio(_("평균 산출 방식", "Aggregation Method"), (_('기하평균 (Geometric)', 'Geometric Mean'), _('산술평균 (Arithmetic)', 'Arithmetic Mean')), index=0)
            mean_method = 'geometric' if '기하' in mean_method_label or 'Geometric' in mean_method_label else 'arithmetic'
            cr_threshold_label = st.selectbox(
                _("일관성 비율(CR) 임계값", "Consistency Ratio (CR) Threshold"), 
                [_("0.1", "0.1"), _("0.15", "0.15"), _("0.2", "0.2"), _("보정 하지 않음", "Do Not Correct")], 
                index=0,
                key="cr_threshold_label",
                help=_(
                    "임계값 설정(0.1, 0.15 또는 0.2)은 일관성 비율(CR)을 해당 수치로 정확하게 일치시키는 것이 아니라, 해당 임계값 이하로 만드는 것을 의미합니다. 이미 임계값 이하인 데이터는 보정하지 않으며, 이를 통해 원본 응답이 과도하게 왜곡되는 것을 방지합니다.",
                    "The threshold setting (0.1, 0.15 or 0.2) does not force the consistency ratio (CR) to equal that value. Instead, it adjusts the CR to be less than or equal to the threshold. If a matrix is already within the threshold, no correction is applied, preventing excessive distortion of the original responses."
                )
            )
            if "보정 하지 않음" in cr_threshold_label or "Do Not Correct" in cr_threshold_label:
                cr_threshold = 999.0
                learning_rate = 0.0
            else:
                try:
                    cr_threshold = float(cr_threshold_label)
                except ValueError:
                    cr_threshold = 0.1
            if "보정 하지 않음" in cr_threshold_label or "Do Not Correct" in cr_threshold_label:
                max_iter_val = 0
                st.number_input(_("최대 보정 반복 횟수", "Max Correction Iterations"), min_value=0, max_value=500, value=0, step=50, disabled=True, key="max_iter_disabled")
            else:
                max_iter_val = st.number_input(_("최대 보정 반복 횟수", "Max Correction Iterations"), min_value=10, max_value=500, value=500, step=50, key="max_iter_enabled")
        
            if "보정 하지 않음" in cr_threshold_label or "Do Not Correct" in cr_threshold_label:
                st.slider(_("보정 강도 (Learning Rate)", "Correction Intensity (Learning Rate)"), min_value=0.0, max_value=0.9, value=0.0, step=0.1, disabled=True, key="learning_rate_disabled")
            else:
                learning_rate = st.slider(_("보정 강도 (Learning Rate)", "Correction Intensity (Learning Rate)"), min_value=0.1, max_value=0.9, value=0.6, step=0.1, key="learning_rate_enabled")
        # 1. CR 보정 결과 왜곡 검증
        with st.expander(_("CR 보정 결과 왜곡 검증", "CR Consistency Distortion Verification"), expanded=False):
            if st.button(_("▶ 검증 실행", "▶ Run Verification"), use_container_width=True, key="btn_cr_verify"):
                if "uploaded_matrix" not in st.session_state:
                    show_warning_dialog()
                else:
                    show_cr_distortion_dialog()

        # 2. 일관성 보정 기준
        with st.expander(_("일관성 보정 기준", "Consistency Correction Standard"), expanded=False):
            st.markdown(_(r"""
            **보정 방법: 반복 수렴 조정법(Iterative Adjustment)**
            가중치 산출 알고리즘(Saaty)에 의해 판단 행렬이 비일관적(CR > 임계값)인 경우, 수학적으로 일관된 행렬과 원본 행렬을 일정 비율로 혼합하여 반복적으로 가중치를 미세 조정한 결과를 제시합니다.
        
            **현재 방법의 특징:**
            1. **최소 판단 왜곡**: 원본 설문 응답의 경향성을 보존하면서 수학적 일관성만을 확보합니다.
            2. **자동 수렴**: 설정된 반복 횟수 내에서 CR 값을 임계값 이하로 자동 개선합니다. ($New = (1-\alpha) \times Old + \alpha \times Ideal$)
            3. **과도한 보정 방지**: 임계값 설정(0.1, 0.15 또는 0.2)은 CR 값을 정확히 맞추는 것이 아니라 임계값 '이하'로 만드는 것을 목표로 합니다. 이미 임계값 이하인 응답은 보정을 수행하지 않아 원본 판단을 최대한 보존합니다.
        
            """, r"""
            **Correction Method: Iterative Adjustment**
            If the judgment matrix is inconsistent (CR > threshold) based on Saaty's weight algorithm, it repeatedly adjusts the weights by mixing the original matrix with a mathematically consistent matrix.
        
            **Key Features:**
            1. **Minimal Distortion of Judgments**: Preserves the trends of the original survey responses while securing mathematical consistency.
            2. **Automatic Convergence**: Automatically improves the CR value to be below the threshold within the maximum number of iterations. ($New = (1-\alpha) \times Old + \alpha \times Ideal$)
            3. **Prevention of Excessive Correction**: The threshold setting (0.1, 0.15 or 0.2) targets bringing the CR 'below or equal to' the threshold, rather than matching it exactly. Responses already below the threshold are left uncorrected to preserve the original judgments as much as possible.
        
            """))

        # 3. 이용자 가이드
        with st.expander(_("이용자 가이드", "User Guide"), expanded=False):
            st.markdown(_("AHP 마스터 서비스 사용 설명서 및 가이드 링크입니다.", "Link to the AHP Master user manual and guide."))
            if st.session_state.get('lang', 'ko') == 'en':
                if st.button("Read English User Guide", use_container_width=True, key="btn_read_guide"):
                    st.session_state.page = "guide"
                    st.rerun()
            else:
                st.link_button("이용자 가이드 바로가기", "https://morison.tistory.com/103", use_container_width=True)

        with st.expander(_("학술 논문 및 연구 보고서 기재 방법 예시", "Example of citation in academic papers/reports"), expanded=False):
            st.info(_("AHP 분석 결과를 학위 논문이나 연구 보고서에 기술할 때 아래 예시문을 참고하여 인용 및 서술하실 수 있습니다.",
                      "When describing AHP analysis results in your thesis or research report, you can refer to and cite the example below."))
            st.markdown(_("""
            > **[논문 기재 예시문]**
            > 
            > "본 연구에서 수집된 설문 데이터는 웹 기반 AHP 전용 분석 솔루션인 'AHP 마스터'를 활용하여 분석을 수행하였다. Saaty(1980)의 계층분석과정에 따라 쌍대비교 행렬을 구성하여 국지적 가중치와 종합 가중치(Global Weight)를 산출하였으며, 일관성 비율(CR)이 0.1 미만이 되도록 시스템의 보정 기능을 거쳐 결과의 타당성을 확보하였다."
            """,
            """
            > **[Example of Paper Citation]**
            > 
            > "The survey data collected in this study was analyzed using 'AHP Master', a web-based dedicated AHP analysis solution. Pairwise comparison matrices were constructed in accordance with Saaty's (1980) Analytic Hierarchy Process to calculate local and global weights, and the validity of the results was secured through the system's consistency ratio (CR) adjustment function to ensure CR was below 0.1."
            """))

        if st.session_state.get('lang', 'ko') == 'ko':
            pdf_path = "AHP_Master_Accuracy_Paper.pdf"
            if os.path.exists(pdf_path):
                import base64
                with open(pdf_path, "rb") as f:
                    base64_pdf = base64.b64encode(f.read()).decode('utf-8')
                pdf_html = f'<a href="data:application/pdf;base64,{base64_pdf}" download="AHP_Master_Accuracy_Paper.pdf" style="text-decoration: underline; font-weight: bold; font-size: 14px; color: #1B2A4A;">📄 AHP 정확성 검증 논문 (PDF) 다운로드</a>'
                st.markdown("<br/>", unsafe_allow_html=True)
                st.markdown(pdf_html, unsafe_allow_html=True)

    return ahp_method, mean_method, cr_threshold, max_iter_val, learning_rate

def run_gspread_with_retry(func, *args, max_retries=6, initial_backoff=2, **kwargs):
    # [2026-10-24] max_retries 5→6: 백오프 합계(2+4+8+16+32≈62초+지터)가 분당 쿼터 윈도우(60초)를
    # 넘겨야 쿼터 소진 상황에서도 재시도가 성공할 수 있음 (5회·약 31초로는 윈도우 리셋 전에 포기했음)
    """
    구글 시트 API 호출 시 429(RESOURCE_EXHAUSTED) 등 일시적 오류 발생 시
    지수 백오프(Exponential Backoff) 및 지터(Jitter)를 적용하여 재시도하는 헬퍼 함수.
    """
    import time
    import random
    backoff = initial_backoff
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            err_msg = str(e)
            is_rate_limit = "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg or "RATE_LIMIT_EXCEEDED" in err_msg
            
            if is_rate_limit and attempt < max_retries - 1:
                sleep_time = backoff + random.uniform(0, 1)
                time.sleep(sleep_time)
                backoff *= 2
                continue
            else:
                raise e

def saaty_to_fuzzy(v):
    try:
        val = max(1, min(9, int(round(v)))) if v >= 1 else max(1, min(9, int(round(1/v))))
        tfn = FUZZY_SCALE[val]
        if v < 1: return (1.0/tfn[2], 1.0/tfn[1], 1.0/tfn[0])
        return tfn
    except: return (1.0, 1.0, 1.0)

def save_analysis_to_db(user_id, filename, file_data):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    # [수정] 대한민국 시간 기준 저장 일시 설정
    save_date = str(datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).strftime("%Y-%m-%d %H:%M:%S"))
    c.execute("INSERT INTO saved_analyses (user_id, filename, save_date, file_data) VALUES (?, ?, ?, ?)",
              (user_id, filename, save_date, file_data))
    conn.commit()
    conn.close()

def show_cr_distortion_dialog():

    from cr_analysis import run_analysis, matrix_to_heatmap_img
        
    st.info(_("📊 업로드된 메인 기준 데이터(응답자 전체 기하평균 행렬)를 바탕으로 검증을 수행합니다.", "📊 Performing verification based on the uploaded Main Criteria data (geometric mean matrix of all respondents)."))
    original_matrix = st.session_state.uploaded_matrix

    # Determine selected CR option
    option = st.session_state.get('cr_threshold_label', '0.1')
    if option in ["보정 하지 않음", "Do Not Correct"]:
        corrected_matrix = original_matrix.copy()
        option_name = _("보정 안 함", "Do Not Correct")
    else:
        corrected_matrix, cr_val, iters, _unused = improve_consistency(
            original_matrix,
            threshold=float(option),
            min_val=-9,
            max_val=9
        )
        option_name = option

    metrics = run_analysis(original_matrix, corrected_matrix, option_name)

    # --- Two-column layout: left=explanation, right=results ---
    left_col, right_col = st.columns([1.2, 1])

    with right_col:
        st.subheader(_(" 검증 결과", " Verification Results"))
        st.dataframe(pd.DataFrame([metrics]), use_container_width=True)

        # Heatmaps side by side
        orig_img = matrix_to_heatmap_img(original_matrix, _("원본 행렬", "Original Matrix"))
        corr_img = matrix_to_heatmap_img(corrected_matrix, option_name)
        hm1, hm2 = st.columns(2)
        with hm1:
            st.image(f"data:image/png;base64,{orig_img}", caption=_("원본 행렬", "Original Matrix"), use_container_width=True)
        with hm2:
            st.image(f"data:image/png;base64,{corr_img}", caption=_("보정 행렬", "Corrected Matrix"), use_container_width=True)

    with left_col:
        st.subheader(_(" 검증 방법", " Verification Method"))
        st.markdown(_(
            f"""
본 검증은 CR(일관성 비율) 보정 과정에서 **원본 응답 데이터가 얼마나 변형되었는지**를 정량적으로 측정합니다.

**검증 절차:**
1. **원본 행렬 확보** — 설문 응답자의 쌍대비교 판단 행렬을 그대로 사용합니다.
2. **보정 행렬 생성** — 선택된 CR 임계값(`{option_name}`)에 따라 반복 수렴 조정법(Iterative Adjustment)으로 보정된 행렬을 생성합니다.
3. **차이 분석** — 원본과 보정 행렬 간 4가지 수리적 지표를 계산합니다:
   - **유클리드 거리**: 행렬 원소 간 직선 거리
   - **맨해튼 거리**: 행렬 원소 간 절대 차이의 합
   - **코사인 유사도**: 두 행렬 벡터의 방향 일치도
   - **왜곡 점수**: 위 지표들을 종합한 왜곡 수준 지수
4. **종합 판정** — 왜곡 점수를 기준으로 보정의 신뢰성을 평가합니다.

> 💡 왜곡 점수가 낮을수록 보정이 원본 응답의 경향성을 잘 보존했음을 의미합니다.

---
""",
            f"""
This verification quantitatively measures **how much the original response data was altered** during the CR (Consistency Ratio) correction process.

**Verification Procedure:**
1. **Obtain Original Matrix** — Use the respondent's raw pairwise comparison judgment matrix as-is.
2. **Generate Corrected Matrix** — Apply the Iterative Adjustment method based on the selected CR threshold (`{option_name}`) to produce a corrected matrix.
3. **Difference Analysis** — Calculate 4 mathematical metrics between the original and corrected matrices:
   - **Euclidean Distance**: Straight-line distance between matrix elements
   - **Manhattan Distance**: Sum of absolute element-wise differences
   - **Cosine Similarity**: Directional alignment of the two matrix vectors
   - **Distortion Score**: Composite index summarizing overall distortion
4. **Overall Verdict** — Evaluate the reliability of the correction based on the Distortion Score.

> 💡 A lower Distortion Score means the correction better preserved the original response patterns.

---
"""))

        st.subheader(_(" 결과 해석", " Interpretation"))

        # Extract metric values
        euc = metrics.get("euclidean", 0)
        man = metrics.get("manhattan", 0)
        cos = metrics.get("cosine_similarity", 1)
        dist = metrics.get("distortion_score", 0)

        st.markdown(_( 
            f"""
**1. 유클리드 거리 (Euclidean Distance): `{euc:.6f}`**  
원본 행렬과 보정 행렬 사이의 직선 거리입니다.  
값이 **0에 가까울수록** 보정이 원본을 거의 변형하지 않았음을 의미합니다.

**2. 맨해튼 거리 (Manhattan Distance): `{man:.6f}`**  
각 원소별 차이의 절대값 합입니다.  
유클리드 거리와 함께 보정의 **전체적인 변동 크기**를 나타냅니다.

**3. 코사인 유사도 (Cosine Similarity): `{cos:.6f}`**  
두 행렬 벡터 간의 방향 유사도입니다.  
**1.0에 가까울수록** 보정 전후 응답 패턴이 동일한 방향을 유지하고 있습니다.

**4. 왜곡 점수 (Distortion Score): `{dist:.6f}`**  
종합적인 왜곡 수준을 나타내는 지표입니다.

---

""",
            f"""
**1. Euclidean Distance: `{euc:.6f}`**  
The straight-line distance between the original and corrected matrices.  
A value **close to 0** means the correction barely altered the original.

**2. Manhattan Distance: `{man:.6f}`**  
The sum of absolute element-wise differences.  
Together with Euclidean distance, it shows the **overall magnitude of change**.

**3. Cosine Similarity: `{cos:.6f}`**  
The directional similarity between the two matrix vectors.  
A value **close to 1.0** means the response pattern is preserved after correction.

**4. Distortion Score: `{dist:.6f}`**  
A composite index representing the overall distortion level.

---

"""))

        # Verdict
        if dist < 0.01:
            verdict_icon = "✅"
            verdict = _("왜곡 수준: **매우 낮음** — 보정이 원본 응답을 거의 변형하지 않았습니다. 신뢰할 수 있는 결과입니다.",
                        "Distortion Level: **Very Low** — The correction barely altered the original responses. The result is reliable.")
        elif dist < 0.05:
            verdict_icon = "🟡"
            verdict = _("왜곡 수준: **낮음** — 경미한 조정이 있었으나 원본 경향성이 잘 보존되었습니다.",
                        "Distortion Level: **Low** — Minor adjustments were made, but the original trends are well preserved.")
        elif dist < 0.15:
            verdict_icon = "🟠"
            verdict = _("왜곡 수준: **보통** — 일부 변형이 발생했습니다. 결과 해석에 주의가 필요합니다.",
                        "Distortion Level: **Moderate** — Some distortion occurred. Interpret results with caution.")
        else:
            verdict_icon = "🔴"
            verdict = _("왜곡 수준: **높음** — 보정 과정에서 상당한 변형이 발생했습니다. CR 임계값을 조정하거나 원본 데이터를 재검토하세요.",
                        "Distortion Level: **High** — Significant distortion occurred during correction. Consider adjusting the CR threshold or reviewing the original data.")

        st.markdown(f"### {verdict_icon} {_('종합 판정', 'Overall Verdict')}")
        st.info(verdict)

def show_reset_survey_dialog(sheet_id, survey_title):
    from survey_manager import reset_survey_responses
    
    st.markdown(_(
        f"선택된 설문: **{survey_title}**\n\n"
        "이 작업은 설문 문항 및 설정(Survey_Metadata)은 그대로 보존하고, **수집된 모든 응답 데이터(Raw_Data, Demographic_Data, Main_Criteria 및 기준별 시트의 2행 이하)만 완전히 삭제**합니다.\n\n"
        "💡 **언제 사용하나요?** 테스트 목적으로 입력한 가짜/테스트 응답을 깨끗이 비우고, 실제 대상자 모집을 시작하기 직전에 유용합니다.",
        f"Selected Survey: **{survey_title}**\n\n"
        "This will preserve survey structure and settings, but **permanently delete all collected response rows**.\n\n"
        "💡 **When to use?** Useful for clearing test responses before officially launching the survey."
    ))
    
    st.warning(_(
        "⚠️ **주의**: 삭제된 데이터는 복구할 수 없습니다. 안전을 위해 '자동 백업 시트 생성' 옵션을 켜두시기를 강력히 권장합니다.",
        "⚠️ **Warning**: Deleted data cannot be recovered. Enabling the 'Auto-backup Sheet' option is strongly recommended."
    ))
    
    do_backup = st.checkbox(
        _("🛡️ 초기화 전 구글 시트 내에 백업 시트('Raw_Backup_날짜시간') 자동 생성 (권장)",
          "🛡️ Automatically create a backup sheet in Google Sheets before reset (Recommended)"),
        value=True,
        key="chk_reset_backup"
    )
    
    agree = st.checkbox(
        _("위 내용을 충분히 확인하였으며, 응답 데이터를 삭제하고 초기화하는 데 동의합니다.",
          "I have read and understood the warning, and I agree to delete response data."),
        value=False,
        key="chk_reset_agree"
    )
    
    confirm_text = st.text_input(
        _("확인을 위해 아래에 **초기화** 또는 **RESET**을 직접 입력하세요:",
          "Type **RESET** below to confirm:"),
        key="txt_reset_confirm"
    )
    
    is_confirmed = agree and (confirm_text.strip() in ["초기화", "RESET", "reset"])
    
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        if st.button(_("❌ 취소", "❌ Cancel"), use_container_width=True, key="btn_cancel_reset"):
            st.rerun()
    with col_c2:
        if st.button(
            _("🗑️ 영구 초기화 실행", "🗑️ Execute Permanent Reset"),
            type="primary",
            use_container_width=True,
            disabled=not is_confirmed,
            key="btn_exec_reset"
        ):
            with st.spinner(_("구글 시트 응답 데이터를 안전하게 초기화 중입니다...", "Resetting survey response data safely...")):
                res = reset_survey_responses(sheet_id, create_backup=do_backup, user_id=st.session_state.get("user_id"))
                if res.get("success"):
                    deleted_cnt = res.get("deleted_count", 0)
                    backup_name = res.get("backup_sheet_name")
                    msg_ko = f"✅ 총 {deleted_cnt}건의 응답 데이터가 성공적으로 초기화되었습니다!"
                    if backup_name:
                        msg_ko += f"\n(구글 시트에 백업 시트 '{backup_name}' 생성 완료)"
                    msg_en = f"✅ Successfully cleared {deleted_cnt} responses!"
                    if backup_name:
                        msg_en += f"\n(Backup sheet '{backup_name}' created in Google Sheet)"
                    st.success(_(msg_ko, msg_en))
                    
                    # 로컬 세션 상태 초기화
                    for k in ["ahp_df_main", "ahp_sub_dfs", "ahp_sub_sub_dfs", "live_df", "demo_df", "survey_stats"]:
                        st.session_state.pop(k, None)
                    import time
                    time.sleep(2.0)
                    st.rerun()
                else:
                    st.error(_(f"초기화 실패: {res.get('error')}", f"Reset failed: {res.get('error')}"))

def show_warning_dialog():
    st.warning(_("⚠️ 분석 후 확인 가능합니다. (데이터를 먼저 업로드하세요)", "⚠️ Available after analysis. (Please upload data first)"))

def sync_short_codes_from_gs():
    try:
        _sync_short_codes_from_gs_cached()
    except Exception:
        pass

def write_alternative_sheets(wb, alt_result):
    """[2026-10-21] 대안 평가 보고서 시트를 xlsxwriter 워크북(wb)에 추가한다.

    시트 수를 줄이기 위해 주제별로 통합하고, 각 시트 안에서는 번호를 붙인
    섹션을 아래로 나열한다 (종합분석 / 가중치·종합점수 / 민감도분석 /
    잎별 상세분석 / 개인별 결과 — 총 5개). 본 결과 파일 통합과 단독
    다운로드가 이 함수를 공용으로 사용한다.
    """
    alts = list(alt_result.get("alternatives", []) or [])
    leaves = list(alt_result.get("leaves", []) or [])
    g_scores = alt_result.get("group_scores", {}) or {}
    leaf_global = alt_result.get("leaf_group_global", {}) or {}
    leaf_alt_group = alt_result.get("leaf_alt_group", {}) or {}
    indiv = (alt_result.get("indiv_df") if alt_result.get("indiv_df") is not None else pd.DataFrame()).copy()
    leaf_detail = alt_result.get("leaf_detail", {}) or {}
    settings = alt_result.get("settings", {}) or {}
    cr_thr = settings.get("cr_threshold", 0.1)
    method_lbl = "기하평균" if settings.get("method", "geometric") == "geometric" else "산술평균"
    n_used = alt_result.get("n_used", len(indiv))
    fg = alt_result.get("factor_group", {}) or {}
    model = alt_result.get("model", {}) or {}
    main_w = dict(fg.get("main_weights", {}) or {})
    sub_w = fg.get("sub_weights", {}) or {}
    ss_w = fg.get("ss_weights", {}) or {}
    main_cr = fg.get("main_cr")
    sub_cr = fg.get("sub_cr", {}) or {}
    ss_cr = fg.get("ss_cr", {}) or {}
    leaf_local = fg.get("leaf_local", {}) or {}
    chains = {k: tuple(v) for k, v in (fg.get("leaf_chain", {}) or {}).items()}
    if not main_w:
        for lf in leaves:
            ch = chains.get(lf)
            if ch:
                main_w[ch[0]] = main_w.get(ch[0], 0.0) + float(leaf_global.get(lf, 0.0))
    mains = [m for m in (model.get("main", []) or []) if m in main_w] or sorted(main_w, key=lambda m: -main_w[m])
    subs_map = model.get("subs", {}) or {}
    is_tier3 = any(ch and len(ch) >= 3 and ch[2] for ch in chains.values())

    F = {
        "title": wb.add_format({"bold": True, "font_size": 14}),
        "section": wb.add_format({"bold": True, "font_size": 12}),
        "header": wb.add_format({"bold": True, "align": "center", "valign": "vcenter", "bg_color": "000000", "font_color": "FFFFFF", "border": 1}),
        "body": wb.add_format({"align": "center", "valign": "vcenter", "border": 1}),
        "body_left": wb.add_format({"align": "left", "valign": "vcenter", "border": 1}),
        "num3": wb.add_format({"align": "center", "valign": "vcenter", "border": 1, "num_format": "0.000"}),
        "pct1": wb.add_format({"align": "center", "valign": "vcenter", "border": 1, "num_format": "0.0"}),
        "sum": wb.add_format({"bold": True, "bg_color": "D3D3D3", "align": "center", "valign": "vcenter", "border": 1}),
        "sum_num": wb.add_format({"bold": True, "bg_color": "D3D3D3", "align": "center", "valign": "vcenter", "border": 1, "num_format": "0.000"}),
        "diag": wb.add_format({"num_format": "0", "align": "center", "valign": "vcenter", "bg_color": "E7E6E6", "border": 1}),
        "yellow_num": wb.add_format({"bg_color": "FFFF00", "border": 1, "align": "center", "valign": "vcenter", "num_format": "0.000"}),
        "note": wb.add_format({"italic": True, "font_color": "666666", "font_size": 9}),
        "wrap": wb.add_format({"text_wrap": True, "valign": "top"}),
        "rowhead": wb.add_format({"bold": True, "align": "center", "valign": "vcenter", "border": 1, "bg_color": "F2F2F2"}),
    }

    def _table(ws, start_row, headers, rows, fmts, widths=None):
        r = start_row
        for c, h in enumerate(headers):
            ws.write(r, c, h, F["header"])
        r += 1
        for row in rows:
            for c, (val, fmt_key) in enumerate(zip(row, fmts)):
                if val is None or (isinstance(val, float) and pd.isna(val)):
                    ws.write_blank(r, c, None, F["body"])
                elif fmt_key in ("num3", "pct1", "sum_num", "yellow_num"):
                    ws.write_number(r, c, float(val), F[fmt_key])
                else:
                    ws.write(r, c, val, F[fmt_key])
            r += 1
        if widths:
            for c, w in enumerate(widths):
                ws.set_column(c, c, w)
        return r

    rank_rows = sorted(g_scores.items(), key=lambda kv: kv[1], reverse=True)
    total_excluded = sum(int((leaf_detail.get(lf, {}) or {}).get("excluded_count", 0) or 0) for lf in leaves)
    leaf_crs = [float((leaf_detail.get(lf, {}) or {}).get("group_cr")) for lf in leaves
                if (leaf_detail.get(lf, {}) or {}).get("group_cr") is not None]
    leaves_by_global = sorted(leaves, key=lambda lf: -float(leaf_global.get(lf, 0.0)))
    global_rank = {lf: i + 1 for i, lf in enumerate(leaves_by_global)}

    # ========== 시트 1: (대안) 종합분석 ==========
    ws = wb.add_worksheet("(대안) 종합분석")
    ws.write(0, 0, "대안 평가 종합 분석 결과", F["title"])
    r = 2; sec = 1
    ws.write(r, 0, f"{sec}. 분석 정보 및 표본·일관성 검증 요약", F["section"]); sec += 1; r += 1
    cr_range = f"{min(leaf_crs):.3f} ~ {max(leaf_crs):.3f}" if leaf_crs else "-"
    info_rows = [
        ("유효 표본 수", f"{n_used}명"),
        ("대안", ", ".join(alts)),
        ("최하위(잎) 요인 수", f"{len(leaves)}개"),
        ("집계 방식", f"{method_lbl}"),
        ("일관성(CR) 임계값", f"{cr_thr}"),
        ("대안 평가 분석 제외 사례수 (잎별 합계)", f"{total_excluded}건"),
        ("대안 평가 집단 CR 범위 (잎별)", cr_range),
        ("1계층 요인 집단 CR", f"{main_cr:.3f}" if main_cr is not None else "-"),
    ]
    r = _table(ws, r, ["항목", "내용"], [[k, v] for k, v in info_rows], ["body", "body"], widths=[34, 30])
    r += 1
    ws.write(r, 0, f"{sec}. 최종 대안 순위 (개인 점수 집계)", F["section"]); sec += 1; r += 1
    r = _table(ws, r, ["순위", "대안", "종합 가중치", "비율(%)"],
               [[i + 1, a, s, s * 100] for i, (a, s) in enumerate(rank_rows)],
               ["body", "body", "num3", "pct1"], widths=[34, 30, 16, 14])
    ws.write(r, 0, "합계", F["sum"]); ws.write(r, 1, "", F["sum"])
    ws.write_number(r, 2, float(sum(g_scores.values())), F["sum_num"])
    ws.write_number(r, 3, float(sum(g_scores.values()) * 100), F["sum"]); r += 2
    grp_rows = []
    if not indiv.empty and "Type" in indiv.columns and indiv["Type"].astype(str).str.strip().ne("").any():
        for grp, gdf in indiv.groupby(indiv["Type"].astype(str)):
            vals = [float(gdf[f"Score_{a}"].mean()) if f"Score_{a}" in gdf.columns else 0.0 for a in alts]
            top = alts[int(max(range(len(vals)), key=lambda i: vals[i]))] if vals else ""
            grp_rows.append([grp, len(gdf)] + vals + [top])
    if len(grp_rows) >= 2:
        ws.write(r, 0, f"{sec}. 그룹별 대안 종합점수 (개인 점수 평균)", F["section"]); sec += 1; r += 1
        r = _table(ws, r, ["그룹", "인원"] + alts + ["그룹 내 1위"], grp_rows,
                   ["body", "body"] + ["num3"] * len(alts) + ["body"])
        r += 1
    ws.write(r, 0, f"{sec}. 계층구조 (목표 - 평가기준 - 대안)", F["section"]); sec += 1; r += 1
    hrows = [["목표", "최종 대안 선정", "", None, None]]
    for m in mains:
        mw = float(main_w.get(m, 0.0))
        hrows.append(["1계층", m, "목표", mw, mw])
        for sc in (subs_map.get(m, []) or []):
            sl = (sub_w.get(m, {}) or {}).get(sc)
            if is_tier3 and sc in ss_w:
                hrows.append(["2계층", sc, m, sl, (mw * sl) if sl is not None else None])
                for lf in [x for x in leaves if chains.get(x, (None, None, None))[1] == sc]:
                    hrows.append(["3계층 (최하위)", lf, sc, leaf_local.get(lf), float(leaf_global.get(lf, 0.0))])
            else:
                hrows.append(["2계층 (최하위)", sc, m, sl, float(leaf_global.get(sc, 0.0))])
        if not (subs_map.get(m, []) or []):
            hrows.append(["1계층 (최하위)", m, "목표", 1.0, float(leaf_global.get(m, 0.0))])
    for a in alts:
        hrows.append(["대안", a, "모든 최하위 요인", None, None])
    r = _table(ws, r, ["계층", "요인", "상위 요인", "부분가중치(Local)", "종합가중치(Global)"], hrows,
               ["body", "body_left", "body", "num3", "num3"], widths=[34, 30, 18, 18, 18])
    r += 1
    ws.write(r, 0, "※ 가중치 상세는 '(대안) 가중치·종합점수', 강건성 검증은 '(대안) 민감도분석' 시트를 참조하십시오.", F["note"])

    # ========== 시트 2: (대안) 가중치·종합점수 ==========
    ws = wb.add_worksheet("(대안) 가중치·종합점수")
    ws.write(0, 0, "대안 평가 가중치 및 종합점수", F["title"])
    r = 2
    ws.write(r, 0, "1. [표 1] 평가기준 계층별 가중치 및 우선순위 분석 결과", F["section"]); r += 1
    if is_tier3:
        headers = ["1계층", "1계층 가중치", "1계층 CR", "중분류", "중분류 부분가중치", "중분류 CR",
                   "소분류 (최하위)", "소분류 부분가중치", "종합가중치(Global)", "종합 순위"]
        fmts = ["body", "num3", "num3", "body", "num3", "num3", "body", "num3", "num3", "body"]
        rows = []
        for m in mains:
            group_leaves = [lf for lf in leaves_by_global if chains.get(lf, (None,))[0] == m]
            for gi, lf in enumerate(group_leaves):
                _mc, _sc, _iss = chains.get(lf, (m, None, False))
                rows.append([
                    m if gi == 0 else None,
                    float(main_w.get(m, 0.0)) if gi == 0 else None,
                    main_cr if gi == 0 else None,
                    _sc, (sub_w.get(m, {}) or {}).get(_sc), ss_cr.get(_sc),
                    lf, leaf_local.get(lf), float(leaf_global.get(lf, 0.0)), global_rank[lf]])
        r = _table(ws, r, headers, rows, fmts, widths=[16, 14, 11, 16, 16, 11, 18, 16, 16, 10])
    else:
        headers = ["1계층", "1계층 가중치", "1계층 CR", "2계층 (최하위 요인)", "부분가중치(Local)",
                   "2계층 CR", "종합가중치(Global)", "종합 순위"]
        fmts = ["body", "num3", "num3", "body", "num3", "num3", "num3", "body"]
        rows = []
        for m in mains:
            group_leaves = [lf for lf in leaves_by_global if chains.get(lf, (None,))[0] == m]
            if not group_leaves and m in leaves:
                group_leaves = [m]
            for gi, lf in enumerate(group_leaves):
                rows.append([
                    m if gi == 0 else None,
                    float(main_w.get(m, 0.0)) if gi == 0 else None,
                    main_cr if gi == 0 else None,
                    lf, leaf_local.get(lf), sub_cr.get(m),
                    float(leaf_global.get(lf, 0.0)), global_rank[lf]])
        r = _table(ws, r, headers, rows, fmts, widths=[16, 14, 11, 22, 16, 11, 16, 10])
    ws.write(r, 0, "합계", F["sum"])
    ws.write_number(r, 1, float(sum(main_w.get(m, 0.0) for m in mains)), F["sum_num"])
    r += 1
    ws.write(r, 0, "※ 부분가중치(Local)는 직속 상위 요인 내에서의 상대적 중요도이며, 종합가중치(Global) = 상위 가중치 × 부분가중치입니다.", F["note"])
    r += 2
    ws.write(r, 0, "2. [표 2] 평가기준별 대안 선호도 및 최종 종합점수 (Synthesis)", F["section"]); r += 1
    headers = ["평가기준 (최하위 요인)", "종합가중치(Wi)"]
    for a in alts:
        headers += [f"{a} 선호도", f"{a} 기여도"]
    headers += ["대안 평가 CR"]
    fmts = ["body", "num3"] + ["num3", "num3"] * len(alts) + ["num3"]
    rows = []
    for lf in leaves_by_global:
        gw = float(leaf_global.get(lf, 0.0))
        row = [lf, gw]
        for a in alts:
            pref = float(leaf_alt_group.get(lf, {}).get(a, 0.0))
            row += [pref, gw * pref]
        row.append((leaf_detail.get(lf, {}) or {}).get("group_cr"))
        rows.append(row)
    r = _table(ws, r, headers, rows, fmts, widths=[24, 15] + [13, 13] * len(alts) + [13])
    contrib_tot = {a: sum(float(leaf_global.get(lf, 0.0)) * float(leaf_alt_group.get(lf, {}).get(a, 0.0)) for lf in leaves) for a in alts}
    ws.write(r, 0, "종합점수 (계층 결합)", F["sum"])
    ws.write_number(r, 1, float(sum(leaf_global.get(lf, 0.0) for lf in leaves)), F["sum_num"])
    for ai, a in enumerate(alts):
        ws.write_blank(r, 2 + ai * 2, None, F["sum"])
        ws.write_number(r, 3 + ai * 2, contrib_tot[a], F["sum_num"])
    ws.write_blank(r, 2 + len(alts) * 2, None, F["sum"]); r += 1
    ws.write(r, 0, "종합점수 비율(%)", F["sum"])
    ws.write_blank(r, 1, None, F["sum"])
    for ai, a in enumerate(alts):
        ws.write_blank(r, 2 + ai * 2, None, F["sum"])
        ws.write_number(r, 3 + ai * 2, contrib_tot[a] * 100, F["sum"])
    ws.write_blank(r, 2 + len(alts) * 2, None, F["sum"]); r += 1
    syn_rank = {a: i + 1 for i, (a, _s) in enumerate(sorted(contrib_tot.items(), key=lambda kv: -kv[1]))}
    ws.write(r, 0, "최종 우선순위 (계층 결합)", F["sum"])
    ws.write_blank(r, 1, None, F["sum"])
    for ai, a in enumerate(alts):
        ws.write_blank(r, 2 + ai * 2, None, F["sum"])
        ws.write(r, 3 + ai * 2, f"{syn_rank[a]}순위", F["sum"])
    ws.write_blank(r, 2 + len(alts) * 2, None, F["sum"]); r += 1
    ws.write(r, 0, "참고: 앱 종합 가중치 (개인 점수 집계)", F["body"])
    ws.write_blank(r, 1, None, F["body"])
    for ai, a in enumerate(alts):
        ws.write_blank(r, 2 + ai * 2, None, F["body"])
        ws.write_number(r, 3 + ai * 2, float(g_scores.get(a, 0.0)), F["num3"])
    ws.write_blank(r, 2 + len(alts) * 2, None, F["body"]); r += 1
    aip_rank = {a: i + 1 for i, (a, _s) in enumerate(rank_rows)}
    ws.write(r, 0, "참고: 앱 최종 우선순위", F["body"])
    ws.write_blank(r, 1, None, F["body"])
    for ai, a in enumerate(alts):
        ws.write_blank(r, 2 + ai * 2, None, F["body"])
        ws.write(r, 3 + ai * 2, f"{aip_rank.get(a, '')}순위", F["body"])
    ws.write_blank(r, 2 + len(alts) * 2, None, F["body"]); r += 1
    ws.write(r, 0, "※ 기여도 = 해당 기준의 종합가중치(Wi) × 대안 선호도. '계층 결합' 종합점수는 기준 가중치와 대안 선호도를 결합한 값이고, 앱 종합 가중치는 응답자 개인별 종합점수를 집계한 값으로 집계 방식 차이만큼 결과가 다를 수 있습니다.", F["note"])
    r += 2
    ws.write(r, 0, "3. 최하위 요인별 대안 국지 가중치 (그룹)", F["section"]); r += 1
    leaf_rows = []
    for lf in leaves:
        vals = [float(leaf_alt_group.get(lf, {}).get(a, 0.0)) for a in alts]
        leaf_rows.append([lf, float(leaf_global.get(lf, 0.0))] + vals + [sum(vals)])
    _table(ws, r, ["최하위 요인", "글로벌 가중치"] + alts + ["행 합계"],
           leaf_rows, ["body", "num3"] + ["num3"] * len(alts) + ["num3"],
           widths=[24, 15] + [13] * len(alts) + [12])

    # ========== 시트 3: (대안) 민감도분석 ==========
    if len(mains) >= 2 and main_w:
        top_main = max(mains, key=lambda m: float(main_w.get(m, 0.0)))
        w0 = float(main_w.get(top_main, 0.0))
        if 0.0 < w0 < 1.0:
            ws = wb.add_worksheet("(대안) 민감도분석")
            ws.write(0, 0, f"민감도 분석 - 1계층 '{top_main}' 가중치 변화에 따른 대안 종합점수", F["title"])
            steps = [i / 20 for i in range(21)]

            def _sens_scores(w_top):
                scale = {}
                for m in mains:
                    if m == top_main:
                        scale[m] = w_top / w0
                    else:
                        scale[m] = (1 - w_top) / (1 - w0) if float(main_w.get(m, 0.0)) > 0 else 0.0
                out = {}
                for a in alts:
                    tot = 0.0
                    for lf in leaves:
                        ch = chains.get(lf)
                        sc = scale.get(ch[0], 1.0) if ch else 1.0
                        tot += float(leaf_global.get(lf, 0.0)) * sc * float(leaf_alt_group.get(lf, {}).get(a, 0.0))
                    out[a] = tot
                return out

            sens = [_sens_scores(w) for w in steps]
            _cur_sens = _sens_scores(w0)
            champ = max(alts, key=lambda a: _cur_sens[a])
            sentences = [f"현재 '{top_main}' 가중치는 {w0:.3f}이며, 계층 결합 기준 1위 대안은 {champ}입니다."]
            for a in alts:
                if a == champ:
                    continue
                diffs = [s[champ] - s[a] for s in sens]
                cross = None
                for i in range(len(steps) - 1):
                    if diffs[i] == 0:
                        cross = steps[i]; break
                    if diffs[i] * diffs[i + 1] < 0:
                        cross = steps[i] + (steps[i + 1] - steps[i]) * abs(diffs[i]) / (abs(diffs[i]) + abs(diffs[i + 1]))
                        break
                if cross is None:
                    sentences.append(f"'{top_main}' 가중치를 0~1 전 구간에서 변화시켜도 {a}가 {champ}를 역전하지 않습니다.")
                elif cross > w0:
                    sentences.append(f"'{top_main}' 가중치가 현재({w0:.3f})보다 상승해 {cross:.3f}를 초과하면 {a}가 1순위로 역전됩니다.")
                else:
                    sentences.append(f"'{top_main}' 가중치가 현재({w0:.3f})보다 하락해 {cross:.3f} 미만이 되면 {a}가 1순위로 역전됩니다.")
            r = 2
            for s in sentences:
                ws.merge_range(r, 0, r, 2 + len(alts), s, F["wrap"])
                ws.set_row(r, 28)
                r += 1
            r += 1
            hdr_row = r
            r = _table(ws, r, [f"{top_main} 가중치"] + alts + ["1위 대안"],
                       [[w] + [sens[i][a] for a in alts] + [max(alts, key=lambda a: sens[i][a])] for i, w in enumerate(steps)],
                       ["num3"] + ["num3"] * len(alts) + ["body"],
                       widths=[16] + [14] * len(alts) + [12])
            chart = wb.add_chart({"type": "line"})
            for ai, a in enumerate(alts):
                chart.add_series({
                    "name": a,
                    "categories": ["(대안) 민감도분석", hdr_row + 1, 0, hdr_row + len(steps), 0],
                    "values": ["(대안) 민감도분석", hdr_row + 1, 1 + ai, hdr_row + len(steps), 1 + ai],
                    "marker": {"type": "circle", "size": 4},
                    "line": {"width": 1.75},
                })
            chart.set_title({"name": f"{top_main} 가중치 변화에 따른 대안 종합점수"})
            chart.set_x_axis({"name": f"{top_main} 가중치"})
            chart.set_y_axis({"name": "대안 종합점수"})
            chart.set_size({"width": 760, "height": 420})
            ws.insert_chart(hdr_row, 3 + len(alts), chart)
            ws.write(r + 1, 0, "※ 다른 1계층 요인의 가중치는 현재 비율을 유지하며 비례 조정됩니다. 종합점수는 계층 결합(표2) 방식입니다.", F["note"])

    # ========== 시트 4: (대안) 잎별 상세분석 ==========
    ws = wb.add_worksheet("(대안) 잎별 상세분석")
    ws.write(0, 0, "최하위 요인별 대안 평가 상세 (종합 행렬 · 개인별 가중치)", F["title"])
    r = 2
    for li, lf in enumerate(leaves):
        det = leaf_detail.get(lf) or {}
        res = det.get("res")
        ws.write(r, 0, f"{li + 1}. [{lf}] 대안 평가 상세", F["section"]); r += 1
        ws.write(r, 0, f"분석 제외 사례수: {int(det.get('excluded_count', 0) or 0)}건"); r += 1
        if res is None or (hasattr(res, "empty") and res.empty):
            ws.write(r, 0, "유효 응답이 없습니다."); r += 2
            continue
        gmat = det.get("group_matrix")
        if gmat is not None:
            ws.write(r, 0, f"[{lf} 기준 대안 평가 종합 행렬]", F["section"]); r += 1
            hdr = [""] + alts + ["", "전체 일관성 지표", ""]
            for c, h in enumerate(hdr):
                if h:
                    ws.write(r, c, h, F["header"])
            r += 1
            gmat_arr = np.asarray(gmat, dtype=float)
            for i, a in enumerate(alts):
                ws.write(r, 0, a, F["rowhead"])
                for j in range(len(alts)):
                    if i == j:
                        ws.write_number(r, 1 + j, 1.0, F["diag"])
                    else:
                        ws.write_number(r, 1 + j, float(gmat_arr[i, j]), F["num3"])
                if i == 0:
                    ws.write(r, 2 + len(alts), "전체 CI", F["body"])
                    if det.get("group_ci") is not None:
                        ws.write_number(r, 3 + len(alts), float(det["group_ci"]), F["num3"])
                if i == 1:
                    ws.write(r, 2 + len(alts), "전체 CR", F["body"])
                    if det.get("group_cr") is not None:
                        ws.write_number(r, 3 + len(alts), float(det["group_cr"]), F["num3"])
                r += 1
            r += 1
        ws.write(r, 0, "[개인별 가중치 및 일관성]", F["section"]); r += 1
        p_headers = ["ID", "Type"] + [f"Weight_{a}" for a in alts] + ["Original_CR", "Final_CR", "보정 여부"]
        for c, h in enumerate(p_headers):
            ws.write(r, c, h, F["header"])
        r += 1
        res_sorted = res.sort_values("ID") if "ID" in res.columns else res
        for _, row in res_sorted.iterrows():
            ocr = float(row.get("Original_CR", 0.0) or 0.0)
            fcr = float(row.get("Final_CR", 0.0) or 0.0)
            ws.write(r, 0, str(row.get("ID", "")), F["body"])
            ws.write(r, 1, str(row.get("Type", "")), F["body"])
            for ci, a in enumerate(alts):
                ws.write_number(r, 2 + ci, float(row.get(f"Weight_{a}", 0.0) or 0.0), F["num3"])
            for kcr, crv in enumerate((ocr, fcr)):
                ws.write_number(r, 2 + len(alts) + kcr, crv, F["yellow_num"] if crv > float(cr_thr) else F["num3"])
            ws.write(r, 4 + len(alts), "보정" if bool(row.get("Corrected", False)) else "", F["body"])
            r += 1
        r += 1
    ws.set_column(0, 0, 18); ws.set_column(1, 1, 14)
    for ci in range(len(alts) + 3):
        ws.set_column(2 + ci, 2 + ci, 13)

    # ========== 시트 5: (대안) 개인별 결과 ==========
    ws = wb.add_worksheet("(대안) 개인별 결과")
    ws.write(0, 0, "개인별 대안 평가 결과", F["title"])
    r = 2
    if leaf_detail:
        ws.write(r, 0, "1. 최하위 요인별 일관성(CR) 요약", F["section"]); r += 1
        crows = []
        for lf in leaves:
            det = leaf_detail.get(lf) or {}
            res = det.get("res")
            if res is None or (hasattr(res, "empty") and res.empty):
                continue
            ocr = pd.to_numeric(res.get("Original_CR"), errors="coerce")
            fcr = pd.to_numeric(res.get("Final_CR"), errors="coerce")
            corr_n = int(res.get("Corrected").astype(bool).sum()) if "Corrected" in res.columns else 0
            crows.append([lf, len(res), int(det.get("excluded_count", 0) or 0),
                          float(ocr.mean()), float(fcr.mean()), float(fcr.max()), corr_n])
        r = _table(ws, r, ["최하위 요인", "유효 응답", "제외", "평균 Original CR", "평균 Final CR", "최대 Final CR", "보정된 응답 수"],
                   crows, ["body", "body", "body", "num3", "num3", "num3", "body"],
                   widths=[22, 12, 10, 17, 15, 15, 15])
        ws.write(r, 0, "※ Final CR은 임계값 초과 시 자동 보정을 거친 뒤의 값입니다. 보정 후에도 임계값을 넘은 응답은 제외됩니다.", F["note"])
        r += 2
    ws.write(r, 0, f"{2 if leaf_detail else 1}. 개인별 대안 종합점수", F["section"]); r += 1
    if not indiv.empty:
        irows = []
        for _, row in indiv.iterrows():
            irows.append([str(row.get("ID", "")), str(row.get("Type", ""))]
                         + [float(row.get(f"Score_{a}", 0.0) or 0.0) for a in alts]
                         + [str(row.get("1위 대안", ""))])
        _table(ws, r, ["ID", "Type"] + alts + ["1위 대안"], irows,
               ["body", "body"] + ["num3"] * len(alts) + ["body"],
               widths=[22, 14] + [14] * len(alts) + [12])
    return True


import pandas as pd
import numpy as np
import yfinance as yf

def test_model(w_fx, w_wti, w_sp, w_vx, w_tech, mode="new"):
    start_date = "2016-06-16"
    end_date = pd.Timestamp.now().strftime('%Y-%m-%d')
    tickers = ['^KS11', '^GSPC', 'KRW=X', 'CL=F', '^VIX', '^TNX', 'HG=F', 'EEM']
    df = yf.download(tickers, start=start_date, end=end_date, progress=False)['Close'].ffill()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    _ks_s = df['^KS11'].ffill()
    _sp_s = df['^GSPC'].ffill()
    _fx_s = df['KRW=X'].ffill()
    _wt_s = df['CL=F'].ffill()
    _vx_s = df['^VIX'].ffill()
    _b10_s = df['^TNX'].ffill()
    _cp_s = df['HG=F'].ffill()
    _em_s = df['EEM'].ffill()
    _ma20 = _ks_s.rolling(window=20).mean()
    
    def calc_rolling_z_score(s, inverse=False):
        mu = s.rolling(window=252).mean()
        std = s.rolling(window=252).std().replace(0, 1e-9)
        z = (s - mu) / std
        score = 100 / (1 + np.exp(-z))
        return 100 - score if inverse else score
    
    s_fx = calc_rolling_z_score(_fx_s)
    s_wt = calc_rolling_z_score(_wt_s)
    s_sp = calc_rolling_z_score(_sp_s, True)
    s_vx = calc_rolling_z_score(_vx_s)
    t = np.clip(100.0 - (_ks_s / _ma20 - 0.9) * 500.0, 0, 100.0)
    
    m_old = (calc_rolling_z_score(_fx_s) + calc_rolling_z_score(_b10_s) + calc_rolling_z_score(_cp_s, True)) / 3.0
    s_em = calc_rolling_z_score(_em_s, True)

    if mode == "new":
        tot_w = w_fx + w_wti + w_sp + w_vx + w_tech
        base = (s_fx * w_fx + s_wt * w_wti + s_sp * w_sp + s_vx * w_vx + t * w_tech) / tot_w
    else:
        # Old model
        w_m, w_t, w_g, w_f, w_p = 0.2, 0.2, 0.2, 0.2, 0.2
        tot_w = w_m + w_t + w_g + w_f + w_p
        base = (m_old * w_m + t * w_t + s_sp * w_g + s_vx * w_f + s_em * w_p) / tot_w

    k_val = 0.5
    convex_risk = ((np.exp(k_val * base / 100.0) - 1.0) / (np.exp(k_val) - 1.0)) * 100.0
    
    eval_df = pd.DataFrame({'KOSPI': _ks_s, 'Risk': convex_risk}).dropna()
    
    best_hit_rate = 0
    best_n = 20
    best_signal_count = 0
    
    for n in range(5, 31):
        eval_df['Min_Future_KOSPI'] = eval_df['KOSPI'].rolling(window=n).min().shift(-n)
        eval_df['Max_Drawdown'] = (eval_df['Min_Future_KOSPI'] - eval_df['KOSPI']) / eval_df['KOSPI']
        
        high_risk_days = eval_df[eval_df['Risk'] >= 60]
        valid_high_risk = high_risk_days.dropna(subset=['Max_Drawdown'])
        hits = valid_high_risk[valid_high_risk['Max_Drawdown'] <= -0.05]
        
        hr = len(hits) / len(valid_high_risk) * 100 if len(valid_high_risk) > 0 else 0
        if hr > best_hit_rate:
            best_hit_rate = hr
            best_n = n
            best_signal_count = len(valid_high_risk)
            
    print(f"[{mode.upper()} MODEL] Dynamic Hit Rate (5-30 days): {best_hit_rate:.2f}% at n={best_n} (Signals: {best_signal_count})")
    
    # 5-day hit rate
    n = 5
    eval_df['Min_Future_KOSPI'] = eval_df['KOSPI'].rolling(window=n).min().shift(-n)
    eval_df['Max_Drawdown'] = (eval_df['Min_Future_KOSPI'] - eval_df['KOSPI']) / eval_df['KOSPI']
    high_risk_days = eval_df[eval_df['Risk'] >= 60]
    valid_high_risk = high_risk_days.dropna(subset=['Max_Drawdown'])
    hits = valid_high_risk[valid_high_risk['Max_Drawdown'] <= -0.05]
    hr5 = len(hits) / len(valid_high_risk) * 100 if len(valid_high_risk) > 0 else 0
    print(f"[{mode.upper()} MODEL] Strict 5-day Hit Rate: {hr5:.2f}% (Signals: {len(valid_high_risk)})")

test_model(0.15, 0.11, 0.12, 0.27, 0.35, mode="new")
test_model(0, 0, 0, 0, 0, mode="old")

import yfinance as yf
import pandas as pd
import numpy as np
import itertools
from datetime import datetime, timedelta

# 1. 데이터 다운로드 (최근 10년: 2016-06-16 ~ 2026-06-16)
end_date = "2026-06-16"
start_date = "2015-06-16" # 1년 전부터 시작해야 롤링 Z-Score 계산 가능 (2016-06-16부터 분석)

tickers = {
    "kospi": "^KS11",
    "sp500": "^GSPC",
    "fx": "KRW=X",
    "us10y": "^TNX",
    "vix": "^VIX",
    "copper": "HG=F",
    "eem": "EEM",
    "wti": "CL=F",
    "dxy": "DX-Y.NYB",
    # Panic indicators
    "gold": "GC=F",
    "jpy_krw": "JPYKRW=X",
    "usd_chf": "CHF=X",
    "vvix": "^VVIX"
}

print("Downloading historical data...")
df = yf.download(list(tickers.values()), start=start_date, end=end_date, progress=False)['Close'].ffill().bfill()
if isinstance(df.columns, pd.MultiIndex):
    df.columns = df.columns.get_level_values(0)

ks_s = df['^KS11']
sp_s = df['^GSPC']
fx_s = df['KRW=X']
b10_s = df['^TNX']
vx_s = df['^VIX']
cp_s = df['HG=F']
em_s = df['EEM']
wt_s = df['CL=F']
dx_s = df['DX-Y.NYB']

gd_s = df['GC=F']
jk_s = df['JPYKRW=X']
uf_s = df['CHF=X']
vv_s = df['^VVIX']

ma20 = ks_s.rolling(window=20).mean()

def calc_rolling_z_score(s, inverse=False):
    mu = s.rolling(window=252).mean()
    std = s.rolling(window=252).std().replace(0, 1e-9)
    z = (s - mu) / std
    score = 100 / (1 + np.exp(-z))
    return 100 - score if inverse else score

# 개별 지표 점수 계산
scores = {}
scores['fx'] = calc_rolling_z_score(fx_s)
scores['b10'] = calc_rolling_z_score(b10_s)
scores['cp'] = calc_rolling_z_score(cp_s, True)
scores['sp'] = calc_rolling_z_score(sp_s, True)
scores['vx'] = calc_rolling_z_score(vx_s)
scores['em'] = calc_rolling_z_score(em_s, True)
scores['wt'] = calc_rolling_z_score(wt_s)
scores['dx'] = calc_rolling_z_score(dx_s)
scores['tech'] = np.clip(100.0 - (ks_s / ma20 - 0.9) * 500.0, 0, 100.0)

# Panic scores
def calc_rolling_panic_score(series):
    # recent 5d mean vs past 1y
    # To compute this efficiently:
    r_5d = series.rolling(window=5).mean()
    mu = series.rolling(window=252).mean()
    std = series.rolling(window=252).std().replace(0, 1e-9)
    z = (r_5d - mu) / std
    panic = (z - 1.0) * 40
    return panic.clip(lower=0.0, upper=100.0)

p_gd = calc_rolling_panic_score(gd_s)
p_jk = calc_rolling_panic_score(jk_s)
p_uf = calc_rolling_panic_score(uf_s)
p_vv = calc_rolling_panic_score(vv_s)

# Combine panic score
active_panics = (p_gd > 30).astype(int) + (p_jk > 30).astype(int) + (p_uf > 30).astype(int) + (p_vv > 30).astype(int)
raw_panic_avg = (p_gd + p_jk + p_uf + p_vv) / 4.0
panic_multiplier = 1.0 + (active_panics * 0.5)
fin_panic = (raw_panic_avg * panic_multiplier).clip(upper=100.0)

# Filter for the last 10 years (from 2016-06-16)
analysis_start = "2016-06-16"
eval_idx = ks_s.index[ks_s.index >= analysis_start]

# Setup target: Max drawdown in next 5 days
n_days = 5
future_min = ks_s.rolling(window=n_days).min().shift(-n_days)
max_drawdown = (future_min - ks_s) / ks_s
is_panic = (max_drawdown <= -0.05).astype(int)

# Features we want to combine
feature_names = ['fx', 'b10', 'cp', 'sp', 'vx', 'em', 'wt', 'dx', 'tech']
# We want to find a combination of features and their weights that maximizes hit rate for n=5
# Let's define the base risk score for a combination of weights
# We can search over a grid of weights

def evaluate_weights(selected_features, weights, apply_panic=True):
    total_w = sum(weights)
    if total_w == 0:
        return 0, 0, 0
    
    # Weighted average of selected features
    base = sum(scores[f] * w for f, w in zip(selected_features, weights)) / total_w
    
    if apply_panic:
        # Panic override
        app_base = np.where(fin_panic > 60, np.maximum(base, fin_panic), base)
    else:
        app_base = base
        
    k_val = 0.5
    convex_risk = ((np.exp(k_val * app_base / 100.0) - 1.0) / (np.exp(k_val) - 1.0)) * 100.0
    
    eval_df = pd.DataFrame({'Risk': convex_risk, 'Is_Panic': is_panic}).loc[eval_idx].dropna()
    
    high_risk_days = eval_df[eval_df['Risk'] >= 60]
    if len(high_risk_days) == 0:
        return 0, 0, 0
    
    hits = high_risk_days[high_risk_days['Is_Panic'] == 1]
    hit_rate = len(hits) / len(high_risk_days) * 100
    
    return hit_rate, len(high_risk_days), len(hits)

# Evaluate the current model setup:
# Current features: macro (fx, b10, cp averaged), sp, vx, tech, em
# Current weights: w_macro, w_global (sp), w_fear (vx), w_tech (tech), w_peri (em)
# Let's say equal weights of 0.2
current_features = ['fx', 'b10', 'cp', 'sp', 'vx', 'tech', 'em']
# Let's map this to the current formula
# base = ( (fx+b10+cp)/3 * 0.2 + tech * 0.2 + sp * 0.2 + vx * 0.2 + em * 0.2 ) / 1.0
current_weights = [0.2/3, 0.2/3, 0.2/3, 0.2, 0.2, 0.2, 0.2]
curr_hr, curr_signals, curr_hits = evaluate_weights(current_features, current_weights, apply_panic=True)
print(f"Current model (equal weights) - 5-day Panic Hit Rate: {curr_hr:.2f}% (Signals: {curr_signals}, Hits: {curr_hits})")

# Let's perform grid search or random search for combinations of features and weights
import random
random.seed(42)

best_hr = 0
best_config = None

# We can try combinations of size 3 to 7 from the features
all_features = ['fx', 'b10', 'cp', 'sp', 'vx', 'em', 'wt', 'dx', 'tech']

# Let's sample a large number of random combinations and weights
for _ in range(5000):
    # Select subset of features
    num_feats = random.randint(3, len(all_features))
    feats = random.sample(all_features, num_feats)
    # Generate weights (e.g. multiples of 0.05 summing to 1.0)
    w_raw = [random.randint(0, 10) for _ in range(num_feats)]
    if sum(w_raw) == 0:
        continue
    w = [float(x)/sum(w_raw) for x in w_raw]
    
    hr, sigs, hits = evaluate_weights(feats, w, apply_panic=True)
    # We want a high hit rate, but we also need a reasonable number of signals (e.g. at least 30 signals in 10 years, which is about 3 per year on average)
    if sigs >= 30:
        if hr > best_hr or (hr == best_hr and sigs > best_config.get('sigs', 0) if best_config else False):
            best_hr = hr
            best_config = {
                'feats': feats,
                'weights': w,
                'hr': hr,
                'sigs': sigs,
                'hits': hits
            }

print("\n--- Best Optimized Model ---")
print(f"Features: {best_config['feats']}")
print(f"Weights: {[round(x, 4) for x in best_config['weights']]}")
print(f"Hit Rate: {best_config['hr']:.2f}%")
print(f"Signals: {best_config['sigs']}")
print(f"Hits: {best_config['hits']}")

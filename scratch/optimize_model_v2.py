import pandas as pd
import numpy as np
import random
from datetime import datetime

# Load downloaded data
df = pd.read_csv("g:/scratch/market_data_10y.csv", index_col=0, parse_dates=True)

# Select KOSPI trading days
ks_s = df['^KS11'].ffill()
# Align other series to KOSPI dates
df_aligned = df.reindex(ks_s.index).ffill()

ks_s = df_aligned['^KS11']
sp_s = df_aligned['^GSPC']
fx_s = df_aligned['KRW=X']
b10_s = df_aligned['^TNX']
vx_s = df_aligned['^VIX']
cp_s = df_aligned['HG=F']
em_s = df_aligned['EEM']
wt_s = df_aligned['CL=F']
dx_s = df_aligned['DX-Y.NYB']

gd_s = df_aligned['GC=F']
jk_s = df_aligned['JPYKRW=X']
uf_s = df_aligned['CHF=X']
vv_s = df_aligned['^VVIX']

ma20 = ks_s.rolling(window=20).mean()

def calc_rolling_z_score(s, inverse=False):
    mu = s.rolling(window=252).mean()
    std = s.rolling(window=252).std().replace(0, 1e-9)
    z = (s - mu) / std
    score = 100 / (1 + np.exp(-z))
    return 100 - score if inverse else score

# Individual scores
scores = {
    'fx': calc_rolling_z_score(fx_s),
    'b10': calc_rolling_z_score(b10_s),
    'cp': calc_rolling_z_score(cp_s, True),
    'sp': calc_rolling_z_score(sp_s, True),
    'vx': calc_rolling_z_score(vx_s),
    'em': calc_rolling_z_score(em_s, True),
    'wt': calc_rolling_z_score(wt_s),
    'dx': calc_rolling_z_score(dx_s),
    'tech': np.clip(100.0 - (ks_s / ma20 - 0.9) * 500.0, 0, 100.0)
}

# Panic scores
def calc_rolling_panic_score(series):
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

# Target: 5-day KOSPI drawdown <= -5%
n_days = 5
future_min = ks_s.rolling(window=n_days).min().shift(-n_days)
max_drawdown = (future_min - ks_s) / ks_s
is_panic = (max_drawdown <= -0.05).astype(int)

# Filter for the last 10 years (from 2016-06-16)
analysis_start = "2016-06-16"
eval_idx = ks_s.index[ks_s.index >= analysis_start]

def evaluate_weights(selected_features, weights, apply_panic=True):
    total_w = sum(weights)
    if total_w == 0:
        return 0, 0, 0
    
    base = sum(scores[f] * w for f, w in zip(selected_features, weights)) / total_w
    
    if apply_panic:
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

# Evaluate the current baseline
# macro: fx, b10, cp averaged (weight 0.2)
# sp (0.2), vx (0.2), tech (0.2), em (0.2)
current_features = ['fx', 'b10', 'cp', 'sp', 'vx', 'tech', 'em']
current_weights = [0.2/3, 0.2/3, 0.2/3, 0.2, 0.2, 0.2, 0.2]
curr_hr, curr_signals, curr_hits = evaluate_weights(current_features, current_weights, apply_panic=True)
print(f"Current model (equal weights) -> Hit Rate: {curr_hr:.2f}% (Signals: {curr_signals}, Hits: {curr_hits})")

# Let's perform random search for all combinations of features and weights
random.seed(42)

all_features = ['fx', 'b10', 'cp', 'sp', 'vx', 'em', 'wt', 'dx', 'tech']

results = []

for _ in range(20000):
    # Select subset of features (at least 3)
    num_feats = random.randint(3, len(all_features))
    feats = sorted(random.sample(all_features, num_feats))
    
    # Generate weights
    w_raw = [random.randint(0, 10) for _ in range(num_feats)]
    if sum(w_raw) == 0:
        continue
    w = [float(x)/sum(w_raw) for x in w_raw]
    
    hr, sigs, hits = evaluate_weights(feats, w, apply_panic=True)
    # We want a high hit rate but also a minimum number of signals (at least 50 days of caution in 10 years, i.e., average 5 days per year)
    if sigs >= 50:
        results.append({
            'feats': feats,
            'weights': w,
            'hr': hr,
            'sigs': sigs,
            'hits': hits
        })

# Sort by hit rate descending, then number of signals descending
results = sorted(results, key=lambda x: (-x['hr'], -x['sigs']))

print("\nTop 5 Optimized Configurations:")
for i, res in enumerate(results[:5]):
    print(f"\n#{i+1}: Hit Rate: {res['hr']:.2f}% (Signals: {res['sigs']}, Hits: {res['hits']})")
    print(f"  Features: {res['feats']}")
    print(f"  Weights: {[round(w, 4) for w in res['weights']]}")

import yfinance as yf
import pandas as pd
import time

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
    "gold": "GC=F",
    "jpy_krw": "JPYKRW=X",
    "usd_chf": "CHF=X",
    "vvix": "^VVIX"
}

end_date = "2026-06-16"
start_date = "2015-06-16"

df_list = {}
for name, ticker in tickers.items():
    print(f"Downloading {name} ({ticker})...")
    success = False
    for attempt in range(5):
        try:
            # yfinance cache can cause locked database, disable cache if possible
            # We can download by using yf.download with threads=False or using Ticker
            ticker_data = yf.download(ticker, start=start_date, end=end_date, progress=False, threads=False)
            if not ticker_data.empty:
                if isinstance(ticker_data.columns, pd.MultiIndex):
                    series = ticker_data['Close'].iloc[:, 0]
                else:
                    series = ticker_data['Close']
                df_list[ticker] = series
                success = True
                print(f"Successfully downloaded {name}")
                break
        except Exception as e:
            print(f"Attempt {attempt+1} failed for {name}: {e}")
            time.sleep(2)
    if not success:
        print(f"Failed to download {name} after 5 attempts.")

# Combine into a single DataFrame
merged_df = pd.DataFrame(df_list)
merged_df = merged_df.ffill().bfill()
merged_df.to_csv("g:/scratch/market_data_10y.csv")
print("Saved data to g:/scratch/market_data_10y.csv. Shape:", merged_df.shape)
print("Missing values per column:\n", merged_df.isna().sum())

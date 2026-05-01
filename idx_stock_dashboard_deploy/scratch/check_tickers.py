import pandas as pd
try:
    url = "https://raw.githubusercontent.com/datasets/idx-listed-companies/main/data/idx.csv"
    df = pd.read_csv(url)
    tickers = df["ticker"].dropna().unique().tolist()
    print(f"Total tickers: {len(tickers)}")
except Exception as e:
    print(f"Error: {e}")


import yfinance as yf
import pandas as pd

def test_yfinance_structure():
    ticker = "GC=F"
    print(f"Downloading {ticker}...")
    df = yf.download(ticker, period="1mo", interval="1d", progress=False)
    
    print("\nDataFrame Shape:", df.shape)
    print("\nColumns:", df.columns)
    print("\nHead:\n", df.head())
    
    if isinstance(df.columns, pd.MultiIndex):
        print("\n[INFO] Columns are MultiIndex")
        # Flatten
        try:
             # Dropping the 'Ticker' level if it exists
            df.columns = df.columns.droplevel(1) 
            print("\nFlattened Columns:", df.columns)
        except:
             print("Could not droplevel 1")
    else:
        print("\n[INFO] Columns are Single Index")

if __name__ == "__main__":
    test_yfinance_structure()

import yfinance as yf
import pandas as pd

def verify_ticker(ticker_name):
    print(f"\nVerifying {ticker_name}...")
    try:
        ticker = yf.Ticker(ticker_name)
        # Fetch last 5 days
        hist = ticker.history(period="5d")
        if hist.empty:
            print(f"❌ No data found for {ticker_name}")
            return None
        else:
            print(f"✅ Data found for {ticker_name}")
            print(hist[['Close']].tail())
            return hist
    except Exception as e:
        print(f"❌ Error fetching {ticker_name}: {e}")
        return None

def main():
    print("Starting yfinance verification...")
    
    # 1. BTC vs USD
    btc = verify_ticker("BTC-USD")
    
    # 2. USD vs TWD
    twd = verify_ticker("TWD=X")
    
    # 3. USD vs VND
    vnd = verify_ticker("VND=X")
    
    # 4. NTD vs VND (Cross Rate)
    if twd is not None and vnd is not None:
        print("\nCalculating NTD vs VND (Cross Rate)...")
        # Ensure alignment of dates
        df = pd.DataFrame()
        df['USD_TWD'] = twd['Close']
        df['USD_VND'] = vnd['Close']
        
        # Drop NaN to ensure we have data for both on the same days
        df = df.dropna()
        
        # Calculate 1 TWD = ? VND
        # (USD/VND) / (USD/TWD) = (VND / USD) * (USD / TWD) ?? No.
        # USD/VND = V
        # USD/TWD = T
        # 1 USD = V VND
        # 1 USD = T TWD
        # => T TWD = V VND
        # => 1 TWD = (V/T) VND
        df['TWD_VND'] = df['USD_VND'] / df['USD_TWD']
        
        print("✅ Cross Rate Calculated (TWD -> VND):")
        print(df[['TWD_VND']].tail())
    else:
        print("❌ Cannot calculate cross rate due to missing data.")

if __name__ == "__main__":
    main()

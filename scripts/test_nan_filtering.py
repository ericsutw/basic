
import pandas as pd
import numpy as np
from pathlib import Path
import shutil
from currency_storage import CurrencyStorage

def test_nan_filtering():
    print("Testing CurrencyStorage NaN filtering...")
    
    # Setup test dir
    test_dir = "data/test_currency"
    storage = CurrencyStorage(data_dir=test_dir)
    
    # Create valid data
    df_valid = pd.DataFrame({
        'Date': [pd.Timestamp('2026-02-18'), pd.Timestamp('2026-02-19')],
        'Close': [30.5, 30.6]
    })
    
    # Create data with NaN
    df_nan = pd.DataFrame({
        'Date': [pd.Timestamp('2026-02-20')],
        'Close': [np.nan]
    })
    
    # Save valid data
    print("Saving valid data...")
    storage.save_data('TEST', df_valid)
    
    # Check latest
    latest = storage.get_latest_price('TEST')
    print(f"Latest after valid save: {latest['Close'] if latest is not None else 'None'}")
    
    # Save NaN data (simulating yfinance returning empty row)
    print("Saving NaN data...")
    # Direct append to file to simulate what might assume happens, 
    # OR use save_data (which we want to test if it filters, OR if load_data filters)
    
    # We want to test if STORAGE filters it. 
    # Let's write the csv manually first to ensure it contains NaN, then try to load it.
    file_path = storage.get_file_path('TEST')
    
    # Manually append NaN row
    # The file has header: Date,Close (from df_valid)
    # We append a row with Date and empty Close
    with open(file_path, 'a') as f:
        f.write("2026-02-20,nan\n") # Date, Close=nan
        
    print("Checking manual NaN append...")
    df_raw = pd.read_csv(file_path)
    print("Raw CSV tail:")
    print(df_raw.tail())
    
    print("Loading via storage (should filter)...")
    df_loaded = storage.load_data('TEST')
    print("Loaded DF tail:")
    print(df_loaded.tail())
    
    latest_clean = storage.get_latest_price('TEST')
    print(f"Latest after clean load: {latest_clean['Close'] if latest_clean is not None else 'None'}")
    
    if latest_clean is not None and pd.isna(latest_clean['Close']):
        print("❌ FAILED: Latest price is NaN")
    elif latest_clean is None:
         print("❌ FAILED: Latest price is None")
    else:
        print("✅ PASSED: Latest price is valid")

    # Clean up
    if Path(test_dir).exists():
        import shutil
        shutil.rmtree(test_dir)

if __name__ == "__main__":
    test_nan_filtering()

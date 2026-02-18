import pandas as pd
from pathlib import Path
from datetime import datetime
import os

class CurrencyStorage:
    def __init__(self, data_dir: str = "data/currency"):
        """
        初始化匯率資料儲存
        Args:
            data_dir: 資料儲存目錄
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def get_file_path(self, symbol: str) -> Path:
        """取得指定幣別的檔案路徑"""
        # File name safe: BTC-USD -> BTC_USD
        safe_symbol = symbol.replace("=", "_").replace("-", "_")
        return self.data_dir / f"{safe_symbol}.csv"

    def save_data(self, symbol: str, df: pd.DataFrame):
        """
        儲存匯率資料
        Args:
            symbol: 幣別代碼
            df: 資料 DataFrame (必須包含 'Date', 'Close')
        """
        file_path = self.get_file_path(symbol)
        
        # 確保 Date 是索引或是欄位
        if 'Date' not in df.columns and df.index.name == 'Date':
            df = df.reset_index()
            
        # 只保留需要的欄位
        if 'Close' in df.columns:
            columns = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']
            # 過濾存在的欄位
            existing_cols = [c for c in columns if c in df.columns]
            # 過濾存在的欄位
            existing_cols = [c for c in columns if c in df.columns]
            df = df[existing_cols]
            
        # 移除 Close 為 NaN 的資料
        if 'Close' in df.columns:
            df = df.dropna(subset=['Close'])
        
        if df.empty:
            return
            
        # 如果檔案存在，讀取並合併
        if file_path.exists():
            try:
                old_df = pd.read_csv(file_path)
                old_df['Date'] = pd.to_datetime(old_df['Date'], utc=True)
                
                # 確保新資料也是 datetime (utc=True)
                if not pd.api.types.is_datetime64_any_dtype(df['Date']):
                    df['Date'] = pd.to_datetime(df['Date'], utc=True)
                
                # 合併並去重
                combined = pd.concat([old_df, df]).drop_duplicates(subset=['Date'], keep='last')
                combined = combined.sort_values('Date')
                
                combined.to_csv(file_path, index=False, encoding='utf-8-sig')
            except Exception as e:
                print(f"合併資料失敗，將覆寫檔案: {e}")
                df.to_csv(file_path, index=False, encoding='utf-8-sig')
        else:
            df.to_csv(file_path, index=False, encoding='utf-8-sig')

    def load_data(self, symbol: str) -> pd.DataFrame:
        """載入匯率資料"""
        file_path = self.get_file_path(symbol)
        if not file_path.exists():
            return pd.DataFrame()
            
        try:
            df = pd.read_csv(file_path)
            df['Date'] = pd.to_datetime(df['Date'])
            return df
        except Exception:
            return pd.DataFrame()

    def get_latest_price(self, symbol: str):
        """取得最新價格"""
        df = self.load_data(symbol)
        if df.empty:
            return None
        return df.iloc[-1]

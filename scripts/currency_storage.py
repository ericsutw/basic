import pandas as pd
from pathlib import Path
from datetime import datetime
import os

class CurrencyStorage:
    def __init__(self, data_dir: str = None):
        """
        初始化匯率資料儲存
        Args:
            data_dir: 資料儲存目錄
        """
        if data_dir is None:
            base_dir = Path(__file__).parent.parent
            self.data_dir = base_dir / "data" / "currency"
        else:
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
        if 'Date' not in df.columns:
            if df.index.name in ['Date', 'Datetime']:
                df = df.reset_index().rename(columns={df.index.name: 'Date'})
            elif not df.empty and not isinstance(df.index, pd.RangeIndex):
                # 如果是其他時間序列索引，也嘗試重置
                df = df.reset_index().rename(columns={df.index.name: 'Date'})
            
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
                
                # --- 資料清理邏輯 (Cleanup Logic) ---
                # 清除超過 3 天以前的即時價格，每個日期僅保留最後一筆
                # 確保使用的是 UTC 時間進行比較
                now_utc = pd.Timestamp.now(tz='UTC')
                cutoff_date = now_utc - pd.Timedelta(days=3)
                
                # 確保 Date 是 UTC
                combined['Date'] = pd.to_datetime(combined['Date'], utc=True)
                
                # 區分「近期資料」(3天內) 與「歷史資料」(超過3天)
                recent_mask = combined['Date'] >= cutoff_date
                recent_data = combined[recent_mask]
                old_data = combined[~recent_mask]
                
                if not old_data.empty:
                    # 對舊資料按日期分組，僅保留每天的最後一筆 (收盤)
                    # 建立暫時日期欄位
                    temp_dates = old_data['Date'].dt.date
                    old_data = old_data.assign(Date_Day=temp_dates).sort_values('Date').groupby('Date_Day').tail(1)
                    old_data = old_data.drop(columns=['Date_Day'])
                
                combined = pd.concat([old_data, recent_data]).sort_values('Date').drop_duplicates(subset=['Date'], keep='last')
                # -----------------------------------
                
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
            if 'Close' in df.columns:
                df['Close'] = pd.to_numeric(df['Close'], errors='coerce')
                df = df.dropna(subset=['Close'])
            return df
        except Exception:
            return pd.DataFrame()

    def get_latest_price(self, symbol: str):
        """取得最新價格"""
        df = self.load_data(symbol)
        if df.empty:
            return None
        return df.iloc[-1]

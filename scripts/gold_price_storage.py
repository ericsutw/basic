#!/usr/bin/env python3
"""
Gold Price Storage Module
管理黃金價格資料的本地儲存
"""

import pandas as pd
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Tuple


class GoldPriceStorage:
    def __init__(self, data_dir: str = "data"):
        """
        初始化儲存模組
        
        Args:
            data_dir: 資料目錄路徑
        """
        self.data_dir = Path(data_dir)
        self.data_file = self.data_dir / "gold_prices.csv"
        self.backup_file = self.data_dir / "gold_prices_backup.csv"
        
        # 確保資料目錄存在
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化資料檔案
        if not self.data_file.exists():
            self._create_empty_file()
    
    def _create_empty_file(self):
        """建立空的資料檔案"""
        df = pd.DataFrame(columns=['date', 'buy_price', 'sell_price', 'timestamp'])
        df.to_csv(self.data_file, index=False, encoding='utf-8-sig')
    
    def load_data(self) -> pd.DataFrame:
        """
        載入本地資料
        
        Returns:
            包含所有歷史資料的 DataFrame
        """
        if not self.data_file.exists() or os.path.getsize(self.data_file) == 0:
            return pd.DataFrame(columns=['date', 'buy_price', 'sell_price', 'timestamp'])
        
        try:
            df = pd.read_csv(self.data_file, encoding='utf-8-sig')
            # 確保 date 欄位是日期格式
            if not df.empty:
                df['date'] = pd.to_datetime(df['date'])
            return df
        except Exception as e:
            print(f"讀取資料檔案時發生錯誤: {e}")
            return pd.DataFrame(columns=['date', 'buy_price', 'sell_price', 'timestamp'])
    
    def save_data(self, df: pd.DataFrame, backup: bool = True):
        """
        儲存資料到檔案
        
        Args:
            df: 要儲存的 DataFrame
            backup: 是否建立備份
        """
        # 建立備份
        if backup and self.data_file.exists():
            try:
                import shutil
                shutil.copy2(self.data_file, self.backup_file)
            except Exception as e:
                print(f"建立備份時發生錯誤: {e}")
        
        # 儲存資料
        df.to_csv(self.data_file, index=False, encoding='utf-8-sig')
    
    def merge_and_save(self, new_data: pd.DataFrame):
        """
        合併新資料與現有資料並儲存
        
        Args:
            new_data: 新抓取的資料
        """
        # 載入現有資料
        existing_data = self.load_data()
        
        # 合併資料
        if existing_data.empty:
            merged_data = new_data
        else:
            # 合併並去重（相同日期保留最新的）
            merged_data = pd.concat([existing_data, new_data], ignore_index=True)
            merged_data['date'] = pd.to_datetime(merged_data['date'])
            merged_data = merged_data.sort_values('timestamp', ascending=False)
            merged_data = merged_data.drop_duplicates(subset=['date'], keep='first')
            merged_data = merged_data.sort_values('date')
        
        # 儲存
        self.save_data(merged_data)
        return merged_data
    
    def get_available_date_range(self) -> Optional[Tuple[datetime, datetime]]:
        """
        取得本地資料的日期範圍
        
        Returns:
            (最早日期, 最晚日期) 或 None（如果沒有資料）
        """
        df = self.load_data()
        if df.empty:
            return None
        
        df['date'] = pd.to_datetime(df['date'])
        return (df['date'].min(), df['date'].max())
    
    def find_missing_dates(self, start_date: datetime, end_date: datetime) -> List[Tuple[datetime, datetime]]:
        """
        找出指定範圍內缺失的日期區間
        
        Args:
            start_date: 開始日期
            end_date: 結束日期
        
        Returns:
            缺失的日期區間列表 [(start1, end1), (start2, end2), ...]
        """
        df = self.load_data()
        
        # 如果沒有資料，整個範圍都是缺失的
        if df.empty:
            return [(start_date, end_date)]
        
        df['date'] = pd.to_datetime(df['date'])
        existing_dates = set(df['date'].dt.date)
        
        # 生成完整的日期範圍（只包含工作日，因為週末沒有牌價）
        all_dates = pd.date_range(start=start_date, end=end_date, freq='D')
        
        # 找出缺失的日期
        missing_dates = []
        for date in all_dates:
            if date.date() not in existing_dates:
                missing_dates.append(date)
        
        # 將連續的缺失日期合併成區間
        if not missing_dates:
            return []
        
        ranges = []
        range_start = missing_dates[0]
        range_end = missing_dates[0]
        
        for i in range(1, len(missing_dates)):
            if (missing_dates[i] - missing_dates[i-1]).days == 1:
                range_end = missing_dates[i]
            else:
                ranges.append((range_start, range_end))
                range_start = missing_dates[i]
                range_end = missing_dates[i]
        
        ranges.append((range_start, range_end))
        return ranges
    
    def get_data_in_range(self, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """
        取得指定日期範圍的資料
        
        Args:
            start_date: 開始日期
            end_date: 結束日期
        
        Returns:
            指定範圍內的資料
        """
        df = self.load_data()
        if df.empty:
            return df
        
        df['date'] = pd.to_datetime(df['date'])
        mask = (df['date'] >= start_date) & (df['date'] <= end_date)
        return df[mask].sort_values('date')
    
    def get_stats(self) -> dict:
        """
        取得資料統計資訊
        
        Returns:
            統計資訊字典
        """
        df = self.load_data()
        if df.empty:
            return {
                'total_records': 0,
                'date_range': None,
                'latest_update': None
            }
        
        df['date'] = pd.to_datetime(df['date'])
        return {
            'total_records': len(df),
            'date_range': (df['date'].min(), df['date'].max()),
            'latest_update': df['timestamp'].max() if 'timestamp' in df.columns else None,
            'buy_price_range': (df['buy_price'].min(), df['buy_price'].max()) if 'buy_price' in df.columns else None,
            'sell_price_range': (df['sell_price'].min(), df['sell_price'].max()) if 'sell_price' in df.columns else None
        }


if __name__ == '__main__':
    # 測試程式碼
    storage = GoldPriceStorage()
    
    # 測試資料
    test_data = pd.DataFrame({
        'date': pd.date_range(start='2026-02-10', end='2026-02-15', freq='D'),
        'buy_price': [2100, 2110, 2105, 2115, 2120, 2125],
        'sell_price': [2150, 2160, 2155, 2165, 2170, 2175],
        'timestamp': [datetime.now().isoformat()] * 6
    })
    
    print("儲存測試資料...")
    storage.merge_and_save(test_data)
    
    print("\n資料統計:")
    stats = storage.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    print("\n查找缺失日期 (2026-02-01 到 2026-02-20):")
    missing = storage.find_missing_dates(
        datetime(2026, 2, 1),
        datetime(2026, 2, 20)
    )
    for start, end in missing:
        print(f"  {start.date()} 到 {end.date()}")

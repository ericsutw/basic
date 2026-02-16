#!/usr/bin/env python3
"""
Gold Price Scraper Module
從台灣銀行網站抓取黃金存摺牌價資料
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import time
import json
from typing import Optional, List, Tuple


class RateLimitError(Exception):
    """查詢間隔限制錯誤"""
    pass


class GoldPriceScraper:
    def __init__(self, data_dir: str = "data"):
        """
        初始化爬蟲
        
        Args:
            data_dir: 資料目錄（用於儲存時間戳記錄）
        """
        self.base_url = "https://rate.bot.com.tw/gold/passbook"
        self.data_dir = Path(data_dir)
        self.timestamp_file = self.data_dir / ".last_query_time"
        self.min_interval = 60  # 最小查詢間隔（秒）
        
        # 確保資料目錄存在
        self.data_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_last_query_time(self) -> Optional[datetime]:
        """取得上次查詢時間"""
        if not self.timestamp_file.exists():
            return None
        
        try:
            with open(self.timestamp_file, 'r') as f:
                data = json.load(f)
                return datetime.fromisoformat(data['last_query_time'])
        except Exception:
            return None
    
    def _update_last_query_time(self):
        """更新上次查詢時間"""
        with open(self.timestamp_file, 'w') as f:
            json.dump({
                'last_query_time': datetime.now().isoformat()
            }, f)
    
    def _check_rate_limit(self, wait: bool = False) -> bool:
        """
        檢查查詢間隔限制
        
        Args:
            wait: 如果間隔不足，是否等待
        
        Returns:
            是否可以查詢
        
        Raises:
            RateLimitError: 如果間隔不足且 wait=False
        """
        last_time = self._get_last_query_time()
        if last_time is None:
            return True
        
        elapsed = (datetime.now() - last_time).total_seconds()
        remaining = self.min_interval - elapsed
        
        if remaining > 0:
            if wait:
                print(f"等待 {remaining:.0f} 秒後繼續查詢...")
                time.sleep(remaining)
                return True
            else:
                raise RateLimitError(
                    f"查詢間隔不足，請等待 {remaining:.0f} 秒後再試。"
                    f"（上次查詢時間: {last_time.strftime('%Y-%m-%d %H:%M:%S')}）"
                )
        
        return True
    
    def fetch_data(self, start_date: datetime, end_date: datetime, 
                   wait_if_needed: bool = True) -> pd.DataFrame:
        """
        抓取指定日期範圍的黃金價格資料
        
        Args:
            start_date: 開始日期
            end_date: 結束日期
            wait_if_needed: 如果查詢間隔不足，是否等待
        
        Returns:
            包含黃金價格的 DataFrame
        """
        all_data = []
        current = start_date.replace(day=1)
        # 計算結束日期的月份，確保包含結束日期當月
        end_month = end_date.replace(day=1)
        
        while current <= end_month:
            # 檢查查詢間隔
            self._check_rate_limit(wait=wait_if_needed)
            
            year = str(current.year)
            month = f"{current.month:02d}"
            
            # 建構查詢參數
            # 使用 /gold/chart 端點的參數
            data = {
                "search_range": "date",
                "year": year,
                "month": month,
                "currency": "TWD",
                "search_hours": "0" # 0=營業時間黃金存摺牌價
            }
            
            try:
                print(f"正在查詢 {year}年{month}月 的資料...")
                
                # 發送請求
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Referer': 'https://rate.bot.com.tw/gold/passbook'
                }
                # 改用 POST 請求到 /gold/chart
                response = requests.post("https://rate.bot.com.tw/gold/chart", data=data, headers=headers, timeout=30)
                response.raise_for_status()
                
                # 更新查詢時間
                self._update_last_query_time()
                
                # 解析 HTML
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 找到資料表格
                table = soup.find('table', class_='table')
                if not table:
                    print(f"警告：未找到 {year}/{month} 的資料表格")
                else:
                    # 解析表格
                    df = self._parse_table(table)
                    if not df.empty:
                        all_data.append(df)
                        print(f"成功抓取 {len(df)} 筆資料")
                
            except requests.RequestException as e:
                print(f"網路請求錯誤: {e}")
            except Exception as e:
                print(f"解析資料時發生錯誤: {e}")
            
            # 移動到下個月
            if current.month == 12:
                current = current.replace(year=current.year+1, month=1)
            else:
                current = current.replace(month=current.month+1)
            
            # 如果還有下一個月，等待一下
            if current <= end_month and wait_if_needed:
                time.sleep(1) # 稍微等待避免太快
        
        if not all_data:
            return pd.DataFrame(columns=['date', 'buy_price', 'sell_price', 'timestamp'])
            
        # 合併所有資料
        result = pd.concat(all_data, ignore_index=True)
        
        # 過濾日期範圍
        if not result.empty:
            # 移除包含 NaN 的行
            result = result.dropna(subset=['date'])
            # 確保日期格式
            result['date'] = pd.to_datetime(result['date'])
            # 過濾
            mask = (result['date'] >= start_date) & (result['date'] <= end_date)
            result = result[mask]
            # 排序
            result = result.sort_values('date')
            
        return result
    
    def _parse_table(self, table) -> pd.DataFrame:
        """
        解析 HTML 表格
        
        Args:
            table: BeautifulSoup 表格物件
        
        Returns:
            解析後的 DataFrame
        """
        rows = []
        
        # 找到所有資料列
        tbody = table.find('tbody')
        if not tbody:
            return pd.DataFrame(columns=['date', 'buy_price', 'sell_price', 'timestamp'])
        
        for tr in tbody.find_all('tr'):
            cols = tr.find_all('td')
            if len(cols) >= 5: # 新版表格有 5 欄
                try:
                    # 提取資料
                    # 索引 0: 日期 (2026/01/30)
                    # 索引 3: 本行買入價格 (5211)
                    # 索引 4: 本行賣出價格 (5267)
                    date_str = cols[0].text.strip()
                    buy_price = float(cols[3].text.strip().replace(',', ''))
                    sell_price = float(cols[4].text.strip().replace(',', ''))
                    
                    # 解析日期
                    date = pd.to_datetime(date_str)
                    
                    rows.append({
                        'date': date,
                        'buy_price': buy_price,
                        'sell_price': sell_price,
                        'timestamp': datetime.now().isoformat()
                    })
                except (ValueError, AttributeError) as e:
                    print(f"解析資料列時發生錯誤: {e}")
                    continue
        
        return pd.DataFrame(rows)
    
    def fetch_missing_ranges(self, missing_ranges: List[Tuple[datetime, datetime]], 
                           wait_if_needed: bool = True) -> pd.DataFrame:
        """
        抓取多個缺失的日期範圍
        
        Args:
            missing_ranges: 缺失的日期範圍列表
            wait_if_needed: 如果查詢間隔不足，是否等待
        
        Returns:
            合併後的資料
        """
        all_data = []
        
        for i, (start, end) in enumerate(missing_ranges):
            print(f"\n[{i+1}/{len(missing_ranges)}] 查詢範圍: {start.date()} 到 {end.date()}")
            
            data = self.fetch_data(start, end, wait_if_needed=wait_if_needed)
            if not data.empty:
                all_data.append(data)
            
            # 如果還有更多範圍要查詢，等待一下
            if i < len(missing_ranges) - 1:
                print(f"等待 {self.min_interval} 秒後繼續下一個範圍...")
                time.sleep(self.min_interval)
        
        if all_data:
            return pd.concat(all_data, ignore_index=True)
        else:
            return pd.DataFrame(columns=['date', 'buy_price', 'sell_price', 'timestamp'])
    
    def get_latest_price(self, wait_if_needed: bool = True) -> Optional[dict]:
        """
        取得最新的黃金價格（今天）
        
        Args:
            wait_if_needed: 如果查詢間隔不足，是否等待
        
        Returns:
            最新價格資料字典
        """
        today = datetime.now()
        data = self.fetch_data(today, today, wait_if_needed=wait_if_needed)
        
        if data.empty:
            return None
        
        latest = data.iloc[-1]
        return {
            'date': latest['date'],
            'buy_price': latest['buy_price'],
            'sell_price': latest['sell_price'],
            'timestamp': latest['timestamp']
        }


if __name__ == '__main__':
    # 測試程式碼
    scraper = GoldPriceScraper()
    
    # 測試抓取最近一週的資料
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    
    print("測試抓取資料...")
    print(f"日期範圍: {start_date.date()} 到 {end_date.date()}")
    
    try:
        data = scraper.fetch_data(start_date, end_date)
        print(f"\n成功抓取 {len(data)} 筆資料")
        if not data.empty:
            print("\n前 5 筆資料:")
            print(data.head())
    except RateLimitError as e:
        print(f"錯誤: {e}")
    except Exception as e:
        print(f"發生錯誤: {e}")

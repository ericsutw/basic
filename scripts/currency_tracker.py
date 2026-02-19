#!/usr/bin/env python3
"""
Currency Tracker Module
匯率與加密貨幣追蹤工具
"""

import argparse
import sys
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from pathlib import Path

# Add script directory to path to import local modules
sys.path.append(str(Path(__file__).parent))

from currency_storage import CurrencyStorage
from currency_visualizer import CurrencyVisualizer

# 定義支援的幣別與 yfinance 代碼
CURRENCY_PAIRS = {
    'BTC': {'ticker': 'BTC-USD', 'name': 'Bitcoin (BTC) vs USD'},
    'USDTWD': {'ticker': 'TWD=X', 'name': 'USD vs NTD (TWD)'},
    'USDVND': {'ticker': 'VND=X', 'name': 'USD vs VND'},
    'TSMC': {'ticker': '2330.TW', 'name': 'TSMC (2330)'},
    'UMC': {'ticker': '2303.TW', 'name': 'UMC (2303)'},
    'Creative': {'ticker': '3443.TW', 'name': 'Creative (3443)'},
    'IntlGold': {'ticker': 'GC=F', 'name': 'Intl Gold (USD/oz)'},
    'NTDVND': {'ticker': 'CALCULATED', 'name': 'NTD vs VND (Cross Rate)'}
}

class CurrencyTracker:
    def __init__(self):
        self.storage = CurrencyStorage()
        self.visualizer = CurrencyVisualizer(self.storage)

    def update(self):
        """更新所有匯率資料"""
        print("開始更新匯率資料...\n")
        
        # 1. 更新標準 Tickers
        for code, info in CURRENCY_PAIRS.items():
            ticker = info['ticker']
            if ticker == 'CALCULATED':
                continue
                
            print(f"[{code}] 正在抓取 {ticker} ({info['name']})...")
            try:
                # 抓取最大可用歷史資料 (Yahoo Finance max)
                # auto_adjust=True 會自動調整股價
                df = yf.download(ticker, period="max", interval="1d", progress=False)
                
                if df.empty:
                    print(f"  [NO DATA] 無資料: {ticker}")
                    continue
                
                # yfinance 回傳的 DataFrame 索引是 Date
                # 欄位通常是 Open, High, Low, Close, Adj Close, Volume
                # 我們需要重置索引變成欄位，或者 storage 會處理
                # storage.save_data 會處理 index.name == 'Date'
                
                # 注意：yf.download 在新版可能回傳 MultiIndex columns (如果抓多個)
                # 這裡只抓一個，應該是單層 Index
                
                # Flatten MultiIndex columns (yfinance > 0.2.x)
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.droplevel(1)
                
                count = len(df)
                self.storage.save_data(code, df)
                print(f"  [OK] 更新完成，共 {count} 筆資料")
                
            except Exception as e:
                print(f"  [ERROR] 更新失敗: {e}")

        # 2. 計算交叉匯率 NTD vs VND
        print(f"\n[NTDVND] 正在計算交叉匯率 NTD vs VND...")
        try:
            df_twd = self.storage.load_data('USDTWD')
            df_vnd = self.storage.load_data('USDVND')
            
            if df_twd.empty or df_vnd.empty:
                print("  [ERROR] 缺少 USDTWD 或 USDVND 資料，無法計算")
            else:
                # 合併資料 (Inner Join by Date)
                # load_data 回傳包含 Date 欄位的 DataFrame
                merged = pd.merge(df_twd[['Date', 'Close']], df_vnd[['Date', 'Close']], 
                                 on='Date', how='inner', suffixes=('_TWD', '_VND'))
                
                # 計算 1 TWD = ? VND
                # USD/VND = V
                # USD/TWD = T
                # 1 USD = V VND, 1 USD = T TWD
                # T TWD = V VND => 1 TWD = V/T VND
                merged['Close'] = merged['Close_VND'] / merged['Close_TWD']
                
                # 儲存
                result = merged[['Date', 'Close']]
                self.storage.save_data('NTDVND', result)
                print(f"  [OK] 計算完成，共 {len(result)} 筆資料")
                
        except Exception as e:
            print(f"  [ERROR] 計算失敗: {e}")

    def list_pairs(self):
        """列出所有幣別與最新價格"""
        print(f"\n{'代碼':<10} {'名稱':<25} {'最新價格':<15} {'日期':<12}")
        print("-" * 65)
        
        for code, info in CURRENCY_PAIRS.items():
            latest = self.storage.get_latest_price(code)
            if latest is not None:
                price = latest['Close']
                date = latest['Date'].strftime('%Y-%m-%d')
                print(f"{code:<10} {info['name']:<25} {price:,.4f}        {date:<12}")
            else:
                print(f"{code:<10} {info['name']:<25} {'(無資料)':<15} {'-':<12}")
        print("-" * 65)

    def show(self, pair: str, range_arg: str = '1M', save: bool = False):
        """顯示趨勢圖"""
        if pair not in CURRENCY_PAIRS:
            print(f"錯誤: 不支援的幣別代碼 '{pair}'")
            print("可用代碼: " + ", ".join(CURRENCY_PAIRS.keys()))
            return

        info = CURRENCY_PAIRS[pair]
        save_path = f"data/currency_{pair}_{range_arg}.png" if save else None
        
        print(f"正在顯示 {info['name']} ({range_arg}) 趨勢圖...")
        self.visualizer.plot_trend(pair, info['name'], range_arg, save_path=save_path)


def main():
    parser = argparse.ArgumentParser(description='Currency & Crypto Tracker')
    subparsers = parser.add_subparsers(dest='command', help='指令')

    # Update command
    subparsers.add_parser('update', help='更新匯率資料')

    # List command
    subparsers.add_parser('list', help='列出目前匯率')

    # Show command
    show_parser = subparsers.add_parser('show', help='顯示趨勢圖')
    show_parser.add_argument('pair', help='幣別代碼 (例如 BTC, USDTWD)')
    show_parser.add_argument('--range', default='1M', help='時間範圍 (1W, 1M, 3M, 6M, 1Y, ALL)')
    show_parser.add_argument('--save', action='store_true', help='儲存圖表圖片')

    args = parser.parse_args()
    tracker = CurrencyTracker()

    if args.command == 'update':
        tracker.update()
    elif args.command == 'list':
        tracker.list_pairs()
    elif args.command == 'show':
        tracker.show(args.pair, args.range, args.save)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()

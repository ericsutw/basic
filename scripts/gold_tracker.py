#!/usr/bin/env python3
"""
Gold Price Tracker - Main CLI
黃金價格追蹤系統主程式
"""

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path

# 加入 scripts 目錄到路徑
sys.path.insert(0, str(Path(__file__).parent))

from gold_price_scraper import GoldPriceScraper, RateLimitError
from gold_price_storage import GoldPriceStorage
from gold_price_visualizer import GoldPriceVisualizer


class GoldTracker:
    def __init__(self, data_dir: str = "data"):
        """
        初始化黃金追蹤器
        
        Args:
            data_dir: 資料目錄
        """
        self.data_dir = data_dir
        self.scraper = GoldPriceScraper(data_dir)
        self.storage = GoldPriceStorage(data_dir)
        self.visualizer = GoldPriceVisualizer(data_dir)
    
    def fetch(self, start_date: datetime = None, end_date: datetime = None, 
             force: bool = False):
        """
        抓取黃金價格資料
        
        Args:
            start_date: 開始日期（預設：一年前）
            end_date: 結束日期（預設：今天）
            force: 是否強制重新抓取（忽略本地資料）
        """
        # 設定預設日期範圍
        if end_date is None:
            end_date = datetime.now()
        if start_date is None:
            start_date = end_date - timedelta(days=365)
        
        print(f"\n{'='*60}")
        print(f"抓取黃金價格資料")
        print(f"{'='*60}")
        print(f"日期範圍: {start_date.date()} 到 {end_date.date()}")
        
        try:
            if force:
                # 強制重新抓取
                print("\n強制模式：重新抓取所有資料...")
                data = self.scraper.fetch_data(start_date, end_date, wait_if_needed=True)
                if not data.empty:
                    self.storage.merge_and_save(data)
                    print(f"\n✓ 成功抓取並儲存 {len(data)} 筆資料")
                else:
                    print("\n✗ 未抓取到資料")
            else:
                # 智能模式：只抓取缺失的資料
                print("\n智能模式：檢查本地資料...")
                missing_ranges = self.storage.find_missing_dates(start_date, end_date)
                
                if not missing_ranges:
                    print("\n✓ 本地已有完整資料，無需查詢")
                    print(f"資料範圍: {start_date.date()} 到 {end_date.date()}")
                else:
                    print(f"\n發現 {len(missing_ranges)} 個缺失的日期範圍:")
                    for i, (start, end) in enumerate(missing_ranges, 1):
                        print(f"  {i}. {start.date()} 到 {end.date()}")
                    
                    print("\n開始抓取缺失的資料...")
                    data = self.scraper.fetch_missing_ranges(missing_ranges, wait_if_needed=True)
                    
                    if not data.empty:
                        self.storage.merge_and_save(data)
                        print(f"\n✓ 成功抓取並儲存 {len(data)} 筆新資料")
                    else:
                        print("\n✗ 未抓取到新資料")
        
        except RateLimitError as e:
            print(f"\n✗ 錯誤: {e}")
            return False
        except Exception as e:
            print(f"\n✗ 發生錯誤: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        # 顯示統計資訊
        print("\n" + "="*60)
        stats = self.storage.get_stats()
        print(f"本地資料統計:")
        print(f"  總筆數: {stats['total_records']}")
        if stats['date_range']:
            print(f"  日期範圍: {stats['date_range'][0].date()} 到 {stats['date_range'][1].date()}")
        print("="*60 + "\n")
        
        return True
    
    def show(self, time_range: str = '1M', save: bool = False):
        """
        顯示價格趨勢圖
        
        Args:
            time_range: 時間範圍 (1W, 1M, 3M, 6M, 1Y, ALL)
            save: 是否儲存圖片
        """
        print(f"\n顯示 {time_range} 價格趨勢圖...")
        
        save_path = None
        if save:
            save_path = f"{self.data_dir}/gold_price_{time_range.lower()}.png"
        
        self.visualizer.plot_price_trend(
            time_range=time_range,
            save_path=save_path,
            show=True
        )
    
    def stats(self, time_range: str = 'ALL'):
        """
        顯示統計資訊
        
        Args:
            time_range: 時間範圍 (1W, 1M, 3M, 6M, 1Y, ALL)
        """
        self.visualizer.print_statistics(time_range)
    
    def update(self):
        """
        更新最新資料（抓取今天的價格）
        """
        print("\n更新最新資料...")
        try:
            latest = self.scraper.get_latest_price(wait_if_needed=True)
            if latest:
                print(f"\n最新黃金價格 ({latest['date'].date()}):")
                print(f"  買入價: {latest['buy_price']:.2f} 元/公克")
                print(f"  賣出價: {latest['sell_price']:.2f} 元/公克")
                print(f"  價差: {latest['sell_price'] - latest['buy_price']:.2f} 元/公克")
                
                # 儲存到本地
                import pandas as pd
                df = pd.DataFrame([latest])
                self.storage.merge_and_save(df)
                print("\n✓ 已更新到本地資料")
            else:
                print("\n✗ 無法取得最新價格")
        except RateLimitError as e:
            print(f"\n✗ 錯誤: {e}")
        except Exception as e:
            print(f"\n✗ 發生錯誤: {e}")


def main():
    parser = argparse.ArgumentParser(
        description='黃金價格追蹤系統 - 從台灣銀行抓取並視覺化黃金存摺牌價',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
範例:
  # 抓取最近一年的資料
  python gold_tracker.py fetch
  
  # 抓取指定日期範圍的資料
  python gold_tracker.py fetch --start 2025-01-01 --end 2026-02-15
  
  # 強制重新抓取（忽略本地資料）
  python gold_tracker.py fetch --force
  
  # 顯示一個月的價格趨勢圖
  python gold_tracker.py show --range 1M
  
  # 顯示並儲存圖表
  python gold_tracker.py show --range 3M --save
  
  # 查看統計資訊
  python gold_tracker.py stats --range 1Y
  
  # 更新今天的最新價格
  python gold_tracker.py update
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='可用指令')
    
    # fetch 指令
    fetch_parser = subparsers.add_parser('fetch', help='抓取黃金價格資料')
    fetch_parser.add_argument('--start', type=str, help='開始日期 (YYYY-MM-DD)')
    fetch_parser.add_argument('--end', type=str, help='結束日期 (YYYY-MM-DD)')
    fetch_parser.add_argument('--force', action='store_true', help='強制重新抓取')
    
    # show 指令
    show_parser = subparsers.add_parser('show', help='顯示價格趨勢圖')
    show_parser.add_argument('--range', type=str, default='1M',
                            choices=['1W', '1M', '3M', '6M', '1Y', 'ALL'],
                            help='時間範圍 (預設: 1M)')
    show_parser.add_argument('--save', action='store_true', help='儲存圖片')
    
    # stats 指令
    stats_parser = subparsers.add_parser('stats', help='顯示統計資訊')
    stats_parser.add_argument('--range', type=str, default='ALL',
                             choices=['1W', '1M', '3M', '6M', '1Y', 'ALL'],
                             help='時間範圍 (預設: ALL)')
    
    # update 指令
    update_parser = subparsers.add_parser('update', help='更新最新價格')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # 建立追蹤器
    tracker = GoldTracker()
    
    # 執行指令
    if args.command == 'fetch':
        start_date = None
        end_date = None
        
        if args.start:
            start_date = datetime.strptime(args.start, '%Y-%m-%d')
        if args.end:
            end_date = datetime.strptime(args.end, '%Y-%m-%d')
        
        tracker.fetch(start_date, end_date, force=args.force)
    
    elif args.command == 'show':
        tracker.show(time_range=args.range, save=args.save)
    
    elif args.command == 'stats':
        tracker.stats(time_range=args.range)
    
    elif args.command == 'update':
        tracker.update()


if __name__ == '__main__':
    main()

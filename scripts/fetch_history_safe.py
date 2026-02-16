#!/usr/bin/env python3
"""
Safe History Fetcher
安全地分批抓取歷史資料，每抓取一年休息一段時間，避免被封鎖。
"""

import time
import argparse
import subprocess
import sys
from datetime import datetime

def run_fetch(year):
    """執行 gold_tracker.py fetch 抓取指定年份"""
    start_date = f"{year}-01-01"
    end_date = f"{year}-12-31"
    
    print(f"\n{'='*50}")
    print(f"開始抓取 {year} 年資料...")
    print(f"範圍: {start_date} 到 {end_date}")
    print(f"{'='*50}\n")
    
    cmd = [
        sys.executable, 
        "scripts/gold_tracker.py", 
        "fetch", 
        "--start", start_date, 
        "--end", end_date
    ]
    
    try:
        # 使用 subprocess.run 執行並等待完成
        # check=True 會在回傳非 0 代碼時拋出錯誤
        subprocess.run(cmd, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"錯誤: 抓取 {year} 年資料失敗 (Exit code: {e.returncode})")
        return False
    except KeyboardInterrupt:
        print("\n使用者中斷執行")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description='安全地分批抓取歷史資料')
    parser.add_argument('--start-year', type=int, required=True, help='開始年份 (例如 2020)')
    parser.add_argument('--end-year', type=int, required=True, help='結束年份 (例如 2024)')
    parser.add_argument('--delay', type=int, default=300, help='年份之間的休息秒數 (預設 300 秒/5分鐘)')
    
    args = parser.parse_args()
    
    current_year = datetime.now().year
    
    if args.start_year > args.end_year:
        print("錯誤: 開始年份不能大於結束年份")
        return
        
    years = range(args.end_year, args.start_year - 1, -1) # 倒序抓取
    total_years = len(years)
    
    print(f"預計抓取 {total_years} 個年份的資料:")
    print(f"年份清單: {list(years)}")
    print(f"年份間隔: {args.delay} 秒")
    print("-" * 50)
    
    for i, year in enumerate(years):
        if year > current_year:
            print(f"跳過未來年份 {year}")
            continue
            
        success = run_fetch(year)
        
        if not success:
            print(f"抓取 {year} 失敗，停止後續任務")
            break
            
        # 如果不是最後一年，則休息
        if i < total_years - 1:
            print(f"\n年份 {year} 完成。")
            print(f"休息 {args.delay} 秒後繼續...\n")
            try:
                for remaining in range(args.delay, 0, -1):
                    sys.stdout.write(f"\r倒數: {remaining} 秒")
                    sys.stdout.flush()
                    time.sleep(1)
                sys.stdout.write("\r" + " " * 20 + "\r") # 清除倒數文字
            except KeyboardInterrupt:
                print("\n\n使用者中斷休息，程式結束")
                sys.exit(0)
    
    print("\n所有任務已完成！")

if __name__ == "__main__":
    main()

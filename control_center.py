#!/usr/bin/env python3
"""
Python Control Center
整合控制中心介面
"""

import sys
import subprocess
import questionary
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich import print as rprint
import os

console = Console()

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def show_header():
    clear_screen()
    title = Text("Python Control Center", style="bold cyan")
    subtitle = Text("您的個人自動化工作站", style="yellow")
    
    panel = Panel(
        Text.assemble(title, "\n", subtitle),
        border_style="blue",
        padding=(1, 2)
    )
    rprint(panel)

def run_system_monitor():
    """執行系統監控"""
    try:
        subprocess.run([sys.executable, "scripts/system_monitor.py"])
    except KeyboardInterrupt:
        pass

def gold_tracker_menu():
    """黃金價格追蹤子選單"""
    while True:
        action = questionary.select(
            "請選擇黃金追蹤功能:",
            choices=[
                "📈 查看趨勢圖 (Show Trend)",
                "🔄 更新今日價格 (Update Today)",
                "📊 查看統計資訊 (View Stats)",
                "📥 抓取歷史資料 (Fetch History - Safe)",
                "🔙 返回主選單"
            ]
        ).ask()
        
        if action == "🔙 返回主選單":
            break
            
        elif action.startswith("📈"):
            # 詢問時間範圍
            range_choice = questionary.select(
                "選擇時間範圍:",
                choices=["1W", "1M", "3M", "6M", "1Y", "ALL"]
            ).ask()
            
            if range_choice:
                print(f"\n啟動圖表視窗 ({range_choice})...")
                subprocess.run([sys.executable, "scripts/gold_tracker.py", "show", "--range", range_choice])
                
        elif action.startswith("🔄"):
            print("\n更新今日價格...")
            subprocess.run([sys.executable, "scripts/gold_tracker.py", "update"])
            input("\n按 Enter 繼續...")
            
        elif action.startswith("📊"):
            print("\n查看統計資訊...")
            # 也可以問範圍，這裡預設 ALL
            subprocess.run([sys.executable, "scripts/gold_tracker.py", "stats"])
            input("\n按 Enter 繼續...")
            
        elif action.startswith("📥"):
            print("\n啟動安全抓取歷史記錄...")
            # 詢問年份
            import datetime
            current_year = datetime.datetime.now().year
            
            start_year = questionary.text("開始年份 (例如 2020):", default=str(current_year-1)).ask()
            end_year = questionary.text("結束年份 (例如 2024):", default=str(current_year-1)).ask()
            
            if start_year and end_year:
                subprocess.run([
                    sys.executable, "scripts/fetch_history_safe.py",
                    "--start-year", start_year,
                    "--end-year", end_year
                ])
                input("\n按 Enter 繼續...")

def currency_tracker_menu():
    """匯率追蹤子選單"""
    while True:
        action = questionary.select(
            "請選擇匯率功能:",
            choices=[
                "📈 查看趨勢圖 (Show Trend)",
                "🔄 更新匯率資料 (Update Rates)",
                "📋 列出目前匯率 (List Rates)",
                "🔙 返回主選單"
            ]
        ).ask()
        
        if action == "🔙 返回主選單":
            break
            
        elif action.startswith("📈"):
            # 選擇幣別
            pair = questionary.select(
                "選擇幣別:",
                choices=[
                    "BTC (Bitcoin)", 
                    "USDTWD (USD vs NTD)", 
                    "USDVND (USD vs VND)", 
                    "NTDVND (NTD vs VND)"
                ]
            ).ask()
            
            if pair:
                code = pair.split(" ")[0]
                range_choice = questionary.select(
                    "選擇時間範圍:",
                    choices=["1W", "1M", "3M", "6M", "1Y", "ALL"]
                ).ask()
                
                if range_choice:
                    print(f"\n啟動圖表視窗 ({code}, {range_choice})...")
                    subprocess.run([sys.executable, "scripts/currency_tracker.py", "show", code, "--range", range_choice])

        elif action.startswith("🔄"):
            print("\n更新匯率資料...")
            subprocess.run([sys.executable, "scripts/currency_tracker.py", "update"])
            input("\n按 Enter 繼續...")
            
        elif action.startswith("📋"):
            print("\n目前匯率列表:")
            subprocess.run([sys.executable, "scripts/currency_tracker.py", "list"])
            input("\n按 Enter 繼續...")

def check_and_run_daily_update():
    """檢查並執行每日自動更新"""
    from datetime import date
    from pathlib import Path
    
    state_file = Path("data/last_daily_update.txt")
    today = date.today().isoformat()
    
    should_update = False
    if not state_file.exists():
        should_update = True
    else:
        try:
            last_date = state_file.read_text().strip()
            if last_date != today:
                should_update = True
        except:
            should_update = True
            
    if should_update:
        msg = Panel(Text("📅 每日首次開啟，正在背景更新最新數據...", style="green"), border_style="green")
        
        # 背景執行黃金價格更新
        subprocess.Popen(
            [sys.executable, "scripts/gold_tracker.py", "update"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        
        # 背景執行匯率更新
        subprocess.Popen(
            [sys.executable, "scripts/currency_tracker.py", "update"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        
        # 更新狀態檔
        state_file.write_text(today)
        return msg
    return None

def main():
    update_msg = check_and_run_daily_update()
    while True:
        show_header()
        
        if update_msg:
            rprint(update_msg)
            update_msg = None
        
        choice = questionary.select(
            "請選擇工具:",
            choices=[
                "📊 系統監控 (System Monitor)",
                "💰 黃金價格追蹤 (Gold Tracker)",
                "💱 匯率追蹤 (Currency Tracker)",
                "❌ 離開 (Exit)"
            ]
        ).ask()
        
        if choice == "❌ 離開 (Exit)":
            rprint("[bold yellow]再見！[/bold yellow]")
            break
            
        elif choice.startswith("📊"):
            run_system_monitor()
            
        elif choice.startswith("💰"):
            gold_tracker_menu()
            
        elif choice.startswith("💱"):
            currency_tracker_menu()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        rprint("\n[bold yellow]程式中斷[/bold yellow]")
        sys.exit(0)

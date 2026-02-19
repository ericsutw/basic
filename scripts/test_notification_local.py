#!/usr/bin/env python3
"""
Local Notification Tester
此腳本用於在本地模擬 GitHub Actions 的執行環境，
協助快速驗證資料讀取與訊息格式，無須等待 CI/CD。
"""

import sys
import os
from pathlib import Path
import logging

# Add script directory to path
sys.path.append(str(Path(__file__).parent))

from line_messaging import LineNotifier
from currency_storage import CurrencyStorage
from gold_price_storage import GoldPriceStorage

# Setup logging
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

def test_data_integrity():
    """檢查所有資料來源的完整性"""
    logger.info("1. 檢查資料完整性 (Data Integrity Check)...")
    
    # 1. Gold
    gold_storage = GoldPriceStorage()
    gold_latest = gold_storage.get_latest_price()
    if gold_latest:
        logger.info(f"   [PASS] Gold Data: Price={gold_latest.get('sell_price')} Date={gold_latest.get('date')}")
    else:
        logger.warning("   [FAIL] Gold Data: No data found (Check scripts/gold_tracker.py)")

    # 2. Currencies
    currency_storage = CurrencyStorage()
    for symbol in ['USDTWD', 'USDVND', 'BTC', 'TSMC', 'UMC', 'Creative', 'IntlGold']:
        latest = currency_storage.get_latest_price(symbol)
        if latest is not None:
            price = latest.get('Close')
            date = latest.get('Date')
            # Check for NaN
            import pandas as pd
            if pd.isna(price):
                 logger.error(f"   [FAIL] {symbol}: Value is NaN! (Fix needed)")
            else:
                 logger.info(f"   [PASS] {symbol}: Price={price} Date={date}")
        else:
            logger.warning(f"   [WARN] {symbol}: No data found")

def test_notification_logic():
    """模擬通知邏輯"""
    logger.info("\n2. 模擬通知訊息 (Simulation)...")
    
    # Mock environment variables if not present (Test run only)
    if 'LINE_CHANNEL_ACCESS_TOKEN' not in os.environ:
        os.environ['LINE_CHANNEL_ACCESS_TOKEN'] = 'mock_token'
    if 'LINE_USER_ID' not in os.environ:
        os.environ['LINE_USER_ID'] = 'mock_user'

    notifier = LineNotifier()
    
    # 1. Check Alerts
    logger.info("   Checking Alerts Logic...")
    alerts = notifier.check_alerts()
    if alerts:
        for msg in alerts:
            logger.info(f"   [ALERT] {msg}")
    else:
        logger.info("   [INFO] No alerts triggered based on current data.")
        
    # 2. Daily Summary
    logger.info("   Generating Daily Summary...")
    summary = notifier.send_daily_summary()
    print("-" * 40)
    print(summary)
    print("-" * 40)
    
    # 3. Check for Nan in output
    if "nan" in summary.lower():
        logger.error("❌ CI CHECK FAILED: Output contains 'nan'")
        sys.exit(1)
    else:
        logger.info("✅ CI CHECK PASSED: Output looks valid")

if __name__ == "__main__":
    print("=== Local Notification Test Suite ===\n")
    test_data_integrity()
    test_notification_logic()

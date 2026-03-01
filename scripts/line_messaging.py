#!/usr/bin/env python3
"""
Line Messaging API Notification Script
負責檢查價格並發送 Line 通知
"""

import os
import json
import sys
import argparse
from pathlib import Path

from linebot.v3 import (
    WebhookHandler
)
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    PushMessageRequest,
    TextMessage
)

# Add script directory to path
sys.path.append(str(Path(__file__).parent))

from currency_storage import CurrencyStorage
from gold_price_storage import GoldPriceStorage

class LineNotifier:
    def __init__(self):
        self.channel_access_token = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
        self.user_id = os.environ.get('LINE_USER_ID')
        
        if not self.channel_access_token or not self.user_id:
            print("Warning: LINE_CHANNEL_ACCESS_TOKEN or LINE_USER_ID not set.")
            self.messaging_api = None
        else:
            configuration = Configuration(access_token=self.channel_access_token)
            self.api_client = ApiClient(configuration)
            self.messaging_api = MessagingApi(self.api_client)
            
        self.currency_storage = CurrencyStorage()
        self.gold_storage = GoldPriceStorage()
        
        base_dir = Path(__file__).parent.parent
        self.alerts_file = base_dir / 'data' / 'alerts.json'
        self.state_file = base_dir / 'data' / 'alert_state.json'
        self.alert_state = self.load_state()
        
    def load_state(self):
        if not self.state_file.exists():
            return {}
        try:
            with open(self.state_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}

    def save_state(self):
        try:
            # Create data dir if not exists
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(self.alert_state, f, indent=4)
        except Exception as e:
            print(f"Error saving alert state: {e}")

    def load_alerts(self):
        if not self.alerts_file.exists():
            return []
        with open(self.alerts_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('alerts', [])

    def check_alerts(self):
        alerts = self.load_alerts()
        messages = []
        
        print("Checking alerts...")
        
        for alert in alerts:
            symbol = alert['symbol']
            alert_type = alert.get('type', 'fluctuation')
            threshold = alert.get('threshold_percent', 5.0)
            target_price = alert.get('target_price', None)
            direction = alert.get('direction', 'below') # below or above
            
            current_price = 0
            prev_price = 0
            name = symbol
            last_timestamp = ""
            
            # Fetch data based on symbol
            if symbol == 'Gold':
                stats = self.gold_storage.get_latest_price()
                if stats:
                    current_price = stats['sell_price']
                    last_timestamp = str(stats.get('date', ''))
                    # Get previous price
                    df = self.gold_storage.load_data()
                    if len(df) > 1:
                        prev_price = df.iloc[-2]['sell_price']
                    name = "黃金 (Gold)"
            else:
                latest = self.currency_storage.get_latest_price(symbol)
                if latest is not None:
                    current_price = latest['Close']
                    last_timestamp = str(latest.get('Date', ''))
                    df = self.currency_storage.load_data(symbol)
                    
                    if len(df) > 1:
                        # 取得前一筆資料進行異常偵測 (15分鐘前)
                        prev_price = df.iloc[-2]['Close']
            
            if current_price == 0 or prev_price == 0 or not last_timestamp:
                continue

            # --- 重複警報抑制 (Alert Suppression) ---
            state_key = f"{symbol}_{alert_type}"
            if self.alert_state.get(state_key) == last_timestamp:
                # 已經通知過了，跳過
                continue
                
            # Check abnormality flag (User request: >2% change between sequences)
            # Fetch individual threshold from alert config or default to 2.0
            alert_threshold = alert.get('abnormality_threshold', 2.0)
            
            triggered = False
            change_pct = ((current_price - prev_price) / prev_price) * 100
            if abs(change_pct) >= alert_threshold:
                trend = "🚨 異常變動"
                indicator = "📈" if change_pct > 0 else "📉"
                msg = f"{trend} {name}: {current_price:,.2f} {indicator} {abs(change_pct):.2f}% (相較於前次報價)"
                messages.append(msg)
                triggered = True
                
            # Check price target alert (Existing logic)
            if alert_type == 'price_target' and target_price:
                hit = False
                if direction == 'above' and current_price >= target_price:
                    hit = True
                    msg = f"🎯 {name} 到價通知: {current_price:,.2f} (高於 {target_price})"
                elif direction == 'below' and current_price <= target_price:
                    hit = True
                    msg = f"🎯 {name} 到價通知: {current_price:,.2f} (低於 {target_price})"
                
                if hit:
                    messages.append(msg)
                    triggered = True

            # 如果這次有觸發任何警報，更新狀態
            if triggered:
                self.alert_state[state_key] = last_timestamp
                self.save_state()

        return messages

    def format_change(self, price, prev_price):
        if prev_price == 0:
            return ""
        
        pct = ((price - prev_price) / prev_price) * 100
        abs_pct = abs(pct)
        
        # Red Triangle for Up (Asian market convention users often prefer this)
        # But user asked for Green Up / Red Down?
        # Standard Emoji: 🔺 (Red Up), 🔻 (Red Down).
        # We will use 🔺/🔻 and let the symbol indicate direction.
        
        if pct > 0:
            return f"🔺 {abs_pct:.2f}%"
        elif pct < 0:
            return f"🔻 {abs_pct:.2f}%"
        else:
            return f"➖ {abs_pct:.2f}%"

    def send_daily_summary(self):
        """傳送每日行情摘要"""
        summary_lines = ["📊 每日行情摘要"]
        
        # 1. Gold
        gold_stats = self.gold_storage.get_latest_price()
        if gold_stats:
            price = gold_stats['sell_price']
            date_str = str(gold_stats['date'])[:10][-5:].replace('-', '/')
            df = self.gold_storage.load_data()
            change_str = ""
            if len(df) > 1:
                prev = df.iloc[-2]['sell_price']
                change_str = self.format_change(price, prev)
            summary_lines.append(f"Gold ({date_str}): {price:,.0f} {change_str}")
            
        # 2. Currencies & Stocks
        symbols = ['USDTWD', 'USDVND', 'BTC', 'TSMC', 'UMC', 'Creative', 'IntlGold']
        for code in symbols:
            latest = self.currency_storage.get_latest_price(code)
            if latest is not None:
                price = latest['Close']
                date_str = str(latest.get('Date', ''))[:10][-5:].replace('-', '/')
                df = self.currency_storage.load_data(code)
                change_str = ""
                if len(df) > 1:
                    prev = df.iloc[-2]['Close']
                    change_str = self.format_change(price, prev)
                summary_lines.append(f"{code} ({date_str}): {price:,.2f} {change_str}")

        return "\n".join(summary_lines)

    def should_send_summary(self):
        """判斷是否該發送每日總表 (1天3次: 09:00, 11:50, 16:00 ICT)"""
        # 目標時間 (UTC): 02:00, 04:50, 09:00
        from datetime import datetime
        now = datetime.utcnow()
        today_str = now.strftime('%Y-%m-%d')
        
        # 轉換成當天的目標時間
        target_times = {
            'morning': now.replace(hour=2, minute=0, second=0, microsecond=0),
            'noon': now.replace(hour=4, minute=50, second=0, microsecond=0),
            'afternoon': now.replace(hour=9, minute=0, second=0, microsecond=0)
        }
        
        # 依照時間先後順序檢查，確保我們檢查到最近的一個時間點
        for slot, target_time in target_times.items():
            state_key = f"summary_sent_{slot}"
            # 如果現在超過「目標時間」，且今天還沒發過
            if now >= target_time:
                if self.alert_state.get(state_key) != today_str:
                    # 更新狀態並同意發送
                    self.alert_state[state_key] = today_str
                    self.save_state()
                    return True
        return False

    def run(self, test_mode=False):
        if not self.messaging_api:
            print("Skipping Line notification (No token)")
            return

        # 1. Check Alerts (靜默巡邏)
        alert_msgs = self.check_alerts()
        
        # 2. Daily Summary (定時發送)
        summary_msg = ""
        # 測試模式下強迫發送總表以供驗證，或是達到指定時間才發送
        if test_mode or self.should_send_summary():
            summary_msg = self.send_daily_summary()
            
        # 決定是否發出 Line 通知
        if not alert_msgs and not summary_msg:
            print("🔕 靜默巡邏模式：沒有異常變動，也尚未到達總表發布時間。")
            return
        
        final_msg = ""
        if summary_msg:
            final_msg = summary_msg
            
        if alert_msgs:
            if final_msg:
                final_msg += "\n\n"
            final_msg += "⚠️ 觸發警報:\n" + "\n".join(alert_msgs)
            
        print("Prepare to send message:")
        print(final_msg)
        
        if test_mode:
            print("Test mode: Message not sent.")
            return

        try:
            push_message_request = PushMessageRequest(
                to=self.user_id,
                messages=[TextMessage(text=final_msg)]
            )
            self.messaging_api.push_message(push_message_request)
            print("Successfully sent Line message.")
        except Exception as e:
            print(f"Error sending Line message: {e}")

def main():
    parser = argparse.ArgumentParser(description='Line Notify Script')
    parser.add_argument('--test', action='store_true', help='Test mode (do not send)')
    args = parser.parse_args()
    
    notifier = LineNotifier()
    notifier.run(test_mode=args.test)

if __name__ == "__main__":
    main()

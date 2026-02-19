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
        self.alerts_file = Path('data/alerts.json')
        
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
            
            # Fetch data based on symbol
            if symbol == 'Gold':
                stats = self.gold_storage.get_latest_price()
                if stats:
                    current_price = stats['sell_price']
                    # Get previous price
                    df = self.gold_storage.load_data()
                    if len(df) > 1:
                        prev_price = df.iloc[-2]['sell_price']
                    name = "黃金 (Gold)"
            else:
                latest = self.currency_storage.get_latest_price(symbol)
                if latest is not None:
                    current_price = latest['Close']
                    df = self.currency_storage.load_data(symbol)
                    
                    # Debug log
                    if symbol == 'USDTWD':
                        print(f"[DEBUG] USDTWD Data Tail:\n{df.tail()}")
                        print(f"[DEBUG] Latest Close Type: {type(current_price)}")
                        print(f"[DEBUG] Latest Close Value: {current_price}")
                        
                    if len(df) > 1:
                        prev_price = df.iloc[-2]['Close']
            
            if current_price == 0:
                continue
                
            # Check fluctuation
            if alert_type == 'fluctuation' and prev_price > 0:
                change_pct = ((current_price - prev_price) / prev_price) * 100
                if abs(change_pct) >= threshold:
                    trend = "📈 大漲" if change_pct > 0 else "📉 大跌"
                    msg = f"{trend} {name}: {current_price:,.2f} ({change_pct:+.2f}%)"
                    messages.append(msg)
                    
            # Check price target
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

        return messages

    def send_daily_summary(self):
        """傳送每日行情摘要"""
        summary_lines = ["📊 每日行情摘要"]
        
        # 1. Gold
        gold_stats = self.gold_storage.get_latest_price()
        if gold_stats:
            price = gold_stats['sell_price']
            df = self.gold_storage.load_data()
            change_str = ""
            if len(df) > 1:
                prev = df.iloc[-2]['sell_price']
                pct = ((price - prev) / prev) * 100
                change_str = f"({pct:+.2f}%)"
            summary_lines.append(f"Gold: {price:,.0f} {change_str}")
            
        # 2. Currencies & Stocks
        symbols = ['USDTWD', 'USDVND', 'BTC', 'TSMC', 'UMC', 'Creative', 'IntlGold']
        for code in symbols:
            latest = self.currency_storage.get_latest_price(code)
            if latest is not None:
                price = latest['Close']
                df = self.currency_storage.load_data(code)
                change_str = ""
                if len(df) > 1:
                    prev = df.iloc[-2]['Close']
                    pct = ((price - prev) / prev) * 100
                    change_str = f"({pct:+.2f}%)"
                summary_lines.append(f"{code}: {price:,.2f} {change_str}")

        return "\n".join(summary_lines)

    def run(self, test_mode=False):
        if not self.messaging_api:
            print("Skipping Line notification (No token)")
            return

        # 1. Check Alerts
        alert_msgs = self.check_alerts()
        
        # 2. Daily Summary
        summary_msg = self.send_daily_summary()
        
        final_msg = summary_msg
        if alert_msgs:
            final_msg += "\n\n⚠️ 觸發警報:\n" + "\n".join(alert_msgs)
            
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

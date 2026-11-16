# Python Control Center

Welcome to your personal Python automation workspace! This project is a collection of scripts and tools designed to help you control your computer and automate daily tasks.

## Market quotes

Tracked symbols: Bank of Taiwan gold (TWD 本行買入 / 本行賣出), USDTWD, USDVND, BTC, 2330.TW (`TSMC`), 2303.TW (`UMC`), 3443.TW (`Creative`), 6768.TW (`SPG`, 志強-KY), GC=F (`IntlGold`), and the NTDVND cross rate. SPG uses the same Taiwan session window as the other TW stocks (09:00–13:30 Asia/Taipei) and appears in the LINE summary after Creative.

Fetching does not need LINE secrets. From the repository root:

```bash
pip install -r requirements.txt
python scripts/fetch_quotes.py
```

That updates the CSVs under `data/` and writes `data/latest.json`. Each symbol has `price`, `previous_close`, `change_percent`, `quote_timestamp` (with a timezone offset), `timezone`, `source`, and `stale`. Gold `price` is the Bank of Taiwan 新台幣本行買入 price; `sell_price` is still stored. The file also lists abnormal-move and price-target alerts. The command exits non-zero if gold cannot be scraped or the latest passbook date is still more than 10 days old. It does not print a success line in that case, and it does not write `data/latest.json`.

If `rate.bot.com.tw` answers with a browser check instead of the price table, the scraper uses a local Chrome or Chromium. Install Google Chrome or set `CHROME_PATH` when that happens. Direct HTTP is tried first.

### Push from the assistant machine

Run the command above on a schedule. Push only when it exits 0. Push to **`main`**. Commit:

- `data/latest.json` (this push is what triggers LINE)
- `data/gold_prices.csv` and `data/gold_prices_backup.csv`
- `data/currency/*.csv`

Do not commit `data/alert_state.json`. The notify workflow owns that de-dupe file. Do not put `[skip ci]` in the commit message.

```bash
git add data/latest.json data/gold_prices.csv data/gold_prices_backup.csv data/currency
git commit -m "Update quotes"
git pull --rebase origin main
git push origin main
```

A push to `main` that changes `data/latest.json` runs `.github/workflows/notify.yml`. It sends the LINE summary at most three times per day, at or after 09:00, 11:50, and 16:00 Asia/Saigon. At other times it sends only for a 2% abnormal move or a price-target alert, using the existing de-dupe state. Schedule the machine so a push lands after each of those three times if you want all three summaries.

`.github/workflows/daily_update.yml` is only a fallback. Every 30 minutes it fetches on its own when `data/latest.json` is missing or older than 90 minutes, then pushes. It does not call LINE itself. The notify workflow sends once for that push, and the de-dupe state stops a second summary or a repeated alert.

## Structure

- `scripts/`: Contains individual automation scripts.
- `lib/`: Shared libraries and utilities.
- `requirements.txt`: Python dependencies.

## Tools

### System Monitor (`system_monitor.py`)

即時系統監控面板，支援多種視圖切換：
- **5 種視圖模式**：CPU、記憶體、磁碟 I/O、網路 I/O、程式存活時間
- **互動式切換**：使用鍵盤快捷鍵 (1-5 或 C/M/D/N/U) 即時切換視圖
- **即時更新**：自動更新系統資源使用情況
- **美觀介面**：使用 rich 庫建立彩色終端介面

```bash
# 執行系統監控
python scripts\system_monitor.py

# 自訂參數（顯示 Top 15，每 0.5 秒更新）
python scripts\system_monitor.py -n 15 -r 0.5
```

## Getting Started

1.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

2.  **Run a Script**:
    Navigate to the `scripts` directory and run the desired script:
    ```bash
    python scripts/your_script_name.py
    ```

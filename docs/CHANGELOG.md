# 專案開發紀錄 (Detailed History)

本文件詳盡紀錄了「Python Control Center」從 2026-02-15 至今的所有開發動作。

---

## 📅 2026-11-16：報價抓取與 LINE 通知拆開
*   **黃金**：改抓台灣銀行黃金存摺頁的營業時間 CSV／表格（`/gold/csv/{YYYY-MM}/TWD/0` 與 `/gold/chart/{YYYY-MM}/TWD`）。抓不到牌價或最新日期仍超過 10 天時，程式以非零狀態結束，不再印出「更新完成」。
*   **價格標準**：LINE 摘要與黃金警報改用本行買入（`buy_price`）。賣出價仍寫進 CSV。
*   **抓取**：`python scripts/fetch_quotes.py` 更新 CSV 並寫 `data/latest.json`，不需要 LINE 密鑰。
*   **通知**：`.github/workflows/notify.yml` 在 `main` 的 `data/latest.json` 變更時，用 LINE Messaging API 發送。每日摘要最多三次（09:00、11:50、16:00 Asia/Saigon）；其餘時間只發 2% 異常或到價警報。
*   **備援**：`daily_update.yml` 每 30 分鐘檢查；報價檔超過約 90 分鐘才自己抓取並推送，不直接發 LINE。

---

## 📅 2026-02-15：專案啟動與核心架構
*   **目標**：建立一個能追蹤金價與匯率的個人工具，並克服先前 Playwright 環境安裝的限制。
*   **關鍵動作**：
    *   設計並實作 `gold_price_scraper.py`：放棄瀏覽器模擬，改用 `requests` + `BeautifulSoup` 直接爬取台灣銀行外匯網頁。
    *   開發 `currency_tracker.py`：導入 `yfinance` 模組，支援多種貨幣數據抓取。
    *   建立 `CurrencyStorage` 系統：定義 CSV 儲存格式與自動補齊數據邏輯。

## 📅 2026-02-16：初版儀表板與雲端同步
*   **目標**：將數據視覺化，並實現 GitHub 自動化更新。
*   **關鍵動作**：
    *   實作 `index.html`：初版 Chart.js 儀表板完成。
    *   Git 環境部署：初始化本地 Repo，並成功 Push 到 GitHub。
    *   GitHub Actions：建立 `daily_update.yml`，設定每日自動更新任務。

## 📅 2026-02-17：功能強化、優化與文件整理
*   **目標**：提升網頁實用性，增加行情分析，並整理專案文件。
*   **關鍵動作**：
    *   解決 GitHub Pages 權限與部署問題。
    *   **漲跌分析**：新增卡片趨勢顯示（▲紅/▼綠）。
    *   **黃金整合**：將黃金數據正式納入 Web 儀表板。
    *   **區間選擇器**：支援 `1W` 到 `ALL` 的動態時間篩選與抽樣優化。
    *   **文件整理**：建立 `docs/` 資料夾，將 `DEVELOPMENT_LOG.md` (摘要版) 與 `CHANGELOG.md` (詳細版) 移入以保持根目錄整潔。

---

## 📝 待辦開發清單
- [x] LINE 通知（Messaging API，不是已經停用的 Line Notify）
- [ ] 技術指標分析 (MA/RSI)
- [ ] 介面更精緻的 UI 改版

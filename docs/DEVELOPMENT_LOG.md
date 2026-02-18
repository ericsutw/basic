# 專案開發進度與功能摘要 (v1.0)

本文件摘要了目前「Python Control Center」已完成的所有功能。

## ✅ 核心功能
- **金融數據抓取**：
    - 匯率：BTC, USDTWD, USDVND。
    - 交叉匯率：自動計算 NTDVND。
    - 黃金：自動抓取台灣銀行牌價 (buy/sell price)。
- **系統監控**：CPU、記憶體、硬碟使用率監控與告警。

## ✅ 自動化與雲端
- **GitHub Actions**：每天早上 8:00 自動執行數據更新。
- **GitHub Pages**：網頁版儀表板 [點此查看](https://ericsutw.github.io/basic/)。

## ✅ 儀表板特性
- **趨勢視覺化**：支援 Chart.js 動態曲線。
- **漲跌指示**：顯示與前一日相比的漲跌數值與百分比。
- **時間區間**：可切換 1W, 1M, 3M, 6M, 1Y, ALL 不同視角。

## 📂 檔案結構
- `scripts/`: 所有 Python 抓取與監控腳本。
- `data/`: CSV 數據儲存目錄。
- `index.html`: 網頁儀表板主頁面。
- `.github/workflows/`: 自動化排程設定。

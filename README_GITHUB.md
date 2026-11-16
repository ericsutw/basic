# GitHub Deployment Guide

本專案已準備好部署至 GitHub，並透過 GitHub Actions 實現完全自動化。

## 1. 準備工作
由於您的環境尚未安裝 Git，請先下載並安裝：
-   [Download Git for Windows](https://git-scm.com/download/win)

## 2. 初始化與上傳
安裝完成後，請在專案資料夾 (`d:\P_WorkPlace\PythonControlCenter`) 右鍵開啟 "Git Bash" 或終端機，執行以下指令：

```bash
# 初始化 Git 儲存庫
git init

# 加入所有檔案
git add .

# 提交第一次變更
git commit -m "Initial commit: Python Control Center with Auto Updates"

# 建立 GitHub Repository (請先在 GitHub 網站上建立一個新的空專案)
# 將下面的 URL 替換為您的專案網址
git remote add origin https://github.com/您的帳號/專案名稱.git

# 上傳程式碼
git branch -M main
git push -u origin main
```

## 3. 設定 GitHub Actions (自動更新)
上傳後，請至 GitHub 專案頁面：
1.  點擊 **Settings** > **Actions** > **General**。
2.  在 **Workflow permissions** 區域，勾選 **Read and write permissions**。
3.  點擊 **Save**。
    *   這很重要！Workflow 檔裡的 `permissions: contents: write` 還需要這個設定，否則 `github-actions[bot]` 推送會 403。

報價由外部機器執行 `python scripts/fetch_quotes.py` 後推上 `main`（見 README.md）。推送若改到 `data/latest.json`，`notify.yml` 才會發 LINE Messaging API。Secrets 是 `LINE_CHANNEL_ACCESS_TOKEN` 與 `LINE_USER_ID`。

`daily_update.yml` 只是每 30 分鐘的備援：`data/latest.json` 超過約 90 分鐘沒更新才自己抓資料並推送，不會自己發 LINE，避免和 notify workflow 各發一次。

## 4. 啟用 GitHub Pages (網頁儀表板)
1.  點擊 **Settings** > **Pages**。
2.  在 **Build and deployment** 下的 **Source** 選擇 **Deploy from a branch**。
3.  在 **Branch** 選擇 **main** (或 master)，資料夾選擇 **/(root)**。
4.  點擊 **Save**。
5.  稍等幾分鐘，重新整理頁面，您會看到網頁連結 (例如 `https://您的帳號.github.io/專案名稱/`)。

---

## 專案結構
-   `.github/workflows/daily_update.yml`: `data/latest.json` 超過約 90 分鐘才抓報價並推送。
-   `.github/workflows/notify.yml`: `main` 上的 `data/latest.json` 有變更時，用 LINE Messaging API 發摘要或警報。
-   `index.html`: 您的網頁版儀表板。
-   `data/`: 儲存數據的資料夾。
-   `scripts/`: Python 程式碼。

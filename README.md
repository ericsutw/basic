# Python Control Center

Welcome to your personal Python automation workspace! This project is a collection of scripts and tools designed to help you control your computer and automate daily tasks.

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

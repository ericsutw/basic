#!/usr/bin/env python3
"""
Gold Price Scraper Module
從台灣銀行網站抓取黃金存摺牌價（新台幣，營業時間）。

牌價頁目前是：
  https://rate.bot.com.tw/gold/chart/{YYYY-MM}/TWD
對應的 CSV 下載是：
  https://rate.bot.com.tw/gold/csv/{YYYY-MM}/TWD/0
最後一段 0 是營業時間牌價（1 為盤後）。欄位含本行買入、本行賣出。
"""

import io
import sys
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
from pathlib import Path
import time
import json
from typing import Optional, List, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))

from chrome_fetch import BrowserFetchError, ChromeSession, find_chrome


class RateLimitError(Exception):
    """查詢間隔限制錯誤"""
    pass


class GoldScrapeError(Exception):
    """無法取得台灣銀行黃金牌價。呼叫端必須把它當成失敗，不能當成更新完成。"""
    pass


def _is_challenge(text: str) -> bool:
    head = (text or "")[:4000].lower()
    return (
        "challenge validation" in head
        or "sec-cpt-if" in head
        or "_incapsula_" in head
        or "pardon our interruption" in head
    )


def _header_kind(name: str) -> Optional[str]:
    label = str(name).strip().lower()
    if "日期" in str(name) or label == "date":
        return "date"
    if "買入" in str(name) or "buying" in label:
        return "buy"
    if "賣出" in str(name) or "selling" in label:
        return "sell"
    return None


def _parse_dates(series: pd.Series) -> pd.Series:
    as_str = series.astype(str).str.strip().str.replace(r"\.0$", "", regex=True)
    if as_str.str.fullmatch(r"\d{8}").all():
        return pd.to_datetime(as_str, format="%Y%m%d", errors="coerce")
    return pd.to_datetime(as_str, errors="coerce")


def _prices_frame(dates, buy, sell) -> pd.DataFrame:
    frame = pd.DataFrame({
        "date": _parse_dates(pd.Series(dates)),
        "buy_price": pd.to_numeric(
            pd.Series(buy).astype(str).str.replace(",", "", regex=False),
            errors="coerce",
        ),
        "sell_price": pd.to_numeric(
            pd.Series(sell).astype(str).str.replace(",", "", regex=False),
            errors="coerce",
        ),
    })
    frame = frame.dropna(subset=["date", "buy_price", "sell_price"])
    frame["timestamp"] = datetime.now().isoformat()
    return frame


def parse_gold_csv(text: str) -> pd.DataFrame:
    """Parse a Bank of Taiwan gold passbook CSV (Chinese or English headers)."""
    if not text or not text.strip() or _is_challenge(text):
        raise GoldScrapeError("回應不是黃金牌價 CSV")
    payload = text.lstrip("\ufeff")
    first = payload.splitlines()[0]
    if "<html" in first.lower() or "<!doctype" in first.lower():
        raise GoldScrapeError("回應是網頁而不是黃金牌價 CSV")
    frame = pd.read_csv(io.StringIO(payload))
    if frame.empty and frame.shape[1] == 0:
        raise GoldScrapeError("黃金牌價 CSV 是空的")
    columns = {_header_kind(col): col for col in frame.columns}
    if not {"date", "buy", "sell"} <= set(k for k in columns if k):
        raise GoldScrapeError(f"黃金牌價 CSV 欄位無法辨識: {list(frame.columns)}")
    return _prices_frame(frame[columns["date"]], frame[columns["buy"]], frame[columns["sell"]])


def parse_gold_html(text: str) -> pd.DataFrame:
    """Parse the history table on the gold passbook chart page."""
    if not text or _is_challenge(text):
        raise GoldScrapeError("回應不是黃金牌價網頁")
    soup = BeautifulSoup(text, "html.parser")
    for table in soup.find_all("table"):
        header_cells = table.find_all("th")
        headers = [cell.get_text(strip=True) for cell in header_cells]
        kinds = [_header_kind(name) for name in headers]
        if not {"date", "buy", "sell"} <= {kind for kind in kinds if kind}:
            continue
        index = {kind: kinds.index(kind) for kind in ("date", "buy", "sell")}
        dates, buy, sell = [], [], []
        tbody = table.find("tbody") or table
        for tr in tbody.find_all("tr"):
            cols = tr.find_all("td")
            if len(cols) <= max(index.values()):
                continue
            dates.append(cols[index["date"]].get_text(strip=True))
            buy.append(cols[index["buy"]].get_text(strip=True))
            sell.append(cols[index["sell"]].get_text(strip=True))
        return _prices_frame(dates, buy, sell)
    raise GoldScrapeError("未找到黃金牌價資料表格（日期 / 本行買入 / 本行賣出）")


class GoldPriceScraper:
    def __init__(self, data_dir: str = "data"):
        """
        初始化爬蟲

        Args:
            data_dir: 資料目錄（用於儲存時間戳記錄）
        """
        self.base_url = "https://rate.bot.com.tw/gold"
        self.data_dir = Path(data_dir)
        self.timestamp_file = self.data_dir / ".last_query_time"
        self.min_interval = 2  # 月份請求之間的最短間隔（秒）

        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
            ),
            "Accept": "text/csv,text/html,application/xhtml+xml,*/*",
            "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
            "Referer": "https://rate.bot.com.tw/gold/",
        })
        self._use_browser = False
        self._chrome: Optional[ChromeSession] = None

    def _get_last_query_time(self) -> Optional[datetime]:
        """取得上次查詢時間"""
        if not self.timestamp_file.exists():
            return None

        try:
            with open(self.timestamp_file, "r") as f:
                data = json.load(f)
                return datetime.fromisoformat(data["last_query_time"])
        except Exception:
            return None

    def _update_last_query_time(self):
        """更新上次查詢時間"""
        with open(self.timestamp_file, "w") as f:
            json.dump({
                "last_query_time": datetime.now().isoformat()
            }, f)

    def _check_rate_limit(self, wait: bool = False) -> bool:
        """
        檢查查詢間隔限制

        Args:
            wait: 如果間隔不足，是否等待

        Returns:
            是否可以查詢

        Raises:
            RateLimitError: 如果間隔不足且 wait=False
        """
        last_time = self._get_last_query_time()
        if last_time is None:
            return True

        elapsed = (datetime.now() - last_time).total_seconds()
        remaining = self.min_interval - elapsed

        if remaining > 0:
            if wait:
                print(f"等待 {remaining:.0f} 秒後繼續查詢...")
                time.sleep(remaining)
                return True
            else:
                raise RateLimitError(
                    f"查詢間隔不足，請等待 {remaining:.0f} 秒後再試。"
                    f"（上次查詢時間: {last_time.strftime('%Y-%m-%d %H:%M:%S')}）"
                )

        return True

    def _close_browser(self):
        if self._chrome is not None:
            self._chrome.close()
            self._chrome = None

    def _ensure_browser(self) -> ChromeSession:
        if self._chrome is not None:
            return self._chrome
        chrome_path = find_chrome()
        if not chrome_path:
            raise GoldScrapeError(
                "台灣銀行回傳瀏覽器驗證頁，而且這台機器找不到 Chrome/Chromium。"
                "請安裝 Google Chrome，或設定 CHROME_PATH 後重試。"
            )
        print(f"使用本機瀏覽器讀取台灣銀行牌價: {chrome_path}")
        session = ChromeSession(chrome_path)
        try:
            session.start()
            session.navigate("https://rate.bot.com.tw/gold/chart/ltm/TWD?Lang=zh-TW", timeout=75)
        except Exception:
            session.close()
            raise
        self._chrome = session
        return session

    def _browser_get(self, url: str) -> str:
        try:
            session = self._ensure_browser()
            if "/gold/csv/" in url:
                return session.fetch_text(url)
            session.navigate(url, timeout=75)
            return session.page_html()
        except BrowserFetchError as exc:
            raise GoldScrapeError(str(exc)) from exc
        except GoldScrapeError:
            raise
        except Exception as exc:
            raise GoldScrapeError(f"瀏覽器讀取失敗: {exc}") from exc

    def _get(self, url: str) -> str:
        if self._use_browser:
            return self._browser_get(url)
        try:
            response = self.session.get(url, timeout=30)
        except requests.RequestException as exc:
            raise GoldScrapeError(f"網路請求錯誤: {exc}") from exc
        text = response.text or ""
        if _is_challenge(text) or response.status_code in (403, 429, 503):
            print(f"台灣銀行拒絕直接抓取（HTTP {response.status_code}），改用本機 Chrome。")
            self._use_browser = True
            return self._browser_get(url)
        if response.status_code != 200:
            raise GoldScrapeError(f"HTTP {response.status_code}：{url}")
        return text

    def _fetch_month(self, year: str, month: str) -> pd.DataFrame:
        period = f"{year}-{month}"
        csv_url = f"https://rate.bot.com.tw/gold/csv/{period}/TWD/0"
        chart_url = f"https://rate.bot.com.tw/gold/chart/{period}/TWD?Lang=zh-TW"
        errors = []

        print(f"正在查詢 {year}年{month}月 營業時間黃金存摺牌價...")
        try:
            text = self._get(csv_url)
            frame = parse_gold_csv(text)
            print(f"  CSV {csv_url}：{len(frame)} 筆")
            return frame
        except GoldScrapeError as exc:
            errors.append(f"CSV: {exc}")
            print(f"  CSV 失敗，改讀牌價網頁：{exc}")

        try:
            text = self._get(chart_url)
            frame = parse_gold_html(text)
            print(f"  網頁 {chart_url}：{len(frame)} 筆")
            return frame
        except GoldScrapeError as exc:
            errors.append(f"網頁: {exc}")

        detail = "；".join(errors) if errors else "沒有回應"
        raise GoldScrapeError(f"未找到 {year}/{month} 的黃金牌價（{detail}）")

    def fetch_data(self, start_date: datetime, end_date: datetime,
                   wait_if_needed: bool = True) -> pd.DataFrame:
        """
        抓取指定日期範圍的黃金價格資料。

        任一個月份無法取得牌價時會拋出 GoldScrapeError，而不是回傳空表。
        月份檔有抓到、但範圍內沒有列（例如只查週末）時，回傳空的 DataFrame。
        """
        all_data = []
        current = start_date.replace(day=1)
        end_month = end_date.replace(day=1)

        try:
            while current <= end_month:
                self._check_rate_limit(wait=wait_if_needed)
                year = str(current.year)
                month = f"{current.month:02d}"
                frame = self._fetch_month(year, month)
                self._update_last_query_time()
                if not frame.empty:
                    all_data.append(frame)

                if current.month == 12:
                    current = current.replace(year=current.year + 1, month=1)
                else:
                    current = current.replace(month=current.month + 1)

                if current <= end_month and wait_if_needed:
                    time.sleep(1)
        finally:
            self._close_browser()

        if not all_data:
            return pd.DataFrame(columns=["date", "buy_price", "sell_price", "timestamp"])

        result = pd.concat(all_data, ignore_index=True)
        result = result.dropna(subset=["date"])
        result["date"] = pd.to_datetime(result["date"])
        result = result[
            (result["date"].dt.date >= start_date.date())
            & (result["date"].dt.date <= end_date.date())
        ]
        result = result.sort_values("date")
        return result

    def fetch_missing_ranges(self, missing_ranges: List[Tuple[datetime, datetime]],
                           wait_if_needed: bool = True) -> pd.DataFrame:
        """
        抓取多個缺失的日期範圍

        Args:
            missing_ranges: 缺失的日期範圍列表
            wait_if_needed: 如果查詢間隔不足，是否等待

        Returns:
            合併後的資料
        """
        if not missing_ranges:
            return pd.DataFrame(columns=["date", "buy_price", "sell_price", "timestamp"])

        # One request span covers every missing day. Per-range downloads repeat the same months.
        start = min(start for start, _end in missing_ranges)
        end = max(end for _start, end in missing_ranges)
        print(f"\n查詢範圍: {start.date()} 到 {end.date()}")
        return self.fetch_data(start, end, wait_if_needed=wait_if_needed)

    def get_latest_price(self, wait_if_needed: bool = True) -> Optional[dict]:
        """
        取得最新的黃金價格（今天所在月份的最新一筆）

        Args:
            wait_if_needed: 如果查詢間隔不足，是否等待

        Returns:
            最新價格資料字典
        """
        today = datetime.now()
        month_start = today.replace(day=1)
        data = self.fetch_data(month_start, today, wait_if_needed=wait_if_needed)

        if data.empty:
            return None

        latest = data.iloc[-1]
        return {
            "date": latest["date"],
            "buy_price": latest["buy_price"],
            "sell_price": latest["sell_price"],
            "timestamp": latest["timestamp"],
        }


if __name__ == "__main__":
    scraper = GoldPriceScraper()
    end_date = datetime.now()
    start_date = end_date.replace(day=1)

    print("測試抓取資料...")
    print(f"日期範圍: {start_date.date()} 到 {end_date.date()}")

    try:
        data = scraper.fetch_data(start_date, end_date)
        if data.empty:
            print("錯誤: 這個月的牌價是空的")
            raise SystemExit(1)
        latest = data.iloc[-1]
        print(
            f"最新 {pd.Timestamp(latest['date']).date()} "
            f"本行買入 {latest['buy_price']:.0f} / 本行賣出 {latest['sell_price']:.0f}"
        )
        print(f"共 {len(data)} 筆")
    except (RateLimitError, GoldScrapeError) as exc:
        print(f"錯誤: {exc}")
        raise SystemExit(1)

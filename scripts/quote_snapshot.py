#!/usr/bin/env python3
"""Build data/latest.json from the CSVs on disk. Does not talk to LINE."""

import json
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import pytz

sys.path.insert(0, str(Path(__file__).parent))

from currency_storage import CurrencyStorage
from gold_price_storage import GoldPriceStorage

ROOT = Path(__file__).resolve().parent.parent
TAIPEI = pytz.timezone("Asia/Taipei")
UTC = pytz.UTC

# LINE 每日摘要的順序。NTDVND 有進 latest.json，但不在現有摘要裡。
SUMMARY_SYMBOLS = [
    "Gold",
    "USDTWD",
    "USDVND",
    "BTC",
    "TSMC",
    "UMC",
    "Creative",
    "IntlGold",
]
REQUIRED_SYMBOLS = SUMMARY_SYMBOLS + ["NTDVND"]

QUOTE_META = {
    "Gold": {
        "timezone": "Asia/Taipei",
        "source": "Bank of Taiwan 黃金存摺 TWD 營業時間本行買入 (rate.bot.com.tw)",
    },
    "BTC": {"timezone": "UTC", "source": "Yahoo Finance BTC-USD"},
    "USDTWD": {"timezone": "UTC", "source": "Yahoo Finance TWD=X"},
    "USDVND": {"timezone": "UTC", "source": "Yahoo Finance VND=X"},
    "TSMC": {"timezone": "UTC", "source": "Yahoo Finance 2330.TW"},
    "UMC": {"timezone": "UTC", "source": "Yahoo Finance 2303.TW"},
    "Creative": {"timezone": "UTC", "source": "Yahoo Finance 3443.TW"},
    "IntlGold": {"timezone": "UTC", "source": "Yahoo Finance GC=F"},
    "NTDVND": {"timezone": "UTC", "source": "Cross rate USDVND / USDTWD"},
}


def _number(value):
    if value is None or pd.isna(value):
        return None
    return float(value)


def _change_percent(price, previous):
    if price is None or previous in (None, 0):
        return None
    return round((price - previous) / previous * 100, 6)


def _aware(value, assume_tz):
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    stamp = pd.Timestamp(value)
    if stamp.tzinfo is None:
        stamp = stamp.tz_localize(assume_tz)
    return stamp


def is_stale(symbol, quote_ts, now=None):
    """True when the stored quote is too old to treat as a current price."""
    if quote_ts is None:
        return True
    now = now or datetime.now(UTC)
    if now.tzinfo is None:
        now = UTC.localize(now)
    age = now - quote_ts.tz_convert(UTC)
    if symbol == "Gold":
        return age > pd.Timedelta(days=10)
    if symbol in ("TSMC", "UMC", "Creative"):
        return age > pd.Timedelta(days=5)
    if symbol == "BTC":
        return age > pd.Timedelta(hours=6)
    return age > pd.Timedelta(hours=72)


def previous_day_close(df, current_date):
    """Previous Taipei calendar day's close. Same rule the LINE summary already uses."""
    if df.empty or len(df) <= 1:
        return None
    frame = df.copy()
    frame["Date"] = pd.to_datetime(frame["Date"])
    if frame["Date"].dt.tz is None:
        frame["Date"] = frame["Date"].dt.tz_localize("UTC").dt.tz_convert(TAIPEI)
    else:
        frame["Date"] = frame["Date"].dt.tz_convert(TAIPEI)

    current = pd.to_datetime(current_date)
    if current.tzinfo is None:
        current = current.tz_localize("UTC").tz_convert(TAIPEI)
    else:
        current = current.tz_convert(TAIPEI)

    earlier = frame[frame["Date"].dt.date < current.date()]
    if earlier.empty:
        return _number(frame.iloc[-2]["Close"])
    return _number(earlier.iloc[-1]["Close"])


def format_change(price, previous):
    if not previous:
        return ""
    pct = ((price - previous) / previous) * 100
    abs_pct = abs(pct)
    if pct > 0:
        return f"🔺 {abs_pct:.2f}%"
    if pct < 0:
        return f"🔻 {abs_pct:.2f}%"
    return f"➖ {abs_pct:.2f}%"


def format_summary(quotes, now=None):
    """Daily summary text. Gold uses the buy price and zero decimal places."""
    now = now or datetime.now(TAIPEI)
    today_val = now.strftime("%m/%d")
    lines = ["📊 每日行情摘要"]
    for symbol in SUMMARY_SYMBOLS:
        quote = quotes.get(symbol)
        if not quote or quote.get("price") is None:
            continue
        price = quote["price"]
        date_str = str(quote.get("quote_timestamp") or "")[:10][-5:].replace("-", "/")
        display_date = f" ({date_str})" if date_str and date_str != today_val else ""
        decimals = 0 if symbol == "Gold" else 2
        change = format_change(price, quote.get("previous_close") or 0)
        lines.append(f"{symbol}{display_date}: {price:,.{decimals}f} {change}")
    return "\n".join(lines)


def _gold_quote(storage: GoldPriceStorage, now):
    frame = storage.load_data()
    if frame.empty:
        return None
    frame = frame.sort_values("date")
    latest = frame.iloc[-1]
    previous = _number(frame.iloc[-2]["buy_price"]) if len(frame) > 1 else None
    price = _number(latest["buy_price"])
    quote_ts = _aware(latest["date"], TAIPEI)
    meta = QUOTE_META["Gold"]
    quote = {
        "price": price,
        "previous_close": previous,
        "change_percent": _change_percent(price, previous),
        "quote_timestamp": quote_ts.isoformat() if quote_ts is not None else None,
        "timezone": meta["timezone"],
        "source": meta["source"],
        "stale": is_stale("Gold", quote_ts, now),
        "buy_price": price,
        "sell_price": _number(latest.get("sell_price")),
    }
    return quote, str(latest["date"]), previous


def _currency_quote(storage: CurrencyStorage, symbol, now):
    frame = storage.load_data(symbol)
    if frame.empty:
        return None
    latest = frame.iloc[-1]
    price = _number(latest["Close"])
    previous = previous_day_close(frame, latest["Date"])
    sequence_previous = _number(frame.iloc[-2]["Close"]) if len(frame) > 1 else None
    quote_ts = _aware(latest["Date"], "UTC")
    meta = QUOTE_META[symbol]
    quote = {
        "price": price,
        "previous_close": previous,
        "change_percent": _change_percent(price, previous),
        "quote_timestamp": quote_ts.isoformat() if quote_ts is not None else None,
        "timezone": meta["timezone"],
        "source": meta["source"],
        "stale": is_stale(symbol, quote_ts, now),
    }
    return quote, str(latest["Date"]), sequence_previous


def detect_alerts(gold_storage=None, currency_storage=None, alerts_file=None):
    """Abnormal-move and price-target alerts. Not de-duplicated."""
    gold_storage = gold_storage or GoldPriceStorage()
    currency_storage = currency_storage or CurrencyStorage()
    alerts_file = Path(alerts_file) if alerts_file else ROOT / "data" / "alerts.json"
    if not alerts_file.exists():
        return []
    with open(alerts_file, "r", encoding="utf-8") as handle:
        configs = json.load(handle).get("alerts", [])

    gold_parts = _gold_quote(gold_storage, datetime.now(UTC))
    detected = []
    for alert in configs:
        symbol = alert["symbol"]
        alert_type = alert.get("type", "fluctuation")
        target_price = alert.get("target_price")
        direction = alert.get("direction", "below")
        threshold = alert.get("abnormality_threshold", 2.0)

        if symbol == "Gold":
            if gold_parts is None:
                continue
            _quote, state_value, sequence_previous = gold_parts
            price = _quote["price"]
            name = "黃金 (Gold)"
        else:
            parts = _currency_quote(currency_storage, symbol, datetime.now(UTC))
            if parts is None:
                continue
            _quote, state_value, sequence_previous = parts
            price = _quote["price"]
            name = symbol

        if not price or not sequence_previous or not state_value:
            continue

        messages = []
        change_pct = ((price - sequence_previous) / sequence_previous) * 100
        if abs(change_pct) >= threshold:
            trend = "🚨 異常變動"
            indicator = "📈" if change_pct > 0 else "📉"
            messages.append(
                f"{trend} {name}: {price:,.2f} {indicator} {abs(change_pct):.2f}% (相較於前次報價)"
            )
            detected.append({
                "symbol": symbol,
                "type": "abnormal_move",
                "state_key": f"{symbol}_{alert_type}",
                "state_value": state_value,
                "message": messages[-1],
            })

        if alert_type == "price_target" and target_price is not None:
            hit = None
            if direction == "above" and price >= target_price:
                hit = f"🎯 {name} 到價通知: {price:,.2f} (高於 {target_price})"
            elif direction == "below" and price <= target_price:
                hit = f"🎯 {name} 到價通知: {price:,.2f} (低於 {target_price})"
            if hit:
                detected.append({
                    "symbol": symbol,
                    "type": "price_target",
                    "state_key": f"{symbol}_{alert_type}",
                    "state_value": state_value,
                    "message": hit,
                })
    return detected


def build_payload(gold_storage=None, currency_storage=None):
    gold_storage = gold_storage or GoldPriceStorage()
    currency_storage = currency_storage or CurrencyStorage()
    now = datetime.now(UTC)
    quotes = {}

    gold_parts = _gold_quote(gold_storage, now)
    if gold_parts is not None:
        quotes["Gold"] = gold_parts[0]

    for symbol in REQUIRED_SYMBOLS:
        if symbol == "Gold":
            continue
        parts = _currency_quote(currency_storage, symbol, now)
        if parts is not None:
            quotes[symbol] = parts[0]

    generated = datetime.now(TAIPEI)
    return {
        "generated_at": generated.isoformat(),
        "quotes": quotes,
        "alerts": detect_alerts(gold_storage, currency_storage),
    }


def write_payload(payload, path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)
    return path

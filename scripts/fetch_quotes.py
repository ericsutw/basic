#!/usr/bin/env python3
"""Fetch every tracked quote, update the CSVs, and write data/latest.json.

No LINE credentials are read. From the repository root:

    pip install -r requirements.txt
    python scripts/fetch_quotes.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from currency_tracker import CurrencyTracker
from gold_tracker import GoldTracker
from quote_snapshot import REQUIRED_SYMBOLS, build_payload, format_summary, write_payload


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    print("Fetching currency, stocks, and cross rates...")
    CurrencyTracker().update()

    print("Fetching Bank of Taiwan gold (TWD buy/sell)...")
    if not GoldTracker(str(root / "data")).update():
        print("ERROR: 黃金價格更新失敗，不寫入 data/latest.json。")
        return 1

    payload = build_payload()
    missing = [
        symbol
        for symbol in REQUIRED_SYMBOLS
        if payload["quotes"].get(symbol, {}).get("price") is None
    ]
    if missing:
        print("ERROR: 缺少報價，不寫入 data/latest.json：" + ", ".join(missing))
        return 1

    path = write_payload(payload, root / "data" / "latest.json")
    gold = payload["quotes"]["Gold"]
    print(f"Wrote {path}")
    print(
        f"Gold {str(gold['quote_timestamp'])[:10]} "
        f"本行買入 {gold['price']:,.0f} "
        f"change {gold['change_percent']}% stale={str(gold['stale']).lower()}"
    )
    print(f"Alerts detected: {len(payload['alerts'])}")
    print(format_summary(payload["quotes"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())

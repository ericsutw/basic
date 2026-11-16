#!/usr/bin/env python3
"""Report whether data/latest.json is older than a threshold.

Exit code is always 0. Prints stale=true or stale=false, and appends
stale=<true|false> to $GITHUB_OUTPUT when that variable is set.
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", default="data/latest.json")
    parser.add_argument("--max-age-minutes", type=float, default=90)
    args = parser.parse_args()

    path = Path(args.file)
    stale = True
    reason = "missing"
    if path.exists():
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            generated = datetime.fromisoformat(payload["generated_at"])
        except (OSError, ValueError, KeyError, TypeError) as exc:
            reason = f"unreadable ({exc})"
        else:
            if generated.tzinfo is None:
                generated = generated.replace(tzinfo=timezone.utc)
            age = datetime.now(timezone.utc) - generated.astimezone(timezone.utc)
            stale = age > timedelta(minutes=args.max_age_minutes)
            reason = f"age {age.total_seconds() / 60:.1f} min"

    value = "true" if stale else "false"
    print(f"stale={value} ({reason})")
    output = os.environ.get("GITHUB_OUTPUT")
    if output:
        with open(output, "a", encoding="utf-8") as handle:
            handle.write(f"stale={value}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())

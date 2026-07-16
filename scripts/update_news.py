#!/usr/bin/env python3
"""Fetch latest headlines per watchlist ticker and write data/news.json.

Source: Yahoo Finance per-symbol RSS. Headlines are displayed with their
publisher domain visible so the reader can judge the source — this script
does no filtering or interpretation of its own.
"""

import json
import os
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

RSS_URL = (
    "https://feeds.finance.yahoo.com/rss/2.0/headline"
    "?s={symbol}&region=US&lang=en-US"
)
MAX_PER_SYMBOL = 3

with open("watchlist.json") as _f:
    SYMBOLS = list(json.load(_f)["watchlist"])


def fetch_headlines(symbol: str) -> list[dict]:
    req = urllib.request.Request(
        RSS_URL.format(symbol=symbol), headers={"User-Agent": "Mozilla/5.0"}
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        root = ET.fromstring(resp.read())
    items = []
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        pub = (item.findtext("pubDate") or "").strip()
        if title and link:
            items.append({"title": title, "link": link, "pubDate": pub})
        if len(items) >= MAX_PER_SYMBOL:
            break
    return items


def main() -> int:
    news = {}
    errors = []
    for symbol in SYMBOLS:
        try:
            items = fetch_headlines(symbol)
            if items:
                news[symbol] = items
        except Exception as exc:
            errors.append(f"{symbol}: {exc}")

    if not news:
        print("All news fetches failed:\n" + "\n".join(errors), file=sys.stderr)
        return 1

    out = {
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "news": news,
        "errors": errors,
    }
    os.makedirs("data", exist_ok=True)
    with open("data/news.json", "w") as f:
        json.dump(out, f, indent=1)
    print(f"Wrote data/news.json for {len(news)} symbols; {len(errors)} errors")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

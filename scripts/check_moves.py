#!/usr/bin/env python3
"""Detect newly significant one-day moves and prepare a notification.

Reads data/quotes.json (already fetched and validated this run), compares
flagged tickers against data/notified_moves.json so each ticker alerts at
most once per trading day, and — when there is something new — writes the
issue body and title for the workflow to post. Reports what moved with a
news link; nothing here interprets or recommends.

Usage: check_moves.py <body.md> <title.txt>
Writes both files ONLY when new flagged tickers exist.
"""

import json
import os
import sys

STATE_PATH = "data/notified_moves.json"


def main() -> int:
    body_path, title_path = sys.argv[1], sys.argv[2]
    with open("data/quotes.json") as f:
        data = json.load(f)

    watched = data["quotes"] + data.get("core", [])
    newest = max(q["date"] for q in watched)
    flagged = [
        q for q in watched
        if q.get("significant") and q["date"] == newest
    ]

    state = {"date": None, "symbols": []}
    if os.path.exists(STATE_PATH):
        with open(STATE_PATH) as f:
            state = json.load(f)
    if state.get("date") != newest:
        state = {"date": newest, "symbols": []}

    new = [q for q in flagged if q["symbol"] not in state["symbols"]]
    if not new:
        print(f"no new significant moves for {newest}")
        return 0

    lines = [
        f"Significant one-day moves (≥ ±{data.get('significant_pct', 3)}%) "
        f"for **{newest}** — observed closes, not recommendations.",
        "",
        "| Ticker | Name | Close | 1 Day | News |",
        "|---|---|---|---|---|",
    ]
    for q in sorted(flagged, key=lambda x: x["d1"]):
        marker = " (new)" if q in new else ""
        lines.append(
            f"| {q['symbol']}{marker} | {q['name']} | ${q['close']:.2f} | "
            f"{q['d1']:+.2f}% | "
            f"[headlines](https://finance.yahoo.com/quote/{q['symbol']}/news) |"
        )
    lines.append(
        "\n_Tracker: https://modernuser.github.io/"
        "skills-introduction-to-github/tracker.html_"
    )

    with open(body_path, "w") as f:
        f.write("\n".join(lines))
    with open(title_path, "w") as f:
        f.write(f"Significant moves {newest}")

    state["symbols"] = sorted(set(state["symbols"]) | {q["symbol"] for q in new})
    with open(STATE_PATH, "w") as f:
        json.dump(state, f, indent=1)
    print(f"{len(new)} newly flagged: {', '.join(q['symbol'] for q in new)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Print the Trading 212 portfolio snapshot and the watchlist, with daily prices, as JSON for Claude to analyse.

Usage:
    python -m portfolio_monitor                 # read the live account (needs T212_API_KEY / T212_API_SECRET)
    python -m portfolio_monitor --sample FILE   # use saved API responses instead of calling Trading 212
"""

import argparse
import json
import os
import sys
from pathlib import Path

from .quotes import fetch_quote
from .snapshot import build_snapshot
from .trading212 import Trading212Client

WATCHLIST = Path(__file__).with_name("watchlist.txt")


def env(name: str, required: bool = True) -> str:
    value = os.environ.get(name, "").strip()
    if required and not value:
        sys.exit(f"Missing environment variable {name}")
    return value


def load_watchlist(path: Path) -> list[str]:
    if not path.exists():
        return []
    tickers = []
    for line in path.read_text().splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            tickers.append(line)
    return tickers


def symbol(ticker: str) -> str:
    return ticker.split("_", 1)[0].upper()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--sample", help="JSON file with {'summary': ..., 'positions': [...]} to use instead of the API")
    parser.add_argument("--watchlist", default=str(WATCHLIST), help="file with one ticker per line")
    parser.add_argument("--no-quotes", action="store_true", help="skip fetching prices from Yahoo Finance")
    args = parser.parse_args()

    if args.sample:
        data = json.loads(Path(args.sample).read_text())
        summary, positions = data["summary"], data["positions"]
    else:
        client = Trading212Client(env("T212_API_KEY"), env("T212_API_SECRET"), demo=bool(env("T212_DEMO", required=False)))
        summary, positions = client.account_summary(), client.positions()

    snapshot = build_snapshot(summary, positions)
    # Trading 212 tickers look like TSLA_US_EQ; compare on the symbol so held stocks drop out of the watchlist.
    held = {symbol(h["ticker"]) for h in snapshot["holdings"] if h["ticker"]}
    watchlist = [t for t in load_watchlist(Path(args.watchlist)) if symbol(t) not in held]

    if not args.no_quotes:
        for h in snapshot["holdings"]:
            if h["ticker"]:
                h["market"] = fetch_quote(h["ticker"])
        watchlist = [{"ticker": t, "market": fetch_quote(t)} for t in watchlist]

    print(json.dumps({"portfolio": snapshot, "watchlist": watchlist}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

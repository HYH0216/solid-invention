"""Daily Trading 212 portfolio report: fetch positions, have Claude review them, push to Telegram.

Usage:
    python -m portfolio_monitor                 # full run, sends to Telegram
    python -m portfolio_monitor --dry-run       # print the report instead of sending it
    python -m portfolio_monitor --sample FILE   # use saved API responses instead of calling Trading 212
    python -m portfolio_monitor --find-chat-id  # print the chat id of whoever messaged your bot
"""

import argparse
import json
import os
import sys
from pathlib import Path

import requests

from . import analyst, telegram
from .snapshot import build_snapshot, diff_snapshots
from .trading212 import Trading212Client


def env(name: str, required: bool = True) -> str:
    value = os.environ.get(name, "").strip()
    if required and not value:
        sys.exit(f"Missing environment variable {name}")
    return value


def find_chat_id() -> None:
    token = env("TELEGRAM_BOT_TOKEN")
    resp = requests.get(f"https://api.telegram.org/bot{token}/getUpdates", timeout=30)
    resp.raise_for_status()
    chats = {}
    for update in resp.json().get("result", []):
        chat = (update.get("message") or {}).get("chat")
        if chat:
            chats[chat["id"]] = chat.get("username") or chat.get("first_name") or ""
    if not chats:
        print("No messages found. Send any message to your bot in Telegram first, then rerun.")
    for chat_id, who in chats.items():
        print(f"chat_id={chat_id}  ({who})")


def load_raw(sample: str | None) -> tuple[dict, list[dict]]:
    if sample:
        data = json.loads(Path(sample).read_text())
        return data["summary"], data["positions"]
    client = Trading212Client(env("T212_API_KEY"), env("T212_API_SECRET"), demo=bool(env("T212_DEMO", required=False)))
    return client.account_summary(), client.positions()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="print the report instead of sending it")
    parser.add_argument("--sample", help="JSON file with {'summary': ..., 'positions': [...]} to use instead of the API")
    parser.add_argument("--state", default=".state/last_snapshot.json", help="where the previous snapshot is kept")
    parser.add_argument("--find-chat-id", action="store_true", help="list chat ids that have messaged the bot")
    args = parser.parse_args()

    if args.find_chat_id:
        find_chat_id()
        return

    if not args.dry_run:
        bot_token, chat_id = env("TELEGRAM_BOT_TOKEN"), env("TELEGRAM_CHAT_ID")

    try:
        summary, positions = load_raw(args.sample)
        snapshot = build_snapshot(summary, positions)

        state_path = Path(args.state)
        previous = json.loads(state_path.read_text()) if state_path.exists() else None
        changes = diff_snapshots(previous, snapshot)

        report = analyst.write_report(snapshot, changes, env("INVESTOR_PROFILE", required=False))
    except Exception as exc:
        if not args.dry_run:
            telegram.send_message(bot_token, chat_id, f"⚠️ 今天的持仓报告生成失败：{exc}")
        raise

    if args.dry_run:
        print(report)
    else:
        telegram.send_message(bot_token, chat_id, report)
        print(f"Report sent ({len(report)} chars, {len(snapshot['holdings'])} holdings).")

    # Only advance the baseline after a successful run, so a failed day isn't skipped in the comparison.
    if not args.sample:
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

import json
import re
import unicodedata
from pathlib import Path
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from modules import news_scraper
from modules import push_notifications

ADDITION_EVENT_RETENTION_DAYS = 30
# 一度見た店を覚えておく期間。リストから一時的に外れて戻った店を再通知しないため。
SEEN_SHOP_RETENTION_DAYS = 180


def shop_key(shop):
    return shop.get("url") or f"{shop.get('area')}:{shop.get('name')}:{shop.get('city')}"


def name_key(shop):
    """同じ県内で、空白の違いを無視して店名を比べるためのキー。"""
    name = unicodedata.normalize("NFKC", shop.get("name") or "")
    name = re.sub(r"\s+", "", name)
    if not name:
        return ""
    return f"{shop.get('area')}:{name}"


def parse_time(value):
    try:
        parsed = datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def build_seen_shops(previous_snapshot, now):
    """前回までに見た店の記録を読み込む。古い記録しかない場合は前回の店と通知履歴から作る。"""
    seen = {}

    def remember(shop, seen_at):
        key = shop_key(shop)
        if not key:
            return
        entry = seen.get(key)
        if entry is None or entry["last_seen"] < seen_at:
            seen[key] = {
                "key": key,
                "name_key": name_key(shop),
                "last_seen": seen_at,
            }

    for entry in previous_snapshot.get("seen_shops", []):
        seen_at = parse_time(entry.get("last_seen"))
        if entry.get("key") and seen_at:
            seen[entry["key"]] = {
                "key": entry["key"],
                "name_key": entry.get("name_key", ""),
                "last_seen": seen_at,
            }

    for event in previous_snapshot.get("addition_events", []):
        seen_at = parse_time(event.get("added_at"))
        if seen_at:
            for shop in event.get("shops", []):
                remember(shop, seen_at)

    for shop in previous_snapshot.get("shops", []):
        remember(shop, now)

    cutoff = now - timedelta(days=SEEN_SHOP_RETENTION_DAYS)
    return {key: entry for key, entry in seen.items() if entry["last_seen"] >= cutoff}


def is_known_shop(shop, seen_shops, seen_name_keys):
    if shop_key(shop) in seen_shops:
        return True
    key = name_key(shop)
    return bool(key) and key in seen_name_keys


def serialize_seen_shops(seen_shops):
    entries = sorted(seen_shops.values(), key=lambda entry: entry["key"])
    return [
        {
            "key": entry["key"],
            "name_key": entry["name_key"],
            "last_seen": entry["last_seen"].isoformat(timespec="seconds"),
        }
        for entry in entries
    ]


def load_previous_snapshot(snapshot_path):
    if not snapshot_path.exists():
        return {}

    try:
        return json.loads(snapshot_path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def prune_addition_events(events, now):
    cutoff = now - timedelta(days=ADDITION_EVENT_RETENTION_DAYS)
    retained = []

    for event in events:
        try:
            added_at = datetime.fromisoformat(event["added_at"])
            if added_at.tzinfo is None:
                added_at = added_at.replace(tzinfo=timezone.utc)
        except (KeyError, TypeError, ValueError):
            continue

        if added_at >= cutoff and event.get("id") and event.get("shops"):
            retained.append(event)

    return retained


def build_addition_event(added_shops, now):
    event_id = now.isoformat(timespec="seconds")
    return {
        "id": event_id,
        "added_at": event_id,
        "shops": added_shops,
    }


def build_notification_payload(added_shops, event_id):
    by_area = defaultdict(list)
    for shop in added_shops:
        by_area[shop.get("area", "その他")].append(shop)

    if len(added_shops) == 1:
        shop = added_shops[0]
        title = "ラ"
        body = f"ラーメン新店が追加されました\n{shop.get('area', '')}: {shop.get('name', '')}"
    else:
        title = "ラ"
        names = "、".join(shop.get("name", "") for shop in added_shops[:3])
        remaining = len(added_shops) - 3
        name_summary = f"{names}、ほか{remaining}店" if remaining > 0 else names
        area_summary = "、".join(f"{area}{len(shops)}件" for area, shops in by_area.items())
        body = f"ラーメン新店が{len(added_shops)}件追加されました\n{name_summary}\n{area_summary}"

    base_url = push_notifications.app_base_url()
    separator = "&" if "?" in base_url else "?"

    return {
        "title": title,
        "body": body,
        "url": f"{base_url}{separator}new={quote(event_id)}",
        "icon": "/static/icons/ramen.png",
        "badge": "/static/icons/badge.png",
        "tag": f"ramen-shinten-{event_id[:10]}",
    }


def main():
    snapshot_path = ROOT / "data" / "news_snapshot.json"
    previous_snapshot = load_previous_snapshot(snapshot_path)
    previous_shops = previous_snapshot.get("shops", [])

    shops, log, debug = news_scraper.get_new_reviews(include_debug=True, allow_snapshot=False)
    if not shops:
        fallback_shops, fallback_log = news_scraper.load_snapshot()
        if fallback_shops:
            print(f"No shops scraped: {log}")
            print(f"Existing snapshot kept: {fallback_log}")
            return
        raise SystemExit(f"No shops scraped and no snapshot available: {log}")

    if debug.get("fallback") == "snapshot":
        print(f"Live scraping unavailable; existing snapshot kept: {log}")
        return

    now = datetime.now(timezone.utc)
    seen_shops = build_seen_shops(previous_snapshot, now)
    seen_name_keys = {entry["name_key"] for entry in seen_shops.values() if entry["name_key"]}
    added_shops = [
        shop for shop in shops
        if not is_known_shop(shop, seen_shops, seen_name_keys)
    ]
    for shop in shops:
        seen_shops[shop_key(shop)] = {
            "key": shop_key(shop),
            "name_key": name_key(shop),
            "last_seen": now,
        }
    addition_events = prune_addition_events(
        previous_snapshot.get("addition_events", []),
        now,
    )
    addition_event = None
    if previous_shops and added_shops:
        addition_event = build_addition_event(added_shops, now)
        addition_events.append(addition_event)

    snapshot = {
        "snapshot_version": 2,
        "status": "success",
        "source": "snapshot",
        "log": log,
        "shops": shops,
        "addition_events": addition_events,
        "seen_shops": serialize_seen_shops(seen_shops),
    }
    snapshot_path.parent.mkdir(exist_ok=True)
    snapshot_path.write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Updated {snapshot_path}: {log}")

    if not previous_shops:
        print("No previous snapshot; notification skipped.")
        return

    if not added_shops:
        print("No new shops; notification skipped.")
        return

    payload = build_notification_payload(added_shops, addition_event["id"])
    result = push_notifications.send_to_all(payload)
    print(f"New shops: {len(added_shops)}")
    print(f"Notification result: {result}")


if __name__ == "__main__":
    main()

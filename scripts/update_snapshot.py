import json
from pathlib import Path
import sys
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from modules import news_scraper
from modules import push_notifications


def shop_key(shop):
    return shop.get("url") or f"{shop.get('area')}:{shop.get('name')}:{shop.get('city')}"


def load_previous_shops(snapshot_path):
    if not snapshot_path.exists():
        return []

    try:
        return json.loads(snapshot_path.read_text(encoding="utf-8")).get("shops", [])
    except Exception:
        return []


def build_notification_payload(added_shops):
    by_area = defaultdict(list)
    for shop in added_shops:
        by_area[shop.get("area", "その他")].append(shop)

    if len(added_shops) == 1:
        shop = added_shops[0]
        title = "ラーメン新店が追加されました"
        body = f"{shop.get('area', '')}: {shop.get('name', '')}"
    else:
        title = f"ラーメン新店が{len(added_shops)}件追加されました"
        body = "、".join(f"{area}{len(shops)}件" for area, shops in by_area.items())

    return {
        "title": title,
        "body": body,
        "url": push_notifications.app_base_url(),
    }


def main():
    snapshot_path = ROOT / "data" / "news_snapshot.json"
    previous_shops = load_previous_shops(snapshot_path)
    previous_keys = {shop_key(shop) for shop in previous_shops}

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

    added_shops = [shop for shop in shops if shop_key(shop) not in previous_keys]

    snapshot = {
        "status": "success",
        "source": "snapshot",
        "log": log,
        "shops": shops,
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

    payload = build_notification_payload(added_shops)
    result = push_notifications.send_to_all(payload)
    print(f"New shops: {len(added_shops)}")
    print(f"Notification result: {result}")


if __name__ == "__main__":
    main()

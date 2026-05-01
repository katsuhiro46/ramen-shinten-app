import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from modules import news_scraper


def main():
    shops, log, _debug = news_scraper.get_new_reviews(include_debug=True)
    if not shops:
        raise SystemExit(f"No shops scraped: {log}")

    snapshot = {
        "status": "success",
        "source": "snapshot",
        "log": log,
        "shops": shops,
    }
    snapshot_path = ROOT / "data" / "news_snapshot.json"
    snapshot_path.parent.mkdir(exist_ok=True)
    snapshot_path.write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Updated {snapshot_path}: {log}")


if __name__ == "__main__":
    main()

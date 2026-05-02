"""ラーメンデータベースのニューオープン検索結果を取得する。"""
try:
    from curl_cffi import requests as http_requests
    USE_BROWSER_TLS = True
except Exception:
    import requests as http_requests
    USE_BROWSER_TLS = False

from bs4 import BeautifulSoup
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple
import time
from urllib.parse import urljoin

BASE_URL = "https://ramendb.supleks.jp"
SNAPSHOT_PATH = Path(__file__).resolve().parents[1] / "data" / "news_snapshot.json"

# 表示順: 群馬 → 栃木 → 茨城 → 埼玉
PREFECTURES = [
    {
        "name": "群馬",
        "state": "gunma",
        "url": "https://gunma-ramendb.supleks.jp/search?q=&state=gunma&city=&order=open-date&station-id=&radius=0.5&type=&page=1&ns=0",
        "fallback_url": "https://ramendb.supleks.jp/search?q=&state=gunma&city=&order=open-date&station-id=&radius=0.5&type=&page=1&ns=0",
    },
    {
        "name": "栃木",
        "state": "tochigi",
        "url": "https://tochigi-ramendb.supleks.jp/search?q=&state=tochigi&city=&order=open-date&station-id=&radius=0.5&type=&page=1&ns=0",
        "fallback_url": "https://ramendb.supleks.jp/search?q=&state=tochigi&city=&order=open-date&station-id=&radius=0.5&type=&page=1&ns=0",
    },
    {
        "name": "茨城",
        "state": "ibaraki",
        "url": "https://ibaraki-ramendb.supleks.jp/search?q=&state=ibaraki&city=&order=open-date&station-id=&radius=0.5&type=&page=1&ns=0",
        "fallback_url": "https://ramendb.supleks.jp/search?q=&state=ibaraki&city=&order=open-date&station-id=&radius=0.5&type=&page=1&ns=0",
    },
    {
        "name": "埼玉",
        "state": "saitama",
        "url": "https://saitama-ramendb.supleks.jp/search?q=&state=saitama&city=&order=open-date&station-id=&radius=0.5&type=&page=1&ns=0",
        "fallback_url": "https://ramendb.supleks.jp/search?q=&state=saitama&city=&order=open-date&station-id=&radius=0.5&type=&page=1&ns=0",
    },
]

SHOPS_PER_PREFECTURE = 20
CACHE_TTL_SECONDS = 10 * 60
REQUEST_INTERVAL_SECONDS = 0.1

_cache: Dict[str, Any] = {
    "created_at": 0,
    "shops": [],
    "log": "",
    "debug": {},
}

# 削除対象キーワード（店名から除外するもの）
GARBAGE_KEYWORDS = ["PR", "広告", "AD"]

def clean_shop_name(raw_text: str) -> str:
    """店名の精密清掃"""
    if not raw_text: return ""
    text = raw_text.strip()
    # 余計な情報をカット
    text = re.sub(r'\d+(\.\d+)?\s*(ポイント|レビュー|スキ|フォト|件)', '', text)
    for keyword in GARBAGE_KEYWORDS:
        text = text.replace(keyword, '')
    # 括弧などを削除
    text = re.sub(r'[【（\(].*?[】）\)]', '', text)
    # 最終整形
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def parse_int(value: str) -> int:
    digits = re.sub(r"[^\d]", "", value or "")
    return int(digits) if digits else 0

def extract_open_date(soup: BeautifulSoup) -> str:
    table = soup.select_one("#shop-data-table")
    if not table:
        return ""

    for row in table.select("tr"):
        heading = row.find("th")
        value = row.find("td")
        if heading and value and "オープン日" in heading.get_text(strip=True):
            return value.get_text(" ", strip=True)

    return ""

def fetch_open_date(url: str, session: Any) -> str:
    try:
        response = session.get(url, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        return extract_open_date(soup)
    except Exception as e:
        print(f"Detail Error {url}: {e}")
        return ""

def parse_search_result(html: str, pref_name: str, session: Any) -> Tuple[List[Dict], Dict]:
    soup = BeautifulSoup(html, "html.parser")
    items = soup.select("ul#searched > li")
    shops = []

    for item in items:
        link_el = item.select_one(".name h4 a[href^='/s/'][href$='.html']")
        if not link_el:
            continue

        shop_name = clean_shop_name(link_el.get_text(" ", strip=True))
        if len(shop_name) < 2:
            continue

        city = ""
        for city_link in item.select(".area a"):
            if "city=" in city_link.get("href", ""):
                city = city_link.get_text(strip=True)
                break
        point = item.select_one(".point-val")
        review = item.select_one(".reviews .val")
        shop_url = urljoin(BASE_URL, link_el.get("href"))

        shops.append({
            "name": shop_name,
            "area": pref_name,
            "url": shop_url,
            "city": city,
            "open_date": "",
            "point": point.get_text(strip=True) if point else "",
            "review_count": parse_int(review.get_text(strip=True) if review else ""),
        })

        if len(shops) >= SHOPS_PER_PREFECTURE:
            break

    for shop in shops:
        shop["open_date"] = fetch_open_date(shop["url"], session)
        time.sleep(REQUEST_INTERVAL_SECONDS)

    debug_info = {
        "result_items": len(items),
        "parsed_shops": len(shops),
        "first_shop": shops[0] if shops else None,
    }
    return shops, debug_info

def scrape_one_prefecture(prefecture: Dict[str, str], session: Any) -> Tuple[List[Dict], Dict]:
    """1県分をスクレイピングする。"""
    pref_name = prefecture["name"]
    urls = [prefecture["url"], prefecture["fallback_url"]]
    attempts = []

    for url in urls:
        try:
            response = session.get(url, timeout=15)
            attempts.append({
                "url": url,
                "status_code": response.status_code,
                "html_length": len(response.text),
            })
            response.raise_for_status()
            shops, debug_info = parse_search_result(response.text, pref_name, session)
            debug_info.update({
                "url": url,
                "attempts": attempts,
                "status_code": response.status_code,
                "html_length": len(response.text),
            })
            return shops, debug_info
        except Exception as e:
            print(f"Error {pref_name} {url}: {e}")
            attempts[-1]["error"] = str(e) if attempts else str(e)

    return [], {
        "url": urls[-1],
        "attempts": attempts,
        "error": attempts[-1].get("error", "Unknown scraping error") if attempts else "Unknown scraping error",
    }

def get_new_reviews(include_debug: bool = False, allow_snapshot: bool = True) -> Tuple[List[Dict], str, Dict]:
    """メインエントリーポイント。"""
    now = time.time()
    if _cache["shops"] and now - _cache["created_at"] < CACHE_TTL_SECONDS:
        debug = dict(_cache["debug"])
        debug["cache_hit"] = True
        return _cache["shops"], _cache["log"], debug if include_debug else {}

    if USE_BROWSER_TLS:
        session = http_requests.Session(impersonate="chrome124")
    else:
        session = http_requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'ja,en-US;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Upgrade-Insecure-Requests': '1',
        'Referer': 'https://ramendb.supleks.jp/',
        'DNT': '1',
    })
    
    all_shops = []
    logs = []
    debug_by_pref = {}
    for prefecture in PREFECTURES:
        shops, debug_info = scrape_one_prefecture(prefecture, session)
        all_shops.extend(shops)
        logs.append(f"{prefecture['name']}: {len(shops)}件")
        debug_by_pref[prefecture["name"]] = debug_info
        time.sleep(REQUEST_INTERVAL_SECONDS)
    
    log = " | ".join(logs)
    if allow_snapshot and not all_shops:
        fallback_shops, fallback_log = load_snapshot()
        if fallback_shops:
            debug = {
                "browser_tls": USE_BROWSER_TLS,
                "cache_hit": False,
                "fallback": "snapshot",
                "live_log": log,
                "prefectures": debug_by_pref,
                "total_shops": len(fallback_shops),
            }
            _cache.update({
                "created_at": now,
                "shops": fallback_shops,
                "log": fallback_log,
                "debug": debug,
            })
            return fallback_shops, fallback_log, debug if include_debug else {}

    _cache.update({
        "created_at": now,
        "shops": all_shops,
        "log": log,
        "debug": {
            "cache_hit": False,
            "browser_tls": USE_BROWSER_TLS,
            "prefectures": debug_by_pref,
            "total_shops": len(all_shops),
        },
    })
    return all_shops, log, _cache["debug"] if include_debug else {}

def load_snapshot() -> Tuple[List[Dict], str]:
    try:
        payload = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
        shops = payload.get("shops", [])
        return shops, f"{payload.get('log', '')} | fallback: snapshot"
    except Exception as e:
        print(f"Snapshot Error: {e}")
        return [], ""

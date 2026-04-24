"""
ラーメンデータベース スクレイパー - 2026年4月 最新対応版
"""
import requests
from bs4 import BeautifulSoup
import re
from typing import List, Dict, Tuple
import time

# 表示順: 群馬 → 栃木 → 埼玉 → 茨城
URLS = [
    ('https://ramendb.supleks.jp/search?state=gunma&order=open-date', '群馬'),
    ('https://ramendb.supleks.jp/search?state=tochigi&order=open-date', '栃木'),
    ('https://ramendb.supleks.jp/search?state=saitama&order=open-date', '埼玉'),
    ('https://ramendb.supleks.jp/search?state=ibaraki&order=open-date', '茨城'),
]

SHOPS_PER_PREFECTURE = 20

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

def scrape_one_prefecture(url: str, pref_name: str, session) -> List[Dict]:
    """1県分をスクレイピング（2026年最新対応版）"""
    shops = []
    try:
        response = session.get(url, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 検索結果の「箱」を直接探す（より確実な方法に変更）
        items = soup.find_all(['li', 'div'], class_=re.compile(r'item|map-item'))
        
        count = 0
        for item in items:
            # 店名リンクを探す
            link_el = item.find('a', href=re.compile(r'^/s/\d+\.html$'))
            if not link_el: continue
            
            # リンクの中にテキストがない（画像リンクなど）場合は飛ばす
            raw_name = link_el.get_text(strip=True)
            if not raw_name: continue
            
            shop_name = clean_shop_name(raw_name)
            if len(shop_name) < 2: continue
            
            # 詳細情報の取得
            info_el = item.find(class_=re.compile(r'info|address'))
            info_text = info_el.get_text(' ', strip=True) if info_el else ""
            
            # 地名とオープン日の抽出
            city = ""
            city_match = re.search(r'([^\s]+?[郡市区])', info_text)
            if city_match: city = city_match.group(1)
            
            open_date = ""
            date_match = re.search(r'(\d{4}/\d{1,2}/\d{1,2}|\d{1,2}月\d{1,2}日)', info_text)
            if date_match: open_date = date_match.group(1)

            shops.append({
                'name': shop_name,
                'area': pref_name,
                'url': f"https://ramendb.supleks.jp{link_el['href']}",
                'city': city,
                'open_date': open_date,
            })
            
            count += 1
            if count >= SHOPS_PER_PREFECTURE: break
            
        return shops
    except Exception as e:
        print(f"Error {pref_name}: {e}")
        return []

def get_new_reviews() -> Tuple[List[Dict], str]:
    """メインエントリーポイント"""
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    })
    all_shops = []
    logs = []
    for url, pref_name in URLS:
        shops = scrape_one_prefecture(url, pref_name, session)
        all_shops.extend(shops)
        logs.append(f"{pref_name}: {len(shops)}件")
        time.sleep(1)
    return all_shops, " | ".join(logs)

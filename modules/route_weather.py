from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import time

import requests


JST = ZoneInfo("Asia/Tokyo")
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

WEEKDAY_LABELS = ["月曜", "火曜", "水曜", "木曜", "金曜", "土曜", "日曜"]
WEEKDAY_NAMES = ["月曜日", "火曜日", "水曜日", "木曜日", "金曜日", "土曜日", "日曜日"]

LOCATIONS = {
    "水戸": {"full_name": "茨城県水戸市", "lat": 36.3659, "lon": 140.4714},
    "筑西": {"full_name": "茨城県筑西市", "lat": 36.3072, "lon": 139.9831},
    "真岡": {"full_name": "栃木県真岡市", "lat": 36.4401, "lon": 140.0134},
    "鹿沼": {"full_name": "栃木県鹿沼市", "lat": 36.5671, "lon": 139.7450},
    "小山": {"full_name": "栃木県小山市", "lat": 36.3147, "lon": 139.8001},
    "熊谷": {"full_name": "埼玉県熊谷市", "lat": 36.1473, "lon": 139.3886},
    "深谷": {"full_name": "埼玉県深谷市", "lat": 36.1975, "lon": 139.2815},
    "日光": {"full_name": "栃木県日光市", "lat": 36.7198, "lon": 139.6982},
    "大田原": {"full_name": "栃木県大田原市", "lat": 36.8712, "lon": 140.0155},
    "邑楽": {"full_name": "群馬県邑楽町", "lat": 36.2524, "lon": 139.4624},
}

ROUTES = {
    0: ["水戸", "筑西"],
    1: ["真岡", "筑西"],
    2: ["鹿沼", "真岡", "小山"],
    3: ["熊谷", "深谷"],
    4: ["日光", "大田原"],
    5: ["邑楽"],
    6: ["邑楽"],
}

WEATHER_CODES = {
    0: ("☀️", "晴れ"),
    1: ("☀️", "晴れ"),
    2: ("☁️", "曇り"),
    3: ("☁️", "曇り"),
    45: ("☁️", "霧"),
    48: ("☁️", "霧"),
    51: ("☔", "小雨"),
    53: ("☔", "小雨"),
    55: ("☔", "雨"),
    56: ("☔", "雨"),
    57: ("☔", "雨"),
    61: ("☔", "雨"),
    63: ("☔", "雨"),
    65: ("☔", "強雨"),
    66: ("☔", "雨"),
    67: ("☔", "雨"),
    71: ("❄️", "雪"),
    73: ("❄️", "雪"),
    75: ("❄️", "大雪"),
    77: ("❄️", "雪"),
    80: ("☔", "雨"),
    81: ("☔", "雨"),
    82: ("☔", "強雨"),
    85: ("❄️", "雪"),
    86: ("❄️", "大雪"),
    95: ("🌩️", "雷"),
    96: ("🌩️", "雷雨"),
    99: ("🌩️", "雷雨"),
}

RAIN_CODES = {51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82, 95, 96, 99}
SNOW_CODES = {71, 73, 75, 77, 85, 86}
THUNDER_CODES = {95, 96, 99}
STRONG_WIND_MS = 10


def parse_base_date(value):
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=JST)


def route_for_tomorrow(base_date=None):
    now = base_date or datetime.now(JST)
    tomorrow = now.date() + timedelta(days=1)
    weekday = tomorrow.weekday()
    return tomorrow, weekday, ROUTES[weekday]


def weather_label(code):
    return WEATHER_CODES.get(int(code), ("☁️", "不明"))


def round_temperature(value):
    return int(round(float(value)))


def max_precipitation_for_hours(hourly, target_date, start_hour, end_hour):
    times = hourly.get("time", [])
    probabilities = hourly.get("precipitation_probability", [])
    values = []

    for time_text, probability in zip(times, probabilities):
        if probability is None:
            continue
        parsed = datetime.fromisoformat(time_text)
        if parsed.date() == target_date and start_hour <= parsed.hour <= end_hour:
            values.append(float(probability))

    if not values:
        return 0
    return int(round(max(values)))


def fetch_weather(location_name, target_date):
    location = LOCATIONS[location_name]
    params = {
        "latitude": location["lat"],
        "longitude": location["lon"],
        "daily": ",".join([
            "weather_code",
            "temperature_2m_max",
            "temperature_2m_min",
            "precipitation_probability_max",
            "wind_speed_10m_max",
        ]),
        "hourly": "precipitation_probability",
        "timezone": "Asia/Tokyo",
        "wind_speed_unit": "ms",
        "start_date": target_date.isoformat(),
        "end_date": target_date.isoformat(),
    }
    last_error = None
    for attempt in range(3):
        try:
            response = requests.get(OPEN_METEO_URL, params=params, timeout=25)
            response.raise_for_status()
            break
        except requests.RequestException as error:
            last_error = error
            if attempt < 2:
                time.sleep(2 * (attempt + 1))
    else:
        raise last_error

    weather_data = response.json()
    daily = weather_data["daily"]
    hourly = weather_data.get("hourly", {})
    code = int(daily["weather_code"][0])
    icon, label = weather_label(code)
    morning_precipitation = max_precipitation_for_hours(hourly, target_date, 0, 11)
    afternoon_precipitation = max_precipitation_for_hours(hourly, target_date, 12, 23)
    precipitation = max(
        int(round(float(daily["precipitation_probability_max"][0]))),
        morning_precipitation,
        afternoon_precipitation,
    )

    return {
        "name": location_name,
        "full_name": location["full_name"],
        "weather_code": code,
        "weather_icon": icon,
        "weather_label": label,
        "max_temp": round_temperature(daily["temperature_2m_max"][0]),
        "min_temp": round_temperature(daily["temperature_2m_min"][0]),
        "precipitation": precipitation,
        "precipitation_morning": morning_precipitation,
        "precipitation_afternoon": afternoon_precipitation,
        "wind": float(daily.get("wind_speed_10m_max", [0])[0] or 0),
    }


def build_attention(forecasts):
    flags = []
    if any(item["weather_code"] in THUNDER_CODES for item in forecasts):
        flags.append("雷")
    if any(item["weather_code"] in SNOW_CODES for item in forecasts):
        flags.append("雪")
    if any(item["weather_code"] in RAIN_CODES or item["precipitation"] >= 60 for item in forecasts):
        flags.append("雨具・荷物濡れ")
    if any(item["wind"] >= STRONG_WIND_MS for item in forecasts):
        flags.append("強風")

    if not flags:
        return ""
    return "⚠️注意：" + "・".join(flags)


def build_payload(target_date, weekday, route, forecasts, url="/weather"):
    title = f"【天】明日の配送天気：{WEEKDAY_LABELS[weekday]}／{'・'.join(route)}"
    lines = ["【天】配送天気"]

    for item in forecasts:
        lines.append(
            f"{item['name']}：{item['weather_icon']}{item['weather_label']} "
            f"{item['max_temp']}/{item['min_temp']}℃ "
            f"降水 午前{item['precipitation_morning']}/午後{item['precipitation_afternoon']}%"
        )

    attention = build_attention(forecasts)
    if attention:
        lines.append(attention)

    return {
        "title": title,
        "body": "\n".join(lines),
        "url": url,
        "date": target_date.isoformat(),
        "tag": f"route-weather-{target_date.isoformat()}",
        "icon": "/static/icons/weather.svg",
        "badge": "/static/icons/weather.svg",
    }


def get_tomorrow_route_weather(base_date=None):
    target_date, weekday, route = route_for_tomorrow(base_date)
    forecasts = [fetch_weather(location, target_date) for location in route]
    attention = build_attention(forecasts)
    return {
        "target_date": target_date.isoformat(),
        "weekday": weekday,
        "weekday_label": WEEKDAY_LABELS[weekday],
        "weekday_name": WEEKDAY_NAMES[weekday],
        "route": route,
        "forecasts": forecasts,
        "attention": attention,
    }

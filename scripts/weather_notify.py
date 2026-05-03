import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from modules import push_notifications, route_weather


def main():
    parser = argparse.ArgumentParser(description="Send tomorrow route weather notification.")
    parser.add_argument("--date", help="Base date in JST, YYYY-MM-DD. Tomorrow's route is notified.")
    parser.add_argument("--dry-run", action="store_true", help="Build the notification without sending it.")
    args = parser.parse_args()

    dry_run = args.dry_run or os.getenv("WEATHER_NOTIFY_DRY_RUN") == "1"
    weather = route_weather.get_tomorrow_route_weather(route_weather.parse_base_date(args.date))
    payload = route_weather.build_payload(
        route_weather.datetime.strptime(weather["target_date"], "%Y-%m-%d").date(),
        weather["weekday"],
        weather["route"],
        weather["forecasts"],
        url=f"{push_notifications.app_base_url().rstrip('/')}/weather",
    )

    print(payload["title"])
    print(payload["body"])

    if dry_run:
        print("Dry run: notification not sent.")
        return

    result = push_notifications.send_to_all(payload)
    print(f"Notification result: {result}")
    if result.get("failed"):
        raise SystemExit("Weather notification failed for at least one subscription.")


if __name__ == "__main__":
    main()

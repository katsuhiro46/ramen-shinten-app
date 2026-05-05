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
    parser.add_argument("--force", action="store_true", help="Send even when today's weather notification was already sent.")
    args = parser.parse_args()

    dry_run = args.dry_run or os.getenv("WEATHER_NOTIFY_DRY_RUN") == "1"
    weather = route_weather.get_tomorrow_route_weather(route_weather.parse_base_date(args.date))
    target_date = route_weather.datetime.strptime(weather["target_date"], "%Y-%m-%d").date()
    payload = route_weather.build_payload(
        target_date,
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

    if not args.force and notification_already_sent(target_date.isoformat()):
        print(f"Weather notification already sent for {target_date.isoformat()}; skipped.")
        return

    result = push_notifications.send_to_all(payload)
    print(f"Notification result: {result}")
    if result.get("failed"):
        raise SystemExit("Weather notification failed for at least one subscription.")
    if result.get("sent"):
        mark_notification_sent(target_date.isoformat())


def notification_already_sent(target_date):
    if not push_notifications.storage_configured():
        return False

    return bool(push_notifications.redis_command("GET", weather_sent_key(target_date)))


def mark_notification_sent(target_date):
    if not push_notifications.storage_configured():
        return

    push_notifications.redis_command("SET", weather_sent_key(target_date), "1", "EX", 60 * 60 * 36)


def weather_sent_key(target_date):
    return f"ramen:weather:sent:{target_date}"


if __name__ == "__main__":
    main()

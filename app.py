import os

from flask import Flask, render_template, jsonify, request, send_from_directory
from modules import news_scraper, push_notifications, route_weather

app = Flask(__name__)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/weather')
def weather_page():
    return render_template('weather.html')


@app.route('/manifest.json')
def manifest():
    return send_from_directory('static', 'manifest.json', mimetype='application/manifest+json')


@app.route('/service-worker.js')
def service_worker():
    return send_from_directory('static', 'service-worker.js', mimetype='application/javascript')


@app.route('/api/news')
def get_news():
    try:
        include_debug = request.args.get('debug') == '1'
        news_data, log_msg, debug_info = news_scraper.get_new_reviews(include_debug=include_debug)
        payload = {
            "status": "success",
            "shops": news_data,
            "log": log_msg
        }
        if include_debug:
            payload["debug"] = debug_info
        return jsonify(payload)
    except Exception as e:
        print(f"Scraper Error: {e}")
        return jsonify({
            "status": "error",
            "message": "データ取得に失敗しました",
            "error": str(e),
            "shops": [],
        }), 500


@app.route('/api/weather')
def get_weather():
    try:
        base_date = route_weather.parse_base_date(request.args.get('date'))
        weather = route_weather.get_tomorrow_route_weather(base_date)
        return jsonify({
            "status": "success",
            "weather": weather,
        })
    except Exception as e:
        print(f"Weather Error: {e}")
        return jsonify({
            "status": "error",
            "message": "天気取得に失敗しました",
            "error": str(e),
        }), 500


@app.route('/api/cron/weather')
def cron_weather():
    if not cron_authorized():
        return jsonify({
            "status": "error",
            "message": "Unauthorized",
        }), 401

    try:
        weather = route_weather.get_tomorrow_route_weather()
        target_date = weather["target_date"]

        if weather_notification_sent(target_date):
            return jsonify({
                "status": "success",
                "message": "already sent",
                "target_date": target_date,
            })

        payload = route_weather.build_payload(
            route_weather.datetime.strptime(target_date, "%Y-%m-%d").date(),
            weather["weekday"],
            weather["route"],
            weather["forecasts"],
            url=f"{push_notifications.app_base_url().rstrip('/')}/weather",
        )
        result = push_notifications.send_to_all(payload)
        if result.get("failed"):
            return jsonify({
                "status": "error",
                "message": "通知送信に失敗しました",
                "result": result,
            }), 500

        if result.get("sent"):
            mark_weather_notification_sent(target_date)

        return jsonify({
            "status": "success",
            "target_date": target_date,
            "title": payload["title"],
            "result": result,
        })
    except Exception as e:
        print(f"Weather cron error: {e}")
        return jsonify({
            "status": "error",
            "message": "天気通知に失敗しました",
            "error": str(e),
        }), 500


def cron_authorized():
    secret = os.getenv("CRON_SECRET", "").strip()
    if not secret:
        return request.headers.get("User-Agent", "").startswith("vercel-cron/")
    return request.headers.get("Authorization") == f"Bearer {secret}"


def weather_notification_sent(target_date):
    if not push_notifications.storage_configured():
        return False
    return bool(push_notifications.redis_command("GET", weather_sent_key(target_date)))


def mark_weather_notification_sent(target_date):
    if push_notifications.storage_configured():
        push_notifications.redis_command("SET", weather_sent_key(target_date), "1", "EX", 60 * 60 * 36)


def weather_sent_key(target_date):
    return f"ramen:weather:sent:{target_date}"


@app.route('/api/push/config')
def push_config():
    return jsonify(push_notifications.public_config())


@app.route('/api/push/subscribe', methods=['POST'])
def push_subscribe():
    if not push_notifications.push_configured():
        return jsonify({
            "status": "error",
            "message": "通知設定がまだ完了していません",
        }), 503

    try:
        push_notifications.save_subscription(request.get_json(force=True))
        return jsonify({"status": "success"})
    except Exception as e:
        print(f"Push subscribe error: {e}")
        return jsonify({
            "status": "error",
            "message": "通知登録に失敗しました",
        }), 400


@app.route('/api/push/unsubscribe', methods=['POST'])
def push_unsubscribe():
    try:
        push_notifications.delete_subscription(request.get_json(force=True))
        return jsonify({"status": "success"})
    except Exception as e:
        print(f"Push unsubscribe error: {e}")
        return jsonify({
            "status": "error",
            "message": "通知解除に失敗しました",
        }), 400


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=3000)

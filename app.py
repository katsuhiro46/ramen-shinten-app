from flask import Flask, render_template, jsonify, request, send_from_directory
from modules import news_scraper, push_notifications

app = Flask(__name__)


@app.route('/')
def index():
    return render_template('index.html')


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

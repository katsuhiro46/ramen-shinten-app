from flask import Flask, render_template, jsonify, request
from modules import news_scraper

app = Flask(__name__)


@app.route('/')
def index():
    return render_template('index.html')


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


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=3000)

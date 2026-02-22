from flask import Flask, render_template, jsonify
from modules import news_scraper

app = Flask(__name__)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/news')
def get_news():
    try:
        news_data, log_msg = news_scraper.get_new_reviews()
        return jsonify({
            "status": "success",
            "shops": news_data,
            "log": log_msg
        })
    except Exception as e:
        print(f"Scraper Error: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=3000)

from flask import Flask, jsonify
from flask_cors import CORS
from datetime import datetime

from bank_api.routes import bank_bp
from wallet_api.routes import wallet_bp
from news_api.routes import news_bp
from stock_api.routes import stock_bp

app = Flask(__name__)
CORS(app)

app.register_blueprint(bank_bp,   url_prefix='/bank')
app.register_blueprint(wallet_bp, url_prefix='/wallet')
app.register_blueprint(news_bp,   url_prefix='/news')
app.register_blueprint(stock_bp,  url_prefix='/stock')


@app.route('/health')
def health():
    return jsonify({
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "services": {
            "bank":   "/bank",
            "wallet": "/wallet",
            "news":   "/news",
            "stock":  "/stock"
        }
    })


@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Endpoint not found"}), 404


@app.errorhandler(500)
def server_error(e):
    return jsonify({"error": "Internal server error"}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

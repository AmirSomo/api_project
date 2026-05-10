from flask import Blueprint, jsonify, request
import uuid
import jwt
from datetime import datetime, timedelta, timezone

wallet_bp = Blueprint('wallet', __name__)

_SECRET = "mock_secret_key_2026"
_ALGO = "HS256"
_TOKEN_MINUTES = 30

_users = {}
_transactions = []
_cryptos = {
    'RNDM': {'id': 'rndm', 'name': 'RandomCoin', 'symbol': 'RNDM', 'current_price': 1.0, 'market_cap': 1000000},
    'FLUX': {'id': 'flux', 'name': 'FluxCoin',  'symbol': 'FLUX', 'current_price': 5.0, 'market_cap': 5000000},
}


def _make_token(username):
    exp = datetime.now(timezone.utc) + timedelta(minutes=_TOKEN_MINUTES)
    return jwt.encode({"sub": username, "exp": exp}, _SECRET, algorithm=_ALGO)


def _auth():
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None, ({"error": "Missing or invalid Authorization header"}, 401)
    try:
        payload = jwt.decode(auth[7:], _SECRET, algorithms=[_ALGO])
        username = payload.get("sub")
        if username not in _users:
            return None, ({"error": "User not found"}, 404)
        return _users[username], None
    except jwt.ExpiredSignatureError:
        return None, ({"error": "Token expired"}, 401)
    except jwt.InvalidTokenError:
        return None, ({"error": "Invalid token"}, 401)


@wallet_bp.route('/register', methods=['POST'])
def register():
    username = request.args.get("username")
    email = request.args.get("email")
    password = request.args.get("password")
    if not username or not email or not password:
        return jsonify({"error": "username, email, and password are required"}), 400
    if username in _users:
        return jsonify({"error": "Username already exists"}), 400
    _users[username] = {
        "username": username,
        "email": email,
        "hashed_password": password + "_hashed",
        "balance": 1000.0,
        "owned_tokens": {}
    }
    return jsonify({"message": "User registered", "username": username, "balance": 1000.0}), 201


@wallet_bp.route('/token', methods=['POST'])
def token():
    username = request.form.get("username")
    password = request.form.get("password")
    user = _users.get(username)
    if not user or user["hashed_password"] != password + "_hashed":
        return jsonify({"error": "Incorrect username or password"}), 401
    return jsonify({"access_token": _make_token(username), "token_type": "bearer"}), 200


@wallet_bp.route('/cryptocurrencies', methods=['GET'])
def list_cryptos():
    return jsonify(list(_cryptos.values())), 200


@wallet_bp.route('/buy', methods=['POST'])
def buy():
    user, err = _auth()
    if err:
        return jsonify(err[0]), err[1]
    symbol = request.args.get("symbol", "").upper()
    amount = request.args.get("amount", type=float)
    if not symbol or symbol not in _cryptos:
        return jsonify({"error": f"Cryptocurrency '{symbol}' not found"}), 404
    if not amount or amount <= 0:
        return jsonify({"error": "Invalid amount"}), 400
    crypto = _cryptos[symbol]
    total_cost = crypto["current_price"] * amount
    if user["balance"] < total_cost:
        return jsonify({"error": "Insufficient balance"}), 400
    crypto["current_price"] = round(crypto["current_price"] * 1.02, 6)
    user["balance"] -= total_cost
    user["owned_tokens"][symbol] = user["owned_tokens"].get(symbol, 0) + amount
    txn = {
        "id": str(uuid.uuid4()),
        "user_id": user["username"],
        "crypto_symbol": symbol,
        "amount": amount,
        "price": crypto["current_price"],
        "transaction_type": "buy",
        "timestamp": datetime.now().isoformat()
    }
    _transactions.append(txn)
    return jsonify(txn), 200


@wallet_bp.route('/sell', methods=['POST'])
def sell():
    user, err = _auth()
    if err:
        return jsonify(err[0]), err[1]
    symbol = request.args.get("symbol", "").upper()
    amount = request.args.get("amount", type=float)
    if not symbol or symbol not in _cryptos:
        return jsonify({"error": f"Cryptocurrency '{symbol}' not found"}), 404
    if not amount or amount <= 0:
        return jsonify({"error": "Invalid amount"}), 400
    user_holding = user["owned_tokens"].get(symbol, 0)
    if user_holding < amount:
        return jsonify({"error": "Insufficient token balance"}), 400
    crypto = _cryptos[symbol]
    crypto["current_price"] = round(crypto["current_price"] * 0.98, 6)
    revenue = crypto["current_price"] * amount
    user["balance"] += revenue
    user["owned_tokens"][symbol] -= amount
    txn = {
        "id": str(uuid.uuid4()),
        "user_id": user["username"],
        "crypto_symbol": symbol,
        "amount": amount,
        "price": crypto["current_price"],
        "transaction_type": "sell",
        "timestamp": datetime.now().isoformat()
    }
    _transactions.append(txn)
    return jsonify(txn), 200


@wallet_bp.route('/transactions', methods=['GET'])
def get_transactions():
    user, err = _auth()
    if err:
        return jsonify(err[0]), err[1]
    return jsonify([t for t in _transactions if t["user_id"] == user["username"]]), 200


@wallet_bp.route('/portfolio', methods=['GET'])
def portfolio():
    user, err = _auth()
    if err:
        return jsonify(err[0]), err[1]
    holdings = []
    for symbol, qty in user["owned_tokens"].items():
        if qty > 0 and symbol in _cryptos:
            price = _cryptos[symbol]["current_price"]
            holdings.append({"symbol": symbol, "quantity": qty, "current_price": price, "value": round(price * qty, 6)})
    return jsonify({"username": user["username"], "cash_balance": user["balance"], "holdings": holdings}), 200

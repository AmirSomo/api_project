from flask import Blueprint, jsonify, request
import uuid
from datetime import datetime

bank_bp = Blueprint('bank', __name__)

_accounts = {}
_transactions = {}


def _record(account_id, amount, kind, recipient_id=None):
    tid = str(uuid.uuid4())
    _transactions[tid] = {
        "account_id": account_id,
        "type": kind,
        "amount": amount,
        "timestamp": datetime.now().isoformat(),
        "recipient_id": recipient_id,
    }
    return tid


@bank_bp.route('/create_account', methods=['POST'])
def create_account():
    data = request.json or {}
    username = data.get("username")
    initial_balance = data.get("initial_balance", 0)
    if not username:
        return jsonify({"error": "username required"}), 400
    if username in _accounts:
        return jsonify({"error": "Account already exists"}), 400
    account_id = str(uuid.uuid4())
    _accounts[username] = {
        "id": account_id,
        "balance": initial_balance,
        "created_at": datetime.now().isoformat()
    }
    _record(account_id, initial_balance, "Account Creation")
    return jsonify({"message": "Account created successfully", "account_id": account_id}), 201


@bank_bp.route('/balance/<username>', methods=['GET'])
def get_balance(username):
    account = _accounts.get(username)
    if not account:
        return jsonify({"error": "Account not found"}), 404
    return jsonify({"balance": account["balance"]}), 200


@bank_bp.route('/deposit', methods=['POST'])
def deposit():
    data = request.json or {}
    username = data.get("username")
    amount = data.get("amount")
    if username not in _accounts:
        return jsonify({"error": "Account not found"}), 404
    if not amount or amount <= 0:
        return jsonify({"error": "Invalid amount"}), 400
    _accounts[username]["balance"] += amount
    _record(_accounts[username]["id"], amount, "Deposit")
    return jsonify({"message": "Deposit successful", "balance": _accounts[username]["balance"]}), 200


@bank_bp.route('/withdraw', methods=['POST'])
def withdraw():
    data = request.json or {}
    username = data.get("username")
    amount = data.get("amount")
    if username not in _accounts:
        return jsonify({"error": "Account not found"}), 404
    if not amount or amount <= 0:
        return jsonify({"error": "Invalid amount"}), 400
    if _accounts[username]["balance"] < amount:
        return jsonify({"error": "Insufficient balance"}), 400
    _accounts[username]["balance"] -= amount
    _record(_accounts[username]["id"], -amount, "Withdrawal")
    return jsonify({"message": "Withdrawal successful", "balance": _accounts[username]["balance"]}), 200


@bank_bp.route('/transfer', methods=['POST'])
def transfer():
    data = request.json or {}
    from_user = data.get("from_user")
    to_user = data.get("to_user")
    amount = data.get("amount")
    if from_user not in _accounts or to_user not in _accounts:
        return jsonify({"error": "One or both accounts not found"}), 404
    if not amount or amount <= 0:
        return jsonify({"error": "Invalid amount"}), 400
    if _accounts[from_user]["balance"] < amount:
        return jsonify({"error": "Insufficient balance"}), 400
    _accounts[from_user]["balance"] -= amount
    _accounts[to_user]["balance"] += amount
    _record(_accounts[from_user]["id"], -amount, "Transfer", _accounts[to_user]["id"])
    _record(_accounts[to_user]["id"], amount, "Transfer", _accounts[from_user]["id"])
    return jsonify({"message": "Transfer successful"}), 200


@bank_bp.route('/transactions/<username>', methods=['GET'])
def get_transactions(username):
    account = _accounts.get(username)
    if not account:
        return jsonify({"error": "Account not found"}), 404
    txns = [t for t in _transactions.values() if t["account_id"] == account["id"]]
    return jsonify({"transactions": txns}), 200


@bank_bp.route('/account_statement/<username>', methods=['GET'])
def account_statement(username):
    account = _accounts.get(username)
    if not account:
        return jsonify({"error": "Account not found"}), 404
    txns = [t for t in _transactions.values() if t["account_id"] == account["id"]]
    return jsonify({
        "account_id": account["id"],
        "username": username,
        "balance": account["balance"],
        "transactions": txns,
        "created_at": account["created_at"]
    }), 200


@bank_bp.route('/delete_account', methods=['DELETE'])
def delete_account():
    data = request.json or {}
    username = data.get("username")
    if username in _accounts:
        del _accounts[username]
        return jsonify({"message": "Account deleted successfully"}), 200
    return jsonify({"error": "Account not found"}), 404


@bank_bp.route('/view_all_accounts', methods=['GET'])
def view_all_accounts():
    return jsonify(_accounts), 200

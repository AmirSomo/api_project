#!/usr/bin/env bash
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"

echo "Installing dependencies..."
pip install -q -r "$ROOT/requirements.txt"

echo ""
echo "Starting News API  → http://localhost:5001"
cd "$ROOT/news_api" && python3 app.py &
NEWS_PID=$!

echo "Starting Stock API → http://localhost:5002"
cd "$ROOT/stock_api" && python3 app.py &
STOCK_PID=$!

echo ""
echo "Both APIs are running. Press Ctrl+C to stop."
echo "  News API  PID: $NEWS_PID"
echo "  Stock API PID: $STOCK_PID"

trap "echo 'Stopping...'; kill $NEWS_PID $STOCK_PID 2>/dev/null; exit 0" SIGINT SIGTERM

wait

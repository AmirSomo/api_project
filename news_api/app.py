from flask import Flask, jsonify, request
from flask_cors import CORS
import json
import os
from datetime import datetime, timezone

app = Flask(__name__)
CORS(app)

VALID_CATEGORIES = {"business", "entertainment", "general", "health", "science", "sports", "technology"}
VALID_SORT_BY = {"relevancy", "popularity", "publishedAt"}
VALID_LANGUAGES = {"ar", "de", "en", "es", "fr", "he", "it", "nl", "no", "pt", "ru", "sv", "ud", "zh"}
VALID_COUNTRIES = {"ae", "ar", "at", "au", "be", "bg", "br", "ca", "ch", "cn", "co", "cu", "cz", "de", "eg", "fr", "gb", "gr", "hk", "hu", "id", "ie", "il", "in", "it", "jp", "kr", "lt", "lv", "ma", "mx", "my", "ng", "nl", "no", "nz", "ph", "pl", "pt", "ro", "rs", "ru", "sa", "se", "sg", "si", "sk", "th", "tr", "tw", "ua", "us", "ve", "za"}


def load_data():
    path = os.path.join(os.path.dirname(__file__), 'mock_data', 'news.json')
    with open(path, 'r') as f:
        return json.load(f)


def error_response(code, message, status=400):
    return jsonify({"status": "error", "code": code, "message": message}), status


def paginate(items, page, page_size):
    page_size = min(max(page_size, 1), 100)
    page = max(page, 1)
    start = (page - 1) * page_size
    return items[start:start + page_size]


# ─────────────────────────────────────────────
# /v2/everything
# ─────────────────────────────────────────────
@app.route('/v2/everything', methods=['GET'])
def get_everything():
    q = request.args.get('q', '').lower().strip()
    sources_param = request.args.get('sources', '').lower()
    domains = request.args.get('domains', '').lower()
    from_date = request.args.get('from', '')
    to_date = request.args.get('to', '')
    language = request.args.get('language', 'en').lower()
    sort_by = request.args.get('sortBy', 'publishedAt')
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('pageSize', 20, type=int)

    if sort_by not in VALID_SORT_BY:
        return error_response("parameterInvalid", f"sortBy must be one of: {', '.join(VALID_SORT_BY)}")

    data = load_data()
    articles = list(data.get('articles', []))

    # Filter: language (all mock articles are 'en')
    if language and language != 'en':
        articles = []

    # Filter: sources
    if sources_param:
        source_ids = [s.strip() for s in sources_param.split(',')]
        articles = [a for a in articles if a['source']['id'] in source_ids]

    # Filter: search query
    if q:
        terms = q.split()
        articles = [
            a for a in articles
            if all(
                t in a.get('title', '').lower()
                or t in a.get('description', '').lower()
                or t in a.get('content', '').lower()
                for t in terms
            )
        ]

    def parse_dt(s: str) -> datetime:
        dt = datetime.fromisoformat(s.replace('Z', '+00:00'))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt

    # Filter: from date
    if from_date:
        try:
            from_dt = parse_dt(from_date)
            articles = [a for a in articles if parse_dt(a['publishedAt']) >= from_dt]
        except ValueError:
            return error_response("parameterInvalid", "from must be in ISO 8601 format (e.g. 2026-05-01 or 2026-05-01T00:00:00Z)")

    # Filter: to date
    if to_date:
        try:
            to_dt = parse_dt(to_date)
            articles = [a for a in articles if parse_dt(a['publishedAt']) <= to_dt]
        except ValueError:
            return error_response("parameterInvalid", "to must be in ISO 8601 format")

    # Sort
    if sort_by == 'publishedAt':
        articles.sort(key=lambda x: x.get('publishedAt', ''), reverse=True)
    elif sort_by == 'popularity':
        articles.sort(key=lambda x: len(x.get('content', '')), reverse=True)
    # relevancy: keep original order (already query-matched order)

    total = len(articles)
    paged = paginate(articles, page, page_size)

    # Strip internal 'category' field from response
    clean = [{k: v for k, v in a.items() if k != 'category'} for a in paged]

    return jsonify({"status": "ok", "totalResults": total, "articles": clean})


# ─────────────────────────────────────────────
# /v2/top-headlines
# ─────────────────────────────────────────────
@app.route('/v2/top-headlines', methods=['GET'])
def get_top_headlines():
    country = request.args.get('country', '').lower()
    category = request.args.get('category', '').lower()
    sources_param = request.args.get('sources', '').lower()
    q = request.args.get('q', '').lower().strip()
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('pageSize', 20, type=int)

    if category and category not in VALID_CATEGORIES:
        return error_response("parameterInvalid", f"category must be one of: {', '.join(sorted(VALID_CATEGORIES))}")

    if sources_param and (country or category):
        return error_response("parameterIncompatible", "You cannot mix the sources param with the country or category params.")

    data = load_data()
    articles = list(data.get('articles', []))

    # Filter: category
    if category:
        articles = [a for a in articles if a.get('category', '') == category]

    # Filter: sources
    if sources_param:
        source_ids = [s.strip() for s in sources_param.split(',')]
        articles = [a for a in articles if a['source']['id'] in source_ids]

    # Filter: search query
    if q:
        articles = [
            a for a in articles
            if q in a.get('title', '').lower() or q in a.get('description', '').lower()
        ]

    # Latest first
    articles.sort(key=lambda x: x.get('publishedAt', ''), reverse=True)

    total = len(articles)
    paged = paginate(articles, page, page_size)

    clean = [{k: v for k, v in a.items() if k != 'category'} for a in paged]

    return jsonify({"status": "ok", "totalResults": total, "articles": clean})


# ─────────────────────────────────────────────
# /v2/sources
# ─────────────────────────────────────────────
@app.route('/v2/sources', methods=['GET'])
def get_sources():
    category = request.args.get('category', '').lower()
    language = request.args.get('language', '').lower()
    country = request.args.get('country', '').lower()

    if category and category not in VALID_CATEGORIES:
        return error_response("parameterInvalid", f"category must be one of: {', '.join(sorted(VALID_CATEGORIES))}")

    data = load_data()
    sources = list(data.get('sources', []))

    if category:
        sources = [s for s in sources if s.get('category', '') == category]
    if language:
        sources = [s for s in sources if s.get('language', '') == language]
    if country:
        sources = [s for s in sources if s.get('country', '') == country]

    full_sources = []
    descriptions = {
        "cnn": "CNN breaking news, latest news and videos",
        "bbc-news": "Use BBC News for up-to-the-minute news, breaking news and video",
        "bloomberg": "Bloomberg delivers business and markets news, data, analysis, and video",
        "financial-times": "News, analysis and comment from the Financial Times",
        "reuters": "Reuters.com brings you the latest news from around the world",
        "techcrunch": "TechCrunch is a leading technology media property",
        "the-verge": "The Verge covers technology, science, art, and culture",
        "wired": "Wired is where tomorrow is realized",
        "espn": "ESPN serves sports fans anytime, anywhere",
        "health-news": "Trusted health and medical news reporting",
        "science-daily": "Science news from research organizations worldwide",
        "entertainment-weekly": "Entertainment Weekly covers movies, music, TV, and pop culture"
    }
    urls = {
        "cnn": "https://www.cnn.com", "bbc-news": "https://www.bbc.co.uk/news",
        "bloomberg": "https://www.bloomberg.com", "financial-times": "https://www.ft.com",
        "reuters": "https://www.reuters.com", "techcrunch": "https://techcrunch.com",
        "the-verge": "https://www.theverge.com", "wired": "https://www.wired.com",
        "espn": "https://www.espn.com", "health-news": "https://health-news.example.com",
        "science-daily": "https://www.sciencedaily.com",
        "entertainment-weekly": "https://ew.com"
    }

    for s in sources:
        full_sources.append({
            "id": s["id"],
            "name": s["name"],
            "description": descriptions.get(s["id"], ""),
            "url": urls.get(s["id"], "https://example.com"),
            "category": s["category"],
            "language": s["language"],
            "country": s["country"]
        })

    return jsonify({"status": "ok", "sources": full_sources})


# ─────────────────────────────────────────────
# Health check
# ─────────────────────────────────────────────
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "ok",
        "service": "News API (newsapi.org compatible mock)",
        "version": "v2",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    })


@app.errorhandler(404)
def not_found(error):
    return jsonify({"status": "error", "code": "404", "message": "The requested endpoint does not exist."}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({"status": "error", "code": "500", "message": "Internal server error."}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)

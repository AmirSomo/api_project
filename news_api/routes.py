from flask import Blueprint, jsonify, request
import json
import os
from datetime import datetime, timezone

news_bp = Blueprint('news', __name__)

VALID_CATEGORIES = {"business", "entertainment", "general", "health", "science", "sports", "technology"}
VALID_SORT_BY = {"relevancy", "popularity", "publishedAt"}


def _load():
    path = os.path.join(os.path.dirname(__file__), 'mock_data', 'news.json')
    with open(path, 'r') as f:
        return json.load(f)


def _err(code, message, status=400):
    return jsonify({"status": "error", "code": code, "message": message}), status


def _paginate(items, page, page_size):
    page_size = min(max(page_size, 1), 100)
    page = max(page, 1)
    start = (page - 1) * page_size
    return items[start:start + page_size]


def _parse_dt(s):
    dt = datetime.fromisoformat(s.replace('Z', '+00:00'))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


@news_bp.route('/v2/everything', methods=['GET'])
def everything():
    q = request.args.get('q', '').lower().strip()
    sources_param = request.args.get('sources', '').lower()
    from_date = request.args.get('from', '')
    to_date = request.args.get('to', '')
    language = request.args.get('language', 'en').lower()
    sort_by = request.args.get('sortBy', 'publishedAt')
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('pageSize', 20, type=int)

    if sort_by not in VALID_SORT_BY:
        return _err("parameterInvalid", f"sortBy must be one of: {', '.join(VALID_SORT_BY)}")

    data = _load()
    articles = list(data.get('articles', []))

    if language and language != 'en':
        articles = []

    if sources_param:
        ids = [s.strip() for s in sources_param.split(',')]
        articles = [a for a in articles if a['source']['id'] in ids]

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

    if from_date:
        try:
            from_dt = _parse_dt(from_date)
            articles = [a for a in articles if _parse_dt(a['publishedAt']) >= from_dt]
        except ValueError:
            return _err("parameterInvalid", "from must be ISO 8601 (e.g. 2026-05-01T00:00:00Z)")

    if to_date:
        try:
            to_dt = _parse_dt(to_date)
            articles = [a for a in articles if _parse_dt(a['publishedAt']) <= to_dt]
        except ValueError:
            return _err("parameterInvalid", "to must be ISO 8601")

    if sort_by == 'publishedAt':
        articles.sort(key=lambda x: x.get('publishedAt', ''), reverse=True)
    elif sort_by == 'popularity':
        articles.sort(key=lambda x: len(x.get('content', '')), reverse=True)

    total = len(articles)
    paged = _paginate(articles, page, page_size)
    clean = [{k: v for k, v in a.items() if k != 'category'} for a in paged]
    return jsonify({"status": "ok", "totalResults": total, "articles": clean})


@news_bp.route('/v2/top-headlines', methods=['GET'])
def top_headlines():
    country = request.args.get('country', '').lower()
    category = request.args.get('category', '').lower()
    sources_param = request.args.get('sources', '').lower()
    q = request.args.get('q', '').lower().strip()
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('pageSize', 20, type=int)

    if category and category not in VALID_CATEGORIES:
        return _err("parameterInvalid", f"category must be one of: {', '.join(sorted(VALID_CATEGORIES))}")

    if sources_param and (country or category):
        return _err("parameterIncompatible", "You cannot mix the sources param with the country or category params.")

    data = _load()
    articles = list(data.get('articles', []))

    if category:
        articles = [a for a in articles if a.get('category', '') == category]

    if sources_param:
        ids = [s.strip() for s in sources_param.split(',')]
        articles = [a for a in articles if a['source']['id'] in ids]

    if q:
        articles = [
            a for a in articles
            if q in a.get('title', '').lower() or q in a.get('description', '').lower()
        ]

    articles.sort(key=lambda x: x.get('publishedAt', ''), reverse=True)
    total = len(articles)
    paged = _paginate(articles, page, page_size)
    clean = [{k: v for k, v in a.items() if k != 'category'} for a in paged]
    return jsonify({"status": "ok", "totalResults": total, "articles": clean})


@news_bp.route('/v2/sources', methods=['GET'])
def sources():
    category = request.args.get('category', '').lower()
    language = request.args.get('language', '').lower()
    country = request.args.get('country', '').lower()

    if category and category not in VALID_CATEGORIES:
        return _err("parameterInvalid", f"category must be one of: {', '.join(sorted(VALID_CATEGORIES))}")

    data = _load()
    srcs = list(data.get('sources', []))

    if category:
        srcs = [s for s in srcs if s.get('category', '') == category]
    if language:
        srcs = [s for s in srcs if s.get('language', '') == language]
    if country:
        srcs = [s for s in srcs if s.get('country', '') == country]

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

    full = [{
        "id": s["id"], "name": s["name"],
        "description": descriptions.get(s["id"], ""),
        "url": urls.get(s["id"], "https://example.com"),
        "category": s["category"], "language": s["language"], "country": s["country"]
    } for s in srcs]

    return jsonify({"status": "ok", "sources": full})

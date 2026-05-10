from flask import Blueprint, jsonify, request
import json
import os

football_bp = Blueprint('football', __name__)

_DATA = os.path.dirname(__file__) + '/mock_data'


def _load(filename):
    with open(f'{_DATA}/{filename}') as f:
        return json.load(f)


def _team_map():
    return {t['id']: t for t in _load('teams.json')['teams']}


def _league_map():
    return {l['id']: l for l in _load('leagues.json')['leagues']}


def _enrich_match(m, teams, leagues):
    ht = teams.get(m['home_team_id'], {})
    at = teams.get(m['away_team_id'], {})
    lg = leagues.get(m['league_id'], {})
    return {
        "id":     m['id'],
        "league": {"id": lg.get('id'), "name": lg.get('name'), "country": lg.get('country'), "season": m.get('season')},
        "round":  m.get('round'),
        "date":   m['date'],
        "status": m['status'],
        "home": {
            "id":     ht.get('id'),
            "name":   ht.get('name'),
            "short":  ht.get('short'),
            "venue":  ht.get('venue'),
            "goals":  m['goals']['home']
        },
        "away": {
            "id":     at.get('id'),
            "name":   at.get('name'),
            "short":  at.get('short'),
            "venue":  at.get('venue'),
            "goals":  m['goals']['away']
        },
        "score":   m['score'],
        "venue":   m.get('venue'),
        "referee": m.get('referee'),
        "events":  m.get('events', [])
    }


@football_bp.route('/leagues', methods=['GET'])
def leagues():
    data = _load('leagues.json')['leagues']
    country = request.args.get('country', '').lower()
    league_type = request.args.get('type', '').lower()

    if country:
        data = [l for l in data if l['country'].lower() == country]
    if league_type:
        data = [l for l in data if l['type'].lower() == league_type]

    return jsonify({"status": "ok", "results": len(data), "data": data})


@football_bp.route('/teams', methods=['GET'])
def teams():
    data = _load('teams.json')['teams']
    league_id = request.args.get('league', type=int)
    country = request.args.get('country', '').lower()
    search = request.args.get('search', '').lower()

    if league_id:
        data = [t for t in data if t['league_id'] == league_id]
    if country:
        data = [t for t in data if t['country'].lower() == country]
    if search:
        data = [t for t in data if search in t['name'].lower() or search in t['short'].lower()]

    return jsonify({"status": "ok", "results": len(data), "data": data})


@football_bp.route('/teams/<int:team_id>', methods=['GET'])
def team_detail(team_id):
    teams = _team_map()
    leagues = _league_map()
    team = teams.get(team_id)
    if not team:
        return jsonify({"status": "error", "message": f"Team {team_id} not found"}), 404
    league = leagues.get(team.get('league_id'), {})
    return jsonify({"status": "ok", "data": {**team, "league": {"id": league.get('id'), "name": league.get('name'), "country": league.get('country')}}})


@football_bp.route('/matches', methods=['GET'])
def matches():
    all_matches = _load('matches.json')['matches']
    teams = _team_map()
    leagues = _league_map()

    status_filter = request.args.get('status', '').lower()
    league_id = request.args.get('league', type=int)
    team_id = request.args.get('team', type=int)
    date_filter = request.args.get('date', '')
    from_date = request.args.get('from', '')
    to_date = request.args.get('to', '')

    LIVE_STATUSES = {'1h', '2h', 'ht', 'et', 'pen', 'bt', 'int'}
    FINISHED_STATUSES = {'ft', 'aet', 'pen'}
    UPCOMING_STATUSES = {'ns', 'pst'}

    filtered = all_matches

    if status_filter == 'live':
        filtered = [m for m in filtered if m['status']['short'].lower() in LIVE_STATUSES]
    elif status_filter == 'finished':
        filtered = [m for m in filtered if m['status']['short'].lower() in FINISHED_STATUSES]
    elif status_filter == 'upcoming':
        filtered = [m for m in filtered if m['status']['short'].lower() in UPCOMING_STATUSES]
    elif status_filter:
        filtered = [m for m in filtered if m['status']['short'].lower() == status_filter]

    if league_id:
        filtered = [m for m in filtered if m['league_id'] == league_id]

    if team_id:
        filtered = [m for m in filtered if m['home_team_id'] == team_id or m['away_team_id'] == team_id]

    if date_filter:
        filtered = [m for m in filtered if m['date'].startswith(date_filter)]

    if from_date:
        filtered = [m for m in filtered if m['date'] >= from_date]

    if to_date:
        filtered = [m for m in filtered if m['date'] <= to_date + 'T99:99:99Z']

    result = [_enrich_match(m, teams, leagues) for m in filtered]
    result.sort(key=lambda x: x['date'])

    return jsonify({"status": "ok", "results": len(result), "data": result})


@football_bp.route('/matches/<int:match_id>', methods=['GET'])
def match_detail(match_id):
    all_matches = _load('matches.json')['matches']
    teams = _team_map()
    leagues = _league_map()

    match = next((m for m in all_matches if m['id'] == match_id), None)
    if not match:
        return jsonify({"status": "error", "message": f"Match {match_id} not found"}), 404

    return jsonify({"status": "ok", "data": _enrich_match(match, teams, leagues)})


@football_bp.route('/standings', methods=['GET'])
def standings():
    league_id = request.args.get('league', type=int)
    if not league_id:
        return jsonify({"status": "error", "message": "league parameter is required"}), 400

    all_standings = _load('standings.json')['standings']
    leagues = _league_map()
    teams = _team_map()

    league_standing = all_standings.get(str(league_id))
    if not league_standing:
        return jsonify({"status": "error", "message": f"No standings found for league {league_id}"}), 404

    table = []
    for row in league_standing['table']:
        team = teams.get(row['team_id'], {})
        table.append({
            **row,
            "team": {"id": team.get('id'), "name": team.get('name'), "short": team.get('short'), "venue": team.get('venue')}
        })

    league = leagues.get(league_id, {})
    return jsonify({
        "status": "ok",
        "league": {"id": league.get('id'), "name": league.get('name'), "country": league.get('country'), "season": league_standing.get('season')},
        "matchday": league_standing.get('matchday'),
        "results": len(table),
        "data": table
    })


@football_bp.route('/top-scorers', methods=['GET'])
def top_scorers():
    league_id = request.args.get('league', type=int)
    if not league_id:
        return jsonify({"status": "error", "message": "league parameter is required"}), 400

    all_scorers = _load('top_scorers.json')['top_scorers']
    leagues = _league_map()
    teams = _team_map()

    scorers = all_scorers.get(str(league_id))
    if not scorers:
        return jsonify({"status": "error", "message": f"No top scorers data for league {league_id}"}), 404

    enriched = []
    for s in scorers:
        team = teams.get(s['team_id'], {})
        enriched.append({
            **s,
            "team": {"id": team.get('id'), "name": team.get('name'), "short": team.get('short')}
        })

    league = leagues.get(league_id, {})
    return jsonify({
        "status": "ok",
        "league": {"id": league.get('id'), "name": league.get('name'), "country": league.get('country')},
        "results": len(enriched),
        "data": enriched
    })


@football_bp.route('/players/search', methods=['GET'])
def player_search():
    name = request.args.get('name', '').lower()
    if not name or len(name) < 2:
        return jsonify({"status": "error", "message": "name parameter must be at least 2 characters"}), 400

    all_scorers = _load('top_scorers.json')['top_scorers']
    teams = _team_map()
    found = []

    seen = set()
    for league_id, scorers in all_scorers.items():
        for s in scorers:
            pid = s['player']['id']
            if pid in seen:
                continue
            if name in s['player']['name'].lower():
                seen.add(pid)
                team = teams.get(s['team_id'], {})
                found.append({
                    "player": s['player'],
                    "team": {"id": team.get('id'), "name": team.get('name'), "short": team.get('short')},
                    "league_id": int(league_id),
                    "goals": s['goals'],
                    "assists": s['assists'],
                    "appearances": s['appearances']
                })

    return jsonify({"status": "ok", "results": len(found), "data": found})

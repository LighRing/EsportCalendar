from datetime import datetime, timezone

def _safe_get(d, *path, default=None):
    cur = d
    for k in path:
        if cur is None:
            return default
        if isinstance(cur, dict):
            cur = cur.get(k)
        else:
            return default
    return cur if cur is not None else default

def _to_utc_iso(s):
    if not s or not isinstance(s, str):
        return None
    try:
        return (
            datetime.fromisoformat(s.replace("Z", "+00:00"))
            .astimezone(timezone.utc)
            .isoformat()
            .replace("+00:00", "Z")
        )
    except Exception:
        return None

# -------- LPDB --------
def map_lpdb_match(game_slug: str, raw: dict, club_name: str) -> dict:
    # On reste permissif sur les noms de champs
    pagename = _safe_get(raw, "pagename") or _safe_get(raw, "slug") or _safe_get(raw, "id") or "unknown"
    tournament = (_safe_get(raw, "tournament", "name")
                  or _safe_get(raw, "tournament")
                  or _safe_get(raw, "event", "name")
                  or _safe_get(raw, "event"))
    stage = _safe_get(raw, "stage") or _safe_get(raw, "round")
    bo = _safe_get(raw, "bestof") or _safe_get(raw, "bo") or _safe_get(raw, "format")
    start_raw = (_safe_get(raw, "date")
                 or _safe_get(raw, "start_time")
                 or _safe_get(raw, "scheduled_at")
                 or _safe_get(raw, "utcStartTime"))
    start_utc = _to_utc_iso(start_raw)

    # équipes (selon LPDB courant : opponent1 / opponent2)
    team1 = _safe_get(raw, "opponent1") or _safe_get(raw, "team1")
    team2 = _safe_get(raw, "opponent2") or _safe_get(raw, "team2")
    # on veut l’adversaire du club
    opponent = team2 if team1 == club_name else (team1 if team2 == club_name else (team2 or team1))

    # streams (souvent structuré mais variable)
    streams = _safe_get(raw, "streams") or {}
    if not isinstance(streams, dict):
        streams = {}
    # fallback simple si champ unique
    single_stream = _safe_get(raw, "stream")
    twitch = list({*(streams.get("twitch") or [])})
    youtube = list({*(streams.get("youtube") or [])})
    if isinstance(single_stream, str):
        if "twitch.tv" in single_stream:
            twitch.append(single_stream)
        if "youtube.com" in single_stream or "youtu.be" in single_stream:
            youtube.append(single_stream)
    streams = {"twitch": list(dict.fromkeys(twitch)), "youtube": list(dict.fromkeys(youtube))}

    source_url = _safe_get(raw, "url") or _safe_get(raw, "match_page") or _safe_get(raw, "page")

    return {
        "id": f"{game_slug}-{pagename}",
        "game": game_slug.upper(),
        "tournament": tournament,
        "stage": stage,
        "bo": bo,
        "team": club_name,
        "opponent": opponent,
        "start_time_utc": start_utc,
        "streams": streams,
        "sources": [{"site": "Liquipedia", "url": source_url}],
    }

# -------- MediaWiki (Cargo) --------
def _streams_from_mediawiki(raw):
    s = (_safe_get(raw, "m.stream") or _safe_get(raw, "stream") or
         _safe_get(raw, "MS.Stream"))
    twitch, youtube = [], []
    if isinstance(s, str):
        parts = [p.strip() for p in s.replace(",", " ").split() if p.strip()]
        for url in parts:
            if "twitch.tv" in url: twitch.append(url)
            if "youtube.com" in url or "youtu.be" in url: youtube.append(url)
    return {"twitch": list(dict.fromkeys(twitch)), "youtube": list(dict.fromkeys(youtube))}

def map_mediawiki_match(game_slug: str, row: dict, club_name: str) -> dict:
    title_obj = row.get("title") if isinstance(row, dict) else None
    def getf(field):
        return (row.get(field) if isinstance(row, dict) and field in row
                else (title_obj.get(field) if isinstance(title_obj, dict) else None))

    pagename = getf("m.pagename") or getf("Page") or getf("pagename")
    start_raw = (getf("m.utcStartTime") or getf("utcStartTime")
                 or getf("MS.DateTime_UTC") or getf("DateTime_UTC"))
    start_utc = _to_utc_iso(start_raw)

    opp1 = getf("m.opponent1") or getf("MS.Team1")
    opp2 = getf("m.opponent2") or getf("MS.Team2")
    opponent = opp2 if opp1 == club_name else (opp1 if opp2 == club_name else (opp2 or opp1))

    tournament = getf("m.tournament") or getf("MS.Tournament")
    bo = getf("m.bestof") or getf("MS.BestOf")
    streams = _streams_from_mediawiki(row)

    return {
        "id": f"{game_slug}-{pagename or 'unknown'}",
        "game": game_slug.upper(),
        "tournament": tournament,
        "stage": None,
        "bo": bo,
        "team": club_name,
        "opponent": opponent,
        "start_time_utc": start_utc,
        "streams": streams,
        "sources": [{"site": "Liquipedia", "url": f"https://liquipedia.net/{pagename}" if pagename else None}],
    }

# -------- Détection & normalisation --------
def normalize_response(game_slug: str, api_payload, club_name: str):
    if not api_payload:
        return []

    # LPDB: { "matches": [...] } ou { "result": [...] } ou liste
    if isinstance(api_payload, dict):
        lpdb_items = (_safe_get(api_payload, "matches")
                      or _safe_get(api_payload, "result")
                      or _safe_get(api_payload, "results"))
        if isinstance(lpdb_items, list):
            return [map_lpdb_match(game_slug, it, club_name) for it in lpdb_items]

        # MediaWiki Cargo: { "cargoquery": [ { title: {...} }, ... ] }
        mw_items = _safe_get(api_payload, "cargoquery")
        if isinstance(mw_items, list):
            return [map_mediawiki_match(game_slug, it, club_name) for it in mw_items]

    if isinstance(api_payload, list):
        # Certains LPDB renvoient directement une liste
        return [map_lpdb_match(game_slug, it, club_name) for it in api_payload]

    return []

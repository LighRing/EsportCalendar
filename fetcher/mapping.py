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
    """Normalise une date/heure en ISO8601 UTC se terminant par 'Z'. Renvoie None si invalide."""
    if not s or not isinstance(s, str):
        return None
    try:
        # Supporte "YYYY-MM-DDTHH:MM:SSZ" ou "...+00:00"
        return (
            datetime.fromisoformat(s.replace("Z", "+00:00"))
            .astimezone(timezone.utc)
            .isoformat()
            .replace("+00:00", "Z")
        )
    except Exception:
        # Certaines réponses MediaWiki peuvent donner un format custom → on laisse None
        return None

def _streams_from_lpdb(raw):
    """
    Essaie d'extraire des liens de stream depuis un objet LPDB.
    Les champs exacts varient selon le wiki; on reste défensif.
    """
    streams = _safe_get(raw, "streams", default={}) or {}
    twitch = []
    youtube = []

    # Cas 1: format déjà structuré
    if isinstance(streams, dict):
        twitch = streams.get("twitch") or []
        youtube = streams.get("youtube") or []

    # Cas 2: certaines implémentations mettent un tableau 'links' ou un champ 'stream'
    links = _safe_get(raw, "links") or []
    if isinstance(links, list):
        for url in links:
            if isinstance(url, str):
                if "twitch.tv" in url:
                    twitch.append(url)
                if "youtube.com" in url or "youtu.be" in url:
                    youtube.append(url)

    single_stream = _safe_get(raw, "stream")  # parfois une seule URL
    if isinstance(single_stream, str):
        if "twitch.tv" in single_stream:
            twitch.append(single_stream)
        if "youtube.com" in single_stream or "youtu.be" in single_stream:
            youtube.append(single_stream)

    # Nettoyage doublons
    twitch = list(dict.fromkeys(twitch))
    youtube = list(dict.fromkeys(youtube))
    return {"twitch": twitch, "youtube": youtube}

def _streams_from_mediawiki(raw):
    """
    Pour MediaWiki (cargoquery), on voit souvent un champ 'm.stream' avec une URL ou un texte.
    """
    s = (
        _safe_get(raw, "m.stream") or
        _safe_get(raw, "stream")
    )
    twitch, youtube = [], []
    if isinstance(s, str):
        # le champ peut contenir plusieurs liens séparés, on split prudemment
        parts = [p.strip() for p in s.replace(",", " ").split() if p.strip()]
        for url in parts:
            if "twitch.tv" in url:
                twitch.append(url)
            if "youtube.com" in url or "youtu.be" in url:
                youtube.append(url)
    return {"twitch": list(dict.fromkeys(twitch)), "youtube": list(dict.fromkeys(youtube))}

def map_lpdb_match(game_slug: str, raw: dict, club_name: str) -> dict:
    """
    Mapping pour un objet renvoyé par LPDB.
    Les noms de champs peuvent varier selon la version; on reste large.
    """
    match_id = (
        _safe_get(raw, "id")
        or _safe_get(raw, "slug")
        or _safe_get(raw, "match_id")
        or _safe_get(raw, "pagename")
        or "unknown"
    )
    tournament = (
        _safe_get(raw, "tournament", "name")
        or _safe_get(raw, "event", "name")
        or _safe_get(raw, "tournament")
        or _safe_get(raw, "event")
    )
    stage = _safe_get(raw, "stage") or _safe_get(raw, "round")
    bo = _safe_get(raw, "bo") or _safe_get(raw, "bestof") or _safe_get(raw, "format")
    start_raw = (
        _safe_get("m.utcStartTime") 
        or _safe_get("utcStartTime") 
        or _safe_get("MS.DateTime_UTC") 
        or _safe_get("DateTime_UTC")
    )
    start_utc = _to_utc_iso(start_raw)

    # Opposant: parfois dans opponents[], parfois team1/team2, etc.
    opponent = (
        _safe_get(raw, "opponent")
        or _safe_get(raw, "opponent", "name")
        or _safe_get(raw, "opponents", 1, "name")  # l'autre équipe
        or _safe_get(raw, "team2")
        or _safe_get(raw, "blue")
        or _safe_get(raw, "red")
    )

    streams = _streams_from_lpdb(raw)

    source_url = (
        _safe_get(raw, "url")
        or _safe_get(raw, "match_page")
        or _safe_get(raw, "page")
    )

    return {
        "id": f"{game_slug}-{match_id}",
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

def map_mediawiki_match(game_slug: str, row: dict, club_name: str) -> dict:
    """
    Mapping pour une ligne cargoquery (MediaWiki). La réponse typique est:
    { 'cargoquery': [ { 'title': { 'm.pagename': ..., 'm.utcStartTime': ... } } ] }
    mais comme on a utilisé fields aliasés, on peut voir directement 'm.xxx' au premier niveau.
    On accepte les deux.
    """
    # Support des deux structures : plate avec clés 'm.xxx', ou imbriquée sous 'title'
    title_obj = row.get("title") if isinstance(row, dict) else None

    def getf(field):
        # cherche d'abord au premier niveau, sinon dans title
        return (
            row.get(field)
            if isinstance(row, dict) and field in row
            else (title_obj.get(field) if isinstance(title_obj, dict) else None)
        )

    pagename = getf("m.pagename") or getf("pagename")
    start_raw = getf("m.utcStartTime") or getf("utcStartTime")
    start_utc = _to_utc_iso(start_raw)

    # équipes selon nos fields (opponent1/opponent2)
    opp1 = getf("m.opponent1") or getf("opponent1")
    opp2 = getf("m.opponent2") or getf("opponent2")
    # l'adversaire = celui qui n'est pas notre club, si on peut deviner
    opponent = opp2 if opp1 == club_name else (opp1 if opp2 == club_name else (opp2 or opp1))

    tournament = getf("m.tournament") or getf("tournament")
    bo = getf("m.bestof") or getf("bestof")
    streams = _streams_from_mediawiki(row)

    return {
        "id": f"{game_slug}-{pagename or 'unknown'}",
        "game": game_slug.upper(),
        "tournament": tournament,
        "stage": None,  # souvent non exposé via cargoquery; à enrichir si dispo
        "bo": bo,
        "team": club_name,
        "opponent": opponent,
        "start_time_utc": start_utc,
        "streams": streams,
        "sources": [{"site": "Liquipedia", "url": f"https://liquipedia.net/{pagename}" if pagename else None}],
    }

def normalize_response(game_slug: str, api_payload, club_name: str):
    """
    Détecte automatiquement si la réponse vient de LPDB ou de MediaWiki
    puis mappe vers une liste de matchs normalisés.
    """
    if not api_payload:
        return []

    # Heuristique: LPDB renvoie souvent { "result": [ ... ] } ou { "matches": [ ... ] }
    if isinstance(api_payload, dict):
        lpdb_items = (
            _safe_get(api_payload, "result")
            or _safe_get(api_payload, "results")
            or _safe_get(api_payload, "matches")
        )
        if isinstance(lpdb_items, list):
            return [map_lpdb_match(game_slug, it, club_name) for it in lpdb_items]

        # MediaWiki cargoquery renvoie { "cargoquery": [ { title: {...} }, ... ] }
        mw_items = _safe_get(api_payload, "cargoquery")
        if isinstance(mw_items, list):
            return [map_mediawiki_match(game_slug, it, club_name) for it in mw_items]

    # Dernier recours: si c'est déjà une liste (peut arriver côté LPDB)
    if isinstance(api_payload, list):
        return [map_lpdb_match(game_slug, it, club_name) for it in api_payload]

    return []

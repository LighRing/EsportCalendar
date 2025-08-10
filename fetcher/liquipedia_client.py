import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()

# ---- Config générale ----
LPDB_BASE = "https://api.liquipedia.net/api"
MW_BASE = "https://liquipedia.net"

USER_AGENT = os.getenv(
    "LIQUIPEDIA_USER_AGENT",
    "EsportsCalendarExtension/0.1 (contact: thomasballini34@gmail.com)"
)
API_KEY = os.getenv("LIQUIPEDIA_API_KEY")
RATE_SECONDS = 2

GAME_TO_WIKI = {
    "valorant": "valorant",
    "league_of_legends": "leagueoflegends",
    "rocket_league": "rocketleague",
    "counter_strike_2": "counterstrike"
}

class LiquipediaClient:
    def __init__(self):
        self.s = requests.Session()
        self.s.headers.update({
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
            "Accept-Encoding": "gzip"
        })

    def upcoming_matches_lpdb(self, wiki: str, team_name: str):
        if not API_KEY:
            raise RuntimeError("LPDB API key missing")

        time.sleep(RATE_SECONDS)
        url = f"{LPDB_BASE}/v1/match"
        params = {
            "wiki": wiki,
            "team": team_name,
            "status": "upcoming",
            "limit": 200
        }
        headers = {"Authorization": f"Bearer {API_KEY}"}
        r = self.s.get(url, params=params, headers=headers, timeout=25)
        r.raise_for_status()
        return r.json()

    def upcoming_matches_mediawiki(self, wiki: str, team_name: str):
        def _cargo_query(params):
            time.sleep(RATE_SECONDS)
            url = f"{MW_BASE}/{wiki}/api.php"
            r = self.s.get(url, params=params, timeout=25)
            r.raise_for_status()
            return r.json()

        # Tentative match2
        params_match2 = {
            "action": "cargoquery",
            "tables": "match2 = m, match2opponent = o",
            "fields": "m.pagename, m.utcStartTime, m.opponent1, m.opponent2, m.stream, m.bestof, m.tournament, o.name",
            "where": f"(m.opponent1='{team_name}' OR m.opponent2='{team_name}')",
            "join_on": "o._rowID = m._rowID",
            "order_by": "m.utcStartTime ASC",
            "limit": "50",
            "format": "json"
        }
        try:
            data = _cargo_query(params_match2)
            if isinstance(data, dict) and data.get("cargoquery"):
                return data
        except requests.HTTPError:
            pass

        # Fallback MatchSchedule
        params_ms = {
            "action": "cargoquery",
            "tables": "MatchSchedule = MS, MatchScheduleGame = MSG",
            "fields": "MS.Page, MS.DateTime_UTC, MS.Team1, MS.Team2, MS.Stream, MS.BestOf, MS.Tournament",
            "where": f"(MS.Team1='{team_name}' OR MS.Team2='{team_name}')",
            "join_on": "MSG._rowID = MS._rowID",
            "order_by": "MS.DateTime_UTC ASC",
            "limit": "50",
            "format": "json"
        }
        return _cargo_query(params_ms)

    def upcoming_matches(self, game_slug: str, team_name: str):
        wiki = GAME_TO_WIKI.get(game_slug)
        if not wiki:
            raise ValueError(f"Unknown game slug: {game_slug}")

        try:
            if API_KEY:
                return self.upcoming_matches_lpdb(wiki, team_name)
            return self.upcoming_matches_mediawiki(wiki, team_name)
        except requests.HTTPError as e:
            if API_KEY:
                try:
                    return self.upcoming_matches_mediawiki(wiki, team_name)
                except Exception:
                    raise e
            raise

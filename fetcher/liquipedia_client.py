import os
import time
import json
import requests
from dotenv import load_dotenv

load_dotenv()

LPDB_BASE = "https://api.liquipedia.net/api/v1"
MW_BASE = "https://liquipedia.net"
RATE_SECONDS = 2

GAME_TO_WIKI = {
    "valorant": "valorant",
    "league_of_legends": "leagueoflegends",
    "rocket_league": "rocketleague",
    "counter_strike_2": "counterstrike",
}

DEBUG_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "public", "data"))
SAMPLES_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "samples"))

def _ua():
    ua = os.getenv("LIQUIPEDIA_USER_AGENT", "").strip()
    return ua or "EsportsScheduleExtension/0.1 (contact: you@example.com)"

class LiquipediaClient:
    def __init__(self):
        self.api_key = os.getenv("LIQUIPEDIA_API_KEY", "").strip()
        self.demo_mode = os.getenv("DEMO_MODE", "0").strip() == "1"
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": _ua(),
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
        })

    def _sleep(self):
        time.sleep(RATE_SECONDS)

    # ---------------- LPDB ----------------
    def _upcoming_matches_lpdb(self, wiki: str, team_name: str):
        self._sleep()
        url = f"{LPDB_BASE}/match"
        params = {
            "wiki": wiki,
            "conditions": f"(opponent1='{team_name}' OR opponent2='{team_name}')",
            "order": "date ASC",
            "limit": 100,
        }
        headers = {"Authorization": f"Bearer {self.api_key}"}
        r = self.session.get(url, params=params, headers=headers, timeout=25)
        r.raise_for_status()
        return r.json()

    # ------------- DEMO MODE -------------
    def _demo_payload_for_wiki(self, wiki: str):
        # Pour l’instant, on ne fournit qu’un exemple Valorant
        if wiki == "valorant":
            path = os.path.join(SAMPLES_DIR, "valorant_demo_lpdb.json")
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return data
            except Exception as e:
                print(f"[DEMO] Impossible de charger {path}: {e}")
        return {"matches": []}

    # ------------- Méthode publique -------------
    def upcoming_matches(self, game_slug: str, team_name: str):
        wiki = GAME_TO_WIKI.get(game_slug)
        if not wiki:
            raise ValueError(f"Jeu inconnu: {game_slug}")

        # 1) Si DEMO_MODE → renvoie l’exemple local (pour tester l’affichage)
        if self.demo_mode:
            print(f"[DEMO] Mode démo actif pour {wiki}.")
            return self._demo_payload_for_wiki(wiki)

        # 2) Si on a une clé → LPDB (recommandé et nécessaire sur Valorant)
        if self.api_key:
            return self._upcoming_matches_lpdb(wiki, team_name)

        # 3) Sinon, pas de Cargo pour Valorant (désactivé) -> on informe clairement
        if wiki == "valorant":
            raise RuntimeError(
                "Le wiki Valorant n'autorise pas Cargo API publiquement. "
                "Active DEMO_MODE=1 pour tester ou attends ta clé LPDB."
            )

        # 4) Pour d’autres wikis, on pourrait tenter Cargo ici s’il est actif.
        #    Mais comme tu veux surtout Valorant, on s’arrête là pour rester propre vis-à-vis des règles.
        return {"matches": []}

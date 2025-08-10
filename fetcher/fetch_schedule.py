import os
import json
from datetime import datetime, timezone
from dotenv import load_dotenv

from liquipedia_client import LiquipediaClient
from mapping import normalize_response

load_dotenv()

OUT_PATH = os.path.join(os.path.dirname(__file__), "..", "public", "data", "schedule.json")
CLUB_NAME = os.getenv("CLUB_NAME", "Team Vitality")
GAMES = [g.strip() for g in os.getenv("GAMES", "valorant").split(",") if g.strip()]

def is_upcoming(m):
    ts = m.get("start_time_utc")
    if not ts:
        return True
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return dt >= datetime.now(timezone.utc)
    except Exception:
        return True

def run():
    client = LiquipediaClient()
    all_matches = []

    # Noms acceptés pour le club (pour filtrer après bulk VALORANT)
    club_aliases = {os.getenv("CLUB_NAME", "Team Vitality"), "Team Vitality", "Vitality"}

    for game in GAMES:
        print(f"[INFO] Query jeu={game} club={CLUB_NAME}")
        try:
            raw = client.upcoming_matches(game, CLUB_NAME)
            matches = normalize_response(game, raw, CLUB_NAME)

            # Filtre Python post-traitement : si opponent1/opponent2 présents dans le payload mappé
            filtered = []
            for m in matches:
                opp = (m.get("opponent") or "").strip()
                me = (m.get("team") or "").strip()
                # garde si l'un des deux champs contient une des variantes (utile après bulk)
                if any(alias.lower() in (opp.lower() + " " + me.lower()) for alias in club_aliases):
                    filtered.append(m)

            # si rien filtré, on garde quand même la liste originale (cas non-valorant)
            if filtered:
                matches = filtered

            # filtre date
            print(f"[INFO]   → {len(matches)} match(es) (avant filtre date)")
            matches = [m for m in matches if is_upcoming(m)]
            print(f"[INFO]   → {len(matches)} match(es) (après filtre date)")
            all_matches.extend(matches)
        except Exception as e:
            print(f"[WARN] {game}: {e}")

if __name__ == "__main__":
    run()

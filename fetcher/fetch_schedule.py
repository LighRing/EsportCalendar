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

            # Filtre Python post-traitement (utile après bulk sans filtre d'équipe)
            filtered = []
            for m in matches:
                opp = (m.get("opponent") or "").strip()
                me = (m.get("team") or "").strip()
                if any(alias.lower() in (opp.lower() + " " + me.lower()) for alias in club_aliases):
                    filtered.append(m)
            if filtered:
                matches = filtered

            print(f"[INFO]   → {len(matches)} match(es) (avant filtre date)")
            matches = [m for m in matches if is_upcoming(m)]
            print(f"[INFO]   → {len(matches)} match(es) (après filtre date)")
            all_matches.extend(matches)
        except Exception as e:
            print(f"[WARN] {game}: {e}")

    # ---------- ÉCRITURE DU FICHIER (manquait !) ----------
    payload = {
        "club": CLUB_NAME,
        "updated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "matches": sorted(
            all_matches,
            key=lambda x: x.get("start_time_utc") or "9999-12-31T00:00:00Z"
        ),
    }

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"[OK] Wrote {OUT_PATH} with {len(all_matches)} matches")

if __name__ == "__main__":
    run()

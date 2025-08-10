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

    for game in GAMES:
        try:
            raw = client.upcoming_matches(game, CLUB_NAME)
            matches = normalize_response(game, raw, CLUB_NAME)
            all_matches.extend(matches)
        except Exception as e:
            print(f"[WARN] {game}: {e}")

    all_matches = [m for m in all_matches if is_upcoming(m)]

    payload = {
        "club": CLUB_NAME,
        "updated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "matches": sorted(all_matches, key=lambda x: x.get("start_time_utc") or "9999-12-31T00:00:00Z")
    }

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"[OK] Wrote {OUT_PATH} with {len(all_matches)} matches")

if __name__ == "__main__":
    run()

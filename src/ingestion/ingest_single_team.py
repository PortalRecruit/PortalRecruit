import os
import sys
import argparse
import time
import re
import chromadb

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from src.ingestion.synergy_client import SynergyClient
from config.settings import SYNERGY_API_KEY


def normalize(text: str) -> str:
    """Normalize team names for reliable matching."""
    return re.sub(r'[^a-z0-9]', '', text.lower())


TAMU_ALIASES = {
    "texasam",
    "texasamaggies",
    "texasamuniversity",
    "texasamaggiesmens",
}


class SingleTeamIngester:
    def __init__(self):
        self.client = SynergyClient()

        db_path = os.path.join(os.getcwd(), "data/vector_db")
        os.makedirs(db_path, exist_ok=True)

        self.chroma_client = chromadb.PersistentClient(path=db_path)
        self.meta_collection = self.chroma_client.get_or_create_collection(
            name="skout_game_metadata"
        )

    # --------------------------------------------------
    # SEASONS
    # --------------------------------------------------
    def get_recent_seasons(self, years_back=6):
        print("🔍 Fetching available seasons...")
        response = self.client.get_seasons(league_code="ncaamb")

        seasons = []
        for wrapper in response.get("data", []):
            season = wrapper.get("data", wrapper)
            seasons.append({
                "id": season["id"],
                "name": season.get("name", ""),
                "year": season.get("year")
            })

        if not seasons:
            raise RuntimeError("No seasons returned by Synergy API")

        # Sort newest → oldest
        seasons.sort(key=lambda s: str(s["name"]), reverse=True)
        selected = seasons[:years_back]

        print("✅ Using seasons:")
        for s in selected:
            print(f"   - {s['name']} ({s['id']})")

        return selected

    # --------------------------------------------------
    # TEAM LOOKUP (FIXED)
    # --------------------------------------------------
        def find_texas_am_team_id(self):
        print("🔍 Resolving Texas A&M team ID...")

        skip = 0
        take = 500

        normalized_target = normalize("texasamaggies")

        while True:
            response = self.client._get(
                "/ncaamb/teams",
                params={"take": take, "skip": skip}
            )

            if not response:
                break

            team_wrappers = response.get("data", [])
            if not team_wrappers:
                break

            for wrapper in team_wrappers:
                team = wrapper.get("data", wrapper)

                # The Synergy docs show these fields are valid:
                # id, name, market, alias (if present) :contentReference[oaicite:1]{index=1}
                name = normalize(team.get("name", ""))
                market = normalize(team.get("market", ""))
                alias = normalize(team.get("alias", ""))

                combined = f"{market}{name}{alias}"

                if normalized_target in combined:
                    print(f"✅ Found Texas A&M team: {team.get('market')} {team.get('name')} ({team['id']})")
                    return team["id"]

            if len(team_wrappers) < take:
                break

            skip += take
            time.sleep(0.2)

        print("❌ Texas A&M team not found in Synergy team list.")
        return None

    # --------------------------------------------------
    # INGESTION
    # --------------------------------------------------
    def ingest_team_history(self, years_back=6):
        seasons = self.get_recent_seasons(years_back)
        team_id = self.find_texas_am_team_id()

        total_games = 0

        for season in seasons:
            season_id = season["id"]
            print(f"\n📅 Ingesting {season['name']}...")

            skip = 0
            take = 50

            while True:
                response = self.client._get(
                    "/ncaamb/games",
                    params={
                        "seasonId": season_id,
                        "teamId": team_id,
                        "take": take,
                        "skip": skip,
                    }
                )

                games = response.get("data", [])
                if not games:
                    break

                for wrapper in games:
                    game = wrapper.get("data", wrapper)
                    self.save_game_metadata(game, season_id)
                    total_games += 1

                if len(games) < take:
                    break

                skip += take
                time.sleep(0.2)

        print(f"\n🎉 Ingestion Complete: {total_games} Texas A&M games indexed")

    # --------------------------------------------------
    # STORAGE
    # --------------------------------------------------
    def save_game_metadata(self, game_data, season_id):
        game_id = str(game_data.get("id"))

        home = game_data.get("homeTeam", {}).get("name", "Unknown")
        away = game_data.get("awayTeam", {}).get("name", "Unknown")
        date = game_data.get("date") or game_data.get("scheduled")

        description = f"{home} vs {away} on {date}"

        self.meta_collection.add(
            ids=[game_id],
            documents=[description],
            metadatas=[{
                "season_id": season_id,
                "game_date": date,
                "home_team": home,
                "away_team": away,
                "status": game_data.get("status"),
                "tags": "Texas A&M"
            }]
        )


# --------------------------------------------------
# CLI
# --------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="SKOUT Single Team Ingestion – Texas A&M Men's Basketball"
    )
    parser.add_argument("--history", type=int, default=6)
    args = parser.parse_args()

    ingester = SingleTeamIngester()
    ingester.ingest_team_history(args.history)

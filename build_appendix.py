#!/usr/bin/env python
"""Bonus appendix (optional, per the assignment FAQ): cross-check our
All-Star dataset against the actual All-Star Game box score
(/allstar/{year}-allstar-game.shtml) for 2024-2026, and report/save any
player who appeared in the game but wasn't [AS]-tagged on their team page.

Cache-first like scrape.py; reads the built CSV like build.py. Writes
data/output/allstar_roster_gaps_appendix.csv (empty if no gaps found).
"""
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src import allstar_parser
from src.http_client import CachingClient

DATA_RAW = Path(__file__).parent / "data" / "raw" / "allstar"
CSV_PATH = Path(__file__).parent / "data" / "output" / "all_stars_2024_2026.csv"
APPENDIX_PATH = Path(__file__).parent / "data" / "output" / "allstar_roster_gaps_appendix.csv"
SEASONS = [2024, 2025, 2026]


def main():
    client = CachingClient(min_delay=3.0)

    csv_rows = list(csv.DictReader(CSV_PATH.open(encoding="utf-8")))
    players_by_season = {}
    for season in SEASONS:
        players_by_season[season] = {
            r["player_id"] for r in csv_rows if r["season_id"] == str(season)
        }

    gaps = []
    for season in SEASONS:
        url = f"https://www.baseball-reference.com/allstar/{season}-allstar-game.shtml"
        cache_path = DATA_RAW / f"{season}.shtml"
        try:
            html, _ = client.fetch(url, cache_path)
        except Exception as exc:  # noqa: BLE001 -- report and continue
            print(f"{season}: could not fetch box score ({exc}), skipping")
            continue

        participants = allstar_parser.parse_allstar_game_participants(html)
        known = players_by_season[season]
        missing = {pid: name for pid, name in participants.items() if pid not in known}

        print(f"{season}: {len(participants)} players appeared in the game, "
              f"{len(missing)} not found in our [AS]-tagged dataset")
        for pid, name in sorted(missing.items(), key=lambda kv: kv[1]):
            print(f"    GAP: {name} ({pid})")
            gaps.append({"season_id": season, "player_id": pid, "full_name": name})

    APPENDIX_PATH.parent.mkdir(parents=True, exist_ok=True)
    with APPENDIX_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["season_id", "player_id", "full_name"])
        writer.writeheader()
        writer.writerows(gaps)

    print(f"\nWrote {len(gaps)} gap row(s) to {APPENDIX_PATH}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python
"""Scrape (cache-first) Baseball-Reference + The Show Ratings pages needed
for the All-Star aggregator.

Order: league pages (URL discovery) -> Show top-100 -> team pages -> player
pages (deduped across all team-seasons). Every page is cached under
data/raw/ and never re-fetched unless --force is passed. See README.md for
usage and expected runtime.
"""
import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src import br_parser, show_parser
from src.http_client import CachingClient, FetchError

DATA_RAW = Path(__file__).parent / "data" / "raw"
SHOW_TOP100_URL = "https://www.theshowratings.com/lists/top-100-players"
DEFAULT_SEASONS = [2024, 2025, 2026]


def league_page_path(season):
    return DATA_RAW / "leagues" / f"{season}.shtml"


def team_page_path(team_id, season):
    return DATA_RAW / "teams" / f"{team_id}_{season}.shtml"


def player_page_path(player_id):
    return DATA_RAW / "players" / f"{player_id}.shtml"


def show_page_path():
    return DATA_RAW / "the_show" / "top100.html"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true",
                         help="re-fetch every page even if already cached")
    parser.add_argument("--seasons", type=int, nargs="+", default=DEFAULT_SEASONS)
    parser.add_argument("--min-delay", type=float, default=3.0,
                         help="minimum seconds between live requests (BR robots.txt crawl-delay is 3s)")
    args = parser.parse_args()

    client = CachingClient(min_delay=args.min_delay, force=args.force)
    started = time.time()

    print(f"[1/3] Show top-100 ({SHOW_TOP100_URL})")
    client.fetch(SHOW_TOP100_URL, show_page_path())

    print(f"[2/3] Discovering team URLs for seasons {args.seasons} via league pages")
    team_targets = []  # (team_id, season, url)
    for season in args.seasons:
        url = f"https://www.baseball-reference.com/leagues/majors/{season}.shtml"
        html, _ = client.fetch(url, league_page_path(season))
        teams = br_parser.discover_season_team_urls(html, season)
        print(f"    {season}: {len(teams)} teams discovered")
        for team_id, team_url in teams:
            team_targets.append((team_id, season, team_url))

    print(f"[3/3] Fetching {len(team_targets)} team pages, then unique All-Star player pages")
    player_ids_needed = set()
    failures = []
    for i, (team_id, season, url) in enumerate(team_targets, 1):
        try:
            html, _ = client.fetch(url, team_page_path(team_id, season))
        except FetchError as exc:
            print(f"    FAILED {team_id} {season}: {exc}")
            failures.append((team_id, season))
            continue
        parsed = br_parser.parse_team_page(html)
        for row in parsed["batting_rows"] + parsed["pitching_rows"]:
            player_ids_needed.add(row["player_id"])
        if i % 10 == 0 or i == len(team_targets):
            print(f"    team pages: {i}/{len(team_targets)} "
                  f"(live={client.live_request_count} cached={client.cache_hit_count})")

    print(f"    {len(player_ids_needed)} unique All-Star player pages to fetch")
    for i, player_id in enumerate(sorted(player_ids_needed), 1):
        letter = player_id[0]
        url = f"https://www.baseball-reference.com/players/{letter}/{player_id}.shtml"
        try:
            client.fetch(url, player_page_path(player_id))
        except FetchError as exc:
            print(f"    FAILED player {player_id}: {exc}")
            failures.append(("player", player_id))
        if i % 20 == 0 or i == len(player_ids_needed):
            print(f"    player pages: {i}/{len(player_ids_needed)} "
                  f"(live={client.live_request_count} cached={client.cache_hit_count})")

    elapsed = time.time() - started
    print(f"\nDone in {elapsed:.1f}s. live_requests={client.live_request_count} "
          f"cache_hits={client.cache_hit_count} failures={len(failures)}")
    if failures:
        print("Failed to fetch (re-run scrape.py to retry, cache is resumable):")
        for f in failures:
            print(f"  {f}")


if __name__ == "__main__":
    main()

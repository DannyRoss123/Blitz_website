#!/usr/bin/env python
"""Validation checks for data/output/all_stars_2024_2026.csv, per the
assignment's required checks. Run standalone (`python validate.py`) or
imported from build.py, which runs it automatically after every build.
"""
import csv
import sys
from collections import Counter, defaultdict
from pathlib import Path

CSV_PATH = Path(__file__).parent / "data" / "output" / "all_stars_2024_2026.csv"

# Known-correct spot checks: (player_id, season_id, stat_type) -> {column: expected}
# Values manually verified against live baseball-reference.com pages.
SPOT_CHECKS = {
    ("judgeaa01", "2024", "batting"): {"bat_HR": "58", "team_id": "NYY"},
    ("ohtansh01", "2024", "batting"): {"bat_HR": "54", "bat_OPS": "1.036", "team_id": "LAD"},
    ("skenepa01", "2024", "pitching"): {"pit_W": "11", "pit_ERA": "1.96", "team_id": "PIT"},
}


def load_rows():
    with CSV_PATH.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def validate(rows) -> bool:
    ok = True

    # 1. No duplicate primary keys.
    key_counts = Counter(
        (r["player_id"], r["season_id"], r["stat_type"], r["team_id"]) for r in rows
    )
    dup_keys = [k for k, c in key_counts.items() if c > 1]
    if dup_keys:
        ok = False
        print(f"FAIL: {len(dup_keys)} duplicate (player_id, season_id, stat_type, team_id) keys, e.g. {dup_keys[:5]}")
    else:
        print("PASS: no duplicate (player_id, season_id, stat_type, team_id) primary keys")

    # 2. No null IDs.
    null_id_rows = [r for r in rows if not r.get("player_id") or not r.get("team_id") or not r.get("season_id")]
    if null_id_rows:
        ok = False
        print(f"FAIL: {len(null_id_rows)} row(s) with a null player_id/team_id/season_id")
    else:
        print("PASS: no null player_id/team_id/season_id")

    # 3. Row + unique-player counts per season (reported, not pass/fail --
    #    row count includes two-way-player and traded-player splits, so it
    #    legitimately runs above the ~64-68-unique-All-Stars guidance).
    rows_by_season = Counter(r["season_id"] for r in rows)
    players_by_season = defaultdict(set)
    for r in rows:
        players_by_season[r["season_id"]].add(r["player_id"])
    print("All-Star counts per season (rows include multi-row players like two-way/traded):")
    for season in sorted(rows_by_season):
        print(f"  {season}: {rows_by_season[season]} rows, {len(players_by_season[season])} unique players")

    unique_players = {r["player_id"] for r in rows}
    print(f"Total: {len(rows)} rows, {len(unique_players)} unique players across 2024-2026")

    show_rows = [r for r in rows if r.get("is_show_top100") == "True"]
    show_players = {r["player_id"] for r in show_rows}
    print(f"Show top-100 matched: {len(show_players)} unique players ({len(show_rows)} rows)")

    # 4. Spot checks against manually verified BR values.
    by_key = {(r["player_id"], r["season_id"], r["stat_type"]): r for r in rows}
    for key, expected in SPOT_CHECKS.items():
        row = by_key.get(key)
        if row is None:
            ok = False
            print(f"FAIL: spot check {key} not found in output")
            continue
        mismatches = {c: (row.get(c), v) for c, v in expected.items() if row.get(c) != v}
        if mismatches:
            ok = False
            print(f"FAIL: spot check {key} mismatches: {mismatches}")
        else:
            print(f"PASS: spot check {key} matches expected values")

    return ok


if __name__ == "__main__":
    sys.exit(0 if validate(load_rows()) else 1)

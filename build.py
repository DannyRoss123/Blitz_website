#!/usr/bin/env python
"""Parse cached Baseball-Reference + Show Ratings HTML into
data/output/all_stars_2024_2026.csv. No network calls -- reads only from
data/raw/. Run scrape.py first (or use the committed cache).
"""
import csv
import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src import br_parser, models, show_parser

DATA_RAW = Path(__file__).parent / "data" / "raw"
OUTPUT_DIR = Path(__file__).parent / "data" / "output"
CSV_PATH = OUTPUT_DIR / "all_stars_2024_2026.csv"
JSON_PATH = OUTPUT_DIR / "all_stars_2024_2026.json"

TEAM_FILE_RE = re.compile(r"^([A-Z0-9]+)_(\d{4})\.shtml$")


def _load_meta(cache_path: Path) -> dict:
    meta_path = Path(str(cache_path) + ".meta.json")
    if meta_path.exists():
        return json.loads(meta_path.read_text(encoding="utf-8"))
    return {}


def _load_show_lookup():
    show_html_path = DATA_RAW / "the_show" / "top100.html"
    if not show_html_path.exists():
        print("WARNING: no cached Show top-100 page found; is_show_top100 will be false for all rows")
        return {}, set()
    entries = show_parser.parse_show_top100(show_html_path.read_text(encoding="utf-8"))
    by_name = {}
    dup_names = set()
    for e in entries:
        key = e["normalized_name"]
        if key in by_name and by_name[key]["name"] != e["name"]:
            dup_names.add(key)
        by_name[key] = e
    return by_name, dup_names


def _collect_raw_rows():
    raw_rows = []
    team_files = sorted((DATA_RAW / "teams").glob("*.shtml"))
    for team_file in team_files:
        m = TEAM_FILE_RE.match(team_file.name)
        if not m:
            continue
        team_id, season = m.group(1), int(m.group(2))
        html = team_file.read_text(encoding="utf-8")
        meta = _load_meta(team_file)
        parsed = br_parser.parse_team_page(html)
        for stat_type, rows in (
            ("batting", parsed["batting_rows"]),
            ("pitching", parsed["pitching_rows"]),
        ):
            for row in rows:
                raw_rows.append({
                    "player_id": row["player_id"],
                    "team_id": team_id,
                    "season_id": season,
                    "stat_type": stat_type,
                    "full_name": row["full_name"],
                    "primary_position": row["primary_position"],
                    "stats": row["stats"],
                    "team_name": parsed["team_name"],
                    "team_wins": parsed["team_wins"],
                    "team_losses": parsed["team_losses"],
                    "team_record": parsed["team_record"],
                    "scraped_at": meta.get("fetched_at"),
                    "source_team_url": meta.get("url"),
                })
    return raw_rows


def _dedupe_primary_key(raw_rows):
    seen = set()
    deduped = []
    for r in raw_rows:
        key = (r["player_id"], r["season_id"], r["stat_type"], r["team_id"])
        if key in seen:
            print(f"WARNING: duplicate primary key {key} in cached data, keeping first occurrence")
            continue
        seen.add(key)
        deduped.append(r)
    return deduped


def _load_bios(player_ids):
    bios = {}
    missing = []
    for pid in sorted(player_ids):
        player_file = DATA_RAW / "players" / f"{pid}.shtml"
        if not player_file.exists():
            missing.append(pid)
            continue
        html = player_file.read_text(encoding="utf-8")
        meta = _load_meta(player_file)
        bio = br_parser.parse_player_page(html)
        bio["source_player_url"] = meta.get("url")
        bios[pid] = bio
    if missing:
        print(f"WARNING: {len(missing)} player id(s) missing a cached bio page "
              f"(run scrape.py to fetch them): {missing[:10]}"
              + (" ..." if len(missing) > 10 else ""))
    return bios


def build():
    show_by_name, show_dup_names = _load_show_lookup()

    raw_rows = _collect_raw_rows()
    raw_rows = _dedupe_primary_key(raw_rows)

    seasons_by_player = defaultdict(set)
    for r in raw_rows:
        seasons_by_player[r["player_id"]].add(r["season_id"])
    selections = {pid: len(seasons) for pid, seasons in seasons_by_player.items()}

    bios = _load_bios(seasons_by_player.keys())

    now_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")
    out_rows = []
    for r in raw_rows:
        row = models.empty_row()
        row["player_id"] = r["player_id"]
        row["team_id"] = r["team_id"]
        row["season_id"] = r["season_id"]
        row["stat_type"] = r["stat_type"]
        row["is_all_star"] = True
        row["all_star_selections_2024_2026"] = selections[r["player_id"]]

        bio = bios.get(r["player_id"], {})
        row["full_name"] = bio.get("full_name") or r["full_name"]
        row["birth_date"] = bio.get("birth_date")
        row["birth_place"] = bio.get("birth_place")
        row["bats"] = bio.get("bats")
        row["throws"] = bio.get("throws")
        row["height_inches"] = bio.get("height_inches")
        row["height_raw"] = bio.get("height_raw")
        row["weight_lbs"] = bio.get("weight_lbs")
        row["debut_date"] = bio.get("debut_date")
        row["primary_position"] = r["primary_position"]

        row["team_name"] = r["team_name"]
        row["team_wins"] = r["team_wins"]
        row["team_losses"] = r["team_losses"]
        row["team_record"] = r["team_record"]

        for col, val in r["stats"].items():
            row[col] = val

        norm_name = show_parser.normalize_name(row["full_name"] or "")
        show_match = None if norm_name in show_dup_names else show_by_name.get(norm_name)
        row["is_show_top100"] = bool(show_match)
        if show_match:
            row["show_overall_rating"] = show_match["ovr"]
            row["show_rank"] = show_match["rank"]
            row["show_potential_grade"] = show_match["pot"]

        row["scraped_at"] = r["scraped_at"] or now_iso
        row["source_team_url"] = r["source_team_url"]
        row["source_player_url"] = bio.get("source_player_url")

        out_rows.append(row)

    out_rows.sort(key=lambda r: (
        -(r["all_star_selections_2024_2026"] or 0),
        r["full_name"] or "",
        -(r["season_id"] or 0),
        r["stat_type"] or "",
    ))

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with CSV_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=models.ALL_COLUMNS)
        writer.writeheader()
        for row in out_rows:
            writer.writerow(row)
    JSON_PATH.write_text(json.dumps(out_rows, default=str), encoding="utf-8")

    print(f"Wrote {len(out_rows)} rows ({len(seasons_by_player)} unique players) to {CSV_PATH}")
    return out_rows


if __name__ == "__main__":
    build()
    import validate
    ok = validate.validate(validate.load_rows())
    sys.exit(0 if ok else 1)

# MLB All-Star Aggregator (2024–2026)

Scrapes Baseball-Reference team/player pages + the MLB The Show 26 Top 100
Players list, builds `data/output/all_stars_2024_2026.csv`, and serves a
localhost website that filters/sorts it. See `WRITEUP.md` for the narrative
on how this was approached.

## Reviewer quickstart

```bash
# 1. Prerequisites: Python 3.11+ (no Node needed)

# 2. Install
python3 -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 3. Build the CSV from the cached raw HTML already committed in data/raw/
#    (no live network requests — scrape.py skips anything already cached)
python scrape.py
python build.py     # writes data/output/all_stars_2024_2026.csv, runs validate.py

# 4. Start the local website (serves the repo root so the site can fetch data/output/*)
make serve           # or: python -m http.server 8080

# 5. Open in browser
open http://localhost:8080/website/     # exact URL — note the /website/ path
```

Run the test suite with `make test` (or `python -m pytest tests/ -v`).

### Expected runtime

- `python scrape.py` with the committed cache populated: a few seconds (every
  page is a cache hit, zero network calls).
- `python build.py`: a few seconds (pure local HTML parsing, no network).
- Live re-scrape from empty cache: **~45–50 minutes** for all 265 pages, by
  design — a 3-second minimum delay between live requests (Baseball-
  Reference's own `robots.txt` sets `Crawl-delay: 3` for `User-agent: *`),
  plus jitter and backoff on retries.

### Forcing a live re-scrape

```bash
python scrape.py --force                 # re-fetch everything
python scrape.py --force --seasons 2026  # re-fetch just one season
```

## Validation results (from the included cache)

```
PASS: no duplicate (player_id, season_id, stat_type, team_id) primary keys
PASS: no null player_id/team_id/season_id
All-Star counts per season (rows include multi-row players like two-way/traded):
  2024: 83 rows, 76 unique players
  2025: 89 rows, 81 unique players
  2026: 78 rows, 71 unique players
Total: 250 rows, 171 unique players across 2024-2026
Show top-100 matched: 67 unique players (116 rows)
PASS: spot check ('judgeaa01', '2024', 'batting') matches expected values
PASS: spot check ('ohtansh01', '2024', 'batting') matches expected values
PASS: spot check ('skenepa01', '2024', 'pitching') matches expected values
```

**On the ~64–68/season guidance:** that figure is *unique All-Star players*
per season roster. Our **row** counts (78–89) run higher because the primary
key is `(player_id, season_id, stat_type, team_id)`, not `(player_id,
season_id)` — a two-way player (Ohtani) contributes a batting row *and* a
pitching row in the same season, and a player traded mid-season while an
All-Star contributes one row per team. Unique-player counts per season
(76/81/71) sit much closer to the 64–68 guidance; the modest excess is real
All-Star-game participants plus a small number of injury-replacement/final-
vote selections that also carry the `[AS]` tag on their team page. 2026 is
lower because the season is still in progress at scrape time
(`scraped_at` on every row records exactly when).

**Show top-100 match rate:** 67 of 171 unique All-Stars (39%) matched the
Show top-100 list by normalized name. This is expected — the Show list only
covers 100 players total across all of MLB, so most All-Stars (correctly)
don't appear on it. No name-collision warnings were logged during the build
(see `build.py`'s `_load_show_lookup`, which would flag it if two different
`player_id`s normalized to the same Show name).

## Known limitations

- `primary_position` for pitchers uses Baseball-Reference's own
  `team_position` field (e.g. `SP`, `CL`, `P`) rather than a heuristic we
  compute — this is directly what BR shows on the team page, not derived.
- Player bio fields (birth date/place, height/weight, bats/throws, debut)
  come from a `schema.org/Person` JSON-LD block embedded in each player
  page. It's present for every player we scraped; if BR ever omits it for an
  obscure player, those fields will be null rather than guessed.
- `team_id` is discovered live from each season's
  `/leagues/majors/{year}.shtml` page rather than hardcoded, specifically
  because some franchises' BR codes are not stable across the 2024–2026
  window (e.g. the Athletics moved from `OAK` to `ATH`) — see WRITEUP.md.

## Repo layout

```
scrape.py             # network layer: cache-first fetch of BR + Show pages
build.py               # parses cached HTML -> CSV + JSON (no network)
validate.py             # required validation checks, run automatically by build.py
src/
  http_client.py        # caching, rate-limiting, retry/backoff HTTP client
  br_parser.py           # team page + player page parsing
  show_parser.py          # Show top-100 parsing + name normalization
  models.py                # CSV column schema shared by build.py and tests
data/raw/{leagues,teams,players,the_show}/   # cached HTML (+ .meta.json sidecars)
data/output/all_stars_2024_2026.csv           # required deliverable
data/output/all_stars_2024_2026.json           # same data, for the website fetch
website/                                        # static site: index.html, app.js, styles.css
tests/                                           # pytest, fixtures under tests/fixtures/
```

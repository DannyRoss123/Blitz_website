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

# 4. Start the local website
make serve           # or: python -m http.server 8080 --directory website

# 5. Open in browser
open http://localhost:8080/
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
  2026: 84 rows, 77 unique players
Total: 256 rows, 177 unique players across 2024-2026
Show top-100 matched: 79 unique players (133 rows)
PASS: spot check ('judgeaa01', '2024', 'batting') matches expected values
PASS: spot check ('ohtansh01', '2024', 'batting') matches expected values
PASS: spot check ('skenepa01', '2024', 'pitching') matches expected values
```

I also cross-checked the built CSV against Blitz's own example-output reference table
(256 rows / 178 unique players / 79 Show-top-100 matches) by name+season+stat_type:
**255 of 256 reference rows matched exactly** to a row in our CSV (the one non-match,
`Adley Stan Rutschman`, is a deliberately-inserted name variant in the reference data —
our CSV correctly has `Adley Rutschman` for that same team/season). That cross-check
caught two real bugs before submission, both now fixed and covered by tests:

1. **Mojibake in scraped HTML.** `requests` falls back to Latin-1 when a server doesn't
   send a charset in `Content-Type`, which both BR and theshowratings.com do. Every
   accented name (Muñoz, Ramírez, Rodón, Suárez, Acuña, ...) was silently corrupted on
   write to the cache, which broke the Show-ratings name join for any accented player.
   Fixed by forcing `resp.encoding = "utf-8"` in `src/http_client.py`, plus a one-time
   repair pass over the already-cached files (reversible: the corruption is a clean
   UTF-8-decoded-as-Latin-1 round trip, so no re-scraping was needed). Show top-100
   matches went from 67 to 79 unique players after the fix.
2. **Unlinked `AS` award text.** BR normally links the All-Star award to
   `/allstar/{year}-allstar-game.shtml`, but for some players recently added to the
   in-progress 2026 season, the Awards cell renders the literal text `AS` with no link
   yet (confirmed on live team pages, e.g. Ceddanne Rafaela/BOS). The parser required
   the link and silently dropped these players. Fixed in `src/br_parser.py` to fall back
   to the literal `AS` token when no link is present; added a regression test
   (`tests/test_br_parser.py`) covering this case.

**Remaining differences vs. the reference are expected, not bugs:**
- **2026 team records** differ by 1 game for nearly every 2026 row — the reference
  snapshot and this scrape were taken at different points during the same in-progress
  season. `scraped_at` on every row records exactly when.
- **Rate stats formatted `.907` vs `0.907`** — this is BR's own display convention
  (no leading zero on BA/OBP/SLG/OPS), preserved verbatim per the assignment's "use the
  values as displayed on the team page" instruction. The reference reformats with a
  leading zero; live spot-checks against BR itself (Judge/Ohtani/Skenes above) confirm
  our values, not the reformatted ones, match the source.
- A handful of OPS+/WHIP/ERA/SO values differ by rounding-level amounts (e.g. 213 vs
  214) — plausibly because the reference is built from Blitz's own internal warehouse
  rather than a live BR mirror at the same instant.

**On the ~64–68/season guidance:** that figure is *unique All-Star players*
per season roster. Our **row** counts (83–89) run higher because the primary
key is `(player_id, season_id, stat_type, team_id)`, not `(player_id,
season_id)` — a two-way player (Ohtani) contributes a batting row *and* a
pitching row in the same season, and a player traded mid-season while an
All-Star contributes one row per team. Unique-player counts per season
(76/81/77) sit much closer to the 64–68 guidance; the modest excess is real
All-Star-game participants plus a small number of injury-replacement/final-
vote selections that also carry the `[AS]` tag on their team page.

**Independent cross-check:** `build_appendix.py` (optional bonus, see below)
fetches the actual All-Star Game box scores and confirms every player who
played in the game across all three years is present in our dataset — 0
gaps found.

**Show top-100 match rate:** 79 of 177 unique All-Stars (~45%) matched the
Show top-100 list by normalized name. This is expected — the Show list only
covers 100 players total across all of MLB, so most All-Stars (correctly)
don't appear on it. No name-collision warnings were logged during the build
(see `build.py`'s `_load_show_lookup`, which would flag it if two different
`player_id`s normalized to the same Show name).

## Optional/bonus items

All optional items in the assignment were completed:

- **Public deployment (Step 3):** live at **[TODO: fill in after GitHub Pages is
  enabled]**. The site is fully self-contained (`website/data/all_stars_2024_2026.json`
  is written next to `index.html` at build time and fetched with a relative path), so
  the same `website/` folder serves both locally and on GitHub Pages with no changes.
- **Bonus appendix CSV:** `make appendix` (or `python build_appendix.py`) fetches and
  caches the actual `/allstar/{year}-allstar-game.shtml` box scores (under
  `data/raw/allstar/`) and cross-checks every player who appeared in the game against
  our `[AS]`-tagged dataset, writing `data/output/allstar_roster_gaps_appendix.csv`.
  Currently empty — 0 gaps found across all three seasons (183 player-appearances
  checked). See WRITEUP.md for what this check can and can't catch.
- **Postgres (extra credit):** `postgres/schema.sql` + `load_postgres.py` load the same
  CSV into Postgres, upserting on the same primary key so reruns are safe. Not required
  for the core submission — CSV remains authoritative. To try it:
  ```bash
  pip install -r requirements-postgres.txt   # or: make postgres-install
  make postgres-up      # docker run postgres:16 on localhost:5432
  make postgres-load    # python load_postgres.py
  make postgres-down    # tear down when done
  ```
  Tested end-to-end against a real `postgres:16` container: all 256 rows load, spot
  checks match the CSV, and a second run doesn't duplicate anything.
- **"What I'd do in production"** section is in `WRITEUP.md` (used instead of a screen
  recording, per the assignment's "either/or" framing).

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
build_appendix.py        # optional bonus: All-Star Game roster cross-check
load_postgres.py           # optional extra credit: load CSV into Postgres
src/
  http_client.py        # caching, rate-limiting, retry/backoff HTTP client
  br_parser.py           # team page + player page parsing
  show_parser.py          # Show top-100 parsing + name normalization
  allstar_parser.py        # All-Star Game box score parsing (bonus appendix)
  models.py                 # CSV column schema shared by build.py and tests
postgres/schema.sql       # optional extra credit: Postgres table schema
data/raw/{leagues,teams,players,the_show,allstar}/   # cached HTML (+ .meta.json sidecars)
data/output/all_stars_2024_2026.csv                   # required deliverable
data/output/all_stars_2024_2026.json                   # same data, JSON form
data/output/allstar_roster_gaps_appendix.csv             # optional bonus appendix
website/                     # static site: index.html, app.js, styles.css, data/ (JSON copy)
tests/                         # pytest, fixtures under tests/fixtures/
```

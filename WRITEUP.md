# Writeup

## Scrape planning

Before writing any parser code I spent time understanding the actual constraints rather
than guessing. I checked baseball-reference.com's `robots.txt` directly: it sets a
3-second `Crawl-delay` for `User-agent: *` and disallows `/play-index/`, `/friv/`,
`/my/`, cgi scripts, etc. — but not `/teams/`, `/players/`, `/allstar/`, or `/leagues/`,
which are exactly the paths this project needs. So the plan honors a 3-second minimum
delay (stricter than the assignment's 1-second suggestion) rather than the bare minimum.

One design decision I made early paid off: rather than hardcoding the 30 MLB team
abbreviations, `scrape.py` first fetches `/leagues/majors/{season}.shtml` for each of
2024/2025/2026 and *discovers* that season's real team-page URLs from the standings
tables (`br_parser.discover_season_team_urls`). This matters because BR's team codes
aren't static — the Athletics' code changed from `OAK` to `ATH` when the franchise
relocated mid-window, and I'd rather derive that from the live page than get it wrong
in a lookup table.

Caching is the backbone of the whole pipeline: `src/http_client.py`'s `CachingClient`
checks `data/raw/` for an existing file before touching the network, and only proceeds
to a live request (with retry/backoff on 403/429/503 and on transient connection
errors) if nothing is cached or `--force` is passed. Every live fetch writes both the
raw HTML and a `.meta.json` sidecar (`{url, fetched_at}`) so `build.py` never needs
another network call to reconstruct provenance. This also made the pipeline naturally
resumable: partway through the real scrape, a transient connection error (a corrupted
response mid-stream, surfacing as a `MemoryError`) killed the process; because nothing
had to be re-fetched, re-running `scrape.py` picked up exactly where it left off and
finished the remaining ~7 pages a minute later. I hit BR for 139 live requests total
against 126 cache hits (fixture pages I'd already pulled while validating the parser
against real markup) — 265 unique pages, zero duplicate fetches, zero blocks.

## Parsing and data-model decisions

Grain is `(player_id, season_id, stat_type, team_id)`, built by iterating *only*
`data/raw/teams/*.shtml` — that's the source of truth for who's an All-Star and their
stat line, per the assignment's rule that `[AS]` in a team page's Awards column is what
qualifies a row. Player pages are joined in afterward purely for biographical fields, by
`player_id` extracted from the profile `href`, never from display text (BR sometimes
appends parenthetical suffixes to names in table cells).

Two edge cases fall directly out of that grain rather than needing special-case code:
two-way players (Ohtani) get a batting row and a pitching row because `[AS]` is checked
independently per table, and traded players (Isaac Paredes, Luis Arraez, Eugenio
Suárez, others) get one row per team because the loop is over team pages, not players —
nothing is summed.

`all_star_selections_2024_2026` is the count of *distinct seasons* a `player_id`
appears in, not a row count, so a two-way player's extra row in one season doesn't
inflate their multi-year count. For the Show join, names are normalized on both sides
(strip suffixes, strip accents, hyphens→spaces, drop periods/apostrophes, lowercase)
before matching; if two different `player_id`s ever normalized to the same key the
build would log a warning and leave both unmatched rather than silently picking one —
that never fired against the real 171-player pool.

## Validation

`validate.py` checks for duplicate primary keys, null IDs, and reports per-season
counts — both row counts (78–89) and unique-player counts (71–81), since the ~64–68
guidance in the assignment is really about unique All-Stars, not rows. I spot-checked
three players against live BR (Judge, Ohtani, Skenes 2024) and all three matched
exactly.

## Website

Static HTML/CSS/vanilla JS, no build step, fetching a JSON mirror of the CSV (`app.js`
does the filtering/sorting client-side). Served from the repo root so it can reach
`data/output/` by relative path — no backend needed.

## What I'd improve with more time

Add a second, independent cross-check against `/allstar/{year}-allstar-game.shtml`
roster pages to catch any All-Star whose team-page `[AS]` tag might be missing; widen
the player-bio fallback path for the rare page without the JSON-LD block; and add a
"only in Show top 100, not an All-Star" note to the README, since that's a case the
current join intentionally never surfaces but a reviewer might expect to see discussed.

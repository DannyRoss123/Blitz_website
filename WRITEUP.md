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
counts — both row counts (83–89) and unique-player counts (76–81), since the ~64–68
guidance in the assignment is really about unique All-Stars, not rows. I spot-checked
three players against live BR (Judge, Ohtani, Skenes 2024) and all three matched
exactly.

I also wrote a throwaway script to cross-check the built CSV against Blitz's own
example-output reference table row by row (matching on normalized name + season +
stat_type, since the reference redacts real IDs). This caught two real bugs the
in-repo validation couldn't see, because both were silent — they dropped or corrupted
data without throwing an error:

1. `requests` was decoding every live response as Latin-1 (BR and theshowratings.com
   don't send a charset on `Content-Type`, so `resp.text` falls back to RFC 2616's
   default instead of the actual UTF-8 body), corrupting every accented name on write
   to the cache and silently breaking the Show-ratings name join for players like
   Muñoz, Ramírez, Rodón, and Acuña. Fixed by forcing `resp.encoding = "utf-8"` before
   reading `resp.text`. Because the corruption was a clean, reversible
   decode-as-Latin-1-then-encode-as-UTF-8 round trip, I could repair the ~260
   already-cached files in place instead of re-scraping — Show top-100 matches went
   from 67 to 79 unique players.
2. BR normally links the All-Star award to `/allstar/{year}-allstar-game.shtml`, but
   for a handful of players recently added to the in-progress 2026 season, the Awards
   cell renders bare `AS` text with no link yet. My parser required the link and
   silently excluded these players — no error, just missing rows. Fixed with a fallback
   to the literal `AS` token, plus a regression test.

After both fixes, 255 of the reference's 256 rows matched ours exactly by identity;
the one non-match is a name variant (`Adley Stan Rutschman`) that appears deliberately
inserted into the reference data. Remaining stat-level differences are explainable,
not bugs: 2026 team records differ by a game or two because the reference snapshot and
my scrape were taken at different points in the same in-progress season, and rate
stats are formatted `.907` rather than `0.907` because I preserve BR's own display
convention (no leading zero) per the assignment's "use the values as displayed on the
team page" instruction — the reference apparently reformats these.

## Website

Static HTML/CSS/vanilla JS, no build step. `build.py` writes a JSON mirror of the CSV
directly next to `index.html` (`website/data/all_stars_2024_2026.json`), and `app.js`
fetches it with a relative path and does all filtering/sorting client-side — no
backend, and no dependency on which directory it's served from, which is what makes
the same `website/` folder work identically on `localhost` and on GitHub Pages.

## Bonus: All-Star Game roster cross-check

The FAQ mentions an optional cross-check against `/allstar/{year}-allstar-game.shtml`
and, separately, a bonus appendix CSV for any gaps found. `build_appendix.py` fetches
and caches those three box-score pages the same cache-first way as the main scraper,
parses every player who actually appeared in the game (unwrapping BR's HTML-comment-
wrapped tables, same trick as the main team-page parser), and diffs that list against
our `[AS]`-tagged dataset per season. Result: 59/63/61 players appeared across
2024/2025/2026, and **zero** were missing from our dataset — a clean independent
confirmation that the team-page `[AS]` method isn't missing anyone who actually played.
(This can only catch false negatives in one direction: a selected All-Star who didn't
play in the game, e.g. an injury replacement, correctly won't appear in the box score
even though they're legitimately an All-Star per the team-page method — so an empty
gap list is the expected good outcome, not a coincidence of a narrow check.)

## Bonus: Postgres

`postgres/schema.sql` mirrors the CSV's grain and columns 1:1 (see `src/models.py` for
the authoritative column list), with one deliberate deviation: `pit_ip` is stored as
`TEXT`, not `NUMERIC`, because BR displays innings pitched in thirds (`63.1` means 63
and ⅓ innings, not 63.1 as a decimal) — storing it numerically would silently imply
the wrong arithmetic. `load_postgres.py` upserts on the same primary key as the CSV, so
rerunning it after a rebuild is safe. Tested end-to-end against a real `postgres:16`
Docker container (not just written and assumed correct): loaded all 256 rows, spot-
checked a batting row (Judge) and a pitching row (Skenes, confirming `bat_hr` is
correctly `NULL` on a pitching row and `pit_ip` preserved as `"133.0"` verbatim), and
confirmed a second run doesn't duplicate anything.

## Public deployment

Deployed to GitHub Pages from the same `website/` folder used for local `make serve` —
no separate build/deploy step, since the JSON data file already lives inside the
folder rather than depending on repo-root serving.

## What I'd do in production

- Move the scraper off a single-process, single-machine cadence: a queue-based fetcher
  (even just a persistent job table) would survive process crashes mid-run without
  relying on cache-checking as the resumability mechanism, and would let scraping scale
  across more sources without a hand-rolled rate limiter.
- Alert on scrape drift, not just report it: the mojibake and unlinked-`AS` bugs were
  both *silent* — they dropped/corrupted data without any check failing. In production
  I'd add a row-count/column-null-rate check per source page that pages someone if a
  parser's yield suddenly drops (e.g. "team page usually yields 2-5 AS rows, got 0" is
  a signal worth surfacing immediately, not discovering via an external diff).
- Replace the from-scratch caching layer with a real HTTP cache (e.g. `requests-cache`
  backed by SQLite) and a real task scheduler (Airflow/Dagster/cron+lock) instead of a
  single `scrape.py` invocation, so partial seasons, mid-season injury replacements, and
  new All-Star Game selections can be picked up incrementally instead of via full reruns.
- Swap the hand-written parser-fixture tests for snapshot tests against a larger corpus
  of saved real pages (one per team, across a few seasons) to catch markup drift BR
  makes over time, since this whole project is built on assumptions about `data-stat`
  attribute names that could change without notice.
- For the website: add the "Show top 100 but not an All-Star" view as a second toggle
  (currently intentionally out of scope, since the CSV's grain is All-Star rows only),
  and paginate/virtualize the table if the dataset ever grows well past a few hundred
  rows.

## What I'd improve with more time

Widen the player-bio fallback path for the rare page without the JSON-LD block, and add
a short note in the README about the "Show top 100 but not an All-Star" case, since
that's a case the current join intentionally never surfaces but a reviewer might expect
to see discussed.

# Writeup

## How I planned the scrape

Before writing any code, I wanted to understand the actual constraints rather than assume them. I read Baseball Reference's robots.txt directly and found that it asks for a three second delay between requests for generic bots, and that the pages I actually needed (team pages, player pages, the All Star game pages, league pages) weren't disallowed at all. Rather than pick some arbitrary "safe sounding" delay, I used their own stated number as a floor, with a bit of random jitter so requests don't land in perfect lockstep.

One decision that paid off later was refusing to hardcode the thirty team abbreviations. Franchise codes on Baseball Reference aren't as stable as they look; the Athletics' code changed partway through the years I was scraping. So instead of maintaining a lookup table by hand, I scrape each season's league page once and pull the real team codes directly from it, which means the pipeline discovers the correct mapping rather than trusting me to have gotten it right.

Everything routes through a single caching layer, `http_client.py`, that checks whether a page already exists on disk before it ever considers a live request. `scrape.py` is the script that actually sequences the fetches: the Show top 100 list first, then the league pages, then team pages, then player pages. That single design choice is what makes the whole pipeline rerunnable in seconds once the cache is populated, and it's also what saved the run when a live scrape crashed partway through on a corrupted response. Since nothing had already succeeded needed to be refetched, I simply reran the scraper and it picked up exactly where it left off.

## How I approached the data model

`build.py` is where the actual dataset gets assembled, and `models.py` holds the column schema that both it and the tests share. I decided early that the grain of each row should come from the team pages rather than the player pages. A row exists because a specific player carries the All Star award on a specific team's batting or pitching table for a specific season, and nothing more complicated than that. Player pages are only consulted afterward, to supply biographical details like birth date and height.

That single decision resolved two edge cases almost incidentally. Two way players, Ohtani being the obvious example, are checked for the award independently on both the batting and pitching tables, so they naturally end up with two rows in a season without any special handling on my part. Traded players work the same way: because the aggregation loops over team pages rather than players, someone traded mid season while an All Star simply appears once per team, each row carrying that team's own statistics. Nothing gets summed or reconciled across teams.

For the multi year selection count, I made sure to count distinct seasons a player appears in rather than raw row count, so a two way player's extra row in a given season doesn't make them look like they were selected more times than they actually were.

For matching player names against the Show ratings list, I followed the stated normalization rules closely: stripping suffixes, removing accents, converting hyphens to spaces, and lowercasing before comparison. I also added a safeguard so that if two different players ever normalized to the same key, the build would flag it rather than silently resolving the collision in either direction.

## Validation, and what it actually turned up

`validate.py` runs the baseline checks you would expect: no duplicate primary keys, no null identifiers, per season counts reported and explained rather than just printed. I also manually verified three well known All Stars against the live site, and all three matched exactly.

What proved far more valuable was building an entirely separate way to check the work. I took the reference table Blitz provided and compared it against my own output, player by player. That comparison is what surfaced two real bugs that my internal validation was structurally incapable of catching, since neither one produced anything technically invalid. Both simply dropped or corrupted data without raising any error.

The first was an encoding issue. The library I was using for requests defaults to a different text encoding whenever a server doesn't explicitly declare one in its response headers, and neither of the sites I was pulling from declared one. As a result, every accented name was being silently corrupted on its way into the cache. Nothing crashed and nothing looked obviously wrong at a glance, but it quietly broke the name matching against the Show ratings for any player with an accent. Once I corrected the decoding in `http_client.py` and repaired the files already sitting in the cache, my Show ratings match count rose from the high sixties to seventy nine, which lined up with what the reference data showed.

The second bug was specific to the season still in progress. Baseball Reference normally renders the All Star award as a hyperlink, but for a handful of players added more recently, the site displays the plain text with no link attached yet. The parsing logic in `br_parser.py` only checked for the link, so it was quietly excluding legitimate All Stars. I added a fallback there that also recognizes the unlinked form.

After correcting both issues, a second comparison showed two hundred fifty five of the reference's two hundred fifty six rows matching exactly by identity. The single row that didn't match turned out to be a name that had been deliberately altered in the reference data itself, not an error on my end.

## Building the website

I kept the site to plain HTML, CSS, and vanilla JavaScript deliberately, with no framework and no build step. All the filtering, searching, and sorting logic lives in `app.js` and runs client side once the data has loaded. The default sort mirrors the example's own ordering: players with the most multi year selections first, then alphabetically, then most recent season first. Every player links directly to their real Baseball Reference profile, since I have the actual URL from the scrape rather than needing to fall back to a search link the way the example does.

## Additional work beyond what was required

Given that this data would plausibly sit in front of a real database eventually, I added an optional Postgres path alongside the CSV, defined in `schema.sql` and loaded through `load_postgres.py`. It shares the same schema and the same primary key, and loading it more than once simply updates existing rows rather than duplicating them. I tested this against an actual Postgres instance running locally rather than assuming the schema and loader were correct, loaded the full dataset in, and verified several rows by hand.

I also deployed the site publicly, which required making it locate its own data regardless of which directory it was being served from, rather than depending on one specific setup. Separately, `build_appendix.py` runs an independent cross check against the actual All Star Game box scores to confirm that no one who played in the real game was missing from my dataset. That check came back clean: every player who appeared in a game was already accounted for.

## Tradeoffs and what I would do differently

The two bugs I encountered are the most instructive part of this project to discuss, because neither was a crash or an obvious failure. Both were the kind of defect that looks entirely correct until you go looking for it specifically. The broader lesson is that a pipeline can pass every check you think to write for it and still be quietly wrong, and the only reason I caught these two was by cross referencing against an independent source rather than trusting my own validation to be complete.

Given more time, I would handle the rare case of a player page missing its structured biographical data more gracefully instead of leaving those fields blank, and I would add a short note addressing players who appear on the Show top 100 list without being All Stars, since that's a case my current design never surfaces but a reviewer might reasonably expect to see discussed.

## What I would do in production

A few things would change if this were a production system rather than a take home assignment. I would move away from a single script performing everything in one run and toward something closer to a proper job queue, so that a crash partway through doesn't depend on caching as the sole safety net. I would also want real alerting on data drift, since both bugs I encountered were silent by nature; in production, I would want to be notified the moment a page that typically yields several All Stars suddenly yields none, rather than discovering it later through an external comparison. I would replace the hand built caching layer with something more standard, and I would want a much larger library of saved real pages to test the parser against over time, since the entire pipeline rests on assumptions about how Baseball Reference structures its markup, assumptions that could shift without notice.

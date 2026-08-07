# Writeup

## How I planned the scrape

Before touching any code I wanted to actually understand what I was dealing with instead of guessing. I pulled up Baseball Reference's robots.txt directly and saw they ask for a 3 second delay between requests for any generic bot, and that the pages I actually needed (team pages, player pages, the all star game pages, league pages) weren't blocked at all. So instead of picking some arbitrary "safe sounding" delay, I just used their own number as the floor, plus a little random jitter so requests don't all land in lockstep.

One thing that saved me a headache later was not hardcoding the 30 team abbreviations. Teams change their codes over time (the Athletics moved and their code changed partway through the years I was scraping), so instead I scrape each season's league page once and pull the real team codes straight off the page. That way I never have to worry about a stale lookup table quietly being wrong.

Everything runs through one caching layer. Before any live request happens it checks if the page already exists on disk, and if it does it just reads it back, no network call at all. That's what makes it possible to rerun the whole pipeline in seconds once the cache is populated, and it's also what saved me when the scrape crashed partway through on a corrupted response. Because nothing had to be refetched, I just reran it and it picked up exactly where it left off a minute later.

## How I approached the data model

I decided pretty early that the grain of each row had to come from the team pages, not the player pages. A row exists because a player shows the All Star award on a specific team's batting or pitching table for a specific season, full stop. Player pages only get pulled in afterward, just to fill in biographical info like birthdate and height.

That decision ended up solving two edge cases almost by accident. Two way players like Ohtani get checked for the award independently on both the batting and pitching tables, so he naturally ends up with two rows in the same season without me writing any special case for it. And traded players work the same way, since I'm looping over team pages and not players, someone who got traded mid season while an All Star just shows up once per team, with that team's own stats. Nothing gets summed together.

For the multi year selection count I made sure to count distinct seasons a player shows up in, not just raw row count, so a two way player doesn't accidentally look like they've made more All Star teams than they actually have.

For matching player names against the Show ratings list, I followed the normalization rules pretty closely: stripping suffixes, removing accents, turning hyphens into spaces, and lowercasing everything before comparing. I also added a small safety check so that if two different players ever normalized down to the same name, it would flag it loudly instead of quietly picking one of them.

## Validation, and what I actually found

I ran the basic checks anyone would expect: no duplicate primary keys, no null IDs, per season counts reported and explained. I also manually checked three well known All Stars against the live site and everything matched exactly.

What ended up being way more useful was building a second, completely independent way to double check the data. I took the reference table Blitz provided and lined it up against my own output player by player. That's actually how I found two real bugs that my own validation checks were structurally incapable of catching, because neither one produced anything invalid, they just quietly dropped or corrupted data.

The first was an encoding issue. The library I was using for requests defaults to a different text encoding whenever a server doesn't explicitly declare one, and neither site I was pulling from declared one. So every name with an accent in it was getting mangled on the way into the cache. Nothing crashed, the data just looked wrong, and it silently broke my name matching against the Show ratings for any player with an accented name. Once I fixed the actual decoding and repaired the files already sitting in the cache, my Show ratings match count jumped from the high 60s to 79, right in line with what the reference data showed.

The second bug was specific to the current in progress season. Normally the All Star award on Baseball Reference shows up as a clickable link, but for a handful of players who'd been added more recently, the site just shows the plain text with no link yet. My original logic only looked for the link, so it was silently skipping real All Stars. I added a fallback that also catches the plain text version.

After fixing both of those, I compared again and got 255 out of 256 rows matching exactly by identity. The one that didn't match turned out to be a name that had been deliberately altered in the reference data, not a mistake on my end.

## Building the website

I kept the site as plain HTML, CSS, and vanilla JavaScript on purpose, no framework, no build step. All the filtering, searching, and sorting happens client side once the data is loaded in. I matched the default sort order from the example: most multi year All Stars first, then alphabetically, then most recent season first. Every player links out to their real Baseball Reference page since I actually have the real URL, rather than needing to fall back to a search link like the example does.

## Extra stuff I added beyond what was required

Since this data was probably going in front of a real database eventually, I also added a Postgres option alongside the CSV. Same data, same primary key, set up so loading it twice doesn't create duplicates. I actually spun up a real Postgres container locally to test it instead of just writing the SQL and hoping it worked, loaded everything in, and checked a few rows by hand.

I also got the site deployed publicly, which meant making sure it could find its own data no matter which folder it was being served from, instead of only working when served from one specific spot. And I built a separate, independent check against the actual All Star Game box scores to see if anyone who played in the real game was missing from my dataset. It came back completely clean, every player who appeared in a game was already there.

## Tradeoffs and what I'd do differently

The two real bugs I hit are honestly the most useful thing to talk about here, because neither one was a crash or an obvious failure. They were both the kind of thing that looks totally fine until you go looking for it specifically. That's probably the biggest lesson from this whole project: a pipeline can pass every check you write for it and still be quietly wrong, and the only way I actually caught these two was by cross referencing against an independent source instead of trusting my own validation logic to be complete.

Given more time I'd want to handle the rare case of a player page missing its structured bio data a little more gracefully instead of just leaving those fields blank, and I'd add a short note about players who show up on the Show top 100 list but aren't All Stars, since that's a case my current setup never surfaces but a reviewer might expect to see addressed somewhere.

## What I'd do in production

A few things I'd change if this were a real production pipeline instead of a take home. I'd move away from a single script doing everything in one run and toward something more like a proper job queue, so a crash partway through doesn't depend on caching as the only safety net. I'd also want actual alerting on data drift, since both bugs I hit were silent. In production I'd want something that pages someone the moment a page that normally yields a handful of All Stars suddenly yields zero, instead of finding out weeks later from an external comparison. I'd swap the hand rolled caching for something more standard, and I'd want a much bigger library of saved real pages to test the parser against over time, since this whole thing is built on assumptions about how Baseball Reference structures its pages, assumptions that could change without warning.

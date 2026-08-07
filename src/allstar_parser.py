"""Parser for the All-Star Game box score page
(/allstar/{year}-allstar-game.shtml), used only as an optional cross-check
per the assignment FAQ: "If you find gaps vs the All-Star game roster,
include them as a bonus appendix CSV."

Note this page only lists players who actually appeared in the game (had a
plate appearance or pitched) -- selected All-Stars who didn't play (rest,
injury) won't show up here even though they're legitimately All-Stars per
the team-page [AS] method. So this cross-check can only ever find false
negatives in the *other* direction: a player who played in the game but
wasn't [AS]-tagged on their team page.
"""
import re

from bs4 import BeautifulSoup

PLAYER_HREF_RE = re.compile(r"/players/[a-z]/([A-Za-z0-9]+)\.shtml")


def parse_allstar_game_participants(html: str):
    """Return {player_id: full_name} for every player who appears in a
    data-stat="player" cell on the box score (both teams, batting + pitching)."""
    # BR wraps every non-default-tab box score table (e.g. the losing
    # league's batting/pitching tables) in an HTML comment. Strip the
    # comment delimiters so BeautifulSoup parses them as live markup,
    # same trick used in br_parser._find_table for team pages.
    html = html.replace("<!--", "").replace("-->", "")
    soup = BeautifulSoup(html, "lxml")
    participants = {}
    for cell in soup.find_all(attrs={"data-stat": "player"}):
        link = cell.find("a", href=True)
        if link is None:
            continue
        m = PLAYER_HREF_RE.search(link["href"])
        if not m:
            continue
        participants[m.group(1)] = link.get_text(strip=True)
    return participants

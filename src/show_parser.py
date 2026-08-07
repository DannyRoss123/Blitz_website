"""Parser for the MLB The Show 26 Top 100 Players list
(theshowratings.com/lists/top-100-players) and the name-normalization used
to join it to Baseball-Reference All-Star rows by display name.
"""
import unicodedata

from bs4 import BeautifulSoup

SUFFIXES = {"jr", "sr", "ii", "iii", "iv"}


def normalize_name(name: str) -> str:
    """Normalize a player display name for cross-source matching:
    strip suffixes (Jr./Sr./II/III/IV), remove accents, replace hyphens with
    spaces, remove periods/apostrophes, and lowercase."""
    if not name:
        return ""
    name = name.replace("-", " ")
    name = "".join(
        ch for ch in unicodedata.normalize("NFKD", name) if not unicodedata.combining(ch)
    )
    name = name.replace(".", "").replace("'", "")
    tokens = [t for t in name.lower().split() if t not in SUFFIXES]
    return " ".join(tokens)


def parse_show_top100(html: str):
    soup = BeautifulSoup(html, "lxml")
    table = soup.find("table")
    if table is None:
        return []
    tbody = table.find("tbody")
    if tbody is None:
        return []

    entries = []
    for tr in tbody.find_all("tr"):
        tds = tr.find_all("td")
        if len(tds) < 4:
            continue

        rank_text = tds[0].get_text(strip=True).rstrip(".")
        try:
            rank = int(rank_text)
        except ValueError:
            continue

        name_span = tds[1].find("span", class_="entry-font")
        name = (name_span or tds[1]).get_text(strip=True)

        ovr_span = tds[2].find("span")
        ovr_text = (ovr_span or tds[2]).get_text(strip=True)
        try:
            ovr = int(float(ovr_text))
        except ValueError:
            ovr = None

        pot_span = tds[3].find("span")
        pot = (pot_span or tds[3]).get_text(strip=True) or None

        entries.append({
            "rank": rank,
            "name": name,
            "normalized_name": normalize_name(name),
            "ovr": ovr,
            "pot": pot,
        })
    return entries

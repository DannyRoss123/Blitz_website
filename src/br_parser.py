"""Parsers for Baseball-Reference league, team, and player pages.

Markup assumptions here were confirmed against live pages during planning
(see WRITEUP.md), not guessed: team pages expose stat cells via
``data-stat="b_*"``/``data-stat="p_*"`` attributes, the All-Star flag is an
``<a href="/allstar/{season}-allstar-game.shtml">`` inside the
``data-stat="awards"`` cell, and player names/ids live in a
``data-stat="name_display"`` cell. Player bio data comes from the page's
``schema.org/Person`` JSON-LD block, which is far more stable than scraping
the prose bio text.
"""
import json
import re
from datetime import datetime

from bs4 import BeautifulSoup, Comment

from . import models

PLAYER_HREF_RE = re.compile(r"/players/[a-z]/([A-Za-z0-9]+)\.shtml")
TEAM_HREF_RE = re.compile(r"/teams/([A-Z0-9]{2,4})/(\d{4})\.shtml")
ALLSTAR_HREF_RE = re.compile(r"/allstar/(\d{4})-allstar-game\.shtml")

BASE_URL = "https://www.baseball-reference.com"

BATS_MAP = {"Right": "R", "Left": "L", "Both": "S"}
THROWS_MAP = {"Right": "R", "Left": "L"}


def discover_season_team_urls(html: str, season: int):
    """Return [(team_id, team_url), ...] for every team appearing on a
    /leagues/majors/{season}.shtml page. Avoids hardcoding team codes, since
    BR's codes for some franchises (e.g. Athletics, Tampa Bay) have changed
    over time."""
    season_str = str(season)
    codes = sorted({
        m.group(1) for m in TEAM_HREF_RE.finditer(html) if m.group(2) == season_str
    })
    return [(code, f"{BASE_URL}/teams/{code}/{season}.shtml") for code in codes]


def _find_table(soup: BeautifulSoup, table_id: str):
    table = soup.find("table", id=table_id)
    if table is not None:
        return table
    # BR sometimes ships non-default-tab tables inside an HTML comment.
    for comment in soup.find_all(string=lambda t: isinstance(t, Comment)):
        if table_id in comment:
            inner = BeautifulSoup(str(comment), "lxml")
            found = inner.find("table", id=table_id)
            if found is not None:
                return found
    return None


def _cell_text(tr, data_stat):
    cell = tr.find(attrs={"data-stat": data_stat})
    return cell.get_text(strip=True) if cell is not None else None


def _parse_stat_table(soup, table_id, header_map):
    """Return only the rows flagged [AS] in this table's Awards column."""
    table = _find_table(soup, table_id)
    if table is None:
        return []
    tbody = table.find("tbody")
    if tbody is None:
        return []

    rows = []
    for tr in tbody.find_all("tr"):
        row_classes = tr.get("class") or []
        if "thead" in row_classes:
            continue  # repeated mid-table header row

        name_cell = tr.find(attrs={"data-stat": "name_display"})
        if name_cell is None:
            continue
        link = name_cell.find("a", href=True)
        if link is None:
            continue
        m = PLAYER_HREF_RE.search(link["href"])
        if not m:
            continue

        awards_cell = tr.find(attrs={"data-stat": "awards"})
        if awards_cell is None:
            continue
        is_all_star = any(
            ALLSTAR_HREF_RE.search(a["href"])
            for a in awards_cell.find_all("a", href=True)
        )
        if not is_all_star:
            # BR normally links the AS award to /allstar/{year}-allstar-
            # game.shtml, but for some recently-tagged players on the
            # current in-progress season it renders the bare "AS" token
            # with no link yet (confirmed against live team pages, e.g.
            # 2026 Ceddanne Rafaela/BOS). Fall back to the literal token.
            award_tokens = [t.strip() for t in awards_cell.get_text(strip=True).split(",")]
            is_all_star = "AS" in award_tokens
        if not is_all_star:
            continue

        stats = {col: _cell_text(tr, data_stat) for data_stat, col in header_map.items()}

        rows.append({
            "player_id": m.group(1),
            "full_name": link.get_text(strip=True),
            "primary_position": _cell_text(tr, "team_position"),
            "stats": stats,
        })
    return rows


def parse_team_page(html: str):
    soup = BeautifulSoup(html, "lxml")

    team_name = None
    h1 = soup.find("h1")
    if h1 is not None:
        spans = h1.find_all("span")
        if len(spans) >= 2:
            team_name = spans[1].get_text(strip=True)

    team_wins = team_losses = team_record = None
    record_strong = soup.find("strong", string=re.compile(r"Record:"))
    if record_strong is not None:
        p = record_strong.find_parent("p")
        text = p.get_text(" ", strip=True) if p is not None else ""
        m = re.search(r"(\d+)-(\d+)", text)
        if m:
            team_wins, team_losses = int(m.group(1)), int(m.group(2))
            team_record = f"{team_wins}-{team_losses}"

    batting_rows = _parse_stat_table(soup, "players_standard_batting", models.BATTING_HEADER_MAP)
    pitching_rows = _parse_stat_table(soup, "players_standard_pitching", models.PITCHING_HEADER_MAP)

    return {
        "team_name": team_name,
        "team_wins": team_wins,
        "team_losses": team_losses,
        "team_record": team_record,
        "batting_rows": batting_rows,
        "pitching_rows": pitching_rows,
    }


def _find_person_ldjson(soup):
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        try:
            data = json.loads(script.string or "")
        except (json.JSONDecodeError, TypeError):
            continue
        if isinstance(data, dict) and data.get("@type") == "Person":
            return data
    return None


def parse_player_page(html: str):
    soup = BeautifulSoup(html, "lxml")
    ldjson = _find_person_ldjson(soup)

    full_name = birth_date = birth_place = height_raw = weight_lbs = None
    if ldjson:
        full_name = ldjson.get("name")
        birth_date = ldjson.get("birthDate")
        birth_place = ldjson.get("birthPlace")
        height = ldjson.get("height")
        if isinstance(height, dict):
            height_raw = height.get("value")
        weight = ldjson.get("weight")
        if isinstance(weight, dict):
            wm = re.search(r"(\d+)", str(weight.get("value", "")))
            if wm:
                weight_lbs = int(wm.group(1))

    height_inches = None
    if height_raw:
        hm = re.match(r"(\d+)-(\d+)", height_raw)
        if hm:
            height_inches = int(hm.group(1)) * 12 + int(hm.group(2))

    page_text = soup.get_text(" ", strip=True)

    bats = throws = None
    bm = re.search(r"Bats:\s*(Right|Left|Both)", page_text)
    if bm:
        bats = BATS_MAP[bm.group(1)]
    tm = re.search(r"Throws:\s*(Right|Left)", page_text)
    if tm:
        throws = THROWS_MAP[tm.group(1)]

    debut_date = None
    dm = re.search(r"Debut:.*?([A-Z][a-z]+ \d{1,2}, \d{4})", page_text)
    if dm:
        try:
            debut_date = datetime.strptime(dm.group(1), "%B %d, %Y").date().isoformat()
        except ValueError:
            debut_date = None

    return {
        "full_name": full_name,
        "birth_date": birth_date,
        "birth_place": birth_place,
        "bats": bats,
        "throws": throws,
        "height_inches": height_inches,
        "height_raw": height_raw,
        "weight_lbs": weight_lbs,
        "debut_date": debut_date,
    }

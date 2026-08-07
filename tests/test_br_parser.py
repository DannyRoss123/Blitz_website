from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from src import br_parser

FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_team_page_batting():
    html = (FIXTURES / "team_page_sample.html").read_text(encoding="utf-8")
    parsed = br_parser.parse_team_page(html)

    assert parsed["team_name"] == "Sample City Sluggers"
    assert parsed["team_wins"] == 56
    assert parsed["team_losses"] == 44
    assert parsed["team_record"] == "56-44"

    # Only the AS-flagged batter should be included; the header-repeat row
    # and the non-AS bench player must both be excluded.
    assert len(parsed["batting_rows"]) == 1
    row = parsed["batting_rows"][0]
    assert row["player_id"] == "allstaal01"
    assert row["full_name"] == "All Star"
    assert row["primary_position"] == "CF"
    assert row["stats"]["bat_HR"] == "58"
    assert row["stats"]["bat_OPS"] == "1.159"


def test_parse_team_page_pitching_inside_html_comment():
    """BR sometimes ships non-default-tab tables wrapped in an HTML comment;
    the fixture deliberately wraps the pitching table this way."""
    html = (FIXTURES / "team_page_sample.html").read_text(encoding="utf-8")
    parsed = br_parser.parse_team_page(html)

    assert len(parsed["pitching_rows"]) == 1
    row = parsed["pitching_rows"][0]
    assert row["player_id"] == "acesta01"
    assert row["primary_position"] == "SP"
    assert row["stats"]["pit_W"] == "12"
    assert row["stats"]["pit_ERA"] == "2.08"


def test_parse_player_page_bio():
    html = (FIXTURES / "player_page_sample.html").read_text(encoding="utf-8")
    bio = br_parser.parse_player_page(html)

    assert bio["full_name"] == "All Star"
    assert bio["birth_date"] == "1992-04-26"
    assert bio["birth_place"] == "Linden, CA, United States"
    assert bio["bats"] == "R"
    assert bio["throws"] == "R"
    assert bio["height_raw"] == "6-7"
    assert bio["height_inches"] == 79
    assert bio["weight_lbs"] == 282
    assert bio["debut_date"] == "2016-08-13"


def test_discover_season_team_urls():
    html = '<a href="/teams/NYY/2024.shtml">Yankees</a> <a href="/teams/BOS/2024.shtml">Red Sox</a> <a href="/teams/NYY/2025.shtml">Yankees</a>'
    teams = br_parser.discover_season_team_urls(html, 2024)
    assert teams == [
        ("BOS", "https://www.baseball-reference.com/teams/BOS/2024.shtml"),
        ("NYY", "https://www.baseball-reference.com/teams/NYY/2024.shtml"),
    ]

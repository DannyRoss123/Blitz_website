from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from src import allstar_parser

FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_allstar_game_participants_unwraps_html_comments():
    """One table is live markup, the other is HTML-comment-wrapped (BR's
    real pattern for non-default-tab tables) -- both must be found."""
    html = (FIXTURES / "allstar_game_sample.html").read_text(encoding="utf-8")
    participants = allstar_parser.parse_allstar_game_participants(html)

    assert participants == {
        "marteke01": "Ketel Marte",
        "ohtansh01": "Shohei Ohtani",
    }

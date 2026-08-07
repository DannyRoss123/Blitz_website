from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from src import show_parser

FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_show_top100():
    html = (FIXTURES / "show_top100_sample.html").read_text(encoding="utf-8")
    entries = show_parser.parse_show_top100(html)

    assert len(entries) == 3
    first = entries[0]
    assert first["rank"] == 1
    assert first["name"] == "All Star"
    assert first["ovr"] == 99
    assert first["pot"] == "A"
    assert first["normalized_name"] == "all star"

    hyphen = entries[1]
    assert hyphen["name"] == "Pete Crow-Armstrong"
    assert hyphen["normalized_name"] == "pete crow armstrong"

    accented = entries[2]
    assert accented["name"] == "Jose Ramírez"
    assert accented["normalized_name"] == "jose ramirez"

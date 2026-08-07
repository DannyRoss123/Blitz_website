from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.show_parser import normalize_name


def test_strips_suffixes():
    assert normalize_name("Bobby Witt Jr.") == "bobby witt"
    assert normalize_name("Ken Griffey Sr.") == "ken griffey"
    assert normalize_name("Cal Ripken III") == "cal ripken"


def test_removes_accents():
    assert normalize_name("José Ramírez") == "jose ramirez"
    assert normalize_name("Julio Rodríguez") == "julio rodriguez"


def test_replaces_hyphens_with_spaces():
    assert normalize_name("Pete Crow-Armstrong") == "pete crow armstrong"


def test_removes_periods_and_apostrophes():
    assert normalize_name("Ryan O'Hearn") == "ryan ohearn"
    assert normalize_name("J.T. Realmuto") == "jt realmuto"


def test_case_insensitive():
    assert normalize_name("AARON JUDGE") == normalize_name("aaron judge") == "aaron judge"


def test_combined():
    assert normalize_name("José Ramírez Jr.") == "jose ramirez"

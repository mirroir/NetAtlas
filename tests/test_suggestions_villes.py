import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent / "python"))

from database import suggerer_villes


def test_suggerer_villes():
    suggestions = suggerer_villes("Saint-Piere")

    assert isinstance(suggestions, list)
    assert len(suggestions) > 0
    assert suggestions[0][0] == "Saint-Pierre"

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python"))

from database import get_villes_par_categorie_pays_region


def test_get_villes_par_categorie_pays_region():
    resultats = get_villes_par_categorie_pays_region(
        "Marché",
        "France",
        "Sud",
    )

    assert isinstance(resultats, list)
    assert len(resultats) > 0

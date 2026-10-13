import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python"))

from database import get_lieux_par_categorie_pays_region_ville


def test_get_lieux_par_categorie_pays_region_ville():
    resultats = get_lieux_par_categorie_pays_region_ville(
        "Marché",
        "France",
        "Sud",
        "Saint-Pierre",
    )

    assert isinstance(resultats, list)
    assert len(resultats) > 0

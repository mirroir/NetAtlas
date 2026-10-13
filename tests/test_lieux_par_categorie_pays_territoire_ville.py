import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python"))

from database import get_lieux_par_categorie_pays_territoire_ville


def test_get_lieux_par_categorie_pays_territoire_ville():
    resultats = get_lieux_par_categorie_pays_territoire_ville(
        "Marché",
        "France",
        "La Réunion",
        "Saint-Pierre",
    )

    assert isinstance(resultats, list)
    assert len(resultats) > 0

    noms_lieux = [lieu[1] for lieu in resultats]

    assert "Marché de Saint-Pierre" in noms_lieux



import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python"))

from database import get_villes_par_categorie_pays_territoire


def test_get_villes_par_categorie_pays_territoire():
    resultats = get_villes_par_categorie_pays_territoire(
        "Marché",
        "France",
        "La Réunion",
    )

    assert isinstance(resultats, list)
    assert len(resultats) > 0

    noms_villes = [ville[1] for ville in resultats]

    assert "Saint-Pierre" in noms_villes



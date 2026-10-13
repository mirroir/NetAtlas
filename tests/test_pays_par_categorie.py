import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "python"))

from database import get_pays_par_categorie


def test_get_pays_par_categorie_marche():
    resultats = get_pays_par_categorie("Marché")

    assert isinstance(resultats, list)
    assert len(resultats) > 0

    noms_pays = [pays[1] for pays in resultats]

    assert "France" in noms_pays



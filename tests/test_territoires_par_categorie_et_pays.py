import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python"))

from database import get_territoires_par_categorie_et_pays


def test_get_territoires_par_categorie_et_pays():
    resultats = get_territoires_par_categorie_et_pays(
        "Marché",
        "France",
    )

    assert isinstance(resultats, list)
    assert len(resultats) > 0
    assert any(territoire[1] == "La Réunion" for territoire in resultats)



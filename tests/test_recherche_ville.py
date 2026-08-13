import sys
import pytest

from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent / "python"))

from database import rechercher_ville


def test_recherche_ville_existante():
    villes = rechercher_ville("Saint-Pierre")

    assert villes
    assert villes[0][1] == "Saint-Pierre"


@pytest.mark.parametrize("entree", [
    "' OR '1'='1",
    "' OR 1=1 --",
    "\" OR \"1\"=\"1",
    "' AND '1'='2",
    "' UNION SELECT NULL --",
    "Saint-Pierre' --",
    "Saint-Pierre/test/",
    "'",
    "\"",
    "--",
    "/* */",
    ";",
])
def test_recherche_ville_resiste_aux_entrees_sql(entree):
    villes = rechercher_ville(entree)

    assert isinstance(villes, list)

    # Une entrée SQL suspecte ne doit jamais retourner
    # toutes les villes de la base.
    assert len(villes) < 3



@pytest.mark.parametrize("entree", [
    "",
    " ",
    "     ",
    "%",
    "_",
    "%%%%",
    "_",
    "Saint-Pierre%",
    "%Saint-Pierre",
    "éèàùç",
    "東京",
    "🚀",
    "A" * 1000,
])
def test_recherche_ville_entrees_inhabituelles(entree):
    villes = rechercher_ville(entree)

    assert isinstance(villes, list)





def test_injection_ne_modifie_pas_les_donnees():
    avant = rechercher_ville("Saint-Pierre")

    rechercher_ville("'; DELETE FROM villes; --")

    apres = rechercher_ville("Saint-Pierre")

    assert avant == apres





import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python"))

from database import get_contexte_recherche


def test_contexte_recherche_trouve_pays():
    contexte = get_contexte_recherche("Fr")

    assert isinstance(contexte, dict)
    assert "pays" in contexte

    noms_pays = [pays[1] for pays in contexte["pays"]]

    assert "France" in noms_pays

def test_contexte_recherche_trouve_lieux():
    contexte = get_contexte_recherche("Marché")

    assert isinstance(contexte, dict)
    assert "lieux" in contexte

    noms_lieux = [lieu[1] for lieu in contexte["lieux"]]

    assert "Marché de Saint-Pierre" in noms_lieux

def test_contexte_recherche_lieu_remonte_au_pays():
    contexte = get_contexte_recherche("Marché")

    noms_pays = [pays[1] for pays in contexte["pays"]]

    assert "France" in noms_pays

def test_contexte_recherche_lieu_remonte_aux_regions():
    contexte = get_contexte_recherche("Marché")

    noms_regions = [region[1] for region in contexte["regions"]]

    assert "Sud" in noms_regions

def test_contexte_recherche_lieu_remonte_aux_villes():
    contexte = get_contexte_recherche("Marché")

    noms_villes = [ville[1] for ville in contexte["villes"]]

    assert "Saint-Pierre" in noms_villes

def test_contexte_recherche_pays_remonte_aux_categories():
    contexte = get_contexte_recherche("France")

    noms_categories = [
        categorie[1]
        for categorie in contexte["categories"]
    ]

    assert "Marché" in noms_categories


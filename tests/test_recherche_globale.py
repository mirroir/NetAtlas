import psycopg

import database
from database import rechercher_global


def test_recherche_globale_par_ville():
    resultats = rechercher_global("Saint-Pierre")

    assert isinstance(resultats, list)
    assert len(resultats) > 0

    # La ville est le 2e élément retourné par la requête SQL
    assert any(
        resultat[2] == "Saint-Pierre"
        for resultat in resultats
    )

def test_recherche_globale_par_categorie():
    resultats = rechercher_global("Marché")

    assert isinstance(resultats, list)
    assert len(resultats) > 0

    # La catégorie est le 3e élément retourné par la requête SQL
    assert any(
        resultat[3] == "Marché"
        for resultat in resultats
    )

def test_recherche_globale_par_pays():
    resultats = rechercher_global("France")

    assert isinstance(resultats, list)
    assert len(resultats) > 0

    # Une recherche par pays doit retrouver un lieu rattaché à ce pays.
    assert any(
        resultat[1] == "Marché de Saint-Pierre"
        for resultat in resultats
    )

def test_recherche_globale_par_description():
    resultats = rechercher_global("automatisés")

    assert isinstance(resultats, list)
    assert len(resultats) > 0

    assert any(
        resultat[1] == "Marché de Saint-Pierre"
        for resultat in resultats
    )

def test_recherche_globale_par_tag():
    resultats = rechercher_global("Producteurs locaux")

    assert isinstance(resultats, list)
    assert len(resultats) > 0

    ids = [resultat[0] for resultat in resultats]

    assert 1 in ids
    assert ids.count(1) == 1

def test_recherche_globale_par_service():
    resultats = rechercher_global("Parking")

    assert isinstance(resultats, list)
    assert len(resultats) > 0

    ids = [resultat[0] for resultat in resultats]

    assert 1 in ids
    assert ids.count(1) == 1


def test_rechercher_global_erreur(monkeypatch):
    class FausseConnexion:
        def cursor(self):
            raise psycopg.Error("Erreur simulée")

        def close(self):
            pass

    monkeypatch.setattr(database, "connexion_db", lambda: FausseConnexion())

    resultat = database.rechercher_global("test")

    assert resultat == []

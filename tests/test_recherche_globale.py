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

def test_recherche_globale_par_territoire():
    resultats = rechercher_global("Réunion")

    assert isinstance(resultats, list)
    assert len(resultats) > 0

    # Une recherche par territoire doit retrouver un lieu rattaché à ce territoire.
    assert any(
        resultat[1] == "Marché de Saint-Pierre"
        for resultat in resultats
    )


def test_recherche_globale_priorise_ville_exacte():
    resultats = rechercher_global("Saint-Pierre")

    assert len(resultats) > 0

    # Une correspondance exacte sur la ville doit être prioritaire.
    assert resultats[0][2] == "Saint-Pierre"

def test_recherche_globale_tolere_faute_sur_ville():
    resultats = rechercher_global("Saint Piere")

    assert len(resultats) > 0

    # Une faute légère doit tout de même retrouver Saint-Pierre en priorité.
    assert resultats[0][2] == "Saint-Pierre"


def test_recherche_globale_tolere_faute_sur_territoire():
    resultats = rechercher_global("Réunoin")

    assert len(resultats) > 0

    # Une faute légère sur le territoire doit retrouver un lieu de La Réunion.
    assert any(
        resultat[1] == "Marché de Saint-Pierre"
        for resultat in resultats
    )

def test_recherche_globale_rejette_terme_sans_rapport():
    resultats = rechercher_global("Xyzqwerty")

    assert resultats == []

def test_recherche_globale_ville_exacte_filtre_resultats():
    resultats = rechercher_global("Saint-Pierre")

    assert len(resultats) > 0

    # Si une ville correspond exactement au terme recherché,
    # les résultats doivent être limités à cette ville.
    assert all(
        resultat[2] == "Saint-Pierre"
        for resultat in resultats
    )

def test_recherche_globale_tolere_faute_saint_piere():
    resultats = rechercher_global("Saint Piere")

    assert isinstance(resultats, list)
    assert len(resultats) > 0

    # Malgré la faute, Saint-Pierre doit être le résultat le plus pertinent.
    assert resultats[0][2] == "Saint-Pierre"
    assert resultats[0][7] > 0.70

def test_recherche_globale_tolere_faute_reunoin():
    resultats = rechercher_global("Réunoin")

    assert isinstance(resultats, list)
    assert len(resultats) > 0

    # Malgré la faute, un lieu de La Réunion doit être retrouvé.
    assert any(
        resultat[2] == "Saint-Pierre"
        for resultat in resultats
    )


def test_recherche_globale_tolere_faute_sur_pays():
    resultats = rechercher_global("Frnace")

    assert isinstance(resultats, list)
    assert len(resultats) > 0

    # Malgré la faute, un lieu rattaché à la France doit être retrouvé.
    assert any(
        resultat[2] == "Saint-Pierre"
        for resultat in resultats
    )

def test_recherche_globale_tolere_faute_sur_categorie():
    resultats = rechercher_global("March")

    assert isinstance(resultats, list)
    assert len(resultats) > 0

    # Malgré la faute, la catégorie Marché doit permettre de retrouver le lieu.
    assert any(
        resultat[1] == "Marché de Saint-Pierre"
        for resultat in resultats
    )

def test_recherche_globale_tolere_faute_sur_tag():
    resultats = rechercher_global("Producteur locaux")

    assert isinstance(resultats, list)
    assert len(resultats) > 0

    # Malgré la faute, le tag Producteurs locaux doit retrouver le lieu.
    assert any(
        resultat[1] == "Marché de Saint-Pierre"
        for resultat in resultats
    )

def test_recherche_globale_tolere_faute_sur_service():
    resultats = rechercher_global("Parkng")

    assert isinstance(resultats, list)
    assert len(resultats) > 0

    # Malgré la faute, le service Parking doit retrouver le lieu.
    assert any(
        resultat[1] == "Marché de Saint-Pierre"
        for resultat in resultats
    )

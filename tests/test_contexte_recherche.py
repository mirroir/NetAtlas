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

def test_contexte_recherche_erreur_sql(monkeypatch):
    import database

    class FauxCurseur:
        def execute(self, requete, parametres):
            raise database.psycopg.Error("Erreur SQL simulée")

        def close(self):
            pass

    class FausseConnexion:
        def __init__(self):
            self.fermee = False

        def cursor(self):
            return FauxCurseur()

        def close(self):
            self.fermee = True

    connexion = FausseConnexion()

    monkeypatch.setattr(database, "connexion_db", lambda: connexion)

    resultat = database.get_contexte_recherche("Marché")

    assert isinstance(resultat, dict)
    assert connexion.fermee is True

def test_get_territoires_par_categorie_et_pays_erreur_sql(monkeypatch):
    import database

    class FauxCurseur:
        def execute(self, requete, parametres):
            raise database.psycopg.Error("Erreur SQL simulée")

        def close(self):
            pass

    class FausseConnexion:
        def __init__(self):
            self.fermee = False

        def cursor(self):
            return FauxCurseur()

        def close(self):
            self.fermee = True

    connexion = FausseConnexion()

    monkeypatch.setattr(database, "connexion_db", lambda: connexion)

    resultat = database.get_territoires_par_categorie_et_pays(
        "Marché", "France"
    )

    assert resultat == []
    assert connexion.fermee is True


def test_get_villes_par_categorie_pays_territoire_erreur_sql(monkeypatch):
    import database

    class FauxCurseur:
        def execute(self, requete, parametres):
            raise database.psycopg.Error("Erreur SQL simulée")

        def close(self):
            pass

    class FausseConnexion:
        def __init__(self):
            self.fermee = False

        def cursor(self):
            return FauxCurseur()

        def close(self):
            self.fermee = True

    connexion = FausseConnexion()

    monkeypatch.setattr(database, "connexion_db", lambda: connexion)

    resultat = database.get_villes_par_categorie_pays_territoire(
        "Marché", "France", "La Réunion"
    )

    assert resultat == []
    assert connexion.fermee is True


def test_get_lieux_par_categorie_pays_territoire_ville_erreur_sql(monkeypatch):
    import database

    class FauxCurseur:
        def execute(self, requete, parametres):
            raise database.psycopg.Error("Erreur SQL simulée")

        def close(self):
            pass

    class FausseConnexion:
        def __init__(self):
            self.fermee = False

        def cursor(self):
            return FauxCurseur()

        def close(self):
            self.fermee = True

    connexion = FausseConnexion()

    monkeypatch.setattr(database, "connexion_db", lambda: connexion)

    resultat = database.get_lieux_par_categorie_pays_territoire_ville(
        "Marché", "France", "La Réunion", "Saint-Pierre"
    )

    assert resultat == []
    assert connexion.fermee is True



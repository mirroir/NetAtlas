import pathlib
import sys

sys.path.append(str(pathlib.Path(__file__).resolve().parents[1] / "python"))

import database


def test_get_place_tags_avec_tags():
    tags = database.get_place_tags(1)


    assert tags == [
            "Marché forain",
            "Producteurs locaux",
            "Produits frais",
            ]


def test_get_place_tags_sans_tag():
    tags = database.get_place_tags(2)

    assert tags == []


def test_get_place_tags_erreur_sql(monkeypatch):
    class FauxCurseur:
        def execute(self, requete, params):
            raise database.psycopg.Error("Erreur SQL simulée")

        def close(self):
            pass

    class FausseConnexion:
        def cursor(self):
            return FauxCurseur()

        def close(self):
            pass

    monkeypatch.setattr(database, "connexion_db", lambda: FausseConnexion())

    tags = database.get_place_tags(1)

    assert tags == []




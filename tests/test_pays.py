import psycopg

import database
from database import get_pays


def test_get_pays():
    pays = get_pays()

    assert isinstance(pays, list)
    assert len(pays) > 0


def test_get_pays_erreur(monkeypatch):
    class FausseConnexion:
        def cursor(self):
            raise psycopg.Error("Erreur simulée")

        def close(self):
            pass

    monkeypatch.setattr(database, "connexion_db", lambda: FausseConnexion())

    resultat = database.get_pays()

    assert resultat == []

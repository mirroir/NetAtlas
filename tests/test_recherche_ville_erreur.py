import psycopg

import database


class FauxCurseur:
    def execute(self, *args, **kwargs):
        raise psycopg.Error("Erreur SQL simulée")


class FausseConnexion:
    def cursor(self):
        return FauxCurseur()

    def close(self):
        pass


def test_rechercher_ville_gere_erreur_sql(monkeypatch):
    monkeypatch.setattr(
        database,
        "connexion_db",
        lambda: FausseConnexion()
    )

    resultat = database.rechercher_ville("Saint-Pierre")

    assert resultat == []

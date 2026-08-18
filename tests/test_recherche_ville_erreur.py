import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent / "python"))

import database


class FauxCurseur:
    def execute(self, *args, **kwargs):
        raise Exception("Erreur SQL simulée")


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

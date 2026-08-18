import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent / "python"))

import database
from database import rechercher_lieux_par_ville


def test_rechercher_lieux_par_ville():
    lieux = rechercher_lieux_par_ville("Saint-Pierre")

    assert isinstance(lieux, list)
    assert len(lieux) > 0

def test_rechercher_lieux_par_ville_erreur(monkeypatch):
    class FausseConnexion:
        def cursor(self):
            raise Exception("Erreur simulée")

        def close(self):
            pass

    monkeypatch.setattr(database, "connexion_db", lambda: FausseConnexion())

    resultat = database.rechercher_lieux_par_ville("Saint-Pierre")

    assert resultat == []

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent / "python"))

import database
from database import rechercher_global


def test_recherche_globale_par_ville():
    resultats = rechercher_global("Saint-Pierre")

    assert isinstance(resultats, list)
    assert len(resultats) > 0

    # La ville est le 2e élément retourné par la requête SQL
    assert any(
        resultat[1] == "Saint-Pierre"
        for resultat in resultats
    )

def test_rechercher_global_erreur(monkeypatch):
    class FausseConnexion:
        def cursor(self):
            raise Exception("Erreur simulée")

        def close(self):
            pass

    monkeypatch.setattr(database, "connexion_db", lambda: FausseConnexion())

    resultat = database.rechercher_global("test")

    assert resultat == []

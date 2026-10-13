import pathlib
import sys

sys.path.append(str(pathlib.Path(__file__).resolve().parents[1] / "python"))

import database


def test_get_pays_par_categorie_erreur_sql(monkeypatch):
    connexions = []

    class FauxCurseur:
        def execute(self, requete, parametres):
            raise database.psycopg.Error("Erreur SQL simulée")

        def fetchall(self):
            return []

        def close(self):
            pass

    class FausseConnexion:
        def cursor(self):
            return FauxCurseur()

        def close(self):
            connexions.append("fermée")

    monkeypatch.setattr(
        database,
        "connexion_db",
        lambda: FausseConnexion(),
    )

    resultat = database.get_pays_par_categorie("Marché")

    assert resultat == []
    assert connexions == ["fermée"]

import pytest


@pytest.mark.parametrize(
    "fonction, arguments",
    [
        (
            database.get_regions_par_categorie_et_pays,
            ("Marché", "France"),
        ),
        (
            database.get_villes_par_categorie_pays_region,
            ("Marché", "France", "Sud"),
        ),
        (
            database.get_lieux_par_categorie_pays_region_ville,
            ("Marché", "France", "Sud", "Saint-Pierre"),
        ),
    ],
)
def test_recherches_geographiques_erreur_sql(
    monkeypatch, fonction, arguments
):
    connexions = []

    class FauxCurseur:
        def execute(self, requete, parametres):
            raise database.psycopg.Error("Erreur SQL simulée")

        def close(self):
            pass

    class FausseConnexion:
        def cursor(self):
            return FauxCurseur()

        def close(self):
            connexions.append("fermée")

    monkeypatch.setattr(
        database,
        "connexion_db",
        lambda: FausseConnexion(),
    )

    resultat = fonction(*arguments)

    assert resultat == []
    assert connexions == ["fermée"]



import pathlib
import sys

sys.path.append(str(pathlib.Path(__file__).resolve().parents[1] / "python"))

import database


def test_get_place_services_avec_services():
    services = database.get_place_services(1)

    assert services == ["Parking", "Accès PMR", "Toilettes"]

def test_get_place_services_sans_service():
    services = database.get_place_services(9999)

    assert services == []


def test_get_place_services_erreur_sql(monkeypatch):
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
            pass

    monkeypatch.setattr(database, "connexion_db", lambda: FausseConnexion())

    services = database.get_place_services(1)

    assert services == []




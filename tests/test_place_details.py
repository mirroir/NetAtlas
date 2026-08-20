from database import get_place_details


def test_get_place_details_retourne_un_lieu():
    place = get_place_details(1)

    assert place is not None
    assert place[0] == 1
    assert place[1] == "Marché de Saint-Pierre"
    assert place[10] == "Saint-Pierre"
    assert place[11] == "Marché"

def test_get_place_details_id_inexistant():
    place = get_place_details(9999)

    assert place is None


def test_get_place_details_erreur_sql(monkeypatch):
    import database

    class FausseConnexion:
        def cursor(self):
            raise database.psycopg.Error("Erreur SQL simulée")

        def close(self):
            pass

    monkeypatch.setattr(
        database,
        "connexion_db",
        lambda: FausseConnexion(),
    )

    resultat = database.get_place_details(4)

    assert resultat is None



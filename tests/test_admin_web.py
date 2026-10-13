import sys
from pathlib import Path
from unittest.mock import patch

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from web.app import app


def test_admin_visiteur_non_connecte():
    with app.test_client() as client:
        reponse = client.get("/admin")

    assert reponse.status_code == 302
    assert "/connexion/admin" in reponse.location


def test_admin_utilisateur_classique_refuse():
    with app.test_client() as client:
        with client.session_transaction() as session:
            session["user_id"] = 3
            session["nom"] = "UtilisateurTest"
            session["role"] = "utilisateur"

        reponse = client.get("/admin")

    assert reponse.status_code == 302
    assert "/connexion/admin" in reponse.location


def test_admin_acces_autorise():
    with app.test_client() as client:
        with client.session_transaction() as session:
            session["user_id"] = 2
            session["nom"] = "AdminNetAtlas"
            session["role"] = "admin"

        reponse = client.get("/admin")

    assert reponse.status_code == 200
    assert b"Espace Administrateur" in reponse.data


def test_admin_connexion_pin_incorrect():
    with patch(
        "web.app.authentifier_utilisateur",
        return_value=None,
    ) as authentifier, app.test_client() as client:
        reponse = client.post(
            "/connexion/admin",
            data={
                "nom": "AdminNetAtlas",
                "pin": "0000",
            },
        )

    assert reponse.status_code == 200
    assert b"PIN incorrect" in reponse.data
    authentifier.assert_called_once_with(
        "AdminNetAtlas", "0000", "admin"
    )


def test_admin_connexion_reussie():
    administrateur = {
        "user_id": 2,
        "nom": "AdminNetAtlas",
        "role": "admin",
    }

    with patch(
        "web.app.authentifier_utilisateur",
        return_value=administrateur,
    ), app.test_client() as client:
        reponse = client.post(
            "/connexion/admin",
            data={
                "nom": "AdminNetAtlas",
                "pin": "2580",
            },
        )

        with client.session_transaction() as session:
            assert session["user_id"] == 2
            assert session["role"] == "admin"

    assert reponse.status_code == 302
    assert "/admin" in reponse.location



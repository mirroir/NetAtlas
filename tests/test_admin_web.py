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


def test_admin_connexion_pin_incorrect(csrf_data):
    with patch(
        "web.app.authentifier_utilisateur",
        return_value=None,
    ) as authentifier, app.test_client() as client:
        donnees_csrf = csrf_data(client)
        reponse = client.post(
            "/connexion/admin",
            data={
                "nom": "AdminNetAtlas",
                "pin": "0000",
                "csrf_token": donnees_csrf["csrf_token"],
            },
        )

    assert reponse.status_code == 200
    assert b"PIN incorrect" in reponse.data
    authentifier.assert_called_once_with(
        "AdminNetAtlas", "0000", "admin"
    )


def test_admin_connexion_reussie(csrf_data):
    administrateur = {
        "user_id": 2,
        "nom": "AdminNetAtlas",
        "role": "admin",
    }

    with patch(
        "web.app.authentifier_utilisateur",
        return_value=administrateur,
    ), app.test_client() as client:
        donnees_csrf = csrf_data(client)
        reponse = client.post(
            "/connexion/admin",
            data={
                "nom": "AdminNetAtlas",
                "pin": "2580",
                "csrf_token": donnees_csrf["csrf_token"],
            },
        )

        with client.session_transaction() as session:
            assert session["user_id"] == 2
            assert session["role"] == "admin"

    assert reponse.status_code == 302
    assert "/admin" in reponse.location

def test_administrateur_refuse_espace_utilisateur():
    with app.test_client() as client:
        with client.session_transaction() as session:
            session["user_id"] = 2
            session["nom"] = "AdminNetAtlas"
            session["role"] = "admin"

        reponse = client.get("/utilisateur")

    assert reponse.status_code == 302
    assert "/connexion/utilisateur" in reponse.location

def test_utilisateur_connecte_acces_espace():
    with app.test_client() as client:
        with client.session_transaction() as session:
            session["user_id"] = 3
            session["nom"] = "UtilisateurTest"
            session["role"] = "utilisateur"

        reponse = client.get("/utilisateur")

    assert reponse.status_code == 200

def test_admin_refuse_recherche_utilisateur():
    with app.test_client() as client:
        with client.session_transaction() as session:
            session["user_id"] = 2
            session["nom"] = "AdminNetAtlas"
            session["role"] = "admin"

        reponse = client.get("/recherche/globale/utilisateur")

    assert reponse.status_code == 302
    assert "/connexion/utilisateur" in reponse.location


def test_utilisateur_autorise_recherche_globale():
    with app.test_client() as client:
        with client.session_transaction() as session:
            session["user_id"] = 3
            session["nom"] = "UtilisateurTest"
            session["role"] = "utilisateur"

        reponse = client.get("/recherche/globale/utilisateur")

    assert reponse.status_code == 200

def test_admin_refuse_ajout_commentaire(csrf_data):
    with patch(
        "web.app.get_place_details",
        return_value={"id": 1, "name": "LieuTest"},
    ), patch(
        "web.app.ajouter_avis",
    ) as ajouter_avis, app.test_client() as client:
        with client.session_transaction() as session:
            session["user_id"] = 2
            session["nom"] = "AdminNetAtlas"
            session["role"] = "admin"

        donnees_csrf = csrf_data(client)

        reponse = client.post(
            "/lieu/1/utilisateur",
            data={
                "action": "commentaire",
                "commentaire": "Test securite NetAtlas",
                "csrf_token": donnees_csrf["csrf_token"],
            },
        )

    assert reponse.status_code == 302
    assert "/connexion/utilisateur" in reponse.location
    ajouter_avis.assert_not_called()

def test_admin_refuse_reaction_lieu(csrf_data):
    with (
        patch("web.app.enregistrer_reaction") as enregistrer,
        app.test_client() as client,
    ):
        with client.session_transaction() as session:
            session["user_id"] = 2
            session["nom"] = "AdminNetAtlas"
            session["role"] = "admin"
        donnees_csrf = csrf_data(client)
        reponse = client.post(
            "/lieu/1/reaction",
            data={
                "reaction": "1",
                "source": "recherche",
                "csrf_token": donnees_csrf["csrf_token"],
            },
        )

    assert reponse.status_code == 302
    assert "/connexion/utilisateur" in reponse.location
    enregistrer.assert_not_called()

def test_generation_jeton_csrf(csrf_data):
    with app.test_client() as client:
        donnees = csrf_data(client)

    assert "csrf_token" in donnees
    assert len(donnees["csrf_token"]) > 20

def test_admin_connexion_sans_jeton_csrf():
    app.config["TESTING"] = True

    with app.test_client() as client:
        reponse = client.post(
            "/connexion/admin",
            data={"pin": "0000"},
        )

    assert reponse.status_code == 400

def test_admin_connexion_jeton_csrf_invalide():
    app.config["TESTING"] = True

    with app.test_client() as client:
        reponse = client.post(
            "/connexion/admin",
            data={
                "pin": "0000",
                "csrf_token": "jeton_invalide_netatlas",
            },
        )

    assert reponse.status_code == 400



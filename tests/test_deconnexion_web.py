"""Tests de sécurité de la déconnexion Web NetAtlas."""

from web.app import app


def test_deconnexion_get_refuse():
    """Une requête GET ne doit pas déconnecter l'utilisateur."""

    with app.test_client() as client:
        with client.session_transaction() as session:
            session["user_id"] = 1
            session["nom"] = "UtilisateurTest"
            session["role"] = "utilisateur"

        reponse = client.get("/deconnexion")

        assert reponse.status_code == 405

        with client.session_transaction() as session:
            assert session["user_id"] == 1


def test_deconnexion_post_sans_csrf_refuse():
    """Une déconnexion sans jeton CSRF doit être refusée."""

    with app.test_client() as client:
        reponse = client.post("/deconnexion")

        assert reponse.status_code == 400


def test_deconnexion_post_csrf_invalide_refuse():
    """Une déconnexion avec un jeton CSRF invalide doit être refusée."""

    with app.test_client() as client:
        reponse = client.post(
            "/deconnexion",
            data={"csrf_token": "jeton_invalide_netatlas"},
        )

        assert reponse.status_code == 400


def test_deconnexion_post_valide_supprime_session(csrf_data):
    """Une déconnexion autorisée doit supprimer la session Flask."""

    with app.test_client() as client:
        donnees_csrf = csrf_data(client)

        with client.session_transaction() as session:
            session["user_id"] = 1
            session["nom"] = "UtilisateurTest"
            session["role"] = "utilisateur"

        reponse = client.post(
            "/deconnexion",
            data={"csrf_token": donnees_csrf["csrf_token"]},
            follow_redirects=False,
        )

        assert reponse.status_code == 302

        with client.session_transaction() as session:
            assert session.get("user_id") is None
            assert session.get("nom") is None
            assert session.get("role") is None


def test_deconnexion_admin_interdit_acces_apres_sortie(csrf_data):
    """Un administrateur déconnecté ne doit plus accéder à son espace."""

    with app.test_client() as client:
        donnees_csrf = csrf_data(client)

        with client.session_transaction() as session:
            session["user_id"] = 2
            session["nom"] = "AdminNetAtlas"
            session["role"] = "admin"

        reponse = client.post(
            "/deconnexion",
            data={"csrf_token": donnees_csrf["csrf_token"]},
        )

        assert reponse.status_code == 302

        acces_admin = client.get("/admin", follow_redirects=False)

        assert acces_admin.status_code == 302
        assert "/connexion/admin" in acces_admin.headers["Location"]

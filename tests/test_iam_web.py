"""Tests de sécurité de l'intégration IAM dans Flask."""

from web.app import app


def test_admin_refuse_session_flask_sans_cookie_iam():
    """Une ancienne session Flask ne doit pas autoriser l'administration."""

    with app.test_client() as client:
        with client.session_transaction() as session:
            session["user_id"] = 2
            session["nom"] = "AdminNetAtlas"
            session["role"] = "admin"

        reponse = client.get(
            "/admin",
            follow_redirects=False,
        )

        assert reponse.status_code == 302
        assert "/connexion/admin" in reponse.headers["Location"]


def test_admin_accepte_session_iam_valide(monkeypatch):
    """Une session IAM valide avec rôle admin autorise l'accès."""

    def simuler_validation(jeton):
        assert jeton == "jeton_iam_test"
        return {
            "user_id": 2,
            "nom": "AdminNetAtlas",
        }

    def simuler_role(user_id, role_nom):
        assert user_id == 2
        assert role_nom == "admin"
        return {
            "user_id": 2,
            "nom": "AdminNetAtlas",
            "role": "admin",
        }

    monkeypatch.setattr(
        "web.app.valider_session_iam",
        simuler_validation,
    )
    monkeypatch.setattr(
        "web.app.get_utilisateur_webauthn",
        simuler_role,
    )

    with app.test_client() as client:
        client.set_cookie("netatlas_iam", "jeton_iam_test")

        reponse = client.get("/admin")

        assert reponse.status_code == 200


def test_admin_refuse_session_iam_sans_role_admin(monkeypatch):
    """Une session IAM valide ne suffit pas sans le rôle admin."""

    def simuler_validation(jeton):
        assert jeton == "jeton_iam_test"
        return {
            "user_id": 3,
            "nom": "UtilisateurTest",
        }

    def simuler_role(user_id, role_nom):
        assert user_id == 3
        assert role_nom == "admin"

    monkeypatch.setattr(
        "web.app.valider_session_iam",
        simuler_validation,
    )
    monkeypatch.setattr(
        "web.app.get_utilisateur_webauthn",
        simuler_role,
    )

    with app.test_client() as client:
        client.set_cookie("netatlas_iam", "jeton_iam_test")

        reponse = client.get(
            "/admin",
            follow_redirects=False,
        )

        assert reponse.status_code == 302
        assert "/connexion/admin" in reponse.headers["Location"]

def test_cache_iam_verifie_separement_les_roles(monkeypatch):
    """Chaque rôle IAM est contrôlé et mémorisé indépendamment."""

    from flask import g

    from web.app import obtenir_utilisateur_iam

    roles_verifies = []

    def simuler_validation(jeton):
        assert jeton == "jeton_iam_test"
        return {
            "user_id": 3,
            "nom": "UtilisateurTest",
        }

    def simuler_role(user_id, role_nom):
        assert user_id == 3
        roles_verifies.append(role_nom)

        if role_nom == "utilisateur":
            return {
                "user_id": 3,
                "nom": "UtilisateurTest",
                "role": "utilisateur",
            }

    monkeypatch.setattr(
        "web.app.valider_session_iam",
        simuler_validation,
    )
    monkeypatch.setattr(
        "web.app.get_utilisateur_webauthn",
        simuler_role,
    )

    with app.test_request_context(
        "/utilisateur",
        headers={"Cookie": "netatlas_iam=jeton_iam_test"},
    ):
        premier = obtenir_utilisateur_iam("utilisateur")
        administrateur = obtenir_utilisateur_iam("admin")
        second = obtenir_utilisateur_iam("utilisateur")

        assert premier is not None
        assert premier["role"] == "utilisateur"
        assert administrateur is None
        assert second == premier
        assert roles_verifies == ["utilisateur", "admin"]
        assert g.utilisateurs_iam["admin"] is None


def test_iam_valide_jeton_une_seule_fois_par_requete(monkeypatch):
    """Deux contrôles de rôles ne revalident pas le même jeton."""

    from web.app import obtenir_utilisateur_iam

    validations = []
    roles = []

    def simuler_validation(jeton):
        validations.append(jeton)
        return {"user_id": 3, "nom": "UtilisateurTest"}

    def simuler_role(user_id, role_nom):
        assert user_id == 3
        roles.append(role_nom)

        if role_nom == "utilisateur":
            return {
                "user_id": 3,
                "nom": "UtilisateurTest",
                "role": "utilisateur",
            }

    monkeypatch.setattr(
        "web.app.valider_session_iam",
        simuler_validation,
    )
    monkeypatch.setattr(
        "web.app.get_utilisateur_webauthn",
        simuler_role,
    )

    with app.test_request_context(
        "/utilisateur",
        headers={"Cookie": "netatlas_iam=jeton_iam_test"},
    ):
        assert obtenir_utilisateur_iam("utilisateur") is not None
        assert obtenir_utilisateur_iam("admin") is None
        assert obtenir_utilisateur_iam("utilisateur") is not None

    assert validations == ["jeton_iam_test"]
    assert roles == ["utilisateur", "admin"]


def test_admin_refuse_jeton_iam_invalide(monkeypatch):
    """Un jeton invalide ne déclenche aucune vérification de rôle."""

    def simuler_validation(jeton):
        assert jeton == "jeton_invalide"

    def interdire_verification_role(user_id, role_nom):
        raise AssertionError(
            "Aucune vérification de rôle attendue pour un jeton invalide."
        )

    monkeypatch.setattr(
        "web.app.valider_session_iam",
        simuler_validation,
    )
    monkeypatch.setattr(
        "web.app.get_utilisateur_webauthn",
        interdire_verification_role,
    )

    with app.test_client() as client:
        client.set_cookie("netatlas_iam", "jeton_invalide")

        reponse = client.get("/admin", follow_redirects=False)

        assert reponse.status_code == 302
        assert "/connexion/admin" in reponse.headers["Location"]


def test_iam_revalide_jeton_entre_deux_requetes(monkeypatch):
    """Une révocation doit être prise en compte à la requête suivante."""

    validations = []

    def simuler_validation(jeton):
        assert jeton == "jeton_iam_test"
        validations.append(jeton)

        if len(validations) == 1:
            return {"user_id": 2, "nom": "AdminNetAtlas"}

        return None

    def simuler_role(user_id, role_nom):
        assert user_id == 2
        assert role_nom == "admin"
        return {
            "user_id": 2,
            "nom": "AdminNetAtlas",
            "role": "admin",
        }

    monkeypatch.setattr(
        "web.app.valider_session_iam",
        simuler_validation,
    )
    monkeypatch.setattr(
        "web.app.get_utilisateur_webauthn",
        simuler_role,
    )

    with app.test_client() as client:
        client.set_cookie("netatlas_iam", "jeton_iam_test")

        premiere = client.get("/admin", follow_redirects=False)
        seconde = client.get("/admin", follow_redirects=False)

    assert premiere.status_code == 200
    assert seconde.status_code == 302
    assert "/connexion/admin" in seconde.headers["Location"]
    assert validations == ["jeton_iam_test", "jeton_iam_test"]


def test_deconnexion_revoque_session_iam(monkeypatch, csrf_data):
    """La déconnexion révoque le jeton IAM et supprime son cookie."""

    jetons_revoques = []

    def simuler_revocation(jeton):
        jetons_revoques.append(jeton)
        return True

    monkeypatch.setattr(
        "web.app.revoquer_session_iam",
        simuler_revocation,
        raising=False,
    )

    with app.test_client() as client:
        donnees_csrf = csrf_data(client)
        client.set_cookie("netatlas_iam", "jeton_iam_test")

        reponse = client.post(
            "/deconnexion",
            data={"csrf_token": donnees_csrf["csrf_token"]},
            follow_redirects=False,
        )

    assert reponse.status_code == 302
    assert jetons_revoques == ["jeton_iam_test"]
    assert "netatlas_iam=" in reponse.headers.get("Set-Cookie", "")


def test_deconnexion_sans_jeton_iam_ne_revoque_pas(monkeypatch, csrf_data):
    """Une déconnexion sans cookie IAM ne sollicite pas PostgreSQL."""

    def interdire_revocation(jeton):
        raise AssertionError(
            "Aucune révocation attendue sans cookie IAM."
        )

    monkeypatch.setattr(
        "web.app.revoquer_session_iam",
        interdire_revocation,
        raising=False,
    )

    with app.test_client() as client:
        donnees_csrf = csrf_data(client)

        reponse = client.post(
            "/deconnexion",
            data={"csrf_token": donnees_csrf["csrf_token"]},
            follow_redirects=False,
        )

    assert reponse.status_code == 302

def test_deconnexion_echec_postgresql_refuse(monkeypatch, csrf_data):
    """Une erreur PostgreSQL ne doit pas annoncer une déconnexion réussie."""

    def simuler_erreur_postgresql(jeton):
        raise RuntimeError("PostgreSQL indisponible")

    monkeypatch.setattr(
        "web.app.revoquer_session_iam",
        simuler_erreur_postgresql,
    )

    with app.test_client() as client:
        donnees_csrf = csrf_data(client)
        client.set_cookie("netatlas_iam", "a" * 64)

        reponse = client.post(
            "/deconnexion",
            data={"csrf_token": donnees_csrf["csrf_token"]},
        )

        assert reponse.status_code == 503
        assert reponse.get_json()["erreur"] == (
            "Déconnexion temporairement impossible."
        )

        assert client.get_cookie("netatlas_iam") is not None


def test_deconnexion_jeton_deja_revoque(monkeypatch, csrf_data):
    """Un jeton déjà révoqué ne bloque pas la déconnexion locale."""

    appels = []

    def simuler_revocation(jeton):
        appels.append(jeton)
        return False

    monkeypatch.setattr(
        "web.app.revoquer_session_iam",
        simuler_revocation,
    )

    with app.test_client() as client:
        donnees_csrf = csrf_data(client)
        client.set_cookie("netatlas_iam", "b" * 64)

        reponse = client.post(
            "/deconnexion",
            data={"csrf_token": donnees_csrf["csrf_token"]},
        )

        assert reponse.status_code == 302
        assert appels == ["b" * 64]
        assert client.get_cookie("netatlas_iam") is None


def test_deconnexion_supprime_cookie_iam(monkeypatch, csrf_data):
    """Une révocation réussie supprime réellement le cookie IAM."""

    monkeypatch.setattr(
        "web.app.revoquer_session_iam",
        lambda jeton: True,
    )

    with app.test_client() as client:
        donnees_csrf = csrf_data(client)
        client.set_cookie("netatlas_iam", "c" * 64)

        reponse = client.post(
            "/deconnexion",
            data={"csrf_token": donnees_csrf["csrf_token"]},
        )

        assert reponse.status_code == 302
        assert client.get_cookie("netatlas_iam") is None
        assert reponse.headers["Cache-Control"] == "no-store"

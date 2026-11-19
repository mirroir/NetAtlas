"""Tests de sécurité de l'intégration IAM dans Flask."""

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

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

def test_utilisateur_refuse_ancienne_session_flask_sans_iam():
    """Une ancienne session Flask seule ne donne plus accès à l'espace."""

    with app.test_client() as client:
        with client.session_transaction() as session:
            session["user_id"] = 3
            session["nom"] = "UtilisateurTest"
            session["role"] = "utilisateur"

        reponse = client.get("/utilisateur")

    assert reponse.status_code == 302
    assert "/connexion/utilisateur" in reponse.location


def test_utilisateur_accepte_identite_iam_valide(monkeypatch):
    """Une identité IAM utilisateur valide autorise l'espace."""

    def simuler_validation(jeton):
        assert jeton == "jeton_iam_test"
        return {"user_id": 3, "nom": "UtilisateurTest"}

    def simuler_role(user_id, role_nom):
        assert user_id == 3
        assert role_nom == "utilisateur"
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

    with app.test_client() as client:
        client.set_cookie("netatlas_iam", "jeton_iam_test")
        reponse = client.get("/utilisateur")

    assert reponse.status_code == 200
    assert b"UtilisateurTest" in reponse.data


def test_utilisateur_refuse_session_iam_revoquee(monkeypatch):
    """Un jeton IAM révoqué ou expiré ne donne aucun accès."""

    def simuler_validation(jeton):
        assert jeton == "jeton_iam_invalide"

    def interdire_verification_role(user_id, role_nom):
        raise AssertionError(
            "Aucun rôle ne doit être recherché après un rejet IAM."
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
        client.set_cookie("netatlas_iam", "jeton_iam_invalide")
        reponse = client.get("/utilisateur")

    assert reponse.status_code == 302
    assert "/connexion/utilisateur" in reponse.location

def test_commentaire_utilise_identite_iam_et_non_flask(
    monkeypatch,
    csrf_data,
):
    """Le commentaire appartient à l'identité IAM authentifiée."""

    from unittest.mock import patch

    def simuler_validation(jeton):
        assert jeton == "jeton_iam_test"
        return {"user_id": 8, "nom": "UtilisateurIAM"}

    def simuler_role(user_id, role_nom):
        assert user_id == 8
        assert role_nom == "utilisateur"
        return {
            "user_id": 8,
            "nom": "UtilisateurIAM",
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

    with (
        patch(
            "web.app.get_place_details",
            return_value={"id": 1, "name": "LieuTest"},
        ),
        patch("web.app.ajouter_avis") as ajouter_avis,
        app.test_client() as client,
    ):
        with client.session_transaction() as session:
            session["user_id"] = 3
            session["nom"] = "AncienUtilisateur"
            session["role"] = "utilisateur"

        donnees_csrf = csrf_data(client)
        client.set_cookie("netatlas_iam", "jeton_iam_test")

        reponse = client.post(
            "/lieu/1/utilisateur",
            data={
                "action": "commentaire",
                "commentaire": "Commentaire IAM sécurisé",
                "csrf_token": donnees_csrf["csrf_token"],
            },
        )

    assert reponse.status_code == 302
    ajouter_avis.assert_called_once_with(
        1,
        8,
        "Commentaire IAM sécurisé",
    )


def test_reaction_utilise_identite_iam_et_non_flask(
    monkeypatch,
    csrf_data,
):
    """La réaction appartient à l'identité IAM authentifiée."""

    from unittest.mock import patch

    def simuler_validation(jeton):
        assert jeton == "jeton_iam_test"
        return {"user_id": 8, "nom": "UtilisateurIAM"}

    def simuler_role(user_id, role_nom):
        assert user_id == 8
        assert role_nom == "utilisateur"
        return {
            "user_id": 8,
            "nom": "UtilisateurIAM",
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

    with (
        patch("web.app.enregistrer_reaction") as enregistrer,
        app.test_client() as client,
    ):
        with client.session_transaction() as session:
            session["user_id"] = 3
            session["nom"] = "AncienUtilisateur"
            session["role"] = "utilisateur"

        donnees_csrf = csrf_data(client)
        client.set_cookie("netatlas_iam", "jeton_iam_test")

        reponse = client.post(
            "/lieu/1/reaction",
            data={
                "reaction": "1",
                "source": "recherche",
                "csrf_token": donnees_csrf["csrf_token"],
            },
        )

    assert reponse.status_code == 302
    enregistrer.assert_called_once_with(1, 8, 1)

def test_iam_erreur_postgresql_validation_retourne_503(monkeypatch):
    """Une panne PostgreSQL pendant la validation IAM refuse l'accès."""

    import psycopg

    def simuler_panne(jeton):
        raise psycopg.OperationalError("Connexion PostgreSQL impossible")

    monkeypatch.setattr(
        "web.app.valider_session_iam",
        simuler_panne,
    )

    with app.test_client() as client:
        client.set_cookie("netatlas_iam", "a" * 64)
        reponse = client.get("/utilisateur")

    assert reponse.status_code == 503
    assert reponse.get_json() == {
        "erreur": "Service temporairement indisponible.",
    }
    assert reponse.headers["Cache-Control"] == "no-store"
    assert b"Connexion PostgreSQL impossible" not in reponse.data


def test_iam_erreur_postgresql_role_retourne_503(monkeypatch):
    """Une panne lors de la vérification du rôle refuse l'accès."""

    import psycopg

    def simuler_validation(jeton):
        assert jeton == "a" * 64
        return {"user_id": 3, "nom": "UtilisateurTest"}

    def simuler_panne_role(user_id, role_nom):
        assert user_id == 3
        assert role_nom == "utilisateur"
        raise psycopg.OperationalError("Lecture des rôles impossible")

    monkeypatch.setattr(
        "web.app.valider_session_iam",
        simuler_validation,
    )
    monkeypatch.setattr(
        "web.app.get_utilisateur_webauthn",
        simuler_panne_role,
    )

    with app.test_client() as client:
        client.set_cookie("netatlas_iam", "a" * 64)
        reponse = client.get("/utilisateur")

    assert reponse.status_code == 503
    assert reponse.get_json() == {
        "erreur": "Service temporairement indisponible.",
    }
    assert reponse.headers["Cache-Control"] == "no-store"
    assert b"Lecture des r" not in reponse.data


def test_iam_erreur_programmation_non_transformee_en_503(monkeypatch):
    """Une erreur Python ordinaire n'est pas assimilée à une panne SQL."""

    import pytest

    def simuler_erreur(jeton):
        raise RuntimeError("Erreur de programmation simulée")

    monkeypatch.setattr(
        "web.app.valider_session_iam",
        simuler_erreur,
    )

    monkeypatch.setitem(app.config, "TESTING", True)

    with app.test_client() as client:
        client.set_cookie("netatlas_iam", "a" * 64)

        with pytest.raises(
            RuntimeError,
            match="Erreur de programmation simulée",
        ):
            client.get("/utilisateur")


def test_iam_erreur_sql_non_operationnelle_retourne_500(monkeypatch):
    """Une erreur SQL non opérationnelle ne doit pas produire HTTP 503."""

    import psycopg

    def simuler_erreur_sql(jeton):
        assert jeton == "a" * 64
        raise psycopg.errors.SyntaxError(
            "Erreur SQL simulée : syntaxe invalide"
        )

    monkeypatch.setattr(
        "web.app.valider_session_iam",
        simuler_erreur_sql,
    )

    with app.test_client() as client:
        client.set_cookie("netatlas_iam", "a" * 64)
        reponse = client.get("/utilisateur")

    assert reponse.status_code == 500
    assert reponse.get_json() == {
        "erreur": "Erreur interne du service.",
    }
    assert reponse.headers["Cache-Control"] == "no-store"
    assert b"syntaxe invalide" not in reponse.data

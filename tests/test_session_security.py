import os
import subprocess
import sys

from web.app import app


def test_configuration_cookies_session():
    assert app.config["SESSION_COOKIE_HTTPONLY"] is True
    assert app.config["SESSION_COOKIE_SAMESITE"] == "Lax"

    assert app.config["SESSION_COOKIE_SECURE"] == (
        os.getenv("NETATLAS_WEB_HTTPS") == "1"
    )

def test_attributs_cookie_session():
    with app.test_client() as client:
        with client.session_transaction() as session:
            session["user_id"] = 1

        # Le cookie de session est émis pendant
        # la transaction qui modifie la session.
        cookie = client.get_cookie(
            app.config["SESSION_COOKIE_NAME"]
        )

    assert cookie is not None
    assert cookie.http_only is True
    assert cookie.same_site == "Lax"

def test_cookie_secure_en_https():
    ancienne_valeur = app.config["SESSION_COOKIE_SECURE"]

    try:
        app.config["SESSION_COOKIE_SECURE"] = True

        with app.test_client() as client:
            with client.session_transaction() as session:
                session["user_id"] = 1

            cookie = client.get_cookie(
                app.config["SESSION_COOKIE_NAME"]
            )

        assert cookie is not None
        assert cookie.secure is True

    finally:
        app.config["SESSION_COOKIE_SECURE"] = ancienne_valeur


def test_refus_production_sans_https():
    environnement = os.environ.copy()

    environnement["NETATLAS_WEB_ENV"] = "production"
    environnement["NETATLAS_WEB_HTTPS"] = "0"

    resultat = subprocess.run(
        [sys.executable, "-c", "import web.app"],
        env=environnement,
        capture_output=True,
        text=True,
        check=False,
    )

    assert resultat.returncode != 0
    assert (
        "HTTPS obligatoire en production."
        in resultat.stderr
    )

def test_production_avec_https_autorisee():
    environnement = os.environ.copy()

    environnement["NETATLAS_WEB_ENV"] = "production"
    environnement["NETATLAS_WEB_HTTPS"] = "1"

    resultat = subprocess.run(
        [sys.executable, "-c", "import web.app"],
        env=environnement,
        capture_output=True,
        text=True,
        check=False,
    )

    assert resultat.returncode == 0, resultat.stderr

def test_connexion_utilisateur_pin_refuse(csrf_data):
    """Un ancien formulaire PIN ne doit jamais ouvrir de session."""

    with app.test_client() as client:
        donnees_csrf = csrf_data(client)

        reponse = client.post(
            "/connexion/utilisateur",
            data={
                "nom": "UtilisateurTest",
                "pin": "1234",
                "csrf_token": donnees_csrf["csrf_token"],
            },
            follow_redirects=False,
        )

        with client.session_transaction() as session:
            assert session.get("user_id") is None
            assert session.get("role") is None

    assert reponse.status_code == 405


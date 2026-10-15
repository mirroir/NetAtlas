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

def test_nettoyage_session_apres_connexion(monkeypatch):
    import re
    from html import unescape

    def fausse_authentification(nom, pin, role):
        return {
            "user_id": 42,
            "nom": "Utilisateur Test",
            "role": "utilisateur",
        }

    monkeypatch.setattr(
        "web.app.authentifier_utilisateur",
        fausse_authentification,
    )

    with app.test_client() as client:

        # Préparer une session contenant d'anciennes données.
        with client.session_transaction() as session:
            session["ancienne_donnee"] = "a_supprimer"
            session["role"] = "ancien_role"

        # Récupérer le formulaire et son jeton CSRF.
        page = client.get("/connexion/utilisateur")

        assert page.status_code == 200

        contenu = page.get_data(as_text=True)

        correspondance = re.search(
            r'name="csrf_token"\s+value="([^"]+)"',
            contenu,
        )

        assert correspondance is not None

        csrf_token = unescape(correspondance.group(1))

        # Simuler une connexion avec un jeton CSRF valide.
        reponse = client.post(
            "/connexion/utilisateur",
            data={
                "nom": "Utilisateur Test",
                "pin": "1234",
                "csrf_token": csrf_token,
            },
            follow_redirects=False,
        )

        # Vérifier la redirection après authentification.
        assert reponse.status_code == 302

        # Vérifier que les anciennes données ont disparu.
        with client.session_transaction() as session:
            assert "ancienne_donnee" not in session

            assert session["user_id"] == 42
            assert session["nom"] == "Utilisateur Test"
            assert session["role"] == "utilisateur"



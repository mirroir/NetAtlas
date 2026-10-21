import hashlib
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from unittest.mock import patch

from web.app import app


def test_passkey_enregistrement_visiteur_refuse(csrf_data):
    """Un visiteur ne peut pas préparer une Passkey administrateur."""

    with app.test_client() as client:
        donnees_csrf = csrf_data(client)

        reponse = client.post(
            "/admin/passkey/enregistrement/options",
            data={
                "csrf_token": donnees_csrf["csrf_token"],
            },
        )

    assert reponse.status_code == 302
    assert "/connexion/admin" in reponse.location

def test_passkey_enregistrement_utilisateur_refuse(csrf_data):
    """Un utilisateur classique ne peut pas enregistrer une Passkey admin."""

    with app.test_client() as client:
        # Récupérer le jeton CSRF avant la connexion.
        donnees_csrf = csrf_data(client)

        # Simuler ensuite une session utilisateur classique.
        with client.session_transaction() as session:
            session["user_id"] = 3
            session["nom"] = "UtilisateurTest"
            session["role"] = "utilisateur"

        reponse = client.post(
            "/admin/passkey/enregistrement/options",
            data={
                "csrf_token": donnees_csrf["csrf_token"],
            },
        )

    assert reponse.status_code == 302
    assert "/connexion/admin" in reponse.location

def test_passkey_enregistrement_sans_csrf_refuse():
    """Un administrateur sans jeton CSRF est refusé."""

    with app.test_client() as client:
        with client.session_transaction() as session:
            session["user_id"] = 2
            session["nom"] = "AdminNetAtlas"
            session["role"] = "admin"

        reponse = client.post(
            "/admin/passkey/enregistrement/options"
        )

    assert reponse.status_code == 400

def test_passkey_enregistrement_admin_autorise(csrf_data):
    """Un administrateur peut préparer une Passkey."""

    with patch(
        "web.app.enregistrer_challenge_webauthn",
        return_value=1,
        create=True,
    ) as enregistrer, app.test_client() as client:

        donnees_csrf = csrf_data(client)

        with client.session_transaction() as session:
            session["user_id"] = 2
            session["nom"] = "AdminNetAtlas"
            session["role"] = "admin"

        reponse = client.post(
            "/admin/passkey/enregistrement/options",
            data={
                "csrf_token": donnees_csrf["csrf_token"],
            },
        )

        # Vérifier les données temporaires de la session WebAuthn.
        with client.session_transaction() as session:
            tentative = session["passkey_registration"]

            assert tentative["user_id"] == 2
            assert len(bytes.fromhex(tentative["challenge"])) >= 16
            assert len(bytes.fromhex(tentative["session_binding"])) == 32

    # Vérifier la réponse HTTP.
    assert reponse.status_code == 200

    options = reponse.get_json()

    assert options["rp"]["id"] == "netatlas.home.arpa"
    assert options["user"]["name"] == "AdminNetAtlas"
    assert options["challenge"]

    # Vérifier l'enregistrement du challenge.
    enregistrer.assert_called_once()

    arguments = enregistrer.call_args

    assert arguments.kwargs["operation"] == "registration"
    assert arguments.kwargs["user_id"] == 2

    assert len(arguments.kwargs["challenge_hash"]) == 32
    assert len(arguments.kwargs["session_binding_hash"]) == 32

    # Vérifier la correspondance des empreintes SHA-256.
    challenge = bytes.fromhex(tentative["challenge"])
    session_binding = bytes.fromhex(tentative["session_binding"])

    assert arguments.kwargs["challenge_hash"] == hashlib.sha256(
        challenge
    ).digest()

    assert arguments.kwargs["session_binding_hash"] == hashlib.sha256(
        session_binding
    ).digest()

def test_passkey_enregistrement_erreur_postgresql(csrf_data):
    """Un échec PostgreSQL empêche la préparation d'une Passkey."""

    with patch(
        "web.app.enregistrer_challenge_webauthn",
        side_effect=RuntimeError("Erreur PostgreSQL simulée"),
    ) as enregistrer, app.test_client() as client:

        donnees_csrf = csrf_data(client)

        with client.session_transaction() as session:
            session["user_id"] = 2
            session["nom"] = "AdminNetAtlas"
            session["role"] = "admin"

        reponse = client.post(
            "/admin/passkey/enregistrement/options",
            data={
                "csrf_token": donnees_csrf["csrf_token"],
            },
        )

        # Vérifier qu'aucune tentative n'a été créée.
        with client.session_transaction() as session:
            assert "passkey_registration" not in session

    # Flask transforme l'exception en erreur HTTP 500.
    assert reponse.status_code == 500

    # Aucun détail interne ne doit être exposé au navigateur.
    assert b"Erreur PostgreSQL simul" not in reponse.data

    # Vérifier que l'enregistrement a bien été tenté.
    enregistrer.assert_called_once()

def test_passkey_erreur_postgresql_invalide_ancienne_tentative(csrf_data):
    """Un échec PostgreSQL ne conserve pas une ancienne tentative."""

    with patch(
        "web.app.enregistrer_challenge_webauthn",
        side_effect=RuntimeError("Erreur PostgreSQL simulée"),
    ), app.test_client() as client:

        donnees_csrf = csrf_data(client)

        with client.session_transaction() as session:
            session["user_id"] = 2
            session["nom"] = "AdminNetAtlas"
            session["role"] = "admin"
            session["passkey_registration"] = {
                "challenge": "ancien_challenge",
                "session_binding": "ancienne_liaison",
                "user_id": 2,
            }

        reponse = client.post(
            "/admin/passkey/enregistrement/options",
            data=donnees_csrf,
        )

        assert reponse.status_code == 500

        with client.session_transaction() as session:
            assert "passkey_registration" not in session

def test_passkey_deux_demandes_successives(csrf_data):
    """Chaque demande remplace la tentative précédente."""

    with patch(
        "web.app.enregistrer_challenge_webauthn",
        return_value=1,
    ) as enregistrer, app.test_client() as client:

        donnees_csrf = csrf_data(client)

        with client.session_transaction() as session:
            session["user_id"] = 2
            session["nom"] = "AdminNetAtlas"
            session["role"] = "admin"

        premiere_reponse = client.post(
            "/admin/passkey/enregistrement/options",
            data=donnees_csrf,
        )

        with client.session_transaction() as session:
            premiere_tentative = dict(session["passkey_registration"])

        seconde_reponse = client.post(
            "/admin/passkey/enregistrement/options",
            data=donnees_csrf,
        )

        with client.session_transaction() as session:
            seconde_tentative = dict(session["passkey_registration"])

    assert premiere_reponse.status_code == 200
    assert seconde_reponse.status_code == 200

    assert (
        premiere_tentative["challenge"]
        != seconde_tentative["challenge"]
    )

    assert (
        premiere_tentative["session_binding"]
        != seconde_tentative["session_binding"]
    )

    assert seconde_tentative["user_id"] == 2

    assert enregistrer.call_count == 2

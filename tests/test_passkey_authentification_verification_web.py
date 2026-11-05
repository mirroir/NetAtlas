
"""Tests HTTP de vérification de l'authentification Passkey."""

import hashlib
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from webauthn.helpers import bytes_to_base64url

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from web.app import app

ROUTE = "/passkey/authentification/verifier"
CHALLENGE = b"c" * 32
SESSION_BINDING = b"b" * 32
CREDENTIAL_ID = b"credential-test"

CREDENTIAL = {
    "id": bytes_to_base64url(CREDENTIAL_ID),
    "rawId": bytes_to_base64url(CREDENTIAL_ID),
    "type": "public-key",
}

PASSKEY = {
    "user_id": 3,
    "credential_id": CREDENTIAL_ID,
    "public_key": b"cle-publique-test",
    "sign_count": 5,
}

UTILISATEUR = {
    "user_id": 3,
    "nom": "UtilisateurTest",
    "role": "utilisateur",
}


@pytest.fixture(autouse=True)
def autoriser_limiteur_passkey():
    """Isole les tests fonctionnels du limiteur de tentatives."""
    with patch(
        "web.app.verifier_limites_combinees_passkey",
        return_value=(True, 0),
    ):
        yield


def preparer_tentative(client):
    """Prépare une tentative Passkey non authentifiée."""
    with client.session_transaction() as session:
        session["passkey_authentication"] = {
            "challenge": CHALLENGE.hex(),
            "session_binding": SESSION_BINDING.hex(),
        }


def envoyer_verification(client, csrf, role="utilisateur", credential=None):
    """Envoie une réponse Passkey avec un jeton CSRF valide."""
    return client.post(
        ROUTE,
        json={
            "role": role,
            "credential": CREDENTIAL if credential is None else credential,
        },
        headers={"X-CSRFToken": csrf["csrf_token"]},
    )


def test_verification_sans_csrf_refuse():
    with app.test_client() as client:
        preparer_tentative(client)
        reponse = client.post(ROUTE, json={})

    assert reponse.status_code == 400


def test_verification_sans_tentative_refuse(csrf_data):
    with app.test_client() as client:
        csrf = csrf_data(client)
        reponse = envoyer_verification(client, csrf)

    assert reponse.status_code == 400


def test_verification_json_invalide_refuse(csrf_data):
    with app.test_client() as client:
        csrf = csrf_data(client)
        preparer_tentative(client)

        reponse = client.post(
            ROUTE,
            data="contenu-invalide",
            content_type="application/json",
            headers={"X-CSRFToken": csrf["csrf_token"]},
        )

    assert reponse.status_code == 400


def test_verification_role_invalide_refuse(csrf_data):
    with app.test_client() as client:
        csrf = csrf_data(client)
        preparer_tentative(client)

        reponse = envoyer_verification(client, csrf, role="superadmin")

    assert reponse.status_code == 400


def test_verification_passkey_inconnue_refuse(csrf_data):
    with (
        patch("web.app.get_credential_webauthn", return_value=None),
        patch("web.app.verifier_authentification") as verifier,
        app.test_client() as client,
    ):
        csrf = csrf_data(client)
        preparer_tentative(client)

        reponse = envoyer_verification(client, csrf)

    assert reponse.status_code == 403
    verifier.assert_not_called()


def test_verification_signature_invalide_refuse(csrf_data):
    with (
        patch("web.app.get_credential_webauthn", return_value=PASSKEY),
        patch(
            "web.app.verifier_authentification",
            side_effect=ValueError("Signature invalide"),
        ),
        patch("web.app.finaliser_authentification_webauthn") as finaliser,
        app.test_client() as client,
    ):
        csrf = csrf_data(client)
        preparer_tentative(client)

        reponse = envoyer_verification(client, csrf)

    assert reponse.status_code == 400
    finaliser.assert_not_called()


def test_verification_identifiant_incoherent_refuse(csrf_data):
    verification = SimpleNamespace(
        credential_id=b"autre-identifiant",
        new_sign_count=6,
    )

    with (
        patch("web.app.get_credential_webauthn", return_value=PASSKEY),
        patch(
            "web.app.verifier_authentification",
            return_value=verification,
        ),
        patch("web.app.finaliser_authentification_webauthn") as finaliser,
        app.test_client() as client,
    ):
        csrf = csrf_data(client)
        preparer_tentative(client)

        reponse = envoyer_verification(client, csrf)

    assert reponse.status_code == 400
    finaliser.assert_not_called()


def test_verification_transaction_refusee(csrf_data):
    verification = SimpleNamespace(
        credential_id=CREDENTIAL_ID,
        new_sign_count=6,
    )

    with (
        patch("web.app.get_credential_webauthn", return_value=PASSKEY),
        patch(
            "web.app.verifier_authentification",
            return_value=verification,
        ),
        patch(
            "web.app.finaliser_authentification_webauthn",
            return_value=False,
        ),
        app.test_client() as client,
    ):
        csrf = csrf_data(client)
        preparer_tentative(client)

        reponse = envoyer_verification(client, csrf)

        with client.session_transaction() as session:
            user_id = session.get("user_id")

    assert reponse.status_code == 403
    assert user_id is None


def test_verification_connexion_reussie(csrf_data):
    verification = SimpleNamespace(
        credential_id=CREDENTIAL_ID,
        new_sign_count=6,
    )

    with (
        patch("web.app.get_credential_webauthn", return_value=PASSKEY),
        patch(
            "web.app.verifier_authentification",
            return_value=verification,
        ) as verifier,
        patch(
            "web.app.finaliser_authentification_webauthn",
            return_value=UTILISATEUR,
        ) as finaliser,
        app.test_client() as client,
    ):
        csrf = csrf_data(client)
        preparer_tentative(client)

        # Vérifier que l'authentification Passkey
        # élimine les anciennes données de session.
        with client.session_transaction() as session:
            session["ancienne_donnee"] = "a_supprimer"
            session["role"] = "ancien_role"

        reponse = envoyer_verification(client, csrf)

        with client.session_transaction() as session:
            user_id = session.get("user_id")
            nom = session.get("nom")
            role = session.get("role")
            tentative = session.get("passkey_authentication")
            ancienne_donnee = session.get("ancienne_donnee")
    assert reponse.status_code == 200
    assert reponse.get_json()["redirect"] == "/utilisateur"
    assert user_id == 3
    assert nom == "UtilisateurTest"
    assert role == "utilisateur"
    assert tentative is None
    assert ancienne_donnee is None

    verifier.assert_called_once_with(
        credential=CREDENTIAL,
        challenge_attendu=CHALLENGE,
        cle_publique=PASSKEY["public_key"],
        compteur_actuel=5,
    )

    finaliser.assert_called_once_with(
        challenge_hash=hashlib.sha256(CHALLENGE).digest(),
        session_binding_hash=hashlib.sha256(SESSION_BINDING).digest(),
        credential_id=CREDENTIAL_ID,
        public_key=PASSKEY["public_key"],
        compteur_precedent=5,
        nouveau_compteur=6,
        role_nom="utilisateur",
    )

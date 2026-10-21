"""Tests Flask de finalisation des Passkeys administrateur."""

import hashlib
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from psycopg.errors import UniqueViolation

from web.app import app

ROUTE = "/admin/passkey/enregistrement/verifier"
CHALLENGE = b"a" * 32
SESSION_BINDING = b"b" * 32


def preparer_session(client, role="admin", user_id=2, tentative=True):
    """Prépare une session de test sans connexion réelle."""

    with client.session_transaction() as session:
        session["user_id"] = user_id
        session["nom"] = "AdminNetAtlas"
        session["role"] = role

        if tentative:
            session["passkey_registration"] = {
                "challenge": CHALLENGE.hex(),
                "session_binding": SESSION_BINDING.hex(),
                "user_id": user_id,
            }


def test_finalisation_visiteur_refuse(csrf_data):
    with app.test_client() as client:
        jeton = csrf_data(client)

        reponse = client.post(
            ROUTE,
            json={"id": "credential-test"},
            headers={"X-CSRFToken": jeton["csrf_token"]},
        )

    assert reponse.status_code == 302
    assert "/connexion/admin" in reponse.location


def test_finalisation_utilisateur_refuse(csrf_data):
    with app.test_client() as client:
        jeton = csrf_data(client)
        preparer_session(client, role="utilisateur")

        reponse = client.post(
            ROUTE,
            json={"id": "credential-test"},
            headers={"X-CSRFToken": jeton["csrf_token"]},
        )

    assert reponse.status_code == 302
    assert "/connexion/admin" in reponse.location


def test_finalisation_sans_csrf_refuse():
    with app.test_client() as client:
        preparer_session(client)

        reponse = client.post(
            ROUTE,
            json={"id": "credential-test"},
        )

    assert reponse.status_code == 400


def test_finalisation_sans_tentative_refuse(csrf_data):
    with app.test_client() as client:
        jeton = csrf_data(client)
        preparer_session(client, tentative=False)

        reponse = client.post(
            ROUTE,
            json={"id": "credential-test"},
            headers={"X-CSRFToken": jeton["csrf_token"]},
        )

    assert reponse.status_code == 400


def test_finalisation_autre_utilisateur_refuse(csrf_data):
    with app.test_client() as client:
        jeton = csrf_data(client)
        preparer_session(client)

        with client.session_transaction() as session:
            session["passkey_registration"]["user_id"] = 999

        reponse = client.post(
            ROUTE,
            json={"id": "credential-test"},
            headers={"X-CSRFToken": jeton["csrf_token"]},
        )

    assert reponse.status_code == 400


def test_finalisation_json_invalide(csrf_data):
    with app.test_client() as client:
        jeton = csrf_data(client)
        preparer_session(client)

        reponse = client.post(
            ROUTE,
            data="json-invalide",
            content_type="application/json",
            headers={"X-CSRFToken": jeton["csrf_token"]},
        )

    assert reponse.status_code == 400


@pytest.mark.parametrize(
    ("champ", "valeur"),
    [
        ("challenge", "hexadecimal-invalide"),
        ("session_binding", "court"),
    ],
)
def test_finalisation_tentative_invalide(csrf_data, champ, valeur):
    with app.test_client() as client:
        jeton = csrf_data(client)
        preparer_session(client)

        with client.session_transaction() as session:
            session["passkey_registration"][champ] = valeur

        reponse = client.post(
            ROUTE,
            json={"id": "credential-test"},
            headers={"X-CSRFToken": jeton["csrf_token"]},
        )

    assert reponse.status_code == 400


def test_finalisation_reussie(csrf_data):
    verification = SimpleNamespace(
        credential_id=b"credential-test",
        credential_public_key=b"public-key-test",
        sign_count=0,
    )

    with (
        patch(
            "web.app.verifier_enregistrement",
            return_value=verification,
        ) as verifier,
        patch(
            "web.app.finaliser_enregistrement_webauthn",
            return_value=42,
        ) as finaliser,
        app.test_client() as client,
    ):
        jeton = csrf_data(client)
        preparer_session(client)

        reponse = client.post(
            ROUTE,
            json={"id": "credential-test"},
            headers={"X-CSRFToken": jeton["csrf_token"]},
        )

        with client.session_transaction() as session:
            assert "passkey_registration" not in session

    assert reponse.status_code == 201
    assert reponse.get_json()["credential_id"] == 42

    verifier.assert_called_once_with(
        credential={"id": "credential-test"},
        challenge_attendu=CHALLENGE,
    )

    finaliser.assert_called_once_with(
        challenge_hash=hashlib.sha256(CHALLENGE).digest(),
        session_binding_hash=hashlib.sha256(SESSION_BINDING).digest(),
        user_id=2,
        credential_id=b"credential-test",
        public_key=b"public-key-test",
        sign_count=0,
    )


def test_finalisation_challenge_consomme(csrf_data):
    verification = SimpleNamespace(
        credential_id=b"credential-test",
        credential_public_key=b"public-key-test",
        sign_count=0,
    )

    with (
        patch("web.app.verifier_enregistrement", return_value=verification),
        patch(
            "web.app.finaliser_enregistrement_webauthn",
            return_value=False,
        ),
        app.test_client() as client,
    ):
        jeton = csrf_data(client)
        preparer_session(client)

        reponse = client.post(
            ROUTE,
            json={"id": "credential-test"},
            headers={"X-CSRFToken": jeton["csrf_token"]},
        )

    assert reponse.status_code == 400


def test_finalisation_erreur_cryptographique(csrf_data):
    with (
        patch(
            "web.app.verifier_enregistrement",
            side_effect=ValueError("Challenge invalide"),
        ),
        patch("web.app.finaliser_enregistrement_webauthn") as finaliser,
        app.test_client() as client,
    ):
        jeton = csrf_data(client)
        preparer_session(client)

        reponse = client.post(
            ROUTE,
            json={"id": "credential-test"},
            headers={"X-CSRFToken": jeton["csrf_token"]},
        )

    assert reponse.status_code == 400
    finaliser.assert_not_called()


def test_finalisation_erreur_postgresql(csrf_data):
    verification = SimpleNamespace(
        credential_id=b"credential-test",
        credential_public_key=b"public-key-test",
        sign_count=0,
    )

    with (
        patch("web.app.verifier_enregistrement", return_value=verification),
        patch(
            "web.app.finaliser_enregistrement_webauthn",
            side_effect=RuntimeError("Erreur PostgreSQL confidentielle"),
        ),
        app.test_client() as client,
    ):
        jeton = csrf_data(client)
        preparer_session(client)

        reponse = client.post(
            ROUTE,
            json={"id": "credential-test"},
            headers={"X-CSRFToken": jeton["csrf_token"]},
        )

    assert reponse.status_code == 500
    assert b"Erreur PostgreSQL confidentielle" not in reponse.data

def test_finalisation_passkey_deja_enregistree(csrf_data):
    verification = SimpleNamespace(
        credential_id=b"credential-test",
        credential_public_key=b"public-key-test",
        sign_count=0,
    )

    with (
        patch("web.app.verifier_enregistrement", return_value=verification),
        patch(
            "web.app.finaliser_enregistrement_webauthn",
            side_effect=UniqueViolation("Credential déjà existante"),
        ),
        app.test_client() as client,
    ):
        jeton = csrf_data(client)
        preparer_session(client)

        reponse = client.post(
            ROUTE,
            json={"id": "credential-test"},
            headers={"X-CSRFToken": jeton["csrf_token"]},
        )

        with client.session_transaction() as session:
            assert "passkey_registration" not in session

    assert reponse.status_code == 409
    assert b"Credential d" not in reponse.data



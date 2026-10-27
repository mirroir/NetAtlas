"""Tests de sécurité du parcours d'amorçage Passkey administrateur."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

import hashlib
from types import SimpleNamespace

from web.app import app

ROUTE_OPTIONS = "/admin/passkey/amorcage/options"
ROUTE_VERIFIER = "/admin/passkey/amorcage/verifier"

@pytest.fixture(autouse=True)
def autoriser_limiteur_passkey_pour_tests_amorcage():
    """Isole les tests WebAuthn du limiteur de tentatives."""

    with patch(
        "web.app.verifier_limites_combinees_passkey",
        return_value=(True, 0),
    ):
        yield


def test_amorcage_options_sans_csrf_refuse():
    """Une requête sans CSRF doit être refusée."""

    with app.test_client() as client:
        reponse = client.post(ROUTE_OPTIONS, json={})

    assert reponse.status_code == 400


def test_amorcage_verification_sans_csrf_refuse():
    """La finalisation sans CSRF doit être refusée."""

    with app.test_client() as client:
        reponse = client.post(ROUTE_VERIFIER, json={})

    assert reponse.status_code == 400


def test_amorcage_options_sans_autorisation_refuse(csrf_data):
    """Un visiteur sans autorisation ne peut générer de challenge."""

    with (
        patch("web.app.generer_options_enregistrement") as generer,
        app.test_client() as client,
    ):
        jeton = csrf_data(client)

        reponse = client.post(
            ROUTE_OPTIONS,
            json={},
            headers={"X-CSRFToken": jeton["csrf_token"]},
        )

    assert reponse.status_code == 403
    generer.assert_not_called()


def test_amorcage_verification_sans_autorisation_refuse(csrf_data):
    """Un visiteur sans autorisation ne peut enregistrer de Passkey."""

    with (
        patch("web.app.verifier_enregistrement") as verifier,
        app.test_client() as client,
    ):
        jeton = csrf_data(client)

        reponse = client.post(
            ROUTE_VERIFIER,
            json={"id": "credential-test"},
            headers={"X-CSRFToken": jeton["csrf_token"]},
        )

    assert reponse.status_code == 403
    verifier.assert_not_called()


def test_amorcage_options_session_admin_sans_jeton_refuse(csrf_data):
    """Même une session admin ne remplace pas l'autorisation d'amorçage."""

    with app.test_client() as client:
        jeton = csrf_data(client)

        with client.session_transaction() as session:
            session["user_id"] = 3
            session["nom"] = "Administrateur"
            session["role"] = "admin"

        reponse = client.post(
            ROUTE_OPTIONS,
            json={},
            headers={"X-CSRFToken": jeton["csrf_token"]},
        )

    assert reponse.status_code == 403

# ============================================================
# PASSKEY - TESTS DU PARCOURS D'AMORCAGE AUTORISÉ
# ============================================================


def test_amorcage_options_jeton_valide(csrf_data):
    """Un jeton valide permet de préparer la première Passkey."""

    token_bytes = b"a" * 32
    token = token_bytes.hex()
    token_hash = hashlib.sha256(token_bytes).digest()

    options = SimpleNamespace(challenge=b"c" * 32)

    administrateur = {
        "user_id": 2,
        "nom": "AdminNetAtlas",
    }

    with (
        patch(
            "web.app.verifier_amorcage_passkey_admin",
            return_value=True,
        ) as verifier,
        patch(
            "web.app.get_admin_passkey_bootstrap",
            return_value=administrateur,
        ),
        patch(
            "web.app.generer_options_enregistrement",
            return_value=options,
        ),
        patch("web.app.enregistrer_challenge_webauthn") as enregistrer,
        patch(
            "web.app.options_to_json",
            return_value='{"challenge": "test"}',
        ),
        app.test_client() as client,
    ):
        csrf = csrf_data(client)

        reponse = client.post(
            ROUTE_OPTIONS,
            json={"token": token},
            headers={"X-CSRFToken": csrf["csrf_token"]},
        )

        with client.session_transaction() as session:
            tentative = session.get("passkey_bootstrap_registration")

    assert reponse.status_code == 200
    assert tentative is not None
    assert tentative["user_id"] == 2
    assert tentative["token_hash"] == token_hash.hex()

    verifier.assert_called_once_with(2, token_hash)
    enregistrer.assert_called_once()


def test_amorcage_options_jeton_invalide(csrf_data):
    """Un jeton incorrect doit être refusé."""

    with (
        patch(
            "web.app.verifier_amorcage_passkey_admin",
            return_value=False,
        ),
        patch("web.app.generer_options_enregistrement") as generer,
        app.test_client() as client,
    ):
        csrf = csrf_data(client)

        reponse = client.post(
            ROUTE_OPTIONS,
            json={"token": (b"a" * 32).hex()},
            headers={"X-CSRFToken": csrf["csrf_token"]},
        )

    assert reponse.status_code == 403
    generer.assert_not_called()


def test_amorcage_options_admin_non_eligible(csrf_data):
    """Un administrateur possédant déjà une Passkey est refusé."""

    with (
        patch(
            "web.app.verifier_amorcage_passkey_admin",
            return_value=True,
        ),
        patch(
            "web.app.get_admin_passkey_bootstrap",
            return_value=None,
        ),
        patch("web.app.generer_options_enregistrement") as generer,
        app.test_client() as client,
    ):
        csrf = csrf_data(client)

        reponse = client.post(
            ROUTE_OPTIONS,
            json={"token": (b"a" * 32).hex()},
            headers={"X-CSRFToken": csrf["csrf_token"]},
        )

    assert reponse.status_code == 403
    generer.assert_not_called()


def test_amorcage_verification_reussie(csrf_data):
    """Une Passkey valide est enregistrée atomiquement."""

    verification = SimpleNamespace(
        credential_id=b"credential-test",
        credential_public_key=b"public-key-test",
        sign_count=0,
    )

    with (
        patch(
            "web.app.verifier_enregistrement",
            return_value=verification,
        ),
        patch(
            "web.app.finaliser_amorcage_passkey_admin",
            return_value=42,
        ) as finaliser,
        app.test_client() as client,
    ):
        csrf = csrf_data(client)

        with client.session_transaction() as session:
            session["passkey_bootstrap_registration"] = {
                "challenge": (b"c" * 32).hex(),
                "session_binding": (b"s" * 32).hex(),
                "token_hash": (b"t" * 32).hex(),
                "user_id": 2,
            }

        reponse = client.post(
            ROUTE_VERIFIER,
            json={"id": "credential-test"},
            headers={"X-CSRFToken": csrf["csrf_token"]},
        )

        with client.session_transaction() as session:
            tentative = session.get("passkey_bootstrap_registration")

    assert reponse.status_code == 201
    assert reponse.get_json()["credential_id"] == 42
    assert tentative is None
    finaliser.assert_called_once()


def test_amorcage_verification_jeton_expire(csrf_data):
    """Un jeton expiré ou déjà utilisé interdit l'enregistrement."""

    verification = SimpleNamespace(
        credential_id=b"credential-test",
        credential_public_key=b"public-key-test",
        sign_count=0,
    )

    with (
        patch(
            "web.app.verifier_enregistrement",
            return_value=verification,
        ),
        patch(
            "web.app.finaliser_amorcage_passkey_admin",
            return_value=False,
        ),
        app.test_client() as client,
    ):
        csrf = csrf_data(client)

        with client.session_transaction() as session:
            session["passkey_bootstrap_registration"] = {
                "challenge": (b"c" * 32).hex(),
                "session_binding": (b"s" * 32).hex(),
                "token_hash": (b"t" * 32).hex(),
                "user_id": 2,
            }

        reponse = client.post(
            ROUTE_VERIFIER,
            json={"id": "credential-test"},
            headers={"X-CSRFToken": csrf["csrf_token"]},
        )

    assert reponse.status_code == 403

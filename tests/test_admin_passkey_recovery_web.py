"""Tests Web du parcours de récupération Passkey administrateur."""

import hashlib
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from web.app import app

ROUTE_OPTIONS = "/admin/passkey/recuperation/options"
ROUTE_VERIFIER = "/admin/passkey/recuperation/verifier"

TOKEN_BYTES = b"t" * 32
TOKEN = TOKEN_BYTES.hex()
TOKEN_HASH = hashlib.sha256(TOKEN_BYTES).digest()

ADMINISTRATEUR = {
    "user_id": 2,
    "nom": "AdminNetAtlas",
}


@pytest.fixture(autouse=True)
def autoriser_limiteur_passkey():
    """Isole les tests HTTP du limiteur de tentatives."""

    with patch(
        "web.app.verifier_limites_combinees_passkey",
        return_value=(True, 0),
    ):
        yield


def envoyer_options(client, csrf_data, donnees):
    """Envoie une requête avec un jeton CSRF valide."""

    csrf = csrf_data(client)

    return client.post(
        ROUTE_OPTIONS,
        json=donnees,
        headers={"X-CSRFToken": csrf["csrf_token"]},
    )


def test_recuperation_options_sans_csrf_refuse():
    """La récupération exige une protection CSRF."""

    with app.test_client() as client:
        reponse = client.post(
            ROUTE_OPTIONS,
            json={"token": TOKEN},
        )

    assert reponse.status_code == 400


@pytest.mark.parametrize(
    "donnees",
    [
        {},
        {"token": None},
        {"token": 123},
        {"token": ""},
        {"token": "abc"},
        {"token": "z" * 64},
        {"token": "a" * 63},
    ],
)
def test_recuperation_options_jeton_mal_forme(
    csrf_data,
    donnees,
):
    """Les jetons mal formés sont refusés avant accès SQL."""

    with (
        patch(
            "web.app.identifier_admin_recuperation_passkey"
        ) as identifier,
        app.test_client() as client,
    ):
        reponse = envoyer_options(
            client,
            csrf_data,
            donnees,
        )

    assert reponse.status_code == 403
    identifier.assert_not_called()


def test_recuperation_options_json_invalide(csrf_data):
    """Un corps JSON qui n'est pas un objet est refusé."""

    with (
        patch(
            "web.app.identifier_admin_recuperation_passkey"
        ) as identifier,
        app.test_client() as client,
    ):
        reponse = envoyer_options(
            client,
            csrf_data,
            ["token", TOKEN],
        )

    assert reponse.status_code == 403
    identifier.assert_not_called()


def test_recuperation_options_jeton_inconnu(csrf_data):
    """Un jeton inconnu ne génère aucun challenge."""

    with (
        patch(
            "web.app.identifier_admin_recuperation_passkey",
            return_value=None,
        ) as identifier,
        patch(
            "web.app.generer_options_enregistrement"
        ) as generer,
        app.test_client() as client,
    ):
        reponse = envoyer_options(
            client,
            csrf_data,
            {"token": TOKEN},
        )

    assert reponse.status_code == 403
    identifier.assert_called_once_with(TOKEN_HASH)
    generer.assert_not_called()


def test_recuperation_options_autorisee(csrf_data):
    """Une autorisation valide prépare un challenge WebAuthn."""

    challenge = b"c" * 32

    options = SimpleNamespace(
        challenge=challenge,
    )

    with (
        patch(
            "web.app.identifier_admin_recuperation_passkey",
            return_value=ADMINISTRATEUR,
        ) as identifier,
        patch(
            "web.app.generer_options_enregistrement",
            return_value=options,
        ) as generer,
        patch(
            "web.app.preparer_recuperation_passkey_admin_securisee",
            return_value=ADMINISTRATEUR,
        ) as preparer,
        patch(
            "web.app.options_to_json",
            return_value='{"challenge":"test"}',
        ),
        app.test_client() as client,
    ):
        reponse = envoyer_options(
            client,
            csrf_data,
            {"token": TOKEN},
        )

        with client.session_transaction() as session:
            tentative = session.get(
                "passkey_recovery_registration"
            )

    assert reponse.status_code == 200
    assert tentative is not None

    assert set(tentative) == {
        "context_reference",
        "session_binding",
    }

    reference = bytes.fromhex(tentative["context_reference"])
    liaison = bytes.fromhex(tentative["session_binding"])

    assert len(reference) == 32
    assert len(liaison) == 32

    assert TOKEN not in reponse.get_data(as_text=True)
    assert TOKEN_HASH.hex() not in reponse.get_data(as_text=True)

    identifier.assert_called_once_with(TOKEN_HASH)

    generer.assert_called_once_with(
        user_id=2,
        nom="AdminNetAtlas",
    )

    preparer.assert_called_once_with(
        token_hash=TOKEN_HASH,
        challenge=challenge,
        session_binding_hash=hashlib.sha256(liaison).digest(),
        context_hash=hashlib.sha256(reference).digest(),
    )

def test_recuperation_options_autorisation_expiree(csrf_data):
    """Une autorisation expirée ne crée aucune session."""

    options = SimpleNamespace(
        challenge=b"c" * 32,
    )

    with (
        patch(
            "web.app.identifier_admin_recuperation_passkey",
            return_value=ADMINISTRATEUR,
        ),
        patch(
            "web.app.generer_options_enregistrement",
            return_value=options,
        ),
        patch(
            "web.app.preparer_recuperation_passkey_admin_securisee",
            return_value=None,
        ),
        app.test_client() as client,
    ):
        reponse = envoyer_options(
            client,
            csrf_data,
            {"token": TOKEN},
        )

        with client.session_transaction() as session:
            tentative = session.get(
                "passkey_recovery_registration"
            )

    assert reponse.status_code == 403
    assert tentative is None


def test_recuperation_options_admin_incoherent(csrf_data):
    """Un changement d'identité interdit la préparation."""

    options = SimpleNamespace(
        challenge=b"c" * 32,
    )

    autre_administrateur = {
        "user_id": 3,
        "nom": "AutreAdmin",
    }

    with (
        patch(
            "web.app.identifier_admin_recuperation_passkey",
            return_value=ADMINISTRATEUR,
        ),
        patch(
            "web.app.generer_options_enregistrement",
            return_value=options,
        ),
        patch(
            "web.app.preparer_recuperation_passkey_admin_securisee",
            return_value=autre_administrateur,
        ),
        app.test_client() as client,
    ):
        reponse = envoyer_options(
            client,
            csrf_data,
            {"token": TOKEN},
        )

    assert reponse.status_code == 403


def test_recuperation_options_efface_ancienne_session(csrf_data):
    """Une nouvelle tentative efface la précédente."""

    with (
        patch(
            "web.app.identifier_admin_recuperation_passkey",
            return_value=None,
        ),
        app.test_client() as client,
    ):
        csrf = csrf_data(client)

        with client.session_transaction() as session:
            session["passkey_recovery_registration"] = {
                "ancienne": "tentative",
            }

        reponse = client.post(
            ROUTE_OPTIONS,
            json={"token": TOKEN},
            headers={"X-CSRFToken": csrf["csrf_token"]},
        )

        with client.session_transaction() as session:
            tentative = session.get(
                "passkey_recovery_registration"
            )

    assert reponse.status_code == 403
    assert tentative is None


def test_recuperation_verification_reste_fermee(csrf_data):
    """La finalisation reste désactivée."""

    with app.test_client() as client:
        csrf = csrf_data(client)

        reponse = client.post(
            ROUTE_VERIFIER,
            json={},
            headers={"X-CSRFToken": csrf["csrf_token"]},
        )

    assert reponse.status_code == 403

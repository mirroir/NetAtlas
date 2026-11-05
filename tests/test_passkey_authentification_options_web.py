
"""Tests HTTP de la génération des options d'authentification Passkey."""

import hashlib
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from web.app import app

ROUTE_OPTIONS = "/passkey/authentification/options"
CHALLENGE = b"c" * 32


@pytest.fixture(autouse=True)
def autoriser_limiteur_passkey():
    """Isole les tests fonctionnels du limiteur Passkey."""
    with patch(
        "web.app.verifier_limites_combinees_passkey",
        return_value=(True, 0),
    ):
        yield


def test_options_authentification_sans_csrf_refuse():
    """Une requête sans jeton CSRF est refusée."""
    with app.test_client() as client:
        reponse = client.post(ROUTE_OPTIONS)

    assert reponse.status_code == 400


def test_options_authentification_csrf_invalide_refuse(csrf_data):
    """Un jeton CSRF incorrect est refusé."""
    with app.test_client() as client:
        csrf_data(client)

        reponse = client.post(
            ROUTE_OPTIONS,
            headers={"X-CSRFToken": "jeton-invalide"},
        )

    assert reponse.status_code == 400


def test_options_authentification_reussies(csrf_data):
    """Génère un challenge et conserve une tentative non authentifiée."""
    options = SimpleNamespace(challenge=CHALLENGE)

    with (
        patch(
            "web.app.generer_options_authentification",
            return_value=options,
        ) as generer,
        patch("web.app.enregistrer_challenge_webauthn") as enregistrer,
        patch(
            "web.app.options_to_json",
            return_value='{"challenge": "test"}',
        ),
        app.test_client() as client,
    ):
        jeton = csrf_data(client)

        reponse = client.post(
            ROUTE_OPTIONS,
            headers={"X-CSRFToken": jeton["csrf_token"]},
        )

        with client.session_transaction() as session:
            tentative = session.get("passkey_authentication")
            user_id = session.get("user_id")
            role = session.get("role")

    assert reponse.status_code == 200
    assert reponse.is_json
    assert reponse.get_json() == {"challenge": "test"}

    generer.assert_called_once()
    enregistrer.assert_called_once()

    assert tentative is not None
    assert tentative["challenge"] == CHALLENGE.hex()
    assert len(bytes.fromhex(tentative["session_binding"])) == 32
    assert user_id is None
    assert role is None


def test_options_authentification_empreintes(csrf_data):
    """Enregistre les empreintes SHA-256 et une expiration de 60 secondes."""
    options = SimpleNamespace(challenge=CHALLENGE)

    with (
        patch(
            "web.app.generer_options_authentification",
            return_value=options,
        ),
        patch("web.app.enregistrer_challenge_webauthn") as enregistrer,
        patch("web.app.options_to_json", return_value="{}"),
        app.test_client() as client,
    ):
        jeton = csrf_data(client)

        reponse = client.post(
            ROUTE_OPTIONS,
            headers={"X-CSRFToken": jeton["csrf_token"]},
        )

        with client.session_transaction() as session:
            tentative = session["passkey_authentication"]

    assert reponse.status_code == 200

    arguments = enregistrer.call_args.kwargs

    assert arguments["challenge_hash"] == hashlib.sha256(CHALLENGE).digest()
    assert arguments["session_binding_hash"] == hashlib.sha256(
        bytes.fromhex(tentative["session_binding"])
    ).digest()
    assert arguments["operation"] == "authentication"
    assert arguments["duree_secondes"] == 60


def test_options_authentification_remplace_tentative(csrf_data):
    """Une nouvelle génération remplace la tentative précédente."""
    options = SimpleNamespace(challenge=CHALLENGE)

    with (
        patch(
            "web.app.generer_options_authentification",
            return_value=options,
        ),
        patch("web.app.enregistrer_challenge_webauthn"),
        patch("web.app.options_to_json", return_value="{}"),
        app.test_client() as client,
    ):
        jeton = csrf_data(client)

        with client.session_transaction() as session:
            session["passkey_authentication"] = {
                "challenge": "ancien-challenge",
                "session_binding": "ancienne-liaison",
            }

        reponse = client.post(
            ROUTE_OPTIONS,
            headers={"X-CSRFToken": jeton["csrf_token"]},
        )

        with client.session_transaction() as session:
            tentative = session["passkey_authentication"]

    assert reponse.status_code == 200
    assert tentative["challenge"] == CHALLENGE.hex()
    assert tentative["session_binding"] != "ancienne-liaison"


def test_options_authentification_cache_desactive(csrf_data):
    """Les réponses sensibles ne doivent pas être mises en cache."""
    options = SimpleNamespace(challenge=CHALLENGE)

    with (
        patch(
            "web.app.generer_options_authentification",
            return_value=options,
        ),
        patch("web.app.enregistrer_challenge_webauthn"),
        patch("web.app.options_to_json", return_value="{}"),
        app.test_client() as client,
    ):
        jeton = csrf_data(client)

        reponse = client.post(
            ROUTE_OPTIONS,
            headers={"X-CSRFToken": jeton["csrf_token"]},
        )

    assert reponse.status_code == 200
    assert reponse.headers["Cache-Control"] == "no-store"
    assert reponse.headers["Pragma"] == "no-cache"

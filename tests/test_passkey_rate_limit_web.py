"""Tests HTTP de la limitation des tentatives Passkey."""

from unittest.mock import patch

import pytest

from web.app import app

ROUTES_PASSKEY_PROTEGEES = [
    "/admin/passkey/amorcage/options",
    "/admin/passkey/amorcage/verifier",
    "/admin/passkey/recuperation/options",
    "/admin/passkey/recuperation/verifier",
]


@pytest.fixture
def client(monkeypatch):
    """Prépare Flask pour tester le limiteur indépendamment du CSRF."""

    monkeypatch.setenv("NETATLAS_RATE_LIMIT_SECRET", "a" * 64)

    ancienne_configuration = {
        "TESTING": app.config.get("TESTING"),
        "WTF_CSRF_ENABLED": app.config.get("WTF_CSRF_ENABLED"),
    }

    app.config.update(
        TESTING=True,
        WTF_CSRF_ENABLED=False,
    )

    try:
        with app.test_client() as client_test:
            yield client_test

    finally:
        app.config.update(ancienne_configuration)


@pytest.mark.parametrize("route", ROUTES_PASSKEY_PROTEGEES)
def test_limite_depassee_retourne_429(client, route):
    """Une tentative excessive doit être refusée."""

    with patch(
        "web.app.verifier_limites_combinees_passkey",
        return_value=(False, 120),
    ):
        reponse = client.post(route, json={})

    assert reponse.status_code == 429
    assert reponse.headers["Retry-After"] == "120"
    assert "Trop de tentatives" in reponse.get_json()["erreur"]


@pytest.mark.parametrize("route", ROUTES_PASSKEY_PROTEGEES)
def test_absence_cle_hmac_retourne_503(client, monkeypatch, route):
    """Le contrôle doit échouer si la clé HMAC est absente."""

    monkeypatch.delenv("NETATLAS_RATE_LIMIT_SECRET", raising=False)

    reponse = client.post(route, json={})

    assert reponse.status_code == 503


@pytest.mark.parametrize("route", ROUTES_PASSKEY_PROTEGEES)
def test_erreur_postgresql_retourne_503(client, route):
    """Une erreur du limiteur doit empêcher le traitement."""

    with patch(
        "web.app.verifier_limites_combinees_passkey",
        side_effect=RuntimeError("PostgreSQL indisponible"),
    ):
        reponse = client.post(route, json={})

    assert reponse.status_code == 503


@pytest.mark.parametrize("route", ROUTES_PASSKEY_PROTEGEES)
def test_tentative_autorisee_continue_traitement(client, route):
    """Une requête autorisée atteint le traitement existant."""

    with patch(
        "web.app.verifier_limites_combinees_passkey",
        return_value=(True, 0),
    ):
        reponse = client.post(route, json={})

    assert reponse.status_code == 403

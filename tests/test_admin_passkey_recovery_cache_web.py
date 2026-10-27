"""Tests de protection du cache des parcours Passkey sensibles."""

import pytest

from web.app import app


@pytest.fixture
def client():
    """Créer un client Flask pour les tests HTTP."""

    app.config["TESTING"] = True

    with app.test_client() as client_test:
        yield client_test


@pytest.mark.parametrize(
    "chemin",
    [
        "/admin/passkey/amorcage",
        "/admin/passkey/amorcage/options",
        "/admin/passkey/amorcage/verifier",
        "/admin/passkey/recuperation",
        "/admin/passkey/recuperation/options",
        "/admin/passkey/recuperation/verifier",
    ],
)
def test_reponses_passkey_sans_cache(client, chemin):
    """Les réponses Passkey sensibles interdisent le cache."""

    reponse = client.get(chemin)

    assert reponse.headers["Cache-Control"] == "no-store"
    assert reponse.headers["Pragma"] == "no-cache"


@pytest.mark.parametrize(
    "chemin",
    [
        "/admin/passkey/amorcage-inconnu",
        "/admin/passkey/recuperation-inconnue",
    ],
)
def test_routes_voisines_non_affectees(client, chemin):
    """Une URL voisine ne doit pas activer la protection spécifique."""

    reponse = client.get(chemin)

    assert reponse.status_code == 404
    assert reponse.headers.get("Cache-Control") != "no-store"
    assert reponse.headers.get("Pragma") != "no-cache"


@pytest.mark.parametrize(
    "chemin",
    [
        "/admin/passkey/recuperation",
        "/admin/passkey/recuperation/options",
        "/admin/passkey/recuperation/verifier",
    ],
)
def test_routes_recuperation_pas_encore_exposees(client, chemin):
    """Les routes de récupération ne sont pas encore disponibles."""

    reponse = client.get(chemin)

    assert reponse.status_code == 404

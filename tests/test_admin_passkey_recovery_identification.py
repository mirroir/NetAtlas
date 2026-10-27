"""Tests unitaires de l'identification Passkey administrateur."""

from unittest.mock import MagicMock

import pytest

from database import identifier_admin_recuperation_passkey


@pytest.fixture
def connexion_simulee(monkeypatch):
    """Simuler la connexion PostgreSQL."""

    connexion = MagicMock()

    monkeypatch.setattr(
        "database.connexion_db",
        lambda: connexion,
    )

    return connexion


@pytest.mark.parametrize(
    "empreinte",
    [
        None,
        "",
        b"",
        b"a" * 31,
        b"a" * 33,
    ],
)
def test_refuser_empreinte_invalide(connexion_simulee, empreinte):
    """Une empreinte invalide ne doit pas accéder à PostgreSQL."""

    with pytest.raises(ValueError, match="Empreinte du jeton invalide"):
        identifier_admin_recuperation_passkey(empreinte)

    connexion_simulee.cursor.assert_not_called()


def test_identification_reussie(connexion_simulee):
    """Retourner l'administrateur identifié par PostgreSQL."""

    curseur = connexion_simulee.cursor.return_value.__enter__.return_value
    curseur.fetchone.return_value = (3, "AdminTest")

    resultat = identifier_admin_recuperation_passkey(b"a" * 32)

    assert resultat == {
        "user_id": 3,
        "nom": "AdminTest",
    }

    requete, parametres = curseur.execute.call_args.args

    assert "public.identifier_admin_recuperation_passkey" in requete
    assert parametres == (b"a" * 32,)

    connexion_simulee.close.assert_called_once()


def test_jeton_inconnu(connexion_simulee):
    """Un jeton inconnu ne doit identifier aucun administrateur."""

    curseur = connexion_simulee.cursor.return_value.__enter__.return_value
    curseur.fetchone.return_value = None

    resultat = identifier_admin_recuperation_passkey(b"a" * 32)

    assert resultat is None

    connexion_simulee.close.assert_called_once()


def test_erreur_postgresql(connexion_simulee):
    """La connexion doit être fermée en cas d'erreur SQL."""

    curseur = connexion_simulee.cursor.return_value.__enter__.return_value
    curseur.execute.side_effect = RuntimeError(
        "Erreur PostgreSQL simulée"
    )

    with pytest.raises(RuntimeError, match="Erreur PostgreSQL simulée"):
        identifier_admin_recuperation_passkey(b"a" * 32)

    connexion_simulee.close.assert_called_once()

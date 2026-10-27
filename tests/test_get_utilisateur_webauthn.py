"""Tests de récupération des utilisateurs WebAuthn."""

from unittest.mock import MagicMock, patch

import pytest

import database


@pytest.mark.parametrize(
    "user_id",
    [None, 0, -1, True, False, "3", 3.5],
)
def test_get_utilisateur_webauthn_identifiant_invalide(user_id):
    with pytest.raises(
        ValueError,
        match="Identifiant utilisateur invalide",
    ):
        database.get_utilisateur_webauthn(user_id, "admin")


@pytest.mark.parametrize(
    "role_nom",
    [None, "", "superadmin", "ADMIN", "moderateur", 123],
)
def test_get_utilisateur_webauthn_role_invalide(role_nom):
    with pytest.raises(
        ValueError,
        match="Rôle utilisateur invalide",
    ):
        database.get_utilisateur_webauthn(3, role_nom)


def test_get_utilisateur_webauthn_admin_existant():
    connexion = MagicMock()
    curseur = connexion.cursor.return_value.__enter__.return_value

    curseur.fetchone.return_value = (
        3,
        "AdminTestNetAtlas",
        "admin",
    )

    with patch("database.connexion_db", return_value=connexion):
        resultat = database.get_utilisateur_webauthn(3, "admin")

    assert resultat == {
        "user_id": 3,
        "nom": "AdminTestNetAtlas",
        "role": "admin",
    }

    curseur.execute.assert_called_once()
    connexion.close.assert_called_once()


def test_get_utilisateur_webauthn_utilisateur_existant():
    connexion = MagicMock()
    curseur = connexion.cursor.return_value.__enter__.return_value

    curseur.fetchone.return_value = (
        8,
        "UtilisateurTestNetAtlas",
        "utilisateur",
    )

    with patch("database.connexion_db", return_value=connexion):
        resultat = database.get_utilisateur_webauthn(
            8,
            "utilisateur",
        )

    assert resultat == {
        "user_id": 8,
        "nom": "UtilisateurTestNetAtlas",
        "role": "utilisateur",
    }

    connexion.close.assert_called_once()


def test_get_utilisateur_webauthn_inexistant():
    connexion = MagicMock()
    curseur = connexion.cursor.return_value.__enter__.return_value

    curseur.fetchone.return_value = None

    with patch("database.connexion_db", return_value=connexion):
        resultat = database.get_utilisateur_webauthn(
            999999,
            "admin",
        )

    assert resultat is None
    connexion.close.assert_called_once()


def test_get_utilisateur_webauthn_role_non_attribue():
    connexion = MagicMock()
    curseur = connexion.cursor.return_value.__enter__.return_value

    curseur.fetchone.return_value = None

    with patch("database.connexion_db", return_value=connexion):
        resultat = database.get_utilisateur_webauthn(
            8,
            "admin",
        )

    assert resultat is None

    curseur.execute.assert_called_once()
    connexion.close.assert_called_once()


def test_get_utilisateur_webauthn_fermeture_apres_erreur():
    connexion = MagicMock()
    curseur = connexion.cursor.return_value.__enter__.return_value

    curseur.execute.side_effect = RuntimeError(
        "Erreur PostgreSQL simulée"
    )

    with patch("database.connexion_db", return_value=connexion), pytest.raises(
        RuntimeError,
        match="Erreur PostgreSQL simulée",
    ):
        database.get_utilisateur_webauthn(3, "admin")

    connexion.close.assert_called_once()

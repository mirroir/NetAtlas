from unittest.mock import MagicMock, patch

import pytest

from database import preparer_recuperation_passkey_admin_securisee


def test_preparation_securisee_retourne_administrateur():
    connexion = MagicMock()
    curseur = connexion.cursor.return_value.__enter__.return_value
    curseur.fetchone.return_value = (2, "AdminNetAtlas")

    with patch("database.connexion_db", return_value=connexion):
        resultat = preparer_recuperation_passkey_admin_securisee(
            bytes.fromhex("a1" * 32),
            bytes.fromhex("b1" * 32),
            bytes.fromhex("c1" * 32),
            bytes.fromhex("d1" * 32),
        )

    assert resultat == {"user_id": 2, "nom": "AdminNetAtlas"}
    assert "preparer_recuperation_passkey_admin_securisee" in (
        curseur.execute.call_args.args[0]
    )
    connexion.commit.assert_called_once()
    connexion.close.assert_called_once()


def test_preparation_securisee_refuse_autorisation_inconnue():
    connexion = MagicMock()
    curseur = connexion.cursor.return_value.__enter__.return_value
    curseur.fetchone.return_value = None

    with patch("database.connexion_db", return_value=connexion):
        resultat = preparer_recuperation_passkey_admin_securisee(
            bytes(32), bytes(32), bytes(32), bytes(32)
        )

    assert resultat is None
    connexion.commit.assert_called_once()
    connexion.close.assert_called_once()


@pytest.mark.parametrize(
    "position",
    [0, 1, 2, 3],
)
def test_preparation_securisee_refuse_parametre_invalide(position):
    valeurs = [bytes(32), bytes(32), bytes(32), bytes(32)]
    valeurs[position] = b"invalide"

    with (
        patch("database.connexion_db") as connexion_db,
        pytest.raises(ValueError),
    ):
        preparer_recuperation_passkey_admin_securisee(*valeurs)
    connexion_db.assert_not_called()


def test_preparation_securisee_rollback_si_erreur_sql():
    connexion = MagicMock()
    curseur = connexion.cursor.return_value.__enter__.return_value
    curseur.execute.side_effect = RuntimeError("Erreur SQL simulee")

    with (
        patch("database.connexion_db", return_value=connexion),
        pytest.raises(RuntimeError, match="Erreur SQL simulee"),
    ):
        preparer_recuperation_passkey_admin_securisee(
            bytes(32), bytes(32), bytes(32), bytes(32)
        )

    connexion.rollback.assert_called_once()
    connexion.commit.assert_not_called()
    connexion.close.assert_called_once()

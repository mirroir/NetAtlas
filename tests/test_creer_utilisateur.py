import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.append(str(Path(__file__).parent.parent / "python"))

from database import creer_utilisateur


def test_creer_utilisateur_succes():
    connexion = MagicMock()
    curseur = MagicMock()

    connexion.cursor.return_value.__enter__.return_value = curseur
    curseur.fetchone.return_value = (42,)

    with (
        patch("database.connexion_db", return_value=connexion),
        patch("database.hash_pin", return_value="HASH_PIN"),
    ):
        user_id = creer_utilisateur("Alice", "2580")

    assert user_id == 42

    premier_appel = curseur.execute.call_args_list[0]
    assert premier_appel.args[1] == ("Alice", "HASH_PIN")

    second_appel = curseur.execute.call_args_list[1]
    assert second_appel.args[1] == (42, "utilisateur")

    connexion.commit.assert_called_once()
    connexion.rollback.assert_not_called()
    connexion.close.assert_called_once()


def test_creer_utilisateur_nom_vide():
    with pytest.raises(
        ValueError,
        match="Le nom de profil ne peut pas être vide.",
    ):
        creer_utilisateur("   ", "2580")


def test_creer_utilisateur_pin_invalide():
    with pytest.raises(
        ValueError,
        match="Le PIN doit contenir entre 4 et 6 chiffres.",
    ):
        creer_utilisateur("Alice", "12")


def test_creer_utilisateur_role_admin():
    connexion = MagicMock()
    curseur = MagicMock()

    connexion.cursor.return_value.__enter__.return_value = curseur
    curseur.fetchone.return_value = (1,)

    with (
        patch("database.connexion_db", return_value=connexion),
        patch("database.hash_pin", return_value="HASH_ADMIN"),
    ):
        user_id = creer_utilisateur(
            "Administrateur",
            "258036",
            role_nom="admin",
        )

    assert user_id == 1

    second_appel = curseur.execute.call_args_list[1]
    assert second_appel.args[1] == (1, "admin")


def test_creer_utilisateur_erreur_sql():
    connexion = MagicMock()
    curseur = MagicMock()

    connexion.cursor.return_value.__enter__.return_value = curseur
    curseur.execute.side_effect = Exception("Erreur SQL")

    with (
        patch("database.connexion_db", return_value=connexion),
        patch("database.hash_pin", return_value="HASH_PIN"),
        pytest.raises(Exception, match="Erreur SQL"),
    ):
        creer_utilisateur("Alice", "2580")

    connexion.rollback.assert_called_once()
    connexion.commit.assert_not_called()
    connexion.close.assert_called_once()




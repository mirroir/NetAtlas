import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.append(str(Path(__file__).parent.parent / "python"))

from database import authentifier_utilisateur


def test_authentifier_utilisateur_succes():
    connexion = MagicMock()
    curseur = MagicMock()

    connexion.cursor.return_value.__enter__.return_value = curseur
    curseur.fetchone.return_value = (42, "Alice", "HASH_PIN")

    with (
        patch("database.connexion_db", return_value=connexion),
        patch("database.verifier_pin", return_value=True),
    ):
        session = authentifier_utilisateur(
            "Alice",
            "2580",
            "utilisateur",
        )

    assert session == {
        "user_id": 42,
        "nom": "Alice",
        "role": "utilisateur",
    }

    connexion.close.assert_called_once()


def test_authentifier_utilisateur_mauvais_pin():
    connexion = MagicMock()
    curseur = MagicMock()

    connexion.cursor.return_value.__enter__.return_value = curseur
    curseur.fetchone.return_value = (42, "Alice", "HASH_PIN")

    with (
        patch("database.connexion_db", return_value=connexion),
        patch("database.verifier_pin", return_value=False),
    ):
        session = authentifier_utilisateur(
            "Alice",
            "9999",
            "utilisateur",
        )

    assert session is None
    connexion.close.assert_called_once()


def test_authentifier_utilisateur_inexistant():
    connexion = MagicMock()
    curseur = MagicMock()

    connexion.cursor.return_value.__enter__.return_value = curseur
    curseur.fetchone.return_value = None

    with patch("database.connexion_db", return_value=connexion):
        session = authentifier_utilisateur(
            "Inconnu",
            "2580",
            "utilisateur",
        )

    assert session is None
    connexion.close.assert_called_once()


def test_authentifier_utilisateur_mauvais_role():
    connexion = MagicMock()
    curseur = MagicMock()

    connexion.cursor.return_value.__enter__.return_value = curseur
    curseur.fetchone.return_value = None

    with patch("database.connexion_db", return_value=connexion):
        session = authentifier_utilisateur(
            "Alice",
            "2580",
            "admin",
        )

    assert session is None
    connexion.close.assert_called_once()




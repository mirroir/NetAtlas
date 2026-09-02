import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python"))

from database import get_users


def test_get_users_retourne_utilisateurs():
    connexion = MagicMock()
    curseur = MagicMock()

    connexion.cursor.return_value.__enter__.return_value = curseur
    curseur.fetchall.return_value = [
        (1, "Utilisateur Test", "test@netatlas.local"),
        (2, "Alice", "alice@netatlas.local"),
    ]

    with patch("database.connexion_db", return_value=connexion):
        resultat = get_users()

    assert resultat == [
        (1, "Utilisateur Test", "test@netatlas.local"),
        (2, "Alice", "alice@netatlas.local"),
    ]

    connexion.close.assert_called_once()


def test_get_users_aucun_utilisateur():
    connexion = MagicMock()
    curseur = MagicMock()

    connexion.cursor.return_value.__enter__.return_value = curseur
    curseur.fetchall.return_value = []

    with patch("database.connexion_db", return_value=connexion):
        resultat = get_users()

    assert resultat == []
    connexion.close.assert_called_once()




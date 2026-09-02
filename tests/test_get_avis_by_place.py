import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.append(str(Path(__file__).parent.parent / "python"))

from database import get_avis_by_place


def test_get_avis_by_place_avec_resultats():
    connexion = MagicMock()
    curseur = MagicMock()

    connexion.cursor.return_value.__enter__.return_value = curseur
    curseur.fetchall.return_value = [
        (1, "Marché agréable le samedi.", "Utilisateur Test"),
        (2, "Beaucoup de producteurs locaux.", "Alice"),
    ]

    with patch("database.connexion_db", return_value=connexion):
        resultat = get_avis_by_place(1)

    assert resultat == [
        (1, "Marché agréable le samedi.", "Utilisateur Test"),
        (2, "Beaucoup de producteurs locaux.", "Alice"),
    ]

    args = curseur.execute.call_args
    assert args.args[1] == (1,)
    connexion.close.assert_called_once()


def test_get_avis_by_place_sans_resultat():
    connexion = MagicMock()
    curseur = MagicMock()

    connexion.cursor.return_value.__enter__.return_value = curseur
    curseur.fetchall.return_value = []

    with patch("database.connexion_db", return_value=connexion):
        resultat = get_avis_by_place(1)

    assert resultat == []
    connexion.close.assert_called_once()



